#!/usr/bin/env bash
# preTool (every tool) -- Officium heartbeat: keeps the card an agent works lit on Officium's board,
# at zero model tokens.
#
# A card stays lit only while something beats for it. Without this hook every beat is a
# `cards.reportStatus` the MODEL has to decide to send: a turn and its tokens each time, and never
# during a long command it cannot interrupt, so a healthy 8-minute test run looks like a dead
# session. So the harness beats instead:
#   - one status line from the tool call (a shell call's description, the file being edited...), at
#     most one per OFFICIUM_HEARTBEAT_INTERVAL seconds (default 10), however many tools run;
#   - a shell call also starts a ticker that re-beats "<description>, 3m12s" every
#     OFFICIUM_HEARTBEAT_TICK seconds (default 30) until officium-heartbeat-done stops it on the
#     call's postTool, and that gives up on its own after 11 minutes;
#   - a shell call that goes to the background returns at once, so its postTool records the task id
#     in the ticker's file instead, and the ticker keeps beating while the agent waits, for up to
#     OFFICIUM_HEARTBEAT_BG_MAX seconds (default 7200). officium-heartbeat-done-prompt stops it when
#     the task's notification arrives, and officium-heartbeat-done-stop when a turn ends with the
#     task no longer running;
#   - a ticker also stops on its own, within one tick, once the client process that started it (the
#     CLAUDE_PID the hook inherits) is gone: a recycled or killed session never runs a postTool.
#     A failed call does not run PostToolUse either: officium-heartbeat-done-failure stops it.
# The server needs no card key: it renews whatever session this account's agent has live on this
# machine, and never starts one. Each beat also carries the model and effort of the transcript's last
# assistant line, read in the background send, never on the tool's path.
#
# Installing it is the opt-in. Token: OFFICIUM_HEARTBEAT_TOKEN, or the file
# OFFICIUM_HEARTBEAT_TOKEN_FILE (default ~/.config/officium/heartbeat-token), created under
# Officium's "Connect an agent". With no token it says so once per session and sends nothing.
# Machine: OFFICIUM_MACHINE, else COMPUTERNAME, else hostname. API: OFFICIUM_API_URL, else
# {{OFFICIUM_API}}. It never blocks a tool: the request is detached.
#
# Builtins only on the common path, and no jq: Git Bash on Windows has no jq and forks slowly
# (~0.3 s per call), and this runs on every tool. The fields it reads are JSON strings taken
# verbatim, still escaped, and sent back inside JSON as they came. State lives in a per-user 0700
# folder, and the token reaches curl through --config on stdin, never through its argv.

umask 077

token="${OFFICIUM_HEARTBEAT_TOKEN:-}"
token_file="${OFFICIUM_HEARTBEAT_TOKEN_FILE:-$HOME/.config/officium/heartbeat-token}"
[ -n "$token" ] || { [ -r "$token_file" ] && read -r token <"$token_file"; }
token="${token//[[:space:]]/}"

IFS= read -r -d '' payload
# get <field> <var>: the first `"field": "..."` string in the payload into <var>, still escaped. A
# key quoted inside another string cannot match, because there its quotes are escaped.
get() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\""
  if [[ $payload =~ $re ]]; then printf -v "$2" '%s' "${BASH_REMATCH[1]}"; else printf -v "$2" ''; fi
}

get tool_name tool
get session_id session
get tool_use_id call
get transcript_path transcript
session="${session//[^A-Za-z0-9_-]/}"
call="${call//[^A-Za-z0-9_-]/}"
transcript="${transcript//\\\\//}"   # a Windows path comes JSON-escaped: C:\\Users -> C:/Users

state="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/heartbeat"
[ -d "$state" ] || mkdir -p "$state" 2>/dev/null || exit 0
case "$OSTYPE" in msys*|cygwin*) ;; *) [ -O "$state" ] || exit 0 ;; esac

if [ -z "$token" ]; then
  # The marker officium-usage checks too, so a session hears it once, from whichever hook runs first.
  set -C
  if { : >"$state/${session:-none}.notoken"; } 2>/dev/null; then
    printf '%s\n' '{"systemMessage":"Officium heartbeat is installed but has no token: the card can lapse and no time gets reported. Create one in Officium (Connect an agent) and save it to ~/.config/officium/heartbeat-token, or set OFFICIUM_HEARTBEAT_TOKEN."}'
  fi
  exit 0
fi

case "$tool" in
  ''|mcp__officium__*) exit 0 ;;   # its own MCP writes already renew the card
esac

get description description
get file_path file
[ -n "$file" ] || get notebook_path file
file="${file##*[/\\]}"
case "$tool" in
  Bash|PowerShell|shell|exec_command) text="${description:-Running a command}" ;;
  Edit|MultiEdit|Write|NotebookEdit|apply_patch) text="Editing ${file:-files}" ;;
  Read) text="Reading $file" ;;
  Grep|Glob) text="Searching the code" ;;
  Agent|Task) text="Delegating: ${description:-a subtask}" ;;
  WebFetch|WebSearch) text="Researching on the web" ;;
  *) text="Using $tool" ;;
