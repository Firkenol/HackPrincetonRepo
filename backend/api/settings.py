"""Everything the API reads from the environment, in one place. Read at call time so tests can change it."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def runner_name() -> str:
    """`agent` (default) uses claimcheck.run_listing. `stub` replays fixtures/expected/."""
    return os.environ.get("CLAIMCHECK_RUNNER", "agent").strip().lower()


def fixtures_dir() -> Path:
    """Folder that holds expected/fixture_NN.json and, later, the fixture screenshots."""
    return Path(os.environ.get("CLAIMCHECK_FIXTURES_DIR", REPO_ROOT / "fixtures")).resolve()


def stub_delay_s() -> float:
    """Base pause between stub events. One run takes about 20 times this."""
    return max(0.0, float(os.environ.get("CLAIMCHECK_STUB_DELAY_MS", "150"))) / 1000


def cors_origins() -> list[str]:
    raw = os.environ.get("CLAIMCHECK_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def max_upload_bytes() -> int:
    return int(float(os.environ.get("CLAIMCHECK_MAX_UPLOAD_MB", "10")) * 1024 * 1024)
