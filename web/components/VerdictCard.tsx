"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ROUTING_TONE, STATUS_LABEL, STATUS_TONE, VERDICT_TONE, num } from "@/lib/format";
import { downloadJson } from "@/lib/run";
import type { RunState } from "@/lib/run";
import { CHECK_IDS } from "@/lib/types";
import type { CheckResult, Citation, Claims, Quantity, Routing, Step } from "@/lib/types";

const MIN_CONFIDENCE = 0.8; // "High confidence means 0.8 or more" (CONTRACT.md)
const STEP_STAGGER = 0.08; // seconds between arithmetic lines; five steps are all visible in under half a second

function Confidence({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return null;
  const low = value < MIN_CONFIDENCE;
  return (
    <span className={`tnum ${low ? "font-medium text-amber-700" : "text-slate-500"}`}>
      {Math.round(value * 100)}%{low ? " (low)" : ""}
    </span>
  );
}

export function RoutingLabel({ routing, reason, compact = false }: { routing: Routing; reason?: string; compact?: boolean }) {
  const tone = ROUTING_TONE[routing];
  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${tone.box}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${tone.dot}`} />
        {routing}
      </span>
    );
  }
  return (
    <div className={`rounded-lg border-2 px-4 py-3 ${tone.box}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wider opacity-70">Routing</div>
      <div className="mt-0.5 flex items-center gap-2 text-xl font-semibold" data-testid="routing">
        <span className={`h-2.5 w-2.5 rounded-full ${tone.dot}`} />
        {routing}
      </div>
      {reason && <p className="mt-1 text-sm opacity-90">{reason}</p>}
    </div>
  );
}

function StepLine({ step, index, last, status }: { step: Step; index: number; last: boolean; status: CheckResult["status"] }) {
  const body = step.text.startsWith(`${step.label}: `) ? step.text.slice(step.label.length + 2) : step.text;
  const emphasis = last ? (status === "violated" ? "text-red-700" : status === "flag" ? "text-amber-800" : "text-slate-900") : "text-slate-900";
  return (
    <motion.li
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * STEP_STAGGER, duration: 0.18 }}
      className="grid grid-cols-[1.5rem_1fr] gap-x-2 py-1.5"
      data-testid="step"
    >
      <span className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-slate-900 text-[11px] font-semibold text-white tnum">{index + 1}</span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="text-xs text-slate-500">{step.label}</span>
          <code className="font-mono text-[11px] text-slate-400">{step.formula}</code>
        </div>
        <div className={`font-mono text-[15px] tnum ${emphasis} ${last ? "font-semibold" : ""}`}>{body}</div>
      </div>
    </motion.li>
  );
}

function ConstantRow({ c }: { c: Citation }) {
  return (
    <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="font-mono text-sm font-semibold text-slate-900 tnum">
          {num(c.value)} {c.unit}
        </span>
        <span className="text-sm text-slate-700">{c.description}</span>
        <span className={`ml-auto rounded px-1.5 py-0.5 text-[11px] font-medium ${c.hard_bound ? "bg-slate-200 text-slate-700" : "bg-amber-100 text-amber-800"}`}>
          {c.hard_bound ? "hard bound" : "soft ceiling"}
        </span>
      </div>
      <div className="mt-1 text-xs text-slate-600">
        Source:{" "}
        <a href={c.source_url} target="_blank" rel="noreferrer" className="font-medium text-slate-900 underline underline-offset-2">
          {c.source_title}
        </a>
        {c.source_publisher && <> · {c.source_publisher}</>}
        {c.locator && <> · {c.locator}</>}
      </div>
      {c.quote && <blockquote className="mt-1 border-l-2 border-slate-300 pl-2 text-xs italic text-slate-600">“{c.quote}”</blockquote>}
      {(c.note || c.accessed) && (
        <div className="mt-1 text-[11px] text-slate-500">
          {c.note}
          {c.note && c.accessed ? " " : ""}
          {c.accessed && <>Accessed {c.accessed}.</>}
        </div>
      )}
    </li>
  );
}

function InputChip({ q }: { q: Quantity }) {
  return (
    <li className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs">
      <span className="text-slate-500">{q.name}: </span>
      <span className="font-mono font-medium text-slate-900 tnum">
        {num(q.value)}
        {q.unit ? ` ${q.unit}` : ""}
      </span>
      <span className="text-slate-400">
        {" "}
        · {q.origin}
        {q.found_in ? `, ${q.found_in}` : ""}
        {q.confidence !== null && q.confidence !== undefined && (
          <>
            , <Confidence value={q.confidence} />
          </>
        )}
      </span>
    </li>
  );
}

