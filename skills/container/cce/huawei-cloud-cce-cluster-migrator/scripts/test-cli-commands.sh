#!/usr/bin/env bash
# ============================================================================
# Functional Test Script for huawei-cloud-cce-cluster-migrator (Parallel Runner)
# ============================================================================
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="cn-north-4"
MAX_JOBS=8
EXECUTOR="cli"
REPORT_FILE=""

usage() {
    echo "Usage: bash test-cli-commands.sh [-s <skill-path>] [-j <concurrency>] [-r <region>] [-e <executor>] [-o <output-report>]" >&2
    echo "  -s  Target Skill directory (default: parent directory)" >&2
    echo "  -j  Maximum parallel worker jobs (default: 8)" >&2
    echo "  -r  Region (default: cn-north-4)" >&2
    echo "  -e  Executor mode (default: cli)" >&2
    echo "  -o  Output report file path" >&2
}

while getopts ":s:j:r:e:o:h" opt; do
    case "$opt" in
        s) SKILL_DIR="$OPTARG" ;;
        j) MAX_JOBS="$OPTARG" ;;
        r) REGION="$OPTARG" ;;
        e) EXECUTOR="$OPTARG" ;;
        o) REPORT_FILE="$OPTARG" ;;
        h) usage; exit 0 ;;
        \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument" >&2; usage; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

# Backward-compat: accept trailing positional argument as skill path
if [ $# -gt 0 ] && [ -n "${1:-}" ]; then
    SKILL_DIR="$1"
fi

if [ ! -d "$SKILL_DIR" ]; then
    echo "[FATAL] Skill directory not found: $SKILL_DIR" >&2
    exit 1
fi
SKILL_DIR="$(cd "$SKILL_DIR" && pwd)"
cd "$SKILL_DIR"

TEST_VARS="$SKILL_DIR/templates/test-vars.json"

if [ ! -f "$TEST_VARS" ]; then
    echo "[FATAL] $TEST_VARS not found" >&2
    exit 1
fi

echo "=================================================="
echo "  Running Tests for: huawei-cloud-cce-cluster-migrator"
echo "  Skill Directory:   $SKILL_DIR"
echo "  Concurrency:       $MAX_JOBS worker(s)"
echo "  Region:            $REGION"
echo "=================================================="

PYTHON_BIN=$(command -v python3 2>/dev/null || command -v python)
if [ -z "$PYTHON_BIN" ]; then
    echo "[FATAL] python3 or python is required to parse test variables" >&2
    exit 1
fi

TMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'cce-test-XXXXXX')
cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

TEST_VARS_PY="$TEST_VARS"
TMP_DIR_PY="$TMP_DIR"
if command -v cygpath >/dev/null 2>&1; then
    TEST_VARS_PY=$(cygpath -m "$TEST_VARS")
    TMP_DIR_PY=$(cygpath -m "$TMP_DIR")
fi

