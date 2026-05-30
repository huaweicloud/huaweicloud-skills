import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListResourceGroupsServicesResourcesRequest
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询资源分组服务资源列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--group_id", type=str, required=True, help="资源分组ID，可通过 list_resource_groups.py 获取")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=str, help="分页大小，范围1-1000，默认1000")
parser.add_argument("--service", type=str, help="服务命名空间，格式service.item")
parser.add_argument("--dim_name", type=str, help="资源维度名称，如instance_id")
parser.add_argument("--status", type=str, help="资源状态，枚举值：HEALTHY/UNHEALTHY/NOT_EXIST")
parser.add_argument("--dim_value", type=str, help="资源维度值")
parser.add_argument("--tag", type=str, help="标签，格式key=value")
parser.add_argument("--extend_relation_id", type=str, help="关联编号")
parser.add_argument("--product_name", type=str, help="云产品名称，如SYS.ECS,instance_id")
parser.add_argument("--resource_name", type=str, help="资源名称")
parser.add_argument("--event_status", type=str, help="事件状态，枚举值：HEALTHY/UNHEALTHY/NOT_EXIST")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListResourceGroupsServicesResourcesRequest()
    request.group_id = args.group_id
    if args.offset is not None:
        request.offset = args.offset
    if args.limit:
        request.limit = args.limit
    if args.service:
        request.service = args.service
    if args.dim_name:
        request.dim_name = args.dim_name
    if args.status:
        request.status = args.status
    if args.dim_value:
        request.dim_value = args.dim_value
    if args.tag:
        request.tag = args.tag
    if args.extend_relation_id:
        request.extend_relation_id = args.extend_relation_id
    if args.product_name:
        request.product_name = args.product_name
    if args.resource_name:
        request.resource_name = args.resource_name
    if args.event_status:
        request.event_status = args.event_status

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_resource_groups_services_resources(request)

    resources = getattr(response, 'resources', []) or []
    count = getattr(response, 'count', 0)

    if not resources:
        print("查询结果为空")
        exit(0)

    output = f"资源分组 {args.group_id} 的服务资源列表（共{count}个）:\n"
    
    for idx, resource in enumerate(resources, 1):
        status = getattr(resource, 'status', '')
        resource_name = getattr(resource, 'resource_name', '')
        dimensions = getattr(resource, 'dimensions', []) or []
        output += f"资源 {idx} (状态: {status}, 名称: {resource_name}):\n"
        for dim in dimensions:
            name = getattr(dim, 'name', '')
            value = getattr(dim, 'value', '')
            output += f"  {name}: {value}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_resource_groups_services_resources 查询失败: {e}")
    exit(1)