function Notes({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-2 text-xs text-slate-600">
      <span className="font-semibold text-slate-700">{title}: </span>
      {items.length === 1 ? items[0] : <ul className="mt-0.5 list-disc pl-4">{items.map((n) => <li key={n}>{n}</li>)}</ul>}
    </div>
  );
}

function CheckBlock({ check }: { check: CheckResult }) {
  return (
    <motion.section
      layout="position"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="rounded-xl border border-slate-200 bg-white p-4"
      data-testid={`check-${check.check_id}`}
      data-status={check.status}
    >
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-semibold text-slate-900">{check.title}</h4>
        <span className={`rounded px-1.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${STATUS_TONE[check.status]}`}>{STATUS_LABEL[check.status]}</span>
      </div>
      <p className="mt-1 text-sm text-slate-700">{check.summary}</p>

      {check.steps.length > 0 && (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
          {check.formula && (
            <div className="mb-1 flex items-baseline gap-2 border-b border-slate-200 pb-1.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Formula</span>
              <code className="font-mono text-[13px] text-slate-800">{check.formula}</code>
            </div>
          )}
          <ol>
            {check.steps.map((step, i) => (
              <StepLine key={i} step={step} index={i} last={i === check.steps.length - 1} status={check.status} />
            ))}
          </ol>
        </div>
      )}

      {check.inputs.length > 0 && (
        <div className="mt-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Inputs</div>
          <ul className="mt-1 flex flex-wrap gap-1.5">{check.inputs.map((q, i) => <InputChip key={i} q={q} />)}</ul>
        </div>
      )}

      {check.constants.length > 0 && (
        <div className="mt-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Constants and sources</div>
          <ul className="mt-1 space-y-1.5" data-testid="constants">{check.constants.map((c) => <ConstantRow key={c.key} c={c} />)}</ul>
        </div>
      )}
      <Notes title="Assumptions" items={check.assumptions} />
      <Notes title="Notes" items={check.notes} />
    </motion.section>
  );
}

