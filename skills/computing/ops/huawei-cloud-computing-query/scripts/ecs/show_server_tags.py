import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowServerTagsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器标签详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


# 渲染
def render(tags):
    total = len(tags)
    if Offset >= total:
        print(f"查询结果为空\n\nECS 服务器标签列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"key\tvalue\n"
    for i in range(Offset, min(total, Offset + 50)):
        tag = tags[i]
        key = getattr(tag, 'key', '')
        value = getattr(tag, 'value', '')
        output += f"{key}\t{value}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\nECS 服务器标签列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    request = ShowServerTagsRequest()
    request.server_id = args.server_id
    response = client.show_server_tags(request)
    tags = response.tags

    if not tags:
        print(f"没有找到 ECS 服务器标签 (区域: {Region}, 服务器 ID: {args.server_id})")
        exit(0)

    # 渲染结果
    render(tags)
except Exception as e:
    print(f"ecs.server_tags_detail 查询失败: {e}")
    exit(1)
