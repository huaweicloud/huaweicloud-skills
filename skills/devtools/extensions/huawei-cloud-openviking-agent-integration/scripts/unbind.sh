#!/bin/bash
# =============================================================================
# OpenViking Agent Unbinding Script
# Usage:
#   ./unbind.sh --agent <name> [--dry-run] [--yes]
#   ./unbind.sh --all [--dry-run] [--yes]
# Agents: codearts, opencode, openclaw, hermes, jiuwenswarm, kimicode, deepseek-harness
# =============================================================================
set -euo pipefail
source "$(dirname "$0")/common.sh"

DRY_RUN=false
AUTO_YES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --all) ALL_AGENTS=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --yes|-y) AUTO_YES=true; shift ;;
    --help|-h) echo "Usage: $0 --agent <name>|--all [--dry-run] [--yes]"; echo "Agents: codearts, opencode, openclaw, hermes, jiuwenswarm, kimicode, deepseek-harness"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ── CodeArts ──────────────────────────────────────────────────────────────────
unbind_codearts() {
  local tpl="/root/template/codearts/start.sh"
  local sandbox; sandbox=$(find_sandbox "codearts")
  local tpl_has_ov=false
  local sandbox_has_ov=false

  # Check template for OpenViking injection
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true

  # Check sandbox config
  local cf=""
  if [[ -n "$sandbox" ]]; then
    cf="${sandbox}/.codeartsdoer/codearts_cli.json"
    [[ -f "$cf" ]] && check_json_mcp "$cf" && sandbox_has_ov=true
    # Also check for OpenViking prompt in build.prompt
    if [[ -f "$cf" ]]; then
      python3 -c "import json; cfg=json.load(open('$cf')); exit(0 if 'OpenViking' in cfg.get('agent',{}).get('build',{}).get('prompt','') else 1)" 2>/dev/null && sandbox_has_ov=true
    fi
  fi

  # Check for openviking-config.json in sandbox
  local ov_conf=""
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/openviking-config.json" ]]; then
    sandbox_has_ov=true
    ov_conf="${sandbox}/.config/opencode/openviking-config.json"
  fi

  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "CodeArts not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking MCP" "codearts" "Remove OpenViking from template start.sh + sandbox config + openviking-config.json" "$RED" || return 1
  if dry_run_msg "Would remove mcp.openviking + prompt from $cf and template start.sh"; then return 0; fi

  # ── 1. Remove injection block from template start.sh ──
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    python3 - "$tpl" <<'PYCAUNBIND'
import sys
path = sys.argv[1]
with open(path) as f:
    lines = f.readlines()

marker = "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──"
marker_legacy = "# ── OpenViking integration (added by openviking-agent-integration skill) ──"
start = None
end = None
for i, line in enumerate(lines):
    if (marker in line or marker_legacy in line) and start is None:
        start = i
    elif start is not None and line.strip() == "fi" and end is None:
        # Check if this fi closes the injection block (next line is blank, sleep, or EOF)
        if i + 1 >= len(lines) or lines[i+1].strip() == "" or "sleep" in lines[i+1]:
            end = i + 1
            break

if start is not None and end is not None:
    # Also remove preceding blank line
    if start > 0 and lines[start-1].strip() == "":
        start -= 1
    # Also remove trailing blank line
    if end < len(lines) and lines[end].strip() == "":
        end += 1
    del lines[start:end]
    with open(path, 'w') as f:
        f.writelines(lines)
    print("removed")
else:
    print("not-found")
PYCAUNBIND
    log_ok "OpenViking injection block removed from template start.sh"
  fi

  # ── 2. Remove mcp.openviking + build.prompt from sandbox config ──
  if [[ -n "$cf" && -f "$cf" ]]; then
    backup_file "$cf"
    python3 -c "
import json
with open('$cf') as f: cfg=json.load(f)
changed = False
if 'mcp' in cfg and 'openviking' in cfg['mcp']:
    del cfg['mcp']['openviking']
    if not cfg['mcp']: del cfg['mcp']
    changed = True
agent = cfg.get('agent', {})
build = agent.get('build', {})
if 'OpenViking' in build.get('prompt', ''):
    del build['prompt']
    if not build: del agent['build']
    if not agent: del cfg['agent']
    changed = True
if changed:
    with open('$cf', 'w') as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
"
    log_ok "OpenViking MCP + prompt removed from sandbox config"
  fi

  # ── 3. Remove openviking-config.json from sandbox ──
  if [[ -n "$ov_conf" ]]; then
    rm -f "$ov_conf"
    log_ok "openviking-config.json removed from sandbox"
  fi

  log_info "Restart CodeArts session for changes to take effect"
}

