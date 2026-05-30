import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, handle_not_found_error

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowLifeCycleHookRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询生命周期挂钩详情')
parser.add_argument('--scaling_group_id', type=str, required=True,
                    help='伸缩组ID，可通过 list_scaling_groups.py 获取')
parser.add_argument('--lifecycle_hook_name', type=str, required=True,
                    help='生命周期挂钩名称，可通过 list_life_cycle_hooks.py 获取')
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

        request = ShowLifeCycleHookRequest()
        request.scaling_group_id = args.scaling_group_id
        request.lifecycle_hook_name = args.lifecycle_hook_name

        response = client.show_life_cycle_hook(request)

        print(f"lifecycle_hook_name:\t{getattr(response, 'lifecycle_hook_name', '')}")
        print(f"lifecycle_hook_type:\t{getattr(response, 'lifecycle_hook_type', '')}")
        print(f"default_result:\t{getattr(response, 'default_result', '')}")
        print(f"default_timeout:\t{getattr(response, 'default_timeout', 0)}")
        print(f"notification_topic_urn:\t{getattr(response, 'notification_topic_urn', '')}")
        print(f"notification_topic_name:\t{getattr(response, 'notification_topic_name', '')}")
        print(f"notification_metadata:\t{getattr(response, 'notification_metadata', '')}")
        print(f"create_time:\t{getattr(response, 'create_time', '')}")

    except Exception as e:
        handle_not_found_error(e, "lifecycleHook", args.lifecycle_hook_name)


if __name__ == '__main__':
    main()
