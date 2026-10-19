import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "statusline.sh"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
FAR_FUTURE = 4102444800
BASH = shutil.which("bash") or "/bin/bash"


def run(payload, config_dir, path=None, home=None, extra=None):
    env = {"PATH": path or os.environ["PATH"], "CLAUDE_CONFIG_DIR": str(config_dir), **(extra or {})}
    if home:
        env["HOME"] = str(home)
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return ANSI.sub("", result.stdout).strip()


FULL = {
    "session_id": "abc",
    "model": {"display_name": "Opus"},
    "workspace": {"current_dir": "/a/proj"},
    "context_window": {"used_percentage": 42.6, "total_input_tokens": 84000, "context_window_size": 200000},
    "rate_limits": {
        "five_hour": {"used_percentage": 61.2, "resets_at": FAR_FUTURE},
        "seven_day": {"used_percentage": 12, "resets_at": FAR_FUTURE},
    },
}


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (FULL, r"^Opus \| proj \| ctx 43%\(84k/200k\) \| 5h 61%\(\S+\) \| 7d 12%\(\S+\)$"),
        (
            {**FULL, "context_window": {"used_percentage": None, "total_input_tokens": 84000, "context_window_size": 200000}},
            r"^Opus \| proj \| 5h 61%\(\S+\) \| 7d 12%\(\S+\)$",
        ),
        ({k: v for k, v in FULL.items() if k != "rate_limits"}, r"^Opus \| proj \| ctx 43%\(84k/200k\)$"),
        (
            {**FULL, "rate_limits": {"seven_day": {"used_percentage": 12, "resets_at": FAR_FUTURE}}},
            r"^Opus \| proj \| ctx 43%\(84k/200k\) \| 7d 12%\(\S+\)$",
        ),
        ({**FULL, "session_id": "", "workspace": {"current_dir": "/"}}, r"^Opus \| ctx 43%\(84k/200k\) \| 5h 61%"),
        ({}, r"^$"),
    ],
    ids=["full", "null-ctx-pct", "no-rate-limits", "seven-day-only", "root-cwd", "empty"],
)
@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_output(payload, expected, tmp_path):
    assert re.search(expected, run(payload, tmp_path))


def test_jq_missing(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "cat").symlink_to(shutil.which("cat"))
    assert run(FULL, tmp_path, path=str(bin_dir)) == "statusline: jq missing"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_caveman_badge(tmp_path):
    sessions = tmp_path / ".caveman-sessions"
    sessions.mkdir()
    (sessions / "abc.mode").write_text("ultra\n")
    assert run(FULL, tmp_path).startswith("Opus | proj | Ultracave | ctx")


def transcript(path, command):
    record = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": "Bash", "input": {"command": command}}]}}
    path.write_text(json.dumps(record, separators=(",", ":")) + "\n")
    return path


