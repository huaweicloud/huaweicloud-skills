#!/bin/bash
# test-cli-commands.sh — Execute HSS CLI test cases
# Usage: bash scripts/test-cli-commands.sh -s {skill-path} -e {cli|sdk|api} [-r {region}]
#   -s {skill-path}   Path to the skill directory (contains templates/test-vars.json)
#   -e {executor}     Execution mode (cli|sdk|api); HSS skill only supports cli
#   -r {region}       Huawei Cloud region used to replace {region} placeholders in
#                     test-vars.json commands. Defaults to $HUAWEI_REGION if set.
#
# PASS/FAIL 判定说明:
#   - 执行前用 -r/{region} 或 $HUAWEI_REGION 替换命令中的 {region} 占位符,
#     无法替换时该用例直接判 FAIL(不再静默执行失败命令)。
#   - 判定以 退出码 + 输出内容 双重为准: hcloud 对部分 USE_ERROR/服务端错误
#     返回码为 0,仅看退出码会把失败误判为 PASS,因此输出含错误标记
#     (error_code/error_msg/USE_ERROR/APIGW./HSS. 等) 一律判 FAIL。
#   - 不使用 eval 执行命令: 命令按空白拆分为参数数组执行,杜绝命令注入。

set -uo pipefail

SKILL_PATH=""
EXECUTOR="cli"
REGION="${HUAWEI_REGION:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -s) SKILL_PATH="$2"; shift 2 ;;
    -e) EXECUTOR="$2"; shift 2 ;;
    -r|--region) REGION="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$SKILL_PATH" ]]; then
  echo "FATAL: skill path required (-s)"
  exit 1
fi

TEST_VARS="${SKILL_PATH}/templates/test-vars.json"
if [[ ! -f "$TEST_VARS" ]]; then
  echo "FATAL: templates/test-vars.json not found"
  exit 1
fi

echo "=== HSS Skill Test Execution ==="
echo "Skill: ${SKILL_PATH}"
echo "Executor: ${EXECUTOR}"
echo "Region: ${REGION:-<unset>}"
echo ""

# Only CLI mode is supported for this skill
if [[ "$EXECUTOR" != "cli" ]]; then
  echo "WARN: Only CLI mode is supported for HSS skill. Falling back to cli."
  EXECUTOR="cli"
fi

# Whitelist check: only allow hcloud, python3, curl, bash prefixed commands
is_whitelisted() {
  local cmd="$1"
  [[ "$cmd" =~ ^hcloud\  ]] && return 0
  [[ "$cmd" =~ ^python3\  ]] && return 0
  [[ "$cmd" =~ ^curl\  ]] && return 0
  [[ "$cmd" =~ ^bash\  ]] && return 0
  return 1
}

# Output-content error detection: hcloud returns exit code 0 for some
# USE_ERROR / server-side errors, so exit code alone cannot prove success.
looks_like_error() {
  local out="$1"
  [[ "$out" =~ error_code|error_msg|error_description|USE_ERROR|APIGW\.[0-9]|HSS\.[0-9]|Traceback|FATAL ]] && return 0
  return 1
}

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Extract test cases from JSON (safe parsing, no eval of JSON content)
TEST_COMMANDS=$(python3 -c "
import json, sys
with open('${TEST_VARS}') as f:
    data = json.load(f)
for tc in data.get('test_cases', []):
    print(f\"{tc['id']}|{tc['name']}|{tc['command']}\")
")

while IFS='|' read -r tc_id tc_name tc_command; do
  [[ -z "$tc_id" ]] && continue

  echo "--- ${tc_id}: ${tc_name} ---"

  if ! is_whitelisted "$tc_command"; then
    echo "  SKIP: command not in whitelist"
    SKIP_COUNT=$((SKIP_COUNT + 1))
    continue
  fi

  # Replace {region} placeholder; without a region the command cannot run
  if [[ "$tc_command" == *"{region}"* ]]; then
    if [[ -z "$REGION" ]]; then
      echo "  FAIL: command contains {region} but no region provided (use -r/--region or set HUAWEI_REGION)"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
    tc_command="${tc_command//\{region\}/$REGION}"
  fi

  # Execute via argument array (no eval — prevents command injection)
  read -r -a cmd_words <<< "$tc_command"
  output=$("${cmd_words[@]}" 2>&1)
  rc=$?

  if [[ $rc -ne 0 ]] || looks_like_error "$output"; then
    echo "  FAIL: exit=${rc}"
    echo "$output" | head -5 | sed 's/^/    /'
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    echo "  PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
done <<< "$TEST_COMMANDS"

echo ""
echo "=== Test Summary ==="
echo "PASS: ${PASS_COUNT}"
echo "FAIL: ${FAIL_COUNT}"
echo "SKIP: ${SKIP_COUNT}"
echo "TOTAL: $((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))"

if [[ $FAIL_COUNT -gt 0 ]]; then
  exit 1
fi
exit 0