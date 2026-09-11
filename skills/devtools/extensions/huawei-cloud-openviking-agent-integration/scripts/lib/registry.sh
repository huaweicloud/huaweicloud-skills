#!/bin/bash
# lib/registry.sh — Agent registry (auto-discover + dispatch)
declare -ga REGISTRY_AGENTS=()
declare -gA REGISTRY_LOADED=()
registry_init() {
  REGISTRY_AGENTS=()
  REGISTRY_LOADED=()
}
# Maps hyphenated names to internal underscored names (deepseek-harness → deepseek_harness)
registry_normalize() {
  local name="$1"
  local existing
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$name" ]] && { echo "$name"; return 0; }
  done
  local normalized="${name//-/_}"
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$normalized" ]] && { echo "$normalized"; return 0; }
  done
  echo "$name"
  return 1
}
# Scans agents/ directory, sources each .sh, calls agent_<name>_register()
registry_discover() {
  local agents_dir="${1:-$(dirname "${BASH_SOURCE[0]}")/../agents}"
  local f name
  for f in "$agents_dir"/*.sh; do
    [[ -f "$f" ]] || continue
    name=$(basename "$f" .sh)
    [[ -n "${REGISTRY_LOADED[$name]:-}" ]] && continue
    # shellcheck disable=SC1090
    source "$f"
    REGISTRY_LOADED["$name"]=1
    local reg_fn="agent_${name}_register"
    if declare -f "$reg_fn" &>/dev/null; then
      agent::clear_meta
      "$reg_fn"
    fi
  done
}
registry_add() {
  local name="$1"
  local existing
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$name" ]] && return 0
  done
  REGISTRY_AGENTS+=("$name")
}
registry_list() { printf '%s\n' "${REGISTRY_AGENTS[@]}"; }
registry_count() { echo "${#REGISTRY_AGENTS[@]}"; }
registry_validate() {
  local target="$1"
  target=$(registry_normalize "$target")
  local existing
  for existing in "${REGISTRY_AGENTS[@]}"; do
    [[ "$existing" == "$target" ]] && return 0
  done
  return 1
}
# registry_dispatch <agent> <method>: calls agent_<name>_<method>() or agent::default_<method>()
registry_dispatch() {
  local name="$1" method="$2"
  name=$(registry_normalize "$name") || true
  if ! registry_validate "$name"; then
    log_error "Unknown agent: $1"
    return 1
  fi
  agent::clear_meta
  local reg_fn="agent_${name}_register"
  if declare -f "$reg_fn" &>/dev/null; then "$reg_fn"; fi
  local method_fn="agent_${name}_${method}"
  if declare -f "$method_fn" &>/dev/null; then "$method_fn"; else "agent::default_${method}"; fi
}
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
