#!/bin/bash
# Test script for cloudrobo-robot skill
# Usage: ./test-cli-commands.sh [-w workspace_id]
# If a workspace id is provided via -w, workspace-scoped tests will use it; otherwise they run without it.
# Lifecycle/certificate tests (Test6-9) need a `robot_id`; provide one via the ROBOT_ID env var
# (e.g. ROBOT_ID=<32hex> ./test-cli-commands.sh) or let Test5 auto-create a robot and parse the
# returned robot_id. If no robot_id is available, Test6-9 are explicitly skipped with a WARN.

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

# Test 4: Dry-run create robot (actually executed, no side effects)
echo "Test 4: Dry-run create robot"
ROBOT_NAME="test-robot-$(date +%s)"
if [ -n "$WORKSPACE_ID" ]; then
    cloudrobo robot create \
        --name "$ROBOT_NAME" \
        --type HUMANOID \
        --manufacturer DemoMaker \
        --robot-model B2-W \
        --workspace-id "$WORKSPACE_ID" \
        --dry-run
else
    cloudrobo robot create \
        --name "$ROBOT_NAME" \
        --type HUMANOID \
        --manufacturer DemoMaker \
        --robot-model B2-W \
        --dry-run
fi
echo ""
echo "Note: Dry-run validates the command/params without submitting. Example used:"
echo "  cloudrobo robot create --name $ROBOT_NAME --type HUMANOID --manufacturer DemoMaker --robot-model B2-W [--workspace-id] --dry-run"
echo ""

# Test 5: Create robot (mutating; user must confirm). Parses robot_id for Test6-9.
echo "Test 5: Create robot"
ROBOT_ID=${ROBOT_ID:-}
if [ -n "$ROBOT_ID" ]; then
    echo "ROBOT_ID already provided via env: $ROBOT_ID (skipping create)"
    echo ""
elif [ -n "$WORKSPACE_ID" ]; then
    echo "WARNING: This will create a robot. Press Ctrl+C within 3 seconds to cancel."
    sleep 3
    CREATE_RESULT=$(cloudrobo robot create \
        --name "$ROBOT_NAME" \
        --type HUMANOID \
        --manufacturer DemoMaker \
        --robot-model B2-W \
        --workspace-id "$WORKSPACE_ID")
    echo "$CREATE_RESULT"
    ROBOT_ID=$(echo "$CREATE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('robot_id',''))" 2>/dev/null || echo "")
    echo ""
    if [ -n "$ROBOT_ID" ]; then
        echo "Parsed robot_id from create output: $ROBOT_ID"
    else
        echo "WARN: 未能从 create 输出解析 robot_id"
    fi
    echo ""
else
    echo "WARN: 未提供 WORKSPACE_ID（-w）且未设置 ROBOT_ID，跳过 create"
    echo ""
fi

# Test 6-9: Lifecycle / certificate tests (require robot_id)
if [ -z "$ROBOT_ID" ]; then
    echo "WARN: ROBOT_ID 未设置，跳过 Test6-9 生命周期/证书验证"
    echo "      设置 ROBOT_ID=<32hex> 环境变量，或提供 -w <workspace-id> 让 Test5 自动创建机器人并解析 robot_id"
    echo ""
else
    echo "Test 6: Show robot detail"
    cloudrobo robot show --robot-id "$ROBOT_ID"
    echo ""

    echo "Test 7: Update robot (user must confirm)"
    echo "WARNING: This updates the robot. Press Ctrl+C within 3 seconds to cancel."
    sleep 3
    cloudrobo robot update --robot-id "$ROBOT_ID" --description "Updated by test"
    echo ""

    echo "Test 8: Export access config / certificate (user must confirm)"
    echo "WARNING: This exports the robot access config (zip) with password. Press Ctrl+C within 3 seconds to cancel."
    sleep 3
    mkdir -p ./certs
    cloudrobo robot export-certificate --robot-id "$ROBOT_ID" --password "temp-export-pw" --output ./certs || echo "Export may fail if certificate unavailable"
    echo ""

    echo "Test 9: Delete robot (user must confirm)"
    echo "WARNING: This deletes the robot. Press Ctrl+C within 3 seconds to cancel."
    sleep 3
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
