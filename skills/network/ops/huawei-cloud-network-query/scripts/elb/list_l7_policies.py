import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import load_credentials, build_http_config
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkelb.v3 import ElbClient
from huaweicloudsdkelb.v3.model import ListL7PoliciesRequest
from huaweicloudsdkelb.v3.region.elb_region import ElbRegion

AK, SK, Region, SecurityToken = load_credentials()

PAGE_SIZE = 50   # 每页展示条数
FETCH_SIZE = PAGE_SIZE + 1  # 多查1条用于判断是否还有更多
API_LIMIT = 2000  # 服务端单次请求上限

parser = argparse.ArgumentParser(description="查询 ELB 七层转发策略列表")
parser.add_argument("--project_id", type=str, required=True, help="项目 ID，可通过 ../iam/get_project_id.py 获取")
parser.add_argument("--region", type=str, help="区域，默认 cn-north-4")
parser.add_argument("--marker", type=str, help="分页标记，从上次查询结果的 next_marker 获取")
parser.add_argument("--sort_by", type=str, help="排序字段和方向（客户端排序），格式: 字段:方向。字段可选: priority；方向可选: asc(升序), desc(降序)。与 --top 配合使用可快速查找最值")
parser.add_argument("--top", type=int, help="取排序后的前 N 条（客户端截取），需与 --sort_by 配合使用。例如 --sort_by priority:asc --top 5 查找优先级最高的 5 个策略")
parser.add_argument("--id", type=str, nargs="+", help="转发策略ID，支持多值查询")
parser.add_argument("--name", type=str, nargs="+", help="转发策略名称，支持多值查询")
parser.add_argument("--description", type=str, nargs="+", help="转发策略的描述信息，支持多值查询")
parser.add_argument("--listener_id", type=str, nargs="+", help="转发策略所属的监听器ID，支持多值查询，可通过 list_listeners.py 获取")
parser.add_argument("--action", type=str, nargs="+", help="转发动作，支持多值查询，取值: REDIRECT_TO_POOL REDIRECT_TO_LISTENER REDIRECT_TO_URL FIXED_RESPONSE")
parser.add_argument("--position", type=int, nargs="+", help="转发策略的优先级，支持多值查询")
parser.add_argument("--priority", type=int, nargs="+", help="转发策略的优先级，数值越小优先级越高，支持多值查询")
parser.add_argument("--redirect_pool_id", type=str, nargs="+", help="转发到pool的ID，支持多值查询")
parser.add_argument("--redirect_listener_id", type=str, nargs="+", help="转发到的listener的ID，支持多值查询")
parser.add_argument("--redirect_url", type=str, nargs="+", help="转发到的url，支持多值查询")
parser.add_argument("--provisioning_status", type=str, nargs="+", help="转发策略的配置状态，支持多值查询，ACTIVE正常，ERROR策略冲突")
parser.add_argument("--admin_state_up", type=bool, help="转发策略的管理状态")
parser.add_argument("--enterprise_project_id", type=str, nargs="+", help="资源所属的企业项目ID，支持多值查询，可通过 ../eps/list_enterprise_projects.py 获取")
parser.add_argument("--display_all_rules", type=bool, help="是否显示转发策略下的rule详细信息，true显示详细信息，false只显示id信息")
args = parser.parse_args()

if args.region is not None:
    Region = args.region

# 参数校验
if args.top is not None and args.sort_by is None:
    print("--top 需要与 --sort_by 配合使用，例如 --sort_by priority:asc --top 3")
    exit(1)

if args.sort_by is not None:
    sort_parts = args.sort_by.split(':')
    if len(sort_parts) != 2 or sort_parts[0] not in ('priority',) or sort_parts[1] not in ('asc', 'desc'):
        print("--sort_by 格式错误，应为 字段:方向，字段可选: priority；方向可选: asc, desc。例如 priority:asc")
        exit(1)

if args.top is not None and args.top <= 0:
    print("--top 必须为正整数")
    exit(1)

# 判断是否有自定义过滤参数
has_custom_filter = args.sort_by is not None

