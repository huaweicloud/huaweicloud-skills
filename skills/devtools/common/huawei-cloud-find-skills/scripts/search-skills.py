#!/usr/bin/env python3
"""Search Huawei Cloud agent skills by keyword/category.

Only the top-3 (score-descending) search results are reported to the
install-count API (exposure impression, fire-and-forget, non-blocking).
Set SKILL_QUALITY_REPORT=0 to disable this reporting.
This script has no other telemetry and no external CLI dependency.

Index loading uses dual-source fallback: GitCode API v5 (primary) → Gitee raw
(backup). On GitCode 429 (Too Many Requests) or network failure, the script
automatically switches to the Gitee raw source, which has an independent IP
and WAF, unaffected by GitCode rate limits. A local cache (TTL 1h) avoids
repeated network calls within the same session.
"""

import argparse
import base64
import binascii
import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


# ---------------------------------------------------------------------------
# Index source configuration — dual-source with automatic failover
# ---------------------------------------------------------------------------

# 索引分支可通过环境变量注入（默认指向当前生产使用的 test-for-index 分支，
# 由索引仓库维护方发布正式数据后切换），避免把分支名硬编码散落在各处。
INDEX_BRANCH = os.environ.get("FIND_SKILLS_INDEX_BRANCH", "test-for-index")

# GitCode API v5 (primary) — returns base64-encoded JSON via contents API
GITCODE_BASE = "https://gitcode.com/api/v5/repos/developer-skill/skills-group-contribution/contents/skills-index"

# Gitee API v5 contents (backup) — independent IP/WAF, unaffected by GitCode
# rate limits. Deliberately uses the contents API instead of the raw path:
# Gitee content review blocks the raw URL for index.json (HTTP 451), while the
# API endpoint returns 200 with a GitCode-compatible base64 envelope, so the
# same decoding branch handles both sources. Optional GITEE_TOKEN env var adds
# an access_token query param to raise anonymous rate limits (default: off).
GITEE_BASE = "https://gitee.com/api/v5/repos/csimon666/skills-group-contribution/contents/skills-index"

SOURCES = [
    {
        "name": "gitcode",
        "is_api": True,  # GitCode contents API returns base64-encoded content
    },
    {
        "name": "gitee",
        "is_api": True,  # Gitee contents API returns the same base64 envelope
    },
]

HTTP_TIMEOUT = 15
MAX_RETRIES = 3

# Local cache — avoids repeated network calls within TTL window
CACHE_DIR = os.path.expanduser("~/.cache/huawei-cloud-find-skills")
CACHE_TTL = int(os.environ.get("FIND_SKILLS_CACHE_TTL", "3600"))  # default 1h

# Install-count API (same endpoint as Step 3 install counting). Used to report
# every search-result skill name as an exposure impression - fire-and-forget,
# never blocks or fails the search.
INSTALL_COUNT_URL = "https://skills-dataset.developer.huaweicloud.com/rest/developer/servlet/hdskillservice/v1/obs/findcounts/increment"
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


# ---------------------------------------------------------------------------
# Network fetch with 429 retry + exponential backoff
# ---------------------------------------------------------------------------

def _fetch_from_network(url, label, is_api):
    """Fetch JSON from a single URL with 429 retry.

    Returns (parsed_data, retry_after_remaining) or raises on non-429 errors.
    On exhausted 429 retries, returns (None, 0) so caller can fall back.
    """
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers={"User-Agent": "huawei-cloud-find-skills/1.0"})
            with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            if is_api and isinstance(parsed, dict) and parsed.get("encoding") == "base64" and "content" in parsed:
                decoded = base64.b64decode(parsed["content"]).decode("utf-8")
                return json.loads(decoded), 0
            return parsed, 0
        except HTTPError as e:
            if e.code == 429:
                # Respect Retry-After header if present
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = min(int(retry_after), 10)
                    except ValueError:
                        wait = 2 ** attempt
                else:
                    wait = 2 ** attempt
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)
                    continue
                # Exhausted retries for this source — return None to trigger fallback
                return None, 0
            raise RuntimeError(f"N02: Failed to fetch {label}: {e}") from e
        except (URLError, OSError, ValueError, UnicodeDecodeError, binascii.Error) as e:
            raise RuntimeError(f"N02: Failed to fetch {label}: {e}") from e
    return None, 0


