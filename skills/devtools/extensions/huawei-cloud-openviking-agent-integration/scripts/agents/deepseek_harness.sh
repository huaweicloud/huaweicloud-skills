#!/bin/bash
# =============================================================================
# agents/deepseek_harness.sh — DeepSeek Harness agent subclass
# =============================================================================
# Mechanism: dsh-memory-plugin bundle
# Inherits shared operations from lib/base.sh (agent::*).
# Overrides: agent_deepseek_harness_integrate, agent_deepseek_harness_unbind, agent_deepseek_harness_status
# =============================================================================

# ── Registration ─────────────────────────────────────────────────────────────
agent_deepseek_harness_register() {
  agent::set_meta name "deepseek_harness"
  agent::set_meta display_name "DeepSeek Harness"
  agent::set_meta sandbox_pattern "deepseek-harness-*"
  agent::set_meta template_path "/root/template/deepseek-harness/start.sh"
  agent::set_meta mechanism "dsh-memory-plugin bundle"
  registry_add "deepseek_harness"
}

# ── Helper functions (deepseek-harness specific) ──────────────────────────────
dsh_ov_body() {
  cat <<'DSHOVBODY'
import json
import os
import shutil
import sys

home = sys.argv[1]
src = sys.argv[2]
url = sys.argv[3]

BUNDLE = '@openviking/dsh-memory-plugin'


def install(prof):
    pdir = os.path.join(home, 'profiles', prof)
    manifest = os.path.join(pdir, 'package.json')
    if not os.path.isfile(manifest):
        sys.stderr.write('skip %s profile: package.json not found\n' % prof)
        return
    target = os.path.join(pdir, 'node_modules', '@openviking', 'dsh-memory-plugin')
    # Remove broken symlink left by pnpm link: resolution
    if os.path.islink(target) and not os.path.isdir(target):
        os.remove(target)
    if os.path.islink(target):
        os.remove(target)
    if os.path.isdir(src) and not os.path.isdir(target):
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        shutil.copytree(src, target)
    with open(manifest, encoding='utf-8') as f:
        pkg = json.load(f)
    changed = False
    # Do NOT add link: dependency — pnpm creates broken relative symlinks from sandbox paths.
    # The real dir in node_modules + dsh.profile.bundles registration is sufficient.
    deps = pkg.get('dependencies', {})
    if BUNDLE in deps:
        del deps[BUNDLE]
        changed = True
    bundles = pkg.setdefault('dsh', {}).setdefault('profile', {}).setdefault('bundles', [])
    if BUNDLE not in bundles:
        bundles.append(BUNDLE)
        changed = True
    if changed:
        with open(manifest, 'w', encoding='utf-8') as f:
            json.dump(pkg, f, indent=2)
    print('openviking-memory bundle ready in %s profile -> %s' % (prof, target))


install('web')
install('dsh-tui')
DSHOVBODY
}

