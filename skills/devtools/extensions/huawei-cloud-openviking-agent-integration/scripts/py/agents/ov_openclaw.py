#!/usr/bin/env python3
"""ov_openclaw.py — OpenClaw agent subclass CLI.

Replaces all embedded Python (heredocs and inline ``python3 -c`` calls) in
``agents/openclaw.sh``.  Each subcommand corresponds 1:1 to an original Python
block and implements the exact same logic, using shared helpers from
``ov_common`` where appropriate.

Subcommands:
    slot-owner <cfg_file>
        Print plugins.slots.contextEngine owner (empty string on error).

    inject <path> <endpoint> <force_slot> <allow_offline> <npm_registry> <shared_dir> <runtime_dir> <template_dir>
        Inject the official OpenViking plugin install block into template
        start.sh and write the standalone ov-openclaw-init.sh.

    clean-legacy-cfg <path>
        Remove legacy direct-config-write Step 5 block from template.

    clean-legacy-mcp <path>
        Remove legacy MCP injection Step 5 block from template.

    has-mcp-server <cfg_file>
        Exit 0 if 'openviking' in mcp.servers, else exit 1.

    remove-mcp-server <cfg_file>
        Remove openviking from mcp.servers and save.

    has-config <cfg_file>
        Exit 0 if openviking is configured (plugin entry, contextEngine slot,
        or mcp server), else exit 1.

    unbind <path> <shared_dir>
        Remove all OpenViking injection blocks from template start.sh.

    clean-config <cfg_file>
        Remove openviking plugin entries, MCP servers, contextEngine slot,
        allow list, and tool policy.  Prints 'cleaned' or 'skip'.
"""
import os
import re
import sys

def _ov_mark_key_consumed():
    """ISSUE-003: notify the parent bash entry point that --api-key was used."""
    f = os.environ.get("OV_API_KEY_CONSUMED_FILE")
    if not f:
        return
    try:
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "a").close()
    except OSError:
        pass

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))  # parent dir holds ov_common.py
from ov_common import (
    read_text, write_text, write_init, source_block,
    load_json, save_json,
)


# ── slot-owner ────────────────────────────────────────────────
def cmd_slot_owner(args):
    """Print the plugins.slots.contextEngine owner (empty string on error).

    Replaces the two inline ``python3 -c`` calls at lines 98-109 of
    openclaw.sh that both print the contextEngine slot owner.
    """
    cfg_file = args[0]
    try:
        d = load_json(cfg_file)
        owner = d.get("plugins", {}).get("slots", {}).get("contextEngine", "")
        print(owner)
    except Exception:
        print("")


