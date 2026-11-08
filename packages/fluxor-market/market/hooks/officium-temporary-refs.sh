#!/usr/bin/env bash
# preTool (every tool) -- refuses an agent's move of an Officium card to review while the card still
# has `card://<KEY> [temporary]` references in the code.
#
# The backlog skill asks it of every card (step 8, and rule 6 of its card references): a temporary
# reference is resolved in the card that made it, or re-pointed to a follow-up card, before review.
# Officium's server cannot check it, because it has no git; this hook can, on the machine that has
# the code. It acts only on `cards.move` to `review` through `mcp__<mcpServer>__query` (the server
# name from <harness>/config/backlog.json, default officium); every other call leaves at once, on
# bash builtins.
#
# `cards.move` names the card only by `cardId`. The key comes from the call's params when they carry
# one (`cardKey` or `key`), else from the session's transcript: the agent learned that id from an
# Officium answer, and every answer that carries a card's id carries its key beside it (a card:
# `"id":..,"projectId":..,"key":..`; a work entry: `"cardId":..,"cardKey":..`). Then
# `<harness>/skills/backlog/scripts/card_refs.py --json list <KEY>` and, with a temporary reference
# left, exit 2 with each one and the fix on stderr. Nothing leaves the machine.
#
# It fails open: no project, no config, no card_refs.py, no python, no key, or an answer it cannot
# read, and the move goes through without a word. A guardrail that breaks must not block the board.

IFS= read -r -d '' payload

# get <field> <var>: the first `"field": "..."` string in the payload into <var>, still escaped.
get() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\""
  if [[ $payload =~ $re ]]; then printf -v "$2" '%s' "${BASH_REMATCH[1]}"; else printf -v "$2" ''; fi
}

get tool_name tool
case "$tool" in mcp__*__query) ;; *) exit 0 ;; esac
get operation operation
[ "$operation" = "cards.move" ] || exit 0
get status status
[ "$status" = "review" ] || exit 0

get cwd cwd
cwd="${cwd//\\\\//}"   # a Windows path comes JSON-escaped: C:\\Users -> C:/Users
root="${CLAUDE_PROJECT_DIR:-}"
[ -n "$root" ] || root="$(git -C "${cwd:-.}" rev-parse --show-toplevel 2>/dev/null)"
[ -n "$root" ] && [ -d "$root" ] || exit 0
harness="${HARNESS_DIR:-.harness}"
case "$harness" in /*|[A-Za-z]:*) ;; *) harness="$root/$harness" ;; esac
config="$harness/config/backlog.json"
script="$harness/skills/backlog/scripts/card_refs.py"
[ -r "$config" ] && [ -r "$script" ] || exit 0

server=officium
re='"mcpServer"[[:space:]]*:[[:space:]]*"([A-Za-z0-9_.-]+)"'
[[ $(<"$config") =~ $re ]] && server="${BASH_REMATCH[1]}"
[ "$tool" = "mcp__${server}__query" ] || exit 0

keyre='^[A-Z][A-Z0-9]*-[0-9]+$'
get cardKey key
[[ $key =~ $keyre ]] || get key key
if ! [[ $key =~ $keyre ]]; then
  get cardId id
  if [[ $id =~ $keyre ]]; then
    key="$id"
  else
    [[ $id =~ ^[0-9A-Fa-f-]{8,64}$ ]] || exit 0
    get transcript_path transcript
    transcript="${transcript//\\\\//}"
    [ -n "$transcript" ] && [ -r "$transcript" ] || exit 0
    # The answers sit in the transcript as JSON strings inside JSON, so their quotes come escaped:
    # backslashes are dropped before matching. The last answer for this id wins.
    s='[[:space:]]*'
    k='([A-Z][A-Z0-9]*-[0-9]+)'
    match="$(grep -F -- "$id" "$transcript" 2>/dev/null | tr -d '\\' \
      | grep -oE "\"id\"$s:$s\"$id\"$s,$s\"projectId\"$s:$s\"[^\"]*\"$s,$s\"key\"$s:$s\"$k\"|\"cardId\"$s:$s\"$id\"$s,$s\"cardKey\"$s:$s\"$k\"" \
      | tail -n 1)"
    match="${match%\"}"
    key="${match##*\"}"
    [[ $key =~ $keyre ]] || exit 0
  fi
fi

# python3 first; on Windows it is often the Store's placeholder, which fails, so then python.
py=""
for candidate in python3 python; do
  if "$candidate" -c pass >/dev/null 2>&1; then py="$candidate"; break; fi
done
[ -n "$py" ] || exit 0

found="$(cd "$root" && CLAUDE_PROJECT_DIR="$root" "$py" "$script" --json list "$key" 2>/dev/null)" || exit 0
lines="$(printf '%s' "$found" | "$py" -c '
import json, sys
try:
    refs = json.load(sys.stdin)["references"]
except Exception:
    sys.exit(0)
for r in refs:
    if r.get("kind") == "temporary":
        print("%s:%s: %s" % (r["file"], r["line"], r["text"]))
' 2>/dev/null)"
[ -n "$lines" ] || exit 0

{
  printf 'officium-temporary-refs: %s still has [temporary] card references, so it does not go to review yet:\n' "$key"
  printf '%s\n' "$lines"
  printf 'Resolve each one in this card, or re-point it to a follow-up card (card://<OTHER> [temporary]) that says when it goes, then move the card again (backlog skill, step 8).\n'
} >&2
exit 2
