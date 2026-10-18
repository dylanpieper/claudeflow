import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "az-guard.sh"
BASH = shutil.which("bash") or "/bin/bash"
JQ_DIR = str(Path(shutil.which("jq")).parent)


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
        "az group delete --name rg1 --yes",
        "az login",
        "az account set --subscription x",
        "az vm update -g rg -n vm --set tags.a=b",
        "az storage blob upload -f a -c c",
        "az rest --method post --url x",
        "az group list && az group delete -n rg",
        "sudo az vm deallocate -g rg -n vm",
        "/usr/local/bin/az vm delete -g rg -n vm",
        "x=1; (az group delete -n rg)",
    ],
)
def test_write_asks(command):
    assert decision(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "AZURE_CONFIG_DIR=x az group delete -n g --yes",
        "env SUBSCRIPTION=y az vm delete -n v",
        "timeout 60 az vm delete -n v",
        "nohup az vm delete -n v",
        "echo rg | xargs az group delete -n",
        "if az group delete -n g; then echo ok; fi",
        "{ az group delete -n g; }",
        "! az group delete -n g",
        'bash -c "az vm delete -n v"',
        "echo $(az group delete -n g)",
        "az \\\n  group delete -n g",
    ],
)
def test_az_in_any_position_asks(command):
    assert decision(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "az group list -o table",
        "az vm show -g rg -n vm1",
        "az account show",
        "az keyvault secret list --vault-name kv",
        "az sql db list-editions -l eastus",
        "az --version",
        "az",
        "az group list > out.json",
        "az account show 2>/dev/null",
        "az group list 2>&1 | head",
        "id=$(az account show --query id -o tsv)",
        "lazy group delete",
        "cat azure.txt",
        "git status",
    ],
)
def test_read_only_passes(command):
    assert decision(command) is None


def fake_az(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    az = bin_dir / "az"
    account = {"tenantId": "t-1", "tenantDisplayName": "Contoso", "name": "Prod", "id": "s-1", "user": {"name": "me@x"}}
    az.write_text(f"#!/bin/sh\necho '{json.dumps(account)}'\n")
    az.chmod(0o755)
    return f"{bin_dir}:{JQ_DIR}:/usr/bin:/bin"


def test_reason_shows_tenant_and_subscription(tmp_path):
    out = run("az group delete -n g --subscription other-sub", path=fake_az(tmp_path))
    reason = out["permissionDecisionReason"]
    assert "Tenant: Contoso (t-1)" in reason
    assert "Subscription: Prod (s-1)" in reason
    assert "User: me@x" in reason
    assert "--subscription other-sub" in reason


def test_subscription_comes_from_the_az_call(tmp_path):
    out = run("az group delete -n g; echo --subscription nope", path=fake_az(tmp_path))
    assert "nope" not in out["permissionDecisionReason"]


def test_reason_without_az_cli():
    out = run("az group delete -n g", path=f"{JQ_DIR}:/usr/bin:/bin")
    assert "not on PATH" in out["permissionDecisionReason"]


def test_missing_jq_asks_for_az_commands():
    out = run("az group delete -n g", path="/nonexistent")
    assert out["permissionDecision"] == "ask"
    assert "jq is not on PATH" in out["permissionDecisionReason"]


def test_missing_jq_passes_other_commands():
    assert run("ls", path="/nonexistent") is None
