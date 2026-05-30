import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ShowSpecifiedVersionRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询BMS API指定版本信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--api_version", type=str, required=True, help="API版本号，如 v1")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求
    request = ShowSpecifiedVersionRequest()
    request.api_version = args.api_version

    response = client.show_specified_version(request)
    version = response.version

    if not version:
        print(f"没有找到API版本信息 (区域: {Region}, 版本: {args.api_version})")
        exit(0)

    # 渲染
    output = ""
    output += f"id: {getattr(version, 'id', '')}\n"
    output += f"status: {getattr(version, 'status', '')}\n"
    output += f"min_version: {getattr(version, 'min_version', '')}\n"
    output += f"version: {getattr(version, 'version', '')}\n"
    output += f"updated: {getattr(version, 'updated', '')}\n"
    links = getattr(version, 'links', None) or []
    if links:
        output += f"links:\n"
        for link in links:
            output += f"  - rel: {getattr(link, 'rel', '')}, href: {getattr(link, 'href', '')}\n"

    print(output)
except Exception as e:
    print(f"bms.show_specified_version 查询失败: {e}")
    exit(1)
