#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each change to the default branch that skips a pull request:
#   `git merge` while the default branch is checked out,
#   `git pull` of a different branch into the default branch,
#   `git push` that updates the default branch on the remote.
# Asks for each command that mentions `git` when `jq` is missing, because the hook cannot parse it.
# Other commands get no decision.
# Limits: the hook reads the command text only.
# It follows `cd`, `git -C`, `--git-dir`, subshells, and backtick substitutions.
# It does not see into `bash -c` strings, git or shell aliases, or scripts.
# It finds `git` in any word position, so text such as `echo git merge x` can also ask.

ask() {
  jq -n --arg r "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $r
    }
  }'
  exit 0
}

input=$(</dev/stdin)
if ! command -v jq >/dev/null; then
  raw_re='"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*git'
  if [[ $input =~ $raw_re ]]; then
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"git-merge-guard cannot check this command because jq is not on PATH."}}'
  fi
  exit 0
fi
command=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

[[ $command == *git* ]] || exit 0

# Prints one segment per line. Splits on ; & | and newlines outside quotes.
# Prints a marker line for each ( ) and backtick outside quotes, so the caller can track subshells.
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
      else if (c == "(" || c == ")" || c == "`") { print out; print "\001" c; out = "" }
      else out = out c
    }
    print out
  }' <<<"$1"
}

# Succeeds when $3 is the default branch of remote $2 in repo $1.
# Without a remote HEAD, main and master count as default.
is_default() {
  local d
  d=$(git -C "$1" symbolic-ref --short "refs/remotes/$2/HEAD" 2>/dev/null)
  d=${d#"$2"/}
  if [[ -n $d ]]; then
    [[ $3 == "$d" ]]
  else
    [[ $3 == main || $3 == master ]]
  fi
}

unquote() {
  local s=${1#[\"\']}
  echo "${s%[\"\']}"
}

resolve() {
  local p
  p=$(unquote "$1")
  p=${p/#\~/$HOME}
  [[ $p = /* ]] || p=$dir/$p
  echo "$p"
}

lead_re='^(if|then|else|elif|do|while|until|!|\{|env|command|exec|time|nohup|sudo|timeout|xargs)$'
global_value_re='^(-C|-c|--git-dir|--work-tree|--namespace|--exec-path|--super-prefix|--config-env)$'
value_opt_re='^(-o|--push-option|--server-option|--repo|--receive-pack|--exec|-m|-F|--file|-s|--strategy|-X|--strategy-option|--into-name|--depth|--deepen|--shallow-since|--shallow-exclude|--upload-pack|-j|--jobs|--negotiation-tip)$'

dir=$cwd
olddir=$cwd
dirs=()

do_cd() {
  local -a a=("$@")
  local i=0
  while ((i < ${#a[@]})) && [[ ${a[i]} == -[LPe@]* && ${a[i]} != - ]]; do ((i++)); done
  local target=${a[i]:-$HOME}
  local prev=$dir
  if [[ $target == - ]]; then
    dir=$olddir
  else
    dir=$(resolve "$target")
  fi
  olddir=$prev
}

# Checks the git call in words $@, which start after the `git` word.
check_git() {
  local -a t=("$@")
  local i=0 n=${#t[@]} repo=$dir

  while ((i < n)) && [[ ${t[i]} == -* ]]; do
    case ${t[i]} in
      -C) repo=$(resolve "${t[i+1]}") ;;
      --git-dir) repo=$(resolve "${t[i+1]}") ;;
      --git-dir=*) repo=$(resolve "${t[i]#*=}") ;;
    esac
    if [[ ${t[i]} =~ $global_value_re ]]; then ((i += 2)); else ((i++)); fi
  done
  ((i < n)) || return 0
  [[ ${repo##*/} == .git ]] && repo=${repo%/.git}

  local sub=${t[i]}
  ((i++))
  [[ $sub =~ ^(merge|pull|push)$ ]] || return 0

  local -a pos=()
  local all=0 tags=0
  while ((i < n)); do
    case ${t[i]} in
      --abort | --quit) return 0 ;;
      --all | --mirror) all=1 ;;
      --tags) tags=1 ;;
      -*)
        if [[ ${t[i]} =~ $value_opt_re || ($sub == push && ${t[i]} == --recurse-submodules) ]]; then
          ((i++))
        fi
        ;;
      *) pos+=("$(unquote "${t[i]}")") ;;
    esac
    ((i++))
  done

  git -C "$repo" rev-parse --git-dir >/dev/null 2>&1 || return 0
  local branch
  branch=$(git -C "$repo" branch --show-current 2>/dev/null)

  local remote=${pos[0]:-origin} spec dst
  case $sub in
    merge)
      [[ -n $branch ]] && is_default "$repo" origin "$branch" &&
        ask "Approve this merge into the default branch ($branch)."
      ;;
    pull)
      [[ -n $branch ]] && is_default "$repo" "$remote" "$branch" || return 0
      for spec in "${pos[@]:1}"; do
        spec=${spec#+}
        spec=${spec%%:*}
        spec=${spec#refs/heads/}
        is_default "$repo" "$remote" "$spec" ||
          ask "Approve this pull of $spec into the default branch ($branch)."
      done
      ;;
    push)
      ((all)) && ask "Approve this push of all branches, which includes the default branch."
      if ((${#pos[@]} <= 1)); then
        ((tags)) && return 0
        [[ -n $branch ]] && is_default "$repo" "$remote" "$branch" &&
          ask "Approve this push to the default branch ($branch) on $remote."
      else
        for spec in "${pos[@]:1}"; do
          spec=${spec#+}
          dst=${spec##*:}
          dst=${dst#refs/heads/}
          if [[ $dst == HEAD ]]; then
            [[ -n $branch ]] || ask "Approve this push of a detached HEAD. The hook cannot tell its target branch."
            dst=$branch
          fi
          is_default "$repo" "$remote" "$dst" &&
            ask "Approve this push to the default branch ($dst) on $remote."
        done
      fi
      ;;
  esac
  return 0
}

check_segment() {
  local -a t
  read -ra t <<<"$1"
  local k=0 n=${#t[@]} w

  while ((k < n)) && [[ ${t[k]} =~ $lead_re || (${t[k]} == *=* && ${t[k]} != -*) ]]; do ((k++)); done
  if [[ ${t[k]} == cd ]]; then
    do_cd "${t[@]:k+1}"
    return 0
  fi

  for ((k = 0; k < n; k++)); do
    w=${t[k]}
    [[ $w == *git ]] || continue
    while [[ $w == [\{\!\$\"\']* ]]; do w=${w:1}; done
    [[ ${w##*/} == git ]] && check_git "${t[@]:k+1}"
  done
  return 0
}

enter_subshell() { dirs+=("$dir|$olddir"); }

leave_subshell() {
  ((${#dirs[@]})) || return 0
  local saved=${dirs[${#dirs[@]}-1]}
  unset 'dirs[${#dirs[@]}-1]'
  dir=${saved%%|*}
  olddir=${saved#*|}
}

command=${command//$'\\\n'/ }
in_backticks=0
while IFS= read -r segment; do
  case $segment in
    $'\001(') enter_subshell ;;
    $'\001)') leave_subshell ;;
    $'\001`')
      if ((in_backticks)); then leave_subshell; else enter_subshell; fi
      ((in_backticks = !in_backticks))
      ;;
    *) check_segment "$segment" ;;
  esac
done < <(split_command "$command")

exit 0
