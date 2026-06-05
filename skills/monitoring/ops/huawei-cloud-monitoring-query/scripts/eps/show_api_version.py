import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ShowApiVersionRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目API版本详情")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--api_version", type=str, required=True, help="版本号，如 v1.0")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EpsClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(EpsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EPS 客户端")
        exit(-1)

    request = ShowApiVersionRequest()
    request.api_version = args.api_version
    response = client.show_api_version(request)

    version = response.version
    if not version:
        print(f"没有找到API版本 (版本号: {args.api_version})")
        exit(0)

    v_id = getattr(version, 'id', '')
    status = getattr(version, 'status', '')
    updated = getattr(version, 'updated', '')
    links = getattr(version, 'links', []) or []

    output = f"id:\t{v_id}\n"
    output += f"status:\t{status}\n"
    output += f"updated:\t{updated}\n"
    if links:
        link_str = '; '.join([f"{getattr(l, 'rel', '')}:{getattr(l, 'href', '')}" for l in links])
        output += f"links:\t{link_str}"
    print(output)
except Exception as e:
    print(f"eps.show_api_version 查询失败: {e}")
    exit(1)
