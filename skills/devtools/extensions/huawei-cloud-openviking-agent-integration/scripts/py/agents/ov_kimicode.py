#!/usr/bin/env python3
"""ov_kimicode.py — KimiCode agent Python operations CLI.

Replaces all heredoc / inline Python in agents/kimicode.sh.

Subcommands:
    integrate <tpl> <mcp_url> <shared_dir> <template_dir> <runtime_dir>
        Deploy MCP mcp.json injection + session lifecycle hooks (path 3:
        hooks + MCP) into template start.sh; deploy hook dispatcher
        (shared/ov-kimi-hook/) + py helpers (shared/py/) for runtime use.
    write-live-mcp <mcp.json> <mcp_url>
    append-hooks-config <config.toml> <shared_dir>
        Append [[hooks]] section to config.toml idempotently (live effect).
    strip-hooks-config <config.toml>
        Remove the OpenViking [[hooks]] section from config.toml.
    check-hooks <config.toml>         exit 0 if OpenViking hooks present
    unbind-hooks <shared_dir> <runtime_dir>
        Remove deployed hook dispatcher + py helpers (OV-owned only).
    unbind-template <tpl> <shared_dir>
    unbind-live-mcp <mcp.json>
    unbind-legacy-toml <config.toml>
    check-live-mcp <mcp.json>          exit 0 if openviking present
    get-live-mcp-url <mcp.json>        print URL (empty if absent)
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ov_common import read_text, write_text

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "templates", "agents-md-snippet.md")) as _f:
    AGENTS_MD = _f.read()

OV_CONFIG_JSON = """{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 10,
    "scoreThreshold": 0.35,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recallLimit": 15,
  "recallMaxContentChars": 20000,
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
"""

# ── Session lifecycle hooks (path 3: hooks + MCP) ──────────────────────────
# Recovered from git history (5a6634e-era production config): kimi-code reads
# [[hooks]] from config.toml; each entry dispatches to the shared hook script
# with the lowercase event as argv[1]. Event names are CamelCase per the
# kimi-code hook protocol.
HOOKS_MARKER = "# ── OpenViking hooks"
HOOKS_FIRST_LINE = "# ── OpenViking hooks (session lifecycle, managed by huawei-cloud-openviking-agent-integration skill) ──"


def _hooks_toml(shared_dir):
    """TOML [[hooks]] section for config.toml (kimi-code session lifecycle)."""
    return (
        HOOKS_FIRST_LINE + "\n"
        "[[hooks]]\n"
        'event = "SessionStart"\n'
        f'command = "{shared_dir}/ov-kimi-hook/ov-kimi-hook.sh session-start"\n'
        "timeout = 10\n"
        "[[hooks]]\n"
        'event = "UserPromptSubmit"\n'
        f'command = "{shared_dir}/ov-kimi-hook/ov-kimi-hook.sh user-prompt"\n'
        "timeout = 15\n"
        "[[hooks]]\n"
        'event = "Stop"\n'
        f'command = "{shared_dir}/ov-kimi-hook/ov-kimi-hook.sh stop"\n'
        "timeout = 30\n"
        "[[hooks]]\n"
        'event = "SessionEnd"\n'
        f'command = "{shared_dir}/ov-kimi-hook/ov-kimi-hook.sh session-end"\n'
        "timeout = 30\n"
        "[[hooks]]\n"
        'event = "PreCompact"\n'
        f'command = "{shared_dir}/ov-kimi-hook/ov-kimi-hook.sh pre-compact"\n'
        "timeout = 30\n"
    )


def _strip_ov_hooks(content):
    """Idempotent: drop any previous OpenViking hooks section (always appended last)."""
    if HOOKS_MARKER in content:
        content = content.split(HOOKS_MARKER)[0].rstrip()
    return content


def _scripts_dir():
    """Absolute path of the skill's scripts/ directory (…/scripts/lib, …/scripts/py live there)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def cmd_deploy_hook_files(args):
    """Deploy the hook dispatcher + py helpers for runtime use.

    Layout MUST live under <shared_dir> (ro-bound into the bwrap sandbox):
      <shared_dir>/ov-kimi-hook/ov-kimi-hook.sh   dispatcher
      <shared_dir>/py/ov_kimi_hook.py ...          helpers
    Dispatcher resolves OV_PY_DIR = $(dirname $0)/../py → <shared_dir>/py,
    i.e. inside the shared mount — visible to hooks running in the sandbox.
    """
    shared_dir, runtime_dir = args[0], args[1]
    scripts_dir = _scripts_dir()

    bundle_dir = os.path.join(shared_dir, "ov-kimi-hook")
    os.makedirs(bundle_dir, exist_ok=True)
    dst_sh = os.path.join(bundle_dir, "ov-kimi-hook.sh")
    shutil.copy2(os.path.join(scripts_dir, "lib", "ov_kimi_hook.sh"), dst_sh)
    os.chmod(dst_sh, 0o755)
    print(f"deployed {dst_sh}")

    py_dir = os.path.join(shared_dir, "py")
    os.makedirs(py_dir, exist_ok=True)
    src_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    for name in ("ov_kimi_hook.py", "ov_redact.py", "ov_common.py"):
        dst = os.path.join(py_dir, name)
        shutil.copy2(os.path.join(src_py, name), dst)
        print(f"deployed {dst}")


def cmd_append_hooks_config(args):
    """Append the [[hooks]] section to a config.toml (idempotent). Live effect."""
    config_path, shared_dir = args[0], args[1]
    if not os.path.exists(config_path):
        print("config.toml not found — skipped")
        return
    with open(config_path, encoding="utf-8") as f:
        content = f.read()
    content = _strip_ov_hooks(content)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content + "\n" + _hooks_toml(shared_dir))
    print("OpenViking hooks injected into config.toml")


