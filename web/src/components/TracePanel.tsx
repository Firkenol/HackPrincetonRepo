"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowDownToLine, Check, ChevronDown } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AGENTS, AGENT_ORDER, STATUS_HEX, VERDICT_HEX, agentOf, type AgentName } from "@/lib/agents";
import type { CheckStatus, StreamEvent } from "@/lib/types";

// The live trace. Everything on screen is read from the stream events: which agent is
// working, which check results have arrived and with what status, and the verdict.
// Nothing is computed, rounded or guessed in the browser.

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

// ------------------------------------------------------------------ derived state

const KIND_STYLE: Record<string, string> = {
  step: "bg-raised text-muted",
  call: "bg-accent/15 text-accent",
  result: "bg-clear/15 text-clear",
  rejected: "bg-flag/15 text-flag",
  report: "bg-text/15 text-text",
  error: "bg-impossible/15 text-impossible",
};

// The contract's six check ids in their fixed order, used only to sort the chips.
const CHECK_ORDER = ["label_consistency", "form_factor_bound", "dimension_bound", "weight_bound", "label_contradiction", "chemistry_mismatch"];

const STATUS_LABEL: Record<CheckStatus, string> = {
  pass: "Pass",
  flag: "Flag",
  violated: "Bound exceeded",
  not_assessed: "Not assessed",
};

interface ChipState {
  id: string;
  title: string;
  status: CheckStatus | null;
  seq: number;
}

function isStatus(value: unknown): value is CheckStatus {
  return value === "pass" || value === "flag" || value === "violated" || value === "not_assessed";
}

/** The check chips, from the check tool results (and the final report, if it came). */
export function checkChips(events: StreamEvent[]): ChipState[] {
  const chips = new Map<string, ChipState>();
  for (const event of events) {
    if (event.type === "tool_result" && event.tool.startsWith("check_")) {
      const result = event.result as { check_id?: unknown; title?: unknown; status?: unknown } | null;
      const id = typeof result?.check_id === "string" ? result.check_id : event.tool.slice("check_".length);
      chips.set(id, {
        id,
        title: typeof result?.title === "string" ? result.title : id.replace(/_/g, " "),
        status: event.ok && isStatus(result?.status) ? result.status : null,
        seq: event.seq,
      });
    }
    if (event.type === "final_report") {
      for (const check of event.report.checks) {
        chips.set(check.check_id, { id: check.check_id, title: check.title, status: check.status, seq: chips.get(check.check_id)?.seq ?? event.seq });
      }
    }
  }
  const rank = (id: string) => (CHECK_ORDER.includes(id) ? CHECK_ORDER.indexOf(id) : CHECK_ORDER.length);
  return [...chips.values()].sort((a, b) => rank(a.id) - rank(b.id) || a.seq - b.seq);
}

type Stage = "idle" | "active" | "done";

/** Which agents have worked, which is working now, and the hand-overs seen so far. */
export function pipeline(events: StreamEvent[], running: boolean): { stages: Record<AgentName, Stage>; handovers: AgentName[] } {
  const seen = new Set<AgentName>();
  const handovers: AgentName[] = [];
  for (const event of events) {
    seen.add(event.agent);
    if (event.type === "tool_call" && event.tool === "task" && typeof event.args?.subagent_type === "string") {
      handovers.push(event.args.subagent_type as AgentName);
    }
  }
  const last = events.at(-1);
  const finished = !running || last?.type === "final_report" || last?.type === "error";
  const current = finished ? null : last?.agent ?? "orchestrator";
  const stages = Object.fromEntries(
    AGENT_ORDER.map((name) => [name, name === current ? "active" : seen.has(name) ? "done" : "idle"]),
  ) as Record<AgentName, Stage>;
  if (!finished && !seen.size) stages.orchestrator = "active";
  return { stages, handovers };
}

function details(event: StreamEvent): { label: string; body: string }[] {
  switch (event.type) {
    case "agent_step":
      return [{ label: "Message", body: event.message }];
    case "tool_call":
      return [
        { label: "Tool", body: event.tool },
        { label: "Arguments", body: JSON.stringify(event.args ?? {}, null, 2) },
      ];
    case "tool_result":
      return [
        { label: "Tool", body: event.tool },
        { label: event.ok ? "Summary" : "Rejected", body: event.summary },
        ...(event.result !== null && event.result !== undefined ? [{ label: "Result", body: JSON.stringify(event.result, null, 2) }] : []),
      ];
    case "final_report":
      return [
        { label: "Verdict", body: event.report.verdict },
        { label: "Why", body: event.report.verdict_reason },
        { label: "Routing", body: event.report.routing },
        { label: "Why", body: event.report.routing_reason },
      ];
    case "error":
      return [{ label: "Error", body: event.message }];
  }
}

