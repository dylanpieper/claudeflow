import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "cli-guard.py"


def decide(command):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
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
        "az vm list",
        "sf org list",
        "sfdx force:org:list",
        "curl -fsSL https://example.com",
        "wget https://example.com/file",
        "http GET https://api.example.com",
        "https POST https://api.example.com x=1",
        "xh https://api.example.com",
        "cd repo && az account show",
        "git status; curl https://example.com",
        "ls | xargs -n 1 curl -O",
        "echo x || wget y",
        "sudo az login",
        "sudo -u admin curl https://example.com",
        "env -i TOKEN=x curl https://example.com",
        "TOKEN=x curl https://example.com",
        "command curl https://example.com",
        "exec curl https://example.com",
        "timeout 30s curl https://example.com",
        "/usr/bin/curl https://example.com",
        "/opt/homebrew/bin/az vm list",
        "bash -c 'curl https://example.com'",
        "sh -c \"sf org list\"",
        "bash -lc 'az vm list'",
        "eval curl https://example.com",
        "echo $(curl -s https://example.com)",
        "echo `az account show`",
        "(cd x && curl https://example.com)",
        "git status\ncurl https://example.com",
        "curl -d \"unbalanced https://example.com",
        "bash <<EOF\ncurl https://example.com\nEOF",
        "cat <<EOF > x.txt\nhello\nEOF\ncurl https://example.com",
        "echo $(jq -r '(.a // \"\")' f | xargs curl -s)",
        "for u in a b; do curl \"$u\"; done",
        "if curl -sf https://example.com; then echo ok; fi",
        "if true; then az vm list; fi",
        "while true; do wget x; done",
        "until az login; do sleep 1; done",
        "! curl https://example.com",
        "{ curl https://example.com; }",
        "echo '<<X'\ncurl https://example.com",
        "cat <<<hello\ncurl https://example.com",
        "cat <<EOF\nno end\ncurl https://example.com",
        "env -u VAR curl https://example.com",
        "timeout -s KILL 10 curl https://example.com",
        "ls | xargs -I {} curl {}",
        "ls | xargs -P 4 -I {} curl {}",
        "ls | xargs -n 1 curl -O",
        "bash --norc -c 'curl https://example.com'",
        "echo 'curl https://example.com' | sh",
        "cat <<EOF | bash\ncurl https://example.com\nEOF",
        "echo 'az group delete -n x --yes' | bash 2>&1",
        "echo 'curl x' | sh >/dev/null",
        "echo 'curl x' | bash 2> err.log",
        "function f { curl https://example.com; }; f",
        "env -P /usr/bin curl https://example.com",
        "env -S 'curl https://example.com'",
        "exec -a name curl https://example.com",
        "bash <<< 'curl https://example.com'",
        "bash <<<'az vm list'",
        "f() { curl https://example.com; }; f",
        "function f() { curl https://example.com; }; f",
        "echo 'curl x' | bash -o pipefail",
        "echo 'curl x' | sh -s foo bar",
        "echo 'curl x' | bash --rcfile ~/.bashrc",
        "CMD='curl https://example.com'; bash <<< \"$CMD\"",
        "echo 'curl x' | bash -eo pipefail",
        "echo 'curl x' | bash -euo pipefail",
        "true;(curl https://example.com)",
        "cd d&&(curl https://example.com)",
        "(curl https://example.com)&&echo ok",
        "echo 'curl x' | bash -oe pipefail",
        "CMD='curl https://example.com'; bash -c \"$CMD\"",
        "CMD='az vm list'; eval \"$CMD\"",
        "echo 'curl https://example.com' | bash -os pipefail",
        "CMD='curl https://example.com'; $CMD",
        "CMD=curl; ${CMD} https://example.com",
    ],
)
def test_cli_command_asks(command):
    assert decide(command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git push -u origin main",
        "ls -la",
        "echo curl is great",
        "grep -r 'az vm' docs/",
        "cat curl.txt",
        "python3 tools/curlish.py",
        "ln -sf a b",
        "rg sfdx README.md",
        "brew install azure-cli",
        "jq '.az' file.json",
        "echo 'run: curl x'",
        "cat > notes.md <<'EOF'\ncurl https://example.com\naz vm list\nEOF",
        "git commit -m \"Add guard\n\ncurl and az now ask\"",
        "gh pr create --body \"Run:\ncurl -fsSL https://example.com\"",
        "for c in \"az vm list\" \"sf org list\"; do echo \"$c\"; done",
        "echo $(date) https://example.com",
        "git clone https://github.com/a/b.git",
        "for f in *.md; do wc -l \"$f\"; done",
        "if git diff --quiet; then echo clean; fi",
        "bash script.sh",
        "bash --norc script.sh",
        "echo hello | sh -s",
        "bash script.sh 2>&1",
        "sh run.sh > out.log",
        "function f { echo hi; }; f",
        "bash <<< 'echo hi'",
        "f() { echo hi; }; f",
        "cat <<< 'curl is a word'",
        "bash -o pipefail script.sh",
        "cat <<EOF | grep x\ncurl https://example.com\nEOF",
        "",
    ],
)
def test_other_command_gets_no_decision(command):
    assert decide(command) is None


@pytest.mark.parametrize("stdin", ["", "not json", "{}", "[]", '{"tool_input": {"command": 5}}'])
def test_bad_input_gets_no_decision(stdin):
    result = subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout == ""
