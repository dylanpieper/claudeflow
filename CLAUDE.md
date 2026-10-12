## Non-negotiable

These two rules apply even when a project says otherwise:

- Get human approval separately before each commit, pull request, and merge.
- Do not commit directly to the default branch (usually `main`).

For all other rules, a project `AGENTS.md` or `CLAUDE.md` overrides this file.

## Shell

- The shell starts in the project root.
- Use `cd` only to go to a different directory.
- Use absolute paths with `git`. Do not use `cd` before `git`.
- Write temporary scripts to the session scratchpad directory.
- Run each script by its literal path: `python3 <scratchpad>/probe_x.py`.
- Do not use inline code (`python3 -c`, `Rscript -e`).
- Do not make paths from shell variables.

## Git and PRs

- Before the first commit or PR in a repository, read its conventions:
  - `README.md` and `CONTRIBUTING.md`.
  - Recent commit messages and branch names.
  - The PR template, if one exists.
- Then read the owner's organization-wide conventions with `gh`, if they exist:
  - The practices repository:
    - Use the one that the README or `CONTRIBUTING.md` names as its practices guide.
    - If none is named, check `<owner>/practices`.
    - List its files. Read the files on Git, PRs, and versions.
  - The `.github` repository:
    - Use its `CONTRIBUTING.md` if the current repository has none.
    - Use its PR template if the current repository has none.
- Order of precedence, highest first:
  - Repository conventions.
  - The practices repository.
  - The `.github` files.
  - The fallback rules below.
- Follow the conventions for base branch, branch names, commits, and PR format.
  - Do the steps they require, for example a draft PR or an AI-use statement.
  - Where they say nothing, use the rules below.
- `gh pr create --body` does not apply the PR template; write the body yourself.
- Use one branch for one purpose.
  - Before a change, compare it with the branch name, commits, and open PR.
  - If you are on the base branch, or the change is unrelated:
    `git fetch origin`, then `git switch --no-track -c <short-name> origin/<base>`.
  - The base branch is the default branch, unless the conventions name a different branch.
- Open each PR against the base branch.
  - Do not stack a PR on another feature branch.
  - If new work depends on an open PR, ask me: add it to that PR, or wait until it merges.
- On the first push, run `git push -u origin <short-name>`.
- Use plain branches in the current checkout, not git worktrees.
- Commit in small, logical steps with clear messages.
- When the work is done, show the PR title and description and ask for approval.
- Before you open or update a PR, make sure each commit fits the PR purpose.
- In the PR description, tell what changed and why.
- If no automated test covers a change, tell in the PR:
  - How you verified it.
  - How another person can reproduce the verification.

## Design

- Do not use one example as the source of truth.
- Find, list, and test all representative examples that apply.
- Give each function or pipeline step one task and a contract: inputs, outputs, errors.
- Put validation and error handling in the small units.
- Keep high-level functions as thin wrappers.
- Use real data at runtime when it is available. Do not hardcode data or fixes.

## Writing

- Write documentation in ASD-STE100 Simplified Technical English.
- In docs, state the requirements, environment, and package versions.
- In comments and docs, describe the result. Do not repeat what the code shows.
- In documents, do not put comments in code blocks.
- Explain the outcome in the text around a code block.
- In Markdown, keep lines short.
  - Split a long item into a short lead line and sub-items.
  - Use a list only for two or more items. Write one item as a sentence.
- Keep a change log and release versions for published work; skip for a prototype.

## Libraries and tools

- Before you first use a third-party package or CLI in a project, find its version.
  - Look in the lockfile or manifest.
  - If there is none, use the installed version.
- Read the documentation and change log for that version.
- Use the current recommended method, not deprecated functions or old defaults.

## Rule files

- These load only after you read a matching file:
  - `~/.claude/rules/r.md`: R files.
  - `~/.claude/rules/python.md`: Python or frontend files.
  - `~/.claude/rules/data.md`: data files, `data-dict.yaml`, and R, Python, notebook, Quarto, or SQL files.
- In a project with no matching files yet, read the rule file before you write code.
