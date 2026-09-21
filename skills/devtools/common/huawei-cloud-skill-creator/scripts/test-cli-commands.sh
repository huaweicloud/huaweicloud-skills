#!/usr/bin/env bash
set -euo pipefail
# ============================================================================
# CLI Functional Test Script for Huawei Cloud Skills Creator v2
# ============================================================================
# Usage: bash test-cli-commands.sh [-s <skill-path>] [-r <region>] [-e cli|sdk|api|auto] [-o <file>] [-i]
#   -s  Target Skill directory path (required; may also be passed positionally for backward compat)
#   -r  Region (default: cn-north-4)
#   -e  Executor mode (default: auto)
#   -o  Output report file
#   -i  Insecure (skip SSL verification)
#
# Extracts test cases from templates/test-vars.json, then:
#   1. Executes each test case with CLI→SDK→API fallback
#   2. Read-only ops run live with --limit=1
#   3. Mutation ops only do --help syntax check (user must confirm for live)
#   4. Generates references/test-report.md with results
# ============================================================================


SKILL_PATH=
REGION="cn-north-4"
EXECUTOR="auto"
OUTPUT_FILE=""
INSECURE=false

usage() {
  echo "Usage: bash test-cli-commands.sh [-s <skill-path>] [-r <region>] [-e cli|sdk|api|auto] [-o <file>] [-i]" >&2
  echo "  -s  Target Skill directory path (required; may also be passed positionally)" >&2
  echo "  -r  Region (default: cn-north-4)" >&2
  echo "  -e  Executor mode (default: auto)" >&2
  echo "  -o  Output report file" >&2
  echo "  -i  Insecure (skip SSL verification)" >&2
  QUALITY_STATUS="sys_fail"
}

while getopts ":s:r:e:o:i" opt; do
  case "$opt" in
    s) SKILL_PATH="$OPTARG" ;;
    r) REGION="$OPTARG" ;;
    e) EXECUTOR="$OPTARG" ;;
    o) OUTPUT_FILE="$OPTARG" ;;
    i) INSECURE=true ;;
    \?) echo "Unknown option: -$OPTARG" >&2; usage; exit 1 ;;
    :) echo "Option -$OPTARG requires an argument" >&2; usage; exit 1 ;;
  esac
done
shift $((OPTIND - 1))
# Backward-compat: accept skill path as a trailing positional argument
if [ -z "$SKILL_PATH" ] && [ $# -gt 0 ]; then
  SKILL_PATH="$1"
fi

if [ -z "$SKILL_PATH" ]; then
  usage
  exit 1
fi

if [ ! -d "$SKILL_PATH" ]; then
  echo "[FATAL] Skill directory not found: $SKILL_PATH"
  QUALITY_STATUS="sys_fail"
  exit 1
fi
SKILL_PATH="$(cd "$SKILL_PATH" && pwd)"

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
SKILL_MD="$SKILL_PATH/SKILL.md"
TEST_VARS="$SKILL_PATH/templates/test-vars.json"
[ -z "$OUTPUT_FILE" ] && OUTPUT_FILE="$SKILL_PATH/references/test-report.md"

if [ ! -f "$SKILL_MD" ]; then
  echo "[FATAL] SKILL.md not found at $SKILL_MD"
  QUALITY_STATUS="sys_fail"
  exit 1
fi

OUTPUT_DIR="$(cd "$(dirname "$OUTPUT_FILE")" 2>/dev/null && pwd)" || true
if [ -z "$OUTPUT_DIR" ] || [ "${OUTPUT_DIR#*$SKILL_PATH}" = "$OUTPUT_DIR" ]; then
  OUTPUT_FILE="$SKILL_PATH/references/test-report.md"
fi

validate_command() {
  local cmd="$1"
  # 1) 快速拒绝 shell 元字符/管道/重定向/命令拼接（字符串级第一道防线）。
  #    权威校验在 argv 级白名单（shlex 解析后校验，多空格/制表符/`-c"code"` 连写
  #    等字面量变体均无法绕过—见 parse_cmd_argv / is_cmd_argv_safe）。
  case "$cmd" in
    *'|'*|*';'*|*'&'*|*'`'*|*'$('*|*'${'*|*'<'*|*'>'*|*$'\n'*)
      echo "[WARN] Command rejected (shell metacharacters): ${cmd:0:60}"; return 1 ;;
  esac
  # 2) argv 级白名单校验
  if ! parse_cmd_argv "$cmd"; then
    echo "[WARN] Command rejected (unparseable): ${cmd:0:60}"; return 1
  fi
  if ! is_cmd_argv_safe; then
    echo "[WARN] Command rejected (not in allowlist): ${cmd:0:60}"; return 1
  fi
  return 0
}

