"""Orchestration CLI.

This is a structural stub. The real subcommands are implemented by the conductor
tracks (`historical_seed_orchestration`, `prospective_sync_orchestration`,
`multi_mirror_publish`, `observability_quality`). Each subcommand shells out to
`fyi-cli` for the heavy lifting; this layer only orchestrates + publishes.
"""

from __future__ import annotations

import typer

from fyi_archive.commands.backfill import app as backfill_app
from fyi_archive.commands.doctor import app as doctor_app
from fyi_archive.commands.backfill import app as backfill_app
from fyi_archive.commands.manifest import app as manifest_app
from fyi_archive.commands.publish import app as publish_app
from fyi_archive.commands.seed import app as seed_app
from fyi_archive.commands.sync import app as sync_app
from fyi_archive.version import __version__

app = typer.Typer(
    name="fyi-archive",
    help="Orchestration + distribution for the fyi.org.nz read-only archive.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


app.add_typer(doctor_app, name="doctor")
app.add_typer(backfill_app, name="backfill")
app.add_typer(manifest_app, name="manifest")
app.add_typer(publish_app, name="publish")
app.add_typer(seed_app, name="seed")
app.add_typer(sync_app, name="sync")


if __name__ == "__main__":
    app()
