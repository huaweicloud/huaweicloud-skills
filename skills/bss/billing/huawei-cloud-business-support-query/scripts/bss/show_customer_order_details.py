import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ShowCustomerOrderDetailsRequest
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询客户订单详情")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--order_id", type=str, required=True, help="订单ID，可通过 list_customer_orders.py 获取")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文；en_US：英文。缺省为zh_CN")
parser.add_argument("--limit", type=int, default=50, help="每页大小，默认50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始，默认0")
parser.add_argument("--indirect_partner_id", type=str, help="云经销商ID。华为云总经销商查询云经销商的客户订单详情时需要携带该参数；否则只能查询自己客户的订单详情")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ShowCustomerOrderDetailsRequest()
    request.order_id = args.order_id
    request.x_language = args.x_language
    request.limit = args.limit
    request.offset = args.offset
    if args.indirect_partner_id:
        request.indirect_partner_id = args.indirect_partner_id

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.show_customer_order_details(request)

    total_count = getattr(response, 'total_count', 0)
    order_info = getattr(response, 'order_info', None)
    order_line_items = getattr(response, 'order_line_items', []) or []

    output = ""
    
    if order_info:
        order_id = getattr(order_info, 'order_id', '')
        customer_id = getattr(order_info, 'customer_id', '')
        service_type_code = getattr(order_info, 'service_type_code', '')
        service_type_name = getattr(order_info, 'service_type_name', '')
        source_type = getattr(order_info, 'source_type', '')
        source_type_str = {1: '客户', 2: '代理', 3: '合同', 4: '分销商', 5: '页面删除资源', 6: '补录订单', 7: '补偿订单', 8: '系统自动创建'}.get(source_type, str(source_type))
        status = getattr(order_info, 'status', '')
        status_str = {1: '待审核', 2: '待退款', 3: '处理中', 4: '已取消', 5: '已完成', 6: '待付款', 9: '待确认', 10: '待发货', 11: '待收货', 12: '待上门取货', 13: '换新中'}.get(status, str(status))
        order_type = getattr(order_info, 'order_type', '')
        order_type_str = {1: '开通', 2: '续订', 3: '变更', 4: '退订', 10: '包年/包月转按需', 11: '按需转包年/包月', 13: '试用', 14: '转商用', 15: '费用调整'}.get(order_type, str(order_type))
        amount_after_discount = getattr(order_info, 'amount_after_discount', '')
        official_amount = getattr(order_info, 'official_amount', '')
        measure_id = getattr(order_info, 'measure_id', '')
        create_time = getattr(order_info, 'create_time', '')
        payment_time = getattr(order_info, 'payment_time', '')
        currency = getattr(order_info, 'currency', '')
        contract_id = getattr(order_info, 'contract_id', '')
        user_name = getattr(order_info, 'user_name', '')
        pending_payment_end_time = getattr(order_info, 'pending_payment_end_time', '')
        
        output += "--- 订单信息 ---\n"
        output += f"订单ID\t{order_id}\n"
        output += f"客户ID\t{customer_id}\n"
        output += f"云服务类型编码\t{service_type_code}\n"
        output += f"云服务类型\t{service_type_name}\n"
        output += f"订单来源\t{source_type_str}\n"
        output += f"订单状态\t{status_str}\n"
        output += f"订单类型\t{order_type_str}\n"
        output += f"优惠后金额\t{amount_after_discount}\n"
        output += f"官网价\t{official_amount}\n"
        output += f"金额单位\t{measure_id}\n"
        output += f"创建时间\t{create_time}\n"
        output += f"支付时间\t{payment_time}\n"
        output += f"币种\t{currency}\n"
        output += f"合同ID\t{contract_id}\n"
        output += f"创建者\t{user_name}\n"
        output += f"待付款截止时间\t{pending_payment_end_time}\n"
        amount_info = getattr(order_info, 'amount_info', None)
        if amount_info:
            output += "--- 金额明细 ---\n"
            output += f"代金券金额\t{getattr(amount_info, 'coupon_amount', '')}\n"
            output += f"现金券金额\t{getattr(amount_info, 'flexipurchase_coupon_amount', '')}\n"
            output += f"储值卡金额\t{getattr(amount_info, 'stored_card_amount', '')}\n"
            output += f"手续费金额\t{getattr(amount_info, 'commission_amount', '')}\n"
            output += f"已消费金额\t{getattr(amount_info, 'consumed_amount', '')}\n"
            discounts = getattr(amount_info, 'discounts', []) or []
            if discounts:
                output += "折扣类型\t折扣金额\n"
                for d in discounts:
                    output += f"{getattr(d, 'discount_type', '')}\t{getattr(d, 'discount_amount', '')}\n"
        sub_order_infos = getattr(order_info, 'sub_order_infos', []) or []
        if sub_order_infos:
            output += "--- 子订单列表 ---\n"
            output += "子订单ID\t客户ID\t云服务类型编码\t云服务类型\t订单来源\t订单状态\t订单类型\t优惠后金额\t官网价\t金额单位\t创建时间\t支付时间\t币种\t合同ID\t创建者\t待付款截止时间\n"
            for sub in sub_order_infos:
                sub_order_id = getattr(sub, 'order_id', '')
                sub_customer_id = getattr(sub, 'customer_id', '')
                sub_stc = getattr(sub, 'service_type_code', '')
                sub_stn = getattr(sub, 'service_type_name', '')
                sub_source = getattr(sub, 'source_type', '')
                sub_source_str = {1: '客户', 2: '代理', 3: '合同', 4: '分销商', 5: '页面删除资源', 6: '补录订单', 7: '补偿订单', 8: '系统自动创建'}.get(sub_source, str(sub_source))
                sub_status = getattr(sub, 'status', '')
                sub_status_str = {1: '待审核', 2: '待退款', 3: '处理中', 4: '已取消', 5: '已完成', 6: '待付款', 9: '待确认', 10: '待发货', 11: '待收货', 12: '待上门取货', 13: '换新中'}.get(sub_status, str(sub_status))
                sub_order_type = getattr(sub, 'order_type', '')
                sub_order_type_str = {1: '开通', 2: '续订', 3: '变更', 4: '退订', 10: '包年/包月转按需', 11: '按需转包年/包月', 13: '试用', 14: '转商用', 15: '费用调整'}.get(sub_order_type, str(sub_order_type))
                sub_aad = getattr(sub, 'amount_after_discount', '')
                sub_oa = getattr(sub, 'official_amount', '')
                sub_mi = getattr(sub, 'measure_id', '')
                sub_ct = getattr(sub, 'create_time', '')
                sub_pt = getattr(sub, 'payment_time', '')
                sub_cur = getattr(sub, 'currency', '')
                sub_cid = getattr(sub, 'contract_id', '')
                sub_un = getattr(sub, 'user_name', '')
                sub_ppe = getattr(sub, 'pending_payment_end_time', '')
                output += f"{sub_order_id}\t{sub_customer_id}\t{sub_stc}\t{sub_stn}\t{sub_source_str}\t{sub_status_str}\t{sub_order_type_str}\t{sub_aad}\t{sub_oa}\t{sub_mi}\t{sub_ct}\t{sub_pt}\t{sub_cur}\t{sub_cid}\t{sub_un}\t{sub_ppe}\n"

    if order_line_items:
        output += f"\n--- 订单项列表 (共{total_count}个) ---\n"
        output += "订单项ID\t订单ID\t云服务类型编码\t云服务类型\t产品ID\t产品规格描述\t产品目录编码\t产品归属服务\t商务资源\t周期类型\t周期数量\t生效时间\t失效时间\t订购数量\t优惠后金额\t官网价\t币种\n"
        for item in order_line_items:
            order_line_item_id = getattr(item, 'order_line_item_id', '')
            item_order_id = getattr(item, 'order_id', '')
            service_type_code = getattr(item, 'service_type_code', '')
            service_type_name = getattr(item, 'service_type_name', '')
            product_id = getattr(item, 'product_id', '')
            product_spec_desc = getattr(item, 'product_spec_desc', '')
            category_code = getattr(item, 'category_code', '')
            product_owner_service = getattr(item, 'product_owner_service', '')
            commercial_resource = getattr(item, 'commercial_resource', '')
            period_type = getattr(item, 'period_type', '')
            period_type_str = {0: '天', 1: '周', 2: '月', 3: '年', 4: '小时', 5: '一次性'}.get(period_type, str(period_type))
            period_num = getattr(item, 'period_num', '')
            effective_time = getattr(item, 'effective_time', '')
            expire_time = getattr(item, 'expire_time', '')
            subscription_num = getattr(item, 'subscription_num', '')
            amount_after_discount = getattr(item, 'amount_after_discount', '')
            official_amount = getattr(item, 'official_amount', '')
            currency = getattr(item, 'currency', '')
            output += f"{order_line_item_id}\t{item_order_id}\t{service_type_code}\t{service_type_name}\t{product_id}\t{product_spec_desc}\t{category_code}\t{product_owner_service}\t{commercial_resource}\t{period_type_str}\t{period_num}\t{effective_time}\t{expire_time}\t{subscription_num}\t{amount_after_discount}\t{official_amount}\t{currency}\n"
            amount_info = getattr(item, 'amount_info', None)
            if amount_info:
                output += f"  金额明细: 代金券={getattr(amount_info, 'coupon_amount', '')}, 现金券={getattr(amount_info, 'flexipurchase_coupon_amount', '')}, 储值卡={getattr(amount_info, 'stored_card_amount', '')}, 手续费={getattr(amount_info, 'commission_amount', '')}, 已消费={getattr(amount_info, 'consumed_amount', '')}\n"
                discounts = getattr(amount_info, 'discounts', []) or []
                for d in discounts:
                    output += f"  折扣: 类型={getattr(d, 'discount_type', '')}, 金额={getattr(d, 'discount_amount', '')}\n"
            base_product_info = getattr(item, 'base_product_info', None)
            if base_product_info:
                output += f"  基础产品: 产品ID={getattr(base_product_info, 'product_id', '')}, 规格={getattr(base_product_info, 'product_spec_desc', '')}, 目录编码={getattr(base_product_info, 'category_code', '')}, 归属服务={getattr(base_product_info, 'product_owner_service', '')}, 商务资源={getattr(base_product_info, 'commercial_resource', '')}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.show_customer_order_details 查询失败: {e}")
    exit(1)
