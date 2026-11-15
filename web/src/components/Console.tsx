"use client";

import { MotionConfig } from "framer-motion";
import { FlaskConical, Radio, WifiOff } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiUnreachable,
  absoluteUrl,
  fetchLatestBatch,
  fetchStats,
  runBatch,
  verifyListing,
  type Frame,
  type ListingInput,
} from "@/lib/api";
import { countItems, statsFromCounts } from "@/lib/counts";
import type { BatchItem, Counts, DashboardStats, DataSource, Listing } from "@/lib/types";
import { SAMPLES, matchSample } from "@/samples";
import { AuditFeed } from "./AuditFeed";
import { BatchView } from "./BatchView";
import { Intake } from "./Intake";
import { MathModule } from "./MathModule";
import { MetricsBar, formatRanAt, sampleLabel } from "./MetricsBar";
import { TracePanel } from "./TracePanel";
import { FeedSkeleton, MathSkeleton, MetricsSkeleton } from "./states/Skeletons";
import { VerdictCard } from "./VerdictCard";

const MSG_OFFLINE_CHECK =
  "The API is offline, so this listing was not checked. The bundled samples in the audit feed can still be opened.";

function toListing(item: BatchItem, sample: boolean): Listing {
  return {
    key: item.id,
    text: item.listing_text,
    imageUrl: absoluteUrl(item.image_url),
    report: item.report,
    error: item.error,
    events: [],
    running: false,
    sample,
  };
}

const SOURCE_PILL: Record<DataSource, { icon: typeof Radio; text: string; cls: string }> = {
  live: { icon: Radio, text: "Live model", cls: "border-clear/40 text-clear" },
  replay: { icon: FlaskConical, text: "Sample data: no model is configured", cls: "border-flag/40 text-flag" },
  offline: { icon: WifiOff, text: "Sample data: the API is offline", cls: "border-flag/40 text-flag" },
};

