#!/usr/bin/env bash
# test-cli-commands.sh — Read-only smoke tests for the cloudrobo-data-pipeline skill
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e cli]
#
# Only READ-ONLY commands are executed (version, workspace, operator discovery, task
# listing, and optional show/wait/log checks for an existing task). Mutating commands
# (asset registration, version publishing, create-task) are never executed by this
# script — they require explicit user confirmation (see templates/test-vars.json).
#
# Credentials: `cloudrobo config set ak <ak> sk <sk>` (preferred) or HUAWEI_CLOUD_AK /
# HUAWEI_CLOUD_SK environment variables.
#
# Optional environment variables:
#   PIPELINE_NAME       Task name prefix to filter list-tasks (default: sim-teleop-cleaning)
#   TASK_ID             Existing proc task (conversion/cleaning) for show/wait/log checks
#   EVAL_TASK_ID        Existing eval task (quality/diversity) for show/wait/log checks
#   REPORT_FILE_NAME    target_report_path without obs://<bucket>/ (for eval get-preview)
#   TARGET_ASSET_ID     Output asset of a SUCCEEDED proc task (for list-versions handoff check)
#   WAIT_TIMEOUT        Seconds for the wait-task checks (default: 60)

set -euo pipefail

SKILL_PATH=""
EXECUTOR="cli"
MAX_LINES=30
PASSED=0
FAILED=0
SKIPPED=0

while getopts ":s:e:" opt; do
    case "$opt" in
        s) SKILL_PATH="$OPTARG" ;;
        e) EXECUTOR="$OPTARG" ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

if [ -z "$SKILL_PATH" ]; then
    echo "Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e cli]"
    exit 1
fi

# Agent orchestration/smoke checks use CLI; the optional Web backend uses SDK.
if [ "$EXECUTOR" != "cli" ]; then
    echo "ERROR: invalid executor '$EXECUTOR' (this skill supports only: cli)"
    exit 1
fi

PIPELINE_NAME="${PIPELINE_NAME:-sim-teleop-cleaning}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-60}"

# cli_config_has <key> — true if `cloudrobo config get <key>` reports a stored value
# (the command always exits 0 and prints "<key> 未设置" when the key is not set).
cli_config_has() {
    local out
    out="$(cloudrobo config get "$1" 2>/dev/null)" || return 1
    [ -n "$out" ] && ! printf '%s' "$out" | grep -q '未设置'
}

# Check AK/SK: environment variables first, then `cloudrobo config set ak <ak> sk <sk>`
scan_credentials() {
    local ak="" sk=""
    for var in $(env | grep -iE '^(HUAWEI|HW|HWC).*(_AK|ACCESS_KEY|_SK|SECRET_KEY)' | cut -d= -f1 | sort -u); do
        case "$var" in
            *_AK|*ACCESS_KEY) ak="${!var}" ;;
            *_SK|*SECRET_KEY) sk="${!var}" ;;
        esac
    done
    if [ -n "$ak" ] && [ -n "$sk" ]; then
        echo "Credentials found in environment variables: AK=${ak:0:4}..."
        return
    fi
    if cli_config_has ak && cli_config_has sk; then
        echo "Credentials found in cloudrobo config"
        return
    fi
    echo "ERROR: AK/SK not configured."
    echo "Run 'cloudrobo config set ak <ak> sk <sk>' or set HUAWEI_CLOUD_AK / HUAWEI_CLOUD_SK."
    exit 1
}

# run_check <TC-ID> <command...> — runs a read-only command, prints the head of its output,
# and records pass/fail without aborting the suite. stdin is fed "n" so that interactive
# prompts (e.g. wait-task's "任务失败，是否查看日志？" on FAILED) never block the suite.
LAST_OUTPUT=""
run_check() {
    local tc_id="$1"; shift
    local rc=0
    echo ""
    echo "=== $tc_id: $* ==="
    LAST_OUTPUT="$(printf 'n\n' | "$@" 2>&1)" || rc=$?
    printf '%s\n' "$LAST_OUTPUT" | head -n "$MAX_LINES" || true
    if [ "$rc" -ne 0 ]; then
        echo "--- $tc_id: FAIL (exit code $rc)"
        FAILED=$((FAILED + 1))
    else
        echo "--- $tc_id: PASS"
        PASSED=$((PASSED + 1))
    fi
}

skip_check() {
    echo ""
    echo "=== $1: SKIPPED ($2) ==="
    SKIPPED=$((SKIPPED + 1))
}

# check_operator <TC-ID> <tag> <name-fragment> <exact-operator-name>
# If the exact operator name is absent from the output, warn: the pipeline must stop for
# stages that need it and must never substitute another operator.
check_operator() {
    local tc_id="$1" tag="$2" fragment="$3" exact="$4"
    run_check "$tc_id" cloudrobo asset list-publication-assets --type algorithm --tags "$tag" --name "$fragment"
    if ! printf '%s' "$LAST_OUTPUT" | grep -qF "$exact"; then
        echo "WARN ($tc_id): '$exact' not found in output (it may also be escaped) — verify manually."
        echo "      If the operator is not published in this region, stages that need it must stop"
        echo "      and the user must be told; never substitute another operator."
    fi
}

