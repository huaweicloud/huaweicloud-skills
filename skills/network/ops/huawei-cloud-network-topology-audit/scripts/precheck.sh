#!/usr/bin/bash
# Precheck Script — Step 1: Verify Huawei Cloud credentials and VPC API reachability
#
# Credentials (first complete pair wins, same order as scripts/query-dcs-instances.py):
#   HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK
#   HUAWEI_ACCESS_KEY  / HUAWEI_SECRET_KEY
#   HW_ACCESS_KEY      / HW_SECRET_KEY
#   HWC_AK             / HWC_SK
#   HWC_ACCESS_KEY     / HWC_SECRET_KEY
#   hcloud CLI profile (hcloud configure set)
#
# Exit 0 on success, 1 on missing credentials / dependency, 2 when the API is unreachable.

set -e

REGION="${HUAWEI_REGION:-cn-north-4}"

echo "[precheck] Checking Huawei Cloud credentials..."

check_pair() {
    local ak_var="$1" sk_var="$2"
    if [ -n "${!ak_var:-}" ] && [ -n "${!sk_var:-}" ]; then
        CRED_SOURCE="$ak_var / $sk_var"
        return 0
    fi
    return 1
}

check_cred_env() {
    local prefix
    check_pair "HUAWEICLOUD_SDK_AK" "HUAWEICLOUD_SDK_SK" && return 0
    for prefix in HUAWEI HW; do
        check_pair "${prefix}_ACCESS_KEY" "${prefix}_SECRET_KEY" && return 0
    done
    check_pair "HWC_AK" "HWC_SK" && return 0
    check_pair "HWC_ACCESS_KEY" "HWC_SECRET_KEY" && return 0
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
    echo "[precheck] Credentials found in environment variables ($CRED_SOURCE)"
elif check_hcloud_config; then
    echo "[precheck] Credentials found in hcloud CLI config"
else
    echo "[precheck] FAILED: No Huawei Cloud credentials found." >&2
    echo "[precheck] Please set one complete AK/SK pair:" >&2
    echo "  - HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK" >&2
    echo "  - HUAWEI_ACCESS_KEY / HUAWEI_SECRET_KEY" >&2
    echo "  - HW_ACCESS_KEY / HW_SECRET_KEY" >&2
    echo "  - HWC_AK / HWC_SK" >&2
    echo "  - HWC_ACCESS_KEY / HWC_SECRET_KEY" >&2
    echo "  - Or configure hcloud CLI: hcloud configure set --cli-region=$REGION" >&2
    exit 1
fi

echo "[precheck] Checking Python availability..."
if ! python3 --version &>/dev/null; then
    echo "[precheck] FAILED: Python 3 not found" >&2
    exit 1
fi

echo "[precheck] Testing VPC API reachability..."

# Try hcloud first
if command -v hcloud &>/dev/null; then
    if hcloud VPC ListVpcs --cli-region="$REGION" --limit=1 &>/dev/null 2>&1; then
        echo "[precheck] VPC API reachable via hcloud"
        echo "[precheck] PASS"
        exit 0
    fi
fi

# Fallback: try Python SDK with the same credential order as query-dcs-instances.py
if python3 - "$REGION" <<'PY' &>/dev/null 2>&1; then
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpc.v2 import VpcClient, ListVpcsRequest
import os
import sys

pairs = [
    ("HUAWEICLOUD_SDK_AK", "HUAWEICLOUD_SDK_SK"),
    ("HUAWEI_ACCESS_KEY", "HUAWEI_SECRET_KEY"),
    ("HW_ACCESS_KEY", "HW_SECRET_KEY"),
    ("HWC_AK", "HWC_SK"),
    ("HWC_ACCESS_KEY", "HWC_SECRET_KEY"),
]
ak = sk = ""
for ak_var, sk_var in pairs:
    if os.environ.get(ak_var) and os.environ.get(sk_var):
        ak, sk = os.environ[ak_var], os.environ[sk_var]
        break
if not ak or not sk:
    sys.exit(1)

region = sys.argv[1]
creds = BasicCredentials(ak, sk)
client = VpcClient.new_builder().with_credentials(creds).with_region(region).build()
request = ListVpcsRequest(limit=1)
response = client.list_vpcs(request)
print(f"VPCs found: {len(response.vpcs) if response.vpcs else 0}")
PY
    echo "[precheck] VPC API reachable via Python SDK"
    echo "[precheck] PASS"
    exit 0
fi

echo "[precheck] FAILED: Cannot reach VPC API. Check credentials, region ($REGION) and network connectivity." >&2
exit 2