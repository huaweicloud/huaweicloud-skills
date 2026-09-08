#!/usr/bin/env bash
# test-cli-commands.sh — Functional testing for cloudrobo-asset skill
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]
# TC numbers correspond to test cases defined in templates/test-vars.json
#
# Coverage: 12/29 CLI commands tested (read-only + dry-run only)
# Implemented: list-repositories, list-catalogs, show-catalog, list-assets, show-asset,
#   create-asset(--dry-run), list-versions, list-tags, search-assets,
#   list-publication-assets, import-asset(--dry-run), export-asset(--dry-run)
# Not implemented: update-asset, delete-asset, batch-delete-assets,
#   create-version, show-version, update-version, delete-version, batch-delete-versions,
#   add-tags, delete-tag, list-actions, create-action, show-action, update-action,
#   delete-action, check-permission, show-lineage, import-asset(full), export-asset(full)
# Mutating operations require explicit user confirmation and are not automated.

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
    echo "Credentials found in environment variables."
}

# Test: List repositories
test_list_repositories() {
    echo "=== TC-01: list-repositories ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-repositories --limit 5 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_repositories(limit=5)
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: List catalogs
test_list_catalogs() {
    local repo_id="${1:-}"
    if [ -z "$repo_id" ]; then
        echo "=== TC-03: list-catalogs (SKIPPED - no REPOSITORY_ID) ==="
        return
    fi
    echo "=== TC-03: list-catalogs --repository-id $repo_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-catalogs --repository-id "$repo_id" --limit 5 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_catalogs('$repo_id', limit=5)
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: Show catalog
test_show_catalog() {
    local catalog_id="${1:-}"
    if [ -z "$catalog_id" ]; then
        echo "=== TC-04: show-catalog (SKIPPED - no CATALOG_ID) ==="
        return
    fi
    echo "=== TC-04: show-catalog --catalog-id $catalog_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset show-catalog --catalog-id "$catalog_id" 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.show_catalog('$catalog_id')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: List assets
test_list_assets() {
    local catalog_id="${1:-}"
    if [ -z "$catalog_id" ]; then
        echo "=== TC-05: list-assets (SKIPPED - no CATALOG_ID) ==="
        return
    fi
    echo "=== TC-05: list-assets --catalog-id $catalog_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-assets --catalog-id "$catalog_id" --limit 5 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_assets(catalog_id='$catalog_id', limit=5)
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: Show asset
test_show_asset() {
    local asset_id="${1:-}"
    if [ -z "$asset_id" ]; then
        echo "=== TC-07: show-asset (SKIPPED - no ASSET_ID) ==="
        return
    fi
    echo "=== TC-07: show-asset --asset-id $asset_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset show-asset --asset-id "$asset_id" 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.show_asset('$asset_id')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: Create asset dry-run
test_create_asset_dry_run() {
    local catalog_id="${1:-}"
    if [ -z "$catalog_id" ]; then
        echo "=== TC-08: create-asset --dry-run (SKIPPED - no CATALOG_ID) ==="
        return
    fi
    echo "=== TC-08: create-asset --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset create-asset \
            --catalog-id "$catalog_id" \
            --name test-dry-run \
            --type model \
            --dry-run 2>&1 | head -10
    fi
}

# Test: List versions
test_list_versions() {
    local asset_id="${1:-}"
    if [ -z "$asset_id" ]; then
        echo "=== TC-13: list-versions (SKIPPED - no ASSET_ID) ==="
        return
    fi
    echo "=== TC-13: list-versions --asset-id $asset_id ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-versions --asset-id "$asset_id" --limit 5 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_asset_versions('$asset_id', limit=5)
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: Search assets
test_search_assets() {
    echo "=== TC-25: search-assets --keyword robot ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset search-assets --keyword robot --limit 5 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.search_assets({'keyword': 'robot', 'limit': 5})
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: List publication assets
test_list_publication_assets() {
    echo "=== TC-27: list-publication-assets --type model ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-publication-assets --type model --limit 5 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_publication_assets(type='model', limit=5)
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: List tags
test_list_tags() {
    echo "=== TC-19: list-tags --language zh ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset list-tags --language zh 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_asset.client import AssetClient
from cloudrobo_core.sdk import Config, HttpClient
client = AssetClient(HttpClient(Config()))
result = client.list_all_tags(language='zh')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Test: Import asset dry-run
test_import_asset_dry_run() {
    local catalog_id="${1:-}"
    if [ -z "$catalog_id" ]; then
        echo "=== TC-29: import-asset --dry-run (SKIPPED - no CATALOG_ID) ==="
        return
    fi
    echo "=== TC-29: import-asset --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset import-asset \
            --catalog-id "$catalog_id" \
            --name test-import \
            --type model \
            --ext-metadata '{"model_type":"planning"}' \
            --local-path ./test-model \
            --dry-run 2>&1 | head -10
    fi
}

# Test: Export asset dry-run
test_export_asset_dry_run() {
    local asset_id="${1:-}"
    if [ -z "$asset_id" ]; then
        echo "=== TC-32: export-asset --dry-run (SKIPPED - no ASSET_ID) ==="
        return
    fi
    echo "=== TC-32: export-asset --dry-run ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo asset export-asset \
            --asset-id "$asset_id" \
            --local-path ./export-out \
            --dry-run 2>&1 | head -10
    fi
}

# Main execution
echo "=== cloudrobo-asset Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo ""

scan_credentials

# Execute read-only tests (no mutation)
test_list_repositories
test_search_assets
test_list_publication_assets
test_list_tags
test_create_asset_dry_run "${CATALOG_ID:-}"
test_import_asset_dry_run "${CATALOG_ID:-}"

# Execute catalog-specific tests if CATALOG_ID is provided
if [ -n "${CATALOG_ID:-}" ]; then
    test_list_catalogs "${REPOSITORY_ID:-}"
    test_show_catalog "$CATALOG_ID"
    test_list_assets "$CATALOG_ID"
else
    echo ""
    echo "NOTE: Set CATALOG_ID environment variable to run catalog-specific tests:"
    echo "  CATALOG_ID=<catalog-id> bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi

# Execute asset-specific tests if ASSET_ID is provided
if [ -n "${ASSET_ID:-}" ]; then
    test_show_asset "$ASSET_ID"
    test_list_versions "$ASSET_ID"
    test_export_asset_dry_run "$ASSET_ID"
else
    echo ""
    echo "NOTE: Set ASSET_ID to run asset-specific tests:"
    echo "  ASSET_ID=<asset-id> bash $0 -s $SKILL_PATH -e $EXECUTOR"
fi

echo ""
echo "=== Test Suite Complete ==="
echo ""
echo "NOTE: Mutating operations (create-asset, update-asset, delete-asset,"
echo "batch-delete-assets, create-version, update-version, delete-version,"
echo "batch-delete-versions, add-tags, delete-tag, create-action, update-action,"
echo "delete-action, import-asset, export-asset) require explicit user confirmation"
echo "and are not executed automatically."
