#!/usr/bin/env bash
# Waits on a request an agent opened with cards.requestAction (Officium, JAVA-1122) until the person
# answers it, and prints ONE line:
#
#   OFFICIUM_REQUEST_DONE <id>       the person did it: resume, then cards.closeRequest
#   OFFICIUM_REQUEST_DECLINED <id>   the person can't now: stop cleanly, leave the card resumable
#   OFFICIUM_REQUEST_CLOSED <id>     it was closed (withdrawn): carry on as if there were no request
#   OFFICIUM_REQUEST_TIMEOUT <id>    nobody answered within --minutes: publish your work and free the slot
#   OFFICIUM_REQUEST_FAILED <reason> it cannot wait (no token, unknown request): say so
#
# Usage: officium-request-wait.sh <requestId> [--minutes N]   (default 10; 0 = until answered)
# Run it in the background: finishing is what wakes the agent, at no cost while it waits.
#
# It long-polls GET /officium/v1/requests/<id>/wait with the account's heartbeat token (never the
# model's), so the answer arrives the moment the person gives it. It prints a status that matched a
# fixed word and the id it was given, never text the server sent. Network errors back off (1 s
# doubling to 30 s) and count against the same deadline.
#
# Token: OFFICIUM_HEARTBEAT_TOKEN, or the file OFFICIUM_HEARTBEAT_TOKEN_FILE (default
# ~/.config/officium/heartbeat-token). API: OFFICIUM_API_URL, else https://javadaba.com/api.
# The token reaches curl through --config on stdin, never its argv.

umask 077
id="${1:-}"
minutes=10
[ "${2:-}" = "--minutes" ] && minutes="${3:-10}"

if ! [[ "$id" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
  echo "OFFICIUM_REQUEST_FAILED usage: officium-request-wait.sh <requestId> [--minutes N]"
  exit 2
fi
[[ "$minutes" =~ ^[0-9]+$ ]] || minutes=10

token="${OFFICIUM_HEARTBEAT_TOKEN:-}"
token_file="${OFFICIUM_HEARTBEAT_TOKEN_FILE:-$HOME/.config/officium/heartbeat-token}"
[ -n "$token" ] || { [ -r "$token_file" ] && read -r token <"$token_file"; }
token="${token//[[:space:]]/}"
if [ -z "$token" ]; then
  echo "OFFICIUM_REQUEST_FAILED no_token"
  exit 1
fi

api="${OFFICIUM_API_URL:-https://javadaba.com/api}"
api="${api%/}"
poll="${OFFICIUM_REQUEST_POLL:-25}"
answer_file="$(mktemp)"
trap 'rm -f "$answer_file"' EXIT
deadline=$(( $(date +%s) + minutes * 60 ))
backoff=1

while :; do
  if [ "$minutes" -gt 0 ] && [ "$(date +%s)" -ge "$deadline" ]; then
    echo "OFFICIUM_REQUEST_TIMEOUT $id"
    exit 0
  fi
  code="$(printf 'header = "Authorization: Bearer %s"\n' "$token" | curl -s -o "$answer_file" \
    -w '%{http_code}' --max-time $(( poll + 15 )) --config - \
    "$api/officium/v1/requests/$id/wait?wait=$poll" 2>/dev/null)" || true
  case "$code" in
    200)
      status="$(grep -o '"status"[[:space:]]*:[[:space:]]*"[a-z]*"' "$answer_file" | head -1 \
        | sed 's/.*"\([a-z]*\)"$/\1/')"
      case "$status" in
        done) echo "OFFICIUM_REQUEST_DONE $id" ;;
        declined) echo "OFFICIUM_REQUEST_DECLINED $id" ;;
        closed) echo "OFFICIUM_REQUEST_CLOSED $id" ;;
        *) echo "OFFICIUM_REQUEST_FAILED unexpected_answer" ; exit 1 ;;
      esac
      exit 0
      ;;
    204) backoff=1 ;;
    401) echo "OFFICIUM_REQUEST_FAILED invalid_token"; exit 1 ;;
    403|404) echo "OFFICIUM_REQUEST_FAILED request_not_found"; exit 1 ;;
    *)
      sleep "$backoff"
      backoff=$(( backoff * 2 > 30 ? 30 : backoff * 2 ))
      ;;
  esac
done
