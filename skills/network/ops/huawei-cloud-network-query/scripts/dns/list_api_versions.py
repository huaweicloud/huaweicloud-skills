import argparse
import os
import ssl
import json
import urllib.request

parser = argparse.ArgumentParser(description="查询API版本信息列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
args = parser.parse_args()

Region = args.region


def render(versions):
    if not versions:
        print("没有找到API版本信息")
        return
    header = "id\tstatus"
    output = header + "\n"
    for v in versions:
        vid = v.get('id', '')
        status = v.get('status', '')
        output += f"{vid}\t{status}\n"
    print(output)


try:
    endpoint = f"https://dns.{Region}.myhuaweicloud.com"
    url = f"{endpoint}/v2/versions"

    ctx = ssl._create_unverified_context()

    proxy_url = os.getenv("HTTPS_PROXY", "") or os.getenv("HTTP_PROXY", "")
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))
    else:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))

    req = urllib.request.Request(url, method="GET")
    req.add_header("Content-Type", "application/json")

    resp = opener.open(req, timeout=30)
    body = resp.read().decode("utf-8")
    data = json.loads(body)

    versions = data.get("versions", [])

    if not versions:
        print("没有找到API版本信息")
        exit(0)

    render(versions)
except Exception as e:
    print(f"dns.list_api_versions 查询失败: {e}")
    exit(1)
