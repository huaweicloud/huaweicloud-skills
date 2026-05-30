import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListScalingTagInfosByTenantIdRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='按租户ID查询标签')
parser.add_argument('--resource_type', type=str, required=True,
                    help='资源类型，枚举类：scaling_group_tag')
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

        request = ListScalingTagInfosByTenantIdRequest()
        request.resource_type = args.resource_type

        response = client.list_scaling_tag_infos_by_tenant_id(request)
        tags = getattr(response, 'tags', []) or []

        if not tags:
            print(f"没有找到标签 (区域: {Region})")
            return

        header = "key\tvalues"
        print(header)
        for t in tags:
            values = ', '.join(getattr(t, 'values', []) or [])
            print(f"{getattr(t, 'key', '')}\t{values}")

    except Exception as e:
        print(f"as.list_scaling_tag_infos_by_tenant_id 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
