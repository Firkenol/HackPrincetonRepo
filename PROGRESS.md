# Progress

Read this first. Update it before stopping. Phases are the build order in SPEC.md.

## Phases

- [x] **1. Check functions and constants file with unit tests.** Done in commit `02da030` (contract frozen in `64ae171`).
- [x] **2. deepagents agent with tools, text input from the command line.** Merged to main on 2026-11-14 (branch `phase-2-agent`). Passes with a scripted fake model; the live run on a real model is still open (see below).
- [ ] **3. Image input.** Built and tested with the scripted model on branch `phase-3-image` (not merged). Open: live extraction from real screenshots (see below).
- [ ] **4. Subagents, skills, evidence report.** Built and tested with the scripted model on branch `phase-4-subagents` (not merged). Open: a live run, and LangSmith showing the subagent and tool calls.
- [ ] **5. Web UI and batch mode.** Built on branch `console` (not merged) as the Carnot console: FastAPI in `backend/api/`, Next.js in `web/`. Tested in sample data mode and with the scripted model. Open: a live run, screenshots in `fixtures/`.
- [ ] **6. README and demo script.** `README.md` is written (setup, both servers, modes, limits). `DEMO.md` is not written.

## Phase 2 status (2026-11-14)

Done:

- `backend/agent/`: a `create_deep_agent` agent (deepagents 0.7.38, LangChain 1.5.0). Tools: `record_claims`, `lookup_form_factor`, the six `check_*` functions, `assemble_report`. The check tools take no arguments and run the Phase 1 functions on the recorded claims. The report always comes from `claimcheck.verdict.evaluate`; no text written by the model reaches an event or the report.
- `agent.run_listing(image_or_text)` yields the contract's stream events and returns the report. On failure the last event is `error` and the return value is `None`.
- Model from `MODEL_PROVIDER` and `MODEL_ID` through `init_chat_model`. No provider is hard-coded.
- `backend/skills/`: `reading-battery-listings` and `running-claim-checks`, loaded read-only by the agent.
- Command line: `python -m agent "listing text"` from `backend/`.
- Tests in `backend/agent/tests/` use a scripted fake chat model (no network). Text versions of fixtures 1, 2, 6, 7, 8 and 9 give the expected verdict and routing and match `fixtures/expected/` exactly.

Open:

1. **Live acceptance blocked by the AWS account, not by code.** Credentials in the local `.env` (git-ignored) authenticate, and `langchain-aws` 1.9.3 is installed and pinned. On 2026-11-14 a one-word test call was sent to 30 vision-capable models and inference profiles in us-east-2 and none could be invoked:
   - Amazon Nova (Pro, Lite, 2 Lite), Claude Haiku 4.5, Pixtral Large, Llama 4, and the on-demand open models: `ThrottlingException: Too many tokens per day` on the first call, which means the account's daily token quota for them is zero.
   - Claude Sonnet 4.6: "Model use case details have not been submitted for this account."
   - Claude 5 family, OpenAI, xAI, Kimi K3: "not available for this account."
   `MODEL_ID` is left empty in `.env` so the live tests skip instead of failing. Once the account has quota, the suggested model is `us.anthropic.claude-haiku-4-5-20251001-v1:0` (vision, tool calling), with `us.amazon.nova-pro-v1:0` as the Amazon-native alternative. Any other provider works by changing `MODEL_PROVIDER`, `MODEL_ID` and the key.
2. **Events are all labelled `orchestrator`.** The three subagent names arrive in Phase 4.
3. `backend/pyproject.toml` `testpaths` now includes `agent/tests`. `packs-docs` edits the same line, so expect a small merge conflict.
4. The `api` and `web` branches are not merged; nothing on main depends on them.

Closed on 2026-11-14: `error-event-replay` rebased and merged (`684e4e6`); `run_listing` return type is `EvidenceReport | None`, recorded under "Contract changes" in CONTRACT.md.

## Phase 3 status (2026-11-14, branch `phase-3-image`)

Done:

