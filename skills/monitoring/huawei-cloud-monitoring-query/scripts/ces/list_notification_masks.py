import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import CesClient
from huaweicloudsdkces.v2.model import ListNotificationMasksRequest, ListNotificationMaskRequestBody, ListRelationType
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询通知屏蔽规则列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--offset", type=int, help="分页偏移量，范围0-10000，默认0")
parser.add_argument("--limit", type=int, default=100, help="分页大小，范围1-100，默认100")
parser.add_argument("--sort_key", type=str, help="排序关键字，与sort_dir同时使用，枚举值：create_time(按创建时间)/update_time(按修改时间)")
parser.add_argument("--sort_dir", type=str, help="排序顺序，与sort_key同时使用，枚举值：DESC(降序)/ASC(升序)")
parser.add_argument("--mask_id", type=str, help="屏蔽规则ID，以nm开头，后跟0-62位字母或数字")
parser.add_argument("--mask_name", type=str, help="屏蔽规则名称，字母/数字/汉字/-/_，长度1-64")
parser.add_argument("--mask_status", type=str, help="屏蔽状态，枚举值：MASK_EFFECTIVE(已生效)/MASK_INEFFECTIVE(未生效)")
parser.add_argument("--relation_type", type=str, default="ALARM_RULE", help="关联类型，枚举值：ALARM_RULE/DEFAULT/RESOURCE/RESOURCE_POLICY_ALARM/RESOURCE_POLICY_NOTIFICATION，默认ALARM_RULE")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

try:
    request = ListNotificationMasksRequest()
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir

    body = ListNotificationMaskRequestBody()
    relation_type_map = {
        "ALARM_RULE": ListRelationType.ALARM_RULE,
        "DEFAULT": ListRelationType.DEFAULT,
        "RESOURCE": ListRelationType.RESOURCE,
        "RESOURCE_POLICY_ALARM": ListRelationType.RESOURCE_POLICY_ALARM,
        "RESOURCE_POLICY_NOTIFICATION": ListRelationType.RESOURCE_POLICY_NOTIFICATION,
    }
    body.relation_type = relation_type_map.get(args.relation_type, ListRelationType.ALARM_RULE)
    if args.mask_id:
        body.mask_id = args.mask_id
    if args.mask_name:
        body.mask_name = args.mask_name
    if args.mask_status:
        body.mask_status = args.mask_status
    request.body = body

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_notification_masks(request)

    masks = getattr(response, 'notification_masks', []) or []
    count = getattr(response, 'count', 0)

    if not masks:
        print("查询结果为空")
        exit(0)

    output = f"通知屏蔽规则列表（共{count}个）:\n"
    output += "屏蔽规则ID\t名称\t状态\t屏蔽类型\t起始日期\t起始时间\t截止日期\t截止时间\n"
    
    for mask in masks:
        notification_mask_id = getattr(mask, 'notification_mask_id', '')
        mask_name = getattr(mask, 'mask_name', '')
        mask_status = getattr(mask, 'mask_status', '')
        mask_type = getattr(mask, 'mask_type', '')
        start_date = getattr(mask, 'start_date', '')
        start_time = getattr(mask, 'start_time', '')
        end_date = getattr(mask, 'end_date', '')
        end_time = getattr(mask, 'end_time', '')
        output += f"{notification_mask_id}\t{mask_name}\t{mask_status}\t{mask_type}\t{start_date}\t{start_time}\t{end_date}\t{end_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_notification_masks 查询失败: {e}")
    exit(1)
