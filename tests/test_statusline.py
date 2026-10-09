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
BASH = shutil.which("bash")


def run(payload, config_dir, path=None):
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": path or os.environ["PATH"], "CLAUDE_CONFIG_DIR": str(config_dir)},
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
