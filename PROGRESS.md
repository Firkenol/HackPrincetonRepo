# Progress

Read this first. Update it before stopping. Phases are the build order in SPEC.md.

## Phases

- [x] **1. Check functions and constants file with unit tests.** Done in commit `02da030` (contract frozen in `64ae171`).
- [x] **2. deepagents agent with tools, text input from the command line.** Merged to main on 2026-11-14 (branch `phase-2-agent`). Passes with a scripted fake model; the live run on a real model is still open (see below).
- [ ] **3. Image input.**
- [ ] **4. Subagents, skills, evidence report.**
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

1. **Live acceptance not run.** SPEC's Phase 2 acceptance (fixtures 1, 2, 6 to 9 end to end on a real model, Bedrock for the Amazon track) is covered by `agent/tests/test_live.py`, which skips until `MODEL_PROVIDER` and `MODEL_ID` are set. A local `.env` (git-ignored) holds an AWS access key id, but the secret access key, region and model id are still missing, and `langchain-aws` is not installed or pinned yet. The prompt and skills have not been tried on a real model.
2. **Return type on failure.** `claimcheck.run_listing` now runs the agent (the import is inside the function so `import claimcheck` stays light). When a run ends in `error` it returns `None`, but the frozen signature still says `EvidenceReport`. Changing the annotation to `EvidenceReport | None` needs the owner's approval.
3. **Events are all labelled `orchestrator`.** The three subagent names arrive in Phase 4.
4. **`error-event-replay` branch** (commit `0cda500`) is local only: not merged, not pushed, waiting for the owner's answer. It makes `replay_claims` end with an `error` event and return `None` when a check raises, and adds a test. It edits `pipeline.py` and `test_contract.py`, which main has since changed, so merging it will need a small conflict fix.
5. `backend/pyproject.toml` `testpaths` now includes `agent/tests`. `packs-docs` edits the same line, so expect a small merge conflict.
6. The `api` and `web` branches are not merged; nothing on main depends on them.

## Environment notes

- Python 3.14 works. No 3.12 environment was needed.
- Windows Smart App Control blocked the native builds of `xxhash` 4.1.0 and `ormsgpack` 1.13.1. `requirements.txt` pins `xxhash` 4.0.2 and `ormsgpack` 1.13.0, which load.