// ------------------------------------------------------------------ pieces

function PipelineStrip({ events, running }: { events: StreamEvent[]; running: boolean }) {
  const reduced = useReducedMotion();
  const { stages } = pipeline(events, running);
  return (
    <ol aria-label="Agents" className="flex items-center gap-1 px-4 py-3">
      {AGENT_ORDER.map((name, index) => {
        const agent = AGENTS[name];
        const stage = stages[name];
        const Icon = agent.icon;
        const next = AGENT_ORDER[index + 1];
        const linkLit = next ? stages[next] !== "idle" : false;
        return (
          <li key={name} className="flex min-w-0 flex-1 items-center gap-1 last:flex-none">
            <div
              data-testid="pipeline-agent"
              data-agent={name}
              data-stage={stage}
              title={`${agent.label}: ${agent.role}`}
              className="relative flex min-w-0 items-center gap-2 rounded-md border px-2 py-1.5 text-xs transition-colors"
              style={{
                borderColor: stage === "idle" ? "var(--color-line)" : agent.hex,
                color: stage === "idle" ? "var(--color-faint)" : agent.hex,
                background: stage === "idle" ? "transparent" : `color-mix(in srgb, ${agent.hex} 10%, transparent)`,
              }}
            >
              {stage === "active" && !reduced && (
                <motion.span
                  aria-hidden
                  className="absolute inset-0 rounded-md"
                  style={{ boxShadow: `0 0 0 1px ${agent.hex}` }}
                  animate={{ opacity: [0.9, 0.2, 0.9] }}
                  transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
                />
              )}
              <span className="relative grid size-5 shrink-0 place-items-center">
                {stage === "done" ? <Check size={14} aria-hidden /> : <Icon size={14} aria-hidden />}
              </span>
              <span className="relative truncate font-medium">{agent.label}</span>
              <span className="sr-only">{stage === "active" ? ", working" : stage === "done" ? ", done" : ", waiting"}</span>
            </div>
            {next && (
              <span aria-hidden className="relative h-px min-w-3 flex-1 bg-line">
                <motion.span
                  className="absolute inset-y-0 left-0"
                  style={{ background: AGENTS[next].hex }}
                  initial={false}
                  animate={{ width: linkLit ? "100%" : "0%" }}
                  transition={{ duration: reduced ? 0 : 0.45, ease: "easeOut" }}
                />
                {stages[next] === "active" && !reduced && (
                  <motion.span
                    className="absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full"
                    style={{ background: AGENTS[next].hex }}
                    animate={{ left: ["0%", "100%"], opacity: [0, 1, 0] }}
                    transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}
                  />
                )}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function CheckChips({ events }: { events: StreamEvent[] }) {
  const chips = useMemo(() => checkChips(events), [events]);
  return (
    <div className="border-t border-line-soft px-4 py-2.5">
      <div className="mb-1.5 flex items-baseline justify-between">
        <h3 className="text-xs font-medium text-muted">Checks</h3>
        <span className="text-xs text-faint">{chips.length ? `${chips.length} returned` : "none returned yet"}</span>
      </div>
      <ul aria-label="Check results" className="flex flex-wrap gap-1.5">
        <AnimatePresence initial={false}>
          {chips.map((chip) => {
            const hex = chip.status ? STATUS_HEX[chip.status] : "#93a0b4";
            return (
              <motion.li
                key={chip.id}
                layout
                data-testid="check-chip"
                data-check-id={chip.id}
                data-status={chip.status ?? "unknown"}
                initial={{ opacity: 0, scale: 0.85, y: 4 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 420, damping: 28 }}
                className="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs"
                style={{ borderColor: hex, color: hex, background: `color-mix(in srgb, ${hex} 12%, transparent)` }}
              >
                <span aria-hidden className="size-1.5 rounded-full" style={{ background: hex }} />
                <span className="text-text/90">{chip.title}</span>
                <span className="font-medium">{chip.status ? STATUS_LABEL[chip.status] : "no status"}</span>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
    </div>
  );
}

function EventRow({ event, open, onToggle }: { event: StreamEvent; open: boolean; onToggle: () => void }) {
  const line = traceLine(event);
  const agent = agentOf(event.agent);
  const reduced = useReducedMotion();
  return (
    <motion.li
      layout={!reduced}
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.18 }}
      className="rounded-md border-l-2"
      style={{ borderLeftColor: agent.hex }}
    >
      <button
        type="button"
        data-testid="trace-line"
        data-agent={event.agent}
        data-kind={line.kind}
        aria-expanded={open}
        onClick={onToggle}
        className={`grid w-full grid-cols-[7.5rem_4rem_1fr_1rem] items-start gap-x-2 rounded-md px-2 py-1 text-left text-xs leading-5 hover:bg-raised/70 ${open ? "bg-raised/60" : ""}`}
      >
        <span className="truncate" style={{ color: agent.hex }}>
          {AGENT[event.agent] ?? event.agent}
        </span>
        <span className={`self-center justify-self-start rounded px-1.5 font-mono text-[11px] leading-4 ${KIND_STYLE[line.kind] ?? "bg-raised text-muted"}`}>
          {line.kind}
        </span>
        <span className={`${line.kind === "call" ? "font-mono" : ""} ${line.tone}`}>{line.text}</span>
        <ChevronDown size={14} aria-hidden className={`mt-0.5 text-faint transition-transform ${open ? "" : "-rotate-90"}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            data-testid="trace-details"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.16 }}
            className="overflow-hidden"
          >
            <dl className="mx-2 mb-2 space-y-1.5 rounded-md bg-ink/70 px-3 py-2 text-xs">
              <div className="flex gap-2 text-faint">
                <dt>Event</dt>
                <dd className="font-mono">
                  {event.type} · seq {event.seq} · {AGENT[event.agent] ?? event.agent}
                </dd>
              </div>
              {details(event).map((d, i) => (
                <div key={`${d.label}-${i}`}>
                  <dt className="text-faint">{d.label}</dt>
                  <dd className="whitespace-pre-wrap break-words font-mono text-text">{d.body}</dd>
                </div>
              ))}
            </dl>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

// ------------------------------------------------------------------ the panel

export function TracePanel({ events, running }: { events: StreamEvent[]; running: boolean }) {
  // Keyed by run, so a new listing starts with nothing expanded and the stream followed.
  const runKey = events[0]?.run_id ?? "";
  return <TraceRun key={runKey} events={events} running={running} runKey={runKey} />;
}

function TraceRun({ events, running, runKey }: { events: StreamEvent[]; running: boolean; runKey: string }) {
  const reduced = useReducedMotion();
  const list = useRef<HTMLOListElement>(null);
  const [openKeys, setOpenKeys] = useState<Set<string>>(() => new Set());
  const [hidden, setHidden] = useState<Set<AgentName>>(() => new Set());
  // null: following the stream. A number: how many events there were when the person
  // scrolled up or hovered; events past it are the ones they have not seen.
  const [pausedAt, setPausedAt] = useState<number | null>(null);
  const pinned = pausedAt === null;
  const behind = pausedAt === null ? 0 : Math.max(0, events.length - pausedAt);

  // Follow the stream by moving the list itself to its bottom. scrollIntoView would also
  // scroll the page, which pulls the reader away from the verdict above the trace.
  const followEnd = useCallback(() => {
    const el = list.current;
    if (!el) return;
    el.scrollTo?.({ top: el.scrollHeight, behavior: reduced ? "auto" : "smooth" });
    if (typeof el.scrollTo !== "function") el.scrollTop = el.scrollHeight;
  }, [reduced]);

  useEffect(() => {
    if (pinned && (running || events.length)) followEnd();
  }, [events.length, running, pinned, followEnd]);

  const jump = useCallback(() => {
    setPausedAt(null);
    followEnd();
  }, [followEnd]);

  const pause = useCallback(() => setPausedAt((current) => current ?? events.length), [events.length]);

  const onScroll = useCallback(() => {
    const el = list.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
    if (atBottom) setPausedAt(null);
    else pause();
  }, [pause]);

  const toggle = (key: string) =>
    setOpenKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const toggleAgent = (name: AgentName) =>
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });

  const counts = useMemo(() => {
    const c = { orchestrator: 0, "listing-reader": 0, "physics-checker": 0, "report-writer": 0 } as Record<AgentName, number>;
    for (const event of events) c[event.agent] = (c[event.agent] ?? 0) + 1;
    return c;
  }, [events]);

  const shown = events.filter((event) => !hidden.has(event.agent));
  const last = events.at(-1);
  const verdict = last?.type === "final_report" ? last.report.verdict : null;
  const failed = last?.type === "error";
  const live = running && !verdict && !failed;

  return (
    <section aria-labelledby="trace-heading" className="rounded-lg border border-line bg-panel">
      <div className="flex items-center justify-between gap-3 border-b border-line-soft px-4 py-2.5">
        <h2 id="trace-heading" className="text-sm font-semibold text-text">
          Trace
        </h2>
        <div className="flex items-center gap-3 text-xs">
          <AnimatePresence>
            {verdict && (
              <motion.span
                key={`${runKey}-verdict`}
                data-testid="trace-verdict"
                role="status"
                initial={{ opacity: 0, scale: 0.8, filter: "blur(4px)" }}
                animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                transition={{ type: "spring", stiffness: 300, damping: 22 }}
                className="rounded-md border px-2 py-0.5 font-semibold"
                style={{ color: VERDICT_HEX[verdict], borderColor: VERDICT_HEX[verdict], background: `color-mix(in srgb, ${VERDICT_HEX[verdict]} 12%, transparent)` }}
              >
                {verdict}
              </motion.span>
            )}
          </AnimatePresence>
          {live ? (
            <span data-testid="trace-live" className="inline-flex items-center gap-1.5 text-clear">
              <span className="relative flex size-2">
                {!reduced && <span className="absolute inline-flex size-full animate-ping rounded-full bg-clear opacity-60" />}
                <span className="relative inline-flex size-2 rounded-full bg-clear" />
              </span>
              live
            </span>
          ) : (
            <span className="text-faint">{events.length === 1 ? "1 event" : `${events.length} events`}</span>
          )}
        </div>
      </div>

      {events.length === 0 ? (
        <p className="px-4 py-3 text-sm leading-6 text-muted">
          {running ? "Waiting for the first event." : "No trace for this listing. Batch results arrive without one."}
        </p>
      ) : (
        <>
          <PipelineStrip events={events} running={running} />
          <CheckChips events={events} />

          <div className="flex flex-wrap items-center gap-1.5 border-t border-line-soft px-4 py-2" role="group" aria-label="Filter by agent">
            {AGENT_ORDER.map((name) => {
              const agent = AGENTS[name];
              const on = !hidden.has(name);
              return (
                <button
                  key={name}
                  type="button"
                  aria-pressed={on}
                  data-testid="trace-filter"
                  data-agent={name}
                  onClick={() => toggleAgent(name)}
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] transition-colors ${on ? "" : "border-line text-faint line-through"}`}
                  style={on ? { borderColor: agent.hex, color: agent.hex } : undefined}
                >
                  <span aria-hidden className="size-1.5 rounded-full" style={{ background: on ? agent.hex : "var(--color-line)" }} />
                  {agent.label}
                  <span className="font-mono text-faint">{counts[name]}</span>
                </button>
              );
            })}
          </div>

          <div className="relative">
            <ol
              ref={list}
              onScroll={onScroll}
              onMouseEnter={pause}
              onMouseLeave={onScroll}
              aria-label="Events"
              className="pane-scroll max-h-[32rem] min-h-40 space-y-0.5 overflow-y-auto border-t border-line-soft px-2 py-2"
            >
              {shown.map((event) => {
                const key = `${event.run_id}-${event.seq}`;
                return <EventRow key={key} event={event} open={openKeys.has(key)} onToggle={() => toggle(key)} />;
              })}
              {shown.length === 0 && <li className="px-2 py-2 text-xs text-faint">Every agent is filtered out.</li>}
            </ol>
            <AnimatePresence>
              {!pinned && behind > 0 && (
                <motion.button
                  key="jump"
                  type="button"
                  data-testid="trace-jump"
                  onClick={jump}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  className="absolute bottom-2 right-3 inline-flex items-center gap-1.5 rounded-full border border-accent/50 bg-panel px-2.5 py-1 text-xs text-accent shadow"
                >
                  <ArrowDownToLine size={12} aria-hidden /> Jump to latest ({behind} new)
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </>
      )}
    </section>
  );
}
