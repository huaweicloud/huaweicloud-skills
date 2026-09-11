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

agent_hermes_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "Hermes template start.sh not found: $tpl"; return 1; }

  # Detect existing injection (modern standalone script or legacy MCP block)
  if grep -q "ov-hermes-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-hermes-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    if ! grep -q "mcp_servers:" "$tpl" 2>/dev/null && ! grep -q "MCP SDK install" "$tpl" 2>/dev/null; then
      log_ok "Hermes already has OpenViking memory provider (template-level)"
      return 0
    fi
    log_warn "Hermes template has modern + legacy injection — will clean up legacy"
  elif has_ov_injection "$tpl"; then
    log_warn "Hermes template has LEGACY OpenViking MCP injection — will replace"
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
    "$OV_PY" - "$tpl" "$OV_ENDPOINT" "$OV_SHARED_DIR" <<'PYTPL'
import sys, os, re
tpl_path = sys.argv[1]
endpoint = sys.argv[2]
shared_dir = sys.argv[3]
with open(tpl_path) as f:
    tpl = f.read()
block = """
# ── OpenViking memory provider (added by huawei-cloud-openviking-agent-integration skill) ──
# Re-injects memory.provider after model config is written on each start.
if ! grep -q "provider: openviking" "$HOME/.hermes/config.yaml" 2>/dev/null; then
  cat >> "$HOME/.hermes/config.yaml" << 'OVYAML'
memory:
  provider: openviking
  openviking:
    endpoint: __OV_ENDPOINT__
OVYAML
fi
if ! grep -q "OPENVIKING_ENDPOINT" "$HOME/.hermes/.env" 2>/dev/null; then
  echo "OPENVIKING_ENDPOINT='__OV_ENDPOINT__'" >> "$HOME/.hermes/.env"
fi
"""
block = block.replace("__OV_ENDPOINT__", endpoint)
init_path = f"{shared_dir}/ov-hermes-init.sh"
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for Hermes ──\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block.lstrip("\n"))
os.chmod(init_path, 0o755)
source_block = (
    "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\n"
    f"source {shared_dir}/ov-hermes-init.sh\n"
    "# ── End OpenViking integration ──\n\n"
)
m = re.search(r'(?m)^sleep infinity$', tpl)
if not m:
    print("ERROR: insertion marker 'sleep infinity' not found in template", file=sys.stderr)
    sys.exit(1)
tpl = tpl[:m.start()] + source_block + tpl[m.start():]
with open(tpl_path, "w") as f:
    f.write(tpl)
PYTPL
    log_ok "Hermes template updated with OpenViking memory provider at $OV_ENDPOINT"
  fi
  # Inject provider config into live sandbox (immediate effect)
  local sandbox; sandbox=$(find_sandbox "hermes")
  if [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]]; then
    local cf="${sandbox}/.hermes/config.yaml"
    if ! grep -q "provider: openviking" "$cf" 2>/dev/null; then
      "$OV_PY" - "$cf" <<'OVCLEAN'
import re, sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()
content = re.sub(r'\n# OpenViking MCP server\nmcp_servers:\n  openviking:\n    url: [^\n]+\n', '\n', content)
content = re.sub(r'\nmcp_servers:\n  openviking:\n    url: [^\n]+\n', '\n', content)
content = re.sub(r'\nmcp_servers:\s*\n(?=\n[^ ])', '\n', content)
with open(path, 'w') as f:
    f.write(content)
OVCLEAN
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
    log_info "No live Hermes sandbox found; config will take effect on next start"
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
  local sandbox; sandbox=$(find_sandbox "hermes")
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
    "$OV_PY" - "$tpl" "$OV_SHARED_DIR" <<'PYRM'
import sys, re
path = sys.argv[1]
shared_dir = sys.argv[2]
with open(path) as f:
    content = f.read()
content = re.sub(
    r'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\n'
    rf'source {shared_dir}/ov-hermes-init\.sh\n'
    r'# ── End OpenViking integration ──\n\n?',
    '', content)
with open(path, 'w') as f:
    f.write(content)
PYRM
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
    "$OV_PY" << PYEOF
import re
with open("$cf") as f:
    content = f.read()