# ── inject ────────────────────────────────────────────────────
def cmd_inject(args):
    """Inject the official OpenViking plugin install block into template start.sh.

    Replaces the PYINJECT heredoc (lines 124-323) in openclaw.sh.
    """
    (path, endpoint, force_slot, allow_offline, npm_registry,
     shared_dir, runtime_dir, template_dir) = args[0:8]

    content = read_text(path)
    if "ov-openclaw-init.sh" in content or "OpenViking plugin install" in content:
        print("already")
        sys.exit(0)

    block = """# ── OpenViking plugin install (official ClawHub, added by huawei-cloud-openviking-agent-integration skill) ──
# Cache-first: check if plugin already installed; if not, install from runtime cache (no network),
# then ClawHub/npm on first integrate or cache miss. Survives undeploy+deploy via __OV_RUNTIME_DIR__/.
echo "[openclaw] Provisioning OpenViking plugin (cache-first)..."
OV_PLUGIN_INSTALLED=0
OV_VENDOR_SRC="__OV_RUNTIME_DIR__/openclaw/openviking-plugin-source"
if "$NODE" "$CLI" plugins list 2>/dev/null | grep -q "openviking"; then
  OV_PLUGIN_INSTALLED=1
  echo "[openclaw] Plugin already installed (cache hit)."
fi
OV_PREBUILT="__OV_RUNTIME_DIR__/openclaw/openviking-plugin-built"
if [[ "$OV_PLUGIN_INSTALLED" = "0" && -d "$OV_PREBUILT" && -d "$OV_PREBUILT/dist" ]]; then
  echo "[openclaw] Installing from pre-built cache (Tier-0 fast path)..."
  if "$NODE" "$CLI" plugins install --force --accept-capabilities "$OV_PREBUILT" 2>&1; then
    OV_PLUGIN_INSTALLED=1
    echo "[openclaw] Installed from pre-built cache (no build needed)."
  else
    echo "[openclaw] WARNING: pre-built install failed — falling back to source build"
  fi
fi
if [[ "$OV_PLUGIN_INSTALLED" = "0" && -d "$OV_VENDOR_SRC" ]]; then
  echo "[openclaw] Installing from runtime source cache (Tier-1)..."
  OV_BUILD_DIR=$(mktemp -d /tmp/openclaw-ov-build.XXXXXX)
  cp -a "$OV_VENDOR_SRC/." "$OV_BUILD_DIR/"
  export NPM_CONFIG_REGISTRY=__OV_NPM_REGISTRY__
  # npm package ships with dist/ pre-compiled; only install runtime deps
  if [[ -d "$OV_BUILD_DIR/dist" ]]; then
    (cd "$OV_BUILD_DIR" && npm install --production --no-audit --no-fund 2>&1 | tail -3) || true
    if "$NODE" "$CLI" plugins install --force --accept-capabilities "$OV_BUILD_DIR" 2>&1; then
      OV_PLUGIN_INSTALLED=1
      echo "[openclaw] Installed from runtime source cache (dist/ pre-compiled)."
    else
      echo "[openclaw] WARNING: local install failed — trying online"
    fi
  else
    echo "[openclaw] WARNING: no dist/ in source cache — trying online"
  fi
  unset NPM_CONFIG_REGISTRY
  rm -rf "$OV_BUILD_DIR"
fi
if [[ "$OV_PLUGIN_INSTALLED" = "0" ]]; then
  echo "[openclaw] Cache miss — trying online (ClawHub → npm mirrors)..."
  if "$NODE" "$CLI" plugins install --accept-capabilities clawhub:@openviking/openclaw-plugin 2>&1; then
    OV_PLUGIN_INSTALLED=1
    echo "[openclaw] Installed from ClawHub"
  else
    echo "[openclaw] WARNING: ClawHub failed — trying npm mirror"
    export NPM_CONFIG_REGISTRY=__OV_NPM_REGISTRY__
    if "$NODE" "$CLI" plugins install --force --accept-capabilities @openviking/openclaw-plugin 2>&1; then
      OV_PLUGIN_INSTALLED=1
      echo "[openclaw] Installed (npm Huawei Cloud mirror)"
    else
      export NPM_CONFIG_REGISTRY=https://registry.npmmirror.com/
      if "$NODE" "$CLI" plugins install --force --accept-capabilities @openviking/openclaw-plugin 2>&1; then
        OV_PLUGIN_INSTALLED=1
        echo "[openclaw] Installed (npm npmmirror)"
      else
        echo "[openclaw] WARNING: all online sources failed"
      fi
    fi
    unset NPM_CONFIG_REGISTRY
  fi
fi
# Fix plugin permissions (gateway blocks world-writable paths)
if [[ "$OV_PLUGIN_INSTALLED" = "1" ]]; then
  for _ext_dir in "$HOME/.openclaw/extensions/openviking" "${OPENCLAW_STATE_DIR:-/tmp/.openclaw}/extensions/openviking"; do
    if [[ -d "$_ext_dir" ]]; then
      chmod -R go-w "$_ext_dir" 2>/dev/null || true
      echo "[openclaw] Fixed permissions: $_ext_dir"
    fi
  done
fi
# Configure OpenViking endpoint via official JSON contract
export OPENVIKING_BASE_URL="__ENDPOINT__"
export OPENVIKING_ENDPOINT="__ENDPOINT__"
if [ "$OV_PLUGIN_INSTALLED" = "1" ]; then
  OV_SETUP_ARGS=(--base-url "__ENDPOINT__" --json)
  [ -n "__API_KEY__" ] && OV_SETUP_ARGS+=(--api-key "__API_KEY__")
  [ "${OV_FORCE_SLOT:-OV_FORCE_SLOT_DEFAULT}" = "1" ] && OV_SETUP_ARGS+=(--force-slot)
  [ "${OV_ALLOW_OFFLINE:-OV_ALLOW_OFFLINE_DEFAULT}" = "1" ] && OV_SETUP_ARGS+=(--allow-offline)

  OV_SETUP_OUT=$("$NODE" "$CLI" openviking setup "${OV_SETUP_ARGS[@]}" 2>/dev/null || true)
  if echo "$OV_SETUP_OUT" | grep -q '"success":true'; then
    echo "[openclaw] Configured via setup (JSON): __ENDPOINT__"
  elif echo "$OV_SETUP_OUT" | grep -q '"action":"slot_blocked"'; then
    if [ "${OV_FORCE_SLOT:-OV_FORCE_SLOT_DEFAULT}" = "1" ]; then
      echo "[openclaw] WARNING: slot blocked; --force-slot retry already attempted"
    else
      echo "[openclaw] WARNING: contextEngine slot owned by another plugin; use --force-slot to override"
    fi
  elif echo "$OV_SETUP_OUT" | grep -q '"action":"error"'; then
    echo "[openclaw] ERROR: setup validation failed: $OV_SETUP_OUT"
  elif echo "$OV_SETUP_OUT" | grep -q '"health":{"ok":false'; then
    if [ "${OV_ALLOW_OFFLINE:-OV_ALLOW_OFFLINE_DEFAULT}" != "1" ]; then
      echo "[openclaw] WARNING: server unreachable and --allow-offline not approved"
    fi
  elif echo "$OV_SETUP_OUT" | grep -q 'root_key'; then
    echo "[openclaw] ERROR: setup requires --account-id/--user-id for root API keys"
  else
    echo "[openclaw] WARNING: unexpected setup output: $OV_SETUP_OUT"
  fi
else
  echo "[openclaw] Plugin not installed — skipping setup"
fi
# Enable OpenViking plugin (sets contextEngine slot)
if [ "$OV_PLUGIN_INSTALLED" = "1" ]; then
  "$NODE" "$CLI" plugins enable --accept-capabilities openviking 2>/dev/null || true
  "$NODE" "$CLI" config set 'plugins.allow' '["openviking"]' 2>/dev/null || true
  "$NODE" "$CLI" config set "plugins.entries.openviking.config.recallMaxInjectedChars" 16000 2>/dev/null || true
  "$NODE" "$CLI" config set "plugins.entries.openviking.config.recallLimit" 10 2>/dev/null || true
  # ── Disable local memory to prevent recall quality degradation ──
  # OpenViking contextEngine handles auto-recall + auto-capture;
  # local session-memory hook and memory_search tool are redundant and degrade recall quality.
  "$NODE" "$CLI" config set "hooks.internal.entries.session-memory.enabled" false 2>/dev/null || true
  # Deny local memory_search tool — use OpenViking MCP tools (search/recall/remember) instead
  "$NODE" "$CLI" config set "tools.deny" '["memory_search"]' 2>/dev/null || true
  echo "[openclaw] Disabled session-memory hook and local memory_search (OpenViking handles recall)"
  echo "[openclaw] Enabled OpenViking plugin (contextEngine slot)"
fi
# Append OpenViking instructions to AGENTS.md
mkdir -p "$OPENCLAW_STATE_DIR/workspace"
OV_AGENTS="$OPENCLAW_STATE_DIR/workspace/AGENTS.md"
if ! grep -q "OpenViking Long-Term Memory" "$OV_AGENTS" 2>/dev/null; then
  cat >> "$OV_AGENTS" << 'OVAGENTS'
## OpenViking Long-Term Memory
OpenViking is integrated as the contextEngine plugin — it automatically recalls
relevant context before each response and captures important information after.
You also have direct access to OpenViking MCP tools for explicit operations:
1. **search**: Deep semantic retrieval with session context and intent analysis.
2. **recall**: Memory recall across memory types (events, entities, preferences).
3. **remember**: Store important information — user preferences, project decisions, technical details.
4. **read**: Read content from viking:// URIs for stored reference materials.
The contextEngine handles auto-recall automatically; use these tools for explicit
or targeted operations when needed.
OVAGENTS
  echo "[openclaw] Instructions appended to AGENTS.md"
else
  echo "[openclaw] Instructions already in AGENTS.md"
fi
# ── Verification: confirm plugin is actually installed ──
if [[ "$OV_PLUGIN_INSTALLED" = "1" ]]; then
  if ! "$NODE" "$CLI" plugins list 2>/dev/null | grep -q "openviking"; then
    echo "[openclaw] ERROR: Plugin install reported success but plugins list does not contain openviking"
    OV_PLUGIN_INSTALLED=0
  fi
fi
if [[ "$OV_PLUGIN_INSTALLED" = "0" ]]; then
  echo "[openclaw] ERROR: OpenViking plugin installation FAILED — auto-recall and memory tools will not be available"
fi
"""
    block = block.replace("__ENDPOINT__", endpoint)
    block = block.replace("OV_FORCE_SLOT_DEFAULT", str(force_slot))
    block = block.replace("OV_ALLOW_OFFLINE_DEFAULT", str(allow_offline))
    api_key = os.environ.get("OV_API_KEY", "")
    block = block.replace("__API_KEY__", api_key)
    if api_key:
        _ov_mark_key_consumed()
    block = block.replace("__OV_NPM_REGISTRY__", npm_registry)
    block = block.replace("__OV_RUNTIME_DIR__", runtime_dir)

    init_path = f"{shared_dir}/ov-openclaw-init.sh"
    write_init(
        init_path, "OpenClaw",
        f"Sourced by {template_dir}/openclaw/start.sh (single source line).",
        block,
    )

    # Ensure OPENCLAW_STATE_DIR is persistent (not ephemeral /tmp).
    # Only rewrite if the old /tmp/.openclaw default is present;
    # skip if start.sh already uses dynamic derivation (${OPENCLAW_DIR}/state).
    if re.search(r'OPENCLAW_STATE_DIR.*(/tmp/\.|\$\{OPENCLAW_STATE_DIR:-/tmp)', content):
        content = re.sub(
            r'# ── State dir:.*──\nexport OPENCLAW_STATE_DIR=.*',
            '# ── State dir: prefer env.yaml extraEnv, fallback to ${OPENCLAW_DIR}/state ──\n'
            '# Persistent path survives sandbox restarts; /tmp (old default) is ephemeral tmpfs.\n'
            'export OPENCLAW_STATE_DIR="${OPENCLAW_STATE_DIR:-${OPENCLAW_DIR}/state}"',
            content,
        )
        print("start.sh state dir rewritten to dynamic persistent path")
    else:
        print("start.sh state dir already persistent (dynamic or explicit) — skip")

    # Also fix env.yaml so CLI commands in terminal use the same persistent path
    env_yaml = f"{template_dir}/openclaw/env.yaml"
    if os.path.exists(env_yaml):
        ey = read_text(env_yaml)
        if "/tmp/.openclaw" in ey:
            ey = ey.replace(
                'OPENCLAW_STATE_DIR: "/tmp/.openclaw"',
                f'OPENCLAW_STATE_DIR: "{runtime_dir}/openclaw/state"',
            )
            write_text(env_yaml, ey)
            print("env.yaml fixed")
        else:
            print("env.yaml already fixed")

    sb = source_block(
        shared_dir, "ov-openclaw-init.sh",
        extra="# OpenViking plugin install is best-effort: if it fails, gateway should still start.\nset +e",
    )

    gateway_marker = "# ── Step 5: Start the Gateway"
    if gateway_marker in content:
        content = content.replace(gateway_marker, sb + gateway_marker)
    else:
        content = re.sub(r'(# ── Step \d+: Start the Gateway)', sb + r'\1', content)
    write_text(path, content)
    print("injected")


