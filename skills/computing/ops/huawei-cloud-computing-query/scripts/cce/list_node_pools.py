import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ListNodePoolsRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数（ListNodePools 接口不支持分页，超出部分需 --all 展示）

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 集群节点池列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--show_default_node_pool", type=str, choices=["true", "false"], help="是否展示默认节点池，true/false，不传则默认不展示")
parser.add_argument("--advance_status", type=str, choices=["true", "false"], help="是否返回节点池的详细状态信息，true/false")
parser.add_argument("--all", action="store_true", help=f"展示全部节点池，默认最多展示 {PAGE_SIZE} 个")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

Region = args.region


# 渲染
def render(node_pools, total_count, has_more):
    if not node_pools:
        print("没有找到 CCE 节点池")
        return

    output = "id\tname\ttype\tflavor\tinitial_node_count\tcurrent_node\tautoscaling\tphase\tcreated\n"
    for node_pool in node_pools:
        metadata = getattr(node_pool, 'metadata', None)
        spec = getattr(node_pool, 'spec', None)
        status = getattr(node_pool, 'status', None)
        pool_id = getattr(metadata, 'uid', '') if metadata else ''
        name = getattr(metadata, 'name', '') if metadata else ''
        created = getattr(metadata, 'creation_timestamp', '') if metadata else ''
        ptype = getattr(spec, 'type', '') if spec else ''
        node_template = getattr(spec, 'node_template', None) if spec else None
        flavor = getattr(node_template, 'flavor', '') if node_template else ''
        initial_node_count = getattr(spec, 'initial_node_count', '') if spec else ''
        autoscaling = getattr(spec, 'autoscaling', None) if spec else None
        if autoscaling and getattr(autoscaling, 'enable', False):
            autoscaling_text = f"on({getattr(autoscaling, 'min_node_count', '')}-{getattr(autoscaling, 'max_node_count', '')})"
        else:
            autoscaling_text = "off"
        current_node = getattr(status, 'current_node', '') if status else ''
        phase = getattr(status, 'phase', '') if status else ''
        output += f"{pool_id}\t{name}\t{ptype}\t{flavor}\t{initial_node_count}\t{current_node}\t{autoscaling_text}\t{phase}\t{created}\n"

    # 汇总信息
    showing_count = len(node_pools)
    if has_more:
        output += f"\n共 {total_count} 个 CCE 节点池，当前展示前 {showing_count} 个（ListNodePools 接口不支持分页）"
        output += "\n可加 --all 展示全部，或使用 --show_default_node_pool true 一并查看默认节点池"
    else:
        output += f"\n共 {showing_count} 个 CCE 节点池"

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

    client = CceClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CceRegion.value_of(Region)).build()
    if not client:
        print("无法获取 CCE 客户端")
        exit(-1)

    # 构建请求，设置过滤参数
    request = ListNodePoolsRequest()
    request.cluster_id = args.cluster_id
    if args.show_default_node_pool:
        request.show_default_node_pool = args.show_default_node_pool
    if args.advance_status:
        request.advance_status = args.advance_status == "true"

    response = client.list_node_pools(request)
    node_pools = response.items or []
    display_pools = node_pools if args.all else node_pools[:PAGE_SIZE]

    # 渲染结果
    render(display_pools, len(node_pools), len(node_pools) > len(display_pools))
except Exception as e:
    print(f"cce.node_pools 查询失败: {e}")
    exit(1)
