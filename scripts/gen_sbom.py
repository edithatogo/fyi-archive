#!/usr/bin/env python3
"""Generate CycloneDX SBOM for Python environment."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Generate SBOM using cyclonedx-py."""
    output_path = Path("dist/sbom.cdx.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "cyclonedx-py",
                "environment",
                "--output-format",
                "json",
                "--output-file",
                str(output_path),
            ],
            check=True,
        )
        print(f"SBOM written to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"SBOM generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()