import importlib.util
import json
import os
import random
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "transcript-redact.py"

pytestmark = pytest.mark.skipif(not shutil.which("trufflehog"), reason="trufflehog is not installed")


def fake(chars, n, seed):
    rng = random.Random(seed)
    return "".join(rng.choice(chars) for _ in range(n))


ALNUM = string.ascii_letters + string.digits
GITHUB = "ghp_" + fake(ALNUM, 36, 1)
ANTHROPIC = "sk-ant-api03-" + fake(ALNUM + "_-", 93, 2) + "AA"
AWS_ID = "AKIA" + fake(string.ascii_uppercase + "234567", 16, 3)
AWS_SECRET = fake(ALNUM + "/+", 40, 4)


@pytest.fixture(scope="module")
def private_key(tmp_path_factory):
    key = tmp_path_factory.mktemp("key") / "k"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    return key.read_text().strip()


def record(text, kind="user"):
    return {"type": kind, "uuid": "u1", "message": {"role": kind, "content": [{"type": "text", "text": text}]}}


def write(path, records, mtime=None):
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records))
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


@pytest.fixture(autouse=True)
def isolated_log(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("TRANSCRIPT_REDACT_LOG", str(tmp_path_factory.mktemp("log") / "redact.log"))


def load_hook():
    spec = importlib.util.spec_from_file_location("transcript_redact", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scan(transcript):
    subprocess.run([sys.executable, str(SCRIPT), "--scan", str(transcript)], check=True, env={**os.environ, "TRANSCRIPT_REDACT_DELAY": "0"})


def test_redacts_secrets_and_keeps_valid_jsonl(tmp_path, private_key):
    transcript = write(
        tmp_path / "s.jsonl",
        [
            record(f"token {GITHUB} ok"),
            record(f"ANTHROPIC_API_KEY={ANTHROPIC}", "assistant"),
            record(f"aws_access_key_id={AWS_ID}\naws_secret_access_key={AWS_SECRET}"),
            record(private_key),
        ],
    )
    scan(transcript)
    text = transcript.read_text()
    for secret in (GITHUB, ANTHROPIC, AWS_ID, AWS_SECRET):
        assert secret not in text
    assert "BEGIN OPENSSH PRIVATE KEY" not in text
    for detector in ("Github", "Anthropic", "AWS", "PrivateKey"):
        assert f"[REDACTED:{detector}]" in text
    rows = [json.loads(line) for line in text.splitlines()]
    assert len(rows) == 4
    assert rows[0]["message"]["content"][0]["text"] == "token [REDACTED:Github] ok"


def test_lines_without_secrets_keep_their_bytes(tmp_path):
    clean = '{"type":"user", "message": {"content":"caf\\u00e9 é"}}\n'
    transcript = tmp_path / "s.jsonl"
    transcript.write_text(clean + json.dumps(record(f"token {GITHUB}")) + "\nnot json\n")
    scan(transcript)
    lines = transcript.read_text().splitlines(keepends=True)
    assert lines[0] == clean
    assert lines[2] == "not json\n"
    assert GITHUB not in lines[1]


def test_changed_line_keeps_other_values(tmp_path):
    line = '{"n":1.10,"big":1e5,"s":"café","t":"token ' + GITHUB + '"}\n'
    transcript = tmp_path / "s.jsonl"
    transcript.write_text(line)
    scan(transcript)
    assert transcript.read_text() == line.replace(GITHUB, "[REDACTED:Github]")


def test_lone_surrogate_and_bad_bytes_do_not_stop_redaction(tmp_path):
    transcript = tmp_path / "s.jsonl"
    transcript.write_bytes(
        b'{"t":"x \\ud83d token ' + GITHUB.encode() + b'"}\n'
        + b'{"t":"bad \xff byte"}\n'
        + b'{"t":"key ' + ANTHROPIC.encode() + b'"}\n'
    )
    scan(transcript)
    data = transcript.read_bytes()
    assert GITHUB.encode() not in data
    assert ANTHROPIC.encode() not in data
    assert b'"x \\ud83d token [REDACTED:Github]"' in data
    assert b"bad \xff byte" in data
    assert not list(tmp_path.glob("*.redact.tmp"))


def test_redacts_session_folder_files(tmp_path):
    transcript = write(tmp_path / "s.jsonl", [record("ended")])
    tool_result = tmp_path / "s" / "tool-results" / "b1.txt"
    tool_result.parent.mkdir(parents=True)
    tool_result.write_text(f"line one\nexport ANTHROPIC_API_KEY={ANTHROPIC}\n")
    subagent = tmp_path / "s" / "subagents" / "agent-1.jsonl"
    subagent.parent.mkdir()
    write(subagent, [record(f"token {GITHUB}")])
    scan(transcript)
    assert tool_result.read_text() == "line one\nexport ANTHROPIC_API_KEY=[REDACTED:Anthropic]\n"
    assert GITHUB not in subagent.read_text()


def test_multiline_key_in_text_file_is_redacted(tmp_path, private_key):
    transcript = write(tmp_path / "s.jsonl", [record("ended")])
    tool_result = tmp_path / "s" / "tool-results" / "cat.txt"
    tool_result.parent.mkdir(parents=True)
    tool_result.write_text(f"before\n{private_key}\nafter\n")
    scan(transcript)
    assert tool_result.read_text() == "before\n[REDACTED:PrivateKey]\nafter\n"


def test_missing_trufflehog_is_logged(tmp_path):
    transcript = write(tmp_path / "s.jsonl", [record(f"token {GITHUB}")])
    log = tmp_path / "redact.log"
    env = {"PATH": str(tmp_path), "TRANSCRIPT_REDACT_DELAY": "0", "TRANSCRIPT_REDACT_LOG": str(log), "HOME": str(tmp_path)}
    hook = load_hook()
    if shutil.which("trufflehog", path=hook.HOMEBREW_PATH):
        pytest.skip("trufflehog is in a Homebrew path")
    subprocess.run([sys.executable, str(SCRIPT), "--scan", str(transcript)], check=True, env=env)
    assert "trufflehog not found" in log.read_text()


def test_url_host_is_not_redacted_alone(tmp_path):
    url = "postgres://admin:" + fake(ALNUM, 16, 5) + "@db.example.com:5432"
    transcript = write(tmp_path / "s.jsonl", [record(f"DATABASE_URL={url}/appdb"), record("host db.example.com:5432/appdb")])
    scan(transcript)
    rows = transcript.read_text().splitlines()
    assert url not in rows[0]
    assert "db.example.com:5432/appdb" in rows[1]


def test_line_separator_and_crlf_keep_records_whole(tmp_path, private_key):
    transcript = tmp_path / "s.jsonl"
    line = json.dumps(record("web text   more\n" + private_key), ensure_ascii=False)
    transcript.write_bytes(line.encode() + b"\r\n" + b'{"t":"clean"}\r\n')
    scan(transcript)
    data = transcript.read_bytes()
    assert b"BEGIN OPENSSH PRIVATE KEY" not in data
    assert "[REDACTED:PrivateKey]" in data.decode()
    assert " ".encode() in data
    assert data.endswith(b'{"t":"clean"}\r\n')


def test_parallel_workers_keep_file_whole(tmp_path):
    transcript = write(tmp_path / "s.jsonl", [record(f"token {GITHUB} line {i}") for i in range(200)])
    env = {**os.environ, "TRANSCRIPT_REDACT_DELAY": "0"}
    workers = [subprocess.Popen([sys.executable, str(SCRIPT), "--scan", str(transcript)], env=env) for _ in range(4)]
    for w in workers:
        w.wait()
    rows = [json.loads(line) for line in transcript.read_text().splitlines()]
    assert len(rows) == 200
    assert GITHUB not in transcript.read_text()
    assert not list(tmp_path.glob("*.redact.tmp"))


def test_file_that_keeps_changing_is_left_alone_without_temp_files(tmp_path, monkeypatch):
    hook = load_hook()
    transcript = write(tmp_path / "s.jsonl", [record(f"token {GITHUB}")])
    real_read = hook.read

    def read_then_append(path):
        text = real_read(path)
        with open(path, "a") as f:
            f.write(json.dumps(record("late")) + "\n")
        return text

    monkeypatch.setattr(hook, "read", read_then_append)
    hook.redact_file(transcript, [(GITHUB, "[REDACTED:Github]")])
    assert len(transcript.read_text().splitlines()) == 4
    assert not list(tmp_path.glob("*.redact.tmp"))
    assert "changed during redaction, skipped" in hook.LOG.read_text()


def test_live_subagent_of_idle_session_is_skipped(tmp_path):
    now = time.time()
    transcript = write(tmp_path / "s.jsonl", [record("ended")])
    idle = write(tmp_path / "idle.jsonl", [record(f"t {GITHUB}")], mtime=now - 600)
    subagent = tmp_path / "idle" / "subagents" / "agent-1.jsonl"
    subagent.parent.mkdir(parents=True)
    write(subagent, [record(f"t {GITHUB}")])
    scan(transcript)
    assert GITHUB not in idle.read_text()
    assert GITHUB in subagent.read_text()


def test_no_secret_leaves_file_untouched(tmp_path):
    transcript = write(tmp_path / "s.jsonl", [record("nothing here")], mtime=1_000_000)
    scan(transcript)
    assert transcript.stat().st_mtime == 1_000_000


def test_scans_recent_transcripts_but_not_live_or_old_ones(tmp_path):
    now = time.time()
    transcript = write(tmp_path / "s.jsonl", [record("ended")])
    recent = write(tmp_path / "recent.jsonl", [record(f"t {GITHUB}")], mtime=now - 3600)
    live = write(tmp_path / "live.jsonl", [record(f"t {GITHUB}")], mtime=now - 10)
    old = write(tmp_path / "old.jsonl", [record(f"t {GITHUB}")], mtime=now - 3 * 24 * 3600)
    scan(transcript)
    assert GITHUB not in recent.read_text()
    assert GITHUB in live.read_text()
    assert GITHUB in old.read_text()


def test_hook_returns_at_once_and_worker_redacts(tmp_path):
    transcript = write(tmp_path / "s.jsonl", [record(f"token {GITHUB}")])
    subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"hook_event_name": "SessionEnd", "transcript_path": str(transcript)}),
        text=True,
        check=True,
        env={**os.environ, "TRANSCRIPT_REDACT_DELAY": "3"},
    )
    assert GITHUB in transcript.read_text()
    for _ in range(60):
        if GITHUB not in transcript.read_text():
            break
        time.sleep(0.25)
    assert GITHUB not in transcript.read_text()


@pytest.mark.parametrize("stdin", ["", "not json", "{}", '{"transcript_path": "/no/such/file.jsonl"}'])
def test_bad_input_exits_zero(stdin):
    result = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, text=True, capture_output=True)
    assert result.returncode == 0
