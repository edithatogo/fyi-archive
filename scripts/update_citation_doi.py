#!/usr/bin/env python3
"""Update citation metadata after a Zenodo DOI is published."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update CITATION.cff with a Zenodo DOI.")
    parser.add_argument("doi", help="Zenodo DOI, e.g. 10.5281/zenodo.1234567")
    parser.add_argument("--citation", default="CITATION.cff", help="CITATION.cff path.")
    return parser.parse_args()


def doi_url(doi: str) -> str:
    normalized = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if not DOI_PATTERN.match(normalized):
        msg = f"Invalid DOI: {doi}"
        raise ValueError(msg)
    return f"https://doi.org/{normalized}"


def update_citation_text(text: str, doi: str) -> str:
    url = doi_url(doi)
    lines = text.splitlines()
    output: list[str] = []
    updated = False

    for line in lines:
        if line.startswith(("url:", "# url:")):
            output.append(f'url: "{url}"')
            updated = True
        else:
            output.append(line)

    if not updated:
        output.append(f'url: "{url}"')

    return "\n".join(output).rstrip() + "\n"


def main() -> None:
    args = parse_args()
    citation_path = Path(args.citation)
    text = citation_path.read_text(encoding="utf-8")
    citation_path.write_text(update_citation_text(text, args.doi), encoding="utf-8")
    print(f"Updated {citation_path} with {doi_url(args.doi)}")


if __name__ == "__main__":
    main()
