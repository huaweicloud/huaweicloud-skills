#!/bin/bash
# =============================================================================
# lib/base.sh — Agent base class
# =============================================================================
# Defines the interface contract and shared operations that all agent
# subclasses inherit. In bash OO, "inheritance" means:
#   - Subclasses call base methods via agent::method_name
#   - Subclasses override by defining agent_<name>_<method>
#   - The registry dispatches to agent_<name>_<method>, falling back to
#     agent::default_<method> if the subclass doesn't override.
#
# Agent metadata is stored in a global associative array AGENT_META,
# populated by each subclass's agent_<name>_register() function.
#
# Key pattern: agent::<method>  = base class method (shared logic)
#              agent_<name>_<method> = subclass override (agent-specific)
# =============================================================================

# ── Template injection marker (shared by all agents) ─────────────────────────
OV_MARKER="added by huawei-cloud-openviking-agent-integration skill"
OV_MARKER_LEGACY="added by openviking-agent-integration skill"

# ── Agent metadata (global associative array) ────────────────────────────────
# Each subclass calls agent::set_meta to populate these fields:
#   name           — agent identifier (e.g. "codearts")
#   sandbox_pattern— pattern for find_sandbox (e.g. "codearts-*")
#   config_path    — relative path to config file within sandbox
#   template_path  — absolute path to template start.sh
#   mechanism      — integration mechanism (MCP, provider, plugin, etc.)
#   display_name   — human-readable name (e.g. "CodeArts CLI")
declare -gA AGENT_META

# ── Base class: metadata management ──────────────────────────────────────────
agent::set_meta() {
  # Usage: agent::set_meta key value
  AGENT_META["$1"]="$2"
}

agent::get_meta() {
  # Usage: agent::get_meta key → echoes value
  echo "${AGENT_META[$1]:-}"
}

agent::clear_meta() {
  AGENT_META=()
}

# ── Base class: sandbox discovery ────────────────────────────────────────────
# Find sandbox directory by pattern. All agents live in bwrap sandboxes
# under /root/job-envs/sandboxes/<pattern>.
agent::discover_sandbox() {
  local pattern="${AGENT_META[sandbox_pattern]:-$1}"
  find /root/job-envs/sandboxes/ -maxdepth 1 -type d -name "$pattern" -print -quit 2>/dev/null
}

# Legacy compat (some agent code calls find_sandbox directly)
find_sandbox() {
  find /root/job-envs/sandboxes/ -maxdepth 1 -type d -name "${1}-*" -print -quit 2>/dev/null
}

# ── Base class: file backup ──────────────────────────────────────────────────
agent::backup_config() {
  local f="$1"
  cp "$f" "${f}.bak.$(date +%s)"
}

# Legacy compat
backup_file() {
  cp "$1" "${1}.bak.$(date +%s)"
}

# ── Base class: authorization ────────────────────────────────────────────────
# Thin wrapper around require_confirmation, pre-filling the agent name.
agent::confirm() {
  local action="$1" details="$2"
  local color="${3:-$YELLOW}"
  require_confirmation "$action" "${AGENT_META[name]:-unknown}" "$details" "$color"
}

# ── Base class: template injection ───────────────────────────────────────────
# Check if a template file already has our injection marker.
agent::has_injection() {
  grep -v "MCP SDK install" "$1" 2>/dev/null | grep -q "$OV_MARKER\|$OV_MARKER_LEGACY"
}

# Legacy compat
has_ov_injection() {
  grep -v "MCP SDK install" "$1" 2>/dev/null | grep -q "$OV_MARKER\|$OV_MARKER_LEGACY"
}

# ── Base class: OpenViking health check ──────────────────────────────────────
# Globals used: OV_ENDPOINT
check_ov_health() {
  local endpoint="${OV_ENDPOINT:-http://127.0.0.1:1933}"
  local resp
  resp=$(curl -sf "${endpoint}/health" 2>/dev/null) || {
    log_error "OpenViking server not reachable at $endpoint"
    return 1
  }
  local status
  status=$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
  if [[ "$status" == "ok" ]]; then
    log_ok "OpenViking server healthy at $endpoint"
    return 0
  else
    log_error "OpenViking server unhealthy: $resp"
    return 1
  fi
}

# ── Base class: default interface (subclasses override these) ────────────────
# These are the "virtual methods" — each subclass should define its own
# agent_<name>_integrate / agent_<name>_unbind / agent_<name>_status.
# The base provides error stubs so unimplemented methods are caught clearly.

agent::default_integrate() {
  log_error "Agent '${AGENT_META[name]}' does not implement integrate()"
  return 1
}

agent::default_unbind() {
  log_error "Agent '${AGENT_META[name]}' does not implement unbind()"
  return 1
}

agent::default_status() {
  echo "${AGENT_META[name]:-unknown}|unknown|status not implemented"
}

# ── Base class: create_ov_config (shared by multiple agents) ─────────────────
# Creates openviking-config.json with official-equivalent behavior knobs.
# Used by codearts, opencode, and others that need the config file.
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
}
