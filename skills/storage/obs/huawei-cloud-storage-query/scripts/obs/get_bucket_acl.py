import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetBucketAclRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶ACL")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetBucketAclRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_bucket_acl(request)

    owner = getattr(response, 'owner', None)
    acl = getattr(response, 'access_control_list', None)

    output = "桶ACL信息:\n"
    if owner:
        output += f"所有者ID: {getattr(owner, 'id', '')}\n"
    if acl:
        grants = getattr(acl, 'grant', []) or []
        for i, g in enumerate(grants):
            grantee = getattr(g, 'grantee', None)
            grantee_type = getattr(grantee, 'type', '') if grantee else ''
            grantee_id = getattr(grantee, 'id', '') if grantee else ''
            grantee_name = getattr(grantee, 'display_name', '') if grantee else ''
            grantee_uri = getattr(grantee, 'uri', '') if grantee else ''
            permission = getattr(g, 'permission', '')
            output += f"授权[{i}]: 被授权者类型={grantee_type}, 被授权者ID={grantee_id}, 显示名称={grantee_name}, URI={grantee_uri}, 权限={permission}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_bucket_acl 查询失败: {e}")
    exit(1)
