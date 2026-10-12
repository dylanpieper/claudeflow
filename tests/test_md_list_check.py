import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "md-list-check.sh"
BASH = shutil.which("bash") or "/bin/bash"


def check(path):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(path)}}),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)["reason"] if result.stdout.strip() else None


def write(tmp_path, text, name="doc.md"):
    path = tmp_path / name
    path.write_text(text)
    return path


@pytest.mark.parametrize(
    "text, line",
    [
        ("- one\n- two\n  - only sub\n- three\n", 3),
        ("Intro:\n\n- only\n\nText.\n", 3),
        ("- a\n  - x\n  - y\n- b\n  - lone\n", 5),
        ("1. one\n   - lone\n2. two\n", 2),
        ("- a\n  - lone\n    continued\n- b\n", 2),
    ],
)
def test_one_item_list_is_reported(tmp_path, text, line):
    reason = check(write(tmp_path, text))
    assert f"line {line}:" in reason


@pytest.mark.parametrize(
    "text",
    [
        "- one\n- two\n",
        "- a\n  - x\n  - y\n- b\n",
        "- a\n  continued line\n- b\n",
        "---\npaths:\n  - \"**/*.R\"\n---\n\nText.\n",
        "```\n- only in code\n```\n",
        "No lists here.\n",
        "- a\n\n- b\n",
    ],
)
def test_valid_markdown_passes(tmp_path, text):
    assert check(write(tmp_path, text)) is None


@pytest.mark.parametrize("name", ["doc.qmd", "doc.Rmd"])
def test_quarto_and_rmarkdown_are_checked(tmp_path, name):
    assert check(write(tmp_path, "- only\n", name)) is not None


def test_other_files_pass(tmp_path):
    assert check(write(tmp_path, "- only\n", "notes.txt")) is None


def test_repo_markdown_has_no_one_item_lists():
    repo = SCRIPT.parent.parent
    files = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "*.md"], capture_output=True, text=True, check=True
    ).stdout.split()
    problems = {f: check(repo / f) for f in files}
    assert {f: r for f, r in problems.items() if r} == {}
