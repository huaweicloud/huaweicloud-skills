import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListHookInstancesRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询伸缩组挂钩实例列表')
parser.add_argument('--scaling_group_id', type=str, required=True,
                    help='伸缩组ID，可通过 list_scaling_groups.py 获取')
parser.add_argument('--instance_id', type=str, default=None,
                    help='伸缩实例ID')
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

        request = ListHookInstancesRequest()
        request.scaling_group_id = args.scaling_group_id
        if args.instance_id:
            request.instance_id = args.instance_id

        response = client.list_hook_instances(request)
        infos = getattr(response, 'instance_hanging_info', []) or []

        if not infos:
            print(f"没有找到挂钩实例 (区域: {Region})")
            return

        header = "instance_id\tlifecycle_hook_name\tlifecycle_action_key\tlifecycle_hook_status\ttimeout\tdefault_result"
        print(header)
        for i in infos:
            print(f"{getattr(i, 'instance_id', '')}\t{getattr(i, 'lifecycle_hook_name', '')}\t{getattr(i, 'lifecycle_action_key', '')}\t{getattr(i, 'lifecycle_hook_status', '')}\t{getattr(i, 'timeout', '')}\t{getattr(i, 'default_result', '')}")

    except Exception as e:
        print(f"as.list_hook_instances 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
