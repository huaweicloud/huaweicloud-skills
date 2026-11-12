#!/usr/bin/env python3
"""huawei-cloud-officeace-expert-migration 最小回归测试套件（1.6.0）。

覆盖四个踩过真实事故的坑 + 两个新增机制的单元行为：

  1. 跨机器闸门：发票据 / 无效票据 / 冷却拒绝 / 冷却放行 / 入口确认透传与过期 /
     环境变量覆盖 / dry-run 不拦。
  2. roster dict 结构：构造器产出 dict 且带运行配置；roster 被手写 JSON 变换压成
     list 时 verify_install 必须显式报错（1.4.1 实测崩溃事故）。
  3. verify_install 单包过滤不泄漏：--name 单包模式下，团队等全局一致性检查用
     全量专家卡比对，不得把无关团队成员误判「没有专家卡」（1.4.1 实测 13 条假 ✗）。
  4. 七处注册完整性：跑一次真实迁移（合成团队包 + 临时数据目录），逐处断言
     专家卡 / catalog / breeds+roster / user-experts / user-teams / 应用镜像技能 /
     installed-skills / capabilities 全部就位，且 verify_install 十项全绿。
  5. 镜像同步：漂移检测与 --fix 修复。
  6. 迁移器无未定义名字（log 事故：调用了不存在的助手函数）。

运行：python tests/run_regression_tests.py   （无需 pytest，标准库 unittest）
"""

from __future__ import annotations

import io
import json
import random
import struct
import sys
import tempfile
import time
import unittest
import zlib
from contextlib import redirect_stderr
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import migration_gate as gate  # noqa: E402
import mirror_sync  # noqa: E402
import runtime_contract as rc  # noqa: E402
import verify_install  # noqa: E402

PROF, MDL = "prof-x", "model-x"


def read_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_png(seed: int = 0, w: int = 64, h: int = 64) -> bytes:
    """合成一张 qualify（≥64px 且 ≥2KB）的真 PNG，供头像链路测试。"""
    rnd = random.Random(seed)
    raw = b"".join(b"\x00" + bytes(rnd.randrange(256) for _ in range(w * 3)) for _ in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- 闸门


class TestGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="esm-gate-")
        self.home = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def _run(self, **kw):
        err = io.StringIO()
        with redirect_stderr(err):
            rc_ = gate.enforce(self.home, **kw)
        return rc_, err.getvalue()

    def test_dry_run_not_blocked(self):
        rc_, _ = self._run(install=False)
        self.assertIsNone(rc_)

    def test_blocks_without_ticket_and_issues_nonce(self):
        rc_, err = self._run(install=True)
        self.assertEqual(rc_, 4)
        self.assertIn("GATE-CROSS-MACHINE", err)
        g = read_json(self.home / ".migration-gate.json")
        self.assertTrue(g.get("nonce"))
        self.assertTrue(g.get("sid"))  # 会话标识：并发会话票据互不误用

    def test_rejects_wrong_ticket(self):
        gate.issue(self.home, "x")
        rc_, err = self._run(install=True, confirm_local="deadbeef0000")
        self.assertEqual(rc_, 4)
        self.assertIn("票据无效", err)

    def test_rejects_fast_confirm(self):
        nonce, _ = gate.issue(self.home, "x")
        rc_, err = self._run(install=True, confirm_local=nonce, cooldown=90)
        self.assertEqual(rc_, 4)
        self.assertIn("确认时间过短", err)

    def test_accepts_after_cooldown_and_marks_confirmed(self):
        nonce, _ = gate.issue(self.home, "x")
        p = self.home / ".migration-gate.json"
        g = read_json(p)
        g["ts"] -= 91  # 模拟冷却已过
        write_json(p, g)
        rc_, _ = self._run(install=True, confirm_local=nonce, cooldown=90)
        self.assertIsNone(rc_)
        self.assertTrue(read_json(p).get("confirmed"))

    def test_passthrough_for_entry_confirmed_and_expiry(self):
        p = self.home / ".migration-gate.json"
        write_json(p, {"confirmed": True, "confirmedAt": time.time()})
        rc_, _ = self._run(install=True)  # 入口已确认：子迁移器透传放行
        self.assertIsNone(rc_)
        g = read_json(p)
        g["confirmedAt"] -= 601  # 窗口过期：重新拦截，不留永久通行证
        write_json(p, g)
        rc_, _ = self._run(install=True)
        self.assertEqual(rc_, 4)

    def test_cooldown_env_override(self):
        nonce, _ = gate.issue(self.home, "x")
        os_val = __import__("os").environ
        os_val["ESM_GATE_COOLDOWN"] = "0"
        try:
            rc_, _ = self._run(install=True, confirm_local=nonce)
            self.assertIsNone(rc_)
        finally:
            os_val.pop("ESM_GATE_COOLDOWN", None)


