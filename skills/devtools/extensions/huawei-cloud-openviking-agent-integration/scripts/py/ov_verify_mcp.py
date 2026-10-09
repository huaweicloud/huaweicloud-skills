#!/usr/bin/env python3
"""ov_verify_mcp.py — MCP endpoint verification helpers CLI.

Replaces inline ``python3 -c`` calls in scripts/verify_mcp.sh.

Subcommands:
    parse-init <sse-data>          print "protocol server version"
    parse-tools <sse-data>         print tool count + names
    parse-health-tool <sse-data>   print health tool text result
    count-results <json-file>      print total result count from REST find
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _load_sse(data_str):
    """Extract the JSON payload from an SSE ``data:`` line or raw JSON."""
    for line in data_str.strip().splitlines():
        line = line.strip()
        if line.startswith("data: "):
            return json.loads(line[6:])
        if line.startswith("{"):
            return json.loads(line)
    return {}


def cmd_parse_init(args):
    try:
        data = args[0] if args else sys.stdin.read()
        r = _load_sse(data).get("result", {})
        proto = r.get("protocolVersion", "unknown")
        name = r.get("serverInfo", {}).get("name", "unknown")
        ver = r.get("serverInfo", {}).get("version", "unknown")
        print(f"{proto} {name} {ver}")
    except Exception as e:
        print("parse-error unknown unknown")


def cmd_parse_tools(args):
    try:
        data = args[0] if args else sys.stdin.read()
        d = _load_sse(data)
        tools = d.get("result", {}).get("tools", [])
        print(len(tools))
        for t in tools:
            desc = t.get("description", "")[:80]
            print(f"  - {t['name']}: {desc}")
    except Exception as e:
        print(f"parse-error: {e}")


def cmd_parse_health_tool(args):
    try:
        data = args[0] if args else sys.stdin.read()
        d = _load_sse(data)
        result = d.get("result", {})
        if isinstance(result, dict) and "content" in result:
            for c in result["content"]:
                if c.get("type") == "text":
                    print(c["text"][:200])
        else:
            print(str(result)[:200])
    except Exception as e:
        print(f"parse-error: {e}")


def cmd_count_results(args):
    """Count total results from a REST /api/v1/search/find response file."""
    try:
        with open(args[0]) as f:
            d = json.load(f)
        r = d.get("result", d)
        total = r.get("total", 0)
        if total == 0:
            total = (
                len(r.get("memories", []))
                + len(r.get("resources", []))
                + len(r.get("skills", []))
            )
        print(total)
    except Exception:
        print("parse-error")


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "parse-init": cmd_parse_init,
        "parse-tools": cmd_parse_tools,
        "parse-health-tool": cmd_parse_health_tool,
        "count-results": cmd_count_results,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
