import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkbss.v2 import BssClient
from huaweicloudsdkbss.v2.model import ListFreeResourceInfosRequest, ListFreeResourceInfosReq
from huaweicloudsdkbss.v2.region.bss_region import BssRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询免费资源信息列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--x_language", type=str, default="zh_CN", help="语言。zh_CN：中文 en_US：英文。默认为zh_CN")
parser.add_argument("--region_code", type=str, help="云服务区编码，例如cn-north-1。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件")
parser.add_argument("--order_id", type=str, help="订单ID。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件")
parser.add_argument("--product_id", type=str, help="产品ID，即资源包ID。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件")
parser.add_argument("--product_name", type=str, help="产品名称，即资源包名称。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件")
parser.add_argument("--enterprise_project_id", type=str, help="企业项目ID。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--status", type=int, help="状态。0：未生效 1：生效中 2：已用完 3：已失效 4：已退订。此参数不携带或携带值为空串或携带值为null时，不作为筛选条件")
parser.add_argument("--limit", type=int, default=50, help="每次查询的记录数。默认值为50")
parser.add_argument("--offset", type=int, default=0, help="偏移量，从0开始。默认值为0")
parser.add_argument("--service_type_code_list", type=str, nargs='+', help="云服务类型编码列表，大小写不敏感，例如hws.service.type.obs。此参数不携带或携带值为空列表或携带值为null时，不作为筛选条件")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    body = ListFreeResourceInfosReq()
    if args.region_code:
        body.region_code = args.region_code
    if args.order_id:
        body.order_id = args.order_id
    if args.product_id:
        body.product_id = args.product_id
    if args.product_name:
        body.product_name = args.product_name
    if args.enterprise_project_id:
        body.enterprise_project_id = args.enterprise_project_id
    if args.status is not None:
        body.status = args.status
    if args.offset is not None:
        body.offset = args.offset
    if args.limit is not None:
        body.limit = args.limit
    if args.service_type_code_list:
        body.service_type_code_list = args.service_type_code_list

    request = ListFreeResourceInfosRequest()
    request.x_language = args.x_language
    request.body = body

    http_config = build_http_config()
    client = BssClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(BssRegion.CN_NORTH_1).build()
    if not client:
        print("无法获取 Bss 客户端")
        exit(-1)

    response = client.list_free_resource_infos(request)

    total_count = getattr(response, 'total_count', 0)
    free_resource_packages = getattr(response, 'free_resource_packages', []) or []

    output = f"总记录数\t{total_count}\n"
    
    if free_resource_packages:
        output += "\n资源包信息列表:\n"
        output += "资源包实例ID\t订单ID\t产品ID\t产品名称\t企业项目ID\t企业项目应用范围\t生效时间\t失效时间\t状态\t云服务类型编码\t云服务类型名称\t区域编码\t来源类型\t套餐绑定类型\t使用模式\n"
        for pkg in free_resource_packages:
            order_instance_id = getattr(pkg, 'order_instance_id', '')
            order_id = getattr(pkg, 'order_id', '')
            product_id = getattr(pkg, 'product_id', '')
            product_name = getattr(pkg, 'product_name', '')
            enterprise_project_id = getattr(pkg, 'enterprise_project_id', '')
            enterprise_project_scope = getattr(pkg, 'enterprise_project_scope', '')
            effective_time = getattr(pkg, 'effective_time', '')
            expire_time = getattr(pkg, 'expire_time', '')
            status = getattr(pkg, 'status', '')
            service_type_code = getattr(pkg, 'service_type_code', '')
            service_type_name = getattr(pkg, 'service_type_name', '')
            region_code = getattr(pkg, 'region_code', '')
            source_type = getattr(pkg, 'source_type', '')
            bundle_type = getattr(pkg, 'bundle_type', '')
            quota_reuse_mode = getattr(pkg, 'quota_reuse_mode', '')
            output += f"{order_instance_id}\t{order_id}\t{product_id}\t{product_name}\t{enterprise_project_id}\t{enterprise_project_scope}\t{effective_time}\t{expire_time}\t{status}\t{service_type_code}\t{service_type_name}\t{region_code}\t{source_type}\t{bundle_type}\t{quota_reuse_mode}\n"

    if not output.strip():
        print("查询结果为空")
        exit(0)

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"bss.list_free_resource_infos 查询失败: {e}")
    exit(1)
