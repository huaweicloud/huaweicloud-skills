#!/bin/bash
# Test script for cloudrobo-infer skill
# Usage: ./test-cli-commands.sh [-w workspace_id]
# If a workspace id is provided via -w, workspace-scoped tests will use it; otherwise they run without it.
#
# Optional env vars (used to drive the actual read-only / no-cost executions):
#   WORKSPACE_ID / -w  - workspace for list/create (create/list are workspace-scoped)
#   MODEL_ID           - model asset id to deploy (for create / dry-run create)
#   MODEL_VERSION_ID   - model version id to deploy (for create / dry-run create)
#   FLAVOR             - compute flavor (for create / dry-run create)
#   POOL_ID            - compute pool id, e.g. pool-<resource_id> (for create / dry-run create)
#   POOL_TYPE          - SHARED / DEDICATED (default SHARED)
#   SERVICE_ID         - existing service id (for show/start/stop/logs/update/delete/wait-deploy)
#   WAIT_TIMEOUT       - wait-deploy timeout seconds (default 600)
# When a required input is missing, the test is explicitly skipped with a WARN instead of
# silently disappearing; dry-run / read-only paths are actually executed when inputs are set.

set -euo pipefail

WORKSPACE_ID=""

while getopts ":w:" opt; do
    case "$opt" in
        w) WORKSPACE_ID="$OPTARG" ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

WORKSPACE_ID=${WORKSPACE_ID:-}
MODEL_ID=${MODEL_ID:-}
MODEL_VERSION_ID=${MODEL_VERSION_ID:-}
FLAVOR=${FLAVOR:-}
POOL_ID=${POOL_ID:-}
POOL_TYPE=${POOL_TYPE:-SHARED}
SERVICE_ID=${SERVICE_ID:-}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-600}

echo "=== Testing cloudrobo-infer skill ==="
echo "Workspace ID:   ${WORKSPACE_ID:-<not set>}"
echo "Model ID:       ${MODEL_ID:-<not set>}"
echo "Model Version:  ${MODEL_VERSION_ID:-<not set>}"
echo "Flavor:         ${FLAVOR:-<not set>}"
echo "Pool ID:        ${POOL_ID:-<not set>}"
echo "Pool Type:      $POOL_TYPE"
echo "Service ID:     ${SERVICE_ID:-<not set>}"
echo "Wait Timeout:   $WAIT_TIMEOUT"
echo ""

# Test 1: List inference services (requires workspace_id)
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 1: List inference services in workspace $WORKSPACE_ID"
    cloudrobo infer list --workspace-id "$WORKSPACE_ID"
    echo ""
else
    echo "Test 1: SKIPPED (no WORKSPACE_ID provided — run with -w <workspace_id>)"
    echo ""
fi

