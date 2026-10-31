#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Shared helpers for the Huawei Cloud RDS single-to-HA scripts.

Overview:
    This module holds the logic shared by the step-split RDS scripts
    (list_instances.py, list_azs.py, pre_check.py, convert.py, resume.py):
    hcloud command execution, project id resolution, RDS command prefix
    building, report writing, recovery state persistence, pre-condition
    checks, backup/job polling, result verification and discovery output
    formatting. It is a library module and must not be run as a script.

Detailed Description:
    The single-to-HA workflow used to live in one monolithic script whose
    --help mixed every step's parameters. After the split, each step script
    exposes only its necessary command line arguments and delegates all
    shared behavior here, so verified cloud behavior stays in one place:
      - Command names and field paths were verified against a real cloud
        environment (see references/ in the skill root).
      - CreateManualBackup returns a `backup` object, not a job_id; backup
        progress is polled via ListBackups on `backups[0].status`.
      - ListJobInfo returns `{"job": {...}}`; `job.process` is an empty
        string when the job finishes, so completion is judged by
        `job.status == "Completed"`.
      - ListFlavors uses independent HA spec codes (e.g. `x.ha`); support is
        judged by the existence of the `.ha` flavor entry.
      - The `nodes` array order is not fixed; master/slave must be located
        by the `role` field.
      - Prepaid instances carry --single_to_ha.is_auto_pay=true so the
        price difference is paid automatically; on-demand instances omit it.
      - hcloud appends diagnostic text (error center link or table) after a
        JSON error object on API errors and still exits 0; run_hcloud
        extracts the leading JSON so the error code stays visible, and
        create_pre_backup retries with a fresh name on DBS.201201.
    Tuning values (poll intervals, limits, subprocess timeout) are module
    constants on purpose: the workflow scripts do not expose them as command
    line options, so users cannot accidentally diverge from the verified
    defaults. The manual backup name is NOT a constant: it is built per run
    by build_backup_name because RDS backup names are project-wide unique
    and a fixed name would collide.

Workflow:
    1. Provide the hcloud execution wrapper and error type.
    2. Resolve a region's project id via KeystoneListAuthProjects.
    3. Build the RDS command prefix for a resolved project.
    4. Write JSON reports and persist/load recovery state.
    5. Provide the pre-condition check functions.
    6. Provide the backup/job polling loops.
    7. Verify a converted instance and format discovery output.

Dependencies:
    - Python 3.9+ standard library only (json, logging, os, subprocess,
      time, datetime, uuid).
    - External: `hcloud` (KooCLI 7.2.2+) installed, configured and
      authenticated. The scripts do not check credentials themselves; the
      SKILL workflow verifies them with ListApiVersionNew beforehand.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone

LOGGER = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 60
DEFAULT_MAX_POLL_TIME = 3600
DEFAULT_BACKUP_POLL_INTERVAL = 30
DEFAULT_BACKUP_MAX_POLL_TIME = 3600
DEFAULT_PREPAID_POLL_INTERVAL = 30
DEFAULT_PREPAID_MAX_POLL_TIME = 900
DEFAULT_TIMEOUT = 120
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE_NAME = "rds_single_to_ha_result_{ts}.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"

# Verified command names (remote validation rounds 1-3).
CMD_LIST_API_VERSIONS = "ListApiVersionNew"
CMD_LIST_INSTANCES = "ListInstances"
CMD_LIST_FLAVORS = "ListFlavors"
CMD_SHOW_BACKUP_POLICY = "ShowBackupPolicy"
CMD_CREATE_MANUAL_BACKUP = "CreateManualBackup"
CMD_LIST_BACKUPS = "ListBackups"
CMD_START_SINGLE_TO_HA = "StartInstanceSingleToHaAction"
CMD_LIST_JOB_INFO = "ListJobInfo"
# Verified discovery command names (desktop validation, 2026-10-15).
CMD_LIST_AUTH_PROJECTS = "KeystoneListAuthProjects"
CMD_LIST_AVAILABILITY_ZONES = "NovaListAvailabilityZones"

# Charge modes returned by ListInstances.
CHARGE_MODE_PREPAID = "prePaid"
CHARGE_MODE_POSTPAID = "postPaid"

# Recovery state file suffix and phases.
STATE_FILE_SUFFIX = ".state.json"
PHASE_BACKUP = "backup"
PHASE_JOB = "job"


