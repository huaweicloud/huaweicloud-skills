#!/bin/bash
# Test CLI Commands for huawei-cloud-lts-manage
# Usage: bash scripts/test-cli-commands.sh
#
# Executes the hcloud commands declared in templates/test-vars.json for real and
# reports actual PASS/FAIL/SKIP based on each command's exit code.
# Placeholders ({region}, {project_id}, ...) are resolved from:
#   1) the "defaults" object in templates/test-vars.json
#   2) environment variables LTS_TEST_<PLACEHOLDER_UPPERCASE> (e.g. LTS_TEST_PROJECT_ID)
# Write/destructive cases pre-marked "SKIP" in test-vars.json are never executed
# (they require explicit user confirmation).

set -uo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEST_VARS="$SKILL_DIR/templates/test-vars.json"

if [ ! -f "$TEST_VARS" ]; then
    echo "FATAL: test-vars.json not found at $TEST_VARS"
    exit 1
fi

echo "=== LTS Skill CLI Test Suite ==="
echo ""

PASS=0
FAIL=0
SKIP=0

# resolve_placeholders <command> -> resolved command on stdout.
# Substitutes {placeholder} tokens using defaults from test-vars.json or
# LTS_TEST_<PLACEHOLDER> env vars. Tokens without a non-empty value are left
# untouched so the caller can flag them as SKIP.
resolve_placeholders() {
  local cmd="$1"
  TEST_VARS="$TEST_VARS" python3 - "$cmd" << 'PYEOF'
import json, os, re, sys
cmd = sys.argv[1]
with open(os.environ["TEST_VARS"], encoding="utf-8") as f:
    data = json.load(f)
defaults = data.get("defaults", {}) or {}
for ph in sorted(set(re.findall(r"\{([a-zA-Z0-9_]+)\}", cmd))):
    env_val = os.environ.get("LTS_TEST_" + ph.upper(), "")
    val = env_val if env_val else defaults.get(ph, "")
    if val:
        cmd = cmd.replace("{" + ph + "}", val)
print(cmd)
PYEOF
}

# has_unresolved <command> — true when a {placeholder} token remains.
has_unresolved() {
  echo "$1" | grep -q '{'
}

TOTAL=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(len(d['test_cases']))")

for i in $(seq 0 $((TOTAL - 1))); do
    TC_ID=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(d['test_cases'][$i]['id'])")
    TC_NAME=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(d['test_cases'][$i]['name'])")
    TC_CMD=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(d['test_cases'][$i]['command'])")
    TC_EXPECTED=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(d['test_cases'][$i]['expected'])")
    TC_RESULT=$(python3 -c "import json; d=json.load(open('$TEST_VARS')); print(d['test_cases'][$i].get('result', 'PENDING'))")

    # Write/destructive operations require explicit user confirmation: never auto-run.
    if [[ "$TC_RESULT" == "SKIP" ]]; then
        echo "[$TC_ID] $TC_NAME ... SKIP (write/destructive - requires user confirmation)"
        SKIP=$((SKIP + 1))
        continue
    fi

    resolved_cmd=$(resolve_placeholders "$TC_CMD")
    if has_unresolved "$resolved_cmd"; then
        echo "[$TC_ID] $TC_NAME ... SKIP (unresolved placeholder, provide LTS_TEST_* env or defaults)"
        echo "  Command: $resolved_cmd"
        SKIP=$((SKIP + 1))
        continue
    fi

    echo "[$TC_ID] $TC_NAME ... running: $resolved_cmd"
    if eval "$resolved_cmd" >/tmp/lts_test_out.txt 2>&1; then
        echo "  Result: PASS (expected: $TC_EXPECTED)"
        PASS=$((PASS + 1))
    else
        rc=$?
        echo "  Result: FAIL (exit=$rc, expected: $TC_EXPECTED)"
        tail -2 /tmp/lts_test_out.txt | sed 's/^/    /'
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "=== Summary: $TOTAL test cases ==="
echo "  PASS: $PASS   FAIL: $FAIL   SKIP: $SKIP"
echo "=== 真实通过率: $PASS/$((PASS + FAIL)) ==="
