#!/usr/bin/env python3
"""ov_opencode.py — OpenCode agent Python operations CLI.

Replaces all heredoc Python and inline ``python3 -c`` calls in
agents/opencode.sh.

Subcommands:
    register-plugin <cf> <plugin_ver>          add @openviking/opencode-plugin to opencode.json
    fix-env-yaml <env_yaml>                    add nodejs paths to env.yaml sandbox config
    integrate-template <tpl> <sdk_ver> <plugin_ver> <npm_registry> <plugin_cache_dir> <shared_dir> <template_dir>
                                              write init script + inject source block into template
    check-plugin <cf>                          exit 0 if @openviking/opencode-plugin present
    unbind-template <tpl>                      remove OpenViking integration block from template
    restore-env-yaml <env_yaml>                remove nodejs paths from env.yaml
    unbind-live-config <cf>                    remove OpenViking plugin + mcp + prompt from opencode.json
"""
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))  # parent dir holds ov_common.py
from ov_common import (
    read_text,
    write_text,
    write_init,
    load_json,
)


# ── register-plugin (PYREG heredoc) ───────────────────────────
def cmd_register_plugin(args):
    path, ver = args[0], args[1]
    cfg = load_json(path)
    plugins = cfg.setdefault("plugin", [])
    plugin_spec = f"@openviking/opencode-plugin@{ver}"
    if plugin_spec not in plugins:
        if "@openviking/opencode-plugin" in plugins:
            plugins.remove("@openviking/opencode-plugin")
        plugins.append(plugin_spec)
    if "mcp" in cfg and "openviking" in cfg["mcp"]:
        del cfg["mcp"]["openviking"]
        if not cfg["mcp"]:
            del cfg["mcp"]
    if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
        del cfg["agent"]["build"]["prompt"]
        if not cfg["agent"]["build"]:
            del cfg["agent"]["build"]
        if not cfg["agent"]:
            del cfg["agent"]
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ── fix-env-yaml (YAMLFIX heredoc) ────────────────────────────
def cmd_fix_env_yaml(args):
    path = args[0]
    yaml = read_text(path)
    changed = False
    if "/usr/local/nodejs" not in yaml:
        yaml = re.sub(
            r'(readablePaths:\n(?:\s+- \S+\n)*?)((?:\s*\S))',
            lambda m: m.group(1) + "    - /usr/local/nodejs\n" + m.group(2),
            yaml, count=1)
        changed = True
    if "PATH:" not in yaml or "/usr/local/nodejs/bin" not in yaml:
        path_line = '    PATH: "/usr/local/nodejs/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
        yaml = re.sub(r'(extraEnv:\n)', lambda m: m.group(1) + path_line, yaml, count=1)
        changed = True
    if changed:
        write_text(path, yaml)
        print("env.yaml updated: added nodejs paths")
    else:
        print("env.yaml already has nodejs paths")


