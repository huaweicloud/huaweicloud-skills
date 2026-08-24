#!/bin/bash
# =============================================================================
# agents/codearts.sh — CodeArts CLI agent subclass
# =============================================================================
# Mechanism: MCP in codearts_cli.json
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_codearts_integrate, agent_codearts_unbind, agent_codearts_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_codearts_register() {
  agent::set_meta name "codearts"
  agent::set_meta display_name "CodeArts CLI"
  agent::set_meta sandbox_pattern "codearts-*"
  agent::set_meta template_path "/root/template/codearts/start.sh"
  agent::set_meta mechanism "MCP in codearts_cli.json"
  registry_add "codearts"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_codearts_integrate() {
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
Before responding to the user's first message, check the session for an already-injected
`<openviking-context>` block; if it answers the question, use it and skip extra tool calls.
Otherwise call `search` with `mode="context"` for "what do I know about X" (the server
assembles a token-budgeted digest across memory types), or `find` for a fast ranked list.
Use retrieved context to inform responses; do not mention the retrieval process.

## Proactive Search (during tasks)
1. `search` with `mode="context"` — first choice for relevant past knowledge, error solutions, decisions.
2. `find` — fast ranked list when you want raw hits to triage yourself.
3. `read` — expand promising hits (viking:// URIs) before relying on them; an abstract may be stale.
4. `grep` / `glob` — exact text or filename matching when you know the literal string or file name.

## Auto-Capture (after meaningful exchanges)
After completing a task or learning important information:
1. `remember` — only for what the user explicitly asks to keep, or clearly durable facts,
   preferences, and decisions needed before automatic extraction would catch them.
   Do not mirror routine conversation into it; automatic extraction covers that.
2. `add_resource` — import files, directories, URLs, or repos as durable knowledge.
   Processing is asynchronous; report that ingestion started rather than blocking.
3. Never echo credentials or surface private memories unrelated to the task.

## Repo Context
When starting work in a repository:
1. `add_resource` with the repo path to index it for context-aware assistance.
2. `search` to find prior work on the same codebase.

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
inject_block = inject_block.replace("URL_PLACEHOLDER", url)
# Strip the block's outer newlines and insert with a single blank line, so the
# unbind's anchor-based removal returns the template to its pre-integration state.
c = c.replace("sleep infinity", inject_block.strip("\n") + "\n\nsleep infinity")
with open(path, 'w') as f: f.write(c)
CATPL
    log_ok "CodeArts template updated with MCP + 4-section prompt + config"
  fi
  log_ok "CodeArts integrated with OpenViking MCP + 4-section prompt at $OV_MCP_URL"
  log_info "Restart CodeArts session for changes to take effect"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_codearts_unbind() {
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
    elif start is not None:
        # The injected block is one contiguous region that integrate inserts right
        # before a top-level anchor (sleep/nohup/exec). End = that anchor, exclusive.
        import re
        if re.match(r'\s*(sleep |nohup |exec |exit )', line):
            end = i
            break

if start is not None:
    # No anchor found (block runs to EOF): end at EOF.
    if end is None:
        end = len(lines)
if start is not None and end is not None:
    # Also remove preceding blank line
    if start > 0 and lines[start-1].strip() == "":
        start -= 1
    # Trim trailing blank lines (e.g. between the block and the anchor)
    while end > start and lines[end-1].strip() == "":
        end -= 1
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


# ── Status ───────────────────────────────────────────────────────────────────
agent_codearts_status() {
  local sandbox; sandbox=$(find_sandbox "codearts")
  [[ -z "$sandbox" ]] && { echo "codearts|unknown|sandbox not found"; return; }
  local cf="${sandbox}/.codeartsdoer/codearts_cli.json"
  [[ ! -f "$cf" ]] && { echo "codearts|unknown|config not found"; return; }
  
  if check_json_mcp "$cf"; then
    echo "codearts|integrated|MCP: $(get_json_mcp_url "$cf")"
  else
    echo "codearts|not_integrated|MCP section absent"
  fi
}

