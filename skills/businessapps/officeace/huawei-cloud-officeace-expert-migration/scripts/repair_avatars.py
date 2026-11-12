#!/usr/bin/env python3
"""修复已迁移专家在 OfficeAce 里显示成破图 / 乱码的头像。

用途：扫描 OfficeAce 全部注册位置，找出 avatar 指向不存在文件的记录，改写成一定可加载的头像
      （优先从 WorkBuddy 源包找回原头像，找不到则用应用内置通用头像）。
参数：--officeace-home 数据目录（默认 ~/.office-claw）；--app-root 应用安装根（默认自动探测）；
      --source-root 源包根（默认 WorkBuddy 专家市场目录）；--fix 真正写盘（默认只诊断）；
      --json 以 JSON 输出结果。
返回值：退出码 0=无坏头像或已全部修复；1=仍有坏头像未修（未加 --fix）或修复后仍不可加载。

为什么需要它：卡片里的 avatar 会原样进前端 <img src>，文件不存在时浏览器改显示 alt 文本，
40px 圆形头像里塞进中文名，看上去就是「乱码」。迁移脚本早期版本按专家名硬拼
/avatars/experts/<name>.png，而应用只自带固定几张图，于是必然破图。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from migrate_suite import (  # noqa: E402
    AVATAR_EXTS,
    active_user_dir,
    avatar_exists,
    avatar_quality,
    ensure_avatar,
    entry_slug,
    find_app_root,
    find_user_catalog,
    find_user_experts,
    read_json,
    stamp,
    write_json,
)

MANIFESTS = (
    ".codebuddy-plugin/plugin.json",
    ".qwenwork-plugin/plugin.json",
    ".claude-plugin/plugin.json",
)


def build_source_index(root: Path | None) -> dict[str, Path]:
    """扫描源包目录，建立 角色名 → 源头像文件 的索引。

    参数：root —— 源包根目录（其下每个子目录是一个专家包）；返回值：{角色名: 图片路径}。
    """
    index: dict[str, Path] = {}
    if not root or not root.is_dir():
        return index
    for pkg in sorted(root.iterdir()):
        avd = pkg / "avatars"
        if not pkg.is_dir() or not avd.is_dir():
            continue
        imgs = [p for p in avd.iterdir() if p.is_file() and p.suffix.lower() in AVATAR_EXTS]
        for p in imgs:
            index.setdefault(p.stem, p)
        # 单角色包常用 avatars/expert.png，文件名带不出角色名，回退到清单里的 agents
        singles = [p for p in imgs if p.stem in ("expert", "avatar", "team")]
        if len(singles) != 1:
            continue
        manifest = None
        for rel in MANIFESTS:
            if (pkg / rel).is_file():
                try:
                    manifest = read_json(pkg / rel)
                except Exception:  # noqa: BLE001
                    manifest = None
                break
        if isinstance(manifest, dict):
            for agent in manifest.get("agents") or []:
                if isinstance(agent, str):
                    index.setdefault(Path(agent).stem, singles[0])
    return index


def collect_entries(home: Path) -> tuple[list[tuple[Path, str, dict, str]], dict[Path, object]]:
    """收集所有带 avatar 字段的注册记录，并保留各文件的内存根对象。

    参数：home —— OfficeAce 数据目录；
    返回值：(记录列表[(文件, 位置说明, 记录对象, 角色名)], {文件: 内存根对象})。
    """
    entries: list[tuple[Path, str, dict, str]] = []
    roots: dict[Path, object] = {}

    def load(p: Path):
        if p not in roots:
            try:
                roots[p] = read_json(p)
            except Exception:  # noqa: BLE001
                roots[p] = None
        return roots[p]

    experts_dir = home / "experts"
    if experts_dir.is_dir():
        for f in sorted(experts_dir.glob("*.json")):
            if ".bak" in f.name:
                continue
            d = load(f)
            if isinstance(d, dict):
                entries.append((f, f"experts/{f.name}", d, str(d.get("name") or f.stem)))

    cat = home / "user-catalogs" / "catalog.json"
    if cat.is_file():
        d = load(cat)
        for e in (d or {}).get("experts") or []:
            if isinstance(e, dict):
                entries.append((cat, "user-catalogs/catalog.json", e, entry_slug(e)))

    uc = find_user_catalog(home)
    if uc and uc.is_file():
        d = load(uc)
        for b in (d or {}).get("breeds") or []:
            if not isinstance(b, dict):
                continue
            entries.append((uc, f"{uc.name}#breed", b, entry_slug(b)))
            for v in b.get("variants") or []:
                if isinstance(v, dict) and "avatar" in v:
                    entries.append((uc, f"{uc.name}#variant", v, entry_slug(b)))

    ue = find_user_experts(home)
    if ue and ue.is_file():
        d = load(ue)
        for e in (d or {}).get("experts") or []:
            if isinstance(e, dict):
                # user-experts 条目没有 name，靠 expertId 反解，否则会生成 expert-xxx-<hash>.png 这种歪路径
                entries.append((ue, f"{ue.parent.name}/user-experts.json", e, entry_slug(e)))

    act = active_user_dir(home)
    teams = (act / "user-teams.json") if act else None
    if teams and teams.is_file():
        d = load(teams)
        for t in (d or {}).get("teams") or []:
            if not isinstance(t, dict):
                continue
            for m in t.get("members") or []:
                if isinstance(m, dict) and "avatar" in m:
                    entries.append((teams, "user-teams.json#member", m, str(m.get("expertId") or "")))
    return entries, roots


def main() -> int:
    ap = argparse.ArgumentParser(description="修复 OfficeAce 已迁移专家的破图头像")
    ap.add_argument("--officeace-home", default="~/.office-claw")
    ap.add_argument("--app-root", default=None)
    ap.add_argument("--source-root", default="~/.workbuddy/plugins/marketplaces/my-experts/plugins")
    ap.add_argument("--avatar-pack", default=None,
                    help="预制头像目录：按 <专家名>.png 取图，优先于源包头像")
    ap.add_argument("--fix", action="store_true", help="真正写盘（默认只诊断）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    home = Path(args.officeace_home).expanduser()
    if not home.is_dir():
        raise SystemExit(f"错误：OfficeAce 数据目录不存在 {home}")
    app_root = Path(args.app_root).expanduser() if args.app_root else find_app_root(home)
    if not app_root:
        raise SystemExit("错误：找不到 OfficeAce 应用安装目录，用 --app-root 指定")

    src_index = build_source_index(Path(args.source_root).expanduser())
    pack = Path(args.avatar_pack).expanduser() if args.avatar_pack else None
    entries, roots = collect_entries(home)

    def is_bad(av) -> bool:
        """坏头像：文件不存在，或存在但只是纯色占位图。"""
        if not avatar_exists(app_root, av):
            return True
        if isinstance(av, str) and av.startswith("/avatars/"):
            root = Path(app_root) / "packages/green-package/web/dist/avatars"
            return avatar_quality(root / av[len("/avatars/"):]) != "ok"
        return False

    broken = [e for e in entries if is_bad(e[2].get("avatar"))]

    detail = []
    touched: dict[Path, int] = {}
    for path, where, obj, name in broken:
        old = obj.get("avatar")
        slug = (name or "").strip()
        if not slug:
            continue  # 取不出专家身份就别动，否则会按文件名生成 user-experts.png 这类歪头像
        src_img = None
        if pack:
            for ext in AVATAR_EXTS:
                cand = pack / f"{slug}{ext}"
                if cand.is_file() and avatar_quality(cand) == "ok":
                    src_img = cand
                    break
        if src_img is None:
            src_img = src_index.get(slug)
            if src_img is not None and avatar_quality(src_img) != "ok":
                src_img = None
        new = ensure_avatar(app_root, slug, src_img, write=args.fix)
        detail.append({"where": where, "name": slug, "old": old, "new": new,
                       "from_source": bool(src_img), "same_path": new == old})
        if args.fix and new and new != old:
            obj["avatar"] = new
            touched[path] = touched.get(path, 0) + 1

    if args.fix and touched:
        ts = stamp()
        for path in touched:
            shutil.copy2(path, path.with_name(f"{path.name}.bak-{ts}"))
            write_json(path, roots[path])

    remaining = [(w, o.get("avatar")) for _, w, o, _ in
                 (collect_entries(home)[0] if args.fix else entries)
                 if is_bad(o.get("avatar"))]

    result = {"app_root": str(app_root), "checked": len(entries), "broken": len(broken),
              "remaining": len(remaining), "rewritten": detail if args.fix else []}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"应用头像目录：{app_root}")
        print(f"扫描 {len(entries)} 条注册记录，坏头像 {len(broken)} 条")
        for d in detail:
            if d["same_path"] and d["from_source"]:
                tail = "  (路径不变，补齐图片文件)"
            elif d["from_source"]:
                tail = "  (还原源头像)"
            else:
                tail = "  (改用内置头像)"
            print(f"  {d['where']:<38} {d['name']:<20} {d['old']} → {d['new']}{tail}")
        if args.fix:
            print(f"已改写 {len(touched)} 个文件，剩余坏头像 {len(remaining)} 条")
        elif broken:
            print("以上仅诊断，未修改任何文件；确认后加 --fix 执行修复")
    return 0 if not remaining else 1


if __name__ == "__main__":
    sys.exit(main())
