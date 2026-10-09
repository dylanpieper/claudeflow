#!/bin/bash
# Status line: model | dir | Caveman badge | context used (tokens) | 5h and 7d plan usage with reset.
# Reads Claude Code status line JSON on stdin. No network calls.

input=$(cat)

IFS=$'\t' read -r sid model dir ctx_pct ctx_tok ctx_size h5 h5r d7 d7r < <(
  echo "$input" | /usr/bin/jq -r '[
    (.session_id // ""),
    (.model.display_name // ""),
    ((.workspace.current_dir // .cwd // "") | split("/") | last // ""),
    (.context_window.used_percentage // ""),
    (.context_window.total_input_tokens // ""),
    (.context_window.context_window_size // ""),
    (.rate_limits.five_hour.used_percentage // ""),
    (.rate_limits.five_hour.resets_at // ""),
    (.rate_limits.seven_day.used_percentage // ""),
    (.rate_limits.seven_day.resets_at // "")
  ] | map(tostring) | join("\t")'
)

RST=$'\033[0m'
DIM=$'\033[2m'

color_for() {
  local p=${1%.*}
  if [ "$p" -ge 80 ]; then printf '\033[31m'
  elif [ "$p" -ge 50 ]; then printf '\033[33m'
  else printf '\033[32m'; fi
}

human_tokens() {
  awk -v n="$1" 'BEGIN{ if (n>=1000000) printf "%.1fM", n/1000000;
    else if (n>=1000) printf "%.0fk", n/1000; else printf "%d", n }'
}

until_reset() {
  local left=$(( $1 - $(date +%s) ))
  [ "$left" -le 0 ] && return
  if [ "$left" -ge 86400 ]; then
    printf '%dd%dh' $((left / 86400)) $((left % 86400 / 3600))
  elif [ "$left" -ge 3600 ]; then
    printf '%dh%dm' $((left / 3600)) $((left % 3600 / 60))
  else
    printf '%dm' $((left / 60))
  fi
}

usage_part() {
  [ -z "$2" ] && return
  local p; p=$(printf '%.0f' "$2")
  local out; out="$1 $(color_for "$p")${p}%${RST}"
  if [ -n "$3" ]; then
    local r; r=$(until_reset "$3")
    [ -n "$r" ] && out="$out${DIM}(${r})${RST}"
  fi
  printf '%s' "$out"
}

# Caveman mode: per-session file, then the legacy flag. A missing file or "off" means off.
cfg=${CLAUDE_CONFIG_DIR:-$HOME/.claude}
cave=""
if [[ $sid =~ ^[A-Za-z0-9_-]+$ ]] && [ -f "$cfg/.caveman-sessions/$sid.mode" ]; then
  cave=$(head -c 32 "$cfg/.caveman-sessions/$sid.mode")
elif [ -f "$cfg/.caveman-active" ]; then
  cave=$(head -c 32 "$cfg/.caveman-active")
fi
cave=$(printf '%s' "$cave" | tr -d '[:space:]')

parts=()
[ -n "$model" ] && parts+=("$model")
[ -n "$dir" ] && parts+=("$dir")
if [[ $cave =~ ^[a-z-]+$ ]] && [ "$cave" != off ]; then
  case $cave in
    caveman|lite|full) label=Caveman ;;
    ultracave|ultra) label=Ultracave ;;
    megacave|wenyan*) label=Megacave ;;
    *) label="Caveman:$cave" ;;
  esac
  parts+=($'\033[1;35m'"$label$RST")
fi

if [ -n "$ctx_pct" ]; then
  p=$(printf '%.0f' "$ctx_pct")
  part="ctx $(color_for "$p")${p}%${RST}"
  if [ -n "$ctx_tok" ] && [ -n "$ctx_size" ]; then
    part="$part${DIM}($(human_tokens "$ctx_tok")/$(human_tokens "$ctx_size"))${RST}"
  fi
  parts+=("$part")
fi

u5=$(usage_part "5h" "$h5" "$h5r")
u7=$(usage_part "7d" "$d7" "$d7r")
[ -n "$u5" ] && parts+=("$u5")
[ -n "$u7" ] && parts+=("$u7")

sep=" ${DIM}|${RST} "
out=""
for p in "${parts[@]}"; do
  out="${out:+$out$sep}$p"
done
printf '%s\n' "$out"
