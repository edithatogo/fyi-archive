"""DuckDB export helpers."""

from __future__ import annotations

from pathlib import Path

import duckdb


def build_duckdb_export(*, manifest_parquet: Path, output_path: Path) -> None:
    """Create a read-only DuckDB export backed by the manifest Parquet."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_literal = str(manifest_parquet).replace("'", "''")
    connection = duckdb.connect(str(output_path))
    try:
        connection.execute("DROP VIEW IF EXISTS requests")
        connection.execute(
            f"CREATE VIEW requests AS SELECT * FROM read_parquet('{parquet_literal}')",  # noqa: S608 - DuckDB read_parquet path cannot be parameterized.
        )
    finally:
        connection.close()
