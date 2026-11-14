"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef } from "react";
import { STATUS_LABEL, STATUS_TONE } from "@/lib/format";
import type { RunState } from "@/lib/run";
import { isCheckResult } from "@/lib/types";
import type { AgentName, StreamEvent, ToolResultEvent } from "@/lib/types";

const AGENT_TONE: Record<AgentName, string> = {
  orchestrator: "bg-slate-200 text-slate-700",
  "listing-reader": "bg-teal-100 text-teal-800",
  "physics-checker": "bg-indigo-100 text-indigo-800",
  "report-writer": "bg-fuchsia-100 text-fuchsia-800",
};

type Row =
  | { key: string; agent: AgentName; kind: "step"; message: string }
  | { key: string; agent: AgentName; kind: "tool"; tool: string; args: Record<string, unknown>; result: ToolResultEvent | null }
  | { key: string; agent: AgentName; kind: "final"; text: string }
  | { key: string; agent: AgentName; kind: "error"; message: string };

function toRows(events: StreamEvent[]): Row[] {
  const rows: Row[] = [];
  const calls = new Map<string, Extract<Row, { kind: "tool" }>>();
  for (const e of events) {
    const key = `${e.run_id}-${e.seq}`;
    if (e.type === "agent_step") rows.push({ key, agent: e.agent, kind: "step", message: e.message });
    else if (e.type === "tool_call") {
      const row = { key, agent: e.agent, kind: "tool" as const, tool: e.tool, args: e.args ?? {}, result: null };
      calls.set(e.call_id, row);
      rows.push(row);
    } else if (e.type === "tool_result") {
      const row = calls.get(e.call_id);
      if (row) row.result = e;
      else rows.push({ key, agent: e.agent, kind: "tool", tool: e.tool, args: {}, result: e });
    } else if (e.type === "final_report") {
      rows.push({ key, agent: e.agent, kind: "final", text: `Report ready: ${e.report.verdict} · ${e.report.routing}` });
    } else rows.push({ key, agent: e.agent, kind: "error", message: e.message });
  }
  return rows;
}

function Spinner() {
  return <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" aria-label="running" />;
}

function ToolOutcome({ result }: { result: ToolResultEvent | null }) {
  if (!result) return <Spinner />;
  if (isCheckResult(result.result)) {
    const check = result.result;
    return (
      <>
        <span className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${STATUS_TONE[check.status]}`}>{STATUS_LABEL[check.status]}</span>
        <span className="truncate text-slate-500" title={check.summary}>
          {check.status === "not_assessed" ? check.not_assessed_reason ?? check.summary : check.summary}
        </span>
      </>
    );
  }
  return (
    <>
      <span className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ring-1 ring-inset ${result.ok ? "bg-slate-100 text-slate-700 ring-slate-200" : "bg-red-50 text-red-700 ring-red-200"}`}>
        {result.ok ? "returned" : "failed"}
      </span>
      <span className="truncate text-slate-500" title={result.summary}>
        {result.summary}
      </span>
    </>
  );
}

export function Trace({ run }: { run: RunState }) {
  const rows = useMemo(() => toRows(run.events), [run.events]);
  const box = useRef<HTMLOListElement>(null);
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight });
  }, [rows.length]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white" aria-label="Tool-call trace">
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-2.5">
        <h2 className="text-sm font-semibold text-slate-900">Live trace</h2>
        <span className="flex items-center gap-2 text-xs text-slate-500 tnum" data-testid="trace-status">
          {run.status === "running" && <Spinner />}
          {run.status === "idle" ? "waiting for a listing" : `${run.events.length} events`}
        </span>
      </header>
      <ol ref={box} className="max-h-[22rem] min-h-24 overflow-y-auto px-2 py-2 text-[13px]" data-testid="trace">
        <AnimatePresence initial={false}>
          {rows.map((row) => (
            <motion.li
              key={row.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-2 rounded px-2 py-1"
            >
              <span className={`shrink-0 rounded px-1.5 py-0.5 text-[11px] font-medium ${AGENT_TONE[row.agent] ?? AGENT_TONE.orchestrator}`}>{row.agent}</span>
              {row.kind === "step" && <span className="text-slate-700">{row.message}</span>}
              {row.kind === "tool" && (
                <>
                  <code className="shrink-0 font-mono text-[12px] text-slate-900">
                    {row.tool}
                    <span className="text-slate-400">({Object.keys(row.args).length ? JSON.stringify(row.args) : ""})</span>
                  </code>
                  <ToolOutcome result={row.result} />
                </>
              )}
              {row.kind === "final" && <span className="font-medium text-slate-900">{row.text}</span>}
              {row.kind === "error" && <span className="text-red-700">{row.message}</span>}
            </motion.li>
          ))}
        </AnimatePresence>
        {rows.length === 0 && <li className="px-2 py-3 text-slate-400">Agent steps and tool calls appear here as they happen.</li>}
      </ol>
    </section>
  );
}
