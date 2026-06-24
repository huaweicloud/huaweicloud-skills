import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListServerTagsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器标签列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
args = parser.parse_args()

Region = args.region


# 渲染
def render(tags, has_more=False):
    if not tags:
        print("没有找到 ECS 服务器标签")
        return

    output = f"key\tvalues\n"
    for tag in tags:
        key = getattr(tag, 'key', '')
        values = getattr(tag, 'values', '')
        if isinstance(values, list):
            values = ','.join(str(v) for v in values)
        output += f"{key}\t{values}\n"

    showing_count = len(tags)
    if has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
    else:
        output += f"\n共 {showing_count} 条 ECS 服务器标签"
    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)


    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    request = ListServerTagsRequest()
    response = client.list_server_tags(request)
    tags = response.tags

    if not tags:
        print(f"没有找到 ECS 服务器标签 (区域: {Region})")
        exit(0)

    # API 不支持分页（无 marker/limit/offset），一次返回全部数据
    has_more = len(tags) > PAGE_SIZE
    display_tags = tags[:PAGE_SIZE]

    # 渲染结果
    render(display_tags, has_more=has_more)
except Exception as e:
    print(f"ecs.server_tags 查询失败: {e}")
    exit(1)
