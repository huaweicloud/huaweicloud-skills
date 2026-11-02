import argparse
import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import query_Config_resource_by_sql

# provider/type/region_id 仅允许字母、数字、下划线、中划线、点，防止 SQL 注入
_SAFE_PATTERN = re.compile(r'^[A-Za-z0-9_.-]+$')


def _validate_param(name, value):
    """校验参数只含安全字符，不合法则拒参"""
    if value and not _SAFE_PATTERN.match(value):
        raise ValueError(f"参数 {name} 含非法字符，仅允许字母/数字/下划线/中划线/点: {value}")
    return value


def query_Config_resource_summary_by_sql(provider, resource_type, region_id):
    """通过高级查询 SQL 统计各服务/类型/区域的资源数量"""
    provider = _validate_param("provider", provider)
    resource_type = _validate_param("resource_type", resource_type)
    region_id = _validate_param("region_id", region_id)

    select_statement = "SELECT provider, type, region_id, count(1) AS cnt FROM resources "
    where_statement = ""
    if provider:
        where_statement += f" AND provider = '{provider}'"
    if resource_type:
        where_statement += f" AND type = '{resource_type}'"
    if region_id:
        where_statement += f" AND region_id = '{region_id}'"
    if where_statement:
        where_statement = "WHERE " + where_statement[5:]

    group_statement = " GROUP BY provider, type, region_id"
    sql = select_statement + where_statement + group_statement
    return query_Config_resource_by_sql(sql).get("results", [])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查询 Config 资源概览（按服务/类型/区域统计资源数量）")
    parser.add_argument("--provider", type=str, help="只查询指定云服务，如 obs、vpc；也支持 provider.type 形式（如 obs.buckets）")
    parser.add_argument("--region_id", type=str, help="只查询指定区域，如 cn-north-4（北京四）、cn-east-3（上海一）、global（全局）")
    args = parser.parse_args()

    try:
        provider = args.provider
        # 支持 provider.type 形式，同时筛选云服务与资源类型
        if provider and "." in provider:
            resource_provider, resource_type = provider.split(".")[0], provider.split(".")[1]
        else:
            resource_provider, resource_type = provider, ""

        result = query_Config_resource_summary_by_sql(resource_provider, resource_type, args.region_id)
        if not result:
            print("没有找到数据")
            exit(0)

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"config.query_Config_resource_summary 查询失败: {e}")
        exit(1)

