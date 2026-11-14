import { ArrowLeft, BookOpen } from "lucide-react";
import Link from "next/link";
import styles from "@/app/report/[id]/print.module.css";
import { STATUS_HEX, VERDICT_HEX } from "@/lib/agents";
import { describeProduct, formatNumber, formatQuantity } from "@/lib/describe";
import type { BatchItem, CheckResult, CheckStatus, Citation, Claims, Quantity } from "@/lib/types";
import { PrintButton } from "./PrintButton";

// The evidence report laid out for paper: claims, each check with its inputs, formula,
// arithmetic and cited constants, the verdict, the routing and what was not assessed.
// Every value is taken from the report as it is; nothing is computed or rounded here.
// No animation: this page is meant to be read and printed.

const STATUS_LABEL: Record<CheckStatus, string> = {
  pass: "Pass",
  flag: "Flag",
  violated: "Bound exceeded",
  not_assessed: "Not assessed",
};

const ORIGIN: Record<Quantity["origin"], string> = {
  claim: "stated in the listing",
  constant: "reference constant",
  derived: "calculated",
  assumption: "assumed",
};

const PRODUCT: Record<Claims["product_type"], string> = {
  loose_cell: "Loose cell",
  battery_pack: "Battery pack",
  power_bank: "Power bank",
  unknown: "Not stated",
};

interface ClaimRow {
  field: string;
  value: string;
  found_in: string;
  confidence: number;
}

/** The claims as table rows, one per stated value. Absent fields are left out. */
export function claimRows(claims: Claims): ClaimRow[] {
  const rows: ClaimRow[] = [];
  const num = (field: string, c: Claims["capacity_mah"], unit: string) => {
    if (c) rows.push({ field, value: `${formatNumber(c.value)} ${unit}`.trim(), found_in: c.found_in, confidence: c.confidence });
  };
  if (claims.chemistry) rows.push({ field: "Chemistry", value: claims.chemistry.value, found_in: claims.chemistry.found_in, confidence: claims.chemistry.confidence });
  for (const f of claims.form_factors) rows.push({ field: "Size code", value: f.value, found_in: f.found_in, confidence: f.confidence });
  num("Cell count", claims.cell_count, "");
  num("Nominal voltage", claims.nominal_voltage_v, "V");
  num("Capacity", claims.capacity_mah, "mAh");
  num("Energy", claims.energy_wh, "Wh");
  num("Output capacity", claims.output_capacity_mah, "mAh");
  if (claims.weight) rows.push({ field: `Weight (${claims.weight.kind})`, value: `${formatNumber(claims.weight.value_g)} g`, found_in: claims.weight.found_in, confidence: claims.weight.confidence });
  if (claims.dimensions) {
    const d = claims.dimensions;
    rows.push({ field: `Dimensions (${d.kind})`, value: `${formatNumber(d.length_mm)} × ${formatNumber(d.width_mm)} × ${formatNumber(d.height_mm)} mm`, found_in: d.found_in, confidence: d.confidence });
  }
  num("Shelf life", claims.shelf_life_years, "years");
  for (const c of claims.printed_codes) rows.push({ field: "Printed code", value: c.value, found_in: c.found_in, confidence: c.confidence });
  for (const t of claims.printed_terms) rows.push({ field: "Printed wording", value: t.value, found_in: t.found_in, confidence: t.confidence });
  return rows;
}

function Source({ c }: { c: Citation }) {
  return (
    <li className="rounded border border-slate-200 bg-slate-50 p-2.5 text-xs leading-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3">
        <span className="font-medium text-slate-900">{c.description}</span>
        <span className="font-mono text-slate-900">{formatQuantity(c)}</span>
      </div>
      <p className="mt-1 text-slate-700">
        {c.source_title}
        {c.source_publisher ? `. ${c.source_publisher}` : ""}
        {c.locator ? `. ${c.locator}` : ""}
        {c.accessed ? `. Accessed ${c.accessed}` : ""}.
      </p>
      {c.quote && <p className="mt-1 border-l-2 border-slate-300 pl-2 italic text-slate-600">“{c.quote}”</p>}
      {c.note && <p className="mt-1 text-slate-600">{c.note}</p>}
      <p className="mt-1 text-slate-600">
        {c.hard_bound ? "Hard bound: exceeding it is a hard result." : "Soft ceiling: exceeding it is a flag."}
        {c.source_url && (
          <>
            {" "}
            <a href={c.source_url} className="text-slate-900 underline" target="_blank" rel="noreferrer noopener">
              Source
            </a>
          </>
        )}
      </p>
    </li>
  );
}

