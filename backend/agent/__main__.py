"""Command line: check one listing, pasted text or a screenshot.

    python -m agent "18650 3.7V 12000mAh li-ion cell"
    python -m agent --file listing.txt
    python -m agent --image screenshot.png
    type listing.txt | python -m agent

Prints one line per stream event to stderr and the evidence report as JSON to stdout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from agent.runner import run_listing


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m agent", description="Check one battery listing given as text or as an image.")
    parser.add_argument("text", nargs="?", help="listing text; read from stdin when omitted")
    parser.add_argument("--file", type=Path, help="read the listing text from a file")
    parser.add_argument("--image", type=Path, help="check a screenshot or product photo (PNG, JPEG or WebP)")
    args = parser.parse_args()

    # backend/.env or the repo root .env, whichever exists. Real variables win.
    load_dotenv()

    if args.image:
        text = args.image
    elif args.file:
        text = args.file.read_text(encoding="utf-8")
    elif args.text is not None:
        text = args.text
    else:
        text = sys.stdin.read()

    last = None
    for event in run_listing(text):
        last = event
        if event.type == "agent_step":
            print(f"[step]   {event.message}", file=sys.stderr)
        elif event.type == "tool_call":
            print(f"[call]   {event.tool}", file=sys.stderr)
        elif event.type == "tool_result":
            print(f"[result] {event.tool}: {event.summary}", file=sys.stderr)
        elif event.type == "error":
            print(f"[error]  {event.message}", file=sys.stderr)

    if last is None or last.type != "final_report":
        return 1
    print(f"\n{last.report.verdict.value} / {last.report.routing.value}", file=sys.stderr)
    print(last.report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
