#!/bin/bash
# =============================================================================
# lib/plugins.sh — Plugin provisioning system
# On-demand install, domestic sources first, SHA-1 verified against upstream.
# Part of the OO refactoring. Sourced by lib/base.sh.
# =============================================================================
# plugins not yet published to npm (dsh-memory-plugin, pi-coding-agent-extension),
# fetched straight from the official volcengine/OpenViking repo. No plugin files
# live inside the skill itself.
#
# Domestic-first source order:
#   npm   : mirrors.huaweicloud.com → registry.npmmirror.com → registry.npmjs.org
#   GitHub: ghfast.top → gh-proxy.com → raw.githubusercontent.com (file downloads)
#           api.github.com for commit/tree metadata (domestic proxies 403 on the
#           GitHub API, so metadata is fetched direct; api.github.com is reachable)
#
# Files downloaded directly are source-checked: each file is verified byte-for-byte
# against the authoritative GitHub blob SHA from the official repo tree, so whatever
# mirror delivered the bytes, the content is only accepted if it matches upstream.
OV_PLUGIN_REPO="https://github.com/volcengine/OpenViking.git"
OV_PLUGIN_API="https://api.github.com/repos/volcengine/OpenViking"
OV_PLUGIN_REPO_HOST="github.com"
OV_PLUGIN_REPO_PATH="volcengine/OpenViking"

# npm registries, domestic mirrors first
NPM_REGISTRIES=(
  "https://mirrors.huaweicloud.com/repository/npm/"
  "https://registry.npmmirror.com/"
  "https://registry.npmjs.org/"
)
# GitHub raw file mirrors, domestic first. Each entry is a base URL; the repo-relative
# path (volcengine/OpenViking/<sha>/...) is appended directly.
GH_RAW_MIRRORS=(
  "https://ghfast.top/https://raw.githubusercontent.com"
  "https://gh-proxy.com/https://raw.githubusercontent.com"
  "https://raw.githubusercontent.com"
)

# name|npm package (empty = GitHub-only)|upstream example dir|npm peer deps (optional)
# opencode-plugin: published to npm; pure .mjs, zero runtime deps
# openclaw-plugin: published to npm; needs @sinclair/typebox + fflate after tsc build
# dsh/pi-coding-agent-extension: NOT published to npm — pulled from GitHub only
OV_PLUGINS=(
  "opencode-plugin|@openviking/opencode-plugin|examples/opencode-plugin|"
  "openclaw-plugin|@openviking/openclaw-plugin|examples/openclaw-plugin|@sinclair/typebox@0.34.48 fflate@^0.8.2"
  "dsh-memory-plugin||examples/dsh-memory-plugin|@deepseek-ai/dsh-llm@0.1.0-rc.6 @deepseek-ai/dsh-tools@0.1.0-rc.6"
  "pi-coding-agent-extension||examples/pi-coding-agent-extension|"
)

# Validate that a plugin source URL is the official volcengine/OpenViking repo.
ov_plugin_validate_source() {
  local url="$1"
  python3 - "$url" "$OV_PLUGIN_REPO_HOST" "$OV_PLUGIN_REPO_PATH" <<'PY'
import sys
from urllib.parse import urlparse
url, host, path = sys.argv[1], sys.argv[2], sys.argv[3]
u = urlparse(url)
ok_host = u.hostname in (host, f"www.{host}")
p = u.path.rstrip('/').lstrip('/').removesuffix('.git')
ok_path = p == path or p.endswith('/' + path)
sys.exit(0 if (ok_host and ok_path and u.scheme in ('http', 'https')) else 1)
PY
}

