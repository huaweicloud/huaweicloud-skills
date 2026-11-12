#!/usr/bin/env python3
"""把 WorkBuddy 自定义专家包 / 专家团迁移为 OfficeAce 专家（与专家团）。

用途：WorkBuddy 专家包 → OfficeAce 专家/专家团（默认 dry-run，--install 才写盘；支持一包多角色展开）。
参数：--source 包或插件市场目录（必填）；--all 批量模式；--install 安装；--force 覆盖；
      --officeace-home 数据目录；--app-root 应用安装根目录。
返回值：退出码 0=成功，非 0=失败（目录不存在、缺清单、找不到应用根等）。

WorkBuddy 源格式（三者中结构最完整的一种）：
  <pkg>/.codebuddy-plugin/plugin.json     清单，含 expertType=agent|team、teamInfo、members、tags、quickPrompts
  <pkg>/agents/<agent>.md                 每个角色一份，frontmatter(name/displayName.zh/profession.zh)+人设正文
  <pkg>/skills/<slug>/                    包级技能（团队里所有成员共享）
  <pkg>/avatars/                          角色头像

与千问办公 / 百度搭子的关键差异：
  1. **一包可含多角色**（团队），一个包要产出 N 个专家 + 1 条团队注册；
  2. 人设是**真文件**（agents/*.md），不需要合成；
  3. 包级 skills 由全部成员共享（OfficeAce 里表现为主提示词 + 包级技能并列）。

用法：
    # 预演（默认，不写盘）
    python migrate_workbuddy.py --source <包目录>

    # 批量预演整个市场目录
    python migrate_workbuddy.py --source <my-experts/plugins> --all

    # 真正安装
    python migrate_workbuddy.py --source <包目录> --install

    # 覆盖已存在的技能目录
    python migrate_workbuddy.py --source <包目录> --install --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_contract as rc  # noqa: E402
import migration_gate as gate  # noqa: E402
from migrate_suite import (  # noqa: E402
    AVATAR_EXTS,
    build_persona_skill_text,
    ensure_avatar,
    find_app_root,
    find_user_catalog,
    find_user_experts,
    kebab,
    parse_frontmatter,
    pick_color,
    read_json,
    sha8,
    short_role,
    source_avatar,
    stamp,
    write_json,
    yaml_escape,
)

MANIFEST_REL = Path(".codebuddy-plugin") / "plugin.json"
CATEGORY_MAP = (
    ("legal", "legal"),
    ("law", "legal"),
    ("engineer", "tech"),
    ("tech", "tech"),
    ("data", "tech"),
    ("research", "insight"),
    ("insight", "insight"),
    ("design", "insight"),
)
TAG_COLORS = ["#8B5CF6", "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#14B8A6"]


def parse_flow_mapping(v: str) -> dict | None:
    """解析 YAML 内联 flow mapping：`{ zh: 纪颜色 }`、`{zh: X, en: Y}`、`{}`。
    非 flow mapping 形态返回 None。只支持一层键值对（不处理嵌套 / 引号内逗号——
    专家包 frontmatter 实际只用 displayName/profession/description 这类简单双语映射）。
    2026-11 评审 P1：文档样例本身就是内联写法，之前只认块状，导致按文档照抄的包
    displayName / mentionPatterns 带着花括号落盘。"""
    t = v.strip()
    if not (t.startswith("{") and t.endswith("}")):
        return None
    inner = t[1:-1].strip()
    if not inner:
        return {}
    out: dict = {}
    for part in inner.split(","):
        if ":" not in part:
            continue
        pk, pv = part.split(":", 1)
        pk = pk.strip().strip('"').strip("'")
        pv = pv.strip().strip('"').strip("'")
        if pk:
            out[pk] = pv
    return out


def parse_fm_nested(text: str) -> tuple[dict, str]:
    """支持两级嵌套的 frontmatter 解析（WorkBuddy 用 displayName: {zh,en} 这种结构）。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm: dict = {}
    current = None
    for raw in text[3:end].splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indented = line[:1] in (" ", "\t")
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        # 内联 flow mapping（文档样例即此写法）优先于块状判断
        val = parse_flow_mapping(v)
        if val is None:
            val = v.strip('"').strip("'")
        if indented and current:
            if not isinstance(fm.get(current), dict):
                fm[current] = {}
            fm[current][k] = val
        elif val:
            fm[k] = val
            current = None
        else:
            fm[k] = {}
            current = k
    return fm, text[end + 4 :].lstrip("\n")