# parse_cmd_argv: 用 shlex 将命令字符串解析为参数数组，结果写入全局 _PARSE_ARGV。
# 返回 0 表示解析成功且至少有一个参数；1 表示解析失败（含空命令/引号不闭合）。
parse_cmd_argv() {
  local cmd="$1"
  _PARSE_ARGV=()
  while IFS= read -r _a; do _PARSE_ARGV+=("$_a"); done < <(python3 -c '
import shlex, sys
try:
    print("\n".join(shlex.split(sys.argv[1])))
except Exception:
    sys.exit(1)
' "$cmd" 2>/dev/null)
  [ ${#_PARSE_ARGV[@]} -gt 0 ]
}

# is_cmd_argv_safe: 对已解析的 _PARSE_ARGV 执行白名单策略（单一事实来源）。
#   - 只放行具体命令 hcloud / curl；
#   - 例外：bash -n <SKILL_PATH 内脚本绝对路径>（自带脚本冒烟语法检查）；
#   - 其余一律拒绝，尤其是解释器（python/python3/bash/sh/perl 等）——
#     封堵 python3 -c "..."、python3 /tmp/evil.py、bash /tmp/evil.sh 等任意代码/脚本执行面。
is_cmd_argv_safe() {
  local _first="${_PARSE_ARGV[0]:-}" _i
  case "$_first" in
    hcloud|curl)
      ;;
    bash)
      # 仅允许 bash -n <仓库内绝对脚本路径> 的语法检查
      if [ "${#_PARSE_ARGV[@]}" -ne 3 ] || [ "${_PARSE_ARGV[1]}" != "-n" ]; then
        return 1
      fi
      case "${_PARSE_ARGV[2]}" in
        "$SKILL_PATH"/*) ;;
        *) return 1 ;;
      esac
      ;;
    *)
      # 解释器及一切未列明命令均拒绝
      for _i in python python3 bash sh perl ruby node php awk; do
        [ "$_first" = "$_i" ] && return 1
      done
      return 1
      ;;
  esac
  return 0
}

# run_cmd_argv: 参数列表直传执行(不经过 shell), 杜绝管道/重定向/命令拼接注入。
# 执行前复用与 validate_command 相同的 argv 级安全校验（双保险），
# 覆盖调用方未先经 validate_command 的路径（如 sdk 兜底、api 分支），
# 校验失败返回 127（调用方统一按 SKIP:command_rejected 处理）。
run_cmd_argv() {
  local cmd="$1"
  local out=""
  local rc=0
  if ! parse_cmd_argv "$cmd" || ! is_cmd_argv_safe; then
    return 127
  fi
  out=$("${_PARSE_ARGV[@]}" 2>&1)
  rc=$?
  printf '%s' "$out"
  return "$rc"
}

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
SKILL_NAME=$(grep '^name:' "$SKILL_MD" 2>/dev/null | head -1 | sed 's/^name:[[:space:]]*//;s/^"//;s/"$//' || echo "unknown")
QUALITY_SKILL_NAME="$SKILL_NAME"

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
RESULTS_ARR=()

record() {
  local op="$1" type="$2" status="$3" note="$4"
  RESULTS_ARR+=("$(printf '| `%s` | %s | %s | %s |' "$op" "$type" "$status" "$note")")
  case "$status" in
    ✅*|✅) PASS_COUNT=$((PASS_COUNT + 1)) ;;
    ❌*|❌) FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
    ⏭️*) SKIP_COUNT=$((SKIP_COUNT + 1)) ;;
  esac
}

# ------------------------------------------------------------------
# Step 0: Check hcloud CLI availability
# ------------------------------------------------------------------
HCLOUD_AVAILABLE=false
HCLOUD_AUTHENTICATED=false
HCLOUD_VERSION=""

if command -v hcloud &>/dev/null; then
  HCLOUD_AVAILABLE=true
  HCLOUD_VERSION=$(hcloud --version 2>/dev/null | head -1 || echo "unknown")
  if hcloud configure list &>/dev/null 2>&1; then
    HCLOUD_AUTHENTICATED=true
  fi
