#!/usr/bin/env python3
"""ov_workswarm.py — WorkSwarm agent Python operations CLI.

Replaces all heredoc Python and inline python3 -c calls in agents/workswarm.sh.

Subcommands:
    mutate-config <apply|revert> <config.yaml> [mcp_url]
        Delegate to ov_jw_mutate.py (single source of truth for config.yaml mutation).
    patch-iface-apply <interface_code.py>
        Add code-mode ExternalMemoryRail call after CodingMemoryRail registration.
    patch-iface-revert <interface_code.py>
        Remove the code-mode ExternalMemoryRail call.
    patch-prov-apply <provider.py>
        Patch openviking_memory_provider.py: top_k → limit.
    patch-prov-revert <provider.py>
        Revert the top_k → limit patch.
    patch-session-apply <provider.py>
        Patch openviking_memory_provider.py: generate jw- prefixed session ID.
    patch-session-revert <provider.py>
        Revert the jw- session ID patch.
    patch-commit-apply <provider.py>
        Patch openviking_memory_provider.py: call commit after sync_turn.
    patch-commit-revert <provider.py>
        Revert the commit-after-sync_turn patch.
    inject-template <tpl> <endpoint> <mcp_url> <agents_md_path> <shared_dir> <template_dir> <runtime_dir>
        Write ov-jiuwenswarm-init.sh and inject a source block into template start.sh.
    unbind-template <tpl> <shared_dir>
        Remove OpenViking integration blocks from template start.sh.
"""
import os
import re
import subprocess
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # parent dir holds ov_common.py
from ov_common import read_text, write_text

# Path to ov_jw_mutate.py — scripts/lib/ov_jw_mutate.py relative to scripts/py/agents/
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(_HERE))
OV_JW_MUTATE = os.path.join(_SCRIPTS_DIR, "lib", "ov_jw_mutate.py")


# ── mutate-config: delegate to ov_jw_mutate.py ──────────────────
def cmd_mutate_config(args):
    """Delegate to ov_jw_mutate.py — single source of truth for WorkSwarm config.yaml."""
    action, cfg = args[0], args[1]
    mcp_url = args[2] if len(args) > 2 else ""
    cmd = [sys.executable, OV_JW_MUTATE, action, cfg]
    if mcp_url:
        cmd.append(mcp_url)
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


# ── patch-iface-apply / patch-iface-revert ──────────────────────
def cmd_patch_iface_apply(args):
    """Add code-mode ExternalMemoryRail call to interface_code.py."""
    path = args[0]
    content = read_text(path)
    pattern = r'(                logger\.info\(\n                    "\[JiuwenSwarmCodeAdapter\] CodingMemoryRail \(re\)registered for %s",\n                    mode,\n                \)\n)\n+(    def _build_code_agent_rail)'
    replacement = r'\1\n        # code-mode ExternalMemoryRail (openviking-agent-integration)\n        await self._handle_external_memory_rail_by_config()\n\n\2'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content, count=1)
        write_text(path, content)


def cmd_patch_iface_revert(args):
    """Remove code-mode ExternalMemoryRail call from interface_code.py."""
    path = args[0]
    content = read_text(path)
    content = re.sub(r'\n        # code-mode ExternalMemoryRail \(openviking-agent-integration\)\n        await self\._handle_external_memory_rail_by_config\(\)\n+', '\n', content, flags=re.DOTALL)
    write_text(path, content)


# ── patch-prov-apply / patch-prov-revert ────────────────────────
def cmd_patch_prov_apply(args):
    """Patch openviking_memory_provider.py: top_k → limit."""
    path = args[0]
    content = read_text(path)
    content = content.replace('{"query": query, "top_k": 5},', '{"query": query, "limit": 5},  # ov-fix-limit').replace('payload["top_k"] = args["limit"]', 'payload["limit"] = args["limit"]  # ov-fix-limit')
    write_text(path, content)


