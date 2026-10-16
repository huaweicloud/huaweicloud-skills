#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Merge OA, Config and SecMaster inspection results into one OA-format JSON.

Overview:
    This script converts the Config and SecMaster inspection results into the
    OA result format and merges them with the OA results themselves into a
    single JSON file, marking the cloud service source of every record for the
    downstream tenant inspection report.

Detailed Description:
    1. The script reads three input JSON files whose absolute paths are passed
       in explicitly via --oa-file, --config-file and --secmaster-file; it
       never scans directories for timestamped files, because the output
       directory may hold results of multiple inspection runs.
    2. Config records are converted per state: each resource-level compliance
       state becomes one OA-format record, with the rule-level judgment
       standard (assignment.description) copied into
       summary.check_item_description. OA fields that have no counterpart in
       the Config source are left empty; no data is fabricated.
    3. SecMaster records are converted per baseline record: each data_object
       becomes one OA-format record with dimension fixed to Security and
       risk_level derived from the source severity enum (High -> high, Low ->
       low), the original severity kept in summary.check_item_severity, and
       the source workspace instance name (resolved from the top-level
       workspaces array, workspace_id fallback) kept in workspace_name;
       remaining OA fields without a counterpart are left empty.
    4. OA records pass through unchanged except for the source marker.
    5. Every merged record carries a source field (OA / Config / SecMaster).
    6. Config failures and the daily compliance trend are preserved verbatim
       on the meta side (failures.config and trends.config_daily) instead of
       being disguised as OA records.
    7. The merged data is written to a timestamped JSON file next to the
       script, and a summary is emitted to stderr via logging.

Workflow:
    1. Parse the command-line arguments and validate the required input files.
    2. Set up logging to stderr with an optional file handler.
    3. Load the three input JSON files.
    4. Convert Config and SecMaster records and merge all three sources.
    5. Write the merged JSON file and emit the summary via logging.

Dependencies:
    Python standard library only: json, argparse, logging, datetime, pathlib,
    sys. No third-party dependencies. The script is purely local and does not
    call hcloud or access the network.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


# Constants
SOURCE_OA = "OA"
SOURCE_CONFIG = "Config"
SOURCE_SECMASTER = "SecMaster"
# SecMaster baseline records all belong to the security dimension and carry a
# severity enum (High / Low) that maps to the OA risk level vocabulary.
DIMENSION_SECURITY = "Security"
RISK_LEVEL_MAP = {
    "High": "high",
    "Low": "low",
}
# Output file is written next to the script with a timestamped name.
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_FILE_NAME = "merge_inspection_results_{ts}.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"
# Deduplication blacklists: entries whose inspection items duplicate OA /
# Config items are filtered out of Config and SecMaster records before the
# merge. Default blacklists live under references/blacklists of the project
# root (the parent of the scripts directory).
PROJECT_ROOT = SCRIPT_DIR.parent
BLACKLIST_DIR = PROJECT_ROOT / "references" / "blacklists"
CONFIG_BLACKLIST_NAME = "config_blacklist.json"
SECMASTER_BLACKLIST_NAME = "secmaster_blacklist.json"


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


def load_json_file(file_path: str) -> Any:
    """Load and parse a JSON input file.

    1. Read the file as UTF-8 text.
    2. Parse it as JSON; on any failure raise a ValueError that names the
       file path so the user can locate the bad input.

    Args:
        file_path: str — Absolute path of the JSON input file.

    Returns:
        Any: The parsed JSON object (dict or list).

    Raises:
        ValueError: The file does not exist or its content is not valid JSON.

    Examples:
        # >>> load_json_file("oa_risk_inspection_results_2026_10_12_15_29_43.json")
        # {'meta': {...}, 'results': [...]}
    """
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Input file cannot be read: {file_path} ({exc})") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Input file is not valid JSON: {file_path} ({exc})") from exc


