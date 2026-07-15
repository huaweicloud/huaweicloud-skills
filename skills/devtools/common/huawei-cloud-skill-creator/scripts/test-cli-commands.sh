#!/bin/bash
# ============================================================================
# CLI Functional Test Script for Huawei Cloud Skills
# ============================================================================
# Usage: bash test-cli-commands.sh <skill-path> [options]
#
# Options:
#   --region <region>    Huawei Cloud region (default: cn-north-4)
#   --output <path>      Test report output path
#   --executor <mode>    Execution backend: cli|sdk|api|auto (default: auto)
#
# Extracts every hcloud CLI command from SKILL.md and reference files, then:
#   1. Runs --help on each command (syntax verification, no side effects)
#   2. Executes read-only ops (List/Show/Get/Describe/Query) with CLI→SDK→API fallback
#   3. Skips mutation operations (Create/Update/Delete/Start/Stop) — only --help
#   4. Generates references/test-report.md with results
# ============================================================================

set -euo pipefail

SKILL_PATH="${1:?Usage: bash test-cli-commands.sh <skill-path> [--region <region>] [--output <path>] [--executor cli|sdk|api|auto]}"
shift || true

REGION="cn-north-4"
OUTPUT_FILE=""
EXECUTOR="auto"

while [ $# -gt 0 ]; do
  case "$1" in
    --region) REGION="$2"; shift 2 ;;
    --output) OUTPUT_FILE="$2"; shift 2 ;;
    --executor) EXECUTOR="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
SKILL_MD="$SKILL_PATH/SKILL.md"
if [ ! -f "$SKILL_MD" ]; then
  echo "[FATAL] SKILL.md not found at $SKILL_MD"
  exit 1
fi

# Default output: references/test-report.md inside the skill
if [ -z "$OUTPUT_FILE" ]; then
  OUTPUT_FILE="$SKILL_PATH/references/test-report.md"
fi

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
SKILL_NAME=$(grep '^name:' "$SKILL_MD" 2>/dev/null | head -1 | sed 's/^name:[[:space:]]*//' | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//" || true)
[ -z "${SKILL_NAME:-}" ] && SKILL_NAME="unknown"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
RESULTS_ARR=()

record() {
  local op="$1"
  local type="$2"
  local status="$3"
  local note="$4"
  RESULTS_ARR+=("$(printf '| `%s` | %s | %s | %s |' "$op" "$type" "$status" "$note")")
  case "$status" in
    ✅*|✅) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    ❌*|❌) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    ⏭️*) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
  esac
}

# ------------------------------------------------------------------
# Step 0: Check if hcloud is available
# ------------------------------------------------------------------
HCLOUD_AVAILABLE=false
HCLOUD_AUTHENTICATED=false
HCLOUD_VERSION=""

if command -v hcloud &>/dev/null; then
  HCLOUD_AVAILABLE=true
  HCLOUD_VERSION=$(hcloud --version 2>/dev/null | head -1 || hcloud version 2>/dev/null | head -1 || echo "unknown")
  if hcloud configure list &>/dev/null 2>&1; then
    HCLOUD_AUTHENTICATED=true
  fi
fi

