#!/bin/bash
# agents/deepseek_harness.sh — DeepSeek Harness agent subclass (dsh-memory-plugin bundle)
# Inherits from lib/base.sh; overrides integrate/unbind/status.
agent_deepseek_harness_register() {
  agent::set_meta name "deepseek_harness"
  agent::set_meta display_name "DeepSeek Harness"
  agent::set_meta sandbox_pattern "deepseek-harness-*"
  agent::set_meta template_path "$OV_TEMPLATE_DIR/deepseek-harness/start.sh"
  agent::set_meta mechanism "dsh-memory-plugin bundle"
  registry_add "deepseek_harness"
}

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
    # Don't add link: dep — pnpm creates broken symlinks; real dir + bundles registration suffices.
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
# ── OpenViking memory integration (added by huawei-cloud-openviking-agent-integration skill) ──
# @openviking/dsh-memory-plugin installed as real package into web/dsh-tui profile node_modules,
# registered in dsh.profile.bundles. Idempotent; cache-first (peer dep sync guarded by marker).
if [ -d "\$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" ]; then
  export OPENVIKING_URL="\${OPENVIKING_URL:-${url}}"
  _ov_py=""
  for _py in python3.12 python3.11 python3.10 python3; do command -v "\$_py" >/dev/null 2>&1 && _ov_py="\$_py" && break; done
  : "\${_ov_py:=python3}"
  "\$_ov_py" - "\$DSH_HOME" "\$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" "\$OPENVIKING_URL" <<'OVDSPY' || true
