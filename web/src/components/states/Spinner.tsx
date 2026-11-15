import { LoaderCircle } from "lucide-react";

// A short wait: a spinning icon with a label. For anything longer than a moment,
// use a skeleton shaped like the view that is coming (Skeletons.tsx).

export function Spinner({
  label = "Loading",
  size = 16,
  className = "",
}: {
  label?: string;
  size?: number;
  className?: string;
}) {
  return (
    <span role="status" className={`inline-flex items-center gap-2 text-sm text-accent ${className}`}>
      <LoaderCircle size={size} className="animate-spin motion-reduce:animate-none" aria-hidden />
      <span>{label}</span>
    </span>
  );
}
