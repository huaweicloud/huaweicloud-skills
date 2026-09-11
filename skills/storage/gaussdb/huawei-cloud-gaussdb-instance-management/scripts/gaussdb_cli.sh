#!/usr/bin/env bash
# Huawei Cloud GaussDB — hcloud (KooCLI) command wrapper
#
# Usage: gaussdb_cli.sh <service> <Operation> [--key=value ...]
#
#   service    hcloud service name: GaussDB (MySQL-compatible) or
#              gaussdbforopengauss (openGauss distributed)
#   Operation  PascalCase operation, e.g. ListGaussMySqlInstances
#
# Behaviour:
#   - injects --cli-region from HUAWEI_REGION (default cn-north-4) when omitted
#   - requires explicit user confirmation for mutating operations (R2/R1)
#   - treats hcloud as failed when the output contains error markers, because
#     hcloud exits 0 even on API/CLI errors (see rds_cli.sh ISSUE-011 lesson)

set -euo pipefail

REGION="${HUAWEI_REGION:-cn-north-4}"
SERVICE="${1:-}"
OPERATION="${2:-}"
shift 2 || true

if [[ -z "${SERVICE}" || -z "${OPERATION}" ]]; then
  echo "ERROR: Usage: gaussdb_cli.sh <service> <Operation> [--key=value ...]" >&2
  echo "       e.g. gaussdb_cli.sh GaussDB ListGaussMySqlInstances --cli-region=cn-north-4 --limit=10" >&2
  exit 2
fi

# Mutating operations (R2 preview+confirm, R1 risk-confirm) per SKILL.md
MUTATING_OPS="
  CreateGaussMySqlInstance CreateInstance
  CreateGaussMySqlBackup CreateManualBackup
  CreateGaussMySqlReadonlyNode CreateReadonlyNodes
  RunInstanceAction
  AddDatabasePermission DeleteDatabasePermission AllowDbPrivileges
  DeleteGaussMySqlInstance DeleteInstance
"
if echo "${MUTATING_OPS}" | grep -qw "${OPERATION}"; then
  echo "Mutating operation: ${SERVICE} ${OPERATION}" >&2
  read -r -p "Confirm execution? (yes/no): " _answer
  if [[ "${_answer}" != "yes" ]]; then
    echo "Cancelled." >&2
    exit 0
  fi
fi

# Inject a default --cli-region when none is passed
HAS_REGION=false
for arg in "$@"; do
  if [[ "${arg}" == --cli-region=* ]]; then
    HAS_REGION=true
    break
  fi
done
if [[ "${HAS_REGION}" == false ]]; then
  set -- --cli-region="${REGION}" "$@"
fi

if ! command -v hcloud &>/dev/null; then
  echo "ERROR: hcloud (KooCLI) not found. See references/cli-installation-guide.md" >&2
  exit 127
fi

OUTPUT="$(hcloud "${SERVICE}" "${OPERATION}" "$@" 2>&1)" || true
STATUS=$?

# hcloud exits 0 even on API/CLI errors — detect them by output content
if grep -qiE "error|failed|exception|not found|invalid|缺少必填参数" <<<"${OUTPUT}"; then
  echo "hcloud reported an error:" >&2
  echo "${OUTPUT}" >&2
  exit 1
fi

echo "${OUTPUT}"
exit "${STATUS}"