"""Dataset metadata generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    """Load latest manifest JSON."""
    return json.loads(path.read_text(encoding="utf-8"))


def build_frictionless(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal Frictionless package descriptor."""
    return {
        "profile": "data-package",
        "name": "fyi-archive-nz",
        "title": "fyi-archive-nz",
        "resources": [
            {
                "name": "requests",
                "path": "manifests/latest_manifest.parquet",
                "format": "parquet",
                "mediatype": "application/vnd.apache.parquet",
            },
        ],
        "custom": {
            "source": manifest["meta"]["source"],
            "record_count": manifest["meta"]["record_count"],
        },
    }


def build_schema_org(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build schema.org Dataset JSON-LD."""
    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "fyi-archive-nz",
        "description": "Read-only archive of public fyi.org.nz OIA request records.",
        "url": "https://github.com/edithatogo/fyi-archive",
        "isBasedOn": manifest["meta"]["source"],
        "version": manifest["meta"]["version"],
        "size": manifest["meta"]["record_count"],
    }


def build_croissant(manifest: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal Croissant-style JSON-LD descriptor."""
    return {
        "@context": {
            "@language": "en",
            "@vocab": "https://schema.org/",
            "cr": "http://mlcommons.org/croissant/",
        },
        "@type": "Dataset",
        "name": "fyi-archive-nz",
        "description": "Read-only archive of public fyi.org.nz OIA request records.",
        "license": "https://github.com/edithatogo/fyi-archive/blob/main/LICENSE",
        "distribution": [
            {
                "@type": "cr:FileObject",
                "name": "latest_manifest",
                "contentUrl": "manifests/latest_manifest.parquet",
                "encodingFormat": "application/vnd.apache.parquet",
            },
        ],
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "name": "requests",
                "description": f"{manifest['meta']['record_count']} request records",
            },
        ],
    }


def write_metadata(manifest_path: Path, output_dir: Path) -> None:
    """Write Croissant, Frictionless, and schema.org metadata files."""
    manifest = load_manifest(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "croissant.jsonld": build_croissant(manifest),
        "frictionless.json": build_frictionless(manifest),
        "schema.org.jsonld": build_schema_org(manifest),
    }
    for name, data in outputs.items():
        (output_dir / name).write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