# ---------------------------------------------------------------- 公共夹具


def build_home(root: Path, roster_as_list: bool = False):
    """构造一个通过 verify 十项检查的最小数据目录（两位专家 + 一条团队）。"""
    home, app = root / "home", root / "app"
    persona = "人设正文，包含判据、输出格式与工作边界。" * 15
    for s in ("sk-a", "sk-b"):
        md = f"---\nname: {s}\ndescription: 测试技能\n---\n\n# {s}\n正文\n"
        (home / "skills" / s).mkdir(parents=True)
        (home / "skills" / s / "SKILL.md").write_text(md, encoding="utf-8")
        (app / ".office-claw" / "skills" / s).mkdir(parents=True)
        (app / ".office-claw" / "skills" / s / "SKILL.md").write_text(md, encoding="utf-8")
    write_json(app / ".office-claw" / "capabilities.json",
               {"capabilities": [{"id": "sk-a", "type": "skill"}, {"id": "sk-b", "type": "skill"}]})
    for sp in (app / ".office-claw" / "installed-skills.json",
               home / ".office-claw" / "installed-skills.json"):
        write_json(sp, {"skills": {"sk-a": {"name": "sk-a"}, "sk-b": {"name": "sk-b"}}})
    write_json(home / "model.json", {PROF: [{"id": MDL}]})
    write_json(home / "connector-owner.local.json", {"ownerUserId": "u1"})
    (home / "users" / "u1").mkdir(parents=True)

    ids = {"card-a": "expert-a-aaaaaaaa", "card-b": "expert-b-bbbbbbbb"}
    skills = {"card-a": ["sk-a"], "card-b": ["sk-b"]}
    for name, eid in ids.items():
        write_json(home / "experts" / f"{name}.json", {
            "expertId": eid, "agentId": eid, "name": name, "displayName": name,
            "nickname": name, "avatar": "", "category": "business",
            "mentionPatterns": [f"@{name}"], "roleDescription": f"{name} 的角色说明",
            "personality": persona, "strengths": [], "skills": skills[name],
            "visibility": "private", "creationSource": "user",
            "defaultModel": MDL, "providerProfileId": PROF, "agent_created": True,
        })
    write_json(home / "user-catalogs" / "catalog.json",
               {"experts": [{"name": n, "agentId": e} for n, e in ids.items()]})
    breeds = [{
        "name": n, "id": e,
        "variants": [{"skills": skills[n], "provider": "relayclaw",
                      "providerProfileId": PROF, "defaultModel": MDL}],
        "roleDescription": f"{n} 的角色说明",
    } for n, e in ids.items()]
    roster = {e: rc.roster_entry(e, f"{n} 的角色说明", PROF, MDL, False) for n, e in ids.items()}
    if roster_as_list:
        roster = list(roster.values())  # 复现 1.4.1 的手写登记事故
    write_json(home / "user-catalogs" / "u1.json", {"breeds": breeds, "roster": roster})
    ue = {"experts": [
        rc.user_experts_entry(e, n, "", "business", f"{n} 的角色说明", persona,
                              skills[n], PROF, MDL) for n, e in ids.items()]}
    write_json(home / "users" / "u1" / "user-experts.json", ue)
    write_json(home / "users" / "u1" / "user-teams.json", {"teams": [{
        "teamId": "wb-team-t", "displayName": "测试团",
        "members": [{"expertId": ids["card-a"], "role": "leader", "displayName": "card-a"},
                    {"expertId": ids["card-b"], "role": "teammate", "displayName": "card-b"}],
        "leaderExpertId": ids["card-a"], **rc.team_scalars(),
    }]})
    return home, app


