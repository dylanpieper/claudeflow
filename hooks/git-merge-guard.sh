#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each change to the default branch that skips a pull request:
#   `git merge` while the default branch is checked out,
#   `git pull` of a different branch into the default branch,
#   `git push` that updates the default branch on the remote.
# Other commands get no decision.
# Limits: the hook reads the command text only.
# It follows `cd <dir>` and `git -C <dir>`, but it does not see into `bash -c` strings,
# git or shell aliases, or scripts.

command -v jq >/dev/null || { echo "git-merge-guard: jq is not on PATH, so the guard is off." >&2; exit 1; }

input=$(cat)
command=$(jq -r '.tool_input.command // empty' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

[[ $command == *git* ]] || exit 0

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

# Options of merge, pull, and push that take their value as the next word.
value_opt_re='^(-o|--push-option|--repo|--receive-pack|--exec|-m|-F|--file|-s|--strategy|-X|--strategy-option|--into-name|--depth|--deepen|--shallow-since|--shallow-exclude|--upload-pack)$'

dir=$cwd

check_segment() {
  local -a t
  read -ra t <<<"$1"
  local i=0 n=${#t[@]}

  if [[ ${t[0]} == cd ]]; then
    ((n > 1)) && dir=$(resolve "${t[1]}")
    return 0
  fi

  while ((i < n)) && [[ ${t[i]} == *=* && ${t[i]} != -* || ${t[i]} =~ ^(env|command|exec|time|nohup)$ ]]; do
    ((i++))
  done
  ((i < n)) && [[ ${t[i]##*/} == git ]] || return 0
  ((i++))

  local repo=$dir
  while ((i < n)); do
    case ${t[i]} in
      -C) repo=$(resolve "${t[i+1]}"); ((i += 2)) ;;
      -c) ((i += 2)) ;;
      -*) ((i++)) ;;
      *) break ;;
    esac
  done
  ((i < n)) || return 0

  local sub=${t[i]}
  ((i++))
  local -a pos=()
  local all=0 tags=0
  while ((i < n)); do
    case ${t[i]} in
      --abort | --quit) return 0 ;;
      --all | --mirror) all=1 ;;
      --tags) tags=1 ;;
      -*) [[ ${t[i]} =~ $value_opt_re ]] && ((i++)) ;;
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
        decide "Approve this merge into the default branch ($branch)."
      ;;
    pull)
      [[ -n $branch ]] && is_default "$repo" "$remote" "$branch" || return 0
      for spec in "${pos[@]:1}"; do
        spec=${spec#+}
        spec=${spec%%:*}
        spec=${spec#refs/heads/}
        is_default "$repo" "$remote" "$spec" ||
          decide "Approve this pull of $spec into the default branch ($branch)."
      done
      ;;
    push)
      ((all)) && decide "Approve this push of all branches, which includes the default branch."
      if ((${#pos[@]} <= 1)); then
        ((tags)) && return 0
        [[ -n $branch ]] && is_default "$repo" "$remote" "$branch" &&
          decide "Approve this push to the default branch ($branch) on $remote."
      else
        for spec in "${pos[@]:1}"; do
          spec=${spec#+}
          dst=${spec##*:}
          dst=${dst#refs/heads/}
          if [[ $dst == HEAD ]]; then
            [[ -n $branch ]] || decide "Approve this push of a detached HEAD. The hook cannot tell its target branch."
            dst=$branch
          fi
          is_default "$repo" "$remote" "$dst" &&
            decide "Approve this push to the default branch ($dst) on $remote."
        done
      fi
      ;;
  esac
  return 0
}

command=${command//$'\\\n'/ }
while IFS= read -r segment; do
  check_segment "$segment"
done < <(tr ';|&()`' '\n' <<<"$command")

exit 0
