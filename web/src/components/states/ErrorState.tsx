"use client";

import { CircleAlert, RotateCcw, WifiOff, type LucideIcon } from "lucide-react";

// Error states that say what went wrong and what to do next. Wording is neutral and
// about this console and its API, never about a marketplace or a seller.

export type ErrorKind = "offline" | "failed" | "rejected";

const KIND: Record<ErrorKind, { icon: LucideIcon; title: string; next: string }> = {
  offline: {
    icon: WifiOff,
    title: "The API could not be reached",
    next: "Start the API (uvicorn api.app:app --port 8000 from backend/) or set NEXT_PUBLIC_API_URL, then try again. Bundled sample reports can still be opened.",
  },
  failed: {
    icon: CircleAlert,
    title: "The check did not finish",
    next: "Try the listing again. If it fails twice, the trace shows the last step that ran.",
  },
  rejected: {
    icon: CircleAlert,
    title: "This input could not be checked",
    next: "Paste the listing text or upload a PNG, JPEG or WebP screenshot under 3.5 MB.",
  },
};

export function ErrorState({
  kind = "failed",
  title,
  detail,
  next,
  onRetry,
  retryLabel = "Try again",
  compact = false,
}: {
  kind?: ErrorKind;
  /** Overrides the default title for the kind. */
  title?: string;
  /** What went wrong, in the words the API or the stream gave. */
  detail?: string | null;
  /** Overrides the default "what to do next". */
  next?: string;
  onRetry?: () => void;
  retryLabel?: string;
  compact?: boolean;
}) {
  const k = KIND[kind];
  const Icon = k.icon;
  return (
    <div
      role="alert"
      data-testid="error-state"
      data-kind={kind}
      className={`rounded-lg border border-impossible/40 bg-impossible/5 ${compact ? "px-3 py-2.5" : "px-4 py-5"}`}
    >
      <div className="flex items-start gap-3">
        <Icon size={compact ? 16 : 20} aria-hidden className="mt-0.5 shrink-0 text-impossible" />
        <div className="min-w-0 flex-1">
          <h3 className={`font-semibold text-text ${compact ? "text-sm" : "text-base"}`}>{title ?? k.title}</h3>
          {detail && <p className="mt-1 max-w-prose text-sm leading-6 text-muted">{detail}</p>}
          <p className="mt-1 max-w-prose text-sm leading-6 text-muted">
            <span className="text-text">What to do next: </span>
            {next ?? k.next}
          </p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-2 rounded-md border border-line bg-raised px-3 py-1.5 text-sm text-text hover:border-accent"
            >
              <RotateCcw size={14} aria-hidden /> {retryLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
