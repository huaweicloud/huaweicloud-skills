#!/usr/bin/env python3
"""把一张图片设为指定专家 / 专家团的头像，并同步全部注册位置。

用途：迁移过来的头像不合格（纯色占位图、误用默认图）时，用 AI 或设计稿生成一张新图，
      本脚本负责落盘 + 写进所有注册点，避免只改一处导致列表与详情不一致。
参数：--name 专家 name（或团队 teamId）；--image 图片文件（png/jpg/webp）；
      --team 声明目标是专家团；--officeace-home 数据目录；--app-root 应用安装根；
      --file-name 头像文件名（默认 <name>.png）。
返回值：退出码 0=已写入全部位置；2=参数或文件错误；3=没找到对应注册项。

写入位置（专家）：头像目录文件、experts/<name>.json、user-catalogs/catalog.json、
      users/<uid>/user-experts.json、用户 catalog 的 breeds[].avatar 与 variants[].avatar。
写入位置（专家团）：头像目录文件、users/<uid>/user-teams.json 的 teams[].avatar。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from migrate_suite import (  # noqa: E402
    AVATAR_EXTS,
    active_user_dir,
    avatar_root,
    entry_slug,
    find_app_root,
    find_user_catalog,
    find_user_experts,
    read_json,
    stamp,
    write_json,
)

URL_PREFIX = "/avatars/experts/"


def install_image(app_root: Path | None, image: Path, file_stem: str) -> str:
    """把图片复制进应用头像目录，返回可用的 avatar URL。"""
    root = avatar_root(app_root)
    if root is None:
        raise SystemExit("错误：找不到应用头像目录，用 --app-root 指定 OfficeAce 安装根目录")
    ext = image.suffix.lower()
    if ext not in AVATAR_EXTS:
        raise SystemExit(f"错误：不支持的图片格式 {ext}（支持 {', '.join(AVATAR_EXTS)}）")
    name = f"{file_stem}{'.png' if ext == '.jpeg' else ext}"
    dst = root / "experts" / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image, dst)
    return URL_PREFIX + name


def patch_expert(home: Path, name: str, url: str) -> list[str]:
    """把 url 写进专家相关的全部注册位置，返回被修改的文件列表。"""
    touched: list[str] = []
    ts = stamp()

    def save(p: Path, data) -> None:
        shutil.copy2(p, p.with_name(f"{p.name}.bak-{ts}"))
        write_json(p, data)
        touched.append(str(p))

    card = home / "experts" / f"{name}.json"
    if card.is_file():
        d = read_json(card)
        d["avatar"] = url
        save(card, d)

    cat = home / "user-catalogs" / "catalog.json"
    if cat.is_file():
        d = read_json(cat)
        hit = False
        for e in d.get("experts") or []:
            if isinstance(e, dict) and entry_slug(e) == name:
                e["avatar"] = url
                hit = True
        if hit:
            save(cat, d)

    ie = find_user_experts(home)
    if ie:
        d = read_json(ie)
        hit = False
        for e in d.get("experts") or []:
            # 这里没有 name 字段，只能靠 expertId 反解 slug 匹配
            if isinstance(e, dict) and entry_slug(e) == name:
                e["avatar"] = url
                hit = True
        if hit:
            save(ie, d)

    uc = find_user_catalog(home)
    if uc and uc.is_file():
        d = read_json(uc)
        hit = False
        for b in d.get("breeds") or []:
            if isinstance(b, dict) and entry_slug(b) == name:
                b["avatar"] = url
                hit = True
                for v in b.get("variants") or []:
                    if isinstance(v, dict) and "avatar" in v:
                        v["avatar"] = url
        if hit:
            save(uc, d)
    return touched


def patch_team(home: Path, team_key: str, display: str | None, url: str) -> list[str]:
    """把 url 写进 user-teams.json 对应团队的 avatar 字段。"""
    act = active_user_dir(home)
    candidates = [act / "user-teams.json"] if act else []
    if (home / "users").is_dir():
        candidates += list((home / "users").glob("*/user-teams.json"))
    seen: set[Path] = set()
    ts = stamp()
    touched: list[str] = []
    for p in candidates:
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        d = read_json(p)
        hit = False
        for t in d.get("teams") or []:
            if not isinstance(t, dict):
                continue
            if t.get("teamId") == team_key or (display and t.get("displayName") == display):
                t["avatar"] = url
                hit = True
        if hit:
            shutil.copy2(p, p.with_name(f"{p.name}.bak-{ts}"))
            write_json(p, d)
            touched.append(str(p))
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description="为专家/专家团设置头像并同步全部注册位置")
    ap.add_argument("--name", required=True, help="专家 name（kebab），设团队时传 teamId")
    ap.add_argument("--image", required=True, help="新头像图片（png/jpg/webp，建议 512×512 正方形）")
    ap.add_argument("--team", action="store_true", help="目标是专家团：写 user-teams.json 的 teams[].avatar")
    ap.add_argument("--display-name", default=None, help="团队显示名（teamId 不匹配时按名兜底）")
    ap.add_argument("--file-name", default=None, help="落盘文件名（默认 <name>.png），团队常用包名")
    ap.add_argument("--officeace-home", default="~/.office-claw", help="OfficeAce 数据目录")
    ap.add_argument("--app-root", default=None, help="OfficeAce 安装根（默认自动探测）")
    args = ap.parse_args()

    home = Path(args.officeace_home).expanduser()
    image = Path(args.image).expanduser()
    if not image.is_file():
        print(f"错误：图片不存在 {image}", file=sys.stderr)
        return 2
    app_root = Path(args.app_root).expanduser() if args.app_root else find_app_root(home)
    url = install_image(app_root, image, args.file_name or args.name)
    touched = (patch_team(home, args.name, args.display_name, url) if args.team
               else patch_expert(home, args.name, url))
    print(f"{args.name} → {url}")
    for t in touched:
        print(f"  写入 {t}")
    if not touched:
        print("  警告：没有匹配到任何注册项，仅复制了图片", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
