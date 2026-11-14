---
name: assembling-evidence-reports
description: Use when asked to assemble the evidence report after the checks have run. Covers the one tool to call, what the report contains, what each verdict and routing value means, and how to word the reply.
---

# Assembling the evidence report

Call `assemble_report` once. It takes no arguments. It builds the whole report in
Python from the recorded claims and the check results: the claims and where each was
found, all six checks with their working, the verdict, the routing, the assumptions
and the list of checks that were not assessed.

You add nothing to the report. Every number in it comes from a tool.

## What the tool returns

| Field | Meaning |
|---|---|
| `verdict` | One of the four verdicts below. |
| `verdict_reason` | Why, in one or two sentences. |
| `routing` | One of the three routing values below. |
| `routing_reason` | Why. |
| `not_assessed` | One line per check that did not run, with the reason. |

## Verdicts

| Verdict | Meaning |
|---|---|
| `Impossible` | A hard physical bound is violated. |
| `Flag` | A contradiction or unusual claim. |
| `No red flags` | Claims were tested and are plausible. This is not a confirmation. |
| `No checkable claim` | Nothing numeric or testable was stated. |

## Routing

| Routing | When |
|---|---|
| `auto-resolvable` | `Impossible`, with the inputs of the violated check read at high confidence. |
| `needs human review` | Any `Flag`, a low-confidence claim, or a numeric claim that could not be tested. |
| `no action needed` | `No red flags` or `No checkable claim`, with every claim read at high confidence. |

## Your reply

After the tool returns, reply with one sentence: the report is ready. If you repeat the
verdict or routing, copy the strings exactly as the tool returned them.

- Do not add, round, restate or calculate any number.
- Do not change or soften the verdict or routing, and do not give your own.
- Never write "verified", "genuine", "fake" or "counterfeit".
- Speak about the claim, never about who is selling the product. Never name a seller,
  store or brand.
- A check that was not assessed is normal. It is not a problem with the listing.

## If the tool returns an error

"No claims are recorded yet" means the listing was not read. Say so in one sentence.
Do not try to build a report yourself.
