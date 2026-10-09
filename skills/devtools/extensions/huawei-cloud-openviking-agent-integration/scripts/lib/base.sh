#!/bin/bash
# lib/base.sh — Agent base class (shared operations for all agent subclasses)
: "${OV_MARKER:=added by huawei-cloud-openviking-agent-integration skill}"
: "${OV_MARKER_LEGACY:=added by openviking-agent-integration skill}"
: "${OV_SKILL_VERSION:=1.2.2}"
: "${OV_HOME:=${HOME:-/root}}"
: "${OV_RUNTIME_DIR:=${OV_HOME}/runtime}"
: "${OV_TEMPLATE_DIR:=${OV_HOME}/template}"
: "${OV_SHARED_DIR:=${OV_RUNTIME_DIR}/shared}"
: "${OV_SANDBOX_DIR:=${OV_HOME}/job-envs/sandboxes}"
: "${OV_PY_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")/../py" && pwd)}"
_ov_health() { "$OV_PY" "$OV_PY_DIR/ov_health.py" "$@"; }

ov_resolve_cmd() { command -v "$1" 2>/dev/null; }

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

# Probe an already-installed package version from a package.json path.
# Prints the version (or nothing) — returns 1 if unreadable/absent.
ov_probe_package_version() {
  local pkg_json="$1"
  [[ -n "$pkg_json" && -f "$pkg_json" ]] || return 1
  "$OV_PY" -c "import json,sys; print(json.load(open(sys.argv[1])).get('version',''))" "$pkg_json" 2>/dev/null || return 1
}

# Resolve effective plugin version: env override -> host-installed probe -> latest.
ov_effective_plugin_ver() {
  local pkg_json="$1" env_ver="${2:-}"
  [[ -n "$env_ver" && "$env_ver" != "latest" ]] && { echo "$env_ver"; return 0; }
  local probe; probe=$(ov_probe_package_version "$pkg_json") || true
  [[ -n "$probe" ]] && { echo "$probe"; return 0; }
  echo "latest"
}

: "${OV_ENDPOINT:=http://127.0.0.1:1933}"
: "${OV_ACCOUNT_DEFAULT:=$(whoami 2>/dev/null || echo default)}"
: "${OV_USER_DEFAULT:=$(whoami 2>/dev/null || echo default)}"
: "${OV_MCP_URL:=${OV_ENDPOINT}/mcp}"
# Version policy: never pin plugin/SDK versions. Default to npm "latest" so the
# installed plugin matches the current agent engine; probe the host install first
# when present (see ov_probe_package_version). Explicit env overrides still win.
: "${OV_OPENCODE_PLUGIN_VER:=latest}"
: "${OV_PLUGIN_SDK_VER:=latest}"
: "${OV_DSH_PLUGIN_VER:=latest}"  # unused for installs; dsh deps come from host sync
: "${OV_NPM_REGISTRY_DEFAULT:=https://mirrors.huaweicloud.com/repository/npm/}"
: "${OV_PLUGIN_CACHE_DIR:=${OV_SHARED_DIR}/openviking-plugins}"
: "${OV_PLUGIN_CACHE_TTL:=86400}"

