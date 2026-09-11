#!/bin/bash
# agents/prime_agent.sh — Prime Agent agent subclass (pi-coding-agent-extension)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_prime_agent_register() {
  agent::set_meta name "prime_agent"
  agent::set_meta display_name "Prime Agent"
  agent::set_meta sandbox_pattern "prime-agent-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/prime-agent/start.sh"
  agent::set_meta mechanism "pi-coding-agent-extension"
  registry_add "prime_agent"
}

agent_prime_agent_integrate() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "prime-agent")
  [[ -z "$sandbox" ]] && { log_error "Prime Agent sandbox not found"; return 1; }

  local pa_runtime="$OV_RUNTIME_DIR/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"
  local persist_src="${pa_runtime}/openviking-extension"

  ov_plugin_provision "pi-coding-agent-extension" "$persist_src" || return 1
  touch "$persist_src"  # Refresh TTL timestamp (cache valid for 24h)
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
      "$OV_PY" - "$tpl" "$OV_SHARED_DIR" <<'PAPYTPL'
import sys
tpl_path = sys.argv[1]
shared_dir = sys.argv[2]
with open(tpl_path, encoding='utf-8') as f:
    tpl = f.read()
block = """
# ── OpenViking memory extension (added by huawei-cloud-openviking-agent-integration skill) ──
# @openviking/pi-coding-agent-extension: TypeScript extension with auto-recall, auto-capture,
# context takeover, and 7 LLM tools. No build step, no MCP server — direct HTTP API.
export OPENVIKING_URL="${OPENVIKING_URL:-http://127.0.0.1:1933}"
OV_EXT_SRC="$PA_RUNTIME/openviking-extension"
OV_EXT_DST="$PRIME_AGENT_CODING_AGENT_DIR/extensions/openviking"
if [ -d "$OV_EXT_SRC" ]; then
  if [ ! -f "$OV_EXT_DST/index.ts" ] || ! diff -q "$OV_EXT_SRC/index.ts" "$OV_EXT_DST/index.ts" >/dev/null 2>&1; then
    mkdir -p "$OV_EXT_DST"
    cp -a "$OV_EXT_SRC"/* "$OV_EXT_DST/"
    echo "OpenViking extension deployed to $OV_EXT_DST"
  else
    echo "OpenViking extension already up-to-date"
  fi
else
  echo "WARN: extension source not found at $OV_EXT_SRC, skipping"
fi
"""
import os
if "ov-prime-agent-init.sh" in tpl or "OpenViking memory extension" in tpl:
    sys.exit(0)
init_path = f"{shared_dir}/ov-prime-agent-init.sh"
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for Prime Agent ──\n")
    f.write("# Sourced by the Prime Agent template start.sh (single source line).\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block.lstrip("\n"))
os.chmod(init_path, 0o755)
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-prime-agent-init.sh\n# ── End OpenViking integration ──\n\n"
for anchor in ("# ── agentwork:", "# ── acpws:"):
    idx = tpl.find(anchor)
    if idx != -1:
        break
else:
    print("ERROR: no known anchor found in template start.sh (tried agentwork, acpws)", file=sys.stderr)
    sys.exit(1)
tpl = tpl[:idx] + source_block + tpl[idx:]
with open(tpl_path, 'w', encoding='utf-8') as f:
    f.write(tpl)
PAPYTPL
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
  local sandbox; sandbox=$(find_sandbox "prime-agent")
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
    rm -rf "$ext_dst"
    log_ok "Extension removed from live extensions directory: $ext_dst"
  fi
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
  # Preserve persistent source (cache for fast re-integration)
  if [[ -d "$persist_src" ]]; then
    log_ok "Persistent extension source preserved at $persist_src (cache for fast re-integration)"
  fi
  if [[ "$tpl_has" == "true" && -f "$tpl" ]]; then
    backup_file "$tpl"
    "$OV_PY" - "$tpl" "$OV_SHARED_DIR" <<'PAUNBINDPY'
import re, sys
path = sys.argv[1]
shared_dir = sys.argv[2]
with open(path, encoding='utf-8') as f:
    content = f.read()
removed = False
# Pattern 1: Source-line block (current integrate format)
source_block_pattern = rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\nsource {shared_dir}/ov-prime-agent-init\.sh\n# ── End OpenViking integration ──\n\n'
new_content = re.sub(source_block_pattern, '', content)
if new_content != content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Source-line block removed from template start.sh")
    content = new_content
    removed = True
# Pattern 2: Inline memory-extension block (older integrate format)
block_header = r'# ── OpenViking memory extension \(added by huawei-cloud-openviking-agent-integration skill\) ──'
for anchor in ("# ── agentwork:", "# ── acpws:"):
    pattern = block_header + r'.*?\n\n(?=' + re.escape(anchor) + r')'
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Inline block removed from template start.sh (anchor: {anchor})")
        content = new_content
        removed = True
        break
if not removed:
    pattern = block_header + r'.*?\n\n(?=# ── )'
    new_content = re.sub(pattern, '', content, flags=re.DOTALL)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Inline block removed from template start.sh (fallback: next comment)")
        removed = True
if not removed:
    print("No OpenViking block found in template (already clean)")
PAUNBINDPY
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
  local sandbox; sandbox=$(find_sandbox "prime-agent")
  local pa_runtime="$OV_RUNTIME_DIR/prime-agent"
  local ext_dst="${pa_runtime}/agent-data/extensions/openviking"

  local tpl_has=false
  grep -q "OpenViking memory extension\|ov-prime-agent-init.sh" "$tpl" 2>/dev/null && tpl_has=true
  local live_has=false
  [[ -f "${ext_dst}/index.ts" ]] && live_has=true

  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    ov_status "prime-agent" "integrated" "pi-coding-agent-extension (TypeScript extension, native hooks: auto-recall + auto-capture + context takeover, template + live)"
  elif [[ "$tpl_has" == "true" ]]; then
    ov_status "prime-agent" "integrated" "pi-coding-agent-extension configured (template only, restart to activate)"
  elif [[ "$live_has" == "true" ]]; then
    ov_status "prime-agent" "partial" "pi-coding-agent-extension (live only, lost on restart)"
  else
    ov_status "prime-agent" "not_integrated" "No OpenViking extension"
  fi
}
