#!/usr/bin/env python3
"""hcloud CLI wrapper: parallel execution, JSON parsing, fault tolerance."""

import json
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)


def run_hcloud(args: list[str], region: str | None = None, timeout: int = 60, hcloud_cmd: str = "hcloud") -> dict[str, Any]:
    """Execute a single hcloud command, return parsed JSON dict.

    On failure, returns {"_error": str} instead of raising, ensuring caller fault tolerance.
    """
    cmd = [hcloud_cmd]
    if region:
        cmd += [f"--region={region}"]
    cmd += args
    cmd_str = " ".join(cmd)
    logger.debug("hcloud exec: %s", cmd_str)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=False
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip()
            logger.warning("hcloud failed (%s): %s", cmd_str, err[:200])
            return {"_error": err[:500]}
        text = result.stdout.strip()
        if not text:
            return {}
        # Try JSON parsing
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # hcloud sometimes outputs non-JSON messages
            return {"_raw": text, "_error": "non-json output"}
    except subprocess.TimeoutExpired:
        logger.warning("hcloud timeout: %s", cmd_str)
        return {"_error": f"timeout after {timeout}s"}
    except FileNotFoundError:
        return {"_error": f"{hcloud_cmd} not found in PATH"}
    except Exception as e:
        logger.warning("hcloud unexpected error: %s -> %s", cmd_str, e)
        return {"_error": str(e)}


def run_hcloud_json(args: list[str], region: str | None = None, timeout: int = 60, hcloud_cmd: str = "hcloud") -> dict[str, Any]:
    """Same as run_hcloud, but forces --cli-output json."""
    args = args + ["--cli-output=json"]
    return run_hcloud(args, region, timeout, hcloud_cmd)


def parallel_execute(
    tasks: list[dict[str, Any]],
    max_workers: int = 10,
    hcloud_cmd: str = "hcloud",
    default_timeout: int = 60,
) -> list[dict[str, Any]]:
    """Execute multiple hcloud tasks in parallel.

    Each task dict:
      - "args": list[str]       hcloud arguments
      - "region": str|None      region
      - "key": str              task identifier (for logging)
      - "timeout": int          per-task timeout (optional, default default_timeout)
      - other fields preserved as-is in result

    Returns list, each result is the original task dict with a "result" field appended.
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {}
        for task in tasks:
            args = task["args"]
            region = task.get("region")
            use_json = task.get("json_output", True)
            timeout = task.get("timeout", default_timeout)
            if use_json:
                future = pool.submit(run_hcloud_json, args, region, timeout, hcloud_cmd)
            else:
                future = pool.submit(run_hcloud, args, region, timeout, hcloud_cmd)
            future_map[future] = task
        for future in as_completed(future_map):
            task = future_map[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"_error": str(e)}
            r = dict(task)
            r["result"] = result
            results.append(r)
    return results


def check_hcloud(hcloud_cmd: str = "hcloud") -> bool:
    """Check if hcloud is available."""
    try:
        r = subprocess.run(
            [hcloud_cmd, "version"], capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except Exception:
        return False