dsh_tpl_block() {
  local url="$1"
  cat <<DSHOVBLK
# ═══════════════════════════════════════════════════════════════════════════
# OpenViking long-term memory integration (added by huawei-cloud-openviking-agent-integration skill)
#   Native mechanism: @openviking/dsh-memory-plugin (official OpenViking dsh-memory bundle,
#   installed on demand at \$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin with self-contained peers
#   for @deepseek-ai/dsh-llm + @deepseek-ai/dsh-tools) is installed as a real package into the
#   web / dsh-tui profile node_modules and registered in dsh.profile.bundles. dsh profile-boot
#   then composes the plugin's cordis.patch.yml (openviking-memory group): viking_search /
#   viking_read / viking_browse / viking_remember / viking_forget / viking_add_resource /
#   viking_archive_expand tools + startup profile injection + per-step recall + auto-capture,
#   against the OpenViking server. No pnpm install needed; idempotent; cache-first (peer dep sync guarded by marker file, skips on restart).
# ═══════════════════════════════════════════════════════════════════════════
if [ -d "\$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" ]; then
  export OPENVIKING_URL="\${OPENVIKING_URL:-${url}}"
  python3 - "\$DSH_HOME" "\$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" "\$OPENVIKING_URL" <<'OVDSPY'
$(dsh_ov_body)
OVDSPY
  # Sync @deepseek-ai/* peer deps (ESM-safe real copies, not symlinks)
  # Cache guard: skip the 193-package copy loop if already synced (marker file present)
  _dsh_nm="\$DSH_RUNTIME/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
  _plugin_da="\$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin/node_modules/@deepseek-ai"
  _peers_marker="\$_plugin_da/.openviking-peers-synced"
  if [[ -f "\$_peers_marker" ]]; then
    echo "OpenViking peer deps already synced — skipping (cache hit)."
  elif [[ -d "\$_dsh_nm" && -d "\$_plugin_da" ]]; then
    for _pd in "\$_dsh_nm"/*; do
      [[ -d "\$_pd" ]] || continue
      _pn=\$(basename "\$_pd")
      [[ "\$_pn" == "dsh-llm" || "\$_pn" == "dsh-tools" ]] && continue
      rm -rf "\$_plugin_da/\$_pn"
      cp -r "\$_pd" "\$_plugin_da/\$_pn"
    done
    touch "\$_peers_marker"
    echo "OpenViking peer deps synced + marker written."
  fi
fi
DSHOVBLK
}

dsh_sync_peer_deps() {
  local plugin_dir="$1"
  local plugin_da="${plugin_dir}/node_modules/@deepseek-ai"
  local dsh_nm="/root/runtime/deepseek-harness/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"

  if [[ ! -d "$dsh_nm" ]]; then
    log_warn "dsh main install not found at $dsh_nm — skipping peer dep sync"
    return 0
  fi

  # Dry-run: no writes; report what would be synced.
  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    local _c=0 _pd
    for _pd in "$dsh_nm"/*; do
      [[ -d "$_pd" ]] || continue
      _c=$((_c + 1))
    done
    log_info "[DRY-RUN] would sync $((_c > 0 ? _c - 2 : 0)) @deepseek-ai/* peer deps into plugin node_modules (minus dsh-llm/dsh-tools)"
    return 0
  fi

  if [[ ! -d "$plugin_da" ]]; then
    mkdir -p "$plugin_da"
  fi

  local count=0
  for pkg_dir in "$dsh_nm"/*; do
    [[ -d "$pkg_dir" ]] || continue
    local pkg; pkg=$(basename "$pkg_dir")
    local dest="${plugin_da}/${pkg}"
    # Skip dsh-llm and dsh-tools — the plugin bundles its own copies
    [[ "$pkg" == "dsh-llm" || "$pkg" == "dsh-tools" ]] && continue
    # Remove existing (symlink or stale copy) and replace with fresh copy
    rm -rf "$dest"
    cp -r "$pkg_dir" "$dest"
    count=$((count + 1))
  done
  log_ok "Synced ${count} @deepseek-ai/* peer deps into plugin node_modules (ESM-safe real copies)"
}

# ── Integrate ─────────────────────────────────────────────────────────────────
agent_deepseek_harness_integrate() {
  local tpl="/root/template/deepseek-harness/start.sh"
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"
  local plugin_src="/root/runtime/deepseek-harness/plugins/@openviking/dsh-memory-plugin"

  # Install the official plugin on demand into the (sandbox bind-mounted) runtime.
  ov_plugin_provision "dsh-memory-plugin" "$plugin_src" || return 1
  touch "$plugin_src"  # Refresh TTL timestamp (cache valid for 24h)

  # Sync @deepseek-ai/* peer deps (ESM-safe real copies, not symlinks)
  dsh_sync_peer_deps "$plugin_src"

  local tpl_has_ov=false
  grep -q "OpenViking long-term memory integration" "$tpl" 2>/dev/null && tpl_has_ov=true
  local live_has_ov=false
  if grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/web/package.json" 2>/dev/null \
     || grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/dsh-tui/package.json" 2>/dev/null; then
    live_has_ov=true
  fi

  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    log_ok "DeepSeek Harness already integrated with OpenViking (dsh-memory-plugin bundle, template + live)"
    return 0
  fi

  require_confirmation "Integrate OpenViking" "deepseek-harness" "Install @openviking/dsh-memory-plugin bundle into dsh profiles (web/dsh-tui) + template start.sh" || return 1
  if dry_run_msg "Would install dsh-memory-plugin into $dsh_home/profiles/{web,dsh-tui} (node_modules + package.json bundles) + template $tpl"; then return 0; fi

  # ── 1. Runtime seed profiles (deploy-resilient layer) ──
  # Pre-seed runtime home/profiles so that undeploy→deploy preserves integration.
  # deploy overwrites template start.sh but does NOT re-extract runtime home/.
  # We register dsh.profile.bundles + install real dir in node_modules (no link: dep,
  # which causes pnpm to create broken relative symlinks from sandbox paths).
  local dsh_runtime_home="/root/runtime/deepseek-harness/home"
  if [[ -d "$dsh_runtime_home/profiles" ]]; then
    python3 - "$dsh_runtime_home" "$plugin_src" <<'DSHSEED'
import json, os, shutil, sys
home = sys.argv[1]
src = sys.argv[2]
BUNDLE = '@openviking/dsh-memory-plugin'
for prof in ('web', 'dsh-tui'):
    pdir = os.path.join(home, 'profiles', prof)
    manifest = os.path.join(pdir, 'package.json')
    if not os.path.isfile(manifest):
        continue
    with open(manifest, encoding='utf-8') as f:
        pkg = json.load(f)
    changed = False
    deps = pkg.get('dependencies', {})
    if BUNDLE in deps:
        del deps[BUNDLE]
        changed = True
    bundles = pkg.setdefault('dsh', {}).setdefault('profile', {}).setdefault('bundles', [])
    if BUNDLE not in bundles:
        bundles.append(BUNDLE)
        changed = True
    if changed:
        with open(manifest, 'w', encoding='utf-8') as f:
            json.dump(pkg, f, indent=2)
    target = os.path.join(pdir, 'node_modules', '@openviking', 'dsh-memory-plugin')
    if os.path.islink(target):
        os.remove(target)
    if not os.path.isdir(target):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copytree(src, target)
DSHSEED
    log_ok "Runtime seed profiles pre-seeded (deploy-resilient: bundles + real dir, no link: dep)"
  fi

  # ── 3. Live sandbox (immediate effect) ──
  dsh_ov_body | python3 - "$dsh_home" "$plugin_src" "$OV_ENDPOINT"
  log_ok "dsh-memory-plugin bundle installed into live dsh profiles (web/dsh-tui)"
  live_has_ov=true

  # ── 4. Template start.sh (persistent) ──
  if [[ "$tpl_has_ov" == "false" ]]; then
    if [[ -f "$tpl" ]]; then
      backup_file "$tpl"
      local inj
      inj="/tmp/dsh_inject_$$.py"
      cat > "$inj" <<'DSHINJ'
import sys
path = sys.argv[1]
anchor = 'echo "==> starting DeepSeek Harness web UI (http://127.0.0.1:13079) ..."\n'
block = sys.stdin.read()
with open(path, encoding='utf-8') as f:
    content = f.read()
if 'OpenViking long-term memory integration' in content:
    sys.exit(0)
if anchor not in content:
    sys.stderr.write('ERROR: anchor not found in template start.sh\n')
    sys.exit(1)
content = content.replace(anchor, block + anchor, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
DSHINJ
      dsh_tpl_block "$OV_ENDPOINT" | python3 "$inj" "$tpl"
      rm -f "$inj"
      log_ok "OpenViking integration block injected into template start.sh"
      tpl_has_ov=true
    else
      log_warn "Template $tpl missing — skipping template injection (live only, lost on restart)"
    fi
  fi

  # ── 5. Sync template to sandbox so a restart preserves integration ──
  if [[ "$tpl_has_ov" == "true" && -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Template start.sh synced to sandbox .process_dir"
  fi

  log_info "Restart DeepSeek Harness (web + dsh-tui) for full effect"
}


# ── Unbind ───────────────────────────────────────────────────────────────────
agent_deepseek_harness_unbind() {
  local tpl="/root/template/deepseek-harness/start.sh"
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"

  local tpl_has_ov=false live_has_ov=false
  grep -q "OpenViking long-term memory integration" "$tpl" 2>/dev/null && tpl_has_ov=true
  for p in web dsh-tui; do
    grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/$p/package.json" 2>/dev/null && live_has_ov=true
    [[ -d "${dsh_home}/profiles/$p/node_modules/@openviking/dsh-memory-plugin" ]] && live_has_ov=true
  done

  [[ "$tpl_has_ov" == "false" && "$live_has_ov" == "false" ]] && { log_ok "DeepSeek Harness not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking" "deepseek-harness" "Remove @openviking/dsh-memory-plugin bundle from dsh profiles (web/dsh-tui) + template start.sh" "$RED" || return 1
  if dry_run_msg "Would remove dsh-memory-plugin from live profiles (node_modules + package.json) + template start.sh"; then return 0; fi

  # ── 1. Template start.sh (persistent) ──
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    python3 << 'DSHUNBINJ'
import os
path = "/root/template/deepseek-harness/start.sh"
with open(path) as f:
    lines = f.read().split('\n')
out = []
i = 0
# The injected block is inserted right before the "starting DeepSeek Harness web UI"
# anchor (see integrate's DSHOVBLK insertion). Remove the contiguous region from the
# preceding '# ═══' rule line up to (not including) that anchor. This is robust
# against nested if/fi depth inside the block.
anchor = 'echo "==> starting DeepSeek Harness web UI'
anchor_idx = None
for i, line in enumerate(lines):
    if anchor in line:
        anchor_idx = i
        break
if anchor_idx is not None:
    # The block contains TWO '# ═══════════' rule lines (one heading the comment
    # header, one below it), so walking up from the anchor would stop at the inner
    # one and leave the header orphaned. Instead locate the marker line first, then
    # back up to the rule line directly above it.
    marker_idx = None
    for i in range(anchor_idx - 1, -1, -1):
        if 'OpenViking long-term memory integration' in lines[i]:
            marker_idx = i
            break
    start = None
    if marker_idx is not None:
        for i in range(marker_idx - 1, -1, -1):
            if lines[i].startswith('# ═══════════'):
                start = i
                break
    if start is None and marker_idx is not None:
        start = marker_idx
    if start is not None:
        # Trim blank lines right before the anchor.
        end = anchor_idx
        while end > start and lines[end - 1] == '':
            end -= 1
        out = lines[:start] + lines[anchor_idx:]
        i = len(lines)
while out and out[-1] == '':
    out.pop()
with open(path, 'w') as f:
    f.write('\n'.join(out) + '\n')
DSHUNBINJ
    log_ok "OpenViking integration block removed from template start.sh"
  fi

  # ── 2. Live sandbox profiles ──
  if [[ "$live_has_ov" == "true" ]]; then
    for p in web dsh-tui; do
      local cf="${dsh_home}/profiles/$p/package.json"
      [[ -f "$cf" ]] || continue
      backup_file "$cf" 2>/dev/null || true
      rm -rf "${dsh_home}/profiles/$p/node_modules/@openviking"
      python3 - "$cf" << 'DSHPJSON'
import json
import sys
path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    pkg = json.load(f)
changed = False
deps = pkg.get('dependencies')
if deps:
    if deps.pop('@openviking/dsh-memory-plugin', None) is not None:
        changed = True
    if not deps:
        pkg.pop('dependencies')
bundles = pkg.get('dsh', {}).get('profile', {}).get('bundles')
if bundles:
    b = [x for x in bundles if x != '@openviking/dsh-memory-plugin']
    if len(b) != len(bundles):
        bundles[:] = b
        changed = True
    if not bundles:
        profile = pkg.get('dsh', {}).get('profile', {})
        profile.pop('bundles', None)
        if not profile:
            pkg.get('dsh', {}).pop('profile', None)
        if not pkg.get('dsh'):
            pkg.pop('dsh', None)
if changed:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pkg, f, indent=2)
DSHPJSON
    done
    log_ok "dsh-memory-plugin bundle removed from live dsh profiles (web/dsh-tui)"
  fi


  # ── 2b. Runtime seed profiles (deploy-resilient layer) ──
  # Integrate pre-seeds /root/runtime/deepseek-harness/home/profiles/ so that
  # undeploy→deploy preserves integration. Unbind must clean these too, otherwise
  # a redeploy after unbind inherits stale OV bundles (status shows "partial"
  # instead of "not_integrated").
  local dsh_runtime_home="/root/runtime/deepseek-harness/home"
  if [[ -d "$dsh_runtime_home/profiles" ]]; then
    local rt_cleaned=false
    for p in web dsh-tui; do
      local rt_cf="$dsh_runtime_home/profiles/$p/package.json"
      [[ -f "$rt_cf" ]] || continue
      # Remove node_modules/@openviking dir
      if [[ -d "$dsh_runtime_home/profiles/$p/node_modules/@openviking" ]]; then
        rm -rf "$dsh_runtime_home/profiles/$p/node_modules/@openviking"
        rt_cleaned=true
      fi
      # Clean package.json: remove bundle registration + any link: dep
      if grep -q '"@openviking/dsh-memory-plugin"' "$rt_cf" 2>/dev/null; then
        python3 - "$rt_cf" << 'DSHRTJSON'
import json
import sys
path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    pkg = json.load(f)
changed = False
deps = pkg.get('dependencies')
if deps:
    if deps.pop('@openviking/dsh-memory-plugin', None) is not None:
        changed = True
    if not deps:
        pkg.pop('dependencies')
bundles = pkg.get('dsh', {}).get('profile', {}).get('bundles')
if bundles:
    b = [x for x in bundles if x != '@openviking/dsh-memory-plugin']
    if len(b) != len(bundles):
        bundles[:] = b
        changed = True
    if not bundles:
        profile = pkg.get('dsh', {}).get('profile', {})
        profile.pop('bundles', None)
        if not profile:
            pkg.get('dsh', {}).pop('profile', None)
        if not pkg.get('dsh'):
            pkg.pop('dsh', None)
if changed:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(pkg, f, indent=2)
DSHRTJSON
        rt_cleaned=true
      fi
    done
    if [[ "$rt_cleaned" == "true" ]]; then
      log_ok "Runtime seed profiles cleaned (deploy-resilient layer removed: bundles + node_modules/@openviking)"
    fi
  fi

  # ── 3. Sync template to sandbox so a restart stays clean ──
  if [[ -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Cleaned template start.sh synced to sandbox .process_dir"
  fi

  log_info "Restart DeepSeek Harness (web + dsh-tui) for changes to take full effect"
}


# ── Status ───────────────────────────────────────────────────────────────────
agent_deepseek_harness_status() {
  local tpl="/root/template/deepseek-harness/start.sh"
  local tpl_has_ov=false
  grep -q "OpenViking long-term memory integration" "$tpl" 2>/dev/null && tpl_has_ov=true

  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { echo "deepseek-harness|unknown|sandbox not found"; return; }
  local live_has_ov=false
  local live_scope=""
  local p
  for p in web dsh-tui; do
    if grep -q '"@openviking/dsh-memory-plugin"' "${sandbox}/.dsh/profiles/$p/package.json" 2>/dev/null \
       || [[ -d "${sandbox}/.dsh/profiles/$p/node_modules/@openviking/dsh-memory-plugin" ]]; then
      live_has_ov=true
      live_scope="${live_scope:+$live_scope,}$p"
    fi
  done

  if [[ "$tpl_has_ov" == "true" && "$live_has_ov" == "true" ]]; then
    echo "deepseek-harness|integrated|dsh-memory-plugin bundle (template + live profiles: ${live_scope:-none})"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    echo "deepseek-harness|integrated|dsh-memory-plugin bundle configured (template only, restart to activate)"
  elif [[ "$live_has_ov" == "true" ]]; then
    echo "deepseek-harness|partial|dsh-memory-plugin bundle (live profiles: ${live_scope:-none}, lost on restart)"
  else
    echo "deepseek-harness|not_integrated|No OpenViking memory bundle"
  fi
}

