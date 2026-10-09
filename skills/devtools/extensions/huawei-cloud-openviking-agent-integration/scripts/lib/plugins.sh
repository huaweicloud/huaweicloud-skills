#!/bin/bash
# lib/plugins.sh — Plugin provisioning: on-demand install, domestic-first, SHA-1 verified.
# npm: mirrors.huaweicloud.com → npmmirror → npmjs.org
# GitHub raw files: proxy mirrors → direct raw.githubusercontent.com (byte-verified later
# against the official GitHub tree SHA). API metadata (commit SHA, recursive tree JSON)
# goes through its own proxy-first chain with direct api.github.com as fallback. Chains
# are overridable via OPENVIKING_GH_RAW_MIRRORS / OPENVIKING_GITHUB_API_MIRROR /
# OPENVIKING_NPM_REGISTRIES (see notes.md).
: "${OV_PY_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")/../py" && pwd)}"
_ov_plugins() { "$OV_PY" "$OV_PY_DIR/ov_plugins.py" "$@"; }
OV_PLUGIN_REPO="https://github.com/volcengine/OpenViking.git"
OV_PLUGIN_API="https://api.github.com/repos/volcengine/OpenViking"
OV_PLUGIN_REPO_HOST="github.com"
OV_PLUGIN_REPO_PATH="volcengine/OpenViking"
# npm registries, domestic mirrors first. OPENVIKING_NPM_REGISTRIES (space-separated)
# is prepended to this list when set (health-checked by ov_first_npm_registry).
NPM_REGISTRIES=(
  "https://mirrors.huaweicloud.com/repository/npm/"
  "https://registry.npmmirror.com/"
  "https://registry.npmjs.org/"
)
# GitHub raw file mirrors, domestic first. Each entry is a base URL; the repo-relative
# path (volcengine/OpenViking/<sha>/...) is appended directly. OPENVIKING_GH_RAW_MIRRORS
# (space-separated) replaces the defaults; direct raw.githubusercontent.com is always
# kept as the final fallback. ov_pick_gh_mirror() health-checks the list once per run.
GH_RAW_MIRROR_DEFAULTS=(
  "https://gh-proxy.com/https://raw.githubusercontent.com"
  "https://ghfast.top/https://raw.githubusercontent.com"
  "https://raw.githubusercontent.com"
)
GH_RAW_MIRRORS=("${GH_RAW_MIRROR_DEFAULTS[@]}")
if [[ -n "${OPENVIKING_GH_RAW_MIRRORS:-}" ]]; then
  read -r -a GH_RAW_MIRRORS <<< "$OPENVIKING_GH_RAW_MIRRORS"