# ---------------------------------------------------------------- 注册结构


class TestRosterDict(unittest.TestCase):
    def test_roster_entry_is_dict_with_runtime_fields(self):
        e = rc.roster_entry("expert-x-1234abcd", "评测", PROF, MDL, False)
        self.assertIsInstance(e, dict)
        for k in ("family", "roles", "lead", "available", "evaluation",
                  "provider", "providerProfileId", "defaultModel"):
            self.assertIn(k, e)
        self.assertEqual(e["provider"], "relayclaw")

    def test_verify_flags_roster_crushed_to_list(self):
        with tempfile.TemporaryDirectory(prefix="esm-roster-") as d:
            home, app = build_home(Path(d), roster_as_list=True)
            res = verify_install.verify(home, None, app)
            self.assertTrue(any("roster" in e and "dict" in e for e in res["errors"]),
                            res["errors"])


class TestSinglePackageNoLeak(unittest.TestCase):
    """1.4.1 回归：--name 单包模式下团队检查用全量卡比对，不误判无关成员缺卡。"""

    def test_only_filter_does_not_leak_team_check(self):
        with tempfile.TemporaryDirectory(prefix="esm-leak-") as d:
            home, app = build_home(Path(d))
            res = verify_install.verify(home, "card-a", app)
            self.assertFalse(any("没有专家卡" in e for e in res["errors"]), res["errors"])

    def test_full_check_passes(self):
        with tempfile.TemporaryDirectory(prefix="esm-full-") as d:
            home, app = build_home(Path(d))
            res = verify_install.verify(home, None, app)
            self.assertEqual(res["errors"], [], res["errors"])


# ---------------------------------------------------------------- 七处注册


