#!/usr/bin/env python3
"""ov_health.py — OpenViking health-check and status helpers CLI.

Replaces inline ``python3 -c`` calls in lib/base.sh and scripts/status.sh.

Subcommands:
    parse-health <json-response>          print "status|version|auth_mode"
    parse-field <json-response> <field>   print a single field from health JSON
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_parse_health(args):
    """Print status|version|auth_mode from a health endpoint JSON response."""
    try:
        d = json.loads(args[0])
    except Exception:
        d = {}
    status = d.get("status", "unknown")
    version = d.get("version", "unknown")
    auth_mode = d.get("auth_mode", "unknown")
    print(f"{status}|{version}|{auth_mode}")


def cmd_parse_field(args):
    """Print a single field from a JSON string (stdin if first arg is '-')."""
    raw_arg, field = args[0], args[1]
    if raw_arg == "-":
        raw = sys.stdin.read()
    else:
        raw = raw_arg
    try:
        d = json.loads(raw)
        val = d.get(field, "")
        if val is None:
            val = ""
        print(val)
    except Exception:
        print("")


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "parse-health": cmd_parse_health,
        "parse-field": cmd_parse_field,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
