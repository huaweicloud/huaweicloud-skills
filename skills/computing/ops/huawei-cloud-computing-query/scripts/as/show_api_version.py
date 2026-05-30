import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowApiVersionRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询AS API版本详情')
parser.add_argument('--api_version', type=str, required=True,
                    help='API版本ID，如v1')
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

        request = ShowApiVersionRequest()
        request.api_version = args.api_version

        response = client.show_api_version(request)
        version = getattr(response, 'version', None)
        if not version:
            print("未找到API版本")
            return

        print(f"id:\t{getattr(version, 'id', '')}")
        print(f"status:\t{getattr(version, 'status', '')}")
        print(f"min_version:\t{getattr(version, 'min_version', '')}")
        print(f"version:\t{getattr(version, 'version', '')}")
        print(f"update:\t{getattr(version, 'update', '')}")

        links = getattr(version, 'links', []) or []
        if links:
            print("\nlinks:")
            for l in links:
                print(f"  rel={getattr(l, 'rel', '')}, href={getattr(l, 'href', '')}")

    except Exception as e:
        print(f"as.show_api_version 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