def cmd_patch_prov_revert(args):
    """Revert openviking_memory_provider.py: limit → top_k."""
    path = args[0]
    content = read_text(path)
    content = content.replace('{"query": query, "limit": 5},  # ov-fix-limit', '{"query": query, "top_k": 5},').replace('payload["limit"] = args["limit"]  # ov-fix-limit', 'payload["top_k"] = args["limit"]')
    write_text(path, content)


# ── patch-session-apply / patch-session-revert ──────────────────
_SESSION_OLD = 'self._session_id = kwargs.get("session_id", "")\n        try:'
_SESSION_NEW = (
    'self._session_id = kwargs.get("session_id", "")\n'
    '        # ov-fix-session: generate jw- prefixed session ID for empty/__default__\n'
    '        if not self._session_id or self._session_id == "__default__":\n'
    '            import uuid; self._session_id = f"jw-{uuid.uuid4()}"\n'
    '        try:'
)
# sync_turn must use self._session_id (set by initialize) instead of
# kwargs["session_id"] which is always "__default__" from the rail
_SID_OLD = 'sid = kwargs.get("session_id", self._session_id)'
_SID_NEW = 'sid = self._session_id  # ov-fix-session: use initialized session ID'


def cmd_patch_session_apply(args):
    """Patch openviking_memory_provider.py: generate jw- session ID + use it in sync_turn."""
    path = args[0]
    content = read_text(path)
    changed = False
    if _SESSION_OLD in content and 'ov-fix-session' not in content:
        content = content.replace(_SESSION_OLD, _SESSION_NEW, 1)
        changed = True
    if _SID_OLD in content and 'ov-fix-session: use initialized' not in content:
        content = content.replace(_SID_OLD, _SID_NEW, 1)
        changed = True
    if changed:
        write_text(path, content)


def cmd_patch_session_revert(args):
    """Revert openviking_memory_provider.py: jw- session ID patch."""
    path = args[0]
    content = read_text(path)
    changed = False
    if _SESSION_NEW in content:
        content = content.replace(_SESSION_NEW, _SESSION_OLD, 1)
        changed = True
    if _SID_NEW in content:
        content = content.replace(_SID_NEW, _SID_OLD, 1)
        changed = True
    if changed:
        write_text(path, content)


# ── patch-commit-apply / patch-commit-revert ────────────────────
# Strategy: threshold commit (every 5 turns) in sync_turn + session-end
# commit in Rail.uninit() via provider.on_session_end().

# --- Provider: sync_turn() threshold commit ---
_COMMIT_ORIG = (
    '            )\n'
    '        except Exception as e:\n'
    '            logger.debug("OpenViking sync failed: %s", e)'
)
_COMMIT_OLD_PER_TURN = (
    '            )\n'
    '            # ov-fix-commit: trigger memory extraction after each turn\n'
    '            await asyncio.to_thread(\n'
    '                self._client.post, f"/api/v1/sessions/{sid}/commit", {}\n'
    '            )\n'
    '        except Exception as e:\n'
    '            logger.debug("OpenViking sync failed: %s", e)'
)
_COMMIT_NEW = (
    '            )\n'
    '            # ov-fix-commit: threshold commit every 5 turns + session-end via uninit\n'
    '            self._turn_count = getattr(self, "_turn_count", 0) + 1\n'
    '            if self._turn_count >= 5:\n'
    '                await asyncio.to_thread(\n'
    '                    self._client.post, f"/api/v1/sessions/{sid}/commit", {}\n'
    '                )\n'
    '                self._turn_count = 0\n'
    '        except Exception as e:\n'
    '            logger.debug("OpenViking sync failed: %s", e)'
)

