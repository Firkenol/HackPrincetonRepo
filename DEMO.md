# OffSpec demo script

Voiceover for `demo/offspec_demo.mp4` (2 min 55 s, 1920x1080, silent). Read at an easy
pace; each block is timed to the section on screen. Timestamps are where the section
starts. The footage was recorded in replay mode, so every report shown is one of the
fixtures in `fixtures/expected/`, computed by the same Python checks the live agent calls.

---

**0:00 — Title card**

Online listings make physical claims. A battery that stores twelve thousand milliamp
hours. A projector that is "4K". A magnifying glass that gives you thirty times.
Some of those claims are impossible, and you can prove it with arithmetic.
That is OffSpec.

**0:08 — The console**

This is the console. Paste a listing on the left, or drop a screenshot. Every listing
you check lands in the audit feed, and the bar across the top counts how the last batch
was routed.

**0:14 — Card: Battery**

Let's start with the most common one. An 18650 cell.

**0:19 — Battery listing**

Here is a real-looking listing: an 18650 lithium-ion cell, twelve thousand milliamp
hours, three point seven volts.

A language model reads the listing and records the claims, with the exact quote and
where it found it. It never does the math. Every number goes to a plain Python
function.

The verdict comes back: Impossible, auto-resolvable.

Watch the trace. Three agents. A listing reader, a physics checker, a report writer.
The physics checker calls six checks, one at a time, and each one is a tool call you
can expand.

And this is the part we care most about: show the math. The claim amounts to forty-four
watt-hours. An 18650 can is eighteen and a half millimetres by sixty-five. That volume,
at the highest energy density any lab has measured in a lithium-ion cell, holds about
twenty-three watt-hours. The claim is nearly twice the ceiling. Every constant has a
cited source, and we chose best-case ceilings on purpose so honest products never fail.

Notice the weight and dimensions were not used. They describe the shipping box, not the
cell, and the system says so instead of guessing.

**0:51 — Card: Projector**

It is not only batteries. The same engine runs check packs for other categories.

**0:56 — Projector listing**

A "4K home theater projector". Scroll to the spec table: native resolution 1280 by 720.

The pack compares the headline resolution to the native panel. This is not physically
impossible, it is a marketing claim contradicted by the listing's own numbers, so the
verdict is a Flag, and it is routed to a human. OffSpec never calls something impossible
unless a hard physical bound is violated.

**1:19 — Card: Magnifying glass**

Optics has hard bounds too.

**1:24 — Magnifier listing**

Thirty-times magnification, seventy-five millimetre lens.

Magnifying power is two hundred fifty millimetres divided by focal length, so thirty
times means a focal length of about eight millimetres. A simple lens cannot be wider
than twice its focal length, about seventeen millimetres. This lens is seventy-five.
Even with a two-times margin for denser glass, it is four and a half times over.
Impossible, and the formula, the constants and the assumptions are all on screen.

**1:46 — Card: Monocular**

Most listings are fine, and the system should say so quietly.

**1:51 — Monocular listing**

A twelve-by-fifty monocular. The checks run, nothing is out of bounds. The verdict is
"No red flags", no action needed. We never say "verified". A passing check means the
claim is plausible, not that it is true.

**2:03 — Card: Screenshots**

You do not need to type anything.

**2:08 — Screenshot upload**

Drop a screenshot of the listing. The model reads the picture, records the claims with
confidence scores, and anything read with low confidence is routed to a person instead
of being decided automatically. The checks and the math are exactly the same.

**2:22 — Card: Batch**

And it scales.

**2:26 — Batch run**

Run batch checks every listing in the folder in one pass. Two settled by the
calculation, seven routed to a person, nine needing no action. Each row opens the full
evidence report, and every report downloads as JSON.

**2:46 — End card**

So, to sum up. The model reads, Python computes. Every constant is cited and chosen as
a best-case ceiling. Verdicts are about the claim, never the seller. Batteries,
projectors, magnifying glasses and monoculars today, and a new pack is one folder of
checks and constants.

OffSpec. Every verdict is arithmetic.

---

## Rebuilding the video

The recording and assembly scripts live outside the repo (they need Playwright,
Chromium and a bundled ffmpeg, none of which are project dependencies). To re-record:
start the API in replay mode with `OFFSPEC_REPLAY=1` on a spare port, point a web
dev server at it with `NEXT_PUBLIC_API_URL`, allow that origin with `CORS_ORIGINS`,
then drive it with Playwright's `record_video_dir`.