# ── clean-legacy-cfg ──────────────────────────────────────────
def cmd_clean_legacy_cfg(args):
    """Remove legacy direct-config-write Step 5 block from template.

    Replaces the PYCLEANCFG heredoc (lines 341-352) in openclaw.sh.
    """
    path = args[0]
    content = read_text(path)
    content = re.sub(
        r'# ── Step 5: OpenViking plugin config \(added by huawei-cloud-openviking-agent-integration skill\) ──.*?OVAGENTS\n',
        '',
        content,
        flags=re.DOTALL,
    )
    write_text(path, content)


# ── clean-legacy-mcp ──────────────────────────────────────────
def cmd_clean_legacy_mcp(args):
    """Remove legacy MCP injection Step 5 block from template.

    Replaces the PYCLEANMCP heredoc (lines 356-367) in openclaw.sh.
    """
    path = args[0]
    content = read_text(path)
    content = re.sub(
        r'# ── Step 5: Inject OpenViking MCP server.*?OVPATCH\n',
        '',
        content,
        flags=re.DOTALL,
    )
    write_text(path, content)


# ── has-mcp-server ────────────────────────────────────────────
def cmd_has_mcp_server(args):
    """Exit 0 if 'openviking' in mcp.servers, else exit 1.

    Replaces the inline ``python3 -c`` call at line 377 of openclaw.sh.
    """
    cfg_file = args[0]
    d = load_json(cfg_file)
    sys.exit(0 if "openviking" in d.get("mcp", {}).get("servers", {}) else 1)


