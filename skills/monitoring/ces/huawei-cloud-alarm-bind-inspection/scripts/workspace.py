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
