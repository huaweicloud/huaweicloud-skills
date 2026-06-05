import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkces.v2 import ListAlarmHistoriesRequest, CesClient
from huaweicloudsdkces.v2.region.ces_region import CesRegion

AK, SK, Region, SecurityToken = load_credentials()

parser = argparse.ArgumentParser(description="查询告警历史列表")
parser.add_argument("--region", type=str, default="cn-north-4", help="区域，默认 cn-north-4")
parser.add_argument("--alarm_id", type=str, help="告警ID，多个用逗号分隔，可通过 list_alarm_rules.py 获取，最多50个")
parser.add_argument("--record_id", type=str, help="告警流水号，以ah开头，后跟22位字母或数字，长度24")
parser.add_argument("--name", type=str, help="告警规则名称(支持模糊匹配)，最大128字符")
parser.add_argument("--status", type=str, help="告警状态，多个用逗号分隔：ok(已解决)/alarm(告警中)/invalid(已失效)/insufficient_data(数据不足)/ok_manual(已解决手动)，最多3个")
parser.add_argument("--level", type=int, help="告警级别：1紧急/2重要/3次要/4提示")
parser.add_argument("--namespace", type=str, help="服务命名空间，格式service.item，长度3-32")
parser.add_argument("--resource_id", type=str, help="告警资源ID，多维度按字母升序逗号分隔，长度0-2048")
parser.add_argument("--from_time", type=str, help="查询起始更新时间，格式：2022-02-10T10:05:46+08:00。必须与to_time同时使用")
parser.add_argument("--to_time", type=str, help="查询截止更新时间，格式：2022-02-10T10:05:47+08:00。必须与from_time同时使用")
parser.add_argument("--alarm_type", type=str, help="告警类型：event(事件类型)/metric(指标类型)")
parser.add_argument("--create_time_from", type=str, help="查询起始创建时间，格式：2022-02-10T10:05:46+08:00。必须与create_time_to同时使用")
parser.add_argument("--create_time_to", type=str, help="查询截止创建时间，格式：2022-02-10T10:05:47+08:00。必须与create_time_from同时使用")
parser.add_argument("--offset", type=int, help="分页偏移量，最小0，最大1000000000，默认0")
parser.add_argument("--limit", type=int, default=100, help="分页大小，最小1，最大100，默认100")
parser.add_argument("--order_by", type=str, help="排序字段，枚举值：first_alarm_time/update_time/alarm_level/record_id，默认update_time")
parser.add_argument("--mask_status", type=str, help="屏蔽状态，枚举值：UN_MASKED(活跃告警)/MASKED(屏蔽告警)")
args = parser.parse_args()

if (args.from_time is not None) != (args.to_time is not None):
    parser.error("from_time 和 to_time 必须同时指定或同时不指定")

if (args.create_time_from is not None) != (args.create_time_to is not None):
    parser.error("create_time_from 和 create_time_to 必须同时指定或同时不指定")

if args.region is not None:
    Region = args.region

try:
    request = ListAlarmHistoriesRequest()
    if args.alarm_id:
        request.alarm_id = args.alarm_id.split(',')
    if args.record_id:
        request.record_id = args.record_id
    if args.name:
        request.name = args.name
    if args.status:
        request.status = args.status.split(',')
    if args.level is not None:
        request.level = args.level
    if args.namespace:
        request.namespace = args.namespace
    if args.resource_id:
        request.resource_id = args.resource_id
    if args.from_time:
        request._from = args.from_time
    if args.to_time:
        request.to = args.to_time
    if args.alarm_type:
        request.alarm_type = args.alarm_type
    if args.create_time_from:
        request.create_time_from = args.create_time_from
    if args.create_time_to:
        request.create_time_to = args.create_time_to
    if args.offset is not None:
        request.offset = args.offset
    if args.limit is not None:
        request.limit = args.limit
    if args.order_by:
        request.order_by = args.order_by
    if args.mask_status:
        request.mask_status = args.mask_status

    http_config = build_http_config()
    client = CesClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK) if not SecurityToken else BasicCredentials(AK, SK).with_security_token(SecurityToken)).with_region(CesRegion.value_of(Region)).build()
    if not client:
        print("无法获取 Ces 客户端")
        exit(-1)

    response = client.list_alarm_histories(request)

    alarm_histories = getattr(response, 'alarm_histories', []) or []
    count = getattr(response, 'count', 0)

    if not alarm_histories:
        print("查询结果为空")
        exit(0)

    output = f"告警历史列表（共{count}个）:\n"
    output += "流水号\t告警ID\t名称\t状态\t级别\t告警类型\t开始时间\t结束时间\n"
    
    for history in alarm_histories:
        record_id = getattr(history, 'record_id', '')
        alarm_id = getattr(history, 'alarm_id', '')
        name = getattr(history, 'name', '')
        status = getattr(history, 'status', '')
        level = getattr(history, 'level', '')
        alarm_type = getattr(history, 'type', '')
        begin_time = getattr(history, 'begin_time', '')
        end_time = getattr(history, 'end_time', '')
        output += f"{record_id}\t{alarm_id}\t{name}\t{status}\t{level}\t{alarm_type}\t{begin_time}\t{end_time}\n"

    print(output.strip())
    exit(0)
except Exception as e:
    print(f"ces.list_alarm_histories 查询失败: {e}")
    exit(1)
