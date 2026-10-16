#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Huawei Cloud Config compliance inspection collector script.

Overview:
    This script collects compliance data from the Huawei Cloud Config (audit)
    service via the hcloud CLI: the compliance rule list, resource-level
    compliance results per rule, and the account-level compliance statistics
    trend. The collected data is written to disk as a timestamped JSON file
    next to the script and a summary is emitted to stderr via logging for
    manual review.

Detailed Description:
    1. Configure basic logging output, parse command-line arguments and
       validate required parameters and hcloud executability.
    2. Paginate through the compliance rule list.
    3. For each rule, paginate through resource-level compliance results; a
       single failure is recorded into failures by default and collection
       continues, while --fail-fast exits immediately.
    4. Fetch the account compliance statistics trend.
    5. Aggregate compliance results per rule and compute compliant /
       non-compliant counts.
    6. Render the data as JSON and write it to disk, then emit a summary to
       stderr via logging.

Dependencies:
    Python standard library: subprocess, json, argparse, logging, datetime,
    pathlib, sys. No third-party dependencies. The hcloud CLI must be
    installed, configured and authenticated with AK/SK in advance;
    --cli-region must be specified explicitly from the outside; this script
    does not hard-code a region.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# Constants
DEFAULT_TIMEOUT = 60
COMPLIANT_STATE = "Compliant"
NON_COMPLIANT_STATE = "NonCompliant"
IAM_SERVICE = "IAM"
AUTH_DOMAINS_API = "KeystoneListAuthDomains"
AUTH_DOMAINS_KEY = "domains"
# Output file is written next to the script with a timestamped name.
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE_NAME = "config_compliance_inspection_results_{ts}.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"


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
        >>> setup_logging(None)
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


class HcloudCommandError(Exception):
    """Raised when an hcloud command fails (non-zero return code)."""

    def __init__(self, command: List[str], return_code: int, stderr: str) -> None:
        """Record the failed command, return code and error output.

        1. Store the command, return code and stderr for inspection.
        2. Compose a descriptive message for the exception.

        Args:
            command: list[str] — The hcloud command argument list actually executed.
            return_code: int — The process return code.
            stderr: str — The standard error output content.

        Returns:
            None

        Examples:
            # >>> raise HcloudCommandError(["hcloud"], 1, "error")
            # HcloudCommandError: Command failed (return code 1): hcloud
        """
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
        super().__init__(f"Command failed (return code {return_code}): {' '.join(command)}\n{stderr}")


class HcloudOutputParseError(Exception):
    """Raised when hcloud output cannot be parsed as JSON."""

    def __init__(self, raw_output: str) -> None:
        """Save the raw output fragment that could not be parsed.

        1. Store the raw output and truncate a preview for the message.

        Args:
            raw_output: str — The unparsable command output (stored after
                keeping leading/trailing fragments).

        Returns:
            None

        Examples:
            # >>> raise HcloudOutputParseError("not json")
            # HcloudOutputParseError: Output could not be parsed as JSON, first 200 characters: not json
        """
        self.raw_output = raw_output
        preview = raw_output[:200] + ("..." if len(raw_output) > 200 else "")
        super().__init__(f"Output could not be parsed as JSON, first 200 characters: {preview}")


class HcloudTimeoutError(Exception):
    """Raised when an hcloud command execution times out."""

    def __init__(self, command: List[str], timeout: int) -> None:
        """Record the timed-out command and timeout seconds.

        1. Store the command and timeout for inspection.
        2. Compose a descriptive message for the exception.

        Args:
            command: list[str] — The hcloud command argument list actually executed.
            timeout: int — The timeout in seconds.

        Returns:
            None

        Examples:
            # >>> raise HcloudTimeoutError(["hcloud"], 60)
            # HcloudTimeoutError: Command timed out after 60 seconds: hcloud
        """
        self.command = command
        self.timeout = timeout
        super().__init__(f"Command timed out after {timeout} seconds: {' '.join(command)}")


