# claudeflow

```
request
   │
   ▼
 branch
   │
   ▼
change ◄──┐
   │      │
   ▼      │
commit    │ fail
   │      │
   ▼      │
review ───┘
   │ pass
   ▼
  PR
   │
   ▼
merge (human)
```

## In this repo

Project `AGENTS.md` or `CLAUDE.md` rules override my rules, except for three git rules.
My rules override installed skills and plugins.
Hooks and permission settings still apply.

- **[CLAUDE.md](CLAUDE.md)**: Rules for every session (e.g., one purpose for each branch and PR).
- **[rules/roborev.md](rules/roborev.md)**: How Claude uses roborev to review or fix commits before opening a PR.
- **[hooks/git-commit-guard.sh](hooks/git-commit-guard.sh)**: Blocks commits to the default branch and asks you to approve all other commits.
- **[research-writing](skills/research-writing/SKILL.md)**: APA 7 and open-science rules.
- **[viz](skills/viz/SKILL.md)**: Rules for figures, charts, maps, and tables, and how to choose a tool.
- **[audit-instructions](skills/audit-instructions/SKILL.md)**: Run `/audit-instructions` to check for outdated instructions and open a PR with fixes.
- **[rules/r.md](rules/r.md)**: R preferences. Loads only for R files.
- **[rules/python.md](rules/python.md)**: Python and frontend preferences. Loads only for Python and frontend files.

## Installed tools

### Workflow

- **[Clanker Constitution](https://github.com/kenn-io/constitution)**: Operating principles for coding agents.
- **[roborev](https://github.com/kenn-io/roborev)**: Reviews each commit in the background and sends findings to Claude.
- **[caveman](https://github.com/juliusbrussee/caveman)**: Short output, fewer tokens.

### Development

- **[Superpowers](https://github.com/obra/superpowers)**: Plan, test, and debug.
- **[duckdb-skills](https://github.com/duckdb/duckdb-skills)**: Read and query data files.
- **[r-skills](https://github.com/ab604/claude-code-r-skills)** and **[Posit skills](https://github.com/posit-dev/skills)**: R, packages, Quarto, and Shiny.
- **[python-skills](https://github.com/wdm0006/python-skills)**: Python setup with uv, ruff, and pytest.
- **[slidecrafting](https://github.com/EmilHvitfeldt/slidecrafting-book.com)**: Build, theme, and animate Quarto reveal.js slide decks.

## Install

### 1. This repo

```
base=https://raw.githubusercontent.com/dylanpieper/claudeflow/main
mkdir -p ~/.claude/rules ~/.claude/hooks ~/.claude/skills/research-writing ~/.claude/skills/viz/references ~/.claude/skills/audit-instructions
curl -fsSL $base/CLAUDE.md -o ~/.claude/CLAUDE.md
curl -fsSL $base/rules/r.md -o ~/.claude/rules/r.md
curl -fsSL $base/rules/python.md -o ~/.claude/rules/python.md
curl -fsSL $base/rules/roborev.md -o ~/.claude/rules/roborev.md
curl -fsSL $base/skills/research-writing/SKILL.md -o ~/.claude/skills/research-writing/SKILL.md
curl -fsSL $base/skills/viz/SKILL.md -o ~/.claude/skills/viz/SKILL.md
for f in r python web maps; do curl -fsSL $base/skills/viz/references/$f.md -o ~/.claude/skills/viz/references/$f.md; done
curl -fsSL $base/skills/audit-instructions/SKILL.md -o ~/.claude/skills/audit-instructions/SKILL.md
curl -fsSL $base/hooks/git-commit-guard.sh -o ~/.claude/hooks/git-commit-guard.sh
chmod +x ~/.claude/hooks/git-commit-guard.sh
```

The three git rules in `CLAUDE.md` are text that Claude can ignore.
Two settings enforce them:

- A deny rule blocks merges.
- A hook blocks commits to the default branch and asks you to approve all other commits.

Add this rule to `permissions.deny` in `~/.claude/settings.json`:

```
"Bash(gh pr merge:*)"
```

Add this entry to `hooks.PreToolUse` in `~/.claude/settings.json`.
The hook needs `jq`.

```
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "if": "Bash(git *)",
      "command": "$HOME/.claude/hooks/git-commit-guard.sh",
      "timeout": 10
    }
  ]
}
```

Add this entry to `~/.claude/settings.json`.
Then Claude reads a project's `AGENTS.md` together with all `CLAUDE.md` files.

- With the default setting, a `CLAUDE.md` in the project or a parent folder stops `AGENTS.md` from loading.
- This needs Claude Code v2.1.285 or later.

```
"pluginConfigs": {
  "cc-plugin-agents-md@builtin": {
    "options": { "instructionFiles": "claude-md-and-agents-md" }
  }
}
```

To add rules for a group of repositories, for example all work repositories, put a `CLAUDE.md` in their parent folder.
Claude Code reads the `CLAUDE.md` in each folder above the working directory.

### 2. Protect main

Run this in each repository to block direct pushes to the default branch.
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

### 3. Clanker Constitution

```
git clone https://github.com/kenn-io/constitution ~/src/constitution
mkdir -p ~/.claude/rules
ln -s ~/src/constitution/CONSTITUTION.md ~/.claude/rules/clanker-constitution.md
```

### 4. roborev

```
brew install kenn-io/tap/roborev
roborev agent-hook install
roborev skills install
```

Then run `roborev init` in each repository that you want to review.

### 5. Plugins

```
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

### 6. Command-line tools the rules call

`CLAUDE.md` calls [data-dict](https://github.com/tidyverse/data-dict).
`rules/r.md` calls [Air](https://posit-dev.github.io/air/).

```
uv tool install data-dict-yaml
uv tool install air-formatter
```

## Use

### roborev dashboard

| Command | Result |
|---|---|
| `roborev tui` | Opens the dashboard in the terminal |
| `roborev ui` | Opens the dashboard in the browser |

### roborev commands

| Command | Result |
|---|---|
| `/roborev-review` · `/roborev-review-branch` | Reviews a commit or a branch |
| `/roborev-design-review` · `/roborev-design-review-branch` | Reviews the design of a commit or a branch |
| `/roborev-lookahead-review` · `/roborev-lookahead-review-branch` | Looks ahead for problems in a commit or a branch |
| `/roborev-fix` | Fixes open review findings |
| `/roborev-refine` | Fixes findings and reviews again until they pass |
| `/roborev-respond` | Replies to a review |
| `/roborev-snooze` | Pauses review reminders |

### caveman commands

| Command | Result |
|---|---|
| `/caveman` | Turns on caveman mode at level `full` |
| `/caveman lite` · `/caveman ultra` | Makes output less or more terse |
| `/caveman off` or "normal mode" | Turns off caveman mode |
| `/caveman-commit` | Writes a short Conventional Commit message |
| `/caveman-review` | Writes one-line review findings |
| `/caveman:compress <file>` | Compresses a Markdown file and keeps a backup |
| `/caveman-help` | Shows the caveman quick reference |
