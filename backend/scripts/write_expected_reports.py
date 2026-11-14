"""Regenerate fixtures/expected/fixture_NN.json from the check code.

Run from the backend folder:  python scripts/write_expected_reports.py
The test suite fails if these files drift from what the code produces.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from claimcheck import evaluate  # noqa: E402
from tests.fixtures_data import FIXTURES  # noqa: E402

EXPECTED_DIR = BACKEND.parent / "fixtures" / "expected"


def expected_path(fixture_id: int) -> Path:
    return EXPECTED_DIR / f"fixture_{fixture_id:02d}.json"


def main() -> None:
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    for fixture in FIXTURES:
        report = json.loads(evaluate(fixture.claims).model_dump_json())
        text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        expected_path(fixture.id).write_text(text, encoding="utf-8", newline="\n")
        print(f"{expected_path(fixture.id).name}: {report['verdict']} | {report['routing']}")


if __name__ == "__main__":
    main()
