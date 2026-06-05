import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowDomainQuotaRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 域配额 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--domain_id", type=str, required=True, help="账号 ID")
parser.add_argument("--type", type=str, choices=["user", "group", "idp", "agency", "policy", "assigment_group_mp", "assigment_agency_mp", "assigment_group_ep", "assigment_user_ep", "mapping"], help="配额类型，不填则返回所有类型")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = ShowDomainQuotaRequest()
    request.domain_id = args.domain_id
    if args.type:
        request.type = args.type
    response = client.show_domain_quota(request)
    quotas = response.quotas

    if not quotas:
        print(f"没有找到 IAM 域配额 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    resources = getattr(quotas, 'resources', []) or []
    if not resources:
        print(f"没有找到 IAM 域配额资源 (区域: {Region}, 域 ID: {args.domain_id})")
        exit(0)

    output = f"type\tused\tquota\tmin\tmax\n"
    for r in resources:
        type_ = getattr(r, 'type', '')
        used = getattr(r, 'used', '')
        quota = getattr(r, 'quota', '')
        min_ = getattr(r, 'min', '')
        max_ = getattr(r, 'max', '')
        output += f"{type_}\t{used}\t{quota}\t{min_}\t{max_}\n"
    print(output)
except Exception as e:
    print(f"iam.show_domain_quota 查询失败: {e}")
    exit(1)
