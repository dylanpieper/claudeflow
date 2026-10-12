# claudeflow

My Claude Code setup.

```
👤 request → 🤖 branch → 🤖 change → 👤 commit → 🤖 review → 👤 PR → 👤 merge
                              ▲                      │
                              └──── fail ────────────┘
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
- [hooks/](hooks/): approval guards.
  - `git-commit-guard.sh` blocks commits to the default branch and asks before all other commits.
  - `gh-pr-guard.sh` asks before each new PR, each `gh pr merge`, and each `gh api` call that can write.
  - `git-merge-guard.sh` asks before each local merge, pull, or push that changes the default branch,
    and before each deletion of a branch that is not merged.
- [statusline.sh](statusline.sh): model, folder, caveman mode, context use, and plan use.

## Install

```
base=https://raw.githubusercontent.com/dylanpieper/claudeflow/main
for f in CLAUDE.md statusline.sh hooks/{git-commit,gh-pr,git-merge}-guard.sh \
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
          { "type": "command", "command": "$HOME/.claude/hooks/git-merge-guard.sh", "timeout": 10 }
        ]
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
