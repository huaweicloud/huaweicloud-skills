#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OptVerse 代码演化 - ZIP 打包辅助

仅做本地文件打包，不调用任何 hcloud 命令。
打包结果可作为 `hcloud OptVerse ImportAlgorithmFile --file=<out.zip>` 的输入。

典型流程（staging 目录方案；多文件场景推荐用此，跨 shell 稳定）：
  mkdir cvrp_pkg && cp algorithm.py evaluator.py cvrp_pkg/
  python scripts/zip_helper.py --src=./cvrp_pkg --out=./cvrp_algorithm.zip --force

注意：
  - `--out` 必须在 `--src` 之外，否则 zip 会自递归（把自己当文件打进去）
  - 默认排除 build/、__pycache__/、.git/、node_modules/ 与 .o/.so/.dll/.exe
"""

from __future__ import annotations

import argparse
import os
import zipfile


def build_zip(src_dir: str, out_path: str,
              exclude_exts: tuple[str, ...] = (".o", ".so", ".dll", ".exe"),
              overwrite: bool = False) -> str:
    """把 src_dir 下的文件按规则打包到 out_path。

    - 默认排除 build/、__pycache__/、.git/、node_modules/ 目录
    - 默认排除 .o / .so / .dll / .exe 后缀
    - 多文件场景推荐 staging 目录：建临时目录把目标文件 cp 进去，--src 指向该 staging
    - --out 必须在 --src 之外（否则 zip 自递归——见模块 docstring）
    """
    if os.path.exists(out_path) and not overwrite:
        raise FileExistsError(f"{out_path} 已存在；如需覆盖请设 overwrite=True")

    if not os.path.isdir(src_dir):
        raise FileNotFoundError(src_dir)

    src_abs = os.path.abspath(src_dir)
    out_abs = os.path.abspath(out_path)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_abs):
            # 排除常见的构建/缓存目录
            dirs[:] = [d for d in dirs if d not in
                       {"build", "__pycache__", ".git", "node_modules"}]
            for name in files:
                full = os.path.join(root, name)
                # 跳过 zip 输出自身（--out 在 --src 内时自递归）
                if os.path.abspath(full) == out_abs:
                    continue
                rel = os.path.relpath(full, src_abs)
                rel_norm = os.path.normpath(rel)

                if any(rel_norm.endswith(ext) for ext in exclude_exts):
                    continue
                zf.write(full, arcname=rel_norm)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="为 OptVerse 算法项目打包 zip")
    parser.add_argument("--src", required=True, help="源代码根目录")
    parser.add_argument("--out", required=True, help="输出 zip 路径（必须在 --src 外）")
    parser.add_argument("--force", action="store_true", help="覆盖已有文件")
    args = parser.parse_args()

    out = build_zip(args.src, args.out, overwrite=args.force)
    print(f"已生成: {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
