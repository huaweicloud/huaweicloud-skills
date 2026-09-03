#!/bin/bash
# test-cli-commands.sh - Test LTS CLI commands for the Skill
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} -e {cli|sdk|api}

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

if [[ -z "$SKILL_PATH" ]]; then
  echo "Usage: bash scripts/test-cli-commands.sh -s {skill-path} -e {cli|sdk|api}"
  exit 1
fi

TEST_VARS="$SKILL_PATH/templates/test-defaults.json"
if [[ ! -f "$TEST_VARS" ]]; then
  echo "FATAL: test-defaults.json not found at $TEST_VARS"
  exit 1
fi

REGION=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(d.get('region','cn-north-4'))")
echo "=== LTS Log Inspector Test Suite ==="
echo "Region: $REGION"
echo "Executor: $EXECUTOR"
echo ""

PASS=0
FAIL=0
SKIP=0

run_test() {
  local id="$1"
  local name="$2"
  local cmd="$3"
  local expected="$4"
  local is_mutating="${5:-false}"

  echo "--- $id: $name ---"

  if [[ "$is_mutating" == "true" ]]; then
    echo "SKIP (mutating operation - requires user confirmation)"
    ((SKIP++))
    return
  fi

  # Only allow whitelist commands
  if ! echo "$cmd" | grep -qE '^(hcloud|python3|curl|bash) '; then
    echo "SKIP (command not in whitelist)"
    ((SKIP++))
    return
  fi

  if eval "$cmd" 2>&1 | tee /tmp/lts_test_output.txt | head -20; then
    echo "PASS"
    ((PASS++))
  else
    echo "FAIL"
    ((FAIL++))
  fi
  echo ""
}

# Test cases
run_test "TC-01" "ListLogGroups" \
  "hcloud LTS ListLogGroups --cli-region=$REGION" \
  "Returns list of log groups"

run_test "TC-02" "ListHostGroup" \
  "hcloud LTS ListHostGroup --cli-region=$REGION" \
  "Returns list of host groups"

run_test "TC-03" "ListHost offline" \
  "hcloud LTS ListHost --cli-region=$REGION --filter.host_status=offline" \
  "Returns offline hosts"

run_test "TC-04" "ListHost error" \
  "hcloud LTS ListHost --cli-region=$REGION --filter.host_status=error" \
  "Returns error-state hosts"

run_test "TC-05" "ListAccessConfig" \
  "hcloud LTS ListAccessConfig --cli-region=$REGION" \
  "Returns access configs"

run_test "TC-06" "ListTransfers" \
  "hcloud LTS ListTransfers --cli-region=$REGION --log_transfer_type=OBS" \
  "Returns OBS transfer configs"

run_test "TC-07" "ListTopnTrafficStatistics" \
  "hcloud LTS ListTopnTrafficStatistics --cli-region=$REGION --resource_type=log_stream --topn=5 --start_time=1704067200000 --end_time=1704153600000 --search_list.1=write --sort_by=write --is_desc=true --filter.log_group_id=test" \
  "Returns TOP-N traffic stats (may fail if no data in time range)"

run_test "TC-08" "ListTimeLineTrafficStatistics" \
  "hcloud LTS ListTimeLineTrafficStatistics --cli-region=$REGION --resource_type=tenant --search_type=write --start_time=1704067200000 --end_time=1704153600000 --period=1 --timezone=Asia/Shanghai" \
  "Returns timeline traffic stats"

run_test "TC-09" "CreateTransfer" \
  "hcloud LTS CreateTransfer --cli-region=$REGION --log_group_id=test --log_streams.1.log_stream_id=test --log_transfer_info.log_transfer_type=OBS --log_transfer_info.log_transfer_mode=cycle --log_transfer_info.log_transfer_status=ENABLE --log_transfer_info.log_storage_format=RAW --log_transfer_info.log_transfer_detail.obs_bucket_name=test --log_transfer_info.log_transfer_detail.obs_period=5 --log_transfer_info.log_transfer_detail.obs_period_unit=min" \
  "Creates OBS transfer" \
  "true"

run_test "TC-10" "DeleteTransfer" \
  "hcloud LTS DeleteTransfer --cli-region=$REGION --log_transfer_id=test" \
  "Deletes transfer" \
  "true"

echo "=== Test Summary ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo "SKIP: $SKIP (mutating operations)"
echo "==================="
