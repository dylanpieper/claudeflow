## Non-negotiable

These two rules apply even when a project says otherwise:

- Get human approval separately before each commit, pull request, and merge.
- Do not commit directly to the default branch (usually `main`).

For all other rules, a project `AGENTS.md` or `CLAUDE.md` overrides this file.

## Shell

- Use `cd` only to go to a different directory.
- Use absolute paths with `git`. Do not use `cd` before `git`.
- Write temporary scripts to the session scratchpad directory.
- Run each script by its literal path: `python3 <scratchpad>/probe_x.py`.
- Do not use inline code (`python3 -c`, `Rscript -e`).
- Do not make paths from shell variables.

## Git and PRs

- Before the first commit or PR in a repository, read its conventions:
  - `README.md`, `CONTRIBUTING.md`, the PR template, and recent commits and branch names.
  - In an organization repository, also `<owner>/practices` and `<owner>/.github`.
- Repository conventions win, then the practices repository, then `.github`, then these rules.
  - Do the steps they require, for example a draft PR or an AI-use statement.
- Use one branch for one purpose.
  - If you are on the base branch, or the change is unrelated:
    `git fetch origin`, then `git switch --no-track -c <short-name> origin/<base>`.
- Open each PR against the base branch. Do not merge branches locally.
  - Do not stack a PR on another feature branch.
  - If new work depends on an open PR, ask me: add it to that PR, or wait until it merges.
- Use plain branches in the current checkout, not git worktrees.
- Match the commit style of the repository. If it has none, use Conventional Commits.
- If no automated test covers a change, tell in the PR:
  - How you verified it.
  - How another person can reproduce the verification.

## Design

- Do not use one example as the source of truth. Find and test all representative examples.
- Use real data at runtime when it is available. Do not hardcode data or fixes.

## Writing

- Write documentation in ASD-STE100 Simplified Technical English.
- In docs, state the requirements, environment, and package versions.
- In documents, do not put comments in code blocks. Explain the outcome in the text around them.
- In Markdown, keep lines short.
  - Split a long item into a short lead line and sub-items.
  - Use a list only for two or more items. Write one item as a sentence.
- Keep a change log and release versions for published work. Skip for a prototype.

## Libraries and tools

- Before you first use a third-party package or CLI, find its version in the lockfile, manifest, or installation.
  - Read the documentation and change log for that version. Use its current recommended method.

## Rule files

In a project with no R, Python, or data files yet, read `~/.claude/rules/r.md`, `python.md`, or `data.md` before you write code.
