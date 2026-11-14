// Mirrors CONTRACT.md. The frontend depends only on the event JSON and the report JSON.

export const VERDICTS = ["Impossible", "Flag", "No red flags", "No checkable claim"] as const;
export type Verdict = (typeof VERDICTS)[number];

export const ROUTINGS = ["auto-resolvable", "needs human review", "no action needed"] as const;
export type Routing = (typeof ROUTINGS)[number];

export const CHECK_IDS = [
  "label_consistency",
  "form_factor_bound",
  "dimension_bound",
  "weight_bound",
  "label_contradiction",
  "chemistry_mismatch",
] as const;
export type CheckId = (typeof CHECK_IDS)[number];

export type CheckStatus = "pass" | "violated" | "flag" | "not_assessed";
export const CHECK_STATUSES: readonly CheckStatus[] = ["pass", "violated", "flag", "not_assessed"];

export type AgentName = "orchestrator" | "listing-reader" | "physics-checker" | "report-writer";

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
  value: number;
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
  check_id: CheckId;
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

export interface EvidenceReport {
  schema_version: string;
  claims: Claims;
  checks: CheckResult[];
  verdict: Verdict;
  verdict_reason: string;
  routing: Routing;
  routing_reason: string;
  assumptions: string[];
  not_assessed: string[];
}

interface EventBase {
  run_id: string;
  seq: number;
  agent: AgentName;
}
export interface AgentStepEvent extends EventBase {
  type: "agent_step";
  message: string;
}
export interface ToolCallEvent extends EventBase {
  type: "tool_call";
  call_id: string;
  tool: string;
  args: Record<string, unknown>;
}
export interface ToolResultEvent extends EventBase {
  type: "tool_result";
  call_id: string;
  tool: string;
  ok: boolean;
  summary: string;
  result: unknown;
}
export interface FinalReportEvent extends EventBase {
  type: "final_report";
  report: EvidenceReport;
}
export interface ErrorEvent extends EventBase {
  type: "error";
  message: string;
}
export type StreamEvent = AgentStepEvent | ToolCallEvent | ToolResultEvent | FinalReportEvent | ErrorEvent;

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;

/** True when a tool result is a CheckResult, so the card can show it before the report arrives. */
export function isCheckResult(v: unknown): v is CheckResult {
  return (
    isObject(v) &&
    (CHECK_IDS as readonly unknown[]).includes(v.check_id) &&
    (CHECK_STATUSES as readonly unknown[]).includes(v.status) &&
    Array.isArray(v.steps) &&
    Array.isArray(v.constants) &&
    Array.isArray(v.inputs)
  );
}

/** Returns a reason when the report uses a verdict or routing string outside the contract. */
export function reportProblem(report: unknown): string | null {
  if (!isObject(report)) return "The report is not a JSON object.";
  if (!(VERDICTS as readonly unknown[]).includes(report.verdict)) return "The report carries a verdict outside the contract.";
  if (!(ROUTINGS as readonly unknown[]).includes(report.routing)) return "The report carries a routing value outside the contract.";
  if (!Array.isArray(report.checks) || !report.checks.every(isCheckResult)) return "The report's checks do not match the contract.";
  if (!isObject(report.claims)) return "The report has no claims object.";
  return null;
}