class TestSevenRegistrations(unittest.TestCase):
    def test_team_package_installs_everywhere(self):
        with tempfile.TemporaryDirectory(prefix="esm-reg7-") as d:
            root = Path(d)
            home, app = root / "home", root / "app"
            # 数据目录前置条件：模型目录 / 活跃用户 / 用户目录 / 技能注册存储 / 闸门已确认
            write_json(home / "model.json", {"huawei-maas": [{"id": "deepseek-v4.1-flash"}]})
            write_json(home / "connector-owner.local.json", {"ownerUserId": "u1"})
            (home / "users" / "u1").mkdir(parents=True)
            write_json(home / "user-catalogs" / "u1.json", {"breeds": [], "roster": {}})
            for sp in (app / ".office-claw" / "installed-skills.json",
                       home / ".office-claw" / "installed-skills.json"):
                write_json(sp, {"skills": {}})
            write_json(app / ".office-claw" / "capabilities.json", {"capabilities": []})
            (app / "packages" / "green-package" / "web" / "dist" / "avatars").mkdir(parents=True)
            # 测试以「已确认」身份运行：写新鲜 confirmed 标记通过闸门透传
            write_json(home / ".migration-gate.json",
                       {"confirmed": True, "confirmedAt": time.time()})

            # 合成 WorkBuddy 团队包：主理人 + 成员 + 包级技能 + 头像
            pkg = root / "ztest-squad"
            manifest = {
                "name": "ztest-squad", "version": "1.0.0",
                "displayName": {"zh": "回归测试小队"},
                "displayDescription": {"zh": "用于回归测试的团队包"},
                "expertType": "team",
                "teamInfo": {"leadAgent": "ztest-lead",
                             "memberAgents": ["ztest-lead", "ztest-member"]},
                "agents": ["agents/ztest-lead.md", "agents/ztest-member.md"],
            }
            write_json(pkg / ".codebuddy-plugin" / "plugin.json", manifest)
            persona = "你是团队的一员，负责按分工交付自己的部分并给出判据。" * 10
            for agent, prof in (("ztest-lead", "团队主理人"), ("ztest-member", "数据分析成员")):
                md = pkg / "agents" / f"{agent}.md"
                md.parent.mkdir(parents=True, exist_ok=True)
                md.write_text(
                    f"---\nname: {agent}\ndisplayName:\n  zh: {agent}\n"
                    f"profession:\n  zh: {prof}\n---\n\n{persona}\n"
                    f"正文点名使用 calc 技能完成计算。\n", encoding="utf-8")
            sk = pkg / "skills" / "calc"
            sk.mkdir(parents=True)
            (sk / "SKILL.md").write_text(
                "---\nname: calc\ndescription: 计算技能\n---\n\n# calc\n负责算数字。\n",
                encoding="utf-8")
            for i, img in enumerate(("ztest-lead.png", "ztest-member.png", "team.png")):
                (pkg / "avatars").mkdir(exist_ok=True)
                (pkg / "avatars" / img).write_bytes(make_png(seed=i))

            import migrate_workbuddy as mw
            saved = sys.argv
            sys.argv = ["migrate_workbuddy.py", "--source", str(pkg), "--install",
                        "--officeace-home", str(home), "--app-root", str(app)]
            try:
                rc_ = mw.main()
            finally:
                sys.argv = saved
            self.assertEqual(rc_, 0)

            # ① 专家卡 ② catalog ③ breeds+roster(dict) ④ user-experts ⑤ user-teams
            for name in ("ztest-lead", "ztest-member"):
                self.assertIn("expertId", read_json(home / "experts" / f"{name}.json"), name)
            cat = read_json(home / "user-catalogs" / "catalog.json")
            self.assertTrue({"ztest-lead", "ztest-member"} <= {e["name"] for e in cat["experts"]})
            uc = read_json(home / "user-catalogs" / "u1.json")
            self.assertTrue({"ztest-lead", "ztest-member"} <= {b["name"] for b in uc["breeds"]})
            self.assertIsInstance(uc["roster"], dict)
            self.assertEqual(len(uc["roster"]), 2)
            ue = read_json(home / "users" / "u1" / "user-experts.json")
            self.assertEqual(len(ue["experts"]), 2)
            ut = read_json(home / "users" / "u1" / "user-teams.json")
            self.assertEqual(ut["teams"][0]["teamId"], "wb-team-ztest-squad")
            # ⑥ 应用镜像技能 ⑦ installed-skills ⑧ capabilities
            for sid in ("ztest-lead", "ztest-member", "calc"):
                self.assertTrue((app / ".office-claw" / "skills" / sid / "SKILL.md").is_file(), sid)
            inst = read_json(app / ".office-claw" / "installed-skills.json")
            self.assertTrue({"ztest-lead", "ztest-member", "calc"} <= set(inst["skills"]))
            caps = read_json(app / ".office-claw" / "capabilities.json")
            self.assertTrue({"ztest-lead", "ztest-member", "calc"}
                            <= {c["id"] for c in caps["capabilities"]})
            # 终检：verify 十项全绿
            res = verify_install.verify(home, None, app)
            self.assertEqual(res["errors"], [], res["errors"])


# ---------------------------------------------------------------- 镜像同步


class TestMirrorSync(unittest.TestCase):
    def test_detect_and_fix_drift(self):
        with tempfile.TemporaryDirectory(prefix="esm-mirror-") as d:
            home, app = Path(d) / "home", Path(d) / "app"
            (home / "skills" / "sk1").mkdir(parents=True)
            (home / "skills" / "sk1" / "SKILL.md").write_text(
                "---\nname: sk1\ndescription: v2\n---\n新版\n", encoding="utf-8")
            m = app / ".office-claw" / "skills" / "sk1"
            m.mkdir(parents=True)
            (m / "SKILL.md").write_text("---\nname: sk1\ndescription: v1\n---\n旧版\n",
                                        encoding="utf-8")
            self.assertEqual([r["status"] for r in mirror_sync.scan(home, app)], ["drift"])
            mirror_sync.fix(home, app)
            self.assertEqual([r["status"] for r in mirror_sync.scan(home, app)], ["same"])

    def test_copy_new_skill_to_mirror(self):
        with tempfile.TemporaryDirectory(prefix="esm-mirror2-") as d:
            home, app = Path(d) / "home", Path(d) / "app"
            (home / "skills" / "new-skill").mkdir(parents=True)
            (home / "skills" / "new-skill" / "SKILL.md").write_text("x\n", encoding="utf-8")
            self.assertEqual([r["status"] for r in mirror_sync.scan(home, app)], ["copy-needed"])
            mirror_sync.fix(home, app)
            self.assertTrue((app / ".office-claw" / "skills" / "new-skill" / "SKILL.md").is_file())


