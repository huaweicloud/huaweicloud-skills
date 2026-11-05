import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkevs.v2 import EvsClient
from huaweicloudsdkevs.v2.model import ListVersionsRequest
from huaweicloudsdkevs.v2.region.evs_region import EvsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询EVS API版本信息")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 scripts/iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--format", type=str, choices=["text", "json"], default="text", help="输出格式，默认 text")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def normalize_version(version_id):
    # 版本号格式归一化: v3.0 -> v3，兼容 list_versions/show_version 两种入参
    v = version_id or ''
    if v.endswith(".0") and v[:-2] in ("v1", "v2", "v3"):
        return v[:-2]
    return v


try:
    request = ListVersionsRequest()

    http_config = build_http_config()
    client = EvsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(EvsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Evs 客户端")
        exit(-1)

    response = client.list_versions(request)

    versions = getattr(response, 'versions', []) or []

    if not versions:
        print("查询结果为空")
        exit(0)

    if args.format == "json":
        items = []
        for version in versions:
            version_id = getattr(version, 'id', '')
            items.append({
                "id": version_id,
                "version": normalize_version(version_id),
                "status": getattr(version, 'status', ''),
                "updated": getattr(version, 'updated', '')
            })
        print(json.dumps({"versions": items}, ensure_ascii=False))
        exit(0)

    output = "EVS API版本信息:\n"
    output += "版本ID\t可用版本号\t状态\t更新时间\n"

    for version in versions:
        version_id = getattr(version, 'id', '')
        status = getattr(version, 'status', '')
        updated = getattr(version, 'updated', '')
        output += f"{version_id}\t{normalize_version(version_id)}\t{status}\t{updated}\n"

    output += "\n提示: show_version.py 的 --version 参数可直接使用上面的可用版本号(如 v3)"
    print(output.strip())
    exit(0)
except Exception as e:
    print(f"evs.list_versions 查询失败: {e}")
    exit(1)