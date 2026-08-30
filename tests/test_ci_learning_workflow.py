"""Failure-reporting workflow inputs must remain data, never shell programs."""

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def test_workflow_name_is_not_executed(tmp_path: Path) -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci-learning-candidates.yml").read_text())
    step = next(
        step
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if step.get("name") == "Record CI failure candidate"
    )
    script = step["run"]
    executable = tmp_path / "python3"
    executable.write_text(
        f'#!{sys.executable}\nimport json,os,sys\nopen(os.environ["CAPTURE_PATH"],"w").write(json.dumps(sys.argv[1:]))\n'
    )
    executable.chmod(0o755)
    captured = tmp_path / "args.json"
    unsafe_name = 'CI $(touch executed) `touch executed` "quoted"'
    environment = {
        **os.environ,
        "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
        "CAPTURE_PATH": str(captured),
        "CI_WORKFLOW_NAME": unsafe_name,
        "CI_RUN_ID": "123",
        "CI_RUN_URL": "https://example.org/run/123",
        "CI_ACTOR": "fixture",
        "CI_HEAD_SHA": "a" * 40,
    }
    result = subprocess.run(
        ["bash", "-euc", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert not (tmp_path / "executed").exists()
    arguments = json.loads(captured.read_text())
    assert (
        arguments[arguments.index("--message") + 1]
        == "CI failure summary candidate for " + unsafe_name
    )
