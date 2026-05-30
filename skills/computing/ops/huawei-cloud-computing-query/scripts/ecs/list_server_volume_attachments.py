import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListServerVolumeAttachmentsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器挂载卷列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(attachments, has_more=False):
    if not attachments:
        print("没有找到 ECS 服务器挂载卷")
        return

    output = f"id\tdevice\tserver_id\tvolume_id\n"
    for att in attachments:
        aid = getattr(att, 'id', '')
        device = getattr(att, 'device', '')
        server_id = getattr(att, 'server_id', '')
        volume_id = getattr(att, 'volume_id', '')
        output += f"{aid}\t{device}\t{server_id}\t{volume_id}\n"

    showing_count = len(attachments)
    if has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
    else:
        output += f"\n共 {showing_count} 条 ECS 服务器挂载卷"
    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    request = ListServerVolumeAttachmentsRequest()
    request.server_id = args.server_id
    response = client.list_server_volume_attachments(request)
    attachments = response.volume_attachments

    if not attachments:
        print(f"没有找到 ECS 服务器挂载卷 (区域: {Region}, 服务器 ID: {args.server_id})")
        exit(0)

    # API 不支持分页（无 marker/limit/offset），一次返回全部数据
    has_more = len(attachments) > PAGE_SIZE
    display_attachments = attachments[:PAGE_SIZE]

    # 渲染结果
    render(display_attachments, has_more=has_more)
except Exception as e:
    print(f"ecs.server_volume_attachments 查询失败: {e}")
    exit(1)
