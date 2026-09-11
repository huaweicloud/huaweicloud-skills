#!/bin/bash
# agents/openclaw.sh — OpenClaw agent subclass (ClawHub plugin + contextEngine)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_openclaw_register() {
  agent::set_meta name "openclaw"
  agent::set_meta display_name "OpenClaw"
  agent::set_meta sandbox_pattern "openclaw-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/openclaw/start.sh"
  agent::set_meta mechanism "ClawHub plugin + contextEngine"
  registry_add "openclaw"
}

agent_openclaw_integrate() {
  # OpenClaw runs in bwrap; config is inside sandbox. Inject plugin install into template start.sh.
  # Official: plugins install clawhub:@openviking/openclaw-plugin → openviking setup --json → gateway restart.
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "OpenClaw template start.sh not found: $tpl"; return 1; }

  local ov_runtime_src="$OV_RUNTIME_DIR/openclaw/openviking-plugin-source"
  # Install plugin source — npm first, fall back to GitHub download
  local _ov_npm_ok=0
  if [[ "${DRY_RUN:-false}" != "true" ]]; then
    local _npm_reg; _npm_reg=$(ov_first_npm_registry)
    log_info "Trying npm install @openviking/openclaw-plugin (online, $_npm_reg)..."
    mkdir -p /tmp/openviking
    local _npm_stage; _npm_stage=$(mktemp -d /tmp/openviking/ov-npm.XXXXXX) || { log_warn "mktemp failed, falling back to GitHub"; _npm_stage=""; }
    cat > "$_npm_stage/package.json" << 'OVPKGEOF'
{
  "dependencies": {
    "@openviking/openclaw-plugin": "latest"
  }
}
OVPKGEOF
    if [[ -n "$_npm_stage" ]] && \
       (cd "$_npm_stage" && "$OV_NPM" install \
           --registry="$_npm_reg" --no-audit --no-fund 2>&1 | tail -5) && \
       [[ -d "$_npm_stage/node_modules/@openviking/openclaw-plugin" ]]; then
      rm -rf "$ov_runtime_src"
      cp -a "$_npm_stage/node_modules/@openviking/openclaw-plugin" "$ov_runtime_src"
      log_ok "openclaw-plugin installed from npm (online) -> $ov_runtime_src"
      touch "$ov_runtime_src"
      _ov_npm_ok=1
    else
      log_warn "npm install failed — falling back to GitHub source download"
    fi
    [[ -n "$_npm_stage" ]] && rm -rf "$_npm_stage"
  fi
  if [[ "$_ov_npm_ok" -eq 0 ]]; then
    ov_plugin_provision "openclaw-plugin" "$ov_runtime_src" || return 1
    [[ "${DRY_RUN:-false}" == "true" ]] || log_ok "openclaw-plugin source installed on demand at $ov_runtime_src"
  fi
  # ── Pre-build plugin at integrate time for fast runtime recovery ──
  # npm package ships with dist/ pre-compiled; we only install runtime deps (no tsc needed).
  # Stores ready-to-use result (dist/ + node_modules/) in persistent runtime cache.
  # At start.sh time, Tier-0 fast path just plugins install (no npm/tsc needed).
  local ov_prebuilt="$OV_RUNTIME_DIR/openclaw/openviking-plugin-built"
  if [[ "${DRY_RUN:-false}" != "true" && -d "$ov_runtime_src" ]]; then
    log_info "Pre-building openclaw-plugin (npm install for runtime deps) for fast runtime recovery..."
    local _pb_stage; _pb_stage=$(mktemp -d /tmp/openviking/ov-prebuild.XXXXXX) || _pb_stage=""
    if [[ -n "$_pb_stage" ]]; then
      cp -a "$ov_runtime_src/." "$_pb_stage/"
      local _npm_reg; _npm_reg=$(ov_first_npm_registry)
      export NPM_CONFIG_REGISTRY="$_npm_reg"
      if (cd "$_pb_stage" && "$OV_NPM" install --production --no-audit --no-fund 2>&1 | tail -5) && \
         [[ -d "$_pb_stage/dist" ]]; then
        rm -rf "$ov_prebuilt"
        cp -a "$_pb_stage" "$ov_prebuilt"
        touch "$ov_prebuilt"
        log_ok "Pre-built plugin cached at $ov_prebuilt (dist/ + node_modules/ ready)"
      else
        log_warn "Pre-build failed — runtime will fall back to source build (slower)"
      fi
      unset NPM_CONFIG_REGISTRY
      rm -rf "$_pb_stage"
    fi
  fi
  # Check if already integrated
  if grep -q "OpenViking plugin install\|ov-openclaw-init.sh" "$tpl" 2>/dev/null; then
    log_ok "OpenClaw already integrated (official plugin install in start.sh)"
    # Verify live sandbox has endpoint config
    local gw_pid=""
    gw_pid=$(pgrep -f "openclaw-gateway" 2>/dev/null | head -1)
    if [ -n "$gw_pid" ] && [ -f "/proc/$gw_pid/environ" ]; then
      if tr '\0' '\n' < "/proc/$gw_pid/environ" 2>/dev/null | grep -q "OPENVIKING_BASE_URL=http"; then
        log_ok "OpenClaw live sandbox has OpenViking endpoint configured"
      else
        log_warn "Template has OpenViking injection, but live sandbox is MISSING endpoint config"
        log_warn "Fix: restart sandbox via job-env-manager API (stop + start re-runs start.sh)"
      fi
    else
      log_warn "OpenClaw gateway process not found — sandbox may not be running"
    fi
    return 0
  fi
  # Slot-replacement approval: check if another plugin owns contextEngine
  local force_slot=0
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    if [[ -f "$cfg_file" ]] && "$OV_PY" -c "
import json,sys
try:
    d=json.load(open('$cfg_file'))
    owner=d.get('plugins',{}).get('slots',{}).get('contextEngine','')
    print(owner)
