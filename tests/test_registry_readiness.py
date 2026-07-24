import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_registry_readiness",
    Path(__file__).parents[1] / "scripts" / "check_registry_readiness.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Could not load registry-readiness script")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
check = _MODULE.check


def test_archive_registry_readiness_contract() -> None:
    check()
