#!/bin/bash
# Test script for cloudrobo-r2c skill
# Usage: ./test-cli-commands.sh [-w workspace_id]
# If a workspace id is provided via -w, cross-skill tests will use it; otherwise they are skipped.
# Environment variables:
#   BUNDLE_PATH   - Path to credential bundle zip (for client tests)
#   ROBOT_CONFIG  - Path to robot config YAML (default: config/robot_dummy_config.yaml)
#   DURATION      - Test duration in seconds (default: 10)

set -euo pipefail

WORKSPACE_ID=""
BUNDLE_PATH=${BUNDLE_PATH:-}
ROBOT_CONFIG=${ROBOT_CONFIG:-config/robot_dummy_config.yaml}
DURATION=${DURATION:-10}

while getopts ":w:" opt; do
    case "$opt" in
        w) WORKSPACE_ID="$OPTARG" ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

echo "=== Testing cloudrobo-r2c skill ==="
if [ -n "$WORKSPACE_ID" ]; then
    echo "Workspace ID: $WORKSPACE_ID"
fi
if [ -n "$BUNDLE_PATH" ]; then
    echo "Bundle Path: $BUNDLE_PATH"
fi
echo "Robot Config: $ROBOT_CONFIG"
echo ""

# Test 1: Client startup with dummy adapter (requires bundle)
echo "Test 1: Start R2C client (dummy adapter, ${DURATION}s)"
if [ -n "$BUNDLE_PATH" ] && [ -f "$BUNDLE_PATH" ]; then
    echo "  Starting client for ${DURATION}s..."
    timeout "$DURATION" cloudrobo r2c client \
      --bundle "$BUNDLE_PATH" \
      --robot-config "$ROBOT_CONFIG" \
      --duration "$DURATION" \
      --log-level INFO 2>&1 || true
    echo "  Client test completed."
else
    echo "  Skipping: BUNDLE_PATH not set or file not found"
    echo "  Set BUNDLE_PATH env var to test client startup"
fi
echo ""

# Test 2: Dry-run mode test
echo "Test 2: Dry-run mode test"
if [ -n "$BUNDLE_PATH" ] && [ -f "$BUNDLE_PATH" ]; then
    echo "  Starting client in dry_run mode for ${DURATION}s..."
    # Create a temporary dry_run config
    DRY_RUN_CONFIG="/tmp/r2c_dryrun_config.yaml"
    if [ -f "$ROBOT_CONFIG" ]; then
        sed 's/dry_run: false/dry_run: true/g' "$ROBOT_CONFIG" > "$DRY_RUN_CONFIG"
        timeout "$DURATION" cloudrobo r2c client \
          --bundle "$BUNDLE_PATH" \
          --robot-config "$DRY_RUN_CONFIG" \
          --duration "$DURATION" \
          --log-level DEBUG 2>&1 || true
        rm -f "$DRY_RUN_CONFIG"
    fi
    echo "  Dry-run test completed."
else
    echo "  Skipping: BUNDLE_PATH not set"
fi
echo ""

# Test 3: Observation recording test
echo "Test 3: Observation recording test"
if [ -n "$BUNDLE_PATH" ] && [ -f "$BUNDLE_PATH" ]; then
    echo "  Recording observations for ${DURATION}s..."
    timeout "$DURATION" cloudrobo r2c client \
      --bundle "$BUNDLE_PATH" \
      --robot-config "$ROBOT_CONFIG" \
      --duration "$DURATION" \
      --record /tmp/r2c_test_observations.pkl \
      --log-level INFO 2>&1 || true
    if [ -f /tmp/r2c_test_observations.pkl ]; then
        echo "  Recording file created: $(ls -la /tmp/r2c_test_observations.pkl)"
        rm -f /tmp/r2c_test_observations.pkl
    else
        echo "  Warning: recording file not created"
    fi
else
    echo "  Skipping: BUNDLE_PATH not set"
fi
echo ""

# Test 4: Missing bundle error (should fail)
echo "Test 4: Missing bundle error (expect failure)"
cloudrobo r2c client --robot-config "$ROBOT_CONFIG" --duration 1 2>&1 || echo "  (expected failure: project_id required)"
echo ""

# Test 5: Log file test
echo "Test 5: Log file test"
if [ -n "$BUNDLE_PATH" ] && [ -f "$BUNDLE_PATH" ]; then
    LOG_FILE="/tmp/r2c_test.log"
    timeout 5 cloudrobo r2c client \
      --bundle "$BUNDLE_PATH" \
      --robot-config "$ROBOT_CONFIG" \
      --duration 5 \
      --log-file "$LOG_FILE" \
      --log-level DEBUG 2>&1 || true
    if [ -f "$LOG_FILE" ]; then
        echo "  Log file created: $(ls -la "$LOG_FILE")"
        rm -f "$LOG_FILE"
    else
        echo "  Warning: log file not created"
    fi
else
    echo "  Skipping: BUNDLE_PATH not set"
fi
echo ""

# Test 6: Cross-skill — verify robot is registered (from robot skill)
if [ -n "$WORKSPACE_ID" ]; then
    echo "Test 6: Cross-skill — list robots (from robot skill)"
    cloudrobo robot list --workspace-id "$WORKSPACE_ID" 2>/dev/null || echo "  Note: robot command may require additional setup"
    echo ""
fi

echo "=== Test script completed ==="
echo "Note: Client tests require BUNDLE_PATH (credential bundle from robot export-certificate)."
echo "For comprehensive end-to-end testing beyond these checks, run the commands from SKILL.md manually."
