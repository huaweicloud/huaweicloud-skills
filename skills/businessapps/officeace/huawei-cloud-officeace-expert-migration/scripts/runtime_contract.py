#!/usr/bin/env python3
"""OfficeAce 运行时契约：迁移必须满足的硬约束，集中实现，供迁移与校验脚本共用。

用途：被 migrate_*.py / verify_install.py / check_runtime.py import 使用；
返回值：各函数见各自 docstring（校验类函数返回 (ok, note) 或抛 ValueError）。

这个模块的每一条都来自实测缺陷，不是「风格偏好」：

  1. `detect_runtime_profile()` —— 专家卡/variant 里的 providerProfileId + defaultModel
     必须是本机 model.json 里真实存在的组合。旧版写死 `modelarts-shared / glm-5`，
     这两个值在本机不存在，专家一被召唤就鉴权失败（表现为「主理人出错」）。
  2. `persona_body()` / `role_line()` —— personality 必须是 agents/*.md 的**完整正文**。
     旧版把团队简介或一句话塞进 personality，四个成员人设退化成同一句话，分工消失。
  3. `bind_skills()` —— 成员只挂自己用得到的技能。旧版 `skills = [自己] + 包级全部技能`，
     每个成员都挂满全队的技能，越界执行别人的活。
  4. `absolutize_scripts()` —— SKILL.md 里的脚本引用必须写成绝对路径。团队会话的 cwd 是
     team-workspace，其中 `skills/` 是空目录，`python scripts/x.py` 必然找不到文件；
     模型于是自己重写算法，导致口径漂移（实测成本 803,520 vs 应为 836,294.40）。
  5. `team_scalars()` / `roster_entry()` —— 队级标量与 roster 运行态字段必须齐全，
     缺字段时 OfficeAce 回退默认值或解析不到主理人。
"""

from __future__ import annotations

import collections
import json
import os
import re
from pathlib import Path

# 队级标量：agentteam-preset.json 的 TEAM_SPEC_DEFAULTS，显式写死避免回退歧义
TEAM_SCALARS = {
    "lifecycle": "persistent",
    "dispatchMode": "autonomous",
    "spawnMode": "inprocess",
    "enableSwarmflow": False,
    "enablePermissions": False,
    "maxIterations": 200,
    "completionTimeout": 600,
}

# model.json 不可用时的最后兜底（仅在确实读不到本机配置时使用）
FALLBACK_PROFILE = "huawei-maas"
FALLBACK_MODEL = "deepseek-v4.1-flash"

# 旧版写死、实测必然鉴权失败的值：任何写入前都要拒绝
KNOWN_BAD_PROFILES = {"modelarts-shared", "xxxxxxxx", ""}
KNOWN_BAD_MODELS = {"glm-5", ""}

RUNTIME_BANNER = "> **OfficeAce 运行约定（必须遵守）**"

RUNTIME_BANNER_BODY = """{banner}
>
> 1. 你的工作目录**不在**技能目录下（团队会话在 `team-workspace`，那里没有 `scripts/`），
>    因此命令一律用绝对路径，不要写 `scripts/xxx.py`。
> 2. 关键数字**必须来自脚本输出**（优先 `--json`）。脚本能算的不自己重算；
>    脚本没给的再按判据推导，并在结论里注明「推导」。
> 3. **不要自行实现或改写脚本逻辑**。脚本报错先修输入、再上报，不要另写一份计算器替代。
> 4. 引用脚本时只使用本文档给出的完整路径；路径含空格时用双引号包住。
"""


# ---------------------------------------------------------------- 基础读写


