import duckdb
import polars as pl
import pytest

from fyi_archive.publish.export import build_duckdb_export


@pytest.mark.security
def test_build_duckdb_export_no_sql_injection(tmp_path) -> None:
    """Test that build_duckdb_export is not vulnerable to SQL injection."""
    malicious_path = tmp_path / "records'; DROP TABLE requests; --.parquet"
    pl.DataFrame({"request_id": [1]}).write_parquet(malicious_path)
    output_db = tmp_path / "output.duckdb"

    build_duckdb_export(manifest_parquet=malicious_path, output_path=output_db)

    with duckdb.connect(str(output_db), read_only=True) as connection:
        assert connection.execute("SELECT request_id FROM requests").fetchall() == [(1,)]
