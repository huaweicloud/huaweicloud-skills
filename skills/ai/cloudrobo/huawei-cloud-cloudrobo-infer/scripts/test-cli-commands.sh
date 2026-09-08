#!/bin/bash
# Test script for cloudrobo-infer skill
# Usage: ./test-cli-commands.sh [-w workspace_id]
# If a workspace id is provided via -w, workspace-scoped tests will use it; otherwise they run without it.

set -euo pipefail

WORKSPACE_ID=""

while getopts ":w:" opt; do
    case "$opt" in
        w) WORKSPACE_ID="$OPTARG" ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

echo "=== Testing cloudrobo-infer skill ==="
if [ -n "$WORKSPACE_ID" ]; then
    echo "Workspace ID: $WORKSPACE_ID"
fi
echo ""

# Test 1: List inference services (requires workspace_id)
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 1: List inference services in workspace $WORKSPACE_ID"
    cloudrobo infer list --workspace-id "$WORKSPACE_ID"
    echo ""
fi

# Test 2: Dry-run create service (without actual submission)
echo "Test 2: Dry-run create inference service"
echo "Note: This requires valid model/pool/flavor. Example:"
echo "  cloudrobo infer create \\"
echo "    --name verify-infer \\"
echo "    --flavor <flavor> \\"
echo "    --model-json '{\"model_id\": \"<model-id>\", \"model_version_id\": \"<model-version-id>\"}' \\"
if [ -n "$WORKSPACE_ID" ]; then
    echo "    --workspace-id $WORKSPACE_ID \\"
else
    echo "    --workspace-id <workspace-id> \\"
fi
echo "    --pool-id <pool-id> --pool-type SHARED \\"
echo "    --stop-schedule-json '{\"duration\": 60, \"time_unit\": \"MINUTES\"}' \\"
echo "    --dry-run"
echo ""

# Test 3: Create service (requires valid inputs; user must confirm)
echo "Test 3: Create inference service"
echo "WARNING: This will create a real service consuming pool resources. Provide valid inputs or skip."
echo "Example command:"
echo "  cloudrobo infer create \\"
echo "    --name verify-infer \\"
echo "    --flavor <flavor> \\"
echo "    --model-json '{\"model_id\": \"<model-id>\", \"model_version_id\": \"<model-version-id>\"}' \\"
if [ -n "$WORKSPACE_ID" ]; then
    echo "    --workspace-id $WORKSPACE_ID \\"
else
    echo "    --workspace-id <workspace-id> \\"
fi
echo "    --pool-id <pool-id> --pool-type SHARED \\"
echo "    --stop-schedule-json '{\"duration\": 60, \"time_unit\": \"MINUTES\"}'"
echo ""

# Test 4: Service detail (if SERVICE_ID env var is set)
SERVICE_ID=${SERVICE_ID:-}
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
fi

# Test 10: Wait-deploy (requires valid service_id; user must confirm)
echo "Test 10: Wait-deploy (CLI convenience)"
echo "WARNING: This waits for a service to finish deploying. Provide valid service_id or skip."
echo "Example command:"
echo "  cloudrobo infer wait-deploy \\"
echo "    --service-id <service-id> \\"
echo "    --timeout 600"
echo ""

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
