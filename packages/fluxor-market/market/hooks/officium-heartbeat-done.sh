#!/usr/bin/env bash
# postTool (every tool) -- stops the ticker officium-heartbeat started for a long shell call, once
# the call has returned. A call that went to the background has returned without finishing: its
# ticker keeps beating, and its task id goes into the ticker's file, for the ticker to lift its
# ceiling and for officium-heartbeat-done-stop to check. Sends nothing. Builtins only: it runs after
# every tool, and a call that started no ticker costs one file test.

IFS= read -r -d '' payload
get() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\"([A-Za-z0-9_-]{1,128})\""
  if [[ $payload =~ $re ]]; then printf -v "$2" '%s' "${BASH_REMATCH[1]}"; else printf -v "$2" ''; fi
}
get session_id session
get tool_use_id call
[ -n "$call" ] || exit 0

ticker="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/heartbeat/${session:-none}.$call.tick"
[ -f "$ticker" ] || exit 0
get backgroundTaskId task
if [ -n "$task" ]; then
  printf '%s\n' "$task" >>"$ticker"
  exit 0
fi
read -r pid <"$ticker"
rm -f "$ticker"
[ -n "$pid" ] && kill "$pid" 2>/dev/null
exit 0
