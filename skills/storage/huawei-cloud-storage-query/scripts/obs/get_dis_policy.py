import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetDisPolicyRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶DIS通知策略")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetDisPolicyRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_dis_policy(request)

    rules_obj = getattr(response, 'rules', None)

    if not rules_obj:
        print("查询结果为空")
        exit(0)

    rules = getattr(rules_obj, 'rules', []) or []

    if not rules:
        print("查询结果为空")
        exit(0)

    output = f"桶 {args.bucket_name} 的DIS通知策略:\n"

    for rule in rules:
        rule_id = getattr(rule, 'id', '')
        stream = getattr(rule, 'stream', '')
        project = getattr(rule, 'project', '')
        events = getattr(rule, 'events', []) or []
        prefix = getattr(rule, 'prefix', '')
        suffix = getattr(rule, 'suffix', '')
        agency = getattr(rule, 'agency', '')
        output += f"规则ID: {rule_id}\n"
        output += f"DIS流: {stream}\n"
        output += f"项目ID: {project}\n"
        output += f"事件: {', '.join(events)}\n"
        output += f"前缀: {prefix}\n"
        output += f"后缀: {suffix}\n"
        output += f"委托: {agency}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_dis_policy 查询失败: {e}")
    exit(1)
