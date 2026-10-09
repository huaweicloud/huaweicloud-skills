#!/usr/bin/env python3
"""ov_prime_agent.py — Prime Agent Python operations CLI.

Replaces all heredoc Python in agents/prime_agent.sh.

Subcommands:
    integrate <tpl> <shared_dir>       write init script + inject source block into template
    unbind-template <tpl> <shared_dir> remove source block / inline block from template
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ov_common import read_text, write_text, write_init, source_block


# ── Extension block written into ov-prime-agent-init.sh ──────────
# Shell variables ($PA_RUNTIME, $PRIME_AGENT_CODING_AGENT_DIR, ${OPENVIKING_URL:-...},
# etc.) are intentional literals — they are expanded by bash at source time, not by Python.
EXTENSION_BLOCK = """
# ── OpenViking memory extension (added by huawei-cloud-openviking-agent-integration skill) ──
# @openviking/pi-coding-agent-extension: TypeScript extension with auto-recall, auto-capture,
# context takeover, and 7 LLM tools. No build step, no MCP server — direct HTTP API.
export OPENVIKING_URL="${OPENVIKING_URL:-http://127.0.0.1:1933}"
OV_EXT_SRC="$PA_RUNTIME/openviking-extension"
OV_EXT_DST="$PRIME_AGENT_CODING_AGENT_DIR/extensions/openviking"
if [ -d "$OV_EXT_SRC" ]; then
  _ov_need_copy=false
  if [ ! -f "$OV_EXT_DST/index.ts" ] || ! diff -q "$OV_EXT_SRC/index.ts" "$OV_EXT_DST/index.ts" >/dev/null 2>&1; then
    _ov_need_copy=true
  fi
  if [ -d "$OV_EXT_SRC/shared" ] && [ ! -d "$OV_EXT_DST/shared" ]; then
    _ov_need_copy=true
  fi
  if [ "$_ov_need_copy" = true ]; then
    mkdir -p "$OV_EXT_DST"
    cp -a "$OV_EXT_SRC"/* "$OV_EXT_DST/"
    echo "OpenViking extension deployed to $OV_EXT_DST"
  else
    echo "OpenViking extension already up-to-date"
  fi
else
  echo "WARN: extension source not found at $OV_EXT_SRC, skipping"
fi
"""


def cmd_integrate(args):
    """Write ov-prime-agent-init.sh and inject a source block into the template start.sh.

    Exits 0 early when the template already contains the integration markers.
    Exits 1 when no known anchor (agentwork / acpws) is found in the template.
    """
    tpl_path, shared_dir = args[0], args[1]
    tpl = read_text(tpl_path)

    if "ov-prime-agent-init.sh" in tpl or "OpenViking memory extension" in tpl:
        sys.exit(0)

    init_path = f"{shared_dir}/ov-prime-agent-init.sh"
    write_init(
        init_path,
        "Prime Agent",
        "Sourced by the Prime Agent template start.sh (single source line).",
        EXTENSION_BLOCK.lstrip("\n"),
    )

    sb = source_block(shared_dir, "ov-prime-agent-init.sh")

    for anchor in ("# ── agentwork:", "# ── acpws:"):
        idx = tpl.find(anchor)
        if idx != -1:
            break
    else:
        print(
            "ERROR: no known anchor found in template start.sh (tried agentwork, acpws)",
            file=sys.stderr,
        )
        sys.exit(1)

    tpl = tpl[:idx] + sb + tpl[idx:]
    write_text(tpl_path, tpl)


def cmd_unbind_template(args):
    """Remove the OpenViking integration block from the template start.sh.

    Tries three patterns in order:
      1. Source-line block (current integrate format).
      2. Inline memory-extension block followed by a known anchor (older format).
      3. Inline block followed by any comment line (fallback).
    """
    path, shared_dir = args[0], args[1]
    content = read_text(path)
    removed = False

    # Pattern 1: Source-line block (current integrate format)
    source_block_pattern = (
        rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\n'
        rf'source {shared_dir}/ov-prime-agent-init\.sh\n'
        r'# ── End OpenViking integration ──\n\n'
    )
    new_content = re.sub(source_block_pattern, '', content)
    if new_content != content:
        write_text(path, new_content)
        print("Source-line block removed from template start.sh")
        content = new_content
        removed = True

    # Pattern 2: Inline memory-extension block (older integrate format)
    block_header = r'# ── OpenViking memory extension \(added by huawei-cloud-openviking-agent-integration skill\) ──'
    for anchor in ("# ── agentwork:", "# ── acpws:"):
        pattern = block_header + r'.*?\n\n(?=' + re.escape(anchor) + r')'
        new_content = re.sub(pattern, '', content, flags=re.DOTALL)
        if new_content != content:
            write_text(path, new_content)
            print(f"Inline block removed from template start.sh (anchor: {anchor})")
            content = new_content
            removed = True
            break

    if not removed:
        pattern = block_header + r'.*?\n\n(?=# ── )'
        new_content = re.sub(pattern, '', content, flags=re.DOTALL)
        if new_content != content:
            write_text(path, new_content)
            print("Inline block removed from template start.sh (fallback: next comment)")
            removed = True

    if not removed:
        print("No OpenViking block found in template (already clean)")


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "integrate": cmd_integrate,
        "unbind-template": cmd_unbind_template,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
