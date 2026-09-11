#!/bin/bash
# agents/opencode.sh — OpenCode agent subclass (Plugin + openviking-config.json)
# Inherits from lib/base.sh; overrides: integrate, unbind, status
agent_opencode_register() {
  agent::set_meta name "opencode"
  agent::set_meta display_name "OpenCode"
  agent::set_meta sandbox_pattern "opencode-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/opencode/start.sh"
  agent::set_meta mechanism "Plugin + openviking-config.json"
  registry_add "opencode"
}
# Sets _ov_deploy_result: "existing" | "cache" | "npm" | "failed"
_ov_deploy_plugin() {
  local dest_parent="$1" local_registry="${2:-$OV_NPM_REGISTRY_DEFAULT}"
  local pkg="@openviking/opencode-plugin"
  local plugin_dst="${dest_parent}/node_modules/@openviking/opencode-plugin"
  _ov_deploy_result="failed"
  if [[ -d "$plugin_dst" && -f "$plugin_dst/package.json" ]]; then
    _ov_deploy_result="existing"
    return 0
  fi
  local cache_dir; cache_dir=$(ov_plugin_cache_path "$pkg")
  if [[ -d "$cache_dir" && -f "$cache_dir/package.json" ]]; then
    mkdir -p "$(dirname "$plugin_dst")"
    rm -rf "$plugin_dst"
    cp -a "$cache_dir" "$plugin_dst"
    local sdk_cache; sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
    if [[ ! -d "${dest_parent}/node_modules/@opencode-ai" && -d "$sdk_cache" ]]; then
      cp -a "$sdk_cache" "${dest_parent}/node_modules/@opencode-ai"
    fi
    _ov_deploy_result="cache"
    return 0
  fi
  if command -v npm &>/dev/null || command -v "$OV_NPM" &>/dev/null; then
    local npm_bin="${OV_NPM:-npm}"
    cat > "${dest_parent}/package.json" <<PKGEOF
{"dependencies":{"@opencode-ai/plugin":"$OV_PLUGIN_SDK_VER","@openviking/opencode-plugin":"$OV_OPENCODE_PLUGIN_VER"}}
PKGEOF
    if (cd "$dest_parent" && "$npm_bin" install --registry="$local_registry" --no-audit --no-fund 2>&1 | tail -5) && \
       [[ -d "$plugin_dst" ]]; then
      ov_plugin_cache_put "$pkg" "$plugin_dst"
      local sdk_cache; sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
      if [[ -d "${dest_parent}/node_modules/@opencode-ai" ]]; then
        mkdir -p "$(dirname "$sdk_cache")"
        rm -rf "$sdk_cache"
        cp -a "${dest_parent}/node_modules/@opencode-ai" "$sdk_cache"
      fi
      _ov_deploy_result="npm"
      return 0
    fi
  fi
  return 1
}
# Pre-filling skips the ~60s npm install on undeploy+deploy.
_ov_prepopulate_cache() {
  local home_dir="$1"
  local plugin_dst="${home_dir}/.config/opencode/node_modules/@openviking/opencode-plugin"
  local cache_pkg="${home_dir}/.cache/opencode/packages/@openviking/opencode-plugin@latest"
  if [[ ! -d "$plugin_dst" || ! -f "$plugin_dst/package.json" ]]; then return 0; fi
  if [[ -d "$cache_pkg/node_modules/@openviking/opencode-plugin" ]]; then return 0; fi
  mkdir -p "$cache_pkg/node_modules/@openviking"
  cp -a "$plugin_dst" "$cache_pkg/node_modules/@openviking/opencode-plugin"
  cat > "$cache_pkg/package.json" <<'OVCACHEPKG'
{"dependencies":{"@openviking/opencode-plugin":"__OV_OPENCODE_PLUGIN_VER__"}}
OVCACHEPKG
  cat > "$cache_pkg/package-lock.json" <<'OVCACHELOCK'
{"name":"@openviking/opencode-plugin@latest","lockfileVersion":3,"requires":true,"packages":{"":{"dependencies":{"@openviking/opencode-plugin":"__OV_OPENCODE_PLUGIN_VER__"}},"node_modules/@openviking/opencode-plugin":{"version":"__OV_OPENCODE_PLUGIN_VER__","resolved":"https://registry.npmjs.org/@openviking/opencode-plugin/-/opencode-plugin-__OV_OPENCODE_PLUGIN_VER__.tgz","integrity":"sha512-jEPnxARNmP5lMNTrEQ42KP5SkKHdF3O5I99HnMHGHC0MyHWT9zn3FanAXT4cjaeC2d4Bzt7Nd9IL50SUZYkhGg==","license":"Apache-2.0"}}}
OVCACHELOCK
  cat > "$cache_pkg/node_modules/.package-lock.json" <<'OVNMLOCK'
{"name":"@openviking/opencode-plugin@latest","lockfileVersion":3,"requires":true,"packages":{"node_modules/@openviking/opencode-plugin":{"version":"__OV_OPENCODE_PLUGIN_VER__","resolved":"https://registry.npmjs.org/@openviking/opencode-plugin/-/opencode-plugin-__OV_OPENCODE_PLUGIN_VER__.tgz","integrity":"sha512-jEPnxARNmP5lMNTrEQ42KP5SkKHdF3O5I99HnMHGHC0MyHWT9zn3FanAXT4cjaeC2d4Bzt7Nd9IL50SUZYkhGg==","license":"Apache-2.0"}}}
OVNMLOCK
  local _ver="${OV_OPENCODE_PLUGIN_VER}"
  sed -i "s/__OV_OPENCODE_PLUGIN_VER__/$_ver/g" "$cache_pkg/package.json" "$cache_pkg/package-lock.json" "$cache_pkg/node_modules/.package-lock.json"
  local cache_ver="${home_dir}/.cache/opencode/packages/@openviking/opencode-plugin@${OV_OPENCODE_PLUGIN_VER}"
  if [[ ! -d "$cache_ver/node_modules/@openviking/opencode-plugin" ]]; then
    cp -a "$cache_pkg" "$cache_ver"
    sed -i "s/@openviking/opencode-plugin@latest/@openviking/opencode-plugin@${OV_OPENCODE_PLUGIN_VER}/g" "$cache_ver/package-lock.json" "$cache_ver/node_modules/.package-lock.json" 2>/dev/null || true
  fi
}
agent_opencode_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "OpenCode template start.sh not found: $tpl"; return 1; }
  local ov_pkg="@openviking/opencode-plugin"
  if grep -q "ov-opencode-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-opencode-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    log_ok "OpenCode already has OpenViking plugin (template-level)"
    return 0
  fi
  require_confirmation "Integrate OpenViking (npm + domestic mirror fallback)" "opencode" \
    "Install @openviking/opencode-plugin (npm online first, on-demand GitHub mirror fallback) + plugin SDK + openviking-config.json to template start.sh (persistent)" \
    || return 1
  if dry_run_msg "Would install OpenViking plugin (npm → on-demand GitHub fallback) to $tpl and live sandbox"; then return 0; fi
  local sandbox; sandbox=$(find_sandbox "opencode")
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    local ov_npm_dir="${sandbox}/.config/opencode"
    local NPM_REGISTRY; NPM_REGISTRY=$(ov_first_npm_registry)
    echo "registry=${NPM_REGISTRY}" > "${ov_npm_dir}/.npmrc"
    log_ok ".npmrc created ($NPM_REGISTRY)"
    _ov_deploy_plugin "$ov_npm_dir" "$NPM_REGISTRY" || true
    case "$_ov_deploy_result" in
      existing) log_ok "Plugin already installed (cache hit)" ;;
      cache)    log_ok "Plugin from shared cache" ;;
      npm)      log_ok "Plugin from npm" ;;
      *)
        log_warn "npm failed — trying GitHub provision (~54s)"
        local _prov_dir; _prov_dir=$(mktemp -d /tmp/ov-prov.XXXXXX)
        if ov_plugin_provision "opencode-plugin" "$_prov_dir"; then
          local plugin_dst="${ov_npm_dir}/node_modules/@openviking/opencode-plugin"
          mkdir -p "$(dirname "$plugin_dst")"
          cp -a "$_prov_dir" "$plugin_dst"
          ov_plugin_cache_put "$ov_pkg" "$plugin_dst"
          log_ok "Plugin provisioned from GitHub"
        else
          log_warn "All plugin installation methods failed"
        fi
        rm -rf "$_prov_dir"
        ;;
    esac
    if [[ ! -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
      local sdk_cache; sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
      if [[ -d "$sdk_cache" ]]; then
        cp -a "$sdk_cache" "${ov_npm_dir}/node_modules/@opencode-ai"
        log_ok "Plugin SDK from shared cache"
      fi
    fi
    local cf="${sandbox}/.config/opencode/opencode.json"
    backup_file "$cf"
    "$OV_PY" - "$cf" "$OV_OPENCODE_PLUGIN_VER" <<'PYREG'
import json, sys
path = sys.argv[1]
ver = sys.argv[2]
with open(path) as f:
    cfg = json.load(f)
plugins = cfg.setdefault("plugin", [])
plugin_spec = f"@openviking/opencode-plugin@{ver}"
if plugin_spec not in plugins:
    if "@openviking/opencode-plugin" in plugins:
        plugins.remove("@openviking/opencode-plugin")
    plugins.append(plugin_spec)
if "mcp" in cfg and "openviking" in cfg["mcp"]:
    del cfg["mcp"]["openviking"]
    if not cfg["mcp"]: del cfg["mcp"]
if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
    del cfg["agent"]["build"]["prompt"]
    if not cfg["agent"]["build"]: del cfg["agent"]["build"]
    if not cfg["agent"]: del cfg["agent"]
with open(path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
PYREG
    log_ok "Plugin registered in opencode.json"
    create_ov_config "$sandbox"
    _ov_prepopulate_cache "$sandbox" | sed 's/^/  /'
    local oc_deps_src="${sandbox}/.opencode"
    local oc_deps_dst="${OV_PLUGIN_CACHE_DIR%/openviking-plugins}/opencode-deps"
    if [[ -d "$oc_deps_src/node_modules/@opencode-ai/plugin" ]]; then
      mkdir -p "$oc_deps_dst"
      cp -a "$oc_deps_src/node_modules" "$oc_deps_dst/node_modules"
      cp -a "$oc_deps_src/package.json" "$oc_deps_dst/package.json" 2>/dev/null
      cp -a "$oc_deps_src/package-lock.json" "$oc_deps_dst/package-lock.json" 2>/dev/null
      log_ok "OpenCode deps saved to shared cache"
    fi
    local npm_cache_src="${sandbox}/.npm/_cacache"
    local npm_cache_dst="${OV_PLUGIN_CACHE_DIR%/openviking-plugins}/opencode-npm-cache"
    if [[ -d "$npm_cache_src" ]]; then
      mkdir -p "$npm_cache_dst"
      cp -a "$npm_cache_src" "$npm_cache_dst/_cacache"
      log_ok "npm cache saved to shared cache"
    fi
  else
    log_info "No live OpenCode sandbox found; plugin will be installed on next start"
    local _prov_dir; _prov_dir=$(mktemp -d /tmp/ov-prov.XXXXXX)
    ov_plugin_provision "opencode-plugin" "$_prov_dir" || { rm -rf "$_prov_dir"; return 1; }
    ov_plugin_cache_put "$ov_pkg" "$_prov_dir"
    rm -rf "$_prov_dir"
    log_ok "opencode-plugin provisioned to shared cache"
  fi
  local env_yaml="$OV_TEMPLATE_DIR/opencode/env.yaml"
  if [[ -f "$env_yaml" ]]; then
    backup_file "$env_yaml"
    "$OV_PY" - "$env_yaml" <<'YAMLFIX'
import sys, re
path = sys.argv[1]
with open(path) as f:
    yaml = f.read()
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
    with open(path, "w") as f: f.write(yaml)
    print("env.yaml updated: added nodejs paths")
else:
    print("env.yaml already has nodejs paths")
YAMLFIX
    log_ok "OpenCode env.yaml updated (nodejs accessible in sandbox)"
  fi
  backup_file "$tpl"
  "$OV_PY" - "$tpl" "$OV_PLUGIN_SDK_VER" "$OV_OPENCODE_PLUGIN_VER" "$OV_NPM_REGISTRY_DEFAULT" "$OV_PLUGIN_CACHE_DIR" "$OV_SHARED_DIR" "$OV_TEMPLATE_DIR" <<'PYTPL'
import sys, os
tpl_path = sys.argv[1]
sdk_ver = sys.argv[2]
plugin_ver = sys.argv[3]
npm_registry = sys.argv[4]
plugin_cache_dir = sys.argv[5]
shared_dir = sys.argv[6]
template_dir = sys.argv[7]
with open(tpl_path) as f:
    tpl = f.read()
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
  nohup bash -c 'sleep 25; SRC="$HOME/.config/opencode/node_modules"; DST="__OV_SHARED_DIR__/opencode-config-nm/node_modules"; if [[ -d "$SRC/@opencode-ai/plugin" ]]; then cur=$(python3 -c "import json;print(json.load(open(\"$SRC/@opencode-ai/plugin/package.json\"))[\"version\"])" 2>/dev/null); old=$(python3 -c "import json;print(json.load(open(\"$DST/@opencode-ai/plugin/package.json\"))[\"version\"])" 2>/dev/null); if [[ "$cur" != "$old" ]]; then TMP="__OV_SHARED_DIR__/opencode-config-nm.tmp.$$"; rm -rf "$TMP"; mkdir -p "$TMP"; cp -a "$SRC" "$TMP/node_modules"; rm -rf "__OV_SHARED_DIR__/opencode-config-nm"; mv "$TMP" "__OV_SHARED_DIR__/opencode-config-nm"; echo "[ov-cache] Saved plugin deps v${cur} to shared cache." >> "$HOME/.config/opencode/openviking/openviking-memory.log"; fi; fi' > /dev/null 2>&1 &
fi
"""
block = block.replace("__OV_NPM_REGISTRY__", npm_registry)
block = block.replace("__OV_PLUGIN_SDK_VER__", sdk_ver)
block = block.replace("__OV_OPENCODE_PLUGIN_VER__", plugin_ver)
block = block.replace("__OV_PLUGIN_CACHE_DIR__", plugin_cache_dir)
block = block.replace("__OV_SHARED_DIR__", shared_dir)
init_path = f"{shared_dir}/ov-opencode-init.sh"
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for OpenCode ──\n")
    f.write(f"# Sourced by {template_dir}/opencode/start.sh.\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block.lstrip("\n"))
os.chmod(init_path, 0o755)
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-opencode-init.sh\n# ── End OpenViking integration ──\n\n"
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
tpl = tpl[:idx] + source_block + tpl[idx:]
if " --pure" in tpl:
    tpl = tpl.replace(" --pure", "")
    print("Removed --pure flag (plugins now enabled)")
else:
    print("--pure flag not present, no change needed")
with open(tpl_path, "w") as f:
    f.write(tpl)
PYTPL
  log_ok "OpenCode template updated with cache-first plugin deployment"
  ov_log_info "重启 OpenCode 以激活插件" "Restart OpenCode for plugin to activate"
}
agent_opencode_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  if grep -q "OpenViking integration\|@openviking/opencode-plugin\|openviking plugin\|plugins/opencode" "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  else
    has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  fi
  local sandbox; sandbox=$(find_sandbox "opencode")
  local sandbox_has_ov=false
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    check_json_mcp "${sandbox}/.config/opencode/opencode.json" && sandbox_has_ov=true
    "$OV_PY" -c "import json,sys; d=json.load(open('${sandbox}/.config/opencode/opencode.json')); sys.exit(0 if any(p.startswith('@openviking/opencode-plugin') for p in d.get('plugin',[])) else 1)" 2>/dev/null && sandbox_has_ov=true
  fi
  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "OpenCode not integrated (nothing to remove)"; return 0; }
  require_confirmation "UNBIND OpenViking" "opencode" "Remove OpenViking plugin + npm packages + config from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking integration from template and sandbox"; then return 0; fi
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    "$OV_PY" - "$tpl" <<'PYUNBIND'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()
marker = "# ── OpenViking integration"
idx = content.find(marker)
if idx != -1:
    end_marker = "export OPENCODE_SERVER_PASSWORD"
    end_idx = content.find(end_marker, idx)
    if end_idx != -1:
        content = content[:idx] + content[end_idx:]
        with open(path, 'w') as f:
            f.write(content)
        print("Removed OpenViking integration block from template")
    else:
        print("WARNING: end marker not found, skipping template removal")
else:
    print("No OpenViking integration block found in template")
if "opencode serve" in content and "--pure" not in content:
    content = content.replace("opencode serve --port 14096 --hostname 127.0.0.1 --print-logs",
                              "opencode serve --port 14096 --hostname 127.0.0.1 --print-logs --pure")
    with open(path, 'w') as f:
        f.write(content)
    print("Restored --pure flag on exec line")
PYUNBIND
    log_ok "OpenViking integration block removed from template"
    rm -f "$OV_SHARED_DIR/ov-opencode-init.sh" && log_ok "Removed ov-opencode-init.sh"
  fi
  local env_yaml="$OV_TEMPLATE_DIR/opencode/env.yaml"
  if [[ -f "$env_yaml" ]]; then
    backup_file "$env_yaml"
    "$OV_PY" - "$env_yaml" <<'YAMLRESTORE'
import sys, re
path = sys.argv[1]
with open(path) as f:
    yaml = f.read()
changed = False
if "/usr/local/nodejs" in yaml:
    yaml = re.sub(r'\n\s+- /usr/local/nodejs\n', '\n', yaml, count=1)
    changed = True
if "/usr/local/nodejs/bin" in yaml:
    yaml = re.sub(r'\n\s+PATH: "/usr/local/nodejs/bin:[^"]*"\n', '\n', yaml, count=1)
    changed = True
if changed:
    with open(path, "w") as f: f.write(yaml)
    print("env.yaml restored: removed nodejs paths")
else:
    print("env.yaml already clean")
YAMLRESTORE
    log_ok "OpenCode env.yaml restored"
  fi
  if [[ -n "$sandbox" ]]; then
    local cf="${sandbox}/.config/opencode/opencode.json"
    if [[ -f "$cf" ]]; then
      backup_file "$cf"
      "$OV_PY" - "$cf" <<'PYUNBIND2'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
changed = False
if "plugin" in cfg:
    removed = False
    for p in list(cfg["plugin"]):
        if p.startswith("@openviking/opencode-plugin"):
            cfg["plugin"].remove(p)
            removed = True
    if removed:
        if not cfg["plugin"]: del cfg["plugin"]
        changed = True
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
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("Removed OpenViking from opencode.json")
PYUNBIND2
      log_ok "OpenViking plugin removed from live sandbox"
    fi
    rm -rf "${sandbox}/.config/opencode/node_modules" 2>/dev/null && log_ok "node_modules removed"
    rm -f  "${sandbox}/.config/opencode/package.json" \
           "${sandbox}/.config/opencode/package-lock.json" \
           "${sandbox}/.config/opencode/.npmrc" \
           "${sandbox}/.config/opencode/openviking-config.json" 2>/dev/null
    rm -rf "${sandbox}/.config/opencode/plugins/openviking" \
           "${sandbox}/.config/opencode/plugins/openviking.js" 2>/dev/null
    rm -rf "${sandbox}/.opencode/node_modules/@openviking" 2>/dev/null
    rm -rf "${sandbox}/.cache/opencode/packages/@openviking" 2>/dev/null
    log_ok "npm packages, .opencode/, .cache/ cleaned up"
  fi
  local oc_deps_cache="${OV_PLUGIN_CACHE_DIR%/openviking-plugins}/opencode-deps"
  if [[ -d "$oc_deps_cache" ]]; then
    rm -rf "$oc_deps_cache"
    log_ok "OpenCode deps shared cache cleaned up"
  fi
  local npm_cache="${OV_PLUGIN_CACHE_DIR%/openviking-plugins}/opencode-npm-cache"
  if [[ -d "$npm_cache" ]]; then
    rm -rf "$npm_cache"
    log_ok "npm cache shared cache cleaned up"
  fi
  ov_log_info "重启 OpenCode 以使更改完全生效" "Restart OpenCode for changes to take full effect"
}
agent_opencode_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  if grep -q "OpenViking integration\|@openviking/opencode-plugin\|openviking plugin\|plugins/opencode" "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  else
    has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  fi
  local sandbox; sandbox=$(find_sandbox "opencode")
  [[ -z "$sandbox" ]] && { ov_status "opencode" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.config/opencode/opencode.json"
  local sandbox_has_ov=false
  if [[ -f "$cf" ]]; then
    if "$OV_PY" -c "import json,sys; d=json.load(open('$cf')); sys.exit(0 if any(p.startswith('@openviking/opencode-plugin') for p in d.get('plugin',[])) else 1)" 2>/dev/null; then
      sandbox_has_ov=true
    elif check_json_mcp "$cf" 2>/dev/null; then
      sandbox_has_ov=true
    fi
  fi
  local plugin_installed=false
  local plugin_source=""
  if [[ -d "${sandbox}/.cache/opencode/packages/@openviking/opencode-plugin@latest/node_modules/@openviking/opencode-plugin" ]] || \
     [[ -d "${sandbox}/.cache/opencode/packages/@openviking/opencode-plugin@${OV_OPENCODE_PLUGIN_VER}/node_modules/@openviking/opencode-plugin" ]]; then
    plugin_installed=true
    plugin_source="cache"
  elif [[ -d "${sandbox}/.config/opencode/node_modules/@openviking/opencode-plugin" ]]; then
    plugin_installed=true
    plugin_source="runtime"
  elif [[ -d "${sandbox}/.config/opencode/node_modules/@opencode-ai" ]]; then
    plugin_installed=true
    plugin_source="npm"
  elif [[ -f "${sandbox}/.config/opencode/plugins/openviking.js" ]]; then
    plugin_installed=true
    plugin_source="legacy"
  fi
  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    if [[ "$plugin_installed" == "true" ]]; then
      if [[ "$plugin_source" == "cache" ]]; then
        ov_status "opencode" "integrated" "Official @openviking/opencode-plugin (.cache pre-populated, template + live)"
      else
        ov_status "opencode" "integrated" "Official @openviking/opencode-plugin (runtime install, template + live)"
      fi
    else
      ov_status "opencode" "integrated" "MCP: $(get_json_mcp_url "$cf" 2>/dev/null || echo "unknown")"
    fi
  elif [[ "$tpl_has_ov" == "true" ]]; then
    if [[ "$plugin_installed" == "true" ]]; then
      ov_status "opencode" "integrated" "Plugin installed (template + live), restart to activate hooks"
    else
      ov_status "opencode" "integrated" "Plugin configured (template only, restart to activate)"
    fi
  elif [[ "$sandbox_has_ov" == "true" ]]; then
    ov_status "opencode" "partial" "Plugin/MCP in live only, lost on restart"
  else
    ov_status "opencode" "not_integrated" "No OpenViking integration found"
  fi
}
