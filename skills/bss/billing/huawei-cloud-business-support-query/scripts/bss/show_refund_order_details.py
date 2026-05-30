import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ShowRefundOrderDetailsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询退款订单详情")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--order_id", type=str, required=True, help="退订订单或者降配订单的ID，可通过 list_customer_orders.py 获取")
parser.add_argument("--customer_id", type=str, help="客户账号ID。伙伴查询子客户退款订单的金额详情必须携带该字段")
parser.add_argument("--indirect_partner_id", type=str, help="云经销商ID。华为云总经销商查询云经销商的子客户退款订单的金额详情必须携带该字段；除此之外，此参数不做处理")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowRefundOrderDetailsRequest()
    request.order_id = args.order_id
    if args.customer_id:
        request.customer_id = args.customer_id
    if args.indirect_partner_id:
        request.indirect_partner_id = args.indirect_partner_id

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.show_refund_order_details(request)

    total_count = getattr(response, 'total_count', 0)
    refund_infos = getattr(response, 'refund_infos', []) or []

    output = f"总记录数\t{total_count}\n"
    if refund_infos:
        output += "\n退款信息列表:\n"
        output += "记录ID\t金额\t金额单位\t客户ID\t云服务类型编码\t云服务类型\t资源类型编码\t资源类型\t云服务区编码\t原订单ID\n"
        for info in refund_infos:
            id = getattr(info, 'id', '')
            amount = getattr(info, 'amount', '')
            measure_id = getattr(info, 'measure_id', '')
            customer_id = getattr(info, 'customer_id', '')
            service_type_code = getattr(info, 'service_type_code', '')
            service_type_name = getattr(info, 'service_type_name', '')
            resource_type_code = getattr(info, 'resource_type_code', '')
            resource_type_name = getattr(info, 'resource_type_name', '')
            region_code = getattr(info, 'region_code', '')
            base_order_id = getattr(info, 'base_order_id', '')
            output += f"{id}\t{amount}\t{measure_id}\t{customer_id}\t{service_type_code}\t{service_type_name}\t{resource_type_code}\t{resource_type_name}\t{region_code}\t{base_order_id}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.show_refund_order_details 查询失败: {e}")
    exit(1)