# --- Rail: uninit() — call on_session_end before shutdown ---
_RAIL_UNINIT_OLD = (
    '            async def _shutdown_with_timeout():\n'
    '                try:\n'
    '                    await asyncio.wait_for(self._provider.shutdown(), timeout=10.0)'
)
_RAIL_UNINIT_NEW = (
    '            async def _shutdown_with_timeout():\n'
    '                # ov-fix-commit: commit session before shutdown\n'
    '                try:\n'
    '                    await asyncio.wait_for(self._provider.on_session_end([]), timeout=10.0)\n'
    '                except Exception:\n'
    '                    pass\n'
    '                try:\n'
    '                    await asyncio.wait_for(self._provider.shutdown(), timeout=10.0)'
)
_RAIL_FALLBACK_OLD = (
    '        except RuntimeError:\n'
    '            try:\n'
    '                asyncio.run(self._provider.shutdown())'
)
_RAIL_FALLBACK_NEW = (
    '        except RuntimeError:\n'
    '            try:\n'
    '                asyncio.run(self._provider.on_session_end([]))\n'
    '            except Exception:\n'
    '                pass\n'
    '            try:\n'
    '                asyncio.run(self._provider.shutdown())'
)


def _find_rail_path(provider_path: str) -> str:
    """Find external_memory_rail.py from the provider path."""
    import os
    # provider: .../openjiuwen/core/memory/external/openviking_memory_provider.py
    # rail:     .../openjiuwen/harness/rails/memory/external_memory_rail.py
    pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(provider_path))))  # .../openjiuwen
    rail = os.path.join(pkg_root, "harness", "rails", "memory",
                        "external_memory_rail.py")
    return rail if os.path.isfile(rail) else ""


def cmd_patch_commit_apply(args):
    """Patch provider sync_turn (threshold commit) + rail uninit (session-end commit)."""
    path = args[0]
    content = read_text(path)
    changed = False
    # Provider: replace per-turn commit or original with threshold commit
    if _COMMIT_OLD_PER_TURN in content:
        content = content.replace(_COMMIT_OLD_PER_TURN, _COMMIT_NEW, 1)
        changed = True
    elif _COMMIT_ORIG in content and 'ov-fix-commit' not in content:
        content = content.replace(_COMMIT_ORIG, _COMMIT_NEW, 1)
        changed = True
    if changed:
        write_text(path, content)
    # Rail: add on_session_end before shutdown
    rail = _find_rail_path(path)
    if rail:
        rc = read_text(rail)
        rchanged = False
        if _RAIL_UNINIT_OLD in rc and 'ov-fix-commit' not in rc:
            rc = rc.replace(_RAIL_UNINIT_OLD, _RAIL_UNINIT_NEW, 1)
            rchanged = True
        if _RAIL_FALLBACK_OLD in rc:
            rc = rc.replace(_RAIL_FALLBACK_OLD, _RAIL_FALLBACK_NEW, 1)
            rchanged = True
        if rchanged:
            write_text(rail, rc)


def cmd_patch_commit_revert(args):
    """Revert provider + rail commit patches."""
    path = args[0]
    content = read_text(path)
    changed = False
    if _COMMIT_NEW in content:
        content = content.replace(_COMMIT_NEW, _COMMIT_ORIG, 1)
        changed = True
    elif _COMMIT_OLD_PER_TURN in content:
        content = content.replace(_COMMIT_OLD_PER_TURN, _COMMIT_ORIG, 1)
        changed = True
    if changed:
        write_text(path, content)
    rail = _find_rail_path(path)
    if rail:
        rc = read_text(rail)
        rchanged = False
        if _RAIL_UNINIT_NEW in rc:
            rc = rc.replace(_RAIL_UNINIT_NEW, _RAIL_UNINIT_OLD, 1)
            rchanged = True
        if _RAIL_FALLBACK_NEW in rc:
            rc = rc.replace(_RAIL_FALLBACK_NEW, _RAIL_FALLBACK_OLD, 1)
            rchanged = True
        if rchanged:
            write_text(rail, rc)