# ---------------------------------------------------------------------------
# Local cache
# ---------------------------------------------------------------------------

def _cache_path(key):
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{h}.json")


def _cache_get(key):
    path = _cache_path(key)
    if not os.path.exists(path):
        return None
    age = time.time() - os.path.getmtime(path)
    if age > CACHE_TTL:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _cache_put(key, data):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except (OSError, ValueError):
        pass  # cache write failure is non-fatal


# ---------------------------------------------------------------------------
# Dual-source loader: GitCode → GitHub → cache
# ---------------------------------------------------------------------------

def load_json_dual_source(filename, label):
    """Load a JSON index file with dual-source fallback and local cache.

    Tries each source in order (GitCode first, GitHub second). On 429 or
    network error, falls back to the next source. Results are cached locally.
    Returns (data, source_name) or raises if all sources fail.
    """
    cache_key = f"{INDEX_BRANCH}:{filename}"

    # 1. Try cache
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached, "cache"

    # 2. Try each network source
    errors = []
    for source in SOURCES:
        sname = source["name"]
        if sname == "gitcode":
            url = f"{GITCODE_BASE}/{filename}?ref={INDEX_BRANCH}"
        else:
            # Gitee contents API: same ?ref= branch injection as GitCode
            url = f"{GITEE_BASE}/{filename}?ref={INDEX_BRANCH}"
            token = os.environ.get("GITEE_TOKEN")
            if token:
                url += f"&access_token={token}"

        try:
            data, _ = _fetch_from_network(url, f"{label} ({sname})", source["is_api"])
            if data is not None:
                _cache_put(cache_key, data)
                return data, sname
            # 429 exhausted — try next source
            errors.append(f"{sname}: 429 after retries")
        except RuntimeError as e:
            errors.append(f"{sname}: {e}")
            continue  # try next source

    raise RuntimeError(f"N02: Failed to fetch {label} from all sources ({', '.join(errors)})")


def load_index():
    data, _ = load_json_dual_source("index.json", "index.json")
    return data


def load_cn_en_map():
    data, _ = load_json_dual_source("cn-en-map.json", "cn-en-map.json")
    return data


# ---------------------------------------------------------------------------
# Search logic (unchanged)
# ---------------------------------------------------------------------------

def is_generic(kw):
    # 泛词判定用"整词语义"而非子串包含: 复合技能名(如 huawei-cloud-computing-query)
    # 含 'huawei' 子串但语义是具体技能名, 整词判泛会使 specific 为空,
    # 触发 1-3 分兜底把全部技能混入结果(166 项污染)。
    # 仅当去掉泛词后剩余为空、或剩余本身也是泛词(如 '华为云技能')时才判泛。
    k = kw.lower().strip()
    if k in GENERIC_KEYWORDS:
        return True
    for g in ("华为云", "huawei"):
        if g in k:
            remainder = k.replace(g, "").strip("-_ ")
            if not remainder or remainder in GENERIC_KEYWORDS:
                return True
    return False


_CJK_LATIN_BOUNDARY = re.compile(
    r'([\u4e00-\u9fff\u3400-\u4dbf])([A-Za-z0-9])'
    r'|'
    r'([A-Za-z0-9])([\u4e00-\u9fff\u3400-\u4dbf])'
)


def split_cjk_latin(text):
    prev = None
    cur = text
    while prev != cur:
        prev = cur
        cur = _CJK_LATIN_BOUNDARY.sub(
            lambda m: f"{m.group(1) or m.group(3)} {m.group(2) or m.group(4)}", cur
        )
    return cur


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


