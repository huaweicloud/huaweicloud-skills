#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Huawei Cloud merged inspection report generator script.

Overview:
    This script reads the merged OA / Config / SecMaster inspection results
    JSON (the artifact written by `merge_inspection_results.py`), classifies
    every record into risk / non-risk / failure, aggregates risk records by
    inspection item, and renders two offline deliverables into the output
    directory: an offline HTML analysis report (metadata, three statistics
    charts and the risk item table with nested resource details) and an Excel
    workbook (overview sheet plus one detail sheet per aggregated risk item).
    Artifacts are written to a timestamped subdirectory under --output-dir so
    repeated runs do not mix in the same directory.

Detailed Description:
    1. Configure basic logging output, parse command-line arguments
       (--input/--output-dir/--timeout/--log-file).
    2. Load and validate the merged input JSON (meta and results structure).
    3. Classify records into risk / non-risk / hint / uninspected / failure and
       aggregate risk records into inspection items (keyed by check_item_id +
       source + workspace_id, so same-named baselines of different SecMaster
       instances stay separate); each item carries a display_source label so
       SecMaster items are shown with their workspace instance name (e.g.
       SecMaster (test)), with the instance region appended when two instances
       share the name. Only the risk items reach the HTML table and the Excel
       detail sheets; the other buckets feed the check-item level coverage
       counts reported in the generation log.
    4. Compute the check-item level coverage per source (OA console four
       categories, Config rule compliance, SecMaster baseline) plus the
       deduplicated failure count for the generation log, and the three chart
       distributions (product / source / dimension) consumed by the HTML
       report. The coverage counts are not rendered into any deliverable.
    5. Resolve the account user name and ID via the hcloud CLI
       (IAM KeystoneListAuthDomains) using the fixed CLI_REGION; the name
       and ID feed the Excel overview page, and the ID is also written to
       analysis.meta.domain_id for the HTML metadata block.
    6. Render the HTML report (template injection) and the Excel workbook
       (overview + detail sheets), writing all artifacts to the output
       directory. When the merged input records a cloud-service whitelist,
       also write the scoped risk-item JSON from the same aggregated items,
       so the agent can present the scoped result without parsing the HTML.
    7. Emit a summary via logging to stderr.

Dependencies:
    Python standard library: argparse, json, logging, subprocess, sys,
    datetime, pathlib. Optional third-party dependency: openpyxl (used for
    xlsx output, skipped with a warning when missing). Chart rendering is
    done by offline echarts shards stored in `assets/` and inlined into the
    HTML; HTML report styling comes from the static templates/report.html
    template. The script is purely local: it calls hcloud only for the
    read-only IAM domain query and never performs cloud write operations.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from cloud_service_filter import (
    build_display_name_map,
    display_service_name,
    load_alias_map,
    normalize_token,
    resolve_service_code,
)


logger = logging.getLogger(__name__)


# Constants
DEFAULT_OUTPUT_DIR = "analysis"
TEMPLATE_FILENAME = "report.html"
OUTPUT_HTML_NAME = "merge_inspection_report_{ts}.html"
OUTPUT_XLSX_NAME = "merge_inspection_report_{ts}.xlsx"
# Written only when a cloud-service whitelist applied, so the agent can
# present the scoped result without parsing the HTML report.
OUTPUT_RISK_ITEMS_NAME = "merge_inspection_report_{ts}_risk_items.json"
TIMESTAMP_FORMAT = "%Y_%m_%d_%H_%M_%S"
# Fixed hcloud region for the IAM domain query; it is never rendered into an
# artifact and is not exposed as a command-line option.
CLI_REGION = "cn-north-4"
IAM_SERVICE = "IAM"
AUTH_DOMAINS_API = "KeystoneListAuthDomains"
AUTH_DOMAINS_KEY = "domains"
STATUS_RISK = "risk"
STATUS_QUALIFIED = "qualified"
STATUS_NORMAL = "normal"
STATUS_NOT_INVOLVED = "not_involved"
# SecMaster baseline records that could not be judged (待处理) have this
# handle_status; they are not inspection failures and must not be counted as
# qualified either.
STATUS_UNINSPECTED = "uninspected"
SOURCE_OA = "OA"
SOURCE_CONFIG = "Config"
SOURCE_SECMASTER = "SecMaster"
# Chinese labels shown for the OA risk dimension, matching the Optimize
# Advisor console wording. Config records already carry the Chinese value
# 资源合规 in the merged data, so the map keeps it unchanged. The fallback
# label 不适用 (Not Applicable) is shown for dimension values that do not
# map to a known key.
DIMENSION_MAP = {
    "Performance": "性能效率",
    "Security": "安全性",
    "Reliability": "可靠性",
    "Cost": "成本优化",
    "Service Restriction": "服务配额",
    "资源合规": "资源合规",
}
DIMENSION_UNKNOWN = "不适用"
# Fixed semantic order for the risk dimension chart; every dimension is
# always shown even when its count is zero. All six entries are real
# categories: the 不适用 bucket retired once Config records received the
# fixed 资源合规 dimension, so it is no longer part of the chart.
DIMENSION_ORDER = [
    "性能效率",
    "安全性",
    "可靠性",
    "成本优化",
    "服务配额",
    "资源合规",
]
RISK_LEVEL_UNKNOWN = "不适用"
# OA console four-category classification keys. The Optimize Advisor console
# shows OA check items as 风险项 / 安全项 / 不涉及 / 提示项, which differ
# from the raw script statuses (risk / normal / not_involved).
OA_CATEGORY_RISK = "risk"
OA_CATEGORY_SECURITY = "security"
OA_CATEGORY_NOT_INVOLVED = "not_involved"
OA_CATEGORY_HINT = "hint"
# Label shown by the product chart when an item carries no cloud service at
# all; it is the only bucket the chart may invent.
PRODUCT_UNKNOWN = "未知"
SHEET_NAME_MAX_LENGTH = 31
OVERVIEW_SHEET_NAME = "风险检查总览"
LINK_BLUE = "0563C1"
RESOURCE_COLUMNS = ["区域", "资源ID", "资源名称", "检查账号", "状态", "标签", "企业项目ID", "扩展属性"]


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
        # >>> load_json_file("merge_inspection_results_2026_10_12_17_17_53.json")
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


def classify_record(record: Dict[str, Any]) -> str:
    """Classify one merged record into risk / non-risk / uninspected / failure.

    1. Return `failure` when the record carries a non-empty top-level error.
    2. Derive the status from summary.check_item_status; `risk` maps to risk,
       `uninspected` maps to uninspected (待处理, not a failure), and every
       other known status maps to non-risk.
    3. Treat records without a recognizable status as failures.

    Args:
        record: dict[str, Any] — One merged result record.

    Returns:
        str: The classification: risk / non-risk / uninspected / failure.

    Examples:
        >>> classify_record({"summary": {"check_item_status": "risk"}})
        'risk'
        >>> classify_record({"summary": {"check_item_status": "uninspected"}})
        'uninspected'
        >>> classify_record({"error": "boom"})
        'failure'
    """
    if record.get("error"):
        return "failure"
    status = (record.get("summary") or {}).get("check_item_status", "")
    if status == STATUS_RISK:
        return "risk"
    if status == STATUS_UNINSPECTED:
        return STATUS_UNINSPECTED
    if status in (STATUS_QUALIFIED, STATUS_NORMAL, STATUS_NOT_INVOLVED):
        return "non-risk"
    return "failure"


def _resource_columns() -> List[str]:
    """Return the fixed resource detail table column names.

    1. Return the shared RESOURCE_COLUMNS constant.

    Args:
        None

    Returns:
        list[str]: The resource detail table column headers.

    Examples:
        >>> _resource_columns()[0]
        '区域'
    """
    return list(RESOURCE_COLUMNS)


