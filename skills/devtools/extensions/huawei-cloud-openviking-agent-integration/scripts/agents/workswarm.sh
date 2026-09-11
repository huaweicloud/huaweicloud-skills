#!/bin/bash
# agents/jiuwenswarm.sh — WorkSwarm agent subclass (dual-channel: provider + MCP)
agent_workswarm_register() {
  agent::set_meta name "jiuwenswarm"
  agent::set_meta display_name "WorkSwarm"
  agent::set_meta sandbox_pattern "jiuwenswarm-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/jiuwenswarm/start.sh"
  agent::set_meta mechanism "Dual-channel: provider + MCP"
  registry_add "workswarm"
}

_jw_agents_md() {
  cat <<'JWAGENTS'
# Agent Instructions
## OpenViking Long-Term Memory
Dual-channel: (1) **Native memory provider** (`memory.engine: external`, `is_proactive: true`): auto-recalls/stores context. (2) **MCP server** (13 tools): `search`, `recall`, `find`, `read`, `remember`, `add_resource`, `grep`, `glob`, `forget`, `health`, `list`, `list_watches`, `cancel_watch`.
### Auto-Recall (conversation start)
Native engine auto-prefetches. For deeper: `search` (mode="context"), `recall` (type-quota), `find` (min_score=0).
### Proactive Search (during tasks)
1. `search` (mode="context") — past knowledge, solutions, decisions. 2. `recall` — structured type-quota. 3. `find` — fast ranked list. 4. `read` — expand viking:// URIs. 5. `grep`/`glob` — exact text/filename.
### Auto-Capture (after meaningful exchanges)
1. `remember` — user shares preferences/facts/decisions or asks to remember. 2. `add_resource` — import files/URLs/repos. 3. Never echo credentials.
### Repo Context
`add_resource` repo path to index; `search` for prior work.
JWAGENTS
}