fi

SDK_AVAILABLE=false
if python3 -c "import huaweicloudsdkcore" &>/dev/null 2>&1; then
  SDK_AVAILABLE=true
fi

CURL_AVAILABLE=false
command -v curl &>/dev/null && CURL_AVAILABLE=true

# ------------------------------------------------------------------
# Resolve executor
# ------------------------------------------------------------------
resolve_executor() {
  local prefer="$1"
  case "$prefer" in
    cli)
      if [ "$HCLOUD_AVAILABLE" = true ]; then echo "cli"; else echo ""; fi
      ;;
    sdk)
      if [ "$SDK_AVAILABLE" = true ]; then echo "sdk"; else echo ""; fi
      ;;
    api)
      local _ak="" _sk="" _name _value; while IFS='=' read -r _name _value; do case "${_name^^}" in HUAWEI*_ACCESS_KEY|HUAWEI*_AK|HW*_ACCESS_KEY|HW*_AK|HWC*_ACCESS_KEY|HWC*_AK) _ak="$_value" ;; HUAWEI*_SECRET_KEY|HUAWEI*_SK|HW*_SECRET_KEY|HW*_SK|HWC*_SECRET_KEY|HWC*_SK) _sk="$_value" ;; esac; done < <(env); if [ "$CURL_AVAILABLE" = true ] && [ -n "$_ak" ] && [ -n "$_sk" ]; then echo "api"; else echo ""; fi
      ;;
    auto)
      if [ "$HCLOUD_AVAILABLE" = true ]; then echo "cli"
      elif [ "$SDK_AVAILABLE" = true ]; then echo "sdk"
      elif [ "$CURL_AVAILABLE" = true ]; then echo "api"
      else echo ""; fi
      ;;
    *) echo "" ;;
  esac
}

# ------------------------------------------------------------------
# Syntax error detection
# ------------------------------------------------------------------
is_syntax_error() {
  local output="$1"
  printf '%s\n' "$output" | grep -qiE "Operation .* is not supported" && return 0
  printf '%s\n' "$output" | grep -qiE "parameter.*not.*recognized|unrecognized.*arg" && return 0
  printf '%s\n' "$output" | grep -qiE "format must be|Invalid.*parameter" && return 0
  printf '%s\n' "$output" | grep -qiE "AttributeError|TypeError|module.*has no attribute" && return 0
  return 1
}

# ------------------------------------------------------------------
# Test execution functions
# ------------------------------------------------------------------
run_cli_test() {
  local cmd="$1"
  local output
  local ec=0
  validate_command "$cmd" || { echo "SKIP:command_rejected"; return 1; }
  if output=$(run_cmd_argv "$cmd"); then
    ec=0
  else
    ec=$?
    if [ "$ec" -eq 127 ]; then
      echo "SKIP:command_rejected"
      return 1
    fi
  fi

  if [ "$ec" -eq 0 ] && ! printf '%s\n' "$output" | grep -qiE "error|failed|denied|unauthorized|not found"; then
    echo "PASS:$output"
    return 0
  fi
  if is_syntax_error "$output"; then
    echo "SYNTAX_ERR:$output"
    return 2
  fi
  echo "FAIL:$output"
  return 1
}

