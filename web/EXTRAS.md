# Web extras

Added on branch `web-extras`, inside `web/` only. The only pre-existing file edited is
`src/components/TracePanel.tsx` (its interface is unchanged). Everything else is new.

## Routes

| Route | File | What it is |
|---|---|---|
| `/` | `src/app/page.tsx` | The console (unchanged). |
| `/how-it-works` | `src/app/how-it-works/page.tsx` → `src/components/HowItWorks.tsx` | Three steps, six checks, four verdicts, three routing values, citation note. Links to `/` and `/report/fixture_01`. |
| `/report/[id]` | `src/app/report/[id]/page.tsx` → `src/components/PrintReport.tsx` | Print-friendly evidence report for a bundled sample (`src/samples`). Prerendered for every sample id; unknown ids 404. Links to `/` and `/how-it-works`, has its own "Print report" button. |

There is no navigation component. To wire these into the console header, add two links
next to the title in `Console.tsx`:

```tsx
import Link from "next/link";
<Link href="/how-it-works">How it works</Link>
```

and, in `VerdictCard.tsx`, a link to `/report/${listing.key}` for listings whose key is a
sample id (`fixture_NN`). Live checks have no bundled report, so for them the print page
would need the report passed in; the `PrintReport` component already takes a `BatchItem`,
so a client page that reads the report from state can reuse it as is.

## Shared agent colours

`src/lib/agents.ts` holds the four agents' labels, colours and Lucide icons, plus the
verdict and check-status colours as hex. The trace, the How it works page and the print
page all read from it. Use `AGENTS[name].hex` wherever an agent needs a colour.

## Trace panel

`TracePanel({ events, running })` and `traceLine(event)` are unchanged in signature, and
each row still carries `data-testid="trace-line"` with exactly agent + kind + text as its
text content. New, all derived from the events only:

- pipeline strip (`data-testid="pipeline-agent"`, `data-stage` idle | active | done)
- check chips (`data-testid="check-chip"`, `data-check-id`, `data-status`)
- expandable rows (`aria-expanded`; details in `data-testid="trace-details"`)
- agent filters (`data-testid="trace-filter"`, `aria-pressed`)
- live indicator (`trace-live`), jump-to-latest (`trace-jump`), verdict reveal (`trace-verdict`)

Exported helpers `checkChips(events)` and `pipeline(events, running)` are pure and tested.

## Loading, empty and error states

All in `src/components/states/`. None of them shows a number that was not given to it.

| Component | Drop it in |
|---|---|
| `MetricsSkeleton` | `Console.tsx`, in place of `<MetricsBar>` while `stats === null` and `source === null`. |
| `FeedSkeleton` | `AuditFeed.tsx` (or around it in `Console.tsx`) before the first batch or check arrives. |
| `VerdictCardSkeleton` | `Console.tsx`, in place of `<VerdictCard>` while `selected.running` and no events have arrived yet. |
| `MathSkeleton` | `Console.tsx`, in place of the "The math appears here" paragraph while `selected.running`. |
| `TraceSkeleton` | Anywhere a trace is expected but `events` is still empty and `running` is true. |
| `BatchTableSkeleton` | `BatchView.tsx`, in place of the table while `running` is true. |
| `Spinner` | Short waits: a button that is submitting, a row that is refreshing. `<Spinner label="Checking the listing" />`. |
| `ErrorState` | `VerdictCard.tsx`, in place of the `listing-error` block: `<ErrorState kind="offline" detail={listing.error} onRetry={...} />`. Kinds: `offline`, `failed`, `rejected`. `title` and `next` override the defaults. |
| `EmptyState` | `AuditFeed.tsx` when there are no listings; `BatchView.tsx` when no batch has run (`action` takes the Run batch button). |

Each skeleton is `role="status" aria-busy="true"` with a screen-reader label; `ErrorState`
is `role="alert"`. Motion: skeletons pulse with Tailwind's `animate-pulse` and stop under
`prefers-reduced-motion` (`motion-reduce:animate-none`); the pages wrap themselves in
`<MotionConfig reducedMotion="user">` like the console does.

## Checks run before each commit

```
npm test && npx tsc --noEmit && npx eslint && npm run build
```