export function Console() {
  const [source, setSource] = useState<DataSource | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [batch, setBatch] = useState<{ items: BatchItem[]; counts: Counts } | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [view, setView] = useState<"listings" | "batch">("listings");
  const [batchRunning, setBatchRunning] = useState(false);
  // When the batch on screen ran, and whether that was before this page was opened.
  const [batchRun, setBatchRun] = useState<{ ranAt: string | null; preRun: boolean } | null>(null);
  const checkNumber = useRef(0);

  /** Replace the batch rows in the feed, keeping listings the person checked themselves on top. */
  const showBatch = useCallback((items: BatchItem[], counts: Counts, sample: boolean) => {
    setBatch({ items, counts });
    setListings((current) => [...current.filter((l) => l.key.startsWith("check-")), ...items.map((i) => toListing(i, sample))]);
    setSelectedKey((current) => current ?? items[0]?.id ?? null);
  }, []);

  const goOffline = useCallback(() => {
    const counts = countItems(SAMPLES);
    setSource("offline");
    setStats(statsFromCounts(counts, "replay", null));
    showBatch(SAMPLES, counts, true);
  }, [showBatch]);

  const doBatch = useCallback(async () => {
    setBatchRunning(true);
    try {
      const result = await runBatch();
      setSource(result.mode);
      showBatch(result.items, result.counts, result.sample_data);
      setBatchRun({ ranAt: result.ran_at, preRun: false });
      setStats(await fetchStats());
    } catch (error) {
      if (error instanceof ApiUnreachable) goOffline();
    } finally {
      setBatchRunning(false);
    }
  }, [goOffline, showBatch]);

  // On load: ask the API what it has. In sample-data mode the batch costs nothing, so
  // it runs straight away and the console opens with the nine sample listings.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const first = await fetchStats();
        if (cancelled) return;
        setSource(first.mode);
        setStats(first);
        if (first.mode === "replay") {
          await doBatch();
        } else if (first.has_run) {
          // A live batch is slow, so it is run ahead of time. Show that run, labelled as pre-run.
          const latest = await fetchLatestBatch();
          if (!cancelled && latest.has_run && latest.counts) {
            showBatch(latest.items, latest.counts, latest.sample_data);
            setBatchRun({ ranAt: latest.ran_at, preRun: true });
          }
        }
      } catch (error) {
        if (!cancelled && error instanceof ApiUnreachable) goOffline();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [doBatch, goOffline, showBatch]);

  const update = useCallback((key: string, change: (listing: Listing) => Listing) => {
    setListings((current) => current.map((l) => (l.key === key ? change(l) : l)));
  }, []);

  const check = useCallback(
    async (input: ListingInput, shown: { text: string | null; imageUrl: string | null }) => {
      checkNumber.current += 1;
      const key = `check-${checkNumber.current}`;
      const fresh: Listing = { key, ...shown, report: null, error: null, events: [], running: true, sample: false };
      setListings((current) => [fresh, ...current]);
      setSelectedKey(key);
      setView("listings");

      const onFrame = (frame: Frame) => {
        if (frame.kind === "meta") {
          update(key, (l) => ({ ...l, sample: frame.meta.sample_data }));
          return;
        }
        const event = frame.event;
        update(key, (l) => ({
          ...l,
          events: [...l.events, event],
          report: event.type === "final_report" ? event.report : l.report,
          error: event.type === "error" ? event.message : l.error,
        }));
      };

      try {
        await verifyListing(input, onFrame);
      } catch (error) {
        if (error instanceof ApiUnreachable) {
          // Offline: only a listing that is one of the bundled samples has a report to show.
          const sample = shown.text ? matchSample(shown.text) : null;
          update(key, (l) =>
            sample?.report ? { ...l, report: sample.report, sample: true } : { ...l, error: MSG_OFFLINE_CHECK },
          );
        } else {
          update(key, (l) => ({ ...l, error: error instanceof Error ? error.message : "The check did not finish." }));
        }
      } finally {
        update(key, (l) => ({ ...l, running: false }));
      }
    },
    [update],
  );

  const selected = listings.find((l) => l.key === selectedKey) ?? null;
  const busy = listings.some((l) => l.running);
  const pill = source ? SOURCE_PILL[source] : null;
  const label = source ? sampleLabel(source) : null;

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex min-h-screen flex-col">
        <header className="relative flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-6 py-4">
          <span aria-hidden className="pointer-events-none absolute inset-x-0 -bottom-px h-px bg-gradient-to-r from-accent/70 via-accent/10 to-transparent" />
          <div className="flex items-baseline gap-3">
            <h1 className="text-xl font-semibold tracking-tight text-text">OffSpec</h1>
            <p className="text-sm text-muted">Checks product claims against physics and shows the math</p>
          </div>
          {pill ? (
            <span data-testid="source-pill" className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs ${pill.cls}`}>
              <pill.icon size={13} aria-hidden /> {pill.text}
            </span>
          ) : (
            <span className="text-xs text-faint">Connecting to the API</span>
          )}
        </header>

        {stats === null && source === null ? (
          <MetricsSkeleton />
        ) : (
          <MetricsBar stats={stats} source={source ?? "live"} preRun={Boolean(batchRun?.preRun)} />
        )}

        <div className="grid flex-1 lg:grid-cols-[19rem_1fr]">
          <aside className="max-h-72 border-b border-line bg-panel lg:sticky lg:top-0 lg:h-screen lg:max-h-screen lg:self-start lg:border-b-0 lg:border-r">
            <div className="flex h-full max-h-72 flex-col lg:max-h-screen">
              {listings.length === 0 && (busy || batchRunning) ? (
                <FeedSkeleton />
              ) : (
                <AuditFeed
                  listings={listings}
                  selectedKey={selectedKey}
                  onSelect={(key) => {
                    setSelectedKey(key);
                    setView("listings");
                  }}
                />
              )}
            </div>
          </aside>

          <main className="min-w-0 space-y-6 p-5 lg:p-6">
            <div role="tablist" aria-label="View" className="inline-flex rounded-md border border-line bg-panel p-0.5 text-sm">
              {(["listings", "batch"] as const).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  role="tab"
                  aria-selected={view === tab}
                  onClick={() => setView(tab)}
                  className={`rounded px-3 py-1 ${view === tab ? "bg-raised text-text" : "text-muted hover:text-text"}`}
                >
                  {tab === "listings" ? "Listing" : "Batch"}
                </button>
              ))}
            </div>

            {view === "batch" ? (
              <BatchView
                items={batch?.items ?? []}
                counts={batch?.counts ?? null}
                running={batchRunning}
                canRun={source !== "offline" && source !== null}
                sampleLabel={label}
                runLabel={
                  batchRun?.ranAt
                    ? `${batchRun.preRun ? "Pre-run batch" : "Ran"}, ${formatRanAt(batchRun.ranAt)}`
                    : batchRun?.preRun
                      ? "Pre-run batch"
                      : null
                }
                onRun={doBatch}
                onOpen={(id) => {
                  setSelectedKey(id);
                  setView("listings");
                }}
              />
            ) : (
              <>
                <Intake
                  busy={busy}
                  onText={(text) => check({ text }, { text, imageUrl: null })}
                  onImage={(file) => check({ image: file }, { text: null, imageUrl: URL.createObjectURL(file) })}
                />

                {selected ? (
                  <>
                    <VerdictCard listing={selected} />
                    {/* The live trace is a core part of the view: full width, directly under the verdict. */}
                    <TracePanel events={selected.events} running={selected.running} />
                    {selected.report ? (
                      <MathModule key={selected.key} report={selected.report} />
                    ) : selected.running ? (
                      <MathSkeleton />
                    ) : (
                      <p className="rounded-lg border border-line bg-panel px-4 py-6 text-sm text-muted">
                        The math appears here once the checks have run.
                      </p>
                    )}
                  </>
                ) : (
                  <p className="rounded-lg border border-line bg-panel px-4 py-8 text-sm leading-6 text-muted">
                    Paste a listing or upload a screenshot to check it. Checked listings appear in the audit feed.
                  </p>
                )}
              </>
            )}
          </main>
        </div>
      </div>
    </MotionConfig>
  );
}
