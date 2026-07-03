#!/usr/bin/env python3
"""Validate that required GitHub Actions secrets are present for publishing."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    """Check required publishing secrets and report status."""
    required_services = [
        {"name": "HF_TOKEN", "label": "Hugging Face"},
        {"name": "HF_REPO_ID", "label": "Hugging Face repository"},
        {"name": "ZENODO_TOKEN", "label": "Zenodo production"},
        {"name": "OSF_TOKEN", "label": "OSF"},
        {"name": "OSF_PARENT_ID", "label": "OSF parent project"},
    ]

    optional_services = [
        {"name": "ZENODO_SANDBOX_TOKEN", "label": "Zenodo sandbox (for rehearsal)"},
    ]

    missing_required_services = []
    missing_optional_services = []

    for item in required_services:
        name = item["name"]
        service = item["label"]
        if not os.environ.get(name):
            missing_required_services.append(service)

    for item in optional_services:
        name = item["name"]
        service = item["label"]
        if not os.environ.get(name):
            missing_optional_services.append(service)

    result = {
        "valid": len(missing_required_services) == 0,
        "missing_required_services": missing_required_services,
        "missing_optional_services": missing_optional_services,
    }

    if result["valid"]:
        print("All required publishing secrets are configured.")
        if optional_services:
            print("Optional publishing secrets are configured or omitted.")
    else:
        print("Missing required publishing services:")
        for service in missing_required_services:
            print(f"  - {service}")

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
