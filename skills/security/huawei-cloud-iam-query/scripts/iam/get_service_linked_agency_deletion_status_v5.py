import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkiam.v5 import IamClient
from huaweicloudsdkiam.v5.model import GetServiceLinkedAgencyDeletionStatusV5Request
from huaweicloudsdkiam.v5.region.iam_region import IamRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询服务关联委托删除状态 (v5)")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--deletion_task_id", type=str, required=True, help="删除任务 ID")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    http_config = build_http_config()
    client = IamClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(IamRegion.value_of(Region)).build()
    if not client:
        print("无法获取 IAM 客户端")
        exit(-1)

    request = GetServiceLinkedAgencyDeletionStatusV5Request()
    request.deletion_task_id = args.deletion_task_id
    response = client.get_service_linked_agency_deletion_status_v5(request)
    item = response
    if not item:
        print("没有找到数据")
        exit(0)

    output = f"status	reason	agency_usage_list\n"
    status = getattr(item, 'status', '')
    reason = getattr(item, 'reason', '')
    agency_usage_list = getattr(item, 'agency_usage_list', None)
    usage_str = ''
    if agency_usage_list:
        usage_parts = []
        for usage in agency_usage_list:
            region = getattr(usage, 'region', '')
            resources = getattr(usage, 'resources', [])
            usage_parts.append(f"{region}: {','.join(resources)}")
        usage_str = '; '.join(usage_parts)
    output += f"{status}	{reason}	{usage_str}\n"
    print(output)
except Exception as e:
    print(f"iam.get_service_linked_agency_deletion_status_v5 查询失败: {e}")
    exit(1)
