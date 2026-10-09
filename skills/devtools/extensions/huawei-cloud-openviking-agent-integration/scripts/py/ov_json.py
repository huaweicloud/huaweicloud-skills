#!/usr/bin/env python3
"""ov_json.py — JSON config manipulation CLI.

Replaces all inline ``python3 -c`` calls in lib/json.sh.

Subcommands:
    check-mcp <file>                     exit 0 if mcp.openviking.enabled is true
    get-mcp-url <file>                   print the openviking MCP URL
    read <file> <dotted.key> [default]   print value or default
    write <file> <dotted.key> <value>    set value (JSON literal)
    has-key <file> <dotted.key>          exit 0 if key exists
    remove-key <file> <dotted.key>       remove key
    parse-field <json-str> <field>       print field from JSON string
    merge-agents <ov-json> <agent-json>...  build status JSON
"""
import json
import sys
import os

# Allow imports from parent dir
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ov_common import load_json, save_json, dotted_get, dotted_set, dotted_exists, dotted_remove


def cmd_check_mcp(args):
    cfg = load_json(args[0])
    ok = cfg.get("mcp", {}).get("openviking", {}).get("enabled")
    sys.exit(0 if ok else 1)


def cmd_get_mcp_url(args):
    cfg = load_json(args[0])
    print(cfg.get("mcp", {}).get("openviking", {}).get("url", ""))


def cmd_read(args):
    file, key = args[0], args[1]
    default = args[2] if len(args) > 2 else ""
    cfg = load_json(file)
    val = dotted_get(cfg, key)
    print(val if val is not None else default)


def cmd_write(args):
    file, key, value = args[0], args[1], args[2]
    cfg = load_json(file)
    # value is a JSON literal (string, number, bool, null)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value  # treat as plain string
    dotted_set(cfg, key, parsed)
    save_json(file, cfg)


def cmd_has_key(args):
    cfg = load_json(args[0])
    sys.exit(0 if dotted_exists(cfg, args[1]) else 1)


def cmd_remove_key(args):
    file, key = args[0], args[1]
    cfg = load_json(file)
    dotted_remove(cfg, key)
    save_json(file, cfg)


def cmd_parse_field(args):
    """Parse a JSON string and print a top-level field."""
    raw, field = args[0], args[1]
    try:
        d = json.loads(raw)
        val = d.get(field, "")
        if isinstance(val, (dict, list)):
            print(json.dumps(val))
        else:
            print(val if val is not None else "")
    except Exception:
        print("")


def cmd_merge_agents(args):
    """Build the final status JSON from an ov-health JSON and agent JSON strings."""
    ov_json = json.loads(args[0])
    agents = [json.loads(s) for s in args[1:]]
    print(json.dumps({"openviking": ov_json, "agents": agents}, indent=2))


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "check-mcp": cmd_check_mcp,
        "get-mcp-url": cmd_get_mcp_url,
        "read": cmd_read,
        "write": cmd_write,
        "has-key": cmd_has_key,
        "remove-key": cmd_remove_key,
        "parse-field": cmd_parse_field,
        "merge-agents": cmd_merge_agents,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
