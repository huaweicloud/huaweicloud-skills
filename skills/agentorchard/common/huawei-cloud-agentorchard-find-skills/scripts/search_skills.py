#!/usr/bin/env python3
"""AI Gallery 技能搜索脚本 — 数据源为公开 API。"""

import argparse
import json
import re
import sys
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

DEFAULT_API_BASE = "https://devdata.huaweicloud.com/rest/aiasset/user_system"
DETAIL_URL_BASE = "https://pangu.huaweicloud.com/gallery/asset-detail-page.html"
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

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
CJK_RUN_RE = re.compile(r"([\u4e00-\u9fff]+|[^\u4e00-\u9fff]+)")
SPLIT_PUNCT_RE = re.compile(r"[，。！？、；;:：,.!?()（）\[\]【】\"']+")

# 中文自然语言中的指令词/语气词：搜索前先剔除，剩余部分才作为核心关键词
INSTRUCTION_WORDS = [
    "帮我找一个", "帮我找一下", "帮我找找", "请帮我找一下", "请帮我找", "帮我找",
    "我想找一个", "我想找", "我要找一个", "我要找", "想要找一个", "想要找",
    "有没有", "是否有", "是否存在", "介绍一下", "介绍下", "具体做什么",
    "具体是做什么", "是做什么的", "做什么的", "大概是做什么", "大致是什么",
    "帮我", "我想", "我要", "想要", "请帮", "请问", "请", "有的",
    "一个", "一下", "同时", "两个方向", "方向", "找找", "看看",
    "相关", "有关", "关于", "以及", "还有", "也是", "分别是",
]

# 中文连词/助词：作为切分符处理，避免跨词边界产生无意义 n-gram
CJK_SEPARATORS = ["和", "与", "跟", "或", "及", "以及", "的", "之", "于"]


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


def strip_instruction_words(text):
    for w in sorted(INSTRUCTION_WORDS, key=len, reverse=True):
        if not w:
            continue
        text = text.replace(w, " ")
    return text


def split_separators(text):
    for sep in sorted(CJK_SEPARATORS, key=len, reverse=True):
        if not sep:
            continue
        text = text.replace(sep, " ")
    return text


def cjk_ngrams(run):
    """对连续中文字符串做核心词 n-gram 切分。

    短串（<=4 字）保留全部 2-4 字子串；长串仅取 3-4 字 n-gram，
    避免"分析"“分类”这类高频 2 字词在长句中造成大量噪音匹配。
    """
    ngrams = set()
    n = len(run)
    if n == 1:
        return ngrams
    if n == 2:
        sizes = (2,)
    elif n == 3:
        sizes = (2, 3)
    else:
        sizes = (3, 4)
    for size in sizes:
        if size > n:
            continue
        for i in range(n - size + 1):
            gram = run[i:i + size]
            if not is_generic(gram):
                ngrams.add(gram)
    return ngrams


def parse_keywords(raw):
    """将用户输入拆分为具体关键词与通用词。

    中文整句（如"帮我找一个银行对公信贷分析的skill"）会先剔除指令词，
    再对连续中文字符串按 2-4 字的核心词 n-gram 切分，保证任意核心子串
    都能参与包含匹配，避免整个句子被当作单个关键词导致必不命中。
    """
    if not raw:
        return [], []
    text = split_separators(strip_instruction_words(format_input(raw)))
    specific, generic = [], []
    for token in text.split():
        if is_generic(token):
            generic.append(token)
            continue
        for run in CJK_RUN_RE.findall(token):
            if not run:
                continue
            if CJK_RE.search(run):
                for gram in cjk_ngrams(run):
                    if gram not in specific:
                        specific.append(gram)
            else:
                run = run.strip()
                if is_generic(run):
                    if run not in generic:
                        generic.append(run)
                elif run and run not in specific:
                    specific.append(run)
    return specific, generic


def format_input(raw):
    return SPLIT_PUNCT_RE.sub(" ", raw.lower())


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
        if specific:
            kws = "、".join(specific[:6])
            if len(specific) > 6:
                kws += " 等"
            print(f"已按核心关键词「{kws}」匹配，仍无结果。\n")
        print("可能原因与建议：")
        print("  1. 关键词未命中：当前用词可能不是核心词，请用更短的 2-4 字词或英文重试")
        print("     （例如 '银行' / '信贷' / '图像分类' / 'image_classification'）")
        print("  2. AI Gallery 市场暂无此能力：可输入 \"有什么skill\" / \"浏览所有\" 查看市场全部技能")
        sys.exit(0)

    print_results(results)


if __name__ == "__main__":
    main()
