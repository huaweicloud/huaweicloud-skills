#!/usr/bin/env python3
"""ov_kimi_hook.py — KimiCode OpenViking hook helper CLI.

Replaces ALL inline ``$OV_PY3 -c "..."`` calls in
``scripts/lib/ov_kimi_hook.sh`` with a single dispatch-based tool.

Subcommands:
    json-field <field>                          extract field from JSON on stdin
    hook-output [message]                       format hook output JSON
    hook-deny <reason>                          format deny-decision JSON
    json-encode <string>                        JSON-encode a string
    peer-id [dir]                               derive peer ID from git config
    sanitize [text]                             strip injected OpenViking tags
    extract-wire <wire_file> <cursor> <u_max> <a_max>   incremental idempotent capture
    filter-signal [text]                        drop ack/slash/punctuation/too-short
    config-get <config_file> <dotted_key>       print config value ('' when absent)
    pending-tokens                              extract pending_tokens from stdin JSON
    archive-overview                            extract latest_archive_overview from stdin
    session-inject <sid> <archive>              assemble <openviking-context> (recall on stdin)
    recall-format <max_chars> <score_threshold> format recall results from stdin JSON
    pending-enqueue <dir> <kind> <path> <body>  write dedup'd pending item (0600)
    pending-should-send <file> <max_retries> <ttl_days>  print SEND or DROP
    pending-get <file> <key>                    print a field from a pending item
    pending-body <file>                         print the raw POST body of a pending item
    pending-bump <file>                         increment attempts + last_attempt_at
    state-update <key> <value> <state_file>     set a key in a JSON state file
    state-get <state_file> <key> [default]      print a key from a JSON state file
    state-get-bool <state_file> <key>           print 'true'/'false' for a boolean key
    state-orphan-check <state_file>             print sid if needs_commit is true
    state-mark-crash-recovered <state_file>     mark state committed + crash_recovered
    state-mark-committed <state_file>           mark committed, reset counters
    state-set-prompt <state_file> <prompt> <ts> set last_prompt + last_prompt_time
    state-update-stop <state_file> <needs_commit> <turn_count> <accumulated_chars>
    check-viking-uri                            print BLOCK if stdin JSON contains viking://
    json-stdin-get <key> [default]              print a key from JSON on stdin
    subagent-state-save <state_file> <parent_sid> <subagent_sid> <agent_name> <peer_id> <started_at>
    extract-subagent-transcript <kc_sid> <kc_dir>   extract full subagent transcript from wire.jsonl
"""
import hashlib
import json
import os
import re
import sys
import time

# Allow imports from the parent py/ directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ov_common import load_json, save_json, dotted_get


# ── json-field: extract a field from JSON on stdin (from _jf) ──────────────
def cmd_json_field(args):
    """Read JSON from stdin, print the named field.

    Dict/list values are printed as JSON; everything else is printed as-is
    (or empty string when falsy).  On any error, print empty string.
    """
    field = args[0]
    try:
        d = json.load(sys.stdin)
        v = d.get(field, "")
        if isinstance(v, (dict, list)):
            print(json.dumps(v))
        else:
            print(v or "")
    except Exception:
        print("")


# ── hook-output: format hook output JSON (from _ov_out) ────────────────────
def cmd_hook_output(args):
    """Print {"message": message} when message is non-empty, else {}."""
    msg = args[0] if args else ""
    r = {}
    if msg:
        r["message"] = msg
    print(json.dumps(r))


