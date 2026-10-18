#!/usr/bin/env python3
# SessionEnd hook. Replaces the secrets that TruffleHog finds in Claude Code transcripts
# with [REDACTED:<detector>].
# The hook starts a detached worker and exits at once, because SessionEnd hooks have a short
# time budget and the transcript can lag the session. The worker waits, then scans:
#   - the transcript of the session that ended, and the files in its session folder
#     (for example tool-results/*.txt, which hold full tool outputs);
#   - the same for other sessions in the project folder, changed in the last day but not in
#     the last 2 minutes (a live session can still write to those).
# JSON escapes hide multiline secrets such as private keys, so the worker scans the decoded
# strings. It replaces the JSON-escaped secret in the line text, so all other bytes stay the
# same. Only if a decoded line still holds a secret does it write the line again from JSON.
# A lock file in the project folder stops two workers from writing the same file.
# Usage: transcript-redact.py < hook-input.json, or transcript-redact.py --scan <transcript>.

import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

DELAY = float(os.environ.get("TRANSCRIPT_REDACT_DELAY", "5"))
RECENT = 24 * 3600
LIVE = 120
MIN_SECRET = 8
TIMEOUT = 300
HOMEBREW_PATH = "/opt/homebrew/bin:/usr/local/bin"
LOG = Path(os.environ.get("TRANSCRIPT_REDACT_LOG", Path.home() / ".claude" / "transcript-redact.log"))


def log(message):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {message}\n")


def read(path):
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read()


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def replace(value, secrets):
    if isinstance(value, str):
        for secret, label in secrets:
            value = value.replace(secret, label)
        return value
    if isinstance(value, dict):
        return {k: replace(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [replace(v, secrets) for v in value]
    return value


def decode(line):
    try:
        return json.loads(line)
    except ValueError:
        return None


def session_files(transcript):
    folder = transcript.with_suffix("")
    return sorted(p for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []


def targets(transcript):
    files = [transcript, *session_files(transcript)]
    now = time.time()

    def age(path):
        try:
            return now - path.stat().st_mtime
        except OSError:
            return -1

    for path in transcript.parent.glob("*.jsonl"):
        if path != transcript and LIVE < age(path) < RECENT:
            files += [p for p in [path, *session_files(path)] if age(p) > LIVE]
    return files


def find_secrets(files, trufflehog):
    with tempfile.TemporaryDirectory() as tmp:
        scan = Path(tmp) / "strings.txt"
        with open(scan, "w", encoding="utf-8", errors="surrogatepass") as out:
            for path in files:
                try:
                    lines = read(path).split("\n")
                except OSError:
                    continue
                for line in lines:
                    obj = decode(line) if path.suffix == ".jsonl" else None
                    for s in strings(obj) if obj is not None else [line]:
                        out.write(s + "\n")
        try:
            result = subprocess.run(
                [trufflehog, "filesystem", "--json", "--no-update", "--no-verification", str(scan)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            log(f"trufflehog timed out after {TIMEOUT} s")
            return []
    if result.returncode != 0:
        log(f"trufflehog exit {result.returncode}: {result.stderr.strip()[-500:]}")
    secrets = {}
    for row in result.stdout.splitlines():
        try:
            finding = json.loads(row)
        except ValueError:
            continue
        label = f"[REDACTED:{finding.get('DetectorName', 'secret')}]"
        raw = finding.get("Raw") or ""
        values = {raw.strip()}
        raw_v2 = finding.get("RawV2") or ""
        if finding.get("DetectorName") == "AWS" and raw and raw_v2.startswith(raw + ":"):
            values.add(raw_v2[len(raw) + 1 :])
        for value in values:
            if len(value) >= MIN_SECRET:
                secrets[value] = label
    return sorted(secrets.items(), key=lambda item: -len(item[0]))


def redact_line(line, secrets, is_json):
    new = line
    for secret, label in secrets:
        if is_json:
            new = new.replace(json.dumps(secret, ensure_ascii=False)[1:-1], label)
        new = new.replace(secret, label)
    if not is_json:
        return new
    obj = decode(new)
    if obj is None:
        obj = decode(line)
        if obj is None:
            return new
    elif not any(secret in s for s in strings(obj) for secret, _ in secrets):
        return new
    return json.dumps(replace(obj, secrets), ensure_ascii=True, separators=(",", ":"))


def redact_file(path, secrets):
    is_json = path.suffix == ".jsonl"
    tmp = None
    try:
        for _ in range(3):
            before = path.stat()
            text = read(path)
            if is_json:
                out = []
                for line in text.split("\n"):
                    body = line.removesuffix("\r")
                    out.append(redact_line(body, secrets, is_json) + line[len(body) :])
                new_text = "\n".join(out)
            else:
                new_text = redact_line(text, secrets, is_json)
            if new_text == text:
                return
            fd, name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".redact.tmp")
            tmp = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
                f.write(new_text)
            tmp.chmod(before.st_mode & 0o777)
            after = path.stat()
            if (after.st_size, after.st_mtime_ns) == (before.st_size, before.st_mtime_ns):
                tmp.replace(path)
                tmp = None
                return
            tmp.unlink()
            tmp = None
        log(f"{path}: changed during redaction, skipped")
    except (OSError, UnicodeError, ValueError) as error:
        log(f"{path}: {error!r}")
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def scan(transcript):
    if not transcript.is_file():
        return
    trufflehog = shutil.which("trufflehog", path=f"{os.environ.get('PATH', '')}:{HOMEBREW_PATH}")
    if not trufflehog:
        log("trufflehog not found")
        return
    time.sleep(DELAY)
    with open(transcript.parent / ".transcript-redact.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        files = targets(transcript)
        secrets = find_secrets(files, trufflehog)
        if secrets:
            for path in files:
                redact_file(path, secrets)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--scan":
        try:
            scan(Path(sys.argv[2]))
        except Exception:
            log(traceback.format_exc())
        return
    try:
        transcript = json.load(sys.stdin).get("transcript_path") or ""
    except ValueError:
        return
    if transcript:
        subprocess.Popen(
            [sys.executable, __file__, "--scan", transcript],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    main()
