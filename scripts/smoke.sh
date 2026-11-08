#!/usr/bin/env bash
# End-to-end smoke test of Fluxor Local, against the real containers:
#   db + api up -> MCP initialize / tools/list -> create a project -> select two base-market items
#   -> fluxor-sync init + pull in a throwaway git repo -> publish an own item -> select it -> pull
#   -> dropped routes answer feature_unavailable_in_local -> token mode (401 / 200 / enrollment).
#
#   scripts/smoke.sh                      # demo repo in a temp dir, containers removed at the end
#   DEMO_REPO=/some/dir scripts/smoke.sh  # keep the demo repo there (it is recreated)
#   KEEP=1 scripts/smoke.sh               # leave the containers running
# Needs docker (compose v2), python3, git and curl.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-fluxor-local-dev}"
export FLUXOR_API_PORT="${FLUXOR_API_PORT:-18191}"
export FLUXOR_DB_PORT="${FLUXOR_DB_PORT:-15434}"
export FLUXOR_LOCAL_TOKEN=""
API="http://127.0.0.1:${FLUXOR_API_PORT}/api"
BODY="$(mktemp)"
DEMO="${DEMO_REPO:-$(mktemp -d)/demo-repo}"
COMPOSE=(docker compose -f "$ROOT/docker-compose.yml")

say() { printf '\n== %s\n' "$*"; }
fail() { printf 'SMOKE FAILED: %s\n' "$*" >&2; exit 1; }

