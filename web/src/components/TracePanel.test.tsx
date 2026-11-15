import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { StreamEvent } from "@/lib/types";
import { SAMPLES } from "@/samples";
import { TracePanel, checkChips, pipeline, traceLine } from "./TracePanel";

const report = SAMPLES[0].report!;
const base = { run_id: "r1" } as const;

function check(seq: number, index: number): StreamEvent[] {
  const result = report.checks[index];
  const tool = `check_${result.check_id}`;
  return [
    { ...base, seq, agent: "physics-checker", type: "tool_call", call_id: `c${seq}`, tool, args: {} },
    { ...base, seq: seq + 1, agent: "physics-checker", type: "tool_result", call_id: `c${seq}`, tool, ok: true, summary: result.summary, result },
  ];
}

const START: StreamEvent[] = [
  { ...base, seq: 0, agent: "orchestrator", type: "agent_step", message: "Reading the listing." },
  { ...base, seq: 1, agent: "orchestrator", type: "tool_call", call_id: "t1", tool: "task", args: { subagent_type: "listing-reader" } },
  { ...base, seq: 2, agent: "listing-reader", type: "tool_call", call_id: "r1", tool: "record_claims", args: { claims: { capacity_mah: { value: 12000 } } } },
  { ...base, seq: 3, agent: "listing-reader", type: "tool_result", call_id: "r1", tool: "record_claims", ok: true, summary: "Recorded 4 claims.", result: null },
  { ...base, seq: 4, agent: "orchestrator", type: "tool_call", call_id: "t2", tool: "task", args: { subagent_type: "physics-checker" } },
];
const CHECKS = [0, 1, 2].flatMap((i) => check(5 + i * 2, i));
const FINAL: StreamEvent = { ...base, seq: 40, agent: "orchestrator", type: "final_report", report };

const lines = () => screen.getAllByTestId("trace-line");
const stageOf = (name: string) => document.querySelector(`[data-testid="pipeline-agent"][data-agent="${name}"]`)!.getAttribute("data-stage");
const filterFor = (name: string) => screen.getAllByTestId("trace-filter").find((f) => f.getAttribute("data-agent") === name)!;

describe("traceLine", () => {
  it("keeps the one-line wording the console depends on", () => {
    expect(traceLine(START[0])).toMatchObject({ kind: "step", text: "Reading the listing." });
    expect(traceLine(START[1])).toMatchObject({ kind: "call", text: "Hands over to listing-reader" });
    expect(traceLine(START[3])).toMatchObject({ kind: "result", text: "Recorded 4 claims." });
    expect(traceLine(FINAL)).toMatchObject({ kind: "report", text: `${report.verdict}, ${report.routing}` });
    expect(traceLine({ ...base, seq: 9, agent: "orchestrator", type: "error", message: "Model call failed." })).toMatchObject({ kind: "error" });
  });
});

describe("derived state", () => {
  it("reads check ids and statuses from the events, not from a fixed table", () => {
    const chips = checkChips([...START, ...CHECKS]);
    expect(chips.map((c) => c.id)).toEqual(report.checks.slice(0, 3).map((c) => c.check_id));
    expect(chips.map((c) => c.status)).toEqual(report.checks.slice(0, 3).map((c) => c.status));
    const unknown: StreamEvent = { ...base, seq: 50, agent: "physics-checker", type: "tool_result", call_id: "x", tool: "check_other_thing", ok: true, summary: "s", result: { status: "pass" } };
    expect(checkChips([unknown]).map((c) => [c.id, c.status])).toEqual([["other_thing", "pass"]]);
    const rejected: StreamEvent = { ...base, seq: 51, agent: "physics-checker", type: "tool_result", call_id: "y", tool: "check_weight_bound", ok: false, summary: "No claims recorded", result: null };
    expect(checkChips([rejected])[0].status).toBeNull();
  });

  it("fills every chip from the final report", () => {
    expect(checkChips([FINAL]).map((c) => c.status)).toEqual(report.checks.map((c) => c.status));
  });

  it("marks the working agent active, earlier agents done, and everyone done at the end", () => {
    expect(pipeline([], true).stages.orchestrator).toBe("active");
    const mid = pipeline([...START, ...CHECKS], true).stages;
    expect(mid).toMatchObject({ orchestrator: "done", "listing-reader": "done", "physics-checker": "active", "report-writer": "idle" });
    const end = pipeline([...START, ...CHECKS, FINAL], false).stages;
    expect(Object.values(end)).not.toContain("active");
    expect(pipeline(START, true).handovers).toEqual(["listing-reader", "physics-checker"]);
  });
});

