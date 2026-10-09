#!/bin/bash
# agents/jiuwenswarm.sh — WorkSwarm agent subclass (dual-channel: provider + MCP)
agent_workswarm_register() {
  agent::set_meta name "workswarm"
  agent::set_meta display_name "WorkSwarm"
  agent::set_meta sandbox_pattern "jiuwenswarm-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/jiuwenswarm/start.sh"
  agent::set_meta config_path "$OV_HOME/.jiuwenswarm/config.json"
  agent::set_meta mechanism "Dual-channel: provider + MCP"
  registry_add "workswarm"
}

_ov_workswarm() { "$OV_PY" "$OV_PY_DIR/agents/ov_workswarm.py" "$@"; }

_jw_agents_md() {
  cat <<'JWAGENTS'
# Agent Instructions
## OpenViking Long-Term Memory
Dual-channel: (1) **Native memory provider** (`memory.engine: external`, `is_proactive: true`): auto-recalls/stores context. (2) **MCP server** (13 tools): `search`, `recall`, `find`, `read`, `remember`, `add_resource`, `grep`, `glob`, `forget`, `health`, `list`, `list_watches`, `cancel_watch`.
### Auto-Recall (conversation start)
Native engine auto-prefetches. For deeper: `search` (mode="context"), `recall` (type-quota), `find` (min_score=0).
### Proactive Search (during tasks)
1. `search` (mode="context") — past knowledge, solutions, decisions. 2. `recall` — structured type-quota. 3. `find` — fast ranked list. 4. `read` — expand viking:// URIs. 5. `grep`/`glob` — exact text/filename.
### Auto-Capture (after meaningful exchanges)
1. `remember` — user shares preferences/facts/decisions or asks to remember. 2. `add_resource` — import files/URLs/repos. 3. Never echo credentials.
### Repo Context
`add_resource` repo path to index; `search` for prior work.
JWAGENTS
}

_jw_mutate_config() {
  local action="$1" cfg="$2" mcp_url="${3:-}"
  _ov_workswarm mutate-config "$action" "$cfg" "$mcp_url"
}

_jw_patch_iface_apply() {
  local file="$1"
  _ov_workswarm patch-iface-apply "$file"
}

_jw_patch_iface_revert() {
  local file="$1"
  _ov_workswarm patch-iface-revert "$file"
}

_jw_patch_prov_apply() {
  local file="$1"
  _ov_workswarm patch-prov-apply "$file"
}

_jw_patch_prov_revert() {
  local file="$1"
  _ov_workswarm patch-prov-revert "$file"
}

_jw_patch_session_apply() {
  local file="$1"
  _ov_workswarm patch-session-apply "$file"
}

_jw_patch_session_revert() {
  local file="$1"
  _ov_workswarm patch-session-revert "$file"
}

_jw_patch_commit_apply() {
  local file="$1"
  _ov_workswarm patch-commit-apply "$file"
}

_jw_patch_commit_revert() {
  local file="$1"
  _ov_workswarm patch-commit-revert "$file"
}

