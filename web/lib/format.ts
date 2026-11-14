import type { CheckStatus, Routing, Verdict } from "@/lib/types";

/** Trims float noise for display. The backend's own step text is shown as sent. */
export function num(value: number | string): string {
  if (typeof value === "string") return value;
  return new Intl.NumberFormat("en-US", { maximumSignificantDigits: 6 }).format(value);
}

export const STATUS_LABEL: Record<CheckStatus, string> = {
  pass: "Pass",
  violated: "Violated",
  flag: "Flag",
  not_assessed: "Not assessed",
};

// "No red flags" is deliberately not green and carries no tick: it is not a confirmation.
export const VERDICT_TONE: Record<Verdict, string> = {
  Impossible: "bg-red-600 text-white",
  Flag: "bg-amber-400 text-amber-950",
  "No red flags": "bg-sky-700 text-white",
  "No checkable claim": "bg-slate-500 text-white",
};

export const VERDICT_TEXT: Record<Verdict, string> = {
  Impossible: "text-red-700",
  Flag: "text-amber-700",
  "No red flags": "text-sky-800",
  "No checkable claim": "text-slate-600",
};

export const STATUS_TONE: Record<CheckStatus, string> = {
  pass: "bg-sky-50 text-sky-800 ring-sky-200",
  violated: "bg-red-50 text-red-700 ring-red-200",
  flag: "bg-amber-50 text-amber-800 ring-amber-300",
  not_assessed: "bg-slate-100 text-slate-600 ring-slate-200",
};

export const ROUTING_TONE: Record<Routing, { box: string; dot: string; bar: string }> = {
  "auto-resolvable": { box: "border-violet-300 bg-violet-50 text-violet-900", dot: "bg-violet-600", bar: "bg-violet-600" },
  "needs human review": { box: "border-amber-300 bg-amber-50 text-amber-900", dot: "bg-amber-500", bar: "bg-amber-400" },
  "no action needed": { box: "border-slate-300 bg-slate-50 text-slate-800", dot: "bg-slate-500", bar: "bg-slate-400" },
};
