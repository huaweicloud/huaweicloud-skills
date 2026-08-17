#!/bin/bash
# =============================================================================
# OpenViking Agent Integration Script
# Usage:
#   ./integrate.sh --agent <name> [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]
#   ./integrate.sh --all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]
# Agents: codearts, opencode, openclaw, hermes, jiuwenswarm, kimicode, deepseek-harness
# =============================================================================
set -euo pipefail
source "$(dirname "$0")/common.sh"

OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
OV_MCP_URL=""

# Shared function to create openviking-config.json in a sandbox
create_ov_config() {
  local conf_dir="$1/.config/opencode"
  mkdir -p "$conf_dir"
  if [[ ! -f "$conf_dir/openviking-config.json" ]]; then
    cat > "$conf_dir/openviking-config.json" <<'OVCONF'
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 15,
    "scoreThreshold": 0.05,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
OVCONF
  fi
}


OV_API_KEY="${OV_API_KEY:-}"
DRY_RUN=false
AUTO_YES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --all) ALL_AGENTS=true; shift ;;
    --endpoint) OV_ENDPOINT="$2"; shift 2 ;;
    --api-key) OV_API_KEY="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --yes|-y) AUTO_YES=true; shift ;;
    --help|-h) echo "Usage: $0 --agent <name>|--all [--endpoint URL] [--api-key KEY] [--dry-run] [--yes]"; echo "Agents: codearts, opencode, openclaw, hermes, jiuwenswarm, kimicode, deepseek-harness"; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

OV_MCP_URL="${OV_ENDPOINT}/mcp"

# ── CodeArts CLI ──────────────────────────────────────────────────────────────
integrate_codearts() {
  local sandbox; sandbox=$(find_sandbox "codearts")
  [[ -z "$sandbox" ]] && { log_error "CodeArts sandbox not found"; return 1; }
  local cf="${sandbox}/.codeartsdoer/codearts_cli.json"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }

  local _tpl="/root/template/codearts/start.sh"
  if check_json_mcp "$cf"; then
    if grep -q "OpenViking integration" "$_tpl" 2>/dev/null; then
      log_ok "CodeArts already integrated with OpenViking MCP (template + live)"
      return 0
    fi
    log_info "Live sandbox has MCP, but template missing injection — proceeding to template injection"
  fi

  require_confirmation "Integrate OpenViking MCP" "codearts" "Add mcp.openviking + 4-section prompt to codearts_cli.json" || return 1
  if dry_run_msg "Would add mcp.openviking + 4-section prompt to $cf"; then return 0; fi

  # ── 1. Inject into live sandbox config (immediate effect) ──
  backup_file "$cf"
  python3 -c "
import json
with open('$cf') as f: cfg=json.load(f)
cfg.setdefault('mcp',{})['openviking']={'type':'remote','url':'$OV_MCP_URL','enabled':True,'oauth':False,'timeout':30000}
json.dump(cfg, open('$cf','w'), indent=2)
"
  create_ov_config "$sandbox"
  log_ok "OpenViking MCP + config injected into live sandbox"

  # ── 2. Inject into template start.sh (persistent) ──
  local tpl="/root/template/codearts/start.sh"
  if [[ -f "$tpl" ]] && ! grep -q "$OV_MARKER" "$tpl" 2>/dev/null; then
    backup_file "$tpl"
    python3 - "$tpl" "$OV_MCP_URL" << 'CATPL'
import sys
path, url = sys.argv[1], sys.argv[2]
with open(path) as f: c = f.read()
inject_block = """
# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──
# MCP server + 4-section prompt (Auto-Recall + Proactive Search + Auto-Capture + Repo Context)
# + openviking-config.json with official-equivalent behavior knobs.
CODEARTS_CFG="$HOME/.codeartsdoer/codearts_cli.json"
if [ -f "$CODEARTS_CFG" ]; then
  python3 - "$CODEARTS_CFG" <<'OVINJECT'
import json, sys
path = sys.argv[1]
with open(path) as f: cfg = json.load(f)
changed = False
if "mcp" not in cfg or "openviking" not in cfg.get("mcp", {}):
    cfg.setdefault("mcp", {})["openviking"] = {
        "type": "remote",
        "url": "URL_PLACEHOLDER",
        "enabled": True,
        "oauth": False,
        "timeout": 30000
    }
    changed = True
prompt = '''You have OpenViking long-term memory integrated. Follow these protocols:

## Auto-Recall (at conversation start)
Before responding to the user's first message:
1. Call `recall` with the user's message as query to retrieve relevant context (limit=6, min_score=0.35).
2. If working in a code repository, call `search` with the repo name and file paths to find relevant past work.
3. Use retrieved context to inform responses. Do not mention the retrieval process to the user.

## Proactive Search (during tasks)
1. Call `search` to find relevant past knowledge, error solutions, and project decisions.
2. Call `find` for quick lookup without session context.
3. Use `read` with viking:// URIs to access stored reference materials.
4. Use `list` and `glob` to browse available memory when exploring.

## Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. Call `remember` to store: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Focus on durable facts, not the full conversation.
3. Use `add_resource` to index important local files or URLs for future reference.

## Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.

Do not wait to be asked — proactively use these tools for context-aware responses across sessions and projects.'''
agent_cfg = cfg.setdefault("agent", {})
build_cfg = agent_cfg.setdefault("build", {})
if build_cfg.get("prompt", "") != prompt:
    build_cfg["prompt"] = prompt
    changed = True
if changed:
    with open(path, "w") as f: json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("OpenViking MCP + 4-section prompt injected")
OVINJECT
fi

# openviking-config.json (mirrors official @openviking/opencode-plugin defaults)
OV_CONF_DIR="$HOME/.config/opencode"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 15,
    "scoreThreshold": 0.05,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
OVCONF
fi

"""
inject_block = inject_block.replace("URL_PLACEHOLDER", url)
c = c.replace("sleep infinity", inject_block + "\nsleep infinity")
with open(path, 'w') as f: f.write(c)
CATPL
    log_ok "CodeArts template updated with MCP + 4-section prompt + config"
  fi
  log_ok "CodeArts integrated with OpenViking MCP + 4-section prompt at $OV_MCP_URL"
  log_info "Restart CodeArts session for changes to take effect"
}

