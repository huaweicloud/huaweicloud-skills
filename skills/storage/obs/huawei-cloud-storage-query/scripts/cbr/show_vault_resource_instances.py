import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model.show_vault_resource_instances_request import ShowVaultResourceInstancesRequest
from huaweicloudsdkcbr.v1.model.vault_resource_instances_req import VaultResourceInstancesReq
from huaweicloudsdkcbr.v1.model.tags_req import TagsReq
from huaweicloudsdkcbr.v1.model.match import Match
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 存储库标签资源实例")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--action", type=str, default="filter", help="操作标识，取值范围：filter(过滤)/count(计数)")
parser.add_argument("--limit", type=str, default="1000", help="返回结果个数限制，默认1000")
parser.add_argument("--offset", type=str, default="0", help="索引位置，从0开始")
parser.add_argument("--tags", type=str, help="标签过滤条件(与关系)，格式: key1=value1|value2,key2=value3")
parser.add_argument("--tags_any", type=str, help="标签过滤条件(或关系)，格式同tags")
parser.add_argument("--not_tags", type=str, help="标签排除条件(与关系)，格式同tags")
parser.add_argument("--not_tags_any", type=str, help="标签排除条件(或关系)，格式同tags")
parser.add_argument("--without_any_tag", action="store_true", help="不包含任意标签的资源")
parser.add_argument("--cloud_type", type=str, help="云类型: public/hybrid")
parser.add_argument("--object_type", type=str, help="对象类型: server/disk/turbo/workspace/vmware/rds/file")
parser.add_argument("--matches", type=str, help="字段匹配条件，格式: key1=value1,key2=value2")
parser.add_argument("--render_offset", type=int, help="本地渲染分页偏移量，从 0 开始")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.render_offset is not None:
    Offset = args.render_offset

if Offset < 0:
    Offset = 0


def parse_tags_str(tags_str):
    result = []
    if not tags_str:
        return result
    for part in tags_str.split(','):
        if '=' in part:
            k, v = part.split('=', 1)
            values = [x.strip() for x in v.split('|') if x.strip()]
            result.append(TagsReq(key=k.strip(), values=values))
    return result


def render(resources, total_count):
    total = len(resources)
    if Offset >= total:
        print(f"查询结果为空\n\n资源实例列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"total_count: {total_count}\n\n"
    for i in range(Offset, min(total, Offset + 50)):
        res = resources[i]
        resource_id = getattr(res, 'resource_id', '')
        resource_name = getattr(res, 'resource_name', '')
        output += f"resource_id: {resource_id}\n"
        output += f"resource_name: {resource_name}\n"

        resource_detail = getattr(res, 'resource_detail', None)
        if resource_detail:
            vault = getattr(resource_detail, 'vault', None)
            if vault:
                vault_billing = getattr(vault, 'billing', None)
                output += f"  vault.id: {getattr(vault, 'id', '')}\n"
                output += f"  vault.name: {getattr(vault, 'name', '')}\n"
                if vault_billing:
                    output += f"  vault.status: {getattr(vault_billing, 'status', '')}\n"
                    output += f"  vault.object_type: {getattr(vault_billing, 'object_type', '')}\n"
                    output += f"  vault.protect_type: {getattr(vault_billing, 'protect_type', '')}\n"
                    output += f"  vault.size: {getattr(vault_billing, 'size', '')}\n"
                    output += f"  vault.used: {getattr(vault_billing, 'used', '')}\n"

        output += "\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n资源实例列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
        if end + 1 < total:
            output += f"可以使用 --render_offset={end + 1} 参数继续获取后续数据"
    print(output)


try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    req_body = VaultResourceInstancesReq()
    req_body.action = args.action
    if args.action != "count":
        req_body.limit = args.limit
        req_body.offset = args.offset

    if args.tags:
        req_body.tags = parse_tags_str(args.tags)
    if args.tags_any:
        req_body.tags_any = parse_tags_str(args.tags_any)
    if args.not_tags:
        req_body.not_tags = parse_tags_str(args.not_tags)
    if args.not_tags_any:
        req_body.not_tags_any = parse_tags_str(args.not_tags_any)
    if args.without_any_tag:
        req_body.without_any_tag = True
    if args.cloud_type:
        req_body.cloud_type = args.cloud_type
    if args.object_type:
        req_body.object_type = args.object_type
    if args.matches:
        matches_list = []
        for pair in args.matches.split(','):
            if '=' in pair:
                k, v = pair.split('=', 1)
                matches_list.append(Match(key=k.strip(), value=v.strip()))
        req_body.matches = matches_list

    request = ShowVaultResourceInstancesRequest()
    request.body = req_body

    response = client.show_vault_resource_instances(request)
    resources = getattr(response, 'resources', []) or []
    total_count = getattr(response, 'total_count', 0)

    if args.action == "count":
        print(f"total_count: {total_count}")
        exit(0)

    if not resources:
        print(f"没有找到标签资源实例 (区域: {Region})")
        exit(0)

    render(resources, total_count)
except Exception as e:
    print(f"cbr.show_vault_resource_instances 查询失败: {e}")
    exit(1)
