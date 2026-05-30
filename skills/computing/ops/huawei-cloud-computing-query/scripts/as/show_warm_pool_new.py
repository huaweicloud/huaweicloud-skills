import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id, handle_not_found_error

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowWarmPoolNewRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询暖池信息(新)')
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

        request = ShowWarmPoolNewRequest()
        request.scaling_group_id = args.scaling_group_id

        response = client.show_warm_pool_new(request)
        pool = getattr(response, 'warm_pool', None)
        if not pool:
            print("未找到暖池信息")
            return

        print(f"min_capacity:\t{getattr(pool, 'min_capacity', 0)}")
        print(f"max_capacity:\t{getattr(pool, 'max_capacity', 0)}")
        print(f"instance_init_wait_time:\t{getattr(pool, 'instance_init_wait_time', 0)}")
        print(f"status:\t{getattr(pool, 'status', '')}")

    except Exception as e:
        handle_not_found_error(e, "warmPool", args.scaling_group_id)


if __name__ == '__main__':
    main()
