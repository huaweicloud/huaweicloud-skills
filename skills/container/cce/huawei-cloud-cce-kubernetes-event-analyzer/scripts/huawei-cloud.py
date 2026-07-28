#!/usr/bin/env python3
"""Command-line entry point for CCE Kubernetes Event queries."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List


def _parse_cli_params(args: List[str]) -> Dict[str, str]:
    """Parse key=value and --key=value/--key value arguments."""
    params: Dict[str, str] = {}
    index = 0
    while index < len(args):
        argument = args[index]
        if argument.startswith("--"):
            normalized = argument[2:]
            if "=" in normalized:
                key, value = normalized.split("=", 1)
                params[key.replace("-", "_")] = value
            elif index + 1 < len(args) and not args[index + 1].startswith("--"):
                params[normalized.replace("-", "_")] = args[index + 1]
                index += 1
            else:
                params[normalized.replace("-", "_")] = "true"
        elif "=" in argument:
            key, value = argument.split("=", 1)
            params[key.lstrip("-").replace("-", "_")] = value
        index += 1
    return params


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "action is required"}))
        return 1

    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from huawei_cloud.dispatcher import dispatch_action, is_registered_action

    action = sys.argv[1]
    if not is_registered_action(action):
        print(json.dumps({"success": False, "error": f"unknown action: {action}"}))
        return 1

    print(json.dumps(dispatch_action(action, _parse_cli_params(sys.argv[2:])), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
