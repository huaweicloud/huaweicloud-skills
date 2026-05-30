import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ShowEnterpriseProjectRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目详情")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--enterprise_project_id", type=str, required=True, help="企业项目ID，可通过 list_enterprise_projects.py 获取")
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

    request = ShowEnterpriseProjectRequest()
    request.enterprise_project_id = args.enterprise_project_id
    response = client.show_enterprise_project(request)

    ep = response.enterprise_project
    if not ep:
        print(f"没有找到企业项目 (ID: {args.enterprise_project_id})")
        exit(0)

    ep_id = getattr(ep, 'id', '')
    name = getattr(ep, 'name', '')
    status = getattr(ep, 'status', '')
    status_str = {1: '启用', 2: '停用'}.get(status, str(status))
    ep_type = getattr(ep, 'type', '')
    description = getattr(ep, 'description', '')
    created_at = getattr(ep, 'created_at', '')
    updated_at = getattr(ep, 'updated_at', '')
    delete_flag = getattr(ep, 'delete_flag', False)

    output = f"id:\t{ep_id}\n"
    output += f"name:\t{name}\n"
    output += f"status:\t{status_str}\n"
    output += f"type:\t{ep_type}\n"
    output += f"description:\t{description}\n"
    output += f"created_at:\t{created_at}\n"
    output += f"updated_at:\t{updated_at}\n"
    output += f"delete_flag:\t{delete_flag}"
    print(output)
except Exception as e:
    print(f"eps.show_enterprise_project 查询失败: {e}")
    exit(1)
