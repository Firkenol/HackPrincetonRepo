# OffSpec specification

This file holds the original build prompt, word for word, followed by the decisions made since. Where a decision in the "Amendments" section differs from the original text, the amendment wins.

## Original build prompt

Build "ClaimCheck" (rename freely): a triage tool that checks whether a battery listing's own claims are physically possible and shows the math. It is a HackPrinceton Fall 2026 project for a team of 4 with about 30 hours left, so prefer the simple working version at every step and keep module boundaries clean enough for four people to work in parallel. Public GitHub repo: no secrets committed, all keys from environment variables, provide .env.example.

PRIZE TARGETS
- LangChain track: the agent core must genuinely be the deepagents library (create_deep_agent) with real subagents and skills.
- Amazon track: practical AI, judged by an Amazon engineer. Model calls go through Amazon Bedrock.

POSITIONING
Marketplaces already combine automated detection with human review. This tool settles the clear-cut cases a calculation can decide and produces an evidence report a reviewer can verify in seconds, so experts spend time on ambiguous cases. It complements review-authenticity checkers. Input is a screenshot or pasted text. It never scrapes or wraps any marketplace site.

CHECKS (batteries only: loose cells, hobby lithium packs, power banks)
1. Label consistency: stated Wh must equal V x Ah, within a small rounding tolerance.
2. Form-factor bound: a size code (18650, 21700, AA, AAA) fixes volume, which caps energy.
3. Dimension bound: stated dimensions give volume; Wh/L must be under the best-case ceiling for the chemistry.
4. Weight bound: Wh/kg must be under the best-case ceiling for the chemistry.
5. Label contradiction: title disagrees with codes printed on the product in the photo (title says "alkaline", cells read R6/R03, which are zinc-carbon; alkaline is LR6/LR03).
6. Chemistry mismatch: a claim unusual for the stated chemistry (10-year shelf life on carbon-zinc). Soft flag only.

VERDICTS, exactly these four strings
- "Impossible": a hard physical bound is violated. Show the arithmetic.
- "Flag": a contradiction or unusual claim. Explain why.
- "No red flags": claims checked and plausible. Never say "verified".
- "No checkable claim": nothing numeric or testable was stated.
Each result carries routing: "auto-resolvable" (hard bound violated, calculation reproducible) or "needs human review" (soft flags, missing data, low extraction confidence). Routing for passing listings is not yet decided: default to "needs human review" and raise it in your Phase 1 report.

EVIDENCE REPORT (the main output)
Per listing, a structured object: claims extracted and where each was found; every check run with inputs, formula, result, and the constant used with its source; verdict and routing; assumptions and anything not assessed. A person with a calculator must be able to reproduce it. Shown as an on-screen card and downloadable as JSON.

HARD RULES
- All arithmetic happens in plain Python functions called as tools. The model never does math.
- Physical constants live in one file, each with a source citation. Use conservative best-case ceilings so honest products never fail. Look up real sources; never invent a value. If you cannot find a source, stop and tell me.
- Verdicts are about the claim, never the seller. Never output, store or display seller or store names.
- Treat listed package weight and package dimensions as unreliable. If they look like placeholders or describe the shipping box, say so and rely on other checks.
- Do not flag a rechargeable or power bank because usable output is below labeled cell capacity; conversion loss is normal.
- Neutral, factual wording. Nothing implying any marketplace is full of fakes.

ARCHITECTURE
- Python backend. Before writing any agent code, read the current deepagents and langchain-aws documentation and follow their present APIs, not memory. Pin every dependency version.
- Model: ChatBedrockConverse from langchain-aws, vision-capable, model ID from an environment variable. One environment variable swaps the provider.
- Tools: extract claims from image or text into a structured object with per-field confidence; look up form-factor dimensions; the six checks; assemble the evidence report.
- Subagents, each with its own skills: listing reader, physics checker, report writer.
- A skills/ folder of SKILL.md files loaded by the agent.
- LangSmith tracing via environment variables.
- API: FastAPI, streaming agent and tool-call events to the browser.
- Frontend: Next.js, TypeScript, Tailwind, Framer Motion. Make it polished: animated upload and drag-drop, tool-call trace streaming in live, verdict card that reveals the arithmetic step by step, clear routing label, JSON download. Batch mode runs a folder of screenshots and shows an animated summary table with counts of auto-resolvable versus routed to a human. Motion must never slow the demo or hide the numbers.

TEST FIXTURES (automated, with expected verdicts)
1. 18650 Li-ion, 12,000 mAh at 3.7 V, package weight 0.600 kg in a 15 cm cube -> Impossible, auto-resolvable (form-factor bound; weight noted as placeholder).
2. AA Ni-MH, 700 mAh, 1.2 V -> No red flags.
3. Pack titled "Alkaline"; cells in photo read R6/R03 and "Heavy Duty" -> Flag, needs human review.
4. Carbon AA/AAA pack claiming 10-year shelf life, no capacity -> Flag (soft), needs human review.
5. Carbon AA/AAA "heavy duty" multipack, no numeric claims -> No checkable claim.
6. 2S LiPo, 7.4 V, 6200 mAh, label 45.88 Wh, 139.5 x 47.5 x 26 mm, 315 g -> No red flags.
7. 3S LiPo, 11.1 V, 2200 mAh, label 24.42 Wh, 106 x 33 x 23 mm, 179 g -> No red flags.
8. 2S LiPo, 7.4 V, 5200 mAh, label 38.48 Wh, 25 x 47 x 139 mm, 307 g -> No red flags.
9. 2S LiPo, 7.4 V, 5200 mAh, label 38.48 Wh, weight and dimensions not visible -> No red flags on label consistency; weight and dimension checks reported as not assessed.

