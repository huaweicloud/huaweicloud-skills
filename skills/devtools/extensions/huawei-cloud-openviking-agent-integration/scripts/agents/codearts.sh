#!/bin/bash
# agents/codearts.sh — CodeArts CLI agent subclass (OpenCode engine + @openviking/opencode-plugin)
# Inherits from lib/base.sh; overrides: integrate, unbind, status
agent_codearts_register() {
  agent::set_meta name "codearts"
  agent::set_meta display_name "CodeArts CLI"
  agent::set_meta sandbox_pattern "codearts-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/codearts/start.sh"
  agent::set_meta config_path "$OV_HOME/.codearts/settings.json"
  agent::set_meta mechanism "Plugin (@openviking/opencode-plugin)"
  registry_add "codearts"
}
_ov_codearts() { "$OV_PY" "$OV_PY_DIR/agents/ov_codearts.py" "$@"; }
agent_codearts_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "CodeArts template start.sh not found: $tpl"; return 1; }
  local ov_pkg="@openviking/opencode-plugin"
  # ISSUE-011: idempotency must verify template AND live — a template-only grep
  # falsely reported "already integrated" for partially-unbound/restored states
  local tpl_has=false live_has=false
  if grep -q "ov-codearts-init.sh\|@openviking/opencode-plugin" "$tpl" 2>/dev/null; then
    tpl_has=true
  fi
  local _sbx_once; _sbx_once=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$_sbx_once" ]]; then
    local _cf_once="${_sbx_once}/.codeartsdoer/codearts_cli.json"
    if [[ -f "$_cf_once" ]]; then
      _ov_codearts has-plugin "$_cf_once" 2>/dev/null && live_has=true
      check_json_mcp "$_cf_once" 2>/dev/null && live_has=true
      _ov_codearts has-prompt "$_cf_once" 2>/dev/null && live_has=true
    fi
    [[ -f "${_sbx_once}/.codeartsdoer/openviking-config.json" ]] && live_has=true
    [[ -d "${_sbx_once}/.codeartsdoer/node_modules/@openviking/opencode-plugin" ]] && live_has=true
  fi
  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    log_ok "CodeArts already integrated with OpenViking (template + live)"
    return 0
  fi
  require_confirmation "Integrate OpenViking (plugin + cache-first deployment)" "codearts" \
    "Install @openviking/opencode-plugin (cache-first from codearts package cache, npm fallback) + plugin SDK + openviking-config.json to template start.sh (persistent)" \
    || return 1
  if dry_run_msg "Would install OpenViking plugin (cache → npm fallback) to $tpl and live sandbox"; then return 0; fi
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
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
        ov_plugin_cache_put "$ov_pkg" "$plugin_dst" || log_warn "ISSUE-019: cache write failed for $ov_pkg"
        log_ok "Plugin saved to shared cache"
        if [[ -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
          local _sdk_cache; _sdk_cache=$(ov_plugin_cache_path "@opencode-ai")
          mkdir -p "$(dirname "$_sdk_cache")"
          ov_safe_rm "$_sdk_cache" 2>/dev/null || true
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
      if [[ ! -d "$plugin_dst" ]]; then
        local _pcache; _pcache=$(ov_plugin_cache_path "$ov_pkg")
        if [[ -d "$_pcache" ]]; then
          cp -a "$_pcache" "$plugin_dst"
          log_ok "Plugin re-deployed from cache"
        fi
      fi
    fi
    if [[ -f "$cf" ]]; then
      backup_file "$cf"
      _ov_codearts register-plugin "$cf"
      log_ok "Plugin registered in codearts_cli.json"
    fi
    create_ov_config "$sandbox" ".codeartsdoer"
  else
    log_info "No live CodeArts sandbox found; plugin will be installed on next start"
  fi
  backup_file "$tpl"
  _ov_codearts inject-template "$tpl" "$OV_PLUGIN_SDK_VER" "$OV_OPENCODE_PLUGIN_VER" "$OV_NPM_REGISTRY_DEFAULT" "$OV_PLUGIN_CACHE_DIR" "$OV_SHARED_DIR"
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
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local sandbox_has_ov=false
  local cf=""
  if [[ -n "$sandbox" ]]; then
    cf="${sandbox}/.codeartsdoer/codearts_cli.json"
    if [[ -f "$cf" ]]; then
      _ov_codearts has-plugin "$cf" 2>/dev/null && sandbox_has_ov=true
      check_json_mcp "$cf" 2>/dev/null && sandbox_has_ov=true
      _ov_codearts has-prompt "$cf" 2>/dev/null && sandbox_has_ov=true
    fi
    [[ -f "${sandbox}/.codeartsdoer/openviking-config.json" ]] && sandbox_has_ov=true
    [[ -d "${sandbox}/.codeartsdoer/node_modules/@openviking/opencode-plugin" ]] && sandbox_has_ov=true
  fi
  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "CodeArts not integrated (nothing to remove)"; return 0; }
  require_confirmation "UNBIND OpenViking" "codearts" "Remove OpenViking plugin + npm packages + config from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking integration from template and sandbox"; then return 0; fi
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    _ov_codearts unbind-template "$tpl"
    log_ok "OpenViking integration block removed from template"
    rm -f "$OV_SHARED_DIR/ov-codearts-init.sh" && log_ok "Removed ov-codearts-init.sh"
  fi
  if [[ -n "$sandbox" ]]; then
    if [[ -n "$cf" && -f "$cf" ]]; then
      backup_file "$cf"
      _ov_codearts remove-plugin "$cf"
      log_ok "OpenViking plugin removed from live sandbox"
    fi
    local ov_npm_dir="${sandbox}/.codeartsdoer"
    # ISSUE-009: only remove OpenViking-owned packages — never the whole node_modules
    ov_safe_rm "${ov_npm_dir}/node_modules/@openviking" 2>/dev/null || true
    ov_safe_rm "${ov_npm_dir}/node_modules/@opencode-ai" 2>/dev/null || true
    log_ok "OpenViking plugin packages removed (user packages in node_modules kept)"
    # OV-injected project files (package.json/.npmrc were written by integrate.sh)
    rm -f "${ov_npm_dir}/package.json" 2>/dev/null
    rm -f "${ov_npm_dir}/package-lock.json" 2>/dev/null
    rm -f "${ov_npm_dir}/.npmrc" 2>/dev/null
    rm -f "${ov_npm_dir}/openviking-config.json" 2>/dev/null
    ov_safe_rm "${ov_npm_dir}/openviking" 2>/dev/null || true
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
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { ov_status "codearts" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.codeartsdoer/codearts_cli.json"
  [[ ! -f "$cf" ]] && { ov_status "codearts" "unknown" "config not found"; return; }
  local sandbox_has_ov=false
  # ISSUE-012: live detection must match unbind (has-plugin alone missed
  # has-prompt / openviking-config.json / installed node_modules states)
  if _ov_codearts has-plugin "$cf" 2>/dev/null; then
    sandbox_has_ov=true
  elif check_json_mcp "$cf" 2>/dev/null; then
    sandbox_has_ov=true
  fi
  _ov_codearts has-prompt "$cf" 2>/dev/null && sandbox_has_ov=true
  [[ -f "${sandbox}/.codeartsdoer/openviking-config.json" ]] && sandbox_has_ov=true
  [[ -d "${sandbox}/.codeartsdoer/node_modules/@openviking/opencode-plugin" ]] && sandbox_has_ov=true
  local plugin_installed=false
  if [[ -d "${sandbox}/.codeartsdoer/node_modules/@openviking/opencode-plugin" ]]; then
    plugin_installed=true
  fi
  local d_integrated="Plugin configured (template + live), restart to activate"
  [[ "$plugin_installed" == "true" ]] && d_integrated="Official @openviking/opencode-plugin (cache-first, template + live)"
  agent::report_status "${AGENT_META[name]}" "$tpl_has_ov" "$sandbox_has_ov" \
    "$d_integrated" \
    "Plugin configured (template only, restart to activate)" \
    "Plugin/MCP in live only, lost on restart" \
    "No OpenViking integration found"
}
