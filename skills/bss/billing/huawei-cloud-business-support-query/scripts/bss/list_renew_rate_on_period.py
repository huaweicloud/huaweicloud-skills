import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListRenewRateOnPeriodRequest
from huaweicloudsdkbss.v2.model import ListRenewRateOnPeriodReq
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询包年/包月产品续费询价")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--resource_id", type=str, action='append', required=True, help="资源ID列表。只支持传入主资源ID，最多10个资源ID（可多次指定）")
parser.add_argument("--period_type", type=int, required=True, help="周期类型。2：月；3：年")
parser.add_argument("--period_num", type=int, required=True, help="周期数目。如果是月，目前支持1-11；如果是年，目前支持1-3")
parser.add_argument("--include_relative_resources", type=bool, default=False, help="是否包含关联资源一起续费询价。false：不包含；true：包含。此参数不携带或携带值为空串时，默认值为false")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    body = ListRenewRateOnPeriodReq()
    body.resource_ids = args.resource_id
    body.period_type = args.period_type
    body.period_num = args.period_num
    if args.include_relative_resources is not None:
        body.include_relative_resources = args.include_relative_resources

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    request = ListRenewRateOnPeriodRequest()
    request.body = body
    response = client.list_renew_rate_on_period(request)

    currency = getattr(response, 'currency', 'CNY') or 'CNY'
    renew_inquiry_results = getattr(response, 'renew_inquiry_results', []) or []
    official_website_rating_result = getattr(response, 'official_website_rating_result', None)
    optional_discount_rating_results = getattr(response, 'optional_discount_rating_results', []) or []
    fail_resource_infos = getattr(response, 'fail_resource_infos', []) or []

    output = ""
    
    if renew_inquiry_results:
        output += "--- 续费询价结果 ---\n"
        output += "resource_id\tamount\n"
        for result in renew_inquiry_results:
            resource_id = getattr(result, 'resource_id', '')
            amount = getattr(result, 'amount', '')
            output += f"{resource_id}\t{amount}\n"

    if official_website_rating_result:
        output += "--- 官网价询价结果 ---\n"
        official_website_amount = getattr(official_website_rating_result, 'official_website_amount', '')
        measure_id = getattr(official_website_rating_result, 'measure_id', '')
        output += f"官网总价\t{official_website_amount}\t度量单位\t{measure_id}\t币种\t{currency}\n"

    if optional_discount_rating_results:
        output += "\n--- 可选折扣询价结果 ---\n"
        for od in optional_discount_rating_results:
            discount_id = getattr(od, 'discount_id', '')
            discount_name = getattr(od, 'discount_name', '')
            amount = getattr(od, 'amount', '')
            official_website_amount = getattr(od, 'official_website_amount', '')
            measure_id = getattr(od, 'measure_id', '')
            output += f"折扣ID\t{discount_id}\t折扣名称\t{discount_name}\n"
            output += f"折后总额\t{amount}\t官网价\t{official_website_amount}\t度量单位\t{measure_id}\t币种\t{currency}\n\n"

    if fail_resource_infos:
        output += "--- 失败资源列表 ---\n"
        output += "resource_id\terror_code\terror_msg\n"
        for fail in fail_resource_infos:
            rid = getattr(fail, 'resource_id', '')
            error_code = getattr(fail, 'error_code', '')
            error_msg = getattr(fail, 'error_msg', '')
            output += f"{rid}\t{error_code}\t{error_msg}\n"

    if not output.strip():
        print("询价结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_renew_rate_on_period 查询失败: {e}")
    exit(1)
