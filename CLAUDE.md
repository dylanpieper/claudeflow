## Design

- Design modern systems that are minimal, modular, and reusable.
- Divide work into units that each have a clear purpose: modules, functions, and pipeline steps.
- Give each unit a clear contract: its inputs, outputs, and errors.
- Make units small, but do not divide a unit that does one clear task.
- Put validation and error handling in the small units.
- Make high-level functions thin wrappers that combine small units.
- Do not use one example as the source of truth.
  - Find, list, and test all examples that apply.
  - Challenge and test your assumptions.

## Cognitive load

- Design for working memory.
  - Use about five to seven items in a single chunk of information.
  - Put larger chunks into groups.
- Use the rule of three in sentences and examples.
  - Group words, examples, and points in threes when the content allows it.
  - Three items seem complete and are easy to remember.

## Writing

- Write in ASD-STE100 Simplified Technical English for technical writing and documentation.
- Communicate requirements, environments, and packages clearly in documentation.
- In code comments and project documents, describe the result.
  - Do not repeat information that the code shows clearly.
  - Do not add text that gives no new information.
- In documents, do not put comments in code blocks. Tell the story and the outcome in the text around the block.
- Keep lines short in Markdown files.
  - Split a long list item into a short lead line and sub-items.
  - Put each sentence of a long item in its own sub-item.
- Use a bulleted list only for two or more items.
  - Do not put a single bullet under a heading or a parent item.
  - Write one item as a sentence.
- Keep a change log and release versions for published work that continues to change. Skip this for a prototype.

## Shell conventions

- The shell starts in the project root. Do not use `cd` to go to the current directory.
- Use `cd` only when the target is a different directory.
- Use absolute paths with `git`. Do not use `cd` before `git`.
- Write temporary test and analysis scripts to the session scratchpad directory.
- Run each script by its literal path: `python3 <scratchpad>/probe_x.py` or `Rscript <scratchpad>/probe_x.R`.
- Do not use inline code (`python3 -c`, `Rscript -e`).
- Do not make paths from shell variables.

## Workspace conventions

- Three rules always apply, even when a project says otherwise:
  - Get a human approval before each commit and before each new PR.
  - Do not commit directly to the default branch (usually "main").
  - Never merge. Humans merge.
- Except for these three rules, a project `AGENTS.md` or `CLAUDE.md` overrides my rules.
- Before the first commit or PR in a repository, read its `CONTRIBUTING.md`, recent commit messages, and branch names.
  - If the repository has no `CONTRIBUTING.md`, look in the owner's `.github` repository.
  - For the base branch, branch names, commit messages, and PR format, follow these conventions.
  - Where the conventions say nothing, use my Git workflow.
- If the repository or its owner has a PR template, use its sections in the PR description.
  - `gh pr create --body` does not apply the template.
  - Put the template sections in the body yourself.
- Do the steps that the conventions require, for example a draft PR or a statement of how AI helped.

## Git workflow

Branches:

- Use one branch for one purpose. Do not add unrelated changes to the current branch or its PR.
- Before any change, compare it with the purpose of the current branch: its name, commits, and open PR.
  - If the current branch is the base branch, or the change is not related:
    - Run `git fetch origin`.
    - Create a new branch from the remote base branch: `git switch --no-track -c <short-name> origin/<base>`.
  - The base branch is the default branch, unless the conventions name a different branch.
- On the first push of a branch, set its upstream: `git push -u origin <short-name>`.
- Use plain branches in the current checkout, not git worktrees.

Commits and PRs:

- Commit in small, logical steps with clear messages.
- When the work is done, show the PR title and description, and ask for approval.
  - Open the PR with `gh pr create` only after a human approves it.
  - An approval of a commit is not an approval of a PR.
- Before you open or update a PR, make sure that each commit on the branch agrees with the PR purpose.
- In the PR description, tell what changed and why.
- If no automated test covers a change, tell in the PR:
  - How you verified the change.
  - How another person can reproduce your verification.

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

- Before you first use a third-party package, library, or CLI, read its current documentation, news, and change log.
- Find the version that the project uses in its lockfile or manifest.
  - Examples: `renv.lock`, `rv.lock`, `uvr.lock`, `DESCRIPTION`, `uv.lock`, `pyproject.toml`, `package-lock.json`.
  - If there is none, use the installed version (`--version`, `packageVersion()`, or `importlib.metadata.version()`).
  - Read the documentation for that version.
- Look for new features, deprecated functions, and changed defaults. Use the current recommended method.

## Languages

- `~/.claude/rules/r.md` loads only after you read an R file.
- `~/.claude/rules/python.md` loads only after you read a Python or frontend file.
- In a project with no files in that language yet, read the rule file before you write code.
