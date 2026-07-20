#!/usr/bin/env python3
"""Command-line entry point for Huawei Cloud CCE metric analyzer tools."""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List


def _parse_cli_params(args: List[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("--"):
            normalized = arg[2:]
            if "=" in normalized:
                key, value = normalized.split("=", 1)
                params[key.replace("-", "_")] = value
            elif index + 1 < len(args) and not args[index + 1].startswith("--"):
                params[normalized.replace("-", "_")] = args[index + 1]
                index += 1
            else:
                params[normalized.replace("-", "_")] = "true"
        elif "=" in arg:
            key, value = arg.split("=", 1)
            params[key.lstrip("-").replace("-", "_")] = value
        index += 1
    return params


def _exit_error(message: str, exit_code: int = 1) -> None:
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False))
    sys.exit(exit_code)


def main() -> None:
    if len(sys.argv) < 2:
        _exit_error("Missing action parameter")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from huawei_cloud.dispatcher import dispatch_action, is_registered_action

    action = sys.argv[1]
    params = _parse_cli_params(sys.argv[2:])
    if not is_registered_action(action):
        _exit_error(f"Unknown action: {action}")

    result = dispatch_action(action, params)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
