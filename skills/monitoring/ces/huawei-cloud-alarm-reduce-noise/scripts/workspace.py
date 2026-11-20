#!/usr/bin/env python3
"""
Workspace directory manager for alarm-reduce-noise.

Provides a timestamped output directory under /root/workspace/.
All scripts in one run share the same directory via ALARM_REDUCE_NOISE_WORKSPACE_DIR env var.

Auto-reuse: when the env var is NOT set, get_workspace_dir() looks for the most recent
existing workspace that already contains core_instances.json (i.e. a prior
generate_instance.py run).  This lets single commands from the SKILL.md Commands
table run in sequence without manually exporting the env var:

    python3 scripts/generate_instance.py   # creates new workspace, writes core_instances.json
    python3 scripts/alarm.py --days 7      # auto-finds the workspace above
    python3 scripts/analyze_alarm.py       # auto-finds the same workspace

If no prior workspace with core_instances.json exists, a new timestamped directory
is created (same as before — for the first command in a pipeline).

Directory layout:
  <WORKSPACE_DIR>/               — output files (alarm_result.json, alarm-noise-report.html, etc.)
"""

import os
from datetime import datetime
from pathlib import Path

BASE_DIR = "/root/workspace"
DIR_PREFIX = "alarm-reduce-noise-workspace"


def _find_recent_workspace() -> str | None:
    """Find the most recent workspace directory that contains core_instances.json.

    Scans BASE_DIR for directories matching DIR_PREFIX_*, sorted newest-first by
    the timestamp embedded in the directory name.  Returns the first one that
    contains core_instances.json, or None if no suitable workspace is found.
    """
    base = Path(BASE_DIR)
    if not base.is_dir():
        return None

    # Sort by mtime (newest first), NOT by name — directory names with
    # extra prefixes (e.g. "pr1006_cross_...") can sort after plain timestamps
    # despite being older.
    candidates = sorted(
        (d for d in base.iterdir()
         if d.is_dir() and d.name.startswith(f"{DIR_PREFIX}_")),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    for d in candidates:
        if (d / "core_instances.json").exists():
            return str(d)
    return None


def get_workspace_dir() -> str:
    """
    Get the workspace directory for this run.

    Resolution order:
      1. ALARM_REDUCE_NOISE_WORKSPACE_DIR env var (explicit, shared across scripts).
      2. Most recent existing workspace that contains core_instances.json (auto-reuse).
      3. New timestamped directory (first command in a fresh pipeline).
    """
    ws = os.environ.get("ALARM_REDUCE_NOISE_WORKSPACE_DIR")
    if ws:
        Path(ws).mkdir(parents=True, exist_ok=True)
        return ws

    # Auto-reuse: find the most recent workspace with core_instances.json
    recent = _find_recent_workspace()
    if recent:
        return recent

    # No prior workspace found — create a new one
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ws = str(Path(BASE_DIR) / f"{DIR_PREFIX}_{timestamp}")
    Path(ws).mkdir(parents=True, exist_ok=True)
    return ws


WORKSPACE_DIR = get_workspace_dir()
