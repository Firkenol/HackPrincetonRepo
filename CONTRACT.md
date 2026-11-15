# ClaimCheck contract

This is the interface between the four parts of the project: the checks, the agent, the API and the web frontend. **It is frozen. Any change to the items listed under "What is frozen" needs the project owner's approval.**

The source of truth is the code. If this document and the code disagree, the code wins and this document has a bug.

## Contract changes

Newest first. API and frontend owners: check this list when you pull.

| Date | Change | What to do |
|---|---|---|
| 2026-11-14 | Check packs for projectors, magnifying glasses and monoculars are wired in. Approved by the project owner. New model `PackEvidenceReport` in `models.py` (additive: nothing existing changed). `final_report.report` and the return value of `run_listing` are now `PackEvidenceReport` or `EvidenceReport`. New helper `replay_pack_claims`. Fixture ids may also be `pack_<pack>_<case>`. | Tell the two reports apart by the `pack` field: only a pack report has it. Do not assume six checks or battery claims when `pack` is present. See "Check packs" below. |
| 2026-11-14 | HTTP transport replaced on the project owner's instruction: `POST /api/verify-listing` (was `/api/check`), plus `POST /api/batch`, `GET /api/dashboard-stats`, `GET /api/samples`, `GET /api/health`. The stream opens with one `meta` frame before the contract events. Replay mode serves `fixtures/expected/` and marks responses as sample data. The frontend folder is `web/`. | See "HTTP transport" below. The event and report models are unchanged. |
| 2026-11-14 | Skills are grouped by subagent: `backend/skills/<subagent>/<skill>/SKILL.md`. | Nothing outside the agent reads them. |
| 2026-11-14 | `run_listing` returns `EvidenceReport | None` (was `EvidenceReport`). A failed run ends with one `error` event and returns `None`; it does not raise. Approved by the project owner. | Handle `error` as a terminal event. Do not assume the return value is a report. |
| 2026-11-14 | `run_listing` is implemented (it used to raise `NotImplementedError`) and the agent lives in `backend/agent/`. `replay_claims` also ends with an `error` event and returns `None` if a check fails. | Nothing, unless you caught `NotImplementedError`. |

## What is frozen

| Item | File |
|---|---|
| Data models: `Claims`, `CheckResult`, `EvidenceReport`, `PackEvidenceReport` and their parts | `backend/claimcheck/models.py` |
| Stream events | `backend/claimcheck/events.py` |
| Entry point signature `run_listing(image_or_text)` | `backend/claimcheck/pipeline.py` |
| The verdict strings, routing strings and check ids below | `backend/claimcheck/models.py`, `backend/claimcheck/checks.py` |
| HTTP transport: the routes under "HTTP transport" | this document |

Not frozen: constants, policy thresholds, check wording, anything inside the agent, `replay_claims`, `replay_pack_claims`, and each pack's own claims model.

`backend/tests/test_contract.py` fails if the expected reports in `fixtures/expected/` drift from what the code produces, so a contract change shows up as a failing test.

## Where things live

| Part | Folder |
|---|---|
| Checks, constants, models (done) | `backend/claimcheck/` |
| Agent: deepagents setup, tools, subagents, `run_listing` implementation | `backend/agent/` |
| Skills, one folder per subagent, then one folder per skill with a `SKILL.md` | `backend/skills/` |
| API (FastAPI) | `backend/api/` |
| Web frontend (Next.js) | `web/` |
| Extra check packs | `backend/packs/` |
| Screenshots for the fixtures | `fixtures/` |
| Expected report per fixture | `fixtures/expected/fixture_NN.json` |

Rules that keep the parts independent:

- The API imports only `run_listing`, `replay_claims`, the event and report models and `to_sse`. It does not import checks or the agent.
- The frontend depends only on the event JSON and the report JSON described here.
- The agent calls the check functions as tools. It never does arithmetic itself.
- A check pack is a folder under `backend/packs/` with `models.py` (its claims), `constants.py` (its cited constants) and `checks.py` (`CHECKS`, a tuple of functions from its claims to a `CheckResult`, and `evaluate`). `backend/packs/registry.py` lists the packs the agent, the API and the console know.

## Fixed strings

**Verdict** (exactly these four):

