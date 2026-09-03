#!/usr/bin/env python3
"""List Terraform variables and defaults from .tf / .tf.json files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Terraform variable defaults.")
    parser.add_argument("directory", help="Terraform template directory")
    return parser.parse_args()


def parse_tf_json_variables(path: Path) -> list[tuple[str, str]]:
    items: list[tuple[str, str, bool]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return items

    variable_block = data.get("variable")
    if not isinstance(variable_block, dict):
        return items

    for name, cfg in variable_block.items():
        default = "<NO_DEFAULT>"
        sensitive = False
        if isinstance(cfg, dict) and "default" in cfg:
            value = cfg["default"]
            if isinstance(value, str):
                default = value
            else:
                default = json.dumps(value, ensure_ascii=False)
        if isinstance(cfg, dict):
            sensitive = bool(cfg.get("sensitive", False))
        items.append((str(name), default, sensitive))
    return items


def parse_tf_hcl_variables(path: Path) -> list[tuple[str, str, bool]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    items: list[tuple[str, str, bool]] = []

    for m in re.finditer(r'variable\s+"([^"]+)"\s*\{', text):
        name = m.group(1)
        block_start = m.end() - 1  # points to "{"
        depth = 0
        end = -1
        for i in range(block_start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end < 0:
            continue

        block = text[block_start + 1 : end]
        default = "<NO_DEFAULT>"
        default_match = re.search(r"(?m)^\s*default\s*=\s*(.+?)\s*$", block)
        if default_match:
            default = default_match.group(1).strip()
        sensitive = bool(re.search(r"(?mi)^\s*sensitive\s*=\s*true\s*$", block))
        items.append((name, default, sensitive))

    return items


def looks_sensitive_name(name: str) -> bool:
    return bool(
        re.search(
            r"(password|passwd|secret|token|access[_-]?key|secret[_-]?key|private[_-]?key|(^|[_-])ak($|[_-])|(^|[_-])sk($|[_-]))",
            name,
            flags=re.IGNORECASE,
        )
    )


def mask_value(value: str) -> str:
    if value in {"<NO_DEFAULT>", '""', "''"}:
        return value

    quote = ""
    raw = value
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        quote = value[0]
        raw = value[1:-1]

    if len(raw) <= 2:
        masked = "*" * len(raw)
    elif len(raw) <= 6:
        masked = raw[0] + ("*" * (len(raw) - 1))
    else:
        masked = raw[:2] + ("*" * (len(raw) - 4)) + raw[-2:]

    return f"{quote}{masked}{quote}" if quote else masked


def main() -> int:
    args = parse_args()
    root = Path(args.directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Directory does not exist: {root}", file=sys.stderr)
        return 1

    pairs: list[tuple[str, str, str, bool]] = []
    for p in sorted(root.rglob("*.tf.json")):
        for name, default, sensitive in parse_tf_json_variables(p):
            pairs.append((name, default, str(p), sensitive))
    for p in sorted(root.rglob("*.tf")):
        for name, default, sensitive in parse_tf_hcl_variables(p):
            pairs.append((name, default, str(p), sensitive))

    if not pairs:
        print("No Terraform variables found.")
        return 2

    for name, default, src, sensitive in pairs:
        safe_default = mask_value(default) if (sensitive or looks_sensitive_name(name)) else default
        print(f"{name}={safe_default}")
        print(f"  source: {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
