import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListEnterpriseSubCustomersRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询企业子客户列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--sub_customer_account_name", type=str, help="企业子账号的账号名。根据fuzzy_query取值决定是否按模糊查询。仅支持前缀匹配、后缀匹配、中间匹配；不支持携带空格查询。此参数不携带或携带值为空时，不作为筛选条件；携带值为空串时，作为筛选条件")
parser.add_argument("--sub_customer_display_name", type=str, help="企业子账号的显示名称。根据fuzzy_query取值决定是否按模糊查询。仅支持前缀匹配、后缀匹配、中间匹配；不支持携带空格查询。此参数不携带或携带值为空时，不作为筛选条件；携带值为空串时，作为筛选条件")
parser.add_argument("--fuzzy_query", type=int, default=0, help="企业子账号的显示名称、用户名是否按模糊查询。0：不按模糊查询（默认） 1：按模糊查询")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="每次查询记录数。默认值为50")
parser.add_argument("--org_id", type=str, help="子账号归属的组织单元ID。此参数不携带或携带值为空时，不作为筛选条件")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListEnterpriseSubCustomersRequest()
    if args.sub_customer_account_name:
        request.sub_customer_account_name = args.sub_customer_account_name
    if args.sub_customer_display_name:
        request.sub_customer_display_name = args.sub_customer_display_name
    if args.fuzzy_query is not None:
        request.fuzzy_query = args.fuzzy_query
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit
    if args.org_id:
        request.org_id = args.org_id

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_enterprise_sub_customers(request)

    total_count = getattr(response, 'total_count', 0)
    sub_customer_infos = getattr(response, 'sub_customer_infos', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if sub_customer_infos:
        output += "\n企业子客户列表:\n"
        output += "客户ID\t用户名\t显示名称\t状态\t组织单元ID\t组织单元名称\n"
        for info in sub_customer_infos:
            customer_id = getattr(info, 'id', '')
            account_name = getattr(info, 'name', '')
            display_name = getattr(info, 'display_name', '')
            status = getattr(info, 'status', '')
            org_id = getattr(info, 'org_id', '')
            org_name = getattr(info, 'org_name', '')
            output += f"{customer_id}\t{account_name}\t{display_name}\t{status}\t{org_id}\t{org_name}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_enterprise_sub_customers 查询失败: {e}")
    exit(1)