_jw_mutate_config() {
  local action="$1" cfg="$2" mcp_url="${3:-}"
  "$OV_PY" - "$action" "$cfg" "$mcp_url" <<'JWMUT'
import sys, re
action, path, mcp_url = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding='utf-8') as f: content = f.read()
changed = False
if action == 'apply':
    new = re.sub(r'(engine:\s*\$\{MEMORY_ENGINE:-)builtin(\})', r'\1external\2', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(provider:\s*\$\{MEMORY_EXTERNAL_PROVIDER:-)(\})', r'\1openviking\2', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(auto_memory_enabled:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(proactive_recommendation:\s*\n\s*enabled:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    mcp_entry = "    - name: openviking\n      transport: streamable-http\n" + f"      url: {mcp_url}\n      enabled: true\n"
    if "name: openviking" not in content:
        new = re.sub(r'(mcp:\s*\n\s*servers:\s*)\[\]', lambda m: m.group(1) + "\n" + mcp_entry, content)
        if new != content: content = new; changed = True
        else:
            new = re.sub(r'(mcp:\s*\n\s*servers:\s*\n)(?!\s*-)', lambda m: m.group(1) + mcp_entry, content)
            if new != content: content = new; changed = True
            else:
                mcp_entry_2sp = "  - name: openviking\n    transport: streamable-http\n" + f"    url: {mcp_url}\n    enabled: true\n"
                new = re.sub(r'(mcp:\s*\n\s*servers:\n(?:  - name: [^\n]+\n(?:    [^\n]+\n)*)*)', lambda m: m.group(1) + mcp_entry_2sp, content, count=1)
                if new != content: content = new; changed = True
    if "    openviking:" not in content:
        ov_block = "    openviking:\n      endpoint: ${OPENVIKING_ENDPOINT:-http://127.0.0.1:1933}\n      api_key: ${OPENVIKING_API_KEY:-}\n      account: ${OPENVIKING_ACCOUNT:-default}\n      user: ${OPENVIKING_USER:-default}\n"
        new = re.sub(r'(  external:\s*\n(?:    [^\n]*\n)*?)(    lakebase:)', lambda m: m.group(1) + ov_block + m.group(2), content)
        if new != content: content = new; changed = True
    new = re.sub(r"(account:\s*\$\{OPENVIKING_ACCOUNT:-)root(\})", r"\1default\2", content)
    if new != content: content = new; changed = True
    if "viking_search: allow" not in content:
        viking_perms = "    viking_search: allow\n    viking_read: allow\n    viking_browse: allow\n    viking_remember: allow\n    viking_add_resource: allow\n"
        new = re.sub(r'(    mem0_conclude: allow\n)', lambda m: m.group(1) + viking_perms, content)
        if new != content: content = new; changed = True
    new = re.sub(r'(fast:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    if re.search(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n)(?!\s*is_proactive)', content):
        new = re.sub(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n)(?!\s*is_proactive)', r'\1      is_proactive: true\n', content)
        if new != content: content = new; changed = True
    new = re.sub(r'(memory:\s*\n\s*enabled:\s*)false(\s*\n\s*scenario:)', r'\1true\2', content)
    if new != content: content = new; changed = True
    if changed:
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
elif action == 'revert':
    # Match both 4-space (apply attempt 1/2) and 2-space (apply attempt 3) indent
    content = re.sub(r'    - name: openviking\n(?:      .+\n)+', '', content, count=1)
    content = re.sub(r'  - name: openviking\n(?:    .+\n)+', '', content, count=1)
    # Only collapse to [] if no server entries remain (skip blank lines)
    if not re.search(r'  servers:\n(?:\s*\n)*  *- ', content):
        content = re.sub(r'  servers:\n(?:\s*\n)*', '  servers: []\n', content, count=1)
    content = content.replace("  servers: []\n\n  # 示例", "  servers: []\n  # 示例")
    content = re.sub(r'(engine:\s*\$\{MEMORY_ENGINE:-)(?:both|external)(\})', r'\1builtin\2', content)
    content = re.sub(r'(provider:\s*\$\{MEMORY_EXTERNAL_PROVIDER:-)openviking(\})', r'\1\2', content)
    content = re.sub(r'(\n    openviking:\n(?:      [^\n]*\n)+)', '\n', content)
    for perm in ('viking_search', 'viking_read', 'viking_browse', 'viking_remember', 'viking_add_resource'):
        content = re.sub(r'\n    ' + perm + r': allow\b', '', content)
    content = re.sub(r'(auto_memory_enabled:\s*)true', r'\1false', content)
    content = re.sub(r'(proactive_recommendation:\s*\n\s*enabled:\s*)true', r'\1false', content)
    content = re.sub(r'(fast:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)true', r'\1false', content)
    content = re.sub(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)true', r'\1false', content)
    content = re.sub(r'(memory:\s*\n\s*enabled:\s*)true(\s*\n\s*scenario:)', r'\1false\2', content)
    with open(path, 'w', encoding='utf-8') as f: f.write(content)
JWMUT
}

_jw_patch_iface_apply() {
  local file="$1"
  "$OV_PY" - "$file" <<'PYPATCH'
import sys, re
path = sys.argv[1]
with open(path) as f: content = f.read()
pattern = r'(                logger\.info\(\n                    "\[JiuwenSwarmCodeAdapter\] CodingMemoryRail \(re\)registered for %s",\n                    mode,\n                \)\n)\n+(    def _build_code_agent_rail)'
replacement = r'\1\n        # code-mode ExternalMemoryRail (openviking-agent-integration)\n        await self._handle_external_memory_rail_by_config()\n\n\2'
if re.search(pattern, content):
    content = re.sub(pattern, replacement, content, count=1)
    with open(path, 'w') as f: f.write(content)
PYPATCH
}

_jw_patch_iface_revert() {
  local file="$1"
  "$OV_PY" - "$file" <<'PYUNPATCH'
import sys, re
path = sys.argv[1]
with open(path) as f: content = f.read()
content = re.sub(r'\n        # code-mode ExternalMemoryRail \(openviking-agent-integration\)\n        await self\._handle_external_memory_rail_by_config\(\)\n+', '\n', content, flags=re.DOTALL)
with open(path, 'w') as f: f.write(content)
PYUNPATCH
}

_jw_patch_prov_apply() {
  local file="$1"
  "$OV_PY" - "$file" <<'PYPROV'
import sys
path = sys.argv[1]
with open(path) as f: content = f.read()
content = content.replace('{"query": query, "top_k": 5},', '{"query": query, "limit": 5},  # ov-fix-limit').replace('payload["top_k"] = args["limit"]', 'payload["limit"] = args["limit"]  # ov-fix-limit')
with open(path, 'w') as f: f.write(content)
PYPROV
}