# ── OpenCode ──────────────────────────────────────────────────────────────────
unbind_opencode() {
  local tpl="/root/template/opencode/start.sh"
  local tpl_has_ov=false
  # Detect OpenViking integration in template (npm-based or legacy)
  if grep -q "OpenViking integration\|@openviking/opencode-plugin\|openviking plugin\|plugins/opencode" "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  else
    has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  fi

  local sandbox; sandbox=$(find_sandbox "opencode")
  local sandbox_has_ov=false
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    check_json_mcp "${sandbox}/.config/opencode/opencode.json" && sandbox_has_ov=true
    python3 -c "import json,sys; d=json.load(open('${sandbox}/.config/opencode/opencode.json')); sys.exit(0 if '@openviking/opencode-plugin' in d.get('plugin',[]) else 1)" 2>/dev/null && sandbox_has_ov=true
  fi

  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "OpenCode not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking" "opencode" "Remove OpenViking plugin + npm packages + config from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking integration from template and sandbox"; then return 0; fi

  # ── 1. Remove from template start.sh ──
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    python3 - "$tpl" <<'PYUNBIND'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()
marker = "# ── OpenViking integration"
idx = content.find(marker)
if idx != -1:
    end_marker = "export OPENCODE_SERVER_PASSWORD"
    end_idx = content.find(end_marker, idx)
    if end_idx != -1:
        content = content[:idx] + content[end_idx:]
        with open(path, 'w') as f:
            f.write(content)
        print("Removed OpenViking integration block from template")
    else:
        print("WARNING: end marker not found, skipping template removal")
else:
    print("No OpenViking integration block found in template")
PYUNBIND
    log_ok "OpenViking integration block removed from template start.sh"
  fi

  # ── 2. Remove from live sandbox ──
  if [[ -n "$sandbox" ]]; then
    local cf="${sandbox}/.config/opencode/opencode.json"
    if [[ -f "$cf" ]]; then
      backup_file "$cf"
      python3 - "$cf" <<'PYUNBIND2'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
changed = False
if "plugin" in cfg and "@openviking/opencode-plugin" in cfg["plugin"]:
    cfg["plugin"].remove("@openviking/opencode-plugin")
    if not cfg["plugin"]:
        del cfg["plugin"]
    changed = True
if "mcp" in cfg and "openviking" in cfg["mcp"]:
    del cfg["mcp"]["openviking"]
    if not cfg["mcp"]:
        del cfg["mcp"]
    changed = True
if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
    del cfg["agent"]["build"]["prompt"]
    if not cfg["agent"]["build"]:
        del cfg["agent"]["build"]
    if not cfg["agent"]:
        del cfg["agent"]
    changed = True
if changed:
    with open(path, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("Removed OpenViking from opencode.json")
PYUNBIND2
      log_ok "OpenViking plugin removed from live sandbox opencode.json"
    fi

    # Clean up npm packages and config
    rm -rf "${sandbox}/.config/opencode/node_modules" 2>/dev/null && log_ok "node_modules removed"
    rm -f "${sandbox}/.config/opencode/package.json" 2>/dev/null
    rm -f "${sandbox}/.config/opencode/package-lock.json" 2>/dev/null
    rm -f "${sandbox}/.config/opencode/.npmrc" 2>/dev/null
    rm -f "${sandbox}/.config/opencode/openviking-config.json" 2>/dev/null
    rm -rf "${sandbox}/.config/opencode/plugins/openviking" 2>/dev/null
    rm -f "${sandbox}/.config/opencode/plugins/openviking.js" 2>/dev/null
    log_ok "npm packages and OpenViking config cleaned up"
  fi
  log_info "Restart OpenCode for changes to take full effect"
}

# ── OpenClaw ──────────────────────────────────────────────────────────────────
unbind_openclaw() {
  local tpl="/root/template/openclaw/start.sh"
  local tpl_has_ov=false

  # Detect OpenViking injection in template start.sh.
  # Match actual block header lines (e.g. "# ── Step 5: OpenViking plugin install ..."),
  # NOT echo strings like "OpenViking plugin installed" that happen to contain the substring.
  # This catches all known formats:
  #   - Current skill:  "# ── Step 5: OpenViking plugin install (added by ...)"
  #   - Older ClawHub:  "# ── Step 5: Install OpenViking plugin (official ClawHub)"
  #   - Legacy config:  "# ── Step 5: OpenViking plugin config (added by ...)"
  #   - Legacy MCP:     "# ── Step 5: Inject OpenViking MCP server"
  #   - Sub-blocks:     "# ── Step 5.5: ... OpenViking ...", "# ── Step 5.6: ... OpenViking ..."
  if [[ -f "$tpl" ]] && grep -qE '# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking' "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  fi

  # Check for plugin/MCP artifacts in config files
  local has_cfg=false
  for cfg_file in /root/.openclaw/openclaw.json /root/runtime/openclaw/state/openclaw.json; do
    if [[ -f "$cfg_file" ]] && python3 -c "import json; d=json.load(open('$cfg_file')); exit(0 if d.get('plugins',{}).get('entries',{}).get('openviking') or d.get('plugins',{}).get('slots',{}).get('contextEngine')=='openviking' or 'openviking' in d.get('mcp',{}).get('servers',{}) else 1)" 2>/dev/null; then
      has_cfg=true
    fi
  done

  # Check for legacy extension directories
  local has_ext=false
  for ext_dir in /root/.openclaw/extensions/openviking /root/runtime/openclaw/state/extensions/openviking; do
    [[ -d "$ext_dir" ]] && has_ext=true
  done

  if [[ "$tpl_has_ov" == "false" && "$has_cfg" == "false" && "$has_ext" == "false" ]]; then
    log_ok "OpenClaw not integrated (nothing to remove)"; return 0
  fi

  require_confirmation "UNBIND OpenViking" "openclaw" "Remove OpenViking plugin install from template start.sh and clean up config files" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking plugin config and legacy artifacts"; then return 0; fi

  # Step 1: Remove ALL OpenViking-related Step 5.x blocks from template start.sh.
  # Uses a line-by-line approach that handles ALL injection formats:
  #   - Current skill format (with OVAGENTS heredoc terminator)
  #   - Older ClawHub format (no heredoc, blocks end at next Step comment)
  #   - Legacy direct-config-write and MCP formats
  # A block starts at any "# ── Step 5..." or "# ── Step 5.x..." line mentioning OpenViking,
  # and ends at the next "# ── Step N" line that does NOT mention OpenViking,
  # or at the gateway start line.
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    python3 - "$tpl" << 'PYUNBIND'
import sys, re

path = sys.argv[1]
with open(path) as f:
    lines = f.readlines()

new_lines = []
removed_blocks = 0
i = 0
n = len(lines)

# Pattern: a Step 5 or Step 5.x comment header that mentions OpenViking
ov_block_start = re.compile(r'# ── Step 5(?:\.\d+)?:.*[Oo]pen[Vv]iking')
# Pattern: any Step N comment header (used to find block end)
any_step_header = re.compile(r'# ── Step \d')

while i < n:
    line = lines[i]

    if ov_block_start.match(line):
        # Found an OpenViking Step 5.x block — skip it entirely
        removed_blocks += 1
        i += 1
        while i < n:
            next_line = lines[i]
            # End of block: next Step header that is NOT OpenViking-related
            if any_step_header.match(next_line) and 'OpenViking' not in next_line and 'openviking' not in next_line.lower():
                break
            # End of block: gateway start line
            if 'Starting Gateway' in next_line or 'gateway run' in next_line:
                break
            i += 1
        continue

    new_lines.append(line)
    i += 1

# Fix step numbering: if we removed Step 5, renumber Step 6 -> Step 5
content = ''.join(new_lines)
content = content.replace("# ── Step 6: Start the Gateway", "# ── Step 5: Start the Gateway")

with open(path, 'w') as f:
    f.write(content)

print(f"removed {removed_blocks} OpenViking block(s)")
PYUNBIND
    local remove_result=$?
    if [[ $remove_result -eq 0 ]]; then
      log_ok "OpenViking injection blocks removed from template start.sh"
    else
      log_warn "Template removal completed with issues"
    fi

    # Post-removal verification: check for residual OpenViking references
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

    # Sync to sandbox workspace
    local sandbox_dir=""
    for d in /root/job-envs/sandboxes/openclaw-*/; do
      if [[ -d "${d}process_dir" ]]; then
        sandbox_dir="$d"
        break
      fi
    done
    if [[ -n "$sandbox_dir" ]]; then
      cp "$tpl" "${sandbox_dir}process_dir/start.sh"
      chmod +x "${sandbox_dir}process_dir/start.sh"
      log_ok "Synced start.sh to sandbox workspace"
    fi
  fi

  # Step 2: Clean up config files (plugin entries, MCP servers, tool policy)
  local cleaned=false
  for ext_dir in /root/.openclaw/extensions/openviking /root/runtime/openclaw/state/extensions/openviking; do
    if [[ -d "$ext_dir" ]]; then
      rm -rf "$ext_dir"
      cleaned=true
    fi
  done
  for cfg_file in /root/.openclaw/openclaw.json /root/runtime/openclaw/state/openclaw.json; do
    [[ -f "$cfg_file" ]] || continue
    python3 -c "
import json, sys
path = sys.argv[1]
with open(path) as f: d=json.load(f)
changed = False
# Remove mcp.servers.openviking (legacy MCP mode)
servers = d.get('mcp',{}).get('servers',{})
if 'openviking' in servers:
    del servers['openviking']
    if not servers: d.get('mcp',{}).pop('servers', None)
    if not d.get('mcp'): d.pop('mcp', None)
    changed = True
# Remove plugin entries (current plugin config mode)
plugins = d.get('plugins', {})
entries = plugins.get('entries', {})
if 'openviking' in entries:
    del entries['openviking']
    changed = True
slots = plugins.get('slots', {})
if slots.get('contextEngine') == 'openviking':
    del slots['contextEngine']
    changed = True
allow = plugins.get('allow', [])
if 'openviking' in allow:
    allow.remove('openviking')
    changed = True
if not entries: plugins.pop('entries', None)
if not slots: plugins.pop('slots', None)
if not allow: plugins.pop('allow', None)
if not plugins: d.pop('plugins', None)
# Remove tools.alsoAllow group:plugins
aa = d.get('tools',{}).get('alsoAllow',[])
aa = [x for x in aa if x != 'group:plugins']
if aa: d.setdefault('tools',{})['alsoAllow'] = aa
else: d.get('tools',{}).pop('alsoAllow',None)
if not d.get('tools'): d.pop('tools', None)
if changed:
    with open(path, 'w') as f: json.dump(d, f, indent=2)
    print('cleaned')
else:
    print('skip')
" "$cfg_file" 2>/dev/null | grep -q "cleaned" && cleaned=true
  done
  [[ "$cleaned" == "true" ]] && log_ok "Config files cleaned (plugin entries, MCP servers, tool policy)"

  # Step 3: Remove AGENTS.md created by integration
  for agents_md in /root/.openclaw/workspace/AGENTS.md /root/runtime/openclaw/state/workspace/AGENTS.md; do
    if [[ -f "$agents_md" ]] && grep -q "OpenViking" "$agents_md" 2>/dev/null; then
      rm -f "$agents_md"
      cleaned=true
    fi
  done

  log_ok "OpenViking removed from OpenClaw"
  log_info "Restart OpenClaw for changes to take effect"
}


# ── Hermes ────────────────────────────────────────────────────────────────────
unbind_hermes() {
  local tpl="/root/template/hermes/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  # Also check for MCP SDK install block (separate marker, same skill)
  grep -q "MCP SDK install.*$OV_MARKER\|MCP SDK install.*$OV_MARKER_LEGACY" "$tpl" 2>/dev/null && tpl_has_ov=true

  local sandbox; sandbox=$(find_sandbox "hermes")
  local sandbox_has_ov=false
  [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]] && grep -q "openviking" "${sandbox}/.hermes/config.yaml" 2>/dev/null && sandbox_has_ov=true

  [[ "$tpl_has_ov" == "false" && "$sandbox_has_ov" == "false" ]] && { log_ok "Hermes not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking MCP" "hermes" "Remove OpenViking MCP + MCP SDK install from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking MCP from template and sandbox"; then return 0; fi

  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    # Remove OpenViking MCP injection block
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── OpenViking MCP injection ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    # Remove MCP SDK install block (separate injection by same skill)
    sed -i '/# ── MCP SDK install ('"$OV_MARKER"')/,/^fi$/d' "$tpl"
    sed -i '/# ── MCP SDK install ('"$OV_MARKER_LEGACY"')/,/^fi$/d' "$tpl"
    log_ok "OpenViking MCP + MCP SDK block removed from template start.sh"
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
    log_ok "OpenViking MCP + memory provider removed from live sandbox"
  fi
  log_info "Restart Hermes for changes to take full effect"
}

# ── JiuwenSwarm ───────────────────────────────────────────────────────────────
unbind_jiuwenswarm() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { log_error "JiuwenSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }

  local tpl="/root/template/jiuwenswarm/start.sh"

  # Check if OpenViking MCP server exists anywhere
  local has_sandbox has_template
  grep -q "name: openviking" "$cf" 2>/dev/null && has_sandbox=1 || has_sandbox=0
  [[ -f "$tpl" ]] && grep -q "OpenViking MCP injection" "$tpl" 2>/dev/null && has_template=1 || has_template=0

  if [[ "$has_sandbox" -eq 0 && "$has_template" -eq 0 ]]; then
    log_ok "JiuwenSwarm not integrated (nothing to remove)"
    return 0
  fi

  require_confirmation "UNBIND OpenViking MCP" "jiuwenswarm" "Remove OpenViking MCP from sandbox config + template start.sh" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking MCP from $cf and $tpl"; then return 0; fi

  # ── 1. Remove from sandbox config ──
  if [[ "$has_sandbox" -eq 1 ]]; then
    backup_file "$cf"
    python3 - "$cf" << 'PYJW'
import sys, re
path = sys.argv[1]
with open(path) as f:
    content = f.read()

content = re.sub(
    r'    - name: openviking\n(?:      .+\n)+',
    '',
    content,
    count=1
)
content = re.sub(
    r'  servers:\n(?!    - )',
    '  servers: []\n',
    content,
    count=1
)
content = content.replace("  servers: []\n\n  # 示例", "  servers: []\n  # 示例")

with open(path, 'w') as f:
    f.write(content)
PYJW
  fi

  # ── 2. Remove injection block from template start.sh ──
  if [[ "$has_template" -eq 1 ]]; then
    backup_file "$tpl"
    python3 - "$tpl" << 'PYTPL'
import sys
path = sys.argv[1]
with open(path) as f:
    lines = f.readlines()

marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
marker_legacy = "# ── OpenViking MCP injection (added by openviking-agent-integration skill) ──"
start = None
end = None
for i, line in enumerate(lines):
    if (marker in line or marker_legacy in line) and start is None:
        start = i
    elif start is not None and line.strip() == "fi" and end is None:
        # Check if this fi closes the injection block (next line is sleep or blank)
        if i + 1 < len(lines) and (lines[i+1].strip() == '' or 'sleep' in lines[i+1]):
            end = i + 1
            break
        # Fallback: just find the first fi after marker
        end = i + 1
        break

if start is not None and end is not None:
    if start > 0 and lines[start-1].strip() == "":
        start -= 1
    del lines[start:end]
    with open(path, 'w') as f:
        f.writelines(lines)
    print("Removed from template")
else:
    print("Injection block not found in template")
PYTPL
    log_ok "Injection block removed from template start.sh"
  fi

  log_ok "OpenViking MCP removed from JiuwenSwarm"
  log_info "Restart JiuwenSwarm for changes to take effect"
}

# ── KimiCode ──────────────────────────────────────────────────────────────────
unbind_kimicode() {
  local tpl="/root/template/kimicode/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  # Also check for openviking-config.json creation block
  grep -q "Create openviking-config.json" "$tpl" 2>/dev/null && tpl_has_ov=true

  local mcp_file="/root/runtime/kimicode/data/mcp.json"
  local live_has_ov=false
  [[ -f "$mcp_file" ]] && python3 -c "import json; d=json.load(open('$mcp_file')); exit(0 if 'openviking' in d.get('mcpServers',{}) else 1)" 2>/dev/null && live_has_ov=true

  # Also check legacy config.toml for old-style injection
  local legacy_cf="/root/runtime/kimicode/data/config.toml"
  local legacy_has_ov=false
  [[ -f "$legacy_cf" ]] && grep -q "mcp_servers.openviking" "$legacy_cf" 2>/dev/null && legacy_has_ov=true

  # Check for openviking-config.json in sandbox
  local sandbox; sandbox=$(find_sandbox "kimicode")
  local ov_conf=""
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/openviking-config.json" ]]; then
    live_has_ov=true
    ov_conf="${sandbox}/.config/opencode/openviking-config.json"
  fi

  [[ "$tpl_has_ov" == "false" && "$live_has_ov" == "false" && "$legacy_has_ov" == "false" ]] && { log_ok "KimiCode not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking MCP" "kimicode" "Remove OpenViking MCP + openviking-config.json from template and sandbox" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking MCP"; then return 0; fi

  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    python3 - "$tpl" <<'PYKUNBIND'
import sys
path = sys.argv[1]
with open(path) as f:
    lines = f.readlines()

marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
marker_legacy = "# ── OpenViking MCP injection (added by openviking-agent-integration skill) ──"
start = None
end = None
for i, line in enumerate(lines):
    if (marker in line or marker_legacy in line) and start is None:
        start = i
    elif start is not None and line.strip() == "AGENTSMD":
        end = i + 1  # include the MCPEOF line
        break

if start is not None and end is not None:
    # Also remove trailing empty line if present
    if end < len(lines) and lines[end].strip() == "":
        end += 1
    del lines[start:end]
    with open(path, 'w') as f:
        f.writelines(lines)
    print("removed MCP injection block")
else:
    print("MCP injection block not found")

# Also remove the openviking-config.json creation block
with open(path) as f:
    lines = f.readlines()

marker2 = "# Create openviking-config.json"
start = None
end = None
for i, line in enumerate(lines):
    if marker2 in line and start is None:
        start = i
    elif start is not None and line.strip() == "fi" and end is None:
        # Check if this fi closes the config block (next line is blank, sleep, or EOF)
        if i + 1 >= len(lines) or lines[i+1].strip() == "" or "sleep" in lines[i+1]:
            end = i + 1
            break

if start is not None and end is not None:
    # Also remove preceding blank line
    if start > 0 and lines[start-1].strip() == "":
        start -= 1
    # Also remove trailing blank line
    if end < len(lines) and lines[end].strip() == "":
        end += 1
    del lines[start:end]
    with open(path, 'w') as f:
        f.writelines(lines)
    print("removed openviking-config.json block")
else:
    print("openviking-config.json block not found")
PYKUNBIND
    log_ok "OpenViking MCP + config block removed from template start.sh"
  fi

  if [[ "$live_has_ov" == "true" ]]; then
    if [[ -f "$mcp_file" ]]; then
      backup_file "$mcp_file"
      python3 -c "
import json
with open('$mcp_file') as f: d=json.load(f)
servers = d.get('mcpServers', {})
if 'openviking' in servers:
    del servers['openviking']
    if not servers:
        del d['mcpServers']
    with open('$mcp_file', 'w') as f:
        json.dump(d, f, indent=2)
"
      log_ok "OpenViking MCP removed from live mcp.json"
    fi
  fi

  # Remove openviking-config.json from sandbox
  if [[ -n "$ov_conf" ]]; then
    rm -f "$ov_conf"
    log_ok "openviking-config.json removed from sandbox"
  fi

  # Clean legacy config.toml if old-style injection exists
  if [[ "$legacy_has_ov" == "true" ]]; then
    backup_file "$legacy_cf"
    python3 -c "
lines = []
skip = False
with open('$legacy_cf') as f:
    for line in f:
        if line.strip().startswith('[mcp_servers.openviking]'):
            skip = True
            continue
        if skip and (line.strip().startswith('[') or line.strip() == ''):
            if line.strip().startswith('['):
                skip = False
            else:
                continue
        if not skip:
            lines.append(line)
while lines and lines[-1].strip() == '':
    lines.pop()
with open('$legacy_cf', 'w') as f:
    f.writelines(lines)
    f.write('\n')
"
    log_ok "Legacy MCP section removed from config.toml"
  fi
  log_info "Restart KimiCode for changes to take full effect"
}

# ── DeepSeek Harness (dsh) ────────────────────────────────────────────────────
unbind_deepseek_harness() {
  local tpl="/root/template/deepseek-harness/start.sh"
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"

  local tpl_has_ov=false live_has_ov=false
  grep -q "OpenViking long-term memory integration" "$tpl" 2>/dev/null && tpl_has_ov=true
  for p in web cc-tui; do
    grep -q "mcp-openviking" "${dsh_home}/profiles/$p/cordis.patch.yml" 2>/dev/null && live_has_ov=true
  done
  local skill_has_ov=false
  [[ -f "${dsh_home}/skills/openviking/SKILL.md" ]] && skill_has_ov=true
  grep -q "## OpenViking Long-Term Memory" "${dsh_home}/AGENTS.md" 2>/dev/null && skill_has_ov=true
  local cfg_has_ov=false
  [[ -f "${dsh_home}/openviking-config.json" ]] && cfg_has_ov=true

  [[ "$tpl_has_ov" == "false" && "$live_has_ov" == "false" && "$skill_has_ov" == "false" && "$cfg_has_ov" == "false" ]] && { log_ok "DeepSeek Harness not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking MCP" "deepseek-harness" "Remove mcp-openviking + persona + re-enable entries from dsh profiles, openviking-config.json, skill + AGENTS.md, template start.sh" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking MCP from template start.sh, live profiles (mcp/persona/re-enable), config, skill + AGENTS.md"; then return 0; fi

  # ── 1. Template start.sh (persistent) ──
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    python3 << 'DSHUNBINJ'
import os
path = "/root/template/deepseek-harness/start.sh"
with open(path) as f:
    lines = f.read().split('\n')
out = []
i = 0
while i < len(lines):
    if 'OpenViking long-term memory integration' in lines[i]:
        # block spans from preceding '# ═══' rule line down to the 'OVPY' terminator
        while i > 0 and not lines[i - 1].startswith('# ═══════════'):
            i -= 1
        if i > 0 and lines[i - 1].startswith('# ═══════════'):
            i -= 1
        if out and out[-1] == '':
            out.pop()
        while i < len(lines) and lines[i] != 'OVPY':
            i += 1
        i += 1  # skip 'OVPY' line
        continue
    out.append(lines[i])
    i += 1
while out and out[-1] == '':
    out.pop()
with open(path, 'w') as f:
    f.write('\n'.join(out) + '\n')
DSHUNBINJ
    log_ok "OpenViking integration block removed from template start.sh"
  fi

  # ── 2. Live sandbox profiles + skill + AGENTS.md ──
  if [[ "$live_has_ov" == "true" ]]; then
    for p in web cc-tui; do
      local cf="${dsh_home}/profiles/$p/cordis.patch.yml"
      [[ -f "$cf" ]] || continue
      backup_file "$cf" 2>/dev/null || true
      python3 - "$cf" << 'DSHPATCH'
import sys
path = sys.argv[1]
with open(path) as f:
    lines = f.read().split('\n')
out = []
i = 0
while i < len(lines):
    line = lines[i].strip()
    if line == '- insert:':
        # capture this insert block, drop it if it defines mcp-openviking
        j = i + 1
        body = []
        while j < len(lines) and not (lines[j].startswith('- ') and not lines[j].startswith('- insert:')):
            body.append(lines[j])
            j += 1
        if any('mcp-openviking' in b for b in body):
            i = j
            continue
        out.append(lines[i])
        i += 1
        continue
    if line == '- id: system-prompt':
        # drop our persona directive block (mentions mcp__openviking__)
        j = i + 1
        body = []
        while j < len(lines) and not (lines[j].startswith('- ') and not lines[j].startswith('  ')):
            body.append(lines[j])
            j += 1
        if any('openviking' in b.lower() for b in body):
            i = j
            continue
        out.append(lines[i])
        i += 1
        continue
    if line == '- id: agent-instructions' and i + 1 < len(lines) and 'disabled: false' in lines[i + 1]:
        i += 2
        continue
    if line == '- id: skill-filesystem' and i + 1 < len(lines) and 'disabled: false' in lines[i + 1]:
        i += 2
        continue
    out.append(lines[i])
    i += 1
while out and out[-1].strip() == '':
    out.pop()
with open(path, 'w') as f:
    f.write('\n'.join(out) + '\n')
DSHPATCH
    done
    log_ok "mcp-openviking entry removed from live dsh profiles (web/cc-tui)"
  fi

  if [[ "$skill_has_ov" == "true" ]]; then
    rm -rf "${dsh_home}/skills/openviking"
    if grep -q "## OpenViking Long-Term Memory" "${dsh_home}/AGENTS.md" 2>/dev/null; then
      rm -f "${dsh_home}/AGENTS.md"
    fi
    log_ok "OpenViking skill + AGENTS.md removed from live dsh home"
  fi

  if [[ "$cfg_has_ov" == "true" ]]; then
    rm -f "${dsh_home}/openviking-config.json"
    log_ok "openviking-config.json removed from live dsh home"
  fi

  # ── 3. Sync template to sandbox so a restart stays clean ──
  if [[ -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Cleaned template start.sh synced to sandbox .process_dir"
  fi

  log_info "Restart DeepSeek Harness (web + cc-tui) for changes to take full effect"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  local agents=()
  if [[ "${ALL_AGENTS:-false}" == "true" ]]; then
    agents=(codearts opencode openclaw hermes jiuwenswarm kimicode deepseek-harness)
  elif [[ -n "${AGENT:-}" ]]; then
    agents=("$AGENT")
  else
    log_error "Specify --agent <name> or --all"
    exit 1
  fi

  local rc=0
  for a in "${agents[@]}"; do
    echo ""
    log_info "Processing agent: $a"
    case "$a" in
      codearts)    unbind_codearts    || rc=1 ;;
      opencode)    unbind_opencode    || rc=1 ;;
      openclaw)    unbind_openclaw    || rc=1 ;;
      hermes)      unbind_hermes      || rc=1 ;;
      jiuwenswarm) unbind_jiuwenswarm || rc=1 ;;
      kimicode)    unbind_kimicode    || rc=1 ;;
      deepseek-harness) unbind_deepseek_harness || rc=1 ;;
      *) log_error "Unknown agent: $a"; rc=1 ;;
    esac
  done

  echo ""
  if [[ $rc -eq 0 ]]; then
    log_ok "All requested unbindings completed successfully"
  else
    log_warn "Some unbindings failed. Review output above."
  fi
  return $rc
}

main "$@"
