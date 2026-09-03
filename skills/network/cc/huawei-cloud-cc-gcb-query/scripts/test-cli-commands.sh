#!/bin/bash
# Test CLI commands for huawei-cloud-cc-gcb-query skill
# Usage: bash scripts/test-cli-commands.sh <skill-path> --executor cli

set -e

SKILL_PATH="${1:-.}"
EXECUTOR="${3:-cli}"
REGION="${REGION:-cn-north-4}"

# Get domain_id from environment or IAM
if [ -z "$DOMAIN_ID" ]; then
    echo "DOMAIN_ID not set, attempting to get from IAM..."
    DOMAIN_ID=$(hcloud IAM KeystoneListAuthDomains --cli-region=$REGION 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['domains'][0]['id'])" 2>/dev/null || echo "")
    if [ -z "$DOMAIN_ID" ]; then
        echo "ERROR: Could not obtain DOMAIN_ID. Set it manually: export DOMAIN_ID=<your_account_id>"
        exit 1
    fi
    echo "Got DOMAIN_ID: ${DOMAIN_ID:0:8}..."
fi

echo "=========================================="
echo "Testing huawei-cloud-cc-gcb-query (executor: $EXECUTOR)"
echo "Region: $REGION"
echo "=========================================="
echo ""

# TC-01: ListGlobalConnectionBandwidths
echo "[TC-01] ListGlobalConnectionBandwidths"
echo "Command: hcloud CC ListGlobalConnectionBandwidths --cli-region=$REGION --domain_id=\$DOMAIN_ID --limit=2"
TC01_RESULT=$(hcloud CC ListGlobalConnectionBandwidths --cli-region=$REGION --domain_id=$DOMAIN_ID --limit=2 2>&1)
if echo "$TC01_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'globalconnection_bandwidths' in d; assert 'page_info' in d" 2>/dev/null; then
    echo "  PASS - Response contains globalconnection_bandwidths and page_info"
else
    echo "  FAIL - Unexpected response: $(echo "$TC01_RESULT" | head -5)"
fi
echo ""

# TC-02: ListGlobalConnectionBandwidthConfigs
echo "[TC-02] ListGlobalConnectionBandwidthConfigs"
echo "Command: hcloud CC ListGlobalConnectionBandwidthConfigs --cli-region=$REGION --domain_id=\$DOMAIN_ID"
RESULT=$(hcloud CC ListGlobalConnectionBandwidthConfigs --cli-region=$REGION --domain_id=$DOMAIN_ID 2>&1)
if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'configs' in d; c=d['configs']; assert 'quotas' in c; assert 'charge_mode' in c" 2>/dev/null; then
    echo "  PASS - Response contains configs with quotas and charge_mode"
else
    echo "  FAIL - Unexpected response: $(echo "$RESULT" | head -5)"
fi
echo ""

# TC-03: ListSupportBindingConnectionBandwidths
echo "[TC-03] ListSupportBindingConnectionBandwidths (binding_service=CC)"
echo "Command: hcloud CC ListSupportBindingConnectionBandwidths --cli-region=$REGION --domain_id=\$DOMAIN_ID --binding_service=CC --limit=2"
RESULT=$(hcloud CC ListSupportBindingConnectionBandwidths --cli-region=$REGION --domain_id=$DOMAIN_ID --binding_service=CC --limit=2 2>&1)
if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'globalconnection_bandwidths' in d; assert 'page_info' in d" 2>/dev/null; then
    echo "  PASS - Response contains globalconnection_bandwidths and page_info"
else
    echo "  FAIL - Unexpected response: $(echo "$RESULT" | head -5)"
fi
echo ""

# TC-04: ShowGlobalConnectionBandwidth
# Auto-discover GCB ID from TC-01 results; fall back to GCB_ID env var; SKIP if neither available
echo "[TC-04] ShowGlobalConnectionBandwidth"
GCB_ID="${GCB_ID:-}"
if [ -z "$GCB_ID" ]; then
    GCB_ID=$(echo "$TC01_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); bw=d.get('globalconnection_bandwidths',[]); print(bw[0]['id'] if bw else '')" 2>/dev/null || echo "")
fi
if [ -n "$GCB_ID" ]; then
    echo "Command: hcloud CC ShowGlobalConnectionBandwidth --cli-region=$REGION --domain_id=\$DOMAIN_ID --id=$GCB_ID"
    RESULT=$(hcloud CC ShowGlobalConnectionBandwidth --cli-region=$REGION --domain_id=$DOMAIN_ID --id=$GCB_ID 2>&1)
    if echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'globalconnection_bandwidth' in d" 2>/dev/null; then
        echo "  PASS - Response contains globalconnection_bandwidth details"
    else
        echo "  FAIL - Unexpected response: $(echo "$RESULT" | head -5)"
    fi
else
    echo "  SKIP - No GCB ID available (TC-01 returned empty list and GCB_ID env var not set)"
    echo "  To test manually: hcloud CC ShowGlobalConnectionBandwidth --cli-region=$REGION --domain_id=\$DOMAIN_ID --id=<gcb_id>"
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "TC-01: ListGlobalConnectionBandwidths      - tested"
echo "TC-02: ListGlobalConnectionBandwidthConfigs - tested"
echo "TC-03: ListSupportBindingBandwidths        - tested"
echo "TC-04: ShowGlobalConnectionBandwidth       - tested (auto-discovered ID) or skipped (no GCB resources)"