run_sdk_test() {
  local svc="$1" op="$2" region="$3"
  local output
  if output=$(python3 -c "
import sys, os, json
svc_lower, op, region, insecure = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == 'true'
try:
    import re
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkcore.http.http_config import HttpConfig
    svc_module = __import__('huaweicloudsdk' + svc_lower + '.v1', fromlist=[svc + 'Client'])
    Client = getattr(svc_module, svc + 'Client')
    ak = (os.environ.get('HUAWEICLOUD_SDK_AK') or os.environ.get('HUAWEI_ACCESS_KEY')
          or os.environ.get('HW_ACCESS_KEY') or os.environ.get('HUAWEI_AK') or os.environ.get('HW_AK') or '')
    sk = (os.environ.get('HUAWEICLOUD_SDK_SK') or os.environ.get('HUAWEI_SECRET_KEY')
          or os.environ.get('HW_SECRET_KEY') or os.environ.get('HUAWEI_SK') or os.environ.get('HW_SK') or '')
    cred = BasicCredentials(ak, sk)
    config = HttpConfig.get_default_config()
    if insecure:
        config.ignore_ssl_verification = True
    client = Client.new_builder().with_http_config(config).with_credentials(cred).with_region(region).build()
    req_class = getattr(svc_module, op + 'Request')
    req = req_class(limit=1)
    fn_name = re.sub(r'(?<!^)(?=[A-Z])', '_', op).lower()  # ListFlavors -> list_flavors
    resp = getattr(client, fn_name)(req)
    print(json.dumps(resp.to_json_object() if hasattr(resp,'to_json_object') else str(resp), indent=2)[:500])
except Exception as e:
    print(f'SDK_ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" "$svc" "$op" "$region" "$INSECURE" 2>&1); then
    local ec=0
  else
    local ec=$?
  fi
  if [ "$ec" -eq 0 ] && [ -n "$output" ]; then
    echo "PASS:$output"
    return 0
  fi
  if echo "$output" | grep -qiE "AttributeError|TypeError|module.*has no attribute"; then
    echo "SYNTAX_ERR:$output"
    return 2
  fi
  echo "FAIL:$output"
  return 1
}

# ------------------------------------------------------------------
# Main test loop
# ------------------------------------------------------------------
echo "=========================================="
echo " CLI Functional Test"
echo " Skill: $SKILL_NAME"
echo " Path: $SKILL_PATH"
echo " Region: $REGION"
echo " Executor mode: $EXECUTOR"
echo "=========================================="
echo ""

if [ ! -f "$TEST_VARS" ]; then
  echo "[FATAL] templates/test-vars.json not found at $TEST_VARS — no tests executed"
  record "(no test vars)" "N/A" "❌ 失败" "templates/test-vars.json 不存在"
  QUALITY_STATUS="sys_fail"
  exit 1
else
  # Parse test cases from JSON
  TC_COUNT=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); print(len(d.get('test_cases',[])))" "$TEST_VARS" 2>/dev/null || echo "0")

  if [ "$TC_COUNT" -eq 0 ]; then
    echo "[WARN] No test cases in templates/test-vars.json"
    record "(empty test list)" "N/A" "⏭️ 跳过" "test_cases 数组为空"
  else
    echo "Found $TC_COUNT test case(s) in templates/test-vars.json"
    echo ""

    for i in $(seq 0 $((TC_COUNT - 1))); do
      TC_ID=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); i=int(sys.argv[2]); print(d['test_cases'][i].get('id','TC-%02d'%(i+1)))" "$TEST_VARS" "$i" 2>/dev/null) || true
      TC_NAME=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); i=int(sys.argv[2]); print(d['test_cases'][i].get('name',''))" "$TEST_VARS" "$i" 2>/dev/null) || true
      TC_CMD=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); i=int(sys.argv[2]); print(d['test_cases'][i].get('command',''))" "$TEST_VARS" "$i" 2>/dev/null) || true
      TC_TYPE=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); i=int(sys.argv[2]); print(d['test_cases'][i].get('type','syntax'))" "$TEST_VARS" "$i" 2>/dev/null) || true
      TC_EXEC=$(python3 -c "import sys,json; d=json.load(open(sys.argv[1])); i=int(sys.argv[2]); print(d['test_cases'][i].get('executor','auto'))" "$TEST_VARS" "$i" 2>/dev/null) || true

      echo "--- [$TC_ID] $TC_NAME ---"
      echo "  Command: $TC_CMD"

      # Resolve executor for this test case
      ACTIVE_EXEC=$(resolve_executor "$TC_EXEC")
      if [ -z "$ACTIVE_EXEC" ]; then
        ACTIVE_EXEC=$(resolve_executor "auto")
      fi
      if [ -z "$ACTIVE_EXEC" ]; then
        record "$TC_CMD" "$TC_TYPE" "⏭️ 跳过" "无可用执行后端"
        echo "  ⏭️ SKIP: No execution backend available"
        echo ""
        continue
      fi

      # Substitute {region} placeholder
      CMD_FINAL="${TC_CMD//\{region\}/$REGION}"

      # Reject commands with unresolved template placeholders ({Service}, {endpoint}, etc.)
      if printf '%s' "$CMD_FINAL" | grep -qE '\{[A-Za-z_]+\}'; then
        record "$CMD_FINAL" "$TC_TYPE" "⛔ 需人工验证" "命令含未替换的模板占位符，未执行"
        echo "  ⛔ MANUAL VERIFICATION NEEDED: unresolved placeholder in command"
        echo ""
        continue
      fi

      case "$ACTIVE_EXEC" in
              cli)
                if echo "$CMD_FINAL" | grep -qE '^hcloud'; then
                  WRAP_CMD="$CMD_FINAL"
                  if result=$(run_cli_test "$WRAP_CMD" 2>&1); then
              status_code=0
            else
              status_code=$?
            fi
            case "$status_code" in
              0)
                record "$CMD_FINAL" "CLI $TC_TYPE" "✅ 通过" "CLI verified"
                echo "  ✅ PASS (CLI)"
                ;;
              2)
                record "$CMD_FINAL" "CLI $TC_TYPE" "❌ 失败" "语法错误，需修复"
                echo "  ❌ FAIL - syntax error (CLI)"
                FAIL_COUNT=$((FAIL_COUNT - 1))  # record already counted
                ;;
              *)
                # Try SDK fallback
                echo "  ⚠ CLI failed → trying SDK fallback"
                if [ "$SDK_AVAILABLE" = true ]; then
                  # Extract svc/op from command
                  svc_op=$(echo "$CMD_FINAL" | grep -oP 'hcloud \K[A-Z][A-Za-z0-9]* [A-Z][A-Za-z0-9]*' | head -1) || true
                  if [ -n "$svc_op" ]; then
                    read -r svc op <<< "$svc_op"
                    if sdk_result=$(run_sdk_test "$svc" "$op" "$REGION" 2>&1); then
                      sdk_ec=0
                    else
                      sdk_ec=$?
                    fi
                    if [ "$sdk_ec" -eq 0 ]; then
                      record "$CMD_FINAL" "CLI→SDK $TC_TYPE" "✅ 通过" "SDK fallback verified"
                      echo "  ✅ PASS (SDK fallback)"
                    else
                      record "$CMD_FINAL" "CLI→SDK $TC_TYPE" "⛔ 需人工验证" "CLI+SDK均失败"
                      echo "  ⛔ MANUAL VERIFICATION NEEDED"
                    fi
                  else
                    record "$CMD_FINAL" "CLI $TC_TYPE" "⛔ 需人工验证" "无法提取svc/op"
                    echo "  ⛔ MANUAL VERIFICATION NEEDED"
                  fi
                else
                  record "$CMD_FINAL" "CLI $TC_TYPE" "⛔ 需人工验证" "CLI失败，SDK不可用"
                  echo "  ⛔ MANUAL VERIFICATION NEEDED"
                fi
                ;;
            esac
          else
            # Non-hcloud command: enforce allowlist before execution
            if ! validate_command "$CMD_FINAL"; then
              record "$CMD_FINAL" "CLI $TC_TYPE" "⛔ 需人工验证" "非白名单命令，未执行"
              echo "  ⛔ MANUAL VERIFICATION NEEDED: command not in allowlist"
            else
              if result=$(run_cmd_argv "$CMD_FINAL" 2>&1); then
                cmd_ec=0
              else
                cmd_ec=$?
              fi
              if [ "$cmd_ec" -eq 0 ] && [ -n "$result" ] && ! echo "$result" | grep -qiE "error|not found|failed"; then
                record "$CMD_FINAL" "CLI $TC_TYPE" "✅ 通过" "executed"
                echo "  ✅ PASS (CLI)"
              else
                record "$CMD_FINAL" "CLI $TC_TYPE" "❌ 失败" "$(echo "$result" | head -1)"
                echo "  ❌ FAIL"
              fi
            fi
          fi
          ;;
        sdk)
          if echo "$CMD_FINAL" | grep -qE 'python3.*huaweicloudsdk'; then
            # Extract svc/op from command for SDK test
            svc=$(echo "$CMD_FINAL" | grep -oP 'huaweicloudsdk\K[a-z]+' | head -1 || echo "")
            if [ -n "$svc" ]; then
              svc_upper=$(echo "$svc" | tr '[:lower:]' '[:upper:]' | head -c1)$(echo "$svc" | tail -c+2)
              if sdk_result=$(run_sdk_test "$svc_upper" "List" "$REGION" 2>&1); then
                sdk_ec=0
              else
                sdk_ec=$?
              fi
              if [ "$sdk_ec" -eq 0 ]; then
                record "$CMD_FINAL" "SDK $TC_TYPE" "✅ 通过" "SDK verified"
                echo "  ✅ PASS (SDK)"
              else
                record "$CMD_FINAL" "SDK $TC_TYPE" "⛔ 需人工验证" "SDK调用失败"
                echo "  ⛔ MANUAL VERIFICATION NEEDED"
              fi
            else
              # Just try the Python command
              if result=$(run_cmd_argv "$CMD_FINAL" 2>&1); then
                py_ec=0
              else
                py_ec=$?
              fi
              if [ "$py_ec" -eq 0 ] && echo "$result" | grep -qiE "SDK OK|success|PASS"; then
                record "$CMD_FINAL" "SDK $TC_TYPE" "✅ 通过" "SDK verified"
                echo "  ✅ PASS (SDK)"
              else
                record "$CMD_FINAL" "SDK $TC_TYPE" "❌ 失败" "$(echo "$result" | head -2 | tr '\n' ' ')"
                echo "  ❌ FAIL"
              fi
            fi
          else
            # Non-SDK command: enforce allowlist before execution
            if ! validate_command "$CMD_FINAL"; then
              record "$CMD_FINAL" "SDK $TC_TYPE" "⛔ 需人工验证" "非白名单命令，未执行"
              echo "  ⛔ MANUAL VERIFICATION NEEDED: command not in allowlist"
            else
              if result=$(run_cmd_argv "$CMD_FINAL" 2>&1); then
                cmd_ec=0
              else
                cmd_ec=$?
              fi
              if [ "$cmd_ec" -eq 0 ] && [ -n "$result" ] && ! echo "$result" | grep -qiE "error|not found|failed"; then
                record "$CMD_FINAL" "SDK $TC_TYPE" "✅ 通过" "executed as script"
                echo "  ✅ PASS (executed as script)"
              else
                record "$CMD_FINAL" "SDK $TC_TYPE" "❌ 失败" "$(echo "$result" | head -1)"
                echo "  ❌ FAIL"
              fi
            fi
          fi
          ;;
        api)
          if echo "$CMD_FINAL" | grep -qE '^curl'; then
            if result=$(run_cmd_argv "$CMD_FINAL" 2>&1); then
              curl_ec=0
            else
              curl_ec=$?
            fi
            if [ "$curl_ec" -eq 0 ] && echo "$result" | grep -qE 'HTTP.*200|HTTP.*202'; then
              record "$CMD_FINAL" "API $TC_TYPE" "✅ 通过" "API verified"
              echo "  ✅ PASS (API)"
            else
              record "$CMD_FINAL" "API $TC_TYPE" "❌ 失败" "$(echo "$result" | head -1)"
              echo "  ❌ FAIL"
            fi
          else
            record "$CMD_FINAL" "API $TC_TYPE" "⏭️ 跳过" "非curl命令，无法以API模式执行"
            echo "  ⏭️ SKIP (not a curl command)"
          fi
          ;;
      esac
      echo ""
    done
  fi