# ── remove-mcp-server ─────────────────────────────────────────
def cmd_remove_mcp_server(args):
    """Remove openviking from mcp.servers and save.

    Replaces the inline ``python3 -c`` call at lines 378-387 of openclaw.sh.
    """
    cfg_file = args[0]
    d = load_json(cfg_file)
    servers = d.get("mcp", {}).get("servers", {})
    if "openviking" in servers:
        del servers["openviking"]
        if not servers:
            d.get("mcp", {}).pop("servers", None)
        if not d.get("mcp"):
            d.pop("mcp", None)
        save_json(cfg_file, d)


# ── has-config ────────────────────────────────────────────────
def cmd_has_config(args):
    """Exit 0 if openviking is configured (plugin entry, slot, or mcp server).

    Replaces the inline ``python3 -c`` call at line 405 of openclaw.sh.
    """
    cfg_file = args[0]
    d = load_json(cfg_file)
    ok = (
        d.get("plugins", {}).get("entries", {}).get("openviking")
        or d.get("plugins", {}).get("slots", {}).get("contextEngine") == "openviking"
        or "openviking" in d.get("mcp", {}).get("servers", {})
    )
    sys.exit(0 if ok else 1)


# ── unbind ────────────────────────────────────────────────────
def cmd_unbind(args):
    """Remove all OpenViking injection blocks from template start.sh.

    Replaces the PYUNBIND heredoc (lines 421-512) in openclaw.sh.
    """
    path = args[0]
    shared_dir = args[1]
    content = read_text(path)

    # First try new-style: source block with start/end markers (flexible content between)
    new_pattern = (
        rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\n'
        rf'.*?'  # Match any content between start and end markers
        rf'# ── End OpenViking integration ──\n\n?'
    )
    new_content = re.sub(new_pattern, '', content, flags=re.DOTALL)
    if new_content != content:
        write_text(path, new_content)
        print("removed 1 OpenViking block(s) [new-style source line]")
        sys.exit(0)

    # Fall back to old-style: full inline Step 5.x blocks
    lines = content.splitlines(keepends=True)
    n = len(lines)
    removed_blocks = 0
    ov_block_start = re.compile(r'# ── Step 5(?:\.\d+)?:.*[Oo]pen[Vv]iking')
    any_step_header = re.compile(r'# ── Step \d')
    ov_ref = re.compile(
        r'openviking|OV_PLUGIN|OV_VENDOR|OV_BUILD|clawhub:@openviking|accept-capabilities|acknowledge-clawhub-risk',
        re.IGNORECASE,
    )

    def find_step_end(start, lines):
        j = start + 1
        while j < len(lines):
            if any_step_header.match(lines[j]) and j > start:
                return j
            if 'Starting Gateway' in lines[j] or 'gateway run' in lines[j]:
                return j
            j += 1
        return len(lines)

    def has_ov_in_range(lines, start, end):
        for j in range(start, end):
            if ov_ref.search(lines[j]):
                return True
        return False

    # Pass 1: Remove Step 5.x OpenViking blocks with look-ahead
    i = 0
    new_lines = []
    while i < n:
        line = lines[i]
        if ov_block_start.match(line):
            removed_blocks += 1
            block_end = find_step_end(i, lines)
            i = block_end
            while i < n:
                if any_step_header.match(lines[i]):
                    step_end = find_step_end(i, lines)
                    if has_ov_in_range(lines, i, step_end):
                        removed_blocks += 1
                        i = step_end
                        continue
                    else:
                        break
                elif 'Starting Gateway' in lines[i] or 'gateway run' in lines[i]:
                    break
                else:
                    if ov_ref.search(lines[i]):
                        i += 1
                        continue
                    stripped = lines[i].strip()
                    if stripped == 'fi' or stripped == '  fi':
                        i += 1
                        continue
                    break
            continue
        new_lines.append(line)
        i += 1

    # Pass 2: Remove orphaned fi statements
    lines = new_lines
    new_lines = []
    fi_balance = 0
    for line in lines:
        stripped = line.strip()
        is_bash_if = re.match(r'if\s', stripped) or re.match(r'if\s', stripped.split('#')[0].strip())
        is_bash_fi = stripped == 'fi' or stripped.startswith('fi ') or stripped.startswith('fi\t')
        if is_bash_if:
            fi_balance += 1
            new_lines.append(line)
        elif is_bash_fi:
            if fi_balance > 0:
                fi_balance -= 1
                new_lines.append(line)
            else:
                continue
        else:
            new_lines.append(line)
    content = ''.join(new_lines)
    content = content.replace("# ── Step 6: Start the Gateway", "# ── Step 5: Start the Gateway")
    write_text(path, content)
    print(f"removed {removed_blocks} OpenViking block(s)")