class TestRelRefDowngrade(unittest.TestCase):
    """技能无 scripts/ 目录时，文档里的相对脚本引用是举例不是缺陷，应降级为警告。"""

    def test_doc_mention_without_scripts_is_warning(self):
        with tempfile.TemporaryDirectory(prefix="esm-relref-") as d:
            home, app = build_home(Path(d))
            md = home / "skills" / "sk-a" / "SKILL.md"
            md.write_text(md.read_text(encoding="utf-8")
                          + "\n可执行 python scripts/tool.py 查看示例。\n", encoding="utf-8")
            (app / ".office-claw" / "skills" / "sk-a" / "SKILL.md").write_text(
                md.read_text(encoding="utf-8"), encoding="utf-8")
            res = verify_install.verify(home, None, app)
            self.assertFalse(any("相对脚本路径" in e for e in res["errors"]), res["errors"])
            self.assertTrue(any("相对脚本路径" in w for w in res["warnings"]), res["warnings"])


class TestMigratePkgHome(unittest.TestCase):
    """1.6.1 回归：migrate_pkg 的 ID 复用必须跟随传入的 home，不能写死默认目录。"""

    def test_id_reuse_follows_given_home(self):
        with tempfile.TemporaryDirectory(prefix="esm-home-") as d:
            root = Path(d)
            pkg = root / "zhome-pkg"
            write_json(pkg / ".codebuddy-plugin" / "plugin.json", {
                "name": "zhome-pkg", "version": "2.0.0",
                "displayName": {"zh": "Home 测试"},
                "agents": ["agents/zhome-a.md"],
            })
            persona = "单专家人设正文，包含判据、输出格式与工作边界。" * 10
            md = pkg / "agents" / "zhome-a.md"
            md.parent.mkdir(parents=True)
            md.write_text(f"---\nname: zhome-a\ndisplayName:\n  zh: zhome-a\n"
                          f"profession:\n  zh: 顾问\n---\n\n{persona}\n", encoding="utf-8")
            custom = root / "custom-home"
            write_json(custom / "experts" / "zhome-a.json", {"expertId": "expert-from-custom-0000"})
            import migrate_workbuddy as mw
            plan = mw.migrate_pkg(pkg, custom)
            self.assertEqual(plan["experts"][0]["expert_id"], "expert-from-custom-0000")
            plan_default = mw.migrate_pkg(pkg)
            self.assertNotEqual(plan_default["experts"][0]["expert_id"],
                                "expert-from-custom-0000")


