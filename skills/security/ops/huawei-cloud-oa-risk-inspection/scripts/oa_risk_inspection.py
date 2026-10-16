#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""OA risk inspection via hcloud CLI.

Detailed Description:
    This script automates Huawei Cloud Optimization Advisor (OA) risk
    inspection by invoking the `hcloud` command line tool. It fetches the
    full list of check items, triggers a check for every item, pulls
    paginated check results, and aggregates all results into a single JSON
    file.

Workflow:
    1. Parse command line arguments (region, language, concurrency, etc.).
    2. Set up logging to stderr with an optional file handler.
    3. Call `hcloud OA ShowCheckItemList` to get all check items.
    4. Process check items concurrently: trigger check via StartItemCheck,
       then fetch paginated results via ShowCheckItemResult.
    5. Merge results in original order and write them to a single JSON file.

Dependencies:
    - Python 3.8+ standard library only (subprocess, json, argparse,
      logging, concurrent.futures, datetime).
    - External: `hcloud` (KooCLI) installed, configured and authenticated.
      The script itself does not check credentials.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

LOGGER = logging.getLogger(__name__)

DEFAULT_REGION = "cn-southwest-2"
DEFAULT_LANGUAGE = "zh-cn"
DEFAULT_THREADS = 3
DEFAULT_PAGE_SIZE = 10
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_INTERVAL = 3
DEFAULT_TIMEOUT = 120
# Output file is written next to the script with a timestamped name.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE_NAME = "oa_risk_inspection_results_{ts}.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"

# OA service is only verified available in cn-southwest-2 (cn-south-4
# returned APIGW.0101 in the pagination verification report). No hard-coded
# whitelist: the remote CLI version may change, so the region is user input.
SUPPORTED_REGIONS_HINT = ("cn-southwest-2", "cn-south-4")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command line argument parser.

    1. Add region, language, concurrency and page options.
    2. Add retry, timeout, output and logging options.

    Args:
        None

    Returns:
        argparse.ArgumentParser: Configured parser with all options.

    Examples:
        >>> parser = build_arg_parser()
        >>> args = parser.parse_args(["--region", "cn-south-4"])
        >>> args.region == "cn-south-4"
        True
    """
    parser = argparse.ArgumentParser(
        prog="oa_risk_inspection",
        description=(
            "Fetch Huawei Cloud OA risk check results via the hcloud CLI "
            "and save them to a single JSON file."
        ),
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help=(
            "Optional. Cloud region for the OA service (default: %(default)s; "
            "hint: {})".format(", ".join(SUPPORTED_REGIONS_HINT))
        ),
    )
    parser.add_argument(
        "--X-Language",
        dest="language",
        default=DEFAULT_LANGUAGE,
        help="Optional. Request language, zh-cn or en-us (default: %(default)s).",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=DEFAULT_THREADS,
        help="Optional. Number of concurrent worker threads (default: %(default)s).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=DEFAULT_PAGE_SIZE,
        help=(
            "Optional. Resources per page for ShowCheckItemResult (default: %(default)s). "
            "Do NOT exceed 10: the server truncates larger page sizes and "
            "computes the offset from the requested value, which skips data."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Optional. Retry count for result queries per check item (default: %(default)s).",
    )
    parser.add_argument(
        "--retry-interval",
        type=int,
        default=DEFAULT_RETRY_INTERVAL,
        help="Optional. Seconds between result query retries (default: %(default)s).",
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
    return parser


def setup_logging(log_file: str | None) -> None:
    """Set up the logging framework.

    1. Configure root logger level to INFO.
    2. Add a stderr StreamHandler.
    3. Add a FileHandler when log_file is provided.

    Args:
        log_file: str | None — Optional path for file logging.

    Returns:
        None

    Examples:
        # >>> setup_logging(None)
        # no output; the logging framework is configured on stderr.
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