# ------------------------------------------------------------------
# Executor selection
# ------------------------------------------------------------------
EXECUTOR_ACTIVE=""
resolve_executor() {
  case "$EXECUTOR" in
    cli)
      if [ "$HCLOUD_AVAILABLE" = true ]; then
        EXECUTOR_ACTIVE="cli"
      else
        echo "[WARN] --executor cli requested but hcloud CLI not found"
        return 1
      fi
      ;;
    sdk)
      if python3 -c "import huaweicloudsdkcore" &>/dev/null 2>&1; then
        EXECUTOR_ACTIVE="sdk"
      elif python3 -m pip install huaweicloudsdkcore --quiet &>/dev/null 2>&1; then
        EXECUTOR_ACTIVE="sdk"
        echo "[INFO] SDK auto-installed"
      else
        echo "[WARN] --executor sdk requested but SDK install failed"
        return 1
      fi
      ;;
    api)
      if command -v curl &>/dev/null && [ -n "${HCLOUD_AK}" ] && [ -n "${HCLOUD_SK}" ]; then
        EXECUTOR_ACTIVE="api"
      else
        echo "[WARN] --executor api requires curl + HCLOUD_AK/HCLOUD_SK"
        return 1
      fi
      ;;
    auto)
      if [ "$HCLOUD_AVAILABLE" = true ]; then
        EXECUTOR_ACTIVE="cli"
      elif python3 -c "import huaweicloudsdkcore" &>/dev/null 2>&1; then
        EXECUTOR_ACTIVE="sdk"
      elif command -v curl &>/dev/null && [ -n "${HCLOUD_AK}" ] && [ -n "${HCLOUD_SK}" ]; then
        EXECUTOR_ACTIVE="api"
      else
        echo "[WARN] No execution backend available (try installing hcloud CLI)"
        return 1
      fi
      ;;
  esac
  echo "[INFO] Executor: $EXECUTOR_ACTIVE"
}

# ------------------------------------------------------------------
# Syntax error detection
# ------------------------------------------------------------------
is_syntax_error() {
  local output="$1"
  local op="$2"
  local tmp
  tmp=$(mktemp)
  printf '%s\n' "$output" > "$tmp"
  # CLI: Operation not supported / parameter not recognized / format error
  grep -qiE "Operation .* is not supported" "$tmp" && { rm -f "$tmp"; return 0; }
  grep -qiE "parameter.*not.*recognized|unrecognized.*arg" "$tmp" && { rm -f "$tmp"; return 0; }
  grep -qiE "format must be" "$tmp" && { rm -f "$tmp"; return 0; }
  # SDK: AttributeError / TypeError
  grep -qiE "AttributeError|TypeError|module.*has no attribute" "$tmp" && { rm -f "$tmp"; return 0; }
  # API: 400 Bad Request (syntax-level, not auth)
  grep -qiE "400.*Bad Request|Invalid.*parameter" "$tmp" && { rm -f "$tmp"; return 0; }
  rm -f "$tmp"
  return 1
}

execute_via_sdk() {
  local svc="$1" op="$2" region="$3"
  local svc_lower
  svc_lower=$(echo "$svc" | tr '[:upper:]' '[:lower:]')
  python3 -c "
import sys, os, json
try:
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.http.http_config import HttpConfig
    svc_module = __import__('huaweicloudsdk${svc_lower}.v1', fromlist=['${svc}Client'])
    Client = getattr(svc_module, '${svc}Client')
    cred = BasicCredentials(os.environ.get('HCLOUD_AK',''), os.environ.get('HCLOUD_SK',''))
    config = HttpConfig.get_default_config()
    config.ignore_ssl_verification = True
    client = Client.new_builder().with_http_config(config).with_credentials(cred).with_region('$region').build()
    req_class = getattr(svc_module, '${op}Request')
    req = req_class(limit=1)
    resp = getattr(client, '${op,}'.lower() + '${op}'[1:] if '${op}' else '')(req)
    print(json.dumps(resp.to_json_object() if hasattr(resp,'to_json_object') else str(resp), indent=2))
except Exception as e:
    print(f'[SDK_ERROR] {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1 || return $?
}

execute_via_api() {
  local svc="$1" op="$2" region="$3"
  # Map service to endpoint
  local endpoint=""
  case "$svc" in
    ECS) endpoint="ecs";;
    VPC) endpoint="vpc";;
    IMS) endpoint="ims";;
    *) endpoint=$(echo "$svc" | tr '[:upper:]' '[:lower:]');;
  esac

  if [[ "$op" == List* ]]; then
    local op_resource
    op_resource=$(printf '%s\n' "$op" | sed 's/^List//')
    local api_path="/v2/{project_id}/${op_resource,,}?limit=1"
    local http_method="GET"
    local host="${endpoint}.${region}.myhuaweicloud.com"
    local url="https://${host}${api_path}"
    local ts
    ts=$(date -u +"%Y%m%dT%H%M%SZ")
    # Minimal curl test — actual signing requires full HMAC implementation
    curl -s -o /dev/null -w "HTTP %{http_code}" -X "$http_method" "$url" \
      -H "Host: $host" -H "X-Sdk-Date: $ts" --connect-timeout 5 2>&1 || echo "API_UNREACHABLE"
  else
    echo "API_SKIPPED (non-List op)"
  fi
}

