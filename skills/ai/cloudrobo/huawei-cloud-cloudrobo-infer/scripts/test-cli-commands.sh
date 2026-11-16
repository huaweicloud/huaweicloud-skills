#!/bin/bash
# Test script for cloudrobo-infer skill
# Usage: bash scripts/test-cli-commands.sh [-w workspace_id]
#
# Behaviour:
#   1) One-time PREFLIGHT — CLI present, `infer` subcommand registered, AK/SK present.
#      Region is reported when configured (client default otherwise). Any failure prints a
#      Chinese hint and exits 1 immediately.
#   2) Negative cases first (client-side validation only): they MUST exit non-zero.
#   3) Read-only + dry-run cases run in one batch (no sleeps, no prompts).
#   4) Mutating cases (create / start / stop / update / delete) are never auto-run — they are
#      reported as SKIP.
#   5) Every case is scored; failures are collected and the script exits non-zero if any case
#      failed. No `|| echo` swallowing: a failing command fails the case.
#
# Optional env vars:
#   WORKSPACE_ID / -w  - workspace for list/create (create/list are workspace-scoped)
#   MODEL_ID           - model asset id to deploy (for dry-run create)
#   MODEL_VERSION_ID   - model version id to deploy (for dry-run create)
#   FLAVOR             - compute flavor (for dry-run create)
#   POOL_ID            - compute pool id, e.g. pool-<resource_id> (dry-run create)
#   POOL_TYPE          - SHARED / DEDICATED (default SHARED)
#   SERVICE_ID         - existing service id (for show / list-logs / wait-deploy)
#   WAIT_TIMEOUT       - wait-deploy timeout seconds (default 60 in this script)
#   OUT_LINES          - max output lines echoed per case (default 8, keeps context small)

set -uo pipefail

WORKSPACE_ID="${WORKSPACE_ID:-}"
while getopts ":w:h" opt; do
    case "$opt" in
        w) WORKSPACE_ID="$OPTARG" ;;
        h) sed -n '2,30p' "$0"; exit 0 ;;
        \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
        :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
done

WORKSPACE_ID=${WORKSPACE_ID:-}
MODEL_ID=${MODEL_ID:-}
MODEL_VERSION_ID=${MODEL_VERSION_ID:-}
FLAVOR=${FLAVOR:-}
POOL_ID=${POOL_ID:-}
POOL_TYPE=${POOL_TYPE:-SHARED}
SERVICE_ID=${SERVICE_ID:-}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-60}
OUT_LINES=${OUT_LINES:-8}

PASS=0
FAIL=0
SKIP=0
FAILED_CASES=()
TMPDIR_RUN=$(mktemp -d "${TMPDIR:-/tmp}/cloudrobo-infer-tests.XXXXXX") || {
    echo "无法创建临时目录，测试终止。" >&2; exit 1; }
trap 'rm -rf "$TMPDIR_RUN"' EXIT

# ---------------------------------------------------------------- preflight
echo "=== cloudrobo-infer preflight ==="

command -v cloudrobo >/dev/null 2>&1 || {
    echo "前置检查失败：未检测到 cloudrobo 命令。请安装聚合客户端 CLI（pip install hw-cloudrobo-client），详见 references/cli-installation-guide.md。" >&2
    exit 2
}

if ! cloudrobo infer --help >/dev/null 2>&1; then
    echo "前置检查失败：cloudrobo infer 子命令不可用。请安装或升级 hw-cloudrobo-client（聚合包，已含推理模块）；cloudrobo --help 可确认已注册命令。" >&2
    exit 2
fi

if ! cloudrobo asset --help >/dev/null 2>&1; then
    echo "前置检查失败：cloudrobo asset 命令组不可用（形如 Error: No such command asset），说明只装了推理模块，模型/资源解析无法进行。请改装聚合客户端 pip install hw-cloudrobo-client 后重试。" >&2
    exit 2
fi

USER_CONFIG="${HOME}/.cloudrobo/config.yaml"
HAS_CREDS=0
if [ -n "${HUAWEI_CLOUD_AK:-}" ] && [ -n "${HUAWEI_CLOUD_SK:-}" ]; then
    HAS_CREDS=1
