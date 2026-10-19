import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PACKS = Path(__file__).resolve().parent.parent / "dcg" / "packs"
DCG = shutil.which("dcg") or str(Path.home() / ".local" / "bin" / "dcg")

pytestmark = pytest.mark.skipif(not Path(DCG).exists(), reason="dcg is not installed")


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("dcg") / "config.toml"
    path.write_text(f'[policy]\ndefault_mode = "ask"\n\n[packs]\ncustom_paths = ["{PACKS}/*.yaml"]\n')
    return path


def decision(config, command):
    result = subprocess.run(
        [DCG, "test", "-c", str(config), "--dialect", "posix", "--robot", command], capture_output=True, text=True
    )
    assert result.returncode in (0, 1), result.stdout + result.stderr
    return json.loads(result.stdout)["decision"]


@pytest.mark.parametrize("pack", sorted(PACKS.glob("*.yaml")), ids=lambda p: p.stem)
def test_pack_is_valid(pack):
    result = subprocess.run([DCG, "pack", "validate", str(pack)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "dscl -plist . -delete /Users/bob",
        "dscl -u admin -P pw /Search -delete /Users/bob",
        'sudo dscl . -append /Groups/admin GroupMembership bob',
        'sudo dseditgroup -o edit -a bob -t user admin',
        'sudo sysadminctl -addUser bob -password pw -admin',
        "tmutil delete /Volumes/TM/Backups.backupdb/mac/2026-01-01",
        "tmutil deletelocalsnapshots /",
        "csrutil disable",
        "sudo dscl . -delete /Users/bob",
        "sudo sysadminctl -deleteUser bob",
        "security delete-keychain login.keychain",
        "security delete-generic-password -s svc",
        "sudo launchctl bootout system/com.example.daemon",
        "launchctl unload -w ~/Library/LaunchAgents/x.plist",
        "osascript -e 'tell application \"Finder\" to empty the trash'",
        "networksetup -removenetworkservice Wi-Fi",
        "sudo nvram -c",
        "sudo fdesetup disable",
        "sudo spctl --master-disable",
        "launchctl stop com.example.daemon",
        "sudo launchctl kill SIGTERM system/com.example.daemon",
        "sudo dseditgroup -o delete staffers",
        "sudo tmutil removedestination 1234-ABCD",
    ],
)
def test_destructive_command_asks(config, command):
    assert decision(config, command) == "ask"


@pytest.mark.parametrize(
    "command",
    [
        "dscl . -list /Users",
        "dscl . -read /Groups/admin",
        "dseditgroup -o checkmember -m bob admin",
        "tmutil listbackups",
        "csrutil status",
        "dscl . -read /Users/bob",
        "security find-generic-password -s svc",
        "launchctl list",
        "networksetup -listallnetworkservices",
        "nvram -p",
        "fdesetup status",
        "spctl --status",
        "defaults delete com.example.app",
    ],
)
def test_read_only_command_is_allowed(config, command):
    assert decision(config, command) == "allow"


README = Path(__file__).resolve().parent.parent / "README.md"


@pytest.fixture(scope="module")
def readme_config(tmp_path_factory):
    text = README.read_text()
    block = text[text.index("```\n[policy]") + 4 :]
    block = block[: block.index("```")]
    home = tmp_path_factory.mktemp("home")
    shutil.copytree(PACKS, home / ".claude" / "dcg" / "packs")
    path = home / "config.toml"
    path.write_text(block)
    return path, home


@pytest.mark.parametrize(
    "command, expected",
    [
        ("az group delete -n rg --yes", "ask"),
        ("csrutil disable", "ask"),
        ("kubectl delete namespace prod", "ask"),
        ("psql -c 'drop table x'", "ask"),
        ("git commit --amend --no-edit", "allow"),
        ("tmutil listbackups", "allow"),
    ],
)
def test_readme_config(readme_config, command, expected):
    path, home = readme_config
    result = subprocess.run(
        [DCG, "test", "-c", str(path), "--dialect", "posix", "--robot", command],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
    )
    assert result.returncode in (0, 1), result.stdout + result.stderr
    assert json.loads(result.stdout)["decision"] == expected