# ── hook-deny: format deny decision JSON (from _ov_deny) ───────────────────
def cmd_hook_deny(args):
    """Print a hookSpecificOutput deny decision with the given reason."""
    reason = args[0] if args else ""
    print(json.dumps({
        "hookSpecificOutput": {
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


# ── json-encode: JSON-encode a string (from _json_str) ─────────────────────
def cmd_json_encode(args):
    """Print json.dumps(args[0])."""
    print(json.dumps(args[0]))


# ── peer-id: derive peer ID from git config (from _ov_peer_id) ─────────────
def cmd_peer_id(args):
    """Walk up from *dir* looking for a .git/config URL.

    If found, normalise the URL and print its md5[:16].
    Otherwise print md5(dir)[:16].
    """
    d = args[0] if args else os.environ.get("CWD", "")
    while d != "/" and d:
        if os.path.isdir(os.path.join(d, ".git")):
            cfg = os.path.join(d, ".git", "config")
            if os.path.isfile(cfg):
                with open(cfg) as f:
                    for line in f:
                        m = re.match(r"\s*url\s*=\s*(.+)", line)
                        if m:
                            url = m.group(1).strip()
                            url = re.sub(r"^(https?://|git://|ssh://)", "", url)
                            url = re.sub(r"^[^@]*@", "", url)
                            url = re.sub(r"\.git$", "", url)
                            url = url.rstrip("/")
                            print(hashlib.md5(url.encode()).hexdigest()[:16])
                            return
            print(hashlib.md5(d.encode()).hexdigest()[:16])
            return
        d = os.path.dirname(d)
    print(hashlib.md5((args[0] if args else "").encode()).hexdigest()[:16])


# ── sanitize: strip injected OpenViking tags (from _ov_sanitize) ──────────
def cmd_sanitize(args):
    """Strip OpenViking recall blocks and injected XML-style tags."""
    text = args[0] if args else sys.stdin.read()
    text = re.sub(r"## OpenViking Recall\n.*?(?=\n\n|\n<|\n## |\Z)", "", text, flags=re.DOTALL)
    text = re.sub(r"<hook_result[^>]*>.*?</hook_result>", "", text, flags=re.DOTALL)
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.DOTALL)
    text = re.sub(r"<openviking-context>.*?</openviking-context>", "", text, flags=re.DOTALL)
    text = re.sub(r"</?hook_result[^>]*>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    print(text.strip())


# ── extract-wire: incremental, idempotent capture from wire.jsonl ──────────
def cmd_extract_wire(args):
    """Parse the NEW span of a KimiCode wire.jsonl since the last cursor.

    A byte-offset cursor (stored per-session in ``cursor_file``) makes the
    capture idempotent: each Stop only harvests events written since the last
    Stop, so intermediate turns are never dropped and never re-uploaded.

    args: wire_file cursor_file [user_max_chars] [assistant_max_chars]
    """
    wf = args[0]
    cursor_file = args[1] if len(args) > 1 else ""
    user_max = 8000
    assist_max = 32000
    if len(args) > 2:
        try:
            user_max = int(args[2])
        except Exception:
            pass
    if len(args) > 3:
        try:
            assist_max = int(args[3])
        except Exception:
            pass

    cur = {}
    if cursor_file:
        try:
            cur = load_json(cursor_file)
        except Exception:
            cur = {}
    offset = 0
    if cur.get("path") == wf and isinstance(cur.get("offset"), int) and cur["offset"] > 0:
        offset = cur["offset"]

    user_text = ""
    assistant_parts = []
    last_text = None
    try:
        with open(wf, encoding="utf-8", errors="replace") as f:
            if offset:
                f.seek(offset)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                t = d.get("type", "")
                if t == "turn.prompt":
                    for p in d.get("input", []) or []:
                        if isinstance(p, dict) and p.get("type") == "text":
                            user_text = p.get("text", "") or ""
                elif t == "context.append_message":
                    m = d.get("message", {}) or {}
                    o = m.get("origin", {}) or {}
                    if m.get("role") == "user" and o.get("kind") == "user":
                        for p in m.get("content", []) or []:
                            if isinstance(p, dict) and p.get("type") == "text":
                                user_text = p.get("text", "") or ""
                elif t == "context.append_loop_event":
                    pt = (d.get("event", {}) or {}).get("part", {}) or {}
                    if pt.get("type") == "text":
                        tx = pt.get("text", "") or ""
                        if tx and tx != last_text:
                            assistant_parts.append(tx)
                            last_text = tx
    except Exception:
        pass

    new_offset = 0
    try:
        new_offset = os.path.getsize(wf)
    except Exception:
        pass
    if cursor_file:
        try:
            save_json(cursor_file, {"path": wf, "offset": new_offset})
        except Exception:
            pass

    assistant = "\n".join(assistant_parts)
    print(json.dumps({
        "user": user_text[:user_max],
        "assistant": assistant[:assist_max],
    }))


# ── filter-signal: drop ack / slash-command / punctuation / too-short ──────
_ACK_TOKENS = {
    "收到", "好的", "好", "嗯", "呃", "可以", "行", "对", "是的", "明白", "了解",
    "继续", "不用", "不需要", "没有了", "没了", "好了", "没事", "谢谢", "thanks",
    "thankyou", "gotit", "sure", "ok", "okay", "yes", "no", "continue", "goahead",
}

def _signal_normalize(s):
    return re.sub(r"[\W_]+", "", s, flags=re.UNICODE).lower()


def cmd_filter_signal(args):
    """Print *text* unchanged when it carries signal, else print ''.

    Drops pure acknowledgements, slash commands, punctuation-only and
    too-short strings — mirroring the official ``shouldCaptureText``.
    """
    text = args[0] if args else sys.stdin.read()
    t = (text or "").strip()
    if not t:
        print("")
        return
    norm = _signal_normalize(t)
    if not norm:
        print("")  # punctuation-only
        return
    if norm in _ACK_TOKENS:
        print("")
        return
    if re.match(r"^/[A-Za-z]", t):
        print("")
        return
    if len(norm) < 2:
        print("")  # too short to be meaningful
        return
    print(text)


# ── config-get: read a (dotted) value from a JSON config file ──────────────
def cmd_config_get(args):
    """Print config[dotted_key] or '' when the file/key does not exist."""
    path, key = args[0], args[1]
    try:
        v = dotted_get(load_json(path), key)
        if v is None:
            print("")
        elif isinstance(v, (dict, list)):
            print(json.dumps(v))
        else:
            print(v)
    except Exception:
        print("")


# ── pending-tokens: extract server-reported pending_tokens ─────────────────
def cmd_pending_tokens(args):
    """Print result.pending_tokens (int) from stdin JSON, else 0."""
    try:
        d = json.load(sys.stdin)
        r = d.get("result", {}) or {}
        v = r.get("pending_tokens", d.get("pending_tokens", 0))
        print(int(v) if isinstance(v, (int, float)) else 0)
    except Exception:
        print("0")


# ── archive-overview: extract latest_archive_overview ──────────────────────
def cmd_archive_overview(args):
    """Print result.latest_archive_overview from stdin JSON, else ''."""
    try:
        d = json.load(sys.stdin)
        r = d.get("result", {}) or {}
        v = r.get("latest_archive_overview", "") or ""
        print(v)
    except Exception:
        print("")


# ── session-inject: assemble the session-start context block ───────────────
def cmd_session_inject(args):
    """Read recall text from stdin; build an <openviking-context> block.

    args: session_id archive_overview
    """
    sid = args[0] if args else ""
    archive = args[1] if len(args) > 1 else ""
    recall = sys.stdin.read().strip()
    parts = []
    if archive:
        parts.append('<session-archive session="%s">\n%s\n</session-archive>' % (sid, archive))
    if recall:
        parts.append('<recall>\n%s\n</recall>' % recall)
    if not parts:
        print("")
        return
    print('<openviking-context source="session-start" session="%s">\n%s\n</openviking-context>'
          % (sid, "\n".join(parts)))


# ── recall-format: format recall search results (from _ov_recall) ─────────
def cmd_recall_format(args):
    """Read search-result JSON from stdin and print formatted recall text.

    args: max_chars score_threshold
    """
    max_chars = int(args[0])
    score_threshold = float(args[1])
    try:
        d = json.load(sys.stdin)
        r = d.get("result", "")
        if isinstance(r, str) and r.strip():
            print(r[:max_chars])
        elif isinstance(r, dict):
            p = []
            # v0.4.19 search/recall response shape: result.entries[] (uri/category/score/text)
            for i in r.get("entries", [])[:8]:
                a = i.get("text") or i.get("detail") or i.get("abstract") or i.get("summary") or ""
                s = i.get("score", 0)
                if a and s >= score_threshold:
                    uri = i.get("uri", "")
                    cat = i.get("category", "")
                    a = a[:160]
                    p.append(f"- [{s:.2f}] {a} ({uri})" if not cat else f"- [{s:.2f}] {a} ({uri}, {cat})")
            # legacy shapes (memories/resources/skills groups)
            for ct in ("memories", "resources", "skills"):
                for i in r.get(ct, [])[:5]:
                    a = i.get("abstract", "") or i.get("summary", "")
                    s = i.get("score", 0)
                    if a and s >= score_threshold:
                        uri = i.get("uri", "")
                        p.append(f"- [{s:.2f}] {a} ({uri})")
            if p:
                out = "## OpenViking Recall\n" + "\n".join(p)
                print(out[:max_chars])
    except Exception:
        pass


# ── pending queue (P1-3) ───────────────────────────────────────────────────
def _pending_dedup_key(kind, path, body):
    return hashlib.sha256(("%s\n%s\n%s" % (kind, path, body)).encode("utf-8")).hexdigest()


def cmd_pending_enqueue(args):
    """Write a dedup'd pending item to <dir>/<sha256>.json (mode 0600)."""
    pdir, kind, path, body = args[0], args[1], args[2], args[3]
    try:
        os.makedirs(pdir, exist_ok=True)
        os.chmod(pdir, 0o700)
    except Exception:
        pass
    key = _pending_dedup_key(kind, path, body)
    fp = os.path.join(pdir, key + ".json")
    if os.path.exists(fp):
        return  # idempotent: same payload already queued
    item = {
        "kind": kind,
        "method": "POST",
        "path": path,
        "body": body,
        "created_at": int(time.time()),
        "attempts": 0,
    }
    try:
        save_json(fp, item)
        os.chmod(fp, 0o600)
    except Exception:
        pass


def cmd_pending_should_send(args):
    """Print 'SEND' when retries/TTL allow, else 'DROP'."""
    fp = args[0]
    try:
        max_retries = int(args[1])
    except Exception:
        max_retries = 3
    try:
        ttl_days = int(args[2])
    except Exception:
        ttl_days = 7
    try:
        s = load_json(fp)
    except Exception:
        print("DROP")
        return
    attempts = int(s.get("attempts", 0) or 0)
    if attempts >= max_retries:
        print("DROP")
        return
    created = int(s.get("created_at", 0) or 0)
    if ttl_days > 0 and created and (time.time() - created) > ttl_days * 86400:
        print("DROP")
        return
    print("SEND")


def cmd_pending_get(args):
    """Print a field (kind/method/path/attempts/...) from a pending item."""
    fp, key = args[0], args[1]
    try:
        s = load_json(fp)
        v = s.get(key, "")
        print(v)
    except Exception:
        print("")


def cmd_pending_body(args):
    """Print the raw POST body string of a pending item."""
    fp = args[0]
    try:
        s = load_json(fp)
        print(s.get("body", ""))
    except Exception:
        print("")


def cmd_pending_bump(args):
    """Increment attempts and record last_attempt_at."""
    fp = args[0]
    try:
        s = load_json(fp)
        s["attempts"] = int(s.get("attempts", 0) or 0) + 1
        s["last_attempt_at"] = int(time.time())
        save_json(fp, s)
    except Exception:
        pass


# ── state-update: set a key in a JSON state file (from _ov_state_update) ──
def cmd_state_update(args):
    """Set state[key] = value (as string) and save."""
    key, val, stf = args[0], args[1], args[2]
    try:
        s = load_json(stf)
    except Exception:
        s = {}
    s[key] = val
    save_json(stf, s)


# ── state-get: print a key from a JSON state file ─────────────────────────
def cmd_state_get(args):
    """Print state[key] or default (default = '' unless given)."""
    stf, key = args[0], args[1]
    default = args[2] if len(args) > 2 else ""
    try:
        s = load_json(stf)
        print(s.get(key, default))
    except Exception:
        print(default)


# ── state-get-bool: print 'true'/'false' for a boolean key ────────────────
def cmd_state_get_bool(args):
    """Print 'true' or 'false' for state[key]."""
    stf, key = args[0], args[1]
    try:
        s = load_json(stf)
        print("true" if s.get(key, False) else "false")
    except Exception:
        print("false")


# ── state-orphan-check: print sid if needs_commit is true ─────────────────
def cmd_state_orphan_check(args):
    """Print the session id if the state file has needs_commit=True."""
    stf = args[0]
    try:
        s = load_json(stf)
        if s.get("needs_commit", False) and s.get("sid", ""):
            print(s["sid"])
    except Exception:
        pass


# ── state-mark-crash-recovered: mark state after crash recovery ───────────
def cmd_state_mark_crash_recovered(args):
    """Set needs_commit=False, committed=True, crash_recovered=True."""
    stf = args[0]
    try:
        s = load_json(stf)
        s["needs_commit"] = False
        s["committed"] = True
        s["crash_recovered"] = True
        save_json(stf, s)
    except Exception:
        pass


# ── state-mark-committed: mark committed and reset counters ───────────────
def cmd_state_mark_committed(args):
    """Set needs_commit=False, committed=True, turn_count=0, accumulated_chars=0."""
    stf = args[0]
    try:
        s = load_json(stf)
        s["needs_commit"] = False
        s["committed"] = True
        s["turn_count"] = 0
        s["accumulated_chars"] = 0
        save_json(stf, s)
    except Exception:
        pass


# ── state-set-prompt: set last_prompt and last_prompt_time ────────────────
def cmd_state_set_prompt(args):
    """Set state['last_prompt'] = prompt, state['last_prompt_time'] = ts."""
    stf, prompt, ts = args[0], args[1], args[2]
    try:
        s = load_json(stf)
        s["last_prompt"] = prompt
        s["last_prompt_time"] = int(ts)
        save_json(stf, s)
    except Exception:
        pass


# ── state-update-stop: update stop-event stats ────────────────────────────
def cmd_state_update_stop(args):
    """Set needs_commit, turn_count, accumulated_chars in the state file."""
    stf = args[0]
    needs_commit = args[1] == "true"
    turn_count = int(args[2])
    accumulated_chars = int(args[3])
    try:
        s = load_json(stf)
        s["needs_commit"] = needs_commit
        s["turn_count"] = turn_count
        s["accumulated_chars"] = accumulated_chars
        save_json(stf, s)
    except Exception:
        pass


# ── check-viking-uri: check if stdin JSON contains viking:// ──────────────
def cmd_check_viking_uri(args):
    """Print 'BLOCK' if any string in the stdin JSON contains 'viking://'."""
    try:
        d = json.load(sys.stdin)

        def check(obj):
            if isinstance(obj, str):
                if "viking://" in obj:
                    return True
            elif isinstance(obj, dict):
                for v in obj.values():
                    if check(v):
                        return True
            elif isinstance(obj, list):
                for v in obj:
                    if check(v):
                        return True
            return False

        if check(d):
            print("BLOCK")
    except Exception:
        pass


# ── json-stdin-get: print a key from JSON on stdin ────────────────────────
def cmd_json_stdin_get(args):
    """Print stdin_json[key] or default (default = '' unless given)."""
    key = args[0]
    default = args[1] if len(args) > 1 else ""
    try:
        d = json.load(sys.stdin)
        print(d.get(key, default))
    except Exception:
        print(default)


# ── subagent-state-save: write subagent state JSON ────────────────────────
def cmd_subagent_state_save(args):
    """Write a subagent state file with parent/subagent metadata."""
    stf, parent_sid, subagent_sid, agent_name, peer_id, started_at = (
        args[0], args[1], args[2], args[3], args[4], args[5]
    )
    with open(stf, "w") as f:
        json.dump({
            "parent_sid": parent_sid,
            "subagent_sid": subagent_sid,
            "agent_name": agent_name,
            "peer_id": peer_id,
            "started_at": int(started_at),
        }, f)


# ── extract-subagent-transcript: extract full transcript from wire.jsonl ──
def cmd_extract_subagent_transcript(args):
    """Find the most recent non-main agent wire.jsonl and extract text parts."""
    kc_sid = args[0]
    kc_dir = args[1]
    for root, dirs, files in os.walk(os.path.join(kc_dir, "sessions")):
        if os.path.basename(root) == kc_sid:
            agents_dir = os.path.join(root, "agents")
            if os.path.isdir(agents_dir):
                # Find most recently modified agent-N wire.jsonl (exclude main)
                candidates = []
                for d in os.listdir(agents_dir):
                    if d == "main":
                        continue
                    wf = os.path.join(agents_dir, d, "wire.jsonl")
                    if os.path.isfile(wf):
                        candidates.append((os.path.getmtime(wf), wf))
                if candidates:
                    candidates.sort(reverse=True)
                    wf = candidates[0][1]
                    parts = []
                    with open(wf) as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                ev = json.loads(line)
                            except Exception:
                                continue
                            t = ev.get("type", "")
                            if t == "context.append_message":
                                m = ev.get("message", {})
                                role = m.get("role", "")
                                for p in m.get("content", []):
                                    if isinstance(p, dict) and p.get("type") == "text":
                                        txt = p.get("text", "")
                                        if txt and len(txt) > 20:
                                            parts.append(f"[{role}] {txt[:6000]}")
                            elif t == "context.append_loop_event":
                                pt = ev.get("event", {}).get("part", {})
                                if pt.get("type") == "text":
                                    txt = pt.get("text", "")
                                    if txt and len(txt) > 20:
                                        parts.append(f"[assistant] {txt[:6000]}")
                    if parts:
                        print("\n".join(parts[:20])[:20000])
            break


# ── Main dispatch ──────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: ov_kimi_hook.py <subcommand> [args...]", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    args = sys.argv[2:]
    dispatch = {
        "json-field": cmd_json_field,
        "hook-output": cmd_hook_output,
        "hook-deny": cmd_hook_deny,
        "json-encode": cmd_json_encode,
        "peer-id": cmd_peer_id,
        "sanitize": cmd_sanitize,
        "extract-wire": cmd_extract_wire,
        "filter-signal": cmd_filter_signal,
        "config-get": cmd_config_get,
        "pending-tokens": cmd_pending_tokens,
        "archive-overview": cmd_archive_overview,
        "session-inject": cmd_session_inject,
        "recall-format": cmd_recall_format,
        "pending-enqueue": cmd_pending_enqueue,
        "pending-should-send": cmd_pending_should_send,
        "pending-get": cmd_pending_get,
        "pending-body": cmd_pending_body,
        "pending-bump": cmd_pending_bump,
        "state-update": cmd_state_update,
        "state-get": cmd_state_get,
        "state-get-bool": cmd_state_get_bool,
        "state-orphan-check": cmd_state_orphan_check,
        "state-mark-crash-recovered": cmd_state_mark_crash_recovered,
        "state-mark-committed": cmd_state_mark_committed,
        "state-set-prompt": cmd_state_set_prompt,
        "state-update-stop": cmd_state_update_stop,
        "check-viking-uri": cmd_check_viking_uri,
        "json-stdin-get": cmd_json_stdin_get,
        "subagent-state-save": cmd_subagent_state_save,
        "extract-subagent-transcript": cmd_extract_subagent_transcript,
    }
    fn = dispatch.get(cmd)
    if not fn:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(2)
    fn(args)


if __name__ == "__main__":
    main()