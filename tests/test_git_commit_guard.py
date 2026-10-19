import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "git-commit-guard.sh"
BASH = shutil.which("bash") or "/bin/bash"

pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="jq not on PATH")

GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV)


def make_repo(path, branch="main", default=None, commit=True):
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", branch)
    if commit:
        git(path, "commit", "-q", "--allow-empty", "-m", "init")
    if default:
        git(path, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{default}")
    return path


def decide(command, cwd, home=None):
    env = {**GIT_ENV, "HOME": str(home)} if home else GIT_ENV
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}),
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    if not result.stdout.strip():
        return None, None
    out = json.loads(result.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


@pytest.mark.parametrize(
    ("branch", "default", "expected"),
    [
        ("main", "main", "deny"),
        ("trunk", "trunk", "deny"),
        ("feature", "main", "ask"),
        ("main", "trunk", "ask"),
        ("main", None, "deny"),
        ("master", None, "deny"),
        ("dev", None, "ask"),
    ],
    ids=["default-main", "default-trunk", "feature", "main-not-default", "no-origin-main", "no-origin-master", "no-origin-dev"],
)
def test_branch_decides(tmp_path, branch, default, expected):
    repo = make_repo(tmp_path / "repo", branch=branch, default=default)
    decision, reason = decide("git commit -m x", repo)
    assert decision == expected
    assert branch in reason


def test_deny_reason_names_the_branch(tmp_path):
    repo = make_repo(tmp_path / "repo", default="main")
    decision, reason = decide("git commit -m x", repo)
    assert decision == "deny"
    assert "origin/main" in reason


def test_repo_without_commits_asks(tmp_path):
    repo = make_repo(tmp_path / "repo", commit=False)
    assert decide("git commit -m x", repo)[0] == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git -C {repo} commit -m x",
        "git -C '{repo}' commit -m x",
        'git -C "{repo}" commit -m x',
        "git -C repo commit -m x",
        "git -C ~/repo commit -m x",
        "git -c user.name=x -C {repo} commit -m x",
        "git --no-pager -C {repo} commit -m x",
    ],
    ids=["absolute", "single-quoted", "double-quoted", "relative", "tilde", "config-then-path", "flag-then-path"],
)
def test_dash_c_path_picks_the_repo(tmp_path, command):
    make_repo(tmp_path / "repo", default="main")
    elsewhere = make_repo(tmp_path / "elsewhere", branch="feature", default="main")
    cwd = tmp_path if "C repo" in command else elsewhere
    assert decide(command.format(repo=tmp_path / "repo"), cwd, home=tmp_path)[0] == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "git commit",
        "git commit --amend --no-edit",
        "git add -A && git commit -m x",
        "git status; git commit -m x",
        "(git commit -m x)",
        "git --no-pager commit -m x",
        "git --git-dir=.git commit -m x",
        "git --git-dir .git commit -m x",
        "git --no-optional-locks commit -m x",
        "git -p commit -m x",
        "git -P -c core.editor=true commit",
    ],
)
def test_commit_forms_are_found(tmp_path, command):
    repo = make_repo(tmp_path / "repo", branch="feature", default="main")
    assert decide(command, repo)[0] == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git log --grep commit",
        "git commit-tree HEAD^{tree}",
        "gitk commit",
        "echo done",
        "",
    ],
)
def test_other_commands_get_no_decision(tmp_path, command):
    repo = make_repo(tmp_path / "repo", default="main")
    assert decide(command, repo) == (None, None)


def test_missing_jq_asks_for_commits(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("bash", "cat", "git"):
        (bin_dir / tool).symlink_to(shutil.which(tool))
    env = {**GIT_ENV, "PATH": str(bin_dir)}

    def run(command):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/"})
        return subprocess.run([BASH, str(SCRIPT)], input=payload, capture_output=True, text=True, check=True, env=env).stdout

    out = run("git commit -m x")
    assert json.loads(out)["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert run("ls -la") == ""
