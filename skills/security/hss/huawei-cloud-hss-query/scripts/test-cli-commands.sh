#!/bin/bash
# test-cli-commands.sh — Execute HSS CLI test cases
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} -e {cli|sdk|api}

set -euo pipefail

SKILL_PATH=""
EXECUTOR="cli"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s) SKILL_PATH="$2"; shift 2 ;;
    -e) EXECUTOR="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$SKILL_PATH" ]]; then
  echo "FATAL: skill path required (-s)"
  exit 1
fi

TEST_VARS="${SKILL_PATH}/templates/test-vars.json"
if [[ ! -f "$TEST_VARS" ]]; then
  echo "FATAL: templates/test-vars.json not found"
  exit 1
fi

echo "=== HSS Skill Test Execution ==="
echo "Skill: ${SKILL_PATH}"
echo "Executor: ${EXECUTOR}"
echo ""

# Only CLI mode is supported for this skill
if [[ "$EXECUTOR" != "cli" ]]; then
  echo "WARN: Only CLI mode is supported for HSS skill. Falling back to cli."
  EXECUTOR="cli"
fi

# Whitelist check: only allow hcloud, python3, curl, bash prefixed commands
is_whitelisted() {
  local cmd="$1"
  [[ "$cmd" =~ ^hcloud\  ]] && return 0
  [[ "$cmd" =~ ^python3\  ]] && return 0
  [[ "$cmd" =~ ^curl\  ]] && return 0
  [[ "$cmd" =~ ^bash\  ]] && return 0
  return 1
}

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Extract and run test cases from JSON
# Using python3 to parse JSON
TEST_COMMANDS=$(python3 -c "
import json, sys
with open('${TEST_VARS}') as f:
    data = json.load(f)
for tc in data.get('test_cases', []):
    print(f\"{tc['id']}|{tc['name']}|{tc['command']}\")
")

while IFS='|' read -r tc_id tc_name tc_command; do
  [[ -z "$tc_id" ]] && continue

  echo "--- ${tc_id}: ${tc_name} ---"

  if ! is_whitelisted "$tc_command"; then
    echo "  SKIP: command not in whitelist"
    SKIP_COUNT=$((SKIP_COUNT + 1))
    continue
  fi

  # Execute the command
  if output=$(eval "$tc_command" 2>&1); then
    echo "  PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "  FAIL: $output" | head -5
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done <<< "$TEST_COMMANDS"

echo ""
echo "=== Test Summary ==="
echo "PASS: ${PASS_COUNT}"
echo "FAIL: ${FAIL_COUNT}"
echo "SKIP: ${SKIP_COUNT}"
echo "TOTAL: $((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))"

if [[ $FAIL_COUNT -gt 0 ]]; then
  exit 1
fi
exit 0