BUILD ORDER
Each phase ends in something runnable. After each phase, stop, report what works, what you assumed and what is open, and wait for my go-ahead.
1. Check functions and constants file with unit tests. Accept: the arithmetic for all nine fixtures gives the expected verdict from hand-entered claims; every constant has a citation.
2. deepagents agent with tools, text input from the command line. Accept: text versions of fixtures 1, 2 and 6 to 9 pass end to end on Bedrock; no math in model output.
3. Image input. Accept: screenshots I place in fixtures/ extract correctly with per-field confidence; fixture 3 is caught from the photo; low confidence routes to human review.
4. Subagents, skills, evidence report. Accept: all nine fixtures pass as automated tests; report JSON validates against a schema; LangSmith shows subagent and tool calls.
5. Web UI and batch mode. Accept: upload and paste work, the trace streams, JSON downloads, batch over fixtures/ shows the summary table, no seller name appears anywhere.
6. README and demo script. Accept: a clean clone runs from the README alone.

DEMO (must run smoothly in about 90 seconds)
Write DEMO.md with these steps and one talking point each:
1. Fixture 1: Impossible, with arithmetic and evidence report.
2. Fixture 6: an honest listing from a major retailer passing.
3. Fixture 3: contradiction caught from the photo.
4. Fixture 5: "No checkable claim"; the tool stays quiet when it has nothing to test.
5. Batch mode over all fixtures: auto-resolvable versus routed to a human.
6. A fresh screenshot supplied live through the same upload path.
Include a note that screenshots were captured in advance with seller names blurred.

README
List every framework, API and library used, setup steps, environment variables, known limits, and what is live versus staged in the demo.

OUT OF SCOPE
Scraping, browser extensions, fine-tuning, user accounts, seller ratings, any category beyond batteries.

## Amendments

### 2026-11-14, after the Phase 1 report

1. **Routing has three values.** "no action needed" is added for "No red flags" and "No checkable claim" results where extraction confidence is high. "needs human review" is now only for flags, missing data and low extraction confidence. "auto-resolvable" is unchanged. This replaces the sentence in the original that left routing for passing listings undecided.
2. **NiMH ceilings are soft.** A NiMH claim above the volume or weight ceiling gives "Flag", not "Impossible", until those ceilings have a primary source with comfortable headroom. Honest products must never fail.
3. **Check 1 stays a flag.** A label where Wh does not equal V x Ah gives "Flag", not "Impossible".
4. **Implied-voltage variant of check 1.** When Wh and capacity are stated but no usable voltage is (typical of power banks), Wh ÷ Ah must be a nominal battery voltage for the chemistry. Soft flag only.
5. **The contract is frozen.** CONTRACT.md describes the data models, stream events and the `run_listing` entry point. Changes need the project owner's approval.

Resulting routing for the nine fixtures: fixture 1 is auto-resolvable; fixtures 3 and 4 need human review; fixtures 2, 5, 6, 7, 8 and 9 need no action.

### How two phrases in amendment 1 are implemented

- **High extraction confidence** means every extracted claim has confidence of at least 0.8 (`MIN_CONFIDENCE` in `backend/claimcheck/policy.py`).
- **Missing data** means the listing states a capacity, energy or shelf-life claim but no check could test it, for example because only package weight is given or no ceiling is on file for the chemistry. A check that did not run because the listing simply says nothing about that property does not count as missing data.

### 2026-11-14, categories beyond batteries

Approved by the project owner. This replaces "any category beyond batteries" in the
original "Out of scope" list for the three categories below. Everything else in the
original text still applies to them: arithmetic in Python, cited constants, the four
verdicts, the three routings, no seller names, package dimensions set aside.

1. **Three categories are added as check packs** in `backend/packs/`, each with its own
   claims model, constants and checks, wired into the agent, the API and the console.
2. **Projectors.** Pixel count of the resolution named in the headline, divided by the
   native pixel count the listing states. Above 1 is a "Flag", never "Impossible": a
   projector can accept a 4K input signal and show it at a lower native resolution.
3. **Magnifying glasses.** Focal length f = 250 mm / claimed power. A simple lens cannot
   be wider than 2 x f (symmetric lens, index 1.5). A listed diameter above 2 x f but
   within twice that limit is a "Flag"; beyond it, "Impossible". The factor of two is a
   team margin for denser glass and for the other convention for magnifying power. A
   Fresnel or sheet lens is not assessed.
4. **Monoculars.** The objective diameter of an "AxB" figure cannot exceed the listed
   body width (the second-longest side), with a 3% rounding tolerance. The owner
   decided this is a "Flag", not "Impossible": listed dimensions are often wrong, and
   a wrong figure feeding a hard result would be worse than a person's look. A
   headline figure that differs from an "actual" figure in the fine print is also a
   "Flag", as for a battery label that contradicts itself.
5. **Missing data.** A stated claim that cannot be tested gives "No checkable claim"
   routed to "needs human review", as amendment 1 already defines.
6. **The contract change** is recorded in CONTRACT.md: `PackEvidenceReport` is added and
   a run can end with either report type.

### 2026-11-14, name

The product is called **OffSpec**. The original build prompt above says "ClaimCheck (rename freely)" and is kept word for word; an earlier console branch used "Carnot". Display names, API metadata, the `OFFSPEC_REPLAY` and `OFFSPEC_FIXTURES_DIR` variables and the `X-OffSpec-Mode` header use the new name (the old `CARNOT_*` variable names are still honoured). The Python import package stays `claimcheck`: it is named in the frozen contract, and renaming it is the project owner's call.
