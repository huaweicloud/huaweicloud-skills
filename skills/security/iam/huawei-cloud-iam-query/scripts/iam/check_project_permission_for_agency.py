import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import CheckProjectPermissionForAgencyRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="检查委托是否拥有项目权限 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 get_project_id.py 获取")
parser.add_argument("--agency_id", type=str, required=True, help="委托 ID，可通过 list_agencies_v5.py 获取")
parser.add_argument("--role_id", type=str, required=True, help="权限 ID，可通过 list_attached_agency_policies_v5.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = CheckProjectPermissionForAgencyRequest()
    request.project_id = args.project_id
    request.agency_id = args.agency_id
    request.role_id = args.role_id
    response = client.check_project_permission_for_agency(request)
    print("检查通过: True")
except Exception as e:
    print(f"检查失败: {e}")
    exit(1)
