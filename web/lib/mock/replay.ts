// Server only. Replays fixtures/expected/ as a stream in the contract's event format.
// The event order follows replay_claims() in backend/claimcheck/pipeline.py, with a
// listing-reader step in front so the trace shows the shape of a full run.

import { readFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { SAMPLES, normalise } from "@/lib/samples";
import type { EvidenceReport, StreamEvent } from "@/lib/types";

const fixturesDir = () =>
  path.resolve(/*turbopackIgnore: true*/ process.cwd(), process.env.CLAIMCHECK_FIXTURES_DIR ?? "../fixtures/expected");

/** Which fixture a mock request refers to, or null when it matches none. */
export function resolveFixtureId(input: { text?: string; filename?: string }): number | null {
  const fromName = (s: string) => {
    const m = /fixture[\s_-]*0*([1-9])(?!\d)/i.exec(s);
    return m ? Number(m[1]) : null;
  };
  if (input.filename) return fromName(input.filename);
  if (input.text) {
    const wanted = normalise(input.text);
    return SAMPLES.find((s) => normalise(s.text) === wanted)?.id ?? fromName(input.text);
  }
  return null;
}

export async function loadFixture(id: number): Promise<EvidenceReport> {
  const file = path.join(fixturesDir(), `fixture_${String(id).padStart(2, "0")}.json`);
  return JSON.parse(await readFile(file, "utf8")) as EvidenceReport;
}

type Draft = StreamEvent extends infer E ? (E extends StreamEvent ? Omit<E, "run_id" | "seq"> : never) : never;

function claimCount(report: EvidenceReport): number {
  return Object.values(report.claims).reduce<number>((n, v) => {
    if (Array.isArray(v)) return n + v.length;
    return v && typeof v === "object" ? n + 1 : n;
  }, 0);
}

export function eventsFor(report: EvidenceReport, source: "text" | "image"): StreamEvent[] {
  const runId = randomUUID().replace(/-/g, "").slice(0, 12);
  const drafts: Draft[] = [
    { type: "agent_step", agent: "orchestrator", message: `Received a listing as ${source === "image" ? "a screenshot" : "pasted text"}.` },
    { type: "agent_step", agent: "listing-reader", message: "Reading the claims the listing itself states." },
    { type: "tool_call", agent: "listing-reader", call_id: `${runId}-extract`, tool: "extract_claims", args: { source } },
    {
      type: "tool_result",
      agent: "listing-reader",
      call_id: `${runId}-extract`,
      tool: "extract_claims",
      ok: true,
      summary: `${claimCount(report)} claims extracted.`,
      result: report.claims,
    },
    { type: "agent_step", agent: "physics-checker", message: "Running the six checks on the extracted claims." },
  ];
  report.checks.forEach((check, index) => {
    const tool = `check_${check.check_id}`;
    const call_id = `${runId}-${index}`;
    drafts.push({ type: "tool_call", agent: "physics-checker", call_id, tool, args: {} });
    drafts.push({
      type: "tool_result",
      agent: "physics-checker",
      call_id,
      tool,
      ok: true,
      summary: `${check.status}: ${check.summary}`,
      result: check,
    });
  });
  drafts.push({ type: "agent_step", agent: "report-writer", message: "Assembling the evidence report." });
  drafts.push({ type: "final_report", agent: "report-writer", report });
  return drafts.map((d, seq) => ({ ...d, run_id: runId, seq }) as StreamEvent);
}

export function errorEvents(message: string): StreamEvent[] {
  const run_id = randomUUID().replace(/-/g, "").slice(0, 12);
  return [
    { type: "agent_step", run_id, seq: 0, agent: "orchestrator", message: "Received a listing." },
    { type: "error", run_id, seq: 1, agent: "orchestrator", message },
  ];
}

/** Same framing as claimcheck.events.to_sse. */
export const toSse = (event: StreamEvent) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`;
