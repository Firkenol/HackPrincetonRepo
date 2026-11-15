// The shapes in CONTRACT.md, as the API sends them. The web app depends only on these.

export const VERDICTS = ["Impossible", "Flag", "No red flags", "No checkable claim"] as const;
export type Verdict = (typeof VERDICTS)[number];

export const ROUTINGS = ["auto-resolvable", "needs human review", "no action needed"] as const;
export type Routing = (typeof ROUTINGS)[number];

export type CheckStatus = "pass" | "violated" | "flag" | "not_assessed";

interface Provenance {
  found_in: string;
  quote: string | null;
  confidence: number;
}
export interface NumberClaim extends Provenance {
  value: number;
}
export interface TextClaim extends Provenance {
  value: string;
}
export interface WeightClaim extends Provenance {
  value_g: number;
  kind: "product" | "package";
}
export interface DimensionsClaim extends Provenance {
  length_mm: number;
  width_mm: number;
  height_mm: number;
  kind: "product" | "package";
}

export interface Claims {
  product_type: "loose_cell" | "battery_pack" | "power_bank" | "unknown";
  chemistry: TextClaim | null;
  form_factors: TextClaim[];
  cell_count: NumberClaim | null;
  nominal_voltage_v: NumberClaim | null;
  capacity_mah: NumberClaim | null;
  energy_wh: NumberClaim | null;
  output_capacity_mah: NumberClaim | null;
  weight: WeightClaim | null;
  dimensions: DimensionsClaim | null;
  shelf_life_years: NumberClaim | null;
  printed_codes: TextClaim[];
  printed_terms: TextClaim[];
}

export interface Quantity {
  name: string;
  value: number | string;
  unit: string;
  origin: "claim" | "constant" | "derived" | "assumption";
  found_in?: string | null;
  confidence?: number | null;
}

export interface Step {
  label: string;
  formula: string;
  substitution: string;
  result: number | null;
  unit: string;
  text: string;
}

export interface Citation {
  key: string;
  value: number | string;
  unit: string;
  description: string;
  source_title: string;
  source_publisher: string;
  source_url: string;
  locator: string;
  quote: string;
  accessed: string;
  note: string;
  hard_bound: boolean;
}

export interface CheckResult {
  check_id: string;
  title: string;
  status: CheckStatus;
  summary: string;
  inputs: Quantity[];
  formula: string | null;
  steps: Step[];
  constants: Citation[];
  assumptions: string[];
  notes: string[];
  not_assessed_reason: string | null;
}

/** A check pack's own claims (projector, magnifying glass, monocular). Each pack has its own fields. */
export type PackClaims = Record<string, unknown>;

/**
 * The report for one listing. A battery listing has no `pack` and battery `Claims`.
 * A listing checked by a pack names the pack and carries that pack's claims
 * (PackEvidenceReport in CONTRACT.md). Everything else is the same.
 */
export interface EvidenceReport {
  schema_version: string;
  pack?: string;
  claims: Claims | PackClaims;
  checks: CheckResult[];
  verdict: Verdict;
  verdict_reason: string;
  routing: Routing;
  routing_reason: string;
  assumptions: string[];
  not_assessed: string[];
}

// ---- stream events

interface EventBase {
  run_id: string;
  seq: number;
  agent: "orchestrator" | "listing-reader" | "physics-checker" | "report-writer";
}
export type StreamEvent =
  | (EventBase & { type: "agent_step"; message: string })
  | (EventBase & { type: "tool_call"; call_id: string; tool: string; args: Record<string, unknown> })
  | (EventBase & { type: "tool_result"; call_id: string; tool: string; ok: boolean; summary: string; result: unknown })
  | (EventBase & { type: "final_report"; report: EvidenceReport })
  | (EventBase & { type: "error"; message: string });

// ---- API bodies

export type Mode = "live" | "replay";

/** Where the data on screen came from. "offline" means the API was unreachable and bundled samples are shown. */
export type DataSource = Mode | "offline";

export interface BatchItem {
  id: string;
  source: "text" | "image";
  listing_text: string | null;
  image_url: string | null;
  report: EvidenceReport | null;
  error: string | null;
}

export interface Counts {
  total: number;
  errors: number;
  by_verdict: Record<Verdict, number>;
  by_routing: Record<Routing, number>;
}

export interface BatchResponse {
  mode: Mode;
  sample_data: boolean;
  ran_at: string;
  items: BatchItem[];
  counts: Counts;
}

/** GET /api/batch: the latest batch run, or has_run false when none has run. */
export interface LatestBatch {
  mode: Mode;
  sample_data: boolean;
  has_run: boolean;
  ran_at: string | null;
  items: BatchItem[];
  counts: Counts | null;
}

export interface DashboardStats {
  mode: Mode;
  sample_data: boolean;
  has_run: boolean;
  ran_at: string | null;
  listings_checked: number | null;
  impossible_claims: number | null;
  routed_to_human_review: number | null;
  no_action_needed: number | null;
  auto_resolvable: number | null;
  errors: number | null;
  by_verdict: Record<Verdict, number> | null;
  by_routing: Record<Routing, number> | null;
}

/** One checked listing as the console holds it. */
export interface Listing {
  key: string;
  /** Text the person pasted or a fixture's text. Shown only in the listing pane. */
  text: string | null;
  /** A URL for the screenshot: an object URL for an upload, or an API URL for a fixture. */
  imageUrl: string | null;
  report: EvidenceReport | null;
  error: string | null;
  events: StreamEvent[];
  running: boolean;
  /** True when the report is sample data rather than a live check. */
  sample: boolean;
}
