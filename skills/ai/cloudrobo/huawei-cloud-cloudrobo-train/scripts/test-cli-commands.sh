#!/bin/bash
# Test script for cloudrobo-train skill
# Usage: ./test-cli-commands.sh [-w workspace_id] [-s start_ts] [-e end_ts]
# If a workspace id is provided via -w, stats tests will use it; otherwise stats is skipped.

set -euo pipefail

WORKSPACE_ID=""
START_TS=$(date -d '1 hour ago' +%s 2>/dev/null || expr $(date +%s) - 3600)
END_TS=$(date +%s)

while getopts ":w:s:e:" opt; do
    case "$opt" in
        w) WORKSPACE_ID="$OPTARG" ;;
        s) START_TS="$OPTARG" ;;
        e) END_TS="$OPTARG" ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

echo "=== Testing cloudrobo-train skill ==="
if [ -n "$WORKSPACE_ID" ]; then
    echo "Workspace ID: $WORKSPACE_ID"
fi
echo "Time range: $START_TS ~ $END_TS"
echo ""

# Test 1: List training tasks
echo "Test 1: List training tasks"
cloudrobo train list-tasks
echo ""

# Test 2: List tasks filtered by status
echo "Test 2: List tasks filtered by status"
cloudrobo train list-tasks --status RUNNING
echo ""

# Test 3: List tasks filtered by train_mode
echo "Test 3: List tasks filtered by train_mode"
cloudrobo train list-tasks --train-mode MODEL_TUNING
echo ""

# Test 4: Stats (requires workspace_id)
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 4: Count tasks by status"
    cloudrobo train stats --workspace-id "$WORKSPACE_ID"
    echo ""
else
    echo "Test 4: Skipped (no workspace_id provided)"
    echo ""
fi

