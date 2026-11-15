import { CircleCheck, CircleSlash, OctagonX, TriangleAlert, type LucideIcon } from "lucide-react";
import type { CheckStatus, Routing, Verdict } from "@/lib/types";

// The four verdict strings are shown exactly as the report gives them.
const VERDICT_STYLE: Record<Verdict, { icon: LucideIcon; text: string; ring: string; fill: string }> = {
  Impossible: { icon: OctagonX, text: "text-impossible", ring: "border-impossible/50", fill: "bg-impossible/10" },
  Flag: { icon: TriangleAlert, text: "text-flag", ring: "border-flag/50", fill: "bg-flag/10" },
  "No red flags": { icon: CircleCheck, text: "text-clear", ring: "border-clear/50", fill: "bg-clear/10" },
  "No checkable claim": { icon: CircleSlash, text: "text-quiet", ring: "border-quiet/50", fill: "bg-quiet/10" },
};

export function verdictColor(verdict: Verdict): string {
  return VERDICT_STYLE[verdict]?.text ?? "text-quiet";
}

export function VerdictBadge({ verdict, size = "md" }: { verdict: Verdict; size?: "sm" | "md" | "lg" }) {
  const style = VERDICT_STYLE[verdict] ?? VERDICT_STYLE["No checkable claim"];
  const Icon = style.icon;
  const sizing =
    size === "lg"
      ? "gap-3 rounded-lg px-4 py-2.5 text-2xl font-semibold tracking-tight shadow-[inset_0_1px_0_rgb(255_255_255/0.08),0_10px_30px_-14px_currentColor]"
      : size === "sm"
        ? "gap-1.5 px-2 py-0.5 text-xs font-medium"
        : "gap-2 px-3 py-1 text-sm font-medium";
  const icon = size === "lg" ? 26 : size === "sm" ? 13 : 16;
  return (
    <span
      data-testid="verdict-badge"
      data-verdict={verdict}
      className={`inline-flex items-center rounded-md border ${style.ring} ${style.fill} ${style.text} ${sizing}`}
    >
      <Icon size={icon} aria-hidden />
      {verdict}
    </span>
  );
}

const ROUTING_NOTE: Record<Routing, string> = {
  "auto-resolvable": "The calculation decides it",
  "needs human review": "A person should look",
  "no action needed": "Nothing to follow up",
};

export function RoutingLabel({ routing, withNote = false }: { routing: Routing; withNote?: boolean }) {
  return (
    <span data-testid="routing-label" className="inline-flex items-baseline gap-2 text-sm">
      <span className="rounded-md border border-line bg-raised px-2 py-0.5 font-medium text-text shadow-[inset_0_1px_0_rgb(255_255_255/0.05)]">{routing}</span>
      {withNote && <span className="text-muted">{ROUTING_NOTE[routing]}</span>}
    </span>
  );
}

const STATUS: Record<CheckStatus, { label: string; cls: string }> = {
  pass: { label: "Pass", cls: "text-clear border-clear/40 bg-clear/10" },
  violated: { label: "Bound exceeded", cls: "text-impossible border-impossible/40 bg-impossible/10" },
  flag: { label: "Flag", cls: "text-flag border-flag/40 bg-flag/10" },
  not_assessed: { label: "Not assessed", cls: "text-quiet border-line" },
};

export function StatusChip({ status }: { status: CheckStatus }) {
  const s = STATUS[status] ?? STATUS.not_assessed;
  return (
    <span data-testid="check-status" className={`shrink-0 rounded-md border px-2 py-0.5 text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  );
}
