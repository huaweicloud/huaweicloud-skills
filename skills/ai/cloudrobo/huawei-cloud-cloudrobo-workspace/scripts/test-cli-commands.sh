#!/usr/bin/env bash
# test-cli-commands.sh — Functional testing for cloudrobo-workspace skill
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
test_list_workspaces() {
    echo "=== TC-01: list workspaces ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace list 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.list_workspaces()
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_list_workspaces_pagination() {
    echo "=== TC-02: list workspaces with pagination ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace list --limit 10 --offset 0 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.list_workspaces(limit=10, offset=0)
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_show_workspace() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-03: show workspace (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-03: show workspace --workspace-id $workspace_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace show --workspace-id "$workspace_id" 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.show_workspace('$workspace_id')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_create_workspace_dry_run() {
    echo "=== TC-04: create workspace --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace create --name test-dry-run --default-obs-path obs://bucket/test --dry-run 2>&1 | head -10
    fi
}

test_overview() {
    echo "=== TC-05: workspace overview ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace overview 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.get_workspace_overview()
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_current() {
    echo "=== TC-06: workspace current ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace current 2>&1 | head -10
    fi
}

test_list_members() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-07: list-members (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-07: list-members --workspace-id $workspace_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace list-members --workspace-id "$workspace_id" 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.list_workspace_members('$workspace_id')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_use_workspace() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-08: workspace use (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-08: workspace use --workspace-id $workspace_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace use --workspace-id "$workspace_id" 2>&1 | head -10
    fi
}

test_update_workspace_dry_run() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-09: update workspace --dry-run (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-09: update workspace --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace update --workspace-id "$workspace_id" --name test-update --dry-run 2>&1 | head -10
    fi
}

test_delete_workspace_dry_run() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-10: delete workspace --dry-run (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-10: delete workspace --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo workspace delete --workspace-id "$workspace_id" --dry-run 2>&1 | head -10
    fi
}

# Main execution
echo "=== cloudrobo-workspace Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo ""

scan_credentials

# Execute read-only tests (no mutation)
test_list_workspaces
test_list_workspaces_pagination
test_create_workspace_dry_run
test_overview
test_current

# Execute workspace-specific tests if WORKSPACE_ID is provided
if [ -n "${WORKSPACE_ID:-}" ]; then
    test_show_workspace "$WORKSPACE_ID"
    test_list_members "$WORKSPACE_ID"
    test_use_workspace "$WORKSPACE_ID"
    test_update_workspace_dry_run "$WORKSPACE_ID"
    test_delete_workspace_dry_run "$WORKSPACE_ID"
else
    echo ""
    echo "NOTE: Set WORKSPACE_ID environment variable to run workspace-specific tests:"
    echo "  WORKSPACE_ID=<workspace-id> bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi

echo ""
echo "=== Test Suite Complete ==="
echo ""
echo "NOTE: Mutating operations (create, update, delete, add-members, update-member,"
echo "delete-members) require explicit user confirmation and are not executed automatically."
