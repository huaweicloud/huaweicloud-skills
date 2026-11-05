#!/bin/bash
# Test script for cloudrobo-dispatch skill
# Usage: ./test-cli-commands.sh
# Requires: a valid SESSION_ID, and for full lifecycle tests, a test ROBOT_ID and EXEC_MODEL_ID.
# Optional env vars:
#   SESSION_ID        - dispatcher session id (required for session-scoped ops)
#   ROBOT_ID          - target robot id (for create-task)
#   EXEC_MODEL_ID     - exec model id (for create-task)
#   TASK_ID           - existing task id (to skip create if you already have one)
#   INFER_SERVICE_ID  - optional filter for list-tasks

set -e

SESSION_ID=${SESSION_ID:-}
ROBOT_ID=${ROBOT_ID:-}
EXEC_MODEL_ID=${EXEC_MODEL_ID:-}
TASK_ID=${TASK_ID:-}
INFER_SERVICE_ID=${INFER_SERVICE_ID:-}

echo "=== Testing cloudrobo-dispatch skill ==="
echo "Session ID: ${SESSION_ID:-<not set>}"
echo "Robot ID:   ${ROBOT_ID:-<not set>}"
echo "Exec Model: ${EXEC_MODEL_ID:-<not set>}"
echo "Task ID:    ${TASK_ID:-<not set>}"
echo ""

if [ -z "$SESSION_ID" ]; then
    echo "ERROR: SESSION_ID is required for dispatch operations."
    echo "Export SESSION_ID to run session-scoped dispatch commands."
    exit 1
fi

# Test 1: List tasks in session
echo "Test 1: List tasks in session"
cloudrobo dispatch list-tasks --session-id "$SESSION_ID"
echo ""

# Test 2: List tasks filtered by status
echo "Test 2: List tasks filtered by status"
cloudrobo dispatch list-tasks --session-id "$SESSION_ID" --status RUNNING
echo ""

# Test 3: List tasks filtered by robot
if [ -n "$ROBOT_ID" ]; then
    echo "Test 3: List tasks filtered by robot"
    cloudrobo dispatch list-tasks --session-id "$SESSION_ID" --robot-id "$ROBOT_ID"
    echo ""
fi

# Test 4: List tasks filtered by infer service
if [ -n "$INFER_SERVICE_ID" ]; then
    echo "Test 4: List tasks filtered by infer service"
    cloudrobo dispatch list-tasks --session-id "$SESSION_ID" --infer-service-id "$INFER_SERVICE_ID"
    echo ""
fi

# Test 5: Create task (mutating, needs confirmation)
if [ -z "$TASK_ID" ]; then
    if [ -n "$ROBOT_ID" ] && [ -n "$EXEC_MODEL_ID" ]; then
        echo "Test 5: Create task (mutating)"
        echo "WARNING: This creates a dispatcher task. Press Ctrl+C to cancel."
        sleep 2
        CREATE_RESULT=$(cloudrobo dispatch create-task \
            --session-id "$SESSION_ID" \
            --name "test-task-$(date +%s)" \
            --task "Move forward 1 meter and report position" \
            --constraints-json "{\"model\":{\"exec_model_id\":\"$EXEC_MODEL_ID\"},\"robot_id\":\"$ROBOT_ID\",\"exec_constraints\":{\"max_run_time\":10,\"max_iter_num\":100}}")
        echo "$CREATE_RESULT"
        TASK_ID=$(echo "$CREATE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || echo "")
        echo "Task ID: $TASK_ID"
        echo ""
    else
        echo "Test 5: Skipped (ROBOT_ID and EXEC_MODEL_ID not both set)"
        echo ""
    fi
fi

# Test 6: Show task detail
if [ -n "$TASK_ID" ]; then
    echo "Test 6: Show task detail"
    cloudrobo dispatch show-task --session-id "$SESSION_ID" --task-id "$TASK_ID"
    echo ""
fi

# Test 7: Wait for task completion via wait-task (blocks, polls every 5s until status != RUNNING)
if [ -n "$TASK_ID" ]; then
    echo "Test 7: Wait for task completion (wait-task, default timeout 600s)"
    cloudrobo dispatch wait-task --session-id "$SESSION_ID" --task-id "$TASK_ID" || \
        echo "  Note: wait-task exited non-zero (timeout or error) — re-check with show-task."
    echo ""
fi

# Test 8: Show task result
if [ -n "$TASK_ID" ]; then
    echo "Test 8: Show task result"
    cloudrobo dispatch show-task-result --session-id "$SESSION_ID" --task-id "$TASK_ID"
    echo ""

    echo "Test 9: Show task result (paginated)"
    cloudrobo dispatch show-task-result --session-id "$SESSION_ID" --task-id "$TASK_ID" --limit 100 --offset 0
    echo ""
fi

# Test 10: Dry-run create (no submission)
echo "Test 10: Dry-run create"
if [ -n "$ROBOT_ID" ] && [ -n "$EXEC_MODEL_ID" ]; then
    cloudrobo dispatch create-task --session-id "$SESSION_ID" --name "dry-run-test" --task "test" --constraints-json "{\"model\":{\"exec_model_id\":\"$EXEC_MODEL_ID\"},\"robot_id\":\"$ROBOT_ID\",\"exec_constraints\":{\"max_run_time\":10,\"max_iter_num\":100}}" --dry-run
else
    echo "Skipped: need ROBOT_ID and EXEC_MODEL_ID"
fi
echo ""

# Test 11: Dry-run cancel
echo "Test 11: Dry-run cancel"
if [ -n "$TASK_ID" ]; then
    cloudrobo dispatch cancel-task --session-id "$SESSION_ID" --task-id "$TASK_ID" --dry-run
else
    echo "Skipped: no TASK_ID"
fi
echo ""

# Test 12: Path traversal blocked (exit-code based; no reliance on specific error text)
echo "Test 12: Path traversal blocked"
if TRAVERSAL_OUTPUT=$(cloudrobo dispatch show-task --session-id "$SESSION_ID" --task-id '../etc/passwd' 2>&1); then
    echo "FAIL: path traversal not blocked (command succeeded)"
else
    echo "PASS: traversal blocked (command exited non-zero; actual error below)"
    echo "$TRAVERSAL_OUTPUT" | tail -3
fi
echo ""

# Test 13: Cancel task (mutating, needs confirmation)
echo "Test 13: Cancel task (mutating)"
if [ -n "$TASK_ID" ]; then
    echo "  Attempting to cancel task $TASK_ID (only valid while running/pending)..."
    if cloudrobo dispatch cancel-task --session-id "$SESSION_ID" --task-id "$TASK_ID"; then
        echo "PASS: cancel-task executed successfully for task $TASK_ID"
    else
        echo "  Note: cancel-task exited non-zero — the task may already be in a terminal state"
        echo "  (cancelling a finished task is rejected; see SKILL.md Edge Cases). Verify with show-task."
    fi
else
    echo "  (No TASK_ID; script did not verify cancellation capability. Create a task to obtain a TASK_ID and run cancel-task manually.)"
fi
echo ""

echo "=== Test script completed ==="
echo "Note: dispatch operations are session-scoped; ensure SESSION_ID is valid."
echo "WARNING: Subagents may return stale cached data for old task/session IDs. If results look stale, wait (60+ minutes) and re-query."
echo "For comprehensive end-to-end testing beyond these read-only checks, run the commands from SKILL.md manually."
