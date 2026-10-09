#!/usr/bin/env python3
"""ov_deepseek_harness.py — DeepSeek Harness agent Python operations CLI.

Replaces all heredoc Python and inline ``python3 -c`` calls in
agents/deepseek_harness.sh.

Subcommands:
    ov_body <home> <src> <url>
        Install @openviking/dsh-memory-plugin bundle into live dsh profiles
        (web, dsh-tui).  Equivalent to the dsh_ov_body() heredoc piped to python3.

    tpl_block <url>
        Emit the shell template block (for ov-deepseek-harness-init.sh) with
        embedded Python runtime code.  Equivalent to dsh_tpl_block() in the shell.

    seed_profiles <home> <src>
        Pre-seed runtime .dsh/profiles (deploy-resilient layer).
        Equivalent to the DSHSEED heredoc.

    inject_template <tpl_path> <init_path> <template_dir> <shared_dir>
        Read a template block from stdin, write it to the standalone init script,
        and inject a source line into the template start.sh.
        Equivalent to the DSHINJ heredoc.

    unbind_template <path>
        Remove the OpenViking integration block from a template start.sh.
        Equivalent to the DSHUNBINJ heredoc.

    remove_bundle <package_json_path>
        Remove @openviking/dsh-memory-plugin from dependencies and dsh.profile.bundles
        in a package.json.  Equivalent to the DSHPJSON / DSHRTJSON heredocs.
"""
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))  # parent dir holds ov_common.py
from ov_common import (
    read_text,
    write_text,
    write_init,
    source_block,
    load_json,
    save_json,
)

BUNDLE = "@openviking/dsh-memory-plugin"

# ── Runtime Python code embedded in the init script ──────────────────
# This is the exact code from the dsh_ov_body() DSHOVBODY heredoc.
# It runs at sandbox startup via:
#   "$_ov_py" - "$DSH_HOME" "$DSH_RUNTIME/.../dsh-memory-plugin" "$OPENVIKING_URL" <<'OVDSPY'
# The code uses sys.argv[1:] directly (not subcommand dispatch) because it is
# fed to the interpreter via stdin heredoc, not invoked as a CLI script.
OV_BODY_CODE = """\
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
        sys.stderr.write('skip %s profile: package.json not found\\n' % prof)
        return
    target = os.path.join(pdir, 'node_modules', '@openviking', 'dsh-memory-plugin')
    if os.path.islink(target) and not os.path.isdir(target):
        os.remove(target)
    if os.path.islink(target):
        os.remove(target)
    parent = os.path.dirname(target)
    os.makedirs(parent, exist_ok=True)
    if os.path.isdir(src):
        # Re-copy if target missing OR src commit differs (src/.openviking-sync newer):
        # keeps live profiles from going stale when the runtime cache is updated.
        need_copy = not os.path.isdir(target)
        if not need_copy:
            src_meta = os.path.join(src, '.openviking-sync')
            dst_meta = os.path.join(target, '.openviking-sync')
            if os.path.isfile(src_meta):
                src_t = os.path.getmtime(src_meta)
                dst_t = os.path.getmtime(dst_meta) if os.path.isfile(dst_meta) else 0
                need_copy = src_t > dst_t
        if need_copy:
            if os.path.isdir(target):
                shutil.rmtree(target)
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
"""

# ── Template block (dsh_tpl_block in the shell) ──────────────────────
# Shell variables ($DSH_RUNTIME, $DSH_HOME, $OPENVIKING_URL, $_ov_py, …) are
# preserved as literal dollar signs — they are expanded at sandbox startup time.
# __URL__ is replaced with the OpenViking endpoint; __OV_BODY_CODE__ is replaced
# with the embedded runtime Python code above.
_TPL_BLOCK_TEMPLATE = """# ── OpenViking memory integration (added by huawei-cloud-openviking-agent-integration skill) ──
# @openviking/dsh-memory-plugin installed as real package into web/dsh-tui profile node_modules,
# registered in dsh.profile.bundles. Idempotent; cache-first (peer dep sync guarded by marker).
if [ -d "$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" ]; then
  export OPENVIKING_URL="${OPENVIKING_URL:-__URL__}"
  _ov_py=""
  for _py in python3.12 python3.11 python3.10 python3; do command -v "$_py" >/dev/null 2>&1 && _ov_py="$_py" && break; done
  : "${_ov_py:=python3}"
  "$_ov_py" - "$DSH_HOME" "$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin" "$OPENVIKING_URL" <<'OVDSPY'
__OV_BODY_CODE__
OVDSPY
  _dsh_nm="$DSH_RUNTIME/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
  _plugin_da="$DSH_RUNTIME/plugins/@openviking/dsh-memory-plugin/node_modules/@deepseek-ai"
  _peers_marker="$_plugin_da/.openviking-peers-synced"
  # Host fingerprint = dsh version + every @deepseek-ai/* package version. Marker
  # stores this fingerprint; sync runs only when the host runtime actually changed.
  _dsh_fp=""
  if [[ -f "$DSH_RUNTIME/lib/node_modules/@deepseek-ai/dsh/package.json" ]]; then
    _dsh_fp=$("$_ov_py" -c "import json,glob,os,hashlib
base='$DSH_RUNTIME/lib/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'
h=hashlib.sha1()
for pkg in sorted(glob.glob(os.path.join(base,'*','package.json'))):
    try: h.update(json.load(open(pkg)).get('version','').encode())
    except Exception: pass
print(h.hexdigest())" 2>/dev/null)
  fi
  if [[ -f "$_peers_marker" && "$(cat "$_peers_marker" 2>/dev/null)" == "$_dsh_fp" && -n "$_dsh_fp" ]]; then
    echo "OV peer deps already synced (host fingerprint match)."
  elif [[ -d "$_dsh_nm" && -d "$_plugin_da" && -n "$_dsh_fp" ]]; then
    for _pd in "$_dsh_nm"/*; do
      [[ -d "$_pd" ]] || continue
      _pn=$(basename "$_pd")
      # Host-matched: copy EVERY @deepseek-ai/* package (incl. dsh-llm/dsh-tools) so
      # plugin deps always equal the installed dsh runtime version — never pinned.
      rm -rf "$_plugin_da/$_pn"
      cp -r "$_pd" "$_plugin_da/$_pn"
    done
    printf '%s' "$_dsh_fp" > "$_peers_marker"
    echo "OV peer deps synced (host fingerprint $_dsh_fp)."
  else
    echo "OV peer deps: host fingerprint unavailable — skipping (no sync)"
  fi
fi
"""