elif [ -f "$USER_CONFIG" ]; then
    # Accept either an encrypted (ak_enc) or a plain ak entry; empty quotes ("", '') do not count.
    CFG_VALUE=$(awk '
        /^[[:space:]]*(ak_enc|ak):[[:space:]]*/ {
            v = $0
            sub(/^[[:space:]]*(ak_enc|ak):[[:space:]]*/, "", v)
            gsub(/["\047[:space:]]/, "", v)
            if (length(v) > 0) { print v; exit }
        }' "$USER_CONFIG" 2>/dev/null)
    [ -n "${CFG_VALUE:-}" ] && HAS_CREDS=1
fi
if [ "$HAS_CREDS" -ne 1 ]; then
    echo "前置检查失败：未找到 AK/SK。请 export HUAWEI_CLOUD_AK / HUAWEI_CLOUD_SK，或执行 cloudrobo config set ak <ak> sk <sk> 后重试。" >&2
    exit 2
fi

REGION=""
if [ -f "$USER_CONFIG" ]; then
    REGION=$(cloudrobo config get region 2>/dev/null | tr -d '[:space:]' || true)
fi
if [ -z "$REGION" ]; then
    echo "提示：未在用户配置中读到 region，将使用客户端默认 cn-southwest-2；如需切换：cloudrobo config set region <region>。"
else
    echo "Region: $REGION"
fi
echo ""

# ---------------------------------------------------------------- helpers
# run_case <id> <expect: zero|nonzero> <label> <command...>
run_case() {
    local id="$1" expect="$2" label="$3"; shift 3
    local out="$TMPDIR_RUN/$id.log"
    echo "[$id] $label"
    "$@" >"$out" 2>&1
    local rc=$?
    if { [ "$expect" = "zero" ] && [ "$rc" -eq 0 ]; } || { [ "$expect" = "nonzero" ] && [ "$rc" -ne 0 ]; }; then
        echo "  PASS (exit=$rc, expected $expect)"
        PASS=$((PASS + 1))
        [ "$OUT_LINES" -gt 0 ] && sed -n "1,${OUT_LINES}p" "$out" | sed 's/^/  /'
    else
        echo "  FAIL (exit=$rc, expected $expect)"
        FAIL=$((FAIL + 1))
        FAILED_CASES+=("$id: $label")
        sed -n "1,${OUT_LINES}p" "$out" | sed 's/^/  /'
    fi
    echo ""
}

# run_case_reject <id> <regex> <label> <command...>
# Expects a non-zero exit AND the client-side error text to match <regex>. Used for
# Click's required-option validation, so the case cannot pass on an unrelated backend
# error (e.g. 403) that happens to also exit non-zero.
run_case_reject() {
    local id="$1" pattern="$2" label="$3"; shift 3
    local out="$TMPDIR_RUN/$id.log"
    echo "[$id] $label"
    "$@" >"$out" 2>&1
    local rc=$?
    if [ "$rc" -ne 0 ] && grep -qiE -- "$pattern" "$out"; then
        echo "  PASS (exit=$rc, expected client-side error text matched)"
        PASS=$((PASS + 1))
        [ "$OUT_LINES" -gt 0 ] && sed -n "1,${OUT_LINES}p" "$out" | sed 's/^/  /'
    else
        echo "  FAIL (exit=$rc, expected non-zero exit + error text /$pattern/ not matched)"
        FAIL=$((FAIL + 1))
        FAILED_CASES+=("$id: $label")
        sed -n "1,${OUT_LINES}p" "$out" | sed 's/^/  /'
    fi
    echo ""
}

skip_case() {
    echo "[$1] $2 ... SKIP ($3)"
    SKIP=$((SKIP + 1))
    echo ""
}

# ---------------------------------------------------------------- negative cases
# These are validation cases: success means the CLI rejects the input (non-zero exit).
# They exercise client-side validators only and never reach the backend.
echo "=== Negative cases (EXPECT-FAIL, exit != 0) ==="

run_case NEG-1 nonzero "TC-13 / TC-F-34 / TC-F-35: path traversal service_id is rejected" \
    cloudrobo infer show --service-id "../../etc/hosts"

run_case NEG-2 nonzero "TC-12: malformed --envs-json is rejected" \
    cloudrobo infer create --name xyz --flavor f \
    --model-json '{"model_id":"m","model_version_id":"mv"}' --workspace-id w \
    --pool-type SHARED --envs-json "not-json"

# NEG-3 / NEG-4 hit Click's own required-option validation (missing --name / --model-json),
# so they never reach the backend (no 403/405 masking) and the assertion can pin the message.
run_case_reject NEG-3 "Missing option '--name'|Missing option \"--name\"" \
    "extra: missing client-required --name is rejected by Click" \
    cloudrobo infer create --flavor f \
    --model-json '{"model_id":"m","model_version_id":"mv"}' --pool-type SHARED \
    --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'

run_case_reject NEG-4 "Missing option '--model-json'|Missing option \"--model-json\"" \
    "extra: missing client-required --model-json is rejected by Click" \
    cloudrobo infer create --name xyz --flavor f --pool-type SHARED \
    --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}'

# ---------------------------------------------------------------- read-only batch
echo "=== Read-only batch ==="

if [ -n "$WORKSPACE_ID" ]; then
    run_case RO-1 zero "list services in workspace $WORKSPACE_ID" \
        cloudrobo infer list --workspace-id "$WORKSPACE_ID" --limit 20
else
    skip_case RO-1 "list services" "no WORKSPACE_ID (run with -w <workspace_id>)"
fi

if [ -n "$SERVICE_ID" ]; then
    run_case RO-2 zero "show service $SERVICE_ID" cloudrobo infer show --service-id "$SERVICE_ID"
    END_MS=$(date +%s%3N 2>/dev/null || echo "0")
    START_MS=$(( END_MS - 3600000 ))
    run_case RO-3 zero "list logs (ms timestamps)" \
        cloudrobo infer list-logs --service-id "$SERVICE_ID" \
        --start-time "$START_MS" --end-time "$END_MS" --limit 50
    run_case RO-4 zero "wait-deploy (client-side polling)" \
        cloudrobo infer wait-deploy --service-id "$SERVICE_ID" --timeout "$WAIT_TIMEOUT"
else
    skip_case RO-2 "show service" "no SERVICE_ID"
    skip_case RO-3 "list logs" "no SERVICE_ID"
    skip_case RO-4 "wait-deploy" "no SERVICE_ID"
fi

# ---------------------------------------------------------------- dry-run batch (no cost)
echo "=== Dry-run batch (no resource created) ==="

if [ -n "$MODEL_ID" ] && [ -n "$MODEL_VERSION_ID" ] && [ -n "$FLAVOR" ] && [ -n "$WORKSPACE_ID" ]; then
    DRYRUN_ARGS=(cloudrobo infer create --name verify-infer --flavor "$FLAVOR"
        --model-json "{\"model_id\": \"$MODEL_ID\", \"model_version_id\": \"$MODEL_VERSION_ID\"}"
        --workspace-id "$WORKSPACE_ID" --pool-type "$POOL_TYPE"
        --stop-schedule-json '{"duration": 60, "time_unit": "MINUTES"}' --dry-run)
    [ -n "$POOL_ID" ] && DRYRUN_ARGS+=(--pool-id "$POOL_ID")
    run_case DR-1 zero "dry-run create validates parameter assembly" "${DRYRUN_ARGS[@]}"
else
    skip_case DR-1 "dry-run create" "MODEL_ID, MODEL_VERSION_ID, FLAVOR and WORKSPACE_ID are required"
fi

# ---------------------------------------------------------------- mutating cases
# Never auto-run: these create / change / delete real cloud resources.
skip_case MUT-1 "create/start/stop/update/delete lifecycle" \
    "mutating operations require explicit user confirmation — run them from SKILL.md manually"

# ---------------------------------------------------------------- summary
TOTAL=$((PASS + FAIL))
echo "=== Summary: $TOTAL executed, $SKIP skipped ==="
echo "  PASS: $PASS   FAIL: $FAIL   SKIP: $SKIP"
if [ "$FAIL" -gt 0 ]; then
    echo "  失败用例:" >&2
    for c in "${FAILED_CASES[@]}"; do echo "    - $c" >&2; done
    echo "结果：失败 $FAIL 项，请按上面的报错逐条修正后重跑。" >&2
    exit 1
fi
if [ "$TOTAL" -eq 0 ]; then
    echo "结果：没有任何用例被执行，请检查输入参数。" >&2
    exit 1
fi
echo "结果：全部执行的用例通过（跳过项需提供对应输入或人工确认）。"
exit 0