def _resource_rows(resources: Sequence[Dict[str, Any]]) -> List[List[Any]]:
    """Flatten resource objects into fixed-width table rows.

    1. For each resource, take id / name / region / status / tags /
       enterprise project / extended properties.
    2. Return rows of the same column count as RESOURCE_COLUMNS.

    Args:
        resources: Sequence[dict[str, Any]] — The resource object list.

    Returns:
        list[list[Any]]: The resource rows ready for tabular output.

    Examples:
        # >>> _resource_rows([{"id": "x", "name": "n", "region_id": "r"}])
        # [['x', 'n', '', 'r', '', '', '', '']]
    """
    rows: List[List[Any]] = []
    for res in resources or []:
        rows.append([
            res.get("region_id", "") or "",
            res.get("id", "") or "",
            res.get("name", "") or "",
            res.get("domain_id", "") or "",
            res.get("status", "") or "",
            res.get("tags", "") or "",
            res.get("enterprise_project_id", "") or "",
            res.get("extended_properties", "") or "",
        ])
    return rows


def _summary_value(record: Dict[str, Any], key: str) -> str:
    """Read a string value from a record's summary block.

    1. Look the key up in summary and return the string value.
    2. Fall back to an empty string when summary or the key is missing.

    Args:
        record: dict[str, Any] — One merged record.
        key: str — The summary field name.

    Returns:
        str: The field value or an empty string.

    Examples:
        >>> _summary_value({"summary": {"a": "b"}}, "a")
        'b'
    """
    summary = record.get("summary") or {}
    value = summary.get(key, "")
    return value if value is not None else ""


def _risk_level_display(record: Dict[str, Any]) -> str:
    """Normalize the risk level of a record for display.

    1. Return the record risk_level when non-empty.
    2. Fall back to the summary check_item_risk_level when present.
    3. Otherwise return an empty string when the source is Config,
       because Config records carry no risk level.
    4. Otherwise return the RISK_LEVEL_UNKNOWN placeholder.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display risk level; empty for Config records without a
            risk level.

    Examples:
        >>> _risk_level_display({"risk_level": "high"})
        'high'
        >>> _risk_level_display({"summary": {"check_item_risk_level": "low"}})
        'low'
        >>> _risk_level_display({"source": "Config"})
        ''
    """
    direct = record.get("risk_level") or ""
    if direct:
        return direct
    fallback = _summary_value(record, "check_item_risk_level")
    if not fallback and record.get("source", "") == SOURCE_CONFIG:
        return ""
    return fallback or RISK_LEVEL_UNKNOWN


_ALIAS_MAP_CACHE: Optional[Dict[str, str]] = None
_DISPLAY_MAP_CACHE: Optional[Dict[str, str]] = None


def _alias_map() -> Dict[str, str]:
    """Return the cloud-service alias map, loading it at most once.

    1. Return the cached map when a previous call already loaded it.
    2. Otherwise load the project table, caching the result so the renderer
       does not re-read the file once per record.

    Args:
        None

    Returns:
        dict[str, str]: Normalised alias to canonical code.

    Examples:
        # >>> _alias_map()["ecs"]
        # 'ecs'
    """
    global _ALIAS_MAP_CACHE
    if _ALIAS_MAP_CACHE is None:
        _ALIAS_MAP_CACHE = load_alias_map()
    return _ALIAS_MAP_CACHE


def _display_name_map() -> Dict[str, str]:
    """Return the code to display-name map, loading it at most once.

    1. Return the cached map when a previous call already loaded it.
    2. Otherwise build it from the same table the alias map came from, so the
       two maps can never disagree about a code.

    Args:
        None

    Returns:
        dict[str, str]: Canonical code to its first alias name.

    Examples:
        # >>> _display_name_map()["idme"]
        # 'iDME'
    """
    global _DISPLAY_MAP_CACHE
    if _DISPLAY_MAP_CACHE is None:
        _DISPLAY_MAP_CACHE = build_display_name_map(_alias_map())
    return _DISPLAY_MAP_CACHE


def _service_type_display(record: Dict[str, Any]) -> str:
    """Derive the display cloud service type for a record.

    1. Return the record service_type_code when non-empty.
    2. Fall back to the summary check_item_service when present.
    3. Otherwise return an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display service type code.

    Examples:
        >>> _service_type_display({"service_type_code": "ecs"})
        'ecs'
        >>> _service_type_display({"summary": {"check_item_service": "RDS"}})
        'RDS'
    """
    direct = record.get("service_type_code") or ""
    if direct:
        return direct
    return _summary_value(record, "check_item_service")


def _service_code(record: Dict[str, Any]) -> str:
    """Resolve a record's cloud service to its canonical code.

    1. Derive the raw service value via `_service_type_display`.
    2. Resolve it through the alias table so case and historical spellings
       (`ECS` / `ecs` / `hecs`) collapse onto one product.
    3. Fall back to the normalised raw value when the table does not cover
       it, so an unmapped service still groups consistently with itself.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The canonical service code, or an empty string when the record
            carries no service at all.

    Examples:
        # >>> _service_code({"service_type_code": "hecs"})
        # 'ecs'
    """
    raw = _service_type_display(record)
    if not raw:
        return ""
    alias_map = _alias_map()
    return resolve_service_code(raw, alias_map) or normalize_token(raw)


def _service_display(record: Dict[str, Any]) -> str:
    """Derive the product label shown by the chart and the HTML filter.

    1. Resolve the canonical code via `_service_code`.
    2. Return the alias table's first name for that code, so official
       spellings such as `iDME` survive.
    3. Fall back to the upper-cased code when the table has no entry.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The product label, or an empty string when no service exists.

    Examples:
        # >>> _service_display({"service_type_code": "ecs"})
        # 'ECS'
    """
    code = _service_code(record)
    if not code:
        return ""
    return display_service_name(code, _display_name_map())


def _dimension_display(record: Dict[str, Any]) -> str:
    """Derive the display risk dimension for a record.

    1. Return the record dimension when non-empty.
    2. Fall back to the summary check_item_dimension when present.
    3. Otherwise return an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display risk dimension.

    Examples:
        >>> _dimension_display({"dimension": "Cost"})
        'Cost'
        >>> _dimension_display({"summary": {"check_item_dimension": "安全"}})
        '安全'
    """
    direct = record.get("dimension") or ""
    if direct:
        return direct
    return _summary_value(record, "check_item_dimension")


def _dimension_cn(record: Dict[str, Any]) -> str:
    """Derive the Chinese display dimension for a record.

    1. Resolve the raw dimension via _dimension_display.
    2. Map it through DIMENSION_MAP; unmapped values, including an empty
       dimension, fall back to the DIMENSION_UNKNOWN placeholder.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The Chinese display dimension.

    Examples:
        >>> _dimension_cn({"dimension": "Reliability"})
        '可靠性'
        >>> _dimension_cn({"dimension": "资源合规"})
        '资源合规'
        >>> _dimension_cn({"source": "Config"})
        '不适用'
        >>> _dimension_cn({"dimension": "Other"})
        '不适用'
    """
    raw = _dimension_display(record)
    return DIMENSION_MAP.get(raw, DIMENSION_UNKNOWN)


def _duplicated_workspace_names(records: Sequence[Dict[str, Any]]) -> set:
    """Collect SecMaster workspace names shared by more than one instance.

    1. Group the distinct workspace_id values of every SecMaster record by
       its workspace_name.
    2. Return the names whose group holds at least two distinct instances.

    Names are compared verbatim; a name used by a single instance is left out
    so its label stays the plain `SecMaster (实例名)` form.

    Args:
        records: Sequence[dict[str, Any]] — The merged records to scan.

    Returns:
        set: The workspace names shared by two or more instances.

    Examples:
        >>> _duplicated_workspace_names([{"source": "SecMaster", "workspace_name": "test", "workspace_id": "a"}])
        set()
    """
    ids_by_name: Dict[str, set] = {}
    for record in records:
        if (record.get("source", "") or "") != SOURCE_SECMASTER:
            continue
        name = record.get("workspace_name", "") or ""
        if not name:
            continue
        workspace_id = record.get("workspace_id", "") or ""
        ids_by_name.setdefault(name, set()).add(workspace_id)
    return {name for name, ids in ids_by_name.items() if len(ids) > 1}


