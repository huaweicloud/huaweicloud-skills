#!/bin/bash
# =============================================================================
# lib/registry.sh — Agent registry (factory + dispatcher)
# =============================================================================
# Implements the Registry pattern: auto-discovers agent subclasses from
# the agents/ directory, provides listing, validation, and dispatch.
#
# Design:
#   - Each agent file in agents/ defines agent_<name>_register() which
#     calls agent::set_meta to populate AGENT_META, then registers itself
#     by appending its name to the global REGISTRY_AGENTS array.
#   - registry_dispatch(agent, method) calls agent_<agent>_<method>(),
#     falling back to agent::default_<method>() if the subclass doesn't
#     define an override.
# =============================================================================

# Global registry state
declare -ga REGISTRY_AGENTS=()
declare -gA REGISTRY_LOADED=()

# ── Registry: initialize ─────────────────────────────────────────────────────
registry_init() {
  REGISTRY_AGENTS=()
  REGISTRY_LOADED=()
}

# ── Registry: normalize agent name ───────────────────────────────────────────
# Maps user-facing names (with hyphens) to internal names (with underscores).
# Example: "deepseek-harness" → "deepseek_harness", "prime-agent" → "prime_agent"
registry_normalize() {
  local name="$1"
  # Try exact match first
  local existing
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$name" ]] && { echo "$name"; return 0; }
  done
  # Try hyphen→underscore mapping
  local normalized="${name//-/_}"
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$normalized" ]] && { echo "$normalized"; return 0; }
  done
  # No match — return original (will fail validation)
  echo "$name"
  return 1
}

# ── Registry: discover all agents ────────────────────────────────────────────
# Scans the agents/ directory and sources each .sh file.
# Each file's agent_<name>_register() is called to self-register.
registry_discover() {
  local agents_dir="${1:-$(dirname "${BASH_SOURCE[0]}")/../agents}"
  local f name

  for f in "$agents_dir"/*.sh; do
    [[ -f "$f" ]] || continue
    name=$(basename "$f" .sh)
    [[ -n "${REGISTRY_LOADED[$name]:-}" ]] && continue

    # Source the agent file (defines agent_<name>_* functions)
    # shellcheck disable=SC1090
    source "$f"
    REGISTRY_LOADED["$name"]=1

    # Call the register function if it exists
    local reg_fn="agent_${name}_register"
    if declare -f "$reg_fn" &>/dev/null; then
      agent::clear_meta
      "$reg_fn"
      # The register function should have called registry_add
    fi
  done
}

# ── Registry: add an agent ───────────────────────────────────────────────────
# Called by each agent's _register() function.
registry_add() {
  local name="$1"
  # Avoid duplicates
  local existing
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$name" ]] && return 0
  done
  REGISTRY_AGENTS+=("$name")
}

# ── Registry: list all agent names ───────────────────────────────────────────
registry_list() {
  printf '%s\n' "${REGISTRY_AGENTS[@]}"
}

# ── Registry: count agents ───────────────────────────────────────────────────
registry_count() {
  echo "${#REGISTRY_AGENTS[@]}"
}

# ── Registry: validate agent name ────────────────────────────────────────────
# Returns 0 if agent is registered, 1 otherwise.
# Accepts both hyphenated (deepseek-harness) and underscored (deepseek_harness) forms.
registry_validate() {
  local target="$1"
  target=$(registry_normalize "$target")
  local existing
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$target" ]] && return 0
  done
  return 1
}

# ── Registry: dispatch to agent method ───────────────────────────────────────
# Usage: registry_dispatch <agent_name> <method>
# Method is one of: integrate, unbind, status
# Calls agent_<name>_<method>(), or agent::default_<method>() as fallback.
# Before dispatching, calls agent_<name>_register() to populate AGENT_META.
registry_dispatch() {
  local name="$1" method="$2"

  # Normalize agent name (deepseek-harness → deepseek_harness)
  name=$(registry_normalize "$name") || true

  # Validate agent
  if ! registry_validate "$name"; then
    log_error "Unknown agent: $1"
    return 1
  fi

  # Populate AGENT_META by calling the agent's register function
  agent::clear_meta
  local reg_fn="agent_${name}_register"
  if declare -f "$reg_fn" &>/dev/null; then
    "$reg_fn"
  fi

  # Try the subclass method, fall back to base default
  local method_fn="agent_${name}_${method}"
  if declare -f "$method_fn" &>/dev/null; then
    "$method_fn"
  else
    "agent::default_${method}"
  fi
}

# ── Registry: get agent display name ─────────────────────────────────────────
registry_display_name() {
  local name="$1"
  local reg_fn="agent_${name}_register"
  if declare -f "$reg_fn" &>/dev/null; then
    agent::clear_meta
    "$reg_fn"
    agent::get_meta display_name
  else
    echo "$name"
  fi
}
