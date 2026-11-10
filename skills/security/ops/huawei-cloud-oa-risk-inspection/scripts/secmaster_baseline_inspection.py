#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fetch Huawei Cloud SecMaster baseline inspection results for the whole account.

Overview:
    Invoke the hcloud CLI tool to scan every SecMaster region defined by the
    built-in region list, enumerate every workspace (instance) in each region,
    pull all baseline inspection results from every instance, then group and
    count them client-side by fields such as severity and handle_status, and
    write the output to JSON files.

Detailed Description:
    The script depends only on the Python standard library
    (subprocess/json/argparse/threading etc.) and introduces no third-party
    dependencies; the hcloud CLI must be installed and configured in advance.
    The account workspace does not subscribe to the Dataspace feature, so the
    monitoring statistics commands (ShowMonitorStats / ShowMoniterMetricStats)
    are unavailable; instead the script pulls all baseline inspection results
    and performs its own grouping and counting client-side.
    The scan scope is the built-in SECMASTER_REGIONS constant list, not a
    region list API: the list was transcribed from the SecMaster console, so a
    newly launched region is not covered until the constant is updated. Each
    entry carries a verified flag; a region marked unverified is still scanned,
    but its failure is reported as a warning instead of a collection failure.
    Every workspace returned by ListWorkspaces is inspected: SearchBaseline
    requires a workspace_id and returns results for exactly one instance, so
    the script iterates all workspaces and merges their baseline results.
    Every SecMaster hcloud call passes through one shared sliding-window rate
    limiter, because the gateway rejects bursts with a throttling error.
    The full-results output document records the scan scope in a meta block
    (per-region and per-instance status plus failure counts), the workspace
    metadata (id + name + region_id) at the top level and keeps every baseline
    result under the data array; each result's data_object carries its own
    workspace_id so downstream consumers can trace it back to the instance.
    Early versions included the compliance package / check item metadata
    pipeline (SearchCompliancePackages, SearchCheckitems, etc.); remote
    testing confirmed that their return values cannot be correlated with
    baseline results, so that pipeline has been removed.

Workflow:
    1. Parse the command-line arguments (rate limit, retries, timeout, log).
    2. Scan every region in the built-in list: call ListWorkspaces with a
       bounded retry, recording each region as ok / no_workspace / failed /
       unverified_failed.
    3. Call SearchBaseline per workspace, paginating to pull all baseline
       inspection results and merging them across regions and instances. A
       workspace whose pagination fails has its partial result discarded and
       is recorded as failed; the remaining workspaces continue.
    4. Group and count by fields such as severity and handle_status.
    5. Write the full data (with meta and workspace metadata) and the
       statistics to JSON files.
    6. Return 0 when at least one instance was inspected, 1 when every
       verified region succeeded and the account holds no instance, and 2 for
       any other incomplete result.

Dependencies:
    - hcloud CLI tool (with authentication configured).
    - Python 3.8+ standard library.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
import time
from collections import Counter, deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional, Tuple

