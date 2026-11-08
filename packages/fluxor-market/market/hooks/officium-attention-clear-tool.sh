#!/usr/bin/env bash
# Clears what officium-attention marked: once a tool runs, the person types, or the turn ends,
# nothing waits on them any more. One script, shipped as three hooks (officium-attention-clear-tool,
# -prompt, -stop), one per event. Only a window that marked itself speaks, so on the common path it
# costs one file test. Token, API and the autonomous-loop switches as officium-attention; the
# request is detached, and the token reaches curl through --config on stdin, never its argv.

[ -z "${AUTOLOOP_SLOT:-}" ] || exit 0
[ "${OFFICIUM_SESSIONS:-}" != "0" ] || exit 0

IFS= read -r -d '' payload
re='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]{1,128})"'
[[ $payload =~ $re ]] || exit 0
session="${BASH_REMATCH[1]}"
marker="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/attention/$session.blocked"
[ -f "$marker" ] || exit 0
rm -f "$marker"

token="${OFFICIUM_HEARTBEAT_TOKEN:-}"
token_file="${OFFICIUM_HEARTBEAT_TOKEN_FILE:-$HOME/.config/officium/heartbeat-token}"
[ -n "$token" ] || { [ -r "$token_file" ] && read -r token <"$token_file"; }
token="${token//[[:space:]]/}"
[ -n "$token" ] || exit 0

api="${OFFICIUM_API_URL:-}"
[ -n "$api" ] || api='{{OFFICIUM_API}}'
case "$api" in '{{'*) api='https://javadaba.com/api' ;; esac   # installed without the param
{
  printf 'header = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\ndata-binary = "{\\"blocked\\":false}"\n' \
    "$token" \
    | curl -s -o /dev/null --max-time 3 -X PUT --config - "${api%/}/officium/v1/sessions/$session/attention"
} </dev/null >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
