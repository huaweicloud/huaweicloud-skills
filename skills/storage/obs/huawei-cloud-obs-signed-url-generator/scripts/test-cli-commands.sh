#!/bin/bash
# test-cli-commands.sh — Test script for huawei-cloud-obs-signed-url-generator skill
# Runs test cases defined in templates/test-vars.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
TEST_VARS="$SKILL_DIR/templates/test-vars.json"

usage() {
    echo "Usage: $(basename "$0") -s <skill-path> [-e <cli|sdk|api|auto>]"
    exit 0
}

while getopts "s:e:h-:" opt; do
    case "$opt" in
        s) TEST_SKILL_PATH="$OPTARG" ;;
        e) EXEC_MODE="$OPTARG" ;;
        h) usage ;;
        -) case "${OPTARG}" in
               help) usage ;;
               *) echo "Unknown option: --${OPTARG}" >&2; exit 1 ;;
           esac ;;
        \?) echo "Unknown option" >&2; exit 1 ;;
    esac
done

# Use independent variable name to avoid conflict with orchestrator's SKILL_PATH env var
if [ -z "${TEST_SKILL_PATH:-}" ]; then
    TEST_SKILL_PATH="$SKILL_DIR"
fi

if [ ! -f "$TEST_VARS" ]; then
    echo "FATAL: test-vars.json not found at $TEST_VARS"
    exit 1
fi

echo "=== OBS Signed URL Generator Test Suite ==="
echo "Skill path: $TEST_SKILL_PATH"
echo "Test vars:  $TEST_VARS"
echo ""

# Run tests using Python with bash subprocess
python3 - "$TEST_SKILL_PATH" "$TEST_VARS" <<'PYEOF'
import json
import os
import subprocess
import sys

skill_path = sys.argv[1]
test_vars_path = sys.argv[2]

# --- Pre-check: AK/SK environment variables (aligned with generate_signed_url.py) ---
AK_VARS = ["ACCESS_KEY_ID", "OBS_ACCESS_KEY_ID", "HUAWEICLOUD_SDK_AK", "HW_ACCESS_KEY"]
SK_VARS = ["SECRET_ACCESS_KEY", "OBS_SECRET_ACCESS_KEY", "HUAWEICLOUD_SDK_SK", "HW_SECRET_KEY"]

ak_present = any(os.getenv(v) for v in AK_VARS)
sk_present = any(os.getenv(v) for v in SK_VARS)
credentials_available = ak_present and sk_present

if not credentials_available:
    missing = []
    if not ak_present:
        missing.append("AK (try: ACCESS_KEY_ID, OBS_ACCESS_KEY_ID, HUAWEICLOUD_SDK_AK)")
    if not sk_present:
        missing.append("SK (try: SECRET_ACCESS_KEY, OBS_SECRET_ACCESS_KEY, HUAWEICLOUD_SDK_SK)")
    print("WARNING: OBS credentials not found in environment variables.")
    print(f"  Missing: {', '.join(missing)}")
    print("  Tests requiring credentials (TC-06 ~ TC-11) will be SKIP with explicit reason.")
    print("  To run all tests, set environment variables first, e.g.:")
    print("    export ACCESS_KEY_ID=<your-ak>")
    print("    export SECRET_ACCESS_KEY=<your-sk>")
    print("")

# Patterns that indicate the test actually invokes generate_signed_url.py execution
# (not syntax checks like py_compile which don't need credentials)
# Match: direct CLI invocation with --flags, or script path followed by space+flag
CREDENTIAL_PATTERNS = [
    "generate_signed_url.py --",       # direct CLI invocation with args
]

with open(test_vars_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", [])
passed = 0
failed = 0
skipped = 0

for tc in test_cases:
    tc_id = tc.get("id", "?")
    tc_name = tc.get("name", "unnamed")
    tc_cmd = tc.get("command", "")
    tc_expected = tc.get("expected", "")
    tc_skip = tc.get("skip", False)

    print(f"\n--- {tc_id}: {tc_name} ---")

    if tc_skip:
        print(f"  SKIP: {tc.get('skip_reason', 'manually skipped')}")
        skipped += 1
        continue

    # Pre-check: skip credential-dependent tests if AK/SK not set
    needs_credentials = any(p in tc_cmd for p in CREDENTIAL_PATTERNS)
    if needs_credentials and not credentials_available:
        print(f"  SKIP: AK/SK environment variables not set — cannot generate signed URL")
        print(f"        Set ACCESS_KEY_ID and SECRET_ACCESS_KEY to run this test")
        skipped += 1
        continue

    # Resolve $PWD to absolute skill_path
    resolved_cmd = tc_cmd.replace("$PWD", skill_path)

    # Only allow whitelisted command prefixes
    stripped = resolved_cmd.strip()
    if not stripped.startswith(("python3", "python", "bash", "curl", "hcloud")):
        print(f"  FAIL: command not in whitelist")
        failed += 1
        continue

    # Execute via bash -c for consistent shell behavior
    try:
        result = subprocess.run(
            ["bash", "-c", resolved_cmd],
            cwd=skill_path,
            capture_output=True,
            timeout=30,
        )
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        if result.returncode == 0:
            if stdout:
                display = stdout[:200] + "..." if len(stdout) > 200 else stdout
                print(f"  PASS (output: {display})")
            else:
                print(f"  PASS")
            passed += 1
        else:
            # Display full stderr (up to 500 chars) for better error diagnosis
            err = stderr[:500] if stderr else "(no stderr output)"
            print(f"  FAIL (exit={result.returncode}): {err}")
            failed += 1
    except subprocess.TimeoutExpired:
        print(f"  FAIL: timeout (30s)")
        failed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1

print(f"\n=== Summary ===")
print(f"Total: {len(test_cases)} | PASS: {passed} | FAIL: {failed} | SKIP: {skipped}")
if skipped > 0 and not credentials_available:
    print(f"\nNOTE: {skipped} test(s) skipped due to missing AK/SK credentials.")
    print(f"      Set ACCESS_KEY_ID and SECRET_ACCESS_KEY environment variables to run all tests.")
sys.exit(0 if failed == 0 else 1)
PYEOF