try:
    http_config = build_http_config()
    client = ElbClient.new_builder().with_http_config(http_config).with_credentials(
        BasicCredentials(AK, SK, args.project_id) if not SecurityToken else BasicCredentials(AK, SK, args.project_id).with_security_token(SecurityToken)).with_region(ElbRegion.value_of(Region)).build()
    if not client:
        print(f"无法获取 ELB 客户端")
        exit(-1)

    request = ListL7PoliciesRequest()
    request.limit = FETCH_SIZE
    if args.marker:
        request.marker = args.marker
    if args.id:
        request.id = args.id
    if args.name:
        request.name = args.name
    if args.description:
        request.description = args.description
    if args.listener_id:
        request.listener_id = args.listener_id
    if args.action:
        request.action = args.action
    if args.position is not None:
        request.position = args.position
    if args.priority is not None:
        request.priority = args.priority
    if args.redirect_pool_id:
        request.redirect_pool_id = args.redirect_pool_id
    if args.redirect_listener_id:
        request.redirect_listener_id = args.redirect_listener_id
    if args.redirect_url:
        request.redirect_url = args.redirect_url
    if args.provisioning_status:
        request.provisioning_status = args.provisioning_status
    if args.admin_state_up is not None:
        request.admin_state_up = args.admin_state_up
    if args.enterprise_project_id:
        request.enterprise_project_id = args.enterprise_project_id
    if args.display_all_rules is not None:
        request.display_all_rules = args.display_all_rules

    if has_custom_filter:
        # 有自定义过滤参数：全量拉取 + 本地排序
        all_l7policies = []
        marker = ""
        while True:
            request.limit = API_LIMIT
            if marker:
                request.marker = marker
            response = client.list_l7_policies(request)
            l7policies = response.l7policies
            if not l7policies:
                break
            if marker and all_l7policies and getattr(l7policies[0], 'id', None) == getattr(all_l7policies[-1], 'id', None):
                break
            all_l7policies.extend(l7policies)
            if len(l7policies) < API_LIMIT:
                break
            marker = l7policies[-1].id
            if not marker:
                break

        if not all_l7policies:
            print("没有找到七层策略")
            exit(0)

        # 客户端排序
        if args.sort_by:
            sort_field, sort_dir = args.sort_by.split(':')
            if sort_field == 'priority':
                all_l7policies.sort(key=lambda f: int(getattr(f, 'priority', 0) or 0), reverse=(sort_dir == 'desc'))

        # top 截取
        if args.top is not None:
            all_l7policies = all_l7policies[:args.top]

        # 渲染
        output = f"name\tid\taction\tpriority\tlistener_id\tredirect_pool_id\tredirect_listener_id\tprovisioning_status\n"
        for item in all_l7policies:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            action = getattr(item, 'action', '')
            priority = getattr(item, 'priority', '')
            listener_id = getattr(item, 'listener_id', '')
            redirect_pool_id = getattr(item, 'redirect_pool_id', '')
            redirect_listener_id = getattr(item, 'redirect_listener_id', '')
            provisioning_status = getattr(item, 'provisioning_status', '')
            output += f"{name}\t{id}\t{action}\t{priority}\t{listener_id}\t{redirect_pool_id}\t{redirect_listener_id}\t{provisioning_status}\n"
        output += f"\n共 {len(all_l7policies)} 条"
        print(output)
    else:
        # 无自定义过滤参数：只查1次
        request.limit = FETCH_SIZE
        if args.marker:
            request.marker = args.marker

        response = client.list_l7_policies(request)
        l7policies = response.l7policies

        if not l7policies:
            print(f"没有找到七层策略 (区域: {Region})")
            exit(0)

        # Response 有 page_info，使用 page_info.next_marker 判断分页
        next_marker = None
        page_info = getattr(response, 'page_info', None)
        if page_info:
            next_marker = getattr(page_info, 'next_marker', None)
            has_more = next_marker is not None
        else:
            has_more = len(l7policies) > PAGE_SIZE
            if has_more:
                next_marker = str(getattr(l7policies[PAGE_SIZE - 1], 'id', ''))

        display_l7policies = l7policies[:PAGE_SIZE]

        output = f"name\tid\taction\tpriority\tlistener_id\tredirect_pool_id\tredirect_listener_id\tprovisioning_status\n"
        for item in display_l7policies:
            name = getattr(item, 'name', '')
            id = getattr(item, 'id', '')
            action = getattr(item, 'action', '')
            priority = getattr(item, 'priority', '')
            listener_id = getattr(item, 'listener_id', '')
            redirect_pool_id = getattr(item, 'redirect_pool_id', '')
            redirect_listener_id = getattr(item, 'redirect_listener_id', '')
            provisioning_status = getattr(item, 'provisioning_status', '')
            output += f"{name}\t{id}\t{action}\t{priority}\t{listener_id}\t{redirect_pool_id}\t{redirect_listener_id}\t{provisioning_status}\n"

        if has_more:
            output += f"\n当前返回 {len(display_l7policies)} 条，还有更多数据"
            if next_marker:
                output += f"\n可使用 --marker={next_marker} 继续查询下一页，或使用过滤参数缩小查询范围"
        else:
            output += f"\n共 {len(display_l7policies)} 条"

        print(output)
except Exception as e:
    print(f"elb.list_l7_policies 查询失败: {e}")
    exit(1)