content = re.sub(r'\n# OpenViking MCP server\nmcp_servers:\n  openviking:\n    url: [^\n]+\n', '\n', content)
content = re.sub(r'\nmcp_servers:\n  openviking:\n    url: [^\n]+\n', '\n', content)
content = re.sub(r'\nmcp_servers:\s*\n(?=\n[^ ])', '\n', content)
content = re.sub(r'\n# OpenViking native memory provider[^\n]*\nmemory:\n  provider: openviking\n  openviking:\n    endpoint: [^\n]+\n', '\n', content)
content = re.sub(r'\nmemory:\n  provider: openviking\n  openviking:\n    endpoint: [^\n]+\n', '\n', content)
content = re.sub(r'\nmemory:\s*\n(?=\n[^ ])', '\n', content)
content = content.rstrip() + '\n'
with open("$cf", 'w') as f:
    f.write(content)
PYEOF
    if [[ -f "${sandbox}/.hermes/.env" ]] && grep -q "OPENVIKING_" "${sandbox}/.hermes/.env" 2>/dev/null; then
      sed -i '/^OPENVIKING_/d' "${sandbox}/.hermes/.env"
    fi
    log_ok "OpenViking MCP + memory provider removed from live sandbox"
  fi
  # Clean up Hermes runtime artifacts
  if [[ -n "$sandbox" ]]; then
    local ov_skill_dir="${sandbox}/.hermes/skills/integrations/openviking-memory-queries"
    if [[ -d "$ov_skill_dir" ]]; then
      rm -rf "$ov_skill_dir"
      log_ok "Removed openviking-memory-queries skill from sandbox"
      rmdir "${sandbox}/.hermes/skills/integrations" 2>/dev/null
    fi
    local snapshot="${sandbox}/.hermes/.skills_prompt_snapshot.json"
    if [[ -f "$snapshot" ]] && grep -q "openviking" "$snapshot" 2>/dev/null; then
      "$OV_PY" - "$snapshot" << 'OVSNAP'
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data['manifest'] = {k: v for k, v in data.get('manifest', {}).items() if 'openviking' not in k.lower()}
data['skills'] = [s for s in data.get('skills', []) if 'openviking' not in s.get('skill_name', '').lower()]
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
OVSNAP
      log_ok "Cleaned OpenViking entries from .skills_prompt_snapshot.json"
    fi
    local usage="${sandbox}/.hermes/skills/.usage.json"
    if [[ -f "$usage" ]] && grep -q "openviking" "$usage" 2>/dev/null; then
      "$OV_PY" - "$usage" << 'OVUSAGE'
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
data = {k: v for k, v in data.items() if 'openviking' not in k.lower()}
with open(path, 'w') as f:
    json.dump(data, f, indent=2)
OVUSAGE
      log_ok "Cleaned OpenViking entries from skills/.usage.json"
    fi
    local memfile="${sandbox}/.hermes/memories/MEMORY.md"
    if [[ -f "$memfile" ]] && grep -qi "openviking" "$memfile" 2>/dev/null; then
      "$OV_PY" - "$memfile" << 'OVMEM'
import sys
path = sys.argv[1]
with open(path) as f:
    lines = f.readlines()
cleaned = [l for l in lines if 'openviking' not in l.lower() and 'viking' not in l.lower() and '1933' not in l]
with open(path, 'w') as f:
    f.writelines(cleaned)
OVMEM
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
  local sandbox; sandbox=$(find_sandbox "hermes")
  [[ -z "$sandbox" ]] && { ov_status "hermes" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.hermes/config.yaml"
  local sandbox_has_ov=false
  [[ -f "$cf" ]] && grep -q "provider: openviking" "$cf" 2>/dev/null && sandbox_has_ov=true
  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    ov_status "hermes" "integrated" "Built-in memory provider (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    ov_status "hermes" "integrated" "Built-in memory provider configured (template only, restart to activate)"
  elif [[ "$sandbox_has_ov" == "true" ]]; then
    ov_status "hermes" "partial" "Built-in memory provider (live only, lost on restart)"
  else
    ov_status "hermes" "not_integrated" "No OpenViking memory provider"
  fi
}
