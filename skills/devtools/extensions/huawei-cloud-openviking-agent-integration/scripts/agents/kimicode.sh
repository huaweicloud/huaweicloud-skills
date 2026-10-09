#!/bin/bash
# agents/kimicode.sh — KimiCode agent subclass (hooks + MCP, path 3)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
# KimiCode strategy: dual-channel.
#   - MCP via mcp.json            → tool access (search/remember/forget/read/...)
#   - session lifecycle hooks     → auto-recall on SessionStart/UserPromptSubmit,
#                                   auto-capture on Stop/SessionEnd/PreCompact
agent_kimicode_register() {
  agent::set_meta name "kimicode"
  agent::set_meta display_name "KimiCode"
  agent::set_meta sandbox_pattern "kimicode-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/kimicode/start.sh"
  agent::set_meta config_path "$OV_HOME/.kimi/settings.json"
  agent::set_meta mechanism "hooks + MCP (session lifecycle)"
  registry_add "kimicode"
}
_ov_kimicode() { "$OV_PY" "$OV_PY_DIR/agents/ov_kimicode.py" "$@"; }

agent_kimicode_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "KimiCode template start.sh not found: $tpl"; return 1; }

  # ISSUE-011: idempotency must verify template AND live mcp.json — a template-only
  # check falsely reported "already integrated" for partially-unbound states
  local tpl_has=false live_has=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has=true
  grep -q "ov-kimicode-init.sh" "$tpl" 2>/dev/null && tpl_has=true
  local _mcp_once="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  local _cfg_once="$OV_RUNTIME_DIR/kimicode/data/config.toml"
  [[ -f "$_mcp_once" ]] && _ov_kimicode check-live-mcp "$_mcp_once" 2>/dev/null && live_has=true
  [[ -f "$_cfg_once" ]] && _ov_kimicode check-hooks "$_cfg_once" 2>/dev/null && live_has=true
  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    log_ok "KimiCode already integrated with OpenViking (hooks + MCP, template + live)"
    return 0
  fi

  require_confirmation "Integrate OpenViking (hooks + MCP)" "kimicode" \
    "Add OpenViking MCP to template start.sh (mcp.json) + session lifecycle hooks (config.toml [[hooks]] via ov-kimicode-init.sh) + deploy hook dispatcher (shared/ov-kimi-hook/)" \
    || return 1
  if dry_run_msg "Would add OpenViking MCP + session hooks to $tpl, live mcp.json/config.toml, and deploy hook dispatcher"; then return 0; fi
  backup_file "$tpl"
  _ov_kimicode integrate "$tpl" "$OV_MCP_URL" "$OV_SHARED_DIR" "$OV_TEMPLATE_DIR" "$OV_RUNTIME_DIR"
  log_ok "KimiCode template updated (MCP at $OV_MCP_URL + session hooks)"
  log_ok "Hook dispatcher deployed: $OV_SHARED_DIR/ov-kimi-hook/ov-kimi-hook.sh (+ py helpers under $OV_SHARED_DIR/py/)"
  # Write to live mcp.json (immediate effect)
  local mcp_file="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  _ov_kimicode write-live-mcp "$mcp_file" "$OV_MCP_URL"
  # Append [[hooks]] to live config.toml (immediate effect)
  local cfg_file="$OV_RUNTIME_DIR/kimicode/data/config.toml"
  if [[ -f "$cfg_file" ]]; then
    backup_file "$cfg_file"
    _ov_kimicode append-hooks-config "$cfg_file" "$OV_SHARED_DIR"
  fi
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$sandbox" ]]; then
    cp "${OV_PY_DIR%/*}/templates/agents-md-snippet.md" "${sandbox}/AGENTS.md"
    create_ov_config "$sandbox"
    log_ok "4-section AGENTS.md + config created in KimiCode sandbox workspace"
  fi
  log_ok "OpenViking MCP in live mcp.json + hooks in live config.toml (immediate effect)"
  ov_log_info "重启 KimiCode 以完全生效" "Restart KimiCode for full effect"
}