describe("TracePanel", () => {
  it("keeps both empty states", () => {
    const { rerender } = render(<TracePanel events={[]} running />);
    expect(screen.getByText("Waiting for the first event.")).toBeInTheDocument();
    rerender(<TracePanel events={[]} running={false} />);
    expect(screen.getByText(/No trace for this listing/)).toBeInTheDocument();
    expect(screen.queryByTestId("trace-line")).toBeNull();
  });

  it("renders one row per event with the agent, kind and text, and nothing else in the row", () => {
    render(<TracePanel events={START} running />);
    expect(lines().map((el) => el.textContent)).toEqual([
      "OrchestratorstepReading the listing.",
      "OrchestratorcallHands over to listing-reader",
      "Listing readercallrecord_claims",
      "Listing readerresultRecorded 4 claims.",
      "OrchestratorcallHands over to physics-checker",
    ]);
    expect(screen.getByTestId("trace-live")).toBeInTheDocument();
  });

  it("shows the pipeline with the current agent pulsing and finished ones done", () => {
    render(<TracePanel events={[...START, ...CHECKS]} running />);
    expect(stageOf("orchestrator")).toBe("done");
    expect(stageOf("listing-reader")).toBe("done");
    expect(stageOf("physics-checker")).toBe("active");
    expect(stageOf("report-writer")).toBe("idle");
    expect(screen.getAllByTestId("pipeline-agent")).toHaveLength(4);
  });

  it("lights up check chips as results arrive, coloured by their status", () => {
    const { rerender } = render(<TracePanel events={START} running />);
    expect(screen.queryAllByTestId("check-chip")).toHaveLength(0);
    rerender(<TracePanel events={[...START, ...CHECKS.slice(0, 2)]} running />);
    let chips = screen.getAllByTestId("check-chip");
    expect(chips).toHaveLength(1);
    expect(chips[0]).toHaveAttribute("data-check-id", report.checks[0].check_id);
    expect(chips[0]).toHaveAttribute("data-status", report.checks[0].status);
    expect(chips[0]).toHaveTextContent(report.checks[0].title);
    rerender(<TracePanel events={[...START, ...CHECKS]} running />);
    chips = screen.getAllByTestId("check-chip");
    expect(chips.map((c) => c.getAttribute("data-status"))).toEqual(report.checks.slice(0, 3).map((c) => c.status));
  });

  it("expands a row to its details and collapses it again", () => {
    render(<TracePanel events={START} running />);
    const row = lines()[2];
    expect(row).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(row);
    expect(row).toHaveAttribute("aria-expanded", "true");
    const panel = screen.getByTestId("trace-details");
    expect(panel).toHaveTextContent("record_claims");
    expect(panel).toHaveTextContent('"capacity_mah"');
    // the row's own text is unchanged, so the console's trace assertions still hold
    expect(row.textContent).toBe("Listing readercallrecord_claims");
    fireEvent.click(row);
    expect(row).toHaveAttribute("aria-expanded", "false");
  });

  it("filters rows by agent with pressable toggles", () => {
    render(<TracePanel events={START} running />);
    const filters = screen.getAllByTestId("trace-filter");
    expect(filters).toHaveLength(4);
    expect(filters.every((f) => f.getAttribute("aria-pressed") === "true")).toBe(true);
    fireEvent.click(filterFor("orchestrator"));
    expect(filterFor("orchestrator")).toHaveAttribute("aria-pressed", "false");
    expect(lines().map((el) => el.getAttribute("data-agent"))).toEqual(["listing-reader", "listing-reader"]);
    fireEvent.click(filterFor("listing-reader"));
    expect(screen.queryByTestId("trace-line")).toBeNull();
    expect(screen.getByText("Every agent is filtered out.")).toBeInTheDocument();
    fireEvent.click(filterFor("orchestrator"));
    expect(lines()).toHaveLength(3);
  });

  it("offers a jump to latest once the person scrolls up and more events arrive", async () => {
    const { rerender } = render(<TracePanel events={START} running />);
    const list = screen.getByRole("list", { name: "Events" });
    Object.defineProperty(list, "scrollHeight", { value: 1000, configurable: true });
    Object.defineProperty(list, "clientHeight", { value: 300, configurable: true });
    list.scrollTop = 100;
    fireEvent.scroll(list);
    expect(screen.queryByTestId("trace-jump")).toBeNull();
    rerender(<TracePanel events={[...START, ...CHECKS]} running />);
    const jump = screen.getByTestId("trace-jump");
    expect(jump).toHaveTextContent("Jump to latest (6 new)");
    fireEvent.click(jump);
    await waitFor(() => expect(screen.queryByTestId("trace-jump")).toBeNull());
  });

  it("reveals the verdict, in its own colour, when the final report arrives", () => {
    const { rerender } = render(<TracePanel events={[...START, ...CHECKS]} running />);
    expect(screen.queryByTestId("trace-verdict")).toBeNull();
    rerender(<TracePanel events={[...START, ...CHECKS, FINAL]} running={false} />);
    const reveal = screen.getByTestId("trace-verdict");
    expect(reveal).toHaveTextContent(new RegExp(`^${report.verdict}$`));
    expect(reveal.style.color).toBe("rgb(242, 109, 120)"); // #f26d78, the Impossible colour
    expect(screen.queryByTestId("trace-live")).toBeNull();
    expect(screen.getAllByTestId("check-chip")).toHaveLength(6);
  });

  it("never says verified and never shows a seller, store or brand", () => {
    const { container } = render(<TracePanel events={[...START, ...CHECKS, FINAL]} running={false} />);
    lines().forEach((row) => fireEvent.click(row));
    const text = container.textContent!.toLowerCase();
    expect(text).not.toContain("verif");
    expect(text).not.toMatch(/seller|store\b|brand/);
    within(screen.getByRole("list", { name: "Events" })).getAllByRole("button").forEach((b) => expect(b).toHaveAttribute("aria-expanded"));
  });
});

