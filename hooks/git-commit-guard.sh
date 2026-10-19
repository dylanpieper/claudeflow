#!/bin/bash
# PreToolUse hook for Bash.
# Denies `git commit` on the default branch.
# Asks the user to approve every other `git commit`.
# Reads git options before `commit`: flags, --opt=value, -c and -C with values, and long options
# that take a separate value. Uses the first -C path as the repository.
# Asks for each command that mentions git and commit when jq is missing, because the hook cannot parse it.
# Other commands get no decision.

input=$(cat)
if ! command -v jq >/dev/null; then
  if [[ $input == *git* && $input == *commit* ]]; then
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' \
      "git-commit-guard cannot check this command because jq is not on PATH."
  fi
  exit 0
fi
command=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

arg='("[^"]*"|'\''[^'\'']*'\''|[^[:space:];&|]+)'
opt="([[:space:]]+-[Cc][[:space:]]+$arg)|([[:space:]]+--(git-dir|work-tree|namespace|config-env)[[:space:]]+$arg)"
opt="$opt|([[:space:]]+--[a-z-]+(=$arg)?)|([[:space:]]+-[A-Za-z])"
commit_re="(^|[;&|(\`[:space:]])git($opt)*[[:space:]]+commit([[:space:];&|)]|$)"
[[ $command =~ $commit_re ]] || exit 0

repo=$cwd
c_re="[[:space:]]-C[[:space:]]+$arg"
if [[ ${BASH_REMATCH[0]} =~ $c_re ]]; then
  repo=${BASH_REMATCH[1]}
  repo=${repo#[\"\']}
  repo=${repo%[\"\']}
  repo=${repo/#\~/$HOME}
  [[ $repo = /* ]] || repo=$cwd/$repo
fi

decide() {
  jq -n --arg d "$1" --arg r "$2" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: $d,
      permissionDecisionReason: $r
    }
  }'
  exit 0
}

branch=$(git -C "$repo" branch --show-current 2>/dev/null)
default=$(git -C "$repo" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)
default=${default#origin/}

if git -C "$repo" rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
  if [[ -n $default && $branch == "$default" ]] ||
     [[ -z $default && ( $branch == main || $branch == master ) ]]; then
    decide deny "Do not commit to the default branch ($branch). Create a branch from origin/$branch first."
  fi
fi

decide ask "Approve this commit on branch ${branch:-unknown}."