def resolve_output_path(timestamp: str) -> str:
    """Resolve the absolute output file path in the script directory.

    1. Join the script directory with the timestamped file name.
    2. Return the absolute path of the output file.

    Args:
        timestamp: str — Formatted timestamp string for the file name.

    Returns:
        str: Absolute output file path.

    Examples:
        >>> resolve_output_path("2026_10_12_14_30_00").endswith("oa_risk_inspection_results_2026_10_12_14_30_00.json")
        True
    """
    return os.path.join(SCRIPT_DIR, OUTPUT_FILE_NAME.format(ts=timestamp))


def _run_hcloud(cmd_args: list[str], timeout: int) -> dict:
    """Run one hcloud subcommand and return its parsed JSON output.

    1. Build the full hcloud command and execute it via subprocess.
    2. Raise an exception when the process fails, output is not JSON, or
       the command times out; the original output text is preserved.

    Args:
        cmd_args: list[str] — hcloud subcommand arguments (service and
            operation plus their parameters, excluding the hcloud binary).
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        dict: Parsed JSON object returned by hcloud.

    Raises:
        HcloudError: When hcloud fails, output is not JSON, or times out.

    Examples:
        # When hcloud is unavailable, an HcloudError is raised:
        # >>> _run_hcloud(["OA", "ShowCheckItemList"], 5)
        # Traceback (most recent call last):
        # HcloudError: ...
    """
    command = ["hcloud"] + cmd_args
    LOGGER.debug("Executing: %s", " ".join(command))
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HcloudError(
            "hcloud executable not found; ensure KooCLI is installed and "
            "present in PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HcloudError(
            "hcloud command timed out after {} seconds: {}".format(
                timeout, " ".join(command)
            )
        ) from exc

    raw_output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        detail = raw_output or (completed.stderr or "").strip()
        raise HcloudError(
            "hcloud exited with code {}: {}".format(
                completed.returncode, detail[:500] or "no output"
            )
        )
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise HcloudError(
            "hcloud output is not valid JSON: {}...".format(raw_output[:300])
        ) from exc
    if not isinstance(parsed, dict):
        raise HcloudError("hcloud output is not a JSON object: {}".format(raw_output[:300]))
    return parsed


class HcloudError(RuntimeError):
    """Error raised when an hcloud invocation fails or returns bad output."""


def _extract_error_code(message: str) -> str | None:
    """Extract the Huawei Cloud error code from an error message.

    1. Scan each occurrence of the 'error_code' key in the message.
    2. For each occurrence, take the quoted value following the key
       (single or double quotes) and return it when it looks like a code.
    3. Return None when no valid code is found.

    Args:
        message: str — Error message text, typically an HcloudError payload.

    Returns:
        str | None: Error code such as "OA.15000020", or None.

    Examples:
        >>> _extract_error_code("{'error_code': 'OA.00000001', 'error_msg': 'internal error'}")
        'OA.00000001'
        >>> _extract_error_code('{"error_code": "OA.15000047"}')
        'OA.15000047'
        >>> _extract_error_code("no code here") is None
        True
    """
    marker = "error_code"
    index = message.find(marker)
    while index != -1:
        remainder = message[index + len(marker):]
        cursor = 0
        while cursor < len(remainder) and remainder[cursor] in ":'\" ":
            cursor += 1
        code = remainder[cursor:]
        for end_quote in (code.find("'"), code.find('"')):
            if end_quote > 0:
                candidate = code[:end_quote]
                if candidate and " " not in candidate:
                    return candidate
        index = message.find(marker, index + 1)
    return None


def _is_retryable_error(error_code: str | None) -> bool:
    """Decide whether an OA error code is transient and worth retrying.

    1. Return False for a null or unknown code (fail-safe: no retry).
    2. Return True only for transient server-side codes.

    Args:
        error_code: str | None — Error code extracted from an error message.

    Returns:
        bool: True when the code indicates a transient server-side failure.

    Examples:
        >>> _is_retryable_error("OA.15000020")
        True
        >>> _is_retryable_error("OA.15000047")
        False
        >>> _is_retryable_error(None)
        False
    """
    transient_codes = {
        "OA.15000020",  # the system is busy, please try again later
        "OA.00000001",  # internal error
    }
    return error_code in transient_codes


