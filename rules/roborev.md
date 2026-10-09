# roborev

roborev reviews each commit in the background.
The agent hook brings failing reviews back into the session.

- Before you use roborev in a repository, run `roborev quickstart`.
  - It shows the setup state and the current commands.
  - If the post-commit hook is missing, ask before you run `roborev init`.
- After you commit, run `roborev list --open`.
- Handle failing reviews (fix or disprove each one) before you open or update a pull request.
- When I ask in plain words to review or fix a branch or pull request, use roborev, not another review tool:
  - Review: `roborev review --branch --wait`.
  - Read findings: `roborev show --job <id> --json`.
  - Prove each finding before you edit.
  - Record what you fixed or disproved: `roborev comment --job <id> -m "<what you fixed or disproved>"`.
  - Then run `roborev close <id>`.
  - Do not close a review while a valid finding is still open.
- The roborev skills (`/roborev-fix`, `/roborev-refine`, and others) run only when I type them.
- Before a pull request, suggest `/roborev-refine`.
