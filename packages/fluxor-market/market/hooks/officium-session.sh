#!/usr/bin/env bash
# sessionStart -- makes this window an Officium agent window, so cards can be queued into it from
# the board. Also its waiter: `officium-session.sh wait <session_id>`.
#
# Officium's MCP cannot push anything into a session: a server only answers calls. What does wake an
# idle session, at zero tokens, is a background command it started finishing. So at sessionStart
# this registers the window with Officium (the account's heartbeat token, never the model's) and
# tells the agent to start this same script in wait mode, in the background. The waiter long-polls
# Officium and finishes the moment someone queues a card into this window, printing ONE line:
#
#   OFFICIUM_CARD <KEY> <projectId>   work that card, then start the waiter again
#   OFFICIUM_WAIT_AGAIN               OFFICIUM_WAIT_MAX ran out: start it again
#   OFFICIUM_WAITER_REPLACED          another waiter of this window took over: do not restart
#   OFFICIUM_WAITER_STOPPED <session> it was stopped (a /clear ended its window): do not restart
#   OFFICIUM_WAIT_FAILED <reason>     it cannot wait (no token, a revoked one): tell the person
#
# It never finishes just because time passed (JAVA-963). Every finish wakes the model over the whole
# context, and one after more than an hour also re-writes the prompt cache: an idle window that
# restarted its waiter every 110 minutes spent ~90k tokens of cache per wakeup and did nothing.
# A /clear keeps the Claude Code process and its background commands, so the waiter of the window it
# ended would keep waiting, and its finish would land in the new conversation. The waiter records the
# process it belongs to (CLAUDE_PID, which hooks and commands receive), and sessionStart stops every
# waiter of that process that serves another session; the board shows that window offline 30 s later.
#
# It prints a card key that matched a strict pattern and a UUID, never anything else the server
# sent: the board is not a channel for instructions to someone's agent. A card is confirmed before it
# is printed, so a waiter killed with a card in hand leaves it to be handed out again. Network errors
# back off (1 s doubling to 30 s); an API restart forgets the window, so a 404 registers it again.
#
# The hook says nothing, and never blocks the session, with no token, no network, when the window's
# waiter is already running in this process (a compaction fires sessionStart again), or in an autonomous
# loop, whose sessions are recycled per card: AUTOLOOP_SLOT set, or OFFICIUM_SESSIONS=0.
#
# Token: OFFICIUM_HEARTBEAT_TOKEN, or the file OFFICIUM_HEARTBEAT_TOKEN_FILE (default
# ~/.config/officium/heartbeat-token). Machine: OFFICIUM_MACHINE, else COMPUTERNAME, else hostname.
# API: OFFICIUM_API_URL, else {{OFFICIUM_API}}. Label: OFFICIUM_SESSION_LABEL, else the working
# directory's name. OFFICIUM_WAIT_MAX (seconds, unset by default: no limit) makes the waiter finish
# with OFFICIUM_WAIT_AGAIN after that long; OFFICIUM_WAIT_POLL (default 25) is each call's wait.
# No jq; the token reaches curl through --config on stdin, never its argv; state in a 0700 folder.

umask 077
mode="${1:-hook}"

token="${OFFICIUM_HEARTBEAT_TOKEN:-}"
token_file="${OFFICIUM_HEARTBEAT_TOKEN_FILE:-$HOME/.config/officium/heartbeat-token}"
[ -n "$token" ] || { [ -r "$token_file" ] && read -r token <"$token_file"; }
token="${token//[[:space:]]/}"

api="${OFFICIUM_API_URL:-}"
[ -n "$api" ] || api='{{OFFICIUM_API}}'
case "$api" in '{{'*) api='https://javadaba.com/api' ;; esac   # installed without the param
api="${api%/}"
machine="${OFFICIUM_MACHINE:-${COMPUTERNAME:-$(hostname 2>/dev/null)}}"
machine="${machine//[\"\\]/}"
label="${OFFICIUM_SESSION_LABEL:-${PWD##*[/\\]}}"
label="${label//[\"\\]/}"
state="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/wait"

