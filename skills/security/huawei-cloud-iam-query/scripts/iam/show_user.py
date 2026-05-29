import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v3 import IamClient
from huaweicloudsdkiam.v3.model import ShowUserRequest
from huaweicloudsdkiam.v3.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 IAM 用户详情 (v3)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--user_id", type=str, required=True, help="用户 ID，可通过 list_users_v5.py 获取")
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

    request = ShowUserRequest()
    request.user_id = args.user_id
    response = client.show_user(request)
    item = response.user

    if not item:
        print(f"没有找到 IAM 用户 (区域: {Region}, 用户 ID: {args.user_id})")
        exit(0)

    id_ = getattr(item, 'id', '')
    name = getattr(item, 'name', '')
    enabled = getattr(item, 'enabled', '')
    domain_id = getattr(item, 'domain_id', '')
    links = getattr(item, 'links', None)
    links_str = str(links) if links else ''
    xuser_id = getattr(item, 'xuser_id', '')
    xuser_type = getattr(item, 'xuser_type', '')
    areacode = getattr(item, 'areacode', '')
    email = getattr(item, 'email', '')
    phone = getattr(item, 'phone', '')
    pwd_status = getattr(item, 'pwd_status', '')
    update_time = getattr(item, 'update_time', '')
    create_time = getattr(item, 'create_time', '')
    last_login_time = getattr(item, 'last_login_time', '')
    last_pwd_auth_time = getattr(item, 'last_pwd_auth_time', '')
    pwd_strength = getattr(item, 'pwd_strength', '')
    is_domain_owner = getattr(item, 'is_domain_owner', '')
    access_mode = getattr(item, 'access_mode', '')
    description = getattr(item, 'description', '')
    pwd_create_time = getattr(item, 'pwd_create_time', '')
    modify_pwd_time = getattr(item, 'modify_pwd_time', '')
    print(f"id\tname\tenabled\tdomain_id\txuser_id\txuser_type\tareacode\temail\tphone\tpwd_status\tpwd_strength\tis_domain_owner\taccess_mode\tdescription\tcreate_time\tupdate_time\tlast_login_time\tlast_pwd_auth_time\tpwd_create_time\tmodify_pwd_time\tlinks\n{id_}\t{name}\t{enabled}\t{domain_id}\t{xuser_id}\t{xuser_type}\t{areacode}\t{email}\t{phone}\t{pwd_status}\t{pwd_strength}\t{is_domain_owner}\t{access_mode}\t{description}\t{create_time}\t{update_time}\t{last_login_time}\t{last_pwd_auth_time}\t{pwd_create_time}\t{modify_pwd_time}\t{links_str}")
except Exception as e:
    print(f"iam.show_user 查询失败: {e}")
    exit(1)
