#!/usr/bin/env python3
"""校验 OfficeAce 专家安装完整性（只读）。

用途：校验专家卡、技能目录、catalog/breeds/roster、capabilities.json 与 user-experts.json 的一致性。
参数：--home 数据目录（默认 ~/.office-claw）；--name 只校验指定专家；--json 以 JSON 输出。
返回值：退出码 0=全部通过，1=存在错误项。

检查十件事：
  1. experts/*.json 是否全部能解析，字段是否齐全（含 personality）
  2. 人设是否真的迁移了：personality 少于 200 字、或与 roleDescription 完全相同 → 判失败
  3. 专家引用的每个技能是否真的存在于 skills/<slug>/SKILL.md
  4. 专家头像 avatar 是否真的指向应用里存在的图片（否则 UI 显示破图/乱码）
  5. user-catalogs/catalog.json 与 experts/ 是否一一对应（有卡无注册 / 有注册无卡）
  6. 用户目录 breeds/roster 与专家卡是否一致，含运行配置（provider=relayclaw +
     providerProfileId/defaultModel 必须在本机 model.json 里真实存在）
  7. 权威技能注册表（应用目录 .office-claw/capabilities.json）是否登记了专家引用的技能
     —— 缺了运行时会报 "configured but not installed"
  8. users/<uid>/user-experts.json 是否包含**每一个**专家（含团队主理与成员），
     且 personality / 运行配置与专家卡一致 —— 这是 /api/experts 的唯一数据源
  9. 专家团：leaderExpertId 可解析、role=leader 有且只有一个、队级标量齐全、成员有 displayName
 10. 技能脚本引用是否为绝对路径且文件存在（团队会话 cwd 不在技能目录，相对路径必然失效）

用法：
    python verify_install.py
    python verify_install.py --home ~/.office-claw --name solution-presales
    python verify_install.py --app-root ~/OfficeAce -q
    python verify_install.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_contract as rc  # noqa: E402
from migrate_suite import active_user_dir, avatar_exists, avatar_quality, find_app_root  # noqa: E402

REQUIRED_EXPERT_KEYS = ("expertId", "name", "displayName", "nickname", "skills",
                        "roleDescription", "personality")

# 人设低于这个长度，说明只是把简介/一句话塞进了 personality（实测退化形态约 40 字）
MIN_PERSONA_CHARS = 200

# --quiet 折叠的逐专家明细（专家多时这类行会占满整屏，掩盖真正的检查结论）
DETAIL_RE = re.compile(r"(的 \d+ 个技能均就位|的技能已全部登记到 capabilities\.json)")


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _collect_ids(node):
    """递归收集 teams 结构里所有 id/agentId/lead 字段值。"""
    out = set()
    if isinstance(node, dict):
        for k in ("id", "agentId", "expertId", "lead", "family"):
            v = node.get(k)
            if isinstance(v, str):
                out.add(v)
        for v in node.values():
            out |= _collect_ids(v)
    elif isinstance(node, list):
        for v in node:
            out |= _collect_ids(v)
    return out


def verify(home: Path, only: str | None, app_root: Path | None = None) -> dict:
    res = {"home": str(home), "errors": [], "warnings": [], "ok": [], "experts": []}
    skills_dir = home / "skills"
    experts_dir = home / "experts"
    app_root = app_root or find_app_root(home)
    model_catalog = rc.model_catalog(home)
    if not experts_dir.is_dir():
        res["errors"].append(f"缺少 experts 目录：{experts_dir}")
        return res

    # 1+2 专家卡与技能
    cards = {}
    all_card_ids = set()  # 全量卡 id，供团队等全局一致性检查使用（不受 --only 过滤影响）
    for p in sorted(experts_dir.glob("*.json")):
        if ".bak" in p.name:
            continue
        data, err = load(p)
        if err:
            res["errors"].append(f"{p.name} JSON 解析失败：{err}")
            continue
        if data.get("expertId"):
            all_card_ids.add(data["expertId"])
        missing_keys = [k for k in REQUIRED_EXPERT_KEYS if not data.get(k)]
        if missing_keys:
            res["errors"].append(f"{p.name} 缺字段：{', '.join(missing_keys)}")
        name = data.get("name") or p.stem
        if only and name != only:
            continue
        cards[name] = data
        # 人设必须是完整正文：只写一句话时成员没有判据，输出会退化（实测四个成员人设同一句话）
        persona = data.get("personality") or ""
        if len(persona) < MIN_PERSONA_CHARS:
            res["errors"].append(
                f"专家 `{name}` 的 personality 只有 {len(persona)} 字（< {MIN_PERSONA_CHARS}），"
                f"像是把简介当人设写入了；应从 agents/*.md 取完整正文"
            )
        elif persona.strip() and persona.strip() == (data.get("roleDescription") or "").strip():
            res["errors"].append(f"专家 `{name}` 的 personality 与 roleDescription 完全相同（人设未迁移）")
        miss_skills = [s for s in (data.get("skills") or []) if not (skills_dir / s / "SKILL.md").exists()]
        if miss_skills:
            res["errors"].append(f"专家 `{name}` 引用的技能缺失：{', '.join(miss_skills)}")
        else:
            res["ok"].append(f"专家 `{name}` 的 {len(data.get('skills') or [])} 个技能均就位")
        # 头像：卡片 avatar 会原样进 <img src>，文件缺失时 UI 显示 alt 文本（表现为乱码）
        av = data.get("avatar")
        if av and not avatar_exists(app_root, av):
            res["errors"].append(
                f"专家 `{name}` 的头像文件不存在：{av}（UI 会显示破图/乱码，"
                f"执行 `python scripts/repair_avatars.py --fix` 修复）"
            )
        elif av and str(av).startswith("/avatars/"):
            disk = Path(app_root or "") / "packages/green-package/web/dist/avatars" / str(av)[len("/avatars/"):]
            if avatar_quality(disk) == "placeholder":
                res["warnings"].append(
                    f"专家 `{name}` 的头像只是纯色占位图（{av}），圆形头像里会显示成色块；"
                    f"建议按职能生成正式头像后用 `python scripts/set_avatar.py` 换上"
                )
        res["experts"].append(
            {
                "name": name,
                "expertId": data.get("expertId"),
                "displayName": data.get("displayName"),
                "skills": data.get("skills"),
                "avatar": av,
                "missing_skills": miss_skills,
            }
        )

    # 3 catalog.json 对应
    cat = home / "user-catalogs" / "catalog.json"
    if cat.exists():
        data, err = load(cat)
        if err:
            res["errors"].append(f"catalog.json 解析失败：{err}")
        else:
            reg_names = {e.get("name") for e in data.get("experts", [])}
            card_names = set(cards)
            if only:
                reg_names = {n for n in reg_names if n == only}
            only_card = card_names - reg_names
            only_reg = reg_names - card_names
            if only_card:
                res["errors"].append(f"有专家卡但未在 catalog.json 注册：{', '.join(sorted(only_card))}")
            if only_reg:
                res["errors"].append(f"catalog.json 有注册但无专家卡：{', '.join(sorted(only_reg))}")
            if not only_card and not only_reg:
                res["ok"].append("catalog.json 与 experts/ 一一对应")

            # id 一致性：catalog.agentId 与 expertId 在历史数据里本就允许不同（两套创建链路），
            # 真正的约束是 breeds.id 必须等于 expertId —— 这条在第 4 步校验。
            id_by_name = {e.get("name"): e.get("agentId") for e in data.get("experts", [])}
            mismatched = [
                n for n, c in cards.items()
                if n in id_by_name and id_by_name[n] != c.get("expertId")
            ]
            if mismatched:
                res["warnings"].append(
                    f"catalog.agentId 与 experts.expertId 不同（历史数据常见，不阻塞）：{', '.join(sorted(mismatched))}"
                )
    else:
        res["warnings"].append("未找到 user-catalogs/catalog.json，专家可能不会出现在列表")

    # 4 用户目录 breeds/roster
    uc = None
    if (home / "user-catalogs").is_dir():
        cands = [
            p
            for p in (home / "user-catalogs").glob("*.json")
            if ".bak" not in p.name and p.name != "catalog.json"
        ]
        if cands:
            def score(p: Path):
                d, _ = load(p)
                return len((d or {}).get("breeds") or []) if isinstance(d, dict) else -1

            uc = max(cands, key=lambda p: (score(p), p.stat().st_mtime))
    if uc:
        data, err = load(uc)
        if err:
            res["errors"].append(f"用户目录 {uc.name} 解析失败：{err}")
        else:
            breeds = {b.get("name"): b for b in data.get("breeds", [])}
            roster = data.get("roster") or {}
            # roster 必须是 dict（id → 条目）。实测手写登记用列表推导式会把 dict 压成 list，
            # 此后 roster.get() 直接 AttributeError 崩溃——这里显式报错而不是跟着崩
            if not isinstance(roster, dict):
                res["errors"].append(
                    f"用户目录 {uc.name} 的 roster 是 {type(roster).__name__}（应为 dict）。"
                    "实测手写 JSON 变换会把它压坏；登记新专家请走 runtime_contract 构造器"
                )
                roster = {}
            for n in cards:
                b = breeds.get(n)
                if not b:
                    res["errors"].append(f"专家 `{n}` 未出现在用户目录 breeds 中（列表中可能不显示）")
                    continue
                if b.get("id") != cards[n].get("expertId"):
                    res["errors"].append(
                        f"专家 `{n}` 的 breeds.id（{b.get('id')}）与专家卡 expertId（{cards[n].get('expertId')}）不一致，编排与 @ 可能失效"
                    )
                if b.get("id") not in roster:
                    res["errors"].append(f"专家 `{n}` 的 breeds.id 未出现在 roster 中")
                variant = (b.get("variants") or [{}])[0]
                if variant.get("skills") != (cards[n].get("skills") or []):
                    res["warnings"].append(
                        f"专家 `{n}` 的 variants[0].skills 与专家卡不一致：{variant.get('skills')} vs {cards[n].get('skills')}"
                    )
                # 运行配置：provider 必须是 relayclaw（否则专家会从 /api/agents 整批消失）；
                # profile/model 必须是本机 model.json 里真实存在的组合，否则召唤即鉴权失败
                if variant.get("provider") != "relayclaw":
                    res["errors"].append(
                        f"专家 `{n}` 的 variant.provider={variant.get('provider')!r}，必须是 'relayclaw'"
                    )
                prof, mod = variant.get("providerProfileId"), variant.get("defaultModel")
                if mod not in model_catalog.get(prof, []):
                    res["errors"].append(
                        f"专家 `{n}` 的运行配置 {prof}/{mod} 不在本机 model.json 中（召唤会鉴权失败）；"
                        f"可用组合：{ {k: v[:3] for k, v in model_catalog.items()} }"
                    )
                entry = roster.get(b.get("id")) or {}
                if entry.get("provider") != "relayclaw" or entry.get("defaultModel") != mod:
                    res["errors"].append(
                        f"专家 `{n}` 的 roster 条目缺运行配置（provider/providerProfileId/defaultModel），"
                        f"团队运行时解析不到模型"
                    )
                if b.get("roleDescription") and not entry.get("evaluation"):
                    res["warnings"].append(f"专家 `{n}` 的 roster.evaluation 为空，团队任务卡片会没有角色说明")
            if not any("未出现在用户目录" in e for e in res["errors"]):
                res["ok"].append(f"用户目录 breeds/roster 覆盖全部 {len(cards)} 个专家")
    else:
        res["warnings"].append("未找到用户目录文件，无法校验 breeds/roster")

    # 5 权威技能注册表 capabilities.json + custom 技能持久化源（应用安装目录 .office-claw/ 下）
    if app_root is None:
        for cand in (home.parent / "OfficeAce", home / "OfficeAce"):
            if (cand / ".office-claw" / "capabilities.json").is_file():
                app_root = cand
                break
    if app_root:
        caps_data, err = load(app_root / ".office-claw" / "capabilities.json")
        if err:
            res["errors"].append(f"capabilities.json 解析失败：{err}")
        else:
            registered = {
                c.get("id") for c in caps_data.get("capabilities", []) if c.get("type") == "skill"
            }
            for n, card in cards.items():
                miss = [s for s in (card.get("skills") or []) if s not in registered]
                if miss:
                    res["errors"].append(
                        f"专家 `{n}` 的技能未登记到 capabilities.json（运行时报 configured but not installed）：{', '.join(miss)}"
                    )
                else:
                    res["ok"].append(f"专家 `{n}` 的技能已全部登记到 capabilities.json")
        # 重启再生源：应用目录 .office-claw/skills/ 目录 + installed-skills.json。
        # 缺这两处，重启后 capabilities.json 再生时 custom 条目会被刷掉。
        store = app_root / ".office-claw" / "skills"
        inst = app_root / ".office-claw" / "installed-skills.json"
        inst_ids = set()
        if inst.is_file():
            inst_data, err = load(inst)
            if not err and isinstance(inst_data, dict):
                inst_ids = set(inst_data.get("skills") or {})
        all_skills = sorted({s for c in cards.values() for s in (c.get("skills") or [])})
        miss_dir = [s for s in all_skills if not (store / s / "SKILL.md").exists()]
        miss_reg = [s for s in all_skills if s not in inst_ids]
        if miss_dir:
            res["errors"].append(f"技能目录不在应用目录存储 {store}（重启后会失效）：{', '.join(miss_dir)}")
        else:
            res["ok"].append(f"{len(all_skills)} 个技能目录均已进入应用目录存储（重启再生不丢）")
        if miss_reg:
            res["errors"].append(f"技能未登记到应用目录 installed-skills.json（重启后会失效）：{', '.join(miss_reg)}")
        else:
            res["ok"].append("技能均已登记到应用目录 installed-skills.json")
        # 1.6.0 镜像一致性：应用读取的是安装目录镜像；数据目录改动没同步过去时，
        # 用户以为改好了、应用跑的还是旧版（实测排查三轮才定位的一次事故）
        try:
            import mirror_sync
            drift = [r["slug"] for r in mirror_sync.scan(home, app_root, all_skills)
                     if r["status"] not in ("same",)]
            if drift:
                res["warnings"].append(
                    f"技能在数据目录与应用镜像内容不一致（应用读镜像，最近改动可能未生效）："
                    f"{', '.join(drift)}；执行 `python ~/.office-claw/skills/huawei-cloud-officeace-expert-migration/scripts/mirror_sync.py --fix` 同步"
                )
        except Exception:  # noqa: BLE001  镜像比对是增值检查，失败不阻塞十项主校验
            pass
    else:
        res["warnings"].append("未找到应用安装目录的 .office-claw/capabilities.json，无法校验技能注册表")

    # 6 用户级专家列表 user-experts.json（UI 专家列表数据源；按用户隔离）
    # 活跃用户以 connector-owner.local.json 的 ownerUserId 为准；猜 mtime 在多账号机器上会查错目录
    users_dir = home / "users"
    act = active_user_dir(home)
    ue = (act / "user-experts.json") if act else None
    if ue is None or not ue.is_file():
        ue_files = [
            p for p in users_dir.glob("*/user-experts.json") if ".bak" not in p.name
        ] if users_dir.is_dir() else []
        ue = max(ue_files, key=lambda p: p.stat().st_mtime) if ue_files else None
    if ue and ue.is_file():
        data, err = load(ue)
        if err:
            res["errors"].append(f"{ue} 解析失败：{err}")
        else:
            # /api/experts 的唯一数据源就是本文件。团队主理人与成员**都必须**登记在这里：
            # 只写 user-teams.json 时，团队运行时解析不到主理人（实测报「主理人出错」，
            # 成员档案回落成英文 id）。这里不接受「团队型专家不進专家列表」的例外。
            entries = {e.get("expertId"): e for e in data.get("experts", [])}
            missing = [n for n, c in cards.items() if c.get("expertId") not in entries]
            for n in missing:
                res["errors"].append(
                    f"专家 `{n}` 不在活跃用户 {ue.parent.name[:16]}…/user-experts.json 中"
                    f"（不会出现在专家列表，专家团也无法解析该角色）"
                )
            # 卡片与列表条目必须同步：只改一处会出现「卡上有人设、列表里还是简介」
            for n, c in cards.items():
                e = entries.get(c.get("expertId"))
                if not e:
                    continue
                if (e.get("personality") or "") != (c.get("personality") or ""):
                    res["errors"].append(f"专家 `{n}` 的 user-experts.personality 与专家卡不一致（列表显示会退化）")
                if e.get("defaultModel") != c.get("defaultModel") or \
                        e.get("providerProfileId") != c.get("providerProfileId"):
                    res["errors"].append(
                        f"专家 `{n}` 的 user-experts 运行配置（{e.get('providerProfileId')}/{e.get('defaultModel')}）"
                        f"与专家卡（{c.get('providerProfileId')}/{c.get('defaultModel')}）不一致"
                    )
            if not missing:
                res["ok"].append(f"活跃用户 user-experts.json 已包含全部 {len(cards)} 个迁移专家（含团队主理人）")
    else:
        res["warnings"].append("未找到 users/<uid>/user-experts.json，专家不会出现在 UI 专家列表")

    # 7 专家团（user-teams.json）：主理人与成员必须都有专家卡
    if ue and ue.is_file():
        tp = ue.parent / "user-teams.json"
        if tp.is_file():
            tdata, terr = load(tp)
            if terr:
                res["errors"].append(f"user-teams.json 解析失败：{terr}")
            else:
                team_list = tdata.get("teams") or []
                card_ids = all_card_ids  # 团队成员是全局注册，必须与全量专家卡比对；
                # 用被 --only 过滤的 cards 会把无关团队成员全部误判成缺卡（1.4.1 修复）
                bad = []
                for t in team_list:
                    ids = [m.get("expertId") for m in (t.get("members") or [])]
                    lead = t.get("leaderExpertId")
                    if not lead:
                        bad.append(f"{t.get('teamId')} 缺 leaderExpertId")
                    elif lead not in ids:
                        bad.append(f"{t.get('teamId')} 的主理人 {lead} 不在成员列表")
                    for eid in ids:
                        if eid and eid not in card_ids:
                            bad.append(f"{t.get('teamId')} 的成员 {eid} 没有专家卡")
                    # 队级标量：省略会回退应用内置默认值，迁移前后行为不一致
                    miss_scalar = [k for k in rc.TEAM_SCALARS if k not in t]
                    if miss_scalar:
                        bad.append(f"{t.get('teamId')} 缺队级标量：{', '.join(miss_scalar)}")
                    # 成员展示名缺失时团队任务卡片显示英文 id
                    nameless = [m.get("expertId") for m in (t.get("members") or [])
                                if not m.get("displayName")]
                    if nameless:
                        res["warnings"].append(
                            f"{t.get('teamId')} 的成员缺 displayName（任务卡片会显示英文 id）：{nameless}"
                        )
                    leaders = [m.get("expertId") for m in (t.get("members") or [])
                               if m.get("role") == "leader"]
                    if len(leaders) != 1:
                        bad.append(f"{t.get('teamId')} 的主理人角色数量为 {len(leaders)}（应为 1）")
                    elif lead and leaders[0] != lead:
                        bad.append(f"{t.get('teamId')} 的 role=leader（{leaders[0]}）与 leaderExpertId（{lead}）不一致")
                for b in bad:
                    res["errors"].append(f"团队注册异常：{b}")
                if not bad:
                    res["ok"].append(f"专家团 {len(team_list)} 个，主理人与成员均已有专家卡")

    # 8 技能脚本引用：必须绝对路径且真实存在
    # 团队会话的 cwd 是 team-workspace，其中 skills/ 是空目录，相对路径必然找不到文件；
    # 模型会因此自己重写算法，造成口径漂移（实测成本 803,520 vs 应为 836,294.40）
    all_scripts = sorted({s for c in cards.values() for s in (c.get("skills") or [])})
    rel_refs, dead_refs, doc_refs, scripted = [], [], [], 0
    for sk in all_scripts:
        md = skills_dir / sk / "SKILL.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        has_scripts = bool(rc.skill_scripts(skills_dir / sk))
        if has_scripts:
            scripted += 1
        for m in re.finditer(r'python(?:3)?\s+"?((?:\./)?scripts/[A-Za-z0-9_./-]+\.(?:py|js|mjs|sh))"?', text):
            # 技能自身带 scripts/ 时，相对引用运行时必然失败（报错）；
            # 无 scripts 目录的技能里出现相对引用多为文档举例（降级为提示，避免误伤说明文字）
            (rel_refs if has_scripts else doc_refs).append(f"{sk}: {m.group(1)}")
        for m in re.finditer(r'python(?:3)?\s+"([A-Za-z]:[\\/][^"]+\.(?:py|js|mjs|sh))"', text):
            if not Path(m.group(1)).is_file():
                dead_refs.append(f"{sk}: {m.group(1)}")
    if rel_refs:
        res["errors"].append(
            f"技能文档仍用相对脚本路径（运行时必然找不到文件，模型会自行重写算法）：{rel_refs[:5]}"
        )
    if doc_refs:
        res["warnings"].append(
            f"技能文档提到相对脚本路径，但该技能无 scripts 目录（多为文档举例，仅提示）：{doc_refs[:5]}"
        )
    if dead_refs:
        res["errors"].append(f"技能文档里的脚本绝对路径不存在：{dead_refs[:5]}")
    if not rel_refs and not dead_refs and scripted:
        res["ok"].append(f"{scripted} 个带脚本的技能均已改成绝对路径且文件存在")

    # 9 技能资源引用：SKILL.md 点名的 references/、scripts/、assets/ 必须可解析到
    # 第 8 项只查 `python scripts/x.py` 这种**调用**，漏掉「读 references/x.md」这类**引用**；
    # 1.7.3 实测技能资源整包丢失（源 10 个文件只剩 SKILL.md），9 处引用全指空，
    # 旧版验收仍报「通过」——这一项就是补这个盲区。
    # 跨技能引用不算缺失：人设技能常写「按 references/taxonomy.md 分类」，文件其实在同包的
    # 另一个技能里；该专家同时挂载了那个技能，运行时能解析到（如 dumate-test-rich →
    # inspection-analytics）。只看单技能目录会把它误判为资源丢失。
    skill_dirs = {p.name: p for p in skills_dir.iterdir() if p.is_dir()} if skills_dir.is_dir() else {}
    cross_ok: set[str] = set()
    for c in cards.values():
        owned = [s for s in (c.get("skills") or []) if s in skill_dirs]
        for sk in owned:
            for rel in rc.missing_resource_refs(skill_dirs[sk]):
                if any((skill_dirs[o] / rel).is_file() for o in owned if o != sk):
                    cross_ok.add(f"{sk}:{rel}")
    missing_res: list[str] = []
    cross_res: list[str] = []
    for sk in all_scripts:
        target = skill_dirs.get(sk) or (skills_dir / sk)
        for rel in rc.missing_resource_refs(target):
            key = f"{sk}:{rel}"
            (cross_res if key in cross_ok else missing_res).append(key)
    if missing_res:
        res["errors"].append(
            f"技能文档引用的资源文件不存在（专家读不到知识库、脚本跑不起来）：{missing_res[:6]}"
            + (f"（共 {len(missing_res)} 处）" if len(missing_res) > 6 else "")
        )
    if cross_res:
        res["warnings"].append(
            f"引用指向同包其他技能的资源（该专家已挂载对应技能，不算缺失）：{cross_res[:5]}"
        )
    if not missing_res and all_scripts:
        res["ok"].append(
            f"{len(all_scripts)} 个专家技能引用的 references/scripts/assets 均可解析"
        )

    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="校验 OfficeAce 专家安装完整性")
    ap.add_argument("--home", default="~/.office-claw")
    ap.add_argument("--name", default=None)
    ap.add_argument("--app-root", default=None, help="OfficeAce 应用安装根目录（自动探测失败时指定）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="折叠逐专家的技能明细，只看检查项汇总（专家多时便于一眼判定）")
    args = ap.parse_args()

    home = Path(args.home).expanduser()
    if not home.is_dir():
        print(f"错误：目录不存在 {home}", file=sys.stderr)
        return 2
    app_root = Path(args.app_root).expanduser() if args.app_root else None
    res = verify(home, args.name, app_root)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"OfficeAce 数据目录：{res['home']}")
        detail = 0
        for x in res["ok"]:
            if args.quiet and DETAIL_RE.search(x):
                detail += 1
                continue
            print(f"  ✓ {x}")
        if detail:
            print(f"  ✓ 逐专家技能明细 {detail} 条均就位（技能目录 ↔ capabilities 双向一致）")
        for x in res["warnings"]:
            print(f"  ! {x}")
        for x in res["errors"]:
            print(f"  ✗ {x}")
        print()
        print("结论：" + ("通过" if not res["errors"] else f"发现 {len(res['errors'])} 个问题"))
    return 0 if not res["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
