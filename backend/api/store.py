"""Finished reports kept in memory so they can be downloaded by run id."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Any

MAX_REPORTS = 500

_reports: OrderedDict[str, dict[str, Any]] = OrderedDict()
_lock = Lock()


def save(run_id: str, report: dict[str, Any]) -> None:
    with _lock:
        _reports[run_id] = report
        _reports.move_to_end(run_id)
        while len(_reports) > MAX_REPORTS:
            _reports.popitem(last=False)


def get(run_id: str) -> dict[str, Any] | None:
    with _lock:
        return _reports.get(run_id)


def clear() -> None:
    with _lock:
        _reports.clear()
