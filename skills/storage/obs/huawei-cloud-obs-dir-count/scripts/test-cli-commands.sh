#!/usr/bin/env bash
# ============================================================================
# Functional Test Script for huawei-cloud-obs-dir-count
# ============================================================================
# Usage: bash scripts/test-cli-commands.sh <skill-path> [--executor cli|auto]
#
# Executes the test cases in templates/test-vars.json against the count script.
# Every command is validated against a strict allow-list before execution:
#   - first word must be hcloud | python3 | curl | bash
#   - no `bash -c`, no $ or backtick, no shell concatenation/redirect/subshell
#   - python3 commands must not call os.system/os.popen/subprocess/eval/exec
# Live count cases require a real OBS bucket (see templates/test-vars.json).
#
# Generates references/test-report.md with results.
# ============================================================================

set -uo pipefail

SKILL_PATH="${1:?Usage: bash scripts/test-cli-commands.sh <skill-path> [--executor cli|auto]}"
shift || true

EXECUTOR="auto"
OUTPUT_FILE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --executor) EXECUTOR="$2"; shift 2 ;;
    --output) OUTPUT_FILE="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ ! -d "$SKILL_PATH" ]; then
  echo "[FATAL] Skill directory not found: $SKILL_PATH"
  exit 1
fi
SKILL_PATH="$(cd "$SKILL_PATH" && pwd)"

SKILL_MD="$SKILL_PATH/SKILL.md"
TEST_VARS="$SKILL_PATH/templates/test-vars.json"
[ -z "$OUTPUT_FILE" ] && OUTPUT_FILE="$SKILL_PATH/references/test-report.md"

[ -f "$SKILL_MD" ] || { echo "[FATAL] SKILL.md not found at $SKILL_MD"; exit 1; }
[ -f "$TEST_VARS" ] || { echo "[FATAL] templates/test-vars.json not found — no tests executed"; exit 1; }

SKILL_NAME=$(grep '^name:' "$SKILL_MD" 2>/dev/null | head -1 | sed 's/^name:[[:space:]]*//;s/^"//;s/"$//' || echo "unknown")

# ---------------------------------------------------------------------------
# Command allow-list validation
# ---------------------------------------------------------------------------
validate_command() {
  local cmd="$1" first_word
  first_word=$(printf '%s\n' "$cmd" | awk '{print $1}')
  case "$first_word" in
    hcloud|python3|curl|bash) ;;
    *) echo "[WARN] Command rejected (first word not in allowlist): ${cmd:0:60}"; return 1 ;;
  esac
  if [ "$first_word" = "bash" ] && printf '%s\n' "$cmd" | grep -qE 'bash[[:space:]]+-c'; then
    echo "[WARN] Command rejected (bash -c not allowed): ${cmd:0:60}"; return 1
  fi
  if printf '%s' "$cmd" | grep -qE '\$|`'; then
    echo "[WARN] Command rejected (dollar-sign/backtick not allowed): ${cmd:0:60}"; return 1
  fi
  if printf '%s' "$cmd" | python3 -c '
import sys
s = sys.stdin.read()
SQ = chr(39); DQ = chr(34); in_s = in_d = False; i = 0; n = len(s)
while i < n:
    c = s[i]
    if in_s:
        if c == chr(92) and i+1 < n: i += 2; continue
        if c == SQ: in_s = False
        i += 1; continue
    if in_d:
        if c == chr(92) and i+1 < n: i += 2; continue
        if c == DQ: in_d = False
        i += 1; continue
    if c == SQ: in_s = True; i += 1; continue
    if c == DQ: in_d = True; i += 1; continue
    if c in chr(59)+chr(124)+chr(38)+chr(62)+chr(60)+chr(40)+chr(41)+chr(123)+chr(125)+chr(10):
        sys.exit(1)
    i += 1
sys.exit(0)
'; then
    :
  else
    echo "[WARN] Command rejected (shell concatenation/redirect/subshell not allowed): ${cmd:0:60}"; return 1
  fi
  if [ "$first_word" = "python3" ] && printf '%s\n' "$cmd" | grep -qiE 'os\.system|os\.popen|subprocess|__import__|[^a-zA-Z_]eval\(|[^a-zA-Z_]exec\('; then
    echo "[WARN] Command rejected (dangerous python call): ${cmd:0:60}"; return 1
  fi
  return 0
}