def _source_display(record: Dict[str, Any], duplicated_names: set | None = None) -> str:
    """Derive the display source label for a record.

    1. Return the record source when it is not SecMaster.
    2. Return `SecMaster (实例名)` when the record carries a non-empty
       workspace_name that is unique across instances.
    3. Append the instance region as `SecMaster (实例名 @ 区域ID)` when the
       name is shared by several instances, so the label stays unambiguous.
    4. Otherwise return the plain source value.

    Args:
        record: dict[str, Any] — One merged record or aggregated item.
        duplicated_names: set | None — Workspace names shared by more than one
            instance, as returned by _duplicated_workspace_names.

    Returns:
        str: The display source label.

    Examples:
        >>> _source_display({"source": "OA"})
        'OA'
        >>> _source_display({"source": "SecMaster", "workspace_name": "test"})
        'SecMaster (test)'
        >>> _source_display({"source": "SecMaster", "workspace_name": ""})
        'SecMaster'
        >>> _source_display({"source": "SecMaster", "workspace_name": "test",
        ...                  "workspace_region_id": "cn-east-2"}, {"test"})
        'SecMaster (test @ cn-east-2)'
    """
    source = record.get("source", "") or ""
    if source == SOURCE_SECMASTER:
        workspace_name = record.get("workspace_name", "") or ""
        if workspace_name:
            if duplicated_names and workspace_name in duplicated_names:
                region_id = record.get("workspace_region_id", "") or ""
                if region_id:
                    return f"SecMaster ({workspace_name} @ {region_id})"
            return f"SecMaster ({workspace_name})"
    return source


def _item_name_display(record: Dict[str, Any]) -> str:
    """Derive the display inspection item name for a record.

    1. Return the record check_item_name when non-empty.
    2. Fall back to the summary check_item_name when present.
    3. Otherwise return an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display inspection item name.

    Examples:
        >>> _item_name_display({"check_item_name": "创建并启用CTS追踪器"})
        '创建并启用CTS追踪器'
        >>> _item_name_display({"summary": {"check_item_name": "数字检测"}})
        '数字检测'
    """
    direct = record.get("check_item_name") or ""
    if direct:
        return direct
    return _summary_value(record, "check_item_name")


def _item_id_display(record: Dict[str, Any]) -> str:
    """Derive the display inspection item id for a record.

    1. Return the record check_item_id when non-empty.
    2. Fall back to the summary check_item_id when present.
    3. Otherwise return an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display inspection item id.

    Examples:
        >>> _item_id_display({"check_item_id": "abc"})
        'abc'
        >>> _item_id_display({"summary": {"check_item_id": "xyz"}})
        'xyz'
    """
    direct = record.get("check_item_id") or ""
    if direct:
        return direct
    return _summary_value(record, "check_item_id")


def _risk_resource_count(record: Dict[str, Any]) -> int:
    """Derive the risk resource count for a record.

    1. Count the entries in the record resources list.
    2. Return 0 when the resources list is missing or empty.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        int: The risk resource count.

    Examples:
        >>> _risk_resource_count({"resources": [{"id": "a"}, {"id": "b"}]})
        2
        >>> _risk_resource_count({"summary": {"resources_summary": {"risk_resource_count": 9}}, "resources": [{"id": "a"}, {"id": "b"}]})
        2
        >>> _risk_resource_count({"summary": {"resources_summary": {"risk_resource_count": -1}}})
        0
    """
    return len(record.get("resources") or [])


def _checked_resource_count(record: Dict[str, Any]) -> int:
    """Derive the checked resource count for a record.

    1. Prefer summary.resources_summary.checked_resource_count when
       available.
    2. Fall back to the number of entries in the record resources list.
    3. Return 0 when neither is available.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        int: The checked resource count.

    Examples:
        >>> _checked_resource_count({"summary": {"resources_summary": {"checked_resource_count": 11}}})
        11
        >>> _checked_resource_count({"resources": [{"id": "a"}]})
        1
    """
    summary = record.get("summary") or {}
    resources_summary = summary.get("resources_summary") or {}
    count = resources_summary.get("checked_resource_count")
    if count is not None:
        return int(count)
    return len(record.get("resources") or [])


def _description_display(record: Dict[str, Any]) -> str:
    """Derive the display judgment standard description for a record.

    1. Return the summary check_item_description when non-empty.
    2. Fall back to an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display description.

    Examples:
        >>> _description_display({"summary": {"check_item_description": "标准"}})
        '标准'
    """
    return _summary_value(record, "check_item_description")


def _advice_display(record: Dict[str, Any]) -> str:
    """Derive the display optimization advice for a record.

    1. Return the summary check_item_advice when non-empty.
    2. Fall back to an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display advice text.

    Examples:
        >>> _advice_display({"summary": {"check_item_advice": "建议"}})
        '建议'
    """
    return _summary_value(record, "check_item_advice")


def _effect_display(record: Dict[str, Any]) -> str:
    """Derive the display risk impact text for a record.

    1. Return the summary check_item_effect when non-empty.
    2. Fall back to an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display risk impact text.

    Examples:
        >>> _effect_display({"summary": {"check_item_effect": "影响"}})
        '影响'
    """
    return _summary_value(record, "check_item_effect")


def _end_time_display(record: Dict[str, Any]) -> str:
    """Derive the display check time for a record.

    1. Return the summary end_time when non-empty.
    2. Fall back to an empty string.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The display check end time.

    Examples:
        >>> _end_time_display({"summary": {"end_time": "2026-10-12"}})
        '2026-10-12'
    """
    return _summary_value(record, "end_time")


def _format_eval_time(timestamp_str: str) -> str:
    """Convert a millisecond timestamp string into a local readable time.

    1. Parse the value as a millisecond timestamp and convert it to local
       time.
    2. Return the original string on parse failure or empty input.

    Args:
        timestamp_str: str — The millisecond timestamp string, e.g.
            "1791737258974".

    Returns:
        str: The formatted local time string, or the original value on
            failure.

    Examples:
        # >>> _format_eval_time("1791737258974")
        # '2026-10-12 15:34:24'
    """
    if not timestamp_str:
        return ""
    try:
        timestamp_ms = int(timestamp_str)
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y/%m/%d %H:%M:%S")
    except (ValueError, OSError, OverflowError):
        return timestamp_str


def _is_hint_record(record: Dict[str, Any]) -> bool:
    """Decide whether an OA risk record is a hint item without real risk.

    1. Return False unless the record is OA source and carries the risk
       status.
    2. Treat the record as a hint when its risk resource list is empty
       (quota-alarm placeholder items reported by the OA interface).
    3. Never classify Config / SecMaster records as hints because they carry
       no risk resource list and would otherwise degrade to zero.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        bool: True when the record is an OA hint item.

    Examples:
        >>> _is_hint_record({"source": "OA", "summary": {"check_item_status": "risk"}, "resources": []})
        True
        >>> _is_hint_record({"source": "OA", "summary": {"check_item_status": "risk"}, "resources": [{"id": "a"}]})
        False
        >>> _is_hint_record({"source": "Config", "summary": {"check_item_status": "risk"}})
        False
    """
    if record.get("source", "") != SOURCE_OA:
        return False
    if _summary_value(record, "check_item_status") != STATUS_RISK:
        return False
    return _risk_resource_count(record) <= 0


