import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import query_Config_resource_by_sql


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="按 SQL 条件查询 Config 资源（高级查询，仅支持 resources 表）")
    parser.add_argument("--sql", type=str, required=True, help="查询的 SQL 语句，双引号包裹，内部字符串用单引号，示例见 references/sql-example.json")
    args = parser.parse_args()

    try:
        result = query_Config_resource_by_sql(sql=args.sql).get("results", [])
        if not result:
            print("没有找到数据")
            exit(0)

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"config.query_Config_resource_by_sql 查询失败: {e}")
        exit(1)

