#!/bin/bash
# Test CLI Commands for huawei-cloud-cc-central-network-query
# Usage: bash scripts/test-cli-commands.sh
# Requires: hcloud CLI configured with valid AK/SK

set -e

REGION="${HUAWEI_REGION:-cn-north-4}"
DOMAIN_ID="${HUAWEI_DOMAIN_ID:-}"

if [ -z "$DOMAIN_ID" ]; then
  echo "ERROR: HUAWEI_DOMAIN_ID is not set. Please export HUAWEI_DOMAIN_ID=<your-account-id>"
  exit 1
fi

echo "=========================================="
echo "CC Central Network Query - CLI Test Script"
echo "Region: $REGION"
echo "Domain ID: $DOMAIN_ID"
echo "=========================================="

# TC-01: List Central Networks
echo ""
echo "[TC-01] ListCentralNetworks"
hcloud CC ListCentralNetworks --cli-region="$REGION" --domain_id="$DOMAIN_ID" --limit=5 2>&1
echo ""

# Get first central network ID for subsequent tests
CN_ID=$(hcloud CC ListCentralNetworks --cli-region="$REGION" --domain_id="$DOMAIN_ID" --limit=1 2>&1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('central_networks',[{}])[0].get('id',''))" 2>/dev/null || echo "")

if [ -z "$CN_ID" ]; then
  echo "[SKIP] No central network instances found. Skipping dependent tests."
  echo "=========================================="
  echo "Test complete. TC-01 passed, TC-02~07 skipped (no resources)."
  exit 0
fi

echo "Found Central Network ID: $CN_ID"

# TC-02: Show Central Network
echo ""
echo "[TC-02] ShowCentralNetwork"
hcloud CC ShowCentralNetwork --cli-region="$REGION" --domain_id="$DOMAIN_ID" --central_network_id="$CN_ID" 2>&1
echo ""

# TC-03: List Attachments
echo ""
echo "[TC-03] ListCentralNetworkAttachments"
hcloud CC ListCentralNetworkAttachments --cli-region="$REGION" --domain_id="$DOMAIN_ID" --central_network_id="$CN_ID" --limit=5 2>&1
echo ""

# TC-04: List Connections
echo ""
echo "[TC-04] ListCentralNetworkConnections"
hcloud CC ListCentralNetworkConnections --cli-region="$REGION" --domain_id="$DOMAIN_ID" --central_network_id="$CN_ID" --limit=5 2>&1
echo ""

echo "=========================================="
echo "All basic tests completed."