# Page size. ListWorkspaces accepts a limit in the range 1~100
# (Min.: 1; max.: 100); use 100 so that every paginated command passes the limit.
PAGE_LIMIT = 100
# Default timeout in seconds for each hcloud subprocess call.
DEFAULT_TIMEOUT = 300
# Default number of SecMaster hcloud calls allowed per second. The gateway
# throttles bursts above roughly two ListWorkspaces calls per second.
DEFAULT_RATE_LIMIT = 2
# Default retry count for a failing ListWorkspaces call.
DEFAULT_MAX_RETRIES = 1
# Length of the sliding window used by the rate limiter, in seconds.
RATE_WINDOW_SECONDS = 1.0
# Chinese language header required by the SearchBaseline command.
X_LANGUAGE = "zh-cn"
# Output files are written next to the script with a shared timestamp.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASELINE_FULL = "secmaster_baseline_inspection_results_{ts}.json"
OUTPUT_STATS = "secmaster_baseline_inspection_stats_{ts}.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"
# Field names used by the full-results output document.
META_KEY = "meta"
WORKSPACES_KEY = "workspaces"
DATA_KEY = "data"
# Region status values recorded in meta.regions.
REGION_STATUS_OK = "ok"
REGION_STATUS_NO_WORKSPACE = "no_workspace"
REGION_STATUS_FAILED = "failed"
REGION_STATUS_UNVERIFIED_FAILED = "unverified_failed"
# Instance status values recorded in meta.instances.
INSTANCE_STATUS_INSPECTED = "inspected"
INSTANCE_STATUS_FAILED = "failed"
# Built-in SecMaster region list transcribed from the SecMaster console.
# Each entry is (region_id, display name, verified). A region marked False is
# known to be unreachable or long-term unavailable; its failure is logged as a
# warning and excluded from the failure count that drives the exit code.
SECMASTER_REGIONS: List[Tuple[str, str, bool]] = [
    ("cn-north-4", "华北-北京四", True),
    ("cn-north-9", "华北-乌兰察布一", True),
    ("cn-north-11", "华北三", False),
    ("cn-east-2", "华东-上海一", True),
    ("cn-east-4", "华东-青岛", True),
    ("cn-east-3", "华东二", True),
    ("cn-south-1", "华南-广州", True),
    ("cn-southwest-2", "西南-贵阳一", True),
    ("ap-southeast-5", "中国-香港", True),
    ("ap-southeast-2", "亚太-曼谷", True),
    ("ap-southeast-1", "亚太-新加坡", True),
    ("ap-southeast-3", "亚太-马尼拉", True),
    ("me-east-1", "中东-利雅得", False),
    ("af-north-1", "非洲-开罗", True),
    ("af-south-1", "非洲-约翰内斯堡", True),
    ("la-south-2", "拉美-墨西哥城二", True),
]
# Module-level logger used to record progress, warnings and errors
# (console output is uniformly in English).
logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window limiter for hcloud calls.

    1. Keep the timestamps of the calls made inside the current window.
    2. Drop timestamps that have slid out of the window before each decision.
    3. Block until the earliest remaining timestamp leaves the window when the
       allowance is exhausted, then record the new call.

    A fixed sleep between calls is not used because it still allows bursts at
    window boundaries (t=0.0, 0.5, 1.0 all fall inside one second).
    """

    def __init__(self, rate: int, window_seconds: float = RATE_WINDOW_SECONDS) -> None:
        """Initialize the limiter state.

        1. Validate that the rate is at least one call per window.
        2. Create an empty timestamp queue and the lock guarding it.

        Args:
            rate: int — Maximum number of calls allowed per window.
            window_seconds: float — Length of the sliding window in seconds.

        Raises:
            ValueError: rate is lower than 1.

        Examples:
            # >>> limiter = RateLimiter(rate=2)
        """
        if rate < 1:
            raise ValueError("rate must be >= 1")
        self._rate = rate
        self._window = window_seconds
        self._timestamps: Deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a call slot is available, then consume it.

        1. Lock the timestamp queue and drop timestamps older than the window.
        2. Record the current time and return when the allowance is not full.
        3. Otherwise compute the wait until the earliest timestamp expires,
           release the lock and sleep, then retry.

        Args:
            None

        Returns:
            None

        Examples:
            # >>> RateLimiter(rate=2).acquire()
        """
        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._rate:
                    self._timestamps.append(now)
                    return
                wait_seconds = self._timestamps[0] + self._window - now
            if wait_seconds > 0:
                time.sleep(wait_seconds)


