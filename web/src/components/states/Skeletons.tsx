// Skeleton loaders shaped like the views they stand in for. Each is a static layout of
// placeholder bars that pulses gently (and not at all under prefers-reduced-motion),
// so the page keeps its shape while the real content is on its way.

function Bar({ w = "w-full", h = "h-3", className = "" }: { w?: string; h?: string; className?: string }) {
  return <span aria-hidden className={`block ${w} ${h} rounded bg-raised ${className}`} />;
}

function Frame({ label, children, className = "" }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div role="status" aria-label={label} aria-busy="true" data-testid="skeleton" className={`animate-pulse motion-reduce:animate-none ${className}`}>
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

/** Stands in for the four metric tiles while the dashboard stats load. */
export function MetricsSkeleton() {
  return (
    <Frame label="Loading batch totals" className="border-b border-line bg-panel">
      <div className="grid grid-cols-2 lg:grid-cols-4 lg:divide-x lg:divide-line-soft">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="px-5 py-4">
            <Bar w="w-28" />
            <Bar w="w-16" h="h-8" className="mt-2" />
          </div>
        ))}
      </div>
      <div className="border-t border-line-soft px-5 py-2.5">
        <Bar w="w-56" h="h-2.5" />
      </div>
    </Frame>
  );
}

/** Stands in for the audit feed. */
export function FeedSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Frame label="Loading the audit feed">
      <ul className="pb-3">
        {Array.from({ length: rows }, (_, i) => (
          <li key={i} className="border-l-2 border-transparent px-4 py-2.5">
            <Bar w={i % 2 ? "w-4/5" : "w-3/5"} />
            <span className="mt-2 flex items-center gap-2">
              <Bar w="w-20" h="h-4" />
              <Bar w="w-24" h="h-2.5" />
            </span>
          </li>
        ))}
      </ul>
    </Frame>
  );
}

/** Stands in for the verdict card: the listing pane on the left, the verdict on the right. */
export function VerdictCardSkeleton() {
  return (
    <Frame label="Loading the verdict card" className="overflow-hidden rounded-lg border border-line bg-panel">
      <div className="grid lg:grid-cols-2">
        <div className="min-h-64 border-b border-line p-4 lg:border-b-0 lg:border-r">
          <Bar w="w-36" h="h-2.5" />
          <div className="mt-4 space-y-2">
            <Bar w="w-5/6" />
            <Bar w="w-2/3" />
            <Bar w="w-3/4" />
            <Bar w="w-1/2" />
          </div>
        </div>
        <div className="space-y-4 p-5">
          <Bar w="w-48" h="h-2.5" />
          <Bar w="w-40" h="h-9" />
          <Bar w="w-full" />
          <Bar w="w-4/5" />
          <div className="border-t border-line-soft pt-4">
            <Bar w="w-32" h="h-5" />
            <Bar w="w-3/4" className="mt-3" />
          </div>
        </div>
      </div>
    </Frame>
  );
}

/** Stands in for "Show the math": six collapsed check rows. */
export function MathSkeleton() {
  return (
    <Frame label="Loading the checks">
      <div className="mb-3 flex items-baseline justify-between">
        <Bar w="w-32" h="h-4" />
        <Bar w="w-56" h="h-2.5" />
      </div>
      <ul className="space-y-2">
        {Array.from({ length: 6 }, (_, i) => (
          <li key={i} className="flex items-start gap-3 rounded-lg border border-line bg-panel px-4 py-3">
            <Bar w="w-4" h="h-4" className="mt-0.5" />
            <span className="flex-1">
              <Bar w="w-48" />
              <Bar w={i % 2 ? "w-5/6" : "w-2/3"} h="h-2.5" className="mt-2" />
            </span>
            <Bar w="w-16" h="h-5" />
          </li>
        ))}
      </ul>
    </Frame>
  );
}

/** Stands in for the trace panel: the agent strip and a few event rows. */
export function TraceSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Frame label="Loading the trace" className="rounded-lg border border-line bg-panel">
      <div className="flex items-center justify-between border-b border-line-soft px-4 py-2.5">
        <Bar w="w-12" h="h-4" />
        <Bar w="w-16" h="h-2.5" />
      </div>
      <div className="flex items-center gap-2 px-4 py-3">
        {[0, 1, 2, 3].map((i) => (
          <Bar key={i} w="w-full" h="h-7" />
        ))}
      </div>
      <ul className="space-y-1.5 border-t border-line-soft px-4 py-3">
        {Array.from({ length: rows }, (_, i) => (
          <li key={i} className="grid grid-cols-[7.5rem_4rem_1fr] gap-x-2">
            <Bar w="w-24" h="h-2.5" />
            <Bar w="w-10" h="h-2.5" />
            <Bar w={["w-3/4", "w-1/2", "w-5/6", "w-2/3", "w-3/5"][i % 5]} h="h-2.5" />
          </li>
        ))}
      </ul>
    </Frame>
  );
}

/** Stands in for the batch table. */
export function BatchTableSkeleton({ rows = 9 }: { rows?: number }) {
  return (
    <Frame label="Loading the batch">
      <div className="mb-4 h-36 rounded-lg border border-line bg-panel p-4">
        <div className="space-y-3">
          <Bar w="w-2/3" h="h-4" />
          <Bar w="w-1/2" h="h-4" />
          <Bar w="w-5/6" h="h-4" />
        </div>
      </div>
      <ul className="divide-y divide-line-soft rounded-lg border border-line bg-panel">
        {Array.from({ length: rows }, (_, i) => (
          <li key={i} className="grid grid-cols-[1fr_8rem_10rem] items-center gap-3 px-4 py-2.5">
            <Bar w={i % 3 ? "w-3/4" : "w-1/2"} />
            <Bar w="w-24" h="h-5" />
            <Bar w="w-32" h="h-5" />
          </li>
        ))}
      </ul>
    </Frame>
  );
}
