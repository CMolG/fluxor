#!/usr/bin/env bash
# promptSubmit -- stops the heartbeat ticker of a background shell call once the call has ended.
# Claude Code tells the agent that a background command finished with a prompt carrying
# <task-notification> ... <tool-use-id>toolu_...</tool-use-id> ... </task-notification>, one per
# task; each names the call whose ticker officium-heartbeat-done left running. Sends nothing.
# Builtins only: any other prompt costs one pattern match.

IFS= read -r -d '' payload
[[ $payload == *"<task-notification>"* ]] || exit 0
re='"session_id"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_-]{1,128})"'
session=none
[[ $payload =~ $re ]] && session="${BASH_REMATCH[1]}"
state="${XDG_RUNTIME_DIR:-$HOME/.cache}/officium/heartbeat"

re='<tool-use-id>([A-Za-z0-9_-]{1,128})</tool-use-id>'
rest="$payload"
while [[ $rest =~ $re ]]; do
  rest="${rest#*"${BASH_REMATCH[0]}"}"
  ticker="$state/$session.${BASH_REMATCH[1]}.tick"
  [ -f "$ticker" ] || continue
  read -r pid <"$ticker"
  rm -f "$ticker"
  [ -n "$pid" ] && kill "$pid" 2>/dev/null
done
exit 0
