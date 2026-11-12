#!/usr/bin/env python3
"""自然语言迁移入口：说一个人名/包名，自动定位源包、识别平台、路由到对应迁移器并验收。

用途：专家/专家套件迁移的唯一默认入口（支持 --list 预览、dry-run 预演、--install 安装+自验收）。

设计目标：调用者（人或 Agent）不需要知道源平台是 WorkBuddy / 千问办公 / 百度搭子，
也不需要知道该用 migrate_workbuddy.py 还是 migrate_suite.py——只给一个"想迁谁"的说法。

参数：
    --source <路径|包名|中文名|关键词>   要迁的对象；--all 时可给"父目录"或省略（扫全部已知源根）
    --all            迁该目录下全部可识别的包，或（配合 --list 的根）迁全部已发现的包
    --list           只列本机可迁移的包与迁移状态，不写盘
    --install        真正写盘（缺省为 dry-run 预演）
    --force          覆盖式重写技能与人设（默认幂等跳过已有内容）
    --name / --display-name / --nickname / --category   目标身份覆盖（单专家场景）
    --officeace-home / --app-root / --staging            路径覆盖，默认取本机真实目录
    --json           以 JSON 输出结论（供程序判定，人看普通输出更清楚）
    --no-runtime     跳过应用侧只读确认（应用没开时用）

退出码：0=成功；2=源找不到/无法识别；3=候选不唯一（需人确认）；1=写入后自检未通过；
4=跨机器确认闸门拦截（须先向用户提问，拿票据重试）。

用法示例：
    python scripts/migrate.py --list
    python scripts/migrate.py --source 投标响应作战团                 # 预演
    python scripts/migrate.py --source 投标响应作战团 --install        # 安装 + 自检
    python scripts/migrate.py --source ~/.qwenworkcn/plugins-custom/procure-bid-compare --install
    python scripts/migrate.py --source ~/.workbuddy/plugins/marketplaces/my-experts/plugins --all --install
    python scripts/migrate.py --source 合同收款节点管家 --install --json

自然语言提示词 → 参数映射（Agent 按此解释用户意图，不必追问路径）：
    「把 X 迁到 OfficeAce / 迁过来 / 装到这边」 → --source X --install
    「先看看会变成什么 / 能不能迁」             → --source X（预演，不写盘）
    「有哪些能迁的 / 我这边都有什么专家」        → --list
    「全迁 / 都搬过来」                         → --all --install（先 --list 确认范围）
    「X 用不了 / 报错 / 专家列表里没有」         → 先 verify_install.py + check_runtime.py 诊断，不重装
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import hashlib
import time
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import migration_gate as gate  # noqa: E402  跨机器确认闸门（三迁移器共用）

# Windows 控制台默认 cp936，输出 ✓ / · 会抛 UnicodeEncodeError；统一按 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001  非 TTY 或旧解释器，忽略
        pass

MANIFESTS = {
    ".qwenwork-plugin/plugin.json": "qwenwork",
    ".qoder-plugin/plugin.json": "qwenwork",
    ".claude-plugin/plugin.json": "dumate",
    ".codebuddy-plugin/plugin.json": "workbuddy",
}

# 本机默认源根：装了哪个平台就扫哪个，扫不到不算错
SOURCE_ROOTS = [
    ("workbuddy", "~/.workbuddy/plugins/marketplaces/*/plugins"),
    ("qwenwork", "~/.qwenworkcn/plugins-custom"),
    ("dumate", "~/AppData/Roaming/qianfan-desktop-app/qianfan_desk_xdg/*/data/plugins/user"),
    ("dumate", "~/AppData/Roaming/qianfan-desktop-app/qianfan_desk_xdg/global/data/plugins/user"),
]

PLATFORM_LABEL = {"workbuddy": "WorkBuddy", "qwenwork": "千问办公", "dumate": "百度搭子"}
SCORE_FLOOR = 55
AMBIGUITY_GAP = 5


# ---------------------------------------------------------------- 基础工具
def pick_text(value) -> str:
    """displayName 在 WorkBuddy/千问里常是 {zh, en} 双语字典，取中文优先。"""
    if isinstance(value, dict):
        for key in ("zh", "zh-CN", "en", "default"):
            if value.get(key):
                return str(value[key])
        for v in value.values():
            if v:
                return str(v)
        return ""
    return str(value or "")


def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def detect(root: Path) -> tuple[str, Path | None]:
    for rel, plat in MANIFESTS.items():
        p = root / rel
        if p.is_file():
            return plat, p
    if (root / "experts").is_dir() and (root / "skills").is_dir():
        return "officeace", None
    return "unknown", None


def manifest_meta(root: Path, plat: str, mpath: Path | None) -> dict:
    """从清单里取展示名、角色数、是否团队——只读清单，不解析全部技能，保证扫 100+ 包也够快。"""
    data = read_json(mpath) if mpath else None
    data = data if isinstance(data, dict) else {}
    display = pick_text(data.get("displayName")) or pick_text(data.get("name")) or root.name
    agents = data.get("agents") or []
    team_info = data.get("teamInfo") or {}
    is_team = bool(data.get("expertType") == "team" or team_info)
    aliases = {root.name, str(data.get("name") or ""), display}
    for lang in ("en", "zh"):
        if isinstance(data.get("displayName"), dict):
            aliases.add(str(data["displayName"].get(lang) or ""))
    for key in ("leadAgent",):
        if team_info.get(key):
            aliases.add(str(team_info[key]))
    for name in team_info.get("memberAgents") or []:
        aliases.add(str(name))
    if isinstance(agents, list):
        roles = len([a for a in agents if a])
        for a in agents:
            if isinstance(a, dict):
                if a.get("name"):
                    aliases.add(str(a["name"]))
                if a.get("displayName"):
                    aliases.add(pick_text(a["displayName"]))
    else:
        roles = 1
    # 只有 WorkBuddy 的 marketplace 里混着大量"纯技能包"（clangd-lsp、dockerfile-gen 之类），
    # 它们不是专家，迁过来只会污染专家列表；其余两个平台的插件目录本来就是专家
    has_agents = (root / "agents").is_dir()
    if is_team:
        kind = "team"
    elif plat != "workbuddy" or has_agents or agents:
        kind = "expert"
    else:
        kind = "skillpack"
    return {
        "display": display,
        "kind": kind,
        "is_team": is_team,
        "roles": roles if is_team else 1,
        "aliases": [a for a in aliases if a],
        "version": str(data.get("version") or ""),
        "description": pick_text(data.get("description"))[:60],
        "origin": origin_of(root),
    }


def origin_of(root: Path) -> str:
    """包在哪来的：marketplace 名 / 平台插件目录名，用于区分同名包。"""
    parts = root.parts
    if "marketplaces" in parts:
        i = parts.index("marketplaces")
        if i + 1 < len(parts):
            return parts[i + 1]
    return ""


def candidates_from(directory: Path, platform_hint: str = "") -> list[dict]:
    out: list[dict] = []
    if not directory.is_dir():
        return out
    for child in sorted(directory.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        plat, mpath = detect(child)
        if plat == "unknown" or plat == "officeace":
            continue
        meta = manifest_meta(child, plat, mpath)
        out.append({"path": child, "platform": plat, **meta})
    return out


def scan_roots(extra: list[str] | None = None) -> list[dict]:
    seen: dict[str, dict] = {}
    patterns = [p for _, p in SOURCE_ROOTS] + (extra or [])
    env_roots = os.environ.get("ESM_SOURCE_ROOTS", "")
    patterns += [p for p in env_roots.replace(";", os.pathsep).split(os.pathsep) if p.strip()]
    for pattern in patterns:
        for base in sorted(Path().home().glob(pattern.replace("~/", ""))):
            if base.is_file():
                continue
            direct = candidates_from(base)
            if direct:
                for c in direct:
                    seen.setdefault(str(c["path"]), c)
                continue
            # 根目录本身就是包
            plat, mpath = detect(base)
            if plat in ("workbuddy", "qwenwork", "dumate"):
                meta = manifest_meta(base, plat, mpath)
                seen.setdefault(str(base), {"path": base, "platform": plat, **meta})
    return list(seen.values())


# ---------------------------------------------------------------- 名称解析
def _norm(s: str) -> str:
    return re.sub(r"[\s\-_/·.，,。、（）()\[\]]+", "", str(s or "")).lower()


def score_of(spec: str, cand: dict) -> int:
    q = _norm(spec)
    if not q:
        return 0
    best = 0
    for alias in cand["aliases"]:
        a = _norm(alias)
        if not a:
            continue
        if q == a:
            s = 100
        elif a.startswith(q) or q.startswith(a):
            s = 84
        elif q in a:
            s = 72
        else:
            s = int(50 * SequenceMatcher(None, q, a).ratio())
        best = max(best, s)
    return best


def resolve(spec: str, extra_roots: list[str] | None, allow_skillpack: bool = False
            ) -> tuple[dict | None, list[tuple[int, dict]], int]:
    """返回 (命中候选, 排序后的候选列表, 退出码提示)。退出码：0 唯一命中 / 2 找不到 / 3 不唯一。"""
    raw = Path(os.path.expanduser(spec))
    if raw.is_dir():
        plat, mpath = detect(raw)
        if plat in ("workbuddy", "qwenwork", "dumate"):
            meta = manifest_meta(raw, plat, mpath)
            return {"path": raw.resolve(), "platform": plat, **meta}, [], 0
        # 父目录：交给 --all 或给出子包提示
        subs = candidates_from(raw)
        if subs:
            return None, [(100, c) for c in subs], 3
        return None, [], 2

    pool = [c for c in scan_roots(extra_roots) if allow_skillpack or c["kind"] != "skillpack"]
    # 同分时优先用户自建市场（my-experts），避免把平台自带副本当成用户要迁的那个
    ranked = sorted(((score_of(spec, c), c) for c in pool),
                    key=lambda x: (-x[0], 0 if "my-experts" in (x[1].get("origin") or "") else 1))
    ranked = [(s, c) for s, c in ranked if s >= 30]
    if not ranked or ranked[0][0] < SCORE_FLOOR:
        return None, ranked[:5], 2
    top_score = ranked[0][0]
    close = [(s, c) for s, c in ranked if s >= top_score - AMBIGUITY_GAP]
    # 同名同平台、只是在不同 marketplace 里重复的，视为同一个（优先 my-experts 等用户自建的）
    names = {(c["platform"], c["path"].name) for _, c in close}
    if len(close) > 1 and len(names) > 1:
        return None, close[:5], 3
    return close[0][1], ranked[:5], 0


# ---------------------------------------------------------------- 路由执行
def run_module(module: str, argv: list[str]) -> int:
    """复用既有迁移器：只替换 sys.argv，不改它们的实现（单一事实来源仍在各自脚本里）。"""
    import importlib

    mod = importlib.import_module(module)
    saved = sys.argv
    sys.argv = [f"{module}.py", *argv]
    try:
        return int(mod.main() or 0)
    finally:
        sys.argv = saved


def staging_for(name: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.home() / ".office-claw" / ".staging" / f"{name}-{stamp}"


def run_one(cand: dict, args) -> int:
    plat = cand["platform"]
    argv: list[str] = ["--source", str(cand["path"])]
    if args.install:
        argv.append("--install")
    if args.force:
        argv.append("--force")
    argv += ["--officeace-home", args.officeace_home]
    if args.app_root:
        argv += ["--app-root", args.app_root]

    if plat == "workbuddy":
        module, argv = "migrate_workbuddy", argv
    else:
        stage = Path(args.staging).expanduser() if args.staging else staging_for(cand["path"].name)
        argv += ["--staging", str(stage), "--category", args.category]
        for flag, val in (("--name", args.name), ("--display-name", args.display_name),
                          ("--nickname", args.nickname)):
            if val:
                argv += [flag, val]
        module = "migrate_suite"

    # --json 时把子迁移器的过程日志挪到 stderr，保证 stdout 只有一段可解析的 JSON
    if args.json:
        with contextlib.redirect_stdout(sys.stderr):
            return run_module(module, argv)
    return run_module(module, argv)


# ---------------------------------------------------------------- 自检
def static_check(home: Path, app_root: str | None) -> dict:
    from verify_install import verify

    return verify(home, None, Path(app_root).expanduser() if app_root else None)


def runtime_check(timeout: int = 60) -> tuple[bool | None, str]:
    """应用侧只读确认。返回 (是否通过 | None=跳过, 摘要)。"""
    try:
        proc = subprocess.run(
            [sys.executable, str(HERE / "check_runtime.py")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except Exception as e:  # noqa: BLE001  应用没开、cookie 失效都不该阻断迁移
        return None, f"跳过（{type(e).__name__}）"
    out = (proc.stdout or "") + (proc.stderr or "")
    last = [ln for ln in out.splitlines() if ln.strip()]
    summary = last[-1].strip() if last else ""
    if proc.returncode == 0:
        return True, summary.replace("结论：", "")
    return False, summary or f"退出码 {proc.returncode}"


def already_migrated(home: Path, cand: dict) -> bool:
    """团队的专家卡按角色命名（<包>-team-lead / 成员名），不能用包名找卡，得查 user-teams。"""
    name = cand["path"].name
    if cand.get("is_team"):
        for tf in home.glob("users/*/user-teams.json"):
            for t in (read_json(tf) or {}).get("teams") or []:
                if t.get("teamId") in (f"wb-team-{name}", name):
                    return True
    card = home / "experts" / f"{name}.json"
    if not card.is_file():
        return False
    data = read_json(card) or {}
    eid = data.get("expertId")
    if not eid:
        return False
    for ue in home.glob("users/*/user-experts.json"):
        blob = read_json(ue) or {}
        if any(e.get("expertId") == eid for e in blob.get("experts") or []):
            return True
    return False


# ---------------------------------------------------------------- 输出
def print_list(pool: list[dict], home: Path, show_skillpack: bool = False) -> None:
    hidden = [c for c in pool if c["kind"] == "skillpack"]
    shown = [c for c in pool if show_skillpack or c["kind"] != "skillpack"]
    if not shown:
        print("没有找到可迁移的专家套件。检查：源平台是否装在本机，或用 --source 直接给路径。")
        return
    print(f"本机可迁移的专家套件（{len(shown)} 个）：\n")
    width = max((len(PLATFORM_LABEL.get(c["platform"], c["platform"])) for c in shown), default=6)
    name_w = min(max((len(c["path"].name) for c in shown), default=20), 34)
    for c in sorted(shown, key=lambda x: (x["platform"], x["path"].name)):
        kind = f"团队 {c['roles']} 角色" if c["is_team"] else "单专家"
        flag = "已迁移" if already_migrated(home, c) else "未迁移"
        plat = PLATFORM_LABEL.get(c["platform"], c["platform"]).ljust(width)
        origin = f"  ←{c['origin']}" if c.get("origin") else ""
        print(f"  [{flag}] {plat}  {c['path'].name:<{name_w}} {c['display']}（{kind}）{origin}")
    print("\n迁移：--source <包名或中文名> [--install]；全迁：--source <父目录> --all --install")
    if hidden and not show_skillpack:
        print(f"（另有 {len(hidden)} 个纯技能包不属于专家，已隐藏；要看加 --all-kinds）")
    print("\n迁移：--source <包名或中文名> [--install]；全迁：--source <父目录> --all --install")


def dump_candidates(ranked, spec: str) -> None:
    if not ranked:
        print(f"找不到「{spec}」。用 --list 看本机有哪些；或直接给套件目录路径。")
        return
    print(f"「{spec}」可能对应多个套件，请确认是哪一个（用 --source <包名> 指定）：")
    for s, c in ranked:
        kind = f"团队 {c['roles']} 角色" if c["is_team"] else "单专家"
        print(f"  ({s}) {c['path'].name:<32} {c['display']}｜{PLATFORM_LABEL.get(c['platform'], c['platform'])}｜{kind}")
        print(f"        {c['path']}")


# ---------------------------------------------------------------- 主流程
def main() -> int:
    ap = argparse.ArgumentParser(description="自然语言迁移入口（自动识别源平台并路由）")
    ap.add_argument("--source", default=None, help="路径 / 包名 / 中文名 / 关键词")
    ap.add_argument("--all", action="store_true", help="迁移目录下全部可识别套件")
    ap.add_argument("--list", action="store_true", help="列出本机可迁移套件与迁移状态")
    ap.add_argument("--all-kinds", dest="all_kinds", action="store_true",
                    help="连纯技能包一起列出/迁移（默认只处理有 agents/ 的专家包）")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--confirm-local", dest="confirm_local", default=None, metavar="TICKET",
                    help="跨机器确认票据：先不带本参数执行以触发闸门获取 nonce，向用户确认后回传。")
    ap.add_argument("--gate-cooldown", dest="gate_cooldown", type=int, default=None, metavar="SECONDS",
                    help="跨机器闸门冷却秒数（默认 90，环境变量 ESM_GATE_COOLDOWN 亦可）。")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--display-name", dest="display_name", default=None)
    ap.add_argument("--nickname", default=None)
    ap.add_argument("--category", default="business")
    ap.add_argument("--officeace-home", dest="officeace_home", default="~/.office-claw")
    ap.add_argument("--app-root", default=None)
    ap.add_argument("--staging", default=None)
    ap.add_argument("--root", action="append", default=None, help="额外的源根目录（可重复）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-runtime", dest="no_runtime", action="store_true")
    args = ap.parse_args()

    home = Path(args.officeace_home).expanduser()

    # ⛔ 跨机器确认闸门（1.6.0 下沉为公共模块 migration_gate.py，三个迁移器共用，
    # 直接调用子迁移器同样被拦截）。机制：--install 无 --confirm-local 时拦截并发放
    # 一次性票据；--confirm-local 需回传票据且距拦截时刻 ≥ 冷却秒数（默认 90，
    # --gate-cooldown 或环境变量 ESM_GATE_COOLDOWN 可调）。确认通过后写 confirmed
    # 标记（10 分钟窗口），转调子迁移器时凭标记放行，不重复提问。
    gate_rc = gate.enforce(home, args.install, args.confirm_local,
                           cooldown=args.gate_cooldown, source=args.source or "",
                           entry="migrate.py", json_mode=args.json)
    if gate_rc is not None:
        return gate_rc

    if args.list:
        pool = scan_roots(args.root)
        if args.json:
            print(json.dumps([{**{k: (str(v) if isinstance(v, Path) else v)
                                  for k, v in c.items() if k != "aliases"},
                               "migrated": already_migrated(home, c)} for c in pool],
                             ensure_ascii=False, indent=2))
        else:
            print_list(pool, home, args.all_kinds)
        return 0

    if not args.source:
        ap.print_help()
        return 2

    def _keep(cands: list[dict]) -> list[dict]:
        return [c for c in cands if args.all_kinds or c["kind"] != "skillpack"]

    raw = Path(os.path.expanduser(args.source))
    hit = None
    # 先判「给的是目录且要批量」：父目录里没有清单，交给 resolve 只会被判成"候选不唯一"
    if args.all and raw.is_dir() and detect(raw)[0] in ("unknown", "officeace"):
        targets = _keep(candidates_from(raw))
        if targets:
            if not args.json:
                print(f"[展开] {raw.name} 下有 {len(targets)} 个专家套件")
        else:
            targets = _keep(scan_roots(args.root))
            if not args.json:
                print(f"[展开] 全部 {len(targets)} 个已发现专家套件")
        if not targets:
            print(f"「{args.source}」下没有可迁移的专家套件。用 --list 看本机都有什么。", file=sys.stderr)
            return 2
    else:
        hit, ranked, code = resolve(args.source, args.root, args.all_kinds)
        if code == 2:
            dump_candidates(ranked, args.source)
            return 2
        if code == 3:
            dump_candidates(ranked, args.source)
            return 3
        if args.all:
            # 给的是单个包却要 --all：展开它所在目录的兄弟包，或退到全机扫描
            subs = _keep(candidates_from(hit["path"].parent))
            if len(subs) > 1:
                targets = subs
                if not args.json:
                    print(f"[展开] {hit['path'].parent.name} 下有 {len(subs)} 个专家套件")
            else:
                targets = _keep(scan_roots(args.root))
                if not args.json:
                    print(f"[展开] 全部 {len(targets)} 个已发现专家套件")
        else:
            targets = [hit]

    if hit is not None and len(targets) == 1 and not args.json:
        kind = f"团队（{hit['roles']} 角色）" if hit["is_team"] else "单专家"
        print(f"[识别] {hit['display']} → {hit['path']}")
        print(f"       {PLATFORM_LABEL.get(hit['platform'], hit['platform'])} · {kind} · "
              f"v{hit['version'] or '?'} · 迁移器 {('migrate_workbuddy' if hit['platform'] == 'workbuddy' else 'migrate_suite')}")

    failed: list[dict] = []
    for cand in targets:
        if not args.json:
            print(f"\n=== {cand['display']}（{cand['path'].name}） ===")
        rc = run_one(cand, args)
        if rc != 0:
            failed.append({"name": cand["path"].name, "rc": rc})

    if not args.install:
        if args.json:
            print(json.dumps({
                "targets": [{"name": c["path"].name, "display": c["display"], "platform": c["platform"],
                             "path": str(c["path"]), "is_team": c["is_team"], "roles": c["roles"]} for c in targets],
                "installed": False, "failed": failed,
            }, ensure_ascii=False, indent=2))
        else:
            print("\n预演完成，未写入 OfficeAce。确认后加 --install（已迁移的会沿用原 expertId，不会重复）。")
        return 0 if not failed else 1

    # 1.6.0：安装后自动同步应用镜像目录（数据目录 skills → 应用镜像）。
    # 正常安装两边一致，此处是兜底：镜像里有过期残留或本次只改了数据目录时自动对齐。
    mirror_note = ""
    try:
        import mirror_sync
        app_root_p = Path(args.app_root).expanduser() if args.app_root else None
        synced = [r["slug"] for r in mirror_sync.fix(home, app_root_p) if r.get("status") == "synced"]
        if synced:
            shown = ", ".join(synced[:5]) + ("…" if len(synced) > 5 else "")
            mirror_note = f"同步 {len(synced)} 个技能到应用镜像（{shown}）"
        else:
            mirror_note = "镜像与数据目录一致，无需同步"
    except Exception as e:  # noqa: BLE001  同步失败不阻断交付，check_runtime/verify 会再兜底
        mirror_note = f"镜像同步跳过（{type(e).__name__}）"

    # 写入后统一验收：静态十项 + 应用侧只读确认
    res = static_check(home, args.app_root)
    rt_ok, rt_note = (None, "已跳过（--no-runtime）") if args.no_runtime else runtime_check()

    if not args.json:
        print("\n=== 验收 ===")
        n_err = len(res["errors"])
        print(f"静态自检：{'通过' if not n_err else f'{n_err} 个问题'}（{len(res['ok'])} 项通过）")
        for e in res["errors"][:6]:
            print(f"  ✗ {e}")
        print(f"应用侧：{'通过' if rt_ok else ('跳过' if rt_ok is None else '未通过')}｜{rt_note}")
        if mirror_note:
            print(f"镜像同步：{mirror_note}")
        if not res["errors"] and rt_ok is True:
            print("\n结论：迁移完成且可用。可直接在 OfficeAce 里派任务；专家多时用 @昵称 召唤，团队在团队列表里。")
        elif res["errors"]:
            print("\n结论：文件已写入，但自检未过。按上面的 ✗ 修，不要靠重启掩盖。")
        else:
            print("\n结论：静态检查通过，应用侧未确认。启动 OfficeAce 后跑 check_runtime.py 复核（不要跳过这步）。")

    summary = {
        "targets": [{"name": c["path"].name, "display": c["display"], "platform": c["platform"],
                     "path": str(c["path"]), "is_team": c["is_team"], "roles": c["roles"]} for c in targets],
        "installed": args.install,
        "failed": failed,
        "static": {"errors": res["errors"], "warnings": res["warnings"], "passed": len(res["ok"])},
        "runtime": {"ok": rt_ok, "note": rt_note},
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    if failed or res["errors"]:
        return 1
    if rt_ok is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
