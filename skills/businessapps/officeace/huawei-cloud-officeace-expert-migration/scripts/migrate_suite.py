#!/usr/bin/env python3
"""把一个千问办公 / 百度搭子格式的专家套件，迁移成 OfficeAce 的「专家卡 + 技能目录」。

用途：千问办公/百度搭子套件 → OfficeAce 专家卡 + 技能目录（默认 dry-run，--install 才写盘）。
参数：--source 源套件目录（必填）；--staging 输出目录；--name / --display-name / --nickname / --category；
      --install 安装；--force 覆盖同名技能；--officeace-home 数据目录；--app-root 应用安装根；--user-catalog 用户目录文件。
返回值：退出码 0=成功，非 0=失败（缺清单、无技能、数据目录不存在等）。

设计原则：
  1. 默认 dry-run：只在 --staging 目录产出，不动 OfficeAce 任何文件。
  2. --install 才写盘，且写前备份、按 name 幂等（重跑不会产生重复专家）。
  3. 不猜内容：源里没有的东西不编，缺项写进 report.md 的「需人工补」。
  4. 技能正文原样保留，只重写 frontmatter 与加一行来源注释——迁移不改行为。

用法：
    # 1) 预演（默认），产物落 staging
    python migrate_suite.py --source <套件目录> --staging ../out/xxx

    # 2) 确认产物无误后安装
    python migrate_suite.py --source <套件目录> --staging ../out/xxx --install

    # 3) 覆盖已存在的同名技能
    python migrate_suite.py --source <套件目录> --install --force

参数（除 source 外均可省略）：
    --name           OfficeAce 内的专家标识（kebab-case），默认取源套件 name
    --display-name   专家显示名（中文），默认取源 displayNameCn / displayName
    --nickname       @提及用的昵称，默认同 display-name
    --category       business / legal / finance / engineering ...，默认 business
    --officeace-home 默认 ~/.office-claw
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_contract as rc  # noqa: E402
import migration_gate as gate  # noqa: E402

# ---------------------------------------------------------------- 基础工具


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.0000000Z")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def sha8(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def slug_from_expert_id(expert_id) -> str:
    """从 expertId 反解专家 slug：`expert-<slug>-<8位hex>` → `<slug>`，解不出返回空串。

    user-experts.json 的条目**没有 name 字段**，只按 name 匹配会全部落空，
    必须靠 expertId 反解，否则改头像会漏掉 UI 专家列表这一处。
    """
    if not isinstance(expert_id, str):
        return ""
    m = re.match(r"^expert-(.+)-[0-9a-f]{6,}$", expert_id)
    return m.group(1) if m else ""


def entry_slug(obj: dict) -> str:
    """从任意注册条目（专家卡 / catalog / breed / user-experts）取专家 slug。"""
    if not isinstance(obj, dict):
        return ""
    name = obj.get("name")
    if isinstance(name, str) and name:
        return name
    return slug_from_expert_id(obj.get("expertId") or obj.get("id") or obj.get("agentId"))


def kebab(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5]+", "-", s.strip().lower())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "expert"


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """返回 (frontmatter dict, body)。没有 frontmatter 时 dict 为空。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = {}
    for line in text[3:end].splitlines():
        line = line.rstrip()
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip().strip('"').strip("'")
    body = text[end + 4 :].lstrip("\n")
    return fm, body


def yaml_escape(s: str) -> str:
    # 单行、无双引号包裹冲突时用双引号；正文描述里常有冒号与中文括号
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- 源格式识别

MANIFESTS = {
    ".qwenwork-plugin/plugin.json": "qwenwork",
    ".qoder-plugin/plugin.json": "qwenwork",
    ".claude-plugin/plugin.json": "dumate",
    ".codebuddy-plugin/plugin.json": "workbuddy",
}


def detect(root: Path) -> tuple[str, Path | None]:
    for rel, plat in MANIFESTS.items():
        p = root / rel
        if p.exists():
            return plat, p
    return "unknown", None


def enumerate_skills(root: Path, manifest: dict) -> list[Path]:
    declared = manifest.get("skills")
    dirs: list[Path] = []
    if isinstance(declared, list) and declared:
        for s in declared:
            p = Path(s) if Path(s).is_absolute() else (root / s)
            if (p / "SKILL.md").exists():
                dirs.append(p)
    if not dirs:
        base = root / "skills"
        if base.is_dir():
            dirs = [d for d in sorted(base.iterdir()) if d.is_dir() and (d / "SKILL.md").exists()]
    seen, out = set(), []
    for d in dirs:
        r = d.resolve()
        if r in seen:
            continue
        seen.add(r)
        out.append(d)
    return out


