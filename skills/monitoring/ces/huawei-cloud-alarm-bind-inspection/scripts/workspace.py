#!/usr/bin/env python3
"""
Workspace directory manager for alarm-bind-inspection.

Provides a timestamped output directory under /root/workspace/.
All scripts in one run share the same directory via ALARM_WORKSPACE_DIR env var.

Directory layout:
  <WORKSPACE_DIR>/               — final output files (.xlsx, .html) for end users
  <WORKSPACE_DIR>/intermediate/  — intermediate JSON files passed between steps
"""

import os
from datetime import datetime
from pathlib import Path

BASE_DIR = "/root/workspace"
DIR_PREFIX = "alarm-bind-inspection-workspace"
INTERMEDIATE_SUBDIR = "intermediate"


def get_workspace_dir() -> str:
    """
    Get the workspace directory for this run.

    - If ALARM_WORKSPACE_DIR env var is set, use it (shared across scripts in one run).
    - Otherwise, create a new timestamped directory.
    """
    ws = os.environ.get("ALARM_WORKSPACE_DIR")
    if ws:
        Path(ws).mkdir(parents=True, exist_ok=True)
        return ws

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ws = str(Path(BASE_DIR) / f"{DIR_PREFIX}_{timestamp}")
    Path(ws).mkdir(parents=True, exist_ok=True)
    return ws


WORKSPACE_DIR = get_workspace_dir()

# Intermediate files go into a subdirectory to keep the workspace root clean.
INTERMEDIATE_DIR = str(Path(WORKSPACE_DIR) / INTERMEDIATE_SUBDIR)
Path(INTERMEDIATE_DIR).mkdir(parents=True, exist_ok=True)


def resolve_input_path(p: str) -> str:
    """Resolve a relative input path against the workspace directory.

    Tries <WORKSPACE_DIR>/p first, then <INTERMEDIATE_DIR>/p for bare filenames.
    Falls back to the original path if neither exists (e.g. absolute paths or
    files relative to CWD).

    Used by bind_analysis.py / event_bind_analysis.py for --baseline, --rules,
    --core, etc. SKILL.md documents usage like:
        --aom-baseline intermediate/aom_indicator_baseline.json
    which is relative to <WORKSPACE_DIR>, not the current working directory.
    """
    if not p or Path(p).is_absolute():
        return p
    resolved = str(Path(WORKSPACE_DIR) / p)
    if Path(resolved).exists():
        return resolved
    # also try relative to INTERMEDIATE_DIR for bare filenames
    resolved2 = str(Path(INTERMEDIATE_DIR) / p)
    if Path(resolved2).exists():
        return resolved2
    return p


def resolve_output_path(p: str) -> str:
    """Resolve a relative output path against the workspace directory.

    --output usually does not exist yet, so existence-based resolution would
    leave a relative path pointing at the CWD. Documented usage is
    workspace-relative (<WORKSPACE_DIR>/...), so always anchor it there.
    Parent directories are created as needed.
    """
    if not p or Path(p).is_absolute():
        return p
    out = Path(WORKSPACE_DIR) / p
    out.parent.mkdir(parents=True, exist_ok=True)
    return str(out)
