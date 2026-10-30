import argparse
import json
import ssl
import sys
import os
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials_optional

# 初始化凭据（API 版本查询为公开接口，AK/SK 可选）
AK, SK, Region, SecurityToken = load_credentials_optional()


parser = argparse.ArgumentParser(description='查询AS API版本列表')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')


def query_via_sdk(region):
    from config import build_http_config
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkas.v1 import AsClient, ListApiVersionsRequest
    from huaweicloudsdkas.v1.region.as_region import AsRegion

    credentials = BasicCredentials(AK, SK)
    if SecurityToken:
        credentials = credentials.with_security_token(SecurityToken)
    http_config = build_http_config()

    client = AsClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(AsRegion.value_of(region)).build()

    request = ListApiVersionsRequest()
    return client.list_api_versions(request)


def query_via_http(region):
    url = f"https://as.{region}.myhuaweicloud.com/"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    class _Version:
        def __init__(self, d):
            self.id = d.get("id", "")
            self.status = d.get("status", "")
            self.min_version = d.get("min_version", "")
            self.version = d.get("version", "")
            self.update = d.get("updated", "")

    class _Response:
        def __init__(self, data):
            self.versions = [_Version(v) for v in data.get("versions", [])]

    return _Response(data)


def main():
    global Region
    args = parser.parse_args()

    if args.region is not None:
        Region = args.region

    try:
        if AK and SK:
            response = query_via_sdk(Region)
        else:
            response = query_via_http(Region)

        versions = getattr(response, 'versions', []) or []
        if not versions:
            print(f"没有找到API版本 (区域: {Region})")
            return

        header = "id\tstatus\tmin_version\tversion\tupdate"
        print(header)
        for v in versions:
            print(f"{getattr(v, 'id', '')}\t{getattr(v, 'status', '')}\t{getattr(v, 'min_version', '')}\t{getattr(v, 'version', '')}\t{getattr(v, 'update', '')}")

    except Exception as e:
        print(f"as.list_api_versions 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