# ── ov_body (DSHOVBODY heredoc) ──────────────────────────────────────
def cmd_ov_body(args):
    """Install @openviking/dsh-memory-plugin bundle into live dsh profiles (web, dsh-tui).

    Args: home, src, url  (url is accepted for parity with the heredoc but unused).
    """
    home = args[0]
    src = args[1]
    # url = args[2]  # accepted for parity with the heredoc; unused in this logic

    def install(prof):
        pdir = os.path.join(home, "profiles", prof)
        manifest = os.path.join(pdir, "package.json")
        if not os.path.isfile(manifest):
            sys.stderr.write("skip %s profile: package.json not found\n" % prof)
            return
        target = os.path.join(pdir, "node_modules", "@openviking", "dsh-memory-plugin")
        if os.path.islink(target) and not os.path.isdir(target):
            os.remove(target)
        if os.path.islink(target):
            os.remove(target)
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        if os.path.isdir(src):
            # Re-copy if target missing OR src commit differs (src/.openviking-sync newer):
            # keeps live profiles from going stale when the runtime cache is updated.
            need_copy = not os.path.isdir(target)
            if not need_copy:
                src_meta = os.path.join(src, ".openviking-sync")
                dst_meta = os.path.join(target, ".openviking-sync")
                if os.path.isfile(src_meta):
                    src_t = os.path.getmtime(src_meta)
                    dst_t = os.path.getmtime(dst_meta) if os.path.isfile(dst_meta) else 0
                    need_copy = src_t > dst_t
            if need_copy:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                shutil.copytree(src, target)
        pkg = load_json(manifest)
        changed = False
        # Don't add link: dep — pnpm creates broken symlinks; real dir + bundles registration suffices.
        deps = pkg.get("dependencies", {})
        if BUNDLE in deps:
            del deps[BUNDLE]
            changed = True
        bundles = pkg.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
        if BUNDLE not in bundles:
            bundles.append(BUNDLE)
            changed = True
        if changed:
            save_json(manifest, pkg)
        print("openviking-memory bundle ready in %s profile -> %s" % (prof, target))

    install("web")
    install("dsh-tui")


# ── tpl_block (dsh_tpl_block shell function) ─────────────────────────
def cmd_tpl_block(args):
    """Emit the shell template block for ov-deepseek-harness-init.sh.

    Args: url  (the OpenViking endpoint).
    """
    url = args[0]
    block = _TPL_BLOCK_TEMPLATE.replace("__URL__", url).replace(
        "__OV_BODY_CODE__", OV_BODY_CODE
    )
    sys.stdout.write(block)


# ── seed_profiles (DSHSEED heredoc) ──────────────────────────────────
def cmd_seed_profiles(args):
    """Pre-seed runtime .dsh/profiles (deploy-resilient layer).

    Args: home, src.
    """
    home = args[0]
    src = args[1]

    for prof in ("web", "dsh-tui"):
        pdir = os.path.join(home, "profiles", prof)
        manifest = os.path.join(pdir, "package.json")
        if not os.path.isfile(manifest):
            continue
        pkg = load_json(manifest)
        changed = False
        deps = pkg.get("dependencies", {})
        if BUNDLE in deps:
            del deps[BUNDLE]
            changed = True
        bundles = pkg.setdefault("dsh", {}).setdefault("profile", {}).setdefault("bundles", [])
        if BUNDLE not in bundles:
            bundles.append(BUNDLE)
            changed = True
        if changed:
            save_json(manifest, pkg)
        target = os.path.join(pdir, "node_modules", "@openviking", "dsh-memory-plugin")
        if os.path.islink(target):
            os.remove(target)
        if not os.path.isdir(target):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copytree(src, target)


