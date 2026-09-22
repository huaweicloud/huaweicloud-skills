#!/usr/bin/env python3
"""Search Huawei Cloud agent skills by keyword/category.

Only the top-3 (score-descending) search results are reported to the
install-count API (exposure impression, fire-and-forget, non-blocking).
Set SKILL_QUALITY_REPORT=0 to disable this reporting.
This script has no other telemetry and no external CLI dependency.
"""

import argparse
import base64
import binascii
import json
import os
import sys
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# 索引分支可通过环境变量注入（默认指向当前生产使用的 test-for-index 分支，
# 由索引仓库维护方发布正式数据后切换），避免把分支名硬编码散落在各处。
INDEX_BRANCH = os.environ.get("FIND_SKILLS_INDEX_BRANCH", "test-for-index")
DEFAULT_INDEX_URL = "https://gitcode.com/api/v5/repos/developer-skill/skills-group-contribution/contents/skills-index/index.json?ref={}".format(INDEX_BRANCH)
DEFAULT_CN_EN_MAP_URL = "https://gitcode.com/api/v5/repos/developer-skill/skills-group-contribution/contents/skills-index/cn-en-map.json?ref={}".format(INDEX_BRANCH)

HTTP_TIMEOUT = 15

# Install-count API (same endpoint as Step 3 install counting). Used to report
# every search-result skill name as an exposure impression - fire-and-forget,
# never blocks or fails the search.
INSTALL_COUNT_URL = "https://devdata2.huaweicloud.com/rest/developer/fwdo/rest/developer/servlet/hdskillservice/v1/obs/findcounts/increment"
INSTALL_COUNT_TIMEOUT = HTTP_TIMEOUT

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
    except (URLError, HTTPError, OSError, ValueError, UnicodeDecodeError, binascii.Error) as e:
        raise RuntimeError(f"N02: Failed to fetch {label}: {e}") from e


def load_index():
    return load_json_from_url(DEFAULT_INDEX_URL, "index.json")


def load_cn_en_map():
    return load_json_from_url(DEFAULT_CN_EN_MAP_URL, "cn-en-map.json")


def is_generic(kw):
    k = kw.lower().strip()
    return k in GENERIC_KEYWORDS or any(g in k for g in ("华为云", "huawei"))


# 上游 cn-en-map.json 部分 key 是脏数据(如 's: 弹性云服务器'、'or "CCE 告警".',
# 'cloud operations (中文触发词：L实例执行脚本)'), 反向映射时仅使用干净的 CN key,
# 避免 expanded/matched 输出混入乱码(ISSUE-002)。全角冒号/反斜杠同样视为脏标记。
DIRTY_KEY_CHARS = (":", "：", '"', "'", "{", "}", "[", "]", "\\")
MAX_MAP_KEY_LEN = 40


def is_clean_map_key(k):
    if not isinstance(k, str):
        return False
    if k != k.strip() or len(k) > MAX_MAP_KEY_LEN:
        return False
    return not any(ch in k for ch in DIRTY_KEY_CHARS)


def expand_keywords(raw_keyword, cn_en_map):
    if not raw_keyword:
        return [], []
    parts = [p for p in raw_keyword.replace(",", " ").replace(";", " ").split() if p]
    expanded = list(parts)
    for p in parts:
        p_lower = p.lower()
        if p in cn_en_map and is_clean_map_key(p):
            expanded.append(cn_en_map[p])
        for cn, en in cn_en_map.items():
            if en == p_lower and is_clean_map_key(cn):
                expanded.append(cn)
    all_kws = sorted(set(expanded))
    specific = [kw for kw in all_kws if not is_generic(kw)]
    generic = [kw for kw in all_kws if is_generic(kw)]
    return specific, generic


def extract_skill_fields(skill):
    """批量提取 skill 字段(一次性字典访问, 后续循环内只做本地匹配)。"""
    name = skill.get("name", "")
    category = skill.get("category", "")
    service = skill.get("service", "")
    description = skill.get("description", "")
    raw_triggers = skill.get("triggers") or []
    triggers = [t for t in raw_triggers if t]
    return {
        "name": name,
        "category": category,
        "service": service,
        "description": description,
        "triggers": triggers,
    }