def _build_command(service_name: str, api_name: str, cli_region: str,
                   domain_id: Optional[str] = None,
                   params: Optional[Dict[str, str]] = None) -> List[str]:
    """Build an hcloud command argument list.

    1. Prefix with hcloud <service_name> <api_name>, supporting Config, IAM etc.
    2. Append the --cli-region required parameter.
    3. Append --domain_id when an account ID is provided (Config collection
       needs it; IAM auth queries do not).
    4. Append remaining optional parameters (non-None values only).

    Args:
        service_name: str — The hcloud service name, e.g. Config, IAM.
        api_name: str — The service API name, e.g. ListPolicyAssignments,
            KeystoneListAuthDomains.
        cli_region: str — The hcloud command region, e.g. cn-north-4.
        domain_id: Optional[str] — The Huawei Cloud account ID; None skips
            appending this parameter.
        params: Optional[dict[str, str]] — Remaining parameter key-value
            pairs; None values are ignored automatically.

    Returns:
        list[str]: The command argument list ready for subprocess.

    Examples:
        >>> _build_command("Config", "ListPolicyAssignments", "cn-north-4", "a9c2", {"limit": "100"})
        ['hcloud', 'Config', 'ListPolicyAssignments', '--cli-region=cn-north-4', '--domain_id=a9c2', '--limit=100']
        >>> _build_command("IAM", "KeystoneListAuthDomains", "cn-north-4")
        ['hcloud', 'IAM', 'KeystoneListAuthDomains', '--cli-region=cn-north-4']
    """
    command: List[str] = ["hcloud", service_name, api_name]
    command.append(f"--cli-region={cli_region}")
    if domain_id is not None:
        command.append(f"--domain_id={domain_id}")
    if params:
        for key, value in params.items():
            if value is not None:
                command.append(f"--{key}={value}")
    return command