def setup_logging(log_file: Optional[str]) -> None:
    """Set up the logging framework.

    1. Configure the root logger level to INFO.
    2. Add a stderr StreamHandler.
    3. Add a FileHandler when log_file is provided.

    Args:
        log_file: Optional[str] — Path for file logging, or None for stderr
            only.

    Returns:
        None

    Examples:
        # >>> setup_logging(None)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s"
    )
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def run_hcloud_command(args: List[str], timeout: int = DEFAULT_TIMEOUT,
                       rate_limiter: Optional[RateLimiter] = None) -> Dict[str, Any]:
    """Run an hcloud command and parse its JSON output.

    1. Consume one rate limiter slot when a limiter is supplied.
    2. Invoke hcloud via subprocess, passing the full argument list.
    3. Check the return code and raise an exception on failure (with the raw stderr).
    4. Parse stdout as JSON, raising an exception on failure (with the raw output).

    Args:
        args: List[str] — Full hcloud command arguments (excluding the executable name).
        timeout: int — Timeout in seconds for the subprocess call.
        rate_limiter: Optional[RateLimiter] — Shared limiter for SecMaster calls,
            or None to call without throttling.

    Returns:
        Dict[str, Any]: The parsed JSON object.

    Raises:
        RuntimeError: hcloud returned a non-zero exit code, or the output could not be parsed as JSON.

    Examples:
        # >>> run_hcloud_command(["SecMaster", "ListWorkspaces", "--help"])
    """
    if rate_limiter is not None:
        rate_limiter.acquire()
    cmd = ["hcloud"] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "hcloud command not found. Make sure the hcloud CLI is installed and "
            "configured."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "hcloud command timed out after {} seconds.".format(timeout)
        ) from exc
    if proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "(no output)"
        raise RuntimeError(f"hcloud command failed (exit code {proc.returncode}): {detail}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"hcloud output is not valid JSON. Raw output: {proc.stdout[:2000]}"
        ) from exc


def list_workspaces(region_id: str, timeout: int = DEFAULT_TIMEOUT,
                    rate_limiter: Optional[RateLimiter] = None) -> List[Dict[str, Any]]:
    """Get the list of workspaces in one region (paginated).

    1. Assemble the ListWorkspaces command arguments.
    2. Paginate through all workspaces based on the count field.

    Args:
        region_id: str — Region ID, e.g. cn-north-4.
        timeout: int — Timeout in seconds for each subprocess call.
        rate_limiter: Optional[RateLimiter] — Shared limiter for SecMaster calls.

    Returns:
        List[Dict[str, Any]]: The list of workspaces.

    Examples:
        # >>> list_workspaces("cn-north-4")
    """
    return _fetch_with_pagination(
        ["SecMaster", "ListWorkspaces", f"--cli-region={region_id}"],
        count_field="count",
        list_field="workspaces",
        timeout=timeout,
        rate_limiter=rate_limiter,
    )


def search_baseline(region_id: str, workspace_id: str, timeout: int = DEFAULT_TIMEOUT,
                    rate_limiter: Optional[RateLimiter] = None) -> List[Dict[str, Any]]:
    """Fetch all baseline inspection results of one workspace (paginated).

    1. Assemble the SearchBaseline command arguments (language header and workspace).
    2. Paginate through all results based on the total count field.

    Args:
        region_id: str — Region ID.
        workspace_id: str — Workspace ID.
        timeout: int — Timeout in seconds for each subprocess call.
        rate_limiter: Optional[RateLimiter] — Shared limiter for SecMaster calls.

    Returns:
        List[Dict[str, Any]]: The baseline inspection results (each containing a data_object).

    Examples:
        # >>> search_baseline("cn-north-4", "ws-id")
    """
    command_args = [
        "SecMaster",
        "SearchBaseline",
        f"--cli-region={region_id}",
        f"--X-Language={X_LANGUAGE}",
        f"--workspace_id={workspace_id}",
    ]
    return _fetch_with_pagination(
        command_args,
        count_field="total",
        list_field="data",
        timeout=timeout,
        rate_limiter=rate_limiter,
    )


def build_workspace_metadata(workspaces: List[Dict[str, Any]],
                             region_id: str = "") -> List[Dict[str, Any]]:
    """Build the workspace metadata list carried by the full-results output.

    1. Iterate over the workspace objects returned by ListWorkspaces.
    2. Keep the id, name and region_id fields of each workspace.

    Args:
        workspaces: List[Dict[str, Any]] — The workspaces returned by
            ListWorkspaces.
        region_id: str — Region the workspaces were listed from; used as the
            fallback when a workspace object omits its own region_id.

    Returns:
        List[Dict[str, Any]]: Workspace metadata entries, each with id, name
            and region_id fields.

    Examples:
        # >>> build_workspace_metadata([{"id": "ws-1", "name": "test"}], "cn-north-4")
        [{'id': 'ws-1', 'name': 'test', 'region_id': 'cn-north-4'}]
    """
    metadata: List[Dict[str, Any]] = []
    for ws in workspaces or []:
        metadata.append({
            "id": ws.get("id", "") or "",
            "name": ws.get("name", "") or "",
            "region_id": ws.get("region_id", "") or region_id,
        })
    return metadata


def _fetch_with_pagination(
    command_args: List[str],
    count_field: str,
    list_field: str,
    timeout: int = DEFAULT_TIMEOUT,
    rate_limiter: Optional[RateLimiter] = None,
) -> List[Dict[str, Any]]:
    """Paginate and aggregate all records based on a count field.

    1. Start at offset=0, with each page limited to PAGE_LIMIT.
    2. Parse the count field and the records array field of each page response.
    3. Loop until offset reaches the count field value, aggregating records across all pages.

    Args:
        command_args: List[str] — hcloud command arguments except limit/offset.
        count_field: str — Field name in the response that holds the total record count (count or total).
        list_field: str — Field name in the response that holds the records array.
        timeout: int — Timeout in seconds for each subprocess call.
        rate_limiter: Optional[RateLimiter] — Shared limiter for SecMaster calls.

    Returns:
        List[Dict[str, Any]]: All records aggregated after pagination.

    Raises:
        RuntimeError: A page request failed; the caller decides whether to
            discard the partial result of the whole workspace.

    Examples:
        # >>> _fetch_with_pagination(["SecMaster", "ListWorkspaces"], "count", "workspaces")
    """
    all_records: List[Dict[str, Any]] = []
    offset = 0
    while True:
        page_args = command_args + [f"--limit={PAGE_LIMIT}", f"--offset={offset}"]
        response = run_hcloud_command(page_args, timeout, rate_limiter)
        total_count = int(response.get(count_field, 0))
        records = response.get(list_field, [])
        if isinstance(records, list):
            all_records.extend(records)
        if total_count == 0 or offset + PAGE_LIMIT >= total_count:
            break
        offset += PAGE_LIMIT
    return all_records


def compute_statistics(baseline_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Group and count baseline inspection results by severity, handle_status, etc.

    1. Iterate over the data_object of each record and extract severity and handle_status.
    2. Count by severity, handle_status, their cross combination, and compliance_package_id.
    3. Aggregate into a statistics dictionary (missing fields fall back to "unknown").

    Args:
        baseline_results: List[Dict[str, Any]] — The records returned by SearchBaseline.

    Returns:
        Dict[str, Any]: Grouped statistics, including total (number of valid records
            counted), severity, handle_status, severity_handle_status, and
            compliance_package_id counts.

    Examples:
        # >>> compute_statistics([{"data_object": {"severity": "Low", "handle_status": "risk"}}])
        # {'total': 1, 'severity': {'Low': 1}, 'handle_status': {'risk': 1}, 'severity_handle_status': {'Low|risk': 1}, 'compliance_package_id': {'unknown': 1}}
    """
    severity_counter: Counter[str] = Counter()
    handle_status_counter: Counter[str] = Counter()
    cross_counter: Counter[str] = Counter()
    package_counter: Counter[str] = Counter()
    counted_records = 0
    for record in baseline_results:
        data_object = record.get("data_object", {})
        if not isinstance(data_object, dict):
            continue
        counted_records += 1
        severity = data_object.get("severity", "unknown") or "unknown"
        handle_status = data_object.get("handle_status", "unknown") or "unknown"
        package_id = (
            data_object.get("compliance_package_id", "unknown") or "unknown"
        )
        severity_counter[severity] += 1
        handle_status_counter[handle_status] += 1
        cross_counter[f"{severity}|{handle_status}"] += 1
        package_counter[package_id] += 1
    return {
        "total": counted_records,
        "severity": dict(sorted(severity_counter.items())),
        "handle_status": dict(sorted(handle_status_counter.items())),
        "severity_handle_status": dict(sorted(cross_counter.items())),
        "compliance_package_id": dict(sorted(package_counter.items())),
    }