def cmd_strip_hooks_config(args):
    config_path = args[0]
    if not os.path.exists(config_path):
        print("config.toml not found")
        return
    with open(config_path, encoding="utf-8") as f:
        content = f.read()
    if HOOKS_MARKER in content:
        new = _strip_ov_hooks(content) + "\n"
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new)
        print("OpenViking hooks removed from config.toml")
    else:
        print("no OpenViking hooks in config.toml")


def cmd_check_hooks(args):
    config_path = args[0]
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as f:
            if HOOKS_MARKER in f.read():
                sys.exit(0)
    sys.exit(1)


def _remove_ov_py_helpers(py_dir, scripts_dir):
    """Remove OV-owned py helpers from a py dir; ov_common.py is byte-compared
    with the skill copy before removal (defensive against user-modified files)."""
    if not os.path.isdir(py_dir):
        return
    for name in ("ov_kimi_hook.py", "ov_redact.py"):
        p = os.path.join(py_dir, name)
        if os.path.exists(p):
            os.remove(p)
            print(f"removed {py_dir}/{name}")
    common_src = os.path.join(scripts_dir, "py", "ov_common.py")
    common_dst = os.path.join(py_dir, "ov_common.py")
    if os.path.exists(common_dst):
        with open(common_dst, "rb") as f:
            dst_data = f.read()
        with open(common_src, "rb") as f:
            src_data = f.read()
        if dst_data == src_data:
            os.remove(common_dst)
            print(f"removed {py_dir}/ov_common.py")
        else:
            print(f"WARN: {py_dir}/ov_common.py differs from skill copy — left untouched")
    cache_dir = os.path.join(py_dir, "__pycache__")
    if os.path.isdir(cache_dir):
        for fn in os.listdir(cache_dir):
            if fn.startswith(("ov_kimi_hook.", "ov_redact.", "ov_common.")) and fn.endswith((".pyc", ".pyo")):
                os.remove(os.path.join(cache_dir, fn))
        if not os.listdir(cache_dir):
            os.rmdir(cache_dir)
    if not os.listdir(py_dir):
        os.rmdir(py_dir)
        print(f"removed empty {py_dir}")


