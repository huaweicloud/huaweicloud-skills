#!/bin/bash
# agents/prime_agent.sh — Prime Agent agent subclass (pi-coding-agent-extension)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_prime_agent_register() {
  agent::set_meta name "prime_agent"
  agent::set_meta display_name "Prime Agent"
  agent::set_meta sandbox_pattern "prime-agent-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/prime-agent/start.sh"
  agent::set_meta config_path "$OV_HOME/.prime-agent/config.json"
  agent::set_meta mechanism "pi-coding-agent-extension"
  registry_add "prime_agent"
}
_ov_prime_agent() { "$OV_PY" "$OV_PY_DIR/agents/ov_prime_agent.py" "$@"; }

agent_prime_agent_integrate() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { log_error "Prime Agent sandbox not found"; return 1; }

  local pa_runtime="$OV_RUNTIME_DIR/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"
  local persist_src="${pa_runtime}/openviking-extension"

  ov_plugin_provision "pi-coding-agent-extension" "$persist_src" || return 1
  if [[ "${DRY_RUN:-false}" != "true" ]]; then
    touch "$persist_src"  # Refresh TTL timestamp (cache valid for 24h)
  fi

  # Post-provision fix: upstream refactor (commit aa3ee2f) moved shared/ files out of
  # the extension to agent-plugins/servers/shared/ and examples/claude-code-memory-plugin/scripts/shared/.
  # The pack-time step that copies them back is not run by ov_plugin_provision, so we
  # download them here to prevent ERR_MODULE_NOT_FOUND at runtime.
  ov_sync_shared_files "$persist_src"
  local tpl_has_ov=false
  grep -q "OpenViking memory extension" "$tpl" 2>/dev/null && tpl_has_ov=true
  local live_has_ov=false
  [[ -f "${ext_dst}/index.ts" ]] && live_has_ov=true

  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    log_ok "Prime Agent already integrated with OpenViking (pi-coding-agent-extension, template + live)"
    return 0
  fi
  require_confirmation "Integrate OpenViking" "prime-agent" "Install @openviking/pi-coding-agent-extension (TypeScript extension with native hooks: auto-recall, auto-capture, context takeover) + template start.sh" || return 1
  if dry_run_msg "Would install pi-coding-agent-extension to $ext_dst + persist at $persist_src + template $tpl"; then return 0; fi
  log_ok "Extension source installed on demand at persistent location: $persist_src"
  # Live sandbox (immediate effect)
  mkdir -p "$ext_dst"
  cp -a "$persist_src"/* "$ext_dst/"
  log_ok "Extension installed to live extensions directory: $ext_dst"
  # Template start.sh (persistent)
  if [[ "$tpl_has_ov" == "false" ]]; then
    if [[ -f "$tpl" ]]; then
      backup_file "$tpl"
      _ov_prime_agent integrate "$tpl" "$OV_SHARED_DIR"
      if [[ $? -ne 0 ]]; then
        log_error "Failed to inject OpenViking block into template start.sh (anchor not found)"
        return 1
      fi
      log_ok "OpenViking integration block injected into template start.sh"
      tpl_has_ov=true
    else
      log_warn "Template $tpl missing — skipping template injection (live only, lost on restart)"
    fi
  fi
  # Sync template to sandbox so a restart preserves integration
  if [[ "$tpl_has_ov" == "true" ]]; then
    local proc_dir
    for proc_dir in "${sandbox}/process_dir" "${sandbox}/.process_dir"; do
      if [[ -f "${proc_dir}/start.sh" ]]; then
        cp "$tpl" "${proc_dir}/start.sh"
        log_ok "Template start.sh synced to sandbox ${proc_dir}"
        break
      fi
    done
  fi
  ov_log_info "重启 Prime Agent 以激活扩展（自动召回 + 自动捕获 + 7 工具）" "Restart Prime Agent for extension to activate (auto-recall + auto-capture + 7 tools)"
}

agent_prime_agent_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local pa_runtime="$OV_RUNTIME_DIR/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"
  local persist_src="${pa_runtime}/openviking-extension"

  local tpl_has=false
  grep -q "OpenViking memory extension\|ov-prime-agent-init.sh" "$tpl" 2>/dev/null && tpl_has=true
  local live_has=false
  [[ -f "${ext_dst}/index.ts" ]] && live_has=true
  [[ -n "$sandbox" && -d "${sandbox}/agent-data/extensions/openviking" ]] && live_has=true

  if [[ "$tpl_has" == "false" && "$live_has" == "false" ]]; then
    log_ok "Prime Agent has no OpenViking integration to unbind"
    return 0
  fi
  require_confirmation "UNBIND OpenViking" "prime-agent" "Remove pi-coding-agent-extension from extensions dir + persistent source + template start.sh injection" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking extension from $ext_dst + $persist_src + template $tpl"; then return 0; fi
  if [[ -d "$ext_dst" ]]; then
    ov_safe_rm "$ext_dst" 2>/dev/null || true
    log_ok "Extension removed from live extensions directory: $ext_dst"
  fi
  if [[ -n "$sandbox" ]]; then
    local sbx_ext="${sandbox}/agent-data/extensions/openviking"
    if [[ -d "$sbx_ext" ]]; then
      ov_safe_rm "$sbx_ext" 2>/dev/null || true
      log_ok "Extension removed from sandbox extensions directory: $sbx_ext"
    fi
    local sbx_state="${sandbox}/.openviking"
    if [[ -d "$sbx_state" ]]; then
      ov_safe_rm "$sbx_state" 2>/dev/null || true
      log_ok "OpenViking state directory removed from sandbox: $sbx_state"
    fi
  fi
  # Preserve persistent source (cache for fast re-integration)
  if [[ -d "$persist_src" ]]; then
    log_ok "Persistent extension source preserved at $persist_src (cache for fast re-integration)"
  fi
  if [[ "$tpl_has" == "true" && -f "$tpl" ]]; then
    backup_file "$tpl"
    _ov_prime_agent unbind-template "$tpl" "$OV_SHARED_DIR"
    if ! grep -q "ov-prime-agent-init.sh\|OpenViking memory extension\|OpenViking integration" "$tpl" 2>/dev/null; then
      log_ok "OpenViking block removed from template start.sh"
    else
      log_error "Failed to remove OpenViking block from template start.sh (block still present)"
      return 1
    fi
    rm -f "$OV_SHARED_DIR/ov-prime-agent-init.sh" && log_ok "Removed standalone ov-prime-agent-init.sh"
  fi
  # Sync template to sandbox
  if [[ -n "$sandbox" ]]; then
    for proc_dir in "${sandbox}/process_dir" "${sandbox}/.process_dir"; do
      if [[ -f "${proc_dir}/start.sh" ]]; then
        cp "$tpl" "${proc_dir}/start.sh"
        log_ok "Template synced to sandbox ${proc_dir}"
        break
      fi
    done
  fi
  ov_log_info "重启 Prime Agent 以使更改生效" "Restart Prime Agent for changes to take effect"
}

agent_prime_agent_status() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local pa_runtime="$OV_RUNTIME_DIR/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"

  local tpl_has=false
  grep -q "OpenViking memory extension\|ov-prime-agent-init.sh" "$tpl" 2>/dev/null && tpl_has=true
  local live_has=false
  [[ -f "${ext_dst}/index.ts" ]] && live_has=true
  # ISSUE-012: status detection must match unbind (sandbox extension dir counted there)
  if [[ "$live_has" == "false" && -n "$sandbox" && -d "${sandbox}/agent-data/extensions/openviking" ]]; then
    live_has=true
  fi

  agent::report_status "${AGENT_META[name]}" "$tpl_has" "$live_has" \
    "pi-coding-agent-extension (TypeScript extension, native hooks: auto-recall + auto-capture + context takeover, template + live)" \
    "pi-coding-agent-extension configured (template only, restart to activate)" \
    "pi-coding-agent-extension (live only, lost on restart)" \
    "No OpenViking extension"
}
