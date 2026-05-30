import argparse
import sys
import os



sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import ListAgentDimensionInfoRequest, CesClient
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询Agent维度信息列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--instance_id", type=str, required=True, help="ECS实例ID（36位），可通过 scripts/ecs/list_servers_details.py 获取")
parser.add_argument("--dim_name", type=str, required=True, help="维度名称，枚举值：mount_point(挂载点)/disk(磁盘)/proc(进程)/gpu(显卡)/raid(RAID控制器)")
parser.add_argument("--dim_value", type=str, help="维度值，32位字符串")
parser.add_argument("--offset", type=int, help="分页偏移量，最小值0，最大值2147483647，默认0")
parser.add_argument("--limit", type=int, help="分页大小，最小值1，最大值1000，默认1000")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListAgentDimensionInfoRequest()
    request.instance_id = args.instance_id
    request.dim_name = args.dim_name
    if args.dim_value:
        request.dim_value = args.dim_value
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_agent_dimension_info(request)

    dimensions = getattr(response, 'dimensions', []) or []
    count = getattr(response, 'count', 0)

    if not dimensions:
        print("查询结果为空")
        exit(0)

    output = f"Agent维度信息列表（共{count}个）:\n"
    
    for dim in dimensions:
        name = getattr(dim, 'name', '')
        value = getattr(dim, 'value', '')
        origin_value = getattr(dim, 'origin_value', '')
        output += f"维度名称: {name}, 维度值: {value}, 实际维度信息: {origin_value}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_agent_dimension_info 查询失败: {e}")
    exit(1)
