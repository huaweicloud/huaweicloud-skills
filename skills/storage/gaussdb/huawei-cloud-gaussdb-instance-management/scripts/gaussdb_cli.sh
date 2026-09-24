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
#   - hard-binds a quality report (success / biz_fail / sys_fail) on every run
#     through skill-quality-cli (unified CLI, see scripts/cli/cli_entry.py) —
#     fire-and-forget, never blocks the business flow (see SKILL.md "Quality
#     Reporting (Unified CLI)")

set -euo pipefail

REGION="${HUAWEI_REGION:-cn-north-4}"
SERVICE="${1:-}"
OPERATION="${2:-}"
shift 2 || true

# ---------------------------------------------------------------- quality report
# Fire-and-forget quality report via skill-quality-cli (unified CLI) or the
# bundled in-skill carrier scripts/cli/cli_entry.py. Carrier resolution order:
#  0. SKILL_QUALITY_CLI_HOME (explicit dir containing cli_entry.py / skill-quality-cli)
#  1. skill-quality-cli on PATH (after ensure_cli.sh + PATH export)
#  2. ~/.local/bin/skill-quality-cli (ensure_cli.sh install dir, even when not on PATH)
#  3. bundled in-skill carrier scripts/cli/cli_entry.py (zero-dependency, always available)
# Skipped (never blocks / never changes output or exit code) when:
#  - SKILL_QUALITY_DISABLE=1 (explicit opt-out),
#  - SKILL_TRACE_ID is already set (the whole command is wrapped with
#    `skill-quality-cli run`, which reports once itself — avoid double counting).
report_quality() {
  local status="$1" error_code="${2:-}" error_msg="${3:-}" cost_ms="${4:-}"
  [[ "${SKILL_QUALITY_DISABLE:-}" == "1" ]] && return 0
  [[ -n "${SKILL_TRACE_ID:-}" ]] && return 0  # already wrapped in `skill-quality-cli run`

  local cli=()
  local home="${SKILL_QUALITY_CLI_HOME:-}"
  if [[ -n "${home}" ]]; then
    if [[ -f "${home}/cli_entry.py" ]]; then cli=(python3 "${home}/cli_entry.py" --no-auto-upgrade)
    elif [[ -x "${home}/skill-quality-cli" ]]; then cli=("${home}/skill-quality-cli" --no-auto-upgrade); fi
  fi
  if [[ ${#cli[@]} -eq 0 ]] && command -v skill-quality-cli &>/dev/null; then
    cli=(skill-quality-cli --no-auto-upgrade)
  fi
  if [[ ${#cli[@]} -eq 0 ]] && [[ -x "$HOME/.local/bin/skill-quality-cli" ]]; then
    cli=("$HOME/.local/bin/skill-quality-cli" --no-auto-upgrade)
  fi
  if [[ ${#cli[@]} -eq 0 ]] && [[ -f "$(dirname "${BASH_SOURCE[0]}")/cli/cli_entry.py" ]]; then
    cli=(python3 "$(dirname "${BASH_SOURCE[0]}")/cli/cli_entry.py" --no-auto-upgrade)
  fi
  if [[ ${#cli[@]} -eq 0 ]]; then
    echo "WARNING: skill-quality-cli not found; quality report skipped" >&2
    return 0
  fi

  local args=(report --skill-name huawei-cloud-gaussdb-instance-management --status "${status}")
  [[ -n "${error_code}" ]] && args+=(--error-code "${error_code}")
  [[ -n "${error_msg}" ]] && args+=(--error-msg "${error_msg}")
  [[ -n "${cost_ms}" ]] && args+=(--cost-ms "${cost_ms}")
  # Truly fire-and-forget: detach and never wait, so an unreachable/slow
  # quality endpoint can never block the main flow.
  ( "${cli[@]}" "${args[@]}" >/dev/null 2>&1 & )
}

_START_MS=$(date +%s%3N)

if [[ -z "${SERVICE}" || -z "${OPERATION}" ]]; then
  echo "ERROR: Usage: gaussdb_cli.sh <service> <Operation> [--key=value ...]" >&2
  echo "       e.g. gaussdb_cli.sh GaussDB ListGaussMySqlInstances --cli-region=cn-north-4 --limit=10" >&2
  report_quality "biz_fail" "U01" "missing required argument: service/Operation"
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
    report_quality "cancel"
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
  report_quality "sys_fail" "C02" "hcloud (KooCLI) not found"
  exit 127
fi

if OUTPUT="$(hcloud "${SERVICE}" "${OPERATION}" "$@" 2>&1)"; then
  STATUS=0
else
  STATUS=$?
fi

# hcloud exits 0 even on API/CLI errors — detect them by output content
if grep -qiE "error|failed|exception|not found|invalid|缺少必填参数" <<<"${OUTPUT}"; then
  echo "hcloud reported an error:" >&2
  echo "${OUTPUT}" >&2
  report_quality "biz_fail" "U03" "hcloud API/CLI error" "$(( $(date +%s%3N) - _START_MS ))"
  exit 1
fi

echo "${OUTPUT}"
if [[ "${STATUS}" -eq 0 ]]; then
  report_quality "success" "" "" "$(( $(date +%s%3N) - _START_MS ))"
else
  report_quality "sys_fail" "B01" "hcloud exited ${STATUS}" "$(( $(date +%s%3N) - _START_MS ))"
fi
exit "${STATUS}"