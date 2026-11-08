#!/usr/bin/env bash
# 90-second demo of the Jira agentic requirements pipeline.
#
# Records cleanly with (from this skill's directory):
#   asciinema rec demo.cast --command "bash examples/demo.sh"
#   agg demo.cast demo.gif
#
# The demo runs against a synthetic ticket fixture, so it works without
# Jira credentials and produces the same output every time. It finds the
# skill relative to itself, so it runs from any directory.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL_DIR"

CLI="scripts/jira_pipeline_cli.py"
FIXTURE="tests/fixtures/issue_ambiguous.json"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

step() {
    printf '\n\033[1;36m▸ %s\033[0m\n' "$1"
    sleep 1
}

run() {
    printf '\033[2m$ %s\033[0m\n' "$*"
    "$@"
    sleep 1
}

step "Step 1 — start with a real-looking but ambiguous Jira ticket"
run cat "$FIXTURE"

step "Step 2 — discovery: rule-based analysis (no LLM needed)"
run python3 "$CLI" discovery --input "$FIXTURE" --output "$WORK/analysis.json"
run python3 -c "
import json
d = json.load(open('$WORK/analysis.json'))
print('  ambiguity:', d['ambiguityLevel']['level'], '(', d['ambiguityLevel']['ambiguityMarkers'], 'markers /100w )')
print('  missing:', len(d['missingBusinessDecisions']), 'decisions')
"

step "Step 3 — generate-questions: 4 baseline + 6 signal-driven"
run python3 "$CLI" generate-questions --input "$WORK/analysis.json" --output "$WORK/questions.json"
run python3 -c "
import json
q = json.load(open('$WORK/questions.json'))
for item in q['questions']:
    print(f\"  {item['id']:4} {item['priority']:3} {item['template_id']:4} {item['category']}\")
"

step "Step 4 — without business answers, refuse to plan"
run python3 -c "
import json
q = json.load(open('$WORK/questions.json'))
print('  status:', q['status'])
print('  required answers:', q['questionCount'])
"

step "Step 5 — ship the questions to the business team and wait."
echo "  (in production: push as a Jira comment, ping #product, etc.)"
sleep 1

printf '\n\033[1;32m✓ Demo complete.\033[0m See SKILL.md for the full six-command pipeline.\n'