agent_workswarm_integrate() {
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { log_error "WorkSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }
  local tpl="${AGENT_META[template_path]}"
  local already=false
  if grep -q "MEMORY_ENGINE:-both\|MEMORY_ENGINE:-external\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null; then
    already=true
  elif [[ -f "$tpl" ]] && grep -q "MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null; then
    already=true
  fi
  if [[ "$already" == "true" ]]; then
    if [[ -f "$tpl" ]] && grep -q "OpenViking native memory provider injection\|ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null; then
      if grep -q "OPENVIKING_ACCOUNT:-root" "$cf" 2>/dev/null; then
        # ISSUE-008: dry-run must never write — gate the account fixup too
        if [[ "${DRY_RUN:-false}" == "true" ]]; then
          log_info "[DRY-RUN] would normalize OPENVIKING_ACCOUNT to default in $cf"
        else
          sed -i "s/OPENVIKING_ACCOUNT:-root/OPENVIKING_ACCOUNT:-default/" "$cf"
        fi
      fi
      return 0
    fi
  fi
  require_confirmation "Integrate OpenViking" "workswarm" "Add OpenViking native memory provider + MCP server to sandbox config + template start.sh" || return 1
  if dry_run_msg "Would add OpenViking native memory provider + MCP server to $cf and $tpl"; then return 0; fi
  backup_file "$cf"
  _jw_mutate_config apply "$cf" "$OV_MCP_URL"
  if [[ -f "$tpl" ]] && ! grep -q "OpenViking native memory provider injection\|ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null; then
    backup_file "$tpl"
    local _agents_tmp; _agents_tmp=$(mktemp)
    _jw_agents_md > "$_agents_tmp"
    _ov_workswarm inject-template "$tpl" "$OV_ENDPOINT" "$OV_MCP_URL" "$_agents_tmp" "$OV_SHARED_DIR" "$OV_TEMPLATE_DIR" "$OV_RUNTIME_DIR"
    rm -f "$_agents_tmp"
  fi
  mkdir -p "${sandbox}/workspace"
  _jw_agents_md > "${sandbox}/workspace/AGENTS.md"
  local jw_iface; jw_iface=$(ov_find_runtime_file "*/jiuwenswarm*/agent_adapter/interface_code.py")
  ov_patch_apply "$jw_iface" "code-mode ExternalMemoryRail" \
    "Code-mode ExternalMemoryRail patch" _jw_patch_iface_apply || true
  local jw_prov; jw_prov=$(ov_find_runtime_file "*/jiuwenswarm*/memory/external/openviking_memory_provider.py")
  ov_patch_apply "$jw_prov" "ov-fix-limit" \
    "Provider top_k→limit patch" _jw_patch_prov_apply || true
  ov_patch_apply "$jw_prov" "ov-fix-session" \
    "Provider jw- session ID patch" _jw_patch_session_apply || true
  ov_patch_apply "$jw_prov" "ov-fix-commit" \
    "Provider commit-after-sync_turn patch" _jw_patch_commit_apply || true
}

agent_workswarm_unbind() {
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local tpl="${AGENT_META[template_path]}"
  local cf=""
  local ov_conf=""
  if [[ -n "$sandbox" ]]; then
    cf="${sandbox}/.jiuwenswarm/config/config.yaml"
    ov_conf="${sandbox}/.config/opencode/openviking-config.json"
  fi
  local has_sandbox=0 has_template=0
  if [[ -n "$cf" && -f "$cf" ]]; then
    grep -q "name: openviking\|openviking:\|viking_search\|MEMORY_ENGINE:-both\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null && has_sandbox=1
  fi
  [[ -n "$ov_conf" && -f "$ov_conf" ]] && has_sandbox=1
  [[ -f "$tpl" ]] && grep -q "OpenViking\|openviking-config\|Enhanced 4-section AGENTS\|MEMORY_EXTERNAL_PROVIDER=openviking\|ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null && has_template=1
  if [[ "$has_sandbox" -eq 0 && "$has_template" -eq 0 ]]; then
    return 0
  fi
  require_confirmation "UNBIND OpenViking" "workswarm" "Remove OpenViking native memory provider (+ legacy MCP if present) from sandbox and template" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking from ${cf:-<no-sandbox>} and $tpl"; then return 0; fi
  # Template start.sh (persistent) — clean first, does not depend on sandbox
  if [[ "$has_template" -eq 1 ]]; then
    backup_file "$tpl"
    _ov_workswarm unbind-template "$tpl" "$OV_SHARED_DIR"
    rm -f "$OV_SHARED_DIR/ov-jiuwenswarm-init.sh"
  fi
  # Sandbox config — only if sandbox exists
  if [[ "$has_sandbox" -eq 1 ]]; then
    if [[ -n "$cf" && -f "$cf" ]]; then
      backup_file "$cf"
      _jw_mutate_config revert "$cf"
    fi
    if [[ -n "$ov_conf" && -f "$ov_conf" ]]; then
      rm -f "$ov_conf"
    fi
  else
    log_warn "sandbox not found — template cleaned, skipping sandbox-layer cleanup"
  fi
  # ISSUE-010: unbind must clean what integrate wrote — workspace/AGENTS.md is
  # written by integrate.sh and was left behind after unbind
  if [[ -n "$sandbox" && -f "${sandbox}/workspace/AGENTS.md" ]]; then
    local _agents_tmp2; _agents_tmp2=$(mktemp)
    _jw_agents_md > "$_agents_tmp2"
    if cmp -s "${sandbox}/workspace/AGENTS.md" "$_agents_tmp2"; then
      rm -f "${sandbox}/workspace/AGENTS.md"
      log_ok "AGENTS.md removed from sandbox workspace"
    else
      log_warn "AGENTS.md in sandbox differs from OpenViking template (user-modified) — left untouched"
    fi
    rm -f "$_agents_tmp2"
  fi
  local jw_iface; jw_iface=$(ov_find_runtime_file "*/jiuwenswarm*/agent_adapter/interface_code.py")
  ov_patch_revert "$jw_iface" "code-mode ExternalMemoryRail" \
    "Code-mode ExternalMemoryRail patch" _jw_patch_iface_revert || true
  local jw_prov; jw_prov=$(ov_find_runtime_file "*/jiuwenswarm*/memory/external/openviking_memory_provider.py")
  ov_patch_revert "$jw_prov" "ov-fix-limit" \
    "Provider top_k→limit patch" _jw_patch_prov_revert || true
  ov_patch_revert "$jw_prov" "ov-fix-session" \
    "Provider jw- session ID patch" _jw_patch_session_revert || true
  ov_patch_revert "$jw_prov" "ov-fix-commit" \
    "Provider commit-after-sync_turn patch" _jw_patch_commit_revert || true
  if [[ -n "$sandbox" ]]; then
    for proc_dir in "${sandbox}/process_dir" "${sandbox}/.process_dir"; do
      if [[ -f "${proc_dir}/start.sh" ]]; then
        cp "$tpl" "${proc_dir}/start.sh"
        break
      fi
    done
  fi
}

agent_workswarm_status() {
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { ov_status "workswarm" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { ov_status "workswarm" "unknown" "config not found"; return; }
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  local live_native=false live_mcp=false detail=""
  local cfg_engine=false cfg_provider=false
  grep -q "engine:.*both\|engine:.*external" "$cf" 2>/dev/null && cfg_engine=true
  { grep -q "provider:.*openviking\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null || \
    { [[ -f "$tpl" ]] && grep -q "MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null; }; } && cfg_provider=true
  [[ "$cfg_engine" == "true" && "$cfg_provider" == "true" ]] && live_native=true
  if grep -q "name: openviking" "$cf" 2>/dev/null; then
    live_mcp=true
  fi
  if [[ "$live_native" == "true" && "$live_mcp" == "true" ]]; then
    detail="native memory provider + MCP"
  elif [[ "$live_native" == "true" ]]; then
    detail="native memory provider only (MCP missing — re-integrate to add MCP)"
  elif [[ "$live_mcp" == "true" ]]; then
    detail="MCP only (native provider not configured)"
  fi
  local jw_iface jw_prov
  jw_iface=$(ov_find_runtime_file "*/jiuwenswarm*/agent_adapter/interface_code.py")
  jw_prov=$(ov_find_runtime_file "*/jiuwenswarm*/memory/external/openviking_memory_provider.py")
  if [[ -n "$detail" && ( -n "$jw_iface" || -n "$jw_prov" ) ]]; then
    local iface_mark prov_mark session_mark commit_mark
    iface_mark=$(ov_patch_mark "$jw_iface" "code-mode ExternalMemoryRail")
    prov_mark=$(ov_patch_mark "$jw_prov" "ov-fix-limit")
    session_mark=$(ov_patch_mark "$jw_prov" "ov-fix-session")
    commit_mark=$(ov_patch_mark "$jw_prov" "ov-fix-commit")
    detail+=" | patches: iface${iface_mark} prov${prov_mark} sess${session_mark} commit${commit_mark}"
  fi
  local live_has=false
  [[ "$live_native" == "true" || "$live_mcp" == "true" ]] && live_has=true
  # ISSUE-012: status detection must match unbind — unbind counts the sandbox
  # openviking-config.json artifact, status did not
  if [[ "$live_has" == "false" && -f "${sandbox}/.config/opencode/openviking-config.json" ]]; then
    live_has=true
    [[ -n "$detail" ]] && detail+=" | config artifact"
  fi
  agent::report_status "${AGENT_META[name]}" "$tpl_has_ov" "$live_has" \
    "$detail (template + live)" \
    "template only, restart to activate" \
    "$detail (live only, lost on restart)" \
    "No OpenViking integration found"
}
