#!/usr/bin/env python3
"""Command-line entry point for the CCE Log Analyzer."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List


def _parse_params(args: List[str]) -> Dict[str, str]:
    params: Dict[str, str] = {}
    index = 0
    while index < len(args):
        argument = args[index]
        if argument.startswith("--"):
            key = argument[2:]
            if "=" in key:
                name, value = key.split("=", 1)
                params[name.replace("-", "_")] = value
            elif index + 1 < len(args) and not args[index + 1].startswith("--"):
                params[key.replace("-", "_")] = args[index + 1]
                index += 1
            else:
                params[key.replace("-", "_")] = "true"
        elif "=" in argument:
            key, value = argument.split("=", 1)
            params[key.lstrip("-").replace("-", "_")] = value
        index += 1
    return params


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "action is required; run 'python3 scripts/huawei-cloud.py help'"}))
        return 1
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from huawei_cloud.dispatcher import dispatch_action, is_registered_action, list_actions

    action = sys.argv[1]
    if action in {"help", "--help", "-h", "list"}:
        print(json.dumps({"success": True, "usage": "python3 scripts/huawei-cloud.py <action> key=value ...", "actions": list_actions()}, ensure_ascii=True, indent=2))
        return 0
    if not is_registered_action(action):
        print(json.dumps({"success": False, "error": f"unknown action: {action}"}))
        return 1
    print(json.dumps(dispatch_action(action, _parse_params(sys.argv[2:])), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