def run_command(command: List[str], timeout: int) -> str:
    """Execute an hcloud command and return the standard output text.

    1. Invoke subprocess.run with the argument list, avoiding shell joining.
    2. Raise HcloudCommandError when the return code is non-zero.
    3. Raise HcloudTimeoutError on execution timeout.

    Args:
        command: list[str] — The hcloud command argument list.
        timeout: int — The timeout in seconds.

    Returns:
        str: The command standard output text.

    Raises:
        HcloudCommandError: The command returned a non-zero code.
        HcloudTimeoutError: The command execution timed out.

    Examples:
        # >>> run_command(["hcloud", "--version"], 10)
        # 'hcloud version ...'
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HcloudTimeoutError(command, timeout) from exc
    except FileNotFoundError as exc:
        raise HcloudCommandError(command, 127, f"hcloud command not found or not executable: {exc}") from exc
    if result.returncode != 0:
        raise HcloudCommandError(command, result.returncode, result.stderr or "")
    return result.stdout


def parse_json_output(raw_output: str) -> Any:
    """Parse hcloud command output into a JSON object.

    1. Try json.loads on the whole output first.
    2. On failure, extract the JSON envelope from the first '{' to the last
       '}' and parse it (tolerating non-JSON text such as upgrade prompts).
    3. Still failing, raise HcloudOutputParseError.

    Args:
        raw_output: str — The raw command output text.

    Returns:
        Any: The parsed JSON object (dict or list).

    Raises:
        HcloudOutputParseError: The output cannot be parsed as JSON.

    Examples:
        >>> parse_json_output('{"value": []}')
        {'value': []}
    """
    text = raw_output.strip()
    if not text:
        raise HcloudOutputParseError(raw_output)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise HcloudOutputParseError(raw_output)


def resolve_domain_id(cli_region: str, timeout: int) -> str:
    """Resolve the account ID of the currently authenticated tenant.

    1. Invoke hcloud IAM KeystoneListAuthDomains --cli-region=<region>.
    2. Parse the domains array in the response and take the id of the first
       entry as the account ID.
    3. Raise HcloudOutputParseError when domains is missing or empty.

    Args:
        cli_region: str — The hcloud command region (specified externally,
            not hard-coded).
        timeout: int — The timeout in seconds for a single command.

    Returns:
        str: The account ID (Domain ID) of the authenticated tenant.

    Raises:
        HcloudOutputParseError: The response has no domains array or it is
            empty.

    Examples:
        # >>> resolve_domain_id("cn-north-4", 60)
        # '<32-hex-digit-domain-id>'
    """
    command = _build_command(IAM_SERVICE, AUTH_DOMAINS_API, cli_region)
    raw_output = run_command(command, timeout)
    data = parse_json_output(raw_output)
    if not isinstance(data, dict):
        raise HcloudOutputParseError(raw_output)
    domains = data.get(AUTH_DOMAINS_KEY) or []
    if not domains or not domains[0].get("id"):
        raise HcloudOutputParseError(raw_output)
    return domains[0]["id"]


class HcloudClient:
    """hcloud command-line client wrapper providing three Config service collection APIs."""

    def __init__(self, cli_region: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """Initialize the client and store shared command parameters.

        1. Record the region and timeout parameters.
        2. The account ID is resolved lazily on the first auth_domain_id()
           call, not during construction.

        Args:
            cli_region: str — The hcloud command region (specified externally,
                not hard-coded).
            timeout: int — The timeout in seconds for a single command,
                default 60.

        Returns:
            None

        Examples:
            >>> client = HcloudClient("cn-north-4")
        """
        self.cli_region = cli_region
        self.timeout = timeout
        self.domain_id: Optional[str] = None

    def auth_domain_id(self) -> str:
        """Resolve and cache the account ID of the authenticated tenant.

        1. Return the cached value when already resolved.
        2. On first call, delegate to resolve_domain_id() to run the IAM
           query and cache the result.

        Args:
            None

        Returns:
            str: The account ID (Domain ID) of the authenticated tenant.

        Examples:
            # >>> client = HcloudClient("cn-north-4")
            # >>> client.auth_domain_id()
        """
        if self.domain_id is None:
            self.domain_id = resolve_domain_id(self.cli_region, self.timeout)
        return self.domain_id

    def _invoke(self, api_name: str, params: Optional[Dict[str, str]] = None,
                service_name: str = "Config") -> Any:
        """Execute a single-page command and return the parsed JSON object.

        1. Build the command argument list (supporting a custom service name).
        2. Execute the command and parse the output JSON.

        Args:
            api_name: str — The service API name.
            params: Optional[dict[str, str]] — The request parameter pairs.
            service_name: str — The service name, default Config; pass other
                services such as IAM explicitly.

        Returns:
            Any: The parsed response JSON object.

        Examples:
            # >>> client = HcloudClient("cn-north-4")
            # >>> client._invoke("ListPolicyStatesStatistics")
        """
        command = _build_command(service_name, api_name, self.cli_region,
                                 self.domain_id, params)
        raw_output = run_command(command, self.timeout)
        return parse_json_output(raw_output)

    def list_policy_assignments(self, marker: Optional[str] = None,
                                limit: Optional[int] = None) -> Any:
        """Call ListPolicyAssignments to fetch one page of the compliance rule list.

        Args:
            marker: Optional[str] — The pagination marker from the previous
                page's next_marker.
            limit: Optional[int] — The maximum number of items per page.

        Returns:
            Any: The response JSON with the value rule list and page_info.

        Examples:
            # >>> client = HcloudClient("cn-north-4")
            # >>> client.list_policy_assignments()
        """
        params: Dict[str, str] = {}
        if marker is not None:
            params["marker"] = marker
        if limit is not None:
            params["limit"] = str(limit)
        return self._invoke("ListPolicyAssignments", params)

    def list_policy_states(self, assignment_id: str,
                           marker: Optional[str] = None,
                           limit: Optional[int] = None) -> Any:
        """Call ListPolicyStatesByAssignmentId to fetch one page of rule compliance results.

        Args:
            assignment_id: str — The compliance rule ID.
            marker: Optional[str] — The pagination marker.
            limit: Optional[int] — The maximum number of items per page.

        Returns:
            Any: The response JSON with the value compliance result list and
                page_info.

        Examples:
            # >>> client = HcloudClient("cn-north-4")
            # >>> client.list_policy_states("6aabb8b5d9689c201d96cb51")
        """
        params: Dict[str, str] = {"policy_assignment_id": assignment_id}
        if marker is not None:
            params["marker"] = marker
        if limit is not None:
            params["limit"] = str(limit)
        return self._invoke("ListPolicyStatesByAssignmentId", params)

    def list_statistics(self) -> Any:
        """Call ListPolicyStatesStatistics to fetch the account compliance trend.

        Args:
            None

        Returns:
            Any: The response JSON whose value holds daily statistic rows in
                ascending date order.

        Examples:
            # >>> client = HcloudClient("cn-north-4")
            # >>> client.list_statistics()
        """
        return self._invoke("ListPolicyStatesStatistics")


def fetch_all_assignments(client: HcloudClient,
                          limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Paginate through the full compliance rule list.

    1. Loop over list_policy_assignments starting from an empty marker.
    2. Follow page_info.next_marker, recording seen markers to guard against
       infinite loops.
    3. Return the merged list of all rule entries.

    Args:
        client: HcloudClient — The hcloud client instance.
        limit: Optional[int] — The maximum number of items per page.

    Returns:
        list[dict[str, Any]]: All compliance rule entries.

    Examples:
        # >>> client = HcloudClient("cn-north-4")
        # >>> fetch_all_assignments(client)
    """
    assignments: List[Dict[str, Any]] = []
    seen_markers: set[str] = set()
    marker: Optional[str] = None
    while True:
        if marker is not None:
            if marker in seen_markers:
                logger.warning("Duplicate pagination marker %s detected, stopping pagination", marker)
                break
            seen_markers.add(marker)
        response = client.list_policy_assignments(marker=marker, limit=limit)
        items = response.get("value", []) if isinstance(response, dict) else []
        assignments.extend(items)
        page_info = response.get("page_info", {}) if isinstance(response, dict) else {}
        next_marker = page_info.get("next_marker")
        if not next_marker:
            break
        marker = next_marker
    return assignments


