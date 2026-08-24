#!/bin/bash
# =============================================================================
# agents/jiuwenswarm.sh — JiuwenSwarm agent subclass
# =============================================================================
# Mechanism: Dual-channel: provider + MCP
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_jiuwenswarm_integrate, agent_jiuwenswarm_unbind, agent_jiuwenswarm_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_jiuwenswarm_register() {
  agent::set_meta name "jiuwenswarm"
  agent::set_meta display_name "JiuwenSwarm"
  agent::set_meta sandbox_pattern "jiuwenswarm-*"
  agent::set_meta template_path "/root/template/jiuwenswarm/start.sh"
  agent::set_meta mechanism "Dual-channel: provider + MCP"
  registry_add "jiuwenswarm"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_jiuwenswarm_integrate() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { log_error "JiuwenSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }

  local tpl="/root/template/jiuwenswarm/start.sh"

  # Check if already integrated (native provider + MCP server)
  local already=false
  if grep -q "MEMORY_ENGINE:-both\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null; then
    already=true
  elif [[ -f "$tpl" ]] && grep -q "MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null; then
    already=true
  fi
  if [[ "$already" == "true" ]]; then
    if [[ -f "$tpl" ]] && grep -q "OpenViking native memory provider injection" "$tpl" 2>/dev/null; then
      log_ok "JiuwenSwarm already integrated with OpenViking (native memory provider + MCP)"
      return 0
    fi
    log_info "Sandbox has native provider but template missing injection — fixing template"
  fi

  require_confirmation "Integrate OpenViking" "jiuwenswarm" "Add OpenViking native memory provider + MCP server to sandbox config + template start.sh" || return 1
  if dry_run_msg "Would add OpenViking native memory provider + MCP server to $cf and $tpl"; then return 0; fi

  # ── 1. Set native memory provider + MCP server + auto_memory in sandbox config (immediate effect) ──
  backup_file "$cf"
  python3 - "$cf" "$OV_MCP_URL" << 'PYNATIVE'
import sys, re
path = sys.argv[1]
mcp_url = sys.argv[2]
with open(path) as f:
    content = f.read()
changed = False

# Change engine default from builtin to both
new_content = re.sub(
    r'(engine:\s*\$\{MEMORY_ENGINE:-)builtin(\})',
    r'\1both\2', content
)
if new_content != content:
    content = new_content
    changed = True

# Change provider default from empty to openviking
new_content = re.sub(
    r'(provider:\s*\$\{MEMORY_EXTERNAL_PROVIDER:-)(\})',
    r'\1openviking\2', content
)
if new_content != content:
    content = new_content
    changed = True

# Enable auto_memory_enabled (change from false to true)
new_content = re.sub(
    r'(auto_memory_enabled:\s*)false',
    r'\1true', content
)
if new_content != content:
    content = new_content
    changed = True

# Add MCP server entry to mcp.servers
mcp_entry = (
    "    - name: openviking\n"
    "      transport: streamable-http\n"
    f"      url: {mcp_url}\n"
    "      enabled: true\n"
)
if "name: openviking" not in content:
    new_content = re.sub(
        r'(mcp:\s*\n\s*servers:\s*)\[\]',
        lambda m: m.group(1) + "\n" + mcp_entry,
        content
    )
    if new_content != content:
        content = new_content
        changed = True
    else:
        new_content = re.sub(
            r'(mcp:\s*\n\s*servers:\s*\n)(?!\s*-)',
            lambda m: m.group(1) + mcp_entry,
            content
        )
        if new_content != content:
            content = new_content
            changed = True

if changed:
    with open(path, 'w') as f:
        f.write(content)
PYNATIVE
  log_ok "OpenViking native memory provider + MCP server + auto_memory added to sandbox config"

  # ── 2. Inject into template start.sh (redeploy persistence) ──
  if [[ -f "$tpl" ]] && ! grep -q "OpenViking native memory provider injection" "$tpl" 2>/dev/null; then
    backup_file "$tpl"
    python3 - "$tpl" "$OV_ENDPOINT" "$OV_MCP_URL" << 'PYTPL'
import sys
path, endpoint, mcp_url = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    lines = f.readlines()

marker = "# ── OpenViking native memory provider injection (added by huawei-cloud-openviking-agent-integration skill) ──"
block = marker + """
# Set native memory provider env vars for auto-recall + auto-store
export MEMORY_ENGINE=both
export MEMORY_EXTERNAL_PROVIDER=openviking
export OPENVIKING_ENDPOINT="__OV_EP__"
export OPENVIKING_AGENT=jiuwenswarm

# JiuwenSwarm init (jiuwenswarm-init) recreates config.yaml on first start.
# This block re-applies native memory provider + MCP server + auto_memory after init if missing.
JW_CFG="$JIUWENSWARM_DATA_DIR/config/config.yaml"
if [ -f "$JW_CFG" ]; then
  python3 - "$JW_CFG" "__OV_MCP__" << 'PYJW2'
import sys, re
path = sys.argv[1]
mcp_url = sys.argv[2]
with open(path) as f:
    content = f.read()
changed = False

# Re-apply engine default
new_content = re.sub(r'(engine:\\s*\\$\\{MEMORY_ENGINE:-)builtin(\\})', r'\\1both\\2', content)
if new_content != content:
    content = new_content
    changed = True

# Re-apply provider default
new_content = re.sub(r'(provider:\\s*\\$\\{MEMORY_EXTERNAL_PROVIDER:-)(\\})', r'\\1openviking\\2', content)
if new_content != content:
    content = new_content
    changed = True

# Re-apply auto_memory_enabled
new_content = re.sub(r'(auto_memory_enabled:\\s*)false', r'\\1true', content)
if new_content != content:
    content = new_content
    changed = True

# Re-apply MCP server entry
mcp_entry = (
    "    - name: openviking\\n"
    "      transport: streamable-http\\n"
    f"      url: {mcp_url}\\n"
    "      enabled: true\\n"
)
if "name: openviking" not in content:
    new_content = re.sub(
        r'(mcp:\\s*\\n\\s*servers:\\s*)\\[\\]',
        lambda m: m.group(1) + "\\n" + mcp_entry,
        content
    )
    if new_content != content:
        content = new_content
        changed = True

if changed:
    with open(path, 'w') as f:
        f.write(content)
PYJW2
fi

# AGENTS.md: dual-channel protocol (MCP tools + native memory provider)
mkdir -p /workspace
cat > /workspace/AGENTS.md << 'AGENTSMD'
# Agent Instructions

## OpenViking Long-Term Memory

You have OpenViking long-term memory integrated via dual channels:
1. **MCP server** — full 13-tool access (search, recall, find, read, remember, add_resource, grep, glob, forget, health, list, list_watches, cancel_watch)
2. **Native memory engine** — automatic recall at conversation start + automatic store after exchanges

Follow these protocols:

### Auto-Recall (at conversation start)
Before responding to the user's first message, check the session for an already-injected
`<openviking-context>` block; if it answers the question, use it and skip extra tool calls.
Otherwise call `search` with `mode="context"` for "what do I know about X" (the server
assembles a token-budgeted digest across memory types), or `find` for a fast ranked list.
Use retrieved context to inform responses; do not mention the retrieval process.

### Proactive Search (during tasks)
1. `search` with `mode="context"` — first choice for relevant past knowledge, error solutions, decisions.
2. `recall` — type-quota recall across events, entities, preferences, experiences for structured retrieval.
3. `find` — fast ranked list when you want raw hits to triage yourself.
4. `read` — expand promising hits (viking:// URIs) before relying on them; an abstract may be stale.
5. `grep` / `glob` — exact text or filename matching when you know the literal string or file name.

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

The native memory engine handles auto-recall and auto-capture automatically.
Use MCP tools (search, recall, find, read, remember, add_resource) for explicit,
targeted operations when you need more control or richer retrieval.
Do not wait to be asked — proactively use these tools for context-aware responses
across sessions and projects.
AGENTSMD

"""
block = block.replace("__OV_EP__", endpoint).replace("__OV_MCP__", mcp_url)

# Insert before "nohup" (process start) so config is ready when process reads it
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
    log_ok "OpenViking native memory provider + MCP injection added to template start.sh (redeploy-safe)"
  fi

  # ── 3. Create AGENTS.md in live sandbox (immediate effect) ──
  mkdir -p "${sandbox}/workspace"
  cat > "${sandbox}/workspace/AGENTS.md" << 'JWAGENTS'
# Agent Instructions

## OpenViking Long-Term Memory

You have OpenViking long-term memory integrated via dual channels:
1. **MCP server** — full 13-tool access (search, recall, find, read, remember, add_resource, grep, glob, forget, health, list, list_watches, cancel_watch)
2. **Native memory engine** — automatic recall at conversation start + automatic store after exchanges

Follow these protocols:

### Auto-Recall (at conversation start)
Before responding to the user's first message, check the session for an already-injected
`<openviking-context>` block; if it answers the question, use it and skip extra tool calls.
Otherwise call `search` with `mode="context"` for "what do I know about X" (the server
assembles a token-budgeted digest across memory types), or `find` for a fast ranked list.
Use retrieved context to inform responses; do not mention the retrieval process.

### Proactive Search (during tasks)
1. `search` with `mode="context"` — first choice for relevant past knowledge, error solutions, decisions.
2. `recall` — type-quota recall across events, entities, preferences, experiences for structured retrieval.
3. `find` — fast ranked list when you want raw hits to triage yourself.
4. `read` — expand promising hits (viking:// URIs) before relying on them; an abstract may be stale.
5. `grep` / `glob` — exact text or filename matching when you know the literal string or file name.

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

The native memory engine handles auto-recall and auto-capture automatically.
Use MCP tools (search, recall, find, read, remember, add_resource) for explicit,
targeted operations when you need more control or richer retrieval.
Do not wait to be asked — proactively use these tools for context-aware responses
across sessions and projects.
JWAGENTS
  log_ok "AGENTS.md created in JiuwenSwarm sandbox"

  log_ok "JiuwenSwarm integrated with OpenViking (native memory provider + MCP) at $OV_ENDPOINT"
  log_info "Restart JiuwenSwarm for changes to take effect"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_jiuwenswarm_unbind() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { log_error "JiuwenSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }

  local tpl="/root/template/jiuwenswarm/start.sh"
  # Backward compat: old integration created this file (now removed, but clean up if present)
  local ov_conf="${sandbox}/.config/opencode/openviking-config.json"

  # Check if OpenViking integration exists anywhere
  local has_sandbox=0 has_template=0
  grep -q "name: openviking\|openviking:\|viking_search\|MEMORY_ENGINE:-both\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null && has_sandbox=1
  [[ -f "$ov_conf" ]] && has_sandbox=1
  [[ -f "$tpl" ]] && grep -q "OpenViking\|openviking-config\|Enhanced 4-section AGENTS\|MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null && has_template=1

  if [[ "$has_sandbox" -eq 0 && "$has_template" -eq 0 ]]; then
    log_ok "JiuwenSwarm not integrated (nothing to remove)"
    return 0
  fi

  require_confirmation "UNBIND OpenViking" "jiuwenswarm" "Remove OpenViking native memory provider (+ legacy MCP if present) from sandbox and template" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking from $cf and $tpl"; then return 0; fi

  # ── 1. Remove from sandbox config (MCP server + native memory provider + tool perms) ──
  if [[ "$has_sandbox" -eq 1 ]]; then
    backup_file "$cf"
    python3 - "$cf" << 'PYJW'
import sys, re
path = sys.argv[1]
with open(path) as f:
    content = f.read()

# Remove MCP server entry (- name: openviking + its sub-entries)
content = re.sub(
    r'    - name: openviking\n(?:      .+\n)+',
    '',
    content,
    count=1
)
# Clean up empty servers section
content = re.sub(
    r'  servers:\n(?!    - )',
    '  servers: []\n',
    content,
    count=1
)
content = content.replace("  servers: []\n\n  # 示例", "  servers: []\n  # 示例")

# Revert native memory provider defaults (robust regex, handles any whitespace)
# engine: ${MEMORY_ENGINE:-both} → engine: ${MEMORY_ENGINE:-builtin}
content = re.sub(
    r'(engine:\s*\$\{MEMORY_ENGINE:-)both(\})',
    r'\1builtin\2', content
)
# provider: ${MEMORY_EXTERNAL_PROVIDER:-openviking} → provider: ${MEMORY_EXTERNAL_PROVIDER:-}
content = re.sub(
    r'(provider:\s*\$\{MEMORY_EXTERNAL_PROVIDER:-)openviking(\})',
    r'\1\2', content
)

# Remove openviking: memory provider section under memory.external
# (robust: handles variable indentation and content)
content = re.sub(
    r'(\n    openviking:\n(?:      [^\n]*\n)+)',
    '\n', content
)

# Remove viking_* tool permissions (handles any order/whitespace)
for perm in ['viking_search', 'viking_read', 'viking_browse', 'viking_remember', 'viking_add_resource']:
    content = re.sub(r'\n    ' + perm + r': allow\b', '', content)


# Revert auto_memory_enabled to false
content = re.sub(
    r'(auto_memory_enabled:\s*)true',
    r'\1false', content
)
with open(path, 'w') as f:
    f.write(content)
PYJW
    log_ok "OpenViking MCP + native memory provider + tool permissions removed from sandbox config"
  fi

  # ── 1b. Remove openviking-config.json from sandbox (backward compat) ──
  if [[ -f "$ov_conf" ]]; then
    rm -f "$ov_conf"
    log_ok "openviking-config.json removed from sandbox (legacy cleanup)"
  fi

  # ── 2. Remove injection block from template start.sh ──
  if [[ "$has_template" -eq 1 ]]; then
    backup_file "$tpl"
    python3 - "$tpl" << 'PYTPL'
import sys, re
path = sys.argv[1]
with open(path) as f:
    content = f.read()

# Pattern 1: "# 3. Enhanced 4-section AGENTS.md" through closing "fi" of AGENTS.md block
pattern_a = r'# 3\. Enhanced 4-section AGENTS\.md.*?fi\n'
new_content = re.sub(pattern_a, '', content, flags=re.DOTALL)

# Pattern 2: "# ── OpenViking MCP injection" marker through closing "fi"
pattern_b = r'# ── OpenViking MCP injection.*?fi\n'
new_content = re.sub(pattern_b, '', new_content, flags=re.DOTALL)

# Clean up any leftover openviking-config.json creation block (backward compat)
pattern_c = r'\n# 4\. openviking-config\.json.*?fi\n'
new_content = re.sub(pattern_c, '\n', new_content, flags=re.DOTALL)

# Also remove standalone AGENTS.md heredoc if present (from older integration)
pattern_d = r"# 3\. Enhanced 4-section AGENTS\.md.*?AGENTSMD\n"
new_content = re.sub(pattern_d, '', new_content, flags=re.DOTALL)

# Pattern 5: current native memory provider injection block (env exports + config
# re-apply heredoc + AGENTS.md heredoc), delimited by the AGENTSMD terminator.
pattern_e = r'# ── OpenViking native memory provider injection.*?AGENTSMD\n\n?'
new_content = re.sub(pattern_e, '', new_content, flags=re.DOTALL)

if new_content != content:
    with open(path, 'w') as f:
        f.write(new_content)
    print("Removed OpenViking blocks from template")
else:
    print("No OpenViking blocks found in template (already clean)")
PYTPL
    log_ok "Injection block removed from template start.sh"
  fi

  # ── 3. Sync template to sandbox ──
  if [[ -n "$sandbox" ]]; then
    for proc_dir in "${sandbox}/process_dir" "${sandbox}/.process_dir"; do
      if [[ -f "${proc_dir}/start.sh" ]]; then
        cp "$tpl" "${proc_dir}/start.sh"
        log_ok "Template synced to sandbox ${proc_dir}"
        break
      fi
    done
  fi

  log_ok "OpenViking removed from JiuwenSwarm"
  log_info "Restart JiuwenSwarm for changes to take effect"
}


# ── Status ───────────────────────────────────────────────────────────────────
agent_jiuwenswarm_status() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { echo "jiuwenswarm|unknown|sandbox not found"; return; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { echo "jiuwenswarm|unknown|config not found"; return; }

  local tpl="/root/template/jiuwenswarm/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true

  # Check live sandbox config for native memory provider + MCP server (dual-channel)
  local live_native=false live_mcp=false detail=""
  local cfg_engine=false cfg_provider=false
  grep -q "engine:.*both\|engine:.*external" "$cf" 2>/dev/null && cfg_engine=true
  { grep -q "provider:.*openviking\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null ||     { [[ -f "$tpl" ]] && grep -q "MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null; }; } && cfg_provider=true
  [[ "$cfg_engine" == "true" && "$cfg_provider" == "true" ]] && live_native=true

  # Detect MCP server (now part of dual-channel integration, not legacy)
  if grep -q "name: openviking" "$cf" 2>/dev/null; then
    live_mcp=true
  fi

  # Build detail string — dual-channel: native + MCP
  if [[ "$live_native" == "true" && "$live_mcp" == "true" ]]; then
    detail="native memory provider + MCP"
  elif [[ "$live_native" == "true" ]]; then
    detail="native memory provider only (MCP missing — re-integrate to add MCP)"
  elif [[ "$live_mcp" == "true" ]]; then
    detail="MCP only (native provider not configured)"
  fi

  if [[ "$tpl_has_ov" == "true" && ( "$live_native" == "true" || "$live_mcp" == "true" ) ]]; then
    echo "jiuwenswarm|integrated|$detail (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    echo "jiuwenswarm|integrated|template only, restart to activate"
  elif [[ "$live_native" == "true" || "$live_mcp" == "true" ]]; then
    echo "jiuwenswarm|partial|$detail (live only, lost on restart)"
  else
    echo "jiuwenswarm|not_integrated|No OpenViking integration found"
  fi
}