function Check({ check, index }: { check: CheckResult; index: number }) {
  const hex = STATUS_HEX[check.status];
  return (
    <li data-testid="print-check" data-check-id={check.check_id} className={`${styles.check} rounded-lg border border-slate-200 p-4`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-base font-semibold text-slate-900">
          <span className="mr-2 font-mono text-sm text-slate-500">{index + 1}</span>
          {check.title}
        </h3>
        <span data-testid="print-status" className="rounded border px-2 py-0.5 text-xs font-semibold" style={{ borderColor: hex, color: hex }}>
          {STATUS_LABEL[check.status]}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-800">{check.summary}</p>
      {check.status === "not_assessed" && check.not_assessed_reason && (
        <p className="mt-2 text-sm text-slate-700">Not assessed: {check.not_assessed_reason}</p>
      )}

      {check.inputs.length > 0 && (
        <div className={`${styles.block} mt-3`}>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Inputs</h4>
          <table className="mt-1 w-full text-sm">
            <tbody>
              {check.inputs.map((q, i) => (
                <tr key={`${q.name}-${i}`} className="border-t border-slate-200">
                  <td className="py-1 pr-3 text-slate-700">{q.name}</td>
                  <td className="whitespace-nowrap py-1 pr-3 font-mono text-slate-900">{formatQuantity(q)}</td>
                  <td className="py-1 text-right text-xs text-slate-500">
                    {ORIGIN[q.origin] ?? q.origin}
                    {q.origin === "claim" && q.found_in ? `, ${q.found_in}` : ""}
                    {q.origin === "claim" && typeof q.confidence === "number" ? `, confidence ${q.confidence}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {check.formula && (
        <p className="mt-3 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Formula </span>
          <span data-testid="print-formula" className="ml-1 font-mono text-slate-900">
            {check.formula}
          </span>
        </p>
      )}

      {check.steps.length > 0 && (
        <div className={`${styles.block} mt-3`}>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Arithmetic</h4>
          <ol className="mt-1 space-y-1">
            {check.steps.map((step, i) => (
              <li key={`${step.label}-${i}`} data-testid="print-step" className="grid grid-cols-[1.25rem_1fr] gap-x-2 font-mono text-sm leading-6 text-slate-900">
                <span className="text-slate-500">{i + 1}</span>
                <span className={styles.pre}>{step.text}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {check.constants.length > 0 && (
        <div className={`${styles.block} mt-3`}>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Constants and sources</h4>
          <ul className="mt-1 space-y-1.5">
            {check.constants.map((c) => (
              <Source key={c.key} c={c} />
            ))}
          </ul>
        </div>
      )}

      {check.assumptions.length > 0 && (
        <div className="mt-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Assumptions</h4>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm leading-6 text-slate-700">
            {check.assumptions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      )}
      {check.notes.length > 0 && (
        <div className="mt-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Notes</h4>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm leading-6 text-slate-700">
            {check.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

export function PrintReport({ sample }: { sample: BatchItem }) {
  const report = sample.report;
  if (!report) {
    return (
      <div className={styles.sheet}>
        <div className={styles.page}>
          <h1 className="text-xl font-semibold">No report for {sample.id}</h1>
          <p className="mt-2 text-sm text-slate-700">{sample.error ?? "This listing has no evidence report."}</p>
        </div>
      </div>
    );
  }
  const verdictHex = VERDICT_HEX[report.verdict];
  const rows = claimRows(report.claims);

  return (
    <div className={styles.sheet}>
      <div className={styles.page}>
        <nav aria-label="Pages" className={`${styles.noPrint} mb-6 flex flex-wrap items-center justify-between gap-3`}>
          <div className="flex items-center gap-3 text-sm">
            <Link href="/" className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-slate-900 hover:bg-slate-100">
              <ArrowLeft size={14} aria-hidden /> Console
            </Link>
            <Link href="/how-it-works" className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-slate-900 hover:bg-slate-100">
              <BookOpen size={14} aria-hidden /> How it works
            </Link>
          </div>
          <PrintButton />
        </nav>

        <header className="border-b border-slate-300 pb-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Evidence report · {sample.id}</p>
          <h1 className="mt-1 text-2xl font-semibold text-slate-900">{describeProduct(report.claims)}</h1>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className={`${styles.block} rounded-lg border p-3`} style={{ borderColor: verdictHex }}>
              <p className="text-xs uppercase tracking-wide text-slate-500">Verdict</p>
              <p data-testid="print-verdict" className="mt-0.5 text-xl font-semibold" style={{ color: verdictHex }}>
                {report.verdict}
              </p>
              <p className="mt-1.5 text-sm leading-6 text-slate-800">{report.verdict_reason}</p>
            </div>
            <div className={`${styles.block} rounded-lg border border-slate-300 p-3`}>
              <p className="text-xs uppercase tracking-wide text-slate-500">Routing</p>
              <p data-testid="print-routing" className="mt-0.5 text-xl font-semibold text-slate-900">
                {report.routing}
              </p>
              <p className="mt-1.5 text-sm leading-6 text-slate-800">{report.routing_reason}</p>
            </div>
          </div>
        </header>

        <section aria-labelledby="claims-heading" className={`${styles.section} mt-6`}>
          <h2 id="claims-heading" className="text-lg font-semibold text-slate-900">
            Claims extracted from the listing
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Product type: {PRODUCT[report.claims.product_type]}. Each claim records where it was found and the extraction confidence.
          </p>
          {rows.length ? (
            <table className="mt-3 w-full text-sm">
              <thead>
                <tr className="border-b border-slate-300 text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-1.5 pr-3 font-semibold">Claim</th>
                  <th className="py-1.5 pr-3 font-semibold">Value</th>
                  <th className="py-1.5 pr-3 font-semibold">Found in</th>
                  <th className="py-1.5 text-right font-semibold">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={`${row.field}-${i}`} data-testid="print-claim" className="border-b border-slate-200">
                    <td className="py-1.5 pr-3 text-slate-800">{row.field}</td>
                    <td className="py-1.5 pr-3 font-mono text-slate-900">{row.value}</td>
                    <td className="py-1.5 pr-3 text-slate-700">{row.found_in}</td>
                    <td className="py-1.5 text-right font-mono text-slate-700">{row.confidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="mt-3 text-sm text-slate-700">No claims were extracted.</p>
          )}
        </section>

        <section aria-labelledby="checks-heading" className={`${styles.section} mt-8`}>
          <h2 id="checks-heading" className="text-lg font-semibold text-slate-900">
            Checks
          </h2>
          <p className="mt-1 text-sm text-slate-600">Six checks, always in this order. Each shows the inputs it used, its formula, the arithmetic and the constants with their sources.</p>
          <ol className={`${styles.checks} mt-3 space-y-3`}>
            {report.checks.map((check, i) => (
              <Check key={check.check_id} check={check} index={i} />
            ))}
          </ol>
        </section>

        {(report.assumptions.length > 0 || report.not_assessed.length > 0) && (
          <section aria-labelledby="notes-heading" className={`${styles.section} ${styles.block} mt-8 grid gap-6 sm:grid-cols-2`}>
            <h2 id="notes-heading" className="sr-only">
              Assumptions and what was not assessed
            </h2>
            {report.assumptions.length > 0 && (
              <div>
                <h3 className="text-base font-semibold text-slate-900">Assumptions</h3>
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
                  {report.assumptions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              </div>
            )}
            {report.not_assessed.length > 0 && (
              <div>
                <h3 className="text-base font-semibold text-slate-900">Not assessed</h3>
                <ul data-testid="print-not-assessed" className="mt-1.5 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-700">
                  {report.not_assessed.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        <footer className="mt-10 border-t border-slate-300 pt-3 text-xs leading-5 text-slate-500">
          Every number on this page is taken from the evidence report as the checks produced it; nothing was calculated or rounded for display.
          The verdict is about the claim, not about whoever listed the product. Schema version {report.schema_version}.
        </footer>
      </div>
    </div>
  );
}
