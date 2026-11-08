#!/usr/bin/env bash
# statusLine -- the window's bar, and its telemetry for Officium's board.
#
# Claude Code runs this, at zero tokens, when a session starts or resumes, after every assistant
# message, after /compact and when the permission mode changes, and hands it the window's state as
# JSON on stdin. It prints one short line (model · effort · context · cost · 5 h limit), and it
# also reports that state to Officium, so the person can see which of their windows to queue a card
# into before doing it.
#
# Reporting never slows the bar: the request goes from a detached child, and Claude Code cancels a
# status line still running when the next update comes. At most one report per
# OFFICIUM_TELEMETRY_INTERVAL seconds (default 10), except that a change of model, effort, fast mode
# or thinking goes at once. A report the interval held back is not lost: one child waits the rest of
# the interval and sends whatever is newest then, so the last message of a turn always arrives.
#
# It draws the bar and reports nothing with no token, for a window Officium does not know (a 404),
# or in an autonomous loop, whose windows are never registered: AUTOLOOP_SLOT set, or
# OFFICIUM_SESSIONS=0. Token: OFFICIUM_HEARTBEAT_TOKEN, or the file OFFICIUM_HEARTBEAT_TOKEN_FILE
# (default ~/.config/officium/heartbeat-token). API: OFFICIUM_API_URL, else {{OFFICIUM_API}}.
#
# Bash builtins and curl, no Node and no jq: the nested fields are read one object level at a time
# (a JSON string may hold braces, so strings are matched whole), and numbers are re-sent as written.
# State lives in a per-user 0700 folder; the token reaches curl through --config on stdin.
#
#   officium-statusline.sh                          the status line (stdin: Claude Code's JSON)
#   officium-statusline.sh --post <session> <ms>    the detached report, after waiting <ms>

umask 077
STR='"([^"\\]|\\.)*"'
INNER="([^{}\"]|$STR)*"
OBJ="\\{($INNER|\\{$INNER\\})*\\}"
NUM='-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?'

state="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/statusline"

token() {
  token="${OFFICIUM_HEARTBEAT_TOKEN:-}"
  local file="${OFFICIUM_HEARTBEAT_TOKEN_FILE:-$HOME/.config/officium/heartbeat-token}"
  [ -n "$token" ] || { [ -r "$file" ] && read -r token <"$file"; }
  token="${token//[[:space:]]/}"
}