function NotAssessed({ checks }: { checks: CheckResult[] }) {
  if (checks.length === 0) return null;
  return (
    <section className="rounded-xl border border-dashed border-slate-300 bg-slate-50/60 p-4" data-testid="not-assessed">
      <h4 className="text-sm font-semibold text-slate-700">
        Not assessed <span className="font-normal text-slate-500">· {checks.length} of {CHECK_IDS.length} checks had nothing to test. This is not a failure.</span>
      </h4>
      <ul className="mt-2 space-y-2">
        <AnimatePresence initial={false}>
          {checks.map((c) => (
            <motion.li key={c.check_id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }} className="text-sm" data-testid={`check-${c.check_id}`} data-status={c.status}>
              <div className="flex gap-2">
                <span className="mt-[3px] h-4 w-4 shrink-0 rounded-full border border-slate-300 text-center text-[10px] leading-[14px] text-slate-400" aria-hidden>
                  –
                </span>
                <div>
                  <span className="font-medium text-slate-700">{c.title}</span>
                  <span className="text-slate-600"> · {c.not_assessed_reason ?? c.summary}</span>
                  {c.notes.length > 0 && (
                    <ul className="mt-0.5 list-disc pl-4 text-xs text-slate-500">{c.notes.map((n) => <li key={n}>{n}</li>)}</ul>
                  )}
                </div>
              </div>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
    </section>
  );
}

function claimRows(claims: Claims): { label: string; value: string; found_in: string; quote: string | null; confidence: number }[] {
  const rows: ReturnType<typeof claimRows> = [];
  const add = (label: string, value: string, c: { found_in: string; quote: string | null; confidence: number }) =>
    rows.push({ label, value, found_in: c.found_in, quote: c.quote, confidence: c.confidence });
  if (claims.chemistry) add("Chemistry", claims.chemistry.value, claims.chemistry);
  claims.form_factors.forEach((c) => add("Size code", c.value, c));
  if (claims.cell_count) add("Cell count", num(claims.cell_count.value), claims.cell_count);
  if (claims.nominal_voltage_v) add("Nominal voltage", `${num(claims.nominal_voltage_v.value)} V`, claims.nominal_voltage_v);
  if (claims.capacity_mah) add("Capacity", `${num(claims.capacity_mah.value)} mAh`, claims.capacity_mah);
  if (claims.energy_wh) add("Energy", `${num(claims.energy_wh.value)} Wh`, claims.energy_wh);
  if (claims.output_capacity_mah) add("Output capacity", `${num(claims.output_capacity_mah.value)} mAh`, claims.output_capacity_mah);
  if (claims.weight) add(`Weight (${claims.weight.kind})`, `${num(claims.weight.value_g)} g`, claims.weight);
  if (claims.dimensions) {
    const d = claims.dimensions;
    add(`Dimensions (${d.kind})`, `${num(d.length_mm)} × ${num(d.width_mm)} × ${num(d.height_mm)} mm`, d);
  }
  if (claims.shelf_life_years) add("Shelf life", `${num(claims.shelf_life_years.value)} years`, claims.shelf_life_years);
  claims.printed_codes.forEach((c) => add("Printed code", c.value, c));
  claims.printed_terms.forEach((c) => add("Printed wording", c.value, c));
  return rows;
}

function ClaimsTable({ claims }: { claims: Claims }) {
  const rows = claimRows(claims);
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="claims">
      <h4 className="text-sm font-semibold text-slate-900">Claims extracted from the listing</h4>
      {rows.length === 0 ? (
        <p className="mt-1 text-sm text-slate-600">No claims were extracted.</p>
      ) : (
        <table className="mt-2 w-full text-left text-sm">
          <thead className="text-[11px] uppercase tracking-wider text-slate-500">
            <tr>
              <th className="py-1 pr-3 font-semibold">Claim</th>
              <th className="py-1 pr-3 font-semibold">Value</th>
              <th className="py-1 pr-3 font-semibold">Found in</th>
              <th className="py-1 font-semibold">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="py-1 pr-3 text-slate-600">{r.label}</td>
                <td className="py-1 pr-3 font-mono text-slate-900 tnum">
                  {r.value}
                  {r.quote && <span className="ml-2 font-sans text-xs text-slate-400">“{r.quote}”</span>}
                </td>
                <td className="py-1 pr-3 text-slate-600">{r.found_in}</td>
                <td className="py-1"><Confidence value={r.confidence} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export function VerdictCard({ run }: { run: RunState }) {
  const { report } = run;
  const seen = CHECK_IDS.map((id) => run.checks[id]).filter((c): c is CheckResult => !!c);
  const assessed = seen.filter((c) => c.status !== "not_assessed");
  const skipped = seen.filter((c) => c.status === "not_assessed");

  if (run.status === "idle") {
    return (
      <div className="flex min-h-64 items-center justify-center rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
        The evidence report appears here: verdict, routing, and the arithmetic behind each check.
      </div>
    );
  }

  return (
    <article className="space-y-3" data-testid="verdict-card" data-state={run.status}>
      <header className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Evidence report</div>
            <div className="truncate text-sm text-slate-700" title={run.name}>{run.name}</div>
          </div>
          {report && (
            <button
              type="button"
              onClick={() => downloadJson(report, run.name)}
              data-testid="download-json"
              className="shrink-0 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-900 hover:bg-slate-50"
            >
              Download JSON
            </button>
          )}
        </div>

        {run.status === "error" && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert" data-testid="run-error">
            <div className="font-semibold">The check did not finish</div>
            {run.error}
          </div>
        )}

        {run.status === "running" && (
          <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
            <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
            Checking: {seen.length} of {CHECK_IDS.length} checks back
          </div>
        )}

        {report && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.18 }}>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Verdict</div>
              <div className={`mt-1 inline-block rounded-lg px-3 py-1 text-2xl font-semibold ${VERDICT_TONE[report.verdict]}`} data-testid="verdict">
                {report.verdict}
              </div>
              <p className="mt-2 text-sm text-slate-700">{report.verdict_reason}</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.18 }}>
              <RoutingLabel routing={report.routing} reason={report.routing_reason} />
            </motion.div>
          </div>
        )}
      </header>

      {assessed.map((c) => <CheckBlock key={c.check_id} check={c} />)}
      <NotAssessed checks={skipped} />

      {report && (
        <>
          {report.assumptions.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-4" data-testid="assumptions">
              <h4 className="text-sm font-semibold text-slate-900">Assumptions</h4>
              <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">{report.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            </section>
          )}
          <ClaimsTable claims={report.claims} />
        </>
      )}
    </article>
  );
}
