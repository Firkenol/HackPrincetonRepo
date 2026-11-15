"""The fixture listings and their expected reports, read from the repo's fixtures/ folder.

    fixtures/fixture_NN.txt                     a listing as pasted text
    fixtures/fixture_NN.png | .jpg | .jpeg | .webp   a listing screenshot, seller names blurred
    fixtures/expected/fixture_NN.json           the report the checks give for it

The nine fixture_NN listings are batteries. Listings for the check packs (projector,
magnifying glass, monocular) use the same layout under another name:

    fixtures/pack_<pack>_<case>.txt             a listing as pasted text
    fixtures/expected/pack_<pack>_<case>.json   the pack's report for it

Only packs in packs.registry are listed.

A listing captured in two screenshots is saved as fixture_NNa.png and fixture_NNb.png.
The two are one listing: they are stitched top to bottom into one image before the
run, because run_listing takes one image.

A fixture can have a text file, a screenshot, or both. When it has both, the
screenshot is the one that is run.
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from claimcheck.models import AnyReport, EvidenceReport, PackEvidenceReport
from packs.registry import PACKS

FIXTURES_ENV = "OFFSPEC_FIXTURES_DIR"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
_ID = re.compile(r"^(?:fixture_\d{2}|pack_(?:" + "|".join(map(re.escape, PACKS)) + r")_[a-z0-9]+)$")
_PART = re.compile(r"^(fixture_\d{2})[a-z]$")
# run_listing refuses images over 3.5 MB; a stitched image above this is re-encoded.
_MAX_STITCHED_BYTES = 3_400_000


def stitch_vertical(paths: list[Path]) -> bytes:
    """The given images stacked top to bottom on a white background, as PNG (or JPEG if large)."""
    from PIL import Image  # imported here: only stitched fixtures need Pillow

    images = [Image.open(path).convert("RGB") for path in paths]
    width = max(image.width for image in images)
    canvas = Image.new("RGB", (width, sum(image.height for image in images)), "white")
    top = 0
    for image in images:
        canvas.paste(image, (0, top))
        top += image.height
    out = io.BytesIO()
    canvas.save(out, format="PNG", optimize=True)
    if out.tell() > _MAX_STITCHED_BYTES:
        out = io.BytesIO()
        canvas.save(out, format="JPEG", quality=88)
    return out.getvalue()


def fixtures_dir() -> Path:
    override = os.environ.get(FIXTURES_ENV, "").strip()
    return Path(override) if override else Path(__file__).resolve().parents[2] / "fixtures"


@dataclass(frozen=True)
class Fixture:
    id: str
    text_path: Path | None
    image_path: Path | None
    expected_path: Path | None
    # the screenshots of a listing captured in parts (fixture_NNa, fixture_NNb), in order
    image_parts: tuple[Path, ...] = ()

    @property
    def has_image(self) -> bool:
        return bool(self.image_path or self.image_parts)

    def image_bytes(self) -> bytes | None:
        """The screenshot to run: the single file, or the parts stitched into one image."""
        if self.image_path:
            return self.image_path.read_bytes()
        if self.image_parts:
            return stitch_vertical(list(self.image_parts))
        return None

    @property
    def source(self) -> str:
        return "image" if self.has_image else "text"

    @property
    def text(self) -> str | None:
        return self.text_path.read_text(encoding="utf-8") if self.text_path else None

    def expected_report(self) -> AnyReport | None:
        """The stored report: a pack's report when the file names a pack, otherwise a battery report."""
        if self.expected_path is None:
            return None
        data = json.loads(self.expected_path.read_text(encoding="utf-8"))
        model = PackEvidenceReport if isinstance(data, dict) and "pack" in data else EvidenceReport
        return model.model_validate(data)


def is_fixture_id(value: str) -> bool:
    return bool(_ID.match(value))


def list_fixtures() -> list[Fixture]:
    """Every fixture that has a listing file or an expected report, in id order."""
    root = fixtures_dir()
    ids: set[str] = set()
    if root.is_dir():
        for path in root.iterdir():
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            part = _PART.match(path.stem)
            if is_fixture_id(path.stem) and suffix in (".txt", *IMAGE_SUFFIXES):
                ids.add(path.stem)
            elif part and suffix in IMAGE_SUFFIXES:
                ids.add(part.group(1))
        expected = root / "expected"
        if expected.is_dir():
            ids.update(p.stem for p in expected.glob("*.json") if is_fixture_id(p.stem))
    return [get_fixture(fixture_id) for fixture_id in sorted(ids)]


def get_fixture(fixture_id: str) -> Fixture | None:
    if not is_fixture_id(fixture_id):
        return None
    root = fixtures_dir()
    text_path = root / f"{fixture_id}.txt"
    image_path = next((root / f"{fixture_id}{s}" for s in IMAGE_SUFFIXES if (root / f"{fixture_id}{s}").is_file()), None)
    expected_path = root / "expected" / f"{fixture_id}.json"
    parts: tuple[Path, ...] = ()
    if image_path is None and root.is_dir():
        parts = tuple(
            sorted(
                path
                for path in root.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and (m := _PART.match(path.stem)) and m.group(1) == fixture_id
            )
        )
    fixture = Fixture(
        id=fixture_id,
        text_path=text_path if text_path.is_file() else None,
        image_path=image_path,
        expected_path=expected_path if expected_path.is_file() else None,
        image_parts=parts,
    )
    if fixture.text_path is None and not fixture.has_image and fixture.expected_path is None:
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
        if fixture.has_image and fixture.image_bytes() == data:
            return fixture
    return None
