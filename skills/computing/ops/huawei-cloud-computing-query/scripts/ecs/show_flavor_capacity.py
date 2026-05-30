import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowFlavorCapacityRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 规格容量")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--flavor_id", type=str, required=True, help="规格 ID，可通过 list_flavors.py 获取")
parser.add_argument("--count", type=int, help="数量")
parser.add_argument("--region_ids", type=str, help="区域 ID 列表，逗号分隔")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


# 渲染
def render(resources):
    total = len(resources)
    if Offset >= total:
        print(f"查询结果为空\n\nECS 规格容量列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"availability_zone\tregion_id\tprefer\n"
    for i in range(Offset, min(total, Offset + 50)):
        r = resources[i]
        availability_zone = getattr(r, 'availability_zone', '')
        region_id = getattr(r, 'region_id', '')
        prefer = str(getattr(r, 'prefer', ''))
        output += f"{availability_zone}\t{region_id}\t{prefer}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\nECS 规格容量列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = ShowFlavorCapacityRequest()
    request.flavor_id = args.flavor_id
    if args.count is not None:
        request.count = args.count
    if args.region_ids:
        request.region_ids = args.region_ids
    response = client.show_flavor_capacity(request)
    resources = response.resources

    if not resources:
        print(f"没有找到 ECS 规格容量 (区域: {Region}, 规格 ID: {args.flavor_id})")
        exit(0)

    # 渲染结果
    render(resources)
except Exception as e:
    print(f"ecs.flavor_capacity 查询失败: {e}")
    exit(1)