class TestResourceRefs(unittest.TestCase):
    """1.7.3 回归：SKILL.md 引用的 references/scripts/assets 必须可解析。

    背景：技能资源整包丢失时（源 10 个文件只剩 SKILL.md），SKILL.md 里 9 处引用全指空，
    旧版验收只查 `python scripts/x.py` 调用形式，仍报「通过」。
    """

    def test_extract_refs(self):
        text = ("- `references/report-structure.md`：六章结构\n"
                "- `scripts/risk_scorer.py`：风险打分\n"
                "- `assets/T1_专业初筛表_模板.md`：模板\n")
        self.assertEqual(rc.resource_refs(text), [
            "references/report-structure.md",
            "scripts/risk_scorer.py",
            "assets/T1_专业初筛表_模板.md",
        ])

    def test_placeholder_filtered(self):
        text = ("命令一律用绝对路径，不要写 `scripts/xxx.py`；"
                "模板见 references/{name}.md")
        self.assertEqual(rc.resource_refs(text), [])

    def _append_ref(self, home, app, skill, line):
        for base in (home / "skills" / skill, app / ".office-claw" / "skills" / skill):
            md = base / "SKILL.md"
            md.write_text(md.read_text(encoding="utf-8") + "\n" + line + "\n", encoding="utf-8")

    def test_missing_resource_is_error(self):
        with tempfile.TemporaryDirectory(prefix="esm-refs-") as d:
            home, app = build_home(Path(d))
            self._append_ref(home, app, "sk-a", "先读 `references/kb.md` 再作答。")
            res = verify_install.verify(home, None, app)
            self.assertTrue(any("资源文件不存在" in e for e in res["errors"]), res["errors"])

    def test_cross_skill_ref_not_error(self):
        """人设技能引用同包另一技能的资源、且专家同时挂载两者 → 不算缺失。"""
        with tempfile.TemporaryDirectory(prefix="esm-refs-cross-") as d:
            home, app = build_home(Path(d))
            self._append_ref(home, app, "sk-a", "按 `references/taxonomy.md` 分类。")
            for base in (home / "skills", app / ".office-claw" / "skills"):
                kb = base / "sk-b" / "references" / "taxonomy.md"
                kb.parent.mkdir(parents=True, exist_ok=True)
                kb.write_text("# 分类表\n", encoding="utf-8")
            card = read_json(home / "experts" / "card-a.json")
            card["skills"] = ["sk-a", "sk-b"]
            write_json(home / "experts" / "card-a.json", card)
            res = verify_install.verify(home, None, app)
            self.assertFalse(any("资源文件不存在" in e for e in res["errors"]), res["errors"])


