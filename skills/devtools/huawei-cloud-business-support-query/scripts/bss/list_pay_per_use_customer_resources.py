import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListPayPerUseCustomerResourcesRequest
from huaweicloudsdkbss.v2.model import QueryResourcesReq
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询按需客户资源列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--resource_id", type=str, action='append', help="资源ID列表。最大支持50个ID同时作为条件查询。此参数不携带或携带值为空列表时，不作为筛选条件（可多次指定）")
parser.add_argument("--order_id", type=str, help="订单号。查询指定订单下的资源。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件")
parser.add_argument("--only_main_resource", type=int, default=0, help="是否只查询主资源。0：查询主资源及附属资源；1：只查询主资源。默认值为0")
parser.add_argument("--status", type=int, action='append', help="资源状态。2：使用中；3：已关闭；4：已冻结；5：已过期（可多次指定）")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--limit", type=int, default=50, help="每次查询的条数。默认值为50")
parser.add_argument("--expire_time_begin", type=str, help="查询指定时间段内失效的资源列表，时间段的起始时间，UTC时间，格式：yyyy-MM-dd'T'HH:mm:ss'Z'")
parser.add_argument("--expire_time_end", type=str, help="查询指定时间段内失效的资源列表，时间段的结束时间，UTC时间，格式：yyyy-MM-dd'T'HH:mm:ss'Z'")
parser.add_argument("--service_type_code", type=str, help="云服务类型编码。此参数不携带、携带值为null，不作为筛选条件")
parser.add_argument("--customer_id", type=str, help="客户账号ID，伙伴查询子客户包年/包月资源列表时必须携带该字段")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    body = QueryResourcesReq()
    if args.resource_id:
        body.resource_ids = args.resource_id
    if args.order_id:
        body.order_id = args.order_id
    if args.only_main_resource is not None:
        body.only_main_resource = args.only_main_resource
    if args.status:
        body.status_list = args.status
    if args.offset is not None:
        body.offset = args.offset
    if args.limit is not None:
        body.limit = args.limit
    if args.expire_time_begin:
        body.expire_time_begin = args.expire_time_begin
    if args.expire_time_end:
        body.expire_time_end = args.expire_time_end
    if args.service_type_code:
        body.service_type_code = args.service_type_code
    if args.customer_id:
        body.customer_id = args.customer_id

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    request = ListPayPerUseCustomerResourcesRequest()
    request.body = body
    response = client.list_pay_per_use_customer_resources(request)

    total_count = getattr(response, 'total_count', 0)
    data = getattr(response, 'data', []) or []

    output = f"总记录数\t{total_count}\n"
    if data:
        output += "\n资源列表:\n"
        output += "id\tresource_id\tresource_name\tregion_code\tservice_type_code\tresource_type_code\tresource_type_name\tservice_type_name\tresource_spec_code\tproject_id\tproduct_id\tparent_resource_id\tis_main_resource\tstatus\teffective_time\texpire_time\texpire_policy\tproduct_spec_desc\tspec_size\tspec_size_measure_id\tupdate_time\n"
        for resource in data:
            _id = getattr(resource, 'id', '')
            resource_id = getattr(resource, 'resource_id', '')
            resource_name = getattr(resource, 'resource_name', '')
            region_code = getattr(resource, 'region_code', '')
            service_type_code = getattr(resource, 'service_type_code', '')
            resource_type_code = getattr(resource, 'resource_type_code', '')
            resource_type_name = getattr(resource, 'resource_type_name', '')
            service_type_name = getattr(resource, 'service_type_name', '')
            resource_spec_code = getattr(resource, 'resource_spec_code', '')
            project_id = getattr(resource, 'project_id', '')
            product_id = getattr(resource, 'product_id', '')
            parent_resource_id = getattr(resource, 'parent_resource_id', '')
            is_main_resource = getattr(resource, 'is_main_resource', '')
            status = getattr(resource, 'status', '')
            effective_time = getattr(resource, 'effective_time', '')
            expire_time = getattr(resource, 'expire_time', '')
            expire_policy = getattr(resource, 'expire_policy', '')
            product_spec_desc = getattr(resource, 'product_spec_desc', '')
            spec_size = getattr(resource, 'spec_size', '')
            spec_size_measure_id = getattr(resource, 'spec_size_measure_id', '')
            update_time = getattr(resource, 'update_time', '')
            output += f"{_id}\t{resource_id}\t{resource_name}\t{region_code}\t{service_type_code}\t{resource_type_code}\t{resource_type_name}\t{service_type_name}\t{resource_spec_code}\t{project_id}\t{product_id}\t{parent_resource_id}\t{is_main_resource}\t{status}\t{effective_time}\t{expire_time}\t{expire_policy}\t{product_spec_desc}\t{spec_size}\t{spec_size_measure_id}\t{update_time}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_pay_per_use_customer_resources 查询失败: {e}")
    exit(1)
