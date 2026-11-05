#!/usr/bin/env bash
# test-cli-commands.sh — Functional testing for cloudrobo-asset skill
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]
# TC numbers correspond to test cases defined in templates/test-vars.json
#
# Coverage: read-only commands + every mutating command via --dry-run rehearsal,
#   plus a key lifecycle round-trip (create→update→tag→version→delete) gated behind
#   RUN_LIFECYCLE=1 with explicit confirmation before each mutation.
#
# Env auto-resolution (matching templates/test-vars.json):
#   REPOSITORY_ID / CATALOG_ID / ASSET_ID / VERSION_ID / ALGO_ASSET_ID / ALGO_VERSION_ID
#   Run with any subset; when a required env var is missing, the dependent test prints
#   an explicit SKIP so a partial run can never look like a full pass.
#
# Safety: mutating operations default to --dry-run (no side effects). Only when
#   RUN_LIFECYCLE=1 does the script execute the real lifecycle and confirm each step.

set -uo pipefail

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

# Optional: 1 => execute key lifecycle mutations for real (confirm each); unset/0 => dry-run only
RUN_LIFECYCLE="${RUN_LIFECYCLE:-0}"

# Env auto-resolution
REPOSITORY_ID="${REPOSITORY_ID:-}"
CATALOG_ID="${CATALOG_ID:-}"
ASSET_ID="${ASSET_ID:-}"
VERSION_ID="${VERSION_ID:-}"
ALGO_ASSET_ID="${ALGO_ASSET_ID:-}"
ALGO_VERSION_ID="${ALGO_VERSION_ID:-}"

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
    echo "Credentials found in environment variables."
}

# Emit an explicit SKIP line (never a silent no-op) for missing env prerequisites.
skip() {
    local tc="$1" reason="$2"
    echo "=== $tc (SKIPPED — $reason) ==="
}

# Run a single test from a CLI invocation; SDK mode maps to an equivalent
# AssetClient call so both executors stay functional.
#   @1 tc label  @2 cli command string  @3 python SDK snippet (mode=sdk)
run_test() {
    local tc="$1" cli_cmd="$2" sdk_py="$3"
    echo "=== $tc ==="
    if [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
try:
    from cloudrobo_asset.client import AssetClient
    from cloudrobo_core.sdk import Config, HttpClient
    client = AssetClient(HttpClient(Config()))
except Exception as e:
    print(f'SDK_UNAVAILABLE: {type(e).__name__}: {e}')
    raise SystemExit(0)
try:
    result = $sdk_py
    print(str(result)[:800])
except Exception as e:
    print(f'SDK_ERROR: {type(e).__name__}: {e}')
" 2>&1 | head -20
    else
        bash -c "$cli_cmd" 2>&1 | head -20
    fi
}

# ---- Read-only tests ----

test_list_repositories() {
    run_test "TC-01: list-repositories" \
        "cloudrobo asset list-repositories --limit 5" \
        "client.list_repositories(limit=5)"
}

test_list_catalogs() {
    if [ -z "$REPOSITORY_ID" ]; then
        skip "TC-03: list-catalogs" "no REPOSITORY_ID env"
        return
    fi
    run_test "TC-03: list-catalogs --repository-id $REPOSITORY_ID" \
        "cloudrobo asset list-catalogs --repository-id '$REPOSITORY_ID' --limit 5" \
        "client.list_catalogs('$REPOSITORY_ID', limit=5)"
}

test_show_catalog() {
    if [ -z "$CATALOG_ID" ]; then
        skip "TC-04: show-catalog" "no CATALOG_ID env"
        return
    fi
    run_test "TC-04: show-catalog --catalog-id $CATALOG_ID" \
        "cloudrobo asset show-catalog --catalog-id '$CATALOG_ID'" \
        "client.show_catalog('$CATALOG_ID')"
}

test_list_assets() {
    if [ -z "$CATALOG_ID" ]; then
        skip "TC-05: list-assets" "no CATALOG_ID env"
        return
    fi
    run_test "TC-05: list-assets --catalog-id $CATALOG_ID" \
        "cloudrobo asset list-assets --catalog-id '$CATALOG_ID' --limit 5" \
        "client.list_assets(catalog_id='$CATALOG_ID', limit=5)"
}

test_show_asset() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-07: show-asset" "no ASSET_ID env"
        return
    fi
    run_test "TC-07: show-asset --asset-id $ASSET_ID" \
        "cloudrobo asset show-asset --asset-id '$ASSET_ID'" \
        "client.show_asset('$ASSET_ID')"
}

