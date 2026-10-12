#!/bin/bash
# PreToolUse hook for Bash.
# Asks the user to approve each change to the default branch that skips a pull request:
#   `git merge` while the default branch is checked out,
#   `git pull` of a different branch into the default branch,
#   `git push` that updates the default branch on the remote.
# Other commands get no decision.

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

check_segment() {
  local -a t
  read -ra t <<<"$1"
  local i=0 n=${#t[@]} repo=$cwd

  while ((i < n)) && [[ ${t[i]} == *=* && ${t[i]} != -* ]]; do ((i++)); done
  ((i < n)) && [[ ${t[i]##*/} == git ]] || return 0
  ((i++))
  while ((i < n)); do
    case ${t[i]} in
      -C) repo=$(unquote "${t[i+1]}"); ((i += 2)) ;;
      -c) ((i += 2)) ;;
      -*) ((i++)) ;;
      *) break ;;
    esac
  done
  ((i < n)) || return 0
  repo=${repo/#\~/$HOME}
  [[ $repo = /* ]] || repo=$cwd/$repo

  local sub=${t[i]}
  local -a args=("${t[@]:i+1}") pos=()
  local a all=0 tags=0
  for a in "${args[@]}"; do
    case $a in
      --abort | --quit) return 0 ;;
      --all | --mirror) all=1 ;;
      --tags) tags=1 ;;
      -*) ;;
      *) pos+=("$(unquote "$a")") ;;
    esac
  done

  local branch
  branch=$(git -C "$repo" branch --show-current 2>/dev/null)
  [[ -n $branch ]] || return 0

  local remote=${pos[0]:-origin} spec dst
  case $sub in
    merge)
      is_default "$repo" origin "$branch" &&
        decide "Approve this merge into the default branch ($branch)."
      ;;
    pull)
      for spec in "${pos[@]:1}"; do
        spec=${spec#+}
        spec=${spec%%:*}
        spec=${spec#refs/heads/}
        is_default "$repo" "$remote" "$branch" && ! is_default "$repo" "$remote" "$spec" &&
          decide "Approve this pull of $spec into the default branch ($branch)."
      done
      ;;
    push)
      ((all)) && decide "Approve this push of all branches, which includes the default branch."
      if ((${#pos[@]} <= 1)); then
        ((tags)) && return 0
        is_default "$repo" "$remote" "$branch" &&
          decide "Approve this push to the default branch ($branch) on $remote."
      else
        for spec in "${pos[@]:1}"; do
          spec=${spec#+}
          dst=${spec##*:}
          dst=${dst#refs/heads/}
          [[ $dst == HEAD ]] && dst=$branch
          is_default "$repo" "$remote" "$dst" &&
            decide "Approve this push to the default branch ($dst) on $remote."
        done
      fi
      ;;
  esac
  return 0
}

while IFS= read -r segment; do
  check_segment "$segment"
done < <(tr ';|&()`' '\n' <<<"$command")

exit 0