cleanup() {
  if [ "${KEEP:-0}" != "1" ]; then
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

wait_ready() {
  for _ in $(seq 1 90); do
    if curl -sf "http://127.0.0.1:${FLUXOR_API_PORT}/q/health/ready" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  "${COMPOSE[@]}" logs api | tail -40
  fail "the API did not become ready"
}

# mcp <token-or-empty> <json-rpc body>: prints the response body.
mcp() {
  local token="$1" body="$2" auth=()
  [ -n "$token" ] && auth=(-H "Authorization: Bearer $token")
  curl -s -X POST "$API/fluxor/mcp" -H 'Content-Type: application/json' "${auth[@]}" -d "$body"
}

# query <operation> <params-json>: runs one Fluxor operation over MCP and prints its JSON result.
query() {
  local body
  body=$(python3 -c 'import json,sys; print(json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"query","arguments":{"operation":sys.argv[1],"params":json.loads(sys.argv[2])}}}))' "$1" "$2")
  mcp "${MCP_TOKEN:-}" "$body" | python3 -c '
import json, sys
reply = json.load(sys.stdin)
result = reply["result"]
if result.get("isError"):
    sys.exit("operation failed: " + json.dumps(result)[:600])
content = result.get("structuredContent")
if content is None:
    content = json.loads(result["content"][0]["text"])
print(json.dumps(content))'
}

jget() { python3 -c 'import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1]))' "$1"; }

say "1. start the database and the API"
"${COMPOSE[@]}" up -d --build
wait_ready

say "2. MCP: initialize, tools/list"
mcp "" '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}' \
  | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; print("server:", r["serverInfo"]); print("instructions:", r["instructions"][:120].replace("\n"," "), "...")'
mcp "" '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python3 -c 'import json,sys; print("tools:", [t["name"] for t in json.load(sys.stdin)["result"]["tools"]])'
echo "operations (discover):"
mcp "" '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"discover","arguments":{}}}' | python3 -c '
import json, sys
result = json.load(sys.stdin)["result"]
content = result.get("structuredContent") or json.loads(result["content"][0]["text"])
ops = content if isinstance(content, list) else content.get("operations", content)
print("  ", ", ".join(o["key"] for o in ops))'

say "3. create a project and select two base-market items"
PROJECT=$(query harness.project.create '{"name":"demo-repo"}' | jget 'd["id"]')
echo "project: $PROJECT"
query harness.catalog '{}' | python3 -c 'import json,sys; d=json.load(sys.stdin); d=d if isinstance(d,list) else d.get("items",d); print("catalog items:", len(d))'
UPDATED=$(query harness.project.update "{\"projectId\":\"$PROJECT\",\"expectedRevision\":0,\"put\":[{\"key\":\"atoms\"},{\"key\":\"review-harness\"}]}")
echo "$UPDATED" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("revision:", d["project"]["revision"], "items:", [i["key"] for i in d["items"]])'

say "3b. the sync plane refuses a request with no device token"
code=$(curl -s -o /dev/null -w '%{http_code}' "$API/fluxor/v1/sync/harness/projects")
[ "$code" = 401 ] || fail "sync without a device token answered $code, expected 401"
echo "  GET /fluxor/v1/sync/harness/projects with no token -> $code"

say "4. the writer, from the server"
rm -rf "$DEMO"; mkdir -p "$DEMO/.harness/bin"
git -C "$DEMO" init -q
curl -sf "$API/fluxor/v1/writer/fluxor-sync.py" -o "$DEMO/.harness/bin/fluxor-sync.py"
SYNC_HOME="$(mktemp -d)"   # this machine's device-token store (~/.config/fluxor) stays out of the real one
SYNC=(env HOME="$SYNC_HOME" python3 "$DEMO/.harness/bin/fluxor-sync.py" --root "$DEMO")

say "5. fluxor-sync init (fixed local enrollment code) + pull"
"${SYNC[@]}" init --server "$API" --enroll local --project "$PROJECT" --storage local
echo "-- .harness after the pull:"
(cd "$DEMO" && find .harness -maxdepth 3 -not -path '.harness/bin*' | sort | head -40)
test -f "$DEMO/.harness/skills/atoms/SKILL.md" || fail "the atoms skill did not land in .harness/skills/atoms"
test -f "$DEMO/.harness/skills/review-harness/SKILL.md" || fail "the review-harness skill did not land"
"${SYNC[@]}" status

say "6. harness.bootstrap: the commands an agent would run"
query harness.bootstrap "{\"projectId\":\"$PROJECT\"}" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("expires:", d["expiresAt"]); [print("  $", c[:150], "...") for c in d["commands"]]'

say "7. publish an own skill and select it"
SKILL_DIR="$(mktemp -d)/hello"; mkdir -p "$SKILL_DIR"
cat > "$SKILL_DIR/SKILL.md" <<'SKILL'
---
name: hello
description: Says hello. Use it when the user asks for a greeting.
---

# Hello

Greet the user in one sentence.
SKILL
"${SYNC[@]}" item publish "$SKILL_DIR" --key local.hello --kind skill --visibility private
"${SYNC[@]}" select --put local.hello
"${SYNC[@]}" pull
test -f "$DEMO/.harness/skills/local.hello/SKILL.md" || {
  (cd "$DEMO" && find .harness -name SKILL.md); fail "the published skill did not land after select + pull"; }
echo "own skill landed"

say "8. dropped routes answer feature_unavailable_in_local"
for route in "POST pairings" "GET releases" "POST ticket"; do
  set -- $route
  code=$(curl -s -o $BODY -w '%{http_code}' -X "$1" "$API/fluxor/v1/$2" -H 'Content-Type: application/json' -d '{}')
  grep -q feature_unavailable_in_local $BODY || fail "$route: no feature_unavailable_in_local"
  echo "  $route -> $code $(cat $BODY)"
done

say "9. token mode: FLUXOR_LOCAL_TOKEN=s3cret-smoke-token"
FLUXOR_LOCAL_TOKEN="s3cret-smoke-token" "${COMPOSE[@]}" up -d api
wait_ready
LIST='{"jsonrpc":"2.0","id":3,"method":"tools/list"}'
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/fluxor/mcp" -H 'Content-Type: application/json' -d "$LIST")
[ "$code" = 401 ] || fail "MCP without a token answered $code, expected 401"
echo "  MCP without token -> $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/fluxor/mcp" -H 'Content-Type: application/json' -H 'Authorization: Bearer wrong' -d "$LIST")
[ "$code" = 401 ] || fail "MCP with a wrong token answered $code, expected 401"
echo "  MCP with a wrong token -> $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/fluxor/mcp" -H 'Content-Type: application/json' -H 'Authorization: Bearer s3cret-smoke-token' -d "$LIST")
[ "$code" = 200 ] || fail "MCP with the token answered $code, expected 200"
echo "  MCP with the token -> $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/fluxor/v1/sync/enrollments" -H 'Content-Type: application/json' -d '{"code":"local","hostname":"smoke"}')
[ "$code" = 401 ] || fail "enrollment with the open-mode code answered $code, expected 401"
echo "  enrollment with code 'local' -> $code"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/fluxor/v1/sync/enrollments" -H 'Content-Type: application/json' -d '{"code":"s3cret-smoke-token","hostname":"smoke"}')
[ "$code" = 201 ] || fail "enrollment with the token answered $code, expected 201"
echo "  enrollment with the token -> $code"

say "SMOKE PASSED"
