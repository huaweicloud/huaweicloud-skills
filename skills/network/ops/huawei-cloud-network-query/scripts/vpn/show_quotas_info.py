import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkvpn.v5 import VpnClient
from huaweicloudsdkvpn.v5.model import ShowQuotasInfoRequest
from huaweicloudsdkvpn.v5.region.vpn_region import VpnRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 VPN 配额信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = VpnClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(VpnRegion.value_of(Region)).build()
    if not client:
        print("无法获取 VPN 客户端")
        exit(-1)

    request = ShowQuotasInfoRequest()
    response = client.show_quotas_info(request)
    quotas = response.quotas
    resources = getattr(quotas, 'resources', []) or []
    if not resources:
        print("没有找到配额信息")
        exit(0)

    output = f"type\tused\tquota\n"
    for r in resources:
        type_ = getattr(r, 'type', '')
        used = getattr(r, 'used', '')
        quota = getattr(r, 'quota', '')
        output += f"{type_}\t{used}\t{quota}\n"
    print(output)
except Exception as e:
    print(f"vpn.show_quotas_info 查询失败: {e}")
    exit(1)
