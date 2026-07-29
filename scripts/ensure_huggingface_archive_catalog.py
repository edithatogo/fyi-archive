"""Create and maintain the dedicated fyi-archive Hugging Face catalog."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.errors import EntryNotFoundError

from fyi_archive.archive_dataset_card import collection_note, render_instance_card
from fyi_archive.instances import ArchiveInstance, list_instances

COLLECTION_TITLE = "fyi-archive: global public-information request archives"
COLLECTION_DESCRIPTION = (
    "Independent, read-only public-information request archives with separate "
    "provenance, rights, state, and completeness evidence."
)
_STATUS_ORDER = {"supported": 0, "experimental": 1, "historical-only": 2}


def ordered_instances() -> list[ArchiveInstance]:
    """Return supported, experimental, then historical instances in stable order."""
    return sorted(list_instances(), key=lambda item: (_STATUS_ORDER[item.status], item.id))


def plan() -> dict[str, Any]:
    """Return the deterministic catalog plan without contacting the Hub."""
    return {
        "schema": "fyi-archive.huggingface-catalog-plan.v1",
        "collection": {
            "title": COLLECTION_TITLE,
            "namespace": "edithatogo",
            "description": COLLECTION_DESCRIPTION,
            "private": False,
            "theme": "blue",
        },
        "datasets": [
            {
                "instance": asdict(instance),
                "repo_id": instance.hf_repo_id,
                "note": collection_note(instance),
            }
            for instance in ordered_instances()
        ],
    }


def apply_catalog(*, token: str | None = None) -> dict[str, object]:
    """Idempotently upload truthful cards and collect every registered dataset."""
    api = HfApi(token=token)
    collection = api.create_collection(
        COLLECTION_TITLE,
        namespace="edithatogo",
        description=COLLECTION_DESCRIPTION,
        private=False,
        exists_ok=True,
        token=token,
    )
    collection = api.update_collection_metadata(
        collection.slug,
        title=COLLECTION_TITLE,
        description=COLLECTION_DESCRIPTION,
        private=False,
        theme="blue",
        token=token,
    )
    revisions: list[dict[str, str]] = []
    for instance in ordered_instances():
        api.create_repo(
            repo_id=instance.hf_repo_id,
            repo_type="dataset",
            private=False,
            exist_ok=True,
            token=token,
        )
        card = (
            Path("DATASET_CARD.md").read_text(encoding="utf-8")
            if instance.id == "nz-fyi"
            else render_instance_card(instance)
        )
        try:
            remote_card = Path(
                hf_hub_download(
                    instance.hf_repo_id,
                    "README.md",
                    repo_type="dataset",
                    token=token,
                )
            ).read_text(encoding="utf-8")
        except EntryNotFoundError:
            remote_card = ""
        if remote_card == card:
            revision = str(api.dataset_info(instance.hf_repo_id, token=token).sha or "")
            action = "unchanged"
        else:
            commit = api.upload_file(
                path_or_fileobj=card.encode(),
                path_in_repo="README.md",
                repo_id=instance.hf_repo_id,
                repo_type="dataset",
                token=token,
                commit_message="docs: publish instance-specific dataset card",
            )
            revision = commit.oid
            action = "updated"
        api.add_collection_item(
            collection.slug,
            instance.hf_repo_id,
            "dataset",
            note=collection_note(instance),
            exists_ok=True,
            token=token,
        )
        revisions.append({"repo_id": instance.hf_repo_id, "commit": revision, "action": action})
    current = api.get_collection(collection.slug, token=token)
    items = {item.item_id: item for item in current.items}
    for position, instance in enumerate(ordered_instances()):
        api.update_collection_item(
            collection.slug,
            items[instance.hf_repo_id].item_object_id,
            note=collection_note(instance),
            position=position,
            token=token,
        )
    return {
        "schema": "fyi-archive.huggingface-catalog-receipt.v1",
        "collection_slug": collection.slug,
        "datasets": revisions,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = apply_catalog() if args.apply else plan()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
