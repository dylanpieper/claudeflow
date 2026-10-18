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


def _run(command, cwd):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}),
        capture_output=True,
        text=True,
        check=True,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def decision(command, cwd):
    out = _run(command, cwd)
    return out and out["permissionDecision"]


def reason(command, cwd):
    return _run(command, cwd)["permissionDecisionReason"]


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


@pytest.fixture
def detached(tmp_path):
    repo = make_repo(tmp_path / "detached")
    git(repo, "switch", "-q", "--detach")
    return repo


@pytest.mark.parametrize(
    "command",
    [
        "git push origin HEAD:main",
        "git push origin feature:main",
        "git push origin :main",
        "git push --all",
        "git push origin HEAD",
    ],
)
def test_detached_head_push_to_default_asks(detached, command):
    assert decision(command, detached) == "ask"


@pytest.mark.parametrize("command", ["git merge feature", "git push origin HEAD:feature"])
def test_detached_head_other_work_passes(detached, command):
    assert decision(command, detached) is None


def test_option_value_is_not_the_remote(tmp_path):
    repo = make_repo(tmp_path / "trunk", default="trunk", checkout="feature")
    assert decision("git push -o ci.skip origin trunk", repo) == "ask"
    assert decision("git push --push-option ci.skip origin feature", repo) is None


def test_cd_sets_the_repo(on_main, on_feature):
    assert decision(f"cd {on_main} && git merge feature", on_feature) == "ask"
    assert decision(f"cd {on_feature} && git merge main", on_main) is None


@pytest.mark.parametrize(
    "command",
    [
        "env git merge feature",
        "command git merge feature",
        "sudo git merge feature",
        "if true; then git merge feature; fi",
        "(git merge feature)",
        "echo $(git merge feature)",
        "! git merge feature",
        "git commit -m 'a; b' && git merge feature",
    ],
)
def test_wrappers_keywords_and_subshells_ask(on_main, command):
    assert decision(command, on_main) == "ask"


def test_line_continuation_is_joined(on_feature):
    assert decision("git push \\\n  origin main", on_feature) == "ask"


def test_for_loop_push_asks(on_feature):
    assert decision("for b in x; do git push origin main; done", on_feature) == "ask"


def test_cd_in_subshell_stays_in_subshell(on_main, on_feature):
    assert decision(f"(cd {on_feature} && git status) && git merge feature", on_main) == "ask"
    assert decision(f"(cd {on_main} && git status) && git merge main", on_feature) is None


def test_cd_dash_returns_to_previous_dir(on_main, on_feature):
    assert decision(f"cd {on_feature} && cd - && git merge feature", on_main) == "ask"


def test_work_tree_does_not_change_the_repo(on_main, on_feature):
    assert decision(f"git --work-tree {on_feature} merge feature", on_main) == "ask"


def test_pull_recurse_submodules_takes_no_separate_value(on_main):
    assert decision("git pull --recurse-submodules origin feature", on_main) == "ask"


def test_push_recurse_submodules_takes_a_value(tmp_path):
    repo = make_repo(tmp_path / "trunk", default="trunk", checkout="feature")
    assert decision("git push --recurse-submodules on-demand origin trunk", repo) == "ask"


def test_cd_in_backticks_stays_in_backticks(on_main, on_feature):
    assert decision(f"x=`cd {on_feature}; pwd`; git merge feature", on_main) == "ask"


def test_quote_in_branch_name_gives_valid_json(on_main):
    assert decision("git pull origin 'feat\"x'", on_main) == "ask"


@pytest.mark.parametrize("flag", ["--git-dir {repo}/.git", "--git-dir={repo}/.git"])
def test_git_dir_sets_the_repo(on_main, on_feature, flag):
    assert decision(f"git {flag.format(repo=on_main)} merge feature", on_feature) == "ask"
    assert decision(f"git {flag.format(repo=on_feature)} merge main", on_main) is None


def test_more_option_values_are_not_the_remote(tmp_path):
    repo = make_repo(tmp_path / "trunk", default="trunk", checkout="feature")
    assert decision("git push --server-option x -j 4 origin trunk", repo) == "ask"


def run_without_jq(command, cwd):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)}),
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent"},
        check=True,
    )
    return result.stdout