PASS_COUNT=0; FAIL_COUNT=0; SKIP_COUNT=0; RESULTS_ARR=()
record() {
  RESULTS_ARR+=("$(printf '| `%s` | %s | %s | %s |' "$1" "$2" "$3" "$4")")
  case "$3" in
    ✅*) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    ❌*) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    ⏭️*) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
  esac
}

echo "=========================================="
echo " Functional Test — $SKILL_NAME"
echo " Path: $SKILL_PATH"
echo " Executor: $EXECUTOR"
echo "=========================================="

TC_COUNT=$(python3 -c "import sys,json; print(len(json.load(open(sys.argv[1])).get('test_cases',[])))" "$TEST_VARS" 2>/dev/null || echo "0")
if [ "$TC_COUNT" -eq 0 ]; then
  echo "[FATAL] No test cases in templates/test-vars.json"; exit 1
fi

for i in $(seq 0 $((TC_COUNT - 1))); do
  TC_ID=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); print(d['test_cases'][int(sys.argv[2])].get('id','TC-%02d'%(int(sys.argv[2])+1)))" "$TEST_VARS" "$i")
  TC_NAME=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); print(d['test_cases'][int(sys.argv[2])].get('name',''))" "$TEST_VARS" "$i")
  TC_CMD=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); print(d['test_cases'][int(sys.argv[2])].get('command',''))" "$TEST_VARS" "$i")

  echo "--- [$TC_ID] $TC_NAME ---"
  echo "  Command: $TC_CMD"

  if ! validate_command "$TC_CMD"; then
    record "$TC_CMD" "cli" "❌ 失败" "命令不在白名单或含shell拼接，未执行"
    echo "  ❌ FAIL - command rejected, not executed"
    echo ""; continue
  fi

  OUT=$(cd "$SKILL_PATH" && bash -c "$TC_CMD" 2>&1); RC=$?
  if [ "$RC" -eq 0 ] && ! printf '%s\n' "$OUT" | grep -qiE "error|failed|denied|unauthorized|not found"; then
    record "$TC_CMD" "cli" "✅ 通过" "exit 0; $(echo "$OUT" | tail -1 | head -c 60)"
    echo "  ✅ PASS: $(echo "$OUT" | tail -1 | head -c 80)"
  else
    record "$TC_CMD" "cli" "❌ 失败" "exit $RC: $(echo "$OUT" | head -1 | head -c 60)"
    echo "  ❌ FAIL (exit $RC): $(echo "$OUT" | head -2 | head -c 120)"
  fi
  echo ""
done

TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
REPORT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
cat > "$OUTPUT_FILE" <<REPORT_HEADER
# Functional Test Report — ${SKILL_NAME}

> Generated: ${REPORT_DATE}
> Executor: ${EXECUTOR}

## Summary

| Metric | Value |
|--------|-------|
| Total | ${TOTAL} |
| ✅ Pass | ${PASS_COUNT} |
| ❌ Fail | ${FAIL_COUNT} |
| ⏭️ Skip | ${SKIP_COUNT} |

## Details

| Operation | Type | Result | Note |
|-----------|------|--------|------|
REPORT_HEADER
for r in "${RESULTS_ARR[@]}"; do echo "$r" >> "$OUTPUT_FILE"; done
echo "" >> "$OUTPUT_FILE"
if [ "$FAIL_COUNT" -eq 0 ] && [ "$TOTAL" -gt 0 ]; then
  echo "**Conclusion: ✅ All ${TOTAL} test cases passed.**" >> "$OUTPUT_FILE"
else
  echo "**Conclusion: ❌ ${FAIL_COUNT}/${TOTAL} failed — review.**" >> "$OUTPUT_FILE"
fi

echo ""
echo "=========================================="
echo " Pass: $PASS_COUNT | Fail: $FAIL_COUNT | Skip: $SKIP_COUNT"
echo " Report: $OUTPUT_FILE"
echo "=========================================="

[ "$FAIL_COUNT" -eq 0 ]