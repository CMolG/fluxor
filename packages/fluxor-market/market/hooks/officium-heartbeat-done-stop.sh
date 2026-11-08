#!/usr/bin/env bash
# stop -- the safety net behind officium-heartbeat-done-prompt: when a turn ends, every background
# ticker of the session whose task the payload's `background_tasks` no longer lists as running is
# stopped (its notification never arrived, or the task was stopped by hand). A client whose stop
# payload has no `background_tasks` is left alone: the ticker's own ceiling ends it. Sends nothing.
# Builtins only, no jq: a session with no background ticker costs one glob.

IFS= read -r -d '' payload
re='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]{1,128})"'
session=none
[[ $payload =~ $re ]] && session="${BASH_REMATCH[1]}"
re='"background_tasks"[[:space:]]*:'
[[ $payload =~ $re ]] || exit 0

# running <task>: whether the task's entry says it still runs. The entry runs from its bare
# `"id":"<task>"` to the next bare `"id"`; a key quoted inside a string never matches, because there
# its quotes are escaped. An entry with no status is taken as running: the ceiling still ends it.
running() {
  local re="\"id\"[[:space:]]*:[[:space:]]*\"$1\"(.*)" entry
  [[ $payload =~ $re ]] || return 1
  entry="${BASH_REMATCH[1]}"
  entry="${entry%%\"id\"*}"
  re='"status"[[:space:]]*:[[:space:]]*"([A-Za-z_]+)"'
  [[ $entry =~ $re ]] || return 0
  [ "${BASH_REMATCH[1]}" = running ]
}

for ticker in "${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/heartbeat/$session".*.tick; do
  [ -f "$ticker" ] || continue
  pid="" task=""
  { read -r pid; read -r task; } <"$ticker"
  [[ $task =~ ^[A-Za-z0-9_-]{1,128}$ ]] || continue   # a foreground call's ticker: its postTool stops it
  running "$task" && continue
  rm -f "$ticker"
  [ -n "$pid" ] && kill "$pid" 2>/dev/null
done
exit 0