describe("TracePanel auto-scroll", () => {
  it("moves the trace list to its bottom as events arrive, and only the list", () => {
    const { rerender } = render(<TracePanel events={START} running />);
    const list = screen.getByRole("list", { name: "Events" });
    Object.defineProperty(list, "scrollHeight", { value: 1200, configurable: true });
    const scrollTo = vi.fn();
    Object.defineProperty(list, "scrollTo", { value: scrollTo, configurable: true });

    rerender(<TracePanel events={[...START, ...CHECKS]} running />);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 1200, behavior: "smooth" });
  });

  it("does not follow the stream after the person has scrolled up", () => {
    const { rerender } = render(<TracePanel events={START} running />);
    const list = screen.getByRole("list", { name: "Events" });
    Object.defineProperty(list, "scrollHeight", { value: 1000, configurable: true });
    Object.defineProperty(list, "clientHeight", { value: 300, configurable: true });
    const scrollTo = vi.fn();
    Object.defineProperty(list, "scrollTo", { value: scrollTo, configurable: true });

    list.scrollTop = 100;
    fireEvent.scroll(list);
    scrollTo.mockClear();
    rerender(<TracePanel events={[...START, ...CHECKS]} running />);
    expect(scrollTo).not.toHaveBeenCalled();
    expect(screen.getByTestId("trace-jump")).toBeInTheDocument();
  });
});
