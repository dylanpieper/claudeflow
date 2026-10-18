# claudeflow

My Claude Code setup.

```
👤 request → 🤖 branch → 🤖 change → 👤 commit → 🤖 review → 👤 PR → 👤 merge
                              ▲                      │
                              └──────── fail ────────┘
```

👤 A human acts. 🤖 Claude acts.

## Precedence

1. Hooks and permission settings.
2. The two non-negotiable rules in [CLAUDE.md](CLAUDE.md).
3. My instructions in a session.
4. The project's `AGENTS.md` or `CLAUDE.md`.
5. This repo.
6. Skills and plugins.

## Files

- [CLAUDE.md](CLAUDE.md): rules for every session.
- [rules/](rules/): R, Python, and data rules, which load for matching files, and roborev rules.
- [skills/](skills/): research-writing, viz, spatial, and audit-instructions.
- [hooks/](hooks/): approval guards and a Markdown check.
  - `git-commit-guard.sh` blocks commits to the default branch and asks before all other commits.
  - `gh-pr-guard.sh` asks before each new PR, each `gh pr merge`, and each `gh api` call that can write.
  - `git-merge-guard.sh` asks before each local merge, pull, or push that changes the default branch,
    before each deletion of a branch that is not merged, and before each force push.
  - `az-guard.sh` asks before each `az` command that is not read-only, and shows the active tenant and subscription.
  - `sf-guard.sh` asks before each `sf` or `sfdx` command that is not read-only, and shows the target org.
  - `md-list-check.sh` sends each one-item list or sub-list in a changed Markdown file back to Claude.
- [statusline.sh](statusline.sh): model, folder, caveman mode, context use, and plan use.

## Install

```
base=https://raw.githubusercontent.com/dylanpieper/claudeflow/main
for f in CLAUDE.md statusline.sh hooks/{git-commit,gh-pr,git-merge,az,sf}-guard.sh hooks/md-list-check.sh \
  rules/{r,python,data,roborev}.md \
  skills/{research-writing,spatial,audit-instructions,viz}/SKILL.md \
  skills/viz/references/{r,grammar-style,python,web,maps}.md; do
  curl -fsSL --create-dirs "$base/$f" -o ~/.claude/$f
done
chmod +x ~/.claude/hooks/*.sh
```

Merge this into `~/.claude/settings.json`. The hooks and the status line need `jq`.
The `pluginConfigs` entry makes Claude read `AGENTS.md` with `CLAUDE.md` (Claude Code v2.1.285 or later).

```
{
  "statusLine": { "type": "command", "command": "bash ~/.claude/statusline.sh" },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git *)",
            "command": "$HOME/.claude/hooks/git-commit-guard.sh",
            "timeout": 10
          },
          { "type": "command", "command": "$HOME/.claude/hooks/gh-pr-guard.sh", "timeout": 10 },
          { "type": "command", "command": "$HOME/.claude/hooks/git-merge-guard.sh", "timeout": 10 },
          { "type": "command", "command": "$HOME/.claude/hooks/az-guard.sh", "timeout": 10 },
          { "type": "command", "command": "$HOME/.claude/hooks/sf-guard.sh", "timeout": 10 }
        ]
      },
      {
        "matcher": "Bash|PowerShell|Monitor",
        "hooks": [{ "type": "command", "command": "$HOME/.local/bin/dcg" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/md-list-check.sh", "timeout": 10 }]
      }
    ]
  },
  "pluginConfigs": {
    "cc-plugin-agents-md@builtin": {
      "options": { "instructionFiles": "claude-md-and-agents-md" }
    }
  }
}
```

Block direct pushes to the default branch in each repository.
On the free plan, GitHub does not enforce this on private repositories.

```
gh api repos/{owner}/{repo}/rulesets --method POST --input - <<'EOF'
{
  "name": "protect-main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    }
  ]
}
EOF
```

Install [destructive_command_guard](https://github.com/Dicklesworthstone/destructive_command_guard) (`dcg`) v0.15.3.
It guards destructive shell commands.

- `--no-configure` stops the installer from changing `settings.json`, other agents, and shell rc files.
  Add the `dcg` entry in the JSON above yourself.
- `--verify` runs a self-test after the install.

```
curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/destructive_command_guard/v0.15.3/install.sh \
  | bash -s -- --version v0.15.3 --no-configure --verify
```

The binary goes to `~/.local/bin/dcg`. Make sure that this folder is on your `PATH`.

By default, dcg blocks each match. Put this in `~/.config/dcg/config.toml`.

- `default_mode = "ask"` asks for approval on each match, including critical rules.
- The `deny` rules always block a recursive delete of `/` or `~`, `git reset --hard`, and each form of force push.

```
[policy]
default_mode = "ask"

[policy.rules]
"core.filesystem:rm-rf-root-home" = "deny"
"core.filesystem:rm-r-f-separate-root-home" = "deny"
"core.filesystem:rm-recursive-force-root-home" = "deny"
"core.git:reset-hard" = "deny"
"core.git:push-force-long" = "deny"
"core.git:push-force-short" = "deny"
"core.git:push-force-refspec" = "deny"
```

dcg has no setting that denies all critical rules and asks for the rest.
Run `dcg explain --format json '<command>'` and read `outcome` to see what a command does.

dcg rewrites its own hook entry in `settings.json` each time it runs (`self_heal_hook`).
It moves the entry to the top of `PreToolUse` and changes `$HOME` to an absolute path.

Tools and plugins:

```
brew install gh kenn-io/tap/roborev
uv tool install data-dict-yaml
uv tool install air-formatter
roborev agent-hook install
roborev skills install

claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin marketplace add JuliusBrussee/caveman
claude plugin install caveman@caveman
claude plugin marketplace add duckdb/duckdb-skills
claude plugin install duckdb-skills@duckdb-skills
claude plugin marketplace add ab604/claude-code-r-skills
claude plugin install r-skills@r-skills
claude plugin marketplace add posit-dev/skills
claude plugin install r-lib@posit-dev-skills
claude plugin install quarto@posit-dev-skills
claude plugin install shiny@posit-dev-skills
claude plugin marketplace add wdm0006/python-skills
claude plugin install python-library-foundations@dev-skills
claude plugin marketplace add EmilHvitfeldt/slidecrafting-book.com
claude plugin install slidecrafting@slidecrafting
```

Run `roborev init` in each repository that you want to review.
