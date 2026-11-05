#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

mkdir -p "${MODULE_DIR}/out"

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "${value}"
}

first_source_id=""
source_count=0
if [[ -n "${SOURCE_SERVER_IDS:-}" ]]; then
  IFS=',' read -r -a _source_ids <<< "${SOURCE_SERVER_IDS}"
  source_count="${#_source_ids[@]}"
  if [[ "${source_count}" -gt 0 ]]; then
    first_source_id="$(trim "${_source_ids[0]}")"
  fi
fi

is_huawei_ecs_uuid() {
  local value="$1"
  [[ "${value}" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]
}

migration_mode="batch_existing_target"
if [[ -n "${first_source_id}" && "${source_count}" -eq 1 ]]; then
  if [[ "${first_source_id}" =~ ^i-[0-9a-fA-F]+$ ]]; then
    migration_mode="external_aws"
  elif ! is_huawei_ecs_uuid "${first_source_id}"; then
    migration_mode="external_generic"
  fi
fi

# External-source single instance uses the single-source SMS flow.
if [[ "${migration_mode}" == "external_aws" || "${migration_mode}" == "external_generic" ]]; then
  if [[ "${migration_mode}" == "external_aws" ]]; then
    echo "[RUN-MIGRATION] Detected AWS EC2 source ${first_source_id}, switching to mgc_migrate.py"
  else
    echo "[RUN-MIGRATION] Detected external source ${first_source_id}, switching to mgc_migrate.py"
  fi

  raw_source_region="$(trim "${SOURCE_REGION:-}")"

  export HC_AK="${DESTINATION_ACCESS_KEY}"
  export HC_SK="${DESTINATION_SECRET_KEY}"
  export SOURCE_SERVER_ID="${first_source_id}"
  # External source IDs are queried from SMS source list. Keep SOURCE_REGION as a valid
  # destination-account region to satisfy downstream IAM project lookup.
  export SOURCE_REGION="${DESTINATION_REGION}"
  export TARGET_REGION="${DESTINATION_REGION}"
  export TARGET_REGION_NAME="${DESTINATION_REGION_NAME:-${DESTINATION_REGION}}"
  export TARGET_VPC_NAME="${TARGET_VPC_NAME:-vpc-migration}"
  export TARGET_VPC_CIDR="${TARGET_VPC_CIDR:-10.250.0.0/16}"
  export TARGET_SUBNET_CIDR="${TARGET_SUBNET_CIDR:-10.250.1.0/24}"
  export TARGET_IMAGE_ID="${TARGET_IMAGE_ID:-def7f676-e1e3-43c3-9098-e41f3324d566}"
  export TARGET_SERVER_NAME="${TARGET_SERVER_NAME:-aws-ohio-migrated-${first_source_id:2:8}}"
  export TARGET_FLAVOR_ID="${TARGET_FLAVOR_ID:-s6.large.2}"
  if [[ -z "${TARGET_ADMIN_PASSWORD:-}" ]]; then
    echo "[RUN-MIGRATION] TARGET_ADMIN_PASSWORD is required and must not be left empty/default." >&2
    exit 1
  fi
  export TARGET_ADMIN_PASSWORD
  export EIP_BANDWIDTH_MBPS="${EIP_BANDWIDTH_MBPS:-100}"
  export ROOT_VOLUME_TYPE="${ROOT_VOLUME_TYPE:-SSD}"
  export DATA_VOLUME_TYPE="${DATA_VOLUME_TYPE:-SSD}"
  export SMS_ENDPOINT="${SMS_ENDPOINT:-https://sms.ap-southeast-3.myhuaweicloud.com}"
  export PREFERRED_MIGRATION_METHOD="${PREFERRED_MIGRATION_METHOD:-sms}"
  export ENABLE_RSYNC_FALLBACK="${ENABLE_RSYNC_FALLBACK:-true}"
  if [[ -z "${RSYNC_SOURCE_HOST:-}" && -n "${SOURCE_PRIVATE_IP:-}" ]]; then
    export RSYNC_SOURCE_HOST="${SOURCE_PRIVATE_IP}"
  fi
  export ENABLE_VPN_BRIDGE="${ENABLE_VPN_BRIDGE:-false}"
  export ENABLE_TARGET_VPN_CLIENT="${ENABLE_TARGET_VPN_CLIENT:-false}"
  export RESULT_PATH="${RESULT_PATH:-${MODULE_DIR}/out/migration_result.json}"

  if [[ "${migration_mode}" == "external_aws" ]]; then
    export AWS_SOURCE_ACCESS_KEY="${AWS_SOURCE_ACCESS_KEY:-${SOURCE_ACCESS_KEY:-}}"
    export AWS_SOURCE_SECRET_KEY="${AWS_SOURCE_SECRET_KEY:-${SOURCE_SECRET_KEY:-}}"
    export AWS_SOURCE_REGION="${AWS_SOURCE_REGION:-${raw_source_region}}"
    if [[ -z "${AWS_SOURCE_PEM_PATH:-}" ]]; then
      echo "[RUN-MIGRATION] AWS_SOURCE_PEM_PATH is required for AWS sources (path to the EC2 key pair .pem file)." >&2
      exit 1
    fi
    export AWS_SOURCE_PEM_PATH
  fi

  python3 "${SCRIPT_DIR}/mgc_migrate.py"
else
  python3 "${SCRIPT_DIR}/mgc_sms_existing_target_batch.py"
fi
