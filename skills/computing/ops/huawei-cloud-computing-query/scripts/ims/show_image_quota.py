import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkims.v2 import ImsClient
from huaweicloudsdkims.v2.model import ShowImageQuotaRequest
from huaweicloudsdkims.v2.region.ims_region import ImsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 IMS 镜像配额，包括已使用数量和配额上限")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
args = parser.parse_args()

Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()
    # 未指定 project_id 则自动获取
    if not args.project_id:
        args.project_id = get_project_id(Region, AK, SK, SecurityToken)
        if not args.project_id:
            print(f"无法获取项目 ID (region={Region})，请检查凭据或手动指定 --project_id")
            exit(-1)


    client = ImsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ImsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 IMS 客户端")
        exit(-1)

    request = ShowImageQuotaRequest()
    response = client.show_image_quota(request)

    quotas = response.quotas
    if not quotas:
        print(f"没有找到镜像配额 (区域: {Region})")
        exit(0)

    # 渲染结果
    resources = getattr(quotas, 'resources', [])
    output = f"type\tused\tquota\tmin\tmax\n"
    for r in resources:
        r_type = getattr(r, 'type', '')
        used = str(getattr(r, 'used', 0))
        quota = str(getattr(r, 'quota', 0))
        r_min = str(getattr(r, 'min', 0))
        r_max = str(getattr(r, 'max', 0))
        output += f"{r_type}\t{used}\t{quota}\t{r_min}\t{r_max}\n"
    print(output)
except Exception as e:
    print(f"ims.show_image_quota 查询失败: {e}")
    exit(1)