def _oa_console_category(record: Dict[str, Any]) -> str:
    """Classify one OA record into the console four-category vocabulary.

    1. Only classify OA records with a non-empty check_item_status; other
       sources and failed records fall back to the hint category.
    2. Count the risk resource list and the raw status / dimension; an empty
       risk resource list with a Service Restriction dimension or a risk
       status maps to a hint item (quota alarms without real risk).
    3. A risk status with real resources maps to risk, a normal status
       outside the Service Restriction dimension maps to security, and every
       remaining succeeded record maps to not_involved.

    Args:
        record: dict[str, Any] — One merged record.

    Returns:
        str: The OA console category: risk / security / not_involved / hint.

    Examples:
        # >>> _oa_console_category({"source": "OA", "dimension": "Reliability", "summary": {"check_item_status": "risk", "resources_summary": {"risk_resource_count": 2}}, "resources": [{"id": "a"}]})
        # 'risk'
        # >>> _oa_console_category({"source": "OA", "dimension": "Service Restriction", "summary": {"check_item_status": "risk", "resources_summary": {"risk_resource_count": -1}}, "resources": []})
        # 'hint'
    """
    if record.get("source", "") != SOURCE_OA:
        return OA_CATEGORY_HINT
    status = _summary_value(record, "check_item_status")
    if not status:
        return OA_CATEGORY_HINT
    dimension = _dimension_display(record)
    count = _risk_resource_count(record)
    if count <= 0 and (dimension == "Service Restriction" or status == STATUS_RISK):
        return OA_CATEGORY_HINT
    if status == STATUS_RISK and count > 0:
        return OA_CATEGORY_RISK
    if status == STATUS_NORMAL and dimension != "Service Restriction":
        return OA_CATEGORY_SECURITY
    return OA_CATEGORY_NOT_INVOLVED


def classify_all(results: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Classify all merged records into the five buckets.

    1. Iterate over every record and classify it via classify_record.
    2. Route OA records classified as risk through _is_hint_record so that
       hint items land in their own bucket instead of the risk bucket.
    3. Append each record to the corresponding bucket list.

    Args:
        results: Sequence[dict[str, Any]] — The merged results array.

    Returns:
        dict[str, list[dict[str, Any]]]: Buckets keyed by risk / non-risk /
            hint / uninspected / failure.

    Examples:
        # >>> classify_all([{"error": "x"}, {"summary": {"check_item_status": "risk"}}])
        # {'risk': [{'summary': {'check_item_status': 'risk'}}], 'non-risk': [], 'hint': [], 'uninspected': [], 'failure': [{'error': 'x'}]}
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "risk": [], "non-risk": [], "hint": [], "uninspected": [], "failure": []
    }
    for record in results:
        bucket = classify_record(record)
        if bucket == "risk" and _is_hint_record(record):
            bucket = "hint"
        buckets[bucket].append(record)
    return buckets