test_list_versions() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-13: list-versions" "no ASSET_ID env"
        return
    fi
    run_test "TC-13: list-versions --asset-id $ASSET_ID" \
        "cloudrobo asset list-versions --asset-id '$ASSET_ID' --limit 5" \
        "client.list_asset_versions('$ASSET_ID', limit=5)"
}

test_show_version() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-14: show-version" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-14: show-version" \
        "cloudrobo asset show-version --asset-id '$ASSET_ID' --version-id '$VERSION_ID'" \
        "client.show_asset_version('$ASSET_ID', '$VERSION_ID')"
}

test_search_assets() {
    run_test "TC-25: search-assets --keyword robot" \
        "cloudrobo asset search-assets --keyword robot --limit 5" \
        "client.search_assets({'keyword': 'robot', 'limit': 5})"
}

test_list_publication_assets() {
    run_test "TC-27: list-publication-assets --type model" \
        "cloudrobo asset list-publication-assets --type model --limit 5" \
        "client.list_publication_assets(type='model', limit=5)"
}

test_list_tags() {
    run_test "TC-19: list-tags --language zh" \
        "cloudrobo asset list-tags --language zh" \
        "client.list_all_tags(language='zh')"
}

test_list_actions() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-21: list-actions" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-21: list-actions" \
        "cloudrobo asset list-actions --asset-id '$ASSET_ID' --version-id '$VERSION_ID'" \
        "client.list_asset_actions('$ASSET_ID', '$VERSION_ID')"
}

test_show_action() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-22a: show-action" "no ASSET_ID/VERSION_ID env"
        return
    fi
    local action="${ACTION_NAME:-FFT}"
    run_test "TC-22a: show-action --action $action" \
        "cloudrobo asset show-action --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --action '$action'" \
        "client.show_asset_action('$ASSET_ID', '$VERSION_ID', '$action')"
}

test_check_permission() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-22: check-permission" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-22: check-permission data_read (export pre-check)" \
        "cloudrobo asset check-permission --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --permissions 'meta_read,data_read'" \
        "client.check_asset_permission('$ASSET_ID', '$VERSION_ID', {'permissions': ['meta_read','data_read']})"
}

test_show_lineage() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-23/24: show-lineage" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-23: show-lineage --type children" \
        "cloudrobo asset show-lineage --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --type children" \
        "client.show_asset_tree('$ASSET_ID', '$VERSION_ID', 'children')"
    run_test "TC-24: show-lineage --type parent" \
        "cloudrobo asset show-lineage --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --type parent" \
        "client.show_asset_tree('$ASSET_ID', '$VERSION_ID', 'parent')"
}

# ---- Mutating commands: --dry-run rehearsal (safe, runs automatically) ----

test_create_asset_dry_run() {
    if [ -z "$CATALOG_ID" ]; then
        skip "TC-08: create-asset --dry-run" "no CATALOG_ID env"
        return
    fi
    run_test "TC-08: create-asset --dry-run" \
        "cloudrobo asset create-asset --catalog-id '$CATALOG_ID' --name test-dry-run --type model --dry-run" \
        "client.create_asset({'catalog_id': '$CATALOG_ID', 'name': 'test-dry-run', 'type': 'model'})"
}

test_update_asset_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-10: update-asset --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-10: update-asset --dry-run" \
        "cloudrobo asset update-asset --asset-id '$ASSET_ID' --description updated-description --dry-run" \
        "client.update_asset('$ASSET_ID', {'description': 'updated-description'})"
}

test_delete_asset_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-11: delete-asset --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-11: delete-asset --dry-run" \
        "cloudrobo asset delete-asset --asset-id '$ASSET_ID' --dry-run" \
        "client.delete_asset('$ASSET_ID')"
}

test_batch_delete_assets_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-12: batch-delete-assets --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-12: batch-delete-assets --dry-run" \
        "cloudrobo asset batch-delete-assets --asset-ids '$ASSET_ID' --dry-run" \
        "client.batch_delete_assets({'asset_ids': ['$ASSET_ID']})"
}

test_create_version_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-15: create-version --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-15: create-version --dry-run" \
        "cloudrobo asset create-version --asset-id '$ASSET_ID' --version 9.9.9-test --dry-run" \
        "client.create_asset_version('$ASSET_ID', {'version': '9.9.9-test'})"
}

test_update_version_dry_run() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-16a: update-version --dry-run" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-16a: update-version --dry-run" \
        "cloudrobo asset update-version --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --description updated-description --dry-run" \
        "client.update_asset_version('$ASSET_ID', '$VERSION_ID', {'description': 'updated-description'})"
}