# ── inject-template ─────────────────────────────────────────────
def cmd_inject_template(args):
    """Write ov-jiuwenswarm-init.sh and inject source block into template start.sh."""
    path, endpoint, mcp_url, agents_md_path, shared_dir, template_dir, runtime_dir = (
        args[0], args[1], args[2], args[3], args[4], args[5], args[6]
    )
    with open(path) as f:
        lines = f.readlines()
    marker = "# ── OpenViking native memory provider injection (added by huawei-cloud-openviking-agent-integration skill) ──"
    agents_md = open(agents_md_path).read()
    block = marker + """
export MEMORY_ENGINE=external
export MEMORY_EXTERNAL_PROVIDER=openviking
export OPENVIKING_ENDPOINT="__OV_EP__"
export OPENVIKING_AGENT=jiuwenswarm
OV_PY="${OV_PY:-$(command -v python3.12 2>/dev/null || command -v python3.11 2>/dev/null || command -v python3.10 2>/dev/null || command -v python3 2>/dev/null || echo python3)}"
JW_CFG="$JIUWENSWARM_DATA_DIR/config/config.yaml"
if [ -f "$JW_CFG" ]; then
  $OV_PY - "$JW_CFG" "__OV_MCP__" << 'PYJW2'
import sys, re
path = sys.argv[1]
mcp_url = sys.argv[2]
with open(path) as f: content = f.read()
changed = False
new = re.sub(r'(engine:\\s*\\$\\{MEMORY_ENGINE:-)builtin(\\})', r'\\1external\\2', content)
if new != content: content = new; changed = True
new = re.sub(r'(provider:\\s*\\$\\{MEMORY_EXTERNAL_PROVIDER:-)(\\})', r'\\1openviking\\2', content)
if new != content: content = new; changed = True
new = re.sub(r'(auto_memory_enabled:\\s*)false', r'\\1true', content)
if new != content: content = new; changed = True
new = re.sub(r'(proactive_recommendation:\\s*\\n\\s*enabled:\\s*)false', r'\\1true', content)
if new != content: content = new; changed = True
if "name: openviking" not in content:
    _dash_m = re.search(r'servers:[^\\n]*\\n([ \t]*)-[ \t]', content)
    _dash = _dash_m.group(1) if _dash_m else '  '
    _inner = _dash + '  '
    mcp_entry = _dash + '- name: openviking\\n' + _inner + 'transport: streamable-http\\n' + _inner + 'url: ' + mcp_url + '\\n' + _inner + 'enabled: true\\n'
    new = re.sub(r'(mcp:\s*\\n\s*servers:\s*)\[\]', lambda m: m.group(1) + "\\n" + mcp_entry, content)
    if new != content: content = new; changed = True
    else:
        new = re.sub(r'(mcp:\s*\\n\s*servers:\s*\\n)(?!\s*-)', lambda m: m.group(1) + mcp_entry, content)
        if new != content: content = new; changed = True
        else:
            _blkre = re.compile(r'(mcp:\s*\\n\s*servers:\\n(?:[ \t]*-[^\\n]*\\n(?:[ \t]+[^\\n]*\\n)*)*)')
            _blkm = _blkre.search(content)
            if _blkm:
                content = content[:_blkm.end()] + mcp_entry + content[_blkm.end():]
                changed = True
if "    openviking:" not in content:
    ov_block = "    openviking:\\n      endpoint: ${OPENVIKING_ENDPOINT:-http://127.0.0.1:1933}\\n      api_key: ${OPENVIKING_API_KEY:-}\\n      account: ${OPENVIKING_ACCOUNT:-default}\\n      user: ${OPENVIKING_USER:-default}\\n"
    new = re.sub(r'(  external:\\s*\\n(?:    [^\\n]*\\n)*?)(    lakebase:)', lambda m: m.group(1) + ov_block + m.group(2), content)
    if new != content: content = new; changed = True
new = re.sub(r"(account:\\s*\\$\\{OPENVIKING_ACCOUNT:-)root(\\})", r"\\1default\\2", content)
if new != content: content = new; changed = True
if "viking_search: allow" not in content:
    viking_perms = "    viking_search: allow\\n    viking_read: allow\\n    viking_browse: allow\\n    viking_remember: allow\\n    viking_add_resource: allow\\n"
    new = re.sub(r'(    mem0_conclude: allow\\n)', lambda m: m.group(1) + viking_perms, content)
    if new != content: content = new; changed = True
new = re.sub(r'(fast:\\s*\\n\\s*memory:\\s*\\n\\s*enabled:\\s*true\\s*\\n\\s*is_proactive:\\s*)false', r'\\1true', content)
if new != content: content = new; changed = True
if re.search(r'(code:\\s*\\n\\s*memory:\\s*\\n\\s*enabled:\\s*true\\s*\\n)(?!\\s*is_proactive)', content):
    new = re.sub(r'(code:\\s*\\n\\s*memory:\\s*\\n\\s*enabled:\\s*true\\s*\\n)(?!\\s*is_proactive)', r'\\1      is_proactive: true\\n', content)
    if new != content: content = new; changed = True
new = re.sub(r'(memory:\\s*\\n\\s*enabled:\\s*)false(\\s*\\n\\s*scenario:)', r'\\1true\\2', content)
if new != content: content = new; changed = True
if changed:
    _cmre = re.search(r'mcp:\s*\\n\s*servers:\s*\\n((?:[ \t]*-[^\\n]*\\n(?:[ \t]+[^\\n]*\\n)*)+)', content)
    if _cmre:
        _dashes = set(re.findall(r'^([ \t]*)- ', _cmre.group(1), re.M))
        if len(_dashes) > 1:
            print('ERROR: mcp.servers indent inconsistent - aborting, file NOT written', file=sys.stderr)
            sys.exit(2)
    with open(path, 'w') as f: f.write(content)

PYJW2
fi
JW_IFACE=$(find __OV_RT__/jiuwenswarm -path '*/agent_adapter/interface_code.py' ! -path '*__pycache__*' 2>/dev/null | head -1)
if [ -n "$JW_IFACE" ] && ! grep -q 'code-mode ExternalMemoryRail' "$JW_IFACE" 2>/dev/null; then
  $OV_PY -c 'p=__import__("sys").argv[1];c=open(p).read();m="    def _build_code_agent_rail";n="\\n        # code-mode ExternalMemoryRail (openviking-agent-integration)\\n        await self._handle_external_memory_rail_by_config()\\n"+m;open(p,"w").write(c.replace(m,n,1)) if m in c else None' "$JW_IFACE" 2>/dev/null
  find __OV_RT__/jiuwenswarm -path '*__pycache__*interface_code*' -delete 2>/dev/null
fi
JW_PROV=$(find __OV_RT__/jiuwenswarm -path '*/memory/external/openviking_memory_provider.py' ! -path '*__pycache__*' 2>/dev/null | head -1)
if [ -n "$JW_PROV" ] && ! grep -q 'ov-fix-limit' "$JW_PROV" 2>/dev/null; then
  $OV_PY -c 'p=__import__("sys").argv[1];q=chr(34);c=open(p).read();c=c.replace(q+"top_k"+q+": 5},",q+"limit"+q+": 5},  # ov-fix-limit").replace("payload["+q+"top_k"+q+"] = args["+q+"limit"+q+"]","payload["+q+"limit"+q+"] = args["+q+"limit"+q+"]  # ov-fix-limit");open(p,"w").write(c) if c!=open(p).read() else None' "$JW_PROV" 2>/dev/null
  find __OV_RT__/jiuwenswarm -path '*__pycache__*openviking_memory_provider*' -delete 2>/dev/null
fi
if [ -n "$JW_PROV" ] && ! grep -q 'ov-fix-session' "$JW_PROV" 2>/dev/null; then
  $OV_PY - "$JW_PROV" << 'PYJW3'
import sys
p = sys.argv[1]
c = open(p).read()
changed = False
# Fix 1: initialize() — generate jw- session ID
old1 = 'self._session_id = kwargs.get("session_id", "")\\n        try:'
new1 = ('self._session_id = kwargs.get("session_id", "")\\n'
       '        # ov-fix-session: generate jw- prefixed session ID for empty/__default__\\n'
       '        if not self._session_id or self._session_id == "__default__":\\n'
       '            import uuid; self._session_id = f"jw-{uuid.uuid4()}"\\n'
       '        try:')
if old1 in c:
    c = c.replace(old1, new1, 1); changed = True
# Fix 2: sync_turn() — use self._session_id instead of kwargs override
old2 = 'sid = kwargs.get("session_id", self._session_id)'
new2 = 'sid = self._session_id  # ov-fix-session: use initialized session ID'
if old2 in c:
    c = c.replace(old2, new2, 1); changed = True
if changed:
    open(p, 'w').write(c)
PYJW3
  find __OV_RT__/jiuwenswarm -path '*__pycache__*openviking_memory_provider*' -delete 2>/dev/null
fi
if [ -n "$JW_PROV" ] && ! grep -q 'ov-fix-commit' "$JW_PROV" 2>/dev/null; then
  $OV_PY - "$JW_PROV" << 'PYJW4'
import sys, os
p = sys.argv[1]
c = open(p).read()
changed = False
# Provider: threshold commit (every 5 turns) in sync_turn
old_pt = ('            )\\n'
          '            # ov-fix-commit: trigger memory extraction after each turn\\n'
          '            await asyncio.to_thread(\\n'
          '                self._client.post, f"/api/v1/sessions/{sid}/commit", {}\\n'
          '            )\\n'
          '        except Exception as e:\\n'
          '            logger.debug("OpenViking sync failed: %s", e)')
old_orig = ('            )\\n'
            '        except Exception as e:\\n'
            '            logger.debug("OpenViking sync failed: %s", e)')
new = ('            )\\n'
       '            # ov-fix-commit: threshold commit every 5 turns + session-end via uninit\\n'
       '            self._turn_count = getattr(self, "_turn_count", 0) + 1\\n'
       '            if self._turn_count >= 5:\\n'
       '                await asyncio.to_thread(\\n'
       '                    self._client.post, f"/api/v1/sessions/{sid}/commit", {}\\n'
       '                )\\n'
       '                self._turn_count = 0\\n'
       '        except Exception as e:\\n'
       '            logger.debug("OpenViking sync failed: %s", e)')
if old_pt in c:
    c = c.replace(old_pt, new, 1); changed = True
elif old_orig in c:
    c = c.replace(old_orig, new, 1); changed = True
if changed:
    open(p, 'w').write(c)
# Rail: add on_session_end before shutdown in uninit()
pkg = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(p))))
rail = os.path.join(pkg, "harness", "rails", "memory", "external_memory_rail.py")
if os.path.isfile(rail):
    rc = open(rail).read()
    rchanged = False
    r_old1 = ('            async def _shutdown_with_timeout():\\n'
              '                try:\\n'
              '                    await asyncio.wait_for(self._provider.shutdown(), timeout=10.0)')
    r_new1 = ('            async def _shutdown_with_timeout():\\n'
              '                # ov-fix-commit: commit session before shutdown\\n'
              '                try:\\n'
              '                    await asyncio.wait_for(self._provider.on_session_end([]), timeout=10.0)\\n'
              '                except Exception:\\n'
              '                    pass\\n'
              '                try:\\n'
              '                    await asyncio.wait_for(self._provider.shutdown(), timeout=10.0)')
    r_old2 = ('        except RuntimeError:\\n'
              '            try:\\n'
              '                asyncio.run(self._provider.shutdown())')
    r_new2 = ('        except RuntimeError:\\n'
              '            try:\\n'
              '                asyncio.run(self._provider.on_session_end([]))\\n'
              '            except Exception:\\n'
              '                pass\\n'
              '            try:\\n'
              '                asyncio.run(self._provider.shutdown())')
    if r_old1 in rc and 'ov-fix-commit' not in rc:
        rc = rc.replace(r_old1, r_new1, 1); rchanged = True
    if r_old2 in rc:
        rc = rc.replace(r_old2, r_new2, 1); rchanged = True
    if rchanged:
        open(rail, 'w').write(rc)
        import glob
        for f in glob.glob(os.path.join(os.path.dirname(rail), '__pycache__', 'external_memory_rail.*.pyc')):
            os.remove(f)
PYJW4
  find __OV_RT__/jiuwenswarm -path '*__pycache__*openviking_memory_provider*' -delete 2>/dev/null
  find __OV_RT__/jiuwenswarm -path '*__pycache__*external_memory_rail*' -delete 2>/dev/null
fi
mkdir -p /workspace
cat > /workspace/AGENTS.md << 'AGENTSMD'
__AGENTS_MD__
AGENTSMD
"""
    block = block.replace("__AGENTS_MD__", agents_md).replace("__OV_EP__", endpoint).replace("__OV_MCP__", mcp_url).replace("__OV_RT__", runtime_dir)
    # ISSUE-003: when --api-key was passed, embed it literally into the generated
    # config template (was a dead parameter — the runtime env never carried it).
    api_key = os.environ.get("OV_API_KEY", "")
    if api_key:
        block = block.replace("${OPENVIKING_API_KEY:-}", api_key)
        _ov_mark_key_consumed()
    init_path = f"{shared_dir}/ov-jiuwenswarm-init.sh"
    with open(init_path, "w") as f:
        f.write("#!/usr/bin/env bash\n# ── OpenViking integration for WorkSwarm ──\n")
        f.write(f"# Sourced by {template_dir}/jiuwenswarm/start.sh (single source line).\n")
        f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
        f.write(block)
    os.chmod(init_path, 0o755)
    source_block = f"# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──\nsource {shared_dir}/ov-jiuwenswarm-init.sh\n# ── End OpenViking integration ──\n"
    inserted = False
    for i, line in enumerate(lines):
        if 'nohup' in line and 'jiuwenswarm-start' in line:
            lines.insert(i, source_block)
            inserted = True
            break
    if not inserted:
        for i, line in enumerate(lines):
            if line.strip() == 'sleep infinity' or line.strip().startswith('sleep infinity'):
                lines.insert(i, source_block)
                break
    with open(path, 'w') as f:
        f.writelines(lines)