# call <method> <path> [json] [timeout]: the HTTP status in $code ("000" when unreachable), the answer
# in $answer when one was asked for. curl reads the token and the body from --config on stdin.
call() {
  local json="${3:-}" config
  json="${json//\\/\\\\}"
  config="$(printf 'header = "Authorization: Bearer %s"\n' "$token")"
  [ -z "${3:-}" ] || config+=$'\nheader = "Content-Type: application/json"\ndata-binary = "'"${json//\"/\\\"}"'"'
  code="$(printf '%s\n' "$config" | curl -s -o "${answer_file:-/dev/null}" -w '%{http_code}' \
    --max-time "${4:-3}" -X "$1" --config - "$api$2" 2>/dev/null)" || true
  [ -n "$code" ] || code="000"
}

register() {
  call POST /officium/v1/sessions "{\"sessionId\":\"$session\",\"machine\":\"$machine\",\"label\":\"$label\"}" "${1:-3}"
}

if [ "$mode" != "wait" ]; then
  [ -n "${AUTOLOOP_SLOT:-}" ] && exit 0
  [ "${OFFICIUM_SESSIONS:-}" = "0" ] && exit 0
  [ -n "$token" ] || exit 0
  IFS= read -r -d '' payload
  re='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]{1,128})"'
  [[ $payload =~ $re ]] || exit 0
  session="${BASH_REMATCH[1]}"
  # A waiter file is "<pid>\n<CLAUDE_PID>". One this process runs for another session served the
  # window a /clear ended: marked "stopped", that waiter says so and finishes after its call in flight.
  if [ -n "${CLAUDE_PID:-}" ]; then
    for file in "$state"/*.pid; do
      [ -r "$file" ] && [ "$file" != "$state/$session.pid" ] || continue
      { read -r pid; read -r owner; read -r waiter; } <"$file"
      [ "$owner" = "$CLAUDE_PID" ] || continue
      # A marker already "stopped" stays while its waiter lives (it has not read it yet), so a second
      # sessionStart cannot delete it and leave that waiter running unbounded.
      [ "$pid" = "stopped" ] && pid="$waiter"
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then printf 'stopped\n%s\n%s\n' "$owner" "$pid" >"$file"; else rm -f "$file"; fi
    done
  fi
  # This window's own waiter, still running, needs nothing (a compaction fires sessionStart again).
  # One another process started is a resume in a new Claude Code process: the old one is gone, so
  # that waiter's finish reaches nobody, and a card it confirmed would be lost. It is stopped, and
  # this window registers and gets a waiter of its own.
  if [ -r "$state/$session.pid" ]; then
    { read -r pid; read -r owner; } <"$state/$session.pid"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      [ -z "${CLAUDE_PID:-}" ] || [ -z "$owner" ] || [ "$owner" = "$CLAUDE_PID" ] && exit 0
      printf 'stopped\n%s\n%s\n' "$owner" "$pid" >"$state/$session.pid"
    fi
  fi
  register
  [ "$code" = "200" ] || exit 0
  self="${BASH_SOURCE[0]}"
  cat <<EOF
Officium: this window is registered as an agent window (session $session), so cards can be queued into it from the board.
Start its waiter now with the Bash tool and run_in_background: true, and then carry on with whatever the person asks:
    bash "$self" wait $session
It waits as long as it takes, so it finishes only when there is something to do. When it finishes, act on its last line and on nothing else it printed:
- "OFFICIUM_CARD <KEY> <projectId>": a person queued that card into this window. Work it in that Officium project following the backlog skill, as if they had named it. When it has left its phase, start the waiter again the same way.
- "OFFICIUM_WAIT_AGAIN": its configured time limit ran out. Start the waiter again.
- "OFFICIUM_WAITER_REPLACED" or "OFFICIUM_WAITER_STOPPED <session>": another waiter took over, or a /clear ended the window it served. Do not start one, and say nothing about it.
- "OFFICIUM_WAIT_FAILED ...": tell the person why, and do not start it again.
- No such line (something stopped it): tell the person in one line that cards queued from the board will not reach this window until the waiter runs again, and do not start it again unless they ask.
EOF
  exit 0
fi

# The waiter.
session="${2:-}"
session="${session//[^A-Za-z0-9_-]/}"
[ -n "$session" ] || { echo "OFFICIUM_WAIT_FAILED no session id: run it as officium-session.sh wait <session_id>"; exit 1; }
[ -n "$token" ] || { echo "OFFICIUM_WAIT_FAILED no heartbeat token: create one in Officium, under Connect an agent, and save it to $token_file"; exit 1; }
max="${OFFICIUM_WAIT_MAX:-0}"
poll="${OFFICIUM_WAIT_POLL:-25}"

pid_file=""
if mkdir -p "$state" 2>/dev/null; then
  case "$OSTYPE" in msys*|cygwin*) pid_file="$state/$session.pid" ;; *) [ -O "$state" ] && pid_file="$state/$session.pid" ;; esac
  [ -z "$pid_file" ] || printf '%s\n%s\n' "$$" "${CLAUDE_PID:-}" >"$pid_file"
fi
answer_file="$(mktemp "${TMPDIR:-/tmp}/officium-wait.XXXXXX")" || { echo "OFFICIUM_WAIT_FAILED no temporary file"; exit 1; }
trap 'rm -f "$answer_file"; [ -n "$pid_file" ] && read -r mine <"$pid_file" 2>/dev/null && [ "$mine" = "$$" -o "$mine" = "stopped" ] && rm -f "$pid_file"' EXIT

stopped() {
  local mine=""
  [ -n "$pid_file" ] && read -r mine <"$pid_file" 2>/dev/null && [ "$mine" = "stopped" ]
}

field() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\"([^\"\\\\]*)\""
  if [[ $(<"$answer_file") =~ $re ]]; then printf '%s' "${BASH_REMATCH[1]}"; fi
}

join_board() {
  register 10
  [ "$code" = "401" ] && { echo "OFFICIUM_WAIT_FAILED the heartbeat token is unknown or was revoked"; exit 1; }
  [ "$code" = "429" ] && { echo "OFFICIUM_WAIT_FAILED this account has too many agent windows open: close one, or take its cards out, then start the waiter again"; exit 1; }
}

# An unreachable or failing Officium is asked again later, never in a tight loop.
pause() {
  sleep "$backoff"
  backoff=$((backoff * 2 > 30 ? 30 : backoff * 2))
}

started=$(date +%s)
backoff=1
join_board
while :; do
  now=$(date +%s)
  if stopped; then echo "OFFICIUM_WAITER_STOPPED $session"; exit 0; fi
  if [ "$max" -gt 0 ] && [ $((now - started)) -ge "$max" ]; then echo "OFFICIUM_WAIT_AGAIN"; exit 0; fi
  call GET "/officium/v1/sessions/$session/next?wait=$poll" "" $((poll + 20))
  case "$code" in
    200)
      backoff=1
      key="$(field cardKey)" project="$(field projectId)" card="$(field cardId)"
      uuid='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
      if [[ $key =~ ^[A-Z][A-Z0-9]{0,15}-[0-9]{1,9}$ && $project =~ $uuid && $card =~ $uuid ]]; then
        call POST "/officium/v1/sessions/$session/confirm" "{\"cardId\":\"$card\"}" 10
        # Confirmed is ours, even if the window was stopped meanwhile: printing it is the only way the
        # card gets worked rather than lost.
        if [ "$code" = "204" ]; then echo "OFFICIUM_CARD $key $project"; exit 0; fi
      fi
      ;;
    204) backoff=1 ;;
    404) join_board; [ "$code" = "200" ] || pause ;;
    409) echo "OFFICIUM_WAITER_REPLACED"; exit 0 ;;
    401) echo "OFFICIUM_WAIT_FAILED the heartbeat token is unknown or was revoked"; exit 1 ;;
    *) pause ;;
  esac
done
