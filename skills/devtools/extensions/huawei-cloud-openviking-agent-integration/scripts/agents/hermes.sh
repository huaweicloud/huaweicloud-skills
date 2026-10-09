#!/bin/bash
# agents/hermes.sh — Hermes agent subclass (Built-in memory provider)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_hermes_register() {
  agent::set_meta name "hermes"
  agent::set_meta display_name "Hermes"
  agent::set_meta sandbox_pattern "hermes-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/hermes/start.sh"
  agent::set_meta mechanism "Built-in memory provider"
  registry_add "hermes"
}
_ov_hermes() { "$OV_PY" "$OV_PY_DIR/agents/ov_hermes.py" "$@"; }

agent_hermes_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "Hermes template start.sh not found: $tpl"; return 1; }

  # Detect existing injection (modern standalone script or legacy MCP block)
  # ISSUE-011: idempotency requires template AND live sandbox state
  local tpl_has=false live_has=false
  if grep -q "ov-hermes-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-hermes-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has=true
    if ! grep -q "mcp_servers:" "$tpl" 2>/dev/null && ! grep -q "MCP SDK install" "$tpl" 2>/dev/null; then
      : # clean modern injection
    else
      log_warn "Hermes template has modern + legacy injection — will clean up legacy"
    fi
  elif has_ov_injection "$tpl"; then
    log_warn "Hermes template has LEGACY OpenViking MCP injection — will replace"
  fi
  local _sbx_once; _sbx_once=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$_sbx_once" && -f "$_sbx_once/.hermes/config.yaml" ]] && \
     grep -q "provider: openviking" "$_sbx_once/.hermes/config.yaml" 2>/dev/null; then
    live_has=true
  fi
  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    log_ok "Hermes already integrated with OpenViking memory provider (template + live)"
    return 0
  fi
  require_confirmation "Integrate OpenViking (official memory provider)" "hermes" \
    "Add memory.provider=openviking (+ endpoint) to template start.sh, remove legacy MCP SDK + mcp_servers" || return 1
  if dry_run_msg "Would add OpenViking memory provider to $tpl and live sandbox"; then return 0; fi
  backup_file "$tpl"
  # Remove legacy MCP SDK install + injection blocks if present
  if grep -q "MCP SDK install" "$tpl" 2>/dev/null; then
    sed -i '/# ── MCP SDK install ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── MCP SDK install ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    log_ok "Removed legacy MCP SDK install block from template"
  fi
  if grep -q "mcp_servers:" "$tpl" 2>/dev/null; then
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    log_ok "Removed legacy MCP injection block from template"
  fi
  # Inject official memory provider block (idempotent)
  if ! grep -q "ov-hermes-init.sh" "$tpl" 2>/dev/null; then
    _ov_hermes integrate "$tpl" "$OV_ENDPOINT" "$OV_SHARED_DIR"
    log_ok "Hermes template updated with OpenViking memory provider at $OV_ENDPOINT"
  fi
  # Inject provider config into live sandbox (immediate effect)
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  if [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]]; then
    local cf="${sandbox}/.hermes/config.yaml"
    if ! grep -q "provider: openviking" "$cf" 2>/dev/null; then
      _ov_hermes clean-legacy-mcp "$cf"
      cat >> "$cf" << YAML
memory:
  provider: openviking
  openviking:
    endpoint: ${OV_ENDPOINT}
YAML
      if ! grep -q "OPENVIKING_ENDPOINT" "${sandbox}/.hermes/.env" 2>/dev/null; then
        echo "OPENVIKING_ENDPOINT=${OV_ENDPOINT}" >> "${sandbox}/.hermes/.env"
      fi
      log_ok "OpenViking memory provider injected into live sandbox"
    else
      log_ok "Live sandbox already has OpenViking memory provider"
    fi
  else
    log_warn "No live Hermes sandbox found — template-only integration (no live verification)"
  fi
  ov_log_info "重启 Hermes 以完全生效" "Restart Hermes for full effect"
}

