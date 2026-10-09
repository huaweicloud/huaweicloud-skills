#!/bin/bash
# lib/json.sh — JSON utilities for agent config manipulation (delegates to py/ov_json.py)
: "${OV_PY_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")/../py" && pwd)}"
_ov_json() { "$OV_PY" "$OV_PY_DIR/ov_json.py" "$@"; }

# Check if a JSON config file has openviking MCP enabled
check_json_mcp() {
  _ov_json check-mcp "$1" 2>/dev/null
}
# Extract the openviking MCP URL from a JSON config file
get_json_mcp_url() {
  _ov_json get-mcp-url "$1" 2>/dev/null
}
# json_read <file> <dotted.key>          → print value (empty string if missing)
# json_read <file> <dotted.key> <default> → print default if missing
json_read() {
  local file="$1" key="$2" default="${3:-}"
  _ov_json read "$file" "$key" "$default" 2>/dev/null
}
# json_write <file> <dotted.key> <value>  → set value (creates intermediate dicts)
# value must be a JSON literal (e.g. '"string"', 'true', '42', 'null')
json_write() {
  local file="$1" key="$2" value="$3"
  _ov_json write "$file" "$key" "$value" 2>/dev/null
}
# json_has_key <file> <dotted.key> → exit 0 if key exists, 1 if not
json_has_key() {
  _ov_json has-key "$1" "$2" 2>/dev/null
}
# json_remove_key <file> <dotted.key> → remove key (no-op if missing)
json_remove_key() {
  local file="$1" key="$2"
  _ov_json remove-key "$file" "$key" 2>/dev/null
}
