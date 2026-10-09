---
name: audit-instructions
description: Check the rules, skills, and README in this instructions repository for outdated claims, broken references, and conflicts between files. Then fix them on a branch and open a pull request.
disable-model-invocation: true
---

# Audit instructions

This skill finds instructions that are now outdated and fixes them in a pull request.
It needs a git clone of the instructions repository at `~/.claude`.
If `git rev-parse` fails there, stop and tell me.

## 1. Find the files

- Get the files from `git ls-files '*.md'`. Do not use a fixed list.
- Run `git status --short --ignored rules skills`.
  - Installed tools (for example, the roborev skills) are ignored on purpose.
  - A file that the README lists but git ignores is a finding.
  - The repository does not publish that file.

## 2. List the claims

Read each file. List each claim that can become outdated, with its `file:line`:

| Type | Examples |
|------|----------|
| Package or tool | It exists, is maintained, is pre-release, or was renamed |
| API | A function, argument, hook, or CLI flag |
| Version | A pinned or minimum version (mature release, breaking changes) |
| Link | A URL (it resolves, and its content still supports the rule) |
| Policy or practice | A usage policy, a license, "use X, not Y" |

## 3. Check each claim

- Check each claim against its primary source.
  - Sources: the official documentation, the release notes, the package registry, or the source repository.
  - Do not check a claim from memory.
- For packages, use the registry:
  - CRAN: `https://crandb.r-pkg.org/<package>`, with a `User-Agent` header.
  - PyPI: `https://pypi.org/pypi/<package>/json`.
  - npm: `https://registry.npmjs.org/<package>`.
- Give each claim a status (current, outdated, or unsure) and a link to the evidence.
- Change a preference ("use X, not Y") only when one of these is true:
  - X is deprecated or archived;
  - the maintainers of X recommend a different tool.
- Do not change a preference for taste.
- When the status is unsure, do not change the claim. Report it.

## 4. Check the files together

- Find rules that conflict, for example two answers to "which database" or "which file overrides".
- Make sure that:
  - the `paths` of each rule load it where its content applies;
  - the scope of each section agrees with the exceptions in other files;
  - each file path and skill name in a rule points to something that exists;
  - the README lists each rule and skill, and the install steps get each file.

## 5. Report and fix

- Report a table with these columns: `file:line`, claim, status, evidence, and fix.
- Put outdated claims and conflicts first in the table.
- Create a branch named `audit-<YYYY-MM-DD>` from the latest `origin/main`.
- If that branch exists, add a suffix such as `-2`.
- Fix only the outdated claims and the conflicts. Keep the wording style of each file.
- Follow the git workflow in `CLAUDE.md` and `rules/roborev.md`:
  - Get my review before you commit.
  - Handle failing reviews (fix or disprove each one) before the pull request.
- Open a pull request that includes the table.
- In the pull request, put the unsure claims in a separate list for my decision.
