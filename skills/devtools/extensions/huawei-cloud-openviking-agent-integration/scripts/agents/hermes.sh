#!/bin/bash
# =============================================================================
# agents/hermes.sh — Hermes agent subclass
# =============================================================================
# Mechanism: Built-in memory provider
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_hermes_integrate, agent_hermes_unbind, agent_hermes_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_hermes_register() {
  agent::set_meta name "hermes"
  agent::set_meta display_name "Hermes"
  agent::set_meta sandbox_pattern "hermes-*"
  agent::set_meta template_path "/root/template/hermes/start.sh"
  agent::set_meta mechanism "Built-in memory provider"
  registry_add "hermes"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_hermes_integrate() {
  local tpl="/root/template/hermes/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "Hermes template start.sh not found: $tpl"; return 1; }

  # If already has a non-MCP OpenViking memory provider injection, skip.
  # (Backward compatibility: the old approach injected mcp_servers + MCP SDK;
  #  has_ov_injection still detects that marker. A re-run will clean it via the
  #  legacy cleanup below.)
  if has_ov_injection "$tpl"; then
    # Distinguish modern provider-only injection from legacy MCP injection
    if grep -q "memory:" "$tpl" 2>/dev/null && ! grep -q "mcp_servers:" "$tpl" 2>/dev/null; then
      log_ok "Hermes already has OpenViking memory provider (template-level)"
      return 0
    fi
    log_warn "Hermes template has LEGACY OpenViking MCP injection — will replace with official memory provider"
  fi

  require_confirmation "Integrate OpenViking (official memory provider)" "hermes" \
    "Add memory.provider=openviking (+ endpoint) to template start.sh, remove legacy MCP SDK + mcp_servers" || return 1
  if dry_run_msg "Would add OpenViking memory provider to $tpl and live sandbox"; then return 0; fi

  backup_file "$tpl"

  # Step 1: Remove legacy MCP SDK install block + legacy MCP injection block if present
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

  # Step 2: Inject official memory provider block (idempotent)
  if ! grep -q "provider: openviking" "$tpl" 2>/dev/null; then
    sed -i '/^sleep infinity$/i \
# ── OpenViking memory provider ('"$OV_MARKER"') ──\
# Official mechanism: Hermes has a built-in OpenViking memory provider (no plugin,\
# no MCP SDK, no mcp_servers). Config is recreated on every start, so this block\
# re-injects memory.provider after the model config is written.\
if ! grep -q "provider: openviking" "$HOME/.hermes/config.yaml" 2>/dev/null; then\
  cat >> "$HOME/.hermes/config.yaml" << '"'"'OVYAML'"'"'\
\
# OpenViking native memory provider (auto-recall + auto-store, HTTP REST)\
memory:\
  provider: openviking\
  openviking:\
    endpoint: '"$OV_ENDPOINT"'\
OVYAML\
fi\
# Write OPENVIKING_ENDPOINT env var (required by plugin is_available() check)\
if ! grep -q "OPENVIKING_ENDPOINT" "$HOME/.hermes/.env" 2>/dev/null; then\
  echo "OPENVIKING_ENDPOINT='"$OV_ENDPOINT"'" >> "$HOME/.hermes/.env"\
fi' "$tpl"
    log_ok "Hermes template updated with OpenViking memory provider at $OV_ENDPOINT"
  fi

  # Immediate effect: inject provider config into live sandbox (no MCP SDK install)
  local sandbox; sandbox=$(find_sandbox "hermes")
  if [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]]; then
    local cf="${sandbox}/.hermes/config.yaml"
    if ! grep -q "provider: openviking" "$cf" 2>/dev/null; then
      # Remove legacy MCP block first if present
      python3 - "$cf" <<'OVCLEAN'
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

# OpenViking native memory provider (auto-recall + auto-store, HTTP REST)
memory:
  provider: openviking
  openviking:
    endpoint: ${OV_ENDPOINT}
YAML
      # Also write OPENVIKING_ENDPOINT to .env (required by plugin is_available())
      if ! grep -q "OPENVIKING_ENDPOINT" "${sandbox}/.hermes/.env" 2>/dev/null; then
        echo "OPENVIKING_ENDPOINT=${OV_ENDPOINT}" >> "${sandbox}/.hermes/.env"
      fi
      log_ok "OpenViking memory provider also injected into live sandbox (immediate effect)"
    else
      log_ok "Live sandbox already has OpenViking memory provider"
    fi
  else
    log_info "No live Hermes sandbox found; config will take effect on next start"
  fi
  log_info "Restart Hermes for full effect"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_hermes_unbind() {
  local tpl="/root/template/hermes/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  # Also check for MCP SDK install block (legacy) and official memory provider block (current)
  grep -q "MCP SDK install.*$OV_MARKER\|MCP SDK install.*$OV_MARKER_LEGACY" "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "OpenViking memory provider" "$tpl" 2>/dev/null && tpl_has_ov=true

  local sandbox; sandbox=$(find_sandbox "hermes")
  local sandbox_has_ov=false
  [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]] && grep -q "openviking" "${sandbox}/.hermes/config.yaml" 2>/dev/null && sandbox_has_ov=true
  # Also detect runtime artifacts: OpenViking skill, snapshot, usage, MEMORY.md
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
    # Remove official memory provider block
    sed -i '/# ── OpenViking memory provider ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking memory provider ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    # Remove legacy OpenViking MCP injection block (backward compatibility)
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    # Remove legacy MCP SDK install block (separate injection by same skill)
    # Remove standalone OPENVIKING_ENDPOINT env var block (injected alongside memory provider; marker-to-fi sed above stops at first fi, leaving this block behind — bug fix)
    sed -i '/# Write OPENVIKING_ENDPOINT env var (required by plugin is_available() check)/,/fi$/d' "$tpl"
    sed -i '/# ── MCP SDK install ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── MCP SDK install ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    log_ok "OpenViking memory provider (and legacy blocks) removed from template start.sh"
  fi

  if [[ "$sandbox_has_ov" == "true" ]]; then
    local cf="${sandbox}/.hermes/config.yaml"
    backup_file "$cf" 2>/dev/null || true
    python3 << PYEOF
import re
with open("$cf") as f:
    content = f.read()
# Remove the OpenViking MCP server block
content = re.sub(r'\n# OpenViking MCP server\nmcp_servers:\n  openviking:\n    url: [^\n]+\n', '\n', content)
# Also remove any standalone mcp_servers.openviking if format differs
content = re.sub(r'\nmcp_servers:\n  openviking:\n    url: [^\n]+\n', '\n', content)
# Clean up empty mcp_servers
content = re.sub(r'\nmcp_servers:\s*\n(?=\n[^ ])', '\n', content)
# Remove OpenViking native memory provider block
content = re.sub(r'\n# OpenViking native memory provider[^\n]*\nmemory:\n  provider: openviking\n  openviking:\n    endpoint: [^\n]+\n', '\n', content)
# Also remove memory block without comment
content = re.sub(r'\nmemory:\n  provider: openviking\n  openviking:\n    endpoint: [^\n]+\n', '\n', content)
# Clean up empty memory section
content = re.sub(r'\nmemory:\s*\n(?=\n[^ ])', '\n', content)
content = content.rstrip() + '\n'
with open("$cf", 'w') as f:
    f.write(content)
PYEOF
    # Remove OPENVIKING_* env vars from .env
    if [[ -f "${sandbox}/.hermes/.env" ]] && grep -q "OPENVIKING_" "${sandbox}/.hermes/.env" 2>/dev/null; then
      sed -i '/^OPENVIKING_/d' "${sandbox}/.hermes/.env"
    fi
    log_ok "OpenViking MCP + memory provider removed from live sandbox"
  fi

  # Step 3: Clean up Hermes runtime artifacts (skill, snapshot, usage, memory)
  # These are created by Hermes at runtime when OpenViking memory provider is active.
  # The unbind must remove them too, otherwise Hermes still sees OpenViking integration.
  if [[ -n "$sandbox" ]]; then
    # 3a: Remove openviking-memory-queries skill directory
    local ov_skill_dir="${sandbox}/.hermes/skills/integrations/openviking-memory-queries"
    if [[ -d "$ov_skill_dir" ]]; then
      rm -rf "$ov_skill_dir"
      log_ok "Removed openviking-memory-queries skill from sandbox"
      # Remove integrations dir if now empty
      rmdir "${sandbox}/.hermes/skills/integrations" 2>/dev/null
    fi

    # 3b: Clean .skills_prompt_snapshot.json
    local snapshot="${sandbox}/.hermes/.skills_prompt_snapshot.json"
    if [[ -f "$snapshot" ]] && grep -q "openviking" "$snapshot" 2>/dev/null; then
      python3 - "$snapshot" << 'OVSNAP'
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

    # 3c: Clean skills/.usage.json
    local usage="${sandbox}/.hermes/skills/.usage.json"
    if [[ -f "$usage" ]] && grep -q "openviking" "$usage" 2>/dev/null; then
      python3 - "$usage" << 'OVUSAGE'
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

    # 3d: Clean MEMORY.md of OpenViking references
    local memfile="${sandbox}/.hermes/memories/MEMORY.md"
    if [[ -f "$memfile" ]] && grep -qi "openviking" "$memfile" 2>/dev/null; then
      python3 - "$memfile" << 'OVMEM'
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

  log_info "Restart Hermes for changes to take full effect"
}


# ── Status ───────────────────────────────────────────────────────────────────
agent_hermes_status() {
  local tpl="/root/template/hermes/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true

  local sandbox; sandbox=$(find_sandbox "hermes")
  [[ -z "$sandbox" ]] && { echo "hermes|unknown|sandbox not found"; return; }
  local cf="${sandbox}/.hermes/config.yaml"
  local sandbox_has_ov=false
  [[ -f "$cf" ]] && grep -q "provider: openviking" "$cf" 2>/dev/null && sandbox_has_ov=true

  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    echo "hermes|integrated|Built-in memory provider (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    echo "hermes|integrated|Built-in memory provider configured (template only, restart to activate)"
  elif [[ "$sandbox_has_ov" == "true" ]]; then
    echo "hermes|partial|Built-in memory provider (live only, lost on restart)"
  else
    echo "hermes|not_integrated|No OpenViking memory provider"
  fi
}