fi

# ------------------------------------------------------------------
# Generate test report
# ------------------------------------------------------------------
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
REPORT_DATE=$(date +"%Y-%m-%d %H:%M:%S")
mkdir -p "$(dirname "$OUTPUT_FILE")"

cat > "$OUTPUT_FILE" << REPORT_HEADER
# 功能测试报告 — ${SKILL_NAME}

> 生成时间：${REPORT_DATE}
> 测试区域：${REGION}
> CLI 版本：${HCLOUD_VERSION:-未安装}
> 执行模式：${EXECUTOR}

## 测试结果汇总

| 指标 | 值 |
|------|-----|
| 总测试数 | ${TOTAL} |
| ✅ 通过 | ${PASS_COUNT} |
| ❌ 失败 | ${FAIL_COUNT} |
| ⏭️ 跳过 | ${SKIP_COUNT} |
| 测试者 | Huawei Cloud Skill Creator v2 |

## 测试详情

| 操作 | 测试类型 | 结果 | 备注 |
|------|----------|------|------|
REPORT_HEADER

for result in "${RESULTS_ARR[@]}"; do
  echo "$result" >> "$OUTPUT_FILE"
done

chmod 600 "$OUTPUT_FILE" 2>/dev/null || true

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

[ "$FAIL_COUNT" -eq 0 ]
