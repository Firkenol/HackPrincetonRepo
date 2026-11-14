import { ROUTINGS, VERDICTS, type BatchItem, type Counts, type DashboardStats, type Mode } from "./types";

/** Counts per verdict and routing. Used only for the bundled samples; live counts come from the API. */
export function countItems(items: BatchItem[]): Counts {
  const by_verdict = Object.fromEntries(VERDICTS.map((v) => [v, 0])) as Counts["by_verdict"];
  const by_routing = Object.fromEntries(ROUTINGS.map((r) => [r, 0])) as Counts["by_routing"];
  let total = 0;
  let errors = 0;
  for (const item of items) {
    if (!item.report) {
      errors += 1;
      continue;
    }
    total += 1;
    by_verdict[item.report.verdict] += 1;
    by_routing[item.report.routing] += 1;
  }
  return { total, errors, by_verdict, by_routing };
}

export function statsFromCounts(counts: Counts, mode: Mode, ranAt: string | null): DashboardStats {
  return {
    mode,
    sample_data: mode === "replay",
    has_run: true,
    ran_at: ranAt,
    listings_checked: counts.total,
    impossible_claims: counts.by_verdict["Impossible"],
    routed_to_human_review: counts.by_routing["needs human review"],
    no_action_needed: counts.by_routing["no action needed"],
    auto_resolvable: counts.by_routing["auto-resolvable"],
    errors: counts.errors,
    by_verdict: counts.by_verdict,
    by_routing: counts.by_routing,
  };
}