agent_kimicode_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-kimicode-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "Create openviking-config.json" "$tpl" 2>/dev/null && tpl_has_ov=true
  local mcp_file="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  local live_has_ov=false
  [[ -f "$mcp_file" ]] && _ov_kimicode check-live-mcp "$mcp_file" 2>/dev/null && live_has_ov=true

  local legacy_cf="$OV_RUNTIME_DIR/kimicode/data/config.toml"
  local legacy_has_ov=false
  [[ -f "$legacy_cf" ]] && grep -q "mcp_servers.openviking" "$legacy_cf" 2>/dev/null && legacy_has_ov=true
  [[ -f "$legacy_cf" ]] && _ov_kimicode check-hooks "$legacy_cf" 2>/dev/null && legacy_has_ov=true
  ( [[ -f "$OV_SHARED_DIR/ov-kimi-hook/ov-kimi-hook.sh" ]] || [[ -f "$OV_SHARED_DIR/ov-kimi-hook.sh" ]] ) && legacy_has_ov=true
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local ov_conf=""
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/openviking-config.json" ]]; then
    live_has_ov=true
    ov_conf="${sandbox}/.config/opencode/openviking-config.json"
  fi
  [[ "$tpl_has_ov" == "false" && "$live_has_ov" == "false" && "$legacy_has_ov" == "false" ]] && { log_ok "KimiCode not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking (hooks + MCP)" "kimicode" "Remove OpenViking MCP (mcp.json) + session hooks (config.toml [[hooks]]) + hook dispatcher (shared/ov-kimi-hook/) from template, config, and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking MCP + hooks + dispatcher"; then return 0; fi
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    _ov_kimicode unbind-template "$tpl" "$OV_SHARED_DIR"
    log_ok "OpenViking MCP + hooks block removed from template start.sh"
    rm -f "$OV_SHARED_DIR/ov-kimicode-init.sh" && log_ok "Removed standalone ov-kimicode-init.sh"
  fi
  if [[ "$live_has_ov" == "true" ]]; then
    if [[ -f "$mcp_file" ]]; then
      backup_file "$mcp_file"
      _ov_kimicode unbind-live-mcp "$mcp_file"
      log_ok "OpenViking MCP removed from live mcp.json"
    fi
  fi
  if [[ -n "$ov_conf" ]]; then
    rm -f "$ov_conf"
    log_ok "openviking-config.json removed from sandbox"
  fi
  # ISSUE-010: unbind must clean what integrate created in the sandbox workspace —
  # the 4-section AGENTS.md is written by integrate.sh and was left behind
  if [[ -n "$sandbox" && -f "${sandbox}/AGENTS.md" ]] && \
     grep -q "OpenViking\|openviking" "${sandbox}/AGENTS.md" 2>/dev/null; then
    if cmp -s "${sandbox}/AGENTS.md" "${OV_PY_DIR%/*}/templates/agents-md-snippet.md" 2>/dev/null; then
      rm -f "${sandbox}/AGENTS.md"
      log_ok "AGENTS.md removed from KimiCode sandbox workspace"
    else
      log_warn "AGENTS.md in sandbox differs from OpenViking template (user-modified) — left untouched"
    fi
  fi
  if [[ "$legacy_has_ov" == "true" ]]; then
    backup_file "$legacy_cf"
    _ov_kimicode strip-hooks-config "$legacy_cf"
    _ov_kimicode unbind-legacy-toml "$legacy_cf"
    log_ok "Legacy OpenViking sections removed from config.toml"
  fi
  # Remove deployed hook dispatcher + py helpers (OV-owned only)
  _ov_kimicode unbind-hooks "$OV_SHARED_DIR" "$OV_RUNTIME_DIR"
  ov_log_info "重启 KimiCode 以使更改完全生效" "Restart KimiCode for changes to take full effect"
}

agent_kimicode_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-kimicode-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  local mcp_file="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  local live_has_ov=false
  local mcp_live=false hooks_live=false
  local url=""
  if [[ -f "$mcp_file" ]] && _ov_kimicode check-live-mcp "$mcp_file" 2>/dev/null; then
    live_has_ov=true; mcp_live=true
    url=$(_ov_kimicode get-live-mcp-url "$mcp_file" 2>/dev/null)
  fi
  # ISSUE-012: status detection must match unbind (legacy config.toml + sandbox
  # openviking-config.json states were visible to unbind but missed by status)
  local legacy_cf="$OV_RUNTIME_DIR/kimicode/data/config.toml"
  if [[ -f "$legacy_cf" ]] && grep -q "mcp_servers.openviking" "$legacy_cf" 2>/dev/null; then
    live_has_ov=true
  fi
  if [[ -f "$legacy_cf" ]] && _ov_kimicode check-hooks "$legacy_cf" 2>/dev/null; then
    live_has_ov=true; hooks_live=true
  fi
  if [[ -f "$OV_SHARED_DIR/ov-kimi-hook/ov-kimi-hook.sh" ]] || [[ -f "$OV_SHARED_DIR/ov-kimi-hook.sh" ]]; then
    live_has_ov=true; hooks_live=true
  fi
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/openviking-config.json" ]]; then
    live_has_ov=true
    [[ -z "$url" ]] && url="http://127.0.0.1:1933/mcp"
  fi
  local d_live d_tpl d_liveonly d_none
  if [[ "$mcp_live" == "true" && "$hooks_live" == "true" ]]; then
    d_live="hooks + MCP: MCP ${url:-http://127.0.0.1:1933/mcp} via mcp.json + session hooks (template + live)"
    d_liveonly="hooks + MCP: live only (lost on restart)"
  elif [[ "$mcp_live" == "true" ]]; then
    d_live="MCP via mcp.json (template + live); hooks not live"
    d_liveonly="MCP via mcp.json (live only, lost on restart)"
  elif [[ "$hooks_live" == "true" ]]; then
    d_live="session hooks via config.toml [[hooks]] (template + live); MCP not live"
    d_liveonly="session hooks (live only, lost on restart)"
  else
    d_live="no live OpenViking channel detected"
    d_liveonly="no live OpenViking channel"
  fi
  d_tpl="hooks + MCP configured (template only, restart to activate)"
  d_none="No OpenViking integration (no MCP, no session hooks)"
  agent::report_status "${AGENT_META[name]}" "$tpl_has_ov" "$live_has_ov" \
    "$d_live" "$d_tpl" "$d_liveonly" "$d_none"
}