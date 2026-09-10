#!/bin/bash
# Test script for cloudrobo-robot skill
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

echo "=== Testing cloudrobo-robot skill ==="
if [ -n "$WORKSPACE_ID" ]; then
    echo "Workspace ID: $WORKSPACE_ID"
fi
echo ""

# Test 1: List robots
echo "Test 1: List robots"
cloudrobo robot list
echo ""

# Test 2: List robots filtered by workspace
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 2: List robots by workspace"
    cloudrobo robot list --workspace-id "$WORKSPACE_ID"
    echo ""
fi

# Test 3: Show SDK info (no parameters)
echo "Test 3: Show robot SDK info"
cloudrobo robot show-sdk
echo ""

# Test 4: Dry-run create robot (without actual submission)
echo "Test 4: Dry-run create robot"
echo "Note: This requires a valid type/manufacturer/robot_model. Example:"
echo "  cloudrobo robot create \\"
echo "    --name test-robot \\"
echo "    --type HUMANOID \\"
echo "    --manufacturer DemoMaker \\"
echo "    --robot-model B2-W \\"
if [ -n "$WORKSPACE_ID" ]; then
    echo "    --workspace-id $WORKSPACE_ID \\"
else
    echo "    --workspace-id <workspace-id> \\"
fi
echo "    --dry-run"
echo ""

# Test 5: Create robot (requires valid inputs; user must confirm)
echo "Test 5: Create robot"
echo "WARNING: This will create a robot. Provide valid inputs or skip."
echo "Example command:"
echo "  cloudrobo robot create \\"
echo "    --name test-robot \\"
echo "    --type HUMANOID \\"
echo "    --manufacturer DemoMaker \\"
echo "    --robot-model B2-W \\"
if [ -n "$WORKSPACE_ID" ]; then
    echo "    --workspace-id $WORKSPACE_ID"
else
    echo "    --workspace-id <workspace-id>"
fi
echo ""

# Test 6: Robot detail (if ROBOT_ID env var is set)
ROBOT_ID=${ROBOT_ID:-}
if [ -n "$ROBOT_ID" ]; then
    echo "Test 6: Show robot detail"
    cloudrobo robot show --robot-id "$ROBOT_ID"
    echo ""

    echo "Test 7: Update robot (user must confirm)"
    echo "WARNING: This updates the robot. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo robot update --robot-id "$ROBOT_ID" --description "Updated by test"
    echo ""

    echo "Test 8: Export access config / certificate (user must confirm)"
    echo "WARNING: This exports the robot access config (zip) with password. Press Ctrl+C to cancel."
    sleep 2
    mkdir -p ./certs
    cloudrobo robot export-certificate --robot-id "$ROBOT_ID" --password "temp-export-pw" --output ./certs || echo "Export may fail if certificate unavailable"
    echo ""

    echo "Test 9: Delete robot (user must confirm)"
    echo "WARNING: This deletes the robot. Press Ctrl+C to cancel."
    sleep 2
    cloudrobo robot delete --robot-id "$ROBOT_ID" || echo "Delete may fail if robot already gone"
    echo ""
fi

# Test 10: Query robots by type filter (cross-package select)
echo "Test 10: List robots by type"
cloudrobo robot list --type HUMANOID 2>/dev/null || echo "Note: no HUMANOID robots or type filter unavailable"
echo ""

# Test 11: Cross-module — query workspace (from workspace skill)
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 11: List workspaces (cross-package)"
    cloudrobo workspace list || echo "Note: workspace command may require additional setup"
    echo ""
fi

echo "=== Test script completed ==="
echo "Note: Some tests require actual robot IDs (set ROBOT_ID env var) or workspace IDs."
echo "For comprehensive end-to-end testing beyond these checks, run the commands from SKILL.md manually."