def cmd_unbind_hooks(args):
    """Remove deployed hook dispatcher + py helpers (OV-owned only)."""
    shared_dir, runtime_dir = args[0], args[1]
    scripts_dir = _scripts_dir()

    # New layout: <shared_dir>/ov-kimi-hook/ (entirely OV-owned — safe to remove)
    bundle_dir = os.path.join(shared_dir, "ov-kimi-hook")
    if os.path.isdir(bundle_dir):
        shutil.rmtree(bundle_dir)
        print(f"removed {bundle_dir}/")
    else:
        print("ov-kimi-hook/ not deployed")

    # New helpers dir (sandbox-visible): <shared_dir>/py/
    _remove_ov_py_helpers(os.path.join(shared_dir, "py"), scripts_dir)

    # Legacy layout (pre-2026-09-21): dispatcher at shared root + helpers in runtime/py
    legacy_sh = os.path.join(shared_dir, "ov-kimi-hook.sh")
    if os.path.exists(legacy_sh):
        os.remove(legacy_sh)
        print(f"removed legacy {legacy_sh}")
    _remove_ov_py_helpers(os.path.join(runtime_dir, "py"), scripts_dir)


def cmd_integrate(args):
    tpl_path, url, shared_dir, template_dir, runtime_dir = args[0], args[1], args[2], args[3], args[4]
    content = read_text(tpl_path)
    marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
    if "ov-kimicode-init.sh" in content or marker in content:
        print("already")
        return

    hooks_toml = _hooks_toml(shared_dir)

    block = f"""# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──
# kimi-code reads MCP config from mcp.json (NOT config.toml, which is recreated on each start).
_ov_py=""
for _py in python3.12 python3.11 python3.10 python3; do command -v "$_py" >/dev/null 2>&1 && _ov_py="$_py" && break; done
: "${{_ov_py:=python3}}"
MCP_FILE="$KIMI_CODE_HOME/mcp.json"
$_ov_py - "$MCP_FILE" <<'MCPEOF'
import json, sys, os
path = sys.argv[1]
entry = {{"url": "{url}"}}
if os.path.exists(path):
    with open(path) as f:
        cfg = json.load(f)
else:
    cfg = {{}}
servers = cfg.setdefault("mcpServers", {{}})
if "openviking" not in servers:
    servers["openviking"] = entry
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    print("OpenViking MCP injected into mcp.json")
else:
    print("OpenViking MCP already in mcp.json")
MCPEOF
mkdir -p /workspace
cat > /workspace/AGENTS.md << 'AGENTSMD'
{AGENTS_MD}AGENTSMD
OV_CONF_DIR="$HOME/.config/opencode"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{OV_CONFIG_JSON}OVCONF
fi
# ── OpenViking session lifecycle hooks (path 3: hooks + MCP) ──
# Every boot regenerates config.toml → re-append [[hooks]] so session hooks
# (auto-recall, auto-capture, auto-commit) persist across restarts.
CONFIG_FILE="$KIMI_CODE_HOME/config.toml"
if [ -f "$CONFIG_FILE" ]; then
  $_ov_py - "$CONFIG_FILE" <<'HOOKEOF'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()
if "# ── OpenViking hooks" in content:
    content = content.split("# ── OpenViking hooks")[0].rstrip()
with open(path, "w") as f:
    f.write(content.rstrip() + "\\n")
HOOKEOF
  cat >> "$CONFIG_FILE" <<'HOOKTOML'
{hooks_toml}HOOKTOML
fi
"""

    init_path = f"{shared_dir}/ov-kimicode-init.sh"
    with open(init_path, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write("# ── OpenViking integration for KimiCode ──\n")
        f.write(f"# Sourced by {template_dir}/kimicode/start.sh (single source line).\n")
        f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
        f.write(block)
    os.chmod(init_path, 0o755)

    source_block = (
        "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\n"
        f"source {shared_dir}/ov-kimicode-init.sh\n"
        "# ── End OpenViking integration ──\n"
    )

    lines = content.split("\n")
    inserted = False
    for i, line in enumerate(lines):
        if line.strip() == "sleep infinity" or line.strip().startswith("sleep infinity"):
            lines.insert(i, source_block.rstrip())
            lines.insert(i + 1, "")
            inserted = True
            break
    if not inserted:
        lines.append(source_block.rstrip())
        lines.append("")
    write_text(tpl_path, "\n".join(lines))
    print("injected")

    # Deploy hook dispatcher + py helpers (runtime side)
    cmd_deploy_hook_files([shared_dir, runtime_dir])


def cmd_write_live_mcp(args):
    path, url = args[0], args[1]
    entry = {"url": url}
    if os.path.exists(path):
        with open(path) as f:
            cfg = json.load(f)
    else:
        cfg = {}
    servers = cfg.setdefault("mcpServers", {})
    if "openviking" not in servers:
        servers["openviking"] = entry
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
        print("injected")
    else:
        print("already exists")


def cmd_unbind_template(args):
    path, shared_dir = args[0], args[1]
    content = read_text(path)
    # First try new-style: 3-line source block
    new_pattern = (
        r"# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\n"
        + re.escape(f"source {shared_dir}/ov-kimicode-init.sh\n")
        + r"# ── End OpenViking integration ──\n\n?"
    )
    new_content = re.sub(new_pattern, "", content)
    if new_content != content:
        write_text(path, new_content)
        print("removed new-style source block")
        return
    # Fall back to old-style: full inline block
    lines = content.splitlines(keepends=True)
    marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
    marker_legacy = "# ── OpenViking MCP injection (added by openviking-agent-integration skill) ──"
    start = None
    for i, line in enumerate(lines):
        if (marker in line or marker_legacy in line) and start is None:
            start = i
            break
    end = None
    if start is not None:
        found_config = False
        for i in range(start, len(lines)):
            if "# Create openviking-config.json" in lines[i]:
                found_config = True
            if found_config and lines[i].strip() == "fi":
                end = i + 1
                break
        if end is None:
            for i in range(start, len(lines)):
                if lines[i].strip() == "AGENTSMD":
                    end = i + 1
                    break
    if start is not None and end is not None:
        if end < len(lines) and lines[end].strip() == "":
            end += 1
        del lines[start:end]
        write_text(path, "".join(lines))
        print("removed MCP injection block")
    else:
        write_text(path, "".join(lines))
        print("MCP injection block not found")


def cmd_unbind_live_mcp(args):
    path = args[0]
    with open(path) as f:
        d = json.load(f)
    servers = d.get("mcpServers", {})
    if "openviking" in servers:
        del servers["openviking"]
        if not servers:
            del d["mcpServers"]
        with open(path, "w") as f:
            json.dump(d, f, indent=2)


def cmd_unbind_legacy_toml(args):
    path = args[0]
    lines = []
    skip = False
    with open(path) as f:
        for line in f:
            if line.strip().startswith("[mcp_servers.openviking]"):
                skip = True
                continue
            if skip and (line.strip().startswith("[") or line.strip() == ""):
                if line.strip().startswith("["):
                    skip = False
                else:
                    continue
            if not skip:
                lines.append(line)
    while lines and lines[-1].strip() == "":
        lines.pop()
    with open(path, "w") as f:
        f.writelines(lines)
        f.write("\n")


def cmd_check_live_mcp(args):
    path = args[0]
    with open(path) as f:
        d = json.load(f)
    sys.exit(0 if "openviking" in d.get("mcpServers", {}) else 1)


def cmd_get_live_mcp_url(args):
    path = args[0]
    with open(path) as f:
        d = json.load(f)
    print(d.get("mcpServers", {}).get("openviking", {}).get("url", ""))


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "integrate": cmd_integrate,
        "deploy-hook-files": cmd_deploy_hook_files,
        "append-hooks-config": cmd_append_hooks_config,
        "strip-hooks-config": cmd_strip_hooks_config,
        "check-hooks": cmd_check_hooks,
        "unbind-hooks": cmd_unbind_hooks,
        "write-live-mcp": cmd_write_live_mcp,
        "unbind-template": cmd_unbind_template,
        "unbind-live-mcp": cmd_unbind_live_mcp,
        "unbind-legacy-toml": cmd_unbind_legacy_toml,
        "check-live-mcp": cmd_check_live_mcp,
        "get-live-mcp-url": cmd_get_live_mcp_url,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()