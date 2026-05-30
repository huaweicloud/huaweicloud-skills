import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowAgencyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 委托详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--agency_id", type=str, required=True, help="委托 ID，可通过 list_agencies_v5.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = ShowAgencyRequest()
    request.agency_id = args.agency_id
    response = client.show_agency(request)
    item = response.agency

    if not item:
        print(f"没有找到 IAM 委托 (区域: {Region}, 委托 ID: {args.agency_id})")
        exit(0)

    id_ = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    domain_id = getattr(item, 'domain_id', '')
    trust_domain_id = getattr(item, 'trust_domain_id', '')
    trust_domain_name = getattr(item, 'trust_domain_name', '')
    description = getattr(item, 'description', '')
    duration = getattr(item, 'duration', '')
    expire_time = getattr(item, 'expire_time', '')
    create_time = getattr(item, 'create_time', '')
    agency_urn = getattr(item, 'agency_urn', '')
    print(f"id\tname\tdomain_id\ttrust_domain_id\ttrust_domain_name\tdescription\tduration\texpire_time\tcreate_time\tagency_urn\n{id_}\t{name}\t{domain_id}\t{trust_domain_id}\t{trust_domain_name}\t{description}\t{duration}\t{expire_time}\t{create_time}\t{agency_urn}")
except Exception as e:
    print(f"iam.show_agency 查询失败: {e}")
    exit(1)
