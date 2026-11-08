#!/usr/bin/env bash
# sessionStart -- prints the backlog skill's session order ("A session, in order") with this
# project's id and this machine's name, so the agent starts from the board instead of from memory.
# Sends nothing; reads only <harness>/config/backlog.json, and says nothing when there is none.
#
# Harness: HARNESS_DIR, else $CLAUDE_PROJECT_DIR/.harness, else the git top level's .harness.
# Machine: AUTOLOOP_MACHINE (an autoloop slot's own name), else the config's machineName
# (`hostname`, `env:VAR` or a literal, as the backlog skill reads it). Bash builtins and sed only.

harness="${HARNESS_DIR:-}"
if [ -z "$harness" ]; then
  root="${CLAUDE_PROJECT_DIR:-}"
  [ -n "$root" ] || root=$(git rev-parse --show-toplevel 2>/dev/null) || root=$PWD
  harness="$root/.harness"
fi
config="$harness/config/backlog.json"
[ -r "$config" ] || exit 0
json=$(tr -d '\r\n' <"$config")

# Only names made of these characters reach the agent's context: the file is data, not instructions.
SAFE='^[A-Za-z0-9._-]{1,128}$'
field() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\"([^\"]*)\""
  if [[ $2 =~ $re ]]; then printf '%s' "${BASH_REMATCH[1]}"; fi
}
project=""
re='"project"[[:space:]]*:[[:space:]]*\{([^}]*)\}'
[[ $json =~ $re ]] && project=$(field id "${BASH_REMATCH[1]}")
[[ $project =~ $SAFE ]] || project=""
provider=$(field provider "$json")
[[ $provider =~ $SAFE ]] || provider=officium

machine="${AUTOLOOP_MACHINE:-}"
if [ -z "$machine" ]; then
  setting=$(field machineName "$json")
  case "$setting" in
    "" | hostname) ;;
    env:*)
      var="${setting#env:}"
      [[ $var =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] && machine="${!var:-}"
      ;;
    *) machine="$setting" ;;
  esac
  [ -n "$machine" ] || machine="${COMPUTERNAME:-$(hostname 2>/dev/null)}"
fi
[[ $machine =~ $SAFE ]] || machine=""

if [ "$provider" = officium ]; then
  id="${project:-<discover it: cards are under a project>}"
  m="${machine:-<this machine>}"
  printf '%s\n' \
    "Backlog: before picking any work, follow the backlog skill's \"A session, in order\" (Officium project $id, machine $m):" \
    "1. cards.working {projectId: \"$id\"}: who is on what right now." \
    "2. cards.resumable {projectId: \"$id\", machine: \"$m\"}: a card this machine left unfinished is finished first." \
    "3. cards.search {projectId: \"$id\", humanEditPending: true}: read each card a person changed, act, then cards.acknowledgeHumanEdit." \
    "4. cards.needsHuman {projectId: \"$id\"}: what waits on a person; never yours to do." \
    "5. cards.next {projectId: \"$id\"}: then the next card." \
    "Pass machine \"$m\" on every call that takes one."
else
  printf '%s\n' \
    "Backlog: before picking any work, follow the backlog skill's \"A session, in order\" through its $provider adapter${project:+ (project $project)}${machine:+, machine $machine}:" \
    "listWorking, listResumable(machine) and finish what this machine left, listHumanEdited (acknowledge each), listNeedsHuman, then nextCard."
fi
exit 0
