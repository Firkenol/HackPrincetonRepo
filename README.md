# OffSpec

A trust and safety console that checks whether a product listing's own claims are
physically possible, and shows the math. Paste a listing or upload a screenshot; OffSpec
extracts the claims, runs the physical checks for that kind of product in plain Python,
and returns an evidence report a reviewer can reproduce with a calculator.

| Category | Checks |
|---|---|
| Batteries (loose cells, packs, power banks) | Six: label consistency, form-factor bound, dimension bound, weight bound, label contradiction, chemistry mismatch |
| Projectors | Headline resolution ("4K") against the native pixel count. A flag at most. |
| Magnifying glasses | Claimed power against the lens diameter |
| Monoculars | An "80x100" figure against the listed body width, and against any "actual" figure in the fine print. A flag at most. |

It reads only what you give it. It never scrapes or wraps a marketplace site, and it
never outputs, stores or displays seller or store names. A verdict is about the claim,
never about who is selling the product.

The four verdicts are exactly `Impossible`, `Flag`, `No red flags` and `No checkable
claim`. Routing is `auto-resolvable`, `needs human review` or `no action needed`.

## What is in the repo

| Folder | What it is |
|---|---|
| `backend/claimcheck/` | The engine: the six battery checks, the cited constants, the report and event models. The folder keeps its original import name; it is part of the frozen contract in `CONTRACT.md` |
| `backend/packs/` | Check packs for other categories: projector, magnifying glass, monocular (and power budget, not wired into the agent). Each has its own claims model, cited constants and checks |
| `backend/agent/` | A deepagents orchestrator with three subagents: listing reader, physics checker, report writer |
| `backend/skills/` | One `SKILL.md` per subagent |
| `backend/api/` | FastAPI server over `run_listing()` |
| `web/` | The OffSpec console: Next.js App Router, TypeScript, Tailwind, Lucide, Recharts, Framer Motion |
| `fixtures/` | Twenty battery listings (`fixture_NN.txt`, with screenshots for 8 to 20, see `fixtures/README.md`), the pack listings (`pack_<pack>_<case>.txt`) and their expected reports (`expected/`) |

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
the fixture listings can be checked; any other listing gets a message saying it was
not checked, never a sample report.

For **live mode**, copy `.env.example` to `.env` in the repo root and set
`MODEL_PROVIDER`, `MODEL_ID` and that provider's credentials. The model must support
tool calling, and vision for screenshots. Restart the API. Set `OFFSPEC_REPLAY=1` to
force sample data mode even with a model configured.

If the web console cannot reach the API at all, it falls back to sample reports bundled
with the web app and says "Sample data: the API is offline".

## Deploy

Two services: the API (Python) and the web console (Next.js). Deploy the API first, then
point the web console at it. These steps follow from how the two parts are configured;
they have not been run against a hosting provider from this repo.

**API.** Any host that runs a Python web process (Render, Railway, Fly.io, AWS App
Runner or Elastic Beanstalk). Deploy the whole repository, not only `backend/`: the API
reads `fixtures/` from the repo root and the agent reads `backend/skills/`.

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn api.app:app --host 0.0.0.0 --port $PORT` |
| Python | 3.11 or newer |
| `CORS_ORIGINS` | The web console's URL, for example `https://offspec.example.com` |
| `MODEL_PROVIDER`, `MODEL_ID`, provider credentials | Only for live mode. Leave them unset to serve sample data. Set them as secrets on the host, never in the repo |

Run one instance: the dashboard counts are kept in memory. Check it with
`GET /api/health`, which answers `{"status":"ok","mode":"replay"|"live",...}`.

**Web console.** Vercel, or any host that runs `next build` and `next start`.

| Setting | Value |
|---|---|
| Root directory | `web` |
| Build command | `npm run build` |
| Start command | `npm run start` (Vercel needs none) |
| `NEXT_PUBLIC_API_URL` | The API's public URL, for example `https://offspec-api.example.com`. It is read at build time, so rebuild after changing it |

If the API is down or the variable is wrong, the console still opens and shows the
bundled sample reports, labelled "Sample data: the API is offline".

## API

| Route | What it does |
|---|---|
| `POST /api/verify-listing` | Form field `image` (a file), `text` or `sample` (a fixture id such as `fixture_01`), exactly one. Streams Server-Sent Events: one `meta` frame, then the contract's events, ending with `final_report` or `error`. |
| `POST /api/batch` | Runs every listing in `fixtures/`. Returns each report and counts per verdict and per routing value. |
| `GET /api/dashboard-stats` | Counts from the latest batch run. Before any run, `has_run` is false and the counts are null. |
| `GET /api/samples` | The fixture listings. |
| `GET /api/health` | Whether the server is in `live` or `replay` mode. |

Every JSON body carries `mode` and `sample_data`, and every response has an
`X-OffSpec-Mode` header.

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

- Four categories: batteries (loose cells, hobby lithium packs, power banks), projectors,
  magnifying glasses and monoculars. Anything else is out of scope.
- Live runs are few (see `PROGRESS.md`), so extraction quality on real screenshots is
  largely untested. The test suites use a scripted model.
- Fixtures 8 to 20 have screenshots with seller names, store links and the delivery
  address covered. In sample data mode the batch serves their expected reports; a live
  batch reads the screenshots.
- Dashboard counts come from the latest batch run and are kept in memory; they reset
  when the API restarts.
- The listing pane shows the text or screenshot exactly as you submitted it. Blur seller
  names in screenshots before uploading. The audit feed, verdicts, reports and trace are
  built only from extracted claims, which have no seller, store or brand field.
