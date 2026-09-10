#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yaml-check-frontmatter.py — 校验 SKILL.md 头部 YAML frontmatter 合法性。

用法: 在 skill 目录下运行 (读取 ./SKILL.md):
    python yaml-check-frontmatter.py

输出与退出码:
    OK                  (exit 0)  -> frontmatter 是合法 YAML 且字段合规
    ERR:<detail>        (exit 1)  -> 语法或字段错误
    NO_PYYAML           (exit 0)  -> 未安装 PyYAML, 深度校验跳过(由调用方降级)
"""
import sys
from pathlib import Path


def main() -> int:
    try:
        import yaml  # noqa: F401
    except Exception:
        print("NO_PYYAML")
        return 0

    try:
        text = Path("SKILL.md").read_text(encoding="utf-8")
    except Exception as e:
        print(f"ERR:read {e}")
        return 1

    if not text.startswith("---"):
        print("ERR:frontmatter must start with ---")
        return 1

    parts = text.split("---", 2)
    if len(parts) < 3:
        print("ERR:closing --- missing")
        return 1

    try:
        data = yaml.safe_load(parts[1])
    except Exception as e:
        print("ERR:yaml " + str(e).replace("\n", " ")[:200])
        return 1

    if not isinstance(data, dict):
        print("ERR:root must be a map")
        return 1

    errs = []
    if not str(data.get("name") or "").strip():
        errs.append("name empty")
    if not str(data.get("description") or "").strip():
        errs.append("description empty")
    if "tags" in data and not isinstance(data["tags"], list):
        errs.append("tags must be a list")
    if isinstance(data.get("tags"), list) and len(data["tags"]) > 5:
        errs.append("tags > 5")
    if "version" in data:
        errs.append("version field must be absent")

    if errs:
        print("ERR:fields " + "; ".join(errs))
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())