esac
text="${text:0:200}"
while [ "${text: -1}" = "\\" ]; do text="${text:0:${#text}-1}"; done   # never end on half an escape

machine="${OFFICIUM_MACHINE:-${COMPUTERNAME:-$(hostname 2>/dev/null)}}"
machine="${machine//[\"\\]/}"
[ -n "$machine" ] || exit 0
api="${OFFICIUM_API_URL:-}"
[ -n "$api" ] || api='{{OFFICIUM_API}}'
case "$api" in '{{'*) api='https://javadaba.com/api' ;; esac   # installed without the param
url="${api%/}/officium/v1/heartbeat"
interval="${OFFICIUM_HEARTBEAT_INTERVAL:-10}"

# runs_on: the model and effort of the transcript's last assistant line, as extra JSON fields. Only a
# `"model":"` or `"effort":"` with bare quotes matches -- inside a string their quotes are escaped --
# and `<synthetic>` never does. Two forks, which is why only the background send calls it.
runs_on() {
  [ -n "$transcript" ] && [ -r "$transcript" ] || return 0
  local found line model="" effort=""
  found=$(tail -c 262144 "$transcript" 2>/dev/null | grep -oE '"(model|effort)":"[A-Za-z0-9._-]{1,100}"')
  while IFS= read -r line; do
    case "$line" in
      '"model":'*) model="${line:9:${#line}-10}" ;;
      '"effort":'*) effort="${line:10:${#line}-11}" ;;
    esac
  done <<<"$found"
  [ -z "$model" ] || printf ',"model":"%s"' "$model"
  [ -z "$effort" ] || printf ',"effort":"%s"' "${effort:0:20}"
}

# gone <pid>: true only when the client process is positively gone. Under msys/cygwin CLAUDE_PID is a
# Windows pid that kill cannot see, so it reads the WINPID column of `ps -W`; if that lists nothing,
# the process is taken as alive.
gone() {
  case "$OSTYPE" in
    msys*|cygwin*)
      local line listed="" w
      while IFS= read -r line; do
        listed=1
        read -r _ _ _ w _ <<<"$line"
        [ "$w" = "$1" ] && return 1
      done < <(ps -W 2>/dev/null)
      [ -n "$listed" ] ;;
    *) ! kill -0 "$1" 2>/dev/null ;;
  esac
}

# send <text>: one beat. curl reads the token and the body from its --config on stdin, quoted the
# way a config file quotes (a backslash and a double quote escaped), so neither is in its argv.
send() {
  local body
  body="$(printf '{"machine":"%s","text":"%s"%s}' "$machine" "$1" "$(runs_on)")"
  body="${body//\\/\\\\}"
  printf 'header = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\ndata-binary = "%s"\n' \
    "$token" "${body//\"/\\\"}" | curl -s -o /dev/null --max-time 2 -X POST --config - "$url"
}

# One beat per interval per session: the first hook to create this slot's file sends, every other
# one in the same slot finds it there. `set -C` makes the create atomic, so parallel tools cannot
# both win.
beat() {
  local now slot mark f won=""
  now=$(date +%s)
  slot=$((now / interval))
  mark="$state/${session:-none}.$slot.slot"
  set -C
  { : >"$mark"; } 2>/dev/null && won=1
  set +C
  [ -n "$won" ] || return 0
  for f in "$state/${session:-none}".*.slot; do [ "$f" = "$mark" ] || rm -f "$f"; done
  if [ "${OFFICIUM_HEARTBEAT_SYNC:-}" = "1" ]; then
    send "$1"
  else
    ( send "$1" ) </dev/null >/dev/null 2>&1 &
  fi
}

beat "$text"

case "$tool" in
  Bash|PowerShell|shell|exec_command) ;;
  *) exit 0 ;;
esac
[ -n "$call" ] || exit 0
ticker="$state/${session:-none}.$call.tick"
tick="${OFFICIUM_HEARTBEAT_TICK:-30}"
bg_max="${OFFICIUM_HEARTBEAT_BG_MAX:-7200}"
owner="${CLAUDE_PID:-}"
[[ $bg_max =~ ^[0-9]+$ ]] || bg_max=7200
: >"$ticker"   # before the ticker starts, which stops as soon as the file is gone
(
  started=$(date +%s)
  max=660
  while [ -f "$ticker" ]; do
    sleep "$tick"
    [ -f "$ticker" ] || break
    [[ $owner =~ ^[0-9]+$ ]] && gone "$owner" && break
    # A second line is the task id officium-heartbeat-done wrote when the call went to the background.
    task=""
    { read -r _; read -r task; } <"$ticker" 2>/dev/null
    [ -z "$task" ] || max="$bg_max"
    now=$(date +%s)
    elapsed=$((now - started))
    [ "$elapsed" -lt "$max" ] || break
    beat "$text, $((elapsed / 60))m$((elapsed % 60))s"
  done
  rm -f "$ticker"
) </dev/null >/dev/null 2>&1 &
echo "$!" >"$ticker"
exit 0
