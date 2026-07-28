"""LTS log queries through hcloud for historical Kubernetes Event queries."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from . import common


def _timestamp(value: Optional[str], default: datetime) -> int:
    if not value:
        return int(default.timestamp() * 1000)
    if "-" in value:
        return int(datetime.strptime(value, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    return int(value)


def _parse_hcloud_json(output: str) -> Dict[str, Any]:
    text = (output or "").strip()
    return json.loads(text or "{}")


def _run_hcloud(cmd: list[str]) -> Dict[str, Any]:
    safe_cmd = common.redact_command(cmd)
    try:
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=75, check=False)
    except FileNotFoundError:
        return {"success": False, "error": "hcloud not found in PATH", "command": safe_cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "hcloud command timed out after 75 seconds", "command": safe_cmd}
    if completed.returncode:
        return {
            "success": False,
            "error": (completed.stderr or completed.stdout or f"hcloud exited with code {completed.returncode}")[:2000],
            "command": safe_cmd,
        }
    try:
        return {"success": True, "data": _parse_hcloud_json(completed.stdout)}
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "success": False,
            "error": f"hcloud response parsing failed: {exc}",
            "command": safe_cmd,
        }


def _hcloud_base_command(
    service: str,
    operation: str,
    region: str,
    ak: Optional[str],
    sk: Optional[str],
    project_id: Optional[str],
) -> list[str]:
    access_key, secret_key, resolved_project_id = common.resolve_hcloud_credentials(ak, sk, project_id)
    cmd = [
        "hcloud", service, operation, f"--cli-region={region}", "--cli-output=json",
        "--cli-connect-timeout=10", "--cli-read-timeout=60",
    ]
    if resolved_project_id:
        cmd.append(f"--cli-project-id={resolved_project_id}")
    if access_key:
        cmd.append(f"--cli-access-key={access_key}")
    if secret_key:
        cmd.append(f"--cli-secret-key={secret_key}")
    return cmd


def query_logs(
    region: str,
    log_group_id: str,
    log_stream_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    keywords: Optional[str] = None,
    limit: int = 1000,
    scroll_id: Optional[str] = None,
    ak: Optional[str] = None,
    sk: Optional[str] = None,
    project_id: Optional[str] = None,
    **_: Any,
) -> Dict[str, Any]:
    """Query one LTS stream through ``hcloud LTS ListLogs``."""
    now = datetime.now()
    cmd = _hcloud_base_command("LTS", "ListLogs", region, ak, sk, project_id)
    cmd.extend(
        [
        f"--log_group_id={log_group_id}",
        f"--log_stream_id={log_stream_id}",
        f"--start_time={_timestamp(start_time, now - timedelta(hours=1))}",
        f"--end_time={_timestamp(end_time, now)}",
        f"--limit={max(1, min(limit, 1000))}",
        "--is_desc=true",
        ]
    )
    if keywords:
        cmd.append(f"--keywords={keywords}")
    if scroll_id:
        cmd.append(f"--scroll_id={scroll_id}")

    query_result = _run_hcloud(cmd)
    if not query_result.get("success"):
        return query_result
    response = query_result["data"]

    logs = [
        {
            "content": item.get("content", ""),
            "timestamp": item.get("timestamp"),
            "log_group_id": log_group_id,
            "log_stream_id": log_stream_id,
        }
        for item in (response.get("logs") or [])
        if isinstance(item, dict)
    ]
    next_scroll_id = response.get("scroll_id")
    return {
        "success": True,
        "log_group_id": log_group_id,
        "log_stream_id": log_stream_id,
        "total": len(logs),
        "scroll_id": next_scroll_id,
        "has_more": bool(next_scroll_id),
        "logs": logs,
    }
