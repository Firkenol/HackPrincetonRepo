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

1. **Live acceptance blocked by the AWS account, not by code.** Credentials in the local `.env` (git-ignored) authenticate, and `langchain-aws` 1.9.3 is installed and pinned. On 2026-11-14 a one-word test call was sent to 30 vision-capable models and inference profiles in us-east-2 and none could be invoked:
   - Amazon Nova (Pro, Lite, 2 Lite), Claude Haiku 4.5, Pixtral Large, Llama 4, and the on-demand open models: `ThrottlingException: Too many tokens per day` on the first call, which means the account's daily token quota for them is zero.
   - Claude Sonnet 4.6: "Model use case details have not been submitted for this account."
   - Claude 5 family, OpenAI, xAI, Kimi K3: "not available for this account."
   `MODEL_ID` is left empty in `.env` so the live tests skip instead of failing. Once the account has quota, the suggested model is `us.anthropic.claude-haiku-4-5-20251001-v1:0` (vision, tool calling), with `us.amazon.nova-pro-v1:0` as the Amazon-native alternative. Any other provider works by changing `MODEL_PROVIDER`, `MODEL_ID` and the key.
2. **Events are all labelled `orchestrator`.** The three subagent names arrive in Phase 4.
3. `backend/pyproject.toml` `testpaths` now includes `agent/tests`. `packs-docs` edits the same line, so expect a small merge conflict.
4. The `api` and `web` branches are not merged; nothing on main depends on them.

Closed on 2026-11-14: `error-event-replay` rebased and merged (`684e4e6`); `run_listing` return type is `EvidenceReport | None`, recorded under "Contract changes" in CONTRACT.md.

## Environment notes

- Python 3.14 works. No 3.12 environment was needed.
- Windows Smart App Control blocked the native builds of `xxhash` 4.1.0 and `ormsgpack` 1.13.1. `requirements.txt` pins `xxhash` 4.0.2 and `ormsgpack` 1.13.0, which load.
- boto3 reads the region from `AWS_DEFAULT_REGION`; `langchain-aws` also accepts `AWS_REGION`, which is what `.env.example` uses.
- The AWS key in use belongs to the account root user. An IAM user limited to Bedrock would be safer.
