#!/usr/bin/env python3
"""WorkSwarm config.yaml mutation — single source of truth.
Called by _jw_mutate_config (during integrate/unbind) and by the sandbox
init script (ov-jiuwenswarm-init.sh) on every start.

Usage: python3 ov_jw_mutate.py <apply|revert> <config.yaml> [mcp_url]
"""
import sys, re, os

action, path = sys.argv[1], sys.argv[2]
mcp_url = sys.argv[3] if len(sys.argv) > 3 else ''

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

try:
    with open(path, encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
    sys.exit(1)
changed = False

def _dash_indent_of(content):
    """Detect existing mcp.servers entry dash indent; default 2-space compact style."""
    m = re.search(r'servers:[^\n]*\n([ \t]*)-[ \t]', content)
    return m.group(1) if m else '  '

def _insert_mcp_entry(content, mcp_url):
    """Insert openviking MCP entry with indentation matching existing entries.
    Pure-regex, no yaml library dependency (works inside bwrap sandbox)."""
    if "name: openviking" in content:
        return content, False
    dash = _dash_indent_of(content)
    inner = dash + '  '
    entry = (dash + '- name: openviking\n'
             + inner + 'transport: streamable-http\n'
             + inner + 'url: %s\n' % mcp_url
             + inner + 'enabled: true\n')
    # Case A: inline empty list  servers: []
    new = re.sub(r'(mcp:\s*\n\s*servers:\s*)\[\]', lambda m: m.group(1) + '\n' + entry, content)
    if new != content:
        return new, True
    # Case B: empty multi-line list  servers:\n (next line not a dash)
    new = re.sub(r'(mcp:\s*\n\s*servers:\s*\n)(?!\s*-)', lambda m: m.group(1) + entry, content)
    if new != content:
        return new, True
    # Case C: existing entries — append after the whole block, matching detected indent
    block_re = re.compile(r'(mcp:\s*\n\s*servers:\n(?:[ \t]*-[^\n]*\n(?:[ \t]+[^\n]*\n)*)*)')
    mm = block_re.search(content)
    if mm:
        return content[:mm.end()] + entry + content[mm.end():], True
    return content, False

def _check_mcp_indent(content):
    """Verify all entries under mcp.servers share one dash indent (no yaml lib needed)."""
    m = re.search(r'mcp:\s*\n\s*servers:\s*\n((?:[ \t]*-[^\n]*\n(?:[ \t]+[^\n]*\n)*)+)', content)
    if not m:
        return True
    block = m.group(1)
    dashes = set(re.findall(r'^([ \t]*)- ', block, re.M))
    return len(dashes) <= 1

def _validate_yaml(path, content, label):
    """Write-time guard: abort WITHOUT writing if the result is not parseable YAML."""
    ok = False
    try:
        import yaml as _y
        _y.safe_load(content)
        ok = True
    except Exception:
        pass
    if not ok:
        try:
            from ruamel.yaml import YAML as _RY
            _ry = _RY()
            _ry.load(content)
            ok = True
        except Exception:
            pass
    if not ok:
        if _check_mcp_indent(content):
            ok = True  # structural check passed, yaml libs unavailable
    if not ok:
        print("ERROR: %s produced invalid YAML — aborting, file NOT written (%s)" % (label, path), file=sys.stderr)
        sys.exit(2)


if action == 'apply':
    new = re.sub(r'(engine:\s*\$\{MEMORY_ENGINE:-)builtin(\})', r'\1external\2', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(provider:\s*\$\{MEMORY_EXTERNAL_PROVIDER:-)(\})', r'\1openviking\2', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(auto_memory_enabled:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(proactive_recommendation:\s*\n\s*enabled:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    # MCP insertion: use ruamel.yaml for correct indentation (ov-fix-yaml-indent)
    try:
        from ruamel.yaml import YAML
        _yaml = YAML()
        _yaml.preserve_quotes = True
        _yaml.indent(mapping=2, sequence=4, offset=2)
        _cfg = _yaml.load(content)
        _mcp = _cfg.get('mcp', None)
        if _mcp is not None:
            _servers = _mcp.get('servers', None)
            if _servers is None:
                from ruamel.yaml.comments import CommentedSeq
                _servers = CommentedSeq()
                _mcp['servers'] = _servers
            _has_ov = any(s.get('name') == 'openviking' for s in _servers)
            if not _has_ov:
                from ruamel.yaml.comments import CommentedMap
                _ov_entry = CommentedMap()
                _ov_entry['name'] = 'openviking'
                _ov_entry['transport'] = 'streamable-http'
                _ov_entry['url'] = mcp_url
                _ov_entry['enabled'] = True
                _servers.insert(0, _ov_entry)
                import io
                _buf = io.StringIO()
                _yaml.dump(_cfg, _buf)
                content = _buf.getvalue()
                changed = True
    except Exception:
        content, _mc = _insert_mcp_entry(content, mcp_url)
        if _mc:
            changed = True
    if "    openviking:" not in content:
        ov_block = "    openviking:\n      endpoint: ${OPENVIKING_ENDPOINT:-http://127.0.0.1:1933}\n      api_key: ${OPENVIKING_API_KEY:-}\n      account: ${OPENVIKING_ACCOUNT:-default}\n      user: ${OPENVIKING_USER:-default}\n"
        # ISSUE-003: --api-key was a dead parameter — the runtime env never carried
        # it, so only ${OPENVIKING_API_KEY:-} (empty) was ever expanded. Embed the
        # literal value when the entry point passed one.
        _api_key = os.environ.get("OV_API_KEY", "")
        if _api_key:
            ov_block = ov_block.replace("${OPENVIKING_API_KEY:-}", _api_key)
            _ov_mark_key_consumed()
        new = re.sub(r'(  external:\s*\n(?:    [^\n]*\n)*?)(    lakebase:)', lambda m: m.group(1) + ov_block + m.group(2), content)
        if new != content: content = new; changed = True
    new = re.sub(r"(account:\s*\$\{OPENVIKING_ACCOUNT:-)root(\})", r"\1default\2", content)
    if new != content: content = new; changed = True
    if "viking_search: allow" not in content:
        viking_perms = "    viking_search: allow\n    viking_read: allow\n    viking_browse: allow\n    viking_remember: allow\n    viking_add_resource: allow\n"
        new = re.sub(r'(    mem0_conclude: allow\n)', lambda m: m.group(1) + viking_perms, content)
        if new != content: content = new; changed = True
    new = re.sub(r'(fast:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    if re.search(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n)(?!\s*is_proactive)', content):
        new = re.sub(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n)(?!\s*is_proactive)', r'\1      is_proactive: true\n', content)
        if new != content: content = new; changed = True
    # ov-fix: code mode is_proactive false→true
    new = re.sub(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    # ov-fix: agent mode is_proactive
    if re.search(r'(agent:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n)(?!\s*is_proactive)', content):
        new = re.sub(r'(agent:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n)(?!\s*is_proactive)', r'\1      is_proactive: true\n', content)
        if new != content: content = new; changed = True
    new = re.sub(r'(agent:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    # ov-fix: compression_recall_config enabled
    new = re.sub(r'(compression_recall_config:\s*\n\s*enabled:\s*)false', r'\1true', content)
    if new != content: content = new; changed = True
    new = re.sub(r'(memory:\s*\n\s*enabled:\s*)false(\s*\n\s*scenario:)', r'\1true\2', content)
    if new != content: content = new; changed = True
    # ov-optimization: keep_recent 0->10 + commit thresholds (ruamel.yaml for correct indentation)
    try:
        from ruamel.yaml import YAML
        _yaml2 = YAML()
        _yaml2.preserve_quotes = True
        _yaml2.indent(mapping=2, sequence=4, offset=2)
        _cfg2 = _yaml2.load(content)
        _crc = _cfg2.get('compression_recall_config') if _cfg2 else None
        if _crc is not None:
            _need_rewrite = False
            # keep_recent: 0 -> 10
            if 'keep_recent' in _crc:
                try:
                    if int(_crc['keep_recent']) == 0:
                        _crc['keep_recent'] = 10
                        _need_rewrite = True
                except (ValueError, TypeError):
                    pass
            else:
                _crc['keep_recent'] = 10
                _need_rewrite = True
            # commit thresholds for auto-commit
            if 'commit_token_threshold' not in _crc:
                _crc['commit_token_threshold'] = 20000
                _need_rewrite = True
            if 'commit_turn_threshold' not in _crc:
                _crc['commit_turn_threshold'] = 5
                _need_rewrite = True
            if _need_rewrite:
                import io as _io2
                _buf2 = _io2.StringIO()
                _yaml2.dump(_cfg2, _buf2)
                content = _buf2.getvalue()
                changed = True
    except Exception:
        # Fallback: regex with 6-space indent (compression_recall_config nested at 4sp, children at 6sp)
        new = re.sub(r'(keep_recent:\s*)0\b', r'\g<1>10', content)
        if new != content: content = new; changed = True
        if 'commit_token_threshold' not in content:
            new = re.sub(r'(compression_recall_config:\s*\n\s*enabled:\s*true\s*\n(?:  \w+: [^\n]+\n)*)',
                          r'\1      commit_token_threshold: 20000\n      commit_turn_threshold: 5\n', content)
            if new != content: content = new; changed = True
    if changed:
        _validate_yaml(path, content, 'apply')
        try:
            with open(path, 'w', encoding='utf-8') as f: f.write(content)
        except Exception as e:
            print(f"ERROR: cannot write {path}: {e}", file=sys.stderr)
            sys.exit(1)

elif action == 'revert':
    original = content
    # Match both 4-space (apply attempt 1/2) and 2-space (apply attempt 3) indent
    content = re.sub(r'    - name: openviking\n(?:      .+\n)+', '', content, count=1)
    content = re.sub(r'  - name: openviking\n(?:    .+\n)+', '', content, count=1)
    # Only collapse to [] if no server entries remain (skip blank lines)
    if not re.search(r'  servers:\n(?:\s*\n)*  *- ', content):
        content = re.sub(r'  servers:\n(?:\s*\n)*', '  servers: []\n', content, count=1)
    content = content.replace("  servers: []\n\n  # 示例", "  servers: []\n  # 示例")
    content = re.sub(r'(engine:\s*\$\{MEMORY_ENGINE:-)(?:both|external)(\})', r'\1builtin\2', content)
    content = re.sub(r'(provider:\s*\$\{MEMORY_EXTERNAL_PROVIDER:-)openviking(\})', r'\1\2', content)
    content = re.sub(r'(\n    openviking:\n(?:      [^\n]*\n)+)', '\n', content)
    for perm in ('viking_search', 'viking_read', 'viking_browse', 'viking_remember', 'viking_add_resource'):
        content = re.sub(r'\n    ' + perm + r': allow\b', '', content)
    content = re.sub(r'(auto_memory_enabled:\s*)true', r'\1false', content)
    content = re.sub(r'(proactive_recommendation:\s*\n\s*enabled:\s*)true', r'\1false', content)
    content = re.sub(r'(fast:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)true', r'\1false', content)
    content = re.sub(r'(code:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)true', r'\1false', content)
    content = re.sub(r'(agent:\s*\n\s*memory:\s*\n\s*enabled:\s*true\s*\n\s*is_proactive:\s*)true', r'\1false', content)
    content = re.sub(r'(compression_recall_config:\s*\n\s*enabled:\s*)true', r'\1false', content)
    content = re.sub(r'(memory:\s*\n\s*enabled:\s*)true(\s*\n\s*scenario:)', r'\1false\2', content)
    # ov-optimization: revert keep_recent 10->0 + remove thresholds (ruamel.yaml for correct indentation)
    try:
        from ruamel.yaml import YAML
        _yaml3 = YAML()
        _yaml3.preserve_quotes = True
        _yaml3.indent(mapping=2, sequence=4, offset=2)
        _cfg3 = _yaml3.load(content)
        _crc3 = _cfg3.get('compression_recall_config') if _cfg3 else None
        if _crc3 is not None:
            _need_revert = False
            if 'keep_recent' in _crc3:
                try:
                    if int(_crc3['keep_recent']) == 10:
                        _crc3['keep_recent'] = 0
                        _need_revert = True
                except (ValueError, TypeError):
                    pass
            for _key in ('commit_token_threshold', 'commit_turn_threshold'):
                if _key in _crc3:
                    del _crc3[_key]
                    _need_revert = True
            if _need_revert:
                import io as _io3
                _buf3 = _io3.StringIO()
                _yaml3.dump(_cfg3, _buf3)
                content = _buf3.getvalue()
    except Exception:
        # Fallback: regex (best-effort)
        content = re.sub(r'(keep_recent:\s*)10\b', r'\g<1>0', content)
        content = re.sub(r'\n  commit_token_threshold: \d+\n  commit_turn_threshold: \d+', '', content)
    if content != original:
        _validate_yaml(path, content, 'revert')
        try:
            with open(path, 'w', encoding='utf-8') as f: f.write(content)
        except Exception as e:
            print(f"ERROR: cannot write {path}: {e}", file=sys.stderr)
            sys.exit(1)
