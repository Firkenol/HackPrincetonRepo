import { LoaderCircle } from "lucide-react";
import { describeProduct } from "@/lib/describe";
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
  return (
    <nav aria-label="Audit feed" className="flex min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-4 pb-2 pt-4">
        <h2 className="text-sm font-semibold text-text">Audit feed</h2>
        <span className="text-xs text-faint">{listings.length} listed</span>
      </div>
      {listings.length === 0 ? (
        <p className="px-4 py-3 text-sm leading-6 text-muted">
          Nothing checked yet. Paste a listing or run the batch.
        </p>
      ) : (
        <ul className="pane-scroll min-h-0 flex-1 overflow-y-auto pb-3">
          {listings.map((listing) => {
            const selected = listing.key === selectedKey;
            return (
              <li key={listing.key}>
                <button
                  type="button"
                  data-testid="feed-item"
                  aria-current={selected ? "true" : undefined}
                  onClick={() => onSelect(listing.key)}
                  className={`block w-full border-l-2 px-4 py-2.5 text-left transition-colors ${
                    selected ? "border-accent bg-raised" : "border-transparent hover:bg-raised/60"
                  }`}
                >
                  <span className="block text-sm leading-5 text-text">{feedTitle(listing)}</span>
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
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