# ── integrate-template (PYTPL heredoc) ────────────────────────
def cmd_integrate_template(args):
    tpl_path = args[0]
    sdk_ver = args[1]
    plugin_ver = args[2]
    npm_registry = args[3]
    plugin_cache_dir = args[4]
    shared_dir = args[5]
    template_dir = args[6]
    tpl = read_text(tpl_path)
    block = """
export NPM_CONFIG_REGISTRY=__OV_NPM_REGISTRY__
export NPM_CONFIG_PREFER_OFFLINE=true
export OPENCODE_DISABLE_AUTOUPDATE=true
export OPENCODE_FAST_BOOT=true
export OPENCODE_DISABLE_LSP_DOWNLOAD=true
export OPENCODE_DISABLE_DEFAULT_PLUGINS=true
cat > "$HOME/.npmrc" <<'NPMRC'
registry=__OV_NPM_REGISTRY__
offline=true
prefer-offline=true
NPMRC
OV_DEPS_CACHE="__OV_SHARED_DIR__/opencode-deps"
OV_NPM_CACHE="__OV_SHARED_DIR__/opencode-npm-cache"
OV_OC_DIR="$HOME/.opencode"
OV_CACHE_OK=false
if [[ ! -d "$OV_OC_DIR/node_modules/@opencode-ai/plugin" ]] && \\
   [[ -d "$OV_DEPS_CACHE/node_modules/@opencode-ai/plugin" ]]; then
  mkdir -p "$OV_OC_DIR"
  cp -a "$OV_DEPS_CACHE/node_modules" "$OV_OC_DIR/node_modules"
  cp -a "$OV_DEPS_CACHE/package.json" "$OV_OC_DIR/package.json"
  cp -a "$OV_DEPS_CACHE/package-lock.json" "$OV_OC_DIR/package-lock.json"
  OV_CACHE_OK=true
fi
if [[ ! -d "$HOME/.npm/_cacache" ]] && [[ -d "$OV_NPM_CACHE/_cacache" ]]; then
  mkdir -p "$HOME/.npm"
  cp -a "$OV_NPM_CACHE/_cacache" "$HOME/.npm/_cacache"
  OV_CACHE_OK=true
fi
if [[ "$OV_CACHE_OK" == "true" ]]; then
  export NPM_CONFIG_OFFLINE=true
fi
OV_CFG_NM="$HOME/.config/opencode/node_modules"
OV_CFG_NM_CACHE="__OV_SHARED_DIR__/opencode-config-nm/node_modules"
OV_CFG_NM_RESTORED=false
if [[ ! -d "$OV_CFG_NM/@opencode-ai/plugin" ]] && [[ -d "$OV_CFG_NM_CACHE/@opencode-ai/plugin" ]]; then
  rm -rf "$OV_CFG_NM"
  mkdir -p "$(dirname "$OV_CFG_NM")"
  cp -a "$OV_CFG_NM_CACHE" "$OV_CFG_NM"
  OV_CFG_NM_RESTORED=true
  OV_CACHE_OK=true
  export NPM_CONFIG_OFFLINE=true
fi
OV_NPM_DIR="$HOME/.config/opencode"
mkdir -p "$OV_NPM_DIR/node_modules/@openviking"
OV_PLUGIN_DST="$OV_NPM_DIR/node_modules/@openviking/opencode-plugin"
OV_PLUGIN_CACHE="__OV_PLUGIN_CACHE_DIR__/@openviking/opencode-plugin"
OV_SDK_CACHE="__OV_PLUGIN_CACHE_DIR__/@opencode-ai"
OV_PLUGIN_SOURCE="none"
if [[ -d "$OV_PLUGIN_DST" && -f "$OV_PLUGIN_DST/package.json" ]]; then
  OV_PLUGIN_SOURCE="existing"
fi
if [[ "$OV_PLUGIN_SOURCE" == "none" && -d "$OV_PLUGIN_CACHE" && -f "$OV_PLUGIN_CACHE/package.json" ]]; then
  rm -rf "$OV_PLUGIN_DST"
  cp -a "$OV_PLUGIN_CACHE" "$OV_PLUGIN_DST"
  OV_PLUGIN_SOURCE="cache"
  if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" && -d "$OV_SDK_CACHE" ]]; then
    cp -a "$OV_SDK_CACHE" "$OV_NPM_DIR/node_modules/@opencode-ai"
  fi
fi
if [[ "$OV_PLUGIN_SOURCE" == "none" ]]; then
  if command -v npm &>/dev/null; then
    cat > "$OV_NPM_DIR/package.json" <<'PKGEOF'
{"dependencies":{"@opencode-ai/plugin":"__OV_PLUGIN_SDK_VER__","@openviking/opencode-plugin":"__OV_OPENCODE_PLUGIN_VER__"}}
PKGEOF
    if (cd "$OV_NPM_DIR" && npm install --registry=__OV_NPM_REGISTRY__ --no-audit --no-fund 2>&1 | tail -5) && \\
       [[ -d "$OV_PLUGIN_DST" ]]; then
      OV_PLUGIN_SOURCE="npm"
      mkdir -p "$(dirname "$OV_PLUGIN_CACHE")"
      rm -rf "$OV_PLUGIN_CACHE"
      cp -a "$OV_PLUGIN_DST" "$OV_PLUGIN_CACHE"
      touch "$OV_PLUGIN_CACHE"
      if [[ -d "$OV_NPM_DIR/node_modules/@opencode-ai" ]]; then
        rm -rf "$OV_SDK_CACHE"
        cp -a "$OV_NPM_DIR/node_modules/@opencode-ai" "$OV_SDK_CACHE"
      fi
    else
      echo "WARN: npm install failed — plugin will not load"
    fi
  else
    echo "WARN: npm not found and no cache available — plugin will not load"
  fi
fi
if [[ -d "$OV_PLUGIN_DST" && -f "$OV_PLUGIN_DST/package.json" ]]; then
  OV_CACHE_PKG="$HOME/.cache/opencode/packages/@openviking/opencode-plugin@latest"
  if [[ ! -d "$OV_CACHE_PKG/node_modules/@openviking/opencode-plugin" ]]; then
    mkdir -p "$OV_CACHE_PKG/node_modules/@openviking"
    cp -a "$OV_PLUGIN_DST" "$OV_CACHE_PKG/node_modules/@openviking/opencode-plugin"
    OV_CACHE_VER="$HOME/.cache/opencode/packages/@openviking/opencode-plugin@__OV_OPENCODE_PLUGIN_VER__"
    if [[ ! -d "$OV_CACHE_VER/node_modules/@openviking/opencode-plugin" ]]; then
      cp -a "$OV_CACHE_PKG" "$OV_CACHE_VER"
    fi
  fi
fi
_ov_py=""
for _py in python3.12 python3.11 python3.10 python3; do command -v "$_py" >/dev/null 2>&1 && _ov_py="$_py" && break; done
: "${_ov_py:=python3}"
if [[ -f "$CONFIG_FILE" ]]; then
  $_ov_py - "$CONFIG_FILE" <<'OVREG'
import json,sys; path=sys.argv[1]; cfg=json.load(open(path)); changed=False
plugins=cfg.setdefault("plugin",[]); plugin_spec="@openviking/opencode-plugin@__OV_OPENCODE_PLUGIN_VER__"
if plugin_spec not in plugins:
    if "@openviking/opencode-plugin" in plugins: plugins.remove("@openviking/opencode-plugin")
    plugins.append(plugin_spec); changed=True
if "mcp" in cfg and "openviking" in cfg["mcp"]:
    del cfg["mcp"]["openviking"]
    if not cfg["mcp"]: del cfg["mcp"]
    changed=True
if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
    del cfg["agent"]["build"]["prompt"]
    if not cfg["agent"]["build"]: del cfg["agent"]["build"]
    if not cfg["agent"]: del cfg["agent"]
    changed=True
if changed: json.dump(cfg,open(path,"w"),indent=2,ensure_ascii=False)
OVREG
fi
OV_CONF_DIR="$HOME/.config/opencode"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{"enabled":true,"timeoutMs":30000,"repoContext":{"enabled":true,"cacheTtlMs":60000},"autoRecall":{"enabled":true,"limit":10,"scoreThreshold":0.35,"maxContentChars":500,"preferAbstract":true,"tokenBudget":2000,"minQueryLength":3},"recallLimit":15,"recallMaxContentChars":20000,"commitTokenThreshold":20000,"commitKeepRecentCount":10,"profileTokenBudget":10000,"resumeContextBudget":32000}
OVCONF
fi
if [[ "${OV_CFG_NM_RESTORED:-false}" != "true" ]]; then
  nohup bash -c 'sleep 25; _py=""; for p in python3.12 python3.11 python3.10 python3; do command -v "$p" >/dev/null 2>&1 && _py="$p" && break; done; : "${_py:=python3}"; SRC="$HOME/.config/opencode/node_modules"; DST="__OV_SHARED_DIR__/opencode-config-nm/node_modules"; if [[ -d "$SRC/@opencode-ai/plugin" ]]; then cur=$("$_py" -c "import json;print(json.load(open(\"$SRC/@opencode-ai/plugin/package.json\"))[\"version\"])" 2>/dev/null); old=$("$_py" -c "import json;print(json.load(open(\"$DST/@opencode-ai/plugin/package.json\"))[\"version\"])" 2>/dev/null); if [[ "$cur" != "$old" ]]; then TMP="__OV_SHARED_DIR__/opencode-config-nm.tmp.$$"; rm -rf "$TMP"; mkdir -p "$TMP"; cp -a "$SRC" "$TMP/node_modules"; rm -rf "__OV_SHARED_DIR__/opencode-config-nm"; mv "$TMP" "__OV_SHARED_DIR__/opencode-config-nm"; echo "[ov-cache] Saved plugin deps v${cur} to shared cache." >> "$HOME/.config/opencode/openviking/openviking-memory.log"; fi; fi' > /dev/null 2>&1 &
fi
"""
    block = block.replace("__OV_NPM_REGISTRY__", npm_registry)
    block = block.replace("__OV_PLUGIN_SDK_VER__", sdk_ver)
    block = block.replace("__OV_OPENCODE_PLUGIN_VER__", plugin_ver)
    block = block.replace("__OV_PLUGIN_CACHE_DIR__", plugin_cache_dir)
    block = block.replace("__OV_SHARED_DIR__", shared_dir)
    init_path = f"{shared_dir}/ov-opencode-init.sh"
    write_init(init_path, "OpenCode", f"Sourced by {template_dir}/opencode/start.sh.", block.lstrip("\n"))
    source_block_str = (
        "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\n"
        f"source {shared_dir}/ov-opencode-init.sh\n"
        "# ── End OpenViking integration ──\n\n"
    )
    markers = ["export OPENCODE_SERVER_PASSWORD", "exec /root/runtime/opencode/opencode"]
    idx = -1
    for marker in markers:
        idx = tpl.find(marker)
        if idx != -1:
            print(f"Insertion point: {marker}")
            break
    if idx == -1:
        print("ERROR: no insertion marker found (tried: " + ", ".join(markers) + ")", file=sys.stderr)
        sys.exit(1)
    tpl = tpl[:idx] + source_block_str + tpl[idx:]
    if " --pure" in tpl:
        tpl = tpl.replace(" --pure", "")
        print("Removed --pure flag (plugins now enabled)")
    else:
        print("--pure flag not present, no change needed")
    write_text(tpl_path, tpl)


