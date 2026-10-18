#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each `sf` or `sfdx` command that is not read-only,
# and shows the target Salesforce org.
# A command is read-only only when its subcommand path is in the READONLY list.
# Asks for each command that mentions `sf` when `jq` is missing, because the hook cannot parse it.
# Other commands get no decision.
# Limits: the hook reads the command text only. It does not see into shell aliases or scripts.
# It finds `sf` and `sfdx` in any word position, so text such as `echo sf org delete` also asks.

ask_raw() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

input=$(</dev/stdin)
if ! command -v jq >/dev/null; then
  raw_re='"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*sf'
  [[ $input =~ $raw_re ]] && ask_raw "sf-guard cannot check this command because jq is not on PATH."
  exit 0
fi
command=$(jq -r '.tool_input.command // empty' <<<"$input")

[[ $command == *sf* ]] || exit 0

# Subcommand paths that only read. `sfdx force:a:b` is checked as `a b`.
READONLY=(
  "" "version" "help" "plugins" "commands" "which" "search"
  "org list" "org display" "org display user" "org open"
  "org list metadata" "org list metadata-types" "org list limits" "org list users" "org list auth"
  "config get" "config list" "alias list"
  "data query" "data soql query" "data get record" "data record get"
  "sobject describe" "sobject list" "schema sobject describe" "schema sobject list"
  "project deploy preview" "project deploy report" "project retrieve preview" "source status"
  "apex list log" "apex get log" "apex log list" "apex log get" "apex get test"
  "package list" "package version list" "package version report" "package installed list"
  "limits api display" "info releasenotes display"
)

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

# Sets NW to word $1 without quotes, leading ( { ! $ backtick backslash, and trailing ) } ; backtick.
norm() {
  NW=${1//[\"\']/}
  while [[ $NW == [\(\{\!\$\`\\]* ]]; do NW=${NW:1}; done
  while [[ $NW == *[\)\}\;\`] ]]; do NW=${NW%?}; done
}

is_sf() {
  [[ $1 == *sf* ]] || return 1
  norm "$1"
  NW=${NW##*[\(\`]}
  [[ ${NW##*/} == sf || ${NW##*/} == sfdx ]]
}

redirect_re='^[0-9]*[<>&]'
org_flag_re='^(-o|--target-org|-u|--targetusername|-v|--target-dev-hub)$'
org_eq_re='^(--target-org|--targetusername|--target-dev-hub)=(.*)$'

ask() {
  local context org=$1 flag=$2 cli
  if [[ -n $flag ]]; then
    context="Target org (from $flag): ${org:-unknown}"
  else
    for cli in sf sfdx; do
      command -v "$cli" >/dev/null || continue
      org=$("$cli" config get target-org --json 2>/dev/null | jq -r '.result[0].value // empty')
      context="Target org (default): ${org:-none set}"
      break
    done
    context=${context:-"The Salesforce CLI is not on PATH, so the target org is unknown."}
  fi
  jq -n --arg r "Approve this Salesforce CLI command. It can change or delete org data or metadata."$'\n'"$context" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $r
    }
  }'
  exit 0
}

# Checks the sf call that starts after word $1 of the segment words in T.
check_call() {
  local i=$1 org="" flag="" p
  local -a path=() parts
  local n=${#T[@]}
  for ((i = i + 1; i < n; i++)); do
    norm "${T[i]}"
    [[ -z $NW || $NW == -* || $NW =~ $redirect_re ]] && break
    read -ra parts <<<"${NW//:/ }"
    path+=("${parts[@]}")
  done
  [[ ${path[0]:-} == force ]] && path=("${path[@]:1}")
  for ((; i < n; i++)); do
    norm "${T[i]}"
    if [[ $NW =~ $org_eq_re ]]; then
      flag=${BASH_REMATCH[1]}; org=${BASH_REMATCH[2]}
    elif [[ $NW =~ $org_flag_re ]]; then
      flag=$NW; norm "${T[i + 1]}"
      [[ $NW == -* ]] && org="" || org=$NW
    fi
  done
  for p in "${READONLY[@]}"; do
    [[ "${path[*]}" == "$p" ]] && return
  done
  ask "$org" "$flag"
}

command=${command//$'\\\n'/ }
while IFS= read -r segment; do
  read -ra T <<<"$segment"
  for ((k = 0; k < ${#T[@]}; k++)); do
    is_sf "${T[k]}" && check_call "$k"
  done
done < <(split_command "$command")

exit 0