agent_hermes_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "MCP SDK install.*$OV_MARKER\|MCP SDK install.*$OV_MARKER_LEGACY" "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "OpenViking memory provider" "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-hermes-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local sandbox_has_ov=false
  [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]] && grep -q "openviking" "${sandbox}/.hermes/config.yaml" 2>/dev/null && sandbox_has_ov=true
  # Detect runtime artifacts
  if [[ -n "$sandbox" && "$sandbox_has_ov" == "false" ]]; then
    [[ -d "${sandbox}/.hermes/skills/integrations/openviking-memory-queries" ]] && sandbox_has_ov=true
    [[ -f "${sandbox}/.hermes/.skills_prompt_snapshot.json" ]] && grep -q "openviking" "${sandbox}/.hermes/.skills_prompt_snapshot.json" 2>/dev/null && sandbox_has_ov=true
    [[ -f "${sandbox}/.hermes/memories/MEMORY.md" ]] && grep -qi "openviking" "${sandbox}/.hermes/memories/MEMORY.md" 2>/dev/null && sandbox_has_ov=true
  fi
  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "Hermes not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking memory provider" "hermes" "Remove OpenViking memory provider (and legacy MCP/MCP SDK if present) from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking memory provider from template and sandbox"; then return 0; fi
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    # Remove modern source-line injection
    _ov_hermes unbind-template "$tpl" "$OV_SHARED_DIR"
    # Remove legacy blocks
    sed -i '/# ── OpenViking memory provider ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking memory provider ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    sed -i '/# Write OPENVIKING_ENDPOINT env var (required by plugin is_available() check)/,/fi$/d' "$tpl"
    sed -i '/# ── MCP SDK install ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── MCP SDK install ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    rm -f "$OV_SHARED_DIR/ov-hermes-init.sh"
    log_ok "OpenViking memory provider (and legacy blocks) removed from template start.sh"
  fi
  if [[ "$sandbox_has_ov" == "true" ]]; then
    local cf="${sandbox}/.hermes/config.yaml"
    backup_file "$cf" 2>/dev/null || true
    _ov_hermes unbind-live "$cf"
    if [[ -f "${sandbox}/.hermes/.env" ]] && grep -q "OPENVIKING_" "${sandbox}/.hermes/.env" 2>/dev/null; then
      sed -i '/^OPENVIKING_/d' "${sandbox}/.hermes/.env"
    fi
    log_ok "OpenViking MCP + memory provider removed from live sandbox"
  fi
  # Clean up Hermes runtime artifacts
  if [[ -n "$sandbox" ]]; then
    local ov_skill_dir="${sandbox}/.hermes/skills/integrations/openviking-memory-queries"
    if [[ -d "$ov_skill_dir" ]]; then
      ov_safe_rm "$ov_skill_dir" 2>/dev/null || true
      log_ok "Removed openviking-memory-queries skill from sandbox"
      rmdir "${sandbox}/.hermes/skills/integrations" 2>/dev/null
    fi
    local snapshot="${sandbox}/.hermes/.skills_prompt_snapshot.json"
    if [[ -f "$snapshot" ]] && grep -q "openviking" "$snapshot" 2>/dev/null; then
      _ov_hermes clean-snapshot "$snapshot"
      log_ok "Cleaned OpenViking entries from .skills_prompt_snapshot.json"
    fi
    local usage="${sandbox}/.hermes/skills/.usage.json"
    if [[ -f "$usage" ]] && grep -q "openviking" "$usage" 2>/dev/null; then
      _ov_hermes clean-usage "$usage"
      log_ok "Cleaned OpenViking entries from skills/.usage.json"
    fi
    local memfile="${sandbox}/.hermes/memories/MEMORY.md"
    if [[ -f "$memfile" ]] && grep -qi "openviking" "$memfile" 2>/dev/null; then
      _ov_hermes clean-memory "$memfile"
      log_ok "Removed OpenViking references from MEMORY.md"
    fi
  fi
  ov_log_info "重启 Hermes 以使更改完全生效" "Restart Hermes for changes to take full effect"
}

agent_hermes_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-hermes-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { ov_status "hermes" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.hermes/config.yaml"
  local sandbox_has_ov=false
  [[ -f "$cf" ]] && grep -q "provider: openviking" "$cf" 2>/dev/null && sandbox_has_ov=true
  # ISSUE-012: status detection must match unbind (runtime artifacts counted there)
  if [[ "$sandbox_has_ov" == "false" ]]; then
    [[ -d "${sandbox}/.hermes/skills/integrations/openviking-memory-queries" ]] && sandbox_has_ov=true
    [[ -f "${sandbox}/.hermes/.skills_prompt_snapshot.json" ]] && grep -q "openviking" "${sandbox}/.hermes/.skills_prompt_snapshot.json" 2>/dev/null && sandbox_has_ov=true
    [[ -f "${sandbox}/.hermes/memories/MEMORY.md" ]] && grep -qi "openviking" "${sandbox}/.hermes/memories/MEMORY.md" 2>/dev/null && sandbox_has_ov=true
  fi
  agent::report_status "${AGENT_META[name]}" "$tpl_has_ov" "$sandbox_has_ov" \
    "Built-in memory provider (template + live)" \
    "Built-in memory provider configured (template only, restart to activate)" \
    "Built-in memory provider (live only, lost on restart)" \
    "No OpenViking memory provider"
}
