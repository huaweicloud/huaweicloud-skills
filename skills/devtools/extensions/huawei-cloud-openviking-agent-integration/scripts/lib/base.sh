#!/bin/bash
# lib/base.sh — Agent base class (shared operations for all agent subclasses)
OV_MARKER="added by huawei-cloud-openviking-agent-integration skill"
OV_MARKER_LEGACY="added by openviking-agent-integration skill"
: "${OV_SKILL_VERSION:=1.2.1}"
: "${OV_HOME:=/root}"
: "${OV_RUNTIME_DIR:=${OV_HOME}/runtime}"
: "${OV_TEMPLATE_DIR:=${OV_HOME}/template}"
: "${OV_SHARED_DIR:=${OV_RUNTIME_DIR}/shared}"
: "${OV_SANDBOX_DIR:=${OV_HOME}/job-envs/sandboxes}"

ov_resolve_cmd() { command -v "$1" 2>/dev/null; }

ov_require_cmd() {
  local cmd="$1" desc="${2:-$1}"
  if ! command -v "$cmd" &>/dev/null; then
    log_error "Required command not found: $desc ($cmd)"
    return 1
  fi
}

ov_detect_python() {
  local py
  for py in python3.12 python3.11 python3.10 python3; do
    local p; p=$(command -v "$py" 2>/dev/null) && "$p" -c 'import json' 2>/dev/null && { printf '%s' "$p"; return 0; }
  done
  return 1
}
: "${OV_PY:=$(ov_detect_python)}"
: "${OV_NODE:=$(ov_resolve_cmd node)}"
: "${OV_NPM:=$(ov_resolve_cmd npm)}"
: "${OV_NPX:=$(ov_resolve_cmd npx)}"
: "${OV_CURL_BIN:=$(ov_resolve_cmd curl)}"
: "${OV_GIT:=$(ov_resolve_cmd git)}"
: "${OV_CURL_CONNECT_TIMEOUT:=5}"
: "${OV_CURL_MAX_TIME:=10}"
ov_curl() { "$OV_CURL_BIN" --connect-timeout "$OV_CURL_CONNECT_TIMEOUT" --max-time "$OV_CURL_MAX_TIME" "$@"; }
: "${OV_ENDPOINT:=http://127.0.0.1:1933}"
: "${OV_ACCOUNT_DEFAULT:=default}"
: "${OV_USER_DEFAULT:=default}"
: "${OV_MCP_URL:=${OV_ENDPOINT}/mcp}"
: "${OV_OPENCODE_PLUGIN_VER:=0.2.4}"
: "${OV_PLUGIN_SDK_VER:=1.18.8}"
: "${OV_DSH_PLUGIN_VER:=0.1.0}"
: "${OV_NPM_REGISTRY_DEFAULT:=https://mirrors.huaweicloud.com/repository/npm/}"
: "${OV_PLUGIN_CACHE_DIR:=${OV_SHARED_DIR}/openviking-plugins}"
: "${OV_PLUGIN_CACHE_TTL:=86400}"

ov_plugin_cache_path() { printf '%s/%s' "$OV_PLUGIN_CACHE_DIR" "$1"; }

ov_plugin_cache_valid() {
  local dir; dir=$(ov_plugin_cache_path "$1")
  [[ -d "$dir" && -f "$dir/package.json" ]] || return 1
  local now mtime
  now=$(date +%s)
  mtime=$(stat -c %Y "$dir" 2>/dev/null || echo 0)
  [[ $((now - mtime)) -le $OV_PLUGIN_CACHE_TTL ]]
}

ov_plugin_cache_put() {
  local pkg="$1" src="$2" dir
  dir=$(ov_plugin_cache_path "$pkg")
  mkdir -p "$(dirname "$dir")"
  rm -rf "$dir"
  cp -a "$src" "$dir"
  touch "$dir"
}

ov_plugin_cache_get() {
  local pkg="$1" dst="$2" dir
  dir=$(ov_plugin_cache_path "$pkg")
  [[ -d "$dir" ]] || return 1
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  cp -a "$dir" "$dst"
}
: "${OV_VERIFY_QUERY:=华为云 ECS 创建 项目配置 区域}"
: "${OV_BACKUP_KEEP:=5}"
declare -gA AGENT_META

agent::set_meta() { AGENT_META["$1"]="$2"; }
agent::get_meta() { echo "${AGENT_META[$1]:-}"; }
agent::clear_meta() { AGENT_META=(); }

find_sandbox() {
  find "$OV_SANDBOX_DIR/" -maxdepth 1 -type d -name "${1}-*" -print -quit 2>/dev/null
}

