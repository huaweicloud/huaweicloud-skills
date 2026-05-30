import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetAgencyV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询委托详情 (v5)")
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

    request = GetAgencyV5Request()
    request.agency_id = args.agency_id
    response = client.get_agency_v5(request)
    item = response.agency
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"agency_id	agency_name	description	trust_domain_id	trust_domain_name	created_at	max_session_duration	urn	path	tags\n"
    agency_id = getattr(item, 'agency_id', '')
    agency_name = getattr(item, 'agency_name', '')
    description = getattr(item, 'description', '')
    trust_domain_id = getattr(item, 'trust_domain_id', '')
    trust_domain_name = getattr(item, 'trust_domain_name', '')
    created_at = getattr(item, 'created_at', '')
    max_session_duration = getattr(item, 'max_session_duration', '')
    urn = getattr(item, 'urn', '')
    path = getattr(item, 'path', '')
    tags = getattr(item, 'tags', None)
    tags_str = ';'.join([f"{getattr(t, 'key', '')}={getattr(t, 'value', '')}" for t in tags]) if tags else ''
    output += f"{agency_id}	{agency_name}	{description}	{trust_domain_id}	{trust_domain_name}	{created_at}	{max_session_duration}	{urn}	{path}	{tags_str}\n"
    print(output)
except Exception as e:
    print(f"iam.get_agency_v5 查询失败: {e}")
    exit(1)
