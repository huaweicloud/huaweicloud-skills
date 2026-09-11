#!/bin/bash
# agents/codearts.sh — CodeArts CLI agent subclass (OpenCode engine + @openviking/opencode-plugin)
# Inherits from lib/base.sh; overrides: integrate, unbind, status
agent_codearts_register() {
  agent::set_meta name "codearts"
  agent::set_meta display_name "CodeArts CLI"
  agent::set_meta sandbox_pattern "codearts-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/codearts/start.sh"
  agent::set_meta mechanism "Plugin (@openviking/opencode-plugin)"
  registry_add "codearts"
}
agent_codearts_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "CodeArts template start.sh not found: $tpl"; return 1; }
  local ov_pkg="@openviking/opencode-plugin"
  if grep -q "ov-codearts-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-codearts-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    log_ok "CodeArts already has OpenViking plugin (template-level)"
    return 0
  fi
  require_confirmation "Integrate OpenViking (plugin + cache-first deployment)" "codearts" \
    "Install @openviking/opencode-plugin (cache-first from codearts package cache, npm fallback) + plugin SDK + openviking-config.json to template start.sh (persistent)" \
    || return 1
  if dry_run_msg "Would install OpenViking plugin (cache → npm fallback) to $tpl and live sandbox"; then return 0; fi
  local sandbox; sandbox=$(find_sandbox "codearts")
  if [[ -n "$sandbox" ]]; then
    local ov_npm_dir="${sandbox}/.codeartsdoer"
    local cf="${sandbox}/.codeartsdoer/codearts_cli.json"
    local plugin_dst="${ov_npm_dir}/node_modules/@openviking/opencode-plugin"
    mkdir -p "$(dirname "$plugin_dst")"
    local plugin_source="none"
    if [[ -d "$plugin_dst" && -f "$plugin_dst/package.json" ]]; then
      plugin_source="existing"
      log_ok "Plugin already installed (cache hit)"
    fi
    if [[ "$plugin_source" == "none" ]] && ov_plugin_cache_valid "$ov_pkg"; then
      ov_plugin_cache_get "$ov_pkg" "$plugin_dst"
      plugin_source="cache"
      log_ok "Plugin from shared cache"
      local _sdk_cache; _sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
      if [[ ! -d "${ov_npm_dir}/node_modules/@opencode-ai" && -d "$_sdk_cache" ]]; then
        cp -a "$_sdk_cache" "${ov_npm_dir}/node_modules/@opencode-ai"
        log_ok "Plugin SDK from shared cache"
      fi
    fi
    if [[ "$plugin_source" == "none" ]]; then
      local NPM_REGISTRY; NPM_REGISTRY=$(ov_first_npm_registry 2>/dev/null || echo "$OV_NPM_REGISTRY_DEFAULT")
      echo "registry=${NPM_REGISTRY}" > "${ov_npm_dir}/.npmrc"
      cat > "${ov_npm_dir}/package.json" <<PKGEOF
{"dependencies":{"@opencode-ai/plugin":"$OV_PLUGIN_SDK_VER","@openviking/opencode-plugin":"$OV_OPENCODE_PLUGIN_VER"}}
PKGEOF
      log_info "Trying npm install @openviking/opencode-plugin (online)..."
      if (cd "$ov_npm_dir" && "$OV_NPM" install --registry="${NPM_REGISTRY}" --no-audit --no-fund 2>&1 | tail -5) && \
         [[ -d "$plugin_dst" ]]; then
        plugin_source="npm"
        log_ok "Plugin installed from npm"
        ov_plugin_cache_put "$ov_pkg" "$plugin_dst"
        log_ok "Plugin saved to shared cache"
        if [[ -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
          local _sdk_cache; _sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
          mkdir -p "$(dirname "$_sdk_cache")"
          rm -rf "$_sdk_cache"
          cp -a "${ov_npm_dir}/node_modules/@opencode-ai" "$_sdk_cache"
        fi
      else
        log_warn "npm install failed — trying shared cache fallback"
        local _cache_dir; _cache_dir=$(ov_plugin_cache_path "$ov_pkg")
        if [[ -d "$_cache_dir" ]]; then
          ov_plugin_cache_get "$ov_pkg" "$plugin_dst"
          plugin_source="cache"
          log_ok "Plugin from shared cache (expired)"
        else
          log_error "Plugin installation failed (no cache, no npm)"
          return 1
        fi
      fi
    fi
    if [[ ! -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
      local NPM_REGISTRY; NPM_REGISTRY=$(ov_first_npm_registry 2>/dev/null || echo "$OV_NPM_REGISTRY_DEFAULT")
      cat > "${ov_npm_dir}/package.json" <<PKGEOF2
{"dependencies":{"@opencode-ai/plugin":"$OV_PLUGIN_SDK_VER","@openviking/opencode-plugin":"$OV_OPENCODE_PLUGIN_VER"}}
PKGEOF2
      (cd "$ov_npm_dir" && "$OV_NPM" install --registry="${NPM_REGISTRY}" --no-audit --no-fund 2>&1 | tail -5) && \
        log_ok "Plugin SDK from npm" || \
        log_warn "Plugin SDK install failed"
      if [[ ! -d "$plugin_dst" && -d "$plugin_cache" ]]; then
        cp -a "$plugin_cache" "$plugin_dst"
        log_ok "Plugin re-deployed from cache"
      fi
    fi
    if [[ -f "$cf" ]]; then
      backup_file "$cf"
      "$OV_PY" - "$cf" <<'PYREG'
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
    print("Plugin registered (old MCP+prompt cleaned)")
PYREG
      log_ok "Plugin registered in codearts_cli.json"
    fi
    create_ov_config "$sandbox" ".codeartsdoer"
  else
    log_info "No live CodeArts sandbox found; plugin will be installed on next start"
  fi
  backup_file "$tpl"
  "$OV_PY" - "$tpl" "$OV_PLUGIN_SDK_VER" "$OV_OPENCODE_PLUGIN_VER" "$OV_NPM_REGISTRY_DEFAULT" "$OV_PLUGIN_CACHE_DIR" "$OV_SHARED_DIR" <<'PYTPL'
import sys, os
tpl_path = sys.argv[1]
sdk_ver = sys.argv[2]
plugin_ver = sys.argv[3]
npm_registry = sys.argv[4]
plugin_cache_dir = sys.argv[5]
shared_dir = sys.argv[6]
with open(tpl_path) as f:
    tpl = f.read()
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
    if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" && -d "$OV_PLUGIN_SHARED/../@opencode-ai" ]]; then
      cp -a "$OV_PLUGIN_SHARED/../@opencode-ai" "$OV_NPM_DIR/node_modules/@opencode-ai"
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
        rm -rf "$OV_PLUGIN_SHARED/../@opencode-ai"
        cp -a "$OV_NPM_DIR/node_modules/@opencode-ai" "$OV_PLUGIN_SHARED/../@opencode-ai"
      fi
    else
      echo "WARN: npm install failed — plugin will not load"
    fi
  else
    echo "WARN: npm not found and no cache available — plugin will not load"
  fi
fi
if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" ]]; then
  if [[ -d "$OV_PLUGIN_SHARED/../@opencode-ai" ]]; then
    cp -a "$OV_PLUGIN_SHARED/../@opencode-ai" "$OV_NPM_DIR/node_modules/@opencode-ai"
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
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for CodeArts ──\n")
    f.write("# Sourced by the CodeArts template start.sh.\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block.lstrip("\n"))
os.chmod(init_path, 0o755)
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-codearts-init.sh\n# ── End OpenViking integration ──\n\n"
marker = "sleep infinity"
idx = tpl.find(marker)
if idx == -1:
    print("ERROR: insertion marker 'sleep infinity' not found", file=sys.stderr)
    sys.exit(1)
tpl = tpl[:idx] + source_block + tpl[idx:]
with open(tpl_path, "w") as f:
    f.write(tpl)
PYTPL
  if [[ $? -ne 0 ]]; then
    log_error "Failed to inject plugin deployment block into template"
    return 1
  fi
  log_ok "CodeArts template updated with cache-first plugin deployment"
  ov_log_info "重启 CodeArts 以激活插件" "Restart CodeArts for plugin to activate"
}
agent_codearts_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  if grep -q "OpenViking integration\|@openviking/opencode-plugin\|opencode-plugin" "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  else
    has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  fi
  local sandbox; sandbox=$(find_sandbox "codearts")
  local sandbox_has_ov=false
  local cf=""
  if [[ -n "$sandbox" ]]; then
    cf="${sandbox}/.codeartsdoer/codearts_cli.json"
    if [[ -f "$cf" ]]; then
      "$OV_PY" -c "import json,sys; d=json.load(open('$cf')); sys.exit(0 if '@openviking/opencode-plugin' in d.get('plugin',[]) else 1)" 2>/dev/null && sandbox_has_ov=true
      check_json_mcp "$cf" 2>/dev/null && sandbox_has_ov=true
      "$OV_PY" -c "import json; cfg=json.load(open('$cf')); exit(0 if 'OpenViking' in cfg.get('agent',{}).get('build',{}).get('prompt','') else 1)" 2>/dev/null && sandbox_has_ov=true
    fi
    [[ -f "${sandbox}/.codeartsdoer/openviking-config.json" ]] && sandbox_has_ov=true
    [[ -d "${sandbox}/.codeartsdoer/node_modules/@openviking/opencode-plugin" ]] && sandbox_has_ov=true
  fi
  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "CodeArts not integrated (nothing to remove)"; return 0; }
  require_confirmation "UNBIND OpenViking" "codearts" "Remove OpenViking plugin + npm packages + config from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking integration from template and sandbox"; then return 0; fi
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    "$OV_PY" - "$tpl" <<'PYUNBIND'
import sys
path = sys.argv[1]
with open(path) as f: content = f.read()
marker = "# ── OpenViking integration"
idx = content.find(marker)
if idx != -1:
    end_idx = content.find("sleep infinity", idx)
    if end_idx != -1:
        with open(path, 'w') as f: f.write(content[:idx] + content[end_idx:])
        print("Removed OpenViking integration block from template")
    else:
        print("WARNING: end marker not found, skipping template removal")
else:
    print("No OpenViking integration block found in template")
PYUNBIND
    log_ok "OpenViking integration block removed from template"
    rm -f "$OV_SHARED_DIR/ov-codearts-init.sh" && log_ok "Removed ov-codearts-init.sh"
  fi
  if [[ -n "$sandbox" ]]; then
    if [[ -n "$cf" && -f "$cf" ]]; then
      backup_file "$cf"
      "$OV_PY" - "$cf" <<'PYUNBIND2'
import json, sys
path = sys.argv[1]
with open(path) as f: cfg = json.load(f)
changed = False
if "plugin" in cfg and "@openviking/opencode-plugin" in cfg["plugin"]:
    cfg["plugin"].remove("@openviking/opencode-plugin")
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
    with open(path, 'w') as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("Removed OpenViking from codearts_cli.json")
PYUNBIND2
      log_ok "OpenViking plugin removed from live sandbox"
    fi
    local ov_npm_dir="${sandbox}/.codeartsdoer"
    rm -rf "${ov_npm_dir}/node_modules" 2>/dev/null && log_ok "node_modules removed"
    rm -f "${ov_npm_dir}/package.json" 2>/dev/null
    rm -f "${ov_npm_dir}/package-lock.json" 2>/dev/null
    rm -f "${ov_npm_dir}/.npmrc" 2>/dev/null
    rm -f "${ov_npm_dir}/openviking-config.json" 2>/dev/null
    rm -rf "${ov_npm_dir}/openviking" 2>/dev/null
    log_ok "npm packages and config cleaned up"
  fi
  if [[ -n "$sandbox" && -f "${sandbox}/AGENTS.md" ]] && grep -q "OpenViking" "${sandbox}/AGENTS.md" 2>/dev/null; then
    rm -f "${sandbox}/AGENTS.md"
    log_ok "AGENTS.md removed (old approach cleanup)"
  fi
  ov_log_info "重启 CodeArts 以使更改完全生效" "Restart CodeArts for changes to take full effect"
}
agent_codearts_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  if grep -q "OpenViking integration\|@openviking/opencode-plugin\|opencode-plugin" "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  else
    has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  fi
  local sandbox; sandbox=$(find_sandbox "codearts")
  [[ -z "$sandbox" ]] && { ov_status "codearts" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.codeartsdoer/codearts_cli.json"
  [[ ! -f "$cf" ]] && { ov_status "codearts" "unknown" "config not found"; return; }
  local sandbox_has_ov=false
  if "$OV_PY" -c "import json,sys; d=json.load(open('$cf')); sys.exit(0 if '@openviking/opencode-plugin' in d.get('plugin',[]) else 1)" 2>/dev/null; then
    sandbox_has_ov=true
  elif check_json_mcp "$cf" 2>/dev/null; then
    sandbox_has_ov=true
  fi
  local plugin_installed=false
  if [[ -d "${sandbox}/.codeartsdoer/node_modules/@openviking/opencode-plugin" ]]; then
    plugin_installed=true
  fi
  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    if [[ "$plugin_installed" == "true" ]]; then
      ov_status "codearts" "integrated" "Official @openviking/opencode-plugin (cache-first, template + live)"
    else
      ov_status "codearts" "integrated" "Plugin configured (template + live), restart to activate"
    fi
  elif [[ "$tpl_has_ov" == "true" ]]; then
    ov_status "codearts" "integrated" "Plugin configured (template only, restart to activate)"
  elif [[ "$sandbox_has_ov" == "true" ]]; then
    ov_status "codearts" "partial" "Plugin/MCP in live only, lost on restart"
  else
    ov_status "codearts" "not_integrated" "No OpenViking integration found"
  fi
}
