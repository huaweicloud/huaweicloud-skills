#!/usr/bin/env bash
# test-cli-commands.sh - functional testing for the huawei-cloud-cloudrobo-dataset skill.
#
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]
#
# Test cases and their variables come from {skill-path}/templates/test-vars.json.
# - Read-only cases (type=read) run automatically.
# - Mutation cases (type=mutation) require explicit confirmation: set
#   CONFIRM_MUTATIONS=1 (they create/delete real assets/tasks).
# - The custom-operator onboarding is pure orchestration (composed from real
#   `cloudrobo asset` / `cloudrobo dataset proc` / `workspace` / `docker` commands),
#   so its read-only cases (dry-run, failure analysis) are covered here too.
#
# Only CLI and SDK executors are automated; API verification is manual
# (see references/verification-method.md).

set -u

SKILL_PATH=""
EXECUTOR="cli"

while [ $# -gt 0 ]; do
  case "$1" in
    -s|--skill|--skill-path) SKILL_PATH="${2:-}"; shift 2 ;;
    -e|--executor) EXECUTOR="${2:-}"; shift 2 ;;
    -h|--help)
      echo "Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$SKILL_PATH" ]; then
  echo "Usage: bash scripts/test-cli-commands.sh -s {skill-path} [-e {cli|sdk}]"
  exit 1
fi

case "$EXECUTOR" in
  cli|sdk) ;;
  *) echo "ERROR: invalid executor '$EXECUTOR' (expected cli|sdk)" >&2; exit 1 ;;
esac

VARS_FILE="$SKILL_PATH/templates/test-vars.json"
if [ ! -f "$VARS_FILE" ]; then
  echo "ERROR: test-vars.json not found at $VARS_FILE" >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required" >&2; exit 1; }

# cli_config_has <key> — true if `cloudrobo config get <key>` reports a stored value
# (the command always exits 0 and prints "<key> 未设置" when the key is not set).
cli_config_has() {
    local out
    out="$(cloudrobo config get "$1" 2>/dev/null)" || return 1
    [ -n "$out" ] && ! printf '%s' "$out" | grep -q '未设置'
}

# Check AK/SK: environment variables first, then `cloudrobo config set ak <ak> sk <sk>`
scan_credentials() {
    local ak="" sk=""
    for var in $(env | grep -iE '^(HUAWEI|HW|HWC).*(_AK|ACCESS_KEY|_SK|SECRET_KEY)' | cut -d= -f1 | sort -u); do
        case "$var" in
            *_AK|*ACCESS_KEY) ak="${!var}" ;;
            *_SK|*SECRET_KEY) sk="${!var}" ;;
        esac
    done
    if [ -n "$ak" ] && [ -n "$sk" ]; then
        echo "Credentials found in environment variables: AK=${ak:0:4}..."
        return
    fi
    if cli_config_has ak && cli_config_has sk; then
        echo "Credentials found in cloudrobo config"
        return
    fi
    echo "ERROR: AK/SK not configured."
    echo "Run 'cloudrobo config set ak <ak> sk <sk>' or set HUAWEI_CLOUD_AK / HUAWEI_CLOUD_SK."
    exit 1
}

echo "=== cloudrobo-dataset Skill Test Suite ==="
echo "Executor: $EXECUTOR"
echo "Skill path: $SKILL_PATH"
echo "Vars: $VARS_FILE"
echo ""

scan_credentials

python3 - "$VARS_FILE" "$EXECUTOR" <<'PY'
import json
import os
import re
import subprocess
import sys

vars_path, executor = sys.argv[1], sys.argv[2]
with open(vars_path, encoding="utf-8") as handle:
    data = json.load(handle)
cases = data.get("test_cases") or data.get("testCases") or []
confirm = os.environ.get("CONFIRM_MUTATIONS") == "1"
env = dict(os.environ)
var_re = re.compile(r"\$\{([A-Z0-9_]+)\}")

passed = failed = skipped = 0
for case in cases:
    cid = case.get("id", "?")
    ctype = case.get("type", "read")
    case_executor = case.get("executor", "cli")

    if case_executor != executor:
        skipped += 1
        continue

    if ctype == "mutation" and not confirm:
        print("=== %s: SKIPPED (mutation - set CONFIRM_MUTATIONS=1 to run) ===" % cid)
        skipped += 1
        continue

    requires = case.get("requires", "")
    req_vars = [r for r in re.split(r"[,\s]+", str(requires)) if r]
    missing = [r for r in req_vars if not env.get(r)]
    if missing:
        print("=== %s: SKIPPED (missing env: %s) ===" % (cid, ", ".join(missing)))
        skipped += 1
        continue

    command = var_re.sub(lambda m: env.get(m.group(1), m.group(0)), case.get("command", ""))
    print("=== %s: %s ===" % (cid, case.get("name", "")))
    print("$ %s" % command)
    try:
        if executor == "sdk":
            rc = subprocess.call(["python3", "-c", command])
        else:
            rc = subprocess.call(command, shell=True)
    except Exception as exc:  # noqa: BLE001
        print("ERROR running %s: %s" % (cid, exc))
        rc = 1

    if rc == 0:
        passed += 1
        print("%s PASS" % cid)
    else:
        failed += 1
        print("%s FAIL (exit %s)" % (cid, rc))
    print("")

print("=== Summary: %d passed, %d failed, %d skipped (executor=%s) ===" % (passed, failed, skipped, executor))
print("")
print("NOTE: Mutating operations require explicit user confirmation (CONFIRM_MUTATIONS=1);")
print("they create/delete real assets and tasks and are skipped by default.")
sys.exit(1 if failed else 0)
PY