fi
# GitHub API mirror chain (commit SHA + recursive tree JSON), domestic first. Each
# entry is the full API base URL; callers append /commits/HEAD or /git/trees/...
# OPENVIKING_PLUGIN_API_URL (or OPENVIKING_GITHUB_API_MIRROR) wins over this chain.
GH_API_MIRROR_DEFAULTS=(
  "https://gh-proxy.com/https://api.github.com/repos/volcengine/OpenViking"
  "https://api.github.com/repos/volcengine/OpenViking"
)
# name|npm package (empty = GitHub-only)|upstream example dir|npm peer deps (optional)
# opencode-plugin: published to npm; pure .mjs, zero runtime deps
# openclaw-plugin: published to npm; needs @sinclair/typebox + fflate after tsc build
# dsh/pi-coding-agent-extension: NOT published to npm — pulled from GitHub only
# Version policy: NEVER pin host-coupled peer deps. dsh-llm/dsh-tools are synced
# from the host dsh runtime node_modules (see dsh_sync_peer_deps), so @latest here
# is only a fallback when the host install is missing. openclaw typebox/fflate stay
# pinned because they are build deps of the plugin itself, not host-coupled.
OV_PLUGINS=(
  "opencode-plugin|@openviking/opencode-plugin|examples/opencode-plugin|"
  "openclaw-plugin|@openviking/openclaw-plugin|examples/openclaw-plugin|@sinclair/typebox@0.34.48 fflate@^0.8.2"
  "dsh-memory-plugin||examples/dsh-memory-plugin|@deepseek-ai/dsh-llm@latest @deepseek-ai/dsh-tools@latest"
  "pi-coding-agent-extension||examples/pi-coding-agent-extension|"
)
# Validate that a plugin source URL is the official volcengine/OpenViking repo.
ov_plugin_validate_source() {
  local url="$1"
  _ov_plugins validate-source "$url" "$OV_PLUGIN_REPO_HOST" "$OV_PLUGIN_REPO_PATH"
}
# Latest upstream commit SHA of the plugin repo (GitHub API first — fast; "$OV_GIT" ls-remote fallback).
ov_plugin_upstream_sha() {
  local repo_url="${OPENVIKING_PLUGIN_REPO_URL:-$OV_PLUGIN_REPO}"
  ov_plugin_validate_source "$repo_url" || { log_error "Plugin source not allowed: $repo_url"; return 1; }
  local sha
  local api_base; api_base=$(ov_plugin_api_base) || return 1
  sha=$("$OV_CURL_BIN" -fsS --retry 2 --connect-timeout 10 --max-time 30 "$api_base/commits/HEAD" 2>/dev/null \
    | _ov_plugins parse-sha 2>/dev/null || true)
  if [[ ${#sha} -ne 40 ]]; then
    sha=$(timeout 20 "$OV_GIT" ls-remote "$repo_url" HEAD 2>/dev/null | awk '{print $1}') || true
  fi
  [[ ${#sha} -eq 40 ]] || return 1
  echo "$sha"
}
# Commit SHA recorded in the runtime cache .openviking-sync (empty if absent).
ov_plugin_cache_sha() {
  local sync="$1/.openviking-sync"
  [[ -f "$sync" ]] || { echo ""; return 0; }
  awk -F': ' '/^# Commit:/{print $2; exit}' "$sync" | awk '{print $1}'
}
# First reachable npm registry from the domestic-first NPM_REGISTRIES list.
ov_first_npm_registry() {
  local reg
  local regs=()
  if [[ -n "${OPENVIKING_NPM_REGISTRIES:-}" ]]; then
    read -r -a regs <<< "$OPENVIKING_NPM_REGISTRIES"
  fi
  regs+=("${NPM_REGISTRIES[@]}")
  for reg in "${regs[@]}"; do
    [[ -n "$reg" ]] || continue
    if "$OV_CURL_BIN" -fsS --connect-timeout 8 --max-time 15 "$reg" -o /dev/null 2>/dev/null; then
      echo "$reg"; return 0
    fi
  done
  echo "${NPM_REGISTRIES[${#NPM_REGISTRIES[@]}-1]}"
}
# Robust single-file fetch with bounded retries + backoff (network to the mirrors is
# intermittently slow; each attempt stays under ~33s).
_ov_fetch_file() {
  local url="$1" out="$2"
  local t_start tries
  t_start=$(date +%s); tries=0
  while true; do
    tries=$((tries + 1))
    if "$OV_CURL_BIN" -fsS --connect-timeout 8 --max-time 25 "$url" -o "$out"; then return 0; fi
    if (( tries >= 8 )); then log_error "Gave up after 8 attempts: $url"; return 1; fi
    if (( $(date +%s) - t_start > 200 )); then log_error "Timed out fetching: $url"; return 1; fi
    local _delay=$((3 * (1 << (tries - 1))))
    ((_delay > 30)) && _delay=30
    sleep "$_delay"
  done
}
# Pick the first reachable raw mirror (health-checked once per run, cached in the parent
# shell so parallel download subshells inherit one result). Honors
# OPENVIKING_GH_RAW_MIRRORS when set, else GH_RAW_MIRROR_DEFAULTS; direct
# raw.githubusercontent.com is the built-in final fallback.
_OV_GH_MIRROR_CHOSEN=""
ov_pick_gh_mirror() {
  [[ -n "$_OV_GH_MIRROR_CHOSEN" ]] && { echo "$_OV_GH_MIRROR_CHOSEN"; return 0; }
  local m
  for m in "${GH_RAW_MIRRORS[@]}" "https://raw.githubusercontent.com"; do
    [[ -n "$m" ]] || continue
    if "$OV_CURL_BIN" -fsS --connect-timeout 5 --max-time 12 "$m/$OV_PLUGIN_REPO_PATH/main/README.md" -o /dev/null 2>/dev/null; then
      _OV_GH_MIRROR_CHOSEN="$m"
      break
    fi
  done
  [[ -n "$_OV_GH_MIRROR_CHOSEN" ]] || _OV_GH_MIRROR_CHOSEN="https://raw.githubusercontent.com"
  echo "$_OV_GH_MIRROR_CHOSEN"
  return 0
}
# Pick the API base URL: OPENVIKING_PLUGIN_API_URL / OPENVIKING_GITHUB_API_MIRROR win,
# else first reachable of GH_API_MIRROR_DEFAULTS (cached per run), else direct.
_OV_API_MIRROR_CHOSEN=""
ov_plugin_api_base() {
  if [[ -n "${OPENVIKING_PLUGIN_API_URL:-}" ]]; then
    echo "$OPENVIKING_PLUGIN_API_URL"; return 0
  fi
  if [[ -n "${OPENVIKING_GITHUB_API_MIRROR:-}" ]]; then
    echo "$OPENVIKING_GITHUB_API_MIRROR"; return 0
  fi
  [[ -n "$_OV_API_MIRROR_CHOSEN" ]] && { echo "$_OV_API_MIRROR_CHOSEN"; return 0; }
  local m
  for m in "${GH_API_MIRROR_DEFAULTS[@]}"; do
    if "$OV_CURL_BIN" -fsS --connect-timeout 5 --max-time 12 "$m" -o /dev/null 2>/dev/null; then
      _OV_API_MIRROR_CHOSEN="$m"; echo "$m"; return 0
    fi
  done
  # Direct api.github.com as final fallback even if the probe failed.
  _OV_API_MIRROR_CHOSEN="${GH_API_MIRROR_DEFAULTS[${#GH_API_MIRROR_DEFAULTS[@]}-1]}"
  echo "$_OV_API_MIRROR_CHOSEN"
  return 0
}
# Fetch a repo-relative <path> at <sha>. Uses the health-checked mirror first; if it
# dies mid-download, falls through the remaining mirrors once each. Returns 0 on
# success (writes <out>).
_ov_fetch_mirrored() {
  local sha="$1" path="$2" out="$3"
  local base chosen
  chosen=$(ov_pick_gh_mirror)
  if _ov_fetch_file "$chosen/$OV_PLUGIN_REPO_PATH/$sha/$path" "$out"; then return 0; fi
  # Chosen mirror failed after _ov_fetch_file's retry loop — uncache it and retry
  # the rest of the chain once each (direct raw last).
  _OV_GH_MIRROR_CHOSEN=""
  for base in "${GH_RAW_MIRRORS[@]}" "https://raw.githubusercontent.com"; do
    [[ -n "$base" ]] || continue
    [[ "$base" != "$chosen" ]] || continue
    if _ov_fetch_file "$base/$OV_PLUGIN_REPO_PATH/$sha/$path" "$out"; then return 0; fi
  done
  return 1
}
# Fetch the recursive repo tree JSON for <sha> (GitHub API, reachable directly).
# Caches under <stage>/trees/.
_ov_tree_fetch() {
  local sha="$1" stage="$2"
  local out="$stage/trees/${sha}.json"
  [[ -f "$out" ]] && { echo "$out"; return 0; }
  mkdir -p "$stage/trees"
  local api_base; api_base=$(ov_plugin_api_base) || return 1
  if ! "$OV_CURL_BIN" -fsS --retry 3 --connect-timeout 10 --max-time 60 "$api_base/git/trees/$sha?recursive=1" -o "$out"; then
    return 1
  fi
  echo "$out"
}
# Diff plugin files between old and new tree JSONs for <exdir>.
# Emits: "A <path>" added, "M <path>" modified, "D <path>" deleted.
_ov_diff_blobs() {
  _ov_plugins diff-blobs "$1" "$2" "$3"
}
# path<tab>blob-sha map for <exdir> from a GitHub tree JSON.
ov_plugin_blob_map() {
  _ov_plugins blob-map "$1" "$2"
}
# Download repo-relative <paths> at <sha> into <dest> (relative to <exdir>), and
# VERIFY each file's SHA-1 against the authoritative GitHub tree blob SHA — this is
# the source-check: content is accepted only if it matches the official tree, no
# matter which domestic mirror actually served the bytes.
_ov_download_files() {
  local sha="$1" newtree="$2" exdir="$3" dest="$4"
  shift 4
  local paths=("$@")
  [[ ${#paths[@]} -gt 0 ]] || return 0
  local blobmap; blobmap=$(ov_plugin_blob_map "$newtree" "$exdir")
  local path rel blobsha
  # Parallel download: launch up to OV_DOWNLOAD_PARALLEL (default 8) background jobs,
  # each downloading + SHA-1 verifying one file. Subshells inherit all functions and
  # variables (GH_RAW_MIRRORS, _ov_fetch_mirrored, etc.) from the parent shell.
  local max_parallel=${OV_DOWNLOAD_PARALLEL:-8}
  local pids=() pid rc=0
  for path in "${paths[@]}"; do
    rel="${path#*$exdir/}"
    blobsha=$(printf '%s\n' "$blobmap" | awk -v p="$path" -F'\t' '$1==p{print $2; exit}')
    [[ -n "$blobsha" ]] || { log_error "No blob sha for $path in upstream tree"; return 1; }
    mkdir -p "$dest/$(dirname "$rel")"
    # Download + verify in background subshell
    (
      _ov_fetch_mirrored "$sha" "$path" "$dest/$rel" || exit 1
      _ov_plugins sha1-verify "$dest/$rel" "$blobsha"
    ) &
    pids+=($!)
    # Throttle: when at capacity, wait for the oldest job to finish
    if (( ${#pids[@]} >= max_parallel )); then
      wait "${pids[0]}" || rc=1
      pids=("${pids[@]:1}")
    fi
  done
  # Wait for all remaining background jobs
  for pid in "${pids[@]}"; do
    wait "$pid" || rc=1
  done
  (( rc == 0 )) || { log_error "One or more parallel file downloads failed"; return 1; }
  return 0
}
# Write .openviking-sync traceability metadata for <dest> at <sha>/<exdir>.
_ov_write_sync_meta() {
  local dest="$1" sha="$2" exdir="$3"
  cat > "$dest/.openviking-sync" <<SYNC
# OpenViking agent plugin (installed on demand by huawei-cloud-openviking-agent-integration skill)
# Source: ${OV_PLUGIN_REPO_HOST}/${OV_PLUGIN_REPO_PATH}
# Commit: ${sha}
# Path: ${exdir}
# Synced: $(date -u +%Y-%m-%dT%H:%M:%SZ)
SYNC
}
# Ensure npm peer deps exist in <dest>/node_modules (domestic-first registry list).
_ov_ensure_peers() {
  local name="$1" peers="$2" dest="$3"
  [[ -n "$peers" ]] || return 0
  local need=false pk pn
  for pk in $peers; do
    # Resolve module path under node_modules: scoped (@scope/name) keeps the @ prefix.
    if [[ "$pk" == @* ]]; then
      pn="${pk#@}"; pn="${pn%%@*}"; pn="@$pn"
    else
      pn="${pk%%@*}"
    fi
    [[ -d "$dest/node_modules/$pn" ]] || need=true
  done
  [[ "$need" == "false" ]] && return 0
  local reg; reg=$(ov_first_npm_registry)
  log_info "Fetching $name peer deps from $reg: $peers"
  mkdir -p /tmp/openviking
  local pkgdir; pkgdir=$(mktemp -d /tmp/openviking/ov-npm.XXXXXX) || { log_error "mktemp failed for $name peer deps staging"; return 1; }
  printf '{"name":"ov-peer-stage","private":true}\n' > "$pkgdir/package.json"
  if ! ( cd "$pkgdir" && timeout 180 "$OV_NPM" install --legacy-peer-deps --registry="$reg" --no-audit --no-fund --no-save $peers >/dev/null 2>&1 ); then
    ov_safe_rm "$pkgdir" 2>/dev/null || true
    log_error ""$OV_NPM" install failed for $name peer deps: $peers"
    return 1
  fi
  mkdir -p "$dest/node_modules"
  cp -a "$pkgdir/node_modules/." "$dest/node_modules/"
  ov_safe_rm "$pkgdir" 2>/dev/null || true
  return 0
}
# Provision a plugin on demand into <dest> for the agent that needs it. Diff-based:
# checks upstream, downloads ONLY the actual file changes (verified against the
# official GitHub tree), all served via the domestic-first raw mirror list. If the
# cache already records the upstream commit, nothing is re-downloaded. If upstream
# is unreachable, the existing <dest> copy is reused (warn) — no network, no skill
# vendoring involved. Globals used: DRY_RUN.
ov_plugin_provision() {
  local name="$1" dest="$2"
  local exdir="" peers=""
  local p rest
  for p in "${OV_PLUGINS[@]}"; do
    if [[ "${p%%|*}" == "$name" ]]; then
      rest="${p#*|}"
      rest="${rest#*|}"         # drop npm package field
      exdir="${rest%%|*}"; peers="${rest#*|}"
      [[ "$peers" == "$rest" ]] && peers=""
      break
    fi
  done
  [[ -n "$exdir" ]] || { log_error "Unknown plugin: $name"; return 1; }
  # P9: a stale non-directory at $dest (e.g. an empty placeholder file left by an
  # earlier run) makes mkdir -p "$dest/..." fail with "Not a directory" and trigger an
  # error flood. Remove it cleanly before provisioning writes into the destination.
  if [[ -e "$dest" && ! -d "$dest" ]]; then
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
      log_warn "[DRY-RUN] would remove stale non-directory at plugin destination: $dest"
    else
      log_warn "Removing stale non-directory at plugin destination: $dest"
      rm -f -- "$dest" || { log_error "Cannot remove stale path: $dest"; return 1; }
    fi
  fi
  local upstream=""
  if ! upstream=$(ov_plugin_upstream_sha); then
    log_warn "Plugin source unreachable — reusing existing install at $dest (if present)"
    [[ -d "$dest" ]] || { log_error "No existing plugin install at $dest"; return 1; }
    return 0
  fi
  # Warm mirror pickers in the parent shell so parallel download subshells inherit a
  # single health-check result instead of each probing the chain independently.
  ov_pick_gh_mirror >/dev/null 2>&1 || true
  ov_plugin_api_base >/dev/null 2>&1 || true
  local cached; cached=$(ov_plugin_cache_sha "$dest")
  if [[ -n "$cached" && "$cached" == "$upstream" ]]; then
    log_ok "Plugin $name already installed at upstream commit (${upstream:0:7})"
    return 0
  fi
  mkdir -p /tmp/openviking
  local stage; stage=$(mktemp -d /tmp/openviking/ov-plugin.XXXXXX) || { log_error "mktemp failed for $name plugin staging"; return 1; }
  local newtree
  if ! newtree=$(_ov_tree_fetch "$upstream" "$stage"); then
    log_warn "Failed to fetch upstream tree — reusing existing install at $dest (if present)"
    ov_safe_rm "$stage" 2>/dev/null || true
    [[ -d "$dest" ]] || { log_error "No existing plugin install at $dest"; return 1; }
    return 0
  fi
  local entries=""
  if [[ -n "$cached" ]]; then
    local oldtree=""
    oldtree=$(_ov_tree_fetch "$cached" "$stage") || true
    if [[ -n "$oldtree" && -f "$oldtree" ]]; then
      entries=$(_ov_diff_blobs "$oldtree" "$newtree" "$exdir")
    fi
  fi
  # No diff baseline: emit add entries from the current tree. Strip the blob sha so
# path matches the "A <path>" format used by _ov_diff_blobs.
  [[ -n "$entries" ]] || entries="$(ov_plugin_blob_map "$newtree" "$exdir" | awk -F'\t' '{print "A " $1}')"

  local dl=() del=() op path
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    read -r op path <<< "$line"
    if [[ "$op" == "D" ]]; then del+=("$path"); else dl+=("$path"); fi
  done <<< "$entries"
  if [[ ${#dl[@]} -eq 0 && ${#del[@]} -eq 0 && -n "$cached" ]]; then
    log_ok "Plugin $name: no file changes upstream (${upstream:0:7}) — recording commit"
    if [[ "${DRY_RUN:-false}" != "true" ]]; then
      _ov_write_sync_meta "$dest" "$upstream" "$exdir"
    fi
  else
    log_info "Plugin $name: ${#dl[@]} file(s) to install, ${#del[@]} to delete (upstream ${upstream:0:7})"
    if [[ "${DRY_RUN:-false}" == "true" ]]; then
      log_warn "[DRY-RUN] would update plugin source at $dest"
      ov_safe_rm "$stage" 2>/dev/null || true
      return 0
    fi
    # Dest dir is created lazily by _ov_download_files / _ov_write_sync_meta.
    _ov_download_files "$upstream" "$newtree" "$exdir" "$dest" "${dl[@]}" || { ov_safe_rm "$stage" 2>/dev/null || true; return 1; }
    local dd
    for dd in "${del[@]}"; do rm -f "$dest/${dd#*$exdir/}"; done
    _ov_ensure_peers "$name" "$peers" "$dest" || { ov_safe_rm "$stage" 2>/dev/null || true; return 1; }
    _ov_write_sync_meta "$dest" "$upstream" "$exdir"
    log_ok "Plugin $name installed on demand (${#dl[@]} downloaded, ${#del[@]} deleted) -> $dest"
  fi
  ov_safe_rm "$stage" 2>/dev/null || true
  return 0
}

# P2-12: Post-install npm audit check — warns on high/critical vulnerabilities
ov_npm_audit_check() {
  local dir="$1"
  [[ -z "$dir" || ! -d "$dir" ]] && return 0
  if [[ "${OV_NPM_AUDIT:-false}" != "true" ]]; then return 0; fi
  local audit_result
  audit_result=$(cd "$dir" && "$OV_NPM" audit --json 2>/dev/null) || return 0
  local high_crit
  high_crit=$(echo "$audit_result" | "$OV_PY" -c "
import json,sys
try:
    d=json.load(sys.stdin)
    m=d.get('metadata',{}).get('vulnerabilities',{})
    print(m.get('high',0)+m.get('critical',0))
except: print(0)
" 2>/dev/null || echo 0)
  if [[ "$high_crit" -gt 0 ]]; then
    log_warn "npm audit: $high_crit high/critical vulnerabilities found in $dir"
  fi
}

# P2-21: Runtime integrity verification — compare installed plugin SHA against upstream
ov_verify_runtime_integrity() {
  local plugin_dir="$1" plugin_name="${2:-plugin}"
  [[ -z "$plugin_dir" || ! -d "$plugin_dir" ]] && return 0
  local meta_file="${plugin_dir}/.ov-sync-meta"
  [[ ! -f "$meta_file" ]] && return 0
  local recorded_sha; recorded_sha=$(head -1 "$meta_file" 2>/dev/null)
  [[ -z "$recorded_sha" ]] && return 0
  local upstream_sha; upstream_sha=$(ov_plugin_upstream_sha 2>/dev/null)
  [[ -z "$upstream_sha" ]] && return 0
  if [[ "$recorded_sha" != "$upstream_sha" ]]; then
    log_warn "$plugin_name: runtime SHA mismatch (recorded=${recorded_sha:0:7}, upstream=${upstream_sha:0:7}) — may need re-sync"
    return 1
  fi
  log_ok "$plugin_name: runtime integrity verified (${recorded_sha:0:7})"
  return 0
}
