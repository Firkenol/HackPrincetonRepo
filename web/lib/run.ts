// Client side of POST /api/check: sends one listing, reads the event stream, and
// folds the events into a RunState the UI renders.

import { useCallback, useEffect, useRef, useState } from "react";
import { isCheckResult, reportProblem } from "@/lib/types";
import type { CheckId, CheckResult, EvidenceReport, StreamEvent } from "@/lib/types";

export type ListingInput = { kind: "text"; name: string; text: string } | { kind: "image"; name: string; file: File };

export interface RunState {
  status: "idle" | "running" | "done" | "error";
  name: string;
  events: StreamEvent[];
  /** Check results seen so far, from tool results and then from the final report. */
  checks: Partial<Record<CheckId, CheckResult>>;
  report: EvidenceReport | null;
  error: string | null;
}

export const idleRun: RunState = { status: "idle", name: "", events: [], checks: {}, report: null, error: null };

export function applyEvent(state: RunState, event: StreamEvent): RunState {
  const next: RunState = { ...state, events: [...state.events, event] };
  if (event.type === "tool_result" && isCheckResult(event.result)) {
    next.checks = { ...state.checks, [event.result.check_id]: event.result };
  } else if (event.type === "final_report") {
    const problem = reportProblem(event.report);
    if (problem) return { ...next, status: "error", error: problem };
    next.report = event.report;
    next.checks = Object.fromEntries(event.report.checks.map((c) => [c.check_id, c]));
    next.status = "done";
  } else if (event.type === "error") {
    next.status = "error";
    next.error = event.message;
  }
  return next;
}

/** Parses Server-Sent Events frames from a fetch body. Yields each frame's JSON data. */
async function* sseData(body: ReadableStream<Uint8Array>): AsyncGenerator<unknown> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, "\n");
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""))
        .join("\n");
      if (data) yield JSON.parse(data);
    }
    if (done) return;
  }
}

/** Runs one listing to completion. Calls onState after every event. Never throws. */
export async function streamRun(
  input: ListingInput,
  onState: (state: RunState) => void,
  signal?: AbortSignal,
): Promise<RunState> {
  let state: RunState = { ...idleRun, status: "running", name: input.name };
  onState(state);
  const fail = (error: string) => {
    state = { ...state, status: "error", error };
    onState(state);
    return state;
  };
  try {
    const form = new FormData();
    if (input.kind === "text") form.set("text", input.text);
    else form.set("image", input.file, input.file.name);
    const response = await fetch("/api/check", { method: "POST", body: form, signal });
    if (!response.ok || !response.body) {
      const detail = await response
        .json()
        .then((j: { detail?: unknown }) => (typeof j.detail === "string" ? j.detail : null))
        .catch(() => null);
      return fail(detail ?? `The request failed with status ${response.status}.`);
    }
    for await (const data of sseData(response.body)) {
      state = applyEvent(state, data as StreamEvent);
      onState(state);
      if (state.status !== "running") return state;
    }
    return fail("The stream ended before a report arrived.");
  } catch (e) {
    if (signal?.aborted) return fail("Cancelled.");
    return fail(e instanceof SyntaxError ? "The stream carried data that is not valid JSON." : "The request could not be completed.");
  }
}

export function useRun() {
  const [state, setState] = useState<RunState>(idleRun);
  const abort = useRef<AbortController | null>(null);

  const start = useCallback((input: ListingInput) => {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    void streamRun(input, (s) => !controller.signal.aborted && setState(s), controller.signal);
  }, []);

  const reset = useCallback(() => {
    abort.current?.abort();
    setState(idleRun);
  }, []);

  useEffect(() => () => abort.current?.abort(), []);
  return { state, start, reset };
}

export function downloadJson(report: unknown, name: string) {
  const safe = name.replace(/\.[a-z0-9]+$/i, "").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() || "listing";
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2) + "\n"], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `claimcheck-${safe}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
