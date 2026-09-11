#!/bin/bash
# agents/kimicode.sh — KimiCode agent subclass (MCP via mcp.json)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_kimicode_register() {
  agent::set_meta name "kimicode"
  agent::set_meta display_name "KimiCode"
  agent::set_meta sandbox_pattern "kimicode-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/kimicode/start.sh"
  agent::set_meta mechanism "MCP via mcp.json"
  registry_add "kimicode"
}

agent_kimicode_integrate() {
  local tpl="${AGENT_META[template_path]}"
  [[ ! -f "$tpl" ]] && { log_error "KimiCode template start.sh not found: $tpl"; return 1; }

  has_ov_injection "$tpl" && { log_ok "KimiCode already has OpenViking MCP (template-level)"; return 0; }

  require_confirmation "Integrate OpenViking MCP" "kimicode" "Add OpenViking MCP to template start.sh (writes mcp.json, not config.toml)" || return 1
  if dry_run_msg "Would add OpenViking MCP injection to $tpl and live mcp.json"; then return 0; fi
  backup_file "$tpl"
  "$OV_PY" - "$tpl" "$OV_MCP_URL" "$OV_SHARED_DIR" "$OV_TEMPLATE_DIR" << 'PYKIMI'
import sys, re
path, url, shared_dir, template_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(path) as f:
    content = f.read()
marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
if "ov-kimicode-init.sh" in content or marker in content:
    print("already")
    sys.exit(0)
block = """# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──
# kimi-code reads MCP config from mcp.json (NOT config.toml, which is recreated on each start).
_ov_py=""
for _py in python3.12 python3.11 python3.10 python3; do command -v "$_py" >/dev/null 2>&1 && _ov_py="$_py" && break; done
: "${_ov_py:=python3}"
MCP_FILE="$KIMI_CODE_HOME/mcp.json"
$_ov_py - "$MCP_FILE" <<'MCPEOF'
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
1. `remember` — call this whenever the user shares preferences, important facts, decisions,
   or explicitly asks to remember/keep/save something (e.g. "记住", "记住这个", "请记住",
   "remember this", "帮我记一下"). This is the ONLY way to persist to long-term memory —
   there is no automatic session capture, so if you don't call `remember`, nothing is saved.
   Do not mirror routine back-and-forth chatter, but DO capture durable knowledge.
2. `add_resource` — import files, directories, URLs, or repos as durable knowledge.
   Processing is asynchronous; report that ingestion started rather than blocking.
3. Never echo credentials or surface private memories unrelated to the task.
### Repo Context
When starting work in a repository:
1. Call `add_resource` with the repo path to index it for context-aware assistance.
2. Use `search` to find prior work on the same codebase.
Do not wait to be asked — proactively use these tools for context-aware responses across sessions and projects.
AGENTSMD
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
import os
init_path = f"{shared_dir}/ov-kimicode-init.sh"
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for KimiCode ──\n")
    f.write(f"# Sourced by {template_dir}/kimicode/start.sh (single source line).\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block)
os.chmod(init_path, 0o755)
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-kimicode-init.sh\n# ── End OpenViking integration ──\n"

lines = content.split('\n')
inserted = False
for i, line in enumerate(lines):
    if line.strip() == 'sleep infinity' or line.strip().startswith('sleep infinity'):
        lines.insert(i, source_block.rstrip())
        lines.insert(i + 1, "")
        inserted = True
        break
if not inserted:
    lines.append(source_block.rstrip())
    lines.append("")
content = '\n'.join(lines)
with open(path, 'w') as f:
    f.write(content)
print("injected")
PYKIMI
  log_ok "KimiCode template updated with OpenViking MCP at $OV_MCP_URL (mcp.json)"
  # Write to live mcp.json (immediate effect)
  local mcp_file="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  "$OV_PY" - "$mcp_file" "$OV_MCP_URL" << 'LIVEMCP'
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
1. `remember` — call this whenever the user shares preferences, important facts, decisions,
   or explicitly asks to remember/keep/save something (e.g. "记住", "记住这个", "请记住",
   "remember this", "帮我记一下"). This is the ONLY way to persist to long-term memory —
   there is no automatic session capture, so if you don't call `remember`, nothing is saved.
   Do not mirror routine back-and-forth chatter, but DO capture durable knowledge.
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
  ov_log_info "重启 KimiCode 以完全生效" "Restart KimiCode for full effect"
}

agent_kimicode_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-kimicode-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "Create openviking-config.json" "$tpl" 2>/dev/null && tpl_has_ov=true
  local mcp_file="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  local live_has_ov=false
  [[ -f "$mcp_file" ]] && "$OV_PY" -c "import json; d=json.load(open('$mcp_file')); exit(0 if 'openviking' in d.get('mcpServers',{}) else 1)" 2>/dev/null && live_has_ov=true

  local legacy_cf="$OV_RUNTIME_DIR/kimicode/data/config.toml"
  local legacy_has_ov=false
  [[ -f "$legacy_cf" ]] && grep -q "mcp_servers.openviking" "$legacy_cf" 2>/dev/null && legacy_has_ov=true
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
    "$OV_PY" - "$tpl" "$OV_SHARED_DIR" <<'PYKUNBIND'
import sys, re
path, shared_dir = sys.argv[1], sys.argv[2]
with open(path) as f:
    content = f.read()
# First try new-style: 3-line source block
new_pattern = rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\nsource {shared_dir}/ov-kimicode-init\.sh\n# ── End OpenViking integration ──\n\n?'
new_content = re.sub(new_pattern, '', content)
if new_content != content:
    with open(path, 'w') as f:
        f.write(new_content)
    print("removed new-style source block")
    sys.exit(0)
# Fall back to old-style: full inline block
lines = content.splitlines(keepends=True)
marker = "# ── OpenViking MCP injection (added by huawei-cloud-openviking-agent-integration skill) ──"
marker_legacy = "# ── OpenViking MCP injection (added by openviking-agent-integration skill) ──"
start = None
for i, line in enumerate(lines):
    if (marker in line or marker_legacy in line) and start is None:
        start = i
        break
end = None
if start is not None:
    # Walk forward to the config-block closing "fi"
    found_config = False
    for i in range(start, len(lines)):
        if "# Create openviking-config.json" in lines[i]:
            found_config = True
        if found_config and lines[i].strip() == "fi":
            end = i + 1
            break
    if end is None:
        # Config sub-block absent: close at AGENTSMD + trailing blank
        for i in range(start, len(lines)):
            if lines[i].strip() == "AGENTSMD":
                end = i + 1
                break
if start is not None and end is not None:
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
    rm -f "$OV_SHARED_DIR/ov-kimicode-init.sh" && log_ok "Removed standalone ov-kimicode-init.sh"
  fi
  if [[ "$live_has_ov" == "true" ]]; then
    if [[ -f "$mcp_file" ]]; then
      backup_file "$mcp_file"
      "$OV_PY" -c "
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
  if [[ -n "$ov_conf" ]]; then
    rm -f "$ov_conf"
    log_ok "openviking-config.json removed from sandbox"
  fi
  if [[ "$legacy_has_ov" == "true" ]]; then
    backup_file "$legacy_cf"
    "$OV_PY" -c "
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
  ov_log_info "重启 KimiCode 以使更改完全生效" "Restart KimiCode for changes to take full effect"
}

agent_kimicode_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-kimicode-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  local mcp_file="$OV_RUNTIME_DIR/kimicode/data/mcp.json"
  local live_has_ov=false
  local url=""
  if [[ -f "$mcp_file" ]] && "$OV_PY" -c "import json; d=json.load(open('$mcp_file')); exit(0 if 'openviking' in d.get('mcpServers',{}) else 1)" 2>/dev/null; then
    live_has_ov=true
    url=$("$OV_PY" -c "import json; d=json.load(open('$mcp_file')); print(d.get('mcpServers',{}).get('openviking',{}).get('url',''))" 2>/dev/null)
  fi
  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    ov_status "kimicode" "integrated" "MCP: ${url:-http://127.0.0.1:1933/mcp} via mcp.json (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    ov_status "kimicode" "integrated" "MCP configured (template only, restart to activate)"
  elif [[ "$live_has_ov" == "true" ]]; then
    ov_status "kimicode" "partial" "MCP: ${url:-http://127.0.0.1:1933/mcp} via mcp.json (live only, lost on restart)"
  else
    ov_status "kimicode" "not_integrated" "No OpenViking MCP"
  fi
}
