import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id, format_api_error, format_empty_result
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ListNodePoolsRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 参数
parser = argparse.ArgumentParser(description="按标签/标签(label)过滤 CCE 节点池（客户端过滤）")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, help="区域，不传时回退环境变量 HW_REGION_NAME（默认 cn-north-4）")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--tag", type=str, action="append", metavar="key=value",
                    help="按节点池 userTags 过滤，可重复指定，多个标签之间为 AND 关系，例如 --tag env=prod")
parser.add_argument("--label", type=str, action="append", metavar="key=value",
                    help="按节点池 k8s tags（Kubernetes label）过滤，可重复指定，多个之间为 AND 关系，例如 --label zone=a")
parser.add_argument("--include_default", action="store_true", help="一并查询默认节点池（show_default_node_pool=true）")
parser.add_argument("--advance_status", type=str, choices=["true", "false"], help="是否返回节点池详细状态，true/false")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

if args.region is not None:
    Region = args.region


def parse_pairs(items, option):
    pairs = []
    for item in items or []:
        if '=' not in item or not item.split('=', 1)[0]:
            print(f"{option} 格式错误，应为 key=value，例如 {option} env=prod，可重复指定多个标签")
            exit(1)
        key, value = item.split('=', 1)
        pairs.append((key, value))
    return pairs


tag_filters = parse_pairs(args.tag, "--tag")
label_filters = parse_pairs(args.label, "--label")
if not tag_filters and not label_filters:
    print("至少指定一个过滤条件：--tag key=value 或 --label key=value")
    exit(1)


def node_template_of(pool):
    spec = getattr(pool, 'spec', None)
    return getattr(spec, 'node_template', None) if spec else None


def user_tags_text(pool):
    tags = getattr(node_template_of(pool), 'user_tags', None)
    return ','.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags) if tags else '-'


def k8s_tags_text(pool):
    tags = getattr(node_template_of(pool), 'k8s_tags', None)
    return ','.join(f"{k}={v}" for k, v in tags.items()) if tags else '-'


def matches(pool):
    user_tags = getattr(node_template_of(pool), 'user_tags', None) or []
    user_map = {getattr(t, 'key', ''): getattr(t, 'value', '') for t in user_tags}
    k8s_tags = getattr(node_template_of(pool), 'k8s_tags', None) or {}

    for key, value in tag_filters:
        if user_map.get(key) != value:
            return False
    for key, value in label_filters:
        if k8s_tags.get(key) != value:
            return False
    return True


def render(pools, total):
    if not pools:
        print(format_empty_result(
            "匹配条件的 CCE 节点池", Region, args.project_id, f"集群 ID: {args.cluster_id}",
            hints=[
                "去掉部分 --tag / --label 条件后重试",
                "使用 list_node_pools.py 查看全部节点池的 user_tags / k8s_tags 后再过滤",
                "默认节点池默认不展示，可加 --include_default",
            ]))
        print(f"\n共 {total} 个节点池，匹配 0 个")
        return

    output = "id\tname\tphase\tcurrent_node\tflavor\tuser_tags\tk8s_tags\tcreated\n"
    for pool in pools:
        metadata = getattr(pool, 'metadata', None)
        status = getattr(pool, 'status', None)
        node_template = node_template_of(pool)
        pool_id = getattr(metadata, 'uid', '') if metadata else ''
        name = getattr(metadata, 'name', '') if metadata else ''
        created = getattr(metadata, 'creation_timestamp', '') if metadata else ''
        phase = getattr(status, 'phase', '') if status else ''
        current_node = getattr(status, 'current_node', '') if status else ''
        flavor = getattr(node_template, 'flavor', '') if node_template else ''
        output += (f"{pool_id}\t{name}\t{phase}\t{current_node}\t{flavor}\t"
                   f"{user_tags_text(pool)}\t{k8s_tags_text(pool)}\t{created}\n")

    output += f"\n共 {total} 个节点池，匹配 {len(pools)} 个"
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

    request = ListNodePoolsRequest()
    request.cluster_id = args.cluster_id
    if args.include_default:
        request.show_default_node_pool = "true"
    if args.advance_status:
        request.advance_status = args.advance_status == "true"

    response = client.list_node_pools(request)
    pools = response.items or []
    matched = [pool for pool in pools if matches(pool)]

    render(matched, len(pools))
except Exception as e:
    print(format_api_error(e, "CCE 节点池标签过滤查询", Region, args.project_id,
                           f"集群 ID: {args.cluster_id}"))
    exit(1)