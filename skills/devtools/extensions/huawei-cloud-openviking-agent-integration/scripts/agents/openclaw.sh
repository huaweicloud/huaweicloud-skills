#!/bin/bash
# agents/openclaw.sh — OpenClaw agent subclass (ClawHub plugin + contextEngine)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_openclaw_register() {
  agent::set_meta name "openclaw"
  agent::set_meta display_name "OpenClaw"
  agent::set_meta sandbox_pattern "openclaw-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/openclaw/start.sh"
  agent::set_meta mechanism "ClawHub plugin + contextEngine"
  registry_add "openclaw"
}

_ov_openclaw() { "$OV_PY" "$OV_PY_DIR/agents/ov_openclaw.py" "$@"; }

agent_openclaw_integrate() {
  # OpenClaw runs in bwrap; config is inside sandbox. Inject plugin install into template start.sh.
  # Official: plugins install clawhub:@openviking/openclaw-plugin → openviking setup --json → gateway restart.
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "OpenClaw template start.sh not found: $tpl"; return 1; }

  local ov_runtime_src="$OV_RUNTIME_DIR/openclaw/openviking-plugin-source"
  # Install plugin source — npm first, fall back to GitHub download
  local _ov_npm_ok=0
  if [[ "${DRY_RUN:-false}" != "true" ]]; then
    mkdir -p /tmp/openviking
    local _npm_stage; _npm_stage=$(mktemp -d /tmp/openviking/ov-npm.XXXXXX) || { log_warn "mktemp failed, falling back to GitHub"; _npm_stage=""; }
    # P8: the pinned 0.2.4 tarball is `notarget` on the Huawei mirror, which used to
    # force a slow npm → GitHub → source-build fallback. Try every domestic-first
    # registry, then `latest`, before giving up and going to GitHub provision.
    local _ver _reg
    for _ver in 0.2.4 latest; do
      for _reg in "${NPM_REGISTRIES[@]}"; do
        [[ -n "$_npm_stage" ]] || break 2
        ov_safe_rm "$_npm_stage/node_modules" 2>/dev/null || true
        ov_safe_rm "$_npm_stage/package-lock.json" 2>/dev/null || true
        printf '{"dependencies":{"@openviking/openclaw-plugin":"%s"}}\n' "$_ver" > "$_npm_stage/package.json"
        log_info "Trying npm install @openviking/openclaw-plugin@$_ver ($_reg)..."
        if (cd "$_npm_stage" && "$OV_NPM" install \
            --registry="$_reg" --no-audit --no-fund 2>&1 | tail -5) && \
           [[ -d "$_npm_stage/node_modules/@openviking/openclaw-plugin" ]]; then
          ov_safe_rm "$ov_runtime_src" 2>/dev/null || true
          mkdir -p "$(dirname "$ov_runtime_src")" || { log_error "Cannot create runtime dir: $(dirname "$ov_runtime_src")"; return 1; }
          cp -a "$_npm_stage/node_modules/@openviking/openclaw-plugin" "$ov_runtime_src" || { log_error "Plugin source copy failed"; return 1; }
          touch "$ov_runtime_src" || { log_error "Cannot touch $ov_runtime_src"; return 1; }
          log_ok "openclaw-plugin installed from npm ($_ver, $_reg) -> $ov_runtime_src"
          _ov_npm_ok=1
          break 2
        fi
        log_warn "npm install @openviking/openclaw-plugin@$_ver ($_reg) failed"
      done
    done
    [[ "$_ov_npm_ok" -eq 0 ]] && log_warn "npm install failed for all registries/versions — falling back to GitHub source download"
    [[ -n "$_npm_stage" ]] && { ov_safe_rm "$_npm_stage" 2>/dev/null || true; }
  fi
  if [[ "$_ov_npm_ok" -eq 0 ]]; then
    ov_plugin_provision "openclaw-plugin" "$ov_runtime_src" || return 1
    [[ "${DRY_RUN:-false}" == "true" ]] || log_ok "openclaw-plugin source installed on demand at $ov_runtime_src"
  fi
  # ── Pre-build plugin at integrate time for fast runtime recovery ──
  # npm package ships with dist/ pre-compiled; we only install runtime deps (no tsc needed).
  # Stores ready-to-use result (dist/ + node_modules/) in persistent runtime cache.
  # At start.sh time, Tier-0 fast path just plugins install (no npm/tsc needed).
  local ov_prebuilt="$OV_RUNTIME_DIR/openclaw/openviking-plugin-built"
  if [[ "${DRY_RUN:-false}" != "true" && -d "$ov_runtime_src" ]]; then
    log_info "Pre-building openclaw-plugin (npm install for runtime deps) for fast runtime recovery..."
    local _pb_stage; _pb_stage=$(mktemp -d /tmp/openviking/ov-prebuild.XXXXXX) || _pb_stage=""
    if [[ -n "$_pb_stage" ]]; then
      cp -a "$ov_runtime_src/." "$_pb_stage/"
      local _npm_reg; _npm_reg=$(ov_first_npm_registry)
      export NPM_CONFIG_REGISTRY="$_npm_reg"
      if (cd "$_pb_stage" && "$OV_NPM" install --production --no-audit --no-fund 2>&1 | tail -5) && \
         [[ -d "$_pb_stage/dist" ]]; then
        ov_safe_rm "$ov_prebuilt" 2>/dev/null || true
        cp -a "$_pb_stage" "$ov_prebuilt"
        touch "$ov_prebuilt"
        log_ok "Pre-built plugin cached at $ov_prebuilt (dist/ + node_modules/ ready)"
      else
        log_warn "Pre-build failed — runtime will fall back to source build (slower)"
      fi
      unset NPM_CONFIG_REGISTRY
      ov_safe_rm "$_pb_stage" 2>/dev/null || true
    fi
  fi
  # Check if already integrated — ISSUE-011: template-only is a HALF state and
  # must not be reported as success; fall through to re-sync/repair instead
  if grep -q "OpenViking plugin install\|ov-openclaw-init.sh" "$tpl" 2>/dev/null; then
    local gw_pid="" _live_endpoint=false
    gw_pid=$(pgrep -f "openclaw-gateway" 2>/dev/null | head -1)
    if [ -n "$gw_pid" ] && [ -f "/proc/$gw_pid/environ" ]; then
      if tr '\0' '\n' < "/proc/$gw_pid/environ" 2>/dev/null | grep -q "OPENVIKING_BASE_URL=http"; then
        _live_endpoint=true
        log_ok "OpenClaw already integrated (official plugin install in start.sh + live endpoint)"
      fi
    else
      log_warn "OpenClaw gateway process not found — sandbox may not be running"
    fi
    if [[ "$_live_endpoint" == "true" ]]; then
      return 0
    fi
    log_warn "OpenClaw template has plugin install but live gateway endpoint is missing — re-running integrate to re-sync start.sh (restart sandbox after)"
  fi
  # Slot-replacement approval: check if another plugin owns contextEngine
  local force_slot=0
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    if [[ -f "$cfg_file" ]] && _ov_openclaw slot-owner "$cfg_file" 2>/dev/null | grep -qv '^$' && ! _ov_openclaw slot-owner "$cfg_file" 2>/dev/null | grep -q 'openviking'; then
      log_warn "plugins.slots.contextEngine is currently owned by another plugin"
      if [[ "${AUTO_YES:-false}" == "true" ]]; then
        force_slot=1
      else
        read -p "Allow --force-slot to replace it (yes/no)? " ans
        [[ "$ans" == "yes" || "$ans" == "y" ]] && force_slot=1
      fi
    fi
  done
  local allow_offline=1   # dev-mode local server; safe default
  require_confirmation "Integrate OpenViking (Official ClawHub Plugin)" "openclaw" "Install @openviking/openclaw-plugin (ClawHub → domestic npm mirror → on-demand source build fallback) + openviking setup --json into template start.sh (contextEngine slot, auto-recall + auto-capture)" || return 1
  if dry_run_msg "Would add OpenViking plugin install to $tpl"; then return 0; fi
  backup_file "$tpl"
  # Insert official plugin install block before the gateway start step
  _ov_openclaw inject "$tpl" "$OV_ENDPOINT" "$force_slot" "$allow_offline" "$OV_NPM_REGISTRY_DEFAULT" "$OV_SHARED_DIR" "$OV_RUNTIME_DIR" "$OV_TEMPLATE_DIR"
  log_ok "OpenClaw template updated with official OpenViking plugin install"
  # Sync to sandbox workspace — ISSUE-013: path join must use a slash, and a
  # missing process_dir must not be reported as synced
  local sandbox_dir=""
  sandbox_dir=$(find_sandbox "openclaw")
  if [[ -n "$sandbox_dir" ]]; then
    ov_sync_template_to_sandbox "$tpl" "$sandbox_dir" process_dir
  fi
  # Clean up legacy direct-config-write injection and old MCP artifacts
  local cleaned=false
  if grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    _ov_openclaw clean-legacy-cfg "$tpl"
    cleaned=true
  fi
  if grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    _ov_openclaw clean-legacy-mcp "$tpl"
    cleaned=true
  fi
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    if [[ -d "$ext_dir" ]]; then
      ov_safe_rm "$ext_dir" 2>/dev/null || true
      cleaned=true
    fi
  done
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    if [[ -f "$cfg_file" ]] && _ov_openclaw has-mcp-server "$cfg_file" 2>/dev/null; then
      _ov_openclaw remove-mcp-server "$cfg_file" 2>/dev/null
      cleaned=true
    fi
  done
  [[ "$cleaned" == "true" ]] && log_ok "Legacy direct-config-write, MCP injection, and old artifacts cleaned"
  log_ok "OpenClaw integrated with OpenViking (official plugin via ClawHub → domestic npm → on-demand source build)"
  ov_log_info "重启 OpenClaw 以使更改生效" "Restart OpenClaw for changes to take effect"
}