def _read_json(p: Path | str, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def model_catalog(home: Path) -> dict[str, list[str]]:
    """本机可用模型：{providerProfileId: [modelId, ...]}，来自 ~/.office-claw/model.json。"""
    raw = _read_json(home / "model.json", {}) or {}
    out: dict[str, list[str]] = {}
    if not isinstance(raw, dict):
        return out
    for profile, models in raw.items():
        if not isinstance(models, list):
            continue
        ids = []
        for m in models:
            mid = m.get("id") if isinstance(m, dict) else m
            if isinstance(mid, str) and mid:
                ids.append(mid)
        if ids:
            out[str(profile)] = ids
    return out


def active_user_dir(home: Path) -> Path | None:
    """活跃用户目录：connector-owner.local.json 的 ownerUserId 是唯一权威标识。"""
    owner = _read_json(home / "connector-owner.local.json", {}) or {}
    uid = owner.get("ownerUserId") if isinstance(owner, dict) else None
    if uid:
        cand = home / "users" / str(uid).replace(":", "%3A")
        if cand.is_dir():
            return cand
    users = home / "users"
    if not users.is_dir():
        return None
    dirs = [p for p in users.iterdir() if p.is_dir() and (p / "user-experts.json").is_file()]
    return max(dirs, key=lambda p: p.stat().st_mtime) if dirs else None


def user_experts_path(home: Path) -> Path | None:
    act = active_user_dir(home)
    if act and (act / "user-experts.json").is_file():
        return act / "user-experts.json"
    users = home / "users"
    if not users.is_dir():
        return None
    cands = [p for p in users.glob("*/user-experts.json") if ".bak" not in p.name]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def detect_runtime_profile(home: Path) -> tuple[str, str]:
    """挑一组**本机真实可用**的 (providerProfileId, defaultModel)。

    优先级：
      1. 已迁移专家（user-experts 里 agent_created=true）当前在用的合法组合 —— 重跑不改变
         既有行为，避免已验收的专家因为重跑换了模型而结果漂移；
      2. 本机存量专家里出现次数最多的合法组合 —— 新机器上跟随平台预置配置；
      3. huawei-maas / deepseek-v4.1-flash（若 model.json 里有）；
      4. model.json 里的第一组。
    绝不返回 modelarts-shared / glm-5 这类本机不存在的占位值。
    """
    catalog = model_catalog(home)
    if not catalog:
        return FALLBACK_PROFILE, FALLBACK_MODEL

    def valid(p, m) -> bool:
        return isinstance(p, str) and isinstance(m, str) and m in catalog.get(p, [])

    ue = user_experts_path(home)
    entries = (_read_json(ue, {}) or {}).get("experts") or [] if ue else []

    migrated = collections.Counter(
        (e.get("providerProfileId"), e.get("defaultModel"))
        for e in entries
        if isinstance(e, dict) and e.get("agent_created") and valid(e.get("providerProfileId"), e.get("defaultModel"))
    )
    if migrated:
        return migrated.most_common(1)[0][0]

    # 首选实测跑通过组合；本机没有该模型时再跟随存量专家的多数配置
    if valid(FALLBACK_PROFILE, FALLBACK_MODEL):
        return FALLBACK_PROFILE, FALLBACK_MODEL

    existing = collections.Counter(
        (e.get("providerProfileId"), e.get("defaultModel"))
        for e in entries
        if isinstance(e, dict) and valid(e.get("providerProfileId"), e.get("defaultModel"))
    )
    if existing:
        return existing.most_common(1)[0][0]

    profile = next(iter(catalog))
    return profile, catalog[profile][0]



# ---------------------------------------------------------------- 人设解析


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    return text[end + 4 :].lstrip("\n") if end != -1 else text


def normalize_frontmatter_fence(text: str) -> str:
    """源包脏格式兜底：frontmatter 围栏被写成 `\\---`（首行多反斜杠、尾随空格）时归一化为 `---`。

    实测案例：3d-modeling 的 skills/3d-modeling-kb/SKILL.md 首尾围栏都是 `\\---`，
    应用侧解析不出技能 name/description，迁移后技能等同裸文件。
    只处理最前面的一对围栏，正文里其他横线不动。
    """
    lines = text.splitlines()
    fixed, seen_open = [], False
    for ln in lines:
        if not seen_open and re.fullmatch(r"\\-{3,}\s*", ln.strip()):
            fixed.append("---")
            seen_open = True
            continue
        if seen_open and re.fullmatch(r"\\-{3,}\s*", ln.strip()):
            fixed.append("---")
            seen_open = False  # 闭合后不再改写
            continue
        fixed.append(ln)
    out = "\n".join(fixed)
    return out + ("\n" if text.endswith("\n") and not out.endswith("\n") else "")


def strip_runtime_banner(text: str) -> str:
    """去掉迁移工具自己加的运行约定块（它是给模型的元指令，不属于人设正文）。"""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if lines[i].strip().startswith(RUNTIME_BANNER[:12]):
            i += 1
            while i < len(lines) and (lines[i].startswith(">") or not lines[i].strip()):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def persona_body(agent_text: str) -> str:
    """专家人设正文：去掉 frontmatter 与一级标题，保留全部小节。

    personality 只有拿到完整正文，模型才知道自己的判据、输出格式与边界；
    只给一句 roleDescription 时，成员会退化成「随便答」。
    """
    body = strip_frontmatter(agent_text or "")
    lines = [ln for ln in body.splitlines() if not ln.startswith("# ")]
    return "\n".join(lines).strip()


def first_sentence(text: str, limit: int = 60) -> str:
    """取正文第一句，作为 roleDescription 的补充说明（不引入英文触发词）。"""
    body = persona_body(text)
    for ln in body.splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", ">", "|", "-", "*", "```")):
            continue
        m = re.split(r"(?<=[。！？.!?])", s, maxsplit=1)
        out = m[0].strip()
        if out:
            return out[:limit] + ("…" if len(out) > limit else "")
    return ""


def role_line(profession: str, agent_text: str, fallback: str = "", limit: int = 60) -> str:
    """一句话角色说明：`职业。第一句正文`，读起来像 OfficeAce 预置专家的描述。

    roleDescription 会直接渲染在专家卡与 roster 上，markdown 记号必须去掉。
    """
    def clean(s: str) -> str:
        s = re.sub(r"[*_`>]+", "", s or "")
        return re.sub(r"\s+", " ", s).strip().rstrip("。")

    head = clean(profession)
    tail = clean(first_sentence(agent_text, limit)) if agent_text else ""
    if head and tail and tail not in head:
        return f"{head}。{tail}"
    return head or tail or clean(fallback)