def detect_pkg(root: Path) -> Path | None:
    if (root / MANIFEST_REL).is_file():
        return root
    return None


def zh(node, fallback: str = "") -> str:
    if isinstance(node, dict):
        return node.get("zh") or node.get("en") or fallback
    return node or fallback


def map_category(category_id: str) -> str:
    low = (category_id or "").lower()
    for key, cat in CATEGORY_MAP:
        if key in low:
            return cat
    return "business"


def agent_description(fm: dict, manifest: dict, teammates: int) -> str:
    desc = fm.get("description")
    if isinstance(desc, dict):
        # 多语言对象（SKILL.md 允许 description 为 {zh,en} dict），取中文优先
        desc = zh(desc, "")
    desc = desc or ""
    if re.search(r"[\u4e00-\u9fff]", desc):
        return short_role(desc, 160)
    return zh(manifest.get("displayDescription"), "") or short_role(desc, 160)


def normalize_slug(raw, context: str = "专家") -> str:
    """P0 安全闸门（2026-11 评审）：源包 frontmatter 的 name 来自第三方 marketplace 包，
    是不可信输入。一切落盘路径（skills/<name>/、experts/<name>.json、头像文件名）都必须
    先经本函数归一。空值 / 含 `..` / 绝对路径 → 报错退出（不静默改写，按评审要求）；
    其余取 basename，保证产物永远落在 ~/.office-claw 数据目录之内。"""
    s = str(raw if raw is not None else "").strip()
    if not s:
        raise SystemExit(f"错误：{context} 的 name 为空，拒绝迁移（非法包内容）。请修正源包 frontmatter 后重试。")
    if ".." in s:
        raise SystemExit(f"错误：{context} 的 name 含 '..'（{s!r}），疑似路径穿越，拒绝迁移。请修正源包 frontmatter 后重试。")
    if s.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[/\\]", s):
        raise SystemExit(f"错误：{context} 的 name 是绝对路径（{s!r}），拒绝迁移。请修正源包 frontmatter 后重试。")
    slug = Path(s).name
    if slug != s:
        print(f"[安全归一] {context} 的 name 含路径分隔符：{s!r} → {slug!r}（取 basename）")
    return slug