| Value | Meaning |
|---|---|
| `Impossible` | A hard physical bound is violated. |
| `Flag` | A contradiction or unusual claim. |
| `No red flags` | Claims were tested and are plausible. This is not a confirmation. |
| `No checkable claim` | Nothing numeric or testable was stated. |

**Routing** (exactly these three):

| Value | When |
|---|---|
| `auto-resolvable` | Verdict is `Impossible` and the inputs of the violated check were read with high confidence. |
| `needs human review` | Any `Flag`; an `Impossible` with a low-confidence input; a passing result with a low-confidence claim; a numeric claim that could not be tested. |
| `no action needed` | `No red flags` or `No checkable claim` with every claim read at high confidence. |

High confidence means 0.8 or more.

**Check ids**, always all six, always in this order in `EvidenceReport.checks`:

`label_consistency`, `form_factor_bound`, `dimension_bound`, `weight_bound`, `label_contradiction`, `chemistry_mismatch`

A `PackEvidenceReport` carries its pack's checks instead (see "Check packs").

**Check status**: `pass`, `violated` (hard bound exceeded), `flag` (soft), `not_assessed`.

## Entry point

```python
from claimcheck import run_listing

def run_listing(image_or_text: str | bytes | Path) -> Generator[StreamEvent, None, PackEvidenceReport | EvidenceReport | None]
```

| Input type | Meaning |
|---|---|
| `str` | Pasted listing text |
| `bytes` | The bytes of a screenshot (PNG, JPEG or WebP) |
| `pathlib.Path` | A screenshot file on disk |

It yields stream events as the run proceeds. A run ends in exactly one of two ways:

| Outcome | Last event | Return value |
|---|---|---|
| Success | `final_report`, carrying the report | the same report: an `EvidenceReport` for a battery listing, a `PackEvidenceReport` for a projector, magnifying glass or monocular listing |
| Failure | `error`, with a message that is safe to display | `None` |

`run_listing` does not raise for a failed run: a missing model setting, a model error and an unreadable listing all end with the `error` event. A caller that only streams can ignore the return value and should treat `error` as the end of the stream.

`run_listing` runs the agent, so it needs a model: set `MODEL_PROVIDER` and `MODEL_ID` (see `.env.example`). Text and image input both work. An image that is not PNG, JPEG or WebP, or is larger than 3.5 MB, ends with an `error` event.

`replay_claims(claims)` yields the same event types for claims that are already extracted, without calling a model. Use it to build and test the API and the UI without a key:

```python
from claimcheck import replay_claims
from tests.fixtures_data import BY_ID

for event in replay_claims(BY_ID[1].claims):
    print(event.type, event.model_dump_json())
```

## Stream events

Every event is a JSON object with these common fields:

| Field | Type | Meaning |
|---|---|---|
| `type` | string | Which event this is. Use it to tell events apart. |
| `run_id` | string | Same for every event of one run. |
| `seq` | integer | Position in the stream. Starts at 0 and increases by 1. |
| `agent` | string | `orchestrator`, `listing-reader`, `physics-checker` or `report-writer`. |

| `type` | Extra fields | Sent when |
|---|---|---|
| `agent_step` | `message` (string) | An agent starts a step. One line for the live trace. |
| `tool_call` | `call_id`, `tool` (strings), `args` (object) | An agent calls a tool. |
| `tool_result` | `call_id`, `tool`, `ok` (boolean), `summary` (string), `result` (any JSON) | A tool returns. `call_id` matches the `tool_call`. For a check tool, `result` is a `CheckResult`. |
| `final_report` | `report` (`EvidenceReport` or `PackEvidenceReport`) | Once, as the last event of a successful run. |
| `error` | `message` (string, safe to display) | Once, as the last event of a failed run. |

Example:

```json
{"type": "tool_call", "run_id": "9f2c", "seq": 3, "agent": "physics-checker", "call_id": "9f2c-1", "tool": "check_form_factor_bound", "args": {}}
```

No event ever carries a seller or store name.

## HTTP transport

Served by `backend/api/` (FastAPI).

```
POST /api/verify-listing
Content-Type: multipart/form-data
  image    a screenshot file          (send exactly one of image, text or sample)
  text     pasted listing text
  sample   a fixture id, such as fixture_01
Response: text/event-stream
```

The stream opens with one frame that is not a contract event:

