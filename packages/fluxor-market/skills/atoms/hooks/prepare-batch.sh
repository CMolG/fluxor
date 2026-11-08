#!/usr/bin/env bash
# UserPromptSubmit — batch preparation (the "preparation" hook of .harness/contracts/harness-convention.md in Fluxor's market).
#
# What it does, in this order and no other:
#
#   1. **The invariants first**, as a prefix: the `## N. Title` commandments of
#      <harness>/INVARIANTS.md, stuck to the prompt instead of thousands of lines away. The
#      PreToolUse hooks BLOCK an invariant when you are already about to violate it; this one
#      puts it up front BEFORE anything is decided, which is when honoring it is still free.
#   2. **Then the atom set**: the role, the mods and the steps the market's engine
#      (<harness>/market/motor.py) resolves for this particular intent.
#
# It never blocks. Preparing is not policing: an invariant is policed in its PreToolUse hook,
# where there is a concrete command to stop. Here there is only a sentence.
#
# It fails open at every step:
#   - no jq            -> silence (there is no safe way to emit well-formed JSON);
#   - no python (3.9+) -> the invariants only, extracted with awk;
#   - no market        -> the invariants only;
#   - no INVARIANTS.md -> the atom set only (or silence);
#   - any error        -> exit 0.
#
# Locations (.harness/contracts/harness-convention.md in Fluxor's market): project root = $CLAUDE_PROJECT_DIR, else the git
# top-level of the session's cwd, else that cwd. Harness = $HARNESS_DIR (relative to the root
# when relative), else <root>/.harness.

set -uo pipefail

PAYLOAD=$(cat 2>/dev/null) || PAYLOAD=""

# With no jq there is no way to return a well-formed `additionalContext`. Staying quiet is
# correct: the agent still gets the invariants through the harness index, if it has one.
command -v jq >/dev/null 2>&1 || exit 0

session_cwd=$(printf '%s' "$PAYLOAD" | jq -r '.cwd // empty' 2>/dev/null) || session_cwd=""
[ -n "$session_cwd" ] && [ -d "$session_cwd" ] || session_cwd="$PWD"

root="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$root" ] || [ ! -d "$root" ]; then
  root=$(git -C "$session_cwd" rev-parse --show-toplevel 2>/dev/null) || root=""
  [ -n "$root" ] || root="$session_cwd"
fi

harness="${HARNESS_DIR:-.harness}"
case "$harness" in
  /*|[A-Za-z]:[\\/]*) ;;
  *) harness="$root/$harness" ;;
esac

engine="$harness/market/motor.py"
invariants="$harness/INVARIANTS.md"

# A real Python 3.9+, not a launcher stub that only prints an install hint.
python_bin=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
     && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    python_bin="$candidate"
    break
  fi
done

# How the invariants file is named in the text the agent reads: relative to the root when inside.
case "$invariants" in
  "$root"/*) invariants_shown="${invariants#"$root"/}" ;;
  *) invariants_shown="$invariants" ;;
esac

invariants_only() {
  [ -f "$invariants" ] || return 0
  # Same escapes the engine honors: slash/bang commands and @noatoms (plus any alias the
  # lexicon maps to it) get no block at all.
  local prompt lowered alias
  prompt=$(printf '%s' "$PAYLOAD" | jq -r '.prompt // .user_prompt // empty' 2>/dev/null) || prompt=""
  case "$prompt" in /*|!*) return 0 ;; esac
  lowered=$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')
  case "$lowered" in *@noatoms*) return 0 ;; esac
  if [ -f "$harness/market/lexicon.json" ]; then
    while IFS= read -r alias; do
      [ -n "$alias" ] || continue
      case "$lowered" in *"$alias"*) return 0 ;; esac
    done < <(jq -r '(.directive_aliases // {}) | to_entries[]
                    | select(.value == "@noatoms") | .key | ascii_downcase' \
               "$harness/market/lexicon.json" 2>/dev/null)
  fi
  local list
  # The run of `## N. Title` headings; the first unnumbered `##` after it ends the list
  # (the same rule motor.py applies).
  list=$(awk '
    /^##[[:space:]]+[0-9]+\./ { sub(/^##[[:space:]]+/, "  "); sub(/[[:space:]]+$/, ""); print; seen = 1; next }
    /^##[[:space:]]/ { if (seen) exit }
  ' "$invariants" 2>/dev/null) || list=""
  [ -n "$list" ] || return 0
  printf '<invariants>\nWhat is not up for discussion in this project. The detail and the why of each one\nis in `%s`; open the one that affects you before you act.\n%s\n</invariants>' \
    "$invariants_shown" "$list"
}

block_text=""
if [ -n "$python_bin" ] && [ -f "$engine" ]; then
  # The engine already puts the invariants ahead of the atom set: one template, one place to
  # change the order. It prints nothing for greetings, slash commands and @noatoms, and that
  # silence is respected. Only if the engine itself cannot run do we fall back.
  if block_text=$(printf '%s' "$PAYLOAD" \
       | CLAUDE_PROJECT_DIR="$root" HARNESS_DIR="$harness" "$python_bin" "$engine" hook 2>/dev/null); then
    :
  else
    block_text=$(invariants_only)
  fi
else
  # Degraded: no python or no market. The commandments still read fine without scoring.
  block_text=$(invariants_only)
fi

[ -n "$block_text" ] || exit 0

jq -n --arg ctx "$block_text" \
  '{hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $ctx}}' 2>/dev/null
exit 0
