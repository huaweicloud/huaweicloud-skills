import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ShowAssociatedResourcesRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询资源关联的企业项目资源")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--project_id", type=str, required=True, help="项目ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region_id", type=str, required=True, help="区域ID，如 cn-north-4")
parser.add_argument("--resource_id", type=str, required=True, help="资源ID")
parser.add_argument("--resource_type", type=str, required=True, help="资源类型，如 ecs, vpc, eip 等，可通过 list_providers.py 查询支持的类型")
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

    request = ShowAssociatedResourcesRequest()
    request.project_id = args.project_id
    request.region_id = args.region_id
    request.resource_id = args.resource_id
    request.resource_type = args.resource_type
    response = client.show_associated_resources(request)

    res_id = getattr(response, 'id', '')
    res_name = getattr(response, 'name', '')
    res_type = getattr(response, 'type', '')
    associated = getattr(response, 'associated_resources', []) or []
    errors = getattr(response, 'errors', []) or []

    output = f"id:\t{res_id}\n"
    output += f"name:\t{res_name}\n"
    output += f"type:\t{res_type}\n"

    if associated:
        output += f"\nassociated_resources:\n"
        for a in associated:
            a_id = getattr(a, 'id', '')
            a_name = getattr(a, 'name', '')
            a_type = getattr(a, 'type', '')
            output += f"  {a_id}\t{a_name}\t{a_type}\n"

    if errors:
        output += f"\nerrors:\n"
        for e in errors:
            e_code = getattr(e, 'code', '')
            e_msg = getattr(e, 'message', '')
            output += f"  {e_code}\t{e_msg}\n"

    print(output.strip())
except Exception as e:
    print(f"eps.show_associated_resources 查询失败: {e}")
    exit(1)