```
event: meta
data: {"mode": "replay", "sample_data": true, "sample_id": "fixture_01"}

```

Every frame after it is one stream event, with the SSE `event` name equal to the event's `type` and the JSON object as `data`, as produced by `claimcheck.events.to_sse(event)`. The stream ends with `final_report` or `error`.

| Route | Response |
|---|---|
| `POST /api/batch` | Runs every listing in `fixtures/`. JSON: `mode`, `sample_data`, `ran_at`, `items` (each with `id`, `source`, `listing_text`, `image_url`, `report`, `error`) and `counts` (`total`, `errors`, `by_verdict`, `by_routing`). |
| `GET /api/dashboard-stats` | Counts from the latest batch run: `has_run`, `ran_at`, `listings_checked`, `impossible_claims`, `routed_to_human_review`, `no_action_needed`, `auto_resolvable`, `errors`, `by_verdict`, `by_routing`. All counts are null until a batch has run. |
| `GET /api/samples` | The fixture listings. |
| `GET /api/fixtures/{name}` | A fixture screenshot. |
| `GET /api/health` | `status`, `mode`, `sample_data`. |

**Modes.** `live` when `MODEL_PROVIDER` and `MODEL_ID` are set, otherwise `replay` (or when `OFFSPEC_REPLAY=1`). In replay mode the API serves the reports in `fixtures/expected/`: a listing that is one of the fixtures streams its checks through `replay_claims`; any other listing ends with an `error` event saying it was not checked. Every JSON body carries `mode` and `sample_data`, and every response has the `X-OffSpec-Mode` header.

The batch view in the web app calls `POST /api/batch`.

## Data models

All models are pydantic v2. For a machine-readable schema run `EvidenceReport.model_json_schema()`.

### Claims: what the listing itself states

A field that is absent means the listing does not state it. There is no field for a seller, store or brand name, and none may be added.

Every individual claim carries three provenance fields:

| Field | Type | Meaning |
|---|---|---|
| `found_in` | string | Where the claim appears: title, bullet points, spec table, product photo, description. |
| `quote` | string or null | The claim as shown, such as `12000mAh`. Never a seller, store or brand name. |
| `confidence` | number 0 to 1 | How sure the extractor is. Defaults to 1. |

Claim types:

| Type | Value fields |
|---|---|
| `NumberClaim` | `value` (number above 0) |
| `TextClaim` | `value` (string) |
| `ChemistryClaim` | `value`: `li-ion`, `nimh`, `alkaline`, `zinc-carbon`, `nicd`, `lithium-primary`, `other` |
| `WeightClaim` | `value_g`, `kind`: `product` or `package` |
| `DimensionsClaim` | `length_mm`, `width_mm`, `height_mm`, `kind`: `product` or `package` |

`li-ion` covers every rechargeable lithium chemistry, including LiPo and LiFePO4. For a cylinder given as diameter by length, repeat the diameter as both `length_mm` and `width_mm`. `kind` is `package` when the listing says package, shipping or box; such measurements are never used as a bound.

`Claims` fields:

| Field | Type | Meaning |
|---|---|---|
| `product_type` | `loose_cell`, `battery_pack`, `power_bank`, `unknown` | What the listing is for. Default `unknown`. |
| `chemistry` | `ChemistryClaim` or null | Chemistry as stated in the title or description. |
| `form_factors` | list of `TextClaim` | Size codes such as `18650`, `21700`, `AA`, `AAA`. |
| `cell_count` | `NumberClaim` or null | Number of cells the stated capacity covers: 1 for loose cells rated individually, N for an assembled pack. |
| `nominal_voltage_v` | `NumberClaim` or null | Nominal voltage of the cell or pack. Not a USB or output voltage. |
| `capacity_mah` | `NumberClaim` or null | Labeled cell or pack capacity. |
| `energy_wh` | `NumberClaim` or null | Energy as printed on the label. |
| `output_capacity_mah` | `NumberClaim` or null | Rated or usable output capacity of a power bank. Recorded, never compared. |
| `weight` | `WeightClaim` or null | |
| `dimensions` | `DimensionsClaim` or null | |
| `shelf_life_years` | `NumberClaim` or null | |
| `printed_codes` | list of `TextClaim` | Designation codes read off the product itself, such as `R6` or `LR03`. |
| `printed_terms` | list of `TextClaim` | Grade wording read off the product itself, such as `Heavy Duty`. |

