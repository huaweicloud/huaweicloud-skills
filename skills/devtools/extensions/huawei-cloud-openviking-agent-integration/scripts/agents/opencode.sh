#!/bin/bash
# =============================================================================
# agents/opencode.sh — OpenCode agent subclass
# =============================================================================
# Mechanism: Plugin + openviking-config.json
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_opencode_integrate, agent_opencode_unbind, agent_opencode_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_opencode_register() {
  agent::set_meta name "opencode"
  agent::set_meta display_name "OpenCode"
  agent::set_meta sandbox_pattern "opencode-*"
  agent::set_meta template_path "/root/template/opencode/start.sh"
  agent::set_meta mechanism "Plugin + openviking-config.json"
  registry_add "opencode"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_opencode_integrate() {
  local tpl="/root/template/opencode/start.sh"
  [[ ! -f "$tpl" ]] && { log_error "OpenCode template start.sh not found: $tpl"; return 1; }

  # Persistent runtime location for the on-demand-installed plugin (survives sandbox stop+start)
  local ov_runtime_dir="/root/runtime/opencode/openviking-plugin"

  # Check if plugin is already installed in template
  if grep -q "OpenViking integration" "$tpl" 2>/dev/null && grep -q "opencode-plugin" "$tpl" 2>/dev/null; then
    log_ok "OpenCode already has OpenViking plugin (template-level)"
    return 0
  fi

  require_confirmation "Integrate OpenViking (npm + domestic mirror fallback)" "opencode" \
    "Install @openviking/opencode-plugin (npm online first, on-demand GitHub mirror fallback) + plugin SDK + openviking-config.json to template start.sh (persistent)" \
    || return 1
  if dry_run_msg "Would install OpenViking plugin (npm → on-demand GitHub fallback) to $tpl and live sandbox"; then return 0; fi

  # ── 0. Lazy plugin provisioning: npm online first (fast, ~13s via Huawei Cloud mirror).
  # The expensive GitHub file-by-file download (ov_plugin_provision, ~54s) is deferred
  # to a fallback that only runs if npm is unreachable. This cuts integrate time from
  # ~65s to ~14s when the npm mirror is available. ──

  # ── 1. Install plugin into live sandbox (immediate effect) ──
  local sandbox; sandbox=$(find_sandbox "opencode")
  if [[ -n "$sandbox" && -f "${sandbox}/.config/opencode/opencode.json" ]]; then
    local ov_npm_dir="${sandbox}/.config/opencode"

    # Create .npmrc with domestic-first registry (npmmirror → Huawei Cloud)
    local NPM_REGISTRY; NPM_REGISTRY=$(ov_first_npm_registry)
    echo "registry=${NPM_REGISTRY}" > "${ov_npm_dir}/.npmrc"
    log_ok ".npmrc created ($NPM_REGISTRY)"

    # Try npm install first (online); fall back to the on-demand-installed runtime copy
    local plugin_dst="${ov_npm_dir}/node_modules/@openviking/opencode-plugin"

    # Ensure package.json has both deps for npm install
    cat > "${ov_npm_dir}/package.json" <<'PKGEOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.8",
    "@openviking/opencode-plugin": "0.2.4"
  }
}
PKGEOF
    
    log_info "Trying npm install @openviking/opencode-plugin (online, $NPM_REGISTRY)..."
    if (cd "$ov_npm_dir" && npm install --registry="${NPM_REGISTRY}" --no-audit --no-fund 2>&1 | tail -5) &&        [[ -d "$plugin_dst" ]]; then
      log_ok "opencode-plugin installed from npm (online)"
      # Save to runtime cache for future undeploy+deploy (TTL = 24h from now)
      mkdir -p "$(dirname "$ov_runtime_dir")"
      rm -rf "$ov_runtime_dir"
      cp -a "$plugin_dst" "$ov_runtime_dir"
      if [[ -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
        rm -rf "$(dirname "$ov_runtime_dir")/@opencode-ai"
        cp -a "${ov_npm_dir}/node_modules/@opencode-ai" "$(dirname "$ov_runtime_dir")/@opencode-ai"
      fi
      touch "$ov_runtime_dir"
      log_ok "Plugin saved to runtime cache at $ov_runtime_dir (TTL=24h)"
    else
      log_warn "npm install failed or plugin not found — falling back to on-demand runtime install"
      # Lazy provision: only download from GitHub mirrors when npm fails (~54s fallback)
      ov_plugin_provision "opencode-plugin" "$ov_runtime_dir" || return 1
      log_ok "opencode-plugin provisioned on demand at $ov_runtime_dir"
      rm -rf "$plugin_dst"
      mkdir -p "$(dirname "$plugin_dst")"
      cp -a "$ov_runtime_dir" "$plugin_dst"
      log_ok "opencode-plugin deployed from on-demand runtime install (offline fallback)"
      
      # Still try to install @opencode-ai/plugin SDK separately (needed as peer dep)
      if [[ ! -d "${ov_npm_dir}/node_modules/@opencode-ai" ]]; then
        cat > "${ov_npm_dir}/package.json" <<'PKGEOF2'
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.8"
  }
}
PKGEOF2
        (cd "$ov_npm_dir" && npm install --registry="${NPM_REGISTRY}" --no-audit --no-fund 2>&1 | tail -5) &&           log_ok "Plugin SDK pre-installed from npm" ||           log_warn "Plugin SDK npm install also failed — plugin may not fully work"
      fi
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
    # No sandbox to npm install into — provision runtime dir for template start.sh fallback
    ov_plugin_provision "opencode-plugin" "$ov_runtime_dir" || return 1
    log_ok "opencode-plugin provisioned on demand at $ov_runtime_dir (for next-start fallback)"
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
# Official @openviking/opencode-plugin: cache-first deployment. On sandbox restart,
# plugins are restored from the persistent runtime cache (no network). Only on first
# integrate or cache miss does npm install run. Plugin provides: stdio MCP proxy +
# lifecycle hooks (autoRecall, capture, repoContext). The plugin is pure .mjs with
# zero deps. @opencode-ai/plugin SDK is a peer dep from the OpenCode ecosystem.