# cn-en-map 的 value 是服务类目, 但部分 CN key 是意图/营销/教程类复合词
# (如 '代金券'、'下单'、'买一台' 的 value 也可能命中服务名)。反向映射(EN→CN)
# 把它们全部拉入扩展词后, ECS 一次检索可扩出 56 词含购买意图词,
# 代金券技能凭长 triggers 列表刷到 276 分排第 1。反向扩展仅接受
# "纯服务同义词"(如 弹性云服务器/云服务器), 意图词一律丢弃。
INTENT_KEYWORDS = (
    "代金券", "优惠券", "优惠", "下单", "省钱", "续费", "购买", "买一台", "买",
    "领取", "领券", "折扣", "活动", "便宜", "价格", "免费", "收费", "计费",
    "教程", "攻略", "是什么", "怎么", "如何", "推荐", "介绍", "新手", "入门",
    "案例", "实战", "最佳实践", "指南", "手册", "文档", "汇总", "大全",
    # QA 补充: 上游持续出现的营销/意图脏词
    "选购", "抵扣", "抵", "成长中心", "划算", "满减", "现金券", "兑换",
    "秒杀", "拼团", "返现", "红包", "抽奖", "福利", "特权", "值得",
)
# 疑问/口语结构词素: 真服务同义词(弹性云服务器/云服务器)不含疑问结构,
# 口语短语(够不够抵/能抵多少/哪个划算)由结构规则拦截, 不依赖黑名单穷举。
QUESTION_MORPHEMES = (
    "多少", "几", "吗", "呢", "什么", "怎么", "如何", "是否", "能否",
    "能不能", "够不够", "值不值", "哪个", "哪些", "为什么", "为啥", "啥",
)
MAX_SYNONYM_KEY_LEN = 8


def is_clean_synonym_key(k):
    if not is_clean_map_key(k):
        return False
    if len(k) > MAX_SYNONYM_KEY_LEN:
        return False
    if any(ch.isspace() for ch in k) or any(ch.isdigit() for ch in k):
        return False
    if any(w in k for w in QUESTION_MORPHEMES):
        return False
    return not any(w in k for w in INTENT_KEYWORDS)


def expand_keywords(raw_keyword, cn_en_map):
    if not raw_keyword:
        return [], []
    parts = [p for p in split_cjk_latin(raw_keyword).replace(",", " ").replace(";", " ").split() if p]
    expanded = list(parts)
    for p in parts:
        p_lower = p.lower()
        if p in cn_en_map and is_clean_map_key(p):
            expanded.append(cn_en_map[p])
        for cn, en in cn_en_map.items():
            if en == p_lower and is_clean_synonym_key(cn):
                expanded.append(cn)
    all_kws = sorted(set(expanded))
    specific = [kw for kw in all_kws if not is_generic(kw)]
    generic = [kw for kw in all_kws if is_generic(kw)]
    return specific, generic


# 连续中文片段。复合词拆分词典取自技能语料(triggers/name)的中文子串,
# 使连写复合词在整词未命中时可拆为子词联合搜索 (issue #1004)。
_CJK_RUN = r"[一-鿿]+"


def build_cjk_vocab(skills):
    """从技能 triggers/name 提取所有长度>=2 的连续中文子串, 作为复合词拆分词典。"""
    vocab = set()

    def _add(text):
        for seg in re.findall(_CJK_RUN, text or ""):
            n = len(seg)
            for i in range(n):
                for j in range(i + 2, n + 1):
                    vocab.add(seg[i:j])

    for s in skills:
        for t in s["triggers"]:
            _add(t)
        _add(s["name"])
    return vocab


def split_cjk_compound(word, vocab):
    """纯中文复合词按词典正向最长匹配拆分; 仅当能完整覆盖且拆出>=2 个子词时返回子词列表,
    否则返回 [](回退整词)。短词/单词/无法覆盖的复合词(如 对象存储)不拆。"""
    if not re.fullmatch(_CJK_RUN, word or "") or len(word) < 4:
        return []
    n = len(word)
    parts = []
    i = 0
    while i < n:
        hit = None
        for j in range(n, i + 1, -1):
            if word[i:j] in vocab:
                hit = word[i:j]
                break
        if not hit:
            return []
        parts.append(hit)
        i += len(hit)
    return parts if len(parts) >= 2 else []


def extract_skill_fields(skill):
    """批量提取 skill 字段(一次性字典访问, 后续循环内只做本地匹配)。

    除索引的单一 `service` 外, 一并保留 `services` 全量服务清单与 `type`
    能力类型(index 已提供), 供结果展示与覆盖分组使用。
    """
    name = skill.get("name", "")
    category = skill.get("category", "")
    service = skill.get("service", "")
    raw_services = skill.get("services") or []
    services = []
    for svc in raw_services:
        if svc and svc not in services:
            services.append(svc)
    if not services and service:
        services = [service]
    if not service and services:
        service = services[0]
    description = skill.get("description", "")
    raw_triggers = skill.get("triggers") or []
    triggers = [t for t in raw_triggers if t]
    return {
        "name": name,
        "category": category,
        "service": service,
        "services": services,
        "type": (skill.get("type") or "").lower(),
        "description": description,
        "triggers": triggers,
    }


