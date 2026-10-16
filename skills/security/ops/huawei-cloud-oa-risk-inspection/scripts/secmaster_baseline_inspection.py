#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fetch all Huawei Cloud SecMaster baseline inspection results.

Overview:
    Invoke the hcloud CLI tool to start from a single region ID, derive
    project_id automatically, enumerate every SecMaster workspace (instance)
    in the region, pull all baseline inspection results from each workspace,
    then group and count them client-side by fields such as severity and
    handle_status, and write the output to JSON files.

Detailed Description:
    The script depends only on the Python standard library
    (subprocess/json/argparse etc.) and introduces no third-party
    dependencies; the hcloud CLI must be installed and configured in
    advance.
    The account workspace does not subscribe to the Dataspace feature, so
    the monitoring statistics commands (ShowMonitorStats /
    ShowMoniterMetricStats) are unavailable; instead the script pulls all
    baseline inspection results and performs its own grouping and counting
    client-side.
    Every workspace returned by ListWorkspaces is inspected: SearchBaseline
    requires a workspace_id and returns results for exactly one instance, so
    the script iterates all workspaces and merges their baseline results.
    The full-results output document records the workspace metadata
    (id + name) at the top level and keeps every baseline result under the
    data array; each result's data_object carries its own workspace_id so
    downstream consumers can trace it back to the instance.
    Early versions included the compliance package / check item metadata
    pipeline (SearchCompliancePackages, SearchCheckitems, etc.); remote
    testing confirmed that their return values cannot be correlated with
    baseline results, so that pipeline has been removed.

Workflow:
    1. Parse the command-line arguments (region ID).
    2. Verify that hcloud project_id is configured; abort with a prompt if not.
    3. Call ListWorkspaces to enumerate every workspace in the region.
    4. Call SearchBaseline per workspace, paginating to pull all baseline
       inspection results, and merge the results across workspaces.
    5. Group and count by fields such as severity and handle_status.
    6. Write the full data (with workspace metadata) and the statistics to
       JSON files.

Dependencies:
    - hcloud CLI tool (with authentication and project_id configured).
    - Python 3.8+ standard library.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Page size. ListWorkspaces accepts a limit in the range 1~100
# (Min.: 1; max.: 100); use 100 so that every paginated command passes the limit.
PAGE_LIMIT = 100
# Default timeout in seconds for each hcloud subprocess call.
DEFAULT_TIMEOUT = 300
# Chinese language header required by the SearchBaseline command.
X_LANGUAGE = "zh-cn"
# Output files are written next to the script with a shared timestamp.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASELINE_FULL = "secmaster_baseline_inspection_results_{ts}.json"
OUTPUT_STATS = "secmaster_baseline_inspection_stats_{ts}.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"
# Field names used by the full-results output document.
WORKSPACES_KEY = "workspaces"
DATA_KEY = "data"
# Module-level logger used to record progress, warnings and errors
# (console output is uniformly in English).
logger = logging.getLogger(__name__)


def setup_logging(log_file: str | None) -> None:
    """Set up the logging framework.

    1. Configure the root logger level to INFO.
    2. Add a stderr StreamHandler.
    3. Add a FileHandler when log_file is provided.

    Args:
        log_file: str | None — Path for file logging, or None for stderr
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


def run_hcloud_command(args: list[str], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    """Run an hcloud command and parse its JSON output.

    1. Invoke hcloud via subprocess, passing the full argument list.
    2. Check the return code and raise an exception on failure (with the raw stderr).
    3. Parse stdout as JSON, raising an exception on failure (with the raw output).

    Args:
        args: list[str] — Full hcloud command arguments (excluding the executable name).
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        dict[str, Any]: The parsed JSON object.

    Raises:
        RuntimeError: hcloud returned a non-zero exit code, or the output could not be parsed as JSON.

    Examples:
        # >>> run_hcloud_command(["SecMaster", "ListWorkspaces", "--help"])
    """
    cmd = ["hcloud"] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "hcloud command not found. Make sure the hcloud CLI is installed and "
            "configured."
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


def list_workspaces(region_id: str, timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    """Get the list of workspaces (paginated).

    1. Assemble the ListWorkspaces command arguments.
    2. Paginate through all workspaces based on the count field.

    Args:
        region_id: str — Region ID, e.g. cn-north-4.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        list[dict[str, Any]]: The list of workspaces.

    Examples:
        # >>> list_workspaces("cn-north-4")
    """
    return _fetch_with_pagination(
        ["SecMaster", "ListWorkspaces", f"--cli-region={region_id}"],
        count_field="count",
        list_field="workspaces",
        timeout=timeout,
    )


def search_baseline(region_id: str, workspace_id: str,
                    timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    """Fetch all baseline inspection results (paginated).

    1. Assemble the SearchBaseline command arguments (language header and workspace).
    2. Paginate through all results based on the total count field.

    Args:
        region_id: str — Region ID.
        workspace_id: str — Workspace ID.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        list[dict[str, Any]]: The baseline inspection results (each containing a data_object).

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
    )


