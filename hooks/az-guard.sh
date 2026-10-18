#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each `az` command that is not read-only,
# and shows the active Azure tenant and subscription.
# Read-only commands (show, list, get, query, ...) and other commands get no decision.

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")

# `az` in command position and its subcommand words, up to the first flag or separator.
calls=$(grep -oE "(^|[;&|(\`])[[:space:]]*((sudo|env|exec|command|time)[[:space:]]+)*([^[:space:];&|()]*/)?az([[:space:]]+[^-;&|()[:space:]][^;&|()[:space:]]*)*" <<<"$command")
[[ -n $calls ]] || exit 0

readonly_re='^(show|list|get|query|exists|version|find|help|check-[a-z-]+|(show|list|get)-[a-z-]+)$'
needs_ask=0
while read -r call; do
  read -ra words <<<"$(sed -E 's#^.*(^|[/[:space:];&|(`])az([[:space:]]|$)##' <<<"$call")"
  ((${#words[@]})) || continue
  [[ ${words[${#words[@]}-1]} =~ $readonly_re ]] || needs_ask=1
done <<<"$calls"
((needs_ask)) || exit 0

if command -v az >/dev/null; then
  context=$(az account show -o json --only-show-errors 2>/dev/null |
    jq -r '"Tenant: \(.tenantDisplayName // "unknown") (\(.tenantId))\nSubscription: \(.name) (\(.id))\nUser: \(.user.name)"')
  context=${context:-"No active Azure account. Run az login."}
else
  context="The Azure CLI is not on PATH, so the active tenant is unknown."
fi
override=$(grep -oE -- '--subscription[= ]+[^[:space:]]+' <<<"$command")
[[ -n $override ]] && context+=$'\n'"This command sets ${override}."

jq -n --arg r "Approve this Azure CLI command. It can change or delete resources."$'\n'"$context" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "ask",
    permissionDecisionReason: $r
  }
}'
