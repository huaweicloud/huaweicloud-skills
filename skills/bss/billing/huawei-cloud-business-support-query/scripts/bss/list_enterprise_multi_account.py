import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListEnterpriseMultiAccountRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询企业多账户可回收余额")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--sub_customer_id", type=str, required=True, help="企业子账户的账号ID。该参数必填")
parser.add_argument("--balance_type", type=str, default="BALANCE_TYPE_DEBIT", help="账户类型。该参数必填。BALANCE_TYPE_DEBIT：余额账户（默认） BALANCE_TYPE_CREDIT：信用账户")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0。只有信用账户有效")
parser.add_argument("--limit", type=int, default=50, help="每次查询条数。默认值为50。只有信用账户有效")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListEnterpriseMultiAccountRequest()
    request.sub_customer_id = args.sub_customer_id
    request.balance_type = args.balance_type
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_enterprise_multi_account(request)

    total_count = getattr(response, 'total_count', 0)
    amount_infos = getattr(response, 'amount_infos', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if amount_infos:
        output += "\n可回收余额信息列表:\n"
        output += "可回收金额\t金额单位\t币种\t账户余额\t信用额度\t信用额度过期时间\n"
        for info in amount_infos:
            avail_retrieve_amount = getattr(info, 'avail_retrieve_amount', '')
            measure_id = getattr(info, 'measure_id', '')
            currency = getattr(info, 'currency', '')
            amount = getattr(info, 'amount', '')
            credit_amount = getattr(info, 'credit_amount', '')
            expire_time = getattr(info, 'expire_time', '')
            output += f"{avail_retrieve_amount}\t{measure_id}\t{currency}\t{amount}\t{credit_amount}\t{expire_time}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_enterprise_multi_account 查询失败: {e}")
    exit(1)
