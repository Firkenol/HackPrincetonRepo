# Progress

Read this first. Update it before stopping. Phases are the build order in SPEC.md.

## Phases

- [x] **1. Check functions and constants file with unit tests.** Done in commit `02da030` (contract frozen in `64ae171`).
- [x] **2. deepagents agent with tools, text input from the command line.** Merged to main on 2026-11-14 (branch `phase-2-agent`). Passes with a scripted fake model; the live run on a real model is still open (see below).
- [ ] **3. Image input.** Built and tested with the scripted model on branch `phase-3-image` (not merged). Open: live extraction from real screenshots (see below).
- [ ] **4. Subagents, skills, evidence report.** Built and tested with the scripted model on branch `phase-4-subagents` (not merged). Open: a live run, and LangSmith showing the subagent and tool calls.
- [ ] **5. Web UI and batch mode.**
- [ ] **6. README and demo script.**

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