# Set npm registry to Huawei Cloud mirror (used only as fallback)
export NPM_CONFIG_REGISTRY=https://mirrors.huaweicloud.com/repository/npm/

OV_NPM_DIR="$HOME/.config/opencode"
mkdir -p "$OV_NPM_DIR/node_modules/@openviking"
OV_PLUGIN_DST="$OV_NPM_DIR/node_modules/@openviking/opencode-plugin"
OV_PLUGIN_CACHE="/root/runtime/opencode/openviking-plugin"

# ── Cache-first: 1) already installed → skip; 2) runtime cache → copy; 3) npm → last resort ──
OV_PLUGIN_SOURCE="none"

# Step 1: Plugin already in sandbox node_modules (survives stop+start, lost on undeploy+deploy)
if [[ -d "$OV_PLUGIN_DST" && -f "$OV_PLUGIN_DST/package.json" ]]; then
  OV_PLUGIN_SOURCE="existing"
  echo "OpenViking plugin already installed in sandbox — skipping re-install (cache hit)."
fi

# Step 2: Copy from persistent runtime cache (survives undeploy+deploy, no network)
if [[ "$OV_PLUGIN_SOURCE" == "none" && -d "$OV_PLUGIN_CACHE" ]]; then
  rm -rf "$OV_PLUGIN_DST"
  cp -a "$OV_PLUGIN_CACHE" "$OV_PLUGIN_DST"
  OV_PLUGIN_SOURCE="cache"
  echo "OpenViking plugin deployed from runtime cache (no network)."
  # Ensure @opencode-ai/plugin SDK is present (copy from cache if bundled, else npm)
  if [[ ! -d "$OV_NPM_DIR/node_modules/@opencode-ai" ]]; then
    if [[ -d "$OV_PLUGIN_CACHE/../@opencode-ai" ]]; then
      cp -a "$OV_PLUGIN_CACHE/../@opencode-ai" "$OV_NPM_DIR/node_modules/@opencode-ai"
      echo "Plugin SDK deployed from runtime cache."
    elif command -v npm &>/dev/null; then
      cat > "$OV_NPM_DIR/package.json" <<'PKGEOF2'
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.8"
  }
}
PKGEOF2
      (cd "$OV_NPM_DIR" && npm install --registry=https://mirrors.huaweicloud.com/repository/npm/ --no-audit --no-fund 2>&1 | tail -5) && \
        echo "Plugin SDK installed from npm." || \
        echo "WARN: Plugin SDK install failed — plugin may not fully work"
    fi
  fi
fi

# Step 3: Last resort — npm install online (first integrate or cache miss)
if [[ "$OV_PLUGIN_SOURCE" == "none" ]]; then
  if command -v npm &>/dev/null; then
    echo "Cache miss — trying npm install @openviking/opencode-plugin (online, domestic mirror)..."
    cat > "$OV_NPM_DIR/package.json" <<'PKGEOF'
{
  "dependencies": {
    "@opencode-ai/plugin": "1.18.8",
    "@openviking/opencode-plugin": "0.2.4"
  }
}
PKGEOF
    if (cd "$OV_NPM_DIR" && npm install --registry=https://mirrors.huaweicloud.com/repository/npm/ --no-audit --no-fund 2>&1 | tail -5) && \
       [[ -d "$OV_PLUGIN_DST" ]]; then
      OV_PLUGIN_SOURCE="npm"
      echo "OpenViking plugin + SDK installed from npm (online, domestic mirror)."
    else
      echo "WARN: npm install failed — plugin will not load"
    fi
  else
    echo "WARN: npm not found and no cache available — plugin will not load"
  fi
fi

# ── Register plugin in opencode.json + cleanup old MCP/prompt approach ──
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
    "limit": 10,
    "scoreThreshold": 0.35,
    "maxContentChars": 500,
    "preferAbstract": true,
    "tokenBudget": 2000,
    "minQueryLength": 3
  },
  "recallLimit": 15,
  "recallMaxContentChars": 20000,
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
# Strip the block's leading newline so unbind's exact splice returns the template
# to its pre-integration state (symmetry with the unbind removal).
tpl = tpl[:idx] + block.lstrip("\n") + tpl[idx:]

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
  log_ok "OpenCode template updated with cache-first plugin deployment (runtime cache → npm fallback, survives undeploy+deploy)"
  log_info "Restart OpenCode for plugin to activate"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_opencode_unbind() {
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
# Restore the --pure flag on the exec line: integration strips it to allow external
# plugins, so unbinding must put it back to return the template to its pre-integration state.
if "opencode serve" in content and "--pure" not in content:
    content = content.replace("opencode serve --port 14096 --hostname 127.0.0.1 --print-logs",
                              "opencode serve --port 14096 --hostname 127.0.0.1 --print-logs --pure")
    with open(path, 'w') as f:
        f.write(content)
    print("Restored --pure flag on exec line")
PYUNBIND
    log_ok "OpenViking integration block removed from template start.sh"
  fi

  # ── 1b. Restore env.yaml: remove nodejs paths added during integration ──
  # Integration adds /usr/local/nodejs to readablePaths and PATH to extraEnv
  # so npm/node are accessible inside the bwrap sandbox. Unbinding must revert this.
  local env_yaml="/root/template/opencode/env.yaml"
  if [[ -f "$env_yaml" ]]; then
    backup_file "$env_yaml"
    python3 - "$env_yaml" <<'YAMLRESTORE'
import sys, re

path = sys.argv[1]
with open(path) as f:
    yaml = f.read()

changed = False

# Remove /usr/local/nodejs from readablePaths
if "/usr/local/nodejs" in yaml:
    yaml = re.sub(r'\n\s+- /usr/local/nodejs\n', '\n', yaml, count=1)
    changed = True

# Remove PATH line containing /usr/local/nodejs/bin from extraEnv
if "/usr/local/nodejs/bin" in yaml:
    yaml = re.sub(r'\n\s+PATH: "/usr/local/nodejs/bin:[^"]*"\n', '\n', yaml, count=1)
    changed = True

if changed:
    with open(path, "w") as f:
        f.write(yaml)
    print("env.yaml restored: removed /usr/local/nodejs from readablePaths and PATH from extraEnv")
else:
    print("env.yaml already clean (no nodejs paths found)")
YAMLRESTORE
    log_ok "OpenCode env.yaml restored (nodejs paths removed)"
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
    # Remove on-demand installed plugin from sandbox node_modules
    rm -rf "${sandbox}/.config/opencode/node_modules/@openviking/opencode-plugin" 2>/dev/null
    log_ok "npm packages and OpenViking config cleaned up"
  fi

  # ── 3. Remove on-demand plugin from persistent runtime location ──
  if [[ -d "/root/runtime/opencode/openviking-plugin" ]]; then
    rm -rf /root/runtime/opencode/openviking-plugin
    log_ok "On-demand installed plugin removed from persistent runtime location"
  fi

  log_info "Restart OpenCode for changes to take full effect"
}


# ── Status ───────────────────────────────────────────────────────────────────
agent_opencode_status() {
  local tpl="/root/template/opencode/start.sh"
  local tpl_has_ov=false
  # Detect OpenViking integration in template (npm-based or legacy embedded)
  if grep -q "OpenViking integration\|@openviking/opencode-plugin\|openviking plugin\|plugins/opencode" "$tpl" 2>/dev/null; then
    tpl_has_ov=true
  else
    has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  fi

  local sandbox; sandbox=$(find_sandbox "opencode")
  [[ -z "$sandbox" ]] && { echo "opencode|unknown|sandbox not found"; return; }
  local cf="${sandbox}/.config/opencode/opencode.json"
  local sandbox_has_ov=false
  # Check for plugin in opencode.json or old MCP
  if [[ -f "$cf" ]]; then
    if python3 -c "import json,sys; d=json.load(open('$cf')); sys.exit(0 if '@openviking/opencode-plugin' in d.get('plugin',[]) else 1)" 2>/dev/null; then
      sandbox_has_ov=true
    elif check_json_mcp "$cf" 2>/dev/null; then
      sandbox_has_ov=true
    fi
  fi

  # Check for plugin SDK installed via npm or the on-demand runtime installation
  local plugin_installed=false
  local plugin_source="npm"
  if [[ -d "${sandbox}/.config/opencode/node_modules/@openviking/opencode-plugin" ]]; then
    plugin_installed=true
    plugin_source="runtime"
  elif [[ -d "${sandbox}/.config/opencode/node_modules/@opencode-ai" ]]; then
    plugin_installed=true
  elif [[ -f "${sandbox}/.config/opencode/plugins/openviking.js" ]]; then
    plugin_installed=true
  fi
  # Check on-demand plugin in persistent runtime location
  local runtime_deployed=false
  [[ -d "/root/runtime/opencode/openviking-plugin" ]] && runtime_deployed=true

  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    if [[ "$plugin_installed" == "true" ]]; then
      if [[ "$plugin_source" == "runtime" ]]; then
        echo "opencode|integrated|Official @openviking/opencode-plugin (on-demand runtime install, template + live)"
      else
        echo "opencode|integrated|Official @openviking/opencode-plugin (npm, domestic mirror, template + live)"
      fi
    else
      echo "opencode|integrated|MCP: $(get_json_mcp_url "$cf") (template + live)"
    fi
  elif [[ "$tpl_has_ov" == "true" ]]; then
    if [[ "$plugin_installed" == "true" ]]; then
      echo "opencode|integrated|Plugin installed (template + live), restart to activate hooks"
    else
      echo "opencode|integrated|Plugin configured (template only, restart to activate)"
    fi
  elif [[ "$sandbox_has_ov" == "true" ]]; then
    echo "opencode|partial|Plugin/MCP in live only, lost on restart"
  else
    echo "opencode|not_integrated|No OpenViking integration found"
  fi
}

