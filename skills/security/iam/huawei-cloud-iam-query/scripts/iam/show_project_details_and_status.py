import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowProjectDetailsAndStatusRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 项目详情和状态 (v3)")
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

    request = ShowProjectDetailsAndStatusRequest()
    request.project_id = args.project_id
    response = client.show_project_details_and_status(request)
    item = response.project

    if not item:
        print(f"没有找到 IAM 项目 (区域: {Region}, 项目 ID: {args.project_id})")
        exit(0)

    id_ = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    enabled = getattr(item, 'enabled', '')
    status = getattr(item, 'status', '')
    parent_id = getattr(item, 'parent_id', '')
    is_domain = getattr(item, 'is_domain', '')
    domain_id = getattr(item, 'domain_id', '')
    description = getattr(item, 'description', '')
    print(f"id\tname\tenabled\tstatus\tparent_id\tis_domain\tdomain_id\tdescription\n{id_}\t{name}\t{enabled}\t{status}\t{parent_id}\t{is_domain}\t{domain_id}\t{description}")
except Exception as e:
    print(f"iam.show_project_details_and_status 查询失败: {e}")
    exit(1)
