#!/usr/bin/env bash
# ============================================================================
# Functional test script for huawei-cloud-account-onboarding (SDK mode)
# Usage: bash scripts/test-cli-commands.sh [--region cn-north-1]
# Runs the two read-only BSS queries and verifies output shape.
# ============================================================================
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="cn-north-1"
PASS=0
FAIL=0

pass() { echo "  ✅ PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "  ❌ FAIL: $1"; FAIL=$((FAIL + 1)); }

usage() {
  echo "Usage: $0 [--region <region>]" >&2
  exit "${1:-0}"
}

# Translate long options (--region/--help) to short options so getopts can
# parse named arguments uniformly; positional args are rejected.
ARGS=()
for arg in "$@"; do
  case "$arg" in
    --region) ARGS+=(-r) ;;
    --region=*) ARGS+=(-r "${arg#--region=}") ;;
    --help) ARGS+=(-h) ;;
    -*) ARGS+=("$arg") ;;
    *) ARGS+=("$arg") ;;
  esac
done
set -- "${ARGS[@]}"

while getopts "r:h" opt; do
  case "$opt" in
    r)
      if [ -z "$OPTARG" ]; then
        echo "❌ --region requires a value" >&2
        usage 1
      fi
      REGION="$OPTARG"
      ;;
    h) usage 0 ;;
    *) usage 1 ;;
  esac
done
shift $((OPTIND - 1))
if [ $# -gt 0 ]; then
  echo "❌ Unexpected positional argument: $1" >&2
  usage 1
fi

echo "=== huawei-cloud-account-onboarding functional test (region=${REGION}) ==="

if ! python3 -c "import huaweicloudsdkbss" 2>/dev/null; then
  echo "  ⚠️  huaweicloudsdkbss not installed, installing..."
  pip install -q huaweicloudsdkbss || { fail "pip install huaweicloudsdkbss"; exit 1; }
fi

if [ -z "${HUAWEICLOUD_SDK_AK:-}" ] && [ -z "${HUAWEI_ACCESS_KEY:-}" ]; then
  echo "  ❌ FAIL: AK/SK not set in environment (HUAWEICLOUD_SDK_AK/HUAWEICLOUD_SDK_SK)"
  exit 1
fi

# TC-01 ShowRealNameAuthStatus
echo "--- TC-01: ShowRealNameAuthStatus ---"
if OUT=$(cd "$SKILL_DIR" && python3 scripts/show_real_name_auth_status.py 2>&1); then
  RC=0
else
  RC=$?
fi
echo "$OUT"
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qE '"verified_status":\s*(-1|0|1|2)'; then
  pass "TC-01 ShowRealNameAuthStatus returns valid verified_status"
else
  fail "TC-01 ShowRealNameAuthStatus (rc=$RC): $OUT"
fi

# TC-02 ShowRealNameAuthQrCode
echo "--- TC-02: ShowRealNameAuthQrCode ---"
if OUT=$(cd "$SKILL_DIR" && python3 scripts/show_real_name_auth_qr_code.py 2>&1); then
  RC=0
else
  RC=$?
fi
echo "$OUT" | sed -E 's#("qr_code_url": "https[^"]{20})[^"]*#\1...#'
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qE '"qr_code_url":\s*"https://'; then
  pass "TC-02 ShowRealNameAuthQrCode returns https QR URL"
else
  fail "TC-02 ShowRealNameAuthQrCode (rc=$RC): $OUT"
fi

echo ""
echo "Result: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1