backup_file() {
  cp "$1" "${1}.bak.$(date +%s)"
  local _bak_prefix="${1}.bak."
  ls -1t "${_bak_prefix}"* 2>/dev/null | tail -n +$((OV_BACKUP_KEEP + 1)) | while IFS= read -r _old; do
    rm -f "$_old"
  done
}

has_ov_injection() {
  grep -v "MCP SDK install" "$1" 2>/dev/null | grep -q "$OV_MARKER\|$OV_MARKER_LEGACY"
}

ov_template_path() {
  if [[ -n "${AGENT_META[template_path]:-}" ]]; then
    echo "${AGENT_META[template_path]}"
  else
    echo "${OV_TEMPLATE_DIR}/$1/start.sh"
  fi
}

ov_require_template() {
  local tpl; tpl=$(ov_template_path "$1")
  if [[ ! -f "$tpl" ]]; then
    log_error "$2 template start.sh not found: $tpl"
    return 1
  fi
}

ov_status() { echo "${1}|${2}|${3}"; }

check_ov_health() {
  local endpoint="${OV_ENDPOINT:-http://127.0.0.1:1933}"
  local resp
  resp=$(ov_curl -sf "${endpoint}/health" 2>/dev/null) || {
    log_error "OpenViking server not reachable at $endpoint"
    return 1
  }
  local status
  status=$(echo "$resp" | "$OV_PY" -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "unknown")
  [[ "$status" == "ok" ]] && return 0
  log_error "OpenViking server unhealthy: $resp"
  return 1
}

agent::default_integrate() { log_error "Agent '${AGENT_META[name]}' does not implement integrate()"; return 1; }
agent::default_unbind()    { log_error "Agent '${AGENT_META[name]}' does not implement unbind()";    return 1; }
agent::default_status()    { ov_status "${AGENT_META[name]:-unknown}" "unknown" "status not implemented"; }

create_ov_config() {
  local conf_subdir="${2:-.config/opencode}"
  local conf_dir="$1/$conf_subdir"
  mkdir -p "$conf_dir"
  if [[ ! -f "$conf_dir/openviking-config.json" ]]; then
    cat > "$conf_dir/openviking-config.json" <<'OVCONF'
{"enabled":true,"timeoutMs":30000,"repoContext":{"enabled":true,"cacheTtlMs":60000},"autoRecall":{"enabled":true,"limit":10,"scoreThreshold":0.35,"maxContentChars":500,"preferAbstract":true,"tokenBudget":2000,"minQueryLength":3},"recallLimit":15,"recallMaxContentChars":20000,"commitTokenThreshold":20000,"commitKeepRecentCount":10,"profileTokenBudget":10000,"resumeContextBudget":32000}
OVCONF
  fi
}

ov_find_runtime_file() {
  find "$OV_RUNTIME_DIR" -path "$1" -not -path "*__pycache__*" 2>/dev/null | head -1
}

ov_clear_pycache() {
  local file="$1" base dir
  [[ -z "$file" || ! -f "$file" ]] && return 0
  base=$(basename "$file" .py)
  dir=$(dirname "$file")
  find "$dir" -path "*__pycache__*${base}*" -delete 2>/dev/null
}

ov_patch_present() {
  local file="$1" marker="$2"
  [[ -n "$file" && -f "$file" ]] && grep -q "$marker" "$file" 2>/dev/null
}

ov_patch_apply() {
  local file="$1" marker="$2" desc="$3" apply_fn="$4"
  if [[ -z "$file" ]]; then
    log_warn "$desc: target file not found — patch skipped"
    return 1
  fi
  ov_patch_present "$file" "$marker" && return 0
  backup_file "$file"
  if "$apply_fn" "$file"; then
    ov_clear_pycache "$file"
    ov_patch_present "$file" "$marker" || log_warn "$desc: marker not found after transform (version mismatch?)"
    return 0
  else
    log_error "$desc: transformation failed"
    return 1
  fi
}

ov_patch_revert() {
  local file="$1" marker="$2" desc="$3" revert_fn="$4"
  if [[ -z "$file" ]] || ! ov_patch_present "$file" "$marker"; then return 0; fi
  backup_file "$file"
  if "$revert_fn" "$file"; then
    ov_clear_pycache "$file"
    ov_patch_present "$file" "$marker" && { log_warn "$desc: revert ran but marker still present"; return 1; }
    return 0
  else
    log_error "$desc: revert failed"
    return 1
  fi
}

ov_patch_mark() {
  if ov_patch_present "$1" "$2"; then printf '✓'; else printf '✗'; fi
}
