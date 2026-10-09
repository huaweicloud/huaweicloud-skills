#!/usr/bin/env python3
"""ov_codearts.py — CodeArts CLI agent Python operations CLI.

Replaces all heredoc Python and inline ``python3 -c`` calls in
agents/codearts.sh.

Subcommands:
    register-plugin <codearts_cli.json>       add @openviking/opencode-plugin to plugin list, clean old MCP+prompt
    inject-template <tpl> <sdk_ver> <plugin_ver> <npm_registry> <plugin_cache_dir> <shared_dir>
                                             write init script + inject source block into template
    has-plugin <codearts_cli.json>            exit 0 if plugin in list, 1 otherwise
    has-prompt <codearts_cli.json>            exit 0 if 'OpenViking' in agent.build.prompt, 1 otherwise
    unbind-template <tpl>                     remove OpenViking integration block from template
    remove-plugin <codearts_cli.json>         remove plugin + old MCP+prompt from codearts_cli.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ov_common import (
    read_text,
    write_text,
    write_init,
    source_block,
    load_json,
)

OV_PLUGIN = "@openviking/opencode-plugin"


# ── register-plugin (PYREG heredoc) ──────────────────────────
def cmd_register_plugin(args):
    """Add @openviking/opencode-plugin to plugin list; clean old MCP+prompt."""
    path = args[0]
    cfg = load_json(path)
    changed = False
    plugins = cfg.setdefault("plugin", [])
    if OV_PLUGIN not in plugins:
        plugins.append(OV_PLUGIN)
        changed = True
    if "mcp" in cfg and "openviking" in cfg["mcp"]:
        del cfg["mcp"]["openviking"]
        if not cfg["mcp"]:
            del cfg["mcp"]
        changed = True
    if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
        del cfg["agent"]["build"]["prompt"]
        if not cfg["agent"]["build"]:
            del cfg["agent"]["build"]
        if not cfg["agent"]:
            del cfg["agent"]
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("Plugin registered (old MCP+prompt cleaned)")


# ── inject-template (PYTPL heredoc) ──────────────────────────
def cmd_inject_template(args):
    """Generate cache-first plugin deployment init script and inject into template."""
    tpl_path = args[0]
    sdk_ver = args[1]
    plugin_ver = args[2]
    npm_registry = args[3]
    plugin_cache_dir = args[4]
    shared_dir = args[5]

    tpl = read_text(tpl_path)

    block = """
export NPM_CONFIG_REGISTRY=__OV_NPM_REGISTRY__
export npm_config_prefer_offline=true
export npm_config_package_lock=true
OV_NPM_DIR="$HOME/.codeartsdoer"
mkdir -p "$OV_NPM_DIR/node_modules/@openviking"
OV_PLUGIN_DST="$OV_NPM_DIR/node_modules/@openviking/opencode-plugin"
OV_PLUGIN_CACHE="$HOME/.cache/codeartsdoer/packages/@openviking/opencode-plugin@latest/node_modules/@openviking/opencode-plugin"
OV_PLUGIN_SHARED="__OV_PLUGIN_CACHE_DIR__/@openviking/opencode-plugin"
OV_PLUGIN_SOURCE="none"
if [[ -d "$OV_PLUGIN_DST" && -f "$OV_PLUGIN_DST/package.json" ]]; then
  OV_PLUGIN_SOURCE="existing"
fi
if [[ "$OV_PLUGIN_SOURCE" == "none" && -d "$OV_PLUGIN_SHARED" && -f "$OV_PLUGIN_SHARED/package.json" ]]; then
  _cache_age=$(( $(date +%s) - $(stat -c %Y "$OV_PLUGIN_SHARED" 2>/dev/null || echo 0) ))
  if [[ $_cache_age -le 86400 ]]; then
    rm -rf "$OV_PLUGIN_DST"
    cp -a "$OV_PLUGIN_SHARED" "$OV_PLUGIN_DST"
    OV_PLUGIN_SOURCE="shared-cache"
    if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" && -d "$OV_PLUGIN_SHARED/../../@opencode-ai" ]]; then
      cp -a "$OV_PLUGIN_SHARED/../../@opencode-ai" "$OV_NPM_DIR/node_modules/@opencode-ai"
    fi
  fi
fi
if [[ "$OV_PLUGIN_SOURCE" == "none" && -d "$OV_PLUGIN_CACHE" ]]; then
  rm -rf "$OV_PLUGIN_DST"
  cp -a "$OV_PLUGIN_CACHE" "$OV_PLUGIN_DST"
  OV_PLUGIN_SOURCE="cache"
