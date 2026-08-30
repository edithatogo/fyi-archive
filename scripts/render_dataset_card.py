"""Render verified sync metadata into the Hugging Face dataset card."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fyi_archive.archive_dataset_card import render_instance_card
from fyi_archive.dataset_card import render
from fyi_archive.instances import get_instance
from fyi_archive.sync_summary import validate_summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--instance")
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    required = {"generated_at", "record_count", "manifest_sha256", "verified"}
    missing = required.difference(summary)
    if missing:
        raise SystemExit(f"sync summary missing required fields: {', '.join(sorted(missing))}")
    validate_summary(summary, instance_id=args.instance or "nz-fyi")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.instance and args.instance != "nz-fyi":
        card = render_instance_card(get_instance(args.instance))
    else:
        card = args.card.read_text(encoding="utf-8")
    args.output.write_text(render(card, summary), encoding="utf-8")


if __name__ == "__main__":
    main()