agent_openclaw_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  # Detect OpenViking injection in template (all known formats)
  if [[ -f "$tpl" ]] && grep -qE '# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking|ov-openclaw-init\.sh' "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  fi
  local has_cfg=false
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    if [[ -f "$cfg_file" ]] && _ov_openclaw has-config "$cfg_file" 2>/dev/null; then
      has_cfg=true
    fi
  done
  local has_ext=false
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    [[ -d "$ext_dir" ]] && has_ext=true
  done
  if [[ "$tpl_has_ov" == "false" && "$has_cfg" == "false" && "$has_ext" == "false" ]]; then
    log_ok "OpenClaw not integrated (nothing to remove)"; return 0
  fi
  require_confirmation "UNBIND OpenViking" "openclaw" "Remove OpenViking plugin install from template start.sh and clean up config files" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking plugin config and legacy artifacts"; then return 0; fi
  # Remove ALL OpenViking-related Step 5.x blocks from template start.sh
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    _ov_openclaw unbind "$tpl" "$OV_SHARED_DIR"
    local remove_result=$?
    if [[ $remove_result -eq 0 ]]; then
      log_ok "OpenViking injection blocks removed from template start.sh"
    else
      log_warn "Template removal completed with issues"
    fi
    rm -f "$OV_SHARED_DIR/ov-openclaw-init.sh" && log_ok "Removed standalone ov-openclaw-init.sh"
    # Post-removal verification
    local residual_count
    residual_count=$(grep -ciE 'openviking' "$tpl" 2>/dev/null || true)
    if [[ "$residual_count" -gt 0 ]]; then
      log_warn "WARNING: $residual_count residual OpenViking reference(s) still in template start.sh — manual review needed"
      grep -niE 'openviking' "$tpl" 2>/dev/null | head -10 | while read -r line; do
        log_warn "  $line"
      done
    else
      log_ok "Verified: no OpenViking references remain in template start.sh"
    fi
    # Sync to sandbox workspace — ISSUE-013: slash-safe sync (matches integrate)
    local sandbox_dir=""
    for d in "$OV_SANDBOX_DIR"/openclaw-*/; do
      if [[ -d "${d}process_dir" ]]; then
        sandbox_dir="${d%/}"
        break
      fi
    done
    if [[ -n "$sandbox_dir" ]]; then
      ov_sync_template_to_sandbox "$tpl" "$sandbox_dir" process_dir
    fi
  fi
  # Clean up config files (plugin entries, MCP servers, tool policy)
  local cleaned=false
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    if [[ -d "$ext_dir" ]]; then
      ov_safe_rm "$ext_dir" 2>/dev/null || true
      cleaned=true
    fi
  done
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    [[ -f "$cfg_file" ]] || continue
    _ov_openclaw clean-config "$cfg_file" 2>/dev/null | grep -q "cleaned" && cleaned=true
  done
  [[ "$cleaned" == "true" ]] && log_ok "Config files cleaned (plugin entries, MCP servers, tool policy)"
  # Remove on-demand plugin source + AGENTS.md
  if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-source" ]]; then
    ov_safe_rm "$OV_RUNTIME_DIR/openclaw/openviking-plugin-source" 2>/dev/null || true
    log_ok "On-demand plugin source removed from persistent runtime location"
  fi
  if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-built" ]]; then
    ov_safe_rm "$OV_RUNTIME_DIR/openclaw/openviking-plugin-built" 2>/dev/null || true
    log_ok "Pre-built plugin cache removed from persistent runtime location"
  fi
  # Revert OPENCLAW_STATE_DIR to default /tmp (only for old hardcoded format)
  # Skip revert if start.sh uses dynamic derivation (${OPENCLAW_DIR}/state) —
  # persistent path is the new default, reverting to /tmp would reintroduce the
  # TUI config-not-found bug.
  local _esc_rt="${OV_RUNTIME_DIR//|/\\|}"
  if grep -q 'OPENCLAW_STATE_DIR.*\${OPENCLAW_DIR}/state' "$tpl" 2>/dev/null; then
    log_info "start.sh uses dynamic state dir — keeping persistent path (not reverting to /tmp)"
  elif grep -q "OPENCLAW_STATE_DIR.*${OV_RUNTIME_DIR}/openclaw/state" "$tpl" 2>/dev/null; then
    sed -i "s|OPENCLAW_STATE_DIR:-${_esc_rt}/openclaw/state|OPENCLAW_STATE_DIR:-/tmp/.openclaw|" "$tpl"
    sed -i 's|# ── State dir: persistent (survives sandbox restarts) ──|# ── State dir: inside sandbox, not mounted outside ──|' "$tpl"
    log_ok "Reverted OPENCLAW_STATE_DIR to default /tmp/.openclaw"
    # Revert env.yaml too (only for old hardcoded format)
    local env_yaml="$OV_TEMPLATE_DIR/openclaw/env.yaml"
    if [[ -f "$env_yaml" ]] && grep -q "OPENCLAW_STATE_DIR.*${OV_RUNTIME_DIR}/openclaw/state" "$env_yaml" 2>/dev/null; then
      sed -i "s|OPENCLAW_STATE_DIR: \"${_esc_rt}/openclaw/state\"|OPENCLAW_STATE_DIR: \"/tmp/.openclaw\"|" "$env_yaml"
      log_ok "Reverted env.yaml OPENCLAW_STATE_DIR to /tmp/.openclaw"
    fi
  fi
  # Clean up persistent state dir
  if [[ -d "$OV_RUNTIME_DIR/openclaw/state" ]]; then
    ov_safe_rm "$OV_RUNTIME_DIR/openclaw/state" 2>/dev/null || true
    log_ok "Persistent state dir removed"
  fi
  for agents_md in "$OV_HOME/.openclaw/workspace/AGENTS.md" "$OV_RUNTIME_DIR/openclaw/state/workspace/AGENTS.md"; do
    if [[ -f "$agents_md" ]] && grep -q "OpenViking" "$agents_md" 2>/dev/null; then
      rm -f "$agents_md"
      cleaned=true
    fi
  done
  log_ok "OpenViking removed from OpenClaw"
  ov_log_info "重启 OpenClaw 以使更改生效" "Restart OpenClaw for changes to take effect"
}

