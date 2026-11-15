"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ChevronDown, ExternalLink } from "lucide-react";
import { useState } from "react";
import { STATUS_HEX } from "@/lib/agents";
import { formatQuantity } from "@/lib/describe";
import { IN_VIEW, RISE, SETTLE, UNFOLD, WEIGHT, stagger } from "@/lib/motion";
import type { CheckResult, CheckStatus, Citation, EvidenceReport, Quantity, Step } from "@/lib/types";
import { StatusChip } from "./VerdictBadge";

// "Show the math": every check of the evidence report, with its inputs, formula,
// arithmetic and sources, so a person with a calculator can reproduce it. Nothing
// here is computed in the browser; each line is taken from the report.

const ORIGIN: Record<Quantity["origin"], { text: string; dot: string }> = {
  claim: { text: "stated in the listing", dot: "bg-accent" },
  constant: { text: "reference constant", dot: "bg-quiet" },
  derived: { text: "calculated", dot: "bg-clear" },
  assumption: { text: "assumed", dot: "bg-flag" },
};

function Heading({ children }: { children: React.ReactNode }) {
  return <h4 className="mb-2 text-[11px] font-medium uppercase tracking-[0.08em] text-faint">{children}</h4>;
}

function Inputs({ inputs }: { inputs: Quantity[] }) {
  if (!inputs.length) return null;
  return (
    <section>
      <Heading>Inputs</Heading>
      <table className="w-full text-sm">
        <tbody>
          {inputs.map((q, i) => {
            const origin = ORIGIN[q.origin];
            return (
              <tr key={`${q.name}-${i}`} className="border-t border-line-soft transition-colors first:border-t-0 hover:bg-raised/40">
                <td className="py-2 pr-3 text-muted">{q.name}</td>
                <td className="whitespace-nowrap py-2 pr-3 font-mono tabular-nums text-text">{formatQuantity(q)}</td>
                <td className="py-2 text-right text-xs text-faint">
                  <span aria-hidden className={`mr-1.5 inline-block size-1.5 rounded-full align-middle ${origin?.dot ?? "bg-quiet"}`} />
                  {origin?.text ?? q.origin}
                  {q.origin === "claim" && q.found_in ? `, ${q.found_in}` : ""}
                  {q.origin === "claim" && typeof q.confidence === "number" ? `, confidence ${q.confidence}` : ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

function Source({ c }: { c: Citation }) {
  return (
    <motion.li variants={RISE} className="well p-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-text">{c.description}</span>
        <span className="whitespace-nowrap font-mono tabular-nums text-text">{formatQuantity(c)}</span>
      </div>
      <p className="mt-1.5 text-xs leading-5 text-muted">
        {c.source_title}
        {c.source_publisher ? `. ${c.source_publisher}` : ""}
        {c.locator ? `. ${c.locator}` : ""}
        {c.accessed ? `. Accessed ${c.accessed}` : ""}.
      </p>
      {c.quote && <p className="mt-1 border-l-2 border-line pl-2 text-xs leading-5 text-faint">“{c.quote}”</p>}
      {c.note && <p className="mt-1 text-xs leading-5 text-faint">{c.note}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
        <span className={c.hard_bound ? "text-impossible" : "text-flag"}>
          {c.hard_bound ? "Hard bound" : "Soft ceiling: exceeding it is a flag"}
        </span>
        {c.source_url && (
          <a
            href={c.source_url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1 text-accent underline-offset-2 hover:underline"
          >
            Open source <ExternalLink size={12} aria-hidden />
          </a>
        )}
      </div>
    </motion.li>
  );
}

function Notes({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <section>
      <Heading>{title}</Heading>
      <ul className="space-y-1 text-sm leading-6 text-muted">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

// ------------------------------------------------------------------ the arithmetic

/**
 * A step's display line, cut into its label, its working and its result so each can be
 * set in its own weight. The pieces are slices of `step.text`; put back together they
 * are that string, character for character.
 */
export function stepParts(step: Step): { label: string | null; working: string; result: string | null } {
  const lead = `${step.label}: `;
  const labelled = Boolean(step.label) && step.text.startsWith(lead);
  const rest = labelled ? step.text.slice(lead.length) : step.text;
  const cut = rest.lastIndexOf(" = ");
  return {
    label: labelled ? step.label : null,
    working: cut === -1 ? rest : rest.slice(0, cut),
    result: cut === -1 ? null : rest.slice(cut + 3),
  };
}

function StepLine({ step, index, last }: { step: Step; index: number; last: boolean }) {
  const { label, working, result } = stepParts(step);
  return (
    <motion.li variants={RISE} className="relative grid grid-cols-[1fr_auto] items-start gap-x-4 pb-4 last:pb-0">
      {/* The rail that joins one step to the next. */}
      {!last && (
        <motion.span
          aria-hidden
          variants={{ hidden: { scaleY: 0 }, show: { scaleY: 1, transition: { duration: 0.3, ease: "easeOut" } } }}
          className="absolute bottom-0 left-[0.8125rem] top-7 w-px origin-top bg-line"
        />
      )}
      <div data-testid="check-step" className="grid grid-cols-[1.75rem_1fr] items-start gap-x-3">
        <span className="relative grid size-[1.625rem] place-items-center rounded-full border border-line bg-ink font-mono text-[11px] text-muted shadow-[inset_0_1px_2px_rgb(0_0_0/0.5)]">
          {index + 1}
        </span>
        <span className="min-w-0">
          {label && (
            <>
              <span className="block text-xs leading-5 text-muted">{label}</span>
              <span className="sr-only">: </span>
            </>
          )}
          <span className="font-mono text-[15px] leading-7 tabular-nums text-text/80">
            {working}
            {result !== null && (
              <>
                <span className="text-faint">{" = "}</span>
                <span className="rounded bg-raised px-1.5 py-0.5 font-medium text-text shadow-[inset_0_1px_0_rgb(255_255_255/0.06)]">{result}</span>
              </>
            )}
          </span>
        </span>
      </div>
      {/* The same step in symbols, as a margin note. */}
      <span aria-hidden className="mt-5 hidden max-w-56 truncate text-right font-mono text-xs text-faint md:block">
        {step.formula}
      </span>
    </motion.li>
  );
}

const COMPARATOR = /^(.+?)\s([>≤<≥=])\s(.+)$/;

/** The comparison step of a check, if it has one: a ratio to a limit, as the report gives it. */
function comparisonOf(check: CheckResult): Step | null {
  const step = check.steps.findLast(
    (s) => typeof s.result === "number" && Number.isFinite(s.result) && s.result >= 0 && s.unit.trim().startsWith("×"),
  );
  return step ?? null;
}

/**
 * The comparison drawn as a bar against its limit. The bar's length is the ratio the
 * report gives (`step.result`); the two values shown are cut from the step's own text.
 * Only positions on screen are worked out here, never a number that is displayed.
 */
function Gauge({ step, status }: { step: Step; status: CheckStatus }) {
  const reduced = useReducedMotion();
  const ratio = step.result as number;
  const hex = STATUS_HEX[status] ?? STATUS_HEX.not_assessed;
  const span = Math.max(1.3, ratio * 1.12); // how many "limits" wide the track is
  const fill = Math.min(100, (ratio / span) * 100);
  const mark = Math.max(2, (1 / span) * 100);
  const over = ratio > 1;
  const sides = COMPARATOR.exec(step.substitution);
  const limitName = step.unit.replace(/^×\s*/, "");

  return (
    <motion.div
      variants={RISE}
      role="img"
      aria-label={step.text}
      data-testid="check-gauge"
      className="well mt-4 px-4 pb-4 pt-3"
    >
      {sides && (
        <div aria-hidden className="mb-3 flex items-end justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.08em] text-faint">From the listing</div>
            <div className="font-mono text-xl font-medium tabular-nums" style={{ color: hex }}>
              {sides[1]}
            </div>
          </div>
          <div className="pb-0.5 font-mono text-xl text-faint">{sides[2]}</div>
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-[0.08em] text-faint">{limitName}</div>
            <div className="font-mono text-xl font-medium tabular-nums text-text">{sides[3]}</div>
          </div>
        </div>
      )}
      <div aria-hidden className="relative h-3">
        <div className="absolute inset-0 overflow-hidden rounded-full bg-ink shadow-[inset_0_1px_3px_rgb(0_0_0/0.7)] ring-1 ring-line-soft">
          <motion.div
            className="absolute inset-0 rounded-full"
            style={{
              background: `linear-gradient(90deg, color-mix(in srgb, ${hex} 55%, transparent), ${hex})`,
              boxShadow: `0 0 14px ${hex}`,
            }}
            initial={reduced ? false : { clipPath: "inset(0% 100% 0% 0% round 999px)" }}
            whileInView={{ clipPath: `inset(0% ${100 - fill}% 0% 0% round 999px)` }}
            viewport={IN_VIEW}
            transition={{ ...WEIGHT, delay: 0.25 }}
          >
            {over && <span className="hatch absolute inset-y-0 right-0" style={{ left: `${mark}%` }} />}
          </motion.div>
        </div>
        {/* The limit. */}
        <span className="absolute -bottom-1.5 -top-1.5 w-0.5 -translate-x-1/2 rounded-full bg-text shadow-[0_0_0_2px_var(--color-ink)]" style={{ left: `${mark}%` }} />
      </div>
    </motion.div>
  );
}

function Arithmetic({ check }: { check: CheckResult }) {
  const comparison = comparisonOf(check);
  return (
    <section>
      <Heading>Arithmetic, step by step</Heading>
      <motion.div variants={stagger(0.09)} initial="hidden" whileInView="show" viewport={IN_VIEW}>
        <ol>
          {check.steps.map((step, i) => (
            <StepLine key={`${step.label}-${i}`} step={step} index={i} last={i === check.steps.length - 1} />
          ))}
        </ol>
        {comparison && <Gauge step={comparison} status={check.status} />}
      </motion.div>
    </section>
  );
}

function CheckBody({ check }: { check: CheckResult }) {
  return (
    <div className="space-y-6 border-t border-line-soft px-4 pb-5 pt-4 sm:px-5">
      {check.status === "not_assessed" && (
        <p data-testid="not-assessed-reason" className="rounded-md border border-line bg-raised px-3 py-2 text-sm text-text">
          Not assessed: {check.not_assessed_reason ?? "the listing did not give what this check needs."}
        </p>
      )}

      <Inputs inputs={check.inputs} />

      {check.formula && (
        <section>
          <Heading>Formula</Heading>
          <p data-testid="check-formula" className="well overflow-x-auto px-4 py-3 text-center font-mono text-base text-accent">
            {check.formula}
          </p>
        </section>
      )}

      {check.steps.length > 0 && <Arithmetic check={check} />}

      {check.constants.length > 0 && (
        <section>
          <Heading>Constants and their sources</Heading>
          <motion.ul variants={stagger(0.05)} initial="hidden" whileInView="show" viewport={IN_VIEW} className="space-y-2">
            {check.constants.map((c) => (
              <Source key={c.key} c={c} />
            ))}
          </motion.ul>
        </section>
      )}

      <Notes title="Assumptions" items={check.assumptions} />
      <Notes title="Notes" items={check.notes} />
    </div>
  );
}

function CheckRow({ check, defaultOpen }: { check: CheckResult; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const hex = STATUS_HEX[check.status] ?? STATUS_HEX.not_assessed;
  const decided = check.status === "violated" || check.status === "flag";
  return (
    <motion.li variants={RISE} data-testid="check" data-check-id={check.check_id} className="surface relative overflow-hidden">
      {/* The check's status, as a strip down its left edge. */}
      <span aria-hidden className="absolute inset-y-0 left-0 w-[3px]" style={{ background: hex, opacity: decided ? 1 : 0.45 }} />
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition-colors hover:bg-raised/40 sm:px-5"
      >
        <motion.span aria-hidden animate={{ rotate: open ? 0 : -90 }} transition={SETTLE} className="mt-1 shrink-0 text-faint">
          <ChevronDown size={16} />
        </motion.span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-text">{check.title}</span>
          <span className="mt-0.5 block text-sm leading-6 text-muted">{check.summary}</span>
        </span>
        <StatusChip status={check.status} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={UNFOLD}
            className="overflow-hidden"
          >
            <CheckBody check={check} />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

export function MathModule({ report }: { report: EvidenceReport }) {
  return (
    <section aria-labelledby="math-heading" className="scroll-mt-4">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 id="math-heading" className="text-base font-semibold text-text">
          Show the math
        </h2>
        <p className="text-xs text-faint">Every number below comes from the evidence report.</p>
      </div>
      <motion.ul variants={stagger(0.05)} initial="hidden" whileInView="show" viewport={{ once: true }} className="space-y-2.5">
        {report.checks.map((check) => (
          // Checks that decided the verdict open first; the rest are one click away.
          <CheckRow
            key={check.check_id}
            check={check}
            defaultOpen={check.status === "violated" || check.status === "flag"}
          />
        ))}
      </motion.ul>
      {report.assumptions.length > 0 && (
        <div className="surface mt-4 px-4 py-3 sm:px-5">
          <Notes title="Assumptions across all checks" items={report.assumptions} />
        </div>
      )}
    </section>
  );
}