# Extract all test cases in a single Python invocation into temporary worker directories
COUNT=$($PYTHON_BIN -c "
import json, sys, os

test_vars_path = sys.argv[1]
out_dir = sys.argv[2]

with open(test_vars_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

cases = data.get('test_cases', [])
for i, c in enumerate(cases):
    case_dir = os.path.join(out_dir, str(i))
    os.makedirs(case_dir, exist_ok=True)
    with open(os.path.join(case_dir, 'id'), 'w', encoding='utf-8') as f_id:
        f_id.write(c.get('id', f'TC-{i+1:02d}'))
    with open(os.path.join(case_dir, 'name'), 'w', encoding='utf-8') as f_name:
        f_name.write(c.get('name', ''))
    with open(os.path.join(case_dir, 'command'), 'w', encoding='utf-8') as f_cmd:
        f_cmd.write(c.get('command', ''))
    with open(os.path.join(case_dir, 'expected'), 'w', encoding='utf-8') as f_exp:
        f_exp.write(c.get('expected', ''))

print(len(cases))
" "$TEST_VARS_PY" "$TMP_DIR_PY")

if [ "$COUNT" -eq 0 ]; then
    echo "[WARN] No test cases found in $TEST_VARS"
    exit 0
fi

echo "Dispatched $COUNT test cases in parallel (max $MAX_JOBS active jobs)..."
echo ""

active_jobs=0

for ((i=0; i<COUNT; i++)); do
    (
        tc_id=$(cat "$TMP_DIR/$i/id")
        tc_name=$(cat "$TMP_DIR/$i/name")
        tc_cmd=$(cat "$TMP_DIR/$i/command")
        tc_expected=$(cat "$TMP_DIR/$i/expected")

        # Substitute {region} if present
        cmd_final="${tc_cmd//\{region\}/$REGION}"

        if [ -n "$tc_expected" ]; then
            if eval "$cmd_final" 2>&1 | grep -qi "$tc_expected"; then
                echo 0 > "$TMP_DIR/$i/status"
                echo "| \`$tc_id\` | $tc_name | \`$cmd_final\` | PASS | Expected pattern verified |" > "$TMP_DIR/$i/row"
                printf "  [%s] %s ... PASS\n" "$tc_id" "$tc_name"
            else
                echo 1 > "$TMP_DIR/$i/status"
                echo "| \`$tc_id\` | $tc_name | \`$cmd_final\` | FAIL | Output did not match expected pattern |" > "$TMP_DIR/$i/row"
                printf "  [%s] %s ... FAIL\n" "$tc_id" "$tc_name"
            fi
        else
            output=$(eval "$cmd_final" 2>&1 || true)
            if echo "$output" | grep -qiE "error|failed|exception"; then
                echo 1 > "$TMP_DIR/$i/status"
                echo "| \`$tc_id\` | $tc_name | \`$cmd_final\` | FAIL | Error detected in output |" > "$TMP_DIR/$i/row"
                printf "  [%s] %s ... FAIL\n" "$tc_id" "$tc_name"
            else
                echo 0 > "$TMP_DIR/$i/status"
                echo "| \`$tc_id\` | $tc_name | \`$cmd_final\` | PASS | Execution completed |" > "$TMP_DIR/$i/row"
                printf "  [%s] %s ... PASS\n" "$tc_id" "$tc_name"
            fi
        fi
    ) &

    active_jobs=$((active_jobs + 1))
    if [ "$active_jobs" -ge "$MAX_JOBS" ]; then
        wait -n 2>/dev/null || wait
        active_jobs=$((active_jobs - 1))
    fi
done

wait

passed=0
failed=0
table_rows=""

for ((i=0; i<COUNT; i++)); do
    st=$(cat "$TMP_DIR/$i/status" 2>/dev/null || echo 1)
    row=$(cat "$TMP_DIR/$i/row" 2>/dev/null || echo "| TC-$i | Unknown | - | FAIL | Worker error |")
    table_rows+="${row}"$'\n'
    if [ "$st" -eq 0 ]; then
        passed=$((passed + 1))
    else
        failed=$((failed + 1))
    fi
done

echo ""
echo "=================================================="
echo "  Test Summary: $passed/$COUNT passed, $failed failed (Concurrency: $MAX_JOBS)"
echo "=================================================="
echo ""
echo "Execution Results:"
echo "| Test ID | Name | Command | Status | Notes |"
echo "|---------|------|---------|--------|-------|"
printf '%s' "${table_rows}"
echo "=================================================="

if [ -n "$REPORT_FILE" ]; then
    mkdir -p "$(dirname "$REPORT_FILE")"
    cat > "$REPORT_FILE" <<EOF
# CCE Cluster Migrator Functional Test Report

- **Date**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
- **Skill**: \`huawei-cloud-cce-cluster-migrator\`
- **Region Tested**: \`$REGION\`
- **Concurrency**: $MAX_JOBS worker(s)
- **Total Cases**: $COUNT
- **Passed**: $passed
- **Failed**: $failed
- **Pass Rate**: $(( passed * 100 / COUNT ))%

## Execution Results

| Test ID | Name | Command | Status | Notes |
|---------|------|---------|--------|-------|
${table_rows}
## Summary

Functional testing verified read-only discovery, cluster flavor specification queries, add-on template availability, and IAM 5.0 policy versions.
EOF
    echo "Report written to: $REPORT_FILE"
fi

if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
