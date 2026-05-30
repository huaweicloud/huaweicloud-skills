import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListServerAzInfoRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 可用区信息列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(zones):
    if not zones:
        print("没有找到 ECS 可用区信息")
        return

    output = f"availability_zone_id\ttype\n"
    for zone in zones:
        zone_id = getattr(zone, 'availability_zone_id', '')
        zone_type = getattr(zone, 'type', '')
        output += f"{zone_id}\t{zone_type}\n"

    output += f"\n共 {len(zones)} 条 ECS 可用区信息"
    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    request = ListServerAzInfoRequest()
    response = client.list_server_az_info(request)
    zones = response.availability_zones

    if not zones:
        print(f"没有找到 ECS 可用区信息 (区域: {Region})")
        exit(0)

    # API 不支持分页（无 marker/limit/offset）；一个 region 的可用区数量由云服务架构决定，通常为个位数，不会超过 PAGE_SIZE
    display_zones = zones[:PAGE_SIZE]

    # 渲染结果
    render(display_zones)
except Exception as e:
    print(f"ecs.server_az_info 查询失败: {e}")
    exit(1)
