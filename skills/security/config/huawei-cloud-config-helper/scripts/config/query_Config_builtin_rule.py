import argparse
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import list_built_in_policy_definitions


def query_Config_builtin_rule(keyword, limit):
    """查询预置合规规则，按关键词过滤（对名称/展示名/描述/keywords 做忽略大小写的子串匹配）并限制返回数量"""
    if not limit:
        limit = 20
    config_rules = list_built_in_policy_definitions()
    items = (config_rules or {}).get("value") or []

    def _match(item):
        if not keyword:
            return True
        kw = keyword.lower()
        if kw in (item.get("name") or "").lower():
            return True
        if kw in (item.get("display_name") or "").lower():
            return True
        if kw in (item.get("description") or "").lower():
            return True
        return any(kw in str(k).lower() for k in item.get("keywords", []))

    config_rules = [item for item in items if _match(item)]
    config_rules = config_rules[:int(limit)]
    return config_rules


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="查询 Config 服务预置合规规则列表")
    parser.add_argument("--keyword", type=str, help="过滤关键词，对规则名称、描述及 keywords 做忽略大小写的子串匹配，如 obs、vpc、iam")
    parser.add_argument("--limit", type=str, help="限制返回结果数量，默认 20")
    args = parser.parse_args()

    try:
        result = query_Config_builtin_rule(keyword=args.keyword, limit=args.limit)
        if not result:
            print("没有找到数据")
            exit(0)

        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"config.query_Config_builtin_rule 查询失败: {e}")
        exit(1)