# ---------------------------------------------------------------- 技能绑定


def package_skills(pkg: Path) -> list[str]:
    d = pkg / "skills"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def pkg_references(pkg: Path) -> Path | None:
    """包级静态知识库目录（WorkBuddy「提示词+静态知识型」的 references/）。

    它不属于任何技能，但人设正文按 `references/xxx.md` 引用它；
    迁移时不带走的话，运行时按相对路径必然查不到（实测类型②缺陷）。
    """
    d = Path(pkg) / "references"
    if d.is_dir() and any(f.is_file() for f in d.rglob("*")):
        return d
    return None


def bind_skills(
    own: str,
    agent_text: str,
    available: list[str],
    is_leader: bool = False,
) -> tuple[list[str], str]:
    """决定一个角色该挂哪些技能。返回 (技能名列表, 判定依据)。

    规则（按优先级）：
      1. agent.md frontmatter 显式 `skills: [...]` → 只挂这些；
      2. 主理人/编排角色 → 只挂自己的人设技能（编排靠派活，不自己跑成员脚本）；
      3. 正文里点名了自己的包级技能 → 只挂被点名的；
      4. 都没命中 → 挂全部包级技能，并标注「需人工确认分工」。
    """
    explicit = parse_skills_frontmatter(agent_text)
    if explicit:
        kept = [s for s in explicit if s in available]
        if kept:
            return _dedup([own] + kept), "frontmatter"
    if is_leader:
        return [own], "leader-only"
    hits = [s for s in available if re.search(r"(?<![\w-])" + re.escape(s) + r"(?![\w-])", agent_text or "")]
    if hits:
        return _dedup([own] + hits), "body-mention"
    if not available:
        return [own], "own-only"
    return _dedup([own] + available), "fallback-all"


def parse_skills_frontmatter(agent_text: str) -> list[str]:
    if not agent_text or not agent_text.startswith("---"):
        return []
    end = agent_text.find("\n---", 3)
    if end == -1:
        return []
    fm = agent_text[3:end]
    block = re.search(r"^skills:\s*\[([^\]]*)\]\s*$", fm, re.M)
    if block:
        return [s.strip().strip("\"'") for s in block.group(1).split(",") if s.strip()]
    items = re.findall(r"^\s*-\s*([\w./-]+)\s*$", fm, re.M)
    return [s.strip() for s in items if s.strip()]


def _dedup(seq: list[str]) -> list[str]:
    out: list[str] = []
    for s in seq:
        if s and s not in out:
            out.append(s)
    return out


# ---------------------------------------------------------------- 脚本路径


def skill_scripts(skill_dir: Path) -> list[Path]:
    d = skill_dir / "scripts"
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*") if p.is_file() and p.suffix in (".py", ".js", ".mjs", ".sh"))