_jw_patch_prov_revert() {
  local file="$1"
  "$OV_PY" - "$file" <<'PYPROVUN'
import sys
path = sys.argv[1]
with open(path) as f: content = f.read()
content = content.replace('{"query": query, "limit": 5},  # ov-fix-limit', '{"query": query, "top_k": 5},').replace('payload["limit"] = args["limit"]  # ov-fix-limit', 'payload["top_k"] = args["limit"]')
with open(path, 'w') as f: f.write(content)
PYPROVUN
}

agent_workswarm_integrate() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { log_error "WorkSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }
  local tpl="${AGENT_META[template_path]}"
  local already=false
  if grep -q "MEMORY_ENGINE:-both\|MEMORY_ENGINE:-external\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null; then
    already=true
  elif [[ -f "$tpl" ]] && grep -q "MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null; then
    already=true
  fi
  if [[ "$already" == "true" ]]; then
    if [[ -f "$tpl" ]] && grep -q "OpenViking native memory provider injection\|ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null; then
      if grep -q "OPENVIKING_ACCOUNT:-root" "$cf" 2>/dev/null; then
        sed -i "s/OPENVIKING_ACCOUNT:-root/OPENVIKING_ACCOUNT:-default/" "$cf"
      fi
      return 0
    fi
  fi
  require_confirmation "Integrate OpenViking" "workswarm" "Add OpenViking native memory provider + MCP server to sandbox config + template start.sh" || return 1
  if dry_run_msg "Would add OpenViking native memory provider + MCP server to $cf and $tpl"; then return 0; fi
  backup_file "$cf"
  _jw_mutate_config apply "$cf" "$OV_MCP_URL"
  if [[ -f "$tpl" ]] && ! grep -q "OpenViking native memory provider injection\|ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null; then
    backup_file "$tpl"
    local _agents_tmp; _agents_tmp=$(mktemp)
    _jw_agents_md > "$_agents_tmp"
    "$OV_PY" - "$tpl" "$OV_ENDPOINT" "$OV_MCP_URL" "$_agents_tmp" "$OV_SHARED_DIR" "$OV_TEMPLATE_DIR" "$OV_RUNTIME_DIR" <<'PYTPL'
import sys, os
path, endpoint, mcp_url, agents_md_path, shared_dir, template_dir, runtime_dir = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7]
with open(path) as f: lines = f.readlines()
marker = "# ── OpenViking native memory provider injection (added by huawei-cloud-openviking-agent-integration skill) ──"
agents_md = open(agents_md_path).read()
block = marker + """
export MEMORY_ENGINE=external
export MEMORY_EXTERNAL_PROVIDER=openviking
export OPENVIKING_ENDPOINT="__OV_EP__"
export OPENVIKING_AGENT=jiuwenswarm
OV_PY="${OV_PY:-$(command -v python3 2>/dev/null || command -v python3.11 2>/dev/null || echo __OV_RT__/jiuwenswarm/bin/python3.11)}"
JW_CFG="$JIUWENSWARM_DATA_DIR/config/config.yaml"
if [ -f "$JW_CFG" ]; then
  $OV_PY - "$JW_CFG" "__OV_MCP__" << 'PYJW2'
import sys, re
path = sys.argv[1]
mcp_url = sys.argv[2]
with open(path) as f: content = f.read()
changed = False
new = re.sub(r'(engine:\\s*\\$\\{MEMORY_ENGINE:-)builtin(\\})', r'\\1external\\2', content)
if new != content: content = new; changed = True
new = re.sub(r'(provider:\\s*\\$\\{MEMORY_EXTERNAL_PROVIDER:-)(\\})', r'\\1openviking\\2', content)
if new != content: content = new; changed = True
new = re.sub(r'(auto_memory_enabled:\\s*)false', r'\\1true', content)
if new != content: content = new; changed = True
new = re.sub(r'(proactive_recommendation:\\s*\\n\\s*enabled:\\s*)false', r'\\1true', content)
if new != content: content = new; changed = True
mcp_entry = "    - name: openviking\\n      transport: streamable-http\\n" + f"      url: {mcp_url}\\n      enabled: true\\n"
if "name: openviking" not in content:
    new = re.sub(r'(mcp:\\s*\\n\\s*servers:\\s*)\\[\\]', lambda m: m.group(1) + "\\n" + mcp_entry, content)
    if new != content: content = new; changed = True
    else:
        new = re.sub(r'(mcp:\\s*\\n\\s*servers:\\s*\\n)(?!\\s*-)', lambda m: m.group(1) + mcp_entry, content)
        if new != content: content = new; changed = True
        else:
            mcp_entry_2sp = "  - name: openviking\\n    transport: streamable-http\\n" + f"    url: {mcp_url}\\n    enabled: true\\n"
            new = re.sub(r'(mcp:\\s*\\n\\s*servers:\\n(?:  - name: [^\\n]+\\n(?:    [^\\n]+\\n)*)*)', lambda m: m.group(1) + mcp_entry_2sp, content, count=1)
            if new != content: content = new; changed = True
if "    openviking:" not in content:
    ov_block = "    openviking:\\n      endpoint: ${OPENVIKING_ENDPOINT:-http://127.0.0.1:1933}\\n      api_key: ${OPENVIKING_API_KEY:-}\\n      account: ${OPENVIKING_ACCOUNT:-default}\\n      user: ${OPENVIKING_USER:-default}\\n"
    new = re.sub(r'(  external:\\s*\\n(?:    [^\\n]*\\n)*?)(    lakebase:)', lambda m: m.group(1) + ov_block + m.group(2), content)
    if new != content: content = new; changed = True
new = re.sub(r"(account:\\s*\\$\\{OPENVIKING_ACCOUNT:-)root(\\})", r"\\1default\\2", content)
if new != content: content = new; changed = True
if "viking_search: allow" not in content:
    viking_perms = "    viking_search: allow\\n    viking_read: allow\\n    viking_browse: allow\\n    viking_remember: allow\\n    viking_add_resource: allow\\n"
    new = re.sub(r'(    mem0_conclude: allow\\n)', lambda m: m.group(1) + viking_perms, content)
    if new != content: content = new; changed = True
new = re.sub(r'(fast:\\s*\\n\\s*memory:\\s*\\n\\s*enabled:\\s*true\\s*\\n\\s*is_proactive:\\s*)false', r'\\1true', content)
if new != content: content = new; changed = True
if re.search(r'(code:\\s*\\n\\s*memory:\\s*\\n\\s*enabled:\\s*true\\s*\\n)(?!\\s*is_proactive)', content):
    new = re.sub(r'(code:\\s*\\n\\s*memory:\\s*\\n\\s*enabled:\\s*true\\s*\\n)(?!\\s*is_proactive)', r'\\1      is_proactive: true\\n', content)
    if new != content: content = new; changed = True
new = re.sub(r'(memory:\\s*\\n\\s*enabled:\\s*)false(\\s*\\n\\s*scenario:)', r'\\1true\\2', content)
if new != content: content = new; changed = True
if changed:
    with open(path, 'w') as f: f.write(content)
PYJW2
fi
JW_IFACE=$(find __OV_RT__/jiuwenswarm -path '*/agent_adapter/interface_code.py' ! -path '*__pycache__*' 2>/dev/null | head -1)
if [ -n "$JW_IFACE" ] && ! grep -q 'code-mode ExternalMemoryRail' "$JW_IFACE" 2>/dev/null; then
  $OV_PY -c 'p=__import__("sys").argv[1];c=open(p).read();m="    def _build_code_agent_rail";n="\\n        # code-mode ExternalMemoryRail (openviking-agent-integration)\\n        await self._handle_external_memory_rail_by_config()\\n"+m;open(p,"w").write(c.replace(m,n,1)) if m in c else None' "$JW_IFACE" 2>/dev/null
  find __OV_RT__/jiuwenswarm -path '*__pycache__*interface_code*' -delete 2>/dev/null
fi
JW_PROV=$(find __OV_RT__/jiuwenswarm -path '*/memory/external/openviking_memory_provider.py' ! -path '*__pycache__*' 2>/dev/null | head -1)
if [ -n "$JW_PROV" ] && ! grep -q 'ov-fix-limit' "$JW_PROV" 2>/dev/null; then
  $OV_PY -c 'p=__import__("sys").argv[1];q=chr(34);c=open(p).read();c=c.replace(q+"top_k"+q+": 5},",q+"limit"+q+": 5},  # ov-fix-limit").replace("payload["+q+"top_k"+q+"] = args["+q+"limit"+q+"]","payload["+q+"limit"+q+"] = args["+q+"limit"+q+"]  # ov-fix-limit");open(p,"w").write(c) if c!=open(p).read() else None' "$JW_PROV" 2>/dev/null
  find __OV_RT__/jiuwenswarm -path '*__pycache__*openviking_memory_provider*' -delete 2>/dev/null
fi
mkdir -p /workspace
cat > /workspace/AGENTS.md << 'AGENTSMD'
__AGENTS_MD__
AGENTSMD
"""
block = block.replace("__AGENTS_MD__", agents_md).replace("__OV_EP__", endpoint).replace("__OV_MCP__", mcp_url).replace("__OV_RT__", runtime_dir)
init_path = f"{shared_dir}/ov-jiuwenswarm-init.sh"
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n# ── OpenViking integration for WorkSwarm ──\n")
    f.write(f"# Sourced by {template_dir}/jiuwenswarm/start.sh (single source line).\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block)
os.chmod(init_path, 0o755)
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-jiuwenswarm-init.sh\n# ── End OpenViking integration ──\n"
inserted = False
for i, line in enumerate(lines):
    if 'nohup' in line and 'jiuwenswarm-start' in line:
        lines.insert(i, source_block)
        inserted = True
        break
if not inserted:
    for i, line in enumerate(lines):
        if line.strip() == 'sleep infinity' or line.strip().startswith('sleep infinity'):
            lines.insert(i, source_block)
            break
with open(path, 'w') as f: f.writelines(lines)
PYTPL
    rm -f "$_agents_tmp"
  fi
  mkdir -p "${sandbox}/workspace"
  _jw_agents_md > "${sandbox}/workspace/AGENTS.md"
  local jw_iface; jw_iface=$(ov_find_runtime_file "*/jiuwenswarm*/agent_adapter/interface_code.py")
  ov_patch_apply "$jw_iface" "code-mode ExternalMemoryRail" \
    "Code-mode ExternalMemoryRail patch" _jw_patch_iface_apply || true
  local jw_prov; jw_prov=$(ov_find_runtime_file "*/jiuwenswarm*/memory/external/openviking_memory_provider.py")
  ov_patch_apply "$jw_prov" "ov-fix-limit" \
    "Provider top_k→limit patch" _jw_patch_prov_apply || true
}

