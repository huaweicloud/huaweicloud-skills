import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkbms.v1 import BmsClient
from huaweicloudsdkbms.v1.model import ShowAvailableResourceRequest
from huaweicloudsdkbms.v1.region.bms_region import BmsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询可用区资源信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--availability_zone", type=str, nargs='+', required=True, help="可用区列表，可指定多个，如 cn-north-4a")
parser.add_argument("--flavor_id", type=str, nargs='+', help="规格ID列表，可指定多个，可通过 list_baremetal_flavor_detail_extends.py 获取")
parser.add_argument("--dec_project_id", type=str, nargs='+', help="专属分布式存储池ID列表，可指定多个")
parser.add_argument("--check_limit", type=str, nargs='+', help="检查配额限制，可指定多个")
parser.add_argument("--expectation", type=str, nargs='+', help="期望值，可指定多个")
parser.add_argument("--resource_type", type=str, nargs='+', help="资源类型，可指定多个")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = BmsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)
    ).with_region(BmsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 BMS 客户端")
        exit(-1)

    # 构建请求
    request = ShowAvailableResourceRequest()
    if args.availability_zone:
        request.availability_zone = args.availability_zone
    if args.flavor_id:
        request.flavor_id = args.flavor_id
    if args.dec_project_id:
        request.dec_project_id = args.dec_project_id
    if args.check_limit:
        request.check_limit = args.check_limit
    if args.expectation:
        request.expectation = args.expectation
    if args.resource_type:
        request.resource_type = args.resource_type

    response = client.show_available_resource(request)
    available_resource = response.available_resource

    if not available_resource:
        print(f"没有找到可用区资源信息 (区域: {Region})")
        exit(0)

    # 渲染
    output = f"availability_zone\tflavor_id\tcount\tstatus\n"
    for resource in available_resource:
        az = getattr(resource, 'availability_zone', '')
        flavors = getattr(resource, 'flavors', None) or []
        if flavors:
            for flavor in flavors:
                flavor_id = getattr(flavor, 'flavor_id', '')
                count = getattr(flavor, 'count', 0)
                status = getattr(flavor, 'status', '')
                output += f"{az}\t{flavor_id}\t{count}\t{status}\n"
        else:
            output += f"{az}\t\t\t\n"

    print(output)
except Exception as e:
    print(f"bms.show_available_resource 查询失败: {e}")
    exit(1)
