#!/usr/bin/env bash
# test-cli-commands.sh — Functional testing for cloudrobo-workspace skill
# Usage:
#   bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}] [-m]
#   -s {skill-path}   Path to the skill directory (required)
#   -e {cli|sdk}       Executor mode: cli (default) or sdk
#   -m                 Include mutation test cases (TC-11..TC-18, TC-23..TC-28);
#                      each mutation case prompts for explicit confirmation before running
#
# Coverage (mirrors templates/test-vars.json, 28 cases):
#   TC-01..TC-10   CLI read-only / dry-run cases (run automatically)
#   TC-11..TC-18   CLI mutation cases (require -m + per-case confirmation)
#   TC-19..TC-22   SDK read-only cases (run automatically with -e sdk)
#   TC-23..TC-27   SDK mutation cases (require -e sdk -m + per-case confirmation)
#   TC-28          End-to-end onboarding flow (CLI mutation, require -m + confirmation)
#
# Note on `set -euo pipefail` + `| head -N`:
# every truncating pipeline ends with `|| true`. Without it, when the producer
# writes more than N lines, head closes the pipe early and the producer dies of
# SIGPIPE (exit 141); pipefail then reports the pipeline as failed and `set -e`
# kills the whole test run mid-way. The `|| true` guard makes truncation safe.

set -euo pipefail

SKILL_PATH=""
EXECUTOR="cli"
INCLUDE_MUTATION=0

while getopts ":s:e:m" opt; do
    case "$opt" in
        s) SKILL_PATH="$OPTARG" ;;
        e) EXECUTOR="$OPTARG" ;;
        m) INCLUDE_MUTATION=1 ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

if [ -z "$SKILL_PATH" ]; then
    echo "Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}] [-m]"
    exit 1
fi

# Only CLI and SDK modes are automated; API verification is manual (see references/verification-method.md)
case "$EXECUTOR" in
    cli|sdk) ;;
    *) echo "ERROR: invalid executor '$EXECUTOR' (expected cli|sdk)"; exit 1 ;;
esac

# Prompt the user for explicit confirmation before a mutation test.
# Returns 0 only on an explicit yes.
confirm() {
    local answer
    printf '%s [y/N]: ' "$1"
    read -r answer
    case "${answer:-}" in
        y|Y|yes|YES) return 0 ;;
        *) echo "  -> skipped"; return 1 ;;
    esac
}

# Check that all required environment variables are present (space-separated list).
vars_present() {
    local v missing=0
    for v in $1; do
        if [ -z "${!v:-}" ]; then
            echo "  -> SKIPPED: required env var $v is not set"
            missing=1
        fi
    done
    [ "$missing" -eq 0 ]
}

# SDK mode helper — the hw-cloudrobo-client Python packages must be importable.
# TC-19..TC-27 depend on the SDK; skip gracefully when it is not installed.
sdk_ready() {
    if python3 -c "import cloudrobo_workspace.client, cloudrobo_core.sdk" 2>/dev/null; then
        return 0
    fi
    echo "  -> SKIPPED: hw-cloudrobo-client Python SDK not installed (pip install hw-cloudrobo-client)"
    return 1
}

# ============================================================================
# TC-01..TC-10 — CLI read-only / dry-run test cases
# ============================================================================

test_list_workspaces() {
    echo "=== TC-01: list workspaces ==="
    cloudrobo workspace list 2>&1 | head -20 || true
}

test_list_workspaces_pagination() {
    echo "=== TC-02: list workspaces with pagination ==="
    cloudrobo workspace list --limit 10 --offset 0 2>&1 | head -20 || true
}

test_show_workspace() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-03: show workspace (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-03: show workspace --workspace-id $workspace_id ==="
    cloudrobo workspace show --workspace-id "$workspace_id" 2>&1 | head -20 || true
}

test_create_workspace_dry_run() {
    echo "=== TC-04: create workspace --dry-run ==="
    cloudrobo workspace create --name test-dry-run --default-obs-path obs://bucket/test --dry-run 2>&1 | head -10 || true
}

test_overview() {
    echo "=== TC-05: workspace overview ==="
    cloudrobo workspace overview 2>&1 | head -20 || true
}

test_current() {
    echo "=== TC-06: workspace current ==="
    cloudrobo workspace current 2>&1 | head -10 || true
}

