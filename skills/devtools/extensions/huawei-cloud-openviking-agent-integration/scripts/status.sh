#!/bin/bash
# =============================================================================
# OpenViking Integration Status Check
# Usage: ./status.sh [--json]
# =============================================================================
set -euo pipefail
source "$(dirname "$0")/common.sh"

OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
JSON_OUTPUT=false
[[ "${1:-}" == "--json" ]] && JSON_OUTPUT=true

# ── Check OpenViking server ───────────────────────────────────────────────────
check_ov() {
  local resp status version auth_mode
  resp=$(curl -sf "${OV_ENDPOINT}/health" 2>/dev/null) || {
    if [[ "$JSON_OUTPUT" == "true" ]]; then
      echo '{"status":"unreachable","endpoint":"'"$OV_ENDPOINT"'"}'
    else
      echo -e "${RED}✗${NC} OpenViking server unreachable at $OV_ENDPOINT"
    fi
    return 1
  }
  status=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null)
  version=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version','unknown'))" 2>/dev/null)
  auth_mode=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('auth_mode','unknown'))" 2>/dev/null)
  
  if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "{\"status\":\"$status\",\"version\":\"$version\",\"auth_mode\":\"$auth_mode\",\"endpoint\":\"$OV_ENDPOINT\"}"
  else
    echo -e "${GREEN}✓${NC} OpenViking server: $status (v$version, auth=$auth_mode) at $OV_ENDPOINT"
  fi
}

