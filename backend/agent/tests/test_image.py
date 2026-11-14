"""Image input and unit-aware extraction, tested with a scripted model. No network."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from agent import run_listing, units
from agent.extraction import ListingExtraction
from agent.images import MAX_IMAGE_BYTES
from agent.tests.fake_model import (
    ScriptedChatModel,
    as_extraction,
    calls,
    checker_turns,
    full_script,
    reader_turns,
    record,
    say,
    writer_turns,
)
from agent.tools import RECORD_CLAIMS
from claimcheck.events import ErrorEvent, FinalReportEvent
from claimcheck.models import Claims
from tests.fixtures_data import BY_ID

EXPECTED_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "expected"

# Only the leading bytes matter: the scripted model never decodes the picture.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32


def drain(generator):
    events = []
    while True:
        try:
            events.append(next(generator))
        except StopIteration as stop:
            return events, stop.value


def run_image(image, claims: Claims | None = None, script=None):
    model = ScriptedChatModel(script=script or full_script(claims))
    events, report = drain(run_listing(image, model=model))
    return model, events, report


def script_for(*reader_calls):
    """A full run in which the listing reader makes the given calls, in order."""
    return [*reader_turns(*reader_calls), *checker_turns(), *writer_turns(), say()]


def recording(extraction: dict):
    return calls((RECORD_CLAIMS, {"claims": extraction}))


# ------------------------------------------------------------- image goes to the model


def test_fixture_3_is_caught_from_the_photo():
    fixture = BY_ID[3]
    model, events, report = run_image(PNG, fixture.claims)

    assert isinstance(events[-1], FinalReportEvent)
    assert report.verdict.value == "Flag" and report.routing.value == "needs human review"
    expected = json.loads((EXPECTED_DIR / "fixture_03.json").read_text(encoding="utf-8"))
    assert json.loads(report.model_dump_json()) == expected

    # the codes printed on the cells are claims, with where they were read
    assert [(c.value, c.found_in) for c in report.claims.printed_codes] == [("R6", "product photo"), ("R03", "product photo")]
    assert [c.value for c in report.claims.printed_terms] == ["Heavy Duty"]
    contradiction = next(c for c in report.checks if c.check_id == "label_contradiction")
    assert contradiction.status.value == "flag"


@pytest.mark.parametrize("fixture_id", [3, 4, 5])
def test_photo_dependent_fixtures_give_expected_verdict_and_routing(fixture_id):
    fixture = BY_ID[fixture_id]
    _, _, report = run_image(JPEG, fixture.claims)
    assert report.verdict is fixture.verdict
    assert report.routing is fixture.routing


@pytest.mark.parametrize(("data", "mime_type"), [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")])
def test_model_receives_the_image_as_a_standard_image_block(data, mime_type):
    model, events, _ = run_image(data, BY_ID[3].claims)

    # the listing reader gets the picture; the orchestrator is only told an image arrived
    user_message = model.reader_prompts()[0][2]
    assert user_message.type == "human"
    for prompt in model.orchestrator_prompts():
        assert all(isinstance(m.content, str) for m in prompt if m.type == "human")
        assert "image" in prompt[1].content
    text_block, image = user_message.content
    assert text_block["type"] == "text" and "image" in text_block["text"]
    assert image["type"] == "image" and image["mime_type"] == mime_type
    assert base64.b64decode(image["base64"]) == data
    assert events[0].type == "agent_step" and events[0].message == "Reading the listing image."


def test_a_path_is_read_from_disk_and_typed_by_content_not_by_name(tmp_path):
    path = tmp_path / "screenshot.png"  # a JPEG behind a .png name
    path.write_bytes(JPEG)
    model, _, report = run_image(path, BY_ID[5].claims)
    assert model.reader_prompts()[0][2].content[1]["mime_type"] == "image/jpeg"
    assert report.verdict is BY_ID[5].verdict


def test_image_bytes_never_appear_in_events():
    _, events, _ = run_image(PNG, BY_ID[3].claims)
    encoded = base64.b64encode(PNG).decode("ascii")
    assert all(encoded not in e.model_dump_json() for e in events)


# -------------------------------------------------------------------- confidence


def _with_confidence(claims: Claims, field: str, confidence: float) -> Claims:
    claim = getattr(claims, field).model_copy(update={"confidence": confidence})
    return claims.model_copy(update={field: claim})


def test_low_confidence_on_a_passing_listing_routes_to_a_person():
    _, _, report = run_image(PNG, _with_confidence(BY_ID[2].claims, "capacity_mah", 0.5))
    assert report.verdict.value == "No red flags"
    assert report.routing.value == "needs human review"
    assert report.claims.capacity_mah.confidence == 0.5


def test_low_confidence_on_a_violated_bound_is_not_auto_resolved():
    _, _, report = run_image(PNG, _with_confidence(BY_ID[1].claims, "capacity_mah", 0.6))
    assert report.verdict.value == "Impossible"
    assert report.routing.value == "needs human review"


def test_confidence_and_found_in_are_required_for_every_claim():
    missing = {"capacity": {"value": 700, "unit": "mAh"}}
    _, events, report = run_image(PNG, script=script_for(recording(missing), record(BY_ID[2].claims)))
    first = next(e for e in events if e.type == "tool_result")
    assert first.ok is False
    assert report.claims == BY_ID[2].claims


# ------------------------------------------------------- unit conversion stays in Python


STATED = {
    "chemistry": {"value": "li-ion", "found_in": "title", "confidence": 1},
    "form_factors": [{"value": "18650", "found_in": "title", "confidence": 1}],
    "nominal_voltage": {"value": 3700, "unit": "mV", "found_in": "spec table", "quote": "3700mV", "confidence": 0.9},
    "capacity": {"value": 12, "unit": "Ah", "found_in": "title", "quote": "12Ah", "confidence": 1},
    "energy": {"value": 44400, "unit": "mWh", "found_in": "label", "confidence": 1},
    "weight": {"value": 0.6, "unit": "kg", "kind": "package", "found_in": "spec table", "quote": "0.600 Kilograms", "confidence": 1},
    "dimensions": {"length": 5.5, "width": 2, "height": 1, "unit": "in", "kind": "package", "found_in": "spec table", "confidence": 1},
    "shelf_life": {"value": 120, "unit": "months", "found_in": "bullet points", "confidence": 1},
}


def test_values_are_converted_by_the_tool_not_by_the_model():
    _, events, report = run_image(PNG, script=script_for(recording(STATED)))
    claims = report.claims

    assert claims.nominal_voltage_v.value == 3.7
    assert claims.capacity_mah.value == 12000
    assert claims.energy_wh.value == 44.4
    assert claims.weight.value_g == 600 and claims.weight.kind.value == "package"
    assert (claims.dimensions.length_mm, claims.dimensions.width_mm, claims.dimensions.height_mm) == (139.7, 50.8, 25.4)
    assert claims.shelf_life_years.value == 10
    # provenance survives the conversion
    assert claims.capacity_mah.quote == "12Ah" and claims.nominal_voltage_v.confidence == 0.9
    assert claims.weight.quote == "0.600 Kilograms"

    # the trace shows the value as the model reported it and as the tool stored it
    call = next(e for e in events if e.type == "tool_call" and e.tool == RECORD_CLAIMS)
    result = next(e for e in events if e.type == "tool_result" and e.tool == RECORD_CLAIMS)
    assert call.args["claims"]["capacity"] == STATED["capacity"]
    assert result.result["claims"]["capacity_mah"]["value"] == 12000
    assert report.verdict.value == "Impossible"


def test_values_already_in_the_standard_unit_are_untouched():
    for fixture in BY_ID.values():
        assert ListingExtraction.model_validate(as_extraction(fixture.claims)).to_claims() == fixture.claims


def test_conversion_factors():
    assert units.convert(1, "in", units.TO_MM) == 25.4
    assert units.convert(1, "lb", units.TO_G) == 453.59237
    assert units.convert(16, "oz", units.TO_G) == units.convert(1, "lb", units.TO_G)
    assert units.convert(2.5, "cm", units.TO_MM) == 25
    assert units.convert(0.6, "kg", units.TO_G) == 600
    assert units.convert(5200, "mAh", units.TO_MAH) == 5200
    assert units.convert(6, "months", units.TO_YEARS) == 0.5


def test_an_unknown_unit_is_rejected_rather_than_guessed():
    bad = {"capacity": {"value": 12, "unit": "kWh", "found_in": "title", "confidence": 1}}
    _, events, _ = run_image(PNG, script=script_for(recording(bad), record(BY_ID[2].claims)))
    assert next(e for e in events if e.type == "tool_result").ok is False


def test_extraction_has_no_place_for_a_seller_or_brand():
    names = set(ListingExtraction.model_json_schema()["properties"])
    assert not {n for n in names if any(word in n for word in ("seller", "store", "brand", "vendor", "shop"))}
    with pytest.raises(ValueError):
        ListingExtraction.model_validate({"brand": "Anything"})


# ------------------------------------------------------------------- bad images


@pytest.mark.parametrize(
    ("image", "message"),
    [
        (b"GIF89a" + b"\x00" * 20, "The image must be a PNG, JPEG or WebP file."),
        (b"just some text", "The image must be a PNG, JPEG or WebP file."),
        (b"", "The image is empty."),
        (PNG + b"\x00" * MAX_IMAGE_BYTES, "The image is too large. Use a screenshot under 3.5 MB."),
        (Path("no-such-file.png"), "The image file could not be read."),
    ],
    ids=["gif", "text", "empty", "too-large", "missing-file"],
)
def test_unusable_image_ends_with_an_error_before_any_model_call(image, message):
    model = ScriptedChatModel(script=[])
    events, report = drain(run_listing(image, model=model))
    assert report is None and len(events) == 1
    assert isinstance(events[0], ErrorEvent) and events[0].message == message
    assert model.prompts == []
