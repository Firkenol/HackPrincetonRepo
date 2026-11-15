import { Inbox, type LucideIcon } from "lucide-react";

// An empty state: what is not here yet and the one thing that fills it.

export function EmptyState({
  title,
  text,
  icon: Icon = Inbox,
  action,
  compact = false,
}: {
  title: string;
  text?: string;
  icon?: LucideIcon;
  /** A button or link that fills the view. */
  action?: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div data-testid="empty-state" className={`rounded-lg border border-dashed border-line bg-panel text-center ${compact ? "px-4 py-5" : "px-4 py-10"}`}>
      <Icon size={compact ? 18 : 24} aria-hidden className="mx-auto text-faint" />
      <h3 className={`mt-2 font-medium text-text ${compact ? "text-sm" : "text-base"}`}>{title}</h3>
      {text && <p className="mx-auto mt-1 max-w-prose text-sm leading-6 text-muted">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
