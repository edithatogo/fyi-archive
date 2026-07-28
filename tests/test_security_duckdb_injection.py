import duckdb
import pytest

from fyi_archive.publish.export import build_duckdb_export


@pytest.mark.security
def test_build_duckdb_export_no_sql_injection(tmp_path):
    """Test that build_duckdb_export is not vulnerable to SQL injection."""
    # Create a malicious filename that tries to inject SQL
    # If parameterization wasn't used, this might try to execute DROP TABLE or similar
    malicious_path = (
        tmp_path
        / "valid_name'; DROP TABLE IF EXISTS dummy; SELECT * FROM read_parquet('other.parquet"
    )

    # We just need it to be a valid file so path operations work
    # DuckDB read_parquet on an empty file might fail with a different error,
    # but it shouldn't execute the injected SQL.
    malicious_path.touch()

    output_db = tmp_path / "output.duckdb"

    # If the injection works, it might execute the drop table or have a syntax error
    # With parameterization, DuckDB will just complain about the file format/contents
    # because it treats the entire string as a literal filename
    with pytest.raises(duckdb.InvalidInputException, match="too small to be a Parquet file"):
        build_duckdb_export(manifest_parquet=malicious_path, output_path=output_db)
