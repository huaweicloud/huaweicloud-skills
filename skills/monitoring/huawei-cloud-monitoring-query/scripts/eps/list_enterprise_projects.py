import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import GlobalCredentials
from huaweicloudsdkeps.v1 import EpsClient
from huaweicloudsdkeps.v1.model import ListEnterpriseProjectRequest
from huaweicloudsdkeps.v1.region.eps_region import EpsRegion

# 常量
PAGE_SIZE = 50  # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()

# 参数
parser = argparse.ArgumentParser(description="查询企业项目列表")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--id", type=str, help="企业项目ID，0表示默认企业项目")
parser.add_argument("--name", type=str, help="企业项目名称，支持模糊搜索")
parser.add_argument("--status", type=int, choices=[1, 2], help="企业项目状态: 1(启用)/2(停用)")
parser.add_argument("--type", type=str, choices=["prod", "poc"], help="项目类型: prod(商用项目)/poc(测试项目)")
parser.add_argument("--sort_key", type=str, help="排序关键字，支持updated_at等，默认created_at")
parser.add_argument("--sort_dir", type=str, choices=["asc", "desc"], help="排序方向: asc(升序)/desc(降序)，默认desc")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
args = parser.parse_args()

if args.region is not None:
    Region = args.region


# 渲染
def render(eps_list, total_count=None, has_more=False, next_marker=None):
    """
    渲染企业项目列表
    :param eps_list: 企业项目列表（最多 PAGE_SIZE 条）
    :param total_count: 总数，None 表示未知
    :param has_more: 是否还有更多数据
    :param next_marker: 下一页的 marker
    """
    if not eps_list:
        print("没有找到企业项目")
        return

    output = f"id\tname\tstatus\ttype\tdescription\tcreated_at\tupdated_at\n"
    for ep in eps_list:
        ep_id = getattr(ep, 'id', '')
        name = getattr(ep, 'name', '')
        status = getattr(ep, 'status', '')
        status_str = {1: '启用', 2: '停用'}.get(status, str(status))
        ep_type = getattr(ep, 'type', '')
        description = getattr(ep, 'description', '')
        created_at = getattr(ep, 'created_at', '')
        updated_at = getattr(ep, 'updated_at', '')
        output += f"{ep_id}\t{name}\t{status_str}\t{ep_type}\t{description}\t{created_at}\t{updated_at}\n"

    # 汇总信息
    showing_count = len(eps_list)

    if total_count is not None:
        output += f"\n共 {total_count} 个企业项目，当前返回 {showing_count} 条"
        if has_more and next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status 等参数缩小查询范围"
    elif has_more:
        output += f"\n当前返回 {showing_count} 条，还有更多数据"
        if next_marker:
            output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用 --id / --name / --status 等参数缩小查询范围"
    else:
        output += f"\n共 {showing_count} 个企业项目"

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
    request = ListEnterpriseProjectRequest()
    request.limit = FETCH_SIZE
    # marker 的值就是 offset（已跳过的条数）
    request.offset = int(args.marker) if args.marker else 0
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.status is not None:
        request.status = args.status
    if args.type:
        request.type = args.type
    if args.sort_key:
        request.sort_key = args.sort_key
    if args.sort_dir:
        request.sort_dir = args.sort_dir

    # 只做一次查询
    response = client.list_enterprise_project(request)
    total_count = getattr(response, 'total_count', None)
    eps_list = response.enterprise_projects

    if not eps_list:
        print(f"没有找到企业项目 (区域: {Region})")
        exit(0)

    # 判断是否还有更多数据，计算 next_marker
    next_marker = None
    if total_count is not None:
        has_more = total_count > (request.offset + PAGE_SIZE)
    else:
        # 无 total_count 时，通过多查的第 FETCH_SIZE 条判断
        has_more = len(eps_list) > PAGE_SIZE

    if has_more and len(eps_list) > PAGE_SIZE:
        # 多查的1条存在，说明还有更多，next_marker 为当前 offset + PAGE_SIZE
        next_marker = str(request.offset + PAGE_SIZE)

    # 只展示前 PAGE_SIZE 条
    display_eps = eps_list[:PAGE_SIZE]

    # 渲染结果
    render(display_eps, total_count=total_count, has_more=has_more, next_marker=next_marker)
except Exception as e:
    print(f"eps.list_enterprise_projects 查询失败: {e}")
    exit(1)