# Test 2: Dry-run create service (no actual submission, no cost)
echo "Test 2: Dry-run create inference service"
if [ -n "$MODEL_ID" ] && [ -n "$MODEL_VERSION_ID" ] && [ -n "$FLAVOR" ]; then
    DRYRUN_ARGS=(--name verify-infer --flavor "$FLAVOR"
        --model-json "{\"model_id\": \"$MODEL_ID\", \"model_version_id\": \"$MODEL_VERSION_ID\"}")
    if [ -n "$WORKSPACE_ID" ]; then
        DRYRUN_ARGS+=(--workspace-id "$WORKSPACE_ID")
    fi
    if [ -n "$POOL_ID" ]; then
        DRYRUN_ARGS+=(--pool-id "$POOL_ID")
    fi
    DRYRUN_ARGS+=(--pool-type "$POOL_TYPE"
        --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' --dry-run)
    cloudrobo infer create "${DRYRUN_ARGS[@]}"
    echo ""
else
    echo "SKIPPED: MODEL_ID, MODEL_VERSION_ID and FLAVOR are required to execute the dry-run create."
    echo "Example:"
    echo "  cloudrobo infer create --name verify-infer --flavor <flavor> \\"
    echo "    --model-json '{\"model_id\": \"<model-id>\", \"model_version_id\": \"<model-version-id>\"}' \\"
    [ -n "$WORKSPACE_ID" ] && echo "    --workspace-id $WORKSPACE_ID \\" || echo "    --workspace-id <workspace-id> \\"
    echo "    --pool-type SHARED --stop-schedule-json '{\"duration\": 60, \"time_unit\": \"MINUTES\"}' \\"
    echo "    # optional: --pool-id <pool-id> only for DEDICATED pools \\"
    echo "    --dry-run"
    echo ""
fi

# Test 3: Create service (mutating, requires valid inputs; runs only when no SERVICE_ID yet)
echo "Test 3: Create inference service"
if [ -n "$SERVICE_ID" ]; then
    echo "SKIPPED: SERVICE_ID already provided ($SERVICE_ID); reuse it for the lifecycle tests."
    echo ""
elif [ -n "$MODEL_ID" ] && [ -n "$MODEL_VERSION_ID" ] && [ -n "$FLAVOR" ] && [ -n "$WORKSPACE_ID" ]; then
    echo "WARNING: This creates a real service consuming pool resources. Press Ctrl+C to cancel."
    sleep 2
    CREATE_ARGS=(--name verify-infer --flavor "$FLAVOR"
        --model-json "{\"model_id\": \"$MODEL_ID\", \"model_version_id\": \"$MODEL_VERSION_ID\"}")
    if [ -n "$WORKSPACE_ID" ]; then
        CREATE_ARGS+=(--workspace-id "$WORKSPACE_ID")
    fi
    if [ -n "$POOL_ID" ]; then
        CREATE_ARGS+=(--pool-id "$POOL_ID")
    fi
    CREATE_ARGS+=(--pool-type "$POOL_TYPE"
        --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}')
    CREATE_RESULT=$(cloudrobo infer create "${CREATE_ARGS[@]}")
    echo "$CREATE_RESULT"
    NEW_SERVICE_ID=$(echo "$CREATE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || echo "")
    if [ -n "$NEW_SERVICE_ID" ]; then
        echo "Created service id: $NEW_SERVICE_ID (set SERVICE_ID=$NEW_SERVICE_ID to run Test4-9/10 against it)"
        SERVICE_ID="$NEW_SERVICE_ID"
    fi
    echo ""
else
    echo "SKIPPED: MODEL_ID, MODEL_VERSION_ID, FLAVOR and WORKSPACE_ID are all required to create a real service."
    echo "Example:"
    echo "  cloudrobo infer create --name verify-infer --flavor <flavor> \\"
    echo "    --model-json '{\"model_id\": \"<model-id>\", \"model_version_id\": \"<model-version-id>\"}' \\"
    [ -n "$WORKSPACE_ID" ] && echo "    --workspace-id $WORKSPACE_ID \\" || echo "    --workspace-id <workspace-id> \\"
    echo "    --pool-type SHARED --stop-schedule-json '{\"duration\": 60, \"time_unit\": \"MINUTES\"}'"
    echo "    # optional: --pool-id <pool-id> only for DEDICATED pools"
    echo ""
fi

# Test 4-9: Service lifecycle (mutating; requires SERVICE_ID)
if [ -n "$SERVICE_ID" ]; then
    echo "Test 4: Show service detail"
    cloudrobo infer show --service-id "$SERVICE_ID"
    echo ""

    echo "Test 5: Start service (user must confirm)"
    echo "WARNING: This starts the service, consuming pool resources. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo infer start --service-id "$SERVICE_ID" || echo "Start may fail if already running"
    echo ""

    echo "Test 6: Stop service (user must confirm)"
    echo "WARNING: This stops the service. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo infer stop --service-id "$SERVICE_ID" || echo "Stop may fail if already stopped"
    echo ""

    echo "Test 7: List logs (ms timestamps)"
    END_MS=$(date +%s%3N 2>/dev/null || echo "0")
    START_MS=$(( END_MS - 3600000 ))
    cloudrobo infer list-logs --service-id "$SERVICE_ID" --start-time "$START_MS" --end-time "$END_MS" --limit 50 || echo "Logs may be empty if service never ran"
    echo ""

    echo "Test 8: Update service (user must confirm)"
    echo "WARNING: This updates the service. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo infer update --service-id "$SERVICE_ID" --description "Updated by test" || echo "Update may fail"
    echo ""

    echo "Test 9: Delete service (user must confirm)"
    echo "WARNING: This deletes the service. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo infer delete --service-id "$SERVICE_ID" || echo "Delete may fail if service already gone"
    echo ""
else
    echo "WARN: Tests 4-9 (show/start/stop/logs/update/delete) are skipped because SERVICE_ID is not set."
    echo "      Export SERVICE_ID=<id> to execute the service lifecycle tests against an existing service."
    echo ""
fi

# Test 10: Wait-deploy (requires valid service_id; no cost — client-side polling)
echo "Test 10: Wait-deploy (CLI convenience)"
if [ -n "$SERVICE_ID" ]; then
    cloudrobo infer wait-deploy --service-id "$SERVICE_ID" --timeout "$WAIT_TIMEOUT"
    echo ""
else
    echo "SKIPPED: SERVICE_ID is required to execute wait-deploy."
    echo "Example:"
    echo "  cloudrobo infer wait-deploy --service-id <service-id> --timeout 600"
    echo ""
fi

# Test 11: Query model assets (cross-package)
echo "Test 11: Query model assets (cross-package)"
echo "Note: list-assets requires --catalog-id (from workspace current) or --repository-id"
echo "Example: cloudrobo asset list-assets --catalog-id <catalog_id> --type model --limit 5"
echo "Or search plaza: cloudrobo asset list-publication-assets --type model --actions ONLINE_DEPLOYMENT --action-status ENABLE --limit 5"
cloudrobo asset list-publication-assets --type model --actions ONLINE_DEPLOYMENT --action-status ENABLE --limit 5 || echo "May return empty if no deployable models"
echo ""

echo "=== Test script completed ==="
echo "Note: Some tests require actual service IDs (set SERVICE_ID env var), model IDs, or workspace IDs."
echo "For comprehensive end-to-end testing beyond these read-only checks, run the commands from SKILL.md manually."
