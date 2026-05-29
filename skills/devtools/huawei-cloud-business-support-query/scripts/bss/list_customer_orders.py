import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListCustomerOrdersRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户订单列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--order_id", type=str, help="订单ID。大小写不敏感。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--customer_id", type=str, help="客户账号ID。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--create_time_begin", type=str, help="订单创建开始时间。UTC时间，格式：yyyy-MM-dd'T'HH:mm:ss'Z'。订单创建开始时间与结束时间间隔不能超过1年。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--create_time_end", type=str, help="订单创建结束时间。UTC时间，格式：yyyy-MM-dd'T'HH:mm:ss'Z'。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--service_type_code", type=str, help="云服务类型编码，例如OBS的云服务类型编码为hws.service.type.obs。大小写不敏感。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--status", type=int, help="订单状态。1-待审核 3-处理中 4-已取消 5-已完成 6-待支付 9-待确认。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--order_type", type=str, help="订单类型。1-开通 2-续订 3-变更 4-退订 10-包年/包月转按需 11-按需转包年/包月 13-试用 14-转商用 15-费用调整。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--limit", type=int, default=50, help="每次查询的订单数量，默认值为50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--order_by", type=str, help="查询的订单列表排序。支持按照创建时间进行排序，带-表示倒序。创建时间：升序为createTime，倒序为-createTime。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--payment_time_begin", type=str, help="订单支付开始时间。UTC时间，格式：yyyy-MM-dd'T'HH:mm:ss'Z'。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--payment_time_end", type=str, help="订单支付结束时间。UTC时间，格式：yyyy-MM-dd'T'HH:mm:ss'Z'。此参数不携带或携带值为空时，不作为筛选条件")
parser.add_argument("--indirect_partner_id", type=str, help="云经销商ID。华为云总经销商查询云经销商的客户订单列表时，需要携带该参数")
parser.add_argument("--method", type=str, help="查询方式。oneself-客户自己订单 sub_customer-客户给企业子代付订单。此参数不携带或携带值为空串或携带值为null时，默认值为oneself")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListCustomerOrdersRequest()
    if args.order_id:
        request.order_id = args.order_id
    if args.customer_id:
        request.customer_id = args.customer_id
    if args.create_time_begin:
        request.create_time_begin = args.create_time_begin
    if args.create_time_end:
        request.create_time_end = args.create_time_end
    if args.service_type_code:
        request.service_type_code = args.service_type_code
    if args.status is not None:
        request.status = args.status
    if args.order_type:
        request.order_type = args.order_type
    if args.limit is not None:
        request.limit = args.limit
    if args.offset is not None:
        request.offset = args.offset
    if args.order_by:
        request.order_by = args.order_by
    if args.payment_time_begin:
        request.payment_time_begin = args.payment_time_begin
    if args.payment_time_end:
        request.payment_time_end = args.payment_time_end
    if args.indirect_partner_id:
        request.indirect_partner_id = args.indirect_partner_id
    if args.method:
        request.method = args.method

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_customer_orders(request)

    total_count = getattr(response, 'total_count', 0)
    order_infos = getattr(response, 'order_infos', []) or []

    output = f"总记录数\t{total_count}\n"
    if order_infos:
        output += "\n订单列表:\n"
        output += "订单ID\t客户ID\t云服务类型编码\t云服务类型名称\t客户订单来源类型\t订单状态\t订单类型\t订单优惠后金额\t订单金额(官网价)\t金额度量单位\t创建时间\t支付时间\t币种\t合同ID\n"
        for order in order_infos:
            order_id = getattr(order, 'order_id', '')
            customer_id = getattr(order, 'customer_id', '')
            service_type_code = getattr(order, 'service_type_code', '')
            service_type_name = getattr(order, 'service_type_name', '')
            source_type = getattr(order, 'source_type', '')
            status = getattr(order, 'status', '')
            order_type = getattr(order, 'order_type', '')
            amount_after_discount = getattr(order, 'amount_after_discount', '')
            official_amount = getattr(order, 'official_amount', '')
            measure_id = getattr(order, 'measure_id', '')
            create_time = getattr(order, 'create_time', '')
            payment_time = getattr(order, 'payment_time', '')
            currency = getattr(order, 'currency', '')
            contract_id = getattr(order, 'contract_id', '')
            output += f"{order_id}\t{customer_id}\t{service_type_code}\t{service_type_name}\t{source_type}\t{status}\t{order_type}\t{amount_after_discount}\t{official_amount}\t{measure_id}\t{create_time}\t{payment_time}\t{currency}\t{contract_id}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_customer_orders 查询失败: {e}")
    exit(1)
