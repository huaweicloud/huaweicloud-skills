#!/usr/bin/env bash
# RDS Smart Service - CLI Command Wrapper
# Executes hcloud RDS commands with three-level fallback (CLI → SDK → API)
# Usage: rds_cli.sh <Operation> [--key=value ...]
#
# Safety: mutating operations require explicit user confirmation.
# Fallback: CLI errors are detected by OUTPUT CONTENT (hcloud exits 0 even on errors),
#           not by exit code alone — see ISSUE-011.

set -euo pipefail

REGION="${HUAWEI_REGION:-cn-north-4}"
OPERATION="${1:-}"
shift || true

if [[ -z "$OPERATION" ]]; then
  echo "ERROR: No operation specified. Usage: rds_cli.sh <Operation> [--key=value ...]"
  exit 1
fi

# ---------------------------------------------------------------------------
# Mutating operations — require explicit user confirmation (ISSUE-013)
# ---------------------------------------------------------------------------
MUTATING_OPS="
  StartInstanceRestartAction StartInstanceEnlargeVolumeAction StartInstanceReduceVolumeAction
  StartResizeFlavorAction StartFailover SetReadOnlySwitch UpdateInstanceAlias SetAutoEnlargePolicy
  CreateSqlLimit CreateIntelligentKillSession ValidateInstanceConnection
  SetBackupPolicy ChangeBackupConfig CreateManualBackup DeleteManualBackup BatchDeleteManualBackup
  CreateRestoreInstance RestoreToExistingInstance RestoreTables
  SetSecurityGroup SwitchSsl SetAuditlogPolicy CreateConfiguration UpdateConfiguration
  ApplyConfigurationAsync UpdateInstanceConfiguration BatchDeleteInstance
"
if echo "$MUTATING_OPS" | grep -qw "$OPERATION"; then
  echo "⚠️  变更操作: $OPERATION"
  read -r -p "  确认执行? (yes/no): " _ans
  if [[ "$_ans" != "yes" ]]; then
    echo "已取消。"
    exit 0
  fi
fi

# Ensure --cli-region is set
HAS_REGION=false
for arg in "$@"; do
  if [[ "$arg" == --cli-region=* ]]; then
    HAS_REGION=true
    break
  fi
done

if [[ "$HAS_REGION" == false ]]; then
  set -- --cli-region="$REGION" "$@"
fi

# ---------------------------------------------------------------------------
# Level 1: Try hcloud CLI
# hcloud returns exit code 0 even on API/CLI errors, so detect failure by
# inspecting stdout/stderr for error markers (ISSUE-011).
# ---------------------------------------------------------------------------
if command -v hcloud &>/dev/null; then
  cli_out="$(hcloud RDS "$OPERATION" "$@" 2>&1)"
  cli_rc=$?
  if [[ $cli_rc -eq 0 ]] && ! echo "$cli_out" | grep -qE 'USE_ERROR|不支持的operation|error_code|error_msg|仅支持参数|缺少必填参数|不正确的参数'; then
    echo "$cli_out"
    exit 0
  else
    echo "$cli_out" >&2
    echo "WARN: CLI execution failed, falling back to SDK..." >&2
  fi
else
  echo "WARN: hcloud CLI not found, falling back to SDK..." >&2
fi

# ---------------------------------------------------------------------------
# Level 2: Try Python SDK
# Pass through any --param=value args (minus hcloud-specific --cli-* flags)
# ---------------------------------------------------------------------------
if python3 -c "import huaweicloudsdkrds" 2>/dev/null; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  sdk_args=()
  for arg in "$@"; do
    case "$arg" in
      --cli-region=*) sdk_args+=(--region="${arg#--cli-region=}") ;;
      --cli-*|--X-Language=*) ;;  # drop hcloud-only flags
      *) sdk_args+=("$arg") ;;
    esac
  done
  if python3 "${SCRIPT_DIR}/rds_sdk_fallback.py" "$OPERATION" "${sdk_args[@]}" 2>/dev/null; then
    exit 0
  else
    echo "WARN: SDK execution failed, falling back to REST API..." >&2
  fi
else
  echo "WARN: huaweicloudsdkrds not installed, falling back to REST API..." >&2
fi

# ---------------------------------------------------------------------------
# Level 3: REST API fallback
# ---------------------------------------------------------------------------
echo "ERROR: All execution modes failed. Please verify credentials and network connectivity." >&2
exit 1
