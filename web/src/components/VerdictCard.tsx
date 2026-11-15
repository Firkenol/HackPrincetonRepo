"use client";

import { motion } from "framer-motion";
import { ArrowDown, Download } from "lucide-react";
import { useEffect, useRef } from "react";
import { VERDICT_HEX } from "@/lib/agents";
import { describeReport } from "@/lib/describe";
import { RISE, SETTLE, SNAP, stagger } from "@/lib/motion";
import { markScrollEdges, scrollToElement } from "@/lib/scroll";
import type { EvidenceReport, Listing } from "@/lib/types";
import { RoutingLabel, VerdictBadge } from "./VerdictBadge";

export function downloadReport(report: EvidenceReport, name: string) {
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${name}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function ListingPane({ listing }: { listing: Listing }) {
  const pane = useRef<HTMLDivElement>(null);
  useEffect(() => markScrollEdges(pane.current), [listing.key, listing.text, listing.imageUrl]);
  return (
    <div className="flex min-h-64 flex-col border-b border-line lg:border-b-0 lg:border-r">
      <h3 className="border-b border-line-soft px-4 py-2.5 text-[11px] font-medium uppercase tracking-[0.08em] text-faint">
        The listing as submitted
      </h3>
      <div className="relative flex-1 overflow-hidden">
        <div
          ref={pane}
          onScroll={(e) => markScrollEdges(e.currentTarget)}
          className="pane-scroll scroll-fade h-full max-h-[26rem] overflow-auto p-4"
        >
          {listing.imageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element -- a local object URL or an API file, not an optimisable asset
            <img
              src={listing.imageUrl}
              alt="Listing screenshot"
              onLoad={() => markScrollEdges(pane.current)}
              className="max-w-full rounded-md border border-line shadow-lg shadow-black/40"
            />
          ) : listing.text ? (
            <pre data-testid="listing-text" className="whitespace-pre-wrap font-mono text-[13px] leading-6 text-text/90">
              {listing.text}
            </pre>
          ) : (
            <p className="text-sm text-muted">The listing itself is not available for this sample.</p>
          )}
        </div>
        {/* While the listing is being read, a light sweeps down it. */}
        {listing.running && <span aria-hidden className="scan-beam" />}
      </div>
    </div>
  );
}

/** The shape of the verdict to come, while the checks run. */
function Pending() {
  return (
    <div role="status" className="flex flex-col gap-4">
      <p className="inline-flex items-center gap-2.5 text-sm text-accent">
        <span aria-hidden className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-accent opacity-60" />
          <span className="relative inline-flex size-2 rounded-full bg-accent" />
        </span>
        Checking the listing. The trace shows each step.
      </p>
      <div aria-hidden className="space-y-3">
        <span className="shimmer block h-10 w-44 rounded-md" />
        <span className="shimmer block h-3 w-full rounded" />
        <span className="shimmer block h-3 w-4/5 rounded" />
        <span className="shimmer mt-5 block h-6 w-36 rounded" />
        <span className="shimmer block h-3 w-3/5 rounded" />
      </div>
    </div>
  );
}

export function VerdictCard({ listing }: { listing: Listing }) {
  const { report } = listing;
  const hex = report ? VERDICT_HEX[report.verdict] ?? VERDICT_HEX["No checkable claim"] : null;
  const state = report ? "report" : listing.running ? "running" : "idle";
  return (
    <article data-testid="verdict-card" className="surface relative overflow-hidden">
      {/* A line in the verdict's colour is drawn across the top of the card when the verdict lands. */}
      {hex && (
        <motion.span
          key={`${listing.key}-line`}
          aria-hidden
          className="absolute inset-x-0 top-0 z-10 h-0.5 origin-left"
          style={{ background: `linear-gradient(90deg, ${hex}, color-mix(in srgb, ${hex} 20%, transparent))` }}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      )}
      <div className="grid lg:grid-cols-2">
        <ListingPane listing={listing} />

        <div className="relative">
          {/* A soft light in the verdict's colour behind the badge. */}
          {hex && (
            <motion.span
              key={`${listing.key}-glow`}
              aria-hidden
              className="pointer-events-none absolute -left-10 -top-16 size-72 rounded-full blur-3xl"
              style={{ background: hex }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.1 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            />
          )}
          <motion.div
            key={`${listing.key}-${state}`}
            variants={stagger(0.06, 0.04)}
            initial="hidden"
            animate="show"
            className="relative flex h-full flex-col gap-4 p-5 sm:p-6"
          >
            {report ? (
              <>
                <motion.p variants={RISE} className="text-sm text-muted">
                  {describeReport(report)}
                </motion.p>
                {/* The badge lands with a little weight: slightly large, then settles. */}
                <motion.div
                  variants={{
                    hidden: { opacity: 0, scale: 1.12, filter: "blur(6px)" },
                    show: { opacity: 1, scale: 1, filter: "blur(0px)", transition: SNAP },
                  }}
                  className="origin-left"
                >
                  <VerdictBadge verdict={report.verdict} size="lg" />
                </motion.div>
                <motion.p variants={RISE} className="max-w-prose text-sm leading-6 text-text">
                  {report.verdict_reason}
                </motion.p>

                <motion.div variants={RISE} className="border-t border-line-soft pt-4">
                  <RoutingLabel routing={report.routing} withNote />
                  <p className="mt-2 max-w-prose text-sm leading-6 text-muted">{report.routing_reason}</p>
                </motion.div>

                {report.not_assessed.length > 0 && (
                  <motion.div variants={RISE} className="border-t border-line-soft pt-4">
                    <h3 className="text-[11px] font-medium uppercase tracking-[0.08em] text-faint">Not assessed</h3>
                    <ul className="mt-1.5 space-y-1 text-sm leading-6 text-muted">
                      {report.not_assessed.map((line) => (
                        <li key={line}>{line}</li>
                      ))}
                    </ul>
                  </motion.div>
                )}

                <motion.div variants={RISE} className="mt-auto flex flex-wrap items-center gap-3 pt-2">
                  <button type="button" onClick={() => scrollToElement(document.getElementById("math-heading"))} className="btn btn-quiet group">
                    <ArrowDown size={15} aria-hidden className="transition-transform group-hover:translate-y-0.5" /> See the math
                  </button>
                  <button type="button" onClick={() => downloadReport(report, `offspec-report-${listing.key}`)} className="btn btn-quiet">
                    <Download size={15} aria-hidden /> Download report JSON
                  </button>
                  {listing.sample && (
                    <span data-testid="card-sample-label" className="rounded border border-flag/40 px-1.5 py-0.5 text-xs text-flag">
                      Sample data
                    </span>
                  )}
                </motion.div>
              </>
            ) : listing.running ? (
              <Pending />
            ) : (
              <motion.div variants={RISE} data-testid="listing-error" transition={SETTLE}>
                <h3 className="text-base font-semibold text-text">No report for this listing</h3>
                <p className="mt-2 max-w-prose text-sm leading-6 text-muted">
                  {listing.error ?? "The check did not finish."}
                </p>
              </motion.div>
            )}
          </motion.div>
        </div>
      </div>
    </article>
  );
}