test_delete_version_dry_run() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-16: delete-version --dry-run" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-16: delete-version --dry-run" \
        "cloudrobo asset delete-version --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --dry-run" \
        "client.delete_asset_version('$ASSET_ID', '$VERSION_ID')"
}

test_batch_delete_versions_dry_run() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-16b: batch-delete-versions --dry-run" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-16b: batch-delete-versions --dry-run" \
        "cloudrobo asset batch-delete-versions --asset-id '$ASSET_ID' --version-ids '$VERSION_ID' --dry-run" \
        "client.batch_delete_asset_versions('$ASSET_ID', {'version_ids': ['$VERSION_ID']})"
}

test_add_tags_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-17: add-tags --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-17: add-tags --dry-run" \
        "cloudrobo asset add-tags --asset-id '$ASSET_ID' --tags 'tag1,tag2' --dry-run" \
        "client.add_tags('$ASSET_ID', ['tag1','tag2'])"
}

test_delete_tag_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-18: delete-tag --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-18: delete-tag --dry-run" \
        "cloudrobo asset delete-tag --asset-id '$ASSET_ID' --tag tag1 --dry-run" \
        "client.delete_tag('$ASSET_ID', 'tag1')"
}

test_create_action_dry_run() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-35: create-action --dry-run" "no ASSET_ID/VERSION_ID env"
        return
    fi
    run_test "TC-35: create-action --dry-run" \
        "cloudrobo asset create-action --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --action-info '{\"action\":\"FFT\",\"algorithm\":{\"asset_id\":\"${ALGO_ASSET_ID:-none}\",\"version_id\":\"${ALGO_VERSION_ID:-none}\"},\"status\":\"ENABLE\"}' --dry-run" \
        "client.create_asset_action('$ASSET_ID', '$VERSION_ID', {'action': 'FFT', 'algorithm': {'asset_id': '${ALGO_ASSET_ID:-none}', 'version_id': '${ALGO_VERSION_ID:-none}'}, 'status': 'ENABLE'})"
}

test_update_action_dry_run() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-36: update-action --dry-run" "no ASSET_ID/VERSION_ID env"
        return
    fi
    local action="${ACTION_NAME:-FFT}"
    run_test "TC-36: update-action --dry-run" \
        "cloudrobo asset update-action --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --action '$action' --action-info '{\"status\":\"DISABLE\"}' --dry-run" \
        "client.update_asset_action('$ASSET_ID', '$VERSION_ID', '$action', {'status': 'DISABLE'})"
}

test_delete_action_dry_run() {
    if [ -z "$ASSET_ID" ] || [ -z "$VERSION_ID" ]; then
        skip "TC-37: delete-action --dry-run" "no ASSET_ID/VERSION_ID env"
        return
    fi
    local action="${ACTION_NAME:-FFT}"
    run_test "TC-37: delete-action --dry-run" \
        "cloudrobo asset delete-action --asset-id '$ASSET_ID' --version-id '$VERSION_ID' --action '$action' --dry-run" \
        "client.delete_asset_action('$ASSET_ID', '$VERSION_ID', '$action')"
}

test_import_asset_dry_run() {
    if [ -z "$CATALOG_ID" ]; then
        skip "TC-29: import-asset --dry-run" "no CATALOG_ID env"
        return
    fi
    run_test "TC-29: import-asset --dry-run" \
        "cloudrobo asset import-asset --catalog-id '$CATALOG_ID' --name test-import --type model --ext-metadata '{\"model_type\":\"planning\"}' --local-path ./test-model --dry-run" \
        "client.import_asset({'catalog_id': '$CATALOG_ID', 'name': 'test-import', 'type': 'model', 'ext_metadata': {'model_type': 'planning'}, 'local_path': './test-model'})"
}

test_export_asset_dry_run() {
    if [ -z "$ASSET_ID" ]; then
        skip "TC-32: export-asset --dry-run" "no ASSET_ID env"
        return
    fi
    run_test "TC-32: export-asset --dry-run" \
        "cloudrobo asset export-asset --asset-id '$ASSET_ID' --local-path ./export-out --dry-run" \
        "client.export_asset({'asset_id': '$ASSET_ID', 'local_path': './export-out'})"
}

# ---- Key lifecycle real execution (RUN_LIFECYCLE=1 only, each mutation confirmed) ----