def build_experts(pkg: Path, manifest: dict, home: Path) -> list[dict]:
    """把一个包里的每个 agent 展开成专家描述（含 ID 复用、技能分工、完整人设、可用头像）。"""
    agents_rel = manifest.get("agents") or []
    info = manifest.get("teamInfo") or {}
    orchestration = {info.get("leadAgent")} if info.get("leadAgent") else set()
    # 包级技能以磁盘为准（manifest 里的 `./skills/x` 是相对路径，可能已被改写）
    pkg_skills = rc.package_skills(pkg) or [Path(p).name for p in (manifest.get("skills") or [])]
    app_root = find_app_root(home)
    # members[] 里每个角色自带 avatar，是团队包最准的源头像
    member_avatar: dict[str, str] = {}
    for m in manifest.get("members") or []:
        if not isinstance(m, dict):
            continue
        rel = m.get("avatar")
        if not (isinstance(rel, str) and rel.strip()):
            continue
        for key in (m.get("id"), m.get("name"), zh(m.get("displayName"))):
            if isinstance(key, str) and key.strip():
                member_avatar.setdefault(key.strip(), rel.strip())
    is_team = manifest.get("expertType") == "team"
    out = []
    for rel in agents_rel:
        md = pkg / Path(rel).relative_to("./") if str(rel).startswith("./") else pkg / rel
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        fm, body = parse_fm_nested(text)
        # P0：name 是不可信输入，落盘前统一归一（拒绝空值/.. /绝对路径，其余取 basename）
        name = normalize_slug(fm.get("name") or md.stem, context=f"{pkg.name}/agents/{md.stem}")
        display = zh(fm.get("displayName")) or zh(manifest.get("displayName")) or name
        profession = zh(fm.get("profession")) or zh(manifest.get("profession")) or display
        desc = agent_description(fm, manifest, len(agents_rel))
        # 头像：成员级 avatar > avatars/<name>.png > 清单级（只在单角色包/主理人时用）
        src_img: Path | None = None
        for cand in (member_avatar.get(name), member_avatar.get(display)):
            if cand and (pkg / cand.lstrip("/")).is_file():
                src_img = pkg / cand.lstrip("/")
                break
        if src_img is None:
            for ext in AVATAR_EXTS:
                p = pkg / "avatars" / f"{name}{ext}"
                if p.is_file():
                    src_img = p
                    break
        if src_img is None and not is_team:
            src_img = source_avatar(pkg, manifest, [name, display])
        if src_img is None and is_team and name in orchestration:
            src_img = source_avatar(pkg, manifest, [name, display])
        # 分工：成员只挂自己用得到的技能。旧版给每人挂全队技能，导致越界执行、口径互相冲突
        is_leader = name in orchestration or (
            is_team and bool(re.search(r"(team-lead|allocator|-lead$)", name))
        )
        skills, skills_basis = rc.bind_skills(name, text, pkg_skills, is_leader=is_leader)
        # ID 复用：已有同名专家卡就沿用其 expertId（保证幂等，且不打断既有会话引用）
        card_path = home / "experts" / f"{name}.json"
        if card_path.is_file():
            old = read_json(card_path)
            expert_id = old.get("expertId") or f"expert-{name}-{sha8(name + '1.0.0')}"
            agent_id = old.get("agentId") or expert_id
        else:
            expert_id = f"expert-{name}-{sha8(name + str(manifest.get('version', '1.0.0')))}"
            agent_id = expert_id
        out.append(
            {
                "name": name,
                "display": display,
                "profession": profession,
                "desc": desc,
                # 完整人设：frontmatter 与一级标题之后的全部正文，判据/输出格式/边界都在里面
                "persona": rc.persona_body(text),
                # 一句话角色说明：`职业。正文第一句`，与 OfficeAce 预置专家的描述同风格
                "role_desc": rc.role_line(profession, text, desc),
                "expert_id": expert_id,
                "agent_id": agent_id,
                "agent_md": text,
                "body": body,
                "skills": skills,
                "skills_basis": skills_basis,
                "is_leader": is_leader,
                # 预演阶段只推算不落盘；真正的落地在 install() 用 --app-root 重算
                "avatar": ensure_avatar(app_root, name, src_img, write=False),
                "avatar_src": str(src_img) if src_img else None,
                "is_team": is_team,
            }
        )
    return out


def persona_text(exp: dict, pkg: Path) -> str:
    label = f"WorkBuddy:{pkg.name}@{read_json(pkg / MANIFEST_REL).get('version', '1.0.0')}"
    return build_persona_skill_text(
        exp["name"], exp["display"], exp["desc"], exp["agent_md"], exp["skills"], label
    )


def team_entry(manifest: dict, experts: list[dict]) -> dict | None:
    if manifest.get("expertType") != "team":
        return None
    info = manifest.get("teamInfo") or {}
    lead = info.get("leadAgent") or manifest.get("agentName")
    by_name = {e["name"]: e for e in experts}
    members = []
    if lead in by_name:
        members.append({"expertId": by_name[lead]["expert_id"], "role": "leader",
                        "displayName": by_name[lead]["display"]})
    for m in info.get("memberAgents") or []:
        if m in by_name:
            members.append({"expertId": by_name[m]["expert_id"], "role": "teammate",
                            "displayName": by_name[m]["display"]})
    scenarios = [zh(q) for q in (manifest.get("quickPrompts") or []) if zh(q)][:3]
    if not scenarios:
        init = zh(manifest.get("defaultInitPrompt"))
        scenarios = [init] if init else []
    tags = []
    for i, t in enumerate((manifest.get("tags") or [])[:4]):
        label = zh(t)
        if label:
            tags.append({"id": kebab(label), "label": label, "color": TAG_COLORS[i % len(TAG_COLORS)]})
    return {
        "teamId": f"wb-team-{manifest['name']}",
        "displayName": zh(manifest.get("displayName")) or manifest["name"],
        "description": zh(manifest.get("displayDescription")),
        "scenarios": scenarios,
        "leaderExpertId": members[0]["expertId"] if members else None,
        "members": members,
        "visibility": "private",
        "creationSource": "user",
        "teamMode": "predefined",
        "teammateMode": "build_mode",
        "maxDebateRounds": 10,
        # OfficeAce 队级标量：省略会回退 TEAM_SPEC_DEFAULTS，不同版本默认值不一致，
        # 显式写死才能保证迁移前后行为一致（实测缺 dispatchMode 时派活策略会变）
        **rc.team_scalars(),
        "tags": tags,
        "summonPrompt": scenarios[0] if scenarios else "",
        "_source": "workbuddy",
    }