# ── inject_template (DSHINJ heredoc) ─────────────────────────────────
def cmd_inject_template(args):
    """Write init script from stdin block and inject source line into template start.sh.

    Args: tpl_path, init_path, template_dir, shared_dir.
    Reads the template block from stdin.
    """
    tpl_path = args[0]
    init_path = args[1]
    template_dir = args[2]
    shared_dir = args[3]
    block = sys.stdin.read()

    write_init(
        init_path,
        "DeepSeek Harness",
        f"Sourced by {template_dir}/deepseek-harness/start.sh (single source line).",
        block.lstrip("\n"),
    )
    sb = source_block(shared_dir, "ov-deepseek-harness-init.sh")

    content = read_text(tpl_path)
    if "ov-deepseek-harness-init.sh" in content:
        sys.exit(0)
    anchor = 'echo "==> starting DeepSeek Harness web UI (http://127.0.0.1:${DSH_WEB_PORT}) ..."\n'
    if anchor not in content:
        sys.stderr.write("ERROR: anchor not found in template start.sh\n")
        sys.exit(1)
    content = content.replace(anchor, sb + anchor, 1)
    write_text(tpl_path, content)


# ── unbind_template (DSHUNBINJ heredoc) ──────────────────────────────
def cmd_unbind_template(args):
    """Remove OpenViking integration block from template start.sh.

    Args: path.
    Handles both new-style (3-line source block) and old-style (═══ rule lines)
    injection formats.
    """
    path = args[0]
    content = read_text(path)
    changed = False
    # New-style: remove the 3-line source block
    marker = "# ── OpenViking integration (added by huawei-cloud-openviking-agent-integration skill) ──"
    idx = content.find(marker)
    if idx != -1:
        end_marker = "# ── End OpenViking integration ──"
        end_idx = content.find(end_marker, idx)
        if end_idx != -1:
            cut_end = end_idx + len(end_marker)
            while cut_end < len(content) and content[cut_end] == "\n":
                cut_end += 1
            content = content[:idx] + content[cut_end:]
            changed = True
    # Old-style fallback: remove the full injected block with ═══ rule lines
    if not changed and "OpenViking long-term memory integration" in content:
        lines = content.split("\n")
        anchor = 'echo "==> starting DeepSeek Harness web UI'
        anchor_idx = None
        for i, line in enumerate(lines):
            if anchor in line:
                anchor_idx = i
                break
        if anchor_idx is not None:
            marker_idx = None
            for i in range(anchor_idx - 1, -1, -1):
                if "OpenViking long-term memory integration" in lines[i]:
                    marker_idx = i
                    break
            start = None
            if marker_idx is not None:
                for i in range(marker_idx - 1, -1, -1):
                    if lines[i].startswith("# ═══════════"):
                        start = i
                        break
            if start is None and marker_idx is not None:
                start = marker_idx
            if start is not None:
                end = anchor_idx
                while end > start and lines[end - 1] == "":
                    end -= 1
                new_lines = lines[:start] + lines[anchor_idx:]
                while new_lines and new_lines[-1] == "":
                    new_lines.pop()
                content = "\n".join(new_lines) + "\n"
                changed = True
    if changed:
        write_text(path, content)


# ── remove_bundle (DSHPJSON / DSHRTJSON heredocs) ────────────────────
def cmd_remove_bundle(args):
    """Remove @openviking/dsh-memory-plugin from dependencies and bundles in package.json.

    Args: path  (path to package.json).
    Used for both live profiles (DSHPJSON) and runtime profiles (DSHRTJSON).
    """
    path = args[0]
    pkg = load_json(path)
    changed = False
    deps = pkg.get("dependencies")
    if deps:
        if deps.pop(BUNDLE, None) is not None:
            changed = True
        if not deps:
            pkg.pop("dependencies")
    bundles = pkg.get("dsh", {}).get("profile", {}).get("bundles")
    if bundles:
        b = [x for x in bundles if x != BUNDLE]
        if len(b) != len(bundles):
            bundles[:] = b
            changed = True
        if not bundles:
            profile = pkg.get("dsh", {}).get("profile", {})
            profile.pop("bundles", None)
            if not profile:
                pkg.get("dsh", {}).pop("profile", None)
            if not pkg.get("dsh"):
                pkg.pop("dsh", None)
    if changed:
        save_json(path, pkg)


# ── dispatch ─────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        sys.stderr.write(
            "Usage: ov_deepseek_harness.py <subcommand> [args...]\n"
            "Subcommands: ov_body, tpl_block, seed_profiles, inject_template, "
            "unbind_template, remove_bundle\n"
        )
        sys.exit(2)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "ov_body": cmd_ov_body,
        "tpl_block": cmd_tpl_block,
        "seed_profiles": cmd_seed_profiles,
        "inject_template": cmd_inject_template,
        "unbind_template": cmd_unbind_template,
        "remove_bundle": cmd_remove_bundle,
    }
    fn = dispatch.get(cmd)
    if not fn:
        sys.stderr.write(f"Unknown subcommand: {cmd}\n")
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()
