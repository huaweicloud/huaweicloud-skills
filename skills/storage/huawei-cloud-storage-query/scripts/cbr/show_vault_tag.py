import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowVaultTagRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 存储库标签")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--vault_id", type=str, required=True, help="存储库ID，可通过 list_vault.py 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()

    client = CbrClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(CbrRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 CBR 客户端")
        exit(-1)

    request = ShowVaultTagRequest()
    request.vault_id = args.vault_id
    response = client.show_vault_tag(request)

    output = ""
    tags = getattr(response, 'tags', []) or []
    if tags:
        output += f"tags ({len(tags)}):\n"
        for tag in tags:
            key = getattr(tag, 'key', '')
            value = getattr(tag, 'value', '')
            output += f"  {key}: {value}\n"
    else:
        output += "tags: (none)\n"

    sys_tags = getattr(response, 'sys_tags', []) or []
    if sys_tags:
        output += f"\nsys_tags ({len(sys_tags)}):\n"
        for stag in sys_tags:
            key = getattr(stag, 'key', '')
            value = getattr(stag, 'value', None)
            if value is not None:
                output += f"  {key}: {value}\n"
            else:
                output += f"  {key}\n"
    else:
        output += "\nsys_tags: (none)\n"

    print(output)
except Exception as e:
    print(f"cbr.show_vault_tag 查询失败: {e}")
    exit(1)
