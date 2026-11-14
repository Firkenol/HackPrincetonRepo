# Progress

Read this first. Update it before stopping. Phases are the build order in SPEC.md.

## Phases

- [x] **1. Check functions and constants file with unit tests.** Done in commit `02da030` (contract frozen in `64ae171`).
- [ ] **2. deepagents agent with tools, text input from the command line.** Built and tested with a scripted fake model on branch `phase-2-agent`. Still open: the live run and the `claimcheck.run_listing` hook (see below).
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

1. **`claimcheck.run_listing` still raises `NotImplementedError`.** The API imports that one. Wiring it to `agent.run_listing` means editing `backend/claimcheck/pipeline.py` and removing `test_run_listing_is_reserved_for_phase_2` from `backend/tests/test_contract.py`. Both are outside the Phase 2 scope, so they wait for the owner's decision.
2. **Live acceptance not run.** No model key is set. SPEC's Phase 2 acceptance (fixtures 1, 2, 6 to 9 end to end on a real model, Bedrock for the Amazon track) is covered by `agent/tests/test_live.py`, which skips until `MODEL_PROVIDER` and `MODEL_ID` are set. The prompt and skills have not been tried on a real model yet.
3. **Agent folder.** CONTRACT.md says `backend/claimcheck/agent/`; the agent is in `backend/agent/` as instructed for this phase. CONTRACT.md needs a one-line update.
4. **Events are all labelled `orchestrator`.** The three subagent names arrive in Phase 4.
5. **`error-event-replay` branch** (commit `0cda500`) is local only: not merged, not pushed. The agent follows the same convention (error event, then `None`).
6. `backend/pyproject.toml` `testpaths` now includes `agent/tests`. `packs-docs` edits the same line, so expect a small merge conflict.

## Environment notes

- Python 3.14 works. No 3.12 environment was needed.
- Windows Smart App Control blocked the native builds of `xxhash` 4.1.0 and `ormsgpack` 1.13.1. `requirements.txt` pins `xxhash` 4.0.2 and `ormsgpack` 1.13.0, which load.
