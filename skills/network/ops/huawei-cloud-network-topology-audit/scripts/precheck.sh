#!/usr/bin/bash
# Precheck Script — Step 1: Verify Huawei Cloud credentials and VPC API reachability
# Exit 0 on success, non-zero on failure

set -e

echo "[precheck] Checking Huawei Cloud credentials..."

# Check for AK/SK environment variables
check_cred_env() {
    for var in HUAWEICLOUD_SDK_AK HUAWEICLOUD_SDK_SK HW_ACCESS_KEY HW_SECRET_KEY HWC_AK HWC_SK; do
        if [ -n "${!var}" ]; then
            return 0
        fi
    done
    return 1
}

# Check hcloud CLI config
check_hcloud_config() {
    if command -v hcloud &>/dev/null; then
        if hcloud configure list &>/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

if check_cred_env; then
    echo "[precheck] Credentials found in environment variables"
elif check_hcloud_config; then
    echo "[precheck] Credentials found in hcloud CLI config"
else
    echo "[precheck] FAILED: No Huawei Cloud credentials found."
    echo "[precheck] Please set one of:"
    echo "  - HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK"
    echo "  - HW_ACCESS_KEY / HW_SECRET_KEY"
    echo "  - HWC_AK / HWC_SK"
    echo "  - Or configure hcloud CLI: hcloud configure set"
    exit 1
fi

echo "[precheck] Checking Python availability..."
if ! python3 --version &>/dev/null; then
    echo "[precheck] FAILED: Python 3 not found"
    exit 1
fi

echo "[precheck] Testing VPC API reachability..."

# Try hcloud first
if command -v hcloud &>/dev/null; then
    if hcloud VPC ListVpcs --cli-region=cn-north-4 --limit=1 &>/dev/null 2>&1; then
        echo "[precheck] VPC API reachable via hcloud"
        echo "[precheck] PASS"
        exit 0
    fi
fi

# Fallback: try Python SDK
if python3 -c "
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient, ListVpcsRequest
import os

ak = os.environ.get('HUAWEICLOUD_SDK_AK') or os.environ.get('HW_ACCESS_KEY') or ''
sk = os.environ.get('HUAWEICLOUD_SDK_SK') or os.environ.get('HW_SECRET_KEY') or ''

creds = BasicCredentials(ak, sk)
client = VpcClient.new_builder().with_credentials(creds).with_region('cn-north-4').build()
request = ListVpcsRequest(limit=1)
response = client.list_vpcs(request)
print(f'VPCs found: {len(response.vpcs) if response.vpcs else 0}')
" &>/dev/null 2>&1; then
    echo "[precheck] VPC API reachable via Python SDK"
    echo "[precheck] PASS"
    exit 0
fi

echo "[precheck] FAILED: Cannot reach VPC API. Check credentials and network connectivity."
exit 1