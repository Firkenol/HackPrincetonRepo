"use client";

import { motion } from "framer-motion";
import { LoaderCircle } from "lucide-react";
import { useEffect, useRef } from "react";
import { describeProduct } from "@/lib/describe";
import { SETTLE } from "@/lib/motion";
import { markScrollEdges } from "@/lib/scroll";
import type { Listing } from "@/lib/types";
import { VerdictBadge } from "./VerdictBadge";

// The audit feed names each listing by a product description built from its extracted
// claims. It never shows the listing's title or any seller or store name.

export function feedTitle(listing: Listing): string {
  if (listing.report) return describeProduct(listing.report.claims);
  if (listing.running) return "Checking a listing";
  return "Listing not checked";
}

export function AuditFeed({
  listings,
  selectedKey,
  onSelect,
}: {
  listings: Listing[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
}) {
  const list = useRef<HTMLUListElement>(null);
  useEffect(() => markScrollEdges(list.current), [listings.length]);

  return (
    <nav aria-label="Audit feed" className="flex min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-4 pb-2 pt-4">
        <h2 className="text-sm font-semibold text-text">Audit feed</h2>
        <span className="font-mono text-xs tabular-nums text-faint">{listings.length} listed</span>
      </div>
      {listings.length === 0 ? (
        <p className="px-4 py-3 text-sm leading-6 text-muted">
          Nothing checked yet. Paste a listing or run the batch.
        </p>
      ) : (
        <motion.ul
          ref={list}
          layoutScroll
          onScroll={(e) => markScrollEdges(e.currentTarget)}
          className="pane-scroll scroll-fade min-h-0 flex-1 overflow-y-auto pb-3"
        >
          {listings.map((listing, index) => {
            const selected = listing.key === selectedKey;
            return (
              // A new check slides in at the top and the rows below make room for it.
              <motion.li
                key={listing.key}
                layout="position"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ ...SETTLE, delay: Math.min(index, 10) * 0.025 }}
                className="relative"
              >
                {/* One marker for the whole feed: it slides from the old selection to the new one. */}
                {selected && (
                  <motion.span
                    layoutId="feed-selection"
                    aria-hidden
                    transition={SETTLE}
                    className="absolute inset-0 border-l-2 border-accent bg-raised shadow-[inset_0_1px_0_rgb(255_255_255/0.04)]"
                  />
                )}
                <button
                  type="button"
                  data-testid="feed-item"
                  aria-current={selected ? "true" : undefined}
                  onClick={() => onSelect(listing.key)}
                  className={`relative block w-full border-l-2 border-transparent px-4 py-2.5 text-left transition-colors ${
                    selected ? "" : "hover:bg-raised/50"
                  }`}
                >
                  <span className={`block text-sm leading-5 transition-colors ${selected ? "text-text" : "text-text/85"}`}>{feedTitle(listing)}</span>
                  <span className="mt-1.5 flex flex-wrap items-center gap-2">
                    {listing.report && <VerdictBadge verdict={listing.report.verdict} size="sm" />}
                    {listing.report && <span className="text-xs text-muted">{listing.report.routing}</span>}
                    {listing.running && (
                      <span className="inline-flex items-center gap-1 text-xs text-accent">
                        <LoaderCircle size={12} className="animate-spin" aria-hidden /> running
                      </span>
                    )}
                    {listing.error && !listing.running && <span className="text-xs text-muted">no report</span>}
                    {listing.sample && <span className="text-xs text-faint">sample</span>}
                  </span>
                </button>
              </motion.li>
            );
          })}
        </motion.ul>
      )}
    </nav>
  );
}