# obj <key> <text> <var>: the object under "key" in <text>, without its braces and without the
# objects nested in it, so a scalar read from it is that level's own.
obj() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*($OBJ)" body
  if [[ $2 =~ $re ]]; then
    body="${BASH_REMATCH[1]:1:${#BASH_REMATCH[1]}-2}"
    while [[ $body =~ \"[^\"]*\"[[:space:]]*:[[:space:]]*(\{$INNER\}) ]]; do
      body="${body/"${BASH_REMATCH[1]}"/null}"
    done
    printf -v "$3" '%s' "$body"
  else
    printf -v "$3" ''
  fi
}
# str|num|bool <key> <text> <var>: a scalar of that type, as written; empty when absent or another type.
str() { local re="\"$1\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\""; [[ $2 =~ $re && -n ${BASH_REMATCH[1]} ]] && printf -v "$3" '%s' "${BASH_REMATCH[1]}" || printf -v "$3" ''; }
num() { local re="\"$1\"[[:space:]]*:[[:space:]]*($NUM)"; [[ $2 =~ $re ]] && printf -v "$3" '%s' "${BASH_REMATCH[1]}" || printf -v "$3" ''; }
bool() { local re="\"$1\"[[:space:]]*:[[:space:]]*(true|false)"; [[ $2 =~ $re ]] && printf -v "$3" '%s' "${BASH_REMATCH[1]}" || printf -v "$3" ''; }
# round <number> <var>: half up, like the board's Math.round (printf alone rounds half to even).
round() {
  local fixed
  printf -v fixed '%.6f' "$1" 2>/dev/null || { printf -v "$2" ''; return; }
  local whole="${fixed%.*}" frac="${fixed#*.}"
  if [ "${fixed:0:1}" = "-" ]; then
    [ "$((10#$frac))" -gt 500000 ] && whole=$((whole - 1))
  else
    [ "$((10#$frac))" -ge 500000 ] && whole=$((whole + 1))
  fi
  printf -v "$2" '%d' "$whole"
}

# telemetry <input>: sets $body, the flat JSON Officium's telemetry route takes, and $sig, what makes
# a report go at once; plus $bar, the line drawn.
telemetry() {
  local in="$1" o v r fields=() k
  local model_id model_name effort thinking fast ctx_pct cost_usd five_pct
  add() { [ -n "$3" ] || return 0; if [ "$2" = s ]; then fields+=("\"$1\":\"$3\""); else fields+=("\"$1\":$3"); fi; }
  addi() { [ -n "$2" ] || return 0; round "$2" r; add "$1" n "$r"; }
  instant() { [ -n "$2" ] || return 0; local s; round "$2" s; s=$(date -u -r "$s" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d "@$s" +%Y-%m-%dT%H:%M:%S); add "$1" s "$s.000Z"; }

  obj context_window "$in" o
  num used_percentage "$o" ctx_pct; add contextUsedPercent n "$ctx_pct"
  num total_input_tokens "$o" v; addi contextInputTokens "$v"
  num context_window_size "$o" v; addi contextWindowSize "$v"
  obj model "$in" o
  str id "$o" model_id; add modelId s "$model_id"
  str display_name "$o" model_name; add modelName s "$model_name"
  obj effort "$in" o
  str level "$o" effort; add effort s "$effort"
  obj thinking "$in" o
  bool enabled "$o" thinking; add thinking b "$thinking"
  bool fast_mode "$in" fast; add fastMode b "$fast"
  obj cost "$in" o
  num total_cost_usd "$o" cost_usd; add costUsd n "$cost_usd"
  num total_duration_ms "$o" v; addi durationMs "$v"
  num total_api_duration_ms "$o" v; addi apiDurationMs "$v"
  num total_lines_added "$o" v; addi linesAdded "$v"
  num total_lines_removed "$o" v; addi linesRemoved "$v"
  obj five_hour "$in" o
  num used_percentage "$o" five_pct; add fiveHourUsedPercent n "$five_pct"
  num resets_at "$o" v; TZ=UTC0 instant fiveHourResetsAt "$v"
  obj seven_day "$in" o
  num used_percentage "$o" v; add sevenDayUsedPercent n "$v"
  num resets_at "$o" v; TZ=UTC0 instant sevenDayResetsAt "$v"
  str session_name "$in" v; add sessionName s "$v"
  obj workspace "$in" o
  str project_dir "$o" v; add projectDir s "$v"
  str git_worktree "$o" v; add gitWorktree s "$v"
  obj repo "$in" o
  local host owner name
  str host "$o" host; str owner "$o" owner; str name "$o" name
  [ -n "$host" ] && [ -n "$owner" ] && [ -n "$name" ] && add repo s "$host/$owner/$name"
  obj pr "$in" o
  num number "$o" v; addi prNumber "$v"
  str url "$o" v; add prUrl s "$v"
  str version "$in" v; add version s "$v"

  body="{"
  for k in "${fields[@]}"; do body+="$k,"; done
  body="${body%,}}"
  sig="$model_id|$effort|$fast|$thinking"

  local shown="${model_name:-${model_id:-Claude}}"
  shown="${shown//\\\"/\"}"; shown="${shown//\\\\/\\}"; shown="${shown//\\\//\/}"
  bar="$shown"
  [ -z "$effort" ] || bar+=" · $effort"
  [ -z "$ctx_pct" ] || { round "$ctx_pct" r; bar+=" · ctx $r%"; }
  [ -z "$cost_usd" ] || { printf -v v '%.2f' "$cost_usd" 2>/dev/null && bar+=" · \$$v"; }
  [ -z "$five_pct" ] || { round "$five_pct" r; bar+=" · 5h $r%"; }
}

now_ms() { local t="${EPOCHREALTIME/[.,]/}"; now=$((10#$t / 1000)); }

# post <session> <delayMs>: waits, then sends the newest telemetry. A delayed one also clears the
# pending mark and records the send, so the next update counts its interval from now.
post() {
  local session="$1" telemetry="" at
  [ "${2:-0}" -le 0 ] || sleep "$(printf '%d.%03d' $(($2 / 1000)) $(($2 % 1000)))"
  [ -r "$state/$session.latest" ] && IFS= read -r telemetry <"$state/$session.latest"
  if [ "${2:-0}" -gt 0 ]; then
    rm -f "$state/$session.pending"
    if [ -n "$telemetry" ]; then
      now_ms; IFS= read -r at <"$state/$session.sig" 2>/dev/null
      printf '%s %s\n' "$now" "${at#* }" >"$state/$session.sig"
    fi
  fi
  [ -n "$telemetry" ] || return 0
  token
  local api="${OFFICIUM_API_URL:-}"
  [ -n "$api" ] || api='{{OFFICIUM_API}}'
  case "$api" in '{{'*) api='https://javadaba.com/api' ;; esac
  telemetry="${telemetry//\\/\\\\}"
  printf 'header = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\ndata-binary = "%s"\n' \
    "$token" "${telemetry//\"/\\\"}" \
    | curl -s -o /dev/null --max-time 3 -X PUT --config - "${api%/}/officium/v1/sessions/$session/telemetry"
}

if [ "${1:-}" = "--post" ]; then
  [[ ${2:-} =~ ^[A-Za-z0-9_-]{1,128}$ ]] || exit 0
  [[ ${3:-0} =~ ^[0-9]+$ ]] || exit 0
  post "$2" "${3:-0}" >/dev/null 2>&1
  exit 0
fi

IFS= read -r -d '' input
telemetry "$input"
printf '%s\n' "$bar"

[ -z "${AUTOLOOP_SLOT:-}" ] || exit 0
[ "${OFFICIUM_SESSIONS:-}" != "0" ] || exit 0
re='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]{1,128})"'
[[ $input =~ $re ]] || exit 0
session="${BASH_REMATCH[1]}"
token
[ -n "$token" ] || exit 0
[ -d "$state" ] || mkdir -p "$state" 2>/dev/null || exit 0
case "$OSTYPE" in msys*|cygwin*) ;; *) [ -O "$state" ] || exit 0 ;; esac

# Whether this update reports now, later, or rides a report already waiting.
interval=$(( ${OFFICIUM_TELEMETRY_INTERVAL:-10} > 0 ? ${OFFICIUM_TELEMETRY_INTERVAL:-10} * 1000 : 1000 ))
now_ms
printf '%s\n' "$body" >"$state/$session.latest"
last="" pending=""
[ -r "$state/$session.sig" ] && IFS= read -r last <"$state/$session.sig"
last_at="${last%% *}" last_sig="${last#* }"
if [ -z "$last" ] || [ $((now - last_at)) -ge "$interval" ] || [ "$last_sig" != "$sig" ]; then
  printf '%s %s\n' "$now" "$sig" >"$state/$session.sig"
  delay=0
else
  [ -r "$state/$session.pending" ] && read -r pending <"$state/$session.pending"
  [ -n "$pending" ] && [ $((now - pending)) -lt $((2 * interval)) ] && exit 0   # one already waits
  printf '%s\n' "$now" >"$state/$session.pending"
  delay=$((last_at + interval - now))
  [ "$delay" -ge 0 ] || delay=0
fi
( trap '' HUP INT TERM; post "$session" "$delay" ) </dev/null >/dev/null 2>&1 &
exit 0