# ── OpenCode ──────────────────────────────────────────────────────────────────
integrate_opencode() {
  local tpl="/root/template/opencode/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "OpenCode template start.sh not found: $tpl"; return 1; }

  # Check if plugin is already installed in template
  if grep -q "OpenViking integration" "$tpl" 2>/dev/null && grep -q "opencode-plugin" "$tpl" 2>/dev/null; then
    log_ok "OpenCode already has OpenViking plugin (template-level)"
    return 0
  fi

  require_confirmation "Integrate OpenViking (official npm plugin)" "opencode" \
    "Install @openviking/opencode-plugin via npm (Huawei Cloud mirror) + pre-install plugin SDK + openviking-config.json to template start.sh (persistent)" \
    || return 1
  if dry_run_msg "Would install OpenViking plugin via npm to $tpl and live sandbox"; then return 0; fi

  local NPM_REGISTRY="https://mirrors.huaweicloud.com/repository/npm/"

  # ── 1. Install plugin into live sandbox (immediate effect) ──
  local sandbox; sandbox=$(find_sandbox "opencode")
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    local ov_npm_dir="${sandbox}/.config/opencode"

    # Create .npmrc with Huawei Cloud registry
    echo "registry=${NPM_REGISTRY}" > "${ov_npm_dir}/.npmrc"
    log_ok ".npmrc created (Huawei Cloud npm mirror)"

    # Pre-install plugin SDK via npm (avoids 45s blocking during OpenCode startup)
    if [[ ! -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
      log_info "Pre-installing @opencode-ai/plugin SDK (Huawei Cloud npm mirror)..."
      cat > "${ov_npm_dir}/package.json" <<'PKGEOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.8"
  }
}
PKGEOF
      (cd "$ov_npm_dir" && npm install --registry="${NPM_REGISTRY}" --no-audit --no-fund 2>&1 | tail -5)
      log_ok "Plugin SDK pre-installed in live sandbox"
    else
      log_ok "Plugin SDK already installed in live sandbox"
    fi

    # Register plugin in opencode.json
    local cf="${sandbox}/.config/opencode/opencode.json"
    backup_file "$cf"
    python3 - "$cf" <<'PYREG'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
plugins = cfg.setdefault("plugin", [])
if "@openviking/opencode-plugin" not in plugins:
    plugins.append("@openviking/opencode-plugin")
# Remove old MCP remote + prompt if present (cleanup from previous approach)
if "mcp" in cfg and "openviking" in cfg["mcp"]:
    del cfg["mcp"]["openviking"]
    if not cfg["mcp"]:
        del cfg["mcp"]
if "agent" in cfg and "build" in cfg["agent"] and "prompt" in cfg["agent"]["build"]:
    del cfg["agent"]["build"]["prompt"]
    if not cfg["agent"]["build"]:
        del cfg["agent"]["build"]
    if not cfg["agent"]:
        del cfg["agent"]
with open(path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
PYREG
    log_ok "Plugin registered in opencode.json (old MCP+prompt cleaned up)"

    # Create openviking-config.json in live sandbox
    create_ov_config "$sandbox"
  else
    log_info "No live OpenCode sandbox found; plugin will be installed on next start"
  fi


  # ── 1b. Update env.yaml: ensure npm/node accessible inside bwrap sandbox ──
  # The opencode sandbox's default PATH and readablePaths do not include /usr/local/nodejs.
  # Without this, npm is not found inside the bwrap, causing start.sh to fail (set -e).
  local env_yaml="/root/template/opencode/env.yaml"
  if [[ -f "$env_yaml" ]]; then
    backup_file "$env_yaml"
    python3 - "$env_yaml" <<'YAMLFIX'
import sys, re

path = sys.argv[1]
with open(path) as f:
    yaml = f.read()

changed = False

# Add /usr/local/nodejs to readablePaths if not present
if "/usr/local/nodejs" not in yaml:
    # Find readablePaths section and add the entry
    yaml = re.sub(
        r'(readablePaths:\n(?:\s+- \S+\n)*?)((?:\s*\S))',
        lambda m: m.group(1) + "    - /usr/local/nodejs\n" + m.group(2),
        yaml,
        count=1
    )
    changed = True

# Add PATH to extraEnv if not present
if "PATH:" not in yaml or "/usr/local/nodejs/bin" not in yaml:
    # Find extraEnv section and add PATH entry
    path_line = '    PATH: "/usr/local/nodejs/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
    yaml = re.sub(
        r'(extraEnv:\n)',
        lambda m: m.group(1) + path_line,
        yaml,
        count=1
    )
    changed = True

if changed:
    with open(path, "w") as f:
        f.write(yaml)
    print("env.yaml updated: added /usr/local/nodejs to readablePaths and PATH to extraEnv")
else:
    print("env.yaml already has nodejs paths configured")
YAMLFIX
    log_ok "OpenCode env.yaml updated (nodejs accessible in sandbox)"
  fi

  # ── 2. Inject into template start.sh (persistent) ──
  backup_file "$tpl"
  python3 - "$tpl" <<'PYTPL'
import sys
tpl_path = sys.argv[1]
with open(tpl_path) as f:
    tpl = f.read()

block = """
# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──
# Official @openviking/opencode-plugin via npm (Huawei Cloud mirror).
# Plugin provides: stdio MCP proxy + lifecycle hooks (autoRecall, capture, repoContext).
# Pre-install plugin SDK before OpenCode starts to avoid blocking TUI during npm install.

# Set npm registry to Huawei Cloud mirror
export NPM_CONFIG_REGISTRY=https://mirrors.huaweicloud.com/repository/npm/

# Pre-install plugin SDK (avoids 45s blocking npm install during OpenCode startup)
# Non-fatal: if npm is unavailable or install fails, opencode still starts without the plugin.
OV_NPM_DIR="$HOME/.config/opencode"
if command -v npm &>/dev/null; then
  if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" ]]; then
    echo "Pre-installing @opencode-ai/plugin SDK (Huawei Cloud npm mirror)..."
    cat > "$OV_NPM_DIR/package.json" <<'PKGEOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.8"
  }
}
PKGEOF
    if (cd "$OV_NPM_DIR" && npm install --registry=https://mirrors.huaweicloud.com/repository/npm/ --no-audit --no-fund 2>&1 | tail -5); then
      echo "Plugin SDK pre-installed."
    else
      echo "WARN: npm install failed, continuing without OpenViking plugin"
    fi
  else
    echo "Plugin SDK already installed, skipping npm install."
  fi

  # Register plugin in opencode.json + cleanup old MCP/prompt approach
  if [[ -f "$CONFIG_FILE" ]]; then
    python3 - "$CONFIG_FILE" <<'OVREG'
import json, sys
path = sys.argv[1]
with open(path) as f:
    cfg = json.load(f)
changed = False
plugins = cfg.setdefault("plugin", [])
if "@openviking/opencode-plugin" not in plugins:
    plugins.append("@openviking/opencode-plugin")
    changed = True
# Remove old MCP remote + prompt if present (cleanup from previous approach)
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
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("OpenViking plugin registered in opencode.json")
OVREG
  fi
else
  echo "WARN: npm not found in PATH, skipping OpenViking plugin install"
fi

# Create openviking-config.json (mirrors official plugin defaults)
OV_CONF_DIR="$HOME/.config/opencode"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 15,
    "scoreThreshold": 0.05,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
OVCONF
fi

"""
marker = "export OPENCODE_SERVER_PASSWORD"
idx = tpl.find(marker)
if idx == -1:
    print("ERROR: insertion marker not found", file=sys.stderr)
    sys.exit(1)
tpl = tpl[:idx] + block + "\n" + tpl[idx:]

# Remove --pure flag from exec line so external plugins can load
# --pure means "run without external plugins" which contradicts the plugin registration above
if " --pure" in tpl:
    tpl = tpl.replace(" --pure", "")
    print("Removed --pure flag from exec line (plugins now enabled)")
else:
    print("--pure flag not present, no change needed")

with open(tpl_path, "w") as f:
    f.write(tpl)
PYTPL
  log_ok "OpenCode template updated with official npm plugin installation (persistent)"
  log_info "Restart OpenCode for plugin to activate"
}
# ── OpenClaw ──────────────────────────────────────────────────────────────────
integrate_openclaw() {
  # OpenClaw runs inside a bwrap sandbox. The config (OPENCLAW_STATE_DIR) is inside
  # the sandbox (e.g. /tmp/.openclaw) and not accessible from outside. We inject
  # the official @openviking/openclaw-plugin install into template start.sh, so it
  # runs inside the gateway's bwrap on every start. The plugin is fetched from npm
  # via the Huawei Cloud mirror (https://mirrors.huaweicloud.com/repository/npm/).
  local tpl="/root/template/openclaw/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "OpenClaw template start.sh not found: $tpl"; return 1; }

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

  require_confirmation "Integrate OpenViking (Official Plugin)" "openclaw" "Install @openviking/openclaw-plugin from npm (Huawei Cloud mirror) into template start.sh (contextEngine slot, auto-recall + auto-capture)" || return 1
  if dry_run_msg "Would add OpenViking plugin install to $tpl"; then return 0; fi

  backup_file "$tpl"

  # Insert official plugin install block before the gateway start step
  python3 - "$tpl" "$OV_ENDPOINT" << 'PYINJECT'
import sys, re
path, endpoint = sys.argv[1], sys.argv[2]
with open(path) as f: content = f.read()

# Skip if already has plugin install injection
if "OpenViking plugin install" in content:
    print("already")
    sys.exit(0)

block = """# ── Step 5: OpenViking plugin install (added by huawei-cloud-openviking-agent-integration skill) ──
# Installs the official @openviking/openclaw-plugin from npm (Huawei Cloud mirror).
# The plugin registers as contextEngine slot for auto-recall + auto-capture.
# Runs inside the gateway's bwrap so files land in the correct /tmp/.openclaw.
#
# FIX: Always install the plugin (idempotent). The previous check for
# $OPENCLAW_STATE_DIR/extensions/openviking was wrong — openclaw plugins install
# puts files in npm/projects/, not extensions/. Since bwrap /tmp is ephemeral
# (--unshare-all), the plugin is lost on every undeploy+deploy, so we must
# reinstall on every start anyway.
echo "[openclaw] Installing OpenViking plugin (Huawei Cloud npm mirror)..."
export NPM_CONFIG_REGISTRY=https://mirrors.huaweicloud.com/repository/npm/
if "$NODE" "$CLI" plugins install @openviking/openclaw-plugin \
  --acknowledge-clawhub-risk 2>&1; then
  echo "[openclaw] OpenViking plugin installed (contextEngine slot)"
else
  echo "[openclaw] WARNING: OpenViking plugin install failed — continuing without it"
fi
unset NPM_CONFIG_REGISTRY

# ── Step 5.4: Configure OpenViking endpoint (added by huawei-cloud-openviking-agent-integration skill) ──
# Set environment variables and plugin config so the plugin knows where OpenViking is.
# Uses __ENDPOINT__ placeholder (replaced by OV_ENDPOINT at injection time).
export OPENVIKING_BASE_URL="__ENDPOINT__"
export OPENVIKING_API_KEY=""
export OPENVIKING_ENDPOINT="__ENDPOINT__"
# Run the plugin's setup command to write config to plugins.entries.openviking.config
# (NOT plugins.entries.openviking.baseUrl — OpenClaw schema rejects unknown keys at that level).
# The setup command writes directly to openclaw.json, bypassing config-set schema validation.
# --base-url enables non-interactive mode; --allow-offline permits write even if health check fails.
if "$NODE" "$CLI" openviking setup --base-url "__ENDPOINT__" --allow-offline --force-slot 2>/dev/null; then
  echo "[openclaw] OpenViking plugin configured via setup command: __ENDPOINT__"
else
  echo "[openclaw] WARNING: openviking setup failed, falling back to env vars only"
fi

# ── Step 5.5: Enable OpenViking plugin (added by huawei-cloud-openviking-agent-integration skill) ──
# Enable the plugin and switch contextEngine slot from "legacy" to "openviking".
# `plugins enable openviking` sets plugins.entries.openviking.enabled=true
# AND plugins.slots.contextEngine=openviking.
"$NODE" "$CLI" plugins enable openviking 2>/dev/null || true
# Also set plugins.allow to explicitly trust the non-bundled plugin.
# The gateway requires plugins.allow for non-bundled plugins; without it,
# the plugin is only "maybe auto-loaded" with a warning.
"$NODE" "$CLI" config set 'plugins.allow' '["openviking"]' 2>/dev/null || true
echo "[openclaw] Enabled OpenViking plugin (contextEngine slot)"

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
2. **recall**: Type-quota memory recall (events, entities, preferences, experiences).
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
  log_ok "OpenClaw template updated with official OpenViking plugin install (npm, Huawei Cloud mirror)"

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

  log_ok "OpenClaw integrated with OpenViking (official plugin via npm, Huawei Cloud mirror)"
  log_info "Restart OpenClaw for changes to take effect"
}



# ── Hermes ────────────────────────────────────────────────────────────────────
integrate_hermes() {
  local tpl="/root/template/hermes/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "Hermes template start.sh not found: $tpl"; return 1; }

  # Check for existing MCP SDK install step
  local has_mcp_sdk=false
  grep -q "MCP SDK install" "$tpl" 2>/dev/null && has_mcp_sdk=true

  # If already has OV injection + MCP SDK install, skip
  if has_ov_injection "$tpl" && [[ "$has_mcp_sdk" == true ]]; then
    log_ok "Hermes already has OpenViking MCP + MCP SDK (template-level)"
    return 0
  fi

  require_confirmation "Integrate OpenViking MCP" "hermes" "Add OpenViking MCP + MCP SDK to template start.sh (persistent)" || return 1
  if dry_run_msg "Would add OpenViking MCP + MCP SDK injection to $tpl and live sandbox"; then return 0; fi

  backup_file "$tpl"

  # Step 1: Add MCP SDK install step if missing
  # Hermes v0.19+ has background MCP discovery, but it silently skips if the
  # 'mcp' Python package is not installed (logs at DEBUG level, invisible).
  # This ensures the package is present after every redeploy.
  if [[ "$has_mcp_sdk" == false ]]; then
    if has_ov_injection "$tpl"; then
      # OV injection exists — insert pip install before it
      sed -i '/# ── OpenViking MCP injection/i \
# ── MCP SDK install ('"$OV_MARKER"') ──\
# Hermes v0.19+ has background MCP discovery, but it silently skips if the\
# '"'"'mcp'"'"' Python package is not installed (logs at DEBUG level, invisible by\
# default). This ensures the package is present after every redeploy.\
# Idempotent: skips if mcp is already importable. Non-fatal: won'"'"'t block startup.\
if ! python3 -c "import mcp" 2>/dev/null; then\
  pip install --quiet --index-url https://mirrors.huaweicloud.com/repository/pypi/simple --trusted-host mirrors.huaweicloud.com "mcp==1.29.0" 2>/dev/null || echo "WARN: failed to install mcp package; MCP tools will be unavailable";\
fi' "$tpl"
    else
      # No OV injection yet — insert pip install before sleep infinity
      sed -i '/^sleep infinity$/i \
# ── MCP SDK install ('"$OV_MARKER"') ──\
# Hermes v0.19+ has background MCP discovery, but it silently skips if the\
# '"'"'mcp'"'"' Python package is not installed (logs at DEBUG level, invisible by\
# default). This ensures the package is present after every redeploy.\
# Idempotent: skips if mcp is already importable. Non-fatal: won'"'"'t block startup.\
if ! python3 -c "import mcp" 2>/dev/null; then\
  pip install --quiet --index-url https://mirrors.huaweicloud.com/repository/pypi/simple --trusted-host mirrors.huaweicloud.com "mcp==1.29.0" 2>/dev/null || echo "WARN: failed to install mcp package; MCP tools will be unavailable";\
fi' "$tpl"
    fi
    log_ok "MCP SDK install step added to Hermes template"
  fi

  # Step 2: Add OpenViking MCP injection if missing
  if ! has_ov_injection "$tpl"; then
    sed -i '/^sleep infinity$/i \
# ── OpenViking MCP injection ('"$OV_MARKER"') ──\
# The model config above recreates config.yaml from scratch (echo > config.yaml).\
# This block re-injects OpenViking MCP after model config is written.\
if ! grep -q "openviking" "$HOME/.hermes/config.yaml" 2>/dev/null; then\
  cat >> "$HOME/.hermes/config.yaml" << '"'"'OVYAML'"'"'\
\
# OpenViking MCP server\
mcp_servers:\
  openviking:\
    url: '"$OV_MCP_URL"'\
\
# OpenViking native memory provider (auto-recall + auto-store)\
memory:\
  provider: openviking\
  openviking:\
    endpoint: '"$OV_ENDPOINT"'\
OVYAML\
fi' "$tpl"
    log_ok "Hermes template updated with OpenViking MCP at $OV_MCP_URL"
  fi

  # Immediate effect: install mcp in live sandbox + inject config
  local sandbox; sandbox=$(find_sandbox "hermes")
  if [[ -n "$sandbox" && -f "${sandbox}/.hermes/config.yaml" ]]; then
    # Install MCP SDK in live sandbox venv (non-fatal)
    if ! /root/runtime/hermes/venv/bin/python3 -c "import mcp" 2>/dev/null; then
      /root/runtime/hermes/venv/bin/pip install --quiet \
        --index-url https://mirrors.huaweicloud.com/repository/pypi/simple \
        --trusted-host mirrors.huaweicloud.com \
        "mcp==1.29.0" 2>/dev/null && log_ok "MCP SDK installed in live Hermes sandbox" \
        || log_info "MCP SDK install in live sandbox failed (will retry on next start)"
    fi
    # Inject OpenViking config if missing
    local cf="${sandbox}/.hermes/config.yaml"
    if ! grep -q "openviking" "$cf" 2>/dev/null; then
      cat >> "$cf" << YAML

# OpenViking MCP server
mcp_servers:
  openviking:
    url: ${OV_MCP_URL}

# OpenViking native memory provider (auto-recall + auto-store)
memory:
  provider: openviking
  openviking:
    endpoint: ${OV_ENDPOINT}
YAML
      log_ok "OpenViking MCP also injected into live sandbox (immediate effect)"
    fi
  else
    log_info "No live Hermes sandbox found; config will take effect on next start"
  fi
  log_info "Restart Hermes for full effect"
}

# ── JiuwenSwarm ───────────────────────────────────────────────────────────────
integrate_jiuwenswarm() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { log_error "JiuwenSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }

  # Template start.sh — injection block for redeploy persistence
  local tpl="/root/template/jiuwenswarm/start.sh"

  # Check if OpenViking MCP server already exists in sandbox config
  if grep -q "name: openviking" "$cf" 2>/dev/null && grep -A5 "name: openviking" "$cf" | grep -q "enabled: true"; then
    # Sandbox has it, but does the template?
    if [[ -f "$tpl" ]] && ! grep -q "OpenViking MCP injection" "$tpl" 2>/dev/null; then
      log_info "Sandbox integrated but template missing — fixing template"
    else
      log_ok "JiuwenSwarm already integrated with OpenViking MCP"
      return 0
    fi
  fi

  require_confirmation "Integrate OpenViking MCP" "jiuwenswarm" "Add OpenViking MCP to sandbox config + template start.sh" || return 1
  if dry_run_msg "Would add OpenViking MCP to $cf and $tpl"; then return 0; fi

  # ── 1. Inject into sandbox config (immediate effect) ──
  if ! grep -q "name: openviking" "$cf" 2>/dev/null; then
    backup_file "$cf"
    python3 - "$cf" "$OV_MCP_URL" << 'PYJW'
import sys, re
path, url = sys.argv[1], sys.argv[2]
with open(path) as f:
    content = f.read()

old = "  servers: []"
new = "  servers:\n    - name: openviking\n      enabled: true\n      transport: streamable-http\n      url: %s\n      timeout_s: 30" % url

if old in content:
    content = content.replace(old, new, 1)
elif "name: openviking" in content:
    pass
else:
    pattern = r"(  servers:\n(?:    - .+\n)+)"
    repl = r"\1    - name: openviking\n      enabled: true\n      transport: streamable-http\n      url: %s\n      timeout_s: 30\n" % url
    content = re.sub(pattern, repl, content, count=1)

# Fallback: servers: followed by comments/whitespace only (no entries, no [])
if "name: openviking" not in content:
    content = content.replace("  servers:\n", new + "\n", 1)

with open(path, 'w') as f:
    f.write(content)
PYJW
    # Also set native memory provider defaults in config
    sed -i 's/engine: ${MEMORY_ENGINE:-builtin}/engine: ${MEMORY_ENGINE:-both}/' "$cf"
    sed -i 's/provider: ${MEMORY_EXTERNAL_PROVIDER:-}   #/provider: ${MEMORY_EXTERNAL_PROVIDER:-openviking}   #/' "$cf"
    log_ok "OpenViking MCP + native memory provider added to sandbox config"
  fi

  # ── 2. Inject into template start.sh (redeploy persistence) ──
  if [[ -f "$tpl" ]] && ! grep -q "OpenViking MCP injection" "$tpl" 2>/dev/null; then
    backup_file "$tpl"
    python3 - "$tpl" "$OV_MCP_URL" << 'PYTPL'
import sys
path, url = sys.argv[1], sys.argv[2]
with open(path) as f:
    lines = f.readlines()

marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
block = marker + """
# Set native memory provider env vars for auto-recall
export MEMORY_ENGINE=both
export MEMORY_EXTERNAL_PROVIDER=openviking
export OPENVIKING_ENDPOINT="__OV_EP__"

# JiuwenSwarm init (jiuwenswarm-init) recreates config.yaml on first start.
# This block re-injects OpenViking MCP after init if missing.
JW_CFG="$JIUWENSWARM_DATA_DIR/config/config.yaml"
if [ -f "$JW_CFG" ] && ! grep -q "name: openviking" "$JW_CFG" 2>/dev/null; then
  python3 - "$JW_CFG" __OV_URL__ << 'PYJW2'
import sys, re
path, url = sys.argv[1], sys.argv[2]
with open(path) as f:
    content = f.read()
old = "  servers: []"
new = "  servers:\\n    - name: openviking\\n      enabled: true\\n      transport: streamable-http\\n      url: %s\\n      timeout_s: 30" % url
if old in content:
    content = content.replace(old, new, 1)
else:
    pattern = r"(  servers:\\n(?:    - .+\\n)+)"
    repl = r"\\1    - name: openviking\\n      enabled: true\\n      transport: streamable-http\\n      url: %s\\n      timeout_s: 30\\n" % url
    content = re.sub(pattern, repl, content, count=1)
# Fallback: servers: followed by comments/whitespace only (no entries, no [])
if "name: openviking" not in content:
    content = content.replace("  servers:\\n", new + "\\n", 1)
with open(path, 'w') as f:
    f.write(content)
PYJW2
fi

# 3. Enhanced 4-section AGENTS.md (Auto-Recall + Proactive Search + Auto-Capture + Repo Context)
#    Supplements native auto-recall with explicit tool guidance for targeted operations.
mkdir -p /workspace
cat > /workspace/AGENTS.md << 'AGENTSMD'
# Agent Instructions

## OpenViking Long-Term Memory

OpenViking is integrated with native memory engine (auto-recall + auto-store at framework level).
You also have direct access to OpenViking MCP tools for explicit and targeted operations.
Follow these protocols:

### Auto-Recall (at conversation start)
Before responding to the user's first message:
1. Call `recall` with the user's message as query to retrieve relevant context (limit=6, min_score=0.35).
2. If working in a code repository, call `search` with the repo name and file paths to find relevant past work.
3. Use retrieved context to inform responses. Do not mention the retrieval process to the user.

### Proactive Search (during tasks)
1. Call `search` to find relevant past knowledge, error solutions, and project decisions.
2. Call `find` for quick lookup without session context.
3. Use `read` with viking:// URIs to access stored reference materials.
4. Use `list` and `glob` to browse available memory when exploring.

### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. Call `remember` to store: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Focus on durable facts, not the full conversation.
3. Use `add_resource` to index important local files or URLs for future reference.

### Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.

The native memory engine handles auto-recall automatically; use these tools for explicit
or targeted operations when needed. Do not wait to be asked — proactively use these tools
for context-aware responses across sessions and projects.
AGENTSMD

# 4. openviking-config.json (mirrors official @openviking/opencode-plugin defaults)
OV_CONF_DIR="$HOME/.config/opencode"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 15,
    "scoreThreshold": 0.05,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
OVCONF
fi

"""
# Substitute the URL placeholder (avoid clashing with %s format strings in the block)
block = block.replace("__OV_URL__", "\"%s\"" % url).replace("__OV_EP__", url.rsplit("/mcp", 1)[0])

# Insert before "nohup" (process start) so config is ready when process reads it
# Fall back to "sleep infinity" if nohup not found
inserted = False
for i, line in enumerate(lines):
    if 'nohup' in line and 'jiuwenswarm-start' in line:
        lines.insert(i, block)
        inserted = True
        break
if not inserted:
    for i, line in enumerate(lines):
        if line.strip() == 'sleep infinity' or line.strip().startswith('sleep infinity'):
            lines.insert(i, block)
            break

with open(path, 'w') as f:
    f.writelines(lines)
PYTPL
    log_ok "OpenViking MCP injection added to template start.sh (redeploy-safe)"
  fi

  # ── 3. Create 4-section AGENTS.md + config in live sandbox (immediate effect) ──
  mkdir -p "${sandbox}/workspace"
  cat > "${sandbox}/workspace/AGENTS.md" << 'JWAGENTS'
# Agent Instructions

## OpenViking Long-Term Memory

OpenViking is integrated with native memory engine (auto-recall + auto-store at framework level).
You also have direct access to OpenViking MCP tools for explicit and targeted operations.
Follow these protocols:

### Auto-Recall (at conversation start)
Before responding to the user's first message:
1. Call `recall` with the user's message as query to retrieve relevant context (limit=6, min_score=0.35).
2. If working in a code repository, call `search` with the repo name and file paths to find relevant past work.
3. Use retrieved context to inform responses. Do not mention the retrieval process to the user.

### Proactive Search (during tasks)
1. Call `search` to find relevant past knowledge, error solutions, and project decisions.
2. Call `find` for quick lookup without session context.
3. Use `read` with viking:// URIs to access stored reference materials.
4. Use `list` and `glob` to browse available memory when exploring.

### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. Call `remember` to store: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Focus on durable facts, not the full conversation.
3. Use `add_resource` to index important local files or URLs for future reference.

### Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.

The native memory engine handles auto-recall automatically; use these tools for explicit
or targeted operations when needed. Do not wait to be asked — proactively use these tools
for context-aware responses across sessions and projects.
JWAGENTS
  create_ov_config "$sandbox"
  log_ok "4-section AGENTS.md + config created in JiuwenSwarm sandbox"

  log_ok "JiuwenSwarm integrated with OpenViking MCP at $OV_MCP_URL"
  log_info "Restart JiuwenSwarm for changes to take effect"
}

# ── KimiCode ──────────────────────────────────────────────────────────────────
integrate_kimicode() {
  local tpl="/root/template/kimicode/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "KimiCode template start.sh not found: $tpl"; return 1; }

  has_ov_injection "$tpl" && { log_ok "KimiCode already has OpenViking MCP (template-level)"; return 0; }

  require_confirmation "Integrate OpenViking MCP" "kimicode" "Add OpenViking MCP to template start.sh (writes mcp.json, not config.toml)" || return 1
  if dry_run_msg "Would add OpenViking MCP injection to $tpl and live mcp.json"; then return 0; fi

  backup_file "$tpl"
  python3 - "$tpl" "$OV_MCP_URL" << 'PYKIMI'
import sys, re
path, url = sys.argv[1], sys.argv[2]
with open(path) as f:
    content = f.read()

marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
if marker in content:
    print("already")
    sys.exit(0)

block = """# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──
# kimi-code reads MCP config from mcp.json (NOT config.toml).
# config.toml is recreated from scratch on every start, but mcp.json is separate.
# This block ensures mcp.json has the OpenViking MCP server entry.
MCP_FILE="$KIMI_CODE_HOME/mcp.json"
python3 - "$MCP_FILE" <<'MCPEOF'
import json, sys, os
path = sys.argv[1]
entry = {"url": "%s"}
if os.path.exists(path):
    with open(path) as f:
        cfg = json.load(f)
else:
    cfg = {}
servers = cfg.setdefault("mcpServers", {})
if "openviking" not in servers:
    servers["openviking"] = entry
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    print("OpenViking MCP injected into mcp.json")
else:
    print("OpenViking MCP already in mcp.json")
MCPEOF

# Create AGENTS.md with 4-section protocol (Auto-Recall + Proactive Search + Auto-Capture + Repo Context)
mkdir -p /workspace
cat > /workspace/AGENTS.md << 'AGENTSMD'
# Agent Instructions

## OpenViking Long-Term Memory

You have OpenViking long-term memory integrated. Follow these protocols:

### Auto-Recall (at conversation start)
Before responding to the user's first message:
1. Call `recall` with the user's message as query to retrieve relevant context (limit=6, min_score=0.35).
2. If working in a code repository, call `search` with the repo name and file paths to find relevant past work.
3. Use retrieved context to inform responses. Do not mention the retrieval process to the user.

### Proactive Search (during tasks)
1. Call `search` to find relevant past knowledge, error solutions, and project decisions.
2. Call `find` for quick lookup without session context.
3. Use `read` with viking:// URIs to access stored reference materials.
4. Use `list` and `glob` to browse available memory when exploring.

### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. Call `remember` to store: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Focus on durable facts, not the full conversation.
3. Use `add_resource` to index important local files or URLs for future reference.

### Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.

Do not wait to be asked — proactively use these tools for context-aware responses across sessions and projects.
AGENTSMD

# Create openviking-config.json (mirrors official @openviking/opencode-plugin defaults)
OV_CONF_DIR="$HOME/.config/opencode"
mkdir -p "$OV_CONF_DIR"
if [[ ! -f "$OV_CONF_DIR/openviking-config.json" ]]; then
  cat > "$OV_CONF_DIR/openviking-config.json" <<'OVCONF'
{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 15,
    "scoreThreshold": 0.05,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
OVCONF
fi

""" % url

# Insert before "sleep infinity" line
lines = content.split('\n')
inserted = False
for i, line in enumerate(lines):
    if line.strip() == 'sleep infinity' or line.strip().startswith('sleep infinity'):
        lines.insert(i, block.rstrip())
        inserted = True
        break
if not inserted:
    # Fallback: append at end
    lines.append(block.rstrip())

content = '\n'.join(lines)
with open(path, 'w') as f:
    f.write(content)
print("injected")
PYKIMI
  log_ok "KimiCode template updated with OpenViking MCP at $OV_MCP_URL (mcp.json)"

  # Immediate effect: write to live mcp.json
  local mcp_file="/root/runtime/kimicode/data/mcp.json"
  python3 - "$mcp_file" "$OV_MCP_URL" << 'LIVEMCP'
import json, sys, os
path, url = sys.argv[1], sys.argv[2]
entry = {"url": url}
if os.path.exists(path):
    with open(path) as f:
        cfg = json.load(f)
else:
    cfg = {}
servers = cfg.setdefault("mcpServers", {})
if "openviking" not in servers:
    servers["openviking"] = entry
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    print("injected")
else:
    print("already exists")
LIVEMCP
  # Create 4-section AGENTS.md in live sandbox workspace
  local sandbox; sandbox=$(find_sandbox "kimicode")
  if [[ -n "$sandbox" ]]; then
    cat > "${sandbox}/AGENTS.md" << 'AGENTSMD'
# Agent Instructions

## OpenViking Long-Term Memory

You have OpenViking long-term memory integrated. Follow these protocols:

### Auto-Recall (at conversation start)
Before responding to the user's first message:
1. Call `recall` with the user's message as query to retrieve relevant context (limit=6, min_score=0.35).
2. If working in a code repository, call `search` with the repo name and file paths to find relevant past work.
3. Use retrieved context to inform responses. Do not mention the retrieval process to the user.

### Proactive Search (during tasks)
1. Call `search` to find relevant past knowledge, error solutions, and project decisions.
2. Call `find` for quick lookup without session context.
3. Use `read` with viking:// URIs to access stored reference materials.
4. Use `list` and `glob` to browse available memory when exploring.

### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. Call `remember` to store: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Focus on durable facts, not the full conversation.
3. Use `add_resource` to index important local files or URLs for future reference.

### Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.

Do not wait to be asked — proactively use these tools for context-aware responses across sessions and projects.
AGENTSMD
    create_ov_config "$sandbox"
    log_ok "4-section AGENTS.md + config created in KimiCode sandbox workspace"
  fi
  log_ok "OpenViking MCP in live mcp.json (immediate effect)"
  log_info "Restart KimiCode for full effect"
}

# ── DeepSeek Harness (dsh) ────────────────────────────────────────────────────
# No official OpenViking plugin (official list: Claude Code/Trae/Cursor/ChatGPT/Codex/OpenCode/Manus/Claude.ai).
# Integration rides dsh's bundled @deepseek-ai/dsh-mcp-client (native MCP client):
#   - profile patch:   .dsh/profiles/{web,cc-tui}/cordis.patch.yml += mcp-openviking insert entry
#   - skill file:      .dsh/skills/openviking/SKILL.md (auto-recall + auto-save + repo context)
#   - guidance:        .dsh/AGENTS.md (cc-tui only; web uses the skill channel)
# Persistence lives in template start.sh — the sandbox .dsh is (re)generated on boot.
dsh_ov_body() {
  cat <<'DSHOVBODY'
import os
import sys

home = sys.argv[1]
profiles = os.path.join(home, 'profiles')

MCP_ENTRY = (
    '- insert:\n'
    '    - id: mcp-openviking\n'
    "      name: '@deepseek-ai/dsh-mcp-client'\n"
    '      config:\n'
    '        serverName: openviking\n'
    '        transport: streamable-http\n'
    '        url: http://127.0.0.1:1933/mcp\n'
)

PERSONA_ENTRY = (
    '\n- id: system-prompt\n'
    '  config:\n'
    '    persona: >-\n'
    '      You are a coding agent powered by the {{model}} model. Your working\n'
    '      directory is {{cwd}}. You have OpenViking long-term memory via\n'
    "      mcp__openviking__* tools: recall relevant past context before\n"
    '      answering, save durable outcomes after meaningful work, and index\n'
    '      repo context at session start (follow the openviking skill protocol).\n'
)

WEB_ENABLE_ENTRY = (
    '\n- id: agent-instructions\n'
    '  disabled: false\n'
    '\n- id: skill-filesystem\n'
    '  disabled: false\n'
)

def write_patch(prof, entries):
    d = os.path.join(profiles, prof)
    os.makedirs(d, exist_ok=True)
    patch = os.path.join(d, 'cordis.patch.yml')
    existing = ''
    if os.path.exists(patch):
        with open(patch, encoding='utf-8') as f:
            existing = f.read()
    body = '\n'.join(l for l in existing.splitlines() if l.strip() != '[]').rstrip()
    for entry in entries:
        if entry in existing or (prof == 'web' and entry == WEB_ENABLE_ENTRY and ('agent-instructions' in existing)):
            continue
        if body.strip():
            body += '\n\n' + entry.strip() + '\n'
        else:
            body = entry.strip() + '\n'
    with open(patch, 'w', encoding='utf-8') as f:
        f.write(body)

write_patch('web', [MCP_ENTRY, PERSONA_ENTRY, WEB_ENABLE_ENTRY])
write_patch('cc-tui', [MCP_ENTRY, PERSONA_ENTRY])

config = os.path.join(home, 'openviking-config.json')
if not os.path.exists(config):
    with open(config, 'w', encoding='utf-8') as f:
        f.write('''{
  "enabled": true,
  "timeoutMs": 30000,
  "repoContext": { "enabled": true, "cacheTtlMs": 60000 },
  "autoRecall": {
    "enabled": true,
    "limit": 10,
    "scoreThreshold": 0.35,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recall": {
    "quotas": { "preferences": 10, "events": 3, "entities": 5 },
    "maxChars": 20000
  },
  "commitTokenThreshold": 20000,
  "commitKeepRecentCount": 10,
  "profileTokenBudget": 10000,
  "resumeContextBudget": 32000
}
''')

SKILL_V2 = '''---
name: openviking
description: OpenViking long-term memory via mcp__openviking__* tools (find/search/recall/read/list/glob/grep/remember/add_resource). RECALL relevant past context before answering; SAVE durable outcomes after meaningful work; INDEX repo context at session start. Use when the user references prior work, asks to remember something, or when past decisions/preferences/error fixes could inform the current task.
---

# OpenViking Long-Term Memory

Behavior knobs live in `$DSH_HOME/openviking-config.json`; defaults quoted inline below.

## Tool cheat-sheet

| Tool | Use when |
|---|---|
| `mcp__openviking__recall` | Balanced current-task recall; preference-heavy questions (type quotas: preferences 10, events 3, entities 5, maxChars 20000) |
| `mcp__openviking__search` | Deep semantic retrieval across memories, resources, and skills (intent analysis, session context) |
| `mcp__openviking__find` | Fast semantic retrieval without session context; cheap lookups |
| `mcp__openviking__read` | Read stored content from viking:// URIs |
| `mcp__openviking__list` / `glob` / `grep` | Browse, match, and regex-search viking:// files |
| `mcp__openviking__remember` | Store durable facts / decisions for memory extraction |
| `mcp__openviking__add_resource` | Index a local file, directory, URL, sitemap, or feed |
| `mcp__openviking__forget` | Delete a viking:// URI after explicit user confirmation |

## 1. Auto-Recall (before responding — mirrors plugin chat.message hook)

1. Before responding to a task message, recall relevant context: `mcp__openviking__recall` (balanced) or `mcp__openviking__search` (deep) with the user's intent as query.
2. Trigger rule: query length >= 3 (minQueryLength); skip trivial greetings.
3. Budget: inline results <= tokenBudget 2000 tokens; per-result preview <= maxContentChars 500 chars; min score scoreThreshold 0.35; preferAbstract=true (use abstract over full content for long items).
4. Use retrieved context as hidden synthetic context. Do not mention the retrieval process to the user.

## 2. Session Start (mirrors session.created hook)

1. On conversation start, inject the user profile and memory index: `mcp__openviking__recall` with preferences/events/entities quotas (10/3/5, maxChars 20000).
2. If working in a code repository, index it: `mcp__openviking__add_resource` with the repo path (cacheTtlMs 60000 — don't re-index the same repo within 60s).
3. Use `mcp__openviking__search` to find prior work on the same codebase.

## 3. Proactive Search (during tasks)

1. `mcp__openviking__search` for deep knowledge, error solutions, and project decisions.
2. `mcp__openviking__find` for quick lookups; `mcp__openviking__read` with viking:// URIs for stored material.
3. `mcp__openviking__list` / `glob` / `grep` to browse memory when exploring.
4. ⚠️ Never read viking:// URIs via local filesystem tools — they are not local files. Always use `mcp__openviking__read` / `glob` / `grep` / `search`.

## 4. Auto-Save (after meaningful exchanges — mirrors auto-capture hook)

1. After a meaningful exchange (task completed or important information learned — roughly a commitTokenThreshold 20000-worth of substance), call `mcp__openviking__remember` to store durable facts: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Store durable facts, not the full conversation; keep the most recent ~10 (commitKeepRecentCount) highlights rather than duplicates.
3. Use `mcp__openviking__add_resource` to index important local files or URLs for future reference.

## 5. Session Boundary Commit (mirrors session.compacting / stop hooks)

1. Before a long session is summarized/compacted, or at session end, call `mcp__openviking__remember` with a compact summary: key decisions, outcomes, and open items.
2. On session resume, rebuild context via `mcp__openviking__recall` (profileTokenBudget 10000 / resumeContextBudget 32000) instead of relying on the old transcript.

Use these tools proactively without waiting to be asked.
'''

skill_dir = os.path.join(home, 'skills', 'openviking')
os.makedirs(skill_dir, exist_ok=True)
skill = os.path.join(skill_dir, 'SKILL.md')
with open(skill, 'w', encoding='utf-8') as f:
    f.write(SKILL_V2)

AGENTS_V2 = '''# Agent Instructions

## OpenViking Long-Term Memory

OpenViking is integrated via MCP. You have direct access to OpenViking MCP tools as `mcp__openviking__*`. Behavior knobs: `$DSH_HOME/openviking-config.json`. Follow these protocols:

### Auto-Recall (before responding)
1. Before responding, call `mcp__openviking__recall` (balanced) or `mcp__openviking__search` (deep) with the user's intent as query (skip if query length < 3).
2. Budget: <=2000 tokens inline, <=500 chars per result, min score 0.35, prefer abstract. Do not mention the retrieval process.

### Session Start
1. Inject profile + memory index: `mcp__openviking__recall` (preferences 10, events 3, entities 5, maxChars 20000).
2. In a code repository: `mcp__openviking__add_resource` on the repo path (cacheTtlMs 60000 — don't re-index within 60s), then `mcp__openviking__search` for prior work.

### Proactive Search (during tasks)
1. `mcp__openviking__search` for deep knowledge / error solutions / decisions; `mcp__openviking__find` for quick lookups.
2. `mcp__openviking__read` with viking:// URIs for stored material; `list` / `glob` / `grep` to browse.
3. ⚠️ Never read viking:// URIs via local filesystem tools — always use the MCP read/glob/grep/search tools.

### Auto-Save (after meaningful exchanges)
1. After completing a task or learning important information, call `mcp__openviking__remember`: user preferences, project decisions, technical details, error solutions, architecture choices.
2. Focus on durable facts, not the full conversation; keep recent ~10 highlights.
3. Use `mcp__openviking__add_resource` to index important local files or URLs.

### Session Boundary
1. Before compaction/session end, `mcp__openviking__remember` a compact summary: decisions, outcomes, open items.
2. On resume, rebuild context via `mcp__openviking__recall`, not the old transcript.

Use these tools proactively — do not wait to be asked.
'''

agents = os.path.join(home, 'AGENTS.md')
with open(agents, 'w', encoding='utf-8') as f:
    f.write(AGENTS_V2)
DSHOVBODY
}
dsh_ov_header() {
  cat <<'DSHOVHDR'
# ═══════════════════════════════════════════════════════════════════════════
# OpenViking long-term memory integration (added by huawei-cloud-openviking-agent-integration skill)
#   Native mechanism: @deepseek-ai/dsh-mcp-client (bundled with dsh core) connects
#   to the OpenViking streamable-HTTP MCP endpoint; its 13 tools surface to the model
#   as mcp__openviking__find / search / recall / remember / add_resource / ... .
#   Mirrors the official plugin strategy: auto-recall (before responding) + auto-save
#   (after meaningful exchanges) + repo context, encoded as a discoverable skill and
#   AGENTS.md guidance. Refreshed on every boot (unconditional overwrite).
# ═══════════════════════════════════════════════════════════════════════════
DSHOVHDR
}

integrate_deepseek_harness() {
  local tpl="/root/template/deepseek-harness/start.sh"
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"

  local tpl_has_ov=false
  grep -q "OpenViking long-term memory integration" "$tpl" 2>/dev/null && tpl_has_ov=true
  local live_has_ov=false
  if grep -q "mcp-openviking" "${dsh_home}/profiles/web/cordis.patch.yml" 2>/dev/null \
     || grep -q "mcp-openviking" "${dsh_home}/profiles/cc-tui/cordis.patch.yml" 2>/dev/null; then
    live_has_ov=true
  fi

  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    log_ok "DeepSeek Harness already integrated with OpenViking MCP (template + live)"
    return 0
  fi

  require_confirmation "Integrate OpenViking MCP" "deepseek-harness" "Inject mcp-openviking into dsh profiles (web/cc-tui) + openviking skill + AGENTS.md (template + live)" || return 1
  if dry_run_msg "Would inject mcp-openviking into $dsh_home/profiles/*/cordis.patch.yml + skills/openviking + AGENTS.md + template $tpl"; then return 0; fi

  # ── 1. Live sandbox (immediate effect) ──
  dsh_ov_body | python3 - "$dsh_home"
  log_ok "OpenViking MCP injected into live dsh profiles + skill + AGENTS.md"

  # ── 2. Template start.sh (persistent) ──
  if [[ "$tpl_has_ov" == "false" ]]; then
    if [[ -f "$tpl" ]]; then
      backup_file "$tpl"
      local inj
      inj="/tmp/dsh_inject_$$.py"
      cat > "$inj" <<'DSHINJ'
import sys
path = sys.argv[1]
anchor = 'chmod 600 "$DSH_HOME/settings.yaml"\n'
with open(path) as f:
    content = f.read()
if 'OpenViking long-term memory integration' in content:
    sys.exit(0)
block = (
    '# ═══════════════════════════════════════════════════════════════════════════\n'
    '# OpenViking long-term memory integration (added by huawei-cloud-openviking-agent-integration skill)\n'
    '#   Native mechanism: @deepseek-ai/dsh-mcp-client (bundled with dsh core) connects\n'
    '#   to the OpenViking streamable-HTTP MCP endpoint; its 13 tools surface to the model\n'
    '#   as mcp__openviking__find / search / recall / remember / add_resource / ... .\n'
    '#   Mirrors the official plugin strategy: auto-recall (before responding) + auto-save\n'
    '#   (after meaningful exchanges) + repo context, encoded as a discoverable skill and\n'
    '#   AGENTS.md guidance. Refreshed on every boot (unconditional overwrite).\n'
    '# ═══════════════════════════════════════════════════════════════════════════\n'
    "python3 - \"$DSH_HOME\" <<'OVPY'\n"
    + sys.stdin.read()
    + 'OVPY\n'
)
if anchor not in content:
    sys.stderr.write('Anchor not found in template start.sh\n')
    sys.exit(1)
content = content.replace(anchor, anchor + block, 1)
with open(path, 'w') as f:
    f.write(content)
DSHINJ
      dsh_ov_body | python3 "$inj" "$tpl"
      rm -f "$inj"
      log_ok "OpenViking integration block injected into template start.sh"
      tpl_has_ov=true
    else
      log_warn "Template $tpl missing — skipping template injection (live only, lost on restart)"
    fi
  fi

  # ── 3. Sync template to sandbox so a restart preserves integration ──
  if [[ "$tpl_has_ov" == "true" && -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Template start.sh synced to sandbox .process_dir"
  fi

  log_info "Restart DeepSeek Harness (web + cc-tui) for full effect"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  check_ov_health || exit 1

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
      codearts)    integrate_codearts    || rc=1 ;;
      opencode)    integrate_opencode    || rc=1 ;;
      openclaw)    integrate_openclaw    || rc=1 ;;
      hermes)      integrate_hermes      || rc=1 ;;
      jiuwenswarm) integrate_jiuwenswarm || rc=1 ;;
      kimicode)    integrate_kimicode    || rc=1 ;;
      deepseek-harness) integrate_deepseek_harness || rc=1 ;;
      *) log_error "Unknown agent: $a"; rc=1 ;;
    esac
  done

  echo ""
  if [[ $rc -eq 0 ]]; then
    log_ok "All requested integrations completed successfully"
  else
    log_warn "Some integrations failed or were skipped. Review output above."
  fi
  return $rc
}

main "$@"