def build_workspace_metadata(workspaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the workspace metadata list carried by the full-results output.

    1. Iterate over the workspace objects returned by ListWorkspaces.
    2. Keep only the id and name fields of each workspace.

    Args:
        workspaces: list[dict[str, Any]] — The workspaces returned by
            ListWorkspaces.

    Returns:
        list[dict[str, Any]]: Workspace metadata entries, each with id and
            name fields.

    Examples:
        >>> build_workspace_metadata([{"id": "ws-1", "name": "test", "region_id": "cn-north-4"}])
        [{'id': 'ws-1', 'name': 'test'}]
    """
    metadata: list[dict[str, Any]] = []
    for ws in workspaces or []:
        metadata.append({
            "id": ws.get("id", "") or "",
            "name": ws.get("name", "") or "",
        })
    return metadata


def _fetch_with_pagination(
    command_args: list[str],
    count_field: str,
    list_field: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """Paginate and aggregate all records based on a count field.

    1. Start at offset=0, with each page limited to PAGE_LIMIT.
    2. Parse the count field and the records array field of each page response.
    3. Loop until offset reaches the count field value, aggregating records across all pages.

    Args:
        command_args: list[str] — hcloud command arguments except limit/offset.
        count_field: str — Field name in the response that holds the total record count (count or total).
        list_field: str — Field name in the response that holds the records array.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        list[dict[str, Any]]: All records aggregated after pagination.

    Examples:
        # >>> _fetch_with_pagination(["SecMaster", "ListWorkspaces"], "count", "workspaces")
    """
    all_records: list[dict[str, Any]] = []
    offset = 0
    while True:
        page_args = command_args + [f"--limit={PAGE_LIMIT}", f"--offset={offset}"]
        response = run_hcloud_command(page_args, timeout)
        total_count = int(response.get(count_field, 0))
        records = response.get(list_field, [])
        if isinstance(records, list):
            all_records.extend(records)
        if total_count == 0 or offset + PAGE_LIMIT >= total_count:
            break
        offset += PAGE_LIMIT
    return all_records


def compute_statistics(baseline_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Group and count baseline inspection results by severity, handle_status, etc.

    1. Iterate over the data_object of each record and extract severity and handle_status.
    2. Count by severity, handle_status, their cross combination, and compliance_package_id.
    3. Aggregate into a statistics dictionary (missing fields fall back to "unknown").

    Args:
        baseline_results: list[dict[str, Any]] — The records returned by SearchBaseline.

    Returns:
        dict[str, Any]: Grouped statistics, including total (number of valid records
            counted), severity, handle_status, severity_handle_status, and
            compliance_package_id counts.

    Examples:
        >>> compute_statistics([{"data_object": {"severity": "Low", "handle_status": "risk"}}])
        {'total': 1, 'severity': {'Low': 1}, 'handle_status': {'risk': 1}, 'severity_handle_status': {'Low|risk': 1}, 'compliance_package_id': {'unknown': 1}}
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


def check_project_id_configured(region_id: str,
                                timeout: int = DEFAULT_TIMEOUT) -> None:
    """Verify that hcloud project_id is configured; abort with a prompt if not.

    1. Probe whether project_id can be resolved via IAM KeystoneListProjects.
    2. Raise an exception with guidance if the call fails or returns no projects.

    Args:
        region_id: str — Region ID.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        None

    Raises:
        RuntimeError: Raised with guidance when project_id cannot be resolved.

    Examples:
        # >>> check_project_id_configured("cn-north-4")
    """
    command_args = ["IAM", "KeystoneListProjects", f"--cli-region={region_id}"]
    try:
        response = run_hcloud_command(command_args, timeout)
    except RuntimeError as exc:
        raise RuntimeError(
            "Could not resolve the hcloud project_id. Run `hcloud configure` or "
            f"`hcloud IAM KeystoneListProjects --cli-region={region_id}` to "
            "verify authentication and project configuration, then re-run the "
            "script."
        ) from exc
    projects = response.get("projects", []) if isinstance(response, dict) else []
    if not projects:
        raise RuntimeError(
            "Could not resolve the hcloud project_id: no project found in the "
            f"given region. Verify the project configuration with "
            f"`hcloud IAM KeystoneListProjects --cli-region={region_id}`."
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    1. Define the required option region_id.
    2. Define the optional timeout and log file options.

    Args:
        argv: list[str] — Command-line arguments (excluding the script name).

    Returns:
        argparse.Namespace: The parsed result, containing region_id and the
            optional settings.

    Examples:
        >>> parse_args(["--region_id", "cn-north-4"]).region_id
        'cn-north-4'
    """
    parser = argparse.ArgumentParser(
        prog="secmaster_baseline_inspection",
        description="Fetch Huawei Cloud SecMaster baseline inspection results and output statistics."
    )
    parser.add_argument(
        "--region_id",
        required=True,
        help="Required. Region ID, e.g. cn-north-4",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Optional. Timeout in seconds for each hcloud subprocess call (default: %(default)s).",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional. Path to a log file; logs are appended to stderr as well.",
    )
    return parser.parse_args(argv)


def _resolve_output_paths(timestamp: str) -> tuple[str, str]:
    """Resolve the absolute paths of the two output JSON files.

    1. Join the script directory with the timestamped file names.
    2. Return the absolute paths.

    Args:
        timestamp: str — Formatted timestamp string shared by both files.

    Returns:
        tuple[str, str]: The absolute paths of the full baseline results
            file and the statistics file.

    Examples:
        >>> full, stats = _resolve_output_paths("2026_10_12_14_30_00")
        >>> full.endswith("secmaster_baseline_inspection_results_2026_10_12_14_30_00.json")
        True
    """
    full_path = os.path.abspath(os.path.join(
        SCRIPT_DIR, OUTPUT_BASELINE_FULL.format(ts=timestamp)))
    stats_path = os.path.abspath(os.path.join(
        SCRIPT_DIR, OUTPUT_STATS.format(ts=timestamp)))
    return full_path, stats_path


def main(argv: list[str]) -> int:
    """Main script workflow.

    1. Parse the command-line arguments.
    2. Verify that project_id is configured.
    3. Enumerate every workspace in the region via ListWorkspaces.
    4. Pull all baseline inspection results from every workspace and merge
       them.
    5. Compute statistics and write the two JSON files.
    6. Return 0 on success; on failure write the data already fetched and
       return non-zero.

    Args:
        argv: list[str] — Command-line arguments (excluding the script name).

    Returns:
        int: Process exit code (0 on success, 1 on failure).

    Examples:
        # >>> main(["--region_id", "cn-north-4"])
    """
    args = parse_args(argv)
    region_id = args.region_id
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    full_path, stats_path = _resolve_output_paths(timestamp)

    setup_logging(args.log_file)
    logger.info("Task started. Output file(s): %s, %s", full_path, stats_path)

    # Data collected stage by stage, used to write partial results on mid-run failure.
    baseline_results: list[dict[str, Any]] = []
    workspace_metadata: list[dict[str, Any]] = []
    try:
        check_project_id_configured(region_id, args.timeout)
        logger.info("Step 1/4: project_id configured, region: %s", region_id)

        workspaces = list_workspaces(region_id, args.timeout)
        if not workspaces:
            logger.warning("Step 2/4: no workspace found in region %s, writing an empty result.", region_id)
        else:
            workspace_metadata = build_workspace_metadata(workspaces)
            logger.info("Step 2/4: %d workspace(s) found in region %s", len(workspaces), region_id)

            for ws in workspaces:
                workspace_id = ws.get("id", "") or ""
                workspace_name = ws.get("name", "") or ""
                logger.info("Step 3/4: fetching baseline for workspace: %s (%s)",
                            workspace_name, workspace_id)
                results = search_baseline(region_id, workspace_id, args.timeout)
                baseline_results.extend(results)
            logger.info("Step 3/4: retrieved %d baseline inspection results from %d workspace(s)",
                        len(baseline_results), len(workspaces))
    except RuntimeError as exc:
        # Mid-run failure: write the data already fetched, then exit with a non-zero code.
        _write_partial_outputs(baseline_results, workspace_metadata, full_path)
        logger.error("%s", exc)
        return 1

    stats = compute_statistics(baseline_results)
    write_json_file(full_path, {
        WORKSPACES_KEY: workspace_metadata,
        DATA_KEY: baseline_results,
    })
    write_json_file(stats_path, stats)
    logger.info("Step 4/4: statistics computed: total=%d", stats["total"])
    logger.info("Task finished. Output file(s): %s, %s", full_path, stats_path)
    return 0


def _write_partial_outputs(
    baseline_results: list[dict[str, Any]],
    workspace_metadata: list[dict[str, Any]],
    full_path: str,
) -> None:
    """Write the partial data already fetched (called on mid-run failure).

    1. Write the collected baseline results and the workspace metadata to
       the full results JSON file.
    2. Silently ignore file write failures (preserving the main exception message).

    Args:
        baseline_results: list[dict[str, Any]] — Baseline inspection results already fetched.
        workspace_metadata: list[dict[str, Any]] — Workspace metadata already collected.
        full_path: str — Absolute path of the full results output file.

    Returns:
        None

    Examples:
        # >>> _write_partial_outputs([], [], "baseline_results_full.json")
    """
    try:
        write_json_file(full_path, {
            WORKSPACES_KEY: workspace_metadata, DATA_KEY: baseline_results
        })
    except OSError:
        # Failure to write the output file does not affect the main error message.
        pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
