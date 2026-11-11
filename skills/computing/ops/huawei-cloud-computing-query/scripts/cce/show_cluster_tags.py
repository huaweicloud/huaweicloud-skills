import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id, format_api_error, format_empty_result
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import GetResourceTagsRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 集群的标签（只读）")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, help="区域，不传时回退环境变量 HW_REGION_NAME（默认 cn-north-4）")
parser.add_argument("--cluster_id", type=str, required=True, help="集群 ID（UUID），可通过 list_clusters.py 获取")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

if args.region is not None:
    Region = args.region


def render(tags, sys_tags):
    output = "tag_key\ttag_value\n"
    for tag in tags:
        output += f"{getattr(tag, 'key', '')}\t{getattr(tag, 'value', '')}\n"

    if sys_tags:
        output += "\nsys_tag_key\tsys_tag_value\n"
        for tag in sys_tags:
            output += f"{getattr(tag, 'key', '')}\t{getattr(tag, 'value', '')}\n"

    output += f"\n共 {len(tags)} 个用户标签、{len(sys_tags or [])} 个系统标签"
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

    request = GetResourceTagsRequest()
    request.resource_type = "cce-cluster"
    request.resource_id = args.cluster_id

    response = client.get_resource_tags(request)
    tags = response.tags or []
    sys_tags = response.sys_tags or []

    if not tags and not sys_tags:
        print(format_empty_result(
            "CCE 集群标签", Region, args.project_id, f"集群 ID: {args.cluster_id}",
            hints=[
                "该集群尚未配置用户标签（系统标签也可能为空）",
                "确认集群 ID 正确（可由 list_clusters.py 获取）",
                "确认账号具备 cce:cluster:get 权限（或 CCEReadOnlyPolicy）",
            ]))
        exit(0)

    render(tags, sys_tags)
except Exception as e:
    print(format_api_error(e, "CCE 集群标签查询", Region, args.project_id, f"集群 ID: {args.cluster_id}"))
    exit(1)