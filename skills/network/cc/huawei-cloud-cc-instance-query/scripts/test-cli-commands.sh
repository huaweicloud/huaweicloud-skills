#!/bin/bash
# Test CLI Commands for huawei-cloud-cc-instance-query skill
# Usage: bash scripts/test-cli-commands.sh <skill-path> --executor cli
# All commands are read-only (GET) — no resources are created or modified.

set -e

SKILL_PATH="${1:-.}"
EXECUTOR="${3:-cli}"

# Default test parameters — override via environment variables
REGION="${HUAWEI_REGION:-cn-north-4}"
DOMAIN_ID="${TEST_DOMAIN_ID:-}"
INSTANCE_ID="${TEST_INSTANCE_ID:-}"
BANDWIDTH_PACKAGE_ID="${TEST_BANDWIDTH_PACKAGE_ID:-}"
INTER_REGION_BW_ID="${TEST_INTER_REGION_BW_ID:-}"
NETWORK_INSTANCE_ID="${TEST_NETWORK_INSTANCE_ID:-}"
ROUTE_ID="${TEST_ROUTE_ID:-}"

if [ -z "$DOMAIN_ID" ]; then
  echo "ERROR: TEST_DOMAIN_ID environment variable is required."
  echo "Set it to your Huawei Cloud Account ID (from IAM → My Credentials → Account ID)."
  exit 1
fi

echo "=========================================="
echo "CC Query Skill — CLI Test Suite"
echo "Region: $REGION"
echo "Domain ID: ${DOMAIN_ID:0:8}..."
echo "Executor: $EXECUTOR"
echo "=========================================="
echo ""

PASS=0
FAIL=0
SKIP=0

run_test() {
  local id="$1"
  local name="$2"
  local cmd="$3"
  echo "--- [$id] $name ---"
  echo "Command: $cmd"
  if eval "$cmd" 2>&1; then
    echo "[$id] PASS ✅"
    PASS=$((PASS + 1))
  else
    echo "[$id] FAIL ❌"
    FAIL=$((FAIL + 1))
  fi
  echo ""
}

skip_test() {
  local id="$1"
  local name="$2"
  local reason="$3"
  echo "--- [$id] $name ---"
  echo "SKIP: $reason"
  SKIP=$((SKIP + 1))
  echo ""
}

# TC-01: List Cloud Connections
run_test "TC-01" "List Cloud Connections" \
  "hcloud CC ListCloudConnections --cli-region=$REGION --domain_id=$DOMAIN_ID --limit=1"

# TC-02: List Bandwidth Packages
run_test "TC-02" "List Bandwidth Packages" \
  "hcloud CC ListBandwidthPackages --cli-region=$REGION --domain_id=$DOMAIN_ID --limit=1"

# TC-03: List Inter-Region Bandwidths
run_test "TC-03" "List Inter-Region Bandwidths" \
  "hcloud CC ListInterRegionBandwidths --cli-region=$REGION --domain_id=$DOMAIN_ID --limit=1"

# TC-04: List Network Instances
run_test "TC-04" "List Network Instances" \
  "hcloud CC ListNetworkInstances --cli-region=$REGION --domain_id=$DOMAIN_ID --limit=1"

# TC-05: List Cloud Connection Routes
run_test "TC-05" "List Cloud Connection Routes" \
  "hcloud CC ListCloudConnectionRoutes --cli-region=$REGION --domain_id=$DOMAIN_ID --limit=1"

# TC-06: Show Cloud Connection (by ID)
if [ -n "$INSTANCE_ID" ]; then
  run_test "TC-06" "Show Cloud Connection" \
    "hcloud CC ShowCloudConnection --cli-region=$REGION --domain_id=$DOMAIN_ID --id=$INSTANCE_ID"
else
  skip_test "TC-06" "Show Cloud Connection" "TEST_INSTANCE_ID not set"
fi

# TC-07: Show Bandwidth Package (by ID)
if [ -n "$BANDWIDTH_PACKAGE_ID" ]; then
  run_test "TC-07" "Show Bandwidth Package" \
    "hcloud CC ShowBandwidthPackage --cli-region=$REGION --domain_id=$DOMAIN_ID --id=$BANDWIDTH_PACKAGE_ID"
else
  skip_test "TC-07" "Show Bandwidth Package" "TEST_BANDWIDTH_PACKAGE_ID not set"
fi

# TC-08: Show Inter-Region Bandwidth (by ID)
if [ -n "$INTER_REGION_BW_ID" ]; then
  run_test "TC-08" "Show Inter-Region Bandwidth" \
    "hcloud CC ShowInterRegionBandwidth --cli-region=$REGION --domain_id=$DOMAIN_ID --id=$INTER_REGION_BW_ID"
else
  skip_test "TC-08" "Show Inter-Region Bandwidth" "TEST_INTER_REGION_BW_ID not set"
fi

# TC-09: Show Network Instance (by ID)
if [ -n "$NETWORK_INSTANCE_ID" ]; then
  run_test "TC-09" "Show Network Instance" \
    "hcloud CC ShowNetworkInstance --cli-region=$REGION --domain_id=$DOMAIN_ID --id=$NETWORK_INSTANCE_ID"
else
  skip_test "TC-09" "Show Network Instance" "TEST_NETWORK_INSTANCE_ID not set"
fi

# TC-10: Show Cloud Connection Route (by ID)
if [ -n "$ROUTE_ID" ]; then
  run_test "TC-10" "Show Cloud Connection Route" \
    "hcloud CC ShowCloudConnectionRoutes --cli-region=$REGION --domain_id=$DOMAIN_ID --id=$ROUTE_ID"
else
  skip_test "TC-10" "Show Cloud Connection Route" "TEST_ROUTE_ID not set"
fi

echo "=========================================="
echo "Test Summary: PASS=$PASS, FAIL=$FAIL, SKIP=$SKIP"
echo "=========================================="
