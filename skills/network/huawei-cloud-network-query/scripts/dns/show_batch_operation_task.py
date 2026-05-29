import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2 import DnsClient
from huaweicloudsdkdns.v2.model import ShowBatchOperationTaskRequest
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询批量操作任务")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--task_id", type=str, required=True, help="批量操作任务ID")
parser.add_argument("--error_item_limit", type=int, help="失败条目限制数")
parser.add_argument("--error_item_offset", type=int, help="失败条目偏移量")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


def render(resp):
    zid = getattr(resp, 'id', '')
    rtype = getattr(resp, 'type', '')
    status = getattr(resp, 'status', '')
    created_at = getattr(resp, 'created_at', '')
    success_count = str(getattr(resp, 'success_count', ''))
    error_count = str(getattr(resp, 'error_count', ''))
    error_items = getattr(resp, 'error_items', []) or []
    output = f"id: {zid}\ntype: {rtype}\nstatus: {status}\ncreated_at: {created_at}\nsuccess_count: {success_count}\nerror_count: {error_count}\n"
    if error_items:
        output += "error_items:\n"
        for item in error_items:
            output += f"  {item}\n"
    print(output)


try:
    http_config = build_http_config()

    client = DnsClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(DnsRegion.value_of(Region)).build()
    if not client:
        print("无法获取 DNS 客户端")
        exit(-1)

    request = ShowBatchOperationTaskRequest()
    request.task_id = args.task_id
    if args.error_item_limit is not None:
        request.error_item_limit = args.error_item_limit
    if args.error_item_offset is not None:
        request.error_item_offset = args.error_item_offset

    response = client.show_batch_operation_task(request)

    render(response)
except Exception as e:
    print(f"dns.show_batch_operation_task 查询失败: {e}")
    exit(1)