except Exception: print('')
" 2>/dev/null | grep -qv '^$' && ! "$OV_PY" -c "
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
  local allow_offline=1   # dev-mode local server; safe default
  require_confirmation "Integrate OpenViking (Official ClawHub Plugin)" "openclaw" "Install @openviking/openclaw-plugin (ClawHub → domestic npm mirror → on-demand source build fallback) + openviking setup --json into template start.sh (contextEngine slot, auto-recall + auto-capture)" || return 1
  if dry_run_msg "Would add OpenViking plugin install to $tpl"; then return 0; fi
  backup_file "$tpl"
  # Insert official plugin install block before the gateway start step
  "$OV_PY" - "$tpl" "$OV_ENDPOINT" "$force_slot" "$allow_offline" "$OV_NPM_REGISTRY_DEFAULT" "$OV_SHARED_DIR" "$OV_RUNTIME_DIR" "$OV_TEMPLATE_DIR" << 'PYINJECT'
import sys, re
path, endpoint, force_slot, allow_offline, npm_registry, shared_dir, runtime_dir, template_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]
with open(path) as f: content = f.read()
if "ov-openclaw-init.sh" in content or "OpenViking plugin install" in content:
    print("already")
    sys.exit(0)
block = """# ── OpenViking plugin install (official ClawHub, added by huawei-cloud-openviking-agent-integration skill) ──
# Cache-first: check if plugin already installed; if not, install from runtime cache (no network),
# then ClawHub/npm on first integrate or cache miss. Survives undeploy+deploy via __OV_RUNTIME_DIR__/.
echo "[openclaw] Provisioning OpenViking plugin (cache-first)..."
OV_PLUGIN_INSTALLED=0
OV_VENDOR_SRC="__OV_RUNTIME_DIR__/openclaw/openviking-plugin-source"
if "$NODE" "$CLI" plugins list 2>/dev/null | grep -q "openviking"; then
  OV_PLUGIN_INSTALLED=1
  echo "[openclaw] Plugin already installed (cache hit)."
fi
OV_PREBUILT="__OV_RUNTIME_DIR__/openclaw/openviking-plugin-built"
if [[ "$OV_PLUGIN_INSTALLED" = "0" && -d "$OV_PREBUILT" && -d "$OV_PREBUILT/dist" ]]; then
  echo "[openclaw] Installing from pre-built cache (Tier-0 fast path)..."
  if "$NODE" "$CLI" plugins install --force --accept-capabilities "$OV_PREBUILT" 2>&1; then
    OV_PLUGIN_INSTALLED=1
    echo "[openclaw] Installed from pre-built cache (no build needed)."
  else
    echo "[openclaw] WARNING: pre-built install failed — falling back to source build"
  fi
fi
if [[ "$OV_PLUGIN_INSTALLED" = "0" && -d "$OV_VENDOR_SRC" ]]; then
  echo "[openclaw] Installing from runtime source cache (Tier-1)..."
  OV_BUILD_DIR=$(mktemp -d /tmp/openclaw-ov-build.XXXXXX)
  cp -a "$OV_VENDOR_SRC/." "$OV_BUILD_DIR/"
  export NPM_CONFIG_REGISTRY=__OV_NPM_REGISTRY__
  # npm package ships with dist/ pre-compiled; only install runtime deps
  if [[ -d "$OV_BUILD_DIR/dist" ]]; then
    (cd "$OV_BUILD_DIR" && npm install --production --no-audit --no-fund 2>&1 | tail -3) || true
    if "$NODE" "$CLI" plugins install --force --accept-capabilities "$OV_BUILD_DIR" 2>&1; then
      OV_PLUGIN_INSTALLED=1
      echo "[openclaw] Installed from runtime source cache (dist/ pre-compiled)."
    else
      echo "[openclaw] WARNING: local install failed — trying online"
    fi
  else
    echo "[openclaw] WARNING: no dist/ in source cache — trying online"
  fi
  unset NPM_CONFIG_REGISTRY
  rm -rf "$OV_BUILD_DIR"
fi
if [[ "$OV_PLUGIN_INSTALLED" = "0" ]]; then
  echo "[openclaw] Cache miss — trying online (ClawHub → npm mirrors)..."
  if "$NODE" "$CLI" plugins install --accept-capabilities clawhub:@openviking/openclaw-plugin 2>&1; then
    OV_PLUGIN_INSTALLED=1
    echo "[openclaw] Installed from ClawHub"
  else
    echo "[openclaw] WARNING: ClawHub failed — trying npm mirror"
    export NPM_CONFIG_REGISTRY=__OV_NPM_REGISTRY__
    if "$NODE" "$CLI" plugins install --force --accept-capabilities @openviking/openclaw-plugin 2>&1; then
      OV_PLUGIN_INSTALLED=1
      echo "[openclaw] Installed (npm Huawei Cloud mirror)"
    else
      export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com/
      if "$NODE" "$CLI" plugins install --force --accept-capabilities @openviking/openclaw-plugin 2>&1; then
        OV_PLUGIN_INSTALLED=1
        echo "[openclaw] Installed (npm npmmirror)"
      else
        echo "[openclaw] WARNING: all online sources failed"
      fi
    fi
    unset NPM_CONFIG_REGISTRY
  fi
fi
# Fix plugin permissions (gateway blocks world-writable paths)
if [[ "$OV_PLUGIN_INSTALLED" = "1" ]]; then
  for _ext_dir in "$HOME/.openclaw/extensions/openviking" "${OPENCLAW_STATE_DIR:-/tmp/.openclaw}/extensions/openviking"; do
    if [[ -d "$_ext_dir" ]]; then
      chmod -R go-w "$_ext_dir" 2>/dev/null || true
      echo "[openclaw] Fixed permissions: $_ext_dir"
    fi
  done
fi
# Configure OpenViking endpoint via official JSON contract
export OPENVIKING_BASE_URL="__ENDPOINT__"
export OPENVIKING_ENDPOINT="__ENDPOINT__"
if [ "$OV_PLUGIN_INSTALLED" = "1" ]; then
  OV_SETUP_ARGS=(--base-url "__ENDPOINT__" --json)
  [ -n "${OPENVIKING_API_KEY:-}" ] && OV_SETUP_ARGS+=(--api-key "$OPENVIKING_API_KEY")
  [ "${OV_FORCE_SLOT:-OV_FORCE_SLOT_DEFAULT}" = "1" ] && OV_SETUP_ARGS+=(--force-slot)
  [ "${OV_ALLOW_OFFLINE:-OV_ALLOW_OFFLINE_DEFAULT}" = "1" ] && OV_SETUP_ARGS+=(--allow-offline)

  OV_SETUP_OUT=$("$NODE" "$CLI" openviking setup "${OV_SETUP_ARGS[@]}" 2>/dev/null || true)
  if echo "$OV_SETUP_OUT" | grep -q '"success":true'; then
    echo "[openclaw] Configured via setup (JSON): __ENDPOINT__"
  elif echo "$OV_SETUP_OUT" | grep -q '"action":"slot_blocked"'; then
    if [ "${OV_FORCE_SLOT:-OV_FORCE_SLOT_DEFAULT}" = "1" ]; then
      echo "[openclaw] WARNING: slot blocked; --force-slot retry already attempted"
    else
      echo "[openclaw] WARNING: contextEngine slot owned by another plugin; use --force-slot to override"
    fi
  elif echo "$OV_SETUP_OUT" | grep -q '"action":"error"'; then
    echo "[openclaw] ERROR: setup validation failed: $OV_SETUP_OUT"
  elif echo "$OV_SETUP_OUT" | grep -q '"health":{"ok":false'; then
    if [ "${OV_ALLOW_OFFLINE:-OV_ALLOW_OFFLINE_DEFAULT}" != "1" ]; then
      echo "[openclaw] WARNING: server unreachable and --allow-offline not approved"
    fi
  elif echo "$OV_SETUP_OUT" | grep -q 'root_key'; then
    echo "[openclaw] ERROR: setup requires --account-id/--user-id for root API keys"
  else
    echo "[openclaw] WARNING: unexpected setup output: $OV_SETUP_OUT"
  fi
else
  echo "[openclaw] Plugin not installed — skipping setup"
fi
# Enable OpenViking plugin (sets contextEngine slot)
if [ "$OV_PLUGIN_INSTALLED" = "1" ]; then
  "$NODE" "$CLI" plugins enable --accept-capabilities openviking 2>/dev/null || true
  "$NODE" "$CLI" config set 'plugins.allow' '["openviking"]' 2>/dev/null || true
  "$NODE" "$CLI" config set "plugins.entries.openviking.config.recallMaxInjectedChars" 16000 2>/dev/null || true
  "$NODE" "$CLI" config set "plugins.entries.openviking.config.recallLimit" 10 2>/dev/null || true
  # ── Disable local memory to prevent recall quality degradation ──
  # OpenViking contextEngine handles auto-recall + auto-capture;
  # local session-memory hook and memory_search tool are redundant and degrade recall quality.
  "$NODE" "$CLI" config set "hooks.internal.entries.session-memory.enabled" false 2>/dev/null || true
  # Deny local memory_search tool — use OpenViking MCP tools (search/recall/remember) instead
  "$NODE" "$CLI" config set "tools.deny" '["memory_search"]' 2>/dev/null || true
  echo "[openclaw] Disabled session-memory hook and local memory_search (OpenViking handles recall)"
  echo "[openclaw] Enabled OpenViking plugin (contextEngine slot)"
fi
# Append OpenViking instructions to AGENTS.md
mkdir -p "$OPENCLAW_STATE_DIR/workspace"
OV_AGENTS="$OPENCLAW_STATE_DIR/workspace/AGENTS.md"
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
  echo "[openclaw] Instructions appended to AGENTS.md"
else
  echo "[openclaw] Instructions already in AGENTS.md"
fi
# ── Verification: confirm plugin is actually installed ──
if [[ "$OV_PLUGIN_INSTALLED" = "1" ]]; then
  if ! "$NODE" "$CLI" plugins list 2>/dev/null | grep -q "openviking"; then
    echo "[openclaw] ERROR: Plugin install reported success but plugins list does not contain openviking"
    OV_PLUGIN_INSTALLED=0
  fi
fi
if [[ "$OV_PLUGIN_INSTALLED" = "0" ]]; then
  echo "[openclaw] ERROR: OpenViking plugin installation FAILED — auto-recall and memory tools will not be available"
fi
"""
block = block.replace('__ENDPOINT__', endpoint)
block = block.replace('OV_FORCE_SLOT_DEFAULT', str(force_slot))
block = block.replace('OV_ALLOW_OFFLINE_DEFAULT', str(allow_offline))
block = block.replace('__OV_NPM_REGISTRY__', npm_registry)
block = block.replace('__OV_RUNTIME_DIR__', runtime_dir)
import os
init_path = f"{shared_dir}/ov-openclaw-init.sh"
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for OpenClaw ──\n")
    f.write(f"# Sourced by {template_dir}/openclaw/start.sh (single source line).\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block)
os.chmod(init_path, 0o755)
# Change OPENCLAW_STATE_DIR to persistent path so plugin survives sandbox restarts
# Override OPENCLAW_STATE_DIR to persistent path (env.yaml sets /tmp/.openclaw which is ephemeral)
content = re.sub(
    r'# ── State dir:.*──\nexport OPENCLAW_STATE_DIR=.*',
    '# ── State dir: persistent (survives sandbox restarts) ──\n# Override env.yaml default (/tmp/.openclaw) so plugin survives restarts.\nexport OPENCLAW_STATE_DIR="/root/runtime/openclaw/state"',
    content
)
# Also fix env.yaml so CLI commands in terminal use the same persistent path
env_yaml = f"{template_dir}/openclaw/env.yaml"
if os.path.exists(env_yaml):
    with open(env_yaml) as ef:
        ey = ef.read()
    if '/tmp/.openclaw' in ey:
        ey = ey.replace('OPENCLAW_STATE_DIR: "/tmp/.openclaw"', 'OPENCLAW_STATE_DIR: "/root/runtime/openclaw/state"')
        with open(env_yaml, 'w') as ef:
            ef.write(ey)
        print("env.yaml fixed")
    else:
        print("env.yaml already fixed")
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\n# OpenViking plugin install is best-effort: if it fails, gateway should still start.\nset +e\nsource {shared_dir}/ov-openclaw-init.sh\nset -e\n# ── End OpenViking integration ──\n\n"

gateway_marker = "# ── Step 5: Start the Gateway"
if gateway_marker in content:
    content = content.replace(gateway_marker, source_block + gateway_marker)
else:
    content = re.sub(r'(# ── Step \d+: Start the Gateway)', source_block + r'\1', content)
with open(path, 'w') as f: f.write(content)
print("injected")
PYINJECT
  log_ok "OpenClaw template updated with official OpenViking plugin install"
  # Sync to sandbox workspace
  local sandbox_dir=""
  for d in "$OV_SANDBOX_DIR"/openclaw-*/; do
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
  # Clean up legacy direct-config-write injection and old MCP artifacts
  local cleaned=false
  if grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    "$OV_PY" - "$tpl" << 'PYCLEANCFG'
import sys, re
path = sys.argv[1]
with open(path) as f: content = f.read()
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
  if grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    "$OV_PY" - "$tpl" << 'PYCLEANMCP'
import sys, re
path = sys.argv[1]
with open(path) as f: content = f.read()
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
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    if [[ -d "$ext_dir" ]]; then
      rm -rf "$ext_dir"
      cleaned=true
    fi
  done
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    if [[ -f "$cfg_file" ]] && "$OV_PY" -c "import json; d=json.load(open('$cfg_file')); exit(0 if 'openviking' in d.get('mcp',{}).get('servers',{}) else 1)" 2>/dev/null; then
      "$OV_PY" -c "
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
  ov_log_info "重启 OpenClaw 以使更改生效" "Restart OpenClaw for changes to take effect"
}

