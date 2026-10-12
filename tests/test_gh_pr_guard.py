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
        "ls",
    ],
)
def test_other_commands_pass(command):
    assert decision(command) is None