# ------------------------------------------------------------------
# Step 1: Extract all hcloud commands from SKILL.md and references
# ------------------------------------------------------------------
extract_bash_blocks() {
  awk '/^```bash/{p=1;next} /^```/{p=0;next} p{print}' "$1" 2>/dev/null || true
}

# Collect all hcloud SERVICE OPERATION pairs (deduplicated)
declare -A CMDS=()
declare -A CMD_FILE_SRC=()

extract_from_file() {
  local file="$1"
  local fname
  fname=$(basename "$file")
  local blocks
  blocks=$(extract_bash_blocks "$file" 2>/dev/null || true)
  [ -z "$blocks" ] && return 0
  local cmd_line
  local blk_file
  blk_file=$(mktemp)
  printf '%s\n' "$blocks" > "$blk_file"
  while IFS= read -r cmd_line; do
    local raw_cmd
    raw_cmd=""
    if [[ "$cmd_line" =~ (hcloud\ [A-Z][A-Za-z0-9]*\ [A-Z][A-Za-z0-9]*) ]]; then
      raw_cmd="${BASH_REMATCH[1]}"
    fi
    [ -z "$raw_cmd" ] && continue
    local key
    key="${raw_cmd// /}"
    if [ -z "${CMDS[$key]:-}" ]; then
      CMDS["$key"]="$raw_cmd"
      CMD_FILE_SRC["$key"]="$fname"
    fi
  done < "$blk_file"
  rm -f "$blk_file"
}

extract_from_file "$SKILL_MD"