### CheckResult: one check, reproducible by hand

| Field | Type | Meaning |
|---|---|---|
| `check_id` | string | One of the six check ids. |
| `title` | string | Display name. |
| `status` | `pass`, `violated`, `flag`, `not_assessed` | |
| `summary` | string | One or two neutral sentences. |
| `inputs` | list of `Quantity` | Every value the check used. |
| `formula` | string or null | The formula in symbols. |
| `steps` | list of `Step` | The arithmetic, one line per step, in order. |
| `constants` | list of `Citation` | Each constant used, with its source. |
| `assumptions` | list of strings | Anything assumed rather than stated. |
| `notes` | list of strings | Remarks, such as a package weight being set aside. |
| `not_assessed_reason` | string or null | Set when `status` is `not_assessed`. |

`Quantity`: `name`, `value` (number or string), `unit`, `origin` (`claim`, `constant`, `derived` or `assumption`), and for claims `found_in` and `confidence`.

`Step`: `label`, `formula`, `substitution` (the formula with numbers in it), `result` (number or null), `unit`, and `text`, which is the whole line ready to display, for example `Energy implied by the stated capacity: 3.7 V × 12 Ah = 44.4 Wh`. The frontend reveals `steps` one at a time and can show `text` as is.

`Citation`: `key`, `value`, `unit`, `description`, `source_title`, `source_publisher`, `source_url`, `locator`, `quote`, `accessed`, `note`, `hard_bound`. When `hard_bound` is false, exceeding the value gives `flag`, never `violated`.

### EvidenceReport: the main output

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | `"1.0"` | |
| `claims` | `Claims` | What was extracted and where each claim was found. |
| `checks` | list of six `CheckResult` | In the fixed order above. |
| `verdict` | verdict string | |
| `verdict_reason` | string | |
| `routing` | routing string | |
| `routing_reason` | string | |
| `assumptions` | list of strings | All assumptions across checks, without duplicates. |
| `not_assessed` | list of strings | One line per check that did not run, with the reason. |

### PackEvidenceReport and check packs

A listing that is not a battery is checked by a pack. The listing reader decides the
category by the record tool it calls; anything that fits no pack is recorded as a
battery listing, as before.

`PackEvidenceReport` has every field of `EvidenceReport`, with two differences:

| Field | Type | Meaning |
|---|---|---|
| `pack` | string | The pack id. Only a pack report has this field. |
| `claims` | object | That pack's own claims, as JSON. Each claim carries `found_in`, `quote` and `confidence`, as battery claims do. |

`checks` holds the pack's checks, in the pack's order. `CheckResult`, the four
verdicts, the three routings and the routing rules are the same as for batteries.

| Pack id | Category | Claims fields | Check ids | Worst verdict |
|---|---|---|---|---|
| `projector_resolution` | projector | `claimed_resolution`, `native_pixels` (`width_px`, `height_px`), `native_name` | `native_resolution` | `Flag` |
| `magnifier_lens` | magnifying glass | `magnification`, `lens_diameter_mm`, `lens_type` | `lens_diameter` | `Impossible` |
| `monocular_optics` | monocular | `magnification`, `objective_mm`, `body_dimensions`, `fine_print_magnification`, `fine_print_objective_mm` | `objective_fits_body`, `fine_print_consistency` | `Flag` |

When a claim is stated but the data to test it is missing (no native resolution, no
lens diameter, no body dimensions), the check is `not_assessed`, the verdict is
`No checkable claim` and the routing is `needs human review`.

`replay_pack_claims(pack, claims)` is `replay_claims` for a pack: the same event types,
no model. Pack fixtures are `fixtures/pack_<pack>_<case>.txt` with expected reports in
`fixtures/expected/pack_<pack>_<case>.json`; regenerate them with
`python packs/write_expected_reports.py` from `backend/`. `power_budget` is a pack with
checks and tests that is not in the registry, so the agent and the API do not use it.

Real examples: `fixtures/expected/fixture_01.json` (Impossible), `fixture_03.json` (Flag), `fixture_05.json` (No checkable claim), `fixture_06.json` (No red flags). Regenerate them with `python scripts/write_expected_reports.py` from `backend/`.
