import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ShowEnterpriseProjectQuotaRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目配额")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EpsClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(EpsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EPS 客户端")
        exit(-1)

    request = ShowEnterpriseProjectQuotaRequest()
    response = client.show_enterprise_project_quota(request)

    quotas = getattr(response, 'quotas', None)
    if not quotas:
        print(f"没有找到企业项目配额信息")
        exit(0)

    resources = getattr(quotas, 'resources', []) or []
    if not resources:
        print(f"没有找到企业项目配额资源")
        exit(0)

    output = f"type\tused\tquota\tlimit\n"
    for r in resources:
        r_type = getattr(r, 'type', '')
        used = getattr(r, 'used', 0)
        quota = getattr(r, 'quota', 0)
        limit = getattr(r, 'limit', 0)
        output += f"{r_type}\t{used}\t{quota}\t{limit}\n"
    print(output.strip())
except Exception as e:
    print(f"eps.show_enterprise_project_quota 查询失败: {e}")
    exit(1)