def list_check_items(region: str, language: str, timeout: int) -> list[dict]:
    """Fetch the full list of OA check items.

    1. Call hcloud OA ShowCheckItemList with the given region and language.
    2. Return the data array of check items.

    Args:
        region: str — Cloud region for the OA service.
        language: str — Request language (zh-cn or en-us).
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        list[dict]: List of check item dictionaries.

    Raises:
        HcloudError: When hcloud fails or the response has no data array.

    Examples:
        # Emits two log entries; no return value. When hcloud is
        # unavailable, list_check_items raises HcloudError.
    """
    response = _run_hcloud(
        [
            "OA",
            "ShowCheckItemList",
            "--cli-region={}".format(region),
            "--X-Language={}".format(language),
        ],
        timeout,
    )
    data = response.get("data")
    if not isinstance(data, list):
        raise HcloudError(
            "ShowCheckItemList response has no data array: {}".format(str(response)[:300])
        )
    return data


def start_check(
    region: str,
    item_id: str,
    timeout: int,
    max_retries: int = 0,
    retry_interval: int = 0,
) -> str:
    """Trigger one check item and return the check number.

    1. Call hcloud OA StartItemCheck with the check item id.
    2. Parse and return the check_num from the response data.
    3. Retry transient server-side errors (system busy, internal error) up
       to max_retries times; deterministic errors are not retried.

    Args:
        region: str — Cloud region for the OA service.
        item_id: str — Check item id from ShowCheckItemList.
        timeout: int — Timeout in seconds for the subprocess call.
        max_retries: int — Retry count for transient trigger failures.
        retry_interval: int — Seconds between retries.

    Returns:
        str: Check number (check_num), e.g. "A2026101000025".

    Raises:
        HcloudError: When hcloud fails or the response has no data value.

    Examples:
        # When hcloud is unavailable, start_check raises HcloudError.
    """
    last_error: HcloudError | None = None
    for attempt in range(max_retries + 1):
        try:
            response = _run_hcloud(
                [
                    "OA",
                    "StartItemCheck",
                    "--cli-region={}".format(region),
                    "--check_item_id={}".format(item_id),
                ],
                timeout,
            )
            check_num = response.get("data")
            if not isinstance(check_num, str) or not check_num:
                raise HcloudError(
                    "StartItemCheck response has no data check_num: {}".format(str(response)[:300])
                )
            return check_num
        except HcloudError as exc:
            last_error = exc
            error_code = _extract_error_code(str(exc))
            if not _is_retryable_error(error_code):
                raise exc
            LOGGER.warning(
                "Trigger failed for item %s with transient error %s "
                "(attempt %d/%d): %s",
                item_id,
                error_code,
                attempt + 1,
                max_retries + 1,
                str(exc)[:300],
            )
            if attempt < max_retries:
                time.sleep(retry_interval)
    assert last_error is not None
    raise HcloudError(
        "Trigger for item {} failed after {} retries: {}".format(
            item_id, max_retries, str(last_error)[:300]
        )
    )


def _fetch_result_page(
    region: str,
    language: str,
    item_id: str,
    check_num: str,
    page_no: int,
    page_size: int,
    timeout: int,
) -> dict:
    """Fetch one page of ShowCheckItemResult.

    1. Call hcloud OA ShowCheckItemResult for one page.
    2. Return the raw data object containing summary and resources.

    Args:
        region: str — Cloud region for the OA service.
        language: str — Request language (zh-cn or en-us).
        item_id: str — Check item id.
        check_num: str — Check number returned by StartItemCheck.
        page_no: int — Page number starting from 1.
        page_size: int — Resources per page.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        dict: data object with check_item_result_summary and resources.

    Raises:
        HcloudError: When hcloud fails or the response is malformed.

    Examples:
        # When hcloud is unavailable, _fetch_result_page raises HcloudError.
    """
    response = _run_hcloud(
        [
            "OA",
            "ShowCheckItemResult",
            "--cli-region={}".format(region),
            "--X-Language={}".format(language),
            "--check_item_id={}".format(item_id),
            "--check_num={}".format(check_num),
            "--page_no={}".format(page_no),
            "--page_size={}".format(page_size),
        ],
        timeout,
    )
    data = response.get("data")
    if not isinstance(data, dict):
        raise HcloudError(
            "ShowCheckItemResult response has no data object: {}".format(str(response)[:300])
        )
    return data


