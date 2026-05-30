import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ListServerBlockDevicesRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 服务器块设备列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--server_id", type=str, required=True, help="服务器 ID（UUID），可通过 list_servers_details.py 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: size；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by size:desc --top 3 查找最大的 3 个磁盘")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by size:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('size',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: size；方向可选: asc, desc。例如 size:desc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)


# 渲染
def render(attachments, has_more=False):
    if not attachments:
        print("没有找到 ECS 服务器块设备")
        return

    output = f"volume_id\tboot_index\tdevice\tsize(GB)\n"
    for att in attachments:
        volume_id = getattr(att, 'volume_id', '')
        boot_index = str(getattr(att, 'boot_index', ''))
        device = getattr(att, 'device', '')
        size = str(getattr(att, 'size', ''))
        output += f"{volume_id}\t{boot_index}\t{device}\t{size}\n"

    showing_count = len(attachments)
    if has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
    else:
        output += f"\n共 {showing_count} 条 ECS 服务器块设备"
    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    request = ListServerBlockDevicesRequest()
    request.server_id = args.server_id
    response = client.list_server_block_devices(request)
    attachments = response.volume_attachments

    if not attachments:
        print(f"没有找到 ECS 服务器块设备 (区域: {Region}, 服务器 ID: {args.server_id})")
        exit(0)

    # API 不支持分页（无 marker/limit/offset），一次返回全部数据

    if args.sort_by:
        # 有排序参数：在全量数据上排序 + 截取
        sort_field, sort_dir = args.sort_by.split(':')
        if sort_field == 'size':
            attachments.sort(key=lambda a: int(getattr(a, 'size', 0) or 0), reverse=(sort_dir == 'desc'))

        if args.top is not None:
            display_attachments = attachments[:args.top]
        else:
            display_attachments = attachments[:PAGE_SIZE]

        has_more = len(attachments) > len(display_attachments)
        render(display_attachments, has_more=has_more)
    else:
        # 无排序参数：原有逻辑
        has_more = len(attachments) > PAGE_SIZE
        display_attachments = attachments[:PAGE_SIZE]
        render(display_attachments, has_more=has_more)
except Exception as e:
    print(f"ecs.server_block_devices 查询失败: {e}")
    exit(1)
