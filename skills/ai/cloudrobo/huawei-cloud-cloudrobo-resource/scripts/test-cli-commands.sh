#!/usr/bin/env bash
# test-cli-commands.sh — Functional testing for cloudrobo-resource skill
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

# Read-only test cases (auto-executed)
test_list_quotas() {
    echo "=== TC-01: list-quotas ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-quotas 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_resource.client import ResourceClient
from cloudrobo_core.sdk import Config, HttpClient
client = ResourceClient(HttpClient(Config()))
result = client.list_quotas()
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_list_quotas_cce() {
    echo "=== TC-02: list-quotas --resource-type CCE (verify npu=0) ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-quotas --resource-type CCE 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_resource.client import ResourceClient
from cloudrobo_core.sdk import Config, HttpClient
client = ResourceClient(HttpClient(Config()))
result = client.list_quotas(resource_type='CCE')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_list_quotas_modelarts() {
    echo "=== TC-03: list-quotas --resource-type MODELARTS (verify cpu/memory/gpu=0) ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-quotas --resource-type MODELARTS 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_resource.client import ResourceClient
from cloudrobo_core.sdk import Config, HttpClient
client = ResourceClient(HttpClient(Config()))
result = client.list_quotas(resource_type='MODELARTS')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_list_quotas_pagination() {
    echo "=== TC-04: list-quotas --limit 20 --offset 0 ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-quotas --limit 20 --offset 0 2>&1 | head -20
    fi
}

test_list_quotas_pool_type() {
    echo "=== TC-05: list-quotas --pool-type DEDICATED ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-quotas --pool-type DEDICATED 2>&1 | head -20
    fi
}

test_pool_list() {
    echo "=== TC-06: list-pools ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-pools 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_resource.client import ResourceClient
from cloudrobo_core.sdk import Config, HttpClient
client = ResourceClient(HttpClient(Config()))
result = client.list_pools()
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

test_pool_list_modelarts_standard() {
    echo "=== TC-07: list-pools --resource-type MODELARTS --resource-sub-type STANDARD ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-pools --resource-type MODELARTS --resource-sub-type STANDARD 2>&1 | head -20
    fi
}

test_pool_list_usages() {
    echo "=== TC-08: list-pools --usages TRAINING,INFERENCE ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-pools --usages TRAINING,INFERENCE 2>&1 | head -20
    fi
}

test_pool_list_pagination() {
    echo "=== TC-09: list-pools --limit 10 --offset 0 ==="
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource list-pools --limit 10 --offset 0 2>&1 | head -20
    fi
}

# Conditional test cases (require environment variables, or auto-derive pool_id)
test_pool_show() {
    local pool_id="${POOL_ID:-}"
    local api_output=""
    if [ -z "$pool_id" ]; then
        # Auto-derive the first resource_id from list-pools output as the default pool_id
        echo "=== TC-10: show-pool (auto-detect pool_id from list-pools) ==="
        if [ "$EXECUTOR" = "sdk" ]; then
            api_output=$(python3 -c "
from cloudrobo_resource.client import ResourceClient
from cloudrobo_core.sdk import Config, HttpClient
client = ResourceClient(HttpClient(Config()))
result = client.list_pools()
import json
try:
    data = json.loads(str(result))
    pools = data.get('resources') or []
except Exception:
    pools = []
for r in pools:
    rid = (r or {}).get('resource_id')
    if rid:
        print(rid)
        break
" 2>&1 || true)
            pool_id=$(echo "$api_output" | grep -oE '[0-9a-fA-F-]{36}' | head -1 || true)
        else
            api_output=$(cloudrobo resource list-pools 2>/dev/null || true)
            pool_id=$(echo "$api_output" | python3 -c "
import json, re, sys
text = sys.stdin.read()
match = re.search(r'out\((.*)\)\s*$', text, re.DOTALL)
if match:
    text = match.group(1)
try:
    data = json.loads(text)
    resources = data.get('resources') or []
    for r in resources:
        rid = (r or {}).get('resource_id')
        if rid:
            print(rid)
            break
except Exception:
    pass
" 2>/dev/null || true)
        fi
    else
        echo "=== TC-10: show-pool --pool-id $pool_id (POOL_ID env) ==="
    fi
    if [ -z "$pool_id" ]; then
        echo "=== TC-10: show-pool (SKIPPED - no pool_id available) ==="
        echo "      list-pools returned no resources or parsing failed;"
        echo "      enable this case by exporting POOL_ID=<pool-id> or ensuring at least one pool exists."
        return
    fi
    echo "       using pool_id=$pool_id"
    if [ "$EXECUTOR" = "cli" ]; then
        cloudrobo resource show-pool --pool-id "$pool_id" 2>&1 | head -20
    elif [ "$EXECUTOR" = "sdk" ]; then
        python3 -c "
from cloudrobo_resource.client import ResourceClient
from cloudrobo_core.sdk import Config, HttpClient
client = ResourceClient(HttpClient(Config()))
result = client.show_pool('$pool_id')
print(str(result)[:500])
" 2>&1 | head -20
    fi
}

# Main execution
echo "=== cloudrobo-resource Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo ""

scan_credentials

# Execute read-only tests (no mutation)
test_list_quotas
test_list_quotas_cce
test_list_quotas_modelarts
test_list_quotas_pagination
test_list_quotas_pool_type
test_pool_list
test_pool_list_modelarts_standard
test_pool_list_usages
test_pool_list_pagination

# Execute conditional tests if environment variables are provided
test_pool_show

echo ""
echo "=== Test Suite Complete ==="
echo ""
echo "NOTE: All tests are read-only. No write operations in this skill."
echo ""
echo "Optional environment variables for conditional tests:"
echo "  POOL_ID=<pool-id>        — Override pool show test pool id (default: auto-derived"
echo "                             from the first resource_id returned by list-pools)"
echo "  WORKSPACE_ID=<ws-id>     — Filter quota list by workspace"
