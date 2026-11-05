#!/bin/bash
set -e

# Load terraform.tfvars and export as environment variables
echo "[AWS-TO-HUAWEI] Loading configuration from terraform.tfvars"

# Parse terraform.tfvars and export variables
while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    
    # Extract variable name and value
    if [[ "$line" =~ ^([a-z_]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
        var_name="${BASH_REMATCH[1]}"
        var_value="${BASH_REMATCH[2]}"
        
        # Remove quotes
        var_value="${var_value#\"}"
        var_value="${var_value%\"}"
        
        # Export based on mapping
        case "$var_name" in
            access_key) export HC_AK="$var_value" ;;
            secret_key) export HC_SK="$var_value" ;;
            target_region) export TARGET_REGION="$var_value" ;;
            target_region_name) export TARGET_REGION_NAME="$var_value" ;;
            target_vpc_name) export TARGET_VPC_NAME="$var_value" ;;
            target_vpc_cidr) export TARGET_VPC_CIDR="$var_value" ;;
            target_subnet_cidr) export TARGET_SUBNET_CIDR="$var_value" ;;
            target_image_id) export TARGET_IMAGE_ID="$var_value" ;;
            target_server_name) export TARGET_SERVER_NAME="$var_value" ;;
            eip_bandwidth_mbps) export EIP_BANDWIDTH_MBPS="$var_value" ;;
            root_volume_type) export ROOT_VOLUME_TYPE="$var_value" ;;
            rsync_source_host) export RSYNC_SOURCE_HOST="$var_value" ;;
            rsync_source_port) export RSYNC_SOURCE_PORT="$var_value" ;;
            rsync_source_user) export RSYNC_SOURCE_USER="$var_value" ;;
            rsync_source_password) export RSYNC_SOURCE_PASSWORD="$var_value" ;;
            target_rsync_ssh_key) export TARGET_RSYNC_SSH_KEY="$var_value" ;;
            rsync_incremental_rounds) export RSYNC_INCREMENTAL_ROUNDS="$var_value" ;;
        esac
    fi
done < terraform.tfvars

# Set defaults
export TARGET_FLAVOR_ID="${TARGET_FLAVOR_ID:-s6.large.2}"
if [[ -z "${TARGET_ADMIN_PASSWORD:-}" ]]; then
    echo "[AWS-TO-HUAWEI] TARGET_ADMIN_PASSWORD is required and must not be left empty/default." >&2
    exit 1
fi
export TARGET_ADMIN_PASSWORD
export RSYNC_TIMEOUT_SEC="${RSYNC_TIMEOUT_SEC:-7200}"
export RESULT_PATH="${RESULT_PATH:-./out/migration_result.json}"

echo "[AWS-TO-HUAWEI] Configuration loaded"
echo "[AWS-TO-HUAWEI] Source: $RSYNC_SOURCE_HOST"
echo "[AWS-TO-HUAWEI] Target Region: $TARGET_REGION"
echo "[AWS-TO-HUAWEI] Target Server: $TARGET_SERVER_NAME"

# Execute migration
python3 scripts/aws_to_huawei_direct.py