def load_agent_prompt(root: Path, manifest: dict) -> tuple[str | None, str]:
    """取入口 agent 的 md（百度搭子）或返回 None。"""
    agents = manifest.get("agents") or []
    if agents:
        rel = agents[0].get("prompt")
        if rel:
            p = (root / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
            if p.exists():
                return p.read_text(encoding="utf-8", errors="replace"), str(p)
    return None, ""


# ---------------------------------------------------------------- 语义映射


def pick_text(v) -> str:
    """把清单里的字段取成纯文本。

    千问 / 搭子的清单允许 `displayName: {zh: "...", en: "..."}` 这种多语言对象，
    直接 str() 会把花括号写进专家名与报告，必须按中文优先归一。
    """
    if isinstance(v, dict):
        for k in ("zh", "zh-CN", "zh_CN", "cn", "en", "default"):
            if isinstance(v.get(k), str) and v[k].strip():
                return v[k].strip()
        for x in v.values():
            if isinstance(x, str) and x.strip():
                return x.strip()
        return ""
    return v.strip() if isinstance(v, str) else ""


def zh_description(fm: dict, fallback: str = "") -> str:
    for k in ("description_zh", "descriptionZh", "description", "description_en"):
        txt = pick_text(fm.get(k))
        if txt:
            return txt
    return fallback


def short_role(desc: str, limit: int = 120) -> str:
    d = re.sub(r"\s+", " ", desc).strip()
    if len(d) <= limit:
        return d
    cut = d[:limit]
    for sep in ("。", "；", ";", "，"):
        i = cut.rfind(sep)
        if i > limit * 0.5:
            return cut[: i + 1]
    return cut.rstrip() + "…"


PALETTE = [
    ("#4A6FA5", "#E3ECF7"),
    ("#D4574A", "#FAE0DC"),
    ("#3F8F6B", "#DFF2E8"),
    ("#9B7EBD", "#E8DFF5"),
    ("#E8A317", "#FFF4D6"),
    ("#2E7C8F", "#DCF0F4"),
]


def pick_color(key: str) -> dict:
    i = int(sha8(key), 16) % len(PALETTE)
    p, s = PALETTE[i]
    return {"primary": p, "secondary": s}


def build_persona_skill_text(
    name: str,
    display: str,
    desc: str,
    agent_prompt: str | None,
    skill_slugs: list[str],
    source_label: str,
) -> str:
    """专家主提示词技能。有 agent md 就用它；没有就按元数据合成一份最小可用的。"""
    if agent_prompt:
        fm, body = parse_frontmatter(agent_prompt)
        body = body.strip() or agent_prompt.strip()
        note = ""
        if not body.startswith("#"):
            body = f"# {display}\n\n{body}"
    else:
        body = (
            f"# {display}\n\n"
            f"你现在是「{display}」。当用户的问题命中本专家的适用场景时，以该身份完成用户请求。\n\n"
            f"## 适用场景\n\n{desc}\n\n"
            f"## 工作流\n\n"
            "1. 先用一句话复述用户要交付的东西，确认口径。\n"
            "2. 判断该走哪个技能（见下表），信息不足时只问最关键的 2-3 个问题。\n"
            "3. 按技能内置的骨架与自检清单产出交付物，不跳自检。\n"
            "4. 交付时说明产物位置、覆盖范围与未覆盖事项。\n\n"
            f"## 技能使用指引\n\n"
            + "\n".join(f"- `{s}`" for s in skill_slugs)
            + "\n\n## 原则与边界\n\n"
            "- 不虚构事实：数据、价格、条款、能力一律标注来源；核不实就明说缺口。\n"
            "- 不越权：不代替用户做不可逆操作（签署、下单、付款、对外发送）。\n"
            "- 交付前跑一遍自检清单，不达标不许交付。\n"
        )
        note = "> 本提示词由迁移工具按源套件元数据合成（源套件未提供入口 agent 提示词），建议人工复核后补全。\n\n"

    fm_lines = [
        "---",
        f"name: {name}",
        f"description: {yaml_escape(short_role(desc, 300))}",
        "agent_created: true",
        "---",
        "",
    ]
    tail = f"\n\n<!-- migrated by huawei-cloud-officeace-expert-migration from {source_label} -->\n"
    head = "\n".join(fm_lines) + "\n"
    if not agent_prompt:
        body = body.rstrip() + "\n\n---\n\n" + note.strip() + "\n"
    return head + body.rstrip() + tail


def richest_skill_body(skill_dirs: list[Path]) -> tuple[str, str]:
    """源包没有入口 agent 提示词时（千问/搭子常见），挑正文最长的技能当角色设定底稿。

    这些套件把"怎么干活"全写在技能正文里，正文本身就是最接近人设的东西；
    用元数据拼一段泛泛的话只会得到一个不知道判据的专家。
    """
    best, slug = "", ""
    for d in skill_dirs:
        md = d / "SKILL.md"
        if not md.is_file():
            continue
        try:
            _, body = parse_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            continue
        body = body.strip()
        if len(body) > len(best):
            best, slug = body, d.name
    return best, slug


def rewrite_skill_md(src: Path, slug: str, fallback_desc: str, source_label: str) -> tuple[str, dict]:
    text = src.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(text)
    desc = zh_description(fm, fallback_desc) or fallback_desc
    desc_one_line = re.sub(r"\s+", " ", desc).strip()
    if not body.strip():
        body = text
    if not body.lstrip().startswith("#"):
        body = f"# {fm.get('name_zh') or fm.get('name') or slug}\n\n{body}"
    out = [
        "---",
        f"name: {slug}",
        f"description: {yaml_escape(desc_one_line)}",
        "agent_created: true",
        "---",
        "",
        body.strip(),
        "",
        f"<!-- migrated by huawei-cloud-officeace-expert-migration from {source_label} -->",
        "",
    ]
    meta = {
        "source_name": fm.get("name", ""),
        "source_name_zh": fm.get("name_zh", ""),
        "dropped_keys": sorted(k for k in fm if k not in ("name", "description")),
        "desc_source": "zh" if (fm.get("description_zh") or fm.get("descriptionZh")) else "raw",
    }
    return "\n".join(out), meta


# ---------------------------------------------------------------- 迁移主体


def migrate(args) -> dict:
    src = Path(args.source).resolve()
    plat, mf_path = detect(src)
    if plat == "unknown":
        raise SystemExit(f"错误：{src} 不是可识别的套件（缺 .qwenwork-plugin / .qoder-plugin / .claude-plugin 清单）")
    manifest = read_json(mf_path) if mf_path else {}

    name = kebab(args.name or pick_text(manifest.get("name")) or src.name)
    display = (
        pick_text(args.display_name)
        or pick_text(manifest.get("displayNameCn"))
        or pick_text(manifest.get("displayName"))
        or pick_text(manifest.get("displayNameZh"))
        or name
    )
    nickname = pick_text(args.nickname) or display
    desc = pick_text(manifest.get("descriptionZh")) or pick_text(manifest.get("description"))
    version = manifest.get("version", "1.0.0")
    source_label = f"{plat}/{manifest.get('name', src.name)}@{version}"

    skill_dirs = enumerate_skills(src, manifest)
    if not skill_dirs:
        raise SystemExit("错误：源套件里没有找到任何含 SKILL.md 的技能目录")

    agent_prompt, agent_path = load_agent_prompt(src, manifest)
    slugs = [d.name for d in skill_dirs]

    expert_id = f"expert-{name}-{sha8(name + version)}"
    home = Path(getattr(args, "officeace_home", "~/.office-claw")).expanduser()
    # 预演产物默认落在用户数据目录下的隐藏暂存区，避免散落在调用者 cwd（迁移是从任何目录发起的）
    staging = Path(args.staging) if args.staging else (
        home / ".staging" / f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    stage_skills = staging / "skills"

    # 头像：源包有图就落地，没有就从应用内置图里稳定挑一张，绝不指向不存在的文件
    app_root = find_app_root(home)
    # 运行配置取自本机 model.json：写死 modelarts-shared/glm-5 会鉴权失败
    profile, model = rc.detect_runtime_profile(home)
    src_img = source_avatar(src, manifest, [name, display, nickname])
    avatar = ensure_avatar(app_root, name, src_img, write=False)  # 预演不落盘，install 时再定版

    report = {
        "generated_at": now_iso(),
        "source": {"path": str(src), "platform": plat, "manifest": str(mf_path), "version": version},
        "avatar_src": str(src_img) if src_img else "",
        "target": {"expert_name": name, "expert_id": expert_id, "display_name": display, "nickname": nickname},
        "skills": [],
        "needs_review": [],
        "dropped": [],
        "install": {"performed": False},
    }

    # 1) 专家主提示词技能（把 agent.md，或源包最完整的技能正文，或按元数据合成的提示词落成 OfficeAce 技能）
    derived_from = ""
    if not agent_prompt:
        rich, rich_slug = richest_skill_body(skill_dirs)
        if len(rich) >= 240:  # 太短的正文不足以承担角色设定，宁可走合成并在报告里要求补全
            # 用专家名替换技能原标题，避免出现两个一级标题
            head_line, _, rest = rich.partition("\n")
            agent_prompt = (f"# {display}\n{rest}" if head_line.startswith("# ") else f"# {display}\n\n{rich}")
            derived_from = rich_slug
    persona_dir = stage_skills / name
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "SKILL.md").write_text(
        build_persona_skill_text(name, display, desc, agent_prompt, slugs, source_label),
        encoding="utf-8",
    )
    report["skills"].append({
        "slug": name, "kind": "persona",
        "source": agent_path or (f"{derived_from}（正文转写）" if derived_from else "(synthesized)"),
    })
    if not agent_prompt:
        report["needs_review"].append(f"主提示词技能 `{name}` 由元数据合成，建议补入源套件的角色设定")
    elif derived_from:
        report["needs_review"].append(
            f"源包无 agents/ 入口提示词，主提示词与人设取自 `{derived_from}` 正文；"
            "若该技能偏执行细则、缺角色定位，建议补一段人设"
        )

    # 2) 逐技能转换
    for d in skill_dirs:
        slug = kebab(d.name)
        target = stage_skills / slug
        target.mkdir(parents=True, exist_ok=True)
        md, meta = rewrite_skill_md(d / "SKILL.md", slug, desc, source_label)
        (target / "SKILL.md").write_text(md, encoding="utf-8")
        copied, skipped = [], []
        for child in sorted(d.iterdir()):
            if child.name in ("SKILL.md", "_meta.json", ".DS_Store"):
                if child.name == "_meta.json":
                    skipped.append(child.name)
                continue
            dst = target / child.name
            if child.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(child, dst)
                copied.append(child.name + "/")
            else:
                shutil.copy2(child, dst)
                copied.append(child.name)
        if skipped:
            report["dropped"].append({"skill": slug, "files": skipped, "reason": "_meta.json 为源平台发布元数据，OfficeAce 不使用"})
        if meta["dropped_keys"]:
            report["dropped"].append({"skill": slug, "frontmatter_keys": meta["dropped_keys"]})
        if "scripts" in copied:
            report["needs_review"].append(f"`{slug}` 带脚本：请确认 Python/Node 依赖在 OfficeAce 环境可用")
        report["skills"].append(
            {"slug": slug, "kind": "skill", "source": str(d), "copied": copied, "desc_source": meta["desc_source"]}
        )

    # 3) 专家卡 + 注册项
    skills_for_expert = [name] + [s["slug"] for s in report["skills"] if s["kind"] == "skill"]
    role_desc = short_role(desc, 80)
    # 人设：有真实角色设定（源 agents/，或从主技能正文转写）时直接取主提示词技能正文；
    # 只有当主提示词是元数据拼出来的空壳时，才退回去扫正文最长的业务技能。
    persona = ""
    persona_md = staging / "skills" / name / "SKILL.md"
    if agent_prompt and persona_md.is_file():
        persona = rc.strip_frontmatter(persona_md.read_text(encoding="utf-8", errors="replace")).strip()
    if len(persona) < 240:
        for sk in report["skills"]:
            p = staging / "skills" / sk["slug"] / "SKILL.md"
            if p.is_file():
                body = rc.strip_runtime_banner(
                    rc.strip_frontmatter(p.read_text(encoding="utf-8", errors="replace"))
                )
                if len(body) > len(persona):
                    persona = body.strip()
    if not persona:
        persona = f"# {display}\n\n你现在是「{display}」。以该身份完成用户请求，数据与结论一律标注来源。"
    persona += rc.execution_rules(skills_for_expert, home, alt_root=staging / "skills")

    # 脚本引用改成绝对路径（指向最终的 ~/.office-claw/skills/<slug>，不是 staging）：
    # 专家的工作目录不是技能目录，相对路径在运行时会找不到文件
    for sk in report["skills"]:
        staged = staging / "skills" / sk["slug"]
        if staged.is_dir():
            rc.absolutize_scripts(staged, runtime_dir=home / "skills" / sk["slug"])
    expert_json = {
        "expertId": expert_id,
        "name": name,
        "displayName": display,
        "nickname": nickname,
        "avatar": avatar,
        "category": args.category,
        "mentionPatterns": [f"@{nickname}"],
        "roleDescription": role_desc,
        "personality": persona,
        "strengths": [],
        "skills": skills_for_expert,
        "agent_created": True,
        "visibility": "private",
        "creationSource": "user",
        "defaultModel": model,
        "providerProfileId": profile,
    }
    write_json(staging / "experts" / f"{name}.json", expert_json)

    catalog_entry = {
        "creationSource": "user",
        "visibility": "private",
        "name": name,
        "agentId": expert_id,
        "avatar": avatar,
    }
    breed = {
        "id": expert_id,
        "color": pick_color(name),
        "defaultVariantId": f"{expert_id}-default",
        "displayName": display,
        "avatar": avatar,
        "features": {"sessionChain": True},
        "agentId": expert_id,
        "creationSource": "user",
        "name": name,
        "nickname": nickname,
        "visibility": "private",
        "category": args.category,
        "variants": [rc.breed_variant(expert_id, skills_for_expert, persona, profile, model)],
        "mentionPatterns": [f"@{nickname}"],
        "roleDescription": expert_json["roleDescription"],
    }
    roster_entry = rc.roster_entry(expert_id, expert_json["roleDescription"], profile, model, False)
    write_json(
        staging / "catalog.patch.json",
        {"catalog_experts_entry": catalog_entry, "breed": breed, "roster": {expert_id: roster_entry}},
    )

    # 4) 报告
    (staging / "report.md").write_text(build_report(report, expert_json), encoding="utf-8")
    write_json(staging / "migration-manifest.json", report)

    # 5) 安装
    if args.install:
        install(staging, report, args)
        (staging / "report.md").write_text(build_report(report, expert_json), encoding="utf-8")
        write_json(staging / "migration-manifest.json", report)

    return report


def find_app_root(home: Path) -> Path | None:
    """定位 OfficeAce 应用安装根目录（其下有 .office-claw/capabilities.json 与 office-claw-skills/）。"""
    home.parent.name  # noqa: B018 —— home 形如 ~/.office-claw，应用根通常是其兄弟目录 OfficeAce
    for cand in (home.parent / "OfficeAce", home / "OfficeAce"):
        if (cand / ".office-claw" / "capabilities.json").is_file():
            return cand
    return None


AVATAR_FALLBACK = "/avatars/experts/expert.png"
AVATAR_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def avatar_root(app_root: Path | None) -> Path | None:
    """定位前端静态头像根目录（URL 前缀 /avatars/ 映射到该目录的磁盘路径）。

    参数：app_root —— OfficeAce 安装根目录；返回值：头像目录，找不到返回 None。
    """
    if not app_root:
        return None
    direct = app_root / "packages" / "green-package" / "web" / "dist" / "avatars"
    if direct.is_dir():
        return direct
    try:
        for cand in sorted(app_root.glob("**/web/dist/avatars")):
            if cand.is_dir():
                return cand
    except OSError:
        return None
    return None


def avatar_exists(app_root: Path | None, url) -> bool:
    """校验卡片里的 avatar URL 是否真能落到一个文件（只有 /avatars/ 前缀可本地校验）。

    参数：app_root —— 应用根；url —— 卡片里的头像值；返回值：可加载为 True。
    """
    if not isinstance(url, str) or not url.strip():
        return False
    url = url.strip()
    if url.startswith("/uploads/") or url.startswith(("http://", "https://")):
        return True
    if not url.startswith("/avatars/"):
        return False
    root = avatar_root(app_root)
    if root is None:
        return False
    return (root / url[len("/avatars/"):]).is_file()


def source_avatar(src: Path, manifest: dict, names: list[str]) -> Path | None:
    """在源套件里找一个可用作头像的图片文件。

    参数：src —— 源包根；manifest —— 源清单；names —— 候选文件名（agent 名、成员 id 等）。
    返回值：图片路径，找不到返回 None。
    """
    cands: list[Path] = []
    rel = manifest.get("avatar") if isinstance(manifest, dict) else None
    if isinstance(rel, str) and rel.strip():
        cands.append(src / rel.strip().lstrip("/"))
    for n in names:
        if not n:
            continue
        for ext in AVATAR_EXTS:
            cands.append(src / "avatars" / f"{n}{ext}")
    for ext in AVATAR_EXTS:
        cands.append(src / "avatars" / f"expert{ext}")
        cands.append(src / f"avatar{ext}")
    for c in cands:
        if c.is_file() and c.suffix.lower() in AVATAR_EXTS:
            return c
    return None


def avatar_quality(path: Path | str | None) -> str:
    """判断头像文件能否当正式头像用。

    参数：path —— 图片路径；返回值："ok" 可用 / "placeholder" 纯色或极小占位图 / "missing" 不存在。
    纯色占位图（如 8×8 单色 png）在 40px 圆框里就是一块色斑，等于没设计，按不合格处理。
    """
    if not path:
        return "missing"
    p = Path(path)
    if not p.is_file():
        return "missing"
    try:
        b = p.read_bytes()
    except OSError:
        return "missing"
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        return "ok"  # 非 PNG 不做深入判断，交给浏览器
    if len(b) < 12:
        return "placeholder"
    w = int.from_bytes(b[16:20], "big")
    h = int.from_bytes(b[20:24], "big")
    if w < 64 or h < 64 or len(b) < 2048:
        return "placeholder"
    return "ok"


def ensure_avatar(app_root: Path | None, slug: str, src_img: Path | None = None,
                  write: bool = True) -> str:
    """为专家选定一个**一定可加载**的头像 URL，避免卡片指向不存在的图片。

    参数：app_root —— 应用根；slug —— 专家目录名；src_img —— 源头像文件（可空）；
          write —— False 时只推算不复制文件（供 dry-run / 诊断使用）。
    优先级：①源头像复制进应用头像目录 ②同名头像已存在（幂等复用）
            ③应用内置通用头像（按名字散列稳定取一张） ④expert.png 兜底。
    返回值：/avatars/... 形式的 URL；极端情况下返回空串，让 UI 退回首字徽标。
    """
    root = avatar_root(app_root)
    if root is None:
        return AVATAR_FALLBACK
    experts = root / "experts"
    try:
        if src_img and avatar_quality(src_img) == "ok":
            ext = Path(src_img).suffix.lower()
            if ext in AVATAR_EXTS:
                name = f"{slug}{'.png' if ext == '.jpeg' else ext}"
                dst = experts / name
                if write and (not dst.is_file() or dst.stat().st_size != Path(src_img).stat().st_size):
                    experts.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src_img, dst)
                return f"/avatars/experts/{name}"
        for ext in AVATAR_EXTS:
            cand = experts / f"{slug}{ext}"
            # 幂等复用只在图合格时生效；纯色占位图要换掉，否则等于没修
            if cand.is_file() and avatar_quality(cand) == "ok":
                return f"/avatars/experts/{slug}{ext}"
        pool = sorted(p.name for p in root.glob("agent-avatar-*.png"))
        if pool:
            return f"/avatars/{pool[int(sha8(slug)[:8], 16) % len(pool)]}"
        if (experts / "expert.png").is_file():
            return AVATAR_FALLBACK
    except OSError:
        return AVATAR_FALLBACK
    return ""


