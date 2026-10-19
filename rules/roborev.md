# roborev

roborev reviews each commit in the background.
The agent hook brings failing reviews back into the session.

- Before you use roborev in a repository, run `roborev quickstart`.
  - It shows the setup state and the current commands.
  - If the post-commit hook is missing, ask before you run `roborev init`.
- After you commit, run `roborev list --open`.
- Handle failing reviews (fix, skip, or disprove each finding) before you open or update a pull request.
- Fix a finding when it can happen in normal use or it causes harm, for example data loss or a security gap.
- Skip the other findings, for example:
  - a finding that needs input that normal work does not use (a rare edge case);
  - a Low finding that has no effect in normal use;
  - a request for a style or test-layout change only;
  - a repeat of a finding that you skipped before.
- Record each skip or disproof with the reason:
  `roborev comment --job <id> -m "skipped: <reason>"` or `-m "disproved: <reason>"`.
- When two rounds in a row have only findings that you skip or disprove, stop the review loop.
  This also applies during `/roborev-refine`. Tell me, then continue to the pull request.
- Before you fix a finding, explain the fix to me. Wait for my OK before you edit.
  - The finding and the proof that it is real.
  - The change that you will make.
  - When I type `/roborev-fix` or `/roborev-refine`, that is my OK for the edits in that run.
    The commit hook still asks before each commit.
- Before you commit a fix, choose to layer or rebuild:
  - Rebuild commits that are not pushed yet.
  - Never rebuild pushed commits. Put each fix to a pushed commit in a new commit.
  - A commit is pushed if `git branch -r --contains <sha>` lists a remote branch.
  - During `/roborev-refine`, commit each loop. After the run, rebuild the commits that are not pushed.
    Then add the new SHA to each job that refine closed.
- When you rebuild:
  - Do not add commits that undo, redo, or patch earlier commits that are not pushed.
  - Choose the best way, and tell me which way and why. For example:
    - Change the last commit (HEAD only): `git commit --amend`.
    - Fold a fix into an earlier commit: `git commit --fixup=<sha>`,
      then `git rebase --autosquash $(git merge-base HEAD origin/<base>)`.
      The fork point keeps the branch on its current base.
    - Squash the commits that are not pushed into fewer commits.
- Record each fix with `roborev comment --job <id>`.
  - Give the SHA of the commit that holds the fix.
  - When you rebuild, record the SHA after the last rewrite.
- When I ask in plain words to review or fix a branch or pull request, use roborev, not another review tool:
  - Review: `roborev review --branch --wait`.
  - Read findings: `roborev show --job <id> --json`.
  - Prove each finding before you edit.
  - Record what you fixed, skipped, or disproved: `roborev comment --job <id> -m "<what you fixed, skipped, or disproved>"`.
  - Then run `roborev close <id>`.
  - Do not close a review while a finding that you must fix is still open.
- The roborev skills (`/roborev-fix`, `/roborev-refine`, and others) run only when I type them.
- Before a pull request, suggest `/roborev-refine`.
