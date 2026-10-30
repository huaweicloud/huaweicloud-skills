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


parser = argparse.ArgumentParser(description='查询AS API版本详情')
parser.add_argument('--api_version', type=str, required=True,
                    help='API版本ID，如v1')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')


def query_via_sdk(region, api_version):
    from config import build_http_config
    from huaweicloudsdkcore.auth.credentials import BasicCredentials
    from huaweicloudsdkas.v1 import AsClient, ShowApiVersionRequest
    from huaweicloudsdkas.v1.region.as_region import AsRegion

    credentials = BasicCredentials(AK, SK)
    if SecurityToken:
        credentials = credentials.with_security_token(SecurityToken)
    http_config = build_http_config()

    client = AsClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(AsRegion.value_of(region)).build()

    request = ShowApiVersionRequest()
    request.api_version = api_version
    return client.show_api_version(request)


def query_via_http(region, api_version):
    url = f"https://as.{region}.myhuaweicloud.com/{api_version}"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    class _Link:
        def __init__(self, d):
            self.rel = d.get("rel", "")
            self.href = d.get("href", "")

    class _Version:
        def __init__(self, d):
            self.id = d.get("id", "")
            self.status = d.get("status", "")
            self.min_version = d.get("min_version", "")
            self.version = d.get("version", "")
            self.update = d.get("updated", "")
            self.links = [_Link(l) for l in d.get("links", [])]

    class _Response:
        def __init__(self, data):
            v = data.get("version")
            self.version = _Version(v) if v else None

    return _Response(data)


def main():
    global Region
    args = parser.parse_args()

    if args.region is not None:
        Region = args.region

    try:
        if AK and SK:
            response = query_via_sdk(Region, args.api_version)
        else:
            response = query_via_http(Region, args.api_version)

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
