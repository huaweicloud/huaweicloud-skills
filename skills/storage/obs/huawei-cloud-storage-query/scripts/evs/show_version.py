import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ShowVersionRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询指定版本的EVS API信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--version", type=str, required=True, help="版本号，可选：v1、v2、v3，兼容 v1.0/v2.0/v3.0 格式")
parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式，默认 text")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 版本号格式归一化: v3.0 -> v3, v3 -> v3
version = args.version
if version.endswith(".0") and version[:-2] in ("v1", "v2", "v3"):
    version = version[:-2]

try:
    request = ShowVersionRequest()
    request.version = version

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.show_version(request)

    versions = getattr(response, 'versions', []) or []

    if not versions:
        print("查询结果为空")
        exit(0)

    if args.format == "json":
        items = []
        for version_info in versions:
            items.append({
                "id": getattr(version_info, 'id', ''),
                "status": getattr(version_info, 'status', ''),
                "updated": getattr(version_info, 'updated', '')
            })
        print(json.dumps({"version": args.version, "normalized_version": version, "versions": items}, ensure_ascii=False))
        exit(0)

    output = f"EVS API {version} (输入 {args.version}) 版本信息:\n"

    for version_info in versions:
        output += f"版本ID: {getattr(version_info, 'id', '')}\n"
        output += f"状态: {getattr(version_info, 'status', '')}\n"
        output += f"更新时间: {getattr(version_info, 'updated', '')}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.show_version 查询失败: {e}")
    exit(1)