def migrate_pkg(pkg: Path, home: Path | None = None) -> dict:
    """规划一个包的迁移产物。`home` 是目标数据目录（ID 复用按它查已有专家卡），
    缺省回退 ~/.office-claw；多数据目录机器必须显式传入，否则幂等判断会查错目录。"""
    manifest = read_json(pkg / MANIFEST_REL)
    home = home or Path("~/.office-claw").expanduser()
    experts = build_experts(pkg, manifest, home)
    return {
        "package": pkg.name,
        "version": str(manifest.get("version", "1.0.0")),
        "expert_type": manifest.get("expertType", "agent"),
        "category": map_category(str(manifest.get("categoryId", ""))),
        "experts": experts,
        "team": team_entry(manifest, experts),
        # 与 build_experts 同源：磁盘扫描优先（manifest 未声明 skills 字段时，
        # 专家卡仍会通过 frontmatter 绑定磁盘上的包级技能，install 必须把它们装上）
        "pkg_skills": rc.package_skills(pkg) or [Path(p).name for p in (manifest.get("skills") or [])],
        "avatar": manifest.get("avatar"),
    }


def build_staging_report(pkg: Path, plan: dict, home: Path) -> Path:
    """评审 P1（2026-11）：WorkBuddy 路径此前 dry-run 不落任何产物，
    SKILL.md 承诺的「先看 report.md 两栏再决定装不装」对主平台失效。
    现在预演与安装前都写 ~/.office-claw/.staging/<pkg>-<时间戳>/report.md，
    内容为「丢弃 / 需人工确认」两栏 + 专家与技能清单。只写报告，不写注册。"""
    manifest = read_json(pkg / MANIFEST_REL)
    staging = home / ".staging" / f"{pkg.name}-{stamp()}"
    dropped: list[str] = []
    manual: list[str] = []
    for key in ("quickPrompts", "tags", "welcome", "shortcuts"):
        if manifest.get(key):
            dropped.append(f"清单字段 `{key}`：OfficeAce 专家卡无对应结构，未迁移")
    for e in plan["experts"]:
        label = f"专家 {e['display']}"
        if not e.get("avatar_src"):
            manual.append(f"{label}：源包未提供头像，将使用内置兜底头像（可用 scripts/set_avatar.py 更换）")
        if not e["skills"]:
            manual.append(f"{label}：未绑定任何技能（依据 {e['skills_basis']}），安装后仅按人设作答")
    for slug in plan["pkg_skills"]:
        sk = pkg / "skills" / slug
        if (sk / "scripts").is_dir() and any((sk / "scripts").iterdir()):
            manual.append(f"技能 `{slug}`：携带 scripts/，Python/Node 依赖、路径分隔符、编码需在本机实测（铁律 8）")
    if plan.get("team"):
        manual.append("专家团：装完后用 scripts/check_runtime.py 验证主理人与成员解析正常（故障表「主理人出错」）")
    staging.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# 迁移预演报告：{plan['package']} v{plan['version']}",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 源包 | `{pkg}` |",
        f"| 类型 | {'专家团' if plan['team'] else '单专家'}（{len(plan['experts'])} 个专家） |",
        f"| 分类 | {plan['category']} |",
        f"| 生成时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        "",
        "## 专家与技能",
        "",
    ]
    for e in plan["experts"]:
        role = "主理人" if e["is_leader"] else ("成员" if e["is_team"] else "专家")
        lines.append(f"- [{role}] {e['display']}（expertId={e['expert_id']}）技能：{', '.join(e['skills']) or '（无）'}")
    lines += ["", "## 丢弃（搬不过去的）", ""]
    lines += [f"- {d}" for d in dropped] or ["- 无"]
    lines += ["", "## 需人工确认（搬过去但要人验的）", ""]
    lines += [f"- {m}" for m in manual] or ["- 无"]
    lines += ["", "> 两栏不空就不要直接 `--install`；逐条处理或给出明确接受理由后再装。", ""]
    report = staging / "report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def install(pkg: Path, plan: dict, home: Path, args) -> list[str]:
    ts = stamp()
    written: list[str] = []
    app_root = Path(args.app_root).expanduser() if args.app_root else find_app_root(home)
    if not app_root:
        raise SystemExit("错误：找不到 OfficeAce 应用安装目录，用 --app-root 指定")

    stores = [home / "skills", app_root / ".office-claw" / "skills"]
    for s in stores:
        s.mkdir(parents=True, exist_ok=True)

    # 1) 技能：包级技能先落盘（带 references/scripts/assets），主提示词技能后写 SKILL.md。
    #    顺序不可颠倒：人设技能会先 mkdir 出同名目录，之后 copytree 撞上 dst.exists()
    #    被跳过，「专家名 == 技能目录名」的包就会丢掉全部脚本与参考文档（1.7.3 修复）。
    skills_to_write: list[tuple[str, Path | None, str]] = []
    for slug in plan["pkg_skills"]:
        src = pkg / "skills" / slug
        if src.is_dir():
            skills_to_write.append((slug, src, ""))
    for exp in plan["experts"]:
        skills_to_write.append((exp["name"], None, persona_text(exp, pkg)))

    skill_ids = []
    for slug, src_dir, text in skills_to_write:
        skill_ids.append(slug)
        for store in stores:
            dst = store / slug
            if src_dir is None:
                # 主提示词技能：始终以源套件为准刷新（专家人设变了要跟着变）
                dst.mkdir(parents=True, exist_ok=True)
                (dst / "SKILL.md").write_text(text, encoding="utf-8")
                written.append(f"{dst}/SKILL.md")
                continue
            if dst.exists() and not args.force:
                have = [p for p in dst.rglob("*") if p.is_file()]
                want = [p for p in src_dir.rglob("*") if p.is_file()]
                # 残缺目录（只剩 SKILL.md，资源在上一次迁移中丢失）→ 补齐而不是跳过
                if len(have) <= 1 and len(want) > 1:
                    shutil.copytree(src_dir, dst, dirs_exist_ok=True)
                    written.append(f"{dst}（补齐缺失资源：{len(want) - len(have)} 个）")
                continue
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src_dir, dst)
            # 源包脏格式兜底：SKILL.md 围栏写成 `\---` 时应用侧解析不出技能元数据
            sk_md = dst / "SKILL.md"
            if sk_md.is_file():
                t = sk_md.read_text(encoding="utf-8", errors="replace")
                fixed = rc.normalize_frontmatter_fence(t)
                if fixed != t:
                    sk_md.write_text(fixed, encoding="utf-8")
                    written.append(f"{dst}/SKILL.md（围栏归一化 \\--- → ---）")
            written.append(str(dst))

    # 1.5) 包级静态知识库：WorkBuddy 的 references/ 不属于任何技能，但人设正文按
    #      `references/xxx.md` 引用它（「提示词+静态知识型」的全部知识都在这里）。
    #      不带走的话运行时查不到 → 专家退化成凭记忆作答（实测类型②缺陷）。
    ref_src = rc.pkg_references(pkg)
    if ref_src:
        ref_files = [f for f in ref_src.rglob("*") if f.is_file()]
        for exp in plan["experts"]:
            slug = exp["name"]
            for store in stores:
                ref_dst = store / slug / "references"
                ref_dst.mkdir(parents=True, exist_ok=True)
                for f in ref_files:
                    rel = f.relative_to(ref_src)
                    (ref_dst / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, ref_dst / rel)
            md = home / "skills" / slug / "SKILL.md"
            if md.is_file():
                t = md.read_text(encoding="utf-8", errors="replace")
                if "静态知识库位置" not in t:
                    note_path = (home / "skills" / slug / "references").resolve()
                    note = (
                        f"\n\n> **静态知识库位置（必须遵守）**：人设中提到的 `references/...` 一律从"
                        f"`{note_path}` 按绝对路径读取——你的工作目录不在技能目录下，"
                        f"相对路径查不到；查库后再作答，不凭记忆输出。\n"
                    )
                    md.write_text(t.rstrip() + note, encoding="utf-8")
        written.append(f"包级 references/（{len(ref_files)} 个文件）→ 各专家主技能 references/")

    # 1.6) 扁平技能结构：`skills/SKILL.md` 直接躺在 skills/ 下、资源放在 skills/references
    #      与 skills/scripts（而非 skills/<slug>/…）。package_skills() 认不出这种形态，
    #      子目录会被整包丢光，SKILL.md 里的 references/、scripts/ 引用全部指向空路径。
    #      这里把 skills/ 下的资源目录并入各专家主技能；SKILL.md 仍以人设版为准。
    flat = pkg / "skills"
    if (flat / "SKILL.md").is_file():
        merged_dirs = 0
        for exp in plan["experts"]:
            for store in stores:
                dst = store / exp["name"]
                dst.mkdir(parents=True, exist_ok=True)
                for sub in flat.iterdir():
                    if not sub.is_dir() or sub.name == "__pycache__":
                        continue
                    shutil.copytree(sub, dst / sub.name, dirs_exist_ok=True)
                    merged_dirs += 1
        if merged_dirs:
            written.append(
                f"扁平技能资源（skills/ 下的 references、scripts 等）→ 专家主技能（{merged_dirs} 个目录）"
            )

    # 脚本路径改写（只处理本次迁移的技能，绝不碰平台预置技能）：
    # 团队会话的 cwd 是 team-workspace，那里没有 scripts/，相对路径必然找不到文件
    patched_md = rc.absolutize_migrated(home, skill_ids)
    # 应用目录副本要跟着改（重启时 capabilities 从这里再生）
    for sid in skill_ids:
        src_md = home / "skills" / sid / "SKILL.md"
        dst_md = app_root / ".office-claw" / "skills" / sid / "SKILL.md"
        if src_md.is_file() and dst_md.parent.is_dir():
            shutil.copy2(src_md, dst_md)
    if patched_md:
        written.append(f"SKILL.md 脚本引用改为绝对路径（{patched_md} 处）")

    # 2) 技能登记：installed-skills.json（应用目录 + 镜像）
    now = datetime.now().isoformat(timespec="seconds")
    for sp in (
        app_root / ".office-claw" / "installed-skills.json",
        home / ".office-claw" / "installed-skills.json",
    ):
        if not sp.is_file():
            continue
        bak = sp.parent / f"installed-skills.json.bak-{ts}"
        if not bak.exists():
            shutil.copy2(sp, bak)
        d = read_json(sp)
        if not isinstance(d, dict) or not isinstance(d.get("skills", {}), dict):
            raise SystemExit(f"installed-skills.json 结构非预期（skills 应为对象），已中止登记：{sp}")
        d.setdefault("skills", {})
        for sid in skill_ids:
            d["skills"].setdefault(sid, {"source": "local", "installedAt": now, "name": sid})
        d["updatedAt"] = now
        write_json(sp, d)

    # 3) capabilities.json（应用安装目录下 .office-claw/；缺失时跳过而不是中断安装）
    caps_path = app_root / ".office-claw" / "capabilities.json"
    if caps_path.is_file():
        caps = read_json(caps_path)
        have = {c.get("id") for c in caps.get("capabilities", [])}
        shutil.copy2(caps_path, caps_path.with_name(f"capabilities.json.bak-{ts}"))
        for sid in skill_ids:
            if sid not in have:
                caps["capabilities"].append(
                    {"id": sid, "type": "skill", "enabled": True, "source": "custom",
                     "selfEvolution": "suggest", "followGlobalSelfEvolution": True}
                )
        write_json(caps_path, caps)
    else:
        written.append(f"! 未找到 {caps_path}，跳过 capabilities 登记（用 --app-root 指定应用安装目录）")

    # 4) 专家卡 + catalog + breeds/roster + user-experts
    experts_dir = home / "experts"
    experts_dir.mkdir(exist_ok=True)
    cat = home / "user-catalogs" / "catalog.json"
    cat_data = read_json(cat) if cat.is_file() else {"experts": []}
    if cat.is_file():
        shutil.copy2(cat, cat.with_name(f"catalog.json.bak-{ts}"))
    cat_data["experts"] = [e for e in cat_data.get("experts", [])
                           if e.get("name") not in {x["name"] for x in plan["experts"]}]

    ue_path = find_user_experts(home)
    if ue_path is None:
        # 没有 user-experts.json 时不能静默跳过：那份文件是 /api/experts 的唯一数据源，
        # 不写等于"专家装好了但列表里没有"，团队也解析不到角色
        act = rc.active_user_dir(home)
        if act:
            ue_path = act / "user-experts.json"
            print(f"    [init] 新建用户专家目录文件：{ue_path}")
    ue = read_json(ue_path) if ue_path and ue_path.is_file() else {"experts": []}
    if ue_path and ue_path.is_file():
        shutil.copy2(ue_path, ue_path.with_name(f"user-experts.json.bak-{ts}"))
    template = (ue.get("experts") or [{}])[0]

    uc_path = find_user_catalog(home)
    uc = read_json(uc_path) if uc_path else None
    if uc_path:
        shutil.copy2(uc_path, uc_path.with_name(f"{uc_path.name}.bak-{ts}"))

    # 运行配置必须取自本机 model.json：写死 modelarts-shared/glm-5 会直接鉴权失败
    profile, model = rc.detect_runtime_profile(home)
    print(f"   运行配置：{profile} / {model}")

    for exp in plan["experts"]:
        # 用真实 app_root 重新解析并落地图片：优先源包原图，其次内置头像；
        # 保证写进卡片的路径一定有文件，否则 UI 会把 alt 文本渲染成乱码
        exp["avatar"] = ensure_avatar(
            app_root, exp["name"],
            Path(exp["avatar_src"]) if exp.get("avatar_src") else None,
        )
        # 人设 = agents/*.md 完整正文 + 该角色所挂技能的「先跑脚本」硬规则
        persona = exp["persona"] + rc.execution_rules(exp["skills"], home)
        card = {
            "expertId": exp["expert_id"],
            "agentId": exp["agent_id"],
            "name": exp["name"],
            "displayName": exp["display"],
            "nickname": exp["display"],
            "avatar": exp["avatar"],
            "category": plan["category"],
            "mentionPatterns": [f"@{exp['display']}"],
            "roleDescription": exp["role_desc"],
            "personality": persona,
            "strengths": [],
            "skills": exp["skills"],
            "visibility": "private",
            "creationSource": "user",
            "defaultModel": model,
            "providerProfileId": profile,
            "agent_created": True,
        }
        write_json(experts_dir / f"{exp['name']}.json", card)
        written.append(f"experts/{exp['name']}.json")

        # catalog.json 对全部角色都要登记（团队运行时按 agentId 解析）
        cat_data["experts"].append({"creationSource": "user", "visibility": "private",
                                    "name": exp["name"], "agentId": exp["agent_id"],
                                    "avatar": exp["avatar"]})

        # users/<uid>/user-experts.json —— /api/experts 的唯一数据源。
        # 主理人与成员必须全部登记：只写 user-teams.json 时团队运行时解析不到主理人，
        # 表现为「主理人出错」+ 成员档案回落成英文 id（实测根因）。
        ue["experts"] = [e for e in ue.get("experts", []) if e.get("expertId") != exp["expert_id"]]
        ue["experts"].append(
            rc.user_experts_entry(
                exp["expert_id"], exp["display"], exp["avatar"], plan["category"],
                exp["role_desc"], persona, exp["skills"], profile, model,
                visibility=template.get("visibility", "public"),
            )
        )

        if uc:
            uc["breeds"] = [b for b in uc.get("breeds", []) if b.get("name") != exp["name"]]
            uc["breeds"].append({
                "id": exp["expert_id"], "color": pick_color(exp["name"]),
                "defaultVariantId": f"{exp['expert_id']}-default",
                "displayName": exp["display"], "avatar": exp["avatar"],
                "features": {"sessionChain": True}, "agentId": exp["expert_id"],
                "creationSource": "user", "name": exp["name"], "nickname": exp["display"],
                "mentionPatterns": [f"@{exp['display']}"],
                "visibility": "private", "category": plan["category"],
                "variants": [rc.breed_variant(exp["expert_id"], exp["skills"],
                                              persona, profile, model)],
                "roleDescription": exp["role_desc"],
            })
            roster = uc.get("roster") or {}
            roster[exp["expert_id"]] = rc.roster_entry(
                exp["expert_id"], exp["role_desc"], profile, model, exp["is_leader"]
            )
            uc["roster"] = roster

    write_json(cat, cat_data)
    if ue_path:
        write_json(ue_path, ue)
    if uc_path:
        write_json(uc_path, uc)

    # 5) 团队注册
    if plan["team"] and ue_path:
        teams_path = ue_path.parent / "user-teams.json"
        if teams_path.is_file():
            shutil.copy2(teams_path, teams_path.with_name(f"user-teams.json.bak-{ts}"))
            tdata = read_json(teams_path)
        else:
            tdata = {"version": 1, "teams": []}
        entry = dict(plan["team"])
        entry.pop("_source", None)
        # 团队头像：源包 avatars/team.png 是最准的一张，落地后才不会退回内置图
        team_img = pkg / "avatars" / "team.png"
        if team_img.is_file():
            entry["avatar"] = ensure_avatar(app_root, entry["teamId"], team_img)
        tdata["teams"] = [t for t in tdata.get("teams", []) if t.get("teamId") != entry["teamId"]]
        tdata["teams"].append(entry)
        write_json(teams_path, tdata)
        written.append(f"users/.../user-teams.json（{entry['teamId']}）")

    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="WorkBuddy 专家包/专家团 → OfficeAce")
    ap.add_argument("--source", required=True)
    ap.add_argument("--all", action="store_true", help="source 是包含多个专家包的目录")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--officeace-home", dest="officeace_home", default="~/.office-claw")
    ap.add_argument("--app-root", default=None)
    ap.add_argument("--confirm-local", dest="confirm_local", default=None, metavar="TICKET",
                    help="跨机器确认票据（闸门 1.6.0：直接调用本脚本 --install 同样被拦截）")
    ap.add_argument("--gate-cooldown", dest="gate_cooldown", type=int, default=None, metavar="SECONDS")
    args = ap.parse_args()

    home = Path(args.officeace_home).expanduser()

    # ⛔ 跨机器确认闸门（1.6.0）：与 migrate.py 共用 migration_gate，堵住直接调用的旁路。
    # 入口脚本已确认时凭票据文件的 confirmed 标记放行，不重复提问。
    gate_rc = gate.enforce(home, args.install, args.confirm_local,
                           cooldown=args.gate_cooldown, source=str(args.source),
                           entry="migrate_workbuddy.py")
    if gate_rc is not None:
        return gate_rc

    src = Path(args.source).expanduser()
    if not src.is_dir():
        raise SystemExit(f"错误：目录不存在 {src}")

    pkgs = []
    if args.all:
        for p in sorted(src.iterdir()):
            if p.is_dir() and detect_pkg(p):
                pkgs.append(p)
    else:
        found = detect_pkg(src)
        if not found:
            raise SystemExit(f"错误：{src} 不是 WorkBuddy 专家包（缺 .codebuddy-plugin/plugin.json）")
        pkgs.append(found)

    total_experts = 0
    for pkg in pkgs:
        plan = migrate_pkg(pkg, home)
        kind = "专家团" if plan["team"] else "单专家"
        print(f"\n[{kind}] {plan['package']} v{plan['version']} → {len(plan['experts'])} 个专家"
              f"（分类 {plan['category']}）")
        # 评审 P1：dry-run 也要落 report.md（丢弃/需人工确认两栏），兑现 SKILL.md 承诺
        report_path = build_staging_report(pkg, plan, home)
        print(f"   报告：{report_path}")
        if not plan["experts"]:
            # 有 agents/ 却没有一个够格的专家：技能照搬，但用户在 OfficeAce 里找不到「专家」入口。
            # 不显式说破就会变成「迁移完成且可用」的伪成功（1.7.3 实测：a-share-analysis 7 个编排
            # agent、20 个技能，最终 0 专家）。
            print("   ⚠ 该包未产出任何专家：agents/*.md 缺少专家身份字段（expertId / 角色声明），"
                  "本次只按技能包迁移。若本意是装专家，请回源平台确认该包是否声明了专家身份。")
        for e in plan["experts"]:
            role = "主理人" if e["is_leader"] else ("成员" if e["is_team"] else "专家")
            print(f"   · [{role}] {e['display']}（@{e['display']}）expertId={e['expert_id']}"
                  f" 人设 {len(e['persona'])} 字 技能 {e['skills']}（依据 {e['skills_basis']}）")
        if plan["team"]:
            t = plan["team"]
            print(f"   团：{t['teamId']}｜{t['displayName']}｜主理人 {t['leaderExpertId']}｜成员 {len(t['members'])}")
        total_experts += len(plan["experts"])
        if args.install:
            written = install(pkg, plan, home, args)
            print(f"   写盘 {len(written)} 项")

    print(f"\n合计：{len(pkgs)} 个包 / {total_experts} 个专家")
    if not args.install:
        print("本次为预演（dry-run）：预演报告已落 ~/.office-claw/.staging/，未写注册。")
        print("先看 report.md 的「丢弃 / 需人工确认」两栏，逐条处理后再加 --install。")
        return 0
    print("已安装：专家卡 + catalog + breeds/roster + user-experts(+user-teams) + 技能注册四件套。")
    print("注册项改完即生效，无需重启；界面里技能列表没刷新时再重启一次 OfficeAce。")
    print("验收：python scripts/verify_install.py -q（静态）+ python scripts/check_runtime.py（应用侧）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
