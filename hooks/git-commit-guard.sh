#!/bin/bash
# PreToolUse hook for Bash.
# Denies `git commit` on the default branch.
# Asks the user to approve every other `git commit`.
# Other commands get no decision.

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

arg='("[^"]*"|'\''[^'\'']*'\''|[^[:space:];&|]+)'
commit_re="(^|[;&|(\`[:space:]])git(([[:space:]]+-[Cc][[:space:]]+$arg)|([[:space:]]+--[a-z-]+=$arg))*[[:space:]]+commit([[:space:];&|)]|$)"
[[ $command =~ $commit_re ]] || exit 0

repo=$cwd
c_re="git[[:space:]]+-C[[:space:]]+$arg"
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

if git -C "$repo" rev-parse --verify --quiet HEAD >/dev/null; then
  if [[ -n $default && $branch == "$default" ]] ||
     [[ -z $default && ( $branch == main || $branch == master ) ]]; then
    decide deny "Do not commit to the default branch ($branch). Create a branch from origin/$branch first."
  fi
fi

decide ask "Approve this commit on branch ${branch:-unknown}."
