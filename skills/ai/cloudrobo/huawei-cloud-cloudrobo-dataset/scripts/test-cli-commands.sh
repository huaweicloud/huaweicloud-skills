#!/usr/bin/env bash
# test-cli-commands.sh — Functional testing for cloudrobo-dataset skill
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]

set -euo pipefail

SKILL_PATH=""
EXECUTOR="cli"

while getopts ":s:e:" opt; do
    case "$opt" in
        s) SKILL_PATH="$OPTARG" ;;
        e) EXECUTOR="$OPTARG" ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

if [ -z "$SKILL_PATH" ]; then
    echo "Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]"
    exit 1
fi

# Only CLI and SDK modes are automated; API verification is manual (see references/verification-method.md)
case "$EXECUTOR" in
    cli|sdk) ;;
    *) echo "ERROR: invalid executor '$EXECUTOR' (expected cli|sdk)"; exit 1 ;;
esac

# Auto-scan for AK/SK environment variables
scan_credentials() {
    local ak="" sk=""
    for var in $(env | grep -iE '^(HUAWEI|HW|HWC).*(_AK|ACCESS_KEY|_SK|SECRET_KEY)' | cut -d= -f1 | sort -u); do
        case "$var" in
            *_AK|*ACCESS_KEY) ak="${!var}" ;;
            *_SK|*SECRET_KEY) sk="${!var}" ;;
        esac
    done
    if [ -z "$ak" ] || [ -z "$sk" ]; then
        echo "ERROR: AK/SK not found in environment variables."
        echo "Set HUAWEI_CLOUD_AK and HUAWEI_CLOUD_SK environment variables."
        exit 1
    fi
    echo "Credentials found: AK=${ak:0:8}..."
}

# Test cases
test_list_tasks() {
    echo "=== TC-01: list-tasks ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset proc list-tasks 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_dataset.client import DatasetClient
from cloudrobo_core.sdk import Config, HttpClient
client = DatasetClient(HttpClient(Config()))
result = client.list_tasks()
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_show_task() {
    local task_id="${1:-}"
    if [ -z "$task_id" ]; then
        echo "=== TC-02: show-task (SKIPPED - no task_id) ==="
        return
    fi
    echo "=== TC-02: show-task --task-id $task_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset proc show-task --task-id "$task_id" 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_dataset.client import DatasetClient
from cloudrobo_core.sdk import Config, HttpClient
client = DatasetClient(HttpClient(Config()))
result = client.get_task_detail('$task_id')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_list_algorithms() {
    echo "=== TC-03: list-algorithms (data_processing) ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-publication-assets --type algorithm --sub-type data_processing --limit 5 2>&1 | head -30
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_publication_assets(type='algorithm', sub_type='data_processing', limit=5)
print(str(result)[:500])
" 2>&1 | head -30
    fi
}

test_get_log() {
    local task_id="${1:-}"
    if [ -z "$task_id" ]; then
        echo "=== TC-04: get-log (SKIPPED - no task_id) ==="
        return
    fi
    echo "=== TC-04: get-log --task-id $task_id --is-system true ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset proc get-log --task-id "$task_id" --is-system true 2>&1 | head -20
    fi
}

test_get_preview() {
    local task_id="${1:-}"
    if [ -z "$task_id" ]; then
        echo "=== TC-05: get-preview (SKIPPED - no task_id) ==="
        return
    fi
    echo "=== TC-05: get-preview --task-id $task_id --file-name $FILE_NAME ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset proc get-preview --task-id "$task_id" --file-name "$FILE_NAME" 2>&1 | head -20
    fi
}

test_create_task_dry_run() {
    echo "=== TC-06: create-task --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset proc create-task \
            --name test-dry-run \
            --algo-type PRESET_ASSETS \
            --task-config '{"algo_name":"test"}' \
            --dry-run 2>&1 | head -10
    fi
}

test_eval_list_tasks() {
    echo "=== TC-22: eval list-tasks ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset eval list-tasks 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_dataset.client import DatasetClient
from cloudrobo_core.sdk import Config, HttpClient
client = DatasetClient(HttpClient(Config()))
result = client.list_eval_tasks()
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_eval_show_task() {
    local task_id="${1:-}"
    if [ -z "$task_id" ]; then
        echo "=== TC-23: eval show-task (SKIPPED - no EVAL_TASK_ID) ==="
        return
    fi
    echo "=== TC-23: eval show-task --task-id $task_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset eval show-task --task-id "$task_id" 2>&1 | head -20
    fi
}

test_eval_get_log() {
    local task_id="${1:-}"
    if [ -z "$task_id" ]; then
        echo "=== TC-25: eval get-log (SKIPPED - no EVAL_TASK_ID) ==="
        return
    fi
    echo "=== TC-25: eval get-log --task-id $task_id --is-system true ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset eval get-log --task-id "$task_id" --is-system true 2>&1 | head -20
    fi
}

test_eval_get_preview() {
    local task_id="${1:-}"
    if [ -z "$task_id" ]; then
        echo "=== TC-28: eval get-preview (SKIPPED - no EVAL_TASK_ID) ==="
        return
    fi
    echo "=== TC-28: eval get-preview --task-id $task_id --file-name report.json ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset eval get-preview --task-id "$task_id" --file-name report.json 2>&1 | head -20
    fi
}

test_get_resource_usage() {
    local task_id="${1:-}"
    local start_ts="${2:-}"
    local end_ts="${3:-}"
    if [ -z "$task_id" ] || [ -z "$start_ts" ] || [ -z "$end_ts" ]; then
        echo "=== TC-28b: get-resource-usage (SKIPPED - no TASK_ID or START_TS/END_TS) ==="
        return
    fi
    echo "=== TC-28b: get-resource-usage --task-id $task_id --metric CPU_UTIL --start $start_ts --end $end_ts --step 60 ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo dataset proc get-resource-usage --task-id "$task_id" --metric CPU_UTIL --start "$start_ts" --end "$end_ts" --step 60 2>&1 | head -20
    fi
}

# Main execution
echo "=== cloudrobo-dataset Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo ""

scan_credentials

# Execute read-only tests (no mutation)
test_list_tasks
test_list_algorithms
test_create_task_dry_run
test_eval_list_tasks

# Execute task-specific tests if TASK_ID is provided
if [ -n "${TASK_ID:-}" ]; then
    test_show_task "$TASK_ID"
    test_get_log "$TASK_ID"
    test_get_preview "$TASK_ID"
    test_get_resource_usage "$TASK_ID" "${START_TS:-}" "${END_TS:-}"
else
    echo ""
    echo "NOTE: Set TASK_ID environment variable to run proc-task-specific tests:"
    echo "  TASK_ID=<task-id> [START_TS=<ts> END_TS=<ts>] bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi

# Execute eval-task-specific tests if EVAL_TASK_ID is provided
if [ -n "${EVAL_TASK_ID:-}" ]; then
    test_eval_show_task "$EVAL_TASK_ID"
    test_eval_get_log "$EVAL_TASK_ID"
    test_eval_get_preview "$EVAL_TASK_ID"
else
    echo ""
    echo "NOTE: Set EVAL_TASK_ID to run eval-task-specific tests:"
    echo "  EVAL_TASK_ID=<eval-task-id> bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi

echo ""
echo "=== Test Suite Complete ==="
echo ""
echo "NOTE: Mutating operations (create-task, update-task, delete-task, restart-task,"
echo "eval create-task, eval update-task, eval delete-task) require explicit user confirmation"
echo "and are not executed automatically."
