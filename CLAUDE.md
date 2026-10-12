## Non-negotiable

These three rules apply even when a project says otherwise:

- Get human approval before each commit and before each new PR, separately.
- Do not commit directly to the default branch (usually `main`).
- Never merge. Humans merge.

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
  - The `.github` repository: use its `CONTRIBUTING.md` or PR template for each file that the repository does not have.
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

## Data stack

- Recommend a modern data stack. Show alternatives and put them in order of best fit.
- Use real data at runtime when it is available. Do not hardcode data or fixes.
- As a general rule:
  - Large or heavy work: when a task needs power, memory, or storage, use DuckDB.
    - Use Arrow or Parquet with DuckDB as necessary.
    - DuckDB is best for large column scans and aggregations.
    - DuckLake is best for data lakes, cataloging, and multiple clients (local or cloud)
    - Use the `duckdb-skills` plugin.
  - Small persistent data: when small data needs transactions or many small row reads and writes, use SQLite.

## Data dictionaries

- Read multiple CSV or Excel files from a file list. Do not rely on exact filenames.
  - Before you assign data to variables, check its schema.
  - If there is a dictionary, check the data against it.
- When a project relies on data files, describe them in `data-dict.yaml`. Use it as the data contract.
- Run the `data-dict` skill commands first:
  - Before you read a dictionary, run `data-dict skill-read`.
  - Before you create or change a dictionary, run `data-dict skill-create`.
- Write code that continues to work when data files, connections, or schemas change.
- When the data and the dictionary do not agree, warn loudly.
- Check the data with `data-dict`:
  - For Parquet, use `data-dict validate-meta` and `data-dict validate-data`.
  - For other sources, use `data-dict translate` to get the checks in R, Python, or SQL.
- If `data-dict` is not available, tell me. Then check the schemas in code.

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
- In a project with no matching files yet, read the rule file before you write code.