def write_json_file(file_path: str, data: Any) -> None:
    """Write data to a JSON file.

    1. Serialize the data as UTF-8 with ensure_ascii=False.
    2. Write to the specified path.

    Args:
        file_path: str — Path of the output file.
        data: Any — The data object to write.

    Returns:
        None

    Examples:
        # >>> write_json_file("out.json", {"a": 1})
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_workspaces_with_retry(
    region_id: str,
    verified: bool,
    timeout: int,
    max_retries: int,
    rate_limiter: Optional[RateLimiter],
) -> Tuple[List[Dict[str, Any]], str, str]:
    """List the workspaces of one region with a bounded retry.

    1. Call ListWorkspaces and return immediately on success, classifying an
       empty result as no_workspace.
    2. Retry the call up to max_retries times while it keeps failing.
    3. After the last failure, classify the region as failed when it is
       verified and as unverified_failed otherwise.

    Args:
        region_id: str — Region ID to query.
        verified: bool — Whether the region is marked verified in the built-in list.
        timeout: int — Timeout in seconds for each subprocess call.
        max_retries: int — Number of retries after the first failed attempt.
        rate_limiter: Optional[RateLimiter] — Shared limiter for SecMaster calls.

    Returns:
        Tuple[List[Dict[str, Any]], str, str]: The workspaces, the region status
            and the last error message (empty on success).

    Examples:
        # >>> workspaces, status, error = fetch_workspaces_with_retry("cn-north-4", True, 300, 1, None)
    """
    attempts = max_retries + 1
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            workspaces = list_workspaces(region_id, timeout, rate_limiter)
        except RuntimeError as exc:
            last_error = str(exc)
            if attempt < attempts:
                logger.warning(
                    "ListWorkspaces failed in region %s (attempt %d/%d), retrying: %s",
                    region_id, attempt, attempts, last_error,
                )
            continue
        if not workspaces:
            return [], REGION_STATUS_NO_WORKSPACE, ""
        return workspaces, REGION_STATUS_OK, ""
    status = REGION_STATUS_FAILED if verified else REGION_STATUS_UNVERIFIED_FAILED
    return [], status, last_error


def scan_all_regions(
    timeout: int,
    max_retries: int,
    rate_limiter: Optional[RateLimiter],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Scan every region in the built-in list and pull all baseline results.

    1. Iterate over SECMASTER_REGIONS and list the workspaces of each region
       with a bounded retry.
    2. Record every region's status and workspace count, and log failures at
       ERROR for verified regions and WARNING for unverified ones.
    3. For every workspace, pull its baseline results; on failure discard the
       partial result and record the instance as failed, then continue.
    4. Return the merged baseline results, the region status list and the
       instance status list.

    Args:
        timeout: int — Timeout in seconds for each subprocess call.
        max_retries: int — Retry count for a failing ListWorkspaces call.
        rate_limiter: Optional[RateLimiter] — Shared limiter for SecMaster calls.

    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
            The baseline results, the meta.regions entries and the
            meta.instances entries.

    Examples:
        # >>> results, regions, instances = scan_all_regions(300, 1, None)
    """
    baseline_results: List[Dict[str, Any]] = []
    region_entries: List[Dict[str, Any]] = []
    instance_entries: List[Dict[str, Any]] = []
    for index, (region_id, region_name, verified) in enumerate(SECMASTER_REGIONS, start=1):
        workspaces, status, error = fetch_workspaces_with_retry(
            region_id, verified, timeout, max_retries, rate_limiter
        )
        region_entries.append({
            "region_id": region_id,
            "region_name": region_name,
            "verified": verified,
            "status": status,
            "workspace_count": len(workspaces),
        })
        if status == REGION_STATUS_FAILED:
            logger.error(
                "Region %s (%s) is unreachable after %d attempt(s): %s",
                region_id, region_name, max_retries + 1, error,
            )
            continue
        if status == REGION_STATUS_UNVERIFIED_FAILED:
            logger.warning(
                "Unverified region %s (%s) is unreachable after %d attempt(s) "
                "and is excluded from the failure count: %s",
                region_id, region_name, max_retries + 1, error,
            )
            continue
        logger.info(
            "Region %d/%d %s (%s): %d workspace(s)",
            index, len(SECMASTER_REGIONS), region_id, region_name, len(workspaces),
        )
        for ws in workspaces:
            workspace_id = ws.get("id", "") or ""
            workspace_name = ws.get("name", "") or ""
            logger.info("Fetching baseline for workspace: %s (%s) in region %s",
                        workspace_name, workspace_id, region_id)
            try:
                results = search_baseline(region_id, workspace_id, timeout, rate_limiter)
            except RuntimeError as exc:
                logger.error(
                    "Baseline fetch failed for workspace %s (%s) in region %s; "
                    "discarding its partial result: %s",
                    workspace_name, workspace_id, region_id, exc,
                )
                instance_entries.append({
                    "id": workspace_id,
                    "name": workspace_name,
                    "region_id": region_id,
                    "status": INSTANCE_STATUS_FAILED,
                })
                continue
            baseline_results.extend(results)
            instance_entries.append({
                "id": workspace_id,
                "name": workspace_name,
                "region_id": region_id,
                "status": INSTANCE_STATUS_INSPECTED,
            })
    return baseline_results, region_entries, instance_entries