def score_skill(fields, specific_kws, generic_kws):
    if not specific_kws and not generic_kws:
        return 1, []
    name_l = fields["name"].lower()
    desc_l = fields["description"].lower()
    service_l = fields["service"].lower()
    trig_l = [t.lower() for t in fields["triggers"]]
    total = 0
    matched = []
    for kw in specific_kws:
        k = kw.lower()
        s = 0
        if k in name_l:
            s += 10
        if any(k in t for t in trig_l):
            s += 8
        if k in desc_l:
            s += 5
        if k in service_l:
            s += 3
        if s > 0:
            total += s
            matched.append(kw)
    for kw in generic_kws:
        k = kw.lower()
        s = 0
        if k in name_l:
            s += 10
        if any(k in t for t in trig_l):
            s += 4
        if k in desc_l:
            s += 2
        if k in service_l:
            s += 1
        if s > 0:
            total += s
            matched.append(kw)
    if not specific_kws and total == 0:
        total = 1
        if len(desc_l) > 20:
            total += 1
        if trig_l:
            total += 1
    return total, matched


def truncate(desc, limit=150):
    if desc and len(desc) > limit:
        return desc[:limit] + "..."
    return desc


def _post_impression(skill_id):
    """Single-instance POST to the install-count API (best-effort)."""
    body = json.dumps({"skill_id": skill_id}).encode("utf-8")
    req = Request(
        INSTALL_COUNT_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://skills.huaweicloud.com",
            "Referer": "https://skills.huaweicloud.com/",
            "User-Agent": "huawei-cloud-find-skills/1.0",
        },
    )
    try:
        with urlopen(req, timeout=INSTALL_COUNT_TIMEOUT) as resp:
            resp.read()
        return True
    except (URLError, HTTPError, OSError, ValueError):
        return False


def report_search_results_impressions(results):
    """Report only the top-3 search results via the install-count API.

    Only the first three results (already sorted by score descending) are reported —
    each skill_id (`skills/<category>/<service>/<name>`) is POSTed to the same
    endpoint Step 3 uses for install counting, so search-result exposures are
    counted too. Fire-and-forget: reporting runs in a daemon background thread and
    returns immediately, so it never blocks or delays the search output.
    """
    if not results:
        return 0
    if os.environ.get("SKILL_QUALITY_REPORT") == "0":
        return 0
    reported = {"n": 0}

    def _worker():
        for r in results[:3]:
            if _post_impression("skills/{}/{}/{}".format(r["category"], r["service"], r["name"])):
                reported["n"] += 1

    threading.Thread(target=_worker, daemon=True).start()
    return reported["n"]


def main():
    parser = argparse.ArgumentParser(description="Search Huawei Cloud skills")
    parser.add_argument("-k", "--keyword", default="", help="Search keyword(s), space/comma/semicolon separated")
    parser.add_argument("-c", "--category", default="", help="Filter by category")
    args = parser.parse_args()

    if not args.keyword and not args.category:
        print("Usage: python search-skills.py -k <keyword> [-c <category>]")
        print("ERROR: missing keyword and category (U02)", file=sys.stderr)
        return 1

    idx = load_index()
    raw_skills = idx.get("skills", [])
    skills = [extract_skill_fields(s) for s in raw_skills]

    if args.keyword:
        cn_en_map = load_cn_en_map()
        specific_kws, generic_kws = expand_keywords(args.keyword, cn_en_map)
    else:
        specific_kws, generic_kws = [], []
    has_specific = bool(specific_kws)

    results = []

    for skill in skills:
        category = skill["category"]
        if args.category and category != args.category:
            continue
        sc, matched = score_skill(skill, specific_kws, generic_kws)
        if has_specific and sc == 0:
            continue
        desc = truncate(skill["description"])
        trig_preview = skill["triggers"][:5]
        results.append({
            "score": sc,
            "name": skill["name"],
            "category": category,
            "service": skill["service"],
            "description": desc,
            "triggers": trig_preview,
            "matched": matched,
        })

    results.sort(key=lambda r: r["score"], reverse=True)

    impressions = report_search_results_impressions(results)

    if not results:
        print(f"No results for keyword='{args.keyword}' category='{args.category}'")
        print()
        print("Fallback suggestions:")
        print("  1. Try broader or alternative keywords")
        print("  2. Remove category filter")
        print("  3. Switch CN<->EN (e.g., 'obs' <-> 'object storage')")
        print("  4. List all: python search-skills.py -c 'computing'")
        return 0

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

    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(rc)