# Test 5: Save draft task
echo "Test 5: Save draft task"
DRAFT_RESULT=$(cloudrobo train save-draft --config '{"name": "test-draft", "train_mode": "MODEL_TUNING"}')
echo "$DRAFT_RESULT"
DRAFT_TASK_ID=$(echo "$DRAFT_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null || echo "")
echo "Draft task ID: $DRAFT_TASK_ID"
echo ""

# Test 6: Show task detail (if task exists)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 6: Show task detail"
    cloudrobo train show-task --task-id "$DRAFT_TASK_ID"
    echo ""
fi

# Test 7: Get execution stages (if task exists)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 7: Get execution stages for draft task"
    cloudrobo train get-stages --task-id "$DRAFT_TASK_ID" || echo "Expected: draft task may not have stages yet"
    echo ""
fi

# Test 8: Get resource usage (requires --metric/--start/--end)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 8: Get resource usage (requires --metric/--start/--end)"
    cloudrobo train get-resource-usage --task-id "$DRAFT_TASK_ID" --metric cpu_util --start "$START_TS" --end "$END_TS" || echo "Expected: draft task has no resource usage yet"
    echo ""
fi

# Test 9: Get events (requires --start-time/--end-time)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 9: Get events (requires --start-time/--end-time)"
    cloudrobo train get-events --task-id "$DRAFT_TASK_ID" --start-time "$START_TS" --end-time "$END_TS" || echo "Expected: draft task has no events yet"
    echo ""
fi

# Test 10: Get logs (uses --file-name)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 10: Get logs"
    cloudrobo train get-logs --task-id "$DRAFT_TASK_ID" || echo "Expected: draft task has no logs yet"
    echo ""
fi

# Test 11: Get signed URL (requires --file-source/--file-name)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 11: Get signed URL (requires --file-source/--file-name)"
    cloudrobo train get-signed-url --task-id "$DRAFT_TASK_ID" --file-source TRAIN --file-name "train.log" || echo "Expected: may fail if file does not exist"
    echo ""
fi

# Test 12: Restart draft task (submit it)
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 12: Restart draft task (submit it)"
    echo "WARNING: This will submit the draft task. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo train restart-task --task-id "$DRAFT_TASK_ID" || echo "Expected: may fail if draft config is incomplete"
    echo ""
fi

# Test 13: Query base models (cross-package)
echo "Test 13: Query base models"
cloudrobo asset list-assets --type model --limit 5 || echo "May return empty if no models in workspace"
echo ""

# Test 14: Query datasets (cross-package)
echo "Test 14: Query datasets"
cloudrobo asset list-assets --type dataset --limit 5 || echo "May return empty if no datasets in workspace"
echo ""

# Test 15: Query algorithms (cross-package)
echo "Test 15: Query algorithms"
cloudrobo asset list-publication-assets --type algorithm --limit 5
echo ""

# Test 16: Create finetune task (example only — requires user confirmation)
echo "Test 16: Create finetune task (MODEL_TUNING)"
echo "Note: This requires valid base model and dataset IDs. Skipping actual execution."
echo "Example command (train_mode/method/model/dataset/spec are inside --config):"
echo "  cloudrobo train create-task --config '{\"name\":\"test-finetune\",\"train_mode\":\"MODEL_TUNING\",\"base_model_asset_id\":\"<model-id>\",\"dataset_asset_ids\":[\"<dataset-id>\"],\"method\":\"LORA\",\"spec\":\"Ascend: 1 * Ascend-910B | 24 vCPUs | 96 GiB\"}'"
echo ""

# Test 17: Create pretrain task (example only — requires user confirmation)
echo "Test 17: Create pretrain task (TRAIN_FROM_SCRATCH)"
echo "Note: This requires valid algorithm config. Skipping actual execution."
echo "Example command (algorithm/spec/dataset are inside --config):"
echo "  cloudrobo train create-task --config '{\"name\":\"test-pretrain\",\"train_mode\":\"TRAIN_FROM_SCRATCH\",\"algorithm\":{\"algorithm_asset_id\":\"...\",\"image_url\":\"...\",\"command\":\"...\",\"boot_file\":\"...\"},\"spec\":\"Ascend: 2 * Ascend-910B | 48 vCPUs | 192 GiB\",\"dataset\":{\"source_type\":\"DATASET\",\"dataset_asset_id\":\"...\"}}'"
echo ""

# Test 18: Delete draft task (cleanup) — CLI now supports delete-tasks
if [ -n "$DRAFT_TASK_ID" ]; then
    echo "Test 18: Delete draft task (cleanup)"
    echo "WARNING: This will delete the draft task. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo train delete-tasks --task-id "$DRAFT_TASK_ID" || echo "Delete may fail if task already submitted"
    echo ""
fi

# --- SimRL tests (--sim-rl flag) ---

echo "=== SimRL tests (--sim-rl) ==="
echo ""

# Test 19: SimRL stats
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 19: Count SimRL tasks by status"
    cloudrobo train stats --workspace-id "$WORKSPACE_ID" --sim-rl
    echo ""
fi

# Test 20: List SimRL tasks
echo "Test 20: List SimRL tasks"
cloudrobo train list-tasks --sim-rl
echo ""

# Test 21: SimRL get-stages (if a SimRL task_id is available)
SIM_RL_TASK_ID=${SIM_RL_TASK_ID:-}
if [ -n "$SIM_RL_TASK_ID" ]; then
    echo "Test 21: Show SimRL task"
    cloudrobo train show-task --task-id "$SIM_RL_TASK_ID" --sim-rl
    echo ""

    echo "Test 22: Get SimRL stages"
    echo "  Skipped: SimRL has no stages endpoint (get-stages is train-only)"

    echo "Test 23: Get SimRL resource usage"
    cloudrobo train get-resource-usage --task-id "$SIM_RL_TASK_ID" --metric cpu_util --start "$START_TS" --end "$END_TS" --sim-rl
    echo ""

    echo "Test 24: Get SimRL events"
    cloudrobo train get-events --task-id "$SIM_RL_TASK_ID" --start-time "$START_TS" --end-time "$END_TS" --sim-rl
    echo ""

    echo "Test 25: Get SimRL logs"
    cloudrobo train get-logs --task-id "$SIM_RL_TASK_ID" --sim-rl
    echo ""

    echo "Test 26: Get SimRL signed URL"
    cloudrobo train get-signed-url --task-id "$SIM_RL_TASK_ID" --file-source TRAIN --file-name "train.log" --sim-rl || echo "May fail if file does not exist"
    echo ""
fi

# Test 27: Verify resume-task rejects --sim-rl
echo "Test 27: Verify resume-task rejects --sim-rl (train-only)"
cloudrobo train resume-task --task-id "${DRAFT_TASK_ID:-dummy}" --sim-rl 2>&1 | grep -i "no such option\|--sim-rl" && echo "PASS: --sim-rl correctly rejected on resume-task" || echo "Note: verify manually that --sim-rl is not accepted on resume-task"
echo ""

echo "=== Test script completed ==="
echo "Note: Some tests may require actual task IDs or valid asset IDs to fully execute."
echo "Set SIM_RL_TASK_ID env var to test SimRL task-specific operations."
echo "For comprehensive end-to-end testing beyond these checks, run the commands from SKILL.md manually."
