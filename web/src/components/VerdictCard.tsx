"use client";

import { motion } from "framer-motion";
import { Download, LoaderCircle } from "lucide-react";
import { describeProduct } from "@/lib/describe";
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
  return (
    <div className="flex min-h-64 flex-col border-b border-line lg:border-b-0 lg:border-r">
      <h3 className="border-b border-line-soft px-4 py-2 text-xs font-medium text-muted">
        The listing as submitted
      </h3>
      <div className="pane-scroll max-h-[26rem] flex-1 overflow-auto p-4">
        {listing.imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- a local object URL or an API file, not an optimisable asset
          <img src={listing.imageUrl} alt="Listing screenshot" className="max-w-full rounded border border-line" />
        ) : listing.text ? (
          <pre data-testid="listing-text" className="whitespace-pre-wrap font-mono text-[13px] leading-6 text-text">
            {listing.text}
          </pre>
        ) : (
          <p className="text-sm text-muted">The listing itself is not available for this sample.</p>
        )}
      </div>
    </div>
  );
}

export function VerdictCard({ listing }: { listing: Listing }) {
  const { report } = listing;
  return (
    <article data-testid="verdict-card" className="overflow-hidden rounded-lg border border-line bg-panel">
      <div className="grid lg:grid-cols-2">
        <ListingPane listing={listing} />

        <motion.div
          key={report ? "report" : listing.running ? "running" : "idle"}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="flex flex-col gap-4 p-5"
        >
          {report ? (
            <>
              <p className="text-sm text-muted">{describeProduct(report.claims)}</p>
              <div>
                <VerdictBadge verdict={report.verdict} size="lg" />
              </div>
              <p className="max-w-prose text-sm leading-6 text-text">{report.verdict_reason}</p>

              <div className="border-t border-line-soft pt-4">
                <RoutingLabel routing={report.routing} withNote />
                <p className="mt-2 max-w-prose text-sm leading-6 text-muted">{report.routing_reason}</p>
              </div>

              {report.not_assessed.length > 0 && (
                <div className="border-t border-line-soft pt-4">
                  <h3 className="text-xs font-medium text-muted">Not assessed</h3>
                  <ul className="mt-1.5 space-y-1 text-sm leading-6 text-muted">
                    {report.not_assessed.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-auto flex flex-wrap items-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => downloadReport(report, `carnot-report-${listing.key}`)}
                  className="inline-flex items-center gap-2 rounded-md border border-line bg-raised px-3 py-1.5 text-sm text-text hover:border-accent"
                >
                  <Download size={15} aria-hidden /> Download report JSON
                </button>
                {listing.sample && (
                  <span data-testid="card-sample-label" className="rounded border border-flag/40 px-1.5 py-0.5 text-xs text-flag">
                    Sample data
                  </span>
                )}
              </div>
            </>
          ) : listing.running ? (
            <p className="inline-flex items-center gap-2 text-sm text-accent">
              <LoaderCircle size={16} className="animate-spin" aria-hidden /> Checking the listing. The trace shows each step.
            </p>
          ) : (
            <div data-testid="listing-error">
              <h3 className="text-base font-semibold text-text">No report for this listing</h3>
              <p className="mt-2 max-w-prose text-sm leading-6 text-muted">
                {listing.error ?? "The check did not finish."}
              </p>
            </div>
          )}
        </motion.div>
      </div>
    </article>
  );
}
