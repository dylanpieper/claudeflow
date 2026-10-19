#!/bin/bash
# Status line: model | dir | Caveman badge | Salesforce org | Azure subscription | context used (tokens)
# | 5h and 7d plan usage with reset.
# Reads Claude Code status line JSON on stdin. No network calls.

input=$(cat)

if ! command -v jq >/dev/null; then
  printf 'statusline: jq missing\n'
  exit 0
fi

# Unit separator, not tab: IFS whitespace would merge empty fields and shift later values.
IFS=$'\x1f' read -r sid model dir ctx_pct ctx_tok ctx_size h5 h5r d7 d7r cwd transcript < <(
  echo "$input" | jq -r '[
    (.session_id // ""),
    (.model.display_name // ""),
    ((.workspace.current_dir // .cwd // "") | split("/") | last // ""),
    ((.context_window.used_percentage | numbers | round) // ""),
    (.context_window.total_input_tokens // ""),
    (.context_window.context_window_size // ""),
    ((.rate_limits.five_hour.used_percentage | numbers | round) // ""),
    (.rate_limits.five_hour.resets_at // ""),
    ((.rate_limits.seven_day.used_percentage | numbers | round) // ""),
    (.rate_limits.seven_day.resets_at // ""),
    (.workspace.current_dir // .cwd // ""),
    (.transcript_path // "")
  ] | map(tostring) | join("\u001f")'
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
  local p=$2
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

# Salesforce org and Azure subscription, read from the CLI config files, because the CLIs take seconds.
# Shown after this session runs az, sf, or sfdx. The Salesforce org also shows in a Salesforce project.
# A per-session cache keeps the scanned byte offset and the CLIs found, so each refresh reads only new bytes,
# plus the last 64 KB again, in case a record was still being written. Caches older than 7 days are deleted.
used=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  cache=""
  [[ $sid =~ ^[A-Za-z0-9_-]+$ ]] && cache="$cfg/.statusline-cli/$sid"
  offset=0
  [ -n "$cache" ] && [ -f "$cache" ] && read -r offset used <"$cache"
  [[ $offset =~ ^[0-9]+$ ]] || offset=0
  size=$(wc -c <"$transcript" | tr -d ' ')
  [ "$size" -lt "$offset" ] && { offset=0; used=""; }
  start=$((offset > 65536 ? offset - 65536 : 0))
  new=$(export LC_ALL=C; tail -c +$((start + 1)) "$transcript" |
    grep -aoE '"name":"Bash","input":\{"command":"(\\.|[^"\\])*' | sed 's/\\n/ /g' |
    grep -aoE '(^|[^[:alnum:]_./-])(az|sf|sfdx)[[:space:]]' | tr -cd 'adfsxz\n')
  used=$(printf '%s\n%s\n' "$used" "$new" | tr ' ' '\n' | grep -E '^(az|sf|sfdx)$' | sort -u | tr '\n' ' ')
  if [ -n "$cache" ]; then
    [ -f "$cache" ] || find "${cache%/*}" -type f -mtime +7 -delete 2>/dev/null
    mkdir -p "${cache%/*}" && printf '%s %s\n' "$size" "$used" >"$cache"
  fi
fi

sf_root=""
d=$cwd
while [ -n "$d" ]; do
  [ -f "$d/sfdx-project.json" ] && { sf_root=$d; break; }
  [ "$d" = / ] || [ "$d" = . ] && break
  d=$(dirname "$d")
done

if [ -n "$sf_root" ] || [[ " $used " == *" sf "* || " $used " == *" sfdx "* ]]; then
  org=""
  for f in ${sf_root:+"$sf_root/.sf/config.json" "$sf_root/.sfdx/sfdx-config.json"} \
    "$HOME/.sf/config.json" "$HOME/.sfdx/sfdx-config.json"; do
    [ -f "$f" ] || continue
    org=$(jq -r '(."target-org" // .defaultusername // "") | strings
      | explode | map(select(. >= 32 and (. < 127 or . > 159))) | implode' "$f" 2>/dev/null)
    [ -n "$org" ] && break
  done
  [ -n "$org" ] && parts+=($'\033[36m'"sf $org$RST")
fi

if [[ " $used " == *" az "* ]]; then
  profile=${AZURE_CONFIG_DIR:-$HOME/.azure}/azureProfile.json
  if [ -f "$profile" ]; then
    IFS=$'\x1f' read -r az_sub az_tenant < <(
      LC_ALL=C sed $'1s/^\xEF\xBB\xBF//' "$profile" | jq -r 'first(.subscriptions[]? | select(.isDefault))
        | [(.name // ""), (.tenantDefaultDomain // .tenantDisplayName // .tenantId // "")]
        | map(explode | map(select(. >= 32 and (. < 127 or . > 159))) | implode) | join("\u001f")' 2>/dev/null
    )
    [ -n "$az_sub" ] && parts+=($'\033[36m'"az $az_sub$RST${az_tenant:+$DIM($az_tenant)$RST}")
  fi
fi

if [ -n "$ctx_pct" ]; then
  p=$ctx_pct
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
