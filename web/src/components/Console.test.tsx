import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { countItems, statsFromCounts } from "@/lib/counts";
import type { BatchResponse, DashboardStats } from "@/lib/types";
import { SAMPLES } from "@/samples";
import { Console } from "./Console";

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });

function sse(...frames: [string, unknown][]): Response {
  const text = frames.map(([name, data]) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`).join("");
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

const NO_RUN = (mode: "live" | "replay"): DashboardStats => ({
  mode,
  sample_data: mode === "replay",
  has_run: false,
  ran_at: null,
  listings_checked: null,
  impossible_claims: null,
  routed_to_human_review: null,
  no_action_needed: null,
  auto_resolvable: null,
  errors: null,
  by_verdict: null,
  by_routing: null,
});

function metric(key: string) {
  return within(screen.getByTestId(`metric-${key}`)).getByRole("definition");
}

/** A fake API. `stats` is what /api/dashboard-stats returns after a batch has run. */
function fakeApi(mode: "live" | "replay", stats: DashboardStats, stream?: () => Response, alreadyRan = false) {
  let ran = alreadyRan;
  const calls: string[] = [];
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    calls.push(`${init?.method ?? "GET"} ${path}`);
    if (path === "/api/dashboard-stats") return json(ran ? stats : NO_RUN(mode));
    if (path === "/api/batch" && (init?.method ?? "GET") === "GET") {
      return json(
        ran
          ? { mode, sample_data: mode === "replay", has_run: true, ran_at: "2026-11-14T12:00:00+00:00", items: SAMPLES, counts: countItems(SAMPLES) }
          : { mode, sample_data: mode === "replay", has_run: false, ran_at: null, items: [], counts: null },
      );
    }
    if (path === "/api/batch") {
      ran = true;
      const body: BatchResponse = { mode, sample_data: mode === "replay", ran_at: "2026-11-14T12:00:00+00:00", items: SAMPLES, counts: countItems(SAMPLES) };
      return json(body);
    }
    if (path === "/api/verify-listing" && stream) return stream();
    return new Response("not found", { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}

describe("Console with the API unreachable", () => {
  it("falls back to the bundled samples and says so", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    render(<Console />);

    await waitFor(() => expect(screen.getAllByTestId("feed-item")).toHaveLength(SAMPLES.length));
    expect(screen.getByTestId("source-pill")).toHaveTextContent("Sample data: the API is offline");
    expect(screen.getByTestId("sample-label")).toHaveTextContent("Sample data, API offline");
    expect(metric("listings_checked")).toHaveTextContent("29");
    expect(metric("impossible_claims")).toHaveTextContent("2");
    expect(metric("routed_to_human_review")).toHaveTextContent("10");
    expect(metric("no_action_needed")).toHaveTextContent("17");

    // the first sample is open: verdict card and math
    expect(within(screen.getByTestId("verdict-card")).getByTestId("verdict-badge")).toHaveTextContent("Impossible");
    expect(screen.getByTestId("card-sample-label")).toBeInTheDocument();
    expect(screen.getAllByTestId("check")).toHaveLength(6);
  });

  it("renders each of the bundled fixtures when it is picked from the feed", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    render(<Console />);
    await waitFor(() => expect(screen.getAllByTestId("feed-item")).toHaveLength(SAMPLES.length));

    for (const [index, sample] of SAMPLES.entries()) {
      fireEvent.click(screen.getAllByTestId("feed-item")[index]);
      const card = screen.getByTestId("verdict-card");
      expect(within(card).getByTestId("verdict-badge")).toHaveTextContent(new RegExp(`^${sample.report!.verdict}$`));
      expect(within(card).getByTestId("routing-label")).toHaveTextContent(sample.report!.routing);
      expect(within(card).getByTestId("listing-text")).toHaveTextContent(sample.listing_text!.split("\n")[0]);
      // six for a battery listing, one or two for a projector, magnifying glass or monocular
      expect(screen.getAllByTestId("check")).toHaveLength(sample.report!.checks.length);
      const notAssessed = sample.report!.checks.filter((c) => c.status === "not_assessed").length;
      expect(screen.queryAllByText("Not assessed", { selector: "[data-testid=check-status]" })).toHaveLength(notAssessed);
    }
  });

  it("does not present a sample report as the result for another listing", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    render(<Console />);
    await waitFor(() => expect(screen.getAllByTestId("feed-item")).toHaveLength(SAMPLES.length));

    fireEvent.change(screen.getByLabelText(/Paste the listing text/), { target: { value: "Some other battery 99999mAh" } });
    fireEvent.click(screen.getByRole("button", { name: /Check listing/ }));

    await waitFor(() => expect(screen.getByTestId("listing-error")).toHaveTextContent("The API is offline"));
    expect(within(screen.getByTestId("verdict-card")).queryByTestId("verdict-badge")).toBeNull();
  });
});

describe("Console in sample-data mode", () => {
  it("runs the batch on load and shows the API's counts, labelled as sample data", async () => {
    // counts that differ from the nine samples, to prove the tiles show what the API sent
    const stats = { ...statsFromCounts(countItems(SAMPLES), "replay", "2026-11-14T12:00:00+00:00"), listings_checked: 42, impossible_claims: 7, routed_to_human_review: 11, no_action_needed: 24 };
    const calls = fakeApi("replay", stats);
    render(<Console />);

    await waitFor(() => expect(metric("listings_checked")).toHaveTextContent("42"));
    expect(metric("impossible_claims")).toHaveTextContent("7");
    expect(metric("routed_to_human_review")).toHaveTextContent("11");
    expect(metric("no_action_needed")).toHaveTextContent("24");
    expect(screen.getByTestId("sample-label")).toHaveTextContent(/^Sample data$/);
    expect(screen.getByTestId("source-pill")).toHaveTextContent("Sample data: no model is configured");
    expect(calls).toEqual(["GET /api/dashboard-stats", "POST /api/batch", "GET /api/dashboard-stats"]);
    expect(screen.getAllByTestId("feed-item")).toHaveLength(SAMPLES.length);
  });

  it("shows the batch summary table", async () => {
    fakeApi("replay", statsFromCounts(countItems(SAMPLES), "replay", null));
    render(<Console />);
    await waitFor(() => expect(screen.getAllByTestId("feed-item")).toHaveLength(SAMPLES.length));

    fireEvent.click(screen.getByRole("tab", { name: "Batch" }));
    expect(screen.getAllByTestId("batch-row")).toHaveLength(SAMPLES.length);
    expect(screen.getByTestId("batch-sample-label")).toHaveTextContent("Sample data");
  });
});

describe("Console with a live model", () => {
  const stats = statsFromCounts(countItems(SAMPLES), "live", "2026-11-14T12:00:00+00:00");
  const report = SAMPLES[0].report!;
  const base = { run_id: "r1", agent: "orchestrator" as const };
  const stream = () =>
    sse(
      ["meta", { mode: "live", sample_data: false, sample_id: null }],
      ["agent_step", { ...base, type: "agent_step", seq: 0, message: "Reading the listing text." }],
      ["tool_call", { ...base, type: "tool_call", seq: 1, call_id: "c1", tool: "task", args: { subagent_type: "physics-checker" } }],
      ["tool_call", { ...base, agent: "physics-checker", type: "tool_call", seq: 2, call_id: "c2", tool: "check_form_factor_bound", args: {} }],
      ["tool_result", { ...base, agent: "physics-checker", type: "tool_result", seq: 3, call_id: "c2", tool: "check_form_factor_bound", ok: true, summary: "violated: over the cap", result: null }],
      ["final_report", { ...base, type: "final_report", seq: 4, report }],
    );

  it("shows no numbers and no sample label before a batch has run, and does not run one by itself", async () => {
    const calls = fakeApi("live", stats);
    render(<Console />);

    await waitFor(() => expect(screen.getByTestId("source-pill")).toHaveTextContent("Live model"));
    expect(metric("listings_checked")).toHaveTextContent("–");
    expect(screen.getByTestId("metrics-caption")).toHaveTextContent("No batch has run yet");
    expect(screen.queryByTestId("sample-label")).toBeNull();
    expect(calls).toEqual(["GET /api/dashboard-stats"]);
  });

  it("checks a pasted listing: live trace, then the verdict card and the math", async () => {
    const calls = fakeApi("live", stats, stream);
    render(<Console />);
    await waitFor(() => expect(screen.getByTestId("source-pill")).toHaveTextContent("Live model"));

    fireEvent.change(screen.getByLabelText(/Paste the listing text/), { target: { value: "Zentrovolt Outlet 18650 12000mAh 3.7V" } });
    fireEvent.click(screen.getByRole("button", { name: /Check listing/ }));

    await waitFor(() => expect(within(screen.getByTestId("verdict-card")).getByTestId("verdict-badge")).toHaveTextContent("Impossible"));
    expect(calls).toContain("POST /api/verify-listing");
    expect(screen.getAllByTestId("trace-line").map((el) => el.textContent)).toEqual([
      "OrchestratorstepReading the listing text.",
      "OrchestratorcallHands over to physics-checker",
      "Physics checkercallcheck_form_factor_bound",
      "Physics checkerresultviolated: over the cap",
      "OrchestratorreportImpossible, auto-resolvable",
    ]);
    expect(screen.queryByTestId("card-sample-label")).toBeNull();
    expect(screen.getAllByTestId("check")).toHaveLength(6);

    // the pasted text is in the listing pane only; the feed shows the description
    expect(screen.getByTestId("listing-text")).toHaveTextContent("Zentrovolt Outlet");
    const feed = screen.getByRole("navigation", { name: "Audit feed" });
    expect(feed).not.toHaveTextContent("Zentrovolt");
    expect(within(feed).getByTestId("feed-item")).toHaveTextContent("18650 lithium-ion battery, 12,000 mAh, 3.7 V");
  });

  it("shows the error event when a check fails", async () => {
    fakeApi("live", stats, () =>
      sse(["meta", { mode: "live", sample_data: false, sample_id: null }], ["error", { ...base, type: "error", seq: 0, message: "The listing could not be read into claims, so no check was run." }]),
    );
    render(<Console />);
    await waitFor(() => expect(screen.getByTestId("source-pill")).toHaveTextContent("Live model"));

    fireEvent.change(screen.getByLabelText(/Paste the listing text/), { target: { value: "hello" } });
    fireEvent.click(screen.getByRole("button", { name: /Check listing/ }));
    await waitFor(() => expect(screen.getByTestId("listing-error")).toHaveTextContent("could not be read into claims"));
  });

  it("opens with a batch that was run ahead of time, labelled as pre-run with its time", async () => {
    const calls = fakeApi("live", stats, undefined, true);
    render(<Console />);

    await waitFor(() => expect(screen.getAllByTestId("feed-item")).toHaveLength(SAMPLES.length));
    expect(calls).toEqual(["GET /api/dashboard-stats", "GET /api/batch"]); // nothing was run
    expect(metric("listings_checked")).toHaveTextContent("29");
    expect(screen.getByTestId("prerun-label")).toHaveTextContent("Pre-run");
    expect(screen.getByTestId("metrics-caption")).toHaveTextContent("Counted from a pre-run batch");
    expect(screen.queryByTestId("sample-label")).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "Batch" }));
    const label = screen.getByTestId("batch-run-label");
    expect(label).toHaveTextContent("Pre-run batch");
    expect(label).toHaveTextContent(new Date("2026-11-14T12:00:00+00:00").toLocaleString());
    expect(screen.getAllByTestId("batch-row")).toHaveLength(SAMPLES.length);

    // running it again replaces the pre-run label
    fireEvent.click(screen.getByRole("button", { name: "Run batch" }));
    await waitFor(() => expect(screen.getByTestId("batch-run-label")).toHaveTextContent(/^Ran, /));
    expect(screen.queryByTestId("prerun-label")).toBeNull();
  });

  it("runs the batch on request and fills the counts", async () => {
    fakeApi("live", stats);
    render(<Console />);
    await waitFor(() => expect(screen.getByTestId("source-pill")).toHaveTextContent("Live model"));

    fireEvent.click(screen.getByRole("tab", { name: "Batch" }));
    fireEvent.click(screen.getByRole("button", { name: "Run batch" }));
    await waitFor(() => expect(screen.getAllByTestId("batch-row")).toHaveLength(SAMPLES.length));
    expect(metric("listings_checked")).toHaveTextContent("29");
    expect(screen.queryByTestId("batch-sample-label")).toBeNull();
  });
});
