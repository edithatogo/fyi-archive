"""Render verified sync metadata into the Hugging Face dataset card."""

from __future__ import annotations

START = "<!-- fyi-archive:generated-metadata:start -->"
END = "<!-- fyi-archive:generated-metadata:end -->"


def render(card: str, summary: dict[str, object]) -> str:
    """Replace the generated metadata block without changing other card text."""
    generated = "\n".join([
        START,
        "## Verified snapshot metadata",
        "",
        f"- Publication status: **{'verified' if summary['verified'] else 'unverified'}**",
        f"- Snapshot records: **{int(str(summary['record_count'])):,}**",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Manifest SHA-256: `{summary['manifest_sha256']}`",
        "",
        (
            "This metadata describes the current verified incremental snapshot; it does not "
            "imply that historical coverage is complete."
        ),
        END,
    ])
    if START in card and END in card:
        before = card.split(START, 1)[0].rstrip()
        after = card.split(END, 1)[1].lstrip()
        return f"{before}\n\n{generated}\n\n{after}"
    return f"{card.rstrip()}\n\n{generated}\n"
