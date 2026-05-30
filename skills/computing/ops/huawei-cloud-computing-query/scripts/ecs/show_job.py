import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkecs.v2 import EcsClient
from huaweicloudsdkecs.v2.model import ShowJobRequest
from huaweicloudsdkecs.v2.region.ecs_region import EcsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询 ECS 异步任务详情")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--job_id", type=str, required=True, help="任务 ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 使用 sdk
try:
    http_config = build_http_config()

    client = EcsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EcsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ECS 客户端")
        exit(-1)

    request = ShowJobRequest()
    request.job_id = args.job_id
    response = client.show_job(request)

    # 渲染结果
    output = ""
    output += f"job_id: {getattr(response, 'job_id', '')}\n"
    output += f"status: {getattr(response, 'status', '')}\n"
    output += f"job_type: {getattr(response, 'job_type', '')}\n"
    output += f"begin_time: {getattr(response, 'begin_time', '')}\n"
    output += f"end_time: {getattr(response, 'end_time', '')}\n"
    output += f"error_code: {getattr(response, 'error_code', '')}\n"
    output += f"fail_reason: {getattr(response, 'fail_reason', '')}\n"
    print(output)
except Exception as e:
    print(f"ecs.job 查询失败: {e}")
    exit(1)
