import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkobs.v1.obs_credentials import ObsCredentials
from huaweicloudsdkobs.v1 import ObsClient
from huaweicloudsdkobs.v1.model import GetBucketNotificationRequest
from huaweicloudsdkobs.v1.region.obs_region import ObsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="获取桶通知配置")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--bucket_name", type=str, required=True, help="桶名称，可通过 list_buckets.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = GetBucketNotificationRequest()
    request.bucket_name = args.bucket_name

    http_config = build_http_config()
    client = ObsClient.new_builder().with_http_config(http_config).with_credentials(
        ObsCredentials(AK, SK) if not SecurityToken else ObsCredentials(AK, SK, SecurityToken)).with_region(ObsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 OBS 客户端")
        exit(-1)

    response = client.get_bucket_notification(request)

    notification_config = getattr(response, 'notification_configuration', None)

    if not notification_config:
        print("查询结果为空")
        exit(0)

    output = f"桶 {args.bucket_name} 的通知配置:\n"

    topic_configurations = getattr(notification_config, 'topic_configuration', []) or []
    for config in topic_configurations:
        config_id = getattr(config, 'id', '')
        topic = getattr(config, 'topic', '')
        event = getattr(config, 'event', '')
        output += f"Topic配置ID: {config_id}\n"
        output += f"主题: {topic}\n"
        output += f"事件: {event}\n"

    function_stage_configurations = getattr(notification_config, 'function_stage_configuration', []) or []
    for config in function_stage_configurations:
        config_id = getattr(config, 'id', '')
        function_graph = getattr(config, 'function_graph', '')
        event = getattr(config, 'event', '')
        output += f"函数配置ID: {config_id}\n"
        output += f"函数: {function_graph}\n"
        output += f"事件: {event}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"obs.get_bucket_notification 查询失败: {e}")
    exit(1)