# SKILL.md 里对随包资源的引用：`references/x.md`、`scripts/y.py`、`assets/z.png`。
# 允许中文文件名（gaokao 那类 assets/T1_专业初筛表_模板.md）；\w 已含中日韩字符。
RESOURCE_REF_RE = re.compile(
    r"(?<![\w/.\-])"
    r"((?:references|scripts|assets|templates)/[\w./\-]*"
    r"\.(?:md|py|js|mjs|sh|json|ya?ml|csv|txt|png|jpe?g|svg|webp))"
)
# 文档里的示例占位符，不是真引用：scripts/xxx.py、scripts/{name}.py、references/x.md
_PLACEHOLDER_TOKENS = ("xxx", "yyy", "zzz", "your", "...", "<", ">", "{", "}", "*",
                       "name.py", "name.md", "/x.py", "/x.md", "/foo", "/bar")


def resource_refs(text: str) -> list[str]:
    """从 SKILL.md 正文里提取随包资源的相对引用路径（去重、去占位符）。

    参数：text —— SKILL.md 全文；返回值：形如 ['references/a.md', 'scripts/b.py'] 的列表。
    为什么存在：旧版验收只查 `python scripts/x.py` 这种**调用**形式，漏掉「读某份知识库」
    这类**引用**。1.7.3 实测中技能资源整包丢失（10 个文件只剩 1 个 SKILL.md），
    9 处引用全部指空，静态验收却依然报「通过」——这条检查就是补那个盲区。
    """
    out: list[str] = []
    for m in RESOURCE_REF_RE.finditer(text):
        rel = m.group(1).rstrip(".,);:：，。")
        low = rel.lower()
        if any(tok in low for tok in _PLACEHOLDER_TOKENS):
            continue
        out.append(rel)
    return _dedup(out)


def missing_resource_refs(skill_dir: Path) -> list[str]:
    """列出该技能 SKILL.md 引用但磁盘上不存在的资源文件。

    参数：skill_dir —— 已安装的技能目录；返回值：缺失的相对路径列表（空 = 完整）。
    """
    md = Path(skill_dir) / "SKILL.md"
    if not md.is_file():
        return []
    text = md.read_text(encoding="utf-8", errors="replace")
    return [rel for rel in resource_refs(text) if not (Path(skill_dir) / rel).is_file()]



def absolutize_scripts(skill_dir: Path, runtime_dir: Path | None = None,
                       search_root: Path | None = None) -> int:
    """把 SKILL.md 里的相对脚本引用改成绝对路径，并补一段运行约定。

    `runtime_dir` 指定这份技能**最终**所在的目录（staging 阶段与安装目录不同时用），
    写入的路径必须指向运行时真实存在的位置，否则改了等于没改。
    `search_root` 用于跨技能解析：人设技能里常写「调用 bid-pricing 的 scripts/x.py」，
    自己的目录下并没有 scripts/，需要在全部技能里按文件名唯一匹配。
    只改 `python scripts/x.py` 这类可判定的调用，正文其余内容一字不动。
    返回改写处数（0 表示无需改动）。
    """
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return 0
    scripts = skill_scripts(skill_dir)
    text = md.read_text(encoding="utf-8", errors="replace")
    original = text
    changed = 0
    final_root = runtime_dir or skill_dir

    by_rel = {str(p.relative_to(skill_dir)).replace("\\", "/"): p for p in scripts}
    by_rel.update({p.name: p for p in scripts})

    def resolve(rel: str) -> Path | None:
        hit = by_rel.get(rel) or next((v for k, v in by_rel.items() if k.endswith(rel)), None)
        if hit is not None:
            return final_root / hit.relative_to(skill_dir)
        if search_root and search_root.is_dir():
            name = Path(rel).name
            cands = [p for p in search_root.glob(f"*/scripts/{name}") if p.is_file()]
            if len(cands) == 1:
                return cands[0]
        return None

    def repl(m: re.Match) -> str:
        nonlocal changed
        rel = m.group(2)
        while rel.startswith("./"):
            rel = rel[2:]
        target = resolve(rel)
        if target is None:
            return m.group(0)
        changed += 1
        return f'{m.group(1)}"{target}"'

    text = re.sub(
        r'(python(?:3)?\s+["\']?)((?:\./)?scripts/[A-Za-z0-9_./-]+\.(?:py|js|mjs|sh))["\']?',
        repl,
        text,
    )

    if RUNTIME_BANNER not in text and (scripts or changed):
        fm_end = 0
        if text.startswith("---"):
            i = text.find("\n---", 3)
            if i != -1:
                fm_end = text.find("\n", i + 4) + 1
        banner = RUNTIME_BANNER_BODY.format(banner=RUNTIME_BANNER)
        text = text[:fm_end] + ("\n" if fm_end else "") + banner + "\n" + text[fm_end:]

    if text != original:
        md.write_text(text, encoding="utf-8")
    return changed


