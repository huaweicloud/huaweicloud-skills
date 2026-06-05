import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListScalingNotificationsRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询弹性伸缩组通知列表')
parser.add_argument('--scaling_group_id', type=str, required=True,
                    help='伸缩组ID，可通过 list_scaling_groups.py 获取')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')


def main():
    global Region
    args = parser.parse_args()

    if args.region is not None:
        Region = args.region

    # 使用 sdk
    try:
        project_id = resolve_project_id(Region, args.project_id)
        credentials = BasicCredentials(AK, SK, project_id)
        if SecurityToken:
            credentials = credentials.with_security_token(SecurityToken)
        http_config = build_http_config()

        client = AsClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(AsRegion.value_of(Region)).build()

        request = ListScalingNotificationsRequest()
        request.scaling_group_id = args.scaling_group_id

        response = client.list_scaling_notifications(request)
        topics = getattr(response, 'topics', []) or []

        if not topics:
            print(f"没有找到通知 (区域: {Region})")
            return

        header = "topic_urn\ttopic_name\ttopic_scene"
        print(header)
        for t in topics:
            scene = ', '.join(getattr(t, 'topic_scene', []) or [])
            print(f"{getattr(t, 'topic_urn', '')}\t{getattr(t, 'topic_name', '')}\t{scene}")

    except Exception as e:
        print(f"as.list_scaling_notifications 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
