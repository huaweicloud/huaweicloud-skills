#!/bin/bash
# =============================================================================
# agents/prime_agent.sh — Prime Agent agent subclass
# =============================================================================
# Mechanism: pi-coding-agent-extension
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_prime_agent_integrate, agent_prime_agent_unbind, agent_prime_agent_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_prime_agent_register() {
  agent::set_meta name "prime_agent"
  agent::set_meta display_name "Prime Agent"
  agent::set_meta sandbox_pattern "prime-agent-*"
  agent::set_meta template_path "/root/template/prime-agent/start.sh"
  agent::set_meta mechanism "pi-coding-agent-extension"
  registry_add "prime_agent"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_prime_agent_integrate() {
  local tpl="/root/template/prime-agent/start.sh"
  local sandbox; sandbox=$(find_sandbox "prime-agent")
  [[ -z "$sandbox" ]] && { log_error "Prime Agent sandbox not found"; return 1; }

  local pa_runtime="/root/runtime/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"
  local persist_src="${pa_runtime}/openviking-extension"

  # Install the official extension source on demand into the persistent runtime location.
  ov_plugin_provision "pi-coding-agent-extension" "$persist_src" || return 1
  touch "$persist_src"  # Refresh TTL timestamp (cache valid for 24h)

  # Check existing integration state
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

  # ── 1. Extension source already installed on demand at persist_src above ──
  log_ok "Extension source installed on demand at persistent location: $persist_src"

  # ── 2. Live sandbox (immediate effect) ──
  mkdir -p "$ext_dst"
  cp -a "$persist_src"/* "$ext_dst/"
  log_ok "Extension installed to live extensions directory: $ext_dst"

  # ── 3. Template start.sh (persistent) ──
  if [[ "$tpl_has_ov" == "false" ]]; then
    if [[ -f "$tpl" ]]; then
      backup_file "$tpl"
      python3 - "$tpl" <<'PAPYTPL'
import sys
tpl_path = sys.argv[1]
with open(tpl_path, encoding='utf-8') as f:
    tpl = f.read()

block = """
# ── OpenViking memory extension (added by huawei-cloud-openviking-agent-integration skill) ──
# Official @openviking/pi-coding-agent-extension: TypeScript extension loaded by
# prime-agent's jiti transpiler. Provides auto-recall (before_agent_start + context
# hooks), auto-capture (turn_end hook), context takeover (session_before_compact),
# and 7 LLM tools (viking_search/read/browse/remember/forget/add_resource/archive_expand).
# No build step, no npm dependencies, no MCP server — direct HTTP API to OpenViking.
# Extension source is installed at $PA_RUNTIME/openviking-extension/ and deployed to
# $PRIME_AGENT_CODING_AGENT_DIR/extensions/openviking/ on each boot (idempotent).
export OPENVIKING_URL="${OPENVIKING_URL:-http://127.0.0.1:1933}"
OV_EXT_SRC="$PA_RUNTIME/openviking-extension"
OV_EXT_DST="$PRIME_AGENT_CODING_AGENT_DIR/extensions/openviking"
if [ -d "$OV_EXT_SRC" ]; then
  if [ ! -f "$OV_EXT_DST/index.ts" ] || ! diff -q "$OV_EXT_SRC/index.ts" "$OV_EXT_DST/index.ts" >/dev/null 2>&1; then
    mkdir -p "$OV_EXT_DST"
    cp -a "$OV_EXT_SRC"/* "$OV_EXT_DST/"
    echo "OpenViking memory extension deployed to $OV_EXT_DST"
  else
    echo "OpenViking memory extension already up-to-date"
  fi
else
  echo "WARN: OpenViking extension source not found at $OV_EXT_SRC, skipping"
fi

"""

anchor = "# ── acpws:"
idx = tpl.find(anchor)
if idx == -1:
    print("ERROR: acpws anchor not found in template start.sh", file=sys.stderr)
    sys.exit(1)
if "OpenViking memory extension" in tpl:
    sys.exit(0)
tpl = tpl[:idx] + block.lstrip("\n") + tpl[idx:]
with open(tpl_path, 'w', encoding='utf-8') as f:
    f.write(tpl)
PAPYTPL
      log_ok "OpenViking integration block injected into template start.sh"
      tpl_has_ov=true
    else
      log_warn "Template $tpl missing — skipping template injection (live only, lost on restart)"
    fi
  fi

  # ── 4. Sync template to sandbox so a restart preserves integration ──
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

  log_info "Restart Prime Agent for extension to activate (auto-recall + auto-capture + 7 tools)"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_prime_agent_unbind() {
  local tpl="/root/template/prime-agent/start.sh"
  local sandbox; sandbox=$(find_sandbox "prime-agent")
  local pa_runtime="/root/runtime/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"
  local persist_src="${pa_runtime}/openviking-extension"

  local tpl_has=false
  grep -q "OpenViking memory extension" "$tpl" 2>/dev/null && tpl_has=true
  local live_has=false
  [[ -f "${ext_dst}/index.ts" ]] && live_has=true
  [[ -n "$sandbox" && -d "${sandbox}/agent-data/extensions/openviking" ]] && live_has=true

  if [[ "$tpl_has" == "false" && "$live_has" == "false" ]]; then
    log_ok "Prime Agent has no OpenViking integration to unbind"
    return 0
  fi

  require_confirmation "UNBIND OpenViking" "prime-agent" "Remove pi-coding-agent-extension from extensions dir + persistent source + template start.sh injection" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking extension from $ext_dst + $persist_src + template $tpl"; then return 0; fi

  # ── 1. Remove from live extensions directory ──
  if [[ -d "$ext_dst" ]]; then
    rm -rf "$ext_dst"
    log_ok "Extension removed from live extensions directory: $ext_dst"
  fi

  # ── 1b. Remove from sandbox extensions directory + state ──
  if [[ -n "$sandbox" ]]; then
    local sbx_ext="${sandbox}/agent-data/extensions/openviking"
    if [[ -d "$sbx_ext" ]]; then
      rm -rf "$sbx_ext"
      log_ok "Extension removed from sandbox extensions directory: $sbx_ext"
    fi
    local sbx_state="${sandbox}/.openviking"
    if [[ -d "$sbx_state" ]]; then
      rm -rf "$sbx_state"
      log_ok "OpenViking state directory removed from sandbox: $sbx_state"
    fi
  fi

  # ── 2. Preserve persistent source (cache for fast re-integration) ──
  # The persistent copy at $persist_src is a downloaded cache of the plugin source.
  # Keeping it allows ov_plugin_provision to skip re-downloading on re-integration
  # (SHA match → instant). This matches deepseek-harness's unbind behavior.
  if [[ -d "$persist_src" ]]; then
    log_ok "Persistent extension source preserved at $persist_src (cache for fast re-integration)"
  fi

  # ── 3. Remove from template start.sh ──
  if [[ "$tpl_has" == "true" && -f "$tpl" ]]; then
    backup_file "$tpl"
    python3 - "$tpl" <<'PAUNBINDPY'
import re, sys
path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    content = f.read()

# Remove the OpenViking memory extension block (from comment header through
# closing fi + trailing newline). The block is injected right before the
# "# ── acpws:" anchor, so it is bounded above by that anchor — match the full
# contiguous region, not the first inner fi (which would orphan else...fi).
anchor = "# ── acpws:"
pattern = r'# ── OpenViking memory extension \(added by huawei-cloud-openviking-agent-integration skill\) ──.*?\n\n(?=' + re.escape(anchor) + r')'
new_content = re.sub(pattern, '', content, flags=re.DOTALL)
if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("OpenViking block removed from template start.sh")
else:
    print("No OpenViking block found in template (already clean)")
PAUNBINDPY
    log_ok "OpenViking block removed from template start.sh"
  fi

  # ── 4. Sync template to sandbox ──
  if [[ -n "$sandbox" ]]; then
    for proc_dir in "${sandbox}/process_dir" "${sandbox}/.process_dir"; do
      if [[ -f "${proc_dir}/start.sh" ]]; then
        cp "$tpl" "${proc_dir}/start.sh"
        log_ok "Template synced to sandbox ${proc_dir}"
        break
      fi
    done
  fi

  log_info "Restart Prime Agent for changes to take effect"
}


# ── Status ───────────────────────────────────────────────────────────────────
agent_prime_agent_status() {
  local tpl="/root/template/prime-agent/start.sh"
  local sandbox; sandbox=$(find_sandbox "prime-agent")
  local pa_runtime="/root/runtime/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"

  local tpl_has=false
  grep -q "OpenViking memory extension" "$tpl" 2>/dev/null && tpl_has=true
  local live_has=false
  [[ -f "${ext_dst}/index.ts" ]] && live_has=true

  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    echo "prime-agent|integrated|pi-coding-agent-extension (TypeScript extension, native hooks: auto-recall + auto-capture + context takeover, template + live)"
  elif [[ "$tpl_has" == "true" ]]; then
    echo "prime-agent|integrated|pi-coding-agent-extension configured (template only, restart to activate)"
  elif [[ "$live_has" == "true" ]]; then
    echo "prime-agent|partial|pi-coding-agent-extension (live only, lost on restart)"
  else
    echo "prime-agent|not_integrated|No OpenViking extension"
  fi
}

