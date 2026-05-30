import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ShowCertificateRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 ELB 证书详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--certificate_id", type=str, required=True, help="证书 ID（必填），可通过 list_certificates.py 获取")
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

    request = ShowCertificateRequest()
    request.certificate_id = args.certificate_id
    response = client.show_certificate(request)
    item = response.certificate
    if not item:
        print(f"没有找到证书")
        exit(0)

    # 输出详情
    output = f"id\tname\ttype\tdomain\tdescription\tadmin_state_up\texpire_time\tcommon_name\tfingerprint\tsource\tcreated_at\tupdated_at\n"
    id = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    type = getattr(item, 'type', '')
    domain = getattr(item, 'domain', '')
    description = getattr(item, 'description', '')
    admin_state_up = getattr(item, 'admin_state_up', '')
    expire_time = getattr(item, 'expire_time', '')
    common_name = getattr(item, 'common_name', '')
    fingerprint = getattr(item, 'fingerprint', '')
    source = getattr(item, 'source', '')
    created_at = getattr(item, 'created_at', '')
    updated_at = getattr(item, 'updated_at', '')
    output += f"{id}\t{name}\t{type}\t{domain}\t{description}\t{admin_state_up}\t{expire_time}\t{common_name}\t{fingerprint}\t{source}\t{created_at}\t{updated_at}\n"
    print(output)
except Exception as e:
    print(f"elb.show_certificate 查询失败: {e}")
    exit(1)
