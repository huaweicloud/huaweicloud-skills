#!/usr/bin/env python3
"""Huawei Cloud CCE Cluster Management — entry point.

Parses CLI key=value args and dispatches to the modular dispatcher.
All tool logic is in huawei_cloud/dispatcher.py (data-driven) and
huawei_cloud/special_ops.py (special-case functions).
"""

import json
import os
import sys
from typing import Any, Dict, Optional


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing action parameter"}))
        sys.exit(1)

    action = sys.argv[1]
    params = _parse_cli_params(sys.argv[2:])

    # Ensure local huawei_cloud package is importable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from huawei_cloud.dispatcher import dispatch_action, is_registered_action

    if not is_registered_action(action):
        print(json.dumps({"success": False, "error": f"Unknown action: {action}"}))
        sys.exit(1)

    result = dispatch_action(action, params)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _parse_cli_params(args):
    """Parse key=value CLI arguments into a parameter mapping."""
    params = {}
    for arg in args:
        if "=" not in arg:
            continue
        key, value = arg.split("=", 1)
        params[key] = value
    return params


if __name__ == "__main__":
    main()
