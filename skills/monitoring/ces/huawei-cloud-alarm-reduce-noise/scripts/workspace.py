#!/usr/bin/env python3
"""
Workspace directory manager for alarm-reduce-noise.

Provides a timestamped output directory under /root/workspace/.
All scripts in one run share the same directory via ALARM_REDUCE_NOISE_WORKSPACE_DIR env var.

Directory layout:
  <WORKSPACE_DIR>/               — output files (alarm_result.json, alarm-noise-report.html, etc.)
"""

import os
from datetime import datetime
from pathlib import Path

BASE_DIR = "/root/workspace"
DIR_PREFIX = "alarm-reduce-noise-workspace"


def get_workspace_dir() -> str:
    """
    Get the workspace directory for this run.

    - If ALARM_REDUCE_NOISE_WORKSPACE_DIR env var is set, use it (shared across scripts in one run).
    - Otherwise, create a new timestamped directory.
    """
    ws = os.environ.get("ALARM_REDUCE_NOISE_WORKSPACE_DIR")
    if ws:
        Path(ws).mkdir(parents=True, exist_ok=True)
        return ws

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ws = str(Path(BASE_DIR) / f"{DIR_PREFIX}_{timestamp}")
    Path(ws).mkdir(parents=True, exist_ok=True)
    return ws


WORKSPACE_DIR = get_workspace_dir()


# 核心资源标记表路径（相对于 scripts 目录的上级 assets 目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MARKING_TABLE_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "assets", "关键资源标记表.xlsx")
