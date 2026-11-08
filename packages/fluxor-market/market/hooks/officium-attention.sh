#!/usr/bin/env bash
# notification (permission prompt, MCP question) -- tells Officium's board this agent window waits on
# its person.
#
# A window stopped at a permission prompt, or at a question an MCP server asked, works on nothing
# until someone answers, and a card queued into it waits too. This marks the window blocked on the
# board ("Waiting on you"); the officium-attention-clear hooks clear it on the next tool run, prompt
# or turn end.
#
# Silent with no token, for any other notification, for an odd session id, and in an autonomous
# loop, whose sessions run without prompts: AUTOLOOP_SLOT set, or OFFICIUM_SESSIONS=0. Token:
# OFFICIUM_HEARTBEAT_TOKEN, or the file OFFICIUM_HEARTBEAT_TOKEN_FILE (default
# ~/.config/officium/heartbeat-token). API: OFFICIUM_API_URL, else {{OFFICIUM_API}}. Builtins only
# and no jq; the request is detached, so a dead network never holds the prompt; the mark lives in a
# per-user 0700 folder; the token reaches curl through --config on stdin, never its argv.

umask 077
[ -z "${AUTOLOOP_SLOT:-}" ] || exit 0
[ "${OFFICIUM_SESSIONS:-}" != "0" ] || exit 0

IFS= read -r -d '' payload
get() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\"([A-Za-z0-9_-]{1,128})\""
  if [[ $payload =~ $re ]]; then printf -v "$2" '%s' "${BASH_REMATCH[1]}"; else printf -v "$2" ''; fi
}
get session_id session
get notification_type reason
[ -n "$session" ] || exit 0
case "$reason" in
  permission_prompt|elicitation_dialog) ;;
  *) exit 0 ;;
esac

token="${OFFICIUM_HEARTBEAT_TOKEN:-}"
token_file="${OFFICIUM_HEARTBEAT_TOKEN_FILE:-$HOME/.config/officium/heartbeat-token}"
[ -n "$token" ] || { [ -r "$token_file" ] && read -r token <"$token_file"; }
token="${token//[[:space:]]/}"
[ -n "$token" ] || exit 0

state="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/attention"
[ -d "$state" ] || mkdir -p "$state" 2>/dev/null || exit 0
case "$OSTYPE" in msys*|cygwin*) ;; *) [ -O "$state" ] || exit 0 ;; esac
: >"$state/$session.blocked"

api="${OFFICIUM_API_URL:-}"
[ -n "$api" ] || api='{{OFFICIUM_API}}'
case "$api" in '{{'*) api='https://javadaba.com/api' ;; esac   # installed without the param
{
  printf 'header = "Authorization: Bearer %s"\nheader = "Content-Type: application/json"\ndata-binary = "{\\"blocked\\":true,\\"reason\\":\\"%s\\"}"\n' \
    "$token" "$reason" \
    | curl -s -o /dev/null --max-time 3 -X PUT --config - "${api%/}/officium/v1/sessions/$session/attention"
} </dev/null >/dev/null 2>&1 &
disown 2>/dev/null
exit 0