fi
if [[ "$OV_PLUGIN_SOURCE" == "none" ]]; then
  if command -v npm &>/dev/null; then
    cat > "$OV_NPM_DIR/package.json" <<'PKGEOF'
{"dependencies":{"@opencode-ai/plugin":"__OV_PLUGIN_SDK_VER__","@openviking/opencode-plugin":"__OV_OPENCODE_PLUGIN_VER__"}}
PKGEOF
    if (cd "$OV_NPM_DIR" && npm install --registry=__OV_NPM_REGISTRY__ --no-audit --no-fund 2>&1 | tail -5) && \\
       [[ -d "$OV_PLUGIN_DST" ]]; then
      OV_PLUGIN_SOURCE="npm"
      mkdir -p "$(dirname "$OV_PLUGIN_SHARED")"
      rm -rf "$OV_PLUGIN_SHARED"
      cp -a "$OV_PLUGIN_DST" "$OV_PLUGIN_SHARED"
      touch "$OV_PLUGIN_SHARED"
      if [[ -d "$OV_NPM_DIR/node_modules/@opencode-ai" ]]; then
        rm -rf "$OV_PLUGIN_SHARED/../../@opencode-ai"
        cp -a "$OV_NPM_DIR/node_modules/@opencode-ai" "$OV_PLUGIN_SHARED/../../@opencode-ai"
      fi
    else
      echo "WARN: npm install failed — plugin will not load"
    fi
  else
    echo "WARN: npm not found and no cache available — plugin will not load"
  fi
fi
if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" ]]; then
  if [[ -d "$OV_PLUGIN_SHARED/../../@opencode-ai" ]]; then
    cp -a "$OV_PLUGIN_SHARED/../../@opencode-ai" "$OV_NPM_DIR/node_modules/@opencode-ai"
  elif command -v npm &>/dev/null; then
    cat > "$OV_NPM_DIR/package.json" <<'PKGEOF2'
{"dependencies":{"@opencode-ai/plugin":"__OV_PLUGIN_SDK_VER__"}}
PKGEOF2
    (cd "$OV_NPM_DIR" && npm install --registry=__OV_NPM_REGISTRY__ --no-audit --no-fund 2>&1 | tail -5) || \\
      echo "WARN: Plugin SDK install failed"
  fi
fi
_ov_py=""
for _py in python3.12 python3.11 python3.10 python3; do command -v "$_py" >/dev/null 2>&1 && _ov_py="$_py" && break; done
: "${_ov_py:=python3}"
OV_PLUGIN_VER="__OV_OPENCODE_PLUGIN_VER__"
OV_SDK_VER="__OV_PLUGIN_SDK_VER__"
if [[ -f "$OV_NPM_DIR/node_modules/@opencode-ai/plugin/package.json" ]]; then
  OV_SDK_VER=$($_ov_py -c "import json; print(json.load(open('$OV_NPM_DIR/node_modules/@opencode-ai/plugin/package.json')).get('version','__OV_PLUGIN_SDK_VER__'))" 2>/dev/null || echo "__OV_PLUGIN_SDK_VER__")
fi
if [[ -f "$OV_NPM_DIR/node_modules/@openviking/opencode-plugin/package.json" ]]; then
  OV_PLUGIN_VER=$($_ov_py -c "import json; print(json.load(open('$OV_NPM_DIR/node_modules/@openviking/opencode-plugin/package.json')).get('version','__OV_OPENCODE_PLUGIN_VER__'))" 2>/dev/null || echo "__OV_OPENCODE_PLUGIN_VER__")
fi
cat > "$OV_NPM_DIR/package.json" <<PKGLCK
{"dependencies":{"@opencode-ai/plugin":"$OV_SDK_VER","@openviking/opencode-plugin":"$OV_PLUGIN_VER"}}
PKGLCK
cat > "$OV_NPM_DIR/package-lock.json" <<LOCKEOF
{"name":"","version":"1.0.0","lockfileVersion":3,"requires":true,"packages":{"":{"dependencies":{"@opencode-ai/plugin":"$OV_SDK_VER","@openviking/opencode-plugin":"$OV_PLUGIN_VER"}},"node_modules/@opencode-ai/plugin":{"version":"$OV_SDK_VER","resolved":"","integrity":""},"node_modules/@openviking/opencode-plugin":{"version":"$OV_PLUGIN_VER","resolved":"","integrity":""}}}
LOCKEOF
CODEARTS_CFG="$HOME/.codeartsdoer/codearts_cli.json"
if [[ -f "$CODEARTS_CFG" ]]; then
  $_ov_py - "$CODEARTS_CFG" <<'OVREG' || true
import json, sys
path = sys.argv[1]
with open(path) as f: cfg = json.load(f)
changed = False
plugins = cfg.setdefault("plugin", [])
if "@openviking/opencode-plugin" not in plugins: plugins.append("@openviking/opencode-plugin"); changed = True
if "mcp" in cfg and "openviking" in cfg["mcp"]:
    del cfg["mcp"]["openviking"]
    if not cfg["mcp"]: del cfg["mcp"]
    changed = True
