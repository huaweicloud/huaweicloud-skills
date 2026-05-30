import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ShowResourceQuotaRequest
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='查询AS资源配额')
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

        request = ShowResourceQuotaRequest()
        response = client.show_resource_quota(request)

        quotas = getattr(response, 'quotas', None)
        if not quotas:
            print("未找到配额信息")
            return

        resources = getattr(quotas, 'resources', []) or []
        if not resources:
            print("无配额数据")
            return

        header = "type\tused\tquota\tmax\tmin"
        print(header)
        for r in resources:
            print(f"{getattr(r, 'type', '')}\t{getattr(r, 'used', 0)}\t{getattr(r, 'quota', 0)}\t{getattr(r, 'max', 0)}\t{getattr(r, 'min', 0)}")

    except Exception as e:
        print(f"as.show_resource_quota 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