# ── check-plugin (inline python3 -c) ──────────────────────────
def cmd_check_plugin(args):
    path = args[0]
    cfg = load_json(path)
    sys.exit(0 if any(p.startswith("@openviking/opencode-plugin") for p in cfg.get("plugin", [])) else 1)


# ── unbind-template (PYUNBIND heredoc) ────────────────────────
def cmd_unbind_template(args):
    path = args[0]
    content = read_text(path)
    marker = "# ── OpenViking integration"
    idx = content.find(marker)
    if idx != -1:
        end_marker = "# ── End OpenViking integration ──"
        end_idx = content.find(end_marker, idx)
        if end_idx != -1:
            # Remove from start marker to end of end marker line (+newline)
            end_pos = end_idx + len(end_marker)
            # Also consume trailing newline(s)
            while end_pos < len(content) and content[end_pos] == '\n':
                end_pos += 1
            content = content[:idx] + content[end_pos:]
            write_text(path, content)
            print("Removed OpenViking integration block from template")
        else:
            print("WARNING: end marker not found, skipping template removal")
    else:
        print("No OpenViking integration block found in template")
    if "opencode serve" in content and "--pure" not in content:
        content = content.replace("opencode serve --port 14096 --hostname 127.0.0.1 --print-logs",
                                  "opencode serve --port 14096 --hostname 127.0.0.1 --print-logs --pure")
        write_text(path, content)
        print("Restored --pure flag on exec line")


