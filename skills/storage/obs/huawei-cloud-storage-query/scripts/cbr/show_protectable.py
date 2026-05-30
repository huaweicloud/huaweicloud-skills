import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowProtectableRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 可保护资源详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--protectable_type", type=str, required=True, help="可保护性类型，可选参数为server,disk,turbo,workspace和workspace_v2")
parser.add_argument("--instance_id", type=str, required=True, help="资源实例ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowProtectableRequest()
    request.protectable_type = args.protectable_type
    request.instance_id = args.instance_id
    response = client.show_protectable(request)
    instance = getattr(response, 'instance', None)

    if not instance:
        print(f"没有找到可保护资源 (区域: {Region}, 实例 ID: {args.instance_id})")
        exit(0)

    output = ""
    output += f"id: {getattr(instance, 'id', '')}\n"
    output += f"name: {getattr(instance, 'name', '')}\n"
    output += f"type: {getattr(instance, 'type', '')}\n"
    output += f"size: {getattr(instance, 'size', '')}\n"
    output += f"status: {getattr(instance, 'status', '')}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_protectable 查询失败: {e}")
    exit(1)
