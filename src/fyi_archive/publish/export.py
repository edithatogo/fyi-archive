"""DuckDB export helpers."""

from __future__ import annotations

from pathlib import Path

import duckdb


def build_duckdb_export(*, manifest_parquet: Path, output_path: Path) -> None:
    """Create a self-contained DuckDB export from the manifest Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(output_path))
    try:
        connection.execute("DROP VIEW IF EXISTS requests")
        connection.execute("DROP TABLE IF EXISTS requests")
        connection.execute(
            "CREATE TABLE requests AS SELECT * FROM read_parquet(?)",
            [str(manifest_parquet)],
        )
    finally:
        connection.close()