def active_user_dir(home: Path) -> Path | None:
    """读取 connector-owner.local.json 的 ownerUserId 精确定位活跃用户目录。

    应用把 `orgId:userId` 中的冒号转义成 %3A 作为目录名；该文件是唯一权威标识。
    """
    p = home / "connector-owner.local.json"
    if not p.is_file():
        return None
    try:
        uid = read_json(p).get("ownerUserId")
    except Exception:  # noqa: BLE001
        return None
    if not uid:
        return None
    cand = home / "users" / str(uid).replace(":", "%3A")
    return cand if cand.is_dir() else None


def find_user_experts(home: Path) -> Path | None:
    """定位活跃用户的 user-experts.json（UI 专家列表的真正数据源，按修改时间取最新）。"""
    act = active_user_dir(home)
    if act and (act / "user-experts.json").is_file():
        return act / "user-experts.json"
    users = home / "users"
    if not users.is_dir():
        return None
    cands = [
        p
        for p in users.glob("*/user-experts.json")
        if ".bak" not in p.name and p.stat().st_size > 2
    ]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def find_user_catalog(home: Path) -> Path | None:
    d = home / "user-catalogs"
    if not d.is_dir():
        return None
    act = active_user_dir(home)
    if act:
        pref = d / (act.name + ".json")
        if pref.is_file():
            return pref
        alt = act / "office-claw-catalog.json"
        if alt.is_file():
            return alt
    cands = [
        p
        for p in d.glob("*.json")
        if ".bak" not in p.name and p.name != "catalog.json" and p.stat().st_size > 2
    ]
    if not cands:
        return None
    # 取 breeds 数量最多且最新的那个（即当前活跃用户目录）
    def score(p: Path) -> tuple[int, float]:
        try:
            n = len(read_json(p).get("breeds") or [])
        except Exception:  # noqa: BLE001
            n = -1
        return (n, p.stat().st_mtime)

    return max(cands, key=score)