def category_matches(category, wanted):
    """类目过滤: 一级类目按前缀匹配(命中其全部子类目), 二级及更深路径精确匹配。

    索引中的 category 均为 "一级/二级" 形式; 用户传单级类目通常是「按大类浏览」,
    传完整路径则要求精确命中; 前缀比较以 "/" 结尾, 避免一级类目误匹配同名前缀的其它类目。
    """
    if not wanted:
        return True
    return category == wanted or category.startswith(wanted + "/")


def build_category_catalog(skills):
    """从 index.json 聚合成 {一级类目: {"count": N, "subs": {二级: N}}}。"""
    catalog = {}
    for skill in skills:
        category = skill.get("category") or ""
        if not category:
            continue
        top, _, sub = category.partition("/")
        entry = catalog.setdefault(top, {"count": 0, "subs": {}})
        entry["count"] += 1
        if sub:
            entry["subs"][sub] = entry["subs"].get(sub, 0) + 1
    return catalog


def format_catalog_lines(catalog):
    """把类目树渲染为可读清单(一级汇总 + 二级明细路径)。"""
    subs_total = sum(len(e["subs"]) for e in catalog.values())
    lines = [f"Available categories ({len(catalog)} top-level / {subs_total} second-level):"]
    for top in sorted(catalog):
        entry = catalog[top]
        lines.append(f"  {top} ({entry['count']} skill(s))")
        if entry["subs"]:
            sub_desc = ", ".join(
                f"{top}/{sub}({n})" for sub, n in sorted(entry["subs"].items())
            )
            lines.append(f"    {sub_desc}")
    return lines


# 技能类型推断: 从 name 识别 查询/管理/演练/营销 四类, 用于意图加权与结果标签。
# experiment 优先判定(shutdown-experiment 同时含 shutdown/experiment);
# marketing 次之(优惠/代金券类技能不应作为服务能力的默认入口)。
TYPE_QUERY_WORDS = ("query", "list", "show", "get", "describe", "只读", "查询")
TYPE_MANAGE_WORDS = ("manage", "lifecycle", "ops", "管理", "运维")
TYPE_EXPERIMENT_WORDS = ("experiment", "chaos", "fault", "演练", "实验")
TYPE_MARKETING_WORDS = ("voucher", "coupon", "discount", "promotion", "rebate", "代金券", "优惠券", "折扣", "返现", "红包")


def infer_skill_type(name):
    n = (name or "").lower()
    if any(w in n for w in TYPE_EXPERIMENT_WORDS):
        return "experiment"
    if any(w in n for w in TYPE_MARKETING_WORDS):
        return "marketing"
    if any(w in n for w in TYPE_QUERY_WORDS):
        return "query"
    if any(w in n for w in TYPE_MANAGE_WORDS):
        return "manage"
    return ""


TYPE_LABELS = {
    "query": "只读查询",
    "manage": "管理",
    "experiment": "演练",
    "marketing": "优惠",
    "general": "通用",
}


def resolve_skill_type(fields):
    """优先使用 index 的 `type` 字段; 缺失时回退到从技能名推断。"""
    stype = (fields.get("type") or "").lower()
    if stype in TYPE_LABELS:
        return stype
    return infer_skill_type(fields["name"])


def format_services(fields):
    """渲染结果行的覆盖服务清单与能力类型。

    单服务技能保持原有 `(category/service)` 形态; 多服务技能追加
    `覆盖: ...` 全量清单与 `[类型]` 标签, 避免覆盖能力被主服务隐藏。
    """
    services = fields.get("services") or []
    stype = resolve_skill_type(fields)
    parts = []
    if len(services) > 1:
        parts.append("覆盖: " + "+".join(svc.upper() for svc in services))
    if stype:
        parts.append(f"[{TYPE_LABELS[stype]}]")
    return "".join(f" {p}" for p in parts)


_NAME_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _name_tokens(name):
    return set(_NAME_TOKEN_RE.findall((name or "").lower()))


