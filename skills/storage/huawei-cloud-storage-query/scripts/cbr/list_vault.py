import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ListVaultRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()
Offset = 0

parser = argparse.ArgumentParser(description="查询 CBR 存储库列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--limit", type=int, default=1000, help="返回结果个数限制，默认1000")
parser.add_argument("--name", type=str, help="存储库名称")
parser.add_argument("--offset", type=int, help="本地渲染分页偏移量，从 0 开始")
parser.add_argument("--cloud_type", type=str, help="云类型")
parser.add_argument("--protect_type", type=str, help="保护类型")
parser.add_argument("--object_type", type=str, help="对象类型：云服务器（server），云硬盘（disk），文件系统（turbo），云桌面（workspace），VMware（vmware），关系型数据库（rds），文件（file）")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目id或all_granted_eps，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--id", type=str, help="存储库ID，多个以英文逗号分隔")
parser.add_argument("--policy_id", type=str, help="策略ID，可通过 list_policies.py 获取")
parser.add_argument("--status", type=str, help="状态")
parser.add_argument("--resource_ids", type=str, help="资源id，支持多资源，以英文逗号分隔")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

if args.offset is not None:
    Offset = args.offset

if Offset < 0:
    Offset = 0

def render(vaults):
    total = len(vaults)
    if Offset >= total:
        print(f"查询结果为空\n\n存储库列表共 {total} 个, 序号从 0 开始, offset必须 < {total}")
        exit(0)

    output = f"id\tname\tstatus\tobject_type\tprotect_type\tsize(GB)\tused(MB)\tcreated_at\tavailability_zone\n"
    for i in range(Offset, min(total, Offset + 50)):
        vault = vaults[i]
        vid = getattr(vault, 'id', '')
        name = getattr(vault, 'name', '')
        created_at = getattr(vault, 'created_at', '')
        availability_zone = getattr(vault, 'availability_zone', '')
        billing = getattr(vault, 'billing', None)
        if billing:
            status = getattr(billing, 'status', '')
            object_type = getattr(billing, 'object_type', '')
            protect_type = getattr(billing, 'protect_type', '')
            size = getattr(billing, 'size', '')
            used = getattr(billing, 'used', '')
        else:
            status = ''
            object_type = ''
            protect_type = ''
            size = ''
            used = ''
        output += f"{vid}\t{name}\t{status}\t{object_type}\t{protect_type}\t{size}\t{used}\t{created_at}\t{availability_zone}\n"
    end = min(total, Offset + 50) - 1
    if total > 50 or Offset > 0:
        output += f"\n存储库列表共 {total} 个, 序号从 0 开始，当前显示第 {Offset}~{end} 个\n"
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

    all_vaults = []
    limit = args.limit

    request = ListVaultRequest()
    request.limit = limit
    if args.name:
        request.name = args.name
    if args.cloud_type:
        request.cloud_type = args.cloud_type
    if args.protect_type:
        request.protect_type = args.protect_type
    if args.object_type:
        request.object_type = args.object_type
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.id:
        request.id = args.id
    if args.policy_id:
        request.policy_id = args.policy_id
    if args.status:
        request.status = args.status
    if args.resource_ids:
        request.resource_ids = args.resource_ids

    response = client.list_vault(request)
    vaults = getattr(response, 'vaults', []) or []
    count = getattr(response, 'count', 0)

    if not vaults:
        print(f"没有找到存储库 (区域: {Region})")
        exit(0)

    render(vaults)
except Exception as e:
    print(f"cbr.list_vault 查询失败: {e}")
    exit(1)
