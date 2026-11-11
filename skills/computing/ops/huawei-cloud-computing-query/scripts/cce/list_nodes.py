import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id, format_api_error, format_empty_result
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ListNodesRequest, ListNodePoolsRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
API_LIMIT = 100  # 服务端单次请求上限

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 集群节点列表（支持全量分页）")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, help="区域，不传时回退环境变量 HW_REGION_NAME（默认 cn-north-4）")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--limit", type=int, help=f"每页展示条数，默认 {PAGE_SIZE}，服务端单次请求上限 {API_LIMIT}")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--all", action="store_true", help="自动翻页拉取全部节点（避免节点数超过一页时漏数据）")
parser.add_argument("--verify", action="store_true", help="与节点池 current_node 汇总数交叉校验节点总数（额外调用 ListNodePools）")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

if args.region is not None:
    Region = args.region

# 参数校验
if args.limit is not None and args.limit <= 0:
    print("--limit 必须为正整数")
    exit(1)

display_limit = args.limit if args.limit else PAGE_SIZE
if display_limit > API_LIMIT:
    display_limit = API_LIMIT


# 渲染
def render(nodes, showing_count, has_more, next_marker):
    if not nodes:
        print(format_empty_result(
            "CCE 节点", Region, args.project_id, f"集群 ID: {args.cluster_id}",
            hints=[
                "确认集群 ID 正确（可由 list_clusters.py 获取）",
                "确认集群属于当前 --region 对应的项目",
                "确认账号具备 cce:node:list 权限（或 CCEReadOnlyPolicy）",
                "集群刚创建时节点可能仍在创建中，可稍后重试",
            ]))
        return

    output = "id\tname\tstatus\tflavor\taz\tprivate_ip\tpublic_ip\tserver_id\tcreated\n"
    for node in nodes:
        metadata = getattr(node, 'metadata', None)
        spec = getattr(node, 'spec', None)
        status = getattr(node, 'status', None)
        nid = getattr(metadata, 'uid', '') if metadata else ''
        name = getattr(metadata, 'name', '') if metadata else ''
        created = getattr(metadata, 'creation_timestamp', '') if metadata else ''
        phase = getattr(status, 'phase', '') if status else ''
        private_ip = getattr(status, 'private_ip', '') if status else ''
        public_ip = getattr(status, 'public_ip', '') if status else ''
        server_id = getattr(status, 'server_id', '') if status else ''
        flavor = getattr(spec, 'flavor', '') if spec else ''
        az = getattr(spec, 'az', '') if spec else ''
        output += f"{nid}\t{name}\t{phase}\t{flavor}\t{az}\t{private_ip}\t{public_ip}\t{server_id}\t{created}\n"

    # 汇总信息
    if has_more:
        output += f"\n当前返回 {showing_count} 条 CCE 节点，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或加 --all 一次拉取全部"
        else:
            output += "\n可使用 --limit 调整每页条数，或使用 --cluster_id 确认集群范围"
    else:
        output += f"\n共 {showing_count} 条 CCE 节点"

    print(output)


# 全量翻页拉取（按 marker 循环，去重并自校验）
def fetch_all_nodes(client):
    all_nodes = []
    seen = set()
    marker = ""
    while True:
        request = ListNodesRequest()
        request.cluster_id = args.cluster_id
        request.limit = API_LIMIT
        if marker:
            request.marker = marker
        response = client.list_nodes(request)
        nodes = response.items or []
        if not nodes:
            break
        for node in nodes:
            nid = getattr(getattr(node, 'metadata', None), 'uid', '')
            if nid and nid in seen:
                continue
            if nid:
                seen.add(nid)
            all_nodes.append(node)
        page_info = getattr(response, 'page_info', None)
        next_marker = getattr(page_info, 'next_marker', None) if page_info else None
        if len(nodes) < API_LIMIT and not next_marker:
            break
        if not next_marker or next_marker == marker:
            break
        marker = next_marker
    return all_nodes


# 与节点池 current_node 汇总数交叉校验
def verify_with_node_pools(client):
    try:
        request = ListNodePoolsRequest()
        request.cluster_id = args.cluster_id
        request.show_default_node_pool = "true"
        response = client.list_node_pools(request)
        pools = response.items or []
    except Exception as e:
        print(f"\n[校验] 无法获取节点池数据: {e}")
        return None
    total = 0
    for pool in pools:
        status = getattr(pool, 'status', None)
        current = getattr(status, 'current_node', None) if status else None
        if isinstance(current, int):
            total += current
    return total


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

    if args.all:
        all_nodes = fetch_all_nodes(client)
        render(all_nodes, len(all_nodes), False, None)
        if args.verify:
            pool_total = verify_with_node_pools(client)
            if pool_total is None:
                pass
            elif pool_total == len(all_nodes):
                print(f"\n[校验] 通过: 节点列表 {len(all_nodes)} 条与节点池 current_node 汇总一致")
            else:
                print(f"\n[校验] 不一致: 节点列表 {len(all_nodes)} 条，节点池 current_node 汇总 {pool_total} 条。"
                      "若差值来自正在创建/删除的节点属正常；持续不一致请核对节点池与集群范围")
        exit(0)

    # 构建请求，多查1条用于判断是否还有更多
    request = ListNodesRequest()
    request.cluster_id = args.cluster_id
    request.limit = min(display_limit + 1, API_LIMIT)
    if args.marker:
        request.marker = args.marker

    response = client.list_nodes(request)
    nodes = response.items or []

    if not nodes:
        render([], 0, False, None)
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    page_info = getattr(response, 'page_info', None)
    next_marker = getattr(page_info, 'next_marker', None) if page_info else None
    has_more = len(nodes) > display_limit or bool(next_marker)

    # 只展示前 display_limit 条
    display_nodes = nodes[:display_limit]

    # 渲染结果
    render(display_nodes, len(display_nodes), has_more, next_marker)
except Exception as e:
    print(format_api_error(e, "CCE 节点列表查询", Region, args.project_id, f"集群 ID: {args.cluster_id}"))
    exit(1)