def keyword_service_codes(specific_kws, cn_en_map, all_service_codes):
    """把检索关键词映射为云服务代码, 用于识别「仅覆盖该服务」的技能。

    支持三种来源: 关键词本身就是服务代码(如 CCE)、cn-en-map 的中文别名
    (如 弹性云服务器 -> ecs)、以及关键词中的英文 token(如 "CCE 集群")。
    """
    codes = set()
    for kw in specific_kws:
        k = (kw or "").lower().strip()
        if not k:
            continue
        if k in all_service_codes:
            codes.add(k)
            continue
        mapped = cn_en_map.get(kw) or cn_en_map.get(k)
        if mapped and mapped.lower() in all_service_codes:
            codes.add(mapped.lower())
        for tok in _NAME_TOKEN_RE.findall(k):
            if tok in all_service_codes:
                codes.add(tok)
    return codes


def collect_coverage_only(skills, service_codes, category="", scores=None):
    """收集名称未体现、但 services 覆盖了目标服务的技能 (coverage-only)。

    这类技能在主排序中天然处于劣势(名称无产品词), 单独分组列出可避免
    被同产品专项技能掩埋 (issue #1047)。
    """
    rows = []
    for fields in skills:
        if not category_matches(fields["category"], category):
            continue
        services = [s.lower() for s in fields.get("services") or []]
        if not (set(services) & service_codes):
            continue
        if _name_tokens(fields["name"]) & service_codes:
            continue
        rows.append(fields)
    scores = scores or {}
    rows.sort(key=lambda f: (-scores.get(f["name"], 0), len(f.get("services") or []), f["name"]))
    return rows


def detect_user_intent(keyword):
    """从用户查询词识别管理/查询/优惠意图(用于类型加权与豁免)。"""
    k = (keyword or "").lower()
    if not k:
        return ""
    if any(w in k for w in ("管理", "运维", "manage", "创建", "启停", "删除", "变更")):
        return "manage"
    if any(w in k for w in ("优惠", "代金券", "折扣", "券", "省钱", "划算", "voucher", "coupon")):
        return "marketing"
    if any(w in k for w in ("查询", "查看", "查", "列出", "list", "query", "show")):
        return "query"
    return ""


# 意图加权系数: 管理/查询意图时对应类型 ×1.2; 演练类 ×0.6;
# 营销类在用户未主动找优惠时 ×0.3(Issue: 上游脏词无法穷举, 黑名单永远有漏网,
# 营销技能按名字识别整体降权才是根治——用户主动搜"代金券"时豁免不受影响)。
INTENT_BOOST = 1.2
EXPERIMENT_PENALTY = 0.6
MARKETING_PENALTY = 0.3


def score_skill(fields, specific_kws, generic_kws, user_intent="", explain=False):
    if not specific_kws and not generic_kws:
        return (1, [], {}) if explain else (1, [])
    name_l = fields["name"].lower()
    desc_l = fields["description"].lower()
    service_l = fields["service"].lower()
    trig_l = [t.lower() for t in fields["triggers"]]
    total = 0
    matched = []
    detail = {}
    name_hit = service_hit = desc_hit = False
    for kw in specific_kws:
        k = kw.lower()
        s = 0
        areas = []
        if k in name_l:
            s += 10
            areas.append("name+10")
            name_hit = True
        if any(k in t for t in trig_l):
            s += 8
            areas.append("trigger+8")
        if k in desc_l:
            s += 5
            areas.append("desc+5")
            desc_hit = True
        if k in service_l:
            s += 3
            areas.append("service+3")
            service_hit = True
        if s > 0:
            total += s
            matched.append(kw)
            detail[kw] = areas
    for kw in generic_kws:
        k = kw.lower()
        s = 0
        areas = []
        if k in name_l:
            s += 10
            areas.append("name+10")
            name_hit = True
        if any(k in t for t in trig_l):
            s += 4
            areas.append("trigger+4")
        if k in desc_l:
            s += 2
            areas.append("desc+2")
            desc_hit = True
        if k in service_l:
            s += 1
            areas.append("service+1")
            service_hit = True
        if s > 0:
            total += s
            matched.append(kw)
            detail[kw] = areas
    browse_fallback = False
    if not specific_kws and total == 0:
        browse_fallback = True
        total = 1
        if len(desc_l) > 20:
            total += 1
        if trig_l:
            total += 1
    # 主词约束(反刷分): specific 主词仅在长 triggers 列表命中,
    # name/desc/service 全部未命中 → 总分 ×0.5, 压制触发词列表刷分。
    if specific_kws and not name_hit and not desc_hit and not service_hit:
        total *= 0.5
    # 意图类型加权(浏览兜分不参与, 避免兜底 1-3 分被压成 0)
    stype = infer_skill_type(fields["name"])
    if not browse_fallback:
        if stype == "experiment":
            total *= EXPERIMENT_PENALTY
        elif stype == "marketing" and user_intent != "marketing":
            total *= MARKETING_PENALTY
        elif user_intent and stype == user_intent:
            total *= INTENT_BOOST
    total = int(total)
    if explain:
        return total, matched, {"detail": detail, "type": stype}
    return total, matched


