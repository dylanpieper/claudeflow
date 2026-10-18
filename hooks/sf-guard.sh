#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each `sf` or `sfdx` command that is not read-only,
# and shows the target Salesforce org.
# Read-only commands (list, display, query, ...) and other commands get no decision.

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")

# `sf` or `sfdx` in command position and its subcommand words, up to the first flag or separator.
calls=$(grep -oE "(^|[;&|(\`])[[:space:]]*((sudo|env|exec|command|time)[[:space:]]+)*([^[:space:];&|()]*/)?sf(dx)?([[:space:]]+[^-;&|()[:space:]][^;&|()[:space:]]*)*" <<<"$command")
[[ -n $calls ]] || exit 0

readonly_re='^(list|display|get|query|describe|preview|report|version|help|open|whoami)$'
needs_ask=0
while read -r call; do
  read -ra words <<<"$(sed -E 's#^.*(^|[/[:space:];&|(`])sf(dx)?([[:space:]]|$)##; s/:/ /g' <<<"$call")"
  ((${#words[@]})) || continue
  ro=0
  for w in "${words[@]}"; do
    [[ $w =~ $readonly_re ]] && ro=1
  done
  ((ro)) || needs_ask=1
done <<<"$calls"
((needs_ask)) || exit 0

org=$(grep -oE -- '(--target-org|-o)[= ]+[^[:space:]]+' <<<"$command" | head -1 | sed -E 's/^(--target-org|-o)[= ]+//')
if [[ -n $org ]]; then
  context="Target org (from the command): $org"
elif command -v sf >/dev/null; then
  org=$(sf config get target-org --json 2>/dev/null | jq -r '.result[0].value // empty')
  context="Target org (default): ${org:-none set}"
else
  context="The Salesforce CLI is not on PATH, so the target org is unknown."
fi

jq -n --arg r "Approve this Salesforce CLI command. It can change or delete org data or metadata."$'\n'"$context" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "ask",
    permissionDecisionReason: $r
  }
}'