def _convert_config_state(state: Dict[str, Any],
                          summary_counts: Dict[str, int],
                          rule_description: str = "") -> Dict[str, Any]:
    """Convert one Config resource-level compliance state into an OA record.

    1. Map the OA identity fields from the Config state: check_item_id from
       policy_assignment_id, check_item_name from policy_assignment_name,
       service_type_code from the lowercased resource_provider.
    2. Leave dimension, risk_level and check_num empty because the Config
       source has no counterpart for them.
    3. Build the summary with check_item_status derived from the compliance
       state, the rule-level compliance counts and the rule-level description
       (the judgment standard text shared by all states of the same rule).
    4. Build a single resource entry from the state and attach error null.

    Args:
        state: dict[str, Any] — One resource-level compliance result.
        summary_counts: dict[str, int] — The rule-level compliant /
            non_compliant / total counts.
        rule_description: str — The rule-level assignment.description text
            shared by all states of the same rule.

    Returns:
        dict[str, Any]: The OA-format record with a source marker.

    Examples:
        # >>> _convert_config_state({"compliance_state": "NonCompliant"}, {"total": 1})
        # {'check_item_id': '', 'summary': {'check_item_status': 'risk', ...}}
    """
    provider = state.get("resource_provider", "") or ""
    status = "risk" if state.get("compliance_state") == "NonCompliant" else "qualified"
    record: Dict[str, Any] = {
        "check_item_id": state.get("policy_assignment_id", "") or "",
        "check_item_name": state.get("policy_assignment_name", "") or "",
        "dimension": "",
        "service_type_code": provider.lower(),
        "risk_level": "",
        "check_num": "",
        "summary": {
            "check_item_status": status,
            "check_item_description": rule_description,
            "config_compliance_summary": summary_counts,
        },
        "resources": [
            {
                "id": state.get("resource_id", "") or "",
                "name": state.get("resource_name", "") or "",
                "domain_id": state.get("domain_id", "") or "",
                "region_id": state.get("region_id", "") or "",
                "status": state.get("compliance_state", "") or "",
                "tags": "",
                "enterprise_project_id": "",
                "extended_properties": "",
            }
        ],
        "error": None,
        "source": SOURCE_CONFIG,
    }
    return record


def _convert_secmaster_record(data_object: Dict[str, Any],
                              workspace_name: str = "") -> Dict[str, Any]:
    """Convert one SecMaster baseline data_object into an OA record.

    1. Map the OA identity fields from the data_object: check_item_id from
       checkitem_id, check_item_name from title, service_type_code from the
       lowercased resource provider.
    2. Set dimension to the fixed DIMENSION_SECURITY value because SecMaster
       baselines all belong to the security dimension.
    3. Derive risk_level from the data_object severity enum via RISK_LEVEL_MAP
       (High -> high, Low -> low); leave it empty for unknown severities and
       keep the original severity in summary.check_item_severity for trace.
    4. Build the summary with check_item_status taken verbatim from
       handle_status and the description / advice text.
    5. Attach the source instance name via the workspace_name field; empty
       input keeps it empty.
    6. Build a single resource entry from the embedded resource object and
       attach error null.

    Args:
        data_object: dict[str, Any] — One baseline inspection data_object.
        workspace_name: str — The display name of the source SecMaster
            workspace instance (may be empty).

    Returns:
        dict[str, Any]: The OA-format record with a source marker.

    Examples:
        # >>> _convert_secmaster_record({"handle_status": "risk", "severity": "High"})
        # {'check_item_id': '', 'dimension': 'Security', 'risk_level': 'high', 'summary': {'check_item_status': 'risk', ...}}
    """
    resource = data_object.get("resource", {}) or {}
    provider = resource.get("provider", "") or ""
    severity = data_object.get("severity", "") or ""
    record: Dict[str, Any] = {
        "check_item_id": data_object.get("checkitem_id", "") or "",
        "check_item_name": data_object.get("title", "") or "",
        "dimension": DIMENSION_SECURITY,
        "service_type_code": provider.lower(),
        "risk_level": RISK_LEVEL_MAP.get(severity, ""),
        "check_num": "",
        "summary": {
            "check_item_status": data_object.get("handle_status", "") or "",
            "check_item_description": data_object.get("description", "") or "",
            "check_item_advice": data_object.get("advice", "") or "",
            "check_item_severity": severity,
        },
        "workspace_name": workspace_name,
        "resources": [
            {
                "id": resource.get("id", "") or "",
                "name": resource.get("name", "") or "",
                "domain_id": resource.get("domain_id", "") or "",
                "region_id": resource.get("region_id", "") or "",
                "status": data_object.get("handle_status", "") or "",
                "tags": "",
                "enterprise_project_id": "",
                "extended_properties": "",
            }
        ],
        "error": None,
        "source": SOURCE_SECMASTER,
    }
    return record