agent_openclaw_status() {
  local tpl="${AGENT_META[template_path]}"

  local has_plugin=false
  if [[ -f "$tpl" ]] && grep -qE "# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking|ov-openclaw-init\.sh" "$tpl" 2>/dev/null; then
    has_plugin=true
  fi
  local has_legacy_cfg=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    has_legacy_cfg=true
  fi
  local has_mcp=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    has_mcp=true
  fi
  local has_legacy=false
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    [[ -d "$ext_dir" ]] && has_legacy=true
  done
  local tpl_has="$has_plugin"
  local live_has=false
  [[ "$has_plugin" == "true" || "$has_legacy_cfg" == "true" || "$has_mcp" == "true" || "$has_legacy" == "true" ]] && live_has=true
  local d_integrated=""
  if [[ "$has_plugin" == "true" ]]; then
    local src_desc="ClawHub"
    grep -q "clawhub:@openviking/openclaw-plugin" "$tpl" 2>/dev/null || src_desc="npm mirror"
    if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-source" ]]; then
      src_desc="${src_desc} + on-demand source fallback"
    fi
    if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-built" ]]; then
      src_desc="${src_desc} + pre-built cache (fast recovery)"
    fi
    if grep -q "openviking setup .*--json" "$tpl" 2>/dev/null; then
      d_integrated="Official plugin install in start.sh (${src_desc}, contextEngine slot, setup --json contract) ✓"
    else
      d_integrated="Official plugin install in start.sh (${src_desc}, contextEngine slot) ✓"
    fi
  fi
  local d_live=""
  if [[ "$has_legacy_cfg" == "true" ]]; then
    d_live="Legacy direct-config-write found — run integrate to upgrade to official plugin install"
  elif [[ "$has_mcp" == "true" ]]; then
    d_live="Legacy MCP injection found — run integrate to upgrade to official plugin install"
  elif [[ "$has_legacy" == "true" ]]; then
    d_live="Legacy plugin artifacts found — run unbind to clean"
  fi
  agent::report_status "${AGENT_META[name]}" "$tpl_has" "$live_has" \
    "$d_integrated" "" "$d_live" "No OpenViking integration found"
}
