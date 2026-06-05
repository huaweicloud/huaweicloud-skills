#!/usr/bin/env python
"""List Terraform variables and defaults from .tf / .tf.json files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Ensure sibling modules are importable regardless of CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sensitive_mask import mask_line


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Terraform variable defaults.")
    parser.add_argument("directory", help="Terraform template directory")
    return parser.parse_args()


def parse_tf_json_variables(path: Path) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return items

    variable_block = data.get("variable")
    if not isinstance(variable_block, dict):
        return items

    for name, cfg in variable_block.items():
        default = "<NO_DEFAULT>"
        if isinstance(cfg, dict) and "default" in cfg:
            value = cfg["default"]
            if isinstance(value, str):
                default = value
            else:
                default = json.dumps(value, ensure_ascii=False)
        items.append((str(name), default))
    return items


def parse_tf_hcl_variables(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    items: list[tuple[str, str]] = []

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
        items.append((name, default))

    return items


def main() -> int:
    args = parse_args()
    root = Path(args.directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Directory does not exist: {root}", file=sys.stderr)
        return 1

    pairs: list[tuple[str, str, str]] = []
    for p in sorted(root.rglob("*.tf.json")):
        for name, default in parse_tf_json_variables(p):
            pairs.append((name, default, str(p)))
    for p in sorted(root.rglob("*.tf")):
        for name, default in parse_tf_hcl_variables(p):
            pairs.append((name, default, str(p)))

    if not pairs:
        print("No Terraform variables found.")
        return 2

    for name, default, src in pairs:
        # Mask sensitive values in output.
        output_line = mask_line(f"{name}={default}")
        print(output_line)
        print(f"  source: {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