class HcloudError(Exception):
    """Raised when an hcloud call fails, times out, or returns no JSON."""


def _extract_leading_json(raw_output: str) -> dict | None:
    """Extract a leading JSON object from text that mixes JSON and junk.

    1. Locate the first opening brace in the text.
    2. Walk the text pairing braces to find the matching close brace.
    3. Parse the substring as JSON and return it, or None on any failure.

    Args:
        raw_output: str — The raw stdout text to scan.

    Returns:
        dict | None: The parsed leading JSON object, or None when no valid
            object is found.

    Examples:
        >>> _extract_leading_json('{"a": 1}\\n诊断文本')
        {'a': 1}
        >>> _extract_leading_json('no json here') is None
        True
    """
    start = raw_output.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(raw_output)):
        char = raw_output[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = raw_output[start : index + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
                if isinstance(parsed, dict):
                    return parsed
                return None
    return None


def run_hcloud(cmd_args: list[str], timeout: int) -> dict:
    """Run one hcloud subcommand and return its parsed JSON output.

    1. Build the full hcloud command and execute it via subprocess.
    2. Raise HcloudError when the process fails, output is not JSON, or the
       command times out; the original output text is preserved.
    3. When the output mixes a JSON error object with trailing diagnostics
       (hcloud appends an error center link or table after an API error),
       extract the leading JSON so the error code stays visible to callers.

    Args:
        cmd_args: list[str] — hcloud subcommand arguments (service and
            operation plus parameters, excluding the hcloud binary).
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        dict: Parsed JSON object returned by hcloud.

    Raises:
        HcloudError: When hcloud fails, output has no usable JSON, or times
            out.

    Examples:
        # When hcloud is unavailable, an HcloudError is raised:
        # >>> run_hcloud(["RDS", "ListInstances"], 5)
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
            "hcloud command failed (exit {}): {}".format(
                completed.returncode, detail
            )
        )

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        parsed = _extract_leading_json(raw_output)
        if parsed is not None:
            return parsed
        raise HcloudError(
            "hcloud returned non-JSON output: {}".format(raw_output)
        ) from None


def extract_error_message(payload: dict) -> str:
    """Extract a readable error message from an hcloud error payload.

    1. Read the error_msg and error_code fields when present.
    2. Return the message, or a fallback string otherwise.

    Args:
        payload: dict — The parsed hcloud JSON payload.

    Returns:
        str: Readable error description.

    Examples:
        >>> extract_error_message({"error_code": "DBS.200543", "error_msg": "Task not found."})
        'DBS.200543: Task not found.'
    """
    if "error_msg" in payload or "error_code" in payload:
        code = payload.get("error_code", "")
        msg = payload.get("error_msg", "")
        if code and msg:
            return "{}: {}".format(code, msg)
        return msg or code or "unknown hcloud error"
    return "no error information in payload"


def extract_project_id(payload: dict, region: str) -> str:
    """Extract the project id of a region from an auth projects payload.

    1. Read the projects list from the KeystoneListAuthProjects payload.
    2. Return the id of the first project whose name equals the region.

    Args:
        payload: dict — The parsed KeystoneListAuthProjects JSON payload.
        region: str — The region code (e.g. cn-north-4).

    Returns:
        str: The matching project id, or an empty string when not found.

    Examples:
        >>> extract_project_id({"projects": [{"id": "p1", "name": "cn-north-4"}]}, "cn-north-4")
        'p1'
        >>> extract_project_id({"projects": [{"id": "p1", "name": "cn-east-2"}]}, "cn-north-4")
        ''
    """
    projects = payload.get("projects") or []
    for project in projects:
        if project.get("name") == region:
            return project.get("id", "")
    return ""


def resolve_project_id(region: str, timeout: int) -> str:
    """Resolve the project id of a region via KeystoneListAuthProjects.

    1. Build and run the KeystoneListAuthProjects command.
    2. Extract the project id matching the region name.
    3. Raise HcloudError with the accessible project names when not found.

    Args:
        region: str — The region code to resolve.
        timeout: int — Timeout in seconds for the subprocess call.

    Returns:
        str: The resolved project id.

    Raises:
        HcloudError: When no project name matches the region.

    Examples:
        # When the region is not in the payload, an HcloudError is raised:
        # >>> resolve_project_id("cn-north-4", 5)
        # Traceback (most recent call last):
        # HcloudError: ...
    """
    iam_prefix = ["IAM", "--cli-region={}".format(region)]
    payload = run_hcloud(iam_prefix + [CMD_LIST_AUTH_PROJECTS], timeout)
    project_id = extract_project_id(payload, region)
    if not project_id:
        projects = payload.get("projects") or []
        names = ", ".join(p.get("name", "") for p in projects if p.get("name"))
        raise HcloudError(
            "no project named {} in KeystoneListAuthProjects; accessible "
            "projects: {}".format(region, names or "(none)")
        )
    return project_id


def make_rds_prefix(region: str, project_id: str) -> list[str]:
    """Build the base RDS hcloud command prefix for a resolved project.

    1. Join the RDS service name, region flag and project id flag.

    Args:
        region: str — The cloud region code.
        project_id: str — The resolved project id of the region.

    Returns:
        list[str]: Command prefix for RDS operations.

    Examples:
        >>> make_rds_prefix("cn-north-4", "p1")
        ['RDS', '--cli-region=cn-north-4', '--project_id=p1']
    """
    return [
        "RDS",
        "--cli-region={}".format(region),
        "--project_id={}".format(project_id),
    ]


def resolve_output_path(timestamp: str) -> str:
    """Resolve the absolute output file path in the script directory.

    1. Join the script directory with the timestamped file name.
    2. Return the absolute path of the output file.

    Args:
        timestamp: str — Formatted timestamp string for the file name.

    Returns:
        str: Absolute output file path.

    Examples:
        >>> resolve_output_path("2026_10_15_14_30_00").endswith("rds_single_to_ha_result_2026_10_15_14_30_00.json")
        True
    """
    return os.path.join(SCRIPT_DIR, OUTPUT_FILE_NAME.format(ts=timestamp))


def timestamp_now() -> str:
    """Return the current local time formatted for file names.

    Args:
        None

    Returns:
        str: Timestamp string like 2026_10_15_14_30_00.

    Examples:
        >>> len(timestamp_now()) == len("2026_10_15_14_30_00")
        True
    """
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def write_report(report: dict, output: str | None, ts: str) -> int:
    """Write the report dict to a JSON file and return an exit code.

    1. Resolve the output path (explicit or timestamped default).
    2. Write the JSON report with UTF-8 encoding.

    Args:
        report: dict — The report payload.
        output: str | None — Explicit output path, or None for default.
        ts: str — Timestamp used for the default file name.

    Returns:
        int: Exit code, 0 on success and 1 when writing fails.

    Examples:
        # >>> write_report({"a": 1}, None, "2026_10_15_14_30_00")
        # 0
    """
    if output:
        path = output
    else:
        path = resolve_output_path(ts)
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
    except OSError as exc:
        LOGGER.error("Failed to write report %s: %s", path, exc)
        return 1
    LOGGER.info("Report written to %s", path)
    return 0


def state_path_for(output: str | None) -> str:
    """Return the recovery state file path for a report output path.

    1. Use the explicit output path or resolve the default one.
    2. Append the state file suffix to the report path.

    Args:
        output: str | None — Explicit report output path, or None.

    Returns:
        str: The absolute state file path.

    Examples:
        >>> state_path_for("r.json")
        'r.json.state.json'
    """
    if output:
        return output + STATE_FILE_SUFFIX
    return resolve_output_path("1") + STATE_FILE_SUFFIX


def save_state(path: str, state: dict) -> None:
    """Write a recovery state dict to a file atomically.

    1. Serialize the state dict as JSON.
    2. Write to a temporary sibling file then replace the target.

    Args:
        path: str — Target state file path.
        state: dict — State dict to persist.

    Returns:
        None

    Raises:
        OSError: When the state file cannot be written.

    Examples:
        # >>> save_state("s.state.json", {"phase": "job"})
        # no output; the state file is written.
    """
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def clear_state(path: str) -> None:
    """Remove a recovery state file if it exists.

    1. Delete the file at the given path, ignoring a missing file.

    Args:
        path: str — State file path to remove.

    Returns:
        None

    Examples:
        # >>> clear_state("s.state.json")
        # no output; the state file is removed if present.
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def load_state(path: str) -> dict | None:
    """Load a recovery state dict from a file.

    1. Read and parse the JSON state file.
    2. Return None when the file is missing or not valid JSON.

    Args:
        path: str — State file path to read.

    Returns:
        dict | None: The parsed state dict, or None.

    Examples:
        # With a written state file the dict is returned:
        # >>> load_state("s.state.json")
        # {'phase': 'job'}
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def is_state_valid(
    state: dict, instance_id: str, region: str, max_age: int
) -> bool:
    """Check whether a recovery state still matches the run context.

    1. Verify the instance id and region match the command line.
    2. Verify the state is not older than the maximum polling time.

    Args:
        state: dict — The loaded recovery state dict.
        instance_id: str — The target instance id from the command line.
        region: str — The region from the command line.
        max_age: int — Maximum allowed age in seconds.

    Returns:
        bool: True when the state is usable for recovery.

    Examples:
        >>> import time as _time
        >>> fresh = _time.monotonic()
        >>> is_state_valid({"instance_id": "i", "region": "r", "started_at": fresh}, "i", "r", 3600)
        True
        >>> is_state_valid({"instance_id": "x", "region": "r", "started_at": fresh}, "i", "r", 3600)
        False
        >>> is_state_valid({"instance_id": "i", "region": "r", "started_at": fresh - 4000.0}, "i", "r", 3600)
        False
    """
    if state.get("instance_id") != instance_id:
        return False
    if state.get("region") != region:
        return False
    started_at = state.get("started_at")
    if not isinstance(started_at, (int, float)):
        return False
    if time.monotonic() - started_at > max_age:
        return False
    return True


def check_instance_status(data: dict) -> tuple[bool, str, str, str]:
    """Check that the instance is an ACTIVE single instance.

    1. Read the first instance from the ListInstances payload.
    2. Verify status is ACTIVE and type is Single.

    Args:
        data: dict — The parsed ListInstances JSON payload.

    Returns:
        tuple[bool, str, str, str]: (pass, status, type, detail) where
            status and type are the observed values.

    Examples:
        >>> ok, st, ty, _ = check_instance_status({"instances": [{"status": "ACTIVE", "type": "Single"}]})
        >>> ok
        True
    """
    instances = data.get("instances") or []
    if not instances:
        return False, "", "", "no instance returned by ListInstances"
    instance = instances[0]
    status = instance.get("status", "")
    inst_type = instance.get("type", "")
    detail = "status={}, type={}".format(status, inst_type)
    if status != "ACTIVE":
        return False, status, inst_type, detail + "; expected status ACTIVE"
    if inst_type != "Single":
        return False, status, inst_type, detail + "; expected type Single"
    return True, status, inst_type, detail


def check_flavor_support(data: dict, flavor_ref: str, target_az: str) -> tuple[bool, str, str]:
    """Check that the instance flavor supports single-to-HA (plan b).

    1. Search ListFlavors payload for an entry whose spec_code equals
       `{flavor_ref}.ha`.
    2. Verify that entry exists and its az_status marks the target AZ normal.

    Args:
        data: dict — The parsed ListFlavors JSON payload.
        flavor_ref: str — The instance flavor code (e.g. rds.mysql.n1.large.2).
        target_az: str — The target availability zone code.

    Returns:
        tuple[bool, str, str]: (pass, ha_spec_code, detail).

    Examples:
        >>> ok, code, _ = check_flavor_support({"flavors": [{"spec_code": "x.ha", "az_status": {"az-a": "normal"}}]}, "x", "az-a")
        >>> ok
        True
    """
    flavors = data.get("flavors") or []
    ha_spec_code = "{}.ha".format(flavor_ref)
    entry = next((f for f in flavors if f.get("spec_code") == ha_spec_code), None)
    if entry is None:
        return False, ha_spec_code, "ha spec {} not found in ListFlavors".format(ha_spec_code)
    az_status = entry.get("az_status") or {}
    if az_status.get(target_az) != "normal":
        return (
            False,
            ha_spec_code,
            "target AZ {} not available for {}: {}".format(
                target_az, ha_spec_code, az_status.get(target_az)
            ),
        )
    return True, ha_spec_code, "ha spec {} available in AZ {}".format(ha_spec_code, target_az)


def check_backup_policy(data: dict) -> tuple[bool, int, str]:
    """Check that automatic backup is enabled.

    1. Read backup_policy.keep_days from the ShowBackupPolicy payload.
    2. Verify it is greater than 0.

    Args:
        data: dict — The parsed ShowBackupPolicy JSON payload.

    Returns:
        tuple[bool, int, str]: (pass, keep_days, detail).

    Examples:
        >>> ok, days, _ = check_backup_policy({"backup_policy": {"keep_days": 7}})
        >>> ok
        True
    """
    policy = data.get("backup_policy") or {}
    keep_days = policy.get("keep_days", 0)
    if keep_days <= 0:
        return False, keep_days, "backup policy keep_days is {}".format(keep_days)
    return True, keep_days, "backup policy keep_days={} (enabled)".format(keep_days)


def parse_backup_duration(begin_time: str, end_time: str) -> float | None:
    """Compute the backup duration in seconds from two ISO timestamps.

    1. Parse the begin and end timestamps in ISO 8601 form
       (e.g. 2026-10-21T17:11:09+0000).
    2. Return the positive difference in seconds, or None when either
       timestamp is missing or unparsable.

    Args:
        begin_time: str — The backup begin timestamp.
        end_time: str — The backup end timestamp.

    Returns:
        float | None: Duration in seconds, or None on parse failure.

    Examples:
        >>> parse_backup_duration("2026-10-21T17:11:09+0000", "2026-10-21T17:13:10+0000")
        121.0
        >>> parse_backup_duration("bad", "2026-10-21T17:13:10+0000") is None
        True
    """
    try:
        begin = datetime.strptime(begin_time, "%Y-%m-%dT%H:%M:%S%z")
        end = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S%z")
    except (TypeError, ValueError):
        return None
    return max(0.0, (end - begin).total_seconds())


def get_backup_time_reference(
    region: str,
    project_id: str,
    instance_id: str,
    volume_size_gb: float | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    """Get a reference for how long one full backup of the instance takes.

    1. Query ListBackups with backup_type=auto and use the first record
       (the API returns begin_time-descending) as the primary reference.
    2. When no automatic backup exists, query backup_type=manual and use
       the first record as a supplementary reference.
    3. When no backup record exists at all, estimate the duration from the
       storage size: size (GB) * 1024 / 100 seconds, and mark it
       conservative because the measured estimate runs ~3.4x larger than
       the actual duration.

    Args:
        region: str — The cloud region code.
        project_id: str — The resolved project id of the region.
        instance_id: str — The target RDS instance id.
        volume_size_gb: float | None — The instance storage size in GB,
            used only for the no-record estimate.
        timeout: int — Timeout in seconds for each subprocess call.

    Returns:
        dict: Reference with source, seconds and a human note.

    Examples:
        # Requires hcloud credentials:
        # >>> get_backup_time_reference("cn-north-4", "p1", "i1")
        # {'source': ..., 'seconds': ..., 'note': ...}
    """
    cmd_prefix = make_rds_prefix(region, project_id)

    def first_backup_duration(backup_type: str) -> float | None:
        """Return the first backup duration for a backup type, or None."""
        payload = run_hcloud(
            cmd_prefix
            + [
                CMD_LIST_BACKUPS,
                "--instance_id={}".format(instance_id),
                "--backup_type={}".format(backup_type),
            ],
            timeout,
        )
        backups = payload.get("backups") or []
        if not backups:
            return None
        first = backups[0]
        return parse_backup_duration(
            first.get("begin_time", ""), first.get("end_time", "")
        )

    auto_seconds = first_backup_duration("auto")
    if auto_seconds is not None:
        return {
            "source": "auto",
            "seconds": round(auto_seconds, 1),
            "note": "latest automatic backup duration",
        }
    manual_seconds = first_backup_duration("manual")
    if manual_seconds is not None:
        return {
            "source": "manual",
            "seconds": round(manual_seconds, 1),
            "note": "latest manual backup duration",
        }
    if volume_size_gb is not None:
        estimate = float(volume_size_gb) * 1024 / 100
        return {
            "source": "estimate",
            "seconds": round(estimate, 1),
            "note": "conservative estimate from storage size; actual "
            "usually shorter",
        }
    return {
        "source": "unknown",
        "seconds": None,
        "note": "no backup record and no storage size available",
    }


def format_discovery_json(instances: list[dict], zones: list[dict]) -> str:
    """Format a discovery payload as pretty JSON for stdout.

    1. Pick the instances or the zones list depending on which is non-empty.
    2. Return an empty array marker when both lists are empty.
    3. Serialize with indentation, UTF-8 safe and sorted keys.

    Args:
        instances: list[dict] — Instances from the ListInstances payload.
        zones: list[dict] — Zones from the NovaListAvailabilityZones payload.

    Returns:
        str: Pretty printed JSON text.

    Examples:
        >>> text = format_discovery_json([{"id": "i1"}], [])
        >>> text.startswith("[\\n  {\\n    \\"id\\": \\"i1\\"")
        True
        >>> format_discovery_json([], []) == "[]"
        True
    """
    items = zones if not instances else instances
    if not items:
        return "[]"
    return json.dumps(items, indent=2, ensure_ascii=False, sort_keys=True)


def build_backup_name(instance_id: str) -> str:
    """Build a project-unique manual backup name for the conversion.

    1. Take the first 8 characters of the instance id.
    2. Append a UTC timestamp and a short random uuid suffix.
    3. Join them with the fixed backup name prefix.

    Args:
        instance_id: str — The target RDS instance id.

    Returns:
        str: A backup name like
            pre_single_to_ha_backup_{id8}_{ts14}_{uuid4} (52 chars).

    Examples:
        >>> name = build_backup_name("fe1bec8a73284cb1")
        >>> name.startswith("pre_single_to_ha_backup_fe1bec8a_")
        True
        >>> len(name) <= 64
        True
        >>> name != build_backup_name("fe1bec8a73284cb1")
        True
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    short_id = (instance_id or "x")[:8]
    suffix = uuid.uuid4().hex[:4]
    return "pre_single_to_ha_backup_{}_{}_{}".format(short_id, ts, suffix)


def create_pre_backup(
    cmd: list[str], timeout: int, instance_id: str, max_retry: int = 3
) -> tuple[str, dict]:
    """Create a manual backup and return its backup id.

    1. Call CreateManualBackup and read backup.id from the payload.
    2. When the error code is DBS.201201 (backup name already exists),
       rebuild the name with build_backup_name and retry.
    3. Return the id with the raw payload, or raise for other errors.

    Args:
        cmd: list[str] — The fully built CreateManualBackup command.
        timeout: int — Timeout in seconds for the subprocess call.
        instance_id: str — The target RDS instance id, used to rebuild the
            backup name on a name collision retry.
        max_retry: int — Maximum number of CreateManualBackup attempts
            (default 3).

    Returns:
        tuple[str, dict]: (backup_id, backup_payload).

    Raises:
        HcloudError: When the backup id is missing after all retries, or
            when a non-collision error is returned.

    Examples:
        # When hcloud returns no backup object, an HcloudError is raised:
        # >>> create_pre_backup([...], 5, "i1")
        # Traceback (most recent call last):
        # HcloudError: ...
    """
    for attempt in range(max_retry):
        payload = run_hcloud(cmd, timeout)
        backup = payload.get("backup") or {}
        backup_id = backup.get("id", "")
        if backup_id:
            return backup_id, backup
        if payload.get("error_code") == "DBS.201201":
            LOGGER.warning("Backup name collision (DBS.201201); retrying.")
            cmd = [c for c in cmd if not c.startswith("--name=")]
            cmd.append("--name={}".format(build_backup_name(instance_id)))
            continue
        raise HcloudError(
            "CreateManualBackup failed: {}".format(
                json.dumps(payload, ensure_ascii=False)
            )
        )
    raise HcloudError(
        "CreateManualBackup still failed after {} attempts".format(max_retry)
    )


def poll_backup_status(
    cmd_prefix: list[str],
    backup_id: str,
    poll_interval: int,
    max_poll_time: int,
    timeout: int,
) -> tuple[str, str]:
    """Poll the manual backup status until it completes or fails.

    1. Repeatedly call ListBackups filtered by backup id.
    2. Return when backups[0].status is COMPLETED or FAILED, or on timeout.

    Args:
        cmd_prefix: list[str] — ListBackups command up to the backup id arg.
        backup_id: str — The manual backup id to poll.
        poll_interval: int — Seconds between polls.
        max_poll_time: int — Maximum polling time in seconds.
        timeout: int — Timeout for each subprocess call.

    Returns:
        tuple[str, str]: (status, detail).

    Examples:
        # With a stubbed run_hcloud the function returns COMPLETED:
        # >>> poll_backup_status([...], "b1", 0, 10, 5)
        # ('COMPLETED', '...')
    """
    command = cmd_prefix + ["--backup_id={}".format(backup_id)]
    deadline = time.monotonic() + max_poll_time
    last_status = ""
    while True:
        payload = run_hcloud(command, timeout)
        backups = payload.get("backups") or []
        if not backups:
            raise HcloudError(
                "ListBackups returned no backup for id {}: {}".format(
                    backup_id, json.dumps(payload)
                )
            )
        last_status = backups[0].get("status", "")
        LOGGER.info("Backup %s status: %s", backup_id, last_status)
        if last_status in ("COMPLETED", "FAILED"):
            return last_status, "backup {} status={}".format(backup_id, last_status)
        if time.monotonic() >= deadline:
            return "TIMEOUT", "backup {} still {} after {}s".format(
                backup_id, last_status or "unknown", max_poll_time
            )
        time.sleep(poll_interval)


def execute_single_to_ha(
    cmd_prefix: list[str], target_az: str, charge_mode: str
) -> list[str]:
    """Build and run the StartInstanceSingleToHaAction command.

    1. Build the command with the nested single_to_ha arguments.
    2. Append the auto-pay flag only for prepaid instances.

    Args:
        cmd_prefix: list[str] — StartInstanceSingleToHaAction command prefix.
        target_az: str — The target availability zone for the standby node.
        charge_mode: str — The instance charge mode (prePaid or postPaid).

    Returns:
        list[str]: The full command arguments to execute.

    Examples:
        >>> cmd_prefix = ["RDS", "StartInstanceSingleToHaAction", "--cli-region=cn-north-4"]
        >>> cmd = execute_single_to_ha(cmd_prefix, "az-b", "postPaid")
        >>> "--single_to_ha.az_code_new_node=az-b" in cmd
        True
        >>> cmd2 = execute_single_to_ha(cmd_prefix, "az-b", "prePaid")
        >>> "--single_to_ha.is_auto_pay=true" in cmd2
        True
        >>> "--single_to_ha.is_auto_pay=true" in cmd
        False
    """
    command = cmd_prefix + ["--single_to_ha.az_code_new_node={}".format(target_az)]
    if charge_mode == CHARGE_MODE_PREPAID:
        command.append("--single_to_ha.is_auto_pay=true")
    return command


def poll_job_status(
    cmd_prefix: list[str],
    job_id: str,
    poll_interval: int,
    max_poll_time: int,
    timeout: int,
) -> tuple[str, str, float]:
    """Poll the conversion job status until it completes or fails.

    1. Repeatedly call ListJobInfo filtered by job id.
    2. Return when job.status is Completed or Failed, or on timeout.

    Args:
        cmd_prefix: list[str] — ListJobInfo command up to the job id arg.
        job_id: str — The job id to poll.
        poll_interval: int — Seconds between polls.
        max_poll_time: int — Maximum polling time in seconds.
        timeout: int — Timeout for each subprocess call.

    Returns:
        tuple[str, str, float]: (status, detail, elapsed_seconds).

    Examples:
        # With a stubbed run_hcloud the function returns Completed:
        # >>> poll_job_status([...], "j1", 0, 10, 5)
        # ('Completed', '...', 0.0)
    """
    command = cmd_prefix + ["--id={}".format(job_id)]
    deadline = time.monotonic() + max_poll_time
    start = time.monotonic()
    last_status = ""
    while True:
        payload = run_hcloud(command, timeout)
        job = payload.get("job") or {}
        last_status = job.get("status", "")
        LOGGER.info("Job %s status: %s process: %s", job_id, last_status, job.get("process", ""))
        if last_status == "Completed":
            return "Completed", "job {} completed".format(job_id), time.monotonic() - start
        if last_status == "Failed":
            reason = job.get("fail_reason", "")
            return (
                "Failed",
                "job {} failed: {}".format(job_id, reason or "unknown reason"),
                time.monotonic() - start,
            )
        if time.monotonic() >= deadline:
            return (
                "TIMEOUT",
                "job {} still {} after {}s; check the console".format(
                    job_id, last_status or "unknown", max_poll_time
                ),
                time.monotonic() - start,
            )
        time.sleep(poll_interval)


def poll_prepaid_conversion(
    cmd_prefix: list[str],
    instance_id: str,
    poll_interval: int,
    max_poll_time: int,
    timeout: int,
) -> tuple[str, str, float]:
    """Poll a prepaid single-to-HA conversion via the instance state.

    1. Repeatedly call ListInstances filtered by instance id.
    2. Phase A: wait until status leaves ACTIVE (the conversion started).
    3. Phase B: wait until type is Ha and status is ACTIVE (the conversion
       completed), then return Completed; return TIMEOUT on the deadline.

    Args:
        cmd_prefix: list[str] — ListInstances command up to the instance id
            arg.
        instance_id: str — The target instance id to poll.
        poll_interval: int — Seconds between polls.
        max_poll_time: int — Maximum polling time in seconds.
        timeout: int — Timeout for each subprocess call.

    Returns:
        tuple[str, str, float]: (status, detail, elapsed_seconds).

    Examples:
        # With a stubbed run_hcloud the function returns Completed:
        # >>> poll_prepaid_conversion([...], "i1", 0, 10, 5)
        # ('Completed', '...', 0.0)
    """
    command = cmd_prefix + ["--id={}".format(instance_id)]
    deadline = time.monotonic() + max_poll_time
    start = time.monotonic()
    conversion_started = False
    last_type = ""
    last_status = ""
    while True:
        payload = run_hcloud(command, timeout)
        instance = (payload.get("instances") or [{}])[0]
        last_type = instance.get("type", "")
        last_status = instance.get("status", "")
        LOGGER.info(
            "Prepaid conversion for %s: type=%s status=%s",
            instance_id,
            last_type,
            last_status,
        )
        if not conversion_started:
            if last_status != "ACTIVE":
                conversion_started = True
                LOGGER.info(
                    "Prepaid conversion %s started (status %s).",
                    instance_id,
                    last_status,
                )
        elif last_type == "Ha" and last_status == "ACTIVE":
            return (
                "Completed",
                "prepaid conversion {} completed".format(instance_id),
                time.monotonic() - start,
            )
        if time.monotonic() >= deadline:
            return (
                "TIMEOUT",
                "prepaid conversion {} still type={} status={} after {}s; "
                "check the console".format(
                    instance_id, last_type, last_status, max_poll_time
                ),
                time.monotonic() - start,
            )
        time.sleep(poll_interval)


def verify_conversion_result(data: dict) -> tuple[bool, dict]:
    """Verify the converted instance is a healthy HA instance.

    1. Read the first instance from the ListInstances payload.
    2. Verify type is Ha, status is ACTIVE and ha is non-empty.
    3. Locate master and slave nodes by role; when they are in different
       AZs set az_verified, when in the same AZ set same_az instead.

    Args:
        data: dict — The parsed ListInstances JSON payload.

    Returns:
        tuple[bool, dict]: (pass, verification detail dict).

    Examples:
        >>> inst = {"type": "Ha", "status": "ACTIVE", "ha": {"replication_mode": "semisync"},
        ...         "nodes": [{"role": "master", "availability_zone": "az-a", "status": "ACTIVE"},
        ...                   {"role": "slave", "availability_zone": "az-b", "status": "ACTIVE"}]}
        >>> ok, _ = verify_conversion_result({"instances": [inst]})
        >>> ok
        True
    """
    instances = data.get("instances") or []
    detail: dict = {}
    if not instances:
        return False, {"error": "no instance returned by ListInstances"}
    instance = instances[0]
    inst_type = instance.get("type", "")
    status = instance.get("status", "")
    ha = instance.get("ha") or {}
    detail = {
        "instance_type": inst_type,
        "instance_status": status,
        "ha": ha,
    }
    if inst_type != "Ha" or status != "ACTIVE" or not ha:
        detail["error"] = "expected type=Ha, status=ACTIVE, non-empty ha"
        return False, detail
    nodes = instance.get("nodes") or []
    master = next((n for n in nodes if n.get("role") == "master"), None)
    slave = next((n for n in nodes if n.get("role") == "slave"), None)
    if master is None or slave is None:
        detail["error"] = "master/slave nodes not found by role"
        return False, detail
    master_az = master.get("availability_zone", "")
    slave_az = slave.get("availability_zone", "")
    detail["primary_az"] = master_az
    detail["standby_az"] = slave_az
    detail["nodes"] = nodes
    if master.get("status") != "ACTIVE" or slave.get("status") != "ACTIVE":
        detail["error"] = "master/slave node not ACTIVE"
        return False, detail
    if master_az == slave_az:
        detail["same_az"] = True
        return True, detail
    detail["az_verified"] = True
    return True, detail
