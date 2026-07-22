import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListEnterpriseOrganizationsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询企业组织节点列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--recursive_query", type=int, default=0, help="是否递归查询。0：不递归（默认） 1：递归。如果不递归，只返回起始节点的直接子节点。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--parent_id", type=str, help="指定的节点ID。为空则从根节点查起。此参数须由纯数字组成。此参数不携带或携带值为空时，不作为筛选条件")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListEnterpriseOrganizationsRequest()
    if args.recursive_query is not None:
        request.recursive_query = args.recursive_query
    if args.parent_id:
        request.parent_id = args.parent_id

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_enterprise_organizations(request)

    root_id = getattr(response, 'root_id', '')
    root_name = getattr(response, 'root_name', '')
    child_nodes = getattr(response, 'child_nodes', []) or []

    output = ""
    if root_id:
        output += f"根节点ID\t{root_id}\n"
    if root_name:
        output += f"根节点名称\t{root_name}\n"
    
    if child_nodes:
        output += "\n子节点列表:\n"
        output += "实体关系ID\t节点ID\t节点名称\n"
        for node in child_nodes:
            relation_id = getattr(node, 'relation_id', '')
            node_id = getattr(node, 'id', '')
            node_name = getattr(node, 'name', '')
            output += f"{relation_id}\t{node_id}\t{node_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_enterprise_organizations 查询失败: {e}")
    exit(1)