# ── restore-env-yaml (YAMLRESTORE heredoc) ────────────────────
def cmd_restore_env_yaml(args):
    path = args[0]
    yaml = read_text(path)
    changed = False
    if "/usr/local/nodejs" in yaml:
        yaml = re.sub(r'\n\s+- /usr/local/nodejs\n', '\n', yaml, count=1)
        changed = True
    if "/usr/local/nodejs/bin" in yaml:
        yaml = re.sub(r'\n\s+PATH: "/usr/local/nodejs/bin:[^"]*"\n', '\n', yaml, count=1)
        changed = True
    if changed:
        write_text(path, yaml)
        print("env.yaml restored: removed nodejs paths")
    else:
        print("env.yaml already clean")


# ── unbind-live-config (PYUNBIND2 heredoc) ────────────────────
def cmd_unbind_live_config(args):
    path = args[0]
    cfg = load_json(path)
    changed = False
    if "plugin" in cfg:
        removed = False
        for p in list(cfg["plugin"]):
            if p.startswith("@openviking/opencode-plugin"):
                cfg["plugin"].remove(p)
                removed = True
        if removed:
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
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print("Removed OpenViking from opencode.json")


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "register-plugin": cmd_register_plugin,
        "fix-env-yaml": cmd_fix_env_yaml,
        "integrate-template": cmd_integrate_template,
        "check-plugin": cmd_check_plugin,
        "unbind-template": cmd_unbind_template,
        "restore-env-yaml": cmd_restore_env_yaml,
        "unbind-live-config": cmd_unbind_live_config,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