agent_openclaw_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  # Detect OpenViking injection in template (all known formats)
  if [[ -f "$tpl" ]] && grep -qE '# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking|ov-openclaw-init\.sh' "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  fi
  local has_cfg=false
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    if [[ -f "$cfg_file" ]] && "$OV_PY" -c "import json; d=json.load(open('$cfg_file')); exit(0 if d.get('plugins',{}).get('entries',{}).get('openviking') or d.get('plugins',{}).get('slots',{}).get('contextEngine')=='openviking' or 'openviking' in d.get('mcp',{}).get('servers',{}) else 1)" 2>/dev/null; then
      has_cfg=true
    fi
  done
  local has_ext=false
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    [[ -d "$ext_dir" ]] && has_ext=true
  done
  if [[ "$tpl_has_ov" == "false" && "$has_cfg" == "false" && "$has_ext" == "false" ]]; then
    log_ok "OpenClaw not integrated (nothing to remove)"; return 0
  fi
  require_confirmation "UNBIND OpenViking" "openclaw" "Remove OpenViking plugin install from template start.sh and clean up config files" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking plugin config and legacy artifacts"; then return 0; fi
  # Remove ALL OpenViking-related Step 5.x blocks from template start.sh
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    "$OV_PY" - "$tpl" "$OV_SHARED_DIR" << 'PYUNBIND'
import sys, re
path = sys.argv[1]
shared_dir = sys.argv[2]
with open(path) as f:
    content = f.read()
