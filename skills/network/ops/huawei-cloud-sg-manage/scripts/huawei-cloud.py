#!/usr/bin/env python3
"""huawei-cloud-sg-manage dispatcher entry point.

Usage:
    python3 scripts/huawei-cloud.py <action> key=value [key=value ...]

Example:
    python3 scripts/huawei-cloud.py huawei_list_security_groups region=cn-north-4
    python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
        security_group_id=<sg-id> direction=ingress protocol=tcp port=22 remote=1.2.3.4/32
    python3 scripts/huawei-cloud.py huawei_create_security_group name=my-sg confirmed=true

All output is JSON on stdout. Manage actions (R2/R1) are write operations and
MUST be previewed (default) and explicitly approved by the user before running
with confirmed=true — see SKILL.md confirmation gates.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List


def _parse_cli_params(args: List[str]) -> Dict[str, str]:
    """Parse key=value and --key=value / --key value arguments."""
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
        elif "=" in arg:
            key, value = arg.split("=", 1)
            params[key.lstrip("-").replace("-", "_")] = value
        index += 1
    return params


def _load_dispatcher():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    from sg.dispatcher import dispatch_action, is_registered_action, list_actions
    return dispatch_action, is_registered_action, list_actions


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "missing action parameter"}))
        return 1

    action = sys.argv[1]
    params = _parse_cli_params(sys.argv[2:])

    try:
        dispatch_action, is_registered_action, list_actions = _load_dispatcher()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"success": False, "error": f"dispatcher load failed: {exc}"}))
        return 1

    if action in ("help", "--help", "-h", "list_actions", "huawei_list_sg_actions"):
        print(json.dumps(list_actions(), ensure_ascii=False))
        return 0

    if not is_registered_action(action):
        print(json.dumps({"success": False, "error": f"unknown action: {action}"}))
        return 1

    result = dispatch_action(action, params)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())