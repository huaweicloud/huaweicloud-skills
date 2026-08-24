#!/bin/bash
# =============================================================================
# lib/json.sh — JSON utilities for agent config file manipulation
# Part of the OO refactoring. Provides both legacy compat functions and
# generic read/write/has/remove helpers.
# =============================================================================

# ── Legacy compat (used by existing agent code) ───────────────────────────────
# Check if a JSON config file has openviking MCP enabled
check_json_mcp() {
  python3 -c "import json; cfg=json.load(open('$1')); exit(0 if cfg.get('mcp',{}).get('openviking',{}).get('enabled') else 1)" 2>/dev/null
}

# Extract the openviking MCP URL from a JSON config file
get_json_mcp_url() {
  python3 -c "import json; cfg=json.load(open('$1')); print(cfg.get('mcp',{}).get('openviking',{}).get('url',''))" 2>/dev/null
}

# ── Generic JSON helpers ──────────────────────────────────────────────────────
# json_read <file> <dotted.key>          → print value (empty string if missing)
# json_read <file> <dotted.key> <default> → print default if missing
# Example: json_read config.json mcp.openviking.url
json_read() {
  local file="$1" key="$2" default="${3:-}"
  python3 -c "
import json, sys
with open('$file') as f: cfg = json.load(f)
val = cfg
for k in '$key'.split('.'):
    if isinstance(val, dict) and k in val: val = val[k]
    else: val = None; break
print(val if val is not None else '$default')
" 2>/dev/null
}

# json_write <file> <dotted.key> <value>  → set value (creates intermediate dicts)
# Example: json_write config.json mcp.openviking.enabled true
json_write() {
  local file="$1" key="$2" value="$3"
  python3 -c "
import json
with open('$file') as f: cfg = json.load(f)
keys = '$key'.split('.')
d = cfg
for k in keys[:-1]:
    d = d.setdefault(k, {})
d[keys[-1]] = $value
with open('$file', 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
" 2>/dev/null
}

# json_has_key <file> <dotted.key> → exit 0 if key exists, 1 if not
json_has_key() {
  python3 -c "
import json
with open('$1') as f: cfg = json.load(f)
val = cfg
for k in '$2'.split('.'):
    if isinstance(val, dict) and k in val: val = val[k]
    else: sys.exit(1)
sys.exit(0)
" 2>/dev/null
}

# json_remove_key <file> <dotted.key> → remove key (no-op if missing)
# Example: json_remove_key config.json mcp.openviking
json_remove_key() {
  local file="$1" key="$2"
  python3 -c "
import json
with open('$file') as f: cfg = json.load(f)
keys = '$key'.split('.')
d = cfg
for k in keys[:-1]:
    if k not in d: sys.exit(0)
    d = d[k]
d.pop(keys[-1], None)
with open('$file', 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
" 2>/dev/null
}