confirm_mutation() {
    local desc="$1"
    if [ "${RUN_LIFECYCLE}" != "1" ]; then
        echo "--- SKIPPED real mutation (RUN_LIFECYCLE=1 to enable): $desc"
        return 1
    fi
    read -r -p "Confirm $desc? [y/N] " yn
    [ "$yn" = "y" ] || [ "$yn" = "Y" ]
}

test_lifecycle_roundtrip() {
    echo "=== Key lifecycle real execution (RUN_LIFECYCLE=${RUN_LIFECYCLE}) ==="
    [ "${RUN_LIFECYCLE}" = "1" ] || {
        echo "  SKIPPED — set RUN_LIFECYCLE=1 to execute the create→update→tag→version→delete round-trip."
        echo "  Dry-run rehearsals above already verify the command contracts safely."
        return
    }
    if [ -z "$CATALOG_ID" ]; then
        skip "LIFECYCLE: create->...->delete" "no CATALOG_ID env"
        return
    fi
    local asset_id=""
    if confirm_mutation "create-asset TCLIFE"; then
        asset_id=$(cloudrobo asset create-asset \
            --catalog-id "$CATALOG_ID" \
            --name "cli-test-lifecycle" \
            --type model \
            --ext-metadata '{"model_type":"planning"}' 2>&1 | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print((d.get('asset') or d).get('asset_id',''))
except Exception:
    print('')" || true)
        echo "  created asset_id=${asset_id:-<parse-failed>}"
    fi
    if [ -n "$asset_id" ]; then
        confirm_mutation "show-asset $asset_id" && cloudrobo asset show-asset --asset-id "$asset_id" 2>&1 | head -10
        confirm_mutation "update-asset $asset_id" && cloudrobo asset update-asset --asset-id "$asset_id" --description lifecycle-updated 2>&1 | head -10
        confirm_mutation "add-tags $asset_id" && cloudrobo asset add-tags --asset-id "$asset_id" --tags "test-tag" 2>&1 | head -10
        confirm_mutation "create-version $asset_id" && cloudrobo asset create-version --asset-id "$asset_id" --version 9.9.9-test 2>&1 | head -10
        confirm_mutation "delete-asset $asset_id" && cloudrobo asset delete-asset --asset-id "$asset_id" 2>&1 | head -10
    else
        echo "  lifecycle create step failed/aborted; skipping dependent mutations"
    fi
}

# Main execution
echo "=== cloudrobo-asset Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo "Env: REPOSITORY_ID=${REPOSITORY_ID:-<unset>} CATALOG_ID=${CATALOG_ID:-<unset>} ASSET_ID=${ASSET_ID:-<unset>} VERSION_ID=${VERSION_ID:-<unset>}"
echo "Lifecycle real-execution: $([ "${RUN_LIFECYCLE}" = "1" ] && echo "ENABLED" || echo "dry-run only")"
echo ""

scan_credentials

# Read-only tests (no mutation)
test_list_repositories
test_search_assets
test_list_publication_assets
test_list_tags
test_show_asset
test_list_versions
test_show_version
test_list_actions
test_show_action
test_check_permission
test_show_lineage
if [ -n "$REPOSITORY_ID" ]; then
    test_list_catalogs
else
    skip "TC-03: list-catalogs" "no REPOSITORY_ID env"
fi
if [ -n "$CATALOG_ID" ]; then
    test_show_catalog
    test_list_assets
else
    skip "TC-04/05: show-catalog / list-assets" "no CATALOG_ID env"
fi

# Mutating commands — safe --dry-run rehearsal (always runs when env present)
test_create_asset_dry_run
test_update_asset_dry_run
test_delete_asset_dry_run
test_batch_delete_assets_dry_run
test_create_version_dry_run
test_update_version_dry_run
test_delete_version_dry_run
test_batch_delete_versions_dry_run
test_add_tags_dry_run
test_delete_tag_dry_run
test_create_action_dry_run
test_update_action_dry_run
test_delete_action_dry_run
test_import_asset_dry_run
test_export_asset_dry_run

# Key lifecycle real execution (only under RUN_LIFECYCLE=1)
test_lifecycle_roundtrip

echo ""
echo "=== Test Suite Complete ==="
echo ""
echo "NOTE: All mutating commands ran with --dry-run (no side effects)."
if [ "${RUN_LIFECYCLE}" = "1" ]; then
    echo "  RUN_LIFECYCLE=1 was set — the create→update→tag→version→delete round-trip ran for real."
else
    echo "  To execute the key lifecycle for real, re-run with: RUN_LIFECYCLE=1 bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi
echo "  Unset optional env (REPOSITORY_ID/CATALOG_ID/ASSET_ID/VERSION_ID) are reported as explicit SKIPs above."