# First try new-style: 3-line source block
new_pattern = rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\nsource {re.escape(shared_dir)}/ov-openclaw-init\.sh\n# ── End OpenViking integration ──\n\n?'
new_content = re.sub(new_pattern, '', content)
if new_content != content:
    with open(path, 'w') as f:
        f.write(new_content)
    print("removed 1 OpenViking block(s) [new-style source line]")
    sys.exit(0)
# Fall back to old-style: full inline Step 5.x blocks
lines = content.splitlines(keepends=True)
n = len(lines)
removed_blocks = 0
ov_block_start = re.compile(r'# ── Step 5(?:\.\d+)?:.*[Oo]pen[Vv]iking')
any_step_header = re.compile(r'# ── Step \d')
ov_ref = re.compile(r'openviking|OV_PLUGIN|OV_VENDOR|OV_BUILD|clawhub:@openviking|accept-capabilities|acknowledge-clawhub-risk', re.IGNORECASE)
def find_step_end(start, lines):
    j = start + 1
    while j < len(lines):
        if any_step_header.match(lines[j]) and j > start:
            return j
        if 'Starting Gateway' in lines[j] or 'gateway run' in lines[j]:
            return j
        j += 1
    return len(lines)
def has_ov_in_range(lines, start, end):
    for j in range(start, end):
        if ov_ref.search(lines[j]):
            return True
    return False
# Pass 1: Remove Step 5.x OpenViking blocks with look-ahead
i = 0
new_lines = []
while i < n:
    line = lines[i]
    if ov_block_start.match(line):
        removed_blocks += 1
        block_end = find_step_end(i, lines)
        i = block_end
        while i < n:
            if any_step_header.match(lines[i]):
                step_end = find_step_end(i, lines)
                if has_ov_in_range(lines, i, step_end):
                    removed_blocks += 1
                    i = step_end
                    continue
                else:
                    break
            elif 'Starting Gateway' in lines[i] or 'gateway run' in lines[i]:
                break
            else:
                if ov_ref.search(lines[i]):
                    i += 1
                    continue
                stripped = lines[i].strip()
                if stripped == 'fi' or stripped == '  fi':
                    i += 1
                    continue
                break
        continue
    new_lines.append(line)
    i += 1
# Pass 2: Remove orphaned fi statements
lines = new_lines
new_lines = []
fi_balance = 0
for line in lines:
    stripped = line.strip()
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
            continue
    else:
        new_lines.append(line)
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
    rm -f "$OV_SHARED_DIR/ov-openclaw-init.sh" && log_ok "Removed standalone ov-openclaw-init.sh"
    # Post-removal verification
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
    for d in "$OV_SANDBOX_DIR"/openclaw-*/; do
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
  # Clean up config files (plugin entries, MCP servers, tool policy)
  local cleaned=false
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    if [[ -d "$ext_dir" ]]; then
      rm -rf "$ext_dir"
      cleaned=true
    fi
  done
  for cfg_file in "$OV_HOME/.openclaw/openclaw.json" "$OV_RUNTIME_DIR/openclaw/state/openclaw.json"; do
    [[ -f "$cfg_file" ]] || continue
    "$OV_PY" -c "
