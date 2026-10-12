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
        "echo gh pr merge 5",
        "gh pr -R o/r view 5",
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


def test_missing_jq_reports_error():
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": "gh pr merge 1"}}),
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent"},
    )
    assert result.returncode == 1
    assert "jq is not on PATH" in result.stderr