ov_plugin_cache_path() {
  [[ -z "$1" ]] && return 1
  [[ "$1" == *..* || "$1" == /* ]] && { log_warn "ov_plugin_cache_path: rejecting suspicious name: $1"; return 1; }
  printf '%s/%s' "$OV_PLUGIN_CACHE_DIR" "$1"
}

# ISSUE-019: cache is valid only when it exists, is within TTL AND is content-sane
# (package.json non-empty + more than a lone manifest — a truncated/corrupted cache
#  is rejected so callers re-download instead of silently reusing it).
ov_plugin_cache_valid() {
  local dir; dir=$(ov_plugin_cache_path "$1")
  [[ -d "$dir" && -f "$dir/package.json" && -s "$dir/package.json" ]] || return 1
  local file_count; file_count=$(find "$dir" -mindepth 1 -type f 2>/dev/null | wc -l)
  (( file_count >= 2 )) || return 1
  local now mtime
  now=$(date +%s)
  mtime=$(stat -c %Y "$dir" 2>/dev/null || echo 0)
  [[ $((now - mtime)) -le $OV_PLUGIN_CACHE_TTL ]]
}

ov_plugin_cache_put() {
  local pkg="$1" src="$2" dir tmp_dir
  dir=$(ov_plugin_cache_path "$pkg") || return 1
  mkdir -p "$(dirname "$dir")"
  tmp_dir="${dir}.tmp.$$"
  ov_safe_rm "$tmp_dir" 2>/dev/null || true
  cp -a "$src" "$tmp_dir" && mv "$tmp_dir" "$dir" || { ov_safe_rm "$tmp_dir" 2>/dev/null || true; return 1; }
  touch "$dir"
}

ov_plugin_cache_get() {
  local pkg="$1" dst="$2" dir
  dir=$(ov_plugin_cache_path "$pkg")
  [[ -d "$dir" ]] || return 1
  mkdir -p "$(dirname "$dst")"
  ov_safe_rm "$dst" 2>/dev/null || true
  cp -a "$dir" "$dst"
}
: "${OV_VERIFY_QUERY:=华为云 ECS 创建 项目配置 区域}"
: "${OV_BACKUP_KEEP:=5}"
declare -gA AGENT_META

agent::set_meta() { AGENT_META["$1"]="$2"; }
agent::get_meta() { echo "${AGENT_META[$1]:-}"; }
agent::clear_meta() { AGENT_META=(); }

find_sandbox() {
  local matches
  mapfile -t matches < <(find "$OV_SANDBOX_DIR/" -maxdepth 1 -type d -name "${1}-*" -print 2>/dev/null)
  [[ ${#matches[@]} -gt 0 ]] || return 1
  if (( ${#matches[@]} > 1 )); then
    log_warn "find_sandbox: ${#matches[@]} sandboxes match '${1}-*'; using first (${matches[0]}) — specify a unique sandbox if ambiguous" >&2
  fi
  printf '%s' "${matches[0]}"
}

backup_file() {
  [[ -f "$1" ]] || { log_warn "backup_file: $1 not found"; return 1; }
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

ov_status() { echo "${1}|${2}|${3}"; }

check_ov_health() {
  local endpoint="${OV_ENDPOINT:-http://127.0.0.1:1933}"
  local resp
  resp=$(ov_curl -sf "${endpoint}/health" 2>/dev/null) || {
    log_error "OpenViking server not reachable at $endpoint"
    return 1
  }
  local status
  status=$(echo "$resp" | _ov_health parse-field - status 2>/dev/null || echo "unknown")
  [[ "$status" == "ok" ]] && return 0
  log_error "OpenViking server unhealthy: $resp"
  return 1
}

agent::default_integrate() { log_error "Agent '${AGENT_META[name]}' does not implement integrate()"; return 1; }
agent::default_unbind()    { log_error "Agent '${AGENT_META[name]}' does not implement unbind()";    return 1; }
agent::default_status()    { ov_status "${AGENT_META[name]:-unknown}" "unknown" "status not implemented"; }

# --- Shared 4-way status reporting (eliminates duplication across 8 agents) ---
agent::report_status() {
  local name="$1" tpl_has="$2" live_has="$3"
  local d_integrated="$4" d_template="$5" d_live="$6" d_none="$7"
  if [[ "$tpl_has" == "true" && "$live_has" == "true" ]]; then
    ov_status "$name" "integrated" "$d_integrated"
  elif [[ "$tpl_has" == "true" ]]; then
    ov_status "$name" "integrated" "$d_template"
  elif [[ "$live_has" == "true" ]]; then
    ov_status "$name" "partial" "$d_live"
  else
    ov_status "$name" "not_integrated" "$d_none"
  fi
}

create_ov_config() {
  local conf_subdir="${2:-.config/opencode}"
  local conf_dir="$1/$conf_subdir"
  mkdir -p "$conf_dir"
  if [[ ! -f "$conf_dir/openviking-config.json" ]]; then
    cat > "$conf_dir/openviking-config.json" <<'OVCONF'
{"enabled":true,"timeoutMs":30000,"repoContext":{"enabled":true,"cacheTtlMs":60000},"autoRecall":{"enabled":true,"limit":10,"scoreThreshold":0.35,"maxContentChars":500,"preferAbstract":true,"tokenBudget":2000,"minQueryLength":3},"recallLimit":15,"recallMaxContentChars":20000,"commitTokenThreshold":20000,"commitKeepRecentCount":10,"profileTokenBudget":10000,"resumeContextBudget":32000}
OVCONF
    chmod 600 "$conf_dir/openviking-config.json" 2>/dev/null || true
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

# --- Sync shared/ .mjs files from upstream (post-provision fix for commit aa3ee2f) ---
# Downloads shared/ files that an upstream refactor moved out of the extension/plugin
# directory. The pack-time step that copies them back is not run by ov_plugin_provision,
# so we fetch them here to prevent ERR_MODULE_NOT_FOUND at runtime.
# Args: $1 = persist_src (persistent source directory to sync shared/ into)
# Globals used: GH_RAW_MIRRORS, OV_CURL_BIN, OV_PLUGIN_REPO_PATH
ov_sync_shared_files() {
  local persist_src="$1"
  [[ -z "$persist_src" ]] && return 1
  # Already synced — nothing to do
  if [[ -d "$persist_src/shared" && -f "$persist_src/shared/ov-http.mjs" ]]; then
    return 0
  fi
  local _sha; _sha=$(ov_plugin_upstream_sha 2>/dev/null || echo "")
  [[ -z "$_sha" ]] && return 0
  local _shared_dir="$persist_src/shared"
  mkdir -p "$_shared_dir"
  local _f _url _src_paths=(
    "agent-plugins/servers/shared"
    "examples/claude-code-memory-plugin/scripts/shared"
  )
  local _needed="ov-http.mjs capture-utils.mjs plugin-config.mjs config-schema.mjs credentials.mjs debug-log.mjs input-filters.mjs mcp-proxy-config.mjs mcp-proxy-core.mjs pending-queue.mjs profile-inject.mjs recall-compress-core.mjs recall-core.mjs retryable.mjs session-model.mjs uri-guard.mjs workspace-identity.mjs workspace-peer.mjs workspace-config.mjs workspace-registry.mjs agent-hook-runtime.mjs async-writer.mjs batch-send.mjs doctor-core.mjs setup-wizard.mjs"
  for _f in $_needed; do
    [[ -f "$_shared_dir/$_f" ]] && continue
    for _src in "${_src_paths[@]}"; do
      for _base in "${GH_RAW_MIRRORS[@]}"; do
        _url="${_base}/${OV_PLUGIN_REPO_PATH}/${_sha}/${_src}/${_f}"
        if "$OV_CURL_BIN" -fsS --connect-timeout 10 --max-time 25 "$_url" -o "$_shared_dir/$_f" 2>/dev/null; then
          break
        fi
      done
      [[ -f "$_shared_dir/$_f" ]] && break
    done
  done
  log_ok "shared/ files synced (${_sha:0:7})"
}

# --- Safe removal (refuses dangerous paths, allows only known dirs) ---
# ISSUE-017: resolves symlinks first, then evaluates the allowlist on the real
# path — a symlink inside an allowlisted dir can no longer escape it. Sandbox
# paths are allowed only at least two segments below the sandbox root, so a
# whole sandbox can never be removed through this helper.
ov_safe_rm() {
  local target="$1"
  [[ -z "$target" ]] && return 1
  case "$target" in
    /|/root|"$HOME"|/tmp|/usr|/bin|/sbin|/lib|/opt|/etc|/var|/boot|/proc|/sys|/dev|/home) return 1 ;;
  esac
  [[ "$target" != /* ]] && return 1
  local real; real=$(realpath -m "$target" 2>/dev/null || echo "$target")
  case "$real" in
    /|/root|"$HOME"|/tmp|/usr|/bin|/sbin|/lib|/opt|/etc|/var|/boot|/proc|/sys|/dev|/home) return 1 ;;
  esac
  local ok=false
  # Runtime / shared / plugin-cache / skill-home trees are fully managed by the skill
  case "$real" in
    "${OV_RUNTIME_DIR:-/nonexistent}"/*|\
    "${OV_SHARED_DIR:-/nonexistent}"/*|\
    "${OV_PLUGIN_CACHE_DIR:-/nonexistent}"/*|\
    "${OV_HOME:-/nonexistent}"/*|\
    /tmp/openviking/*|\
    /tmp/ov-*) ok=true ;;
  esac
  # Sandbox sub-paths: allow, but never the sandbox itself nor an arbitrary
  # one-segment child. OV-owned shadow dirs (.openviking/.codeartsdoer) are
  # created only by this skill, so they are safe even at depth one.
  if [[ "$real" == "${OV_SANDBOX_DIR:-/nonexistent}/"* ]]; then
    local _rest="${real#"${OV_SANDBOX_DIR}/"}"
    case "$_rest" in
      .openviking|.codeartsdoer) ok=true ;;
      */*) ok=true ;;
    esac
  fi
  if [[ "$ok" != "true" ]]; then
    log_warn "ov_safe_rm: path outside allowlist: $real (was: $target)"
    return 1
  fi
  rm -rf "$real"
}

# --- Require sandbox exists ---
ov_require_sandbox() {
  local pattern="$1"
  local sbx; sbx=$(find_sandbox "$pattern")
  [[ -n "$sbx" ]] || { log_error "No sandbox found for: $pattern"; return 1; }
  printf '%s' "$sbx"
}

# --- ISSUE-007: require the current agent's sandbox before integrating ---
# Reads AGENT_META (populated by agent::register) so entry points can gate on it.
ov_require_agent_sandbox() {
  local pattern="${AGENT_META[sandbox_pattern]:-}"
  local name="${AGENT_META[name]:-unknown}"
  [[ -n "$pattern" ]] || { log_error "Agent '$name' has no sandbox_pattern meta — cannot validate sandbox"; return 1; }
  ov_require_sandbox "${pattern%-*}"
}

# --- ISSUE-006: validate an agent name against the discovered registry ---
ov_supported_agents() { registry_list | tr '\n' ',' | sed 's/,$//'; }
ov_require_supported_agent() {
  local name="$1"
  if ! registry_validate "$name"; then
    log_error "Unknown agent: $name — supported: $(ov_supported_agents)"
    return 1
  fi
}

# --- ISSUE-003: track whether an explicitly provided --api-key was consumed ---
# bash-side flag plus a marker file that the python injectors touch when they
# actually embed the key into an agent config (the marker survives the bash ->
# python -> bash round-trip).
OV_API_KEY_CONSUMED=false
: "${OV_API_KEY_CONSUMED_FILE:=${OV_RUNTIME_DIR}/.ov_api_key_consumed}"
export OV_API_KEY_CONSUMED_FILE
# ISSUE-003: sh-side marker writer. Kept as reserved API: the Python injectors
# (_ov_mark_key_consumed) currently write the marker file, but sh-only injection
# paths can call this function directly.
ov_mark_api_key_consumed() {
  OV_API_KEY_CONSUMED=true
  mkdir -p "$(dirname "$OV_API_KEY_CONSUMED_FILE")" 2>/dev/null || true
  : > "$OV_API_KEY_CONSUMED_FILE" 2>/dev/null || true
}
ov_api_key_was_consumed() {
  [[ "$OV_API_KEY_CONSUMED" == "true" || -f "${OV_API_KEY_CONSUMED_FILE:-}" ]]
}

# --- P2-8: Sync template to sandbox process_dir ---
# ISSUE-013: join with a separator so a sandbox path without a trailing "/"
# never produces a bogus "${sandbox}process_dir" that silently never exists.
ov_sync_template_to_sandbox() {
  local tpl="$1" sandbox="$2" process_subdir="${3:-process_dir}"
  [[ -z "$tpl" || -z "$sandbox" || ! -f "$tpl" ]] && return 1
  local target_dir="${sandbox%/}/${process_subdir#/}"
  if [[ -d "$target_dir" ]]; then
    cp "$tpl" "${target_dir}/start.sh" && chmod +x "${target_dir}/start.sh" \
      && log_ok "Synced start.sh to sandbox (${process_subdir})" \
      || { log_error "Failed to sync start.sh to sandbox"; return 1; }
    return 0
  fi
  log_warn "No ${process_subdir} in sandbox '${sandbox}' — start.sh NOT synced (do NOT report it as synced)"
  return 0
}

# --- Deploy plugin from cache (returns 1 on cache miss) ---
# --- Tiered plugin deploy: existing → cache → npm → GitHub provision ---
# Unified deployment extracted from opencode.sh and deepseek_harness.sh.
# Sets global _ov_tiered_result: "existing" | "cache" | "npm" | "provision" | "failed"
# Args: $1=pkg_name   $2=dest_dir   $3=npm_registry   $4=provision_name   $5=plugin_subpath   $6=pkg_ver (opt, default "latest")
#       $7=force_provision (opt, default false) — when true, an existing install still
#          runs ov_plugin_provision to compare upstream commit (zero download if same,
#          keeps existing on network failure) instead of short-circuiting as "existing".
# If plugin_subpath is empty, deploys directly to dest_dir (no node_modules/ prefix).
ov_deploy_plugin_tiered() {
  local pkg_name="$1" dest_dir="$2" npm_registry="$3" provision_name="$4" plugin_subpath="$5"
  local pkg_ver="${6:-latest}"
  local force_provision="${7:-false}"
  local plugin_dst
  if [[ -z "$plugin_subpath" ]]; then
    plugin_dst="$dest_dir"
  else
    plugin_dst="${dest_dir}/node_modules/${plugin_subpath}"
  fi
  _ov_tiered_result="failed"

  # 1. Already installed
  if [[ -d "$plugin_dst" && -f "$plugin_dst/package.json" ]]; then
    if [[ "$force_provision" == "true" && -n "$provision_name" ]]; then
      if ov_plugin_provision "$provision_name" "$plugin_dst"; then
        _ov_tiered_result="provision"
        return 0
      fi
      log_warn "Upstream check failed for $provision_name — keeping existing install at $plugin_dst"
    fi
    _ov_tiered_result="existing"
    return 0
  fi

  # 2. Shared cache
  local cache_dir; cache_dir=$(ov_plugin_cache_path "$pkg_name" 2>/dev/null) || true
  if [[ -n "$cache_dir" && -d "$cache_dir" && -f "$cache_dir/package.json" ]]; then
    mkdir -p "$(dirname "$plugin_dst")"
    ov_safe_rm "$plugin_dst" 2>/dev/null || true
    cp -a "$cache_dir" "$plugin_dst"
    _ov_tiered_result="cache"
    return 0
  fi

  # 3. npm install
  if [[ -n "$npm_registry" && -n "$pkg_name" ]] && { command -v npm &>/dev/null || command -v "${OV_NPM:-npm}" &>/dev/null; }; then
    local npm_bin="${OV_NPM:-npm}"
    mkdir -p "$dest_dir"
    printf '{"dependencies":{"%s":"%s"}}\n' "$pkg_name" "$pkg_ver" > "$dest_dir/package.json"
    if (cd "$dest_dir" && "$npm_bin" install --registry="$npm_registry" --no-audit --no-fund 2>&1 | tail -5) && \
       [[ -d "$plugin_dst" ]]; then
      ov_plugin_cache_put "$pkg_name" "$plugin_dst" || log_warn "ISSUE-019: cache write failed for $pkg_name"
      _ov_tiered_result="npm"
      return 0
    fi
  fi

  # 4. GitHub provision fallback
  log_warn "npm/cache failed — trying GitHub provision for $provision_name"
  local _prov_dir; _prov_dir=$(mktemp -d /tmp/ov-prov.XXXXXX)
  if ov_plugin_provision "$provision_name" "$_prov_dir"; then
    mkdir -p "$(dirname "$plugin_dst")"
    ov_safe_rm "$plugin_dst" 2>/dev/null || true
    cp -a "$_prov_dir" "$plugin_dst"
    ov_plugin_cache_put "$pkg_name" "$plugin_dst" || log_warn "ISSUE-019: cache write failed for $pkg_name"
    ov_safe_rm "$_prov_dir" 2>/dev/null || true
    _ov_tiered_result="provision"
    return 0
  fi
  ov_safe_rm "$_prov_dir" 2>/dev/null || true
  _ov_tiered_result="failed"
  return 1
}