- `run_listing` accepts `bytes` or a `Path`. The image type is taken from the bytes (PNG, JPEG, WebP), the limit is 3.5 MB, and the picture goes to the model as a LangChain standard image block. Command line: `python -m agent --image screenshot.png`.
- `record_claims` now takes a `ListingExtraction` (`backend/agent/extraction.py`): the same claims as the contract's `Claims`, but each value carries the unit shown (mAh or Ah, g or kg or oz or lb, mm or cm or in, and so on) and `found_in` and `confidence` are required for every claim. The tool converts in Python (`backend/agent/units.py`) and stores a contract `Claims`. The contract models are unchanged.
- Codes and grade wording printed on the product go into `printed_codes` and `printed_terms` with `found_in: "product photo"`. No field exists for a seller, store or brand name, and unknown fields are rejected.
- Low confidence (below 0.8) routes to a person, through the Phase 1 routing policy.
- Tests in `agent/tests/test_image.py` (scripted model): fixtures 3, 4 and 5 from an image, image block wiring, confidence routing, unit conversion, bad images.
- Live tests in `agent/tests/test_live.py` cover all nine fixtures from screenshots, with an extra test that fixture 3's printed codes are read. They skip without a model, and each fixture skips without its screenshot.

Open:

1. **No screenshots yet.** Live image tests look for `fixtures/fixture_NN.png` (or `.jpg`, `.jpeg`, `.webp`), seller names blurred. None are in the repo.
2. **No live run yet**, for the same account reason as Phase 2. Extraction quality on real screenshots, and whether 0.8 is the right confidence threshold, are untested.
3. **Conversion factors live in `backend/agent/units.py`**, not in `claimcheck/constants.py`. They are exact definitions (SI prefixes, inch, pound), cited in the module docstring, and `backend/claimcheck/` was closed to changes in this phase. Move them if the owner prefers one file.
4. Images are not resized. A screenshot over 3.5 MB is refused with a clear message.

## Phase 4 status (2026-11-14, branch `phase-4-subagents`)

Done:

- The agent is an orchestrator with three deepagents subagents, called through the `task` tool: `listing-reader` (only `record_claims`), `physics-checker` (the six check tools and `lookup_form_factor`), `report-writer` (only `assemble_report`). The orchestrator has none of these tools. No subagent can delegate.
- Each subagent has its own system prompt (`backend/agent/prompts.py`) and its own skills folder: `backend/skills/listing-reader/reading-battery-listings/`, `backend/skills/physics-checker/running-claim-checks/`, `backend/skills/report-writer/assembling-evidence-reports/`.
- Stream events carry the agent name. Each delegation shows as a `task` tool call by the orchestrator followed by an `agent_step` from the subagent.
- All nine fixtures pass through `run_listing()` with the scripted model, from text and from an image (`agent/tests/test_fixtures_end_to_end.py`). Text versions of fixtures 3, 4 and 5 were added. Every report matches its file in `fixtures/expected/` and round-trips strictly through the contract models.
- Hard-rule tests in `agent/tests/test_hard_rules.py`: only the four verdicts and three routings appear; "verified" never appears; seller and store names; low confidence routes to a person; a check that raises ends with an `error` event and `None`.
- Test count: 365 passed, 19 skipped (the skips are the live-model tests).

Open:

1. **No live run.** Same account reason as Phase 2. The subagent prompts are untested on a real model, and the LangSmith part of the acceptance line is not checked.
2. **A seller name inside a free-text field cannot be ruled out mechanically.** There is no seller, store or brand field, unknown fields are rejected at every level, the orchestrator never sees the listing, and no model prose reaches an event. What remains is `quote`, `found_in` and the text values (`form_factors`, `printed_codes`, `printed_terms`): a model that ignored its prompt could put a name there. Only the prompt and the skill guard this.
3. **CONTRACT.md says "one folder per skill" under `backend/skills/`.** Skills now sit one level deeper, grouped by subagent, because deepagents gives a subagent a folder of skills. CONTRACT.md was not edited; that row needs a one-line update by the owner.
4. The `task` tool also offers deepagents' built-in `general-purpose` subagent (see decisions).

## Console status (2026-11-14, branch `console`, created from `phase-4-subagents`)

The product is now called Carnot. The engine (`claimcheck`, `agent`, `skills`) is unchanged on this branch: no check, rule or constant was added or altered.

Done:

- **API** (`backend/api/`): `POST /api/verify-listing` (image, text or sample id; streams the contract's events), `POST /api/batch` (every listing in `fixtures/`, reports and counts), `GET /api/dashboard-stats` (counts from the latest batch run, null before one), plus `/api/samples`, `/api/fixtures/{name}`, `/api/health`.
- **Replay mode** when `MODEL_PROVIDER` or `MODEL_ID` is empty, or `CARNOT_REPLAY=1`: serves the reports in `fixtures/expected/`, and every response is marked (`mode`, `sample_data`, the `X-Carnot-Mode` header, a `meta` frame at the start of a stream).
- **Fixture listing texts are files**: `fixtures/fixture_01.txt` to `fixture_09.txt`, the same text the agent tests use (a test compares them).
- **Web console** (`web/`): metrics bar, audit feed, verdict card with the listing beside the verdict badge and routing label, "Show the math" (inputs, formula, steps, constants with sources, not-assessed reasons), paste and upload with drag and drop, live trace, JSON download, batch view with a summary table and a routing chart. Falls back to bundled sample reports when the API is unreachable, labelled.
- Both servers were started and the console was checked in a browser in sample data mode: the nine fixtures, a pasted fixture streaming its trace, and the batch view.
- Tests: backend 423 passed, 19 skipped (58 of the passes are for the API). Web 69 passed; `tsc`, `eslint` and `next build` are clean.

Open:

1. **No live run**, for the same account reason as before. Live mode is tested only with the scripted model behind the API.
2. **No screenshots in `fixtures/`.** The batch runs the text versions. A screenshot named `fixture_NN.png` takes the place of the text file for that fixture. Image upload in the browser was not tried by hand; it is covered by API and client tests.
3. **`DEMO.md` is not written.**
4. **Dashboard counts are kept in memory** and reset when the API restarts.
5. **The listing pane shows the input as submitted**, so a seller name in a pasted listing or an unblurred screenshot is visible there, to the person who submitted it. Nothing else on screen can show one.
6. `readme.txt` at the repo root is the original placeholder and was left alone; `README.md` is the real one.
7. `npm audit` reports 7 moderate advisories in the Next.js toolchain as scaffolded. Not changed, to keep the versions the scaffold chose.
8. On Windows, `npm test` must be started from a path with an upper-case drive letter (see README).

## Check packs status (2026-11-14, branch `console`, with `packs-docs` merged in, not committed)

Three categories beyond batteries, approved by the owner (see the last amendment in SPEC.md and the top row of "Contract changes" in CONTRACT.md).

Done:

- **`packs-docs` is merged into the working tree of `console`.** The merge is not committed: the one conflict (`backend/pyproject.toml` `testpaths`) is resolved in the file, and `git status` still shows the merge in progress.
- **Three packs** in `backend/packs/`, each with `models.py`, `constants.py`, `checks.py`: `projector_resolution` (flag at most), `magnifier_lens` (flag between 1x and 2x the limit, hard above), `monocular_optics` (objective against body width, and headline against fine print; both flags). `packs/registry.py` lists them.
- **Contract change** (additive): `PackEvidenceReport` in `claimcheck/models.py`; `final_report.report` and `run_listing` can carry either report; `replay_pack_claims` in `pipeline.py`. The battery models, the six checks and their expected reports are unchanged.
- **Agent**: the listing reader has one record tool per pack beside `record_claims`, and the tool it calls decides the category. The physics checker has `list_checks`, which names the checks for the recorded category, and the four pack check tools. `assemble_report` builds the pack's report. New skill `reading-optics-listings`; the checker and writer skills are updated.
- **API**: pack fixtures (`fixtures/pack_<pack>_<case>.txt` and `expected/…json`) are listed, replayed and batched beside the nine battery fixtures.
- **Web**: a report may carry `pack`; product descriptions for the three categories; the bundled samples are the nine battery fixtures plus nine pack fixtures.
- **Fixtures**: three per pack (trips the rule, honest, missing data), as hand-entered claims in `packs/fixtures_data.py`, with listing text and expected reports.
- Tests: backend 601 passed without the live tests (was 423 on this branch before the merge and the packs). Web 133 passed; `tsc`, `eslint` and `next build` are clean.
- One live run from the command line: the projector fixture went through `record_projector_claims`, `list_checks` and `check_native_resolution` on the configured model and gave Flag, needs human review.

Open, for the physics teammate:

1. **Magnifier: the refractive index of 1.5 has no citation.** It is shown in every report as an assumption, not as a constant. The only source found (OpenStax) works its example with 1.55. See the TODO in `packs/magnifier_lens/constants.py`.
2. **Magnifier: the 2x margin before a hard result is a team choice.** It covers glass up to index 2.0. Confirm it also covers the M = 250/f + 1 convention and thick lenses.
3. **Magnifier: the "no wider than 2 x f" rule is a derivation** (lens maker's equation plus geometry), not a cited value. Confirm it.
4. **Projector: the resolution definitions cite Wikipedia at fixed revisions.** The primary documents (ITU-R BT.2020, BT.709, SMPTE ST 296) were not read. Replace the citations, and read the quotes against the pages: they were fetched by a tool, not by a person.
5. **Monocular: the 3% rounding tolerance is a team choice**, copied from the battery label check. The check uses no physical constant.
6. ~~Monocular hard result from listed dimensions~~ Decided by the owner on 2026-11-14: a flag, because listed dimensions can be wrong.

Open, other:

7. `power_budget` (from `packs-docs`) has checks and tests but is not in the registry, so the agent, API and console do not use it.
8. The local `.env` now has a model configured, so plain `pytest` runs the live tests against it. Use `pytest -m "not live"` to skip them.
9. No screenshots exist for the pack fixtures; they are text only.
10. CLAUDE.md still describes the project as batteries only and was not edited.

## Decisions made while unattended

2026-11-14, Phase 4:

1. **The listing goes to the listing reader directly, not through the orchestrator.** A deepagents subagent only receives the task text its caller writes, so an image could not reach it, and text would be retyped by a model. A small middleware (`ListingMiddleware` in `agent/graph.py`) adds the listing to the reader's model requests. The orchestrator is only told "a listing was submitted as text" or "as an image".
2. **The built-in `general-purpose` subagent is left in place.** Removing it needs a harness profile registered per model provider, which would tie the code to a provider. It has no claim, check or report tools, so it cannot change a result, and the orchestrator prompt says to use only the three subagents.
3. **Delegation events hide model-written text.** A `task` tool call shows only `{"subagent_type": ...}`; its result shows a fixed summary and no data. Calls to deepagents' file tools show no arguments and no result.
4. **The report is still computed by `claimcheck.verdict.evaluate`.** The report writer's tool calls it; if a model skips the checks or the report writer, `run_listing` computes the same report itself.
5. **`record_claims` rejects a claim whose `quote`, `found_in` or text value contains "verified"** (`agent/extraction.py`). Otherwise a listing that uses the word could carry it into a report. The model gets an error naming the field and retries.
6. **Text versions of fixtures 3, 4 and 5** include a line giving the print on the cells, as a person pasting the listing might type it.
7. **A check tool that raises ends the run with the generic `error` event.** Nothing was changed to make this so; the tests now pin it.

## Environment notes

- Python 3.14 works. No 3.12 environment was needed.
- Windows Smart App Control blocked the native builds of `xxhash` 4.1.0 and `ormsgpack` 1.13.1. `requirements.txt` pins `xxhash` 4.0.2 and `ormsgpack` 1.13.0, which load.
- boto3 reads the region from `AWS_DEFAULT_REGION`; `langchain-aws` also accepts `AWS_REGION`, which is what `.env.example` uses.
- The AWS key in use belongs to the account root user. An IAM user limited to Bedrock would be safer.

2026-11-14, console:

8. **Branch `console` was created from `phase-4-subagents`**, the newest branch, after its suite passed (365 passed) and it was committed and pushed.
9. **The HTTP transport in CONTRACT.md was replaced** with the routes in the owner's instruction (`/api/verify-listing`, `/api/batch`, `/api/dashboard-stats`) and the frontend folder is `web/`, not `frontend/`. CONTRACT.md is updated with a row under "Contract changes". The frozen models, events and `run_listing` signature were not touched.
10. **In replay mode a listing that is not a fixture is not given a report.** It ends with an `error` event saying it was not checked. Showing a sample verdict for someone's own listing would be a false result. The web app does the same when the API is offline.
11. **Replay mode is decided by `MODEL_PROVIDER` and `MODEL_ID`**, not by looking for a provider key, so the API stays provider-neutral. A configured model with a bad key runs live and ends with the generic error event.
12. **The endpoint is named `verify-listing` as instructed.** The word appears only in that URL. No screen, event or report says "verified"; tests check this on both sides.
13. **The stream starts with a `meta` frame** (mode, sample_data, sample id). It is an extra SSE frame, not a new contract event, so `events.py` is unchanged.
14. **The audit feed and batch table name a listing by a description built from its extracted claims** (for example "18650 lithium-ion battery, 12,000 mAh, 3.7 V"), never by its title.
15. **In sample data mode the web app runs the batch on load**, since it costs nothing, so the console opens with the nine fixtures and real counts. In live mode it does not: the tiles show a dash until someone runs the batch.
16. **Dashboard stats count only the latest batch run**, as instructed. Listings checked one at a time do not change them.
17. **New dependencies**, all pinned: fastapi, uvicorn, python-multipart (backend); next, react, tailwindcss, lucide-react, recharts, framer-motion, vitest, Testing Library, jsdom (web). The scaffold came from `create-next-app` 16.4.6 and its config was kept.
18. **Verdict colours**: Impossible red `#f26d78`, Flag amber `#f2b441`, No red flags green `#4fcf8e`, No checkable claim gray `#9aa4b2`.
