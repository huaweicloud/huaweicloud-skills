#!/usr/bin/env python3
"""AI Gallery 技能搜索脚本 — 数据源为公开 API。"""

import argparse
import json
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

DEFAULT_API_BASE = "https://devdata.huaweicloud.com/rest/modelarts/user_system"
DETAIL_URL_BASE = "https://pangu.huaweicloud.com/gallery/asset-detail.html"
HTTP_TIMEOUT = 10


GENERIC_KEYWORDS = {
    "ai gallery", "gallery", "技能", "skill", "skills",
    "所有", "all", "全部", "有什么", "有哪些", "相关",
    "列表", "list", "查找", "搜索", "发现", "浏览",
    "find", "search", "discover", "browse", "show", "explore",
    "agent", "市场", "market", "类目", "category",
    "安装", "install", "订阅", "subscribe",
}

BROWSE_PATTERNS = [
    "gallery", "skill", "skills", "有什么", "有哪些", "什么", "相关",
    "ai", "agent", "市场", "类目", "浏览", "探索", "发现", "列表",
    "有没有", "帮我找", "介绍", "具体做什么",
]


def fetch_json(url):
    try:
        req = Request(url, headers={"User-Agent": "agentorchard-find-skills/1.0"})
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"Error: 无法获取数据: {e}", file=sys.stderr)
        return None


def map_to_skill(item):
    detail = item.get("content_detail", {})
    if not detail:
        return None
    stats = item.get("content_statistic", {})
    return {
        "name": detail.get("content_title", ""),
        "description": detail.get("short_desc", ""),
        "content_id": detail.get("content_id", ""),
        "show_id": detail.get("show_id", ""),
        "views": stats.get("count_views", 0),
        "stars": stats.get("count_stars", 0),
    }


def load_skills(api_base):
    params = {"content_type": "skills", "limit": 200, "offset": 0, "review_status": 1}
    url = f"{api_base}/v1/aihub/contents?{urlencode(params)}"
    raw = fetch_json(url)
    if raw is None:
        return None
    return [s for s in (map_to_skill(i) for i in raw.get("content_list", [])) if s]


def is_generic(kw):
    k = kw.lower().strip()
    return k in GENERIC_KEYWORDS or "ai gallery" in k


def parse_keywords(raw):
    if not raw:
        return [], []
    parts = [p for p in raw.replace(",", " ").replace(";", " ").split() if p]
    return [k for k in parts if not is_generic(k)], [k for k in parts if is_generic(k)]


def is_browse_intent(keyword, specific_kws):
    if not keyword or not specific_kws:
        return True
    kl = keyword.lower()
    matched_len = sum(len(p) for p in BROWSE_PATTERNS if p in kl)
    return matched_len / len(kl) > 0.8 if kl else True


def score_skill(skill, kws):
    total = 0
    name_l = skill.get("name", "").lower()
    desc_l = skill.get("description", "").lower()
    for kw in kws:
        k = kw.lower()
        if k in name_l:
            total += 20
        if k in desc_l:
            total += 15
    return total


def print_browse(skills):
    hot = sorted(skills, key=lambda s: s["views"] + s["stars"] * 3, reverse=True)[:5]
    print(f"AI Gallery 目前共有 {len(skills)} 个 skill，以下是为您精选的内容：\n")
    print("热门 skill：")
    for i, s in enumerate(hot, 1):
        stats = []
        if s["views"]:
            stats.append(f"浏览:{s['views']}")
        if s["stars"]:
            stats.append(f"收藏:{s['stars']}")
        suffix = f" ({', '.join(stats)})" if stats else ""
        print(f"  {i}. {s['name']}{suffix}")
    print("\n您可以：")
    print("  - 输入功能描述，如 \"PDF处理\" 或 \"图像分类\"")
    print("  - 输入中英文均可，系统自动识别")


def print_results(results):
    print(f"找到 {len(results)} 个相关技能：\n")
    for i, r in enumerate(results, 1):
        print(f"  {i}. {r['name']}")
        if r["description"]:
            print(f"     {r['description']}")
        sid = r.get("show_id") or r.get("content_id")
        if sid:
            print(f"     详情: {DETAIL_URL_BASE}?id={sid}")
        print()


def main():
    parser = argparse.ArgumentParser(description="搜索 AI Gallery 技能")
    parser.add_argument("-k", "--keyword", nargs="?", const="", default="")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    args = parser.parse_args()

    keyword = args.keyword or ""
    skills = load_skills(args.api_base)
    if skills is None:
        print("Error: 无法连接到 AI Gallery API，请检查网络连接。", file=sys.stderr)
        sys.exit(2)

    specific, generic = parse_keywords(keyword)

    if is_browse_intent(keyword, specific):
        if skills:
            print_browse(skills)
        else:
            print("无法获取 skill 数据，请检查网络连接。")
            sys.exit(1)
        sys.exit(0)

    all_kws = specific + generic
    results = []
    for s in skills:
        sc = score_skill(s, all_kws)
        if sc == 0:
            continue
        results.append({"score": sc, **s})

    results.sort(key=lambda r: r["score"], reverse=True)

    if not results:
        print(f"未找到与 '{keyword}' 相关的技能。\n")
        print("建议尝试：")
        print("  1. 使用更广泛或替代的关键词")
        print("  2. 中英文切换（例如 '图像分类' <-> 'image_classification'）")
        sys.exit(0)

    print_results(results)


if __name__ == "__main__":
    main()
