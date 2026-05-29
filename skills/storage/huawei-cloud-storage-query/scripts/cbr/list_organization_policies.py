import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListOrganizationPoliciesRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 组织策略列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--operation_type", type=str, required=True, help="组织策略类型：备份（backup）、复制（replication）")
parser.add_argument("--limit", type=int, default=1000, help="返回结果个数限制，默认1000")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0


def render(policies):
    total = len(policies)
    if Offset >= total:
        print(f"查询结果为空\n\n组织策略列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"id\tname\toperation_type\tpolicy_enabled\tstatus\n"
    for i in range(Offset, min(total, Offset + 50)):
        policy = policies[i]
        pid = getattr(policy, 'id', '')
        name = getattr(policy, 'name', '')
        operation_type = getattr(policy, 'operation_type', '')
        policy_enabled = getattr(policy, 'policy_enabled', '')
        status = getattr(policy, 'status', '')
        output += f"{pid}\t{name}\t{operation_type}\t{policy_enabled}\t{status}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n组织策略列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ListOrganizationPoliciesRequest()
    if args.operation_type:
        request.operation_type = args.operation_type
    if args.limit:
        request.limit = args.limit

    response = client.list_organization_policies(request)
    policies = getattr(response, 'policies', []) or []
    count = getattr(response, 'count', 0)

    if not policies:
        print(f"没有找到组织策略 (区域: {Region})")
        exit(0)

    render(policies)
except Exception as e:
    print(f"cbr.list_organization_policies 查询失败: {e}")
    exit(1)