class TestReviewFixes20261110(unittest.TestCase):
    """2026-11 PR 评审修复回归：P0 路径归一 + P1 内联 frontmatter / 多语言 description / staging 报告。"""

    # ---------- P0：normalize_slug ----------
    def test_normalize_slug_rejects_traversal_absolute_empty(self):
        import migrate_workbuddy as mw
        for bad in ("../../evil", "..\\evil", "/tmp/pr926/pwn_lead", "C:\\evil", "", "   ", None):
            with self.assertRaises(SystemExit, msg=f"应拒绝 {bad!r}"):
                mw.normalize_slug(bad, "测试")

    def test_normalize_slug_basenames_separator_names(self):
        import migrate_workbuddy as mw
        self.assertEqual(mw.normalize_slug("a/b/c", "测试"), "c")
        self.assertEqual(mw.normalize_slug("  ok-name  ", "测试"), "ok-name")

    def test_malicious_agent_name_cannot_escape_home(self):
        # 评审复现场景：name: ../../../../evil-lead 曾把产物写到 $HOME/evil-lead.json
        with tempfile.TemporaryDirectory(prefix="esm-p0-") as d:
            root = Path(d)
            home = root / "home"
            pkg = root / "evil-pkg"
            write_json(pkg / ".codebuddy-plugin" / "plugin.json",
                       {"name": "evil-pkg", "version": "1.0.0", "expertType": "agent",
                        "agents": ["agents/lead.md"]})
            (pkg / "agents").mkdir(parents=True)
            (pkg / "agents" / "lead.md").write_text(
                "---\nname: ../../../../evil-lead\ndisplayName:\n  zh: 恶意包\n---\n\n正文\n",
                encoding="utf-8")
            import migrate_workbuddy as mw
            saved = sys.argv
            sys.argv = ["migrate_workbuddy.py", "--source", str(pkg),
                        "--officeace-home", str(home)]
            try:
                with self.assertRaises(SystemExit):
                    mw.main()
            finally:
                sys.argv = saved
            # 数据目录内外都不得出现逃逸产物
            self.assertFalse((root / "evil-lead.json").exists())
            self.assertFalse((root / "evil-lead").exists())
            self.assertFalse((home / "experts").exists())

    def test_absolute_agent_name_rejected(self):
        with tempfile.TemporaryDirectory(prefix="esm-p0b-") as d:
            root = Path(d)
            home, pkg = root / "home", root / "abs-pkg"
            write_json(pkg / ".codebuddy-plugin" / "plugin.json",
                       {"name": "abs-pkg", "version": "1.0.0", "expertType": "agent",
                        "agents": ["agents/lead.md"]})
            (pkg / "agents").mkdir(parents=True)
            (pkg / "agents" / "lead.md").write_text(
                f"---\nname: {root / 'pwn_lead'}\ndisplayName:\n  zh: 绝对路径\n---\n\n正文\n",
                encoding="utf-8")
            import migrate_workbuddy as mw
            saved = sys.argv
            sys.argv = ["migrate_workbuddy.py", "--source", str(pkg),
                        "--officeace-home", str(home)]
            try:
                with self.assertRaises(SystemExit):
                    mw.main()
            finally:
                sys.argv = saved
            self.assertFalse((root / "pwn_lead").exists())

    # ---------- P1-1：内联 flow mapping ----------
    def test_inline_flow_mapping_parsed(self):
        # 文档样例本身就是内联写法；此前只认块状导致 displayName 带花括号落盘
        import migrate_workbuddy as mw
        fm, _ = mw.parse_fm_nested(
            "---\nname: ji-yanse\ndisplayName: { zh: 纪颜色 }\n"
            "profession: {zh: 数据分析师, en: Analyst}\nnickname: 陆掌舵\n---\n正文")
        self.assertEqual(fm.get("displayName"), {"zh": "纪颜色"})
        self.assertEqual(fm.get("profession"), {"zh": "数据分析师", "en": "Analyst"})
        self.assertEqual(fm.get("nickname"), "陆掌舵")

    # ---------- P1-2：多语言 description 不崩溃 ----------
    def test_multilang_description_no_crash(self):
        import inspect_suite
        import migrate_workbuddy as mw
        # dict 直接切片曾触发 TypeError: unhashable type: 'slice'（to_text 描述行）
        info = {"root": "x", "platform": "workbuddy", "manifest": None,
                "manifest_data": {"name": "p", "description": {"zh": "内联多语言描述", "en": "desc"}},
                "skills": [],
                "counts": {"skills": 0, "with_scripts": 0, "with_references": 0, "with_templates": 0}}
        self.assertIn("内联多语言描述", inspect_suite.to_text(info))
        self.assertEqual(mw.agent_description({"description": {"zh": "内联多语言描述"}}, {}, 0),
                         "内联多语言描述")

    # ---------- P1-3：dry-run 落 staging 报告 ----------
    def test_dry_run_writes_staging_report(self):
        with tempfile.TemporaryDirectory(prefix="esm-p13-") as d:
            root = Path(d)
            home, pkg = root / "home", root / "inline-pkg"
            write_json(pkg / ".codebuddy-plugin" / "plugin.json",
                       {"name": "inline-pkg", "version": "1.0.0", "expertType": "agent",
                        "agents": ["agents/lead.md"], "tags": ["测试"],
                        "quickPrompts": ["/help"]})
            (pkg / "agents").mkdir(parents=True)
            (pkg / "agents" / "lead.md").write_text(
                "---\nname: inline-lead\ndisplayName: { zh: 纪颜色 }\n---\n\n正文\n",
                encoding="utf-8")
            import migrate_workbuddy as mw
            saved = sys.argv
            sys.argv = ["migrate_workbuddy.py", "--source", str(pkg),
                        "--officeace-home", str(home)]
            try:
                self.assertEqual(mw.main(), 0)
            finally:
                sys.argv = saved
            reports = list((home / ".staging").glob("inline-pkg-*/report.md"))
            self.assertEqual(len(reports), 1, "dry-run 必须落 staging 报告")
            text = reports[0].read_text(encoding="utf-8")
            for token in ("丢弃", "需人工确认", "纪颜色", "quickPrompts"):
                self.assertIn(token, text)
            # dry-run 不写注册
            self.assertFalse((home / "experts").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
