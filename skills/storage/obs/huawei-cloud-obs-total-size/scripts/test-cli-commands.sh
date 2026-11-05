#!/usr/bin/env bash
# test-cli-commands.sh — functional smoke test for huawei-cloud-obs-total-size
set -uo pipefail

SKILL_PATH="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
REGION="${HUAWEI_CLOUD_REGION:-cn-north-4}"
BUCKET="${TEST_OBS_BUCKET:-obs-hd-dev-static}"

pass=0
fail=0
skip=0

SCRIPT="$SKILL_PATH/scripts/query_obs_total_size.py"

run_test() {
    local id="$1" name="$2"
    shift 2
    echo -n "  [$id] $name ... "
    if output=$("$@" 2>&1); then
        echo "PASS"
        pass=$((pass + 1))
    else
        echo "FAIL"
        echo "    Error: $output"
        fail=$((fail + 1))
    fi
}

echo "=== OBS Total Size Skill Tests (region: $REGION, bucket: $BUCKET) ==="
echo

# Prerequisite check
if ! command -v python3 &>/dev/null; then
    echo "SKIP: python3 not available"
    skip=$((skip + 4))
    exit 0
fi

run_test "TC-01" "Help output" python3 "$SCRIPT" --help
run_test "TC-02" "Single bucket size (CLI auto)" python3 "$SCRIPT" --bucket "$BUCKET"
run_test "TC-03" "Single bucket size (SDK)" python3 "$SCRIPT" --bucket "$BUCKET" --executor sdk
run_test "TC-04" "All buckets total (SDK)" python3 "$SCRIPT" --all --executor sdk

echo
echo "=== Results: $pass passed, $fail failed, $skip skipped ==="
if [ "$fail" -gt 0 ]; then
    exit 1
fi
exit 0