def aggregate_risk_items(risk_records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate risk records into inspection items.

    1. Group records by (check_item_id, source, workspace_id) preserving
       first-seen order; the workspace id keeps same-named baselines of
       different SecMaster instances apart and is empty for other sources.
    2. Collect the workspace names shared by several instances so the source
       label can append the region and stay unambiguous.
    3. Build one inspection item per group: display fields from the first
       record, merged resource list, summed risk / checked resource counts
       and description / advice / effect / end time.
    4. Keep records sharing an item id but a different source or instance in
       separate items so the source column stays unambiguous.

    Args:
        risk_records: Sequence[dict[str, Any]] — The risk-classified records.

    Returns:
        list[dict[str, Any]]: Aggregated inspection item rows.

    Examples:
        # >>> aggregate_risk_items([{"check_item_id": "a", "source": "Config", "resources": [{"id": "r1"}]}, {"check_item_id": "a", "source": "Config", "resources": [{"id": "r2"}]}])
        # [{'check_item_id': 'a', 'resource_count': 2, 'resources': [{'id': 'r1'}, {'id': 'r2'}]}]
    """
    duplicated_names = _duplicated_workspace_names(risk_records)
    order: List[Tuple[str, str, str]] = []
    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for record in risk_records:
        key = (
            _item_id_display(record),
            record.get("source", "") or "",
            record.get("workspace_id", "") or "",
        )
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(record)

    items: List[Dict[str, Any]] = []
    for key in order:
        group = groups[key]
        first = group[0]
        resources: List[Dict[str, Any]] = []
        resource_count = 0
        total_resources = 0
        for record in group:
            resources.extend(record.get("resources") or [])
            resource_count += _risk_resource_count(record)
            total_resources += _checked_resource_count(record)
        items.append({
            "check_item_id": key[0],
            "check_item_name": _item_name_display(first),
            "dimension": _dimension_cn(first),
            "service_type_code": _service_type_display(first),
            "service_code": _service_code(first),
            "service_display": _service_display(first),
            "risk_level": _risk_level_display(first),
            "source": key[1],
            "workspace_id": key[2],
            "workspace_name": first.get("workspace_name", "") or "",
            "workspace_region_id": first.get("workspace_region_id", "") or "",
            "display_source": _source_display(first, duplicated_names),
            "resource_count": resource_count,
            "resources": resources,
            "description": _description_display(first),
            "advice": _advice_display(first),
            "effect": _effect_display(first),
            "end_time": _format_eval_time(_end_time_display(first)),
            "total_resources": total_resources,
        })
    return items


def _source_distribution(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute the risk item count per display source label.

    1. Count inspection items by their display_source field (SecMaster items
       carry their instance name, e.g. SecMaster (test)).
    2. Sort descending by count and return name/value pairs.

    Args:
        items: Sequence[dict[str, Any]] — The aggregated inspection items.

    Returns:
        list[dict[str, Any]]: name/value pairs keyed by display source.

    Examples:
        >>> _source_distribution([{"display_source": "OA"}, {"display_source": "SecMaster (test)"}])
        [{'name': 'OA', 'value': 1}, {'name': 'SecMaster (test)', 'value': 1}]
    """
    counts: Dict[str, int] = {}
    for item in items:
        label = item.get("display_source") or item.get("source") or ""
        counts[label] = counts.get(label, 0) + 1
    pairs = [{"name": name, "value": value} for name, value in counts.items()]
    pairs.sort(key=lambda p: p["value"], reverse=True)
    return pairs


def _oa_console_coverage(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Compute the OA console four-category coverage.

    1. Filter records whose source is OA and group distinct check_item_id by
       the console category via _oa_console_category.
    2. Count distinct check_item_id of OA records with a non-empty error as
       failed.
    3. Return the five counts; every OA check item falls into exactly one
       bucket because a record carries either an error or a result summary.

    Args:
        results: Sequence[dict[str, Any]] — The merged results array.

    Returns:
        dict[str, int]: OA console coverage keyed by risk / security /
            not_involved / hint / failed.

    Examples:
        # >>> _oa_console_coverage([{"source": "OA", "summary": {"check_item_status": "risk", "resources_summary": {"risk_resource_count": 2}}}])
        # {'risk': 1, 'security': 0, 'not_involved': 0, 'hint': 0, 'failed': 0}
    """
    category_buckets: Dict[str, set] = {
        OA_CATEGORY_RISK: set(),
        OA_CATEGORY_SECURITY: set(),
        OA_CATEGORY_NOT_INVOLVED: set(),
        OA_CATEGORY_HINT: set(),
    }
    failed_ids: set = set()
    for record in results:
        if record.get("source", "") != SOURCE_OA:
            continue
        item_id = _item_id_display(record)
        if record.get("error"):
            failed_ids.add(item_id)
            continue
        category = _oa_console_category(record)
        category_buckets[category].add(item_id)
    return {
        "risk": len(category_buckets[OA_CATEGORY_RISK]),
        "security": len(category_buckets[OA_CATEGORY_SECURITY]),
        "not_involved": len(category_buckets[OA_CATEGORY_NOT_INVOLVED]),
        "hint": len(category_buckets[OA_CATEGORY_HINT]),
        "failed": len(failed_ids),
    }


def _coverage_config(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Compute the Config rule-level compliance coverage.

    1. Group Config records by check_item_id (the policy_assignment_id).
    2. Mark a rule as non-compliant when any of its records carries the risk
       status, compliant otherwise.
    3. Return rule totals: total_rules / compliant_rules /
       non_compliant_rules.

    Args:
        results: Sequence[dict[str, Any]] — The merged results array.

    Returns:
        dict[str, int]: Config coverage keyed by total_rules /
            compliant_rules / non_compliant_rules.

    Examples:
        # >>> _coverage_config([{"source": "Config", "check_item_id": "r", "summary": {"check_item_status": "qualified"}}])
        # {'total_rules': 1, 'compliant_rules': 1, 'non_compliant_rules': 0}
    """
    rule_status: Dict[str, str] = {}
    for record in results:
        if record.get("source", "") != SOURCE_CONFIG:
            continue
        rule_id = _item_id_display(record)
        if _summary_value(record, "check_item_status") == STATUS_RISK:
            rule_status[rule_id] = STATUS_RISK
        else:
            rule_status.setdefault(rule_id, STATUS_QUALIFIED)
    total = len(rule_status)
    non_compliant = sum(1 for status in rule_status.values() if status == STATUS_RISK)
    return {
        "total_rules": total,
        "compliant_rules": total - non_compliant,
        "non_compliant_rules": non_compliant,
    }


def _coverage_secmaster(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Compute the SecMaster baseline-level coverage.

    1. Filter records whose source is SecMaster and count distinct
       (checkitem_id, workspace_id) pairs per handle_status: qualified / risk /
       uninspected; the instance id keeps the same baseline of two instances
       counted separately instead of collapsing into one.
    2. Return the three counts; uninspected (待处理) baselines are counted
       separately and never folded into qualified.

    Args:
        results: Sequence[dict[str, Any]] — The merged results array.

    Returns:
        dict[str, int]: SecMaster coverage keyed by qualified / risk /
            uninspected.

    Examples:
        # >>> _coverage_secmaster([{"source": "SecMaster", "summary": {"check_item_status": "qualified"}}])
        # {'qualified': 1, 'risk': 0, 'uninspected': 0}
    """
    qualified_ids: set = set()
    risk_ids: set = set()
    uninspected_ids: set = set()
    for record in results:
        if record.get("source", "") != SOURCE_SECMASTER:
            continue
        item_id = (_item_id_display(record), record.get("workspace_id", "") or "")
        status = _summary_value(record, "check_item_status")
        if status == STATUS_RISK:
            risk_ids.add(item_id)
        elif status == STATUS_UNINSPECTED:
            uninspected_ids.add(item_id)
        else:
            qualified_ids.add(item_id)
    return {
        "qualified": len(qualified_ids),
        "risk": len(risk_ids),
        "uninspected": len(uninspected_ids),
    }


def build_analysis_data(merged: Dict[str, Any]) -> Dict[str, Any]:
    """Build the analysis payload for the HTML report and Excel output.

    1. Classify all results into risk / non-risk / hint / uninspected /
       failure buckets.
    2. Aggregate risk records into inspection items.
    3. Compute the chart distributions consumed by the HTML report (product,
       source and dimension).
    4. Compute the check-item level coverage per source for the generation log
       (the run summary).
    5. Attach the original meta block.

    Args:
        merged: dict[str, Any] — The parsed merged inspection JSON.

    Returns:
        dict[str, Any]: The analysis payload consumed by the renderers.

    Examples:
        # >>> build_analysis_data({"meta": {}, "results": []})
        # {'meta': {}, 'items': [], 'coverage': {...}, 'charts': {...}}
    """
    results = merged.get("results", []) or []
    buckets = classify_all(results)
    items = aggregate_risk_items(buckets["risk"])
    config_coverage = _coverage_config(results)
    secmaster_coverage = _coverage_secmaster(results)
    oa_console_coverage = _oa_console_coverage(results)
    failed_item_ids = {_item_id_display(r) for r in results if r.get("error")}
    coverage = {
        "oa_console": oa_console_coverage,
        "config": config_coverage,
        "secmaster": secmaster_coverage,
        "failed": {
            "total": len(failed_item_ids),
        },
    }
    charts = {
        "products": _product_distribution(items),
        "sources": _source_distribution(items),
        "dimensions": _dimension_distribution(items),
    }
    return {
        "meta": merged.get("meta", {}),
        "items": items,
        "coverage": coverage,
        "charts": charts,
    }


def _product_distribution(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute the risk item count per cloud service product.

    1. Group by the resolved service code carried by each item, so values the
       alias table treats as one product (`ECS` / `ecs` / `hecs`) collapse
       into a single bar; an item without a resolved code falls back to its
       raw value.
    2. Sort descending by count and return name/value pairs labelled with the
       item's display service name.

    Args:
        items: Sequence[dict[str, Any]] — The aggregated inspection items,
            each carrying `service_code` / `service_display`.

    Returns:
        list[dict[str, Any]]: name/value pairs; an empty service is shown as 未知.

    Examples:
        # >>> _product_distribution([{"service_code": "ecs", "service_display": "ECS"},
        # ...                          {"service_code": "ecs", "service_display": "ECS"}])
        # [{'name': 'ECS', 'value': 2}]
    """
    counts: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = item.get("service_code") or item.get("service_type_code") or ""
        if not key:
            counts.setdefault("", {"name": PRODUCT_UNKNOWN, "value": 0})
            counts[""]["value"] += 1
            continue
        entry = counts.setdefault(
            key, {"name": item.get("service_display") or key.upper(), "value": 0})
        entry["value"] += 1
    pairs = list(counts.values())
    pairs.sort(key=lambda p: p["value"], reverse=True)
    return pairs


def _dimension_distribution(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute the risk item count per Chinese risk dimension.

    1. Seed every dimension in DIMENSION_ORDER with a zero count so
       dimensions without data still appear in the chart.
    2. Count inspection items by their Chinese dimension field; an empty
       dimension falls back to DIMENSION_UNKNOWN.
    3. Return name/value pairs in the fixed semantic order. Only the six
       dimensions in DIMENSION_ORDER are charted, so an item whose dimension
       resolves to DIMENSION_UNKNOWN is not represented.

    Args:
        items: Sequence[dict[str, Any]] — The aggregated inspection items.

    Returns:
        list[dict[str, Any]]: Six name/value pairs in semantic order, zero
        count for dimensions without data.

    Examples:
        >>> _dimension_distribution([{"dimension": "可靠性"}, {"dimension": "可靠性"}])
        [{'name': '性能效率', 'value': 0}, {'name': '安全性', 'value': 0}, {'name': '可靠性', 'value': 2}, {'name': '成本优化', 'value': 0}, {'name': '服务配额', 'value': 0}, {'name': '资源合规', 'value': 0}]
        >>> _dimension_distribution([{"dimension": "资源合规"}])
        [{'name': '性能效率', 'value': 0}, {'name': '安全性', 'value': 0}, {'name': '可靠性', 'value': 0}, {'name': '成本优化', 'value': 0}, {'name': '服务配额', 'value': 0}, {'name': '资源合规', 'value': 1}]
    """
    counts: Dict[str, int] = {dimension: 0 for dimension in DIMENSION_ORDER}
    for item in items:
        dimension = item.get("dimension") or DIMENSION_UNKNOWN
        counts[dimension] = counts.get(dimension, 0) + 1
    return [{"name": name, "value": counts[name]} for name in DIMENSION_ORDER]


def resolve_domain_info(cli_region: str, timeout: int) -> Tuple[str, str]:
    """Resolve the account user name and ID via the hcloud CLI.

    1. Invoke `hcloud IAM KeystoneListAuthDomains --cli-region=<region>`.
    2. Parse the domains array; take the name and id of the first entry.
    3. Return ('', '') on any command / parse failure so the caller can
       degrade gracefully.

    Args:
        cli_region: str — The hcloud command region.
        timeout: int — The timeout in seconds for the command.

    Returns:
        tuple[str, str]: The user name and account (domain) ID.

    Examples:
        # >>> resolve_domain_info("cn-north-4", 30)
        # ('hwcloudsretam', 'a9c2d92bd05e4c78ac1bc6c6849c3c10')
    """
    command = ["hcloud", IAM_SERVICE, AUTH_DOMAINS_API, f"--cli-region={cli_region}"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Failed to resolve account info via hcloud: %s", exc)
        return "", ""
    if result.returncode != 0:
        logger.warning("hcloud domain query failed (return code %s)", result.returncode)
        return "", ""
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse hcloud domain response: %s", exc)
        return "", ""
    domains = data.get(AUTH_DOMAINS_KEY) or [] if isinstance(data, dict) else []
    if not domains:
        logger.warning("hcloud domain response has no domains entry")
        return "", ""
    first = domains[0]
    return first.get("name", "") or "", first.get("id", "") or ""


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    """Locate the repository root (parent of the script directory).

    1. Walk one level up from this file's absolute path.

    Args:
        None

    Returns:
        Path: The repository root path.

    Examples:
        >>> _project_root().name
        'huawei-cloud-oa-risk-inspection'
    """
    return Path(__file__).resolve().parent.parent


def _template_dir() -> Path:
    """Locate the templates directory under the repository root.

    1. Join the repository root with the templates subdirectory.

    Args:
        None

    Returns:
        Path: The templates directory path (existence not guaranteed).

    Examples:
        >>> _template_dir().name
        'templates'
    """
    return _project_root() / "templates"


def _assets_dir() -> Path:
    """Locate the assets directory under the repository root.

    1. Join the repository root with the assets subdirectory.

    Args:
        None

    Returns:
        Path: The assets directory path (existence not guaranteed).

    Examples:
        >>> _assets_dir().name
        'assets'
    """
    return _project_root() / "assets"


def load_echarts_bundle() -> Optional[str]:
    """Load the offline echarts shards and join them into full JS source.

    1. Locate the assets directory and glob all echarts.part_*.js shards.
    2. Sort by file name (lexicographic order) and join into one string.
    3. Log a warning and return None when no shards exist.

    Args:
        None

    Returns:
        Optional[str]: The joined full echarts JS source; None when no
            shards exist.

    Examples:
        >>> bundle = load_echarts_bundle()
    """
    assets_dir = _assets_dir()
    parts = sorted(assets_dir.glob("echarts.part_*.js"))
    if not parts:
        logger.warning("No echarts shards found in %s, charts will degrade in HTML", assets_dir)
        return None
    return "".join(p.read_text(encoding="utf-8") for p in parts)


def load_template() -> Optional[str]:
    """Read the HTML report static template content.

    1. Locate the template file templates/report.html.
    2. Read the full text when it exists; log a warning and return None when
       missing.

    Args:
        None

    Returns:
        Optional[str]: The template text; None when the template is missing.

    Examples:
        >>> text = load_template()
    """
    template_path = _template_dir() / TEMPLATE_FILENAME
    if not template_path.exists():
        logger.error("HTML report template missing: %s, skipping HTML artifact", template_path)
        return None
    return template_path.read_text(encoding="utf-8")


def render_html(analysis: Dict[str, Any], out_dir: Path,
                timestamp: str) -> Optional[Path]:
    """Render the offline HTML report (echarts inlined into the template).

    1. Load the static template templates/report.html; return None when
       missing.
    2. Load the offline echarts shards and inject them into the
       __ECHARTS_BUNDLE__ placeholder.
    3. Serialize the analysis payload and inject it into the __DATA__
       placeholder.
    4. Write the HTML file to the output directory using the run timestamp,
       so the file name and its directory never disagree.

    Args:
        analysis: dict[str, Any] — The analysis payload.
        out_dir: Path — The output directory.
        timestamp: str — The run timestamp shared by every artifact.

    Returns:
        Optional[Path]: The written HTML file path; None when the template is
            missing.

    Examples:
        # >>> render_html({"meta": {}, "items": []}, Path("analysis"), "2026_11_06_18_30_00")
    """
    template = load_template()
    if template is None:
        return None
    echarts_bundle = load_echarts_bundle() or ""
    html = template.replace("__ECHARTS_BUNDLE__", echarts_bundle)
    data_json = json.dumps(analysis, ensure_ascii=False, indent=1)
    html = html.replace("__DATA__", data_json)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_HTML_NAME.format(ts=timestamp)
    target.write_text(html, encoding="utf-8")
    return target


def _risk_item_resources(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """Project one inspection item's resources onto the JSON fields.

    1. Iterate over the aggregated item resources.
    2. Keep the region, resource ID, resource name and status only, because
       those are what the scoped result has to show; the remaining Excel
       columns are not part of the risk-item document.

    Args:
        item: dict[str, Any] — One aggregated inspection item.

    Returns:
        list[dict[str, str]]: One entry per resource with the four fields.

    Examples:
        >>> _risk_item_resources({"resources": [{"id": "a", "name": "n"}]})
        [{'region': '', 'id': 'a', 'name': 'n', 'status': ''}]
    """
    resources: List[Dict[str, str]] = []
    for res in item.get("resources") or []:
        resources.append({
            "region": res.get("region_id", "") or "",
            "id": res.get("id", "") or "",
            "name": res.get("name", "") or "",
            "status": res.get("status", "") or "",
        })
    return resources


def build_risk_item_document(analysis: Dict[str, Any],
                             record_count: int) -> Dict[str, Any]:
    """Build the scoped risk-item document from the analysis payload.

    1. Read the cloud-service scope recorded by the merge step.
    2. Copy the aggregated risk items into the document, projecting each
       item's resources onto the region / id / name / status fields.
    3. Sum the risk items and their resources, and carry the number of
       merged records that entered the analysis, so the caller can state
       "matched N records but found no risk" correctly.

    Args:
        analysis: dict[str, Any] — The analysis payload built by
            build_analysis_data.
        record_count: int — The number of merged records analysed.

    Returns:
        dict[str, Any]: The risk-item document with services / totals / items.

    Examples:
        # >>> build_risk_item_document({"meta": {"cloud_service_filter": {"services": ["ecs"]}}, "items": []}, 30)["totals"]["records"]
        # 30
    """
    meta = analysis.get("meta") or {}
    scope = meta.get("cloud_service_filter") or {}
    items: List[Dict[str, Any]] = []
    for item in analysis.get("items") or []:
        items.append({
            "service_type_code": item.get("service_type_code", "") or "",
            "check_item_name": item.get("check_item_name", "") or "",
            "dimension": item.get("dimension", "") or "",
            "risk_level": item.get("risk_level", "") or "",
            "source": item.get("source", "") or "",
            "display_source": item.get("display_source", "") or "",
            "resource_count": item.get("resource_count", 0),
            "total_resources": item.get("total_resources", 0),
            "description": item.get("description", "") or "",
            "advice": item.get("advice", "") or "",
            "effect": item.get("effect", "") or "",
            "resources": _risk_item_resources(item),
        })
    total_resources = sum(len(entry["resources"]) for entry in items)
    return {
        "services": list(scope.get("services", []) or []),
        "totals": {
            "items": len(items),
            "resources": total_resources,
            "records": record_count,
        },
        "items": items,
    }


def render_risk_items(analysis: Dict[str, Any], out_dir: Path,
                      timestamp: str, record_count: int) -> Optional[Path]:
    """Write the scoped risk-item JSON when a cloud-service whitelist applied.

    1. Return None when the merged metadata carries no cloud-service scope,
       keeping full-tenant runs artifact-identical to before.
    2. Build the document from the same aggregated items the HTML and Excel
       renderers consume, so the three artifacts cannot disagree.
    3. Write it next to the reports with the shared run timestamp.

    Args:
        analysis: dict[str, Any] — The analysis payload.
        out_dir: Path — The output directory.
        timestamp: str — The run timestamp shared by every artifact.
        record_count: int — The number of merged records analysed.

    Returns:
        Optional[Path]: The written JSON path, or None when the run has no
            cloud-service scope.

    Examples:
        # >>> render_risk_items({"meta": {}, "items": []}, Path("analysis"), "2026_11_06_18_30_00", 0) is None
        True
    """
    meta = analysis.get("meta") or {}
    if not meta.get("cloud_service_filter"):
        return None
    document = build_risk_item_document(analysis, record_count)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_RISK_ITEMS_NAME.format(ts=timestamp)
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Excel rendering
# ---------------------------------------------------------------------------


def _sanitize_sheet_name(name: str, used: set[str]) -> str:
    """Produce a unique, Excel-legal sheet name from an item name.

    1. Strip characters illegal in Excel sheet names and collapse whitespace.
    2. Truncate to SHEET_NAME_MAX_LENGTH characters.
    3. Append a numeric suffix while the name collides with used names.

    Args:
        name: str — The raw inspection item name.
        used: set[str] — The set of already-used sheet names.

    Returns:
        str: A unique Excel-legal sheet name.

    Examples:
        >>> used = set()
        >>> _sanitize_sheet_name("DCS实例未开启自动备份", used)
        'DCS实例未开启自动备份'
    """
    cleaned = "".join(ch for ch in name if ch not in "[]:*?/\\").strip()
    if not cleaned:
        cleaned = "检查项"
    cleaned = cleaned[:SHEET_NAME_MAX_LENGTH]
    candidate = cleaned
    index = 2
    while candidate in used:
        suffix = f"_{index}"
        candidate = cleaned[:SHEET_NAME_MAX_LENGTH - len(suffix)] + suffix
        index += 1
    used.add(candidate)
    return candidate


def _quote_sheet_reference(sheet_name: str) -> str:
    """Escape a sheet name for use inside a workbook-internal reference.

    1. Double every embedded apostrophe, which is Excel's escape for a quote
       inside a quoted sheet name.
    2. Wrap the result in single quotes so spaces and other characters that
       are illegal in an unquoted reference stay literal.

    Args:
        sheet_name: str — The worksheet name to reference.

    Returns:
        str: The sheet name ready to be used as `'<name>'!A1`.

    Examples:
        >>> _quote_sheet_reference("ECS 实例检查")
        "'ECS 实例检查'"
        >>> _quote_sheet_reference("it's")
        "'it''s'"
    """
    return "'" + str(sheet_name).replace("'", "''") + "'"


def _internal_hyperlink(cell: Any, sheet_name: str, anchor: str = "A1") -> None:
    """Attach a workbook-internal jump to a cell.

    1. Build the target as a `location` reference rather than a URL, because
       openpyxl writes a plain string as an *external* relationship and Excel
       then reports the target as an invalid reference.
    2. Point the hyperlink at the cell's own coordinate and apply the link
       font so the cell reads as clickable.

    Args:
        cell: Any — The openpyxl cell that becomes the link.
        sheet_name: str — Destination worksheet name.
        anchor: str — Destination cell in A1 notation.

    Returns:
        None

    Examples:
        # >>> _internal_hyperlink(ws.cell(row=5, column=10), "风险检查总览")
    """
    from openpyxl.worksheet.hyperlink import Hyperlink
    location = "{}!{}".format(_quote_sheet_reference(sheet_name), anchor)
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=location)
    _style_hyperlink(cell)


def _style_hyperlink(cell: Any) -> None:
    """Apply the classic link-blue underlined font to a hyperlink cell.

    1. Set the cell font color to LINK_BLUE.
    2. Set the cell font underline to single.

    Args:
        cell: Any — The openpyxl cell holding a hyperlink.

    Returns:
        None

    Examples:
        >>> from openpyxl import Workbook
        >>> ws = Workbook().active
        >>> _style_hyperlink(ws.cell(row=1, column=1))
    """
    from openpyxl.styles import Font
    cell.font = Font(color=LINK_BLUE, underline="single")


def _write_overview_sheet(ws: Any, analysis: Dict[str, Any], sheet_names: Dict[str, str]) -> None:
    """Write the Excel overview sheet (account info + risk item table).

    1. Write the user name and check account at A1/A2.
    2. Write the risk item overview table headers (dimension / product /
       item / standard / result / risk level / risk resource count / total
       resources plus data source and jump-link columns).
    3. Write one row per aggregated inspection item; the jump-link cell
       shows 点击查看详情 and links to the item detail sheet through a
       workbook-internal `location` reference, which Excel and WPS both
       accept (a `#Sheet!A1` string would be written as an external link).

    Args:
        ws: Any — The openpyxl worksheet.
        analysis: dict[str, Any] — The analysis payload.
        sheet_names: dict[str, str] — Aggregated item key to sheet name.

    Returns:
        None

    Examples:
        # >>> _write_overview_sheet(ws, {"meta": {}, "items": [], "user": {"name": "u", "account": "a"}}, {})
    """
    user = analysis.get("user") or {}
    ws.cell(row=1, column=1, value="用户名")
    ws.cell(row=1, column=2, value=user.get("name", ""))
    ws.cell(row=2, column=1, value="检查账号")
    ws.cell(row=2, column=2, value=user.get("account", ""))
    headers = ["风险检查维度", "产品", "检查项名称", "判断标准", "检查结果", "风险等级",
               "风险资源数", "资源总数", "数据来源", "跳转链接"]
    for col, header in enumerate(headers, start=1):
        ws.cell(row=4, column=col, value=header)
    for row_offset, item in enumerate(analysis.get("items") or [], start=5):
        sheet_name = sheet_names.get(_item_sheet_key(item), "")
        row = [
            item.get("dimension", ""),
            item.get("service_type_code", ""),
            item.get("check_item_name", ""),
            item.get("description", ""),
            STATUS_RISK,
            item.get("risk_level", ""),
            item.get("resource_count", 0),
            item.get("total_resources", 0),
            item.get("display_source") or item.get("source", ""),
        ]
        for col, value in enumerate(row, start=1):
            ws.cell(row=row_offset, column=col, value=value)
        link_cell = ws.cell(row=row_offset, column=10, value="点击查看详情")
        if sheet_name:
            _internal_hyperlink(link_cell, sheet_name)
        else:
            link_cell.hyperlink = None


def _write_detail_sheet(ws: Any, item: Dict[str, Any]) -> None:
    """Write one Excel detail sheet for an aggregated inspection item.

    1. Write the header block: check time at row 1, then dimension /
       product / item name / standard / result / counts / effect / advice /
       resource list label starting at row 4 (rows 2-3 stay blank except
       the top back link in A2).
    2. Add a styled back-to-overview link at row 2 column 1 (A2) and after
       the last resource row plus one blank row.
    3. Write the resource detail table one blank row below the resource
       list label (resource header at row 14).

    Args:
        ws: Any — The openpyxl worksheet.
        item: dict[str, Any] — One aggregated inspection item.

    Returns:
        None

    Examples:
        # >>> _write_detail_sheet(ws, {"check_item_name": "x", "resources": []})
    """
    header_values: List[Tuple[str, str]] = [
        ("检查时间", _format_eval_time(item.get("end_time", ""))),
        ("风险检查维度", item.get("dimension", "")),
        ("产品", item.get("service_type_code", "")),
        ("检查项名称", item.get("check_item_name", "")),
        ("判断标准", item.get("description", "")),
        ("检查结果", STATUS_RISK),
        ("风险资源数/资源总数", f"{item.get('resource_count', 0)}/{item.get('total_resources', 0)}"),
        ("风险影响", item.get("effect", "")),
        ("优化建议", item.get("advice", "")),
        ("风险资源列表", ""),
    ]
    for index, (label, value) in enumerate(header_values):
        row = index + 1 if index == 0 else index + 3
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=value)
    top_cell = ws.cell(row=2, column=1, value="返回总览")
    _internal_hyperlink(top_cell, OVERVIEW_SHEET_NAME)

    resources = item.get("resources") or []
    resource_header_row = len(header_values) + 4
    if resources:
        for col, header in enumerate(_resource_columns(), start=1):
            ws.cell(row=resource_header_row, column=col, value=header)
        for offset, row in enumerate(_resource_rows(resources), start=1):
            for col, value in enumerate(row, start=1):
                ws.cell(row=resource_header_row + offset, column=col, value=value)
        last_row = resource_header_row + len(resources)
    else:
        last_row = len(header_values) + 2
    back_cell = ws.cell(row=last_row + 2, column=1, value="返回总览")
    _internal_hyperlink(back_cell, OVERVIEW_SHEET_NAME)


def _item_sheet_key(item: Dict[str, Any]) -> str:
    """Build the key that links an inspection item to its detail sheet.

    1. Join check_item_id, source and workspace_id with a NUL separator.
    2. Return the joined key so the sheet lookup mirrors the aggregation key
       and same-named baselines of different instances keep separate sheets.

    Args:
        item: dict[str, Any] — One aggregated inspection item.

    Returns:
        str: The stable key shared by the sheet-name map and its lookups.

    Examples:
        # >>> _item_sheet_key({"check_item_id": "a", "source": "Config"}) == "a\\u0000Config\\u0000"
        True
    """
    return "\u0000".join([
        item.get("check_item_id", "") or "",
        item.get("source", "") or "",
        item.get("workspace_id", "") or "",
    ])


def render_xlsx(analysis: Dict[str, Any], out_dir: Path,
                timestamp: str) -> Optional[Path]:
    """Render the Excel workbook (overview + detail sheets).

    1. Try to import openpyxl; log a warning and return None when missing.
    2. Create the overview sheet first, then one detail sheet per
       aggregated inspection item.
    3. Write the workbook to the output directory using the run timestamp,
       so the file name and its directory never disagree.

    Args:
        analysis: dict[str, Any] — The analysis payload.
        out_dir: Path — The output directory.
        timestamp: str — The run timestamp shared by every artifact.

    Returns:
        Optional[Path]: The written xlsx file path; None when openpyxl is
            missing.

    Examples:
        # >>> render_xlsx({"meta": {}, "items": []}, Path("analysis"), "2026_11_06_18_30_00")
    """
    try:
        from openpyxl import Workbook
    except ImportError:
        logger.warning("openpyxl is not installed, skipping Excel workbook generation")
        return None

    wb = Workbook()
    overview_ws = wb.active
    overview_ws.title = OVERVIEW_SHEET_NAME
    sheet_names: Dict[str, str] = {}
    used: set[str] = {OVERVIEW_SHEET_NAME}
    for item in analysis.get("items") or []:
        sheet_name = _sanitize_sheet_name(item.get("check_item_name", ""), used)
        key = _item_sheet_key(item)
        sheet_names[key] = sheet_name
    _write_overview_sheet(overview_ws, analysis, sheet_names)
    for item in analysis.get("items") or []:
        key = _item_sheet_key(item)
        detail_ws = wb.create_sheet(title=sheet_names.get(key, "检查项"))
        _write_detail_sheet(detail_ws, item)

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUTPUT_XLSX_NAME.format(ts=timestamp)
    wb.save(str(target))
    return target


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    1. Add the required --input option.
    2. Add the optional --output-dir / --timeout / --log-file options. No
       region option is registered: the region is fixed to CLI_REGION.

    Args:
        None

    Returns:
        argparse.ArgumentParser: The configured argument parser.

    Examples:
        >>> parser = build_parser()
    """
    parser = argparse.ArgumentParser(
        prog="merge_report_generator",
        description="Generate offline HTML report and Excel workbook from merged OA / Config / SecMaster inspection results")
    parser.add_argument("--input", required=True,
                        help="Required. Absolute path of the merged inspection results JSON file")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="Optional. Output directory for artifacts (default: %(default)s)")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Optional. Timeout in seconds for the hcloud command (default: %(default)s).")
    parser.add_argument("--log-file", default=None,
                        help="Optional. Path to a log file; logs are appended to stderr as well")
    return parser


def print_summary(analysis: Dict[str, Any], written_files: List[str]) -> None:
    """Emit the generation summary via logging to stderr.

    1. Output the classification and aggregated item counts.
    2. Output the per-source risk counts.
    3. Output the check-item level hint and failure totals.
    4. Output the written file paths.

    Args:
        analysis: dict[str, Any] — The analysis payload.
        written_files: list[str] — The list of written file paths.

    Returns:
        None

    Examples:
        # >>> print_summary({"meta": {}, "items": [], "coverage": {}}, [])
    """
    items = analysis.get("items") or []
    coverage = analysis.get("coverage") or {}
    oa_console_cov = coverage.get("oa_console") or {}
    config_cov = coverage.get("config") or {}
    secmaster_cov = coverage.get("secmaster") or {}
    failed_cov = coverage.get("failed") or {}
    non_risk_total = (oa_console_cov.get("security", 0)
                      + oa_console_cov.get("not_involved", 0)
                      + config_cov.get("compliant_rules", 0)
                      + secmaster_cov.get("qualified", 0))
    item_counts = {"OA": 0, "Config": 0, "SecMaster": 0}
    for item in items:
        if item.get("source") in item_counts:
            item_counts[item["source"]] += 1
    logger.info("=" * 60)
    logger.info("Merged inspection report generation completed")
    logger.info("=" * 60)
    logger.info("Risk items: %d (OA %d, Config %d, SecMaster %d)",
                len(items),
                item_counts.get("OA", 0),
                item_counts.get("Config", 0),
                item_counts.get("SecMaster", 0))
    logger.info("Hint items (OA console): %d", oa_console_cov.get("hint", 0))
    logger.info("Non-risk items (check-item level): %d", non_risk_total)
    logger.info("Uninspected items (check-item level): %d",
                secmaster_cov.get("uninspected", 0))
    logger.info("Failed items (check-item level): %d", failed_cov.get("total", 0))
    if written_files:
        logger.info("-" * 60)
        logger.info("Generated files:")
        for file_path in written_files:
            logger.info("  - %s", file_path)
    logger.info("=" * 60)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main entry wiring up parsing, analysis and artifact generation.

    1. Configure basic logging output (stderr by default, optional
       --log-file handler).
    2. Parse the command-line arguments and validate the required input.
    3. Load the merged input and build the analysis payload.
    4. Resolve the account user name / ID via hcloud with the fixed
       CLI_REGION, store the pair on analysis.user for the Excel overview
       and the ID on analysis.meta.domain_id for the HTML metadata block.
    5. Render the HTML report and the Excel workbook into a timestamped
       subdirectory under --output-dir, plus the scoped risk-item JSON when
       the merged input records a cloud-service whitelist.
    6. Emit the summary via logging.

    Args:
        argv: Optional[Sequence[str]] — The command-line argument list, or
            sys.argv[1:] when None.

    Returns:
        int: The exit code; 0 for success, 1 for failure.

    Examples:
        # >>> main(["--input", "merge_inspection_results.json"])
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_file)
    logger.info("Task started. Input: %s", args.input)
    try:
        merged = load_json_file(args.input)
    except ValueError as exc:
        logger.error("Failed to load input file: %s", exc)
        return 1
    analysis = build_analysis_data(merged)
    user_name, account_id = resolve_domain_info(CLI_REGION, args.timeout)
    analysis["user"] = {"name": user_name, "account": account_id}
    # The HTML metadata block reads the account ID from meta.domain_id.
    analysis.setdefault("meta", {})["domain_id"] = account_id
    # One run timestamp for the directory and every file name, so a run that
    # crosses a second boundary cannot split them.
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    out_dir = Path(args.output_dir).resolve() / timestamp
    record_count = len(merged.get("results", []) or [])
    written_files: List[str] = []
    html_path = render_html(analysis, out_dir, timestamp)
    if html_path is not None:
        written_files.append(str(html_path))
    xlsx_path = render_xlsx(analysis, out_dir, timestamp)
    if xlsx_path is not None:
        written_files.append(str(xlsx_path))
    risk_items_path = render_risk_items(analysis, out_dir, timestamp, record_count)
    if risk_items_path is not None:
        written_files.append(str(risk_items_path.resolve()))
        logger.info("Risk item scope file: %s", risk_items_path.resolve())
    print_summary(analysis, written_files)
    logger.info("Task finished. Output files: %s", ", ".join(written_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
