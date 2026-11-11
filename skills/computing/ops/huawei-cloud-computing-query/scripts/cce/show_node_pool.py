import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id, format_api_error, format_empty_result
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ShowNodePoolRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 节点池详情")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, help="区域，不传时回退环境变量 HW_REGION_NAME（默认 cn-north-4）")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
parser.add_argument("--nodepool_id", type=str, required=True, help="节点池 ID（UUID），可通过 list_node_pools.py 获取")
parser.add_argument("--advance_status", type=str, choices=["true", "false"], help="是否返回节点池详细状态，true/false")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

if args.region is not None:
    Region = args.region


def _volume_text(volume):
    if not volume:
        return ''
    size = getattr(volume, 'size', '')
    vtype = getattr(volume, 'volumetype', '') or getattr(volume, 'volume_type', '')
    return f"{size}GiB/{vtype}" if size or vtype else ''


def _tags_text(tags):
    if not tags:
        return ''
    return ','.join(f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags)


def render(node_pool):
    metadata = getattr(node_pool, 'metadata', None)
    spec = getattr(node_pool, 'spec', None)
    status = getattr(node_pool, 'status', None)

    output = ""
    output += f"id: {getattr(metadata, 'uid', '') if metadata else ''}\n"
    output += f"name: {getattr(metadata, 'name', '') if metadata else ''}\n"
    output += f"type: {getattr(spec, 'type', '') if spec else ''}\n"
    output += f"initial_node_count: {getattr(spec, 'initial_node_count', '') if spec else ''}\n"

    autoscaling = getattr(spec, 'autoscaling', None) if spec else None
    if autoscaling is not None:
        enabled = getattr(autoscaling, 'enable', False)
        if enabled:
            output += (f"autoscaling: on(min={getattr(autoscaling, 'min_node_count', '')}"
                       f", max={getattr(autoscaling, 'max_node_count', '')})\n")
        else:
            output += "autoscaling: off\n"
    else:
        output += "autoscaling: \n"

    node_template = getattr(spec, 'node_template', None) if spec else None
    output += f"flavor: {getattr(node_template, 'flavor', '') if node_template else ''}\n"
    output += f"az: {getattr(node_template, 'az', '') if node_template else ''}\n"
    output += f"os: {getattr(node_template, 'os', '') if node_template else ''}\n"
    output += f"billing_mode: {getattr(node_template, 'billing_mode', '') if node_template else ''}\n"
    output += f"root_volume: {_volume_text(getattr(node_template, 'root_volume', None)) if node_template else ''}\n"
    data_volumes = getattr(node_template, 'data_volumes', None) if node_template else None
    if data_volumes:
        output += f"data_volumes: {'; '.join(_volume_text(v) for v in data_volumes if _volume_text(v))}\n"
    else:
        output += "data_volumes: \n"
    output += f"user_tags: {_tags_text(getattr(node_template, 'user_tags', None)) if node_template else ''}\n"
    k8s_tags = getattr(node_template, 'k8s_tags', None) if node_template else None
    output += f"k8s_tags: {','.join(f'{k}={v}' for k, v in k8s_tags.items()) if k8s_tags else ''}\n"
    taints = getattr(node_template, 'taints', None) if node_template else None
    if taints:
        output += "taints: " + "; ".join(
            f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}:{getattr(t, 'effect', '')}" for t in taints) + "\n"
    else:
        output += "taints: \n"
    runtime = getattr(node_template, 'runtime', None) if node_template else None
    if runtime:
        output += f"runtime: {getattr(runtime, 'name', '')} {getattr(runtime, 'runtime_class', '')}\n"
    else:
        output += "runtime: \n"

    output += f"current_node: {getattr(status, 'current_node', '') if status else ''}\n"
    output += f"active_node: {getattr(status, 'active_node', '') if status else ''}\n"
    output += f"creating_node: {getattr(status, 'creating_node', '') if status else ''}\n"
    output += f"deleting_node: {getattr(status, 'deleting_node', '') if status else ''}\n"
    output += f"phase: {getattr(status, 'phase', '') if status else ''}\n"
    output += f"created: {getattr(metadata, 'creation_timestamp', '') if metadata else ''}\n"
    output += f"updated: {getattr(metadata, 'update_timestamp', '') if metadata else ''}\n"

    conditions = getattr(status, 'conditions', None) if status else None
    if conditions:
        output += "conditions: " + "; ".join(
            f"{getattr(c, 'type', '')}={getattr(c, 'status', '')}" for c in conditions) + "\n"
    else:
        output += "conditions: \n"

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

    request = ShowNodePoolRequest()
    request.cluster_id = args.cluster_id
    request.nodepool_id = args.nodepool_id
    if args.advance_status:
        request.advance_status = args.advance_status == "true"

    response = client.show_node_pool(request)
    node_pool = response
    if not node_pool or not getattr(node_pool, 'metadata', None):
        print(format_empty_result(
            "CCE 节点池", Region, args.project_id,
            f"集群 ID: {args.cluster_id}, 节点池 ID: {args.nodepool_id}",
            hints=[
                "确认节点池 ID 正确（可由 list_node_pools.py 获取）",
                "确认节点池属于当前 --region 对应的集群",
                "确认账号具备 cce:nodepool:get 权限（或 CCEReadOnlyPolicy）",
            ]))
        exit(0)

    render(node_pool)
except Exception as e:
    print(format_api_error(e, "CCE 节点池详情查询", Region, args.project_id,
                           f"集群 ID: {args.cluster_id}, 节点池 ID: {args.nodepool_id}"))
    exit(1)