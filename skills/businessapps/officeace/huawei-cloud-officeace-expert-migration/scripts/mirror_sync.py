#!/usr/bin/env python3
"""应用镜像目录同步（1.6.0）：消除「改了用户目录、应用读的还是旧镜像」这一类静默失效。

背景：OfficeAce 应用读取的是**应用安装目录** `<app-root>/.office-claw/skills/` 下的
技能镜像（启动时缓存文件副本）。迁移器安装时会同时写入数据目录与镜像，但安装之后
对 `~/.office-claw/skills/<slug>/` 的任何手工修改（改 SKILL.md、修脚本、换头像）都
**不会自动生效**——曾经实测改了 SKILL.md 的 description 而应用仍加载旧版，排查了
三轮才发现是镜像没同步。

本脚本把镜像同步变成一条命令：
  - 默认方向：数据目录 `~/.office-claw/skills/` → 应用镜像（数据目录是人/Agent 编辑的源头）；
  - `--reverse` 反向：应用镜像 → 数据目录（镜像里有应用侧生成物时用）；
  - `--check` 只报告差异不写盘，退出码 1 表示存在漂移（可接 CI / 定时巡检）；
  - 按 SHA-256 逐文件比对，只覆盖有差异的文件，不整目录删除（镜像里的孤儿文件保留并报告）。
用途：消除镜像漂移；返回值（退出码）：0=一致或已同步，1=存在漂移（--check），2=用法错误。

用法：
    python mirror_sync.py --check                     # 报告全部技能的镜像漂移
    python mirror_sync.py --fix                       # 把漂移的技能从数据目录同步到镜像
    python mirror_sync.py --slug my-skill --fix       # 只同步指定技能
    python mirror_sync.py --reverse --check           # 反向检查
退出码：0=无漂移（或已修复）；1=存在漂移（--check 模式）；2=目录不存在。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from migrate_suite import find_app_root  # noqa: E402


def _hash(p: Path) -> str:
    h = hashlib.sha256()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return "unreadable"
    return h.hexdigest()


SKIP_NAMES = {"__pycache__", ".DS_Store"}


def _skip(rel: str) -> bool:
    parts = rel.split("/")
    if any(p in SKIP_NAMES for p in parts[:-1]):
        return True
    name = parts[-1]
    return name.endswith((".pyc", ".pyo")) or ".bak" in name  # .bak 是迁移器自己的备份，不进镜像


def snapshot(root: Path) -> dict[str, str]:
    """目录内全部文件的 {相对路径: sha256}。目录不存在返回空表。"""
    if not root.is_dir():
        return {}
    return {
        str(p.relative_to(root)).replace("\\", "/"): _hash(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and not _skip(str(p.relative_to(root)).replace("\\", "/"))
    }


def diff_slug(src: Path, dst: Path) -> dict:
    """比对一个技能的两个副本。返回 changed/only_src/only_dst 三个相对路径列表。"""
    s, d = snapshot(src), snapshot(dst)
    changed = sorted(k for k in (set(s) & set(d)) if s[k] != d[k])
    only_src = sorted(set(s) - set(d))
    only_dst = sorted(set(d) - set(s))
    return {"changed": changed, "only_src": only_src, "only_dst": only_dst}


def scan(home: Path, app_root: Path | None, slugs: list[str] | None = None,
         reverse: bool = False) -> list[dict]:
    """扫描漂移。返回每个技能一条记录：slug / status / detail。"""
    user_skills = home / "skills"
    app_skills = (app_root / ".office-claw" / "skills") if app_root else None
    names = sorted(p.name for p in user_skills.iterdir() if p.is_dir()) \
        if (user_skills.is_dir() and not slugs) else (slugs or [])
    out: list[dict] = []
    for slug in names:
        src = user_skills / slug
        dst = app_skills / slug if app_skills else None
        first, second = (dst, src) if reverse else (src, dst)
        if second is None:
            out.append({"slug": slug, "status": "no-app-root",
                        "detail": "未找到应用安装目录，无法比对镜像"})
            continue
        if not first.is_dir():
            out.append({"slug": slug, "status": "missing-in-home" if not reverse else "missing-in-app",
                        "detail": f"{'数据目录' if not reverse else '应用镜像'}缺少 skills/{slug}/"})
            continue
        d = diff_slug(first, second)
        if not (d["changed"] or d["only_src"] or d["only_dst"]):
            out.append({"slug": slug, "status": "same", "detail": ""})
        else:
            status = "drift" if d["changed"] else ("copy-needed" if d["only_src"] and not reverse
                                                   else "missing-in-app" if not reverse else "missing-in-home")
            out.append({"slug": slug, "status": status, "detail": json.dumps(d, ensure_ascii=False)})
    return out


def fix(home: Path, app_root: Path | None, slugs: list[str] | None = None,
        reverse: bool = False) -> list[dict]:
    """把漂移技能按方向复制对齐。返回与 scan 同构的结果（status 变为 synced）。"""
    results = scan(home, app_root, slugs, reverse)
    user_skills = home / "skills"
    app_skills = (app_root / ".office-claw" / "skills") if app_root else None
    for r in results:
        if r["status"] in ("same", "no-app-root", "missing-in-home", "missing-in-app"):
            continue
        src = user_skills / r["slug"] if not reverse else app_skills / r["slug"]
        dst = app_skills / r["slug"] if not reverse else user_skills / r["slug"]
        try:
            dst.mkdir(parents=True, exist_ok=True)
            d = diff_slug(src, dst)
            for rel in d["changed"] + (d["only_src"] if not reverse else d["only_dst"]):
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / rel, target)
            r["status"] = "synced"
        except OSError as e:
            r["status"] = "error"
            r["detail"] = f"{type(e).__name__}: {e}"
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="应用镜像目录同步（数据目录 skills ↔ 应用镜像 skills）")
    ap.add_argument("--slug", action="append", default=None,
                    help="只处理指定技能（可重复）；缺省处理数据目录下全部技能")
    ap.add_argument("--fix", action="store_true", help="写盘修复漂移（缺省只报告）")
    ap.add_argument("--check", action="store_true",
                    help="只报告差异不写盘（与缺省行为一致，显式写出便于 CI/巡检表达意图）")
    ap.add_argument("--reverse", action="store_true", help="反向同步：应用镜像 → 数据目录")
    ap.add_argument("--home", default="~/.office-claw")
    ap.add_argument("--app-root", default=None, help="应用安装根（自动探测失败时指定）")
    args = ap.parse_args()

    home = Path(args.home).expanduser()
    if not home.is_dir():
        print(f"错误：数据目录不存在 {home}", file=sys.stderr)
        return 2
    app_root = Path(args.app_root).expanduser() if args.app_root else find_app_root(home)
    if not app_root:
        print("未找到应用安装目录（--app-root 指定）。无法比对镜像。", file=sys.stderr)
        return 2

    results = fix(home, app_root, args.slug, args.reverse) if args.fix else scan(home, app_root, args.slug, args.reverse)
    drifted = [r for r in results if r["status"] not in ("same",)]
    for r in results:
        if r["status"] == "same":
            continue
        print(f"  [{r['status']}] {r['slug']} {r['detail']}")
    verb = "已同步" if args.fix else "存在漂移"
    print(f"\n结论：检查 {len(results)} 个技能，{verb} {len(drifted)} 个"
          + ("（--fix 已写盘修复）" if args.fix and drifted else
             "（加 --fix 修复）" if drifted and not args.fix else ""))
    return 0 if (not drifted or args.fix) else 1


if __name__ == "__main__":
    raise SystemExit(main())