def get_check_result(
    region: str,
    language: str,
    item_id: str,
    check_num: str,
    page_size: int,
    max_retries: int,
    retry_interval: int,
    timeout: int,
) -> dict:
    """Fetch the full paginated result for one check item.

    1. Query page 1 and read the check summary once.
    2. Keep querying subsequent pages while a page returns a full page.
    3. Stop when a page returns fewer resources than page_size, or when an
       empty resources array is returned (fallback termination).
    4. Merge all resources into a single list.
    5. Retry the whole pagination flow up to max_retries times.

    Args:
        region: str — Cloud region for the OA service.
        language: str — Request language (zh-cn or en-us).
        item_id: str — Check item id.
        check_num: str — Check number returned by StartItemCheck.
        page_size: int — Resources per page (use 10 by default).
        max_retries: int — Number of retries for the query flow.
        retry_interval: int — Seconds between retries.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        dict: Result data with check_item_result_summary and merged
            resources list.

    Raises:
        HcloudError: When all retries are exhausted or responses are
            malformed. Pagination never relies on checked_resource_count
            or risk_resource_count.

    Examples:
        # When hcloud is unavailable, get_check_result raises HcloudError.
    """
    last_error: HcloudError | None = None
    for attempt in range(max_retries + 1):
        try:
            page_one = _fetch_result_page(
                region, language, item_id, check_num, 1, page_size, timeout
            )
            resources: list[dict] = []
            summary = page_one.get("check_item_result_summary")
            page_resources = page_one.get("resources", [])
            if not isinstance(page_resources, list):
                raise HcloudError(
                    "ShowCheckItemResult resources is not a list: {}".format(
                        str(page_one)[:300]
                    )
                )
            resources.extend(page_resources)
            page_no = 2
            while len(page_resources) >= page_size:
                page_data = _fetch_result_page(
                    region, language, item_id, check_num, page_no, page_size, timeout
                )
                page_resources = page_data.get("resources", [])
                if not isinstance(page_resources, list):
                    raise HcloudError(
                        "ShowCheckItemResult resources is not a list: {}".format(
                            str(page_data)[:300]
                        )
                    )
                resources.extend(page_resources)
                page_no += 1
            return {"check_item_result_summary": summary, "resources": resources}
        except HcloudError as exc:
            last_error = exc
            LOGGER.warning(
                "Result query failed for item %s (attempt %d/%d): %s",
                item_id,
                attempt + 1,
                max_retries + 1,
                str(exc)[:300],
            )
            if attempt < max_retries:
                time.sleep(retry_interval)
    assert last_error is not None
    raise HcloudError(
        "Result query for item {} failed after {} retries: {}".format(
            item_id, max_retries, str(last_error)[:300]
        )
    )


def _build_success_record(check_item: dict, check_num: str, result_data: dict) -> dict:
    """Assemble a success record for one check item.

    1. Copy identity fields from the check item.
    2. Attach check_num, summary and resources from the result data.

    Args:
        check_item: dict — Check item from ShowCheckItemList.
        check_num: str — Check number returned by StartItemCheck.
        result_data: dict — Aggregated result data from get_check_result.

    Returns:
        dict: Success record with identity, check_num, summary, resources
            and a null error field.
    """
    record: dict = {
        "check_item_id": check_item.get("id"),
        "check_item_name": check_item.get("name"),
        "dimension": check_item.get("dimension"),
        "service_type_code": check_item.get("service_type_code"),
        "risk_level": check_item.get("risk_level"),
        "check_num": check_num,
        "summary": result_data.get("check_item_result_summary"),
        "resources": result_data.get("resources", []),
        "error": None,
    }
    return record


