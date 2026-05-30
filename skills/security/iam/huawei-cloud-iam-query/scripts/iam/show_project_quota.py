import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowProjectQuotaRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 项目配额 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 get_project_id.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = ShowProjectQuotaRequest()
    request.project_id = args.project_id
    response = client.show_project_quota(request)
    quotas = response.quotas

    if not quotas:
        print(f"没有找到 IAM 项目配额 (区域: {Region}, 项目 ID: {args.project_id})")
        exit(0)

    resources = getattr(quotas, 'resources', []) or []
    if not resources:
        print(f"没有找到 IAM 项目配额资源 (区域: {Region}, 项目 ID: {args.project_id})")
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
    print(f"iam.show_project_quota 查询失败: {e}")
    exit(1)
