import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import load_credentials, build_http_config
from _common import resolve_project_id

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkas.v1 import AsClient, ListResourceInstancesRequest, QueryTagsOption, TagsMultiValue, Matches
from huaweicloudsdkas.v1.region.as_region import AsRegion

# 资源类型枚举
RESOURCE_TYPES = ["SCALING_GROUP_TAG", "SCALING_CONFIGURATION_TAG"]

# 初始化凭据
AK, SK, Region, SecurityToken = load_credentials()


parser = argparse.ArgumentParser(description='按标签查询资源实例（POST .../resource_instances/action）')
parser.add_argument('--resource_type', type=str, required=True, choices=RESOURCE_TYPES,
                    help='资源类型，枚举类：SCALING_GROUP_TAG（伸缩组）、SCALING_CONFIGURATION_TAG（伸缩配置）')
parser.add_argument('--tag', action='append', metavar='KEY=VALUE',
                    help='过滤条件：包含该标签，格式 key=value；可多次传入，多个之间为 AND 关系。只传 key（不带 =）表示该 key 任意值')
parser.add_argument('--tag_any', action='append', metavar='KEY=VALUE',
                    help='过滤条件：包含任意一个标签，格式 key=value；可多次传入，多个之间为 OR 关系')
parser.add_argument('--not_tag', action='append', metavar='KEY=VALUE',
                    help='过滤条件：不包含该标签，格式 key=value；可多次传入')
parser.add_argument('--not_tag_any', action='append', metavar='KEY=VALUE',
                    help='过滤条件：不包含任意一个标签，格式 key=value；可多次传入')
parser.add_argument('--match', action='append', metavar='KEY=VALUE',
                    help='模糊搜索字段，目前仅支持 key=resource_name，例如 --match resource_name=web；可多次传入')
parser.add_argument('--count', action='store_true',
                    help='只查询满足条件的资源总数（action=count），不返回资源明细')
parser.add_argument('--limit', type=str,
                    help='查询记录数，取值范围 1-1000，默认 1000（action=count 时不生效）')
parser.add_argument('--offset', type=str,
                    help='索引位置，从该位置的下一条数据开始查询，默认为 0（action=count 时不生效）')
parser.add_argument('--marker', type=str,
                    help='分页位置标识（资源 ID 或索引位置），用于查询下一页')
parser.add_argument('--project_id', type=str, default=None,
                    help='项目ID，不传则通过 IAM API 根据 --region 自动获取')
parser.add_argument('--region', type=str,
                    help='区域，默认从环境变量获取')


def parse_kv_pairs(items):
    """把 ['key=value', 'key2'] 解析成 [(key, value_or_None)]"""
    pairs = []
    for item in items or []:
        if '=' in item:
            key, _, value = item.partition('=')
            key, value = key.strip(), value.strip()
        else:
            key, value = item.strip(), None
        if not key:
            print(f"标签参数格式错误: {item}，正确格式为 key=value")
            exit(1)
        pairs.append((key, value))
    return pairs


def build_tags(pairs):
    """构造 TagsMultiValue 列表；只给 key 时 values 传空列表表示任意值"""
    tags = []
    for key, value in pairs:
        tags.append(TagsMultiValue(key=key, values=[value] if value is not None else []))
    return tags


def main():
    global Region
    args = parser.parse_args()

    if args.region is not None:
        Region = args.region

    tags = build_tags(parse_kv_pairs(args.tag))
    tags_any = build_tags(parse_kv_pairs(args.tag_any))
    not_tags = build_tags(parse_kv_pairs(args.not_tag))
    not_tags_any = build_tags(parse_kv_pairs(args.not_tag_any))

    matches = []
    for key, value in parse_kv_pairs(args.match):
        if value is None:
            print(f"模糊匹配参数格式错误: {key}，正确格式为 key=value（如 resource_name=web）")
            exit(1)
        matches.append(Matches(key=key, value=value))

    if args.count and (args.limit is not None or args.offset is not None or args.marker is not None):
        print("--count 与 --limit/--offset/--marker 不能同时使用")
        exit(1)

    # 使用 sdk
    try:
        project_id = resolve_project_id(Region, args.project_id)
        credentials = BasicCredentials(AK, SK, project_id)
        if SecurityToken:
            credentials = credentials.with_security_token(SecurityToken)
        http_config = build_http_config()

        client = AsClient.new_builder().with_http_config(http_config).with_credentials(credentials).with_region(AsRegion.value_of(Region)).build()

        # 请求体为必需参数，缺失会返回 400 / AS.0002 Request body is null
        body = QueryTagsOption(
            action='count' if args.count else 'filter',
            tags=tags or None,
            tags_any=tags_any or None,
            not_tags=not_tags or None,
            not_tags_any=not_tags_any or None,
            matches=matches or None,
            limit=args.limit,
            offset=args.offset,
            marker=args.marker,
        )
        request = ListResourceInstancesRequest(resource_type=args.resource_type, body=body)

        response = client.list_resource_instances(request)
        total_count = getattr(response, 'total_count', 0)

        if args.count:
            print(f"total_count:\t{total_count}")
            return

        resources = getattr(response, 'resources', []) or []

        if not resources:
            print(f"没有找到资源实例 (区域: {Region}, resource_type: {args.resource_type})")
            return

        print(f"total_count:\t{total_count}")
        header = "resource_id\tresource_name\tresource_detail"
        print(header)
        for r in resources:
            print(f"{getattr(r, 'resource_id', '')}\t{getattr(r, 'resource_name', '')}\t{getattr(r, 'resource_detail', '')}")
            tags_of_resource = getattr(r, 'tags', []) or []
            if tags_of_resource:
                tag_str = ', '.join(
                    f"{getattr(t, 'key', '')}={getattr(t, 'value', getattr(t, 'values', ''))}"
                    for t in tags_of_resource
                )
                print(f"  tags: {tag_str}")

        print(f"\n共 {total_count} 条资源实例，当前返回 {len(resources)} 条")
        if total_count > len(resources):
            print("可使用 --offset 翻页继续查询（将上一次返回的条数累加后作为下一次的 --offset）")

    except Exception as e:
        print(f"as.list_resource_instances 查询失败: {e}")
        exit(1)


if __name__ == '__main__':
    main()
