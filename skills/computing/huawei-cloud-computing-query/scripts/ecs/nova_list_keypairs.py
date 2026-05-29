import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import NovaListKeypairsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS SSH 密钥对列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(keypairs, has_more=False, next_marker=None):
    if not keypairs:
        print("没有找到 SSH 密钥对")
        return

    output = f"name\ttype\tfingerprint\n"
    for kp_result in keypairs:
        kp = getattr(kp_result, 'keypair', None)
        if not kp:
            continue
        name = getattr(kp, 'name', '')
        kp_type = getattr(kp, 'type', '')
        fingerprint = getattr(kp, 'fingerprint', '')
        output += f"{name}\t{kp_type}\t{fingerprint}\n"

    # 汇总信息
    showing_count = len(keypairs)
    if has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页"
    else:
        output += f"\n共 {showing_count} 条 SSH 密钥对"
    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 ECS 客户端")
        exit(-1)

    # 构建请求
    request = NovaListKeypairsRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker

    # 只做一次查询
    response = client.nova_list_keypairs(request)
    keypairs = response.keypairs

    if not keypairs:
        print(f"没有找到 SSH 密钥对 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据
    # 此 API 的 marker 是 keypair 的 name
    has_more = len(keypairs) > PAGE_SIZE
    next_marker = None
    if has_more:
        last_kp = keypairs[PAGE_SIZE - 1].keypair if keypairs[PAGE_SIZE - 1].keypair else None
        next_marker = getattr(last_kp, 'name', None) if last_kp else None

    # 只展示前 PAGE_SIZE 条
    display_keypairs = keypairs[:PAGE_SIZE]

    # 渲染结果
    render(display_keypairs, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"ecs.nova_list_keypairs 查询失败: {e}")
    exit(1)
