import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ListNodesRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 100  # 服务端单次请求上限

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 集群节点列表")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--limit", type=int, help=f"每页展示条数，默认 {PAGE_SIZE}，服务端单次请求上限 {API_LIMIT}")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

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
        print("没有找到 CCE 节点")
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
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --limit 调整每页条数"
        else:
            output += "\n可使用 --limit 调整每页条数，或使用 --cluster_id 确认集群范围"
    else:
        output += f"\n共 {showing_count} 条 CCE 节点"

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

    # 构建请求，多查1条用于判断是否还有更多
    request = ListNodesRequest()
    request.cluster_id = args.cluster_id
    request.limit = min(display_limit + 1, API_LIMIT)
    if args.marker:
        request.marker = args.marker

    response = client.list_nodes(request)
    nodes = response.items or []

    if not nodes:
        print(f"没有找到 CCE 节点 (区域: {Region}, 集群 ID: {args.cluster_id})")
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
    print(f"cce.nodes 查询失败: {e}")
    exit(1)
