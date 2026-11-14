"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ExternalLink } from "lucide-react";
import { useState } from "react";
import { formatQuantity } from "@/lib/describe";
import type { CheckResult, Citation, EvidenceReport, Quantity } from "@/lib/types";
import { StatusChip } from "./VerdictBadge";

// "Show the math": every check of the evidence report, with its inputs, formula,
// arithmetic and sources, so a person with a calculator can reproduce it. Nothing
// here is computed in the browser; each line is taken from the report.

const ORIGIN: Record<Quantity["origin"], string> = {
  claim: "stated in the listing",
  constant: "reference constant",
  derived: "calculated",
  assumption: "assumed",
};

function Inputs({ inputs }: { inputs: Quantity[] }) {
  if (!inputs.length) return null;
  return (
    <section>
      <h4 className="mb-1.5 text-xs font-medium text-muted">Inputs</h4>
      <table className="w-full text-sm">
        <tbody>
          {inputs.map((q, i) => (
            <tr key={`${q.name}-${i}`} className="border-t border-line-soft first:border-t-0">
              <td className="py-1.5 pr-3 text-muted">{q.name}</td>
              <td className="whitespace-nowrap py-1.5 pr-3 font-mono text-text">{formatQuantity(q)}</td>
              <td className="py-1.5 text-right text-xs text-faint">
                {ORIGIN[q.origin] ?? q.origin}
                {q.origin === "claim" && q.found_in ? `, ${q.found_in}` : ""}
                {q.origin === "claim" && typeof q.confidence === "number" ? `, confidence ${q.confidence}` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Source({ c }: { c: Citation }) {
  return (
    <li className="rounded-md border border-line-soft bg-ink/60 p-3 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="text-text">{c.description}</span>
        <span className="whitespace-nowrap font-mono text-text">{formatQuantity(c)}</span>
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
            className="inline-flex items-center gap-1 text-accent hover:underline"
          >
            Open source <ExternalLink size={12} aria-hidden />
          </a>
        )}
      </div>
    </li>
  );
}

function Notes({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <section>
      <h4 className="mb-1.5 text-xs font-medium text-muted">{title}</h4>
      <ul className="space-y-1 text-sm leading-6 text-muted">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function CheckBody({ check }: { check: CheckResult }) {
  return (
    <div className="space-y-5 border-t border-line-soft px-4 pb-5 pt-4">
      {check.status === "not_assessed" && (
        <p data-testid="not-assessed-reason" className="rounded-md border border-line bg-raised px-3 py-2 text-sm text-text">
          Not assessed: {check.not_assessed_reason ?? "the listing did not give what this check needs."}
        </p>
      )}

      <Inputs inputs={check.inputs} />

      {check.formula && (
        <section>
          <h4 className="mb-1.5 text-xs font-medium text-muted">Formula</h4>
          <p data-testid="check-formula" className="font-mono text-[15px] text-accent">
            {check.formula}
          </p>
        </section>
      )}

      {check.steps.length > 0 && (
        <section>
          <h4 className="mb-1.5 text-xs font-medium text-muted">Arithmetic, step by step</h4>
          <ol className="space-y-1.5">
            {check.steps.map((step, i) => (
              <motion.li
                key={`${step.label}-${i}`}
                data-testid="check-step"
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.12, duration: 0.2 }}
                className="grid grid-cols-[1.5rem_1fr] gap-x-2 rounded-md bg-ink/60 px-3 py-2"
              >
                <span className="font-mono text-xs leading-6 text-faint">{i + 1}</span>
                <span className="font-mono text-sm leading-6 text-text">{step.text}</span>
              </motion.li>
            ))}
          </ol>
        </section>
      )}

      {check.constants.length > 0 && (
        <section>
          <h4 className="mb-1.5 text-xs font-medium text-muted">Constants and their sources</h4>
          <ul className="space-y-2">
            {check.constants.map((c) => (
              <Source key={c.key} c={c} />
            ))}
          </ul>
        </section>
      )}

      <Notes title="Assumptions" items={check.assumptions} />
      <Notes title="Notes" items={check.notes} />
    </div>
  );
}

function CheckRow({ check, defaultOpen }: { check: CheckResult; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <li data-testid="check" data-check-id={check.check_id} className="rounded-lg border border-line bg-panel">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 px-4 py-3 text-left"
      >
        <ChevronDown
          size={16}
          aria-hidden
          className={`mt-1 shrink-0 text-faint transition-transform ${open ? "" : "-rotate-90"}`}
        />
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
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <CheckBody check={check} />
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  );
}

export function MathModule({ report }: { report: EvidenceReport }) {
  return (
    <section aria-labelledby="math-heading">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 id="math-heading" className="text-base font-semibold text-text">
          Show the math
        </h2>
        <p className="text-xs text-faint">Every number below comes from the evidence report.</p>
      </div>
      <ul className="space-y-2">
        {report.checks.map((check) => (
          // Checks that decided the verdict open first; the rest are one click away.
          <CheckRow
            key={check.check_id}
            check={check}
            defaultOpen={check.status === "violated" || check.status === "flag"}
          />
        ))}
      </ul>
      {report.assumptions.length > 0 && (
        <div className="mt-4 rounded-lg border border-line bg-panel px-4 py-3">
          <Notes title="Assumptions across all checks" items={report.assumptions} />
        </div>
      )}
    </section>
  );
}