def install(staging: Path, report: dict, args) -> None:
    home = Path(args.officeace_home).expanduser()
    if not home.is_dir():
        raise SystemExit(f"错误：OfficeAce 数据目录不存在 {home}（用 --officeace-home 指定）")
    ts = stamp()
    name = report["target"]["expert_name"]
    expert_id = report["target"]["expert_id"]
    patched = []

    # 技能目录
    for skill in staging.joinpath("skills").iterdir():
        if not skill.is_dir():
            continue
        dst = home / "skills" / skill.name
        if dst.exists():
            if not args.force:
                report["needs_review"].append(f"技能 `{skill.name}` 已存在，跳过覆盖（需覆盖请加 --force）")
                continue
            shutil.rmtree(dst)
        shutil.copytree(skill, dst)
        patched.append(f"skills/{skill.name}/")

    # 落盘后再统一改写一次脚本引用：此时全部技能都在，跨技能引用可按文件名唯一解析
    rc.absolutize_migrated(home, [sk["slug"] for sk in report["skills"]])

    # 专家卡
    (home / "experts").mkdir(parents=True, exist_ok=True)
    dst_json = home / "experts" / f"{name}.json"
    if dst_json.exists():
        shutil.copy2(dst_json, dst_json.with_suffix(f".json.bak-{ts}"))
    shutil.copy2(staging / "experts" / f"{name}.json", dst_json)
    patched.append(f"experts/{name}.json")

    patch = read_json(staging / "catalog.patch.json")

    # 头像定版：用真实 app_root 再解析一次并落地图片，保证四处注册写进去的路径都有文件
    app_root = (
        Path(args.app_root).expanduser() if getattr(args, "app_root", None) else find_app_root(home)
    )
    # 预演阶段已解析出源头像（report["avatar_src"]），install 必须沿用它；
    # 否则单专家包会退到应用通用头像，多个专家共用同一张图。
    src_img = Path(report["avatar_src"]) if report.get("avatar_src") else None
    if src_img is not None and not src_img.is_file():
        src_img = None
    avatar = ensure_avatar(app_root, name, src_img)
    if not avatar_exists(app_root, avatar):
        avatar = AVATAR_FALLBACK
    card = read_json(dst_json)
    card["avatar"] = avatar
    write_json(dst_json, card)
    patch["catalog_experts_entry"]["avatar"] = avatar
    patch["breed"]["avatar"] = avatar
    for v in patch["breed"].get("variants") or []:
        if isinstance(v, dict) and "avatar" in v:
            v["avatar"] = avatar

    # catalog.json
    cat = home / "user-catalogs" / "catalog.json"
    if cat.exists():
        shutil.copy2(cat, cat.with_name(f"catalog.json.bak-{ts}"))
        data = read_json(cat)
        experts = [e for e in data.get("experts", []) if e.get("name") != name]
        experts.append(patch["catalog_experts_entry"])
        data["experts"] = experts
        data["updatedAt"] = now_iso()
        write_json(cat, data)
        patched.append("user-catalogs/catalog.json")

    # 用户目录（breeds + roster）
    uc = Path(args.user_catalog) if args.user_catalog else find_user_catalog(home)
    if uc and uc.exists():
        shutil.copy2(uc, uc.with_name(f"{uc.name}.bak-{ts}"))
        data = read_json(uc)
        breeds = [b for b in data.get("breeds", []) if b.get("name") != name]
        breeds.append(patch["breed"])
        data["breeds"] = breeds
        roster = data.get("roster") or {}
        roster.update(patch["roster"])
        data["roster"] = roster
        write_json(uc, data)
        patched.append(f"user-catalogs/{uc.name}")
    else:
        report["needs_review"].append("未找到用户目录文件，专家卡与技能已就位但可能不会出现在专家列表，需在应用内重新保存一次专家")

    # 权威技能注册表 capabilities.json（应用安装目录下 .office-claw/，缺失即报 "configured but not installed"）
    app_root = (
        Path(args.app_root).expanduser() if getattr(args, "app_root", None) else find_app_root(home)
    )
    caps_path = app_root / ".office-claw" / "capabilities.json" if app_root else None
    if caps_path:
        shutil.copy2(caps_path, caps_path.with_name(f"capabilities.json.bak-{ts}"))
        caps = read_json(caps_path)
        have = {c.get("id") for c in caps.get("capabilities", [])}
        newly = []
        for sk in report["skills"]:
            sid = sk["slug"]
            if sid not in have:
                caps["capabilities"].append(
                    {"id": sid, "type": "skill", "enabled": True, "source": "custom",
                     "selfEvolution": "suggest", "followGlobalSelfEvolution": True}
                )
                newly.append(sid)
        write_json(caps_path, caps)
        patched.append(f"{caps_path}（注册 {len(newly)} 个技能）")
    else:
        report["needs_review"].append(
            "未找到应用安装目录的 .office-claw/capabilities.json，技能未登记到权威注册表，"
            "运行时会报 configured but not installed（可用 --app-root 指定）"
        )

    # custom 技能的持久化源：应用安装目录 .office-claw/skills/ + installed-skills.json。
    # capabilities.json 在应用每次启动时会再生：builtin + 该存储（36 个目录 = 36 条），
    # 只写 ~/.office-claw/skills 的技能会在重启后被刷掉。
    if app_root:
        store_skills = app_root / ".office-claw" / "skills"
        store_skills.mkdir(parents=True, exist_ok=True)
        for skill in staging.joinpath("skills").iterdir():
            if not skill.is_dir():
                continue
            dst = store_skills / skill.name
            if dst.exists() and not args.force:
                report["needs_review"].append(
                    f"应用目录技能 `{skill.name}` 已存在，跳过（需覆盖加 --force）"
                )
                continue
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(skill, dst)
        # 登记进应用目录 installed-skills.json 及其在数据目录的镜像
        now = datetime.now().isoformat(timespec="seconds")
        for sp in (
            app_root / ".office-claw" / "installed-skills.json",
            home / ".office-claw" / "installed-skills.json",
        ):
            if not sp.exists():
                continue
            sp_bak = sp.parent / f"installed-skills.json.bak-{ts}"
            if not sp_bak.exists():
                shutil.copy2(sp, sp_bak)
            d = read_json(sp)
            if not isinstance(d, dict) or not isinstance(d.get("skills", {}), dict):
                raise SystemExit(f"installed-skills.json 结构非预期（skills 应为对象），已中止登记：{sp}")
            d.setdefault("skills", {})
            for sk in report["skills"]:
                d["skills"].setdefault(
                    sk["slug"], {"source": "local", "installedAt": now, "name": sk["slug"]}
                )
            d["updatedAt"] = now
            write_json(sp, d)
        patched.append(f"{store_skills}（{len(report['skills'])} 个技能目录 + installed-skills.json）")
    else:
        report["needs_review"].append(
            "未找到应用安装目录，技能只写入了数据目录，重启后会被 capabilities 再生刷掉"
        )

    # 用户级专家列表 users/<uid>/user-experts.json（UI 专家列表的真正数据源）
    ue = find_user_experts(home)
    if ue:
        shutil.copy2(ue, ue.with_name(f"{ue.name}.bak-{ts}"))
        data = read_json(ue)
        card = read_json(dst_json)  # 用已定版头像的落盘卡片，避免回填 staging 里的旧值
        template = (data.get("experts") or [{}])[0]
        entry = rc.user_experts_entry(
            card["expertId"], card["displayName"],
            card.get("avatar") if avatar_exists(app_root, card.get("avatar")) else AVATAR_FALLBACK,
            card.get("category", "business"),
            card.get("roleDescription", ""), card.get("personality", ""),
            card.get("skills", []),
            card.get("providerProfileId") or template.get("providerProfileId", rc.FALLBACK_PROFILE),
            card.get("defaultModel") or template.get("defaultModel", rc.FALLBACK_MODEL),
            visibility=template.get("visibility", "public"),
        )
        rest = [e for e in data.get("experts", []) if e.get("expertId") != entry["expertId"]]
        rest.append(entry)
        data["experts"] = rest
        write_json(ue, data)
        patched.append(f"users/.../{ue.name}")
    else:
        report["needs_review"].append("未找到 users/<uid>/user-experts.json，专家将不出现在 UI 专家列表")

    report["install"] = {
        "performed": True,
        "officeace_home": str(home),
        "backup_stamp": ts,
        "written": patched,
        "expert_id": expert_id,
    }


