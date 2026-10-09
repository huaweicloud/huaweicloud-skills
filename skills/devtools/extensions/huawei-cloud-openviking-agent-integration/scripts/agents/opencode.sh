#!/bin/bash
# agents/opencode.sh — OpenCode agent subclass (Plugin + openviking-config.json)
# Inherits from lib/base.sh; overrides: integrate, unbind, status
agent_opencode_register() {
  agent::set_meta name "opencode"
  agent::set_meta display_name "OpenCode"
  agent::set_meta sandbox_pattern "opencode-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/opencode/start.sh"
  agent::set_meta config_path "$OV_SANDBOX_DIR/opencode-*/.config/opencode/opencode.json"
  agent::set_meta mechanism "Plugin + openviking-config.json"
  registry_add "opencode"
}
_ov_opencode() { "$OV_PY" "$OV_PY_DIR/agents/ov_opencode.py" "$@"; }
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
  local _ver; _ver=$(ov_probe_package_version "$plugin_dst/package.json") || _ver="${OV_OPENCODE_PLUGIN_VER:-latest}"
  sed -i "s/__OV_OPENCODE_PLUGIN_VER__/$_ver/g" "$cache_pkg/package.json" "$cache_pkg/package-lock.json" "$cache_pkg/node_modules/.package-lock.json"
  # Use the resolved real version (not the possibly-latest constant) for the
  # versioned cache dir — avoids self-copy when OV_OPENCODE_PLUGIN_VER=latest.
  local cache_ver="${home_dir}/.cache/opencode/packages/@openviking/opencode-plugin@${_ver}"
  if [[ "$_ver" != "latest" && ! -d "$cache_ver/node_modules/@openviking/opencode-plugin" ]]; then
    cp -a "$cache_pkg" "$cache_ver"
    sed -i "s/@openviking/opencode-plugin@latest/@openviking/opencode-plugin@${_ver}/g" "$cache_ver/package-lock.json" "$cache_ver/node_modules/.package-lock.json" 2>/dev/null || true
  fi
}
agent_opencode_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "OpenCode template start.sh not found: $tpl"; return 1; }
  local ov_pkg="@openviking/opencode-plugin"
  # ISSUE-011: idempotency must verify template AND live — a template-only grep
  # falsely reported "already integrated" for partially-unbound/restored states
  local tpl_has=false live_has=false
  if grep -q "ov-opencode-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-opencode-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has=true
  fi
  local _sbx_once; _sbx_once=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$_sbx_once" && -f "$_sbx_once/.config/opencode/opencode.json" ]]; then
    check_json_mcp "$_sbx_once/.config/opencode/opencode.json" && live_has=true
    _ov_opencode check-plugin "$_sbx_once/.config/opencode/opencode.json" 2>/dev/null && live_has=true
  fi
  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    log_ok "OpenCode already integrated with OpenViking (template + live)"
    return 0
  fi
  require_confirmation "Integrate OpenViking (npm + domestic mirror fallback)" "opencode" \
    "Install @openviking/opencode-plugin (npm online first, on-demand GitHub mirror fallback) + plugin SDK + openviking-config.json to template start.sh (persistent)" \
    || return 1
  if dry_run_msg "Would install OpenViking plugin (npm → on-demand GitHub fallback) to $tpl and live sandbox"; then return 0; fi
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    local ov_npm_dir="${sandbox}/.config/opencode"
    local NPM_REGISTRY; NPM_REGISTRY=$(ov_first_npm_registry)
    echo "registry=${NPM_REGISTRY}" > "${ov_npm_dir}/.npmrc"
    log_ok ".npmrc created ($NPM_REGISTRY)"
    local _ov_ver; _ov_ver=$(ov_effective_plugin_ver "${ov_npm_dir}/node_modules/@openviking/opencode-plugin/package.json" "$OV_OPENCODE_PLUGIN_VER")
    ov_deploy_plugin_tiered "$ov_pkg" "$ov_npm_dir" "$NPM_REGISTRY" "opencode-plugin" "@openviking/opencode-plugin" "$_ov_ver" || true
    case "$_ov_tiered_result" in
      existing)  log_ok "Plugin already installed (cache hit)" ;;
      cache)     log_ok "Plugin from shared cache" ;;
      npm)       log_ok "Plugin from npm" ;;
      provision) log_ok "Plugin provisioned from GitHub" ;;
      *)
        log_warn "All plugin installation methods failed"
        if [[ ! -d "${ov_npm_dir}/node_modules/@openviking/opencode-plugin" ]]; then
          log_error "Plugin not installed and no existing copy — aborting integrate"
          return 1
        fi
        ;;
    esac
    # Agent-specific: ensure @opencode-ai SDK is available (from cache or npm)
    if [[ ! -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
      local sdk_cache; sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
      if [[ -d "$sdk_cache" ]]; then
        cp -a "$sdk_cache" "${ov_npm_dir}/node_modules/@opencode-ai"
        log_ok "Plugin SDK from shared cache"
      elif command -v npm &>/dev/null || command -v "${OV_NPM:-npm}" &>/dev/null; then
        (cd "$ov_npm_dir" && "${OV_NPM:-npm}" install "@opencode-ai/plugin@$OV_PLUGIN_SDK_VER" --registry="$NPM_REGISTRY" --no-audit --no-fund 2>&1 | tail -3) && \
          log_ok "Plugin SDK from npm"
        if [[ -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
          mkdir -p "$(dirname "$sdk_cache")"
          ov_safe_rm "$sdk_cache" 2>/dev/null || true
          cp -a "${ov_npm_dir}/node_modules/@opencode-ai" "$sdk_cache"
        fi
      fi
    fi
    local cf="${sandbox}/.config/opencode/opencode.json"
    backup_file "$cf"
    _ov_opencode register-plugin "$cf" "$OV_OPENCODE_PLUGIN_VER"
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
    ov_plugin_provision "opencode-plugin" "$_prov_dir" || { ov_safe_rm "$_prov_dir" 2>/dev/null || true; return 1; }
    ov_plugin_cache_put "$ov_pkg" "$_prov_dir" || log_warn "ISSUE-019: cache write failed for $ov_pkg"
    ov_safe_rm "$_prov_dir" 2>/dev/null || true
    log_ok "opencode-plugin provisioned to shared cache"
  fi
  local env_yaml="$OV_TEMPLATE_DIR/opencode/env.yaml"
  if [[ -f "$env_yaml" ]]; then
    backup_file "$env_yaml"
    _ov_opencode fix-env-yaml "$env_yaml"
    log_ok "OpenCode env.yaml updated (nodejs accessible in sandbox)"
  fi
  backup_file "$tpl"
  _ov_opencode integrate-template "$tpl" "$OV_PLUGIN_SDK_VER" "$OV_OPENCODE_PLUGIN_VER" "$OV_NPM_REGISTRY_DEFAULT" "$OV_PLUGIN_CACHE_DIR" "$OV_SHARED_DIR" "$OV_TEMPLATE_DIR"
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
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local sandbox_has_ov=false
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    check_json_mcp "${sandbox}/.config/opencode/opencode.json" && sandbox_has_ov=true
    _ov_opencode check-plugin "${sandbox}/.config/opencode/opencode.json" 2>/dev/null && sandbox_has_ov=true
  fi
  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "OpenCode not integrated (nothing to remove)"; return 0; }
  require_confirmation "UNBIND OpenViking" "opencode" "Remove OpenViking plugin + npm packages + config from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking integration from template and sandbox"; then return 0; fi
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    _ov_opencode unbind-template "$tpl"
    log_ok "OpenViking integration block removed from template"
    rm -f "$OV_SHARED_DIR/ov-opencode-init.sh" && log_ok "Removed ov-opencode-init.sh"
  fi
  local env_yaml="$OV_TEMPLATE_DIR/opencode/env.yaml"
  if [[ -f "$env_yaml" ]]; then
    backup_file "$env_yaml"
    _ov_opencode restore-env-yaml "$env_yaml"
    log_ok "OpenCode env.yaml restored"
  fi
  if [[ -n "$sandbox" ]]; then
    local cf="${sandbox}/.config/opencode/opencode.json"
    if [[ -f "$cf" ]]; then
      backup_file "$cf"
      _ov_opencode unbind-live-config "$cf"
      log_ok "OpenViking plugin removed from live sandbox"
    fi
    # ISSUE-009: only remove OpenViking-owned packages — never the whole node_modules
    # (users may have extra packages installed there)
    ov_safe_rm "${sandbox}/.config/opencode/node_modules/@openviking" 2>/dev/null || true
    ov_safe_rm "${sandbox}/.config/opencode/node_modules/@opencode-ai" 2>/dev/null || true
    log_ok "OpenViking plugin packages removed (user packages in node_modules kept)"
    # OV-owned files: openviking-config.json and the .npmrc written by integrate.sh
    rm -f  "${sandbox}/.config/opencode/.npmrc" \
           "${sandbox}/.config/opencode/openviking-config.json" 2>/dev/null
    ov_safe_rm "${sandbox}/.config/opencode/plugins/openviking" 2>/dev/null || true
    rm -f  "${sandbox}/.config/opencode/plugins/openviking.js" 2>/dev/null
    ov_safe_rm "${sandbox}/.opencode/node_modules/@openviking" 2>/dev/null || true
    ov_safe_rm "${sandbox}/.cache/opencode/packages/@openviking" 2>/dev/null || true
    log_ok "npm packages, .opencode/, .cache/ cleaned up"
  fi
  local oc_deps_cache="${OV_PLUGIN_CACHE_DIR%/openviking-plugins}/opencode-deps"
  if [[ -d "$oc_deps_cache" ]]; then
    ov_safe_rm "$oc_deps_cache" 2>/dev/null || true
    log_ok "OpenCode deps shared cache cleaned up"
  fi
  local npm_cache="${OV_PLUGIN_CACHE_DIR%/openviking-plugins}/opencode-npm-cache"
  if [[ -d "$npm_cache" ]]; then
    ov_safe_rm "$npm_cache" 2>/dev/null || true
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
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { ov_status "opencode" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.config/opencode/opencode.json"
  local sandbox_has_ov=false
  if [[ -f "$cf" ]]; then
    if _ov_opencode check-plugin "$cf" 2>/dev/null; then
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
  local d_integrated=""
  if [[ "$plugin_installed" == "true" ]]; then
    if [[ "$plugin_source" == "cache" ]]; then
      d_integrated="Official @openviking/opencode-plugin (.cache pre-populated, template + live)"
    else
      d_integrated="Official @openviking/opencode-plugin (runtime install, template + live)"
    fi
  else
    d_integrated="MCP: $(get_json_mcp_url "$cf" 2>/dev/null || echo "unknown")"
  fi
  local d_template="Plugin configured (template only, restart to activate)"
  [[ "$plugin_installed" == "true" ]] && d_template="Plugin installed (template + live), restart to activate hooks"
  agent::report_status "${AGENT_META[name]}" "$tpl_has_ov" "$sandbox_has_ov" \
    "$d_integrated" "$d_template" \
    "Plugin/MCP in live only, lost on restart" \
    "No OpenViking integration found"
}