test_list_members() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-07: list-members (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-07: list-members --workspace-id $workspace_id ==="
    cloudrobo workspace list-members --workspace-id "$workspace_id" 2>&1 | head -20 || true
}

test_use_workspace() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-08: workspace use (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-08: workspace use --workspace-id $workspace_id ==="
    cloudrobo workspace use --workspace-id "$workspace_id" 2>&1 | head -10 || true
}

test_update_workspace_dry_run() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-09: update workspace --dry-run (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-09: update workspace --dry-run ==="
    cloudrobo workspace update --workspace-id "$workspace_id" --name test-update --dry-run 2>&1 | head -10 || true
}

test_delete_workspace_dry_run() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-10: delete workspace --dry-run (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-10: delete workspace --dry-run ==="
    cloudrobo workspace delete --workspace-id "$workspace_id" --dry-run 2>&1 | head -10 || true
}

# ============================================================================
# TC-11..TC-18 — CLI mutation test cases (user confirmation required)
# ============================================================================

test_create_workspace() {
    echo "=== TC-11: create workspace ==="
    cloudrobo workspace create --name test-ws --default-obs-path obs://bucket/test \
        --description 'test workspace' --tags 'tag1,tag2' 2>&1 | head -20 || true
}

test_create_workspace_with_members() {
    echo "=== TC-12: create workspace with members ==="
    cloudrobo workspace create --name team-ws --default-obs-path obs://bucket/team \
        --member-list "[{\"user_id\":\"${USER_ID}\",\"role_ids\":[\"${ROLE_ID}\"]}]" 2>&1 | head -20 || true
}

test_update_workspace_name() {
    local workspace_id="${1:-}"
    echo "=== TC-13: update workspace name ==="
    cloudrobo workspace update --workspace-id "$workspace_id" --name updated-name 2>&1 | head -20 || true
}

test_update_workspace_tags() {
    local workspace_id="${1:-}"
    echo "=== TC-14: update workspace tags (full replacement) ==="
    cloudrobo workspace update --workspace-id "$workspace_id" --tags 'new-tag1,new-tag2' 2>&1 | head -20 || true
}

test_add_members() {
    local workspace_id="${1:-}"
    echo "=== TC-15: add members ==="
    cloudrobo workspace add-members --workspace-id "$workspace_id" \
        --member-list "[{\"user_id\":\"${USER_ID}\",\"role_ids\":[\"${ROLE_ID}\"]}]" 2>&1 | head -20 || true
}

test_update_member() {
    local workspace_id="${1:-}"
    echo "=== TC-16: update member roles ==="
    cloudrobo workspace update-member --workspace-id "$workspace_id" \
        --user-id "${USER_ID}" --role-ids "${ROLE_ID}" 2>&1 | head -20 || true
}

test_delete_members() {
    local workspace_id="${1:-}"
    echo "=== TC-17: delete members ==="
    cloudrobo workspace delete-members --workspace-id "$workspace_id" \
        --user-ids "${USER_ID}" 2>&1 | head -20 || true
}

test_delete_workspace() {
    local workspace_id="${1:-}"
    echo "=== TC-18: delete workspace (irreversible) ==="
    cloudrobo workspace delete --workspace-id "$workspace_id" 2>&1 | head -20 || true
}

# ============================================================================
# TC-19..TC-22 — SDK read-only test cases
# ============================================================================