# Latest upstream commit SHA of the plugin repo (GitHub API first — fast; git ls-remote fallback).
ov_plugin_upstream_sha() {
  local repo_url="${OPENVIKING_PLUGIN_REPO_URL:-$OV_PLUGIN_REPO}"
  ov_plugin_validate_source "$repo_url" || { log_error "Plugin source not allowed: $repo_url"; return 1; }
  local sha
  sha=$(curl -fsS --retry 2 --connect-timeout 10 --max-time 30 "${OPENVIKING_PLUGIN_API_URL:-$OV_PLUGIN_API}/commits/HEAD" 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || true)
  if [[ ${#sha} -ne 40 ]]; then
    sha=$(timeout 20 git ls-remote "$repo_url" HEAD 2>/dev/null | awk '{print $1}') || true
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
  for reg in "${NPM_REGISTRIES[@]}"; do
    if curl -fsS --connect-timeout 8 --max-time 15 "$reg" -o /dev/null 2>/dev/null; then
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
    if curl -fsS --connect-timeout 8 --max-time 25 "$url" -o "$out"; then return 0; fi
    if (( tries >= 8 )); then log_error "Gave up after 8 attempts: $url"; return 1; fi
    if (( $(date +%s) - t_start > 200 )); then log_error "Timed out fetching: $url"; return 1; fi
    sleep 3
  done
}

# Fetch a repo-relative <path> at <sha>, trying the domestic-first raw mirror list.
# Returns 0 on success (writes <out>).
_ov_fetch_mirrored() {
  local sha="$1" path="$2" out="$3"
  local base
  for base in "${GH_RAW_MIRRORS[@]}"; do
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
  if ! curl -fsS --retry 3 --connect-timeout 10 --max-time 60 "${OPENVIKING_PLUGIN_API_URL:-$OV_PLUGIN_API}/git/trees/$sha?recursive=1" -o "$out"; then
    return 1
  fi
  echo "$out"
}

# Diff plugin files between old and new tree JSONs for <exdir>.
# Emits: "A <path>" added, "M <path>" modified, "D <path>" deleted.
_ov_diff_blobs() {
  python3 - "$1" "$2" "$3" <<'PY'
import json, sys
old, new, exdir = sys.argv[1], sys.argv[2], sys.argv[3]
def m(fn):
    d = json.load(open(fn)); out = {}
    for e in d.get('tree', []):
        if e.get('type') == 'blob' and e.get('path', '').startswith(exdir + '/'):
            out[e['path']] = e['sha']
    return out
o, n = m(old), m(new)
for p in sorted(set(o) | set(n)):
    if p not in o: print('A', p)
    elif p not in n: print('D', p)
    elif o[p] != n[p]: print('M', p)
PY
}

# path<tab>blob-sha map for <exdir> from a GitHub tree JSON.
ov_plugin_blob_map() {
  python3 - "$1" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
exdir = sys.argv[2]
for e in d.get('tree', []):
    if e.get('type') == 'blob' and e.get('path', '').startswith(exdir + '/'):
        print(e['path'] + '\t' + e['sha'])
PY
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
      python3 - "$dest/$rel" "$blobsha" <<'PY'
import hashlib, sys
p, sha = sys.argv[1], sys.argv[2]
data = open(p, 'rb').read()
actual = hashlib.sha1(b'blob %d\x00' % len(data) + data).hexdigest()
sys.exit(0 if actual == sha else 1)
PY
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
  if ! ( cd "$pkgdir" && timeout 180 npm install --legacy-peer-deps --registry="$reg" --no-audit --no-fund --no-save $peers >/dev/null 2>&1 ); then
    rm -rf "$pkgdir"
    log_error "npm install failed for $name peer deps: $peers"
    return 1
  fi
  mkdir -p "$dest/node_modules"
  cp -a "$pkgdir/node_modules/." "$dest/node_modules/"
  rm -rf "$pkgdir"
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

  local upstream=""
  if ! upstream=$(ov_plugin_upstream_sha); then
    log_warn "Plugin source unreachable — reusing existing install at $dest (if present)"
    [[ -d "$dest" ]] || { log_error "No existing plugin install at $dest"; return 1; }
    return 0
  fi

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
    rm -rf "$stage"
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
      rm -rf "$stage"
      return 0
    fi
    # Dest dir is created lazily by _ov_download_files / _ov_write_sync_meta.
    _ov_download_files "$upstream" "$newtree" "$exdir" "$dest" "${dl[@]}" || { rm -rf "$stage"; return 1; }
    local dd
    for dd in "${del[@]}"; do rm -f "$dest/${dd#*$exdir/}"; done
    _ov_ensure_peers "$name" "$peers" "$dest" || { rm -rf "$stage"; return 1; }
    _ov_write_sync_meta "$dest" "$upstream" "$exdir"
    log_ok "Plugin $name installed on demand (${#dl[@]} downloaded, ${#del[@]} deleted) -> $dest"
  fi

  rm -rf "$stage"
  return 0
}

