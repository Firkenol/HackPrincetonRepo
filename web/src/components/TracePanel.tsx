"use client";

import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import type { StreamEvent } from "@/lib/types";

// The live trace: one line per stream event, in the order the API sent them.

const AGENT: Record<StreamEvent["agent"], string> = {
  orchestrator: "Orchestrator",
  "listing-reader": "Listing reader",
  "physics-checker": "Physics checker",
  "report-writer": "Report writer",
};

export function traceLine(event: StreamEvent): { kind: string; text: string; tone: string } {
  switch (event.type) {
    case "agent_step":
      return { kind: "step", text: event.message, tone: "text-text" };
    case "tool_call": {
      const to = typeof event.args?.subagent_type === "string" ? ` to ${event.args.subagent_type}` : "";
      return { kind: "call", text: event.tool === "task" ? `Hands over${to}` : event.tool, tone: "text-accent" };
    }
    case "tool_result":
      return { kind: event.ok ? "result" : "rejected", text: event.summary, tone: event.ok ? "text-muted" : "text-flag" };
    case "final_report":
      return { kind: "report", text: `${event.report.verdict}, ${event.report.routing}`, tone: "text-text" };
    case "error":
      return { kind: "error", text: event.message, tone: "text-impossible" };
  }
}

export function TracePanel({ events, running }: { events: StreamEvent[]; running: boolean }) {
  const end = useRef<HTMLLIElement>(null);
  useEffect(() => {
    if (running) end.current?.scrollIntoView?.({ block: "nearest" });
  }, [events.length, running]);

  return (
    <section aria-labelledby="trace-heading" className="rounded-lg border border-line bg-panel">
      <div className="flex items-baseline justify-between border-b border-line-soft px-4 py-2.5">
        <h2 id="trace-heading" className="text-sm font-semibold text-text">
          Trace
        </h2>
        <span className="text-xs text-faint">{running ? "streaming" : `${events.length} events`}</span>
      </div>
      {events.length === 0 ? (
        <p className="px-4 py-3 text-sm leading-6 text-muted">
          {running ? "Waiting for the first event." : "No trace for this listing. Batch results arrive without one."}
        </p>
      ) : (
        <ol className="pane-scroll max-h-80 overflow-y-auto px-2 py-2">
          {events.map((event) => {
            const line = traceLine(event);
            return (
              <motion.li
                key={`${event.run_id}-${event.seq}`}
                data-testid="trace-line"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15 }}
                className="grid grid-cols-[7.5rem_3.5rem_1fr] gap-x-2 rounded px-2 py-1 text-xs leading-5"
              >
                <span className="truncate text-faint">{AGENT[event.agent] ?? event.agent}</span>
                <span className="font-mono text-faint">{line.kind}</span>
                <span className={`${line.kind === "call" ? "font-mono" : ""} ${line.tone}`}>{line.text}</span>
              </motion.li>
            );
          })}
          <li ref={end} aria-hidden />
        </ol>
      )}
    </section>
  );
}
