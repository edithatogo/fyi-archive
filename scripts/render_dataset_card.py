"""Render verified sync metadata into the Hugging Face dataset card."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.dataset_card import render


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    required = {"generated_at", "record_count", "manifest_sha256", "verified"}
    missing = required.difference(summary)
    if missing:
        raise SystemExit(f"sync summary missing required fields: {', '.join(sorted(missing))}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(args.card.read_text(encoding="utf-8"), summary), encoding="utf-8")


if __name__ == "__main__":
    main()
