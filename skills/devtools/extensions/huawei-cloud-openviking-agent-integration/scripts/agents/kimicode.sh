#!/bin/bash
# =============================================================================
# agents/kimicode.sh — KimiCode agent subclass
# =============================================================================
# Mechanism: MCP via mcp.json
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_kimicode_integrate, agent_kimicode_unbind, agent_kimicode_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_kimicode_register() {
  agent::set_meta name "kimicode"
  agent::set_meta display_name "KimiCode"
  agent::set_meta sandbox_pattern "kimicode-*"
  agent::set_meta template_path "/root/template/kimicode/start.sh"
  agent::set_meta mechanism "MCP via mcp.json"
  registry_add "kimicode"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_kimicode_integrate() {
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
Before responding to the user's first message, check the session for an already-injected
`<openviking-context>` block; if it answers the question, use it and skip extra tool calls.
Otherwise call `search` with `mode="context"` for "what do I know about X" (the server
assembles a token-budgeted digest across memory types), or `find` for a fast ranked list.
Use retrieved context to inform responses; do not mention the retrieval process.

### Proactive Search (during tasks)
1. `search` with `mode="context"` — first choice for relevant past knowledge, error solutions, decisions.
2. `find` — fast ranked list when you want raw hits to triage yourself.
3. `read` — expand promising hits (viking:// URIs) before relying on them; an abstract may be stale.
4. `grep` / `glob` — exact text or filename matching when you know the literal string or file name.

### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. `remember` — only for what the user explicitly asks to keep, or clearly durable facts,
   preferences, and decisions needed before automatic extraction would catch them.
   Do not mirror routine conversation into it; automatic extraction covers that.
2. `add_resource` — import files, directories, URLs, or repos as durable knowledge.
   Processing is asynchronous; report that ingestion started rather than blocking.
3. Never echo credentials or surface private memories unrelated to the task.

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

""" % url

# Insert before "sleep infinity" line
lines = content.split('\n')
inserted = False
for i, line in enumerate(lines):
    if line.strip() == 'sleep infinity' or line.strip().startswith('sleep infinity'):
        lines.insert(i, block.rstrip())
        lines.insert(i + 1, "")
        inserted = True
        break
if not inserted:
    # Fallback: append at end
    lines.append(block.rstrip())
    lines.append("")

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
Before responding to the user's first message, check the session for an already-injected
`<openviking-context>` block; if it answers the question, use it and skip extra tool calls.
Otherwise call `search` with `mode="context"` for "what do I know about X" (the server
assembles a token-budgeted digest across memory types), or `find` for a fast ranked list.
Use retrieved context to inform responses; do not mention the retrieval process.

### Proactive Search (during tasks)
1. `search` with `mode="context"` — first choice for relevant past knowledge, error solutions, decisions.
2. `find` — fast ranked list when you want raw hits to triage yourself.
3. `read` — expand promising hits (viking:// URIs) before relying on them; an abstract may be stale.
4. `grep` / `glob` — exact text or filename matching when you know the literal string or file name.

### Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. `remember` — only for what the user explicitly asks to keep, or clearly durable facts,
   preferences, and decisions needed before automatic extraction would catch them.
   Do not mirror routine conversation into it; automatic extraction covers that.
2. `add_resource` — import files, directories, URLs, or repos as durable knowledge.
   Processing is asynchronous; report that ingestion started rather than blocking.
3. Never echo credentials or surface private memories unrelated to the task.

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


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_kimicode_unbind() {
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
for i, line in enumerate(lines):
    if (marker in line or marker_legacy in line) and start is None:
        start = i
        break

end = None
if start is not None:
    # The block is one contiguous injection: marker ... AGENTSMD ... <blank>
    # ... # Create openviking-config.json ... OVCONF ... fi. Walk forward to the
    # config-block closing "fi" (next line blank / sleep / EOF).
    found_config = False
    for i in range(start, len(lines)):
        if "# Create openviking-config.json" in lines[i]:
            found_config = True
        if found_config and lines[i].strip() == "fi":
            end = i + 1  # include the "fi" line
            break
    if end is None:
        # Config sub-block absent (older injection): close at AGENTSMD + trailing blank.
        for i in range(start, len(lines)):
            if lines[i].strip() == "AGENTSMD":
                end = i + 1
                break

if start is not None and end is not None:
    # Also remove trailing blank line if present
    if end < len(lines) and lines[end].strip() == "":
        end += 1
    del lines[start:end]
    with open(path, 'w') as f:
        f.writelines(lines)
    print("removed MCP injection block")
else:
    print("MCP injection block not found")
    with open(path, 'w') as f:
        f.writelines(lines)

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


# ── Status ───────────────────────────────────────────────────────────────────
agent_kimicode_status() {
  local tpl="/root/template/kimicode/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true

  local mcp_file="/root/runtime/kimicode/data/mcp.json"
  local live_has_ov=false
  local url=""
  if [[ -f "$mcp_file" ]] && python3 -c "import json; d=json.load(open('$mcp_file')); exit(0 if 'openviking' in d.get('mcpServers',{}) else 1)" 2>/dev/null; then
    live_has_ov=true
    url=$(python3 -c "import json; d=json.load(open('$mcp_file')); print(d.get('mcpServers',{}).get('openviking',{}).get('url',''))" 2>/dev/null)
  fi

  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    echo "kimicode|integrated|MCP: ${url:-http://127.0.0.1:1933/mcp} via mcp.json (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    echo "kimicode|integrated|MCP configured (template only, restart to activate)"
  elif [[ "$live_has_ov" == "true" ]]; then
    echo "kimicode|partial|MCP: ${url:-http://127.0.0.1:1933/mcp} via mcp.json (live only, lost on restart)"
  else
    echo "kimicode|not_integrated|No OpenViking MCP"
  fi
}

