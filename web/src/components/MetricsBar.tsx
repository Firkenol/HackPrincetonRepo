import type { DashboardStats, DataSource } from "@/lib/types";

// The four headline counts. Every number comes from the API's dashboard stats, which
// are counted from the latest batch run. Before a run there is nothing to show, so
// the tiles show a dash rather than a made-up figure.

const TILES: { key: keyof DashboardStats; label: string; tone: string }[] = [
  { key: "listings_checked", label: "Listings checked", tone: "text-text" },
  { key: "impossible_claims", label: "Impossible claims", tone: "text-impossible" },
  { key: "routed_to_human_review", label: "Routed to human review", tone: "text-flag" },
  { key: "no_action_needed", label: "No action needed", tone: "text-clear" },
];

export function sampleLabel(source: DataSource): string | null {
  if (source === "replay") return "Sample data";
  if (source === "offline") return "Sample data, API offline";
  return null;
}

/** "11/14/2026, 2:53 PM" for an API timestamp, or an empty string. */
export function formatRanAt(ranAt: string | null | undefined): string {
  return ranAt ? new Date(ranAt).toLocaleString() : "";
}

export function MetricsBar({
  stats,
  source,
  preRun = false,
}: {
  stats: DashboardStats | null;
  source: DataSource;
  /** True when the counts come from a batch that was run before this page was opened. */
  preRun?: boolean;
}) {
  const label = sampleLabel(source);
  const hasRun = Boolean(stats?.has_run);
  return (
    <section aria-label="Batch totals" className="border-b border-line bg-panel">
      <dl className="grid grid-cols-2 divide-line-soft lg:grid-cols-4 lg:divide-x">
        {TILES.map((tile) => {
          const value = hasRun ? (stats?.[tile.key] as number | null) : null;
          return (
            <div key={tile.key} data-testid={`metric-${tile.key}`} className="px-5 py-4">
              <dt className="text-sm text-muted">{tile.label}</dt>
              <dd className={`mt-1 font-mono text-3xl font-medium tabular-nums ${value === null ? "text-faint" : tile.tone}`}>
                {value === null ? "–" : value}
              </dd>
            </div>
          );
        })}
      </dl>
      <p className="border-t border-line-soft px-5 py-1.5 text-xs text-faint" data-testid="metrics-caption">
        {hasRun
          ? `Counted from ${preRun ? "a pre-run batch" : "the latest batch run"}${stats?.ran_at ? `, ${formatRanAt(stats.ran_at)}` : ""}.`
          : "No batch has run yet. Run the batch to fill these counts."}
        {hasRun && preRun && (
          <span data-testid="prerun-label" className="ml-2 rounded border border-accent/40 px-1.5 py-0.5 text-accent">
            Pre-run
          </span>
        )}
        {label && (
          <span data-testid="sample-label" className="ml-2 rounded border border-flag/40 px-1.5 py-0.5 text-flag">
            {label}
          </span>
        )}
      </p>
    </section>
  );
}
