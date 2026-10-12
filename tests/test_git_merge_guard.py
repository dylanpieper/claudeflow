import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "git-merge-guard.sh"
BASH = shutil.which("bash") or "/bin/bash"


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def make_repo(path, default="main", checkout=None, remote_head=True):
    path.mkdir()
    git(path, "init", "-q", "-b", default)
    git(path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
    if remote_head:
        git(path, "update-ref", f"refs/remotes/origin/{default}", "HEAD")
        git(path, "symbolic-ref", "refs/remotes/origin/HEAD", f"refs/remotes/origin/{default}")
    if checkout:
        git(path, "switch", "-q", "-c", checkout)
    return path


def decision(command, cwd):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}),
        capture_output=True,
        text=True,
        check=True,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


@pytest.fixture
def on_main(tmp_path):
    return make_repo(tmp_path / "on_main")


@pytest.fixture
def on_feature(tmp_path):
    return make_repo(tmp_path / "on_feature", checkout="feature")


@pytest.mark.parametrize(
    "command",
    [
        "git merge feature",
        "git merge --no-ff feature",
        "git fetch && git merge origin/feature",
        "git pull origin feature",
        "git push",
        "git push origin",
        "git push -u origin main",
        "git push origin HEAD",
        "git push --all",
    ],
)
def test_default_branch_checked_out_asks(on_main, command):
    assert decision(command, on_main) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git push origin feature:main",
        "git push origin +feature:refs/heads/main",
        "git push origin HEAD:main",
        "git push origin main",
        "git status && git push origin feature:main",
        "git push --mirror",
    ],
)
def test_push_to_default_from_feature_asks(on_feature, command):
    assert decision(command, on_feature) == "ask"


def test_dash_c_uses_that_repo(on_main, on_feature):
    assert decision(f"git -C {on_main} merge feature", on_feature) == "ask"
    assert decision(f"git -C {on_feature} merge main", on_main) is None


@pytest.mark.parametrize(
    "command",
    [
        "git merge origin/main",
        "git pull",
        "git pull origin main",
        "git push",
        "git push -u origin feature",
        "git push origin HEAD",
        "git push origin --tags",
        "git status",
        "git log --oneline",
    ],
)
def test_feature_branch_work_passes(on_feature, command):
    assert decision(command, on_feature) is None


@pytest.mark.parametrize(
    "command",
    [
        "git pull",
        "git pull origin main",
        "git pull --rebase origin main",
        "git merge --abort",
        "git push origin --tags",
        "git push origin v1.0",
        "ls",
    ],
)
def test_sync_on_default_passes(on_main, command):
    assert decision(command, on_main) is None


def test_remote_head_names_default(tmp_path):
    repo = make_repo(tmp_path / "trunk", default="trunk")
    assert decision("git merge feature", repo) == "ask"
    git(repo, "switch", "-q", "-c", "main")
    assert decision("git merge feature", repo) is None


def test_main_is_default_without_remote_head(tmp_path):
    repo = make_repo(tmp_path / "local", remote_head=False)
    assert decision("git merge feature", repo) == "ask"


def test_outside_a_repo_passes(tmp_path):
    assert decision("git merge feature", tmp_path) is None