agent_workswarm_unbind() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { log_error "WorkSwarm sandbox not found"; return 1; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { log_error "Config not found: $cf"; return 1; }
  local tpl="${AGENT_META[template_path]}"
  local ov_conf="${sandbox}/.config/opencode/openviking-config.json"
  local has_sandbox=0 has_template=0
  grep -q "name: openviking\|openviking:\|viking_search\|MEMORY_ENGINE:-both\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null && has_sandbox=1
  [[ -f "$ov_conf" ]] && has_sandbox=1
  [[ -f "$tpl" ]] && grep -q "OpenViking\|openviking-config\|Enhanced 4-section AGENTS\|MEMORY_EXTERNAL_PROVIDER=openviking\|ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null && has_template=1
  if [[ "$has_sandbox" -eq 0 && "$has_template" -eq 0 ]]; then
    return 0
  fi
  require_confirmation "UNBIND OpenViking" "workswarm" "Remove OpenViking native memory provider (+ legacy MCP if present) from sandbox and template" "$RED" || return 1
  if dry_run_msg "Would remove OpenViking from $cf and $tpl"; then return 0; fi
  if [[ "$has_sandbox" -eq 1 ]]; then
    backup_file "$cf"
    _jw_mutate_config revert "$cf"
  fi
  if [[ -f "$ov_conf" ]]; then
    rm -f "$ov_conf"
  fi
  if [[ "$has_template" -eq 1 ]]; then
    backup_file "$tpl"
    "$OV_PY" - "$tpl" "$OV_SHARED_DIR" <<'PYTPL'
import sys, re
path, shared_dir = sys.argv[1], sys.argv[2]
with open(path) as f: content = f.read()
new = re.sub(rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\nsource {shared_dir}/ov-jiuwenswarm-init\.sh\n# ── End OpenViking integration ──\n\n?', '', content)
new = re.sub(r'# 3\. Enhanced 4-section AGENTS\.md.*?fi\n', '', new, flags=re.DOTALL)
new = re.sub(r'# ── OpenViking MCP injection.*?fi\n', '', new, flags=re.DOTALL)
new = re.sub(r'\n# 4\. openviking-config\.json.*?fi\n', '\n', new, flags=re.DOTALL)
new = re.sub(r"# 3\. Enhanced 4-section AGENTS\.md.*?AGENTSMD\n", '', new, flags=re.DOTALL)
new = re.sub(r'# ── OpenViking native memory provider injection.*?AGENTSMD\n\n?', '', new, flags=re.DOTALL)
if new != content:
    with open(path, 'w') as f: f.write(new)
PYTPL
    rm -f "$OV_SHARED_DIR/ov-jiuwenswarm-init.sh"
  fi
  local jw_iface; jw_iface=$(ov_find_runtime_file "*/jiuwenswarm*/agent_adapter/interface_code.py")
  ov_patch_revert "$jw_iface" "code-mode ExternalMemoryRail" \
    "Code-mode ExternalMemoryRail patch" _jw_patch_iface_revert || true
  local jw_prov; jw_prov=$(ov_find_runtime_file "*/jiuwenswarm*/memory/external/openviking_memory_provider.py")
  ov_patch_revert "$jw_prov" "ov-fix-limit" \
    "Provider top_k→limit patch" _jw_patch_prov_revert || true
  if [[ -n "$sandbox" ]]; then
    for proc_dir in "${sandbox}/process_dir" "${sandbox}/.process_dir"; do
      if [[ -f "${proc_dir}/start.sh" ]]; then
        cp "$tpl" "${proc_dir}/start.sh"
        break
      fi
    done
  fi
}

agent_workswarm_status() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { ov_status "workswarm" "unknown" "sandbox not found"; return; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { ov_status "workswarm" "unknown" "config not found"; return; }
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true
  grep -q "ov-jiuwenswarm-init.sh" "$tpl" 2>/dev/null && tpl_has_ov=true
  local live_native=false live_mcp=false detail=""
  local cfg_engine=false cfg_provider=false
  grep -q "engine:.*both\|engine:.*external" "$cf" 2>/dev/null && cfg_engine=true
  { grep -q "provider:.*openviking\|MEMORY_EXTERNAL_PROVIDER:-openviking" "$cf" 2>/dev/null || \
    { [[ -f "$tpl" ]] && grep -q "MEMORY_EXTERNAL_PROVIDER=openviking" "$tpl" 2>/dev/null; }; } && cfg_provider=true
  [[ "$cfg_engine" == "true" && "$cfg_provider" == "true" ]] && live_native=true
  if grep -q "name: openviking" "$cf" 2>/dev/null; then
    live_mcp=true
  fi
  if [[ "$live_native" == "true" && "$live_mcp" == "true" ]]; then
    detail="native memory provider + MCP"
  elif [[ "$live_native" == "true" ]]; then
    detail="native memory provider only (MCP missing — re-integrate to add MCP)"
  elif [[ "$live_mcp" == "true" ]]; then
    detail="MCP only (native provider not configured)"
  fi
  local jw_iface jw_prov
  jw_iface=$(ov_find_runtime_file "*/jiuwenswarm*/agent_adapter/interface_code.py")
  jw_prov=$(ov_find_runtime_file "*/jiuwenswarm*/memory/external/openviking_memory_provider.py")
  if [[ -n "$detail" && ( -n "$jw_iface" || -n "$jw_prov" ) ]]; then
    local iface_mark prov_mark
    iface_mark=$(ov_patch_mark "$jw_iface" "code-mode ExternalMemoryRail")
    prov_mark=$(ov_patch_mark "$jw_prov" "ov-fix-limit")
    detail+=" | patches: iface${iface_mark} prov${prov_mark}"
  fi
  if [[ "$tpl_has_ov" == "true" && ( "$live_native" == "true" || "$live_mcp" == "true" ) ]]; then
    ov_status "workswarm" "integrated" "$detail (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    ov_status "workswarm" "integrated" "template only, restart to activate"
  elif [[ "$live_native" == "true" || "$live_mcp" == "true" ]]; then
    ov_status "workswarm" "partial" "$detail (live only, lost on restart)"
  else
    ov_status "workswarm" "not_integrated" "No OpenViking integration found"
  fi
}