test_list_workspaces_sdk() {
    echo "=== TC-19: list workspaces (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.list_workspaces()
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_show_workspace_sdk() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-20: show workspace (SDK) (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-20: show workspace (SDK) --workspace-id $workspace_id ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.show_workspace('$workspace_id')
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_get_overview_sdk() {
    echo "=== TC-21: get workspace overview (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.get_workspace_overview()
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_list_members_sdk() {
    local workspace_id="${1:-}"
    if [ -z "$workspace_id" ]; then
        echo "=== TC-22: list members (SDK) (SKIPPED - no WORKSPACE_ID) ==="
        return
    fi
    echo "=== TC-22: list members (SDK) --workspace-id $workspace_id ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.list_workspace_members('$workspace_id')
print(str(result)[:500])
" 2>&1 | head -20 || true
}

# ============================================================================
# TC-23..TC-27 — SDK mutation test cases (user confirmation required)
# ============================================================================

test_create_workspace_sdk() {
    echo "=== TC-23: create workspace (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.create_workspace({'name': 'sdk-test', 'default_obs_path': 'obs://bucket/test'})
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_update_workspace_sdk() {
    local workspace_id="${1:-}"
    echo "=== TC-24: update workspace (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.update_workspace('$workspace_id', {'name': 'sdk-updated'})
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_delete_workspace_sdk() {
    local workspace_id="${1:-}"
    echo "=== TC-25: delete workspace (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.delete_workspace('$workspace_id')
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_add_members_sdk() {
    local workspace_id="${1:-}"
    echo "=== TC-26: add members (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.add_workspace_members('$workspace_id', {'member_list': [{'user_id': '${USER_ID}', 'role_ids': ['${ROLE_ID}']}]})
print(str(result)[:500])
" 2>&1 | head -20 || true
}

test_delete_members_sdk() {
    local workspace_id="${1:-}"
    echo "=== TC-27: delete members (SDK) ==="
    python3 -c "
from cloudrobo_workspace.client import WorkspaceClient
from cloudrobo_core.sdk import Config, HttpClient
client = WorkspaceClient(HttpClient(Config()))
result = client.delete_workspace_members('$workspace_id', ['${USER_ID}'])
print(str(result)[:500])
" 2>&1 | head -20 || true
}

# ============================================================================
# TC-28 — End-to-end onboarding flow (CLI mutation, user confirmation required)
# ============================================================================

test_onboarding_flow() {
    echo "=== TC-28: onboarding flow (list -> create -> use -> current) ==="
    local ws_name="onboard-$(date +%s)"
    echo "--- Step 1/4: list existing workspaces ---"
    cloudrobo workspace list 2>&1 | head -10 || true
    echo "--- Step 2/4: create workspace '$ws_name' ---"
    cloudrobo workspace create --name "$ws_name" --default-obs-path "obs://bucket/$ws_name" 2>&1 | head -15 || true
    local created_id
    created_id=$(cloudrobo workspace list 2>/dev/null | grep -oE "\"workspace_id\"[^,]*" | head -1 | grep -oE "[0-9a-fA-F-]{36}" || true)
    if [ -z "$created_id" ]; then
        echo "--- Step 3/4: NOTE: could not auto-detect the created workspace_id; switch manually with: ---"
        echo "  cloudrobo workspace use --workspace-id <id>"
        return
    fi
    echo "--- Step 3/4: switch context (use $created_id) ---"
    cloudrobo workspace use --workspace-id "$created_id" 2>&1 | head -10 || true
    echo "--- Step 4/4: verify active workspace (current) ---"
    cloudrobo workspace current 2>&1 | head -10 || true
}

# ============================================================================
# Main execution
# ============================================================================
echo "=== cloudrobo-workspace Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo ""

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

scan_credentials

echo ""
echo "--- Read-only / dry-run test cases (automatic) ---"
echo ""
if [ "$EXECUTOR" = "cli" ]; then
    test_list_workspaces
    test_list_workspaces_pagination
    test_create_workspace_dry_run
    test_overview
    test_current

    if [ -n "${WORKSPACE_ID:-}" ]; then
        test_show_workspace "$WORKSPACE_ID"
        test_list_members "$WORKSPACE_ID"
        test_use_workspace "$WORKSPACE_ID"
        test_update_workspace_dry_run "$WORKSPACE_ID"
        test_delete_workspace_dry_run "$WORKSPACE_ID"
    else
        echo ""
        echo "NOTE: Set WORKSPACE_ID environment variable to run workspace-specific cases:"
        echo "  WORKSPACE_ID=<workspace-id> bash $0 -s $SKILL_PATH -e cli"
    fi
elif [ "$EXECUTOR" = "sdk" ]; then
    if sdk_ready; then
        test_list_workspaces_sdk
        test_get_overview_sdk
        if [ -n "${WORKSPACE_ID:-}" ]; then
            test_show_workspace_sdk "$WORKSPACE_ID"
            test_list_members_sdk "$WORKSPACE_ID"
        else
            echo ""
            echo "NOTE: Set WORKSPACE_ID environment variable to run workspace-specific SDK cases:"
            echo "  WORKSPACE_ID=<workspace-id> bash $0 -s $SKILL_PATH -e sdk"
        fi
    fi
fi

# ----------------------------------------------------------------------------
# Mutation test cases — only with -m, each case confirmed interactively
# ----------------------------------------------------------------------------
if [ "$INCLUDE_MUTATION" = "1" ]; then
    echo ""
    echo "--- Mutation test cases (TC-11..TC-18, TC-23..TC-28) ---"
    echo "Each mutation case requires explicit confirmation. Answer y to run, anything else to skip."
    echo ""

    if [ "$EXECUTOR" = "cli" ]; then
        if confirm "TC-11 create-workspace: create workspace 'test-ws'?"; then
            test_create_workspace
        fi
        if confirm "TC-12 create-workspace-with-members: create 'team-ws' with members?"; then
            if vars_present "USER_ID ROLE_ID"; then
                test_create_workspace_with_members
            fi
        fi
        if [ -n "${WORKSPACE_ID:-}" ]; then
            if confirm "TC-13 update-workspace-name: rename WORKSPACE_ID to 'updated-name'?"; then
                test_update_workspace_name "$WORKSPACE_ID"
            fi
            if confirm "TC-14 update-workspace-tags: replace tags on WORKSPACE_ID?"; then
                test_update_workspace_tags "$WORKSPACE_ID"
            fi
            if confirm "TC-15 add-members: add USER_ID to WORKSPACE_ID?"; then
                if vars_present "USER_ID ROLE_ID"; then
                    test_add_members "$WORKSPACE_ID"
                fi
            fi
            if confirm "TC-16 update-member: update USER_ID roles in WORKSPACE_ID?"; then
                if vars_present "USER_ID ROLE_ID"; then
                    test_update_member "$WORKSPACE_ID"
                fi
            fi
            if confirm "TC-17 delete-members: remove USER_ID from WORKSPACE_ID?"; then
                if vars_present "USER_ID"; then
                    test_delete_members "$WORKSPACE_ID"
                fi
            fi
            if confirm "TC-18 delete-workspace: DELETE WORKSPACE_ID (irreversible)?"; then
                test_delete_workspace "$WORKSPACE_ID"
            fi
        else
            echo ""
            echo "NOTE: TC-13..TC-18 skipped — set WORKSPACE_ID to run workspace mutation cases."
        fi
        if confirm "TC-28 onboarding-flow: run end-to-end list -> create -> use -> current?"; then
            test_onboarding_flow
        fi
    elif [ "$EXECUTOR" = "sdk" ]; then
        if sdk_ready; then
            if confirm "TC-23 create-workspace-sdk: create 'sdk-test' workspace?"; then
                test_create_workspace_sdk
            fi
            if [ -n "${WORKSPACE_ID:-}" ]; then
                if confirm "TC-24 update-workspace-sdk: rename WORKSPACE_ID to 'sdk-updated'?"; then
                    test_update_workspace_sdk "$WORKSPACE_ID"
                fi
                if confirm "TC-25 delete-workspace-sdk: DELETE WORKSPACE_ID (irreversible)?"; then
                    test_delete_workspace_sdk "$WORKSPACE_ID"
                fi
                if confirm "TC-26 add-members-sdk: add USER_ID to WORKSPACE_ID?"; then
                    if vars_present "USER_ID ROLE_ID"; then
                        test_add_members_sdk "$WORKSPACE_ID"
                    fi
                fi
                if confirm "TC-27 delete-members-sdk: remove USER_ID from WORKSPACE_ID?"; then
                    if vars_present "USER_ID"; then
                        test_delete_members_sdk "$WORKSPACE_ID"
                    fi
                fi
            else
                echo ""
                echo "NOTE: TC-24..TC-27 skipped — set WORKSPACE_ID to run SDK workspace mutation cases."
            fi
        fi
    fi
else
    echo ""
    echo "NOTE: Mutation test cases (TC-11..TC-18, TC-23..TC-28) were NOT executed."
    echo "Re-run with -m to run them interactively (each case prompts for confirmation):"
    echo "  bash $0 -s $SKILL_PATH -e $EXECUTOR -m"
fi

echo ""
echo "=== Test Suite Complete ==="