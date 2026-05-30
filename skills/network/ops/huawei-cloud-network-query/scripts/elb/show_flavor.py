import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowFlavorRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB Flavor 详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--flavor_id", type=str, required=True, help="Flavor ID（必填），可通过 list_flavors.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ShowFlavorRequest()
    request.flavor_id = args.flavor_id
    response = client.show_flavor(request)
    item = response.flavor
    if not item:
        print(f"没有找到 Flavor")
        exit(0)

    # 输出详情
    output = f"id\tname\ttype\tshared\tflavor_sold_out\tpublic_border_group\tcategory\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    type = getattr(item, 'type', '')
    shared = getattr(item, 'shared', '')
    flavor_sold_out = getattr(item, 'flavor_sold_out', '')
    public_border_group = getattr(item, 'public_border_group', '')
    category = getattr(item, 'category', '')
    output += f"{id}\t{name}\t{type}\t{shared}\t{flavor_sold_out}\t{public_border_group}\t{category}\n"
    print(output)
except Exception as e:
    print(f"elb.show_flavor 查询失败: {e}")
    exit(1)
