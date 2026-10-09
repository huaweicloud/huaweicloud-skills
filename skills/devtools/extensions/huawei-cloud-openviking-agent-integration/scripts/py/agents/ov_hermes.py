#!/usr/bin/env python3
"""ov_hermes.py — Hermes agent Python operations CLI.

Replaces all heredoc Python in agents/hermes.sh.

Subcommands:
    integrate <tpl> <endpoint> <shared_dir>   write init script + inject source block
    clean-legacy-mcp <config.yaml>            remove legacy mcp_servers from live config
    unbind-template <tpl> <shared_dir>        remove source block from template
    unbind-live <config.yaml>                 remove MCP + memory provider from live config
    clean-snapshot <snapshot.json>            remove openviking entries from skills snapshot
    clean-usage <usage.json>                  remove openviking entries from skills usage
    clean-memory <MEMORY.md>                  remove openviking lines from MEMORY.md
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ov_common import read_text, write_text, write_init


def cmd_integrate(args):
    tpl_path, endpoint, shared_dir = args[0], args[1], args[2]
    tpl = read_text(tpl_path)

    block = f"""
# ── OpenViking memory provider (added by huawei-cloud-openviking-agent-integration skill) ──
# Re-injects memory.provider after model config is written on each start.
if ! grep -q "provider: openviking" "$HOME/.hermes/config.yaml" 2>/dev/null; then
  cat >> "$HOME/.hermes/config.yaml" << 'OVYAML'
memory:
  provider: openviking
  openviking:
    endpoint: {endpoint}
OVYAML
fi
if ! grep -q "OPENVIKING_ENDPOINT" "$HOME/.hermes/.env" 2>/dev/null; then
  echo "OPENVIKING_ENDPOINT='{endpoint}'" >> "$HOME/.hermes/.env"
fi
"""
    init_path = f"{shared_dir}/ov-hermes-init.sh"
    write_init(init_path, "Hermes", "integrate.sh", block.lstrip("\n"))

    sb = (
        "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\n"
        f"source {shared_dir}/ov-hermes-init.sh\n"
        "# ── End OpenViking integration ──\n\n"
    )
    m = re.search(r"(?m)^sleep infinity$", tpl)
    if not m:
        print("ERROR: insertion marker 'sleep infinity' not found in template", file=sys.stderr)
        sys.exit(1)
    tpl = tpl[: m.start()] + sb + tpl[m.start():]
    write_text(tpl_path, tpl)


def _clean_mcp_servers(content):
    content = re.sub(r"\n# OpenViking MCP server\nmcp_servers:\n  openviking:\n    url: [^\n]+\n", "\n", content)
    content = re.sub(r"\nmcp_servers:\n  openviking:\n    url: [^\n]+\n", "\n", content)
    content = re.sub(r"\nmcp_servers:\s*\n(?=\n[^ ])", "\n", content)
    return content


def cmd_clean_legacy_mcp(args):
    path = args[0]
    content = read_text(path)
    content = _clean_mcp_servers(content)
    write_text(path, content)


def cmd_unbind_template(args):
    path, shared_dir = args[0], args[1]
    content = read_text(path)
    content = re.sub(
        r"# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\n"
        + re.escape(f"source {shared_dir}/ov-hermes-init.sh\n")
        + r"# ── End OpenViking integration ──\n\n?",
        "",
        content,
    )
    write_text(path, content)


def cmd_unbind_live(args):
    path = args[0]
    content = read_text(path)
    content = _clean_mcp_servers(content)
    content = re.sub(
        r"\n# OpenViking native memory provider[^\n]*\nmemory:\n  provider: openviking\n  openviking:\n    endpoint: [^\n]+\n",
        "\n",
        content,
    )
    content = re.sub(r"\nmemory:\n  provider: openviking\n  openviking:\n    endpoint: [^\n]+\n", "\n", content)
    content = re.sub(r"\nmemory:\s*\n(?=\n[^ ])", "\n", content)
    content = content.rstrip() + "\n"
    write_text(path, content)


def cmd_clean_snapshot(args):
    path = args[0]
    with open(path) as f:
        data = json.load(f)
    data["manifest"] = {k: v for k, v in data.get("manifest", {}).items() if "openviking" not in k.lower()}
    data["skills"] = [s for s in data.get("skills", []) if "openviking" not in s.get("skill_name", "").lower()]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def cmd_clean_usage(args):
    path = args[0]
    with open(path) as f:
        data = json.load(f)
    data = {k: v for k, v in data.items() if "openviking" not in k.lower()}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def cmd_clean_memory(args):
    path = args[0]
    with open(path) as f:
        lines = f.readlines()
    cleaned = [l for l in lines if "openviking" not in l.lower() and "viking" not in l.lower() and "1933" not in l]
    with open(path, "w") as f:
        f.writelines(cleaned)


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "integrate": cmd_integrate,
        "clean-legacy-mcp": cmd_clean_legacy_mcp,
        "unbind-template": cmd_unbind_template,
        "unbind-live": cmd_unbind_live,
        "clean-snapshot": cmd_clean_snapshot,
        "clean-usage": cmd_clean_usage,
        "clean-memory": cmd_clean_memory,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
