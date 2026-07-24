from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_renovate_configuration_covers_locked_dependencies() -> None:
    config = json.loads((ROOT / "renovate.json").read_text(encoding="utf-8"))
    assert config["$schema"] == "https://docs.renovatebot.com/renovate-schema.json"
    assert {"pep621", "github-actions", "pre-commit"} <= set(config["enabledManagers"])
    assert config["lockFileMaintenance"]["enabled"] is True
    assert config["timezone"] == "Australia/Sydney"
    assert all("matchPackagePatterns" not in rule for rule in config["packageRules"])
    pinned = next(
        rule for rule in config["packageRules"] if "fyi-cli" in rule.get("matchPackageNames", [])
    )
    assert pinned["enabled"] is False


def test_codecov_policy_matches_repository_coverage_floor() -> None:
    policy = (ROOT / "codecov.yml").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert policy.count("target: 90%") == 2
    assert "require_ci_to_pass: true" in policy
    assert "if_ci_failed: error" in policy
    assert "if: matrix.python-version == '3.12'" in workflow
    assert "disable_search: true" in workflow
    assert "fail_ci_if_error: true" in workflow
    assert "flags: unit" in workflow
