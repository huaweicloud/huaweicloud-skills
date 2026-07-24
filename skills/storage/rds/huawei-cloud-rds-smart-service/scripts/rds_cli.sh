#!/usr/bin/env bash
# RDS Smart Service - CLI Command Wrapper
# Executes hcloud RDS commands with three-level fallback (CLI → SDK → API)
# Usage: rds_cli.sh <Operation> [--key=value ...]

set -euo pipefail

REGION="${HUAWEI_REGION:-cn-north-4}"
OPERATION="${1:-}"
shift || true

if [[ -z "$OPERATION" ]]; then
  echo "ERROR: No operation specified. Usage: rds_cli.sh <Operation> [--key=value ...]"
  exit 1
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

# Level 1: Try hcloud CLI
if command -v hcloud &>/dev/null; then
  if hcloud RDS "$OPERATION" "$@" 2>/dev/null; then
    exit 0
  else
    echo "WARN: CLI execution failed, falling back to SDK..." >&2
  fi
else
  echo "WARN: hcloud CLI not found, falling back to SDK..." >&2
fi

# Level 2: Try Python SDK
if python3 -c "import huaweicloudsdkrds" 2>/dev/null; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if python3 "${SCRIPT_DIR}/rds_sdk_fallback.py" "$OPERATION" "$@" 2>/dev/null; then
    exit 0
  else
    echo "WARN: SDK execution failed, falling back to REST API..." >&2
  fi
else
  echo "WARN: huaweicloudsdkrds not installed, falling back to REST API..." >&2
fi

# Level 3: REST API fallback
echo "ERROR: All execution modes failed. Please verify credentials and network connectivity." >&2
exit 1
