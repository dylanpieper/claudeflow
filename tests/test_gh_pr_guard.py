import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "gh-pr-guard.sh"
BASH = shutil.which("bash") or "/bin/bash"


def decision(command):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/tmp"}),
        capture_output=True,
        text=True,
        check=True,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 12",
        "gh pr merge --squash --auto",
        "gh pr merge",
        "git push && gh pr merge 3 --delete-branch",
        "/opt/homebrew/bin/gh pr merge 4",
        "GH_REPO=a/b gh pr merge 5",
        "gh api -X PUT repos/o/r/pulls/7/merge",
        "gh api repos/o/r/pulls/7/merge --method PUT -f merge_method=squash",
        "gh api graphql -f query='mutation { mergePullRequest(input: {pullRequestId: \"x\"}) { clientMutationId } }'",
        "gh api graphql -f query='mutation { enablePullRequestAutoMerge(input: {pullRequestId: \"x\"}) { clientMutationId } }'",
        "gh pr -R o/r merge 5",
        "gh pr --repo o/r merge --squash 5",
        "gh api -X GET repos/o/r/pulls; gh api -X PUT repos/o/r/pulls/7/merge",
        "env gh pr merge 6",
        "gh pr \\\n  merge 8",
    ],
)
def test_merge_asks(command):
    assert decision(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --title T --body B",
        "gh pr create",
        "git push -u origin x && gh pr create --draft --fill",
        "gh pr create --body \"$(cat <<'EOF'\nbody\nEOF\n)\"",
        "gh api repos/o/r/pulls -f title=T -f head=x -f base=main",
        "gh api -X POST repos/o/r/pulls --input body.json",
        "gh api graphql -f query='mutation { createPullRequest(input: {}) { pullRequest { url } } }'",
        "gh pr new --fill",
        "gh pr --repo o/r create --fill",
        "gh pr -R o/r new",
    ],
)
def test_create_asks(command):
    assert decision(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "gh pr view 12",
        "gh pr list --state open",
        "gh pr checks 12",
        "gh pr diff 12",
        "gh api repos/o/r/pulls",
        "gh api repos/o/r/pulls/7",
        "gh api repos/o/r/pulls/7/merge",
        "gh api -X GET repos/o/r/pulls -f state=open",
        "git merge origin/main",
        "echo gh-pr-merge",
        "gh pr -R o/r view 5",
        "gh api -X GET repos/o/r/pulls -f q='a|b; c & d'",
        "grep -f patterns.txt x; gh api repos/o/r/pulls",
        "gh api graphql -f query='query { viewer { login } }'",
        "ls",
    ],
)
def test_other_commands_pass(command):
    assert decision(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "gh api graphql -F query=@merge.graphql",
        "gh api graphql --field query=@q.graphql",
        "gh api graphql --input q.json",
    ],
)
def test_graphql_query_from_file_asks(command):
    assert decision(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "if true; then gh pr merge 5; fi",
        "for n in 1 2; do gh pr create --fill; done",
        "(gh pr merge 5)",
        "echo $(gh pr merge 5)",
        "{ gh pr create --fill; }",
        "echo 5 | xargs -n1 gh pr merge",
        "timeout 30 gh pr merge 5",
        "! gh pr merge 5",
        "echo gh pr merge 5",
        "gh api -X PUT -f commit_title='fix a|b' repos/o/r/pulls/7/merge",
        "gh api -f title='A & B' repos/o/r/pulls -f head=x",
        "git commit -m \"$(cat <<'EOF'\nIt's done\nEOF\n)\"\ngh pr merge 5",
        "\\gh pr create --fill",
        "\"gh\" pr merge 5",
        "gh \"pr\" merge 5",
        "gh pr 'create' --fill",
        "(gh pr merge)",
        "gh api -X PUT repos/o/r/pulls/7/merge -f sha=\"$(gh api -X GET repos/o/r/pulls/7 --jq .head.sha)\"",
    ],
)
def test_gh_in_any_position_asks(command):
    assert decision(command) == "ask"


def run_without_jq(command):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent"},
        check=True,
    )
    return result.stdout


def test_missing_jq_asks_for_gh_commands():
    out = json.loads(run_without_jq("gh pr merge 1"))
    assert out["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert "jq is not on PATH" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_missing_jq_passes_other_commands():
    assert run_without_jq("ls") == ""


def test_missing_jq_ignores_gh_in_other_fields():
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": "ls"}, "cwd": "/Users/me/github/proj"}),
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent"},
        check=True,
    )
    assert result.stdout == ""
