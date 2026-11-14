# Carnot

A trust and safety console that checks whether a battery listing's own claims are
physically possible, and shows the math. Paste a listing or upload a screenshot; Carnot
extracts the claims, runs six physical checks in plain Python, and returns an evidence
report a reviewer can reproduce with a calculator.

It reads only what you give it. It never scrapes or wraps a marketplace site, and it
never outputs, stores or displays seller or store names. A verdict is about the claim,
never about who is selling the product.

The four verdicts are exactly `Impossible`, `Flag`, `No red flags` and `No checkable
claim`. Routing is `auto-resolvable`, `needs human review` or `no action needed`.

## What is in the repo

| Folder | What it is |
|---|---|
| `backend/claimcheck/` | The engine: the six checks, the cited constants, the report and event models |
| `backend/agent/` | A deepagents orchestrator with three subagents: listing reader, physics checker, report writer |
| `backend/skills/` | One `SKILL.md` per subagent |
| `backend/api/` | FastAPI server over `run_listing()` |
| `web/` | The Carnot console: Next.js App Router, TypeScript, Tailwind, Lucide, Recharts, Framer Motion |
| `fixtures/` | Nine test listings (`fixture_NN.txt`) and their expected reports (`expected/`) |

`SPEC.md` is the specification, `CONTRACT.md` the interface between the parts, and
`PROGRESS.md` the current state and open items.

## Run it

You need Python 3.11 or newer (tested on 3.14) and Node.js 20 or newer (tested on 24).
Use two terminals.

### 1. API, on port 8000

```
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS and Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn api.app:app --port 8000
```

### 2. Web console, on port 3000

```
cd web
npm install
npm run dev
```

Open http://localhost:3000.

### Sample data mode and live mode

With no model configured, the API runs in **sample data mode**: it serves the reports in
`fixtures/expected/`, and every response and every screen that shows them is labelled
"Sample data". This is the default on a fresh clone and needs no key. In this mode only
the nine fixture listings can be checked; any other listing gets a message saying it was
not checked, never a sample report.

For **live mode**, copy `.env.example` to `.env` in the repo root and set
`MODEL_PROVIDER`, `MODEL_ID` and that provider's credentials. The model must support
tool calling, and vision for screenshots. Restart the API. Set `CARNOT_REPLAY=1` to
force sample data mode even with a model configured.

If the web console cannot reach the API at all, it falls back to sample reports bundled
with the web app and says "Sample data: the API is offline".

## API

| Route | What it does |
|---|---|
| `POST /api/verify-listing` | Form field `image` (a file), `text` or `sample` (a fixture id such as `fixture_01`), exactly one. Streams Server-Sent Events: one `meta` frame, then the contract's events, ending with `final_report` or `error`. |
| `POST /api/batch` | Runs every listing in `fixtures/`. Returns each report and counts per verdict and per routing value. |
| `GET /api/dashboard-stats` | Counts from the latest batch run. Before any run, `has_run` is false and the counts are null. |
| `GET /api/samples` | The fixture listings. |
| `GET /api/health` | Whether the server is in `live` or `replay` mode. |

Every JSON body carries `mode` and `sample_data`, and every response has an
`X-Carnot-Mode` header.

## Tests

```
cd backend
pytest                 # live-model tests skip unless a model is configured

cd web
npm test
npm run lint
npm run build
```

`npm test` also checks that the samples bundled with the web app match `fixtures/`. If
you change a fixture, run `npm run sync-samples` in `web/`.

On Windows, start `npm test` from a path with the drive letter in upper case
(`C:\...`, as PowerShell and cmd give you). Vitest fails with "failed to find the current
suite" when the working directory is spelled `c:\...`, which Git Bash's `cd /c/...`
produces.

## Frameworks and libraries

Backend: Python, pydantic, deepagents, LangChain, LangGraph, FastAPI, uvicorn,
python-multipart, python-dotenv, pytest. Model providers through LangChain's
`init_chat_model`: langchain-aws (Amazon Bedrock), langchain-anthropic,
langchain-google-genai. Optional tracing with LangSmith.

Web: Next.js, React, TypeScript, Tailwind CSS, lucide-react, Recharts, Framer Motion,
IBM Plex Sans and IBM Plex Mono (through `next/font`), Vitest, Testing Library, ESLint.

Every version is pinned in `backend/requirements.txt` and `web/package.json`.

## Known limits

- Batteries only: loose cells, hobby lithium packs and power banks.
- No live model run has been made yet (see `PROGRESS.md`), so extraction quality on
  real screenshots is untested. Everything is tested with a scripted model.
- `fixtures/` has no screenshots yet, so the batch runs the text versions.
- Dashboard counts come from the latest batch run and are kept in memory; they reset
  when the API restarts.
- The listing pane shows the text or screenshot exactly as you submitted it. Blur seller
  names in screenshots before uploading. The audit feed, verdicts, reports and trace are
  built only from extracted claims, which have no seller, store or brand field.