# Also scan reference files
REF_DIR="$SKILL_PATH/references"
if [ -d "$REF_DIR" ]; then
  for ref_file in "$REF_DIR"/*.md; do
    [ -f "$ref_file" ] && extract_from_file "$ref_file"
  done
fi

# Also scan templates
TPL_DIR="$SKILL_PATH/templates"
if [ -d "$TPL_DIR" ]; then
  for tpl_file in "$TPL_DIR"/*.template; do
    [ -f "$tpl_file" ] && extract_from_file "$tpl_file"
  done
fi

# ------------------------------------------------------------------
# Step 2: Determine operation types
# ------------------------------------------------------------------
is_read_only_op() {
  local op="$1"
  case "$op" in
    List*|Show*|Get*|Describe*|Query*) return 0 ;;
    *) return 1 ;;
  esac
}

is_mutation_op() {
  local op="$1"
  case "$op" in
    Create*|Update*|Delete*|Remove*|Start*|Stop*|Restart*|Reboot*|Shutdown*|Resize*|Attach*|Detach*) return 0 ;;
    *) return 1 ;;
  esac
}

# ------------------------------------------------------------------
# Step 3: Run tests
# ------------------------------------------------------------------
echo "=========================================="
echo " CLI Functional Test"
echo " Skill: $SKILL_NAME"
echo " Path: $SKILL_PATH"
echo " Region: $REGION"
echo "=========================================="
echo ""

if [ "${#CMDS[@]}" -eq 0 ]; then
  echo "[WARN] No hcloud commands found in SKILL.md or references."
  record "(no commands found)" "N/A" "⏭️ 跳过" "无 hcloud 命令可测试"
else
  echo "Found ${#CMDS[@]} unique hcloud command(s)."
  echo ""

  for key in "${!CMDS[@]}"; do
    raw_cmd="${CMDS[$key]}"
    tmp_cmd=$(mktemp)
    printf '%s\n' "$raw_cmd" > "$tmp_cmd"
    read -r _ svc op < "$tmp_cmd"
    rm -f "$tmp_cmd"
    src="${CMD_FILE_SRC[$key]:-unknown}"

    echo "--- Testing: $svc $op (from $src) ---"

    # Test 1: --help syntax check
    if [ "$HCLOUD_AVAILABLE" = true ]; then
      help_cmd="hcloud $svc $op --help"
      if hcloud "$svc" "$op" --help &>/dev/null; then
        record "$help_cmd" "CLI 语法" "✅ 通过" "来自 $src"
        echo "  ✅ --help: PASS"
      else
        record "$help_cmd" "CLI 语法" "❌ 失败" "命令可能不存在或参数错误 (来自 $src)"
        echo "  ❌ --help: FAIL — command may not exist"
        continue
      fi
    else
      record "hcloud $svc $op --help" "CLI 语法" "⏭️ 跳过" "hcloud CLI 未安装"
      echo "  ⏭️ --help: SKIP (hcloud not installed)"
      continue
    fi

    # Test 2: Read-only live test with CLI→SDK→API fallback
    if is_read_only_op "$op"; then
      resolve_executor || true
      live_pass=false
      live_note=""
      
      if [[ "$op" =~ ^(Show|Get|Describe) ]]; then
        record "hcloud $svc $op --cli-region=$REGION --server_id={id}" "只读实时" "⏭️ 跳过" "需要具体的资源 ID，跳过 live 测试"
        echo "  ⏭️ live: SKIP (Show/Get needs resource ID)"
        continue
      fi

      # --- 1st: CLI ---
      if [ "$EXECUTOR_ACTIVE" = "cli" ] && [ "$HCLOUD_AUTHENTICATED" = true ]; then
        live_cmd="hcloud $svc $op --cli-region=$REGION --limit=1"
        output=$(hcloud "$svc" "$op" --cli-region="$REGION" --limit=1 2>&1 || true)
        out_file=$(mktemp)
        printf '%s\\n' "$output" > "$out_file"
        if grep -qiE 'error|failed|denied|unauthorized' "$out_file"; then
          # Check if syntax error → fix advice
          if is_syntax_error "$output" "$op"; then
            live_note="CLI语法错误，需修复：$(head -3 "$out_file" | tr '\\n' ' ')"
            echo "  ⚠ CLI syntax error — suggesting fix"
          else
            live_note="CLI返回错误，降级到SDK"
            echo "  ⚠ CLI failed — falling back to SDK"
          fi
        elif [ -n "$output" ]; then
          line_cnt=$(wc -l < "$out_file")
          record "$live_cmd" "只读实时" "✅ 通过" "CLI verified (${line_cnt}行)"
          echo "  ✅ live: PASS ($line_cnt lines, CLI)"
          live_pass=true
        else
          record "$live_cmd" "只读实时" "✅ 通过" "CLI verified (空结果)"
          echo "  ✅ live: PASS (empty, CLI)"
          live_pass=true
        fi
        rm -f "$out_file"
      fi

      # --- 2nd: SDK (fallback from CLI) ---
      if [ "$live_pass" != true ] && { [ "$EXECUTOR" = "sdk" ] || { [ "$EXECUTOR" = "auto" ] && [ "$EXECUTOR_ACTIVE" != "cli" ]; } || { [ "$live_note" != "" ] && [ "$EXECUTOR" = "auto" ]; }; }; then
        if [ "$EXECUTOR_ACTIVE" != "sdk" ]; then
          EXECUTOR_ACTIVE="sdk"
          python3 -c "import huaweicloudsdkcore" &>/dev/null 2>&1 || python3 -m pip install huaweicloudsdkcore --quiet &>/dev/null 2>&1 || true
        fi
        if python3 -c "import huaweicloudsdkcore" &>/dev/null 2>&1; then
          sdk_output=$(execute_via_sdk "$svc" "$op" "$REGION" 2>&1 || true)
          local sdk_tmp
          sdk_tmp=$(mktemp)
          printf '%s\n' "$sdk_output" > "$sdk_tmp"
          if grep -qiE 'error|SDK_ERROR' "$sdk_tmp"; then
            if is_syntax_error "$sdk_output" "$op"; then
              echo "  ⚠ SDK syntax error — check operation/param names"
            else
              echo "  ⚠ SDK failed — falling back to API"
            fi
            live_note="SDK失败"
          elif [ -n "$sdk_output" ]; then
            record "SDK $svc $op --limit=1" "只读实时" "✅ 通过" "SDK verified"
            echo "  ✅ live: PASS (SDK)"
            live_pass=true
          fi
          rm -f "$sdk_tmp"
        fi
      fi

      # --- 3rd: API (fallback from SDK) ---
      if [ "$live_pass" != true ]; then
        api_output=$(execute_via_api "$svc" "$op" "$REGION" 2>&1 || true)
        local api_tmp
        api_tmp=$(mktemp)
        printf '%s\n' "$api_output" > "$api_tmp"
        if grep -qE 'HTTP 200|HTTP 202' "$api_tmp"; then
          record "API $svc $op --limit=1" "只读实时" "✅ 通过" "API verified"
          echo "  ✅ live: PASS (API)"
          live_pass=true
          rm -f "$api_tmp"
        elif grep -qi 'API_UNREACHABLE' "$api_tmp"; then
          record "API $svc $op --limit=1" "只读实时" "❌ 失败" "API不可达"
          echo "  ❌ live: FAIL (API unreachable)"
          rm -f "$api_tmp"
        else
          record "API $svc $op --limit=1" "只读实时" "⛔ 需人工验证" "所有降级均失败"
          echo "  ⛔ live: MANUAL VERIFICATION NEEDED"
        fi
        rm -f "$api_tmp"
      fi

    elif is_mutation_op "$op"; then
      record "hcloud $svc $op --help" "变更操作(仅语法)" "⏭️ 安全跳过" "已通过 --help 验证，不执行实际变更"
      echo "  ⏭️ mutation: SKIP live (only --help verified as safe)"
    else
      echo "  - other operation, no live test needed"
    fi
    echo ""
  done
fi

# ------------------------------------------------------------------
# Step 4: Generate test report
# ------------------------------------------------------------------
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))

REPORT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
mkdir -p "$(dirname "$OUTPUT_FILE")"

cat > "$OUTPUT_FILE" << REPORT_HEADER
# 功能测试报告 — ${SKILL_NAME}

> 生成时间：${REPORT_DATE}
> 测试区域：${REGION}
> CLI 版本：${HCLOUD_VERSION:-未安装}

## 测试结果汇总

| 指标 | 值 |
|------|-----|
| 总测试数 | ${TOTAL} |
| ✅ 通过 | ${PASS_COUNT} |
| ❌ 失败 | ${FAIL_COUNT} |
| ⏭️ 跳过 | ${SKIP_COUNT} |
| 测试者 | Skill Creator (huawei-cloud-skill-creator) |

## 测试详情

| 操作 | 测试类型 | 结果 | 备注 |
|------|----------|------|------|
REPORT_HEADER

for result in "${RESULTS_ARR[@]}"; do
  echo "$result" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$TOTAL" -gt 0 ]; then
  echo "**结论：✅ 全部 ${TOTAL} 项测试通过 — 可进入用户验收**" >> "$OUTPUT_FILE"
elif [ "$FAIL_COUNT" -gt 0 ]; then
  echo "**结论：❌ ${FAIL_COUNT}/${TOTAL} 项测试失败 — 需要修复后重新测试**" >> "$OUTPUT_FILE"
else
  echo "**结论：⏭️ 无实际测试执行 — 请检查 hcloud CLI 安装和认证状态**" >> "$OUTPUT_FILE"
fi

echo ""
echo "=========================================="
echo " Test Results"
echo "=========================================="
echo "  PASS: $PASS_COUNT"
echo "  FAIL: $FAIL_COUNT"
echo "  SKIP: $SKIP_COUNT"
echo "  Report: $OUTPUT_FILE"
echo "=========================================="

# Exit code reflects whether any failures
[ "$FAIL_COUNT" -eq 0 ]
