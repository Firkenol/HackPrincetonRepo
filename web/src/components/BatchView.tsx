"use client";

import { motion } from "framer-motion";
import { LoaderCircle, Play } from "lucide-react";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { describeProduct } from "@/lib/describe";
import { RISE, stagger } from "@/lib/motion";
import { ROUTINGS, type BatchItem, type Counts, type Routing } from "@/lib/types";
import { RoutingLabel, VerdictBadge } from "./VerdictBadge";

// Batch view: every listing in the fixtures folder, one row each, with the split
// between what the calculation settles and what goes to a person.

const ROUTING_COLOR: Record<Routing, string> = {
  "auto-resolvable": "#f26d78",
  "needs human review": "#f2b441",
  "no action needed": "#4fcf8e",
};

function RoutingChart({ counts }: { counts: Counts }) {
  const data = ROUTINGS.map((routing) => ({ routing, count: counts.by_routing[routing] }));
  return (
    <div className="h-36" data-testid="routing-chart">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 8 }}>
          <XAxis type="number" allowDecimals={false} hide />
          <YAxis
            type="category"
            dataKey="routing"
            width={140}
            tickLine={false}
            axisLine={false}
            tick={{ fill: "#93a0b4", fontSize: 12 }}
          />
          <Tooltip
            cursor={{ fill: "#1a2433" }}
            contentStyle={{ background: "#131b27", border: "1px solid #273347", borderRadius: 6, color: "#e7ecf3" }}
          />
          <Bar dataKey="count" radius={[0, 3, 3, 0]} barSize={16} label={{ position: "right", fill: "#e7ecf3", fontSize: 12 }}>
            {data.map((row) => (
              <Cell key={row.routing} fill={ROUTING_COLOR[row.routing]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BatchView({
  items,
  counts,
  running,
  canRun,
  sampleLabel,
  runLabel = null,
  onRun,
  onOpen,
}: {
  items: BatchItem[];
  counts: Counts | null;
  running: boolean;
  canRun: boolean;
  sampleLabel: string | null;
  /** When the batch on screen ran, e.g. "Pre-run batch, 11/14/2026, 2:53 PM". */
  runLabel?: string | null;
  onRun: () => void;
  onOpen: (id: string) => void;
}) {
  return (
    <section aria-labelledby="batch-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="batch-heading" className="text-base font-semibold text-text">
            Batch
          </h2>
          <p className="mt-0.5 text-sm text-muted">Runs every listing in the fixtures folder and counts the results.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {runLabel && (
            <span data-testid="batch-run-label" className="rounded border border-accent/40 px-1.5 py-0.5 text-xs text-accent">
              {runLabel}
            </span>
          )}
          {sampleLabel && (
            <span data-testid="batch-sample-label" className="rounded border border-flag/40 px-1.5 py-0.5 text-xs text-flag">
              {sampleLabel}
            </span>
          )}
          <button
            type="button"
            onClick={onRun}
            disabled={running || !canRun}
            className="btn btn-primary"
          >
            {running ? <LoaderCircle size={14} className="animate-spin" aria-hidden /> : <Play size={14} aria-hidden />}
            {running ? "Running batch" : "Run batch"}
          </button>
        </div>
      </div>

      {counts && items.length > 0 ? (
        <>
          <motion.div variants={RISE} initial="hidden" animate="show" className="surface grid gap-4 p-5 lg:grid-cols-[18rem_1fr]">
            <dl className="grid grid-cols-2 content-start gap-x-6 gap-y-3">
              <div>
                <dt className="text-xs text-muted">Settled by the calculation</dt>
                <dd data-testid="batch-auto" className="font-mono text-3xl font-medium tabular-nums text-impossible">
                  {counts.by_routing["auto-resolvable"]}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Routed to a person</dt>
                <dd data-testid="batch-human" className="font-mono text-3xl font-medium tabular-nums text-flag">
                  {counts.by_routing["needs human review"]}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted">No action needed</dt>
                <dd data-testid="batch-none" className="font-mono text-3xl font-medium tabular-nums text-clear">
                  {counts.by_routing["no action needed"]}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted">Could not be checked</dt>
                <dd className="font-mono text-3xl font-medium tabular-nums text-muted">{counts.errors}</dd>
              </div>
            </dl>
            <RoutingChart counts={counts} />
          </motion.div>

          <div className="surface overflow-x-auto">
            <table className="w-full min-w-[40rem] text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] uppercase tracking-[0.08em] text-faint">
                  <th scope="col" className="px-4 py-2.5 font-medium">Product</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Verdict</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Routing</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Checks not assessed</th>
                </tr>
              </thead>
              <motion.tbody variants={stagger(0.035, 0.05)} initial="hidden" animate="show">
                {items.map((item) => (
                  <motion.tr
                    key={item.id}
                    variants={RISE}
                    data-testid="batch-row"
                    className="border-b border-line-soft transition-colors last:border-b-0 hover:bg-raised/40"
                  >
                    <td className="px-4 py-2.5">
                      <button type="button" onClick={() => onOpen(item.id)} className="text-left text-text underline-offset-4 transition-colors hover:text-accent hover:underline">
                        {item.report ? describeProduct(item.report.claims) : "Listing not checked"}
                      </button>
                    </td>
                    <td className="px-4 py-2.5">
                      {item.report ? <VerdictBadge verdict={item.report.verdict} size="sm" /> : <span className="text-muted">{item.error}</span>}
                    </td>
                    <td className="px-4 py-2.5">{item.report && <RoutingLabel routing={item.report.routing} />}</td>
                    <td className="px-4 py-2.5 font-mono tabular-nums text-muted">{item.report ? item.report.not_assessed.length : ""}</td>
                  </motion.tr>
                ))}
              </motion.tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="surface px-4 py-6 text-sm leading-6 text-muted">
          {running
            ? "Running every listing. With a live model this takes a while."
            : canRun
              ? "No batch has run yet. Run the batch to see the summary table."
              : "The API is offline, so a batch cannot run."}
        </p>
      )}
    </section>
  );
}