$(dsh_ov_body)
OVDSPY
  _dsh_nm="\$DSH_RUNTIME/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
  _plugin_da="\$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin/node_modules/@deepseek-ai"
  _peers_marker="\$_plugin_da/.openviking-peers-synced"
  if [[ -f "\$_peers_marker" ]]; then
    echo "OV peer deps already synced (cache hit)."
  elif [[ -d "\$_dsh_nm" && -d "\$_plugin_da" ]]; then
    for _pd in "\$_dsh_nm"/*; do
      [[ -d "\$_pd" ]] || continue
      _pn=\$(basename "\$_pd")
      [[ "\$_pn" == "dsh-llm" || "\$_pn" == "dsh-tools" ]] && continue
      rm -rf "\$_plugin_da/\$_pn"
      cp -r "\$_pd" "\$_plugin_da/\$_pn"
    done
    touch "\$_peers_marker"
    echo "OV peer deps synced."
  fi
fi
DSHOVBLK
}

dsh_sync_peer_deps() {
  local plugin_dir="$1"
  local plugin_da="${plugin_dir}/node_modules/@deepseek-ai"
  local dsh_nm="$OV_RUNTIME_DIR/deepseek-harness/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
  if [[ ! -d "$dsh_nm" ]]; then
    log_warn "dsh main install not found at $dsh_nm — skipping peer dep sync"
    return 0
  fi
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
    [[ "$pkg" == "dsh-llm" || "$pkg" == "dsh-tools" ]] && continue
    rm -rf "$dest"
    cp -r "$pkg_dir" "$dest"
    count=$((count + 1))
  done
  log_ok "Synced ${count} @deepseek-ai/* peer deps into plugin node_modules (ESM-safe real copies)"
}

agent_deepseek_harness_integrate() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"
  local plugin_src="$OV_RUNTIME_DIR/deepseek-harness/plugins/@openviking/dsh-memory-plugin"
  ov_plugin_provision "dsh-memory-plugin" "$plugin_src" || return 1
  touch "$plugin_src"  # Refresh TTL timestamp (cache valid for 24h)
  dsh_sync_peer_deps "$plugin_src"
  local tpl_has_ov=false
  if grep -q "ov-deepseek-harness-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has_ov=true
  fi
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

  # Runtime seed profiles (deploy-resilient: bundles + real dir, no link: dep)
  local dsh_runtime_home="$OV_RUNTIME_DIR/deepseek-harness/home"
  if [[ -d "$dsh_runtime_home/profiles" ]]; then
    "$OV_PY" - "$dsh_runtime_home" "$plugin_src" <<'DSHSEED'
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
    log_ok "Runtime seed profiles pre-seeded (deploy-resilient)"
  fi
  # Live sandbox (immediate effect)
  dsh_ov_body | "$OV_PY" - "$dsh_home" "$plugin_src" "$OV_ENDPOINT"
  log_ok "dsh-memory-plugin bundle installed into live dsh profiles (web/dsh-tui)"
  live_has_ov=true
  # Template start.sh (persistent)
  if [[ "$tpl_has_ov" == "false" ]]; then
    if [[ -f "$tpl" ]]; then
      backup_file "$tpl"
      local init_sh="$OV_SHARED_DIR/ov-deepseek-harness-init.sh"
      local inj
      inj="/tmp/dsh_inject_$$.py"
      cat > "$inj" <<'DSHINJ'
import os
import sys
tpl_path = sys.argv[1]
init_path = sys.argv[2]
template_dir = sys.argv[3]
shared_dir = sys.argv[4]
block = sys.stdin.read()
with open(init_path, "w") as f:
    f.write("#!/usr/bin/env bash\n")
    f.write("# ── OpenViking integration for DeepSeek Harness ──\n")
    f.write(f"# Sourced by {template_dir}/deepseek-harness/start.sh (single source line).\n")
    f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
    f.write(block.lstrip("\n"))
os.chmod(init_path, 0o755)
source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-deepseek-harness-init.sh\n# ── End OpenViking integration ──\n\n"

with open(tpl_path, encoding='utf-8') as f:
    content = f.read()
if 'ov-deepseek-harness-init.sh' in content:
    sys.exit(0)
anchor = 'echo "==> starting DeepSeek Harness web UI (http://127.0.0.1:${DSH_WEB_PORT}) ..."\n'
if anchor not in content:
    sys.stderr.write('ERROR: anchor not found in template start.sh\n')
    sys.exit(1)
content = content.replace(anchor, source_block + anchor, 1)
with open(tpl_path, 'w', encoding='utf-8') as f:
    f.write(content)
DSHINJ
      dsh_tpl_block "$OV_ENDPOINT" | "$OV_PY" "$inj" "$tpl" "$init_sh" "$OV_TEMPLATE_DIR" "$OV_SHARED_DIR"
      rm -f "$inj"
      log_ok "OpenViking integration written to standalone script + source line injected into template start.sh"
      tpl_has_ov=true
    else
      log_warn "Template $tpl missing — skipping template injection (live only, lost on restart)"
    fi
  fi
  # Sync template to sandbox so a restart preserves integration
  if [[ "$tpl_has_ov" == "true" && -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Template start.sh synced to sandbox .process_dir"
  fi
  ov_log_info "重启 DeepSeek Harness（web + dsh-tui）以完全生效" "Restart DeepSeek Harness (web + dsh-tui) for full effect"
}

agent_deepseek_harness_unbind() {
  local tpl="${AGENT_META[template_path]}"
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { log_error "DeepSeek Harness sandbox not found"; return 1; }
  local dsh_home="${sandbox}/.dsh"

  local tpl_has_ov=false live_has_ov=false
  if grep -q "ov-deepseek-harness-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has_ov=true
  fi
  for p in web dsh-tui; do
    grep -q '"@openviking/dsh-memory-plugin"' "${dsh_home}/profiles/$p/package.json" 2>/dev/null && live_has_ov=true
    [[ -d "${dsh_home}/profiles/$p/node_modules/@openviking/dsh-memory-plugin" ]] && live_has_ov=true
  done
  [[ "$tpl_has_ov" == "false" && "$live_has_ov" == "false" ]] && { log_ok "DeepSeek Harness not integrated (nothing to remove)"; return 0; }

  require_confirmation "UNBIND OpenViking" "deepseek-harness" "Remove @openviking/dsh-memory-plugin bundle from dsh profiles (web/dsh-tui) + template start.sh" "$RED" || return 1
  if dry_run_msg "Would remove dsh-memory-plugin from live profiles (node_modules + package.json) + template start.sh"; then return 0; fi
  # Template start.sh (persistent)
  if [[ "$tpl_has_ov" == "true" ]]; then
    backup_file "$tpl"
    "$OV_PY" - "$tpl" << 'DSHUNBINJ'
import sys
path = sys.argv[1]
with open(path) as f:
    content = f.read()
changed = False
# New-style: remove the 3-line source block
marker = "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──"
idx = content.find(marker)
if idx != -1:
    end_marker = "# ── End OpenViking integration ──"
    end_idx = content.find(end_marker, idx)
    if end_idx != -1:
        cut_end = end_idx + len(end_marker)
        while cut_end < len(content) and content[cut_end] == '\n':
            cut_end += 1
        content = content[:idx] + content[cut_end:]
        changed = True
# Old-style fallback: remove the full injected block with ═══ rule lines
if not changed and 'OpenViking long-term memory integration' in content:
    lines = content.split('\n')
    anchor = 'echo "==> starting DeepSeek Harness web UI'
    anchor_idx = None
    for i, line in enumerate(lines):
        if anchor in line:
            anchor_idx = i
            break
    if anchor_idx is not None:
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
            end = anchor_idx
            while end > start and lines[end - 1] == '':
                end -= 1
            new_lines = lines[:start] + lines[anchor_idx:]
            while new_lines and new_lines[-1] == '':
                new_lines.pop()
            content = '\n'.join(new_lines) + '\n'
            changed = True
if changed:
    with open(path, 'w') as f:
        f.write(content)
DSHUNBINJ
    log_ok "OpenViking integration block removed from template start.sh"
    rm -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" && log_ok "Removed standalone ov-deepseek-harness-init.sh"
  fi
  # Live sandbox profiles
  if [[ "$live_has_ov" == "true" ]]; then
    for p in web dsh-tui; do
      local cf="${dsh_home}/profiles/$p/package.json"
      [[ -f "$cf" ]] || continue
      backup_file "$cf" 2>/dev/null || true
      rm -rf "${dsh_home}/profiles/$p/node_modules/@openviking"
      "$OV_PY" - "$cf" << 'DSHPJSON'
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
  # Runtime .dsh/profiles (deploy-resilient layer — must clean or redeploy inherits stale bundles)
  local _rt_profile_dirs=( "$OV_RUNTIME_DIR/deepseek-harness/.dsh/profiles" "$OV_RUNTIME_DIR/deepseek-harness/home/profiles" )
  local rt_cleaned=false
  for _rt_profiles in "${_rt_profile_dirs[@]}"; do
    [[ -d "$_rt_profiles" ]] || continue
    for p in web dsh-tui; do
      local rt_cf="$_rt_profiles/$p/package.json"
      [[ -f "$rt_cf" ]] || continue
      if [[ -d "$_rt_profiles/$p/node_modules/@openviking" ]]; then
        rm -rf "$_rt_profiles/$p/node_modules/@openviking"
        rt_cleaned=true
      fi
      if grep -q '"@openviking/dsh-memory-plugin"' "$rt_cf" 2>/dev/null; then
        "$OV_PY" - "$rt_cf" << 'DSHRTJSON'
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
  done
  if [[ "$rt_cleaned" == "true" ]]; then
    log_ok "Runtime .dsh/profiles cleaned (deploy-resilient layer removed)"
  fi
  # Plugin source cache
  local _plugin_cache="$OV_RUNTIME_DIR/deepseek-harness/plugins/@openviking"
  if [[ -d "$_plugin_cache" ]]; then
    rm -rf "$_plugin_cache"
    log_ok "Plugin source cache removed ($_plugin_cache)"
  fi
  # Sync template to sandbox so a restart stays clean
  if [[ -f "${sandbox}/.process_dir/start.sh" ]]; then
    cp "$tpl" "${sandbox}/.process_dir/start.sh"
    log_ok "Cleaned template start.sh synced to sandbox .process_dir"
  fi
  ov_log_info "重启 DeepSeek Harness（web + dsh-tui）以使更改完全生效" "Restart DeepSeek Harness (web + dsh-tui) for changes to take full effect"
}

agent_deepseek_harness_status() {
  local tpl="${AGENT_META[template_path]}"
  local tpl_has_ov=false
  if grep -q "ov-deepseek-harness-init.sh" "$tpl" 2>/dev/null || { [[ -f "$OV_SHARED_DIR/ov-deepseek-harness-init.sh" ]] && grep -q "OpenViking integration" "$tpl" 2>/dev/null; }; then
    tpl_has_ov=true
  fi
  local sandbox; sandbox=$(find_sandbox "deepseek-harness")
  [[ -z "$sandbox" ]] && { ov_status "deepseek-harness" "unknown" "sandbox not found"; return; }
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
    ov_status "deepseek-harness" "integrated" "dsh-memory-plugin bundle (template + live profiles: ${live_scope:-none})"
  elif [[ "$tpl_has_ov" == "true" ]]; then
    ov_status "deepseek-harness" "integrated" "dsh-memory-plugin bundle configured (template only, restart to activate)"
  elif [[ "$live_has_ov" == "true" ]]; then
    ov_status "deepseek-harness" "partial" "dsh-memory-plugin bundle (live profiles: ${live_scope:-none}, lost on restart)"
  else
    ov_status "deepseek-harness" "not_integrated" "No OpenViking memory bundle"
  fi
}
