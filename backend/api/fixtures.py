"""The fixture listings and their expected reports, read from the repo's fixtures/ folder.

    fixtures/fixture_NN.txt                     a listing as pasted text
    fixtures/fixture_NN.png | .jpg | .jpeg | .webp   a listing screenshot, seller names blurred
    fixtures/expected/fixture_NN.json           the report the checks give for it

A fixture can have a text file, a screenshot, or both. When it has both, the
screenshot is the one that is run.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from claimcheck.models import EvidenceReport

FIXTURES_ENV = "CARNOT_FIXTURES_DIR"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
_ID = re.compile(r"^fixture_\d{2}$")


def fixtures_dir() -> Path:
    override = os.environ.get(FIXTURES_ENV, "").strip()
    return Path(override) if override else Path(__file__).resolve().parents[2] / "fixtures"


@dataclass(frozen=True)
class Fixture:
    id: str
    text_path: Path | None
    image_path: Path | None
    expected_path: Path | None

    @property
    def source(self) -> str:
        return "image" if self.image_path else "text"

    @property
    def text(self) -> str | None:
        return self.text_path.read_text(encoding="utf-8") if self.text_path else None

    def expected_report(self) -> EvidenceReport | None:
        if self.expected_path is None:
            return None
        return EvidenceReport.model_validate(json.loads(self.expected_path.read_text(encoding="utf-8")))


def is_fixture_id(value: str) -> bool:
    return bool(_ID.match(value))


def list_fixtures() -> list[Fixture]:
    """Every fixture that has a listing file or an expected report, in id order."""
    root = fixtures_dir()
    ids: set[str] = set()
    if root.is_dir():
        for path in root.iterdir():
            if path.is_file() and is_fixture_id(path.stem) and path.suffix.lower() in (".txt", *IMAGE_SUFFIXES):
                ids.add(path.stem)
        expected = root / "expected"
        if expected.is_dir():
            ids.update(p.stem for p in expected.glob("fixture_*.json") if is_fixture_id(p.stem))
    return [get_fixture(fixture_id) for fixture_id in sorted(ids)]


def get_fixture(fixture_id: str) -> Fixture | None:
    if not is_fixture_id(fixture_id):
        return None
    root = fixtures_dir()
    text_path = root / f"{fixture_id}.txt"
    image_path = next((root / f"{fixture_id}{s}" for s in IMAGE_SUFFIXES if (root / f"{fixture_id}{s}").is_file()), None)
    expected_path = root / "expected" / f"{fixture_id}.json"
    fixture = Fixture(
        id=fixture_id,
        text_path=text_path if text_path.is_file() else None,
        image_path=image_path,
        expected_path=expected_path if expected_path.is_file() else None,
    )
    if fixture.text_path is None and fixture.image_path is None and fixture.expected_path is None:
        return None
    return fixture


def _normalized(text: str) -> str:
    return " ".join(text.split())


def match_text(text: str) -> Fixture | None:
    """The fixture whose listing text is the given text, ignoring whitespace differences."""
    wanted = _normalized(text)
    if not wanted:
        return None
    for fixture in list_fixtures():
        if fixture.text_path and _normalized(fixture.text or "") == wanted:
            return fixture
    return None


def match_image(data: bytes) -> Fixture | None:
    """The fixture whose screenshot has exactly these bytes."""
    for fixture in list_fixtures():
        if fixture.image_path and fixture.image_path.read_bytes() == data:
            return fixture
    return None