def test_missing_jq_asks_for_git_commands(on_main):
    out = json.loads(run_without_jq("git merge feature", on_main))
    assert out["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "jq is not on PATH" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_missing_jq_passes_other_commands(on_main):
    assert run_without_jq("ls", on_main) == ""


def test_missing_jq_ignores_git_in_the_cwd(tmp_path):
    cwd = tmp_path / "github" / "proj"
    cwd.mkdir(parents=True)
    assert run_without_jq("ls", cwd) == ""


@pytest.fixture
def branches(tmp_path):
    """A repo on main with a merged branch `done` and an unmerged branch `wip`, both also on origin."""
    repo = make_repo(tmp_path / "branches")
    git(repo, "branch", "done")
    git(repo, "update-ref", "refs/remotes/origin/done", "refs/heads/done")
    git(repo, "switch", "-q", "-c", "wip")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "wip")
    git(repo, "update-ref", "refs/remotes/origin/wip", "refs/heads/wip")
    git(repo, "switch", "-q", "main")
    return repo


@pytest.mark.parametrize(
    "command",
    [
        "git branch -d done",
        "git branch -D done",
        "git branch --delete --force done",
        "git push origin --delete done",
        "git push origin -d done",
        "git push origin :done",
        "git branch -dr origin/wip",
    ],
)
def test_deleting_a_merged_branch_passes(branches, command):
    assert decision(command, branches) is None


@pytest.mark.parametrize(
    "command",
    [
        "git branch -d wip",
        "git branch -D wip",
        "git branch -D done wip",
        "git push origin --delete wip",
        "git push origin :wip",
        "git push origin --delete gone",
        "git branch -D gone",
        "git branch -D main",
        "git push origin --delete main",
        "git push origin :main",
    ],
)
def test_deleting_an_unmerged_or_default_branch_asks(branches, command):
    assert decision(command, branches) == "ask"


def test_branch_without_delete_passes(branches):
    assert decision("git branch -m done finished", branches) is None
    assert decision("git branch new-work", branches) is None


@pytest.mark.parametrize(
    "command",
    [
        "git push -f",
        "git push --force origin feature",
        "git push --force-with-lease",
        "git push --force-with-lease origin feature",
        "git push --force-with-lease=feature:abc123 origin feature",
        "git push --force-with-lease --force-if-includes origin feature",
        "git push origin +feature",
        "git push origin +HEAD:feature",
        "git -C . push --force-with-lease",
        "git commit --amend --no-edit && git push --force-with-lease",
    ],
)
def test_force_push_to_any_branch_asks(on_feature, command):
    assert decision(command, on_feature) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git push",
        "git push -u origin feature",
        "git push --force-if-includes origin feature",
        "git branch -f other HEAD",
    ],
)
def test_push_without_force_passes(on_feature, command):
    assert decision(command, on_feature) is None


@pytest.mark.parametrize("command", ["git push -fu origin feature", "git push -uf origin feature", "git push -fq"])
def test_bundled_force_flag_asks(on_feature, command):
    assert decision(command, on_feature) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git push --force-with-lease origin main",
        "git push origin +main",
        "git push -f origin HEAD:refs/heads/main",
    ],
)
def test_force_push_to_default_names_it(on_feature, command):
    assert reason(command, on_feature) == "Approve this force push to the default branch (main) on origin."


def test_force_push_on_default_names_it(on_main):
    assert reason("git push --force-with-lease", on_main) == "Approve this force push to the default branch (main) on origin."


def test_force_push_to_feature_uses_general_message(on_feature):
    assert "rewrites commits on the remote branch" in reason("git push --force-with-lease origin feature", on_feature)


def test_force_push_of_all_branches_names_default(on_feature):
    expected = "Approve this force push of all branches, which includes the default branch."
    assert reason("git push -f --all", on_feature) == expected
    assert reason("git push --mirror --force", on_feature) == expected


def test_force_push_of_tags_on_default_does_not_name_it(on_main):
    assert "rewrites commits on the remote branch" in reason("git push --force --tags", on_main)


def test_push_option_value_with_f_is_not_force(on_feature):
    assert decision("git push -ofoo origin feature", on_feature) is None