def fetch_all_policy_states(client: HcloudClient, assignment_id: str,
                            limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Paginate through all resource-level compliance results of one rule.

    1. Loop over list_policy_states starting from an empty marker.
    2. Follow page_info.next_marker, recording seen markers to guard against
       infinite loops.
    3. Return the merged list of all compliance results of the rule.

    Args:
        client: HcloudClient — The hcloud client instance.
        assignment_id: str — The compliance rule ID.
        limit: Optional[int] — The maximum number of items per page.

    Returns:
        list[dict[str, Any]]: All resource-level compliance results of the rule.

    Examples:
        # >>> client = HcloudClient("cn-north-4")
        # >>> fetch_all_policy_states(client, "6aabb8b5d9689c201d96cb51")
    """
    states: List[Dict[str, Any]] = []
    seen_markers: set[str] = set()
    marker: Optional[str] = None
    while True:
        if marker is not None:
            if marker in seen_markers:
                logger.warning("Duplicate pagination marker %s detected, stopping pagination", marker)
                break
            seen_markers.add(marker)
        response = client.list_policy_states(
            assignment_id=assignment_id,
            marker=marker,
            limit=limit,
        )
        items = response.get("value", []) if isinstance(response, dict) else []
        states.extend(items)
        page_info = response.get("page_info", {}) if isinstance(response, dict) else {}
        next_marker = page_info.get("next_marker")
        if not next_marker:
            break
        marker = next_marker
    return states


def compute_summary(states: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count rule result records by compliance state.

    1. Iterate over the compliance results and count Compliant and
       NonCompliant entries separately.
    2. Return a statistics dict with compliant, non_compliant and total.

    Args:
        states: list[dict[str, Any]] — The compliance result list.

    Returns:
        dict[str, int]: The count statistics keyed by compliant,
            non_compliant and total.

    Examples:
        >>> compute_summary([{"compliance_state": "Compliant"}])
        {'compliant': 1, 'non_compliant': 0, 'total': 1}
    """
    compliant = sum(1 for s in states if s.get("compliance_state") == COMPLIANT_STATE)
    non_compliant = sum(1 for s in states if s.get("compliance_state") == NON_COMPLIANT_STATE)
    return {
        "compliant": compliant,
        "non_compliant": non_compliant,
        "total": len(states),
    }


def collect_all(client: HcloudClient, fail_fast: bool) -> Dict[str, Any]:
    """Run the full collection flow and return the aggregated data.

    1. Resolve the account ID of the authenticated tenant via auth_domain_id()
       at startup.
    2. Paginate through the full rule list.
    3. Paginate through compliance results per rule; a single failure is
       recorded into failures by default and collection continues.
    4. Fetch the statistics trend.
    5. Assemble the meta, assignments, statistics, failures summary structure.

    Args:
        client: HcloudClient — The hcloud client instance.
        fail_fast: bool — True exits immediately on a single failure, False
            records the failure and continues.

    Returns:
        dict[str, Any]: The summary data with meta, assignments, statistics
            and failures.

    Examples:
        # >>> client = HcloudClient("cn-north-4")
        # >>> collect_all(client, False)
    """
    domain_id = client.auth_domain_id()
    failures: List[Dict[str, str]] = []
    assignments = fetch_all_assignments(client)
    assignment_records: List[Dict[str, Any]] = []
    for assignment in assignments:
        assignment_id = assignment.get("id", "")
        assignment_name_text = assignment.get("name", "")
        try:
            states = fetch_all_policy_states(
                client=client,
                assignment_id=assignment_id,
            )
        except (HcloudCommandError, HcloudOutputParseError, HcloudTimeoutError) as exc:
            if fail_fast:
                raise
            failures.append({
                "assignment_id": assignment_id,
                "name": assignment_name_text,
                "error": str(exc),
            })
            logger.warning("Failed to collect rule [%s] (%s): %s", assignment_name_text, assignment_id, exc)
            states = []
        assignment_records.append({
            "assignment": assignment,
            "states": states,
            "summary": compute_summary(states),
        })
    statistics = client.list_statistics()
    statistics_rows = statistics.get("value", []) if isinstance(statistics, dict) else []
    return {
        "meta": {
            "domain_id": domain_id,
            "cli_region": client.cli_region,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "assignments": assignment_records,
        "statistics": statistics_rows,
        "failures": failures,
    }


def _format_evaluation_time(timestamp_str: Optional[str]) -> str:
    """Convert a millisecond timestamp string into a local readable time.

    1. Parse the value as a millisecond timestamp and convert it to local
       time.
    2. Return the original string on parse failure or empty input.

    Args:
        timestamp_str: Optional[str] — The millisecond timestamp string,
            e.g. "1789638850817".

    Returns:
        str: The formatted local time string, or the original value on
            failure.

    Examples:
        # >>> _format_evaluation_time("1789638850817")
        # '2026-09-17 09:54:10'
    """
    if not timestamp_str:
        return ""
    try:
        timestamp_ms = int(timestamp_str)
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError, OverflowError):
        return timestamp_str


def render_json(data: Dict[str, Any]) -> str:
    """Render the summary data into a JSON string.

    1. Add a readable evaluation_time display field to compliance results,
       keeping the raw value.

    Args:
        data: dict[str, Any] — The collection summary data.

    Returns:
        str: The formatted JSON text (ensure_ascii=False, indent 2).

    Examples:
        # >>> render_json({"assignments": [], "statistics": [], "failures": []})
        # '{"assignments": [], "statistics": [], "failures": []}'
    """
    assignments = data.get("assignments", [])
    for record in assignments:
        for state in record.get("states", []):
            if state.get("evaluation_time"):
                state["evaluation_time_readable"] = _format_evaluation_time(
                    state.get("evaluation_time"))
    return json.dumps(data, ensure_ascii=False, indent=2)


def resolve_output_path(timestamp: str) -> str:
    """Resolve the absolute output file path in the script directory.

    1. Join the script directory with the timestamped file name.
    2. Return the absolute path of the output file.

    Args:
        timestamp: str — Formatted timestamp string for the file name.

    Returns:
        str: Absolute output file path.

    Examples:
        >>> resolve_output_path("2026_10_12_14_30_00").endswith("config_compliance_inspection_results_2026_10_12_14_30_00.json")
        True
    """
    return str(SCRIPT_DIR / OUTPUT_FILE_NAME.format(ts=timestamp))


def write_outputs(data: Dict[str, Any], output_path: str) -> List[str]:
    """Write the summary data to disk as a timestamped JSON file.

    1. Render the data as JSON.
    2. Write it to the fixed output path resolved at startup.

    Args:
        data: dict[str, Any] — The collection summary data.
        output_path: str — Absolute output file path resolved at startup.

    Returns:
        list[str]: The list of written file paths.

    Examples:
        # >>> write_outputs({"assignments": []}, "/abs/out.json")
        # ['/abs/out.json']
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_json(data), encoding="utf-8")
    return [str(target)]


def print_summary(data: Dict[str, Any], written_files: List[str]) -> None:
    """Emit the collection summary (via logging to stderr).

    1. Output meta information, total rules and failed rules (info level).
    2. Output per-rule compliant/non-compliant counts (info level).
    3. Output failed-rule warnings (warning level).
    4. Output the trend summary and written file paths (info level).

    Args:
        data: dict[str, Any] — The collection summary data.
        written_files: list[str] — The list of written file paths.

    Returns:
        None

    Examples:
        # >>> print_summary({"assignments": [], "failures": []}, [])
    """
    meta = data.get("meta", {})
    assignments = data.get("assignments", [])
    failures = data.get("failures", [])
    statistics = data.get("statistics", [])
    logger.info("=" * 60)
    logger.info("Huawei Cloud Config compliance inspection collection completed")
    logger.info("=" * 60)
    logger.info("Account ID: %s", meta.get("domain_id", ""))
    logger.info("hcloud region: %s", meta.get("cli_region", ""))
    logger.info("Total rules: %d", len(assignments))
    logger.info("Failed rules: %d", len(failures))
    logger.info("-" * 60)
    for record in assignments:
        assignment = record.get("assignment", {})
        summary = record.get("summary", {})
        logger.info("[{:<6}] compliant {:>4} / non-compliant {:>4} / total {:>4}  {}".format(
            assignment.get("policy_assignment_type", ""),
            summary.get("compliant", 0),
            summary.get("non_compliant", 0),
            summary.get("total", 0),
            assignment.get("name", ""),
        ))
    if failures:
        logger.info("-" * 60)
        logger.warning("The following rules failed to collect; see the output file for details:")
        for failure in failures:
            logger.warning("  - %s (%s)", failure.get("name", ""),
                           failure.get("assignment_id", ""))
    if statistics:
        logger.info("-" * 60)
        first = statistics[0]
        last = statistics[-1]
        total_resource = last.get("total_resource_count", 0)
        non_compliant_resource = last.get("non_compliant_resource_count", 0)
        rate = ""
        if total_resource:
            rate = f"{100 * (total_resource - non_compliant_resource) / total_resource:.1f}%"
        logger.info("Trend: %s ~ %s, %d days, latest compliance rate %s",
                    first.get("statistic_date", ""), last.get("statistic_date", ""),
                    len(statistics), rate)
    if written_files:
        logger.info("-" * 60)
        logger.info("Generated files:")
        for file_path in written_files:
            logger.info("  - %s", file_path)
    logger.info("=" * 60)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Args:
        None

    Returns:
        argparse.ArgumentParser: The configured argument parser.

    Examples:
        >>> parser = build_parser()
    """
    parser = argparse.ArgumentParser(
        prog="config_compliance_inspection",
        description="Huawei Cloud Config compliance inspection collector (requires hcloud CLI installed and authenticated)")
    parser.add_argument("--cli-region", default=None,
                        help="Required. hcloud CLI region, e.g. cn-north-4 (not hard-coded)")
    parser.add_argument("--log-file", default=None,
                        help="Optional. Path to a log file; logs are appended to stderr as well")
    parser.add_argument("--fail-fast", action="store_true",
                        help="Optional. Exit immediately when a rule collection fails (default: record failure and continue)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help="Optional. Timeout in seconds per command (default: %(default)s).")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry wiring up argument parsing, collection, rendering and write-out.

    1. Configure basic logging output (stderr by default, optional
       --log-file handler).
    2. Parse the command-line arguments.
    3. Create HcloudClient and run the full collection; the account ID is
       auto-detected by the script.
    4. Render to the requested format, write to disk, and emit the summary to
       stderr via logging.

    Args:
        argv: Optional[list[str]] — The command-line argument list, or
            sys.argv[1:] when None.

    Returns:
        int: The exit code; 0 for success, 1 for failure.

    Examples:
        # >>> main(["--cli-region", "cn-north-4"])
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_file)
    if not args.cli_region:
        parser.error("--cli-region is required")
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    output_absolute = resolve_output_path(timestamp)
    logger.info("Task started. Output file(s): %s", output_absolute)
    try:
        client = HcloudClient(cli_region=args.cli_region,
                              timeout=args.timeout)
        data = collect_all(
            client=client,
            fail_fast=args.fail_fast,
        )
    except (HcloudCommandError, HcloudOutputParseError, HcloudTimeoutError) as exc:
        logger.error("Collection failed: %s", exc)
        return 1
    written_files = write_outputs(data, output_absolute)
    print_summary(data, written_files)
    logger.info("Task finished. Output file(s): %s", written_files[0])
    logger.info("Collection completed, %d files written", len(written_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
