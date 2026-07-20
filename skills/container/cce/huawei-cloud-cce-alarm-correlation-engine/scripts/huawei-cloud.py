#!/usr/bin/env python3
"""Huawei Cloud CCE alarm-correlation dispatcher."""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List


def _parse_cli_params(args: List[str]) -> Dict[str, str]:
    """Parse key=value and --key=value/--key value CLI arguments."""
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


def _load_dispatcher():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from huawei_cloud.dispatcher import dispatch_action, is_registered_action

    return dispatch_action, is_registered_action


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing action parameter"}))
        sys.exit(1)

    action = sys.argv[1]
    params = _parse_cli_params(sys.argv[2:])

    try:
        dispatch_action, is_registered_action = _load_dispatcher()
        if not is_registered_action(action):
            print(json.dumps({"success": False, "error": f"Unknown action: {action}"}))
            sys.exit(1)

        result = dispatch_action(action, params)
        print(json.dumps(result, indent=2, ensure_ascii=True))
    except Exception as exc:
        print(json.dumps({
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