def truncate(desc, limit=150):
    if desc and len(desc) > limit:
        return desc[:limit] + "..."
    return desc


def build_result(fields, score, matched):
    """构造统一的结果行, 保留 services/type 供覆盖展示与分组使用。"""
    return {
        "score": score,
        "name": fields["name"],
        "category": fields["category"],
        "service": fields["service"],
        "services": fields["services"],
        "type": fields["type"],
        "description": truncate(fields["description"]),
        "triggers": fields["triggers"][:5],
        "matched": matched,
    }


# ---------------------------------------------------------------------------
# Telemetry: install-count impression (unchanged from master)
# ---------------------------------------------------------------------------

def _post_impression(skill_id):
    """Single-instance POST to the install-count API (best-effort)."""
    body = json.dumps({"skill_id": skill_id}).encode("utf-8")
    req = Request(
        INSTALL_COUNT_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://skills.developer.huaweicloud.com",
            "Referer": "https://skills.developer.huaweicloud.com/",
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
    each skill_id (`skills/<category>/<name>`) is POSTed to the same
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
            if _post_impression("skills/{}/{}".format(r["category"], r["name"])):
                reported["n"] += 1

    threading.Thread(target=_worker, daemon=True).start()
    return reported["n"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, 'reconfigure'):
            _stream.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="Search Huawei Cloud skills")
    parser.add_argument("-k", "--keyword", default="", help="Search keyword(s), space/comma/semicolon separated")
    parser.add_argument("-c", "--category", default="",
                        help="Filter by category: a top-level category (prefix match, covers all its subcategories) "
                             "or an exact two-level path")
    parser.add_argument("-l", "--list-categories", action="store_true",
                        help="List available categories from the index (optionally narrow with -c)")
    parser.add_argument("--explain", action="store_true", help="Show per-keyword score breakdown for each result")
    args = parser.parse_args()

    if not args.keyword and not args.category and not args.list_categories:
        print("Usage: python search-skills.py -k <keyword> [-c <category>]")
        print("       python search-skills.py -c <category>            # exact path or top-level prefix")
        print("       python search-skills.py -l [-c <category>]       # browse available categories")
        print("ERROR: missing keyword and category (U02)", file=sys.stderr)
        return 1

    idx, idx_source = load_json_dual_source("index.json", "index.json")
    raw_skills = idx.get("skills", [])
    skills = [extract_skill_fields(s) for s in raw_skills]
    all_service_codes = set()
    for _skill in skills:
        all_service_codes.update(x.lower() for x in _skill["services"])
    catalog = build_category_catalog(skills)

    if args.list_categories:
        filtered = catalog
        if args.category:
            filtered = {}
            for top, entry in catalog.items():
                if category_matches(top, args.category):
                    filtered[top] = entry
                    continue
                matched_subs = {
                    sub: n for sub, n in entry["subs"].items()
                    if category_matches(f"{top}/{sub}", args.category)
                }
                if matched_subs:
                    filtered[top] = {"count": sum(matched_subs.values()), "subs": matched_subs}
            if not filtered:
                print(f"No category matched '{args.category}'.")
                print()
                print("\n".join(format_catalog_lines(catalog)))
                print()
                print(f"  [data source: index: {idx_source}]")
                return 0
        print("\n".join(format_catalog_lines(filtered)))
        print()
        print(f"  [data source: index: {idx_source}]")
        return 0

    if args.keyword:
        cn_en_map, map_source = load_json_dual_source("cn-en-map.json", "cn-en-map.json")
        specific_kws, generic_kws = expand_keywords(args.keyword, cn_en_map)
    else:
        specific_kws, generic_kws = [], []
        map_source = "n/a"
    has_specific = bool(specific_kws)
    user_intent = detect_user_intent(args.keyword)

    # 精确技能名短路: 关键词(单一 token)与某 skill name 完全一致(忽略大小写)时,
    # 直接只返回该技能, 其余条目不再以 1-3 分兜底混入。
    kw_clean = args.keyword.strip()
    if has_specific and kw_clean and "," not in kw_clean and ";" not in kw_clean and len(kw_clean.split()) == 1:
        kw_lower = kw_clean.lower()
        exact = [s for s in skills if s["name"].strip().lower() == kw_lower]
        if len(exact) == 1:
            skill = exact[0]
            if category_matches(skill["category"], args.category):
                print(f"Found 1 skill (exact name match) for keyword='{args.keyword}':")
                print()
                print(f"  [{skill['category']}/{skill['service']}] {skill['name']}{format_services(skill)}")
                print(f"    {skill['description']}")
                if skill["triggers"]:
                    print(f"    triggers: {', '.join(skill['triggers'][:5])}")
                print()
                print(f"  [data source: index: {idx_source}, map: {map_source}]")
                return 0

    results = []
    explain_info = {}
    cjk_split_note = ""

    for skill in skills:
        category = skill["category"]
        if not category_matches(category, args.category):
            continue
        sc, matched, extra = score_skill(skill, specific_kws, generic_kws, user_intent=user_intent, explain=True)
        if has_specific and sc == 0:
            continue
        results.append(build_result(skill, sc, matched))
        if args.explain:
            explain_info[skill["name"]] = extra

    results.sort(key=lambda r: r["score"], reverse=True)

    if has_specific and len(results) <= 1:
        en_tokens = re.findall(r'[A-Za-z]{2,}', args.keyword)
        if en_tokens:
            retry_kw = " ".join(en_tokens)
            retry_specific, retry_generic = expand_keywords(retry_kw, cn_en_map)
            if retry_specific:
                retry_results = []
                for skill in skills:
                    category = skill["category"]
                    if not category_matches(category, args.category):
                        continue
                    sc, matched = score_skill(skill, retry_specific, retry_generic, user_intent=user_intent)
                    if sc > 0:
                        retry_results.append(build_result(skill, sc, matched))
                if len(retry_results) > 1:
                    retry_results.sort(key=lambda r: r["score"], reverse=True)
                    results = retry_results
                    specific_kws = retry_specific
                    generic_kws = retry_generic

    # 中文复合词回退(issue #1004): 整词未命中(<=1 结果)且关键词为单一连写中文复合词时,
    # 用语料子串词典做最长匹配拆分, 子词联合搜索, 命中更多则采用并标注拆分。
    if has_specific and len(results) <= 1:
        kw_cjk = args.keyword.strip()
        if re.fullmatch(_CJK_RUN, kw_cjk) and len(kw_cjk) >= 4:
            sub_words = split_cjk_compound(kw_cjk, build_cjk_vocab(skills))
            if sub_words:
                retry_specific, retry_generic = expand_keywords(" ".join(sub_words), cn_en_map)
                if retry_specific:
                    retry_results = []
                    for skill in skills:
                        if not category_matches(skill["category"], args.category):
                            continue
                        sc, matched = score_skill(skill, retry_specific, retry_generic, user_intent=user_intent)
                        if sc > 0:
                            retry_results.append(build_result(skill, sc, matched))
                    if len(retry_results) > len(results):
                        retry_results.sort(key=lambda r: r["score"], reverse=True)
                        results = retry_results
                        specific_kws = retry_specific
                        generic_kws = retry_generic
                        cjk_split_note = " + ".join(sub_words)

    impressions = report_search_results_impressions(results)

    if not results:
        print(f"No results for keyword='{args.keyword}' category='{args.category}'")
        print()
        if args.category:
            # 区分「类目存在但关键词无命中」与「类目名写错」, 并给出近似候选;
            # 类目清单由 index.json 聚合去重生成(不再写死具体类目值)。
            all_paths = sorted(
                set(catalog)
                | {f"{top}/{sub}" for top, entry in catalog.items() for sub in entry["subs"]}
            )
            hit_count = sum(1 for s in skills if category_matches(s["category"], args.category))
            if hit_count:
                print(f"Category '{args.category}' exists ({hit_count} skill(s)) but no skill matched "
                      f"keyword='{args.keyword}'.")
                print(f"  Browse it without a keyword: python search-skills.py -c '{args.category}'")
            else:
                print(f"Category '{args.category}' was not found in the index.")
                candidates = difflib.get_close_matches(args.category, all_paths, n=5, cutoff=0.5)
                if not candidates:
                    needle = args.category.lower()
                    candidates = [p for p in all_paths if needle in p.lower()][:5]
                if candidates:
                    print("  Similar available categories:")
                    for cand in candidates:
                        print(f"    {cand} "
                              f"({sum(1 for s in skills if category_matches(s['category'], cand))} skill(s))")
            print()
            print("\n".join(format_catalog_lines(catalog)))
            print()
        else:
            print("Fallback suggestions:")
            print("  1. Try broader or alternative keywords")
            print("  2. Remove category filter")
            print("  3. Switch CN<->EN (e.g., 'obs' <-> 'object storage')")
            print("  4. Browse available categories: python search-skills.py -l")
        print(f"  [data source: index: {idx_source}]")
        return 0

    all_kws = specific_kws + generic_kws
    print(f"Found {len(results)} skill(s) for keyword='{args.keyword}' category='{args.category}':")
    if cjk_split_note:
        print(f"  (复合词拆分: {cjk_split_note})")
    if len(all_kws) > 1 or (len(all_kws) == 1 and all_kws[0] != args.keyword):
        print(f"  (expanded: {', '.join(all_kws)})")
    print()
    for r in results:
        match_info = f" matched: {','.join(r['matched'])}" if r["matched"] else ""
        print(f"  [{r['score']}pts] {r['name']} ({r['category']}/{r['service']}){format_services(r)}{match_info}")
        print(f"    {r['description']}")
        if r["triggers"]:
            print(f"    triggers: {', '.join(r['triggers'])}")
        if args.explain and r["name"] in explain_info:
            info = explain_info[r["name"]]
            print(f"    [explain] type={info['type'] or 'general'} breakdown:")
            for kw, areas in info["detail"].items():
                print(f"      {kw}: {', '.join(areas)}")
            if not info["detail"]:
                print("      (no keyword hit, browse-fallback score)")
        print()

    # 覆盖分组(issue #1047): 名称未体现、但索引 services 覆盖了目标服务的
    # 技能在主排序中天然偏低, 单独分组列出, 避免被同产品专项技能掩埋。
    if has_specific:
        service_codes = keyword_service_codes(specific_kws, cn_en_map, all_service_codes)
        if service_codes:
            scores = {r["name"]: r["score"] for r in results}
            coverage_rows = collect_coverage_only(skills, service_codes, args.category, scores)
            if coverage_rows:
                covered = ",".join(sorted(service_codes))
                print(f"  Other skills covering '{args.keyword}' ({covered}) — 其他覆盖该服务的技能:")
                print()
                for fields in coverage_rows:
                    print(f"    {fields['name']} ({fields['category']}/{fields['service']})"
                          f"{format_services(fields)}")
                    print(f"      {truncate(fields['description'])}")
                print()

    # 同域重叠提示: 同一 category/service 下多个候选能力可能重叠,
    # 提示开发者/智能体先对比 description 再选择, 避免装了再卸载试错。
    svc_groups = {}
    for r in results:
        svc_groups.setdefault((r["category"], r["service"]), []).append(r["name"])
    overlap_lines = [
        f"  {cat}/{svc} ({len(names)}): {', '.join(names[:5])}{'...' if len(names) > 5 else ''}"
        for (cat, svc), names in svc_groups.items() if len(names) >= 2
    ]
    if overlap_lines:
        print("  Overlap hint — multiple candidates under the same service, compare descriptions before installing:")
        for line in overlap_lines:
            print(line)
        print()

    print(f"  [data source: index: {idx_source}, map: {map_source}]")
    return 0


if __name__ == "__main__":
    try:
        rc = main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(rc)