# Main execution
echo "=== cloudrobo-data-pipeline Skill Test Suite (read-only) ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo "Pipeline name prefix: $PIPELINE_NAME"
echo ""

scan_credentials

# Environment
run_check "TC-01" cloudrobo --version
run_check "TC-02" cloudrobo workspace current

# Operator discovery (tags + Chinese name fragments)
run_check "TC-03" cloudrobo asset list-publication-assets --type algorithm --tags "Data Processing" --limit 20
run_check "TC-04" cloudrobo asset list-publication-assets --type algorithm --tags "Data Evaluation" --limit 20
check_operator "TC-05" "Data Processing" "H5转LeRobotV3"  "数据转换--H5转LeRobotV3"
check_operator "TC-06" "Data Processing" "ros转LeRobotV3" "数据转换--ros转LeRobotV3"
check_operator "TC-07" "Data Processing" "UMI转LeRobotV3" "数据转换--UMI转LeRobotV3"
check_operator "TC-08" "Data Processing" "数据清洗"        "数据清洗"
check_operator "TC-09" "Data Evaluation" "质量评测"        "数据集质量评测-LeRobot"
check_operator "TC-10" "Data Evaluation" "多样性评测"      "数据集多样性评测-LeRobot"

# Pipeline task listing (tasks share the <pipeline_name>- prefix)
run_check "TC-11" cloudrobo dataset proc list-tasks --name "$PIPELINE_NAME" --limit 20
run_check "TC-12" cloudrobo dataset eval list-tasks --name "$PIPELINE_NAME" --limit 20

# Proc-task checks (existing task only)
if [ -n "${TASK_ID:-}" ]; then
    run_check "TC-13" cloudrobo dataset proc show-task --task-id "$TASK_ID"
    run_check "TC-14" cloudrobo dataset proc wait-task --task-id "$TASK_ID" --timeout "$WAIT_TIMEOUT" --interval 10
    run_check "TC-15" cloudrobo dataset proc get-log --task-id "$TASK_ID" --is-system true
    run_check "TC-16" cloudrobo dataset proc get-log --task-id "$TASK_ID" --is-system false
else
    for tc in TC-13 TC-14 TC-15 TC-16; do skip_check "$tc" "no TASK_ID"; done
fi

# Eval-task checks (existing task only)
if [ -n "${EVAL_TASK_ID:-}" ]; then
    run_check "TC-17" cloudrobo dataset eval show-task --task-id "$EVAL_TASK_ID"
    run_check "TC-18" cloudrobo dataset eval wait-task --task-id "$EVAL_TASK_ID" --timeout "$WAIT_TIMEOUT" --interval 10
    run_check "TC-19" cloudrobo dataset eval get-log --task-id "$EVAL_TASK_ID" --is-system true
    if [ -n "${REPORT_FILE_NAME:-}" ]; then
        run_check "TC-20" cloudrobo dataset eval get-preview --task-id "$EVAL_TASK_ID" --file-name "$REPORT_FILE_NAME"
    else
        skip_check "TC-20" "no REPORT_FILE_NAME"
    fi
else
    for tc in TC-17 TC-18 TC-19 TC-20; do skip_check "$tc" "no EVAL_TASK_ID"; done
fi

# Artifact handoff check (output asset of a SUCCEEDED proc task)
if [ -n "${TARGET_ASSET_ID:-}" ]; then
    run_check "TC-21" cloudrobo asset list-versions --asset-id "$TARGET_ASSET_ID" --sort-key created_at --sort-dir desc --limit 1
else
    skip_check "TC-21" "no TARGET_ASSET_ID"
fi

echo ""
echo "=== Test Suite Complete: $PASSED passed, $FAILED failed, $SKIPPED skipped ==="

if [ -z "${TASK_ID:-}" ] || [ -z "${EVAL_TASK_ID:-}" ]; then
    echo ""
    echo "NOTE: Set TASK_ID / EVAL_TASK_ID (and optionally REPORT_FILE_NAME, TARGET_ASSET_ID)"
    echo "to run the task-specific checks:"
    echo "  TASK_ID=<id> EVAL_TASK_ID=<id> bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi

echo ""
echo "NOTE: Mutating operations are NOT executed by this script and require explicit user"
echo "confirmation of the execution plan: asset create-asset / create-version / import-asset /"
echo "update-version, dataset proc create-task (conversion, cleaning), dataset eval create-task"
echo "(quality-eval, diversity-eval), and any retry (a NEW create-task after diagnosis)."

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
