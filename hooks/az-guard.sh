#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each `az` command that is not read-only,
# and shows the active Azure tenant and subscription.
# A command is read-only when its last subcommand word is show, list, get, query, or a similar verb.
# Asks for each command that mentions `az` when `jq` is missing, because the hook cannot parse it.
# Other commands get no decision.
# Limits: the hook reads the command text only. It does not see into shell aliases or scripts.
# It finds `az` in any word position, so text such as `echo az vm delete` also asks.

ask_raw() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

input=$(</dev/stdin)
if ! command -v jq >/dev/null; then
  raw_re='"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*az'
  [[ $input =~ $raw_re ]] && ask_raw "az-guard cannot check this command because jq is not on PATH."
  exit 0
fi
command=$(jq -r '.tool_input.command // empty' <<<"$input")

[[ $command == *az* ]] || exit 0

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

is_az() {
  [[ $1 == *az* ]] || return 1
  norm "$1"
  NW=${NW##*[\(\`]}
  [[ ${NW##*/} == az ]]
}

readonly_re='^(show|list|get|query|exists|version|find|help|check-[a-z-]+|(show|list|get)-[a-z-]+)$'
redirect_re='^[0-9]*[<>&]'

ask() {
  local context sub=$1 envs=$2
  if command -v az >/dev/null; then
    context=$(az account show -o json --only-show-errors 2>/dev/null |
      jq -r '"Tenant: \(.tenantDisplayName // "unknown") (\(.tenantId))\nSubscription: \(.name) (\(.id))\nUser: \(.user.name)"')
    context=${context:-"No active Azure account. Run az login."}
  else
    context="The Azure CLI is not on PATH, so the active tenant is unknown."
  fi
  [[ -n $sub ]] && context+=$'\n'"This command sets --subscription $sub."
  [[ -n $envs ]] && context+=$'\n'"This command sets${envs}, so the tenant above may not apply."
  jq -n --arg r "Approve this Azure CLI command. It can change or delete resources."$'\n'"$context" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $r
    }
  }'
  exit 0
}

# Checks the az call that starts after word $1 of the segment words in T.
# Flags before the first subcommand word, such as --debug, are skipped.
check_call() {
  local i=$1 last="" sub="" envs="" j
  local n=${#T[@]}
  for ((j = 0; j < i; j++)); do
    [[ ${T[j]} =~ ^AZURE_[A-Z_]*= ]] && envs+=" ${T[j]}"
  done
  for ((i = i + 1; i < n; i++)); do
    norm "${T[i]}"
    [[ -z $NW || $NW =~ $redirect_re ]] && break
    if [[ $NW == -* ]]; then
      [[ -n $last ]] && break
      continue
    fi
    last=$NW
  done
  for ((; i < n; i++)); do
    norm "${T[i]}"
    case $NW in
      --subscription=*) sub=${NW#*=} ;;
      --subscription) norm "${T[i + 1]}"; sub=$NW ;;
    esac
  done
  [[ -z $last || $last =~ $readonly_re ]] || ask "$sub" "$envs"
}

command=${command//$'\\\n'/ }
while IFS= read -r segment; do
  read -ra T <<<"$segment"
  for ((k = 0; k < ${#T[@]}; k++)); do
    is_az "${T[k]}" && check_call "$k"
  done
done < <(split_command "$command")

exit 0