@pytest.fixture
def cloud(tmp_path):
    home = tmp_path / "home"
    (home / ".sf").mkdir(parents=True)
    (home / ".sf" / "config.json").write_text('{"target-org": "global-org"}')
    (home / ".azure").mkdir()
    profile = {
        "subscriptions": [
            {"name": "Other", "isDefault": False, "tenantId": "t0"},
            {"name": "Prod Sub", "isDefault": True, "tenantId": "1111", "tenantDefaultDomain": "contoso.onmicrosoft.com"},
        ]
    }
    (home / ".azure" / "azureProfile.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(profile).encode())
    project = tmp_path / "my proj"
    (project / ".sf").mkdir(parents=True)
    (project / "sub").mkdir()
    (project / "sfdx-project.json").write_text("{}")
    (project / ".sf" / "config.json").write_text('{"target-org": "dev-scratch"}')
    plain = tmp_path / "plain"
    plain.mkdir()
    return tmp_path, home, project, plain


@pytest.mark.parametrize(
    ("where", "command", "expected"),
    [
        ("project/sub", "ls", r"^Opus \| sub \| sf dev-scratch$"),
        ("plain", "ln -sf a b; echo graz baz/az x", r"^Opus \| plain$"),
        ("plain", "cd x && az account show\nsfdx force:org:list", r"^Opus \| plain \| sf global-org \| az Prod Sub\(contoso\.onmicrosoft\.com\)$"),
        ("project", "az vm list", r"^Opus \| my proj \| sf dev-scratch \| az Prod Sub\(contoso\.onmicrosoft\.com\)$"),
        ("plain", "sf org list", r"^Opus \| plain \| sf global-org$"),
    ],
    ids=["sf-project", "no-cli-use", "both-used", "project-and-az", "sf-used"],
)
@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_cloud_context(cloud, where, command, expected):
    tmp, home, project, plain = cloud
    cwd = {"project": project, "project/sub": project / "sub", "plain": plain}[where]
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": str(cwd)}, "transcript_path": str(transcript(tmp / "t.jsonl", command))}
    assert re.search(expected, run(payload, tmp, home=home))


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_cloud_context_after_escaped_quotes(cloud):
    tmp, home, project, plain = cloud
    command = 'git commit -m "msg" && bash -c "az account show"'
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": str(plain)}, "transcript_path": str(transcript(tmp / "t.jsonl", command))}
    assert "az Prod Sub" in run(payload, tmp, home=home)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_relative_cwd_does_not_hang(cloud):
    tmp, home, project, plain = cloud
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": "rel/dir"}}
    assert run(payload, tmp, home=home) == "Opus | dir"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_control_characters_are_removed(cloud):
    tmp, home, project, plain = cloud
    (project / ".sf" / "config.json").write_text(json.dumps({"target-org": "evil\u001b]0;pwn\u0007org"}))
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": str(project)}}
    result = subprocess.run(
        [BASH, str(SCRIPT)], input=json.dumps(payload), capture_output=True, text=True,
        env={"PATH": os.environ["PATH"], "CLAUDE_CONFIG_DIR": str(tmp), "HOME": str(home)}, check=True,
    )
    assert "\u0007" not in result.stdout
    assert "\u001b]" not in result.stdout
    assert "sf evil]0;pwnorg" in ANSI.sub("", result.stdout)
    (project / ".sf" / "config.json").write_text(json.dumps({"target-org": "c1\u009b31morg"}))
    assert "\u009b" not in run(payload, tmp, home=home)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_cache_reads_only_new_lines(cloud):
    tmp, home, project, plain = cloud
    path = transcript(tmp / "t.jsonl", "ls")
    payload = {"session_id": "s1", "model": {"display_name": "Opus"}, "workspace": {"current_dir": str(plain)}, "transcript_path": str(path)}
    assert run(payload, tmp, home=home) == "Opus | plain"
    assert (tmp / ".statusline-cli" / "s1").read_text().split()[0] == str(path.stat().st_size)
    record = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u", "name": "Bash", "input": {"command": "az vm list"}}]}}
    with path.open("a") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")
    assert "az Prod Sub" in run(payload, tmp, home=home)
    path.write_text("")
    assert run(payload, tmp, home=home) == "Opus | plain"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_record_split_at_cache_offset_is_found(cloud):
    tmp, home, project, plain = cloud
    record = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u", "name": "Bash", "input": {"command": "az vm list"}}]}}
    line = json.dumps(record, separators=(",", ":")) + "\n"
    path = tmp / "t.jsonl"
    half = len(line) // 2
    path.write_text(line[:half])
    payload = {"session_id": "s2", "model": {"display_name": "Opus"}, "workspace": {"current_dir": str(plain)}, "transcript_path": str(path)}
    assert run(payload, tmp, home=home) == "Opus | plain"
    with path.open("a") as f:
        f.write(line[half:])
    assert "az Prod Sub" in run(payload, tmp, home=home)


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_old_caches_are_deleted(cloud):
    tmp, home, project, plain = cloud
    folder = tmp / ".statusline-cli"
    folder.mkdir()
    old, recent = folder / "old", folder / "recent"
    old.write_text("0 ")
    recent.write_text("0 ")
    os.utime(old, (1_000_000, 1_000_000))
    path = transcript(tmp / "t.jsonl", "ls")
    payload = {"session_id": "s3", "model": {"display_name": "Opus"}, "workspace": {"current_dir": str(plain)}, "transcript_path": str(path)}
    run(payload, tmp, home=home)
    assert not old.exists()
    assert recent.exists()
    assert (folder / "s3").exists()


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_config_fallbacks(cloud):
    tmp, home, project, plain = cloud
    used = str(transcript(tmp / "t.jsonl", "az vm list; sf org list"))
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": str(project)}, "transcript_path": used}

    (project / ".sf" / "config.json").write_text('{"org-api-version": "60.0"}')
    assert "sf global-org" in run(payload, tmp, home=home)

    (home / ".sf" / "config.json").unlink()
    (home / ".sfdx").mkdir()
    (home / ".sfdx" / "sfdx-config.json").write_text('{"defaultusername": "legacy-user"}')
    assert "sf legacy-user" in run(payload, tmp, home=home)

    other = tmp / "azcfg"
    other.mkdir()
    (other / "azureProfile.json").write_text(json.dumps({"subscriptions": [{"name": "Dev", "isDefault": True, "tenantId": "abcd"}]}))
    assert "az Dev(abcd)" in run(payload, tmp, home=home, extra={"AZURE_CONFIG_DIR": str(other)})

    (other / "azureProfile.json").write_text(json.dumps({"subscriptions": [{"name": "Dev", "isDefault": False, "tenantId": "abcd"}]}))
    assert not re.search(r"\| az ", run(payload, tmp, home=home, extra={"AZURE_CONFIG_DIR": str(other)}))

    (other / "azureProfile.json").write_text(
        json.dumps({"subscriptions": [{"name": "Dev", "isDefault": True, "tenantId": "abcd", "tenantDisplayName": "Contoso"}]})
    )
    assert "az Dev(Contoso)" in run(payload, tmp, home=home, extra={"AZURE_CONFIG_DIR": str(other)})


def bang(path, command):
    record = {"type": "user", "message": {"role": "user", "content": f"<bash-input> {command}</bash-input>"}}
    path.write_text(json.dumps(record, separators=(",", ":")) + "\n")
    return path


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("az login", r"\| az Prod Sub"),
        ("sf org list", r"\| sf global-org"),
        ("echo azure is nice", r"^Opus \| plain$"),
    ],
    ids=["az", "sf", "no-cli"],
)
@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_bang_command_turns_on_cloud_context(cloud, command, expected):
    tmp, home, project, plain = cloud
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": str(plain)}, "transcript_path": str(bang(tmp / "t.jsonl", command))}
    assert re.search(expected, run(payload, tmp, home=home))


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")
def test_quoted_bash_input_in_tool_output_is_ignored(cloud):
    tmp, home, project, plain = cloud
    record = {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t", "content": "<bash-input> az login</bash-input>"}]}}
    path = tmp / "t.jsonl"
    path.write_text(json.dumps(record, separators=(",", ":")) + "\n")
    payload = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": str(plain)}, "transcript_path": str(path)}
    assert run(payload, tmp, home=home) == "Opus | plain"
