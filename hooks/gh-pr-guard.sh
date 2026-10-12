#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each pull request merge, also auto-merge, through `gh pr merge` or `gh api`.
# Asks the user to approve each new pull request, through `gh pr create`, `gh pr new`, or `gh api`.
# Asks for each `gh api graphql` call that reads its query from a file, because the hook cannot see it.
# Asks for each command that mentions `gh` when `jq` is missing, because the hook cannot parse it.
# Other commands get no decision.
# Limits: the hook reads the command text only.
# It does not see into `bash -c` strings, shell aliases, or scripts.
# It finds `gh` in any word position, so text such as `echo gh pr merge` also asks.

ask() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

input=$(</dev/stdin)
if ! command -v jq >/dev/null; then
  [[ $input == *gh* ]] && ask "gh-pr-guard cannot check this command because jq is not on PATH."
  exit 0
fi
command=$(jq -r '.tool_input.command // empty' <<<"$input")

[[ $command == *gh* ]] || exit 0

# Prints one segment per line. Splits on ; & | and newlines outside quotes.
# A newline also ends any open quote, so a stray quote in a heredoc cannot hide later commands.
split_command() {
  LC_ALL=C awk '{
    out = ""; q = ""; n = length($0)
    for (i = 1; i <= n; i++) {
      c = substr($0, i, 1)
      if (q != "") {
        if (q == "\"" && c == "\\") { out = out c substr($0, i + 1, 1); i++; continue }
        if (c == q) q = ""
        out = out c; continue
      }
      if (c == "\047" || c == "\"") { q = c; out = out c }
      else if (c == "\\") { out = out c substr($0, i + 1, 1); i++ }
      else if (c == ";" || c == "&" || c == "|") { print out; out = "" }
      else out = out c
    }
    print out
  }' <<<"$1"
}

write_re='[[:space:]](-[fFX]|--field|--raw-field|--method|--input)([[:space:]=]|[^[:space:]])'
get_re='[[:space:]](-X|--method)[[:space:]=]*GET([[:space:]]|$)'
api_merge_re='pulls/[^[:space:]/]+/merge([^[:alnum:]_/]|$)'
api_create_re="repos/[^[:space:]]+/pulls([[:space:]\"'?]|$)"
query_file_re='[[:space:]](--input|(-F|--field)[[:space:]=]*query=@)'

check_pr() {
  local -a t=("$@")
  local i=0 n=${#t[@]}
  while ((i < n)) && [[ ${t[i]} == -* ]]; do
    case ${t[i]} in
      -R | --repo) ((i += 2)) ;;
      *) ((i++)) ;;
    esac
  done
  case ${t[i]} in
    merge) ask "Approve merging this pull request." ;;
    create | new) ask "Approve opening this pull request." ;;
  esac
}

check_api() {
  local segment=$1 writes=0
  [[ $segment =~ $write_re && ! $segment =~ $get_re ]] && writes=1
  if [[ $segment =~ (mergePullRequest|enablePullRequestAutoMerge) ]] ||
     { ((writes)) && [[ $segment =~ $api_merge_re ]]; }; then
    ask "Approve merging this pull request."
  fi
  if [[ $segment =~ createPullRequest ]] || { ((writes)) && [[ $segment =~ $api_create_re ]]; }; then
    ask "Approve opening this pull request."
  fi
  if [[ $segment =~ [[:space:]]graphql([[:space:]]|$) && $segment =~ $query_file_re ]]; then
    ask "Approve this GraphQL call. Its query is in a file, so the hook cannot check for a PR merge or create."
  fi
}

check_segment() {
  local segment=$1 k w
  local -a t
  read -ra t <<<"$segment"
  for ((k = 0; k < ${#t[@]}; k++)); do
    w=${t[k]}
    [[ $w == *gh ]] || continue
    while [[ $w == [\(\{\!\$\`\"\']* ]]; do w=${w:1}; done
    [[ ${w##*/} == gh ]] || continue
    case ${t[k + 1]} in
      pr) check_pr "${t[@]:k+2}" ;;
      api) check_api "$segment" ;;
    esac
  done
}

command=${command//$'\\\n'/ }
while IFS= read -r segment; do
  check_segment "$segment"
done < <(split_command "$command")

exit 0