if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
    del cfg["agent"]["build"]["prompt"]
    if not cfg["agent"]["build"]: del cfg["agent"]["build"]
    if not cfg["agent"]: del cfg["agent"]
    changed = True
if changed:
    with open(path, "w") as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("Plugin registered in codearts_cli.json")
OVREG
fi
OV_CONF_DIR="$HOME/.codeartsdoer"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{"enabled":true,"timeoutMs":30000,"repoContext":{"enabled":true,"cacheTtlMs":60000},"autoRecall":{"enabled":true,"limit":10,"scoreThreshold":0.35,"maxContentChars":500,"preferAbstract":true,"tokenBudget":2000,"minQueryLength":3},"recallLimit":15,"recallMaxContentChars":20000,"commitTokenThreshold":20000,"commitKeepRecentCount":10,"profileTokenBudget":10000,"resumeContextBudget":32000}
OVCONF
fi
"""
    block = block.replace("__OV_NPM_REGISTRY__", npm_registry)
    block = block.replace("__OV_PLUGIN_SDK_VER__", sdk_ver)
    block = block.replace("__OV_OPENCODE_PLUGIN_VER__", plugin_ver)
    block = block.replace("__OV_PLUGIN_CACHE_DIR__", plugin_cache_dir)

    init_path = f"{shared_dir}/ov-codearts-init.sh"
    write_init(init_path, "CodeArts", "Sourced by the CodeArts template start.sh.", block.lstrip("\n"))

    sb = source_block(shared_dir, "ov-codearts-init.sh")

    marker = 'echo "Starting CodeArts..."'
    idx = tpl.find(marker)
    if idx == -1:
        marker = "sleep infinity"
        idx = tpl.find(marker)
    if idx == -1:
        print("ERROR: insertion marker not found", file=sys.stderr)
        sys.exit(1)
    tpl = tpl[:idx] + sb + tpl[idx:]
    write_text(tpl_path, tpl)


# ── has-plugin (inline python3 -c) ───────────────────────────
def cmd_has_plugin(args):
    """Exit 0 if @openviking/opencode-plugin is in the plugin list, 1 otherwise."""
    path = args[0]
    cfg = load_json(path)
    sys.exit(0 if OV_PLUGIN in cfg.get("plugin", []) else 1)


# ── has-prompt (inline python3 -c) ───────────────────────────
def cmd_has_prompt(args):
    """Exit 0 if 'OpenViking' appears in agent.build.prompt, 1 otherwise."""
    path = args[0]
    cfg = load_json(path)
    prompt = cfg.get("agent", {}).get("build", {}).get("prompt", "")
    sys.exit(0 if "OpenViking" in prompt else 1)


# ── unbind-template (PYUNBIND heredoc) ───────────────────────
def cmd_unbind_template(args):
    """Remove OpenViking integration block from template."""
    path = args[0]
    content = read_text(path)
    marker = "# ── OpenViking integration"
    idx = content.find(marker)
    if idx != -1:
        end_marker = "# ── End OpenViking integration ──"
        end_idx = content.find(end_marker, idx)
        if end_idx != -1:
            end_pos = end_idx + len(end_marker)
            while end_pos < len(content) and content[end_pos] == '\n':
                end_pos += 1
            write_text(path, content[:idx] + content[end_pos:])
            print("Removed OpenViking integration block from template")
        else:
            print("WARNING: end marker not found, skipping template removal")
    else:
        print("No OpenViking integration block found in template")


# ── remove-plugin (PYUNBIND2 heredoc) ────────────────────────
def cmd_remove_plugin(args):
    """Remove @openviking/opencode-plugin + old MCP+prompt from codearts_cli.json."""
    path = args[0]
    cfg = load_json(path)
    changed = False
    if "plugin" in cfg and OV_PLUGIN in cfg["plugin"]:
        cfg["plugin"].remove(OV_PLUGIN)
        if not cfg["plugin"]:
            del cfg["plugin"]
        changed = True
    if "mcp" in cfg and "openviking" in cfg["mcp"]:
        del cfg["mcp"]["openviking"]
        if not cfg["mcp"]:
            del cfg["mcp"]
        changed = True
    if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
        del cfg["agent"]["build"]["prompt"]
        if not cfg["agent"]["build"]:
            del cfg["agent"]["build"]
        if not cfg["agent"]:
            del cfg["agent"]
        changed = True
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("Removed OpenViking from codearts_cli.json")


def main():
    if len(sys.argv) < 2:
        print("Usage: ov_codearts.py <subcommand> [args...]", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "register-plugin": cmd_register_plugin,
        "inject-template": cmd_inject_template,
        "has-plugin": cmd_has_plugin,
        "has-prompt": cmd_has_prompt,
        "unbind-template": cmd_unbind_template,
        "remove-plugin": cmd_remove_plugin,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
