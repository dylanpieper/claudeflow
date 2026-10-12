#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each pull request merge, also auto-merge, through `gh pr merge` or `gh api`.
# Asks the user to approve each new pull request, through `gh pr create`, `gh pr new`, or `gh api`.
# Asks for each `gh api graphql` call that reads its query from a file, because the hook cannot see it.
# Other commands get no decision.
# Limits: the hook reads the command text only.
# It does not see into `bash -c` strings, shell aliases, or scripts.

command -v jq >/dev/null || { echo "gh-pr-guard: jq is not on PATH, so the guard is off." >&2; exit 1; }

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")

[[ $command == *gh* ]] || exit 0

decide() {
  jq -n --arg r "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $r
    }
  }'
  exit 0
}

write_re='[[:space:]](-[fFX]|--field|--raw-field|--method|--input)([[:space:]=]|[^[:space:]])'
get_re='[[:space:]](-X|--method)[[:space:]=]*GET([[:space:]]|$)'
api_merge_re='pulls/[^[:space:]/]+/merge([^[:alnum:]_/]|$)'
api_create_re="repos/[^[:space:]]+/pulls([[:space:]\"'?]|$)"
query_file_re='[[:space:]](--input|(-F|--field)[[:space:]=]*query=@)'

check_segment() {
  local segment=$1
  local -a t
  read -ra t <<<"$segment"
  local i=0 n=${#t[@]}

  while ((i < n)) && [[ ${t[i]} == *=* && ${t[i]} != -* || ${t[i]} =~ ^(env|command|exec|time|nohup)$ ]]; do
    ((i++))
  done
  ((i < n)) && [[ ${t[i]##*/} == gh ]] || return 0
  ((i++))

  case ${t[i]} in
    pr)
      ((i++))
      while ((i < n)) && [[ ${t[i]} == -* ]]; do
        case ${t[i]} in
          -R | --repo) ((i += 2)) ;;
          *) ((i++)) ;;
        esac
      done
      case ${t[i]} in
        merge) decide "Approve merging this pull request." ;;
        create | new) decide "Approve opening this pull request." ;;
      esac
      ;;
    api)
      local writes=0
      [[ $segment =~ $write_re && ! $segment =~ $get_re ]] && writes=1
      if [[ $segment =~ (mergePullRequest|enablePullRequestAutoMerge) ]] ||
         { ((writes)) && [[ $segment =~ $api_merge_re ]]; }; then
        decide "Approve merging this pull request."
      fi
      if [[ $segment =~ createPullRequest ]] || { ((writes)) && [[ $segment =~ $api_create_re ]]; }; then
        decide "Approve opening this pull request."
      fi
      if [[ $segment =~ [[:space:]]graphql([[:space:]]|$) && $segment =~ $query_file_re ]]; then
        decide "Approve this GraphQL call. Its query is in a file, so the hook cannot check for a PR merge or create."
      fi
      ;;
  esac
  return 0
}

command=${command//$'\\\n'/ }
while IFS= read -r segment; do
  check_segment "$segment"
done < <(tr ';|&' '\n' <<<"$command")

exit 0