def _build_failure_record(check_item: dict, error_text: str) -> dict:
    """Assemble a failure record for one check item.

    1. Copy identity fields from the check item.
    2. Attach the error text and leave result fields absent.

    Args:
        check_item: dict — Check item from ShowCheckItemList.
        error_text: str — Truncated original error message.

    Returns:
        dict: Failure record with identity and error field.
    """
    record: dict = {
        "check_item_id": check_item.get("id"),
        "check_item_name": check_item.get("name"),
        "dimension": check_item.get("dimension"),
        "service_type_code": check_item.get("service_type_code"),
        "risk_level": check_item.get("risk_level"),
        "error": error_text[:2000],
    }
    return record


def process_check_item(
    check_item: dict,
    region: str,
    language: str,
    page_size: int,
    max_retries: int,
    retry_interval: int,
    timeout: int,
) -> dict:
    """Process one check item: trigger, query, and assemble a record.

    1. Trigger the check via StartItemCheck to get check_num; transient
       trigger errors are retried up to max_retries times.
    2. Fetch the paginated result via get_check_result.
    3. Assemble a success or failure record; never raise.

    Args:
        check_item: dict — Check item from ShowCheckItemList.
        region: str — Cloud region for the OA service.
        language: str — Request language (zh-cn or en-us).
        page_size: int — Resources per page.
        max_retries: int — Retry count for result queries and transient
            trigger failures.
        retry_interval: int — Seconds between retries.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        dict: Success or failure record for the check item.

    Examples:
        # >>> process_check_item({"id": "x"}, "cn-southwest-2", "zh-cn", 10, 0, 0, 5)
        # {'check_item_id': 'x', 'error': ...}
    """
    item_id = check_item.get("id")
    try:
        check_num = start_check(region, item_id, timeout, max_retries, retry_interval)
        result_data = get_check_result(
            region,
            language,
            item_id,
            check_num,
            page_size,
            max_retries,
            retry_interval,
            timeout,
        )
        record = _build_success_record(check_item, check_num, result_data)
        LOGGER.info(
            "Check item %s (%s) succeeded with %d resources",
            item_id,
            check_item.get("name"),
            len(record["resources"]),
        )
        return record
    except HcloudError as exc:
        LOGGER.error("Check item %s (%s) failed: %s", item_id, check_item.get("name"), str(exc)[:300])
        return _build_failure_record(check_item, str(exc))


def collect_results(
    check_items: list[dict],
    region: str,
    language: str,
    threads: int,
    page_size: int,
    max_retries: int,
    retry_interval: int,
    timeout: int,
) -> list[dict]:
    """Run all check items concurrently and merge results in original order.

    1. Submit one process_check_item task per check item to a thread pool.
    2. Wait for all tasks and collect them by index.
    3. Sort by original index to restore the list order.

    Args:
        check_items: list[dict] — All check items from ShowCheckItemList.
        region: str — Cloud region for the OA service.
        language: str — Request language (zh-cn or en-us).
        threads: int — Number of worker threads.
        page_size: int — Resources per page.
        max_retries: int — Retry count for result queries.
        retry_interval: int — Seconds between retries.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        list[dict]: Records in the same order as check_items; a failure in
            one item never blocks the others.

    Examples:
        >>> collect_results([], "cn-southwest-2", "zh-cn", 5, 10, 0, 0, 5)
        []
    """
    ordered_results: list[tuple[int, dict]] = []
    worker_count = max(1, threads)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                process_check_item,
                check_item,
                region,
                language,
                page_size,
                max_retries,
                retry_interval,
                timeout,
            ): index
            for index, check_item in enumerate(check_items)
        }
        for future in as_completed(future_map):
            index = future_map[future]
            try:
                record = future.result()
            except Exception as exc:  # defensive: process_check_item should not raise
                record = _build_failure_record(check_items[index], str(exc))
            ordered_results.append((index, record))
    ordered_results.sort(key=lambda pair: pair[0])
    return [record for _, record in ordered_results]


