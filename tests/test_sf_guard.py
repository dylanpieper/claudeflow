import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "sf-guard.sh"
BASH = shutil.which("bash") or "/bin/bash"
JQ = shutil.which("jq")
AWK = shutil.which("awk")
pytestmark = pytest.mark.skipif(JQ is None, reason="jq is not installed")


def tool_path(tmp_path, fakes=None):
    """Returns a PATH with only jq, awk, and the fake CLIs in `fakes` (name to stdout)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in (JQ, AWK):
        (bin_dir / Path(tool).name).symlink_to(tool)
    for name, stdout in (fakes or {}).items():
        cli = bin_dir / name
        cli.write_text(f"#!/bin/sh\necho '{stdout}'\n")
        cli.chmod(0o755)
    return str(bin_dir)


def run(command, path=None):
    env = {"PATH": path} if path else None
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/tmp"}),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def decision(command):
    out = run(command)
    return out and out["permissionDecision"]


@pytest.mark.parametrize(
    "command",
    [
        "sf project deploy start -o prod",
        "sf data delete record -s Account -i 001",
        'sf data update record -s Account -i 001 -v "Name=x"',
        "sf apex run -f script.apex",
        "sf org delete scratch -o s1",
        "sf config set target-org=prod",
        "sf config set target-org list",
        "sf package version create -p x",
        "sf package version promote -p x",
        "sf package version delete -p x",
        "sfdx force:package:version:create",
        "sfdx force:source:deploy -p src",
        "sf org list; sf project retrieve start",
        "sudo /usr/local/bin/sf org delete scratch",
        "SF_ORG=x sf project deploy start",
        "timeout 60 sf project deploy start",
        'bash -c "sf org delete scratch"',
    ],
)
def test_write_asks(command):
    assert decision(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "sf org list",
        "sf org display -o dev",
        'sf data query --query "SELECT Id FROM Account"',
        "sf data get record -s Account -i 001",
        "sf sobject describe -s Account",
        "sf project deploy preview",
        "sf package version list",
        "sf --version",
        "sfdx force:org:list",
        "sf org list > orgs.txt",
        "sf org list 2>/dev/null",
        "echo sf",
        "sfx run",
        "git status",
    ],
)
def test_read_only_passes(command):
    assert decision(command) is None


def fake_cli(tmp_path, name, org):
    return tool_path(tmp_path, {name: json.dumps({"result": [{"value": org}]})})


def reason(command, path=None):
    return run(command, path=path)["permissionDecisionReason"]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("sf project deploy start -o prod", "Target org (from -o): prod"),
        ("sf project deploy start --target-org=prod", "Target org (from --target-org): prod"),
        ("sfdx force:source:deploy -u prod", "Target org (from -u): prod"),
        ("sfdx force:source:deploy --targetusername prod", "Target org (from --targetusername): prod"),
        ("sf project deploy start -o --dry-run", "Target org (from -o): unknown"),
        ("sf project deploy start -o=prod", "Target org (from -o): prod"),
        ("sf project deploy start -oprod", "Target org (from -o): prod"),
        ("sfdx force:source:deploy -u=prod", "Target org (from -u): prod"),
        ("SF_TARGET_ORG=prod sf project deploy start", "Target org (from SF_TARGET_ORG): prod"),
        ('sf data update record -o prod -s Account -i 001 -v "Name=x"', "Target org (from -o): prod"),
        ("sf package version create -v hub", "Dev Hub (from -v): hub"),
        ("sf org create scratch -v=hub -f def.json", "Dev Hub (from -v): hub"),
        ("sf package create --target-dev-hub hub -n P", "Dev Hub (from --target-dev-hub): hub"),
    ],
)
def test_org_comes_from_the_command(command, expected, tmp_path):
    assert expected in reason(command, path=fake_cli(tmp_path, "sf", "dev-sandbox"))


def test_values_flag_is_not_an_org(tmp_path):
    text = reason('sf data update record -o prod -s Account -i 001 -v "Name=x"', path=fake_cli(tmp_path, "sf", "dev"))
    assert "Name=x" not in text
    assert "Dev Hub" not in text


def test_org_flag_from_other_command_is_ignored(tmp_path):
    text = reason("sort -o out.txt data; sf project deploy start", path=fake_cli(tmp_path, "sf", "dev-sandbox"))
    assert "out.txt" not in text
    assert "Target org (default): dev-sandbox" in text


def test_default_org_from_sfdx(tmp_path):
    text = reason("sfdx force:source:deploy -p src", path=fake_cli(tmp_path, "sfdx", "legacy-org"))
    assert "Target org (default): legacy-org" in text


def test_reason_without_cli(tmp_path):
    assert "not on PATH" in reason("sf project deploy start", path=tool_path(tmp_path))


def test_missing_jq_asks_for_sf_commands():
    out = run("sf org delete scratch", path="/nonexistent")
    assert out["permissionDecision"] == "ask"
    assert "jq is not on PATH" in out["permissionDecisionReason"]


def test_missing_jq_passes_other_commands():
    assert run("ls", path="/nonexistent") is None