def absolutize_migrated(home: Path, skill_names: list[str]) -> int:
    """安装完成后统一改写：此时全部技能都已落盘，跨技能引用可以按文件名唯一解析。"""
    total = 0
    root = home / "skills"
    for name in dict.fromkeys(skill_names):
        d = root / name
        if (d / "SKILL.md").is_file():
            total += absolutize_scripts(d, search_root=root)
    return total


def execution_rules(skill_names: list[str], home: Path, alt_root: Path | None = None) -> str:
    """把「先跑脚本」的执行纪律写进人设——模型对人设的服从度高于技能文档。

    `alt_root` 用于 staging 阶段：脚本还没落到 home/skills，但写进人设的必须是
    home 下的**最终**路径，所以从 alt_root 探文件、按 home 拼路径。
    """
    lines: list[str] = []
    for name in dict.fromkeys(skill_names):
        final_dir = home / "skills" / name
        probe = final_dir
        if not (probe / "scripts").is_dir() and alt_root and (alt_root / name / "scripts").is_dir():
            probe = alt_root / name
        for script in skill_scripts(probe):
            lines.append(
                f"- `{name}`：`python \"{final_dir / script.relative_to(probe)}\"`（参数见该技能 SKILL.md）"
            )
    if not lines:
        return ""
    return (
        "\n\n## OfficeAce 执行硬规则\n\n"
        "- 你的工作目录**不在**技能目录下（团队会话在 `team-workspace`，其中没有 `scripts/`）。"
        "调用脚本一律用绝对路径，不要写 `scripts/xxx.py`。\n"
        "- 计算类任务**先跑脚本**。关键数字只能来自脚本输出（优先 `--json`）；"
        "脚本没给的再按判据推导，并在结论里注明「推导」。\n"
        "- **不要自行实现或改写脚本逻辑**替代脚本；脚本报错先修输入、再上报。\n"
        "- 可用脚本入口：\n"
        + "\n".join("  " + ln for ln in lines)
        + "\n"
    )


# ---------------------------------------------------------------- 注册结构


def roster_entry(expert_id: str, evaluation: str, profile: str, model: str, is_lead: bool) -> dict:
    """roster 运行态条目：family/roles/lead/available + 运行配置。

    缺 provider 三字段时，运行时会拿不到模型配置，召唤直接失败。
    """
    return {
        "family": expert_id,
        "roles": ["assistant"],
        "lead": bool(is_lead),
        "available": True,
        "evaluation": evaluation,
        "provider": "relayclaw",
        "providerProfileId": profile,
        "defaultModel": model,
    }


def breed_variant(expert_id: str, skills: list[str], personality: str, profile: str, model: str) -> dict:
    """breed 的默认变体。`provider` 必须是 relayclaw，否则专家会从 /api/agents 整批消失。"""
    return {
        "id": f"{expert_id}-default",
        "skills": list(skills),
        "personality": personality,
        "cli": {"command": "vendor/jiuwenclaw.exe", "outputFormat": "json"},
        "mcpSupport": False,
        "accountRef": profile,
        "providerProfileId": profile,
        "strengths": [],
        "defaultModel": model,
        "provider": "relayclaw",
    }


def user_experts_entry(
    expert_id: str,
    display: str,
    avatar: str,
    category: str,
    role_description: str,
    personality: str,
    skills: list[str],
    profile: str,
    model: str,
    visibility: str = "public",
) -> dict:
    """users/<uid>/user-experts.json 条目 —— /api/experts 的唯一数据源。

    团队主理人与成员都必须在这里登记：OfficeAce 的专家目录以本文件为准，
    只写 user-teams.json 时团队运行时解析不到主理人（实测报「主理人出错」）。
    """
    return {
        "expertId": expert_id,
        "displayName": display,
        "nickname": display,
        "avatar": avatar,
        "category": category,
        "mentionPatterns": [f"@{display}"],
        "roleDescription": role_description,
        "personality": personality,
        "strengths": [],
        "skills": list(skills),
        "visibility": visibility,
        "defaultModel": model,
        "providerProfileId": profile,
        "agent_created": True,
    }


def team_scalars() -> dict:
    return dict(TEAM_SCALARS)


