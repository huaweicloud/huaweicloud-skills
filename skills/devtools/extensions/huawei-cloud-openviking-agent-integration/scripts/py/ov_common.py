#!/usr/bin/env python3
"""ov_common.py — Shared utilities for all ov_*.py CLI helpers.

Every standalone Python script under scripts/py/ imports from this module to
avoid duplicating JSON / file / string helpers.  The shell scripts call these
.py files directly via ``"$OV_PY" "$PY_DIR/ov_xxx.py" <subcommand> ...``.
"""
import json
import os


# ── JSON helpers ──────────────────────────────────────────────
def load_json(path):
    """Load a JSON file and return the parsed object."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data, indent=2):
    """Write *data* as JSON to *path* with a trailing newline.

    ISSUE-014: write to a temp file in the same directory and atomically rename
    — a crash mid-write can no longer leave a truncated/corrupt config.
    """
    import tempfile

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(path) or ".", prefix=os.path.basename(path) + ".",
        suffix=".tmp", text=True,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def dotted_get(cfg, key):
    """Walk a dotted key path (``a.b.c``) through nested dicts.

    Returns ``None`` when any segment is missing.
    """
    val = cfg
    for k in key.split("."):
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return None
    return val


def dotted_set(cfg, key, value):
    """Set a dotted key path, creating intermediate dicts as needed."""
    keys = key.split(".")
    d = cfg
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def dotted_exists(cfg, key):
    """Return True iff every segment of the dotted key exists."""
    val = cfg
    for k in key.split("."):
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return False
    return True


def dotted_remove(cfg, key):
    """Remove a dotted key (no-op if missing)."""
    keys = key.split(".")
    d = cfg
    for k in keys[:-1]:
        if not isinstance(d, dict) or k not in d:
            return
        d = d[k]
    if isinstance(d, dict):
        d.pop(keys[-1], None)


# ── Text helpers ──────────────────────────────────────────────
def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    """Write text atomically (ISSUE-014: tmp file + rename on same filesystem)."""
    import tempfile

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(path) or ".", prefix=os.path.basename(path) + ".",
        suffix=".tmp", text=True,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Init-script generation (shared by all agent subclasses) ──
def write_init(init_path, agent_name, sourced_by, block):
    """Write an init script with a standard header.  Returns *init_path*."""
    with open(init_path, "w") as f:
        f.write("#!/usr/bin/env bash\n")
        f.write(f"# ── OpenViking integration for {agent_name} ──\n")
        f.write(f"# {sourced_by}\n")
        f.write("# Managed by huawei-cloud-openviking-agent-integration skill.\n\n")
        f.write(block)
    os.chmod(init_path, 0o755)
    return init_path


def source_block(shared_dir, init_filename, extra=""):
    """Return the source-block string for template insertion."""
    _marker = os.environ.get(
        "OV_MARKER", "added by huawei-cloud-openviking-agent-integration skill"
    )
    lines = [
        f"# ── OpenViking integration ({_marker}) ──",
    ]
    if extra:
        lines.append(extra)
    lines.append(f"source {shared_dir}/{init_filename}")
    if extra:
        lines.append("set -e")
    lines.append("# ── End OpenViking integration ──")
    lines.append("")
    return "\n".join(lines) + "\n"
