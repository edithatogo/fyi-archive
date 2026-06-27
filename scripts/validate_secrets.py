#!/usr/bin/env python3
"""Validate that required GitHub Actions secrets are present for publishing."""

from __future__ import annotations

import json
import os
import sys


def main() -> None:
    """Check required publishing secrets and report status."""
    required_secrets = [
        ("HF_TOKEN", "Hugging Face"),
        ("OSF_TOKEN", "OSF"),
    ]

    optional_secrets = [
        ("ZENODO_TOKEN", "Zenodo production"),
        ("ZENODO_SANDBOX_TOKEN", "Zenodo sandbox (for rehearsal)"),
    ]

    missing_required = []
    missing_optional = []

    for name, service in required_secrets:
        if not os.environ.get(name):
            missing_required.append(f"{name} ({service})")

    for name, service in optional_secrets:
        if not os.environ.get(name):
            missing_optional.append(f"{name} ({service})")

    result = {
        "valid": len(missing_required) == 0,
        "missing_required": missing_required,
        "missing_optional": missing_optional,
    }

    if result["valid"]:
        print("All required publishing secrets are configured.")
        for name, service in optional_secrets:
            is_present = name in os.environ
            status = "present" if is_present else "not configured (optional)"
            print(f"  {service}: {status}")
    else:
        print("Missing required secrets for publishing:")
        for secret in missing_required:
            print(f"  - {secret}")

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()