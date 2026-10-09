#!/bin/bash
# agents/deepseek_harness.sh — DeepSeek Harness agent subclass (dsh-memory-plugin bundle)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_deepseek_harness_register() {
  agent::set_meta name "deepseek_harness"
  agent::set_meta display_name "DeepSeek Harness"
  agent::set_meta sandbox_pattern "deepseek-harness-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/deepseek-harness/start.sh"
  agent::set_meta config_path "$OV_HOME/.deepseek-harness/config.json"
  agent::set_meta mechanism "dsh-memory-plugin bundle"
  registry_add "deepseek_harness"
}

_ov_deepseek() { "$OV_PY" "$OV_PY_DIR/agents/ov_deepseek_harness.py" "$@"; }

dsh_tpl_block() {
  _ov_deepseek tpl_block "$1"
}

dsh_sync_peer_deps() {
  local plugin_dir="$1"
  local plugin_da="${plugin_dir}/node_modules/@deepseek-ai"
  local dsh_nm="$OV_RUNTIME_DIR/deepseek-harness/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
  if [[ ! -d "$dsh_nm" ]]; then
    log_warn "dsh main install not found at $dsh_nm — skipping peer dep sync"
    return 0
  fi
  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    local _c=0 _pd
    for _pd in "$dsh_nm"/*; do
      [[ -d "$_pd" ]] || continue
      _c=$((_c + 1))
    done
    log_info "[DRY-RUN] would sync $_c @deepseek-ai/* peer deps into plugin node_modules (host-matched, incl. dsh-llm/dsh-tools)"
    return 0
  fi
  if [[ ! -d "$plugin_da" ]]; then
    mkdir -p "$plugin_da"
  fi
  local count=0
  for pkg_dir in "$dsh_nm"/*; do
    [[ -d "$pkg_dir" ]] || continue
    local pkg; pkg=$(basename "$pkg_dir")
    local dest="${plugin_da}/${pkg}"
    # Host-matched: copy EVERY @deepseek-ai/* package (incl. dsh-llm/dsh-tools) so plugin
    # deps always equal the installed dsh runtime version — never a pinned version.
    ov_safe_rm "$dest" 2>/dev/null || true
    cp -r "$pkg_dir" "$dest"
    count=$((count + 1))
  done
  # Update the boot-time sync marker to the current host fingerprint so a subsequent
  # sandbox start matches the cache and skips re-copying (no stale boolean marker).
  local _fp
  _fp=$("$OV_PY" -c "import json,glob,os,hashlib
base='$dsh_nm'
h=hashlib.sha1()
for pkg in sorted(glob.glob(os.path.join(base,'*','package.json'))):
    try: h.update(json.load(open(pkg)).get('version','').encode())
    except Exception: pass
print(h.hexdigest())" 2>/dev/null)
  if [[ -n "$_fp" ]]; then
    printf '%s' "$_fp" > "$plugin_da/.openviking-peers-synced"
  fi
  log_ok "Synced ${count} @deepseek-ai/* peer deps into plugin node_modules (host-matched, ESM-safe real copies)"
}

agent_deepseek_harness_integrate() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"
  local plugin_src="$OV_RUNTIME_DIR/deepseek-harness/plugins/@openviking/dsh-memory-plugin"
  # force_provision=true: existing cache still checks upstream commit (zero download
  # on same commit, keeps existing on network failure) — never stuck on an old snapshot.
  ov_deploy_plugin_tiered "dsh-memory-plugin" "$plugin_src" "" "dsh-memory-plugin" "" true || return 1
  if [[ "${DRY_RUN:-false}" != "true" ]]; then
    touch "$plugin_src"  # Refresh TTL timestamp (cache valid for 24h)
  fi
  dsh_sync_peer_deps "$plugin_src"
  # Post-provision fix: upstream refactor (commit aa3ee2f) moved shared/ files out of
  # examples/dsh-memory-plugin/ to examples/claude-code-memory-plugin/scripts/shared/.
  # The pack-time step that copies them back is not run by ov_plugin_provision, so we
  # download them here to prevent ERR_MODULE_NOT_FOUND at runtime.
  ov_sync_shared_files "$plugin_src"
  local tpl_has_ov=false
  if grep -q "ov-deepseek-harness-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has_ov=true
  fi
  local live_has_ov=false
  if grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/web/package.json" 2>/dev/null \
     || grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/dsh-tui/package.json" 2>/dev/null; then
    live_has_ov=true
  fi
  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    log_ok "DeepSeek Harness already integrated with OpenViking (dsh-memory-plugin bundle, template + live)"
    return 0
  fi
  require_confirmation "Integrate OpenViking" "deepseek-harness" "Install @openviking/dsh-memory-plugin bundle into dsh profiles (web/dsh-tui) + template start.sh" || return 1
  if dry_run_msg "Would install dsh-memory-plugin into $dsh_home/profiles/{web,dsh-tui} (node_modules + package.json bundles) + template $tpl"; then return 0; fi

  # Runtime seed profiles (deploy-resilient: bundles + real dir, no link: dep)
  local dsh_runtime_home="$OV_RUNTIME_DIR/deepseek-harness/home"
  if [[ -d "$dsh_runtime_home/profiles" ]]; then
    _ov_deepseek seed_profiles "$dsh_runtime_home" "$plugin_src"
    log_ok "Runtime seed profiles pre-seeded (deploy-resilient)"
  fi
  # Live sandbox (immediate effect)
  _ov_deepseek ov_body "$dsh_home" "$plugin_src" "$OV_ENDPOINT"
  log_ok "dsh-memory-plugin bundle installed into live dsh profiles (web/dsh-tui)"
  live_has_ov=true
  # Template start.sh (persistent)
  if [[ "$tpl_has_ov" == "false" ]]; then
    if [[ -f "$tpl" ]]; then
      backup_file "$tpl"
      local init_sh="$OV_SHARED_DIR/ov-deepseek-harness-init.sh"
      dsh_tpl_block "$OV_ENDPOINT" | _ov_deepseek inject_template "$tpl" "$init_sh" "$OV_TEMPLATE_DIR" "$OV_SHARED_DIR"
      log_ok "OpenViking integration written to standalone script + source line injected into template start.sh"
      tpl_has_ov=true
    else
      log_warn "Template $tpl missing — skipping template injection (live only, lost on restart)"
    fi
  fi
  # Sync template to sandbox so a restart preserves integration
  if [[ "$tpl_has_ov" == "true" && -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Template start.sh synced to sandbox .process_dir"
  fi
  ov_log_info "重启 DeepSeek Harness（web + dsh-tui）以完全生效" "Restart DeepSeek Harness (web + dsh-tui) for full effect"
}

agent_deepseek_harness_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  local dsh_home=""
  [[ -n "$sandbox" ]] && dsh_home="${sandbox}/.dsh"

  local tpl_has_ov=false live_has_ov=false
  if grep -q "ov-deepseek-harness-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has_ov=true
  fi
  if [[ -n "$dsh_home" ]]; then
    for p in web dsh-tui; do
      grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/$p/package.json" 2>/dev/null && live_has_ov=true
      [[ -d "${dsh_home}/profiles/$p/node_modules/@openviking/dsh-memory-plugin" ]] && live_has_ov=true
    done
  fi
  [[ "$tpl_has_ov" == "false" && "$live_has_ov" == "false" ]] && { log_ok "DeepSeek Harness not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking" "deepseek-harness" "Remove @openviking/dsh-memory-plugin bundle from dsh profiles (web/dsh-tui) + template start.sh" "$RED" || return 1
  if dry_run_msg "Would remove dsh-memory-plugin from live profiles (node_modules + package.json) + template start.sh"; then return 0; fi
  # Template start.sh (persistent) — clean first, does not depend on sandbox
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    _ov_deepseek unbind_template "$tpl"
    log_ok "OpenViking integration block removed from template start.sh"
    rm -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" && log_ok "Removed standalone ov-deepseek-harness-init.sh"
  fi
  # Live sandbox profiles — only if sandbox exists
  if [[ "$live_has_ov" == "true" ]]; then
    if [[ -z "$dsh_home" ]]; then
      log_warn "sandbox not found — template cleaned, skipping sandbox-layer cleanup"
    fi
    for p in web dsh-tui; do
      local cf="${dsh_home}/profiles/$p/package.json"
      [[ -f "$cf" ]] || continue
      backup_file "$cf" 2>/dev/null || true
      ov_safe_rm "${dsh_home}/profiles/$p/node_modules/@openviking" 2>/dev/null || true
      _ov_deepseek remove_bundle "$cf"
    done
    log_ok "dsh-memory-plugin bundle removed from live dsh profiles (web/dsh-tui)"
  fi
  # Runtime .dsh/profiles (deploy-resilient layer — must clean or redeploy inherits stale bundles)
  local _rt_profile_dirs=( "$OV_RUNTIME_DIR/deepseek-harness/.dsh/profiles" "$OV_RUNTIME_DIR/deepseek-harness/home/profiles" )
  local rt_cleaned=false
  for _rt_profiles in "${_rt_profile_dirs[@]}"; do
    [[ -d "$_rt_profiles" ]] || continue
    for p in web dsh-tui; do
      local rt_cf="$_rt_profiles/$p/package.json"
      [[ -f "$rt_cf" ]] || continue
      if [[ -d "$_rt_profiles/$p/node_modules/@openviking" ]]; then
        ov_safe_rm "$_rt_profiles/$p/node_modules/@openviking" 2>/dev/null || true
        rt_cleaned=true
      fi
      if grep -q '"@openviking/dsh-memory-plugin"' "$rt_cf" 2>/dev/null; then
        _ov_deepseek remove_bundle "$rt_cf"
        rt_cleaned=true
      fi
    done
  done
  if [[ "$rt_cleaned" == "true" ]]; then
    log_ok "Runtime .dsh/profiles cleaned (deploy-resilient layer removed)"
  fi
  # Plugin source cache
  local _plugin_cache="$OV_RUNTIME_DIR/deepseek-harness/plugins/@openviking"
  if [[ -d "$_plugin_cache" ]]; then
    ov_safe_rm "$_plugin_cache" 2>/dev/null || true
    log_ok "Plugin source cache removed ($_plugin_cache)"
  fi
  # Sync template to sandbox so a restart stays clean
  if [[ -n "$sandbox" && -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Cleaned template start.sh synced to sandbox .process_dir"
  fi
  ov_log_info "重启 DeepSeek Harness（web + dsh-tui）以使更改完全生效" "Restart DeepSeek Harness (web + dsh-tui) for changes to take full effect"
}

agent_deepseek_harness_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  if grep -q "ov-deepseek-harness-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has_ov=true
  fi
  local sandbox; sandbox=$(find_sandbox "${AGENT_META[sandbox_pattern]%-*}")
  [[ -z "$sandbox" ]] && { ov_status "deepseek-harness" "unknown" "sandbox not found"; return; }
  local live_has_ov=false
  local live_scope=""
  local p
  for p in web dsh-tui; do
    if grep -q '"@openviking/dsh-memory-plugin"' "${sandbox}/.dsh/profiles/$p/package.json" 2>/dev/null \
       || [[ -d "${sandbox}/.dsh/profiles/$p/node_modules/@openviking/dsh-memory-plugin" ]]; then
      live_has_ov=true
      live_scope="${live_scope:+$live_scope,}$p"
    fi
  done
  agent::report_status "${AGENT_META[name]}" "$tpl_has_ov" "$live_has_ov" \
    "dsh-memory-plugin bundle (template + live profiles: ${live_scope:-none})" \
    "dsh-memory-plugin bundle configured (template only, restart to activate)" \
    "dsh-memory-plugin bundle (live profiles: ${live_scope:-none}, lost on restart)" \
    "No OpenViking memory bundle"
}