# ── clean-config ──────────────────────────────────────────────
def cmd_clean_config(args):
    """Remove openviking plugin entries, MCP servers, slots, and tool policy.

    Replaces the inline ``python3 -c`` call at lines 555-593 of openclaw.sh.
    Prints 'cleaned' if changes were made, 'skip' otherwise.
    """
    cfg_file = args[0]
    d = load_json(cfg_file)
    changed = False
    servers = d.get("mcp", {}).get("servers", {})
    if "openviking" in servers:
        del servers["openviking"]
        if not servers:
            d.get("mcp", {}).pop("servers", None)
        if not d.get("mcp"):
            d.pop("mcp", None)
        changed = True
    plugins = d.get("plugins", {})
    entries = plugins.get("entries", {})
    if "openviking" in entries:
        del entries["openviking"]
        changed = True
    slots = plugins.get("slots", {})
    if slots.get("contextEngine") == "openviking":
        del slots["contextEngine"]
        changed = True
    allow = plugins.get("allow", [])
    if "openviking" in allow:
        allow.remove("openviking")
        changed = True
    if not entries:
        plugins.pop("entries", None)
    if not slots:
        plugins.pop("slots", None)
    if not allow:
        plugins.pop("allow", None)
    if not plugins:
        d.pop("plugins", None)
    aa = d.get("tools", {}).get("alsoAllow", [])
    aa = [x for x in aa if x != "group:plugins"]
    if aa:
        d.setdefault("tools", {})["alsoAllow"] = aa
    else:
        d.get("tools", {}).pop("alsoAllow", None)
    if not d.get("tools"):
        d.pop("tools", None)
    if changed:
        save_json(cfg_file, d)
        print("cleaned")
    else:
        print("skip")


def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "slot-owner": cmd_slot_owner,
        "inject": cmd_inject,
        "clean-legacy-cfg": cmd_clean_legacy_cfg,
        "clean-legacy-mcp": cmd_clean_legacy_mcp,
        "has-mcp-server": cmd_has_mcp_server,
        "remove-mcp-server": cmd_remove_mcp_server,
        "has-config": cmd_has_config,
        "unbind": cmd_unbind,
        "clean-config": cmd_clean_config,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