# ── unbind-template ─────────────────────────────────────────────
def cmd_unbind_template(args):
    """Remove OpenViking integration blocks from template start.sh."""
    path, shared_dir = args[0], args[1]
    content = read_text(path)
    new = re.sub(rf'# ── OpenViking integration \(added by huawei-cloud-openviking-agent-integration skill\) ──\n.*?# ── End OpenViking integration ──\n\n?', '', content, flags=re.DOTALL)
    new = re.sub(r'# 3\. Enhanced 4-section AGENTS\.md.*?fi\n', '', new, flags=re.DOTALL)
    new = re.sub(r'# ── OpenViking MCP injection.*?fi\n', '', new, flags=re.DOTALL)
    new = re.sub(r'\n# 4\. openviking-config\.json.*?fi\n', '\n', new, flags=re.DOTALL)
    new = re.sub(r"# 3\. Enhanced 4-section AGENTS\.md.*?AGENTSMD\n", '', new, flags=re.DOTALL)
    new = re.sub(r'# ── OpenViking native memory provider injection.*?AGENTSMD\n\n?', '', new, flags=re.DOTALL)
    if new != content:
        write_text(path, new)


# ── dispatch ────────────────────────────────────────────────────
def main():
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "mutate-config": cmd_mutate_config,
        "patch-iface-apply": cmd_patch_iface_apply,
        "patch-iface-revert": cmd_patch_iface_revert,
        "patch-prov-apply": cmd_patch_prov_apply,
        "patch-prov-revert": cmd_patch_prov_revert,
        "patch-session-apply": cmd_patch_session_apply,
        "patch-session-revert": cmd_patch_session_revert,
        "patch-commit-apply": cmd_patch_commit_apply,
        "patch-commit-revert": cmd_patch_commit_revert,
        "inject-template": cmd_inject_template,
        "unbind-template": cmd_unbind_template,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