def build_report(report: dict, expert_json: dict) -> str:
    s = report["source"]
    t = report["target"]
    lines = [
        f"# 迁移报告：{t['display_name']}（{t['expert_name']}）",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 源套件 | `{s['path']}` |",
        f"| 源平台 | {s['platform']} @ {s['version']} |",
        f"| 目标专家 ID | `{t['expert_id']}` |",
        f"| 显示名 / 昵称 | {t['display_name']} / {t['nickname']} |",
        f"| 迁移时间 | {report['generated_at']} |",
        "",
        "## 技能清单",
        "",
        "| # | 技能 | 类型 | 来源 |",
        "|---|---|---|---|",
    ]
    for i, sk in enumerate(report["skills"], 1):
        kind = "专家主提示词" if sk["kind"] == "persona" else "业务技能"
        lines.append(f"| {i} | `{sk['slug']}` | {kind} | {sk.get('source', '')} |")
    lines += ["", "## 专家卡", "", "```json", json.dumps(expert_json, ensure_ascii=False, indent=2), "```"]
    lines += ["", "## 丢弃 / 剥离", ""]
    if report["dropped"]:
        for d in report["dropped"]:
            lines.append(f"- `{d['skill']}`：{', '.join(d.get('files', []) or d.get('frontmatter_keys', []))}"
                         + (f"（{d.get('reason')}）" if d.get("reason") else "（源平台专有 frontmatter，OfficeAce 不识别）"))
    else:
        lines.append("- 无")
    lines += ["", "## 需人工确认", ""]
    if report["needs_review"]:
        for n in dict.fromkeys(report["needs_review"]):
            lines.append(f"- {n}")
    else:
        lines.append("- 无")
    inst = report.get("install") or {}
    lines += ["", "## 安装结果", ""]
    if inst.get("performed"):
        lines.append(f"- 已写入 `{inst['officeace_home']}`，备份后缀 `{inst['backup_stamp']}`")
        for w in inst.get("written", []):
            lines.append(f"  - {w}")
        lines.append("- 注册项即时生效；界面或当前会话未刷新时重启一次 OfficeAce；团队改动要新建会话才套用")
    else:
        lines.append("- 本次为预演（dry-run），未写入 OfficeAce。确认无误后加 `--install` 重跑。")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="专家套件 → OfficeAce 迁移")
    ap.add_argument("--source", required=True)
    ap.add_argument("--staging", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--display-name", dest="display_name", default=None)
    ap.add_argument("--nickname", default=None)
    ap.add_argument("--category", default="business")
    ap.add_argument("--officeace-home", dest="officeace_home", default="~/.office-claw")
    ap.add_argument("--app-root", default=None, help="OfficeAce 应用安装根目录（含 .office-claw/capabilities.json）")
    ap.add_argument("--user-catalog", dest="user_catalog", default=None)
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--confirm-local", dest="confirm_local", default=None, metavar="TICKET",
                    help="跨机器确认票据（闸门 1.6.0：直接调用本脚本 --install 同样被拦截）")
    ap.add_argument("--gate-cooldown", dest="gate_cooldown", type=int, default=None, metavar="SECONDS")
    args = ap.parse_args()

    # ⛔ 跨机器确认闸门（1.6.0）：与 migrate.py 共用 migration_gate，堵住直接调用的旁路。
    # 入口脚本已确认时凭票据文件的 confirmed 标记放行，不重复提问。
    gate_rc = gate.enforce(Path(args.officeace_home).expanduser(), args.install,
                           args.confirm_local, cooldown=args.gate_cooldown,
                           source=str(args.source), entry="migrate_suite.py")
    if gate_rc is not None:
        return gate_rc

    if not Path(args.source).exists():
        print(f"错误：源目录不存在 {args.source}", file=sys.stderr)
        return 2
    report = migrate(args)
    st = report["install"]
    print(f"[{'已安装' if st.get('performed') else '预演'}] {report['target']['display_name']} "
          f"-> {report['target']['expert_id']}，技能 {len(report['skills'])} 个")
    for sk in report["skills"]:
        print(f"   - {sk['slug']} ({sk['kind']})")
    if report["needs_review"]:
        print("需人工确认：")
        for n in dict.fromkeys(report["needs_review"]):
            print(f"   ! {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