def build_meta(region_entries: List[Dict[str, Any]],
               instance_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the meta block describing the scan scope and its outcome.

    1. Count scanned, verified and unverified regions from the built-in list.
    2. Count failed regions by status and failed instances.
    3. Assemble the meta document with the per-region and per-instance entries.

    Args:
        region_entries: List[Dict[str, Any]] — The meta.regions entries.
        instance_entries: List[Dict[str, Any]] — The meta.instances entries.

    Returns:
        Dict[str, Any]: The meta block written to the full-results file.

    Examples:
        # >>> build_meta([], [])["scanned_regions"]
        16
    """
    failed_regions = sum(1 for r in region_entries if r.get("status") == REGION_STATUS_FAILED)
    unverified_failed = sum(
        1 for r in region_entries if r.get("status") == REGION_STATUS_UNVERIFIED_FAILED
    )
    failed_instances = sum(
        1 for i in instance_entries if i.get("status") == INSTANCE_STATUS_FAILED
    )
    return {
        "scanned_regions": len(SECMASTER_REGIONS),
        "verified_regions": sum(1 for r in SECMASTER_REGIONS if r[2]),
        "unverified_regions": sum(1 for r in SECMASTER_REGIONS if not r[2]),
        "regions": region_entries,
        "instances": instance_entries,
        "failed_regions": failed_regions,
        "unverified_failed_regions": unverified_failed,
        "failed_instances": failed_instances,
    }


def compute_exit_code(instance_entries: List[Dict[str, Any]],
                      failed_regions: int) -> int:
    """Derive the process exit code from the scan outcome.

    1. Return 0 when at least one instance was inspected.
    2. Return 1 when every verified region succeeded and no instance exists.
    3. Return 2 for any other incomplete result.

    Args:
        instance_entries: List[Dict[str, Any]] — The meta.instances entries.
        failed_regions: int — Number of failed verified regions.

    Returns:
        int: 0 on success, 1 when the account holds no instance, 2 otherwise.

    Examples:
        # >>> compute_exit_code([], 0)
        1
        # >>> compute_exit_code([{"status": "inspected"}], 1)
        0
    """
    inspected = sum(
        1 for i in instance_entries if i.get("status") == INSTANCE_STATUS_INSPECTED
    )
    if inspected > 0:
        return 0
    if failed_regions == 0 and not instance_entries:
        return 1
    return 2


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    1. Define the optional rate limit, retry, timeout and log file options.
    2. Do not define any region option: the scan scope is the built-in list.

    Args:
        argv: List[str] — Command-line arguments (excluding the script name).

    Returns:
        argparse.Namespace: The parsed result, containing the optional settings.

    Examples:
        # >>> parse_args([]).rate_limit
        2
    """
    parser = argparse.ArgumentParser(
        prog="secmaster_baseline_inspection",
        description=(
            "Fetch Huawei Cloud SecMaster baseline inspection results for every "
            "workspace in the built-in region list and output statistics."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Optional. Timeout in seconds for each hcloud subprocess call (default: %(default)s).",
    )
    parser.add_argument(
        "--rate-limit",
        dest="rate_limit",
        type=int,
        default=DEFAULT_RATE_LIMIT,
        help=(
            "Optional. Maximum SecMaster hcloud calls per second, applied to "
            "ListWorkspaces and SearchBaseline through one shared limiter "
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--max-retries",
        dest="max_retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Optional. Retry count for a failing ListWorkspaces call (default: %(default)s).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional. Path to a log file; logs are appended to stderr as well.",
    )
    return parser.parse_args(argv)


def _resolve_output_paths(timestamp: str) -> Tuple[str, str]:
    """Resolve the absolute paths of the two output JSON files.

    1. Join the script directory with the timestamped file names.
    2. Return the absolute paths.

    Args:
        timestamp: str — Formatted timestamp string shared by both files.

    Returns:
        Tuple[str, str]: The absolute paths of the full baseline results
            file and the statistics file.

    Examples:
        # >>> full, stats = _resolve_output_paths("2026_10_12_14_30_00")
        # >>> full.endswith("secmaster_baseline_inspection_results_2026_10_12_14_30_00.json")
        True
    """
    full_path = os.path.abspath(os.path.join(
        SCRIPT_DIR, OUTPUT_BASELINE_FULL.format(ts=timestamp)))
    stats_path = os.path.abspath(os.path.join(
        SCRIPT_DIR, OUTPUT_STATS.format(ts=timestamp)))
    return full_path, stats_path


def _log_scan_scope() -> None:
    """Log the built-in scan scope before the first hcloud call.

    1. Count verified and unverified regions in the built-in list.
    2. Log the totals and warn that a newly launched region is not covered
       until the constant is updated.

    Args:
        None

    Returns:
        None

    Examples:
        # >>> _log_scan_scope()
    """
    verified = sum(1 for r in SECMASTER_REGIONS if r[2])
    unverified = len(SECMASTER_REGIONS) - verified
    logger.info(
        "Scanning %d SecMaster region(s) from the built-in list "
        "(%d verified, %d unverified); a newly launched region is not covered "
        "until the list is updated.",
        len(SECMASTER_REGIONS), verified, unverified,
    )


def main(argv: List[str]) -> int:
    """Main script workflow.

    1. Parse the command-line arguments and resolve the output paths.
    2. Log the scan scope from the built-in region list.
    3. Scan every region and pull every instance's baseline results.
    4. Compute statistics, build the meta block and write the two JSON files.
    5. Return the exit code derived from the scan outcome: 0 when at least one
       instance was inspected, 1 when the account holds no instance, 2 when the
       result is incomplete.

    Args:
        argv: List[str] — Command-line arguments (excluding the script name).

    Returns:
        int: Process exit code (0 / 1 / 2).

    Examples:
        # >>> main([])
    """
    args = parse_args(argv)
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    full_path, stats_path = _resolve_output_paths(timestamp)

    setup_logging(args.log_file)
    logger.info("Task started. Output file(s): %s, %s", full_path, stats_path)

    rate_limiter = RateLimiter(args.rate_limit)
    _log_scan_scope()

    baseline_results, region_entries, instance_entries = scan_all_regions(
        args.timeout, args.max_retries, rate_limiter
    )
    meta = build_meta(region_entries, instance_entries)
    stats = compute_statistics(baseline_results)
    workspaces = [
        {"id": entry["id"], "name": entry["name"], "region_id": entry["region_id"]}
        for entry in instance_entries
        if entry["status"] == INSTANCE_STATUS_INSPECTED
    ]

    write_json_file(full_path, {
        META_KEY: meta,
        WORKSPACES_KEY: workspaces,
        DATA_KEY: baseline_results,
    })
    write_json_file(stats_path, stats)

    inspected = len(workspaces)
    logger.info(
        "Scan summary: %d region(s), %d instance(s) inspected, %d instance(s) failed, "
        "%d baseline result(s).",
        meta["scanned_regions"], inspected, meta["failed_instances"], stats["total"],
    )
    logger.info(
        "Region failures: %d verified, %d unverified.",
        meta["failed_regions"], meta["unverified_failed_regions"],
    )
    logger.info("Task finished. Output file(s): %s, %s", full_path, stats_path)

    exit_code = compute_exit_code(instance_entries, meta["failed_regions"])
    if exit_code == 1:
        logger.warning(
            "No SecMaster workspace was found in any verified region; the account "
            "holds no instance as far as the built-in region list can tell."
        )
    elif exit_code == 2:
        logger.error("The scan is incomplete; see the region and instance statuses above.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
