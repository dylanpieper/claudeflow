#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each `gh pr merge`, `gh pr create`, and `gh pr new`.
# Asks the user to approve each `gh api` call that can write, because a write can open or merge a PR.
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
  raw_re='"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*gh'
  [[ $input =~ $raw_re ]] && ask "gh-pr-guard cannot check this command because jq is not on PATH."
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

field_re='[[:space:]](-[fF]|--field|--raw-field|--input)([[:space:]=]|[^[:space:]])'
method_re="[[:space:]](-X|--method)[[:space:]=]*[\"']?([A-Za-z]+)"
graphql_re='[[:space:]]graphql([[:space:]]|$)'

# Sets NW to word $1 without quotes, leading ( { ! $ backtick backslash, and trailing ) } ; backtick.
norm() {
  NW=${1//[\"\']/}
  while [[ $NW == [\(\{\!\$\`\\]* ]]; do NW=${NW:1}; done
  while [[ $NW == *[\)\}\;\`] ]]; do NW=${NW%?}; done
}

check_pr() {
  local -a t=()
  local w
  for w in "$@"; do norm "$w"; t+=("$NW"); done
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

# Asks for a segment with a `gh api` call that can write: any graphql call,
# any method other than GET, or fields or input without a GET method.
# The hook does not parse the endpoint, so it also asks for writes that are not about PRs.
check_api() {
  local s=" $1" m field=0 get=0
  [[ $s =~ $graphql_re ]] && ask "Approve this GraphQL call. It can open or merge a pull request."
  [[ $s =~ $field_re ]] && field=1
  while [[ $s =~ $method_re ]]; do
    m=${BASH_REMATCH[2]}
    if [[ $m == [Gg][Ee][Tt] ]]; then
      get=1
    else
      ask "Approve this gh api $m call. It can open or merge a pull request."
    fi
    s=${s#*"${BASH_REMATCH[0]}"}
  done
  ((field && !get)) && ask "Approve this gh api call. Its fields make it a POST, which can open or merge a pull request."
}

is_gh() {
  [[ $1 == *gh* ]] || return 1
  norm "$1"
  NW=${NW##*[\(\`]}
  [[ ${NW##*/} == gh ]]
}

check_segment() {
  local segment=$1 k
  local -a t
  read -ra t <<<"$segment"
  for ((k = 0; k < ${#t[@]}; k++)); do
    is_gh "${t[k]}" || continue
    norm "${t[k + 1]}"
    case $NW in
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
