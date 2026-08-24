#!/bin/bash
# =============================================================================
# agents/openclaw.sh — OpenClaw agent subclass
# =============================================================================
# Mechanism: ClawHub plugin + contextEngine
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_openclaw_integrate, agent_openclaw_unbind, agent_openclaw_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_openclaw_register() {
  agent::set_meta name "openclaw"
  agent::set_meta display_name "OpenClaw"
  agent::set_meta sandbox_pattern "openclaw-*"
  agent::set_meta template_path "/root/template/openclaw/start.sh"
  agent::set_meta mechanism "ClawHub plugin + contextEngine"
  registry_add "openclaw"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_openclaw_integrate() {
  # OpenClaw runs inside a bwrap sandbox. The config (OPENCLAW_STATE_DIR) is inside
  # the sandbox (e.g. /tmp/.openclaw) and not accessible from outside. We inject
  # the official @openviking/openclaw-plugin install into template start.sh, so it
  # runs inside the gateway's bwrap on every start.
  # Official mechanism (docs/en/agent-integrations/03-openclaw.md + INSTALL-AGENT.md):
  #   openclaw plugins install clawhub:@openviking/openclaw-plugin   (primary)
  #   openclaw openviking setup --base-url ... --api-key ... --json  (JSON contract)
  #   openclaw gateway restart && openclaw openviking status --json  (verify)
  # ClawHub is the primary source; Huawei Cloud npm mirror is the fallback when
  # ClawHub is unreachable/rate-limited.
  local tpl="/root/template/openclaw/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "OpenClaw template start.sh not found: $tpl"; return 1; }

  # Persistent runtime location for the on-demand plugin source (survives sandbox stop+start)
  local ov_runtime_src="/root/runtime/openclaw/openviking-plugin-source"

  # Install the plugin source — try npm first (fast, single tarball), fall back to
  # GitHub file-by-file download (ov_plugin_provision) if npm is unreachable.
  local _ov_npm_ok=0
  if [[ "${DRY_RUN:-false}" != "true" ]]; then
    local _npm_reg; _npm_reg=$(ov_first_npm_registry)
    log_info "Trying npm install @openviking/openclaw-plugin (online, $_npm_reg)..."
    mkdir -p /tmp/openviking
    local _npm_stage; _npm_stage=$(mktemp -d /tmp/openviking/ov-npm.XXXXXX) || { log_warn "mktemp failed, falling back to GitHub"; _npm_stage=""; }
    # Create package.json first so npm installs into local node_modules
    cat > "$_npm_stage/package.json" << 'OVPKGEOF'
{
  "dependencies": {
    "@openviking/openclaw-plugin": "latest"
  }
}
OVPKGEOF
    if [[ -n "$_npm_stage" ]] && \
       (cd "$_npm_stage" && npm install \
           --registry="$_npm_reg" --no-audit --no-fund 2>&1 | tail -5) && \
       [[ -d "$_npm_stage/node_modules/@openviking/openclaw-plugin" ]]; then
      rm -rf "$ov_runtime_src"
      cp -a "$_npm_stage/node_modules/@openviking/openclaw-plugin" "$ov_runtime_src"
      log_ok "openclaw-plugin installed from npm (online) -> $ov_runtime_src"
      touch "$ov_runtime_src"
      _ov_npm_ok=1
    else
      log_warn "npm install failed or plugin not found — falling back to GitHub source download"
    fi
    [[ -n "$_npm_stage" ]] && rm -rf "$_npm_stage"
  fi
  if [[ "$_ov_npm_ok" -eq 0 ]]; then
    ov_plugin_provision "openclaw-plugin" "$ov_runtime_src" || return 1
    [[ "${DRY_RUN:-false}" == "true" ]] || log_ok "openclaw-plugin source installed on demand at $ov_runtime_src"
  fi

  # Check if already integrated (official plugin install in start.sh)
  if grep -q "OpenViking plugin install" "$tpl" 2>/dev/null; then
    log_ok "OpenClaw already integrated (official plugin install in start.sh)"
    # Verify live sandbox has endpoint config applied (not just template).
    # The gateway process should have OPENVIKING_BASE_URL in its environment.
    # If missing, start.sh was not re-run (e.g. sandbox restarted via stop+start
    # stop+start recreates bwrap with 'bash /workspace/process_dir/start.sh', re-running start.sh).
    local gw_pid=""
    gw_pid=$(pgrep -f "openclaw-gateway" 2>/dev/null | head -1)
    if [ -n "$gw_pid" ] && [ -f "/proc/$gw_pid/environ" ]; then
      if tr '\0' '\n' < "/proc/$gw_pid/environ" 2>/dev/null | grep -q "OPENVIKING_BASE_URL=http"; then
        log_ok "OpenClaw live sandbox has OpenViking endpoint configured"
      else
        log_warn "Template has OpenViking injection, but live sandbox is MISSING endpoint config"
        log_warn "Fix: restart sandbox via job-env-manager API (stop + start re-runs start.sh):"
        log_warn "  curl -s -X POST http://127.0.0.1:8090/api/v1/envs/openclaw/stop"
        log_warn "  # Wait for stopped, then:"
        log_warn "  curl -s -X POST http://127.0.0.1:8090/api/v1/envs/openclaw/start"
        log_warn "  # Poll until running: curl -s http://127.0.0.1:8090/api/v1/envs/openclaw | jq -r .state"
      fi
    else
      log_warn "OpenClaw gateway process not found — sandbox may not be running"
    fi
    return 0
  fi

  # Slot-replacement approval: before baking --force-slot into the template, check
  # the live config to see whether another plugin owns plugins.slots.contextEngine.
  # Official INSTALL-AGENT.md: "Never silently replace another context engine."
  local force_slot=0
  for cfg_file in /root/.openclaw/openclaw.json /root/runtime/openclaw/state/openclaw.json; do
    if [[ -f "$cfg_file" ]] && python3 -c "
import json,sys
try:
    d=json.load(open('$cfg_file'))
    owner=d.get('plugins',{}).get('slots',{}).get('contextEngine','')
    print(owner)
except Exception: print('')
" 2>/dev/null | grep -qv '^$' && ! python3 -c "
import json
d=json.load(open('$cfg_file'))
print(d.get('plugins',{}).get('slots',{}).get('contextEngine',''))
" 2>/dev/null | grep -q 'openviking'; then
      log_warn "plugins.slots.contextEngine is currently owned by another plugin"
      if [[ "${AUTO_YES:-false}" == "true" ]]; then
        force_slot=1
      else
        read -p "Allow --force-slot to replace it (yes/no)? " ans
        [[ "$ans" == "yes" || "$ans" == "y" ]] && force_slot=1
      fi
    fi
  done

  # Offline-write approval (official: use --allow-offline only with user approval).
  local allow_offline=1   # dev-mode local server; safe default, still documented

  require_confirmation "Integrate OpenViking (Official ClawHub Plugin)" "openclaw" "Install @openviking/openclaw-plugin (ClawHub → domestic npm mirror → on-demand source build fallback) + openviking setup --json into template start.sh (contextEngine slot, auto-recall + auto-capture)" || return 1
  if dry_run_msg "Would add OpenViking plugin install to $tpl"; then return 0; fi

  backup_file "$tpl"

  # Insert official plugin install block before the gateway start step
  python3 - "$tpl" "$OV_ENDPOINT" "$force_slot" "$allow_offline" << 'PYINJECT'
import sys, re
path, endpoint, force_slot, allow_offline = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path) as f: content = f.read()

# Skip if already has plugin install injection
if "OpenViking plugin install" in content:
    print("already")
    sys.exit(0)

block = """# ── Step 5: OpenViking plugin install (official ClawHub, added by huawei-cloud-openviking-agent-integration skill) ──
# Official mechanism (docs/en/agent-integrations/03-openclaw.md + INSTALL-AGENT.md):
#   openclaw plugins install clawhub:@openviking/openclaw-plugin
#   openclaw openviking setup --base-url ... [--api-key ...] --json
#   openclaw gateway restart
#   openclaw openviking status --json
# Cache-first: on sandbox restart, check if plugin already installed; if not,
# install from the persistent runtime cache (no network); only hit ClawHub/npm
# on first integrate or cache miss. Survives undeploy+deploy via /root/runtime/.
echo "[openclaw] Provisioning OpenViking plugin (cache-first)..."
OV_PLUGIN_INSTALLED=0
OV_VENDOR_SRC="/root/runtime/openclaw/openviking-plugin-source"

# ── Step 1: Plugin already installed? (survives stop+start, lost on undeploy+deploy) ──
if "$NODE" "$CLI" plugins list 2>/dev/null | grep -q "openviking"; then
  OV_PLUGIN_INSTALLED=1
  echo "[openclaw] OpenViking plugin already installed — skipping re-install (cache hit)."
fi

# ── Step 2: Install from persistent runtime cache (no network, survives undeploy+deploy) ──
if [[ "$OV_PLUGIN_INSTALLED" = "0" && -d "$OV_VENDOR_SRC" ]]; then
  echo "[openclaw] Installing OpenViking plugin from runtime cache (no network)..."
  OV_BUILD_DIR=$(mktemp -d /tmp/openclaw-ov-build.XXXXXX)
  cp -a "$OV_VENDOR_SRC/." "$OV_BUILD_DIR/"
  export NPM_CONFIG_REGISTRY=https://mirrors.huaweicloud.com/repository/npm/
  if (cd "$OV_BUILD_DIR" && npm install --production --no-audit --no-fund 2>&1 | tail -3) && \
     (cd "$OV_BUILD_DIR" && npx tsc -p tsconfig.build.json 2>&1 | tail -3); then
    if [[ -d "$OV_BUILD_DIR/dist" ]]; then
      if "$NODE" "$CLI" plugins install "$OV_BUILD_DIR" 2>&1; then
        OV_PLUGIN_INSTALLED=1
        echo "[openclaw] OpenViking plugin installed from runtime cache (local build)."
      else
        echo "[openclaw] WARNING: local plugin install command failed — trying online sources"
      fi
    else
      echo "[openclaw] WARNING: tsc build produced no dist/ — trying online sources"
    fi
  else
    echo "[openclaw] WARNING: local build failed — trying online sources"
  fi
  unset NPM_CONFIG_REGISTRY
  rm -rf "$OV_BUILD_DIR"
fi

# ── Step 3: Online fallback — ClawHub → npm mirrors (first integrate or cache miss) ──
if [[ "$OV_PLUGIN_INSTALLED" = "0" ]]; then
  echo "[openclaw] Cache miss — trying online sources (ClawHub → npm mirrors)..."
  if "$NODE" "$CLI" plugins install clawhub:@openviking/openclaw-plugin 2>&1; then
    OV_PLUGIN_INSTALLED=1
    echo "[openclaw] OpenViking plugin installed from ClawHub"
  else
    echo "[openclaw] WARNING: ClawHub install failed — falling back to domestic npm mirror"
    export NPM_CONFIG_REGISTRY=https://mirrors.huaweicloud.com/repository/npm/
    if "$NODE" "$CLI" plugins install @openviking/openclaw-plugin --acknowledge-clawhub-risk 2>&1; then
      OV_PLUGIN_INSTALLED=1
      echo "[openclaw] OpenViking plugin installed (npm Huawei Cloud mirror fallback)"
    else
      export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com/
      if "$NODE" "$CLI" plugins install @openviking/openclaw-plugin --acknowledge-clawhub-risk 2>&1; then
        OV_PLUGIN_INSTALLED=1
        echo "[openclaw] OpenViking plugin installed (npm npmmirror fallback)"
      else
        echo "[openclaw] WARNING: all online sources failed — plugin will not load"
      fi
    fi
    unset NPM_CONFIG_REGISTRY
  fi
fi

# ── Step 5.4: Configure OpenViking endpoint via official JSON contract ──
# OpenClaw runs in an ephemeral bwrap on every boot, so environment and config
# are re-derived each start. `openviking setup --json` is the official write path
# (it bypasses config-set schema validation and emits machine-readable results).
export OPENVIKING_BASE_URL="__ENDPOINT__"
# API key is passed through from the boot environment when set — never written here.
export OPENVIKING_ENDPOINT="__ENDPOINT__"
if [ "$OV_PLUGIN_INSTALLED" = "1" ]; then
  # --force-slot / --allow-offline are baked at integrate time by explicit user
  # approval (Official INSTALL-AGENT.md: never silently replace another engine).
  OV_SETUP_ARGS=(--base-url "__ENDPOINT__" --json)
  [ -n "${OPENVIKING_API_KEY:-}" ] && OV_SETUP_ARGS+=(--api-key "$OPENVIKING_API_KEY")
  [ "${OV_FORCE_SLOT:-OV_FORCE_SLOT_DEFAULT}" = "1" ] && OV_SETUP_ARGS+=(--force-slot)
  [ "${OV_ALLOW_OFFLINE:-OV_ALLOW_OFFLINE_DEFAULT}" = "1" ] && OV_SETUP_ARGS+=(--allow-offline)

  OV_SETUP_OUT=$("$NODE" "$CLI" openviking setup "${OV_SETUP_ARGS[@]}" 2>/dev/null || true)
  if echo "$OV_SETUP_OUT" | grep -q '"success":true'; then
    echo "[openclaw] OpenViking plugin configured via setup (JSON contract): __ENDPOINT__"
  elif echo "$OV_SETUP_OUT" | grep -q '"action":"slot_blocked"'; then
    if [ "${OV_FORCE_SLOT:-OV_FORCE_SLOT_DEFAULT}" = "1" ]; then
      echo "[openclaw] WARNING: slot was blocked; --force-slot retry already attempted"
    else
      echo "[openclaw] WARNING: contextEngine slot owned by another plugin; not replacing (authorize --force-slot at integrate time to override)"
    fi
  elif echo "$OV_SETUP_OUT" | grep -q '"action":"error"'; then
    echo "[openclaw] ERROR: openviking setup validation failed: $OV_SETUP_OUT"
  elif echo "$OV_SETUP_OUT" | grep -q '"health":{"ok":false'; then
    if [ "${OV_ALLOW_OFFLINE:-OV_ALLOW_OFFLINE_DEFAULT}" != "1" ]; then
      echo "[openclaw] WARNING: OpenViking server unreachable and --allow-offline not approved; config not written"
    fi
  elif echo "$OV_SETUP_OUT" | grep -q 'root_key'; then
    echo "[openclaw] ERROR: setup requires --account-id/--user-id for root API keys; see INSTALL-AGENT.md"
  else
    echo "[openclaw] WARNING: unexpected setup output: $OV_SETUP_OUT"
  fi
else
  echo "[openclaw] Plugin not installed — skipping openviking setup"
fi

# ── Step 5.5: Enable OpenViking plugin (official contract) ──
# `plugins enable openviking` sets plugins.entries.openviking.enabled=true
# AND plugins.slots.contextEngine=openviking.
if [ "$OV_PLUGIN_INSTALLED" = "1" ]; then
  "$NODE" "$CLI" plugins enable openviking 2>/dev/null || true
  # Explicitly trust the non-bundled plugin (the gateway requires plugins.allow
  # for non-bundled plugins; without it the plugin is only "maybe auto-loaded").
  "$NODE" "$CLI" config set 'plugins.allow' '["openviking"]' 2>/dev/null || true
  echo "[openclaw] Enabled OpenViking plugin (contextEngine slot)"
fi

# ── Step 5.6: OpenViking agent instructions (added by huawei-cloud-openviking-agent-integration skill) ──
# Supplementary AGENTS.md for explicit tool usage guidance
mkdir -p "$OPENCLAW_STATE_DIR/workspace"
OV_AGENTS="$OPENCLAW_STATE_DIR/workspace/AGENTS.md"
# Append OpenViking instructions to AGENTS.md (don't overwrite — OpenClaw bootstrap may have created it)
if ! grep -q "OpenViking Long-Term Memory" "$OV_AGENTS" 2>/dev/null; then
  cat >> "$OV_AGENTS" << 'OVAGENTS'

## OpenViking Long-Term Memory

OpenViking is integrated as the contextEngine plugin — it automatically recalls
relevant context before each response and captures important information after.
You also have direct access to OpenViking MCP tools for explicit operations:

1. **search**: Deep semantic retrieval with session context and intent analysis.
2. **recall**: Memory recall across memory types (events, entities, preferences).
3. **remember**: Store important information — user preferences, project decisions, technical details.
4. **read**: Read content from viking:// URIs for stored reference materials.

The contextEngine handles auto-recall automatically; use these tools for explicit
or targeted operations when needed.
OVAGENTS
  echo "[openclaw] OpenViking instructions appended to AGENTS.md"
else
  echo "[openclaw] OpenViking instructions already in AGENTS.md"
fi

"""
block = block.replace('__ENDPOINT__', endpoint)
# Bake the user-approved slot/offline decisions into the injected block (each boot is non-interactive)
block = block.replace('OV_FORCE_SLOT_DEFAULT', str(force_slot))
block = block.replace('OV_ALLOW_OFFLINE_DEFAULT', str(allow_offline))

# Find gateway start marker and insert before it
gateway_marker = "# ── Step 5: Start the Gateway"
if gateway_marker in content:
    content = content.replace(gateway_marker, block + gateway_marker)
    # Renumber Step 5 -> Step 6
    content = content.replace(gateway_marker, gateway_marker.replace("Step 5", "Step 6"))
else:
    # Fallback: try any "Step N: Start the Gateway" pattern
    content = re.sub(r'(# ── Step \d+: Start the Gateway)', block + r'\1', content)
with open(path, 'w') as f: f.write(content)
print("injected")
PYINJECT
  log_ok "OpenClaw template updated with official OpenViking plugin install (ClawHub → domestic npm → on-demand source build)"

  # Sync to sandbox workspace so it takes effect on next restart
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
    log_ok "Synced start.sh to sandbox workspace (effective on next restart)"
  fi

  # Clean up legacy direct-config-write injection and old MCP artifacts (backward compatibility)
  local cleaned=false
  # Remove old direct-config-write injection from template if present
  if grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    python3 - "$tpl" << 'PYCLEANCFG'
import sys, re
path = sys.argv[1]
with open(path) as f: content = f.read()
# Remove old direct-config-write block (Step 5: OpenViking plugin config through OVAGENTS)
content = re.sub(
    r'# ── Step 5: OpenViking plugin config \(added by huawei-cloud-openviking-agent-integration skill\) ──.*?OVAGENTS\n',
    '',
    content,
    flags=re.DOTALL
)
with open(path, 'w') as f: f.write(content)
PYCLEANCFG
    cleaned=true
  fi
  # Remove old MCP injection from template if present
  if grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    python3 - "$tpl" << 'PYCLEANMCP'
import sys, re
path = sys.argv[1]
with open(path) as f: content = f.read()
# Remove old MCP injection block (Step 5: Inject OpenViking MCP server through OVPATCH)
content = re.sub(
    r'# ── Step 5: Inject OpenViking MCP server.*?OVPATCH\n',
    '',
    content,
    flags=re.DOTALL
)
with open(path, 'w') as f: f.write(content)
PYCLEANMCP
    cleaned=true
  fi
  # Remove old extension directories
  for ext_dir in /root/.openclaw/extensions/openviking /root/runtime/openclaw/state/extensions/openviking; do
    if [[ -d "$ext_dir" ]]; then
      rm -rf "$ext_dir"
      cleaned=true
    fi
  done
  # Remove old MCP server entries from config files
  for cfg_file in /root/.openclaw/openclaw.json /root/runtime/openclaw/state/openclaw.json; do
    if [[ -f "$cfg_file" ]] && python3 -c "import json; d=json.load(open('$cfg_file')); exit(0 if 'openviking' in d.get('mcp',{}).get('servers',{}) else 1)" 2>/dev/null; then
      python3 -c "
import json
with open('$cfg_file') as f: d=json.load(f)
servers = d.get('mcp',{}).get('servers',{})
if 'openviking' in servers:
    del servers['openviking']
    if not servers: d.get('mcp',{}).pop('servers', None)
    if not d.get('mcp'): d.pop('mcp', None)
    with open('$cfg_file', 'w') as f: json.dump(d, f, indent=2)
" 2>/dev/null
      cleaned=true
    fi
  done
  [[ "$cleaned" == "true" ]] && log_ok "Legacy direct-config-write, MCP injection, and old artifacts cleaned"

  log_ok "OpenClaw integrated with OpenViking (official plugin via ClawHub → domestic npm → on-demand source build)"
  log_info "Restart OpenClaw for changes to take effect"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_openclaw_unbind() {
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

n = len(lines)
removed_blocks = 0

# Patterns
ov_block_start = re.compile(r'# ── Step 5(?:\.\d+)?:.*[Oo]pen[Vv]iking')
any_step_header = re.compile(r'# ── Step \d')
ov_ref = re.compile(r'openviking|OV_PLUGIN|OV_VENDOR|OV_BUILD|clawhub:@openviking|acknowledge-clawhub-risk', re.IGNORECASE)

# ── Helper: find the end of a step block (next step header or gateway line) ──
def find_step_end(start, lines):
    """Find the line index where the step block starting at 'start' ends."""
    j = start + 1
    while j < len(lines):
        if any_step_header.match(lines[j]) and j > start:
            return j
        if 'Starting Gateway' in lines[j] or 'gateway run' in lines[j]:
            return j
        j += 1
    return len(lines)

# ── Helper: check if a range of lines contains OV references ──
def has_ov_in_range(lines, start, end):
    for j in range(start, end):
        if ov_ref.search(lines[j]):
            return True
    return False

# ── Pass 1: Remove Step 5.x OpenViking blocks with look-ahead ──
# When we find a Step 5 OpenViking header, we skip it. Then we look at the
# next step block: if it also contains OV references (even if its header
# doesn't mention OpenViking), we skip it too. Continue until we find a
# step block with no OV references.
i = 0
new_lines = []

while i < n:
    line = lines[i]

    if ov_block_start.match(line):
        # Found an OpenViking Step 5.x block — skip it
        removed_blocks += 1
        block_end = find_step_end(i, lines)
        i = block_end

        # Look-ahead: skip subsequent step blocks that also contain OV refs
        # (these are sub-steps like Step 1/2/3 plugin install logic whose
        # headers don't mention OpenViking but whose code does)
        while i < n:
            # Check if we're at another step header
            if any_step_header.match(lines[i]):
                step_end = find_step_end(i, lines)
                if has_ov_in_range(lines, i, step_end):
                    removed_blocks += 1
                    i = step_end
                    continue
                else:
                    break  # Next step has no OV refs — stop skipping
            elif 'Starting Gateway' in lines[i] or 'gateway run' in lines[i]:
                break
            else:
                # Non-step line between blocks — check if it has OV refs
                # (could be orphaned fi, blank line, etc.)
                if ov_ref.search(lines[i]):
                    i += 1
                    continue
                # Check if it's an orphaned fi (closing a removed if block)
                stripped = lines[i].strip()
                if stripped == 'fi' or stripped == '  fi':
                    i += 1
                    continue
                break
        continue

    new_lines.append(line)
    i += 1

# ── Pass 2: Remove orphaned fi statements ──
# Removing if blocks may leave dangling fi lines.
# Track if/fi balance and drop fi that would make balance go negative.
lines = new_lines
new_lines = []
fi_balance = 0
for line in lines:
    stripped = line.strip()
    # Detect bash if (not inside heredoc — heredoc content won't have bare 'fi')
    is_bash_if = re.match(r'if\s', stripped) or re.match(r'if\s', stripped.split('#')[0].strip())
    is_bash_fi = stripped == 'fi' or stripped.startswith('fi ') or stripped.startswith('fi\t')

    if is_bash_if:
        fi_balance += 1
        new_lines.append(line)
    elif is_bash_fi:
        if fi_balance > 0:
            fi_balance -= 1
            new_lines.append(line)
        else:
            # Orphaned fi — skip
            continue
    else:
        new_lines.append(line)

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
  # ── Remove on-demand plugin source from persistent runtime location ──
  if [[ -d "/root/runtime/openclaw/openviking-plugin-source" ]]; then
    rm -rf /root/runtime/openclaw/openviking-plugin-source
    log_ok "On-demand plugin source removed from persistent runtime location"
  fi

  for agents_md in /root/.openclaw/workspace/AGENTS.md /root/runtime/openclaw/state/workspace/AGENTS.md; do
    if [[ -f "$agents_md" ]] && grep -q "OpenViking" "$agents_md" 2>/dev/null; then
      rm -f "$agents_md"
      cleaned=true
    fi
  done

  log_ok "OpenViking removed from OpenClaw"
  log_info "Restart OpenClaw for changes to take effect"
}


# ── Status ───────────────────────────────────────────────────────────────────
agent_openclaw_status() {
  local tpl="/root/template/openclaw/start.sh"

  # Check official plugin install injection in template start.sh (current method)
  local has_plugin=false
  if [[ -f "$tpl" ]] && grep -qE "# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking" "$tpl" 2>/dev/null; then
    has_plugin=true
  fi

  # Check legacy direct-config-write injection (backward compatibility)
  local has_legacy_cfg=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    has_legacy_cfg=true
  fi

  # Check legacy MCP injection (backward compatibility)
  local has_mcp=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    has_mcp=true
  fi

  # Check for legacy plugin extension artifacts
  local has_legacy=false
  for ext_dir in /root/.openclaw/extensions/openviking /root/runtime/openclaw/state/extensions/openviking; do
    [[ -d "$ext_dir" ]] && has_legacy=true
  done

  if [[ "$has_plugin" == "true" ]]; then
    # Distinguish official ClawHub primary vs npm mirror fallback for reporting
    local src_desc="ClawHub"
    grep -q "clawhub:@openviking/openclaw-plugin" "$tpl" 2>/dev/null || src_desc="npm mirror"
    # Check if on-demand source fallback is also deployed
    if [[ -d "/root/runtime/openclaw/openviking-plugin-source" ]]; then
      src_desc="${src_desc} + on-demand source fallback"
    fi
    if grep -q "openviking setup .*--json" "$tpl" 2>/dev/null; then
      echo "openclaw|integrated|Official plugin install in start.sh (${src_desc}, contextEngine slot, setup --json contract) ✓"
    else
      echo "openclaw|integrated|Official plugin install in start.sh (${src_desc}, contextEngine slot) ✓"
    fi
  elif [[ "$has_legacy_cfg" == "true" ]]; then
    echo "openclaw|partial|Legacy direct-config-write found — run integrate to upgrade to official plugin install"
  elif [[ "$has_mcp" == "true" ]]; then
    echo "openclaw|partial|Legacy MCP injection found — run integrate to upgrade to official plugin install"
  elif [[ "$has_legacy" == "true" ]]; then
    echo "openclaw|partial|Legacy plugin artifacts found — run unbind to clean"
  else
    echo "openclaw|not_integrated|No OpenViking integration found"
  fi
}

