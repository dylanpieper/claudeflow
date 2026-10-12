#!/bin/bash
# PostToolUse hook for Write and Edit.
# After a change to a Markdown file (.md, .qmd, .Rmd), finds each list or sub-list with one item
# and sends the lines back to Claude, because a single item must be a sentence.
# Skips front matter and fenced code blocks. Other files get no output.

input=$(</dev/stdin)
command -v jq >/dev/null || exit 0
file=$(jq -r '.tool_input.file_path // empty' <<<"$input")

[[ $file == *.md || $file == *.qmd || $file == *.Rmd ]] || exit 0
[[ -f $file ]] || exit 0

found=$(LC_ALL=C awk '
  function indent_of(s) { return match(s, /[^[:space:]]/) - 1 }
  function close_from(level,   k, n, keys, i) {
    n = 0
    for (k in count) if (k + 0 >= level) keys[++n] = k
    for (i = 1; i <= n; i++) {
      k = keys[i]
      if (count[k] == 1) printf "line %d: %s\n", first[k], text[k]
      delete count[k]; delete first[k]; delete text[k]
    }
  }
  NR == 1 && /^---[[:space:]]*$/ { front = 1; next }
  front { if (/^---[[:space:]]*$/) front = 0; next }
  /^[[:space:]]*(```|~~~)/ { fence = !fence; next }
  fence { next }
  /^[[:space:]]*$/ { next }
  /^[[:space:]]*([-*+]|[0-9]+[.)])[[:space:]]/ {
    level = indent_of($0)
    close_from(level + 1)
    if (level in count) count[level]++
    else { count[level] = 1; first[level] = NR; sub(/^[[:space:]]+/, "", $0); text[level] = $0 }
    next
  }
  { close_from(indent_of($0)) }
  END { close_from(0) }
' "$file")

[[ -n $found ]] || exit 0

jq -n --arg r "$file has a list or sub-list with one item. Write one item as a sentence, in its parent item if it is a sub-item:
$found" '{decision: "block", reason: $r}'