import json, sys
path = sys.argv[1]
with open(path) as f: d=json.load(f)
changed = False
servers = d.get('mcp',{}).get('servers',{})
if 'openviking' in servers:
    del servers['openviking']
    if not servers: d.get('mcp',{}).pop('servers', None)
    if not d.get('mcp'): d.pop('mcp', None)
    changed = True
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
  # Remove on-demand plugin source + AGENTS.md
  if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-source" ]]; then
    rm -rf "$OV_RUNTIME_DIR/openclaw/openviking-plugin-source"
    log_ok "On-demand plugin source removed from persistent runtime location"
  fi
  if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-built" ]]; then
    rm -rf "$OV_RUNTIME_DIR/openclaw/openviking-plugin-built"
    log_ok "Pre-built plugin cache removed from persistent runtime location"
  fi
  # Revert OPENCLAW_STATE_DIR to default /tmp
  if grep -q 'OPENCLAW_STATE_DIR.*/root/runtime/openclaw/state' "$tpl" 2>/dev/null; then
    sed -i 's|OPENCLAW_STATE_DIR:-/root/runtime/openclaw/state|OPENCLAW_STATE_DIR:-/tmp/.openclaw|' "$tpl"
    sed -i 's|# ── State dir: persistent (survives sandbox restarts) ──|# ── State dir: inside sandbox, not mounted outside ──|' "$tpl"
    log_ok "Reverted OPENCLAW_STATE_DIR to default /tmp/.openclaw"
  fi
  # Revert env.yaml
  local env_yaml="$OV_TEMPLATE_DIR/openclaw/env.yaml"
  if [[ -f "$env_yaml" ]] && grep -q 'OPENCLAW_STATE_DIR.*/root/runtime/openclaw/state' "$env_yaml" 2>/dev/null; then
    sed -i 's|OPENCLAW_STATE_DIR: "/root/runtime/openclaw/state"|OPENCLAW_STATE_DIR: "/tmp/.openclaw"|' "$env_yaml"
    log_ok "Reverted env.yaml OPENCLAW_STATE_DIR to /tmp/.openclaw"
  fi
  # Clean up persistent state dir
  if [[ -d "$OV_RUNTIME_DIR/openclaw/state" ]]; then
    rm -rf "$OV_RUNTIME_DIR/openclaw/state"
    log_ok "Persistent state dir removed"
  fi
  for agents_md in "$OV_HOME/.openclaw/workspace/AGENTS.md" "$OV_RUNTIME_DIR/openclaw/state/workspace/AGENTS.md"; do
    if [[ -f "$agents_md" ]] && grep -q "OpenViking" "$agents_md" 2>/dev/null; then
      rm -f "$agents_md"
      cleaned=true
    fi
  done
  log_ok "OpenViking removed from OpenClaw"
  ov_log_info "重启 OpenClaw 以使更改生效" "Restart OpenClaw for changes to take effect"
}

