import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import list_schema


def query_Config_resource_schema(resource_type):
    """查询指定资源类型的 Schema，循环分页取全后再本地过滤"""
    schemas = []
    marker = None
    while True:
        resp = list_schema(marker)
        schemas += resp.get("value", [])
        marker = (resp.get("page_info") or {}).get("next_marker", "")
        if not marker:
            break

    schemas = [item for item in schemas if resource_type in item.get("type", "")]
    return schemas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查询 Config 资源 Schema（资源结构定义，含字段名/类型/描述）")
    parser.add_argument("--resource_type", type=str, required=True, help="资源类型标识，格式 provider.type，如 obs.buckets、ecs.cloudservers、iam.users、vpc.securityGroups")
    args = parser.parse_args()

    try:
        result = query_Config_resource_schema(resource_type=args.resource_type)
        if not result:
            print("没有找到数据")
            exit(0)

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"config.query_Config_resource_schema 查询失败: {e}")
        exit(1)