def _convert_config(config_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert all Config states into OA-format records.

    1. Iterate over every assignment record.
    2. Convert each resource-level state with the assignment summary counts
       and the rule-level description.
    3. Return the flattened list of OA-format records.

    Args:
        config_data: dict[str, Any] — The parsed Config inspection JSON.

    Returns:
        list[dict[str, Any]]: OA-format records for every Config state.

    Examples:
        # >>> _convert_config({"assignments": []})
        # []
    """
    records: List[Dict[str, Any]] = []
    for record in config_data.get("assignments", []) or []:
        summary_counts = record.get("summary", {}) or {}
        rule_description = (record.get("assignment") or {}).get("description", "") or ""
        for state in record.get("states", []) or []:
            records.append(_convert_config_state(state, summary_counts, rule_description))
    return records


def _convert_secmaster(secmaster_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert all SecMaster baseline records into OA-format records.

    1. Build the workspace id -> name mapping from the input top-level
       workspaces array.
    2. Iterate over every data entry, resolving each record's workspace_name
       (workspace name preferred, workspace_id fallback) from the mapping.
    3. Convert each data_object into an OA-format record.
    4. Return the list of OA-format records.

    Args:
        secmaster_data: dict[str, Any] — The parsed SecMaster inspection JSON.

    Returns:
        list[dict[str, Any]]: OA-format records for every baseline record.

    Examples:
        # >>> _convert_secmaster({"data": []})
        # []
    """
    name_by_id: Dict[str, str] = {}
    for ws in secmaster_data.get("workspaces", []) or []:
        ws_id = str(ws.get("id", "") or "").strip()
        if ws_id:
            name_by_id[ws_id] = str(ws.get("name", "") or "").strip()
    records: List[Dict[str, Any]] = []
    for entry in secmaster_data.get("data", []) or []:
        data_object = entry.get("data_object", {}) or {}
        workspace_id = str(data_object.get("workspace_id", "") or "").strip()
        workspace_name = name_by_id.get(workspace_id, "") or workspace_id
        records.append(_convert_secmaster_record(data_object, workspace_name))
    return records


def _tag_oa_records(oa_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the OA records unchanged except for the source marker.

    1. Iterate over every OA result record.
    2. Copy each record and attach the OA source marker.

    Args:
        oa_data: dict[str, Any] — The parsed OA inspection JSON.

    Returns:
        list[dict[str, Any]]: The OA records, each tagged with the source.

    Examples:
        # >>> _tag_oa_records({"results": []})
        # []
    """
    records: List[Dict[str, Any]] = []
    for record in oa_data.get("results", []) or []:
        tagged = dict(record)
        tagged["source"] = SOURCE_OA
        records.append(tagged)
    return records


def _load_blacklist(file_path: Path) -> List[Dict[str, Any]]:
    """Load a blacklist JSON file into a list of entries.

    1. Read the file as UTF-8 text and parse it as JSON.
    2. Validate the result is a list; raise a ValueError naming the path
       when the file is missing, invalid or not a list.

    Args:
        file_path: Path — Absolute path of the blacklist JSON file.

    Returns:
        list[dict[str, Any]]: The parsed blacklist entries.

    Raises:
        ValueError: The file cannot be read, is not valid JSON, or does not
            hold a list.

    Examples:
        # >>> _load_blacklist(Path("config_blacklist.json"))
        # []
    """
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Blacklist file cannot be read: {file_path} ({exc})") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Blacklist file is not valid JSON: {file_path} ({exc})") from exc
    if not isinstance(data, list):
        raise ValueError(f"Blacklist file must contain a JSON list: {file_path}")
    return data


def _normalize_name(name: str) -> str:
    """Conservatively normalize a check-item name for fallback matching.

    1. Strip leading and trailing whitespace.
    2. Map full-width characters (letters, digits, punctuation) to their
       half-width equivalents via NFKC.

    Args:
        name: str — The raw check-item name.

    Returns:
        str: The normalized name, or an empty string for empty input.

    Examples:
        >>> _normalize_name("  ＲＤＳ实例开启备份  ")
        'RDS实例开启备份'
    """
    if not name:
        return ""
    try:
        return unicodedata.normalize("NFKC", " ".join(name.split())).strip()
    except Exception:
        return name


def _build_match_keys(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build exact and normalized name sets plus reasons from blacklist entries.

    1. Read each entry's match_key and name.
    2. Collect exact names and normalized names into two sets.
    3. Map both the exact and the normalized name to the entry reason so the
       filtering logs can explain why an item was dropped.

    Args:
        entries: list[dict[str, Any]] — The blacklist entries.

    Returns:
        dict[str, Any]: A dict with exact / normalized name sets and a
            reasons map keyed by both exact and normalized names.

    Examples:
        >>> _build_match_keys([{"name": "RDS实例开启备份", "match_key": "title"}])
        {'exact': {'RDS实例开启备份'}, 'normalized': {'RDS实例开启备份'}, 'reasons': {'RDS实例开启备份': 'blacklisted'}}
    """
    exact: set[str] = set()
    normalized: set[str] = set()
    reasons: Dict[str, str] = {}
    for entry in entries:
        name = str(entry.get("name", "") or "").strip()
        if not name:
            continue
        reason = str(entry.get("reason", "") or "").strip() or "blacklisted"
        exact.add(name)
        normalized_name = _normalize_name(name)
        normalized.add(normalized_name)
        reasons[name] = reason
        reasons[normalized_name] = reason
    return {"exact": exact, "normalized": normalized, "reasons": reasons}


def _is_blacklisted(match_value: str, match_keys: Dict[str, set[str]]) -> bool:
    """Decide whether a record matches the blacklist.

    1. Try exact matching first.
    2. On failure, fall back to conservative normalized matching.

    Args:
        match_value: str — The record field named by the blacklist match_key.
        match_keys: dict[str, set[str]] — The exact and normalized name sets.

    Returns:
        bool: True when the value is blacklisted, False otherwise.

    Examples:
        >>> _is_blacklisted("RDS实例开启备份", _build_match_keys([{"name": "RDS实例开启备份", "match_key": "title"}]))
        True
        >>> _is_blacklisted("ＲＤＳ实例开启备份", _build_match_keys([{"name": "RDS实例开启备份", "match_key": "title"}]))
        True
    """
    value = str(match_value or "").strip()
    if not value:
        return False
    if value in match_keys.get("exact", set()):
        return True
    return _normalize_name(value) in match_keys.get("normalized", set())


def _blacklist_reason(match_value: str, match_keys: Dict[str, Any]) -> str:
    """Return the blacklist reason for a matching value, empty when not listed.

    1. Look up the exact value in the reasons map.
    2. On failure, look up the normalized value as a fallback.

    Args:
        match_value: str — The record field named by the blacklist match_key.
        match_keys: dict[str, Any] — The exact / normalized name sets and the
            reasons map.

    Returns:
        str: The blacklist reason text, or an empty string when the value is
            not blacklisted.

    Examples:
        # >>> _blacklist_reason("RDS实例开启备份", _build_match_keys([{"name": "RDS实例开启备份", "reason": "与配置重复"}]))
        # '与配置重复'
    """
    reasons = match_keys.get("reasons", {}) or {}
    value = str(match_value or "").strip()
    if not value:
        return ""
    if value in reasons:
        return reasons.get(value, "")
    return reasons.get(_normalize_name(value), "")


def _filter_blacklisted_records(
    records: List[Dict[str, Any]],
    match_key: str,
    match_keys: Dict[str, Any],
    source_label: str = "",
) -> List[Dict[str, Any]]:
    """Drop records whose match field hits the blacklist.

    1. Iterate over the raw records.
    2. Log each dropped record with its match value, status and blacklist
       reason so users can reconcile page check items with the final report.
    3. Keep records whose match field value is not blacklisted.

    Args:
        records: list[dict[str, Any]] — The raw input records of one source.
        match_key: str — The field name holding the check-item name.
        match_keys: dict[str, Any] — The exact / normalized name sets and the
            reasons map.
        source_label: str — A source label (e.g. "Config" / "SecMaster") used
            in the drop logs.

    Returns:
        list[dict[str, Any]]: The records that are not blacklisted.

    Examples:
        # >>> _filter_blacklisted_records([{"title": "x"}], "title", _build_match_keys([]))
        # [{'title': 'x'}]
    """
    kept: List[Dict[str, Any]] = []
    for record in records:
        value = str(record.get(match_key, "") or "")
        if _is_blacklisted(value, match_keys):
            reason = _blacklist_reason(value, match_keys)
            status = str(record.get("handle_status", "") or record.get("compliance_state", "") or "")
            logger.info("Blacklist filtered out %s item: %s (status=%s, reason=%s)",
                        source_label, value, status, reason)
            continue
        kept.append(record)
    return kept


def _filter_config_states(config_data: Dict[str, Any],
                          match_keys: Dict[str, Any]) -> int:
    """Remove blacklisted states from every Config assignment.

    1. Iterate over the assignments and filter each one's states by the
       policy_assignment_name field, logging every removed state with its
       compliance status and blacklist reason.
    2. Count and return the total number of removed states.

    Args:
        config_data: dict[str, Any] — The parsed Config inspection JSON.
        match_keys: dict[str, Any] — The exact / normalized name sets and the
            reasons map.

    Returns:
        int: The number of Config states removed by the blacklist.

    Examples:
        # >>> _filter_config_states({"assignments": []}, {"exact": set(), "normalized": set()})
        # 0
    """
    removed = 0
    for record in config_data.get("assignments", []) or []:
        states = record.get("states", []) or []
        kept_states = _filter_blacklisted_records(
            states,
            "policy_assignment_name",
            match_keys,
            source_label=SOURCE_CONFIG,
        )
        removed += len(states) - len(kept_states)
        record["states"] = kept_states
    return removed


def _filter_secmaster_data(secmaster_data: Dict[str, Any],
                           match_keys: Dict[str, Any]) -> int:
    """Remove blacklisted data objects from the SecMaster result list.

    1. Iterate over the data entries and drop entries whose data_object
       title is blacklisted, logging every removed entry with its handle
       status and blacklist reason.
    2. Count and return the total number of removed entries.

    Args:
        secmaster_data: dict[str, Any] — The parsed SecMaster inspection JSON.
        match_keys: dict[str, Any] — The exact / normalized name sets and the
            reasons map.

    Returns:
        int: The number of SecMaster entries removed by the blacklist.

    Examples:
        # >>> _filter_secmaster_data({"data": []}, {"exact": set(), "normalized": set()})
        # 0
    """
    entries = secmaster_data.get("data", []) or []
    kept_entries: List[Dict[str, Any]] = []
    for entry in entries:
        data_object = entry.get("data_object", {}) or {}
        if _is_blacklisted(data_object.get("title", ""), match_keys):
            reason = _blacklist_reason(data_object.get("title", ""), match_keys)
            status = str(data_object.get("handle_status", "") or "")
            logger.info("Blacklist filtered out %s item: %s (status=%s, reason=%s)",
                        SOURCE_SECMASTER, data_object.get("title", ""), status, reason)
            continue
        kept_entries.append(entry)
    removed = len(entries) - len(kept_entries)
    secmaster_data["data"] = kept_entries
    return removed


def merge_all(oa_data: Dict[str, Any], config_data: Dict[str, Any],
              secmaster_data: Dict[str, Any],
              oa_file: str, config_file: str,
              secmaster_file: str,
              config_match_keys: Optional[Dict[str, Any]] = None,
              secmaster_match_keys: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Merge the three sources into one OA-format output document.

    1. Tag OA records and convert Config / SecMaster records.
    2. Concatenate all records into the merged results array.
    3. Preserve the Config failures and daily trend verbatim on the meta side.
    4. Build the meta block with input paths, counts and generation time.

    Args:
        oa_data: dict[str, Any] — The parsed OA inspection JSON.
        config_data: dict[str, Any] — The parsed Config inspection JSON.
        secmaster_data: dict[str, Any] — The parsed SecMaster inspection JSON.
        oa_file: str — Absolute path of the OA input file.
        config_file: str — Absolute path of the Config input file.
        secmaster_file: str — Absolute path of the SecMaster input file.
        config_match_keys: Optional[dict[str, Any]] — The Config blacklist
            name sets plus reasons, or None to skip Config filtering.
        secmaster_match_keys: Optional[dict[str, Any]] — The SecMaster
            blacklist name sets plus reasons, or None to skip SecMaster
            filtering.

    Returns:
        dict[str, Any]: The output document with meta and merged results.

    Examples:
        # >>> merge_all({"results": []}, {"assignments": []}, {"data": []}, "a", "b", "c")["meta"]["converted_total"]
        # 0
    """
    config_filtered = 0
    secmaster_filtered = 0
    if config_match_keys is not None:
        config_filtered = _filter_config_states(config_data, config_match_keys)
    if secmaster_match_keys is not None:
        secmaster_filtered = _filter_secmaster_data(secmaster_data, secmaster_match_keys)
    oa_records = _tag_oa_records(oa_data)
    config_records = _convert_config(config_data)
    secmaster_records = _convert_secmaster(secmaster_data)
    statistics = config_data.get("statistics", []) or []
    config_failures = config_data.get("failures", []) or []
    meta: Dict[str, Any] = {
        "generator": "merge_inspection_results",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {
            "oa": Path(oa_file).resolve().as_posix(),
            "config": Path(config_file).resolve().as_posix(),
            "secmaster": Path(secmaster_file).resolve().as_posix(),
        },
        "counts": {
            "oa_total": len(oa_records),
            "config_total": len(config_records),
            "secmaster_total": len(secmaster_records),
            "converted_total": len(oa_records) + len(config_records) + len(secmaster_records),
        },
        "filtered": {
            "config": config_filtered,
            "secmaster": secmaster_filtered,
        },
        "trends": {
            "config_daily": statistics,
        },
        "failures": {
            "config": config_failures,
        },
    }
    return {
        "meta": meta,
        "results": oa_records + config_records + secmaster_records,
    }


def resolve_output_path(timestamp: str) -> str:
    """Resolve the absolute output file path in the script directory.

    1. Join the script directory with the timestamped file name.
    2. Return the absolute path of the output file.

    Args:
        timestamp: str — Formatted timestamp string for the file name.

    Returns:
        str: Absolute output file path.

    Examples:
        >>> resolve_output_path("2026_10_12_14_30_00").endswith("merge_inspection_results_2026_10_12_14_30_00.json")
        True
    """
    return str(SCRIPT_DIR / OUTPUT_FILE_NAME.format(ts=timestamp))


def write_outputs(data: Dict[str, Any], output_path: str) -> List[str]:
    """Write the merged data to disk as a timestamped JSON file.

    1. Serialize the data as UTF-8 with ensure_ascii=False and indent=2.
    2. Write it to the fixed output path resolved at startup.

    Args:
        data: dict[str, Any] — The merged output document.
        output_path: str — Absolute output file path resolved at startup.

    Returns:
        list[str]: The list of written file paths.

    Examples:
        # >>> write_outputs({"meta": {}, "results": []}, "/abs/out.json")
        # ['/abs/out.json']
    """
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return [str(target)]


def print_summary(data: Dict[str, Any], written_files: List[str]) -> None:
    """Emit the merge summary via logging to stderr.

    1. Output the input paths, per-source counts and conversion total.
    2. Output the Config trend and failure information when present.
    3. Output the written file paths.

    Args:
        data: dict[str, Any] — The merged output document.
        written_files: list[str] — The list of written file paths.

    Returns:
        None

    Examples:
        # >>> print_summary({"meta": {}, "results": []}, [])
    """
    meta = data.get("meta", {})
    inputs = meta.get("inputs", {})
    counts = meta.get("counts", {})
    logger.info("=" * 60)
    logger.info("Merge of OA / Config / SecMaster inspection results completed")
    logger.info("=" * 60)
    logger.info("Input files:")
    logger.info("  - OA: %s", inputs.get("oa", ""))
    logger.info("  - Config: %s", inputs.get("config", ""))
    logger.info("  - SecMaster: %s", inputs.get("secmaster", ""))
    logger.info("Records: OA %d, Config %d, SecMaster %d, total %d",
                counts.get("oa_total", 0),
                counts.get("config_total", 0),
                counts.get("secmaster_total", 0),
                counts.get("converted_total", 0))
    filtered = meta.get("filtered", {}) or {}
    logger.info("Filtered: Config %d, SecMaster %d",
                filtered.get("config", 0),
                filtered.get("secmaster", 0))
    trends = meta.get("trends", {}) or {}
    config_daily = trends.get("config_daily", []) or []
    if config_daily:
        logger.info("Config daily compliance trend preserved: %d days",
                    len(config_daily))
    failures = meta.get("failures", {}) or {}
    config_failures = failures.get("config", []) or []
    if config_failures:
        logger.info("Config collection failures preserved: %d rules",
                    len(config_failures))
    if written_files:
        logger.info("-" * 60)
        logger.info("Generated files:")
        for file_path in written_files:
            logger.info("  - %s", file_path)
    logger.info("=" * 60)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    1. Add the three required input file options.
    2. Add the optional logging option.

    Args:
        None

    Returns:
        argparse.ArgumentParser: The configured argument parser.

    Examples:
        >>> parser = build_parser()
    """
    parser = argparse.ArgumentParser(
        prog="merge_inspection_results",
        description="Merge OA / Config / SecMaster inspection results into one OA-format JSON file")
    parser.add_argument("--oa-file", required=True,
                        help="Required. Absolute path of the OA inspection results JSON file")
    parser.add_argument("--config-file", required=True,
                        help="Required. Absolute path of the Config inspection results JSON file")
    parser.add_argument("--secmaster-file", required=True,
                        help="Required. Absolute path of the SecMaster inspection results JSON file")
    parser.add_argument("--log-file", default=None,
                        help="Optional. Path to a log file; logs are appended to stderr as well")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry wiring up argument parsing, loading, merging and write-out.

    1. Configure basic logging output (stderr by default, optional
       --log-file handler).
    2. Parse the command-line arguments; the three input files are required.
    3. Load the three input JSON files.
    4. Merge the three sources and write the merged document to disk.
    5. Emit the summary via logging.

    Args:
        argv: Optional[list[str]] — The command-line argument list, or
            sys.argv[1:] when None.

    Returns:
        int: The exit code; 0 for success, 1 for failure.

    Examples:
        # >>> main(["--oa-file", "a.json", "--config-file", "b.json", "--secmaster-file", "c.json"])
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_file)
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    output_absolute = resolve_output_path(timestamp)
    logger.info("Task started. Output file(s): %s", output_absolute)
    try:
        oa_data = load_json_file(args.oa_file)
        config_data = load_json_file(args.config_file)
        secmaster_data = load_json_file(args.secmaster_file)
        config_match_keys = _build_match_keys(
            _load_blacklist(BLACKLIST_DIR / CONFIG_BLACKLIST_NAME))
        secmaster_match_keys = _build_match_keys(
            _load_blacklist(BLACKLIST_DIR / SECMASTER_BLACKLIST_NAME))
    except ValueError as exc:
        logger.error("Failed to load input files: %s", exc)
        return 1
    data = merge_all(oa_data, config_data, secmaster_data,
                     args.oa_file, args.config_file, args.secmaster_file,
                     config_match_keys=config_match_keys,
                     secmaster_match_keys=secmaster_match_keys)
    written_files = write_outputs(data, output_absolute)
    print_summary(data, written_files)
    logger.info("Task finished. Output file(s): %s", written_files[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