agent_openclaw_status() {
  local tpl="${AGENT_META[template_path]}"

  local has_plugin=false
  if [[ -f "$tpl" ]] && grep -qE "# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking|ov-openclaw-init\.sh" "$tpl" 2>/dev/null; then
    has_plugin=true
  fi
  local has_legacy_cfg=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    has_legacy_cfg=true
  fi
  local has_mcp=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    has_mcp=true
  fi
  local has_legacy=false
  for ext_dir in "$OV_HOME/.openclaw/extensions/openviking" "$OV_RUNTIME_DIR/openclaw/state/extensions/openviking"; do
    [[ -d "$ext_dir" ]] && has_legacy=true
  done
  if [[ "$has_plugin" == "true" ]]; then
    local src_desc="ClawHub"
    grep -q "clawhub:@openviking/openclaw-plugin" "$tpl" 2>/dev/null || src_desc="npm mirror"
    if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-source" ]]; then
      src_desc="${src_desc} + on-demand source fallback"
    fi
    if [[ -d "$OV_RUNTIME_DIR/openclaw/openviking-plugin-built" ]]; then
      src_desc="${src_desc} + pre-built cache (fast recovery)"
    fi
    if grep -q "openviking setup .*--json" "$tpl" 2>/dev/null; then
      ov_status "openclaw" "integrated" "Official plugin install in start.sh (${src_desc}, contextEngine slot, setup --json contract) ✓"
    else
      ov_status "openclaw" "integrated" "Official plugin install in start.sh (${src_desc}, contextEngine slot) ✓"
    fi
  elif [[ "$has_legacy_cfg" == "true" ]]; then
    ov_status "openclaw" "partial" "Legacy direct-config-write found — run integrate to upgrade to official plugin install"
  elif [[ "$has_mcp" == "true" ]]; then
    ov_status "openclaw" "partial" "Legacy MCP injection found — run integrate to upgrade to official plugin install"
  elif [[ "$has_legacy" == "true" ]]; then
    ov_status "openclaw" "partial" "Legacy plugin artifacts found — run unbind to clean"
  else
    ov_status "openclaw" "not_integrated" "No OpenViking integration found"
  fi
}
