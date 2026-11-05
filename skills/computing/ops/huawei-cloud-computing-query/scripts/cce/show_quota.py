import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcce.v3 import CceClient
from huaweicloudsdkcce.v3.model import ShowQuotasRequest
from huaweicloudsdkcce.v3.region.cce_region import CceRegion

# 参数
parser = argparse.ArgumentParser(description="查询 CCE 资源配额")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
args = parser.parse_args()

# 初始化凭据（放在参数解析之后，保证未配置 AK/SK 时 --help 仍能正常打印）
AK, SK, Region, SecurityToken = load_credentials()

Region = args.region


# 渲染
def render(quotas):
    if not quotas:
        print("没有找到 CCE 配额信息")
        return

    output = "quota_key\tquota_limit\tused\tremain\tunit\tregion_id\tavailability_zone_id\n"
    for quota in quotas:
        quota_key = getattr(quota, 'quota_key', '')
        quota_limit = getattr(quota, 'quota_limit', '')
        used = getattr(quota, 'used', '')
        remain = ''
        if isinstance(quota_limit, int) and isinstance(used, int):
            remain = quota_limit - used
        output += f"{quota_key}\t{quota_limit}\t{used}\t{remain}\t{getattr(quota, 'unit', '')}\t{getattr(quota, 'region_id', '')}\t{getattr(quota, 'availability_zone_id', '')}\n"

    # 汇总信息
    output += f"\n共 {len(quotas)} 项 CCE 配额"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)

    client = CceClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CceRegion.value_of(Region)).build()
    if not client:
        print("无法获取 CCE 客户端")
        exit(-1)

    request = ShowQuotasRequest()
    response = client.show_quotas(request)
    quotas = response.quotas or []

    if not quotas:
        print(f"没有找到 CCE 配额信息 (区域: {Region})")
        exit(0)

    # 渲染结果
    render(quotas)
except Exception as e:
    print(f"cce.quotas 查询失败: {e}")
    exit(1)
