import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcbr.v1 import CbrClient
from huaweicloudsdkcbr.v1.model import ShowMetadataRequest
from huaweicloudsdkcbr.v1.region.cbr_region import CbrRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询 CBR 备份元数据")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--backup_id", type=str, required=True, help="备份ID")
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

    request = ShowMetadataRequest()
    request.backup_id = args.backup_id
    response = client.show_metadata(request)

    output = ""
    output += f"backup_id: {getattr(response, 'backup_id', '')}\n"
    output += f"backups: {getattr(response, 'backups', '')}\n"
    output += f"flavor: {getattr(response, 'flavor', '')}\n"
    floatingips = getattr(response, 'floatingips', []) or []
    output += f"floatingips: {floatingips}\n"
    output += f"interface: {getattr(response, 'interface', '')}\n"
    ports = getattr(response, 'ports', []) or []
    output += f"ports: {ports}\n"
    output += f"server: {getattr(response, 'server', '')}\n"
    volumes = getattr(response, 'volumes', []) or []
    output += f"volumes: {volumes}\n"
    print(output)
except Exception as e:
    print(f"cbr.show_metadata 查询失败: {e}")
    exit(1)
