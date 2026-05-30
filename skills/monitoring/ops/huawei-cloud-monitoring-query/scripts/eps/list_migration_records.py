import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ListMigrationRecordRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目迁移记录列表")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--start_time", type=str, help="开始时间，格式: yyyy-MM-ddThh:mm:ssZ")
parser.add_argument("--end_time", type=str, help="结束时间，格式: yyyy-MM-ddThh:mm:ssZ")
parser.add_argument("--resource_id", type=str, help="资源ID，用于精确过滤")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(records, total_count=None, has_more=False, next_marker=None):
    """
    渲染迁移记录列表
    :param records: 迁移记录列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not records:
        print("没有找到迁移记录")
        return

    output = f"resource_id\tresource_name\tresource_type\toperate_type\torigin_ep_name\ttarget_ep_name\tevent_time\tstatus\n"
    for r in records:
        resource_id = getattr(r, 'resource_id', '')
        resource_name = getattr(r, 'resource_name', '')
        resource_type = getattr(r, 'resource_type', '')
        operate_type = getattr(r, 'operate_type', '')
        origin_ep_name = getattr(r, 'origin_ep_name', '')
        target_ep_name = getattr(r, 'target_ep_name', '')
        event_time = getattr(r, 'event_time', '')
        associated = getattr(r, 'associated', None)
        status = '成功' if associated is True else ('失败' if associated is False else str(associated))
        output += f"{resource_id}\t{resource_name}\t{resource_type}\t{operate_type}\t{origin_ep_name}\t{target_ep_name}\t{event_time}\t{status}\n"

    # 汇总信息
    showing_count = len(records)

    if total_count is not None:
        output += f"\n共 {total_count} 条迁移记录，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --start_time / --end_time / --resource_id 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --start_time / --end_time / --resource_id 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 条迁移记录"

    print(output)


# 使用 sdk
try:
    http_config = build_http_config()

    client = EpsClient.new_builder().with_http_config(http_config).with_credentials(
        GlobalCredentials(AK, SK) if not SecurityToken else GlobalCredentials(AK, SK).with_security_token(SecurityToken)).with_region(EpsRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 EPS 客户端")
        exit(-1)

    # API 使用 offset/limit 分页（无 marker），用 --marker 传递 offset 值实现翻页
    request = ListMigrationRecordRequest()
    request.limit = FETCH_SIZE
    # marker 的值就是 offset（已跳过的条数）
    request.offset = str(int(args.marker) if args.marker else 0)
    if args.start_time:
        request.start_time = args.start_time
    if args.end_time:
        request.end_time = args.end_time
    if args.resource_id:
        request.resource_id = args.resource_id

    # 只做一次查询
    response = client.list_migration_record(request)
    records = response.records

    if not records:
        print(f"没有找到迁移记录 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    # Response 无 total_count/page_info，通过多查的第 FETCH_SIZE 条判断
    next_marker = None
    has_more = len(records) > PAGE_SIZE

    if has_more:
        # 多查的1条存在，说明还有更多，next_marker 为当前 offset + PAGE_SIZE
        next_marker = str(int(args.marker) if args.marker else 0) + PAGE_SIZE
        next_marker = str(next_marker)

    # 只展示前 PAGE_SIZE 条
    display_records = records[:PAGE_SIZE]

    # 渲染结果
    render(display_records, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eps.list_migration_records 查询失败: {e}")
    exit(1)