# ── Agent checks ──────────────────────────────────────────────────────────────
check_codearts() {
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

check_opencode() {
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

  # Check for plugin SDK installed via npm or legacy embedded plugin files
  local plugin_installed=false
  if [[ -d "${sandbox}/.config/opencode/node_modules/@opencode-ai" ]]; then
    plugin_installed=true
  elif [[ -f "${sandbox}/.config/opencode/plugins/openviking.js" ]]; then
    plugin_installed=true
  fi

  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    if [[ "$plugin_installed" == "true" ]]; then
      echo "opencode|integrated|Official @openviking/opencode-plugin (npm, Huawei Cloud mirror, template + live)"
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

check_openclaw() {
  local tpl="/root/template/openclaw/start.sh"

  # Check official plugin install injection in template start.sh (current method)
  local has_plugin=false
  if [[ -f "$tpl" ]] && grep -qE "# ── Step 5(\.[0-9]+)?:.*[Oo]pen[Vv]iking" "$tpl" 2>/dev/null; then
    has_plugin=true
  fi

  # Check legacy direct-config-write injection (backward compatibility)
  local has_legacy_cfg=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking plugin config" "$tpl" 2>/dev/null; then
    has_legacy_cfg=true
  fi

  # Check legacy MCP injection (backward compatibility)
  local has_mcp=false
  if [[ -f "$tpl" ]] && grep -q "OpenViking MCP server injected" "$tpl" 2>/dev/null; then
    has_mcp=true
  fi

  # Check for legacy plugin extension artifacts
  local has_legacy=false
  for ext_dir in /root/.openclaw/extensions/openviking /root/runtime/openclaw/state/extensions/openviking; do
    [[ -d "$ext_dir" ]] && has_legacy=true
  done

  if [[ "$has_plugin" == "true" ]]; then
    echo "openclaw|integrated|Official plugin install in start.sh (npm, Huawei Cloud mirror, contextEngine slot) ✓"
  elif [[ "$has_legacy_cfg" == "true" ]]; then
    echo "openclaw|partial|Legacy direct-config-write found — run integrate to upgrade to official plugin install"
  elif [[ "$has_mcp" == "true" ]]; then
    echo "openclaw|partial|Legacy MCP injection found — run integrate to upgrade to official plugin install"
  elif [[ "$has_legacy" == "true" ]]; then
    echo "openclaw|partial|Legacy plugin artifacts found — run unbind to clean"
  else
    echo "openclaw|not_integrated|No OpenViking integration found"
  fi
}


check_hermes() {
  local tpl="/root/template/hermes/start.sh"
  local tpl_has_ov=false
  has_ov_injection "$tpl" 2>/dev/null && tpl_has_ov=true

  local sandbox; sandbox=$(find_sandbox "hermes")
  [[ -z "$sandbox" ]] && { echo "hermes|unknown|sandbox not found"; return; }
  local cf="${sandbox}/.hermes/config.yaml"
  local sandbox_has_ov=false
  [[ -f "$cf" ]] && grep -q "openviking" "$cf" 2>/dev/null && sandbox_has_ov=true

  if [[ "$tpl_has_ov" == "true" && "$sandbox_has_ov" == "true" ]]; then
    echo "hermes|integrated|MCP (template + live)"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    echo "hermes|integrated|MCP configured (template only, restart to activate)"
  elif [[ "$sandbox_has_ov" == "true" ]]; then
    echo "hermes|partial|MCP (live only, lost on restart)"
  else
    echo "hermes|not_integrated|No OpenViking MCP"
  fi
}

check_jiuwenswarm() {
  local sandbox; sandbox=$(find_sandbox "jiuwenswarm")
  [[ -z "$sandbox" ]] && { echo "jiuwenswarm|unknown|sandbox not found"; return; }
  local cf="${sandbox}/.jiuwenswarm/config/config.yaml"
  [[ ! -f "$cf" ]] && { echo "jiuwenswarm|unknown|config not found"; return; }
  
  if grep -q "name: openviking" "$cf" 2>/dev/null; then
    local url
    url=$(grep -A5 "name: openviking" "$cf" | grep "url:" | head -1 | awk '{print $2}')
    echo "jiuwenswarm|integrated|MCP: ${url:-http://127.0.0.1:1933/mcp}"
  else
    echo "jiuwenswarm|not_integrated|No OpenViking MCP server in mcp.servers"
  fi
}

check_kimicode() {
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

check_deepseek_harness() {
  local tpl="/root/template/deepseek-harness/start.sh"
  local tpl_has_ov=false
  grep -q "OpenViking long-term memory integration" "$tpl" 2>/dev/null && tpl_has_ov=true

  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { echo "deepseek-harness|unknown|sandbox not found"; return; }
  local live_has_ov=false
  local live_scope=""
  if [[ -f "${sandbox}/.dsh/profiles/web/cordis.patch.yml" ]] && grep -q "mcp-openviking" "${sandbox}/.dsh/profiles/web/cordis.patch.yml" 2>/dev/null; then
    live_has_ov=true; live_scope="web"
  fi
  if [[ -f "${sandbox}/.dsh/profiles/cc-tui/cordis.patch.yml" ]] && grep -q "mcp-openviking" "${sandbox}/.dsh/profiles/cc-tui/cordis.patch.yml" 2>/dev/null; then
    live_has_ov=true; live_scope="${live_scope:+$live_scope,}cc-tui"
  fi
  local skill_ok=false
  [[ -f "${sandbox}/.dsh/skills/openviking/SKILL.md" ]] && skill_ok=true
  local cfg_ok=false
  [[ -f "${sandbox}/.dsh/openviking-config.json" ]] && cfg_ok=true
  local web_guidance=false
  if [[ -f "${sandbox}/.dsh/profiles/web/cordis.patch.yml" ]] \
     && grep -q "agent-instructions" "${sandbox}/.dsh/profiles/web/cordis.patch.yml" 2>/dev/null \
     && grep -q "mcp__openviking__" "${sandbox}/.dsh/profiles/web/cordis.patch.yml" 2>/dev/null; then
    web_guidance=true
  fi

  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    echo "deepseek-harness|integrated|MCP (template + live profiles: ${live_scope:-none}, skill: $([[ $skill_ok == true ]] && echo yes || echo no), config: $([[ $cfg_ok == true ]] && echo yes || echo no), web-guidance: $([[ $web_guidance == true ]] && echo yes || echo no))"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    echo "deepseek-harness|integrated|MCP configured (template only, restart to activate)"
  elif [[ "$live_has_ov" == "true" ]]; then
    echo "deepseek-harness|partial|MCP (live profiles: ${live_scope:-none}, lost on restart)"
  else
    echo "deepseek-harness|not_integrated|No OpenViking MCP"
  fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
if [[ "$JSON_OUTPUT" == "true" ]]; then
  echo '{"openviking":'
  check_ov
  echo ',"agents":['
else
  echo "━━━ OpenViking Integration Status ━━━"
  echo ""
  check_ov
  echo ""
  echo "━━━ Agent Integration Status ━━━"
  echo ""
fi

first=true
for agent in codearts opencode openclaw hermes jiuwenswarm kimicode deepseek-harness; do
  fn="check_${agent//-/_}"
  result=$($fn)
  name=""; status=""; desc=""
  IFS='|' read -r name status desc <<< "$result"
  
  if [[ "$JSON_OUTPUT" == "true" ]]; then
    [[ "$first" == "true" ]] || echo ","
    echo -n "{\"agent\":\"$name\",\"status\":\"$status\",\"detail\":\"$desc\"}"
    first=false
  else
    icon=""
    case "$status" in
      integrated)     icon="${GREEN}✓${NC}" ;;
      not_integrated) icon="${RED}✗${NC}" ;;
      partial)        icon="${YELLOW}⚠${NC}" ;;
      *)              icon="${YELLOW}?${NC}" ;;
    esac
    printf "  %b %-14s %s\n" "$icon" "$name" "$desc"
  fi
done

if [[ "$JSON_OUTPUT" == "true" ]]; then
  echo ']}'
else
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
