#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each pull request merge, also auto-merge, through `gh pr merge` or `gh api`.
# Asks the user to approve each new pull request, through `gh pr create` or `gh api`.
# Other commands get no decision.

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")

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

gh_re='(^|[;&|(`[:space:]/])gh[[:space:]]+'
[[ $command =~ $gh_re ]] || exit 0

write_re='[[:space:]](-[fFX]|--field|--raw-field|--method|--input)([[:space:]=]|[^[:space:]])'
get_re='[[:space:]](-X|--method)[[:space:]=]*GET([[:space:]]|$)'
api_writes() { [[ $command =~ $1 && $command =~ $write_re && ! $command =~ $get_re ]]; }

merge_re="${gh_re}pr[[:space:]]+merge([[:space:];&|)]|$)"
api_merge_re="${gh_re}api[[:space:]].*pulls/[^[:space:]/]+/merge([^[:alnum:]_/]|$)"
gql_merge_re="${gh_re}api[[:space:]].*(mergePullRequest|enablePullRequestAutoMerge)"
if [[ $command =~ $merge_re || $command =~ $gql_merge_re ]] || api_writes "$api_merge_re"; then
  decide ask "Approve merging this pull request."
fi

create_re="${gh_re}pr[[:space:]]+create([[:space:];&|)]|$)"
api_create_re="${gh_re}api[[:space:]].*repos/[^[:space:]]+/pulls([[:space:]\"'?]|$)"
gql_create_re="${gh_re}api[[:space:]].*createPullRequest"
if [[ $command =~ $create_re || $command =~ $gql_create_re ]] || api_writes "$api_create_re"; then
  decide ask "Approve opening this pull request."
fi

exit 0
