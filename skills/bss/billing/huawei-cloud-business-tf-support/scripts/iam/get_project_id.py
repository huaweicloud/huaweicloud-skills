import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import KeystoneListProjectsRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取指定区域的项目 ID")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域名称，如 cn-north-4、cn-east-3 等")
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

    request = KeystoneListProjectsRequest()
    request.name = Region
    response = client.keystone_list_projects(request)
    projects = response.projects
    if not projects:
        print(f"未找到可访问的项目 (区域: {Region})")
        exit(0)

    # 按 region 名称匹配项目（项目名称通常就是区域名）
    for project in projects:
        if getattr(project, 'name', '') == Region:
            print(project.id)
            exit(0)

    # 未精确匹配，返回第一个项目
    print(projects[0].id)
except Exception as e:
    print(f"获取项目 ID 失败: {e}")
    exit(1)
