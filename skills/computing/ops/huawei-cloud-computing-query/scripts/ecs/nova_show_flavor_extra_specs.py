import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config, get_project_id
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import NovaShowFlavorExtraSpecsRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 规格扩展属性")
parser.add_argument("--project_id", type=str, help="项目 ID，不传则通过 IAM API 根据 --region 自动获取")
parser.add_argument("--region", type=str, required=True, help="区域，例如 cn-north-4、cn-east-3")
parser.add_argument("--flavor_id", type=str, required=True, help="规格 ID，可通过 list_flavors.py 获取")
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


    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = NovaShowFlavorExtraSpecsRequest()
    request.flavor_id = args.flavor_id
    response = client.nova_show_flavor_extra_specs(request)
    extra_specs = response.extra_specs

    if not extra_specs:
        print(f"没有找到规格扩展属性 (区域: {Region}, 规格 ID: {args.flavor_id})")
        exit(0)

    # 渲染结果
    output = f"key\tvalue\n"
    for key, value in extra_specs.items():
        output += f"{key}\t{value}\n"
    print(output)
except Exception as e:
    print(f"ecs.nova_show_flavor_extra_specs 查询失败: {e}")
    exit(1)
