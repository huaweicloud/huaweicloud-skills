#!/usr/bin/env python3
import argparse
import base64
import json

import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


DEFAULT_INDEX_URL = "https://gitcode.com/api/v5/repos/2501_91318609/skills-for-index/contents/skills-index/index.json?ref=main"
DEFAULT_CN_EN_MAP_URL = "https://gitcode.com/api/v5/repos/2501_91318609/skills-for-index/contents/skills-index/cn-en-map.json?ref=main"

HTTP_TIMEOUT = 15

GENERIC_KEYWORDS = {
    "华为云", "huawei", "huawei cloud", "云", "cloud",
    "技能", "skill", "skills", "所有", "all", "全部",
    "有什么", "有哪些", "相关", "列表", "list",
    "查找", "搜索", "发现", "浏览", "find", "search",
    "discover", "browse", "show", "explore",
    "agent", "市场", "market", "类目", "category",
    "安装", "install",
}


def load_json_from_url(url, label=""):
    try:
        req = Request(url, headers={"User-Agent": "huawei-cloud-find-skills/1.0"})
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
        parsed = json.loads(data)
        if isinstance(parsed, dict) and parsed.get("encoding") == "base64" and "content" in parsed:
            decoded = base64.b64decode(parsed["content"]).decode("utf-8")
            return json.loads(decoded)
        return parsed
    except (URLError, HTTPError, json.JSONDecodeError) as e:
        print(f"Error: Failed to fetch {label}: {e}", file=sys.stderr)
        sys.exit(1)


def load_index():
    return load_json_from_url(DEFAULT_INDEX_URL, "index.json")


def load_cn_en_map():
    return load_json_from_url(DEFAULT_CN_EN_MAP_URL, "cn-en-map.json")


def is_generic(kw):
    k = kw.lower().strip()
    return k in GENERIC_KEYWORDS or any(g in k for g in ("华为云", "huawei"))


def expand_keywords(raw_keyword, cn_en_map):
    if not raw_keyword:
        return [], []
    parts = [p for p in raw_keyword.replace(",", " ").replace(";", " ").split() if p]
    expanded = list(parts)
    for p in parts:
        p_lower = p.lower()
        if p in cn_en_map:
            expanded.append(cn_en_map[p])
        for cn, en in cn_en_map.items():
            if en == p_lower:
                expanded.append(cn)
    all_kws = sorted(set(expanded))
    specific = [kw for kw in all_kws if not is_generic(kw)]
    generic = [kw for kw in all_kws if is_generic(kw)]
    return specific, generic


def score_skill(skill, specific_kws, generic_kws):
    if not specific_kws and not generic_kws:
        return 1, []
    total = 0
    matched = []
    for kw in specific_kws:
        k = kw.lower()
        s = 0
        if k in skill.get("name", "").lower():
            s += 10
        for t in skill.get("triggers") or []:
            if t and k in t.lower():
                s += 8
                break
        if k in (skill.get("description") or "").lower():
            s += 5
        if k in (skill.get("service") or "").lower():
            s += 3
        if s > 0:
            total += s
            matched.append(kw)
    for kw in generic_kws:
        k = kw.lower()
        s = 0
        if k in skill.get("name", "").lower():
            s += 10
        for t in skill.get("triggers") or []:
            if t and k in t.lower():
                s += 4
                break
        if k in (skill.get("description") or "").lower():
            s += 2
        if k in (skill.get("service") or "").lower():
            s += 1
        if s > 0:
            total += s
            matched.append(kw)
    if not specific_kws and total == 0:
        total = 1
        desc = skill.get("description") or ""
        if len(desc) > 20:
            total += 1
        if skill.get("triggers"):
            total += 1
    return total, matched


def truncate(desc, limit=150):
    if desc and len(desc) > limit:
        return desc[:limit] + "..."
    return desc


def main():
    parser = argparse.ArgumentParser(description="Search Huawei Cloud skills")
    parser.add_argument("-k", "--keyword", default="", help="Search keyword(s), space/comma/semicolon separated")
    parser.add_argument("-c", "--category", default="", help="Filter by category")
    args = parser.parse_args()

    idx = load_index()

    if not args.keyword and not args.category:
        cats = ", ".join(idx.get("categories", []))
        print("Usage: python search-skills.py -k <keyword> [-c <category>]")
        print(f"Categories: {cats}")
        sys.exit(1)

    cn_en_map = load_cn_en_map()
    specific_kws, generic_kws = expand_keywords(args.keyword, cn_en_map)
    has_specific = bool(specific_kws)

    results = []

    for skill in idx.get("skills", []):
        if args.category and skill.get("category") != args.category:
            continue
        sc, matched = score_skill(skill, specific_kws, generic_kws)
        if has_specific and sc == 0:
            continue
        desc = truncate(skill.get("description"))
        trig_preview = (skill.get("triggers") or [])[:5]
        results.append({
            "score": sc,
            "name": skill.get("name", ""),
            "category": skill.get("category", ""),
            "service": skill.get("service", ""),
            "description": desc,
            "triggers": trig_preview,
            "matched": matched,
        })

    results.sort(key=lambda r: r["score"], reverse=True)

    if not results:
        print(f"No results for keyword='{args.keyword}' category='{args.category}'")
        print()
        print("Fallback suggestions:")
        print("  1. Try broader or alternative keywords")
        print("  2. Remove category filter")
        print("  3. Switch CN<->EN (e.g., 'obs' <-> 'object storage')")
        print("  4. List all: python search-skills.py -c 'computing'")
        sys.exit(0)

    all_kws = specific_kws + generic_kws
    print(f"Found {len(results)} skill(s) for keyword='{args.keyword}' category='{args.category}':")
    if len(all_kws) > 1 or (len(all_kws) == 1 and all_kws[0] != args.keyword):
        print(f"  (expanded: {', '.join(all_kws)})")
    print()
    for r in results:
        match_info = f" matched: {','.join(r['matched'])}" if r["matched"] else ""
        print(f"  [{r['score']}pts] {r['name']} ({r['category']}/{r['service']}){match_info}")
        print(f"    {r['description']}")
        if r["triggers"]:
            print(f"    triggers: {', '.join(r['triggers'])}")
        print()


if __name__ == "__main__":
    main()