def _build_output_document(
    check_items: list[dict],
    records: list[dict],
    region: str,
    language: str,
    threads: int,
    page_size: int,
    output_path: str,
) -> dict:
    """Assemble the final output JSON document.

    1. Count succeeded and failed records.
    2. Build the meta block with run configuration and timestamps.
    3. Return the document with meta and results in original order.

    Args:
        check_items: list[dict] — All check items (for the total count).
        records: list[dict] — Collected records in original order.
        region: str — Cloud region used.
        language: str — Request language used.
        threads: int — Worker thread count used.
        page_size: int — Page size used.
        output_path: str — Output file path (absolute form included).

    Returns:
        dict: Output document with meta and results.

    Examples:
        >>> _build_output_document([{}], [{"error": "boom"}], "cn-southwest-2", "zh-cn", 5, 10, "out.json")["meta"]["failed"]
        1
    """
    succeeded = sum(1 for record in records if record.get("error") is None)
    failed = len(records) - succeeded
    now = datetime.now(timezone(timedelta(hours=8))).isoformat()
    meta: dict = {
        "region": region,
        "language": language,
        "generated_at": now,
        "check_item_total": len(check_items),
        "succeeded": succeeded,
        "failed": failed,
        "threads": threads,
        "page_size": page_size,
        "output_path": os.path.abspath(output_path),
    }
    document: dict = {"meta": meta, "results": records}
    return document


def write_output_document(document: dict, output_path: str) -> str:
    """Write the output document to a timestamped JSON file next to the script.

    1. Serialize with ensure_ascii=False and indent=2.
    2. Write to the fixed output path resolved at startup.
    3. Return the absolute path of the written file.

    Args:
        document: dict — Output document with meta and results.
        output_path: str — Absolute output file path resolved at startup.

    Returns:
        str: Absolute path of the written file.

    Examples:
        # >>> write_output_document({"meta": {}, "results": []}, "/abs/out.json")
        # '/abs/out.json'
    """
    absolute_path = os.path.abspath(output_path)
    parent_dir = os.path.dirname(absolute_path)
    if parent_dir and not os.path.isdir(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    with open(absolute_path, "w", encoding="utf-8") as file_handle:
        json.dump(document, file_handle, ensure_ascii=False, indent=2)
    return absolute_path


def main() -> int:
    """Orchestrate the full inspection workflow.

    1. Parse command line arguments.
    2. Set up logging and log start with the output absolute path.
    3. Fetch all check items, run them concurrently, and write the aggregated
       JSON document.
    4. Log completion counts and the output absolute path.

    Args:
        None

    Returns:
        int: Process exit code (0 on success, 1 on fatal failure).
    """
    parser = build_arg_parser()
    args = parser.parse_args()
    setup_logging(args.log_file)

    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    output_absolute = resolve_output_path(timestamp)
    LOGGER.info("Task started. Output file(s): %s", output_absolute)
    try:
        check_items = list_check_items(args.region, args.language, args.timeout)
        LOGGER.info("Fetched %d check items from region %s", len(check_items), args.region)
        records = collect_results(
            check_items,
            args.region,
            args.language,
            args.threads,
            args.page_size,
            args.max_retries,
            args.retry_interval,
            args.timeout,
        )
        document = _build_output_document(
            check_items,
            records,
            args.region,
            args.language,
            args.threads,
            args.page_size,
            output_absolute,
        )
        written_path = write_output_document(document, output_absolute)
        meta = document.get("meta", {})
        LOGGER.info(
            "Finished: %d succeeded, %d failed, %d total",
            meta.get("succeeded", 0),
            meta.get("failed", 0),
            meta.get("check_item_total", 0),
        )
        LOGGER.info("Task finished. Output file(s): %s", written_path)
        return 0
    except HcloudError as exc:
        LOGGER.error("Fatal error: %s", str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
