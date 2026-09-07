#!/usr/bin/env python3
"""Check generated Huawei Cloud questions against registry and risk gates."""

from __future__ import annotations

import argparse
import collections
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import hcloud_change_plan
import hcloud_common

ROOT = hcloud_common.ROOT
DEFAULT_QUESTIONS_DIR = ROOT / "references" / "maintenance" / "question-coverage"
DEFAULT_XLSX_PATH: Path | None = None
REGISTRY_PATH = hcloud_common.REGISTRY_PATH
DEFAULT_MIN_REGISTERED_RATIO = 0.10

XLSX_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XLSX_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

SERVICE_ALIASES = {
    "安全组": "VPC",
    "子网": "VPC",
    "路由表": "VPC",
    "网关": "VPC",
    "云硬盘": "EVS",
    "镜像": "IMS",
    "密钥对": "KPS",
    "NAT网关": "NAT",
    "弹性公网": "EIP",
    "负载均衡": "ELB",
    "云监控": "CES",
    "对象存储": "OBS",
}

OPERATION_SERVICE_HINTS = [
    ("VPC", ("Vpc", "Subnet", "SecurityGroup", "RouteTable", "Route", "Firewall", "Port", "Peer")),
    ("EIP", ("Publicip", "PublicIp", "Bandwidth", "Eip", "FloatingIp")),
    ("ELB", ("Loadbalancer", "Listener", "Member", "Pool", "HealthMonitor", "L7", "Whitelist")),
    ("EVS", ("Volume", "Snapshot", "Cinder")),
    ("IMS", ("Image", "Glance")),
    ("KPS", ("Keypair", "PrivateKey")),
    ("NAT", ("NatGateway", "Dnat", "Snat", "TransitIp")),
    ("RDS", ("Instance", "Database", "DbUser", "Backup", "SlowLog", "Configuration", "Sql", "Datastore")),
    ("DNS", ("RecordSet",)),
    ("SCM", ("Certificate",)),
    ("OBS", ("Bucket",)),
    ("CES", ("Metric",)),
    ("CCE", ("Cluster", "Node")),
]

EXTERNAL_VALIDATION_PATTERNS = [
    "web_fetch",
    "HTTP 探测",
    "HTTPS 探测",
    "curl",
    "kubectl",
    "Docker Remote API",
    "控制台",
    "ping",
    "SELECT ",
    "SHOW VARIABLES",
]

SIDE_EFFECT_VALIDATION_PATTERNS = [
    "停掉",
    "设置为禁用",
    "恢复",
    "POST ",
    "创建容器",
    "启动该容器",
    "创建一个 Nginx Pod",
    "touch ",
    "docker run",
]

VALIDATION_OPERATION_ALIASES = {
    ("CDN", "ShowDomain"): "ShowDomainDetail",
    ("ECS", "ListServers"): "ListServersDetails",
    ("RDS", "ShowConfigurationDetail"): "ShowConfiguration",
}


def normalize_operation(value: str) -> str:
    """Return a loose operation key for case-insensitive matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def split_api_reference(raw_api: str, default_service: str) -> tuple[str, str]:
    """Split a question API reference into service and operation parts."""
    if "-" in raw_api:
        service, operation = raw_api.split("-", 1)
        return service.upper(), operation
    return default_service.upper(), raw_api


def load_json(path: Path) -> Any:
    """Return parsed JSON content from a file."""
    return hcloud_common.load_json(path)


def load_registry_operations(path: Path = REGISTRY_PATH) -> dict[str, set[str]]:
    """Return registry operation names keyed by service."""
    if not path.exists():
        return {}
    registry = load_json(path)
    operations: dict[str, set[str]] = {}
    for service, entry in registry.get("services", {}).items():
        service_ops = set(entry.get("query_operations", []))
        service_ops.update(entry.get("resource_query_operations", []))
        service_ops.update(entry.get("change_operations", []))
        operations[service.upper()] = {normalize_operation(operation) for operation in service_ops}
    return operations


def load_registry_execution_paths(path: Path = REGISTRY_PATH) -> dict[str, dict[str, dict[str, str]]]:
    """Return executable script paths for registered operations."""
    if not path.exists():
        return {}
    registry = load_json(path)
    execution_paths: dict[str, dict[str, dict[str, str]]] = {}
    for service, entry in registry.get("services", {}).items():
        service_key = service.upper()
        service_paths: dict[str, dict[str, str]] = {}
        query_runner = entry.get("query_runner") or "scripts/hcloud_resource_discovery.py"
        resource_query_runner = entry.get("resource_query_runner") or "scripts/hcloud_resource_query.py"
        for operation in entry.get("query_operations", []):
            service_paths[normalize_operation(operation)] = {
                "operation": operation,
                "scope": "query",
                "runner": query_runner,
            }
        for operation in entry.get("resource_query_operations", []):
            service_paths[normalize_operation(operation)] = {
                "operation": operation,
                "scope": "resource_query",
                "runner": resource_query_runner,
            }
        for operation in entry.get("change_operations", []):
            change_flow = entry.get("change_flow")
            service_paths[normalize_operation(operation)] = {
                "operation": operation,
                "scope": "guarded_change" if change_flow else "planner_only_change",
                "runner": change_flow or entry.get("planner") or "missing_planner",
            }
        execution_paths[service_key] = service_paths
    return execution_paths


def load_registry_services(path: Path = REGISTRY_PATH) -> set[str]:
    """Return registered service names."""
    if not path.exists():
        return set()
    registry = load_json(path)
    return {service.upper() for service in registry.get("services", {})}


def iter_question_files(questions_dir: Path) -> list[tuple[str, Path]]:
    """Return generated question files grouped by subset."""
    files: list[tuple[str, Path]] = []
    for subset in ("read_type", "crud"):
        subset_dir = questions_dir / subset
        if subset_dir.exists():
            files.extend((subset, path) for path in sorted(subset_dir.glob("*.json")))
    return files


def expected_crud_type(path: Path) -> str:
    """Infer expected CRUD type from a file name like ecs_update.json."""
    return path.stem.rsplit("_", 1)[-1]


def parse_min_registered_ratios(values: list[str]) -> dict[str, float]:
    """Parse service coverage thresholds from SERVICE=RATIO strings."""
    ratios: dict[str, float] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid ratio threshold, expected SERVICE=RATIO: {value}")
        service, raw_ratio = value.split("=", 1)
        try:
            ratio = float(raw_ratio)
        except ValueError as exc:
            raise ValueError(f"Invalid ratio value for {service}: {raw_ratio}") from exc
        if ratio < 0 or ratio > 1:
            raise ValueError(f"Ratio must be between 0 and 1 for {service}: {raw_ratio}")
        ratios[service.upper()] = ratio
    return ratios


def coverage_errors_from_registry(
    registry_by_service: dict[str, collections.Counter[str]],
    thresholds: dict[str, float],
    default_threshold: float | None,
) -> list[dict[str, Any]]:
    """Return services whose registered operation ratio is below threshold."""
    errors: list[dict[str, Any]] = []
    for service, counter in sorted(registry_by_service.items()):
        total = counter.get("total", 0)
        if not total:
            continue
        threshold = thresholds.get(service, default_threshold)
        if threshold is None:
            continue
        registered = counter.get("registered", 0)
        ratio = registered / total
        if ratio < threshold:
            errors.append(
                {
                    "service": service,
                    "registered": registered,
                    "total": total,
                    "registered_ratio": round(ratio, 4),
                    "min_registered_ratio": threshold,
                    "error": "Registry coverage ratio is below threshold.",
                }
            )
    return errors


def cell_column_index(cell_ref: str) -> int:
    """Return zero-based column index from an Excel cell reference."""
    column = "".join(ch for ch in cell_ref if ch.isalpha()).upper()
    index = 0
    for ch in column:
        index = index * 26 + ord(ch) - ord("A") + 1
    return max(index - 1, 0)


def collect_text(element: ET.Element, namespace: str = XLSX_MAIN_NS) -> str:
    """Return concatenated text nodes from an XLSX XML element."""
    return "".join(node.text or "" for node in element.findall(f".//{{{namespace}}}t"))


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Read XLSX shared strings using only the standard library."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [collect_text(item) for item in root.findall(f"{{{XLSX_MAIN_NS}}}si")]


def workbook_sheet_paths(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return worksheet names and XML paths from an XLSX archive."""
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_by_id = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in rels.findall(f"{{{PACKAGE_REL_NS}}}Relationship")
        if item.attrib.get("Target")
    }

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall(f".//{{{XLSX_MAIN_NS}}}sheet"):
        name = sheet.attrib.get("name", "")
        rel_id = sheet.attrib.get(f"{{{XLSX_REL_NS}}}id")
        target = rel_by_id.get(rel_id or "")
        if not target:
            continue
        path = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
        sheets.append((name, path))
    return sheets


def read_xlsx_rows(path: Path) -> dict[str, list[list[str]]]:
    """Read worksheet rows from a simple .xlsx file without external packages."""
    rows_by_sheet: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(path) as archive:
        shared_strings = read_shared_strings(archive)
        for sheet_name, sheet_path in workbook_sheet_paths(archive):
            if sheet_path not in archive.namelist():
                continue
            sheet_root = ET.fromstring(archive.read(sheet_path))
            sheet_rows: list[list[str]] = []
            for row in sheet_root.findall(f".//{{{XLSX_MAIN_NS}}}row"):
                values: list[str] = []
                for cell in row.findall(f"{{{XLSX_MAIN_NS}}}c"):
                    ref = cell.attrib.get("r", "")
                    column_index = cell_column_index(ref)
                    while len(values) <= column_index:
                        values.append("")
                    cell_type = cell.attrib.get("t")
                    if cell_type == "s":
                        raw_value = cell.findtext(f"{{{XLSX_MAIN_NS}}}v")
                        value = shared_strings[int(raw_value)] if raw_value is not None else ""
                    elif cell_type == "inlineStr":
                        inline = cell.find(f"{{{XLSX_MAIN_NS}}}is")
                        value = collect_text(inline) if inline is not None else ""
                    else:
                        value = cell.findtext(f"{{{XLSX_MAIN_NS}}}v") or ""
                    values[column_index] = str(value).strip()
                sheet_rows.append(values)
            rows_by_sheet[sheet_name] = sheet_rows
    return rows_by_sheet


def question_validation_pairs(rows: list[list[str]]) -> tuple[int | None, list[tuple[int, int]]]:
    """Find question/validation-method column pairs in worksheet rows."""
    for row_index, row in enumerate(rows[:5]):
        normalized = [str(value).strip() for value in row]
        pairs = []
        for index, value in enumerate(normalized):
            if value == "问题" and index + 1 < len(normalized) and normalized[index + 1] == "验证方法":
                pairs.append((index, index + 1))
        if pairs:
            return row_index, pairs
    return None, []


def infer_service(text: str, operation: str) -> str | None:
    """Infer a Huawei Cloud service from validation text and operation name."""
    text_upper = text.upper()
    for service in ("ECS", "EIP", "ELB", "RDS", "VPC", "EVS", "IMS", "KPS", "NAT", "CCE", "CDN", "DNS", "SCM", "OBS", "CES"):
        if re.search(rf"\b{service}\b", text_upper):
            return service
    for keyword, service in SERVICE_ALIASES.items():
        if keyword in text:
            return service
    for service, hints in OPERATION_SERVICE_HINTS:
        if any(hint.lower() in operation.lower() for hint in hints):
            return service
    return None


def looks_like_operation_reference(value: str) -> bool:
    """Return whether a parenthesized token looks like an API operation name."""
    return bool(value) and value[0].isupper() and not value.isupper() and not value.islower()


def infer_nearest_service(prefix: str, operation: str) -> str | None:
    """Infer service from the nearest marker before an operation reference."""
    candidates: list[tuple[int, str]] = []
    prefix_upper = prefix.upper()
    for service in ("ECS", "EIP", "ELB", "RDS", "VPC", "EVS", "IMS", "KPS", "NAT", "CCE", "CDN", "DNS", "SCM", "OBS", "CES"):
        for match in re.finditer(rf"\b{service}\b", prefix_upper):
            candidates.append((match.start(), service))
    for keyword, service in SERVICE_ALIASES.items():
        position = prefix.rfind(keyword)
        if position >= 0:
            candidates.append((position, service))
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    return infer_service(prefix, operation)


def extract_validation_operations(text: str) -> list[dict[str, str]]:
    """Extract explicit operation references from a validation method."""
    operations: list[dict[str, str]] = []
    for match in re.finditer(r"[（(]([A-Za-z][A-Za-z0-9_]*)[）)]", text):
        operation = match.group(1)
        if not looks_like_operation_reference(operation):
            continue
        context = text[max(0, match.start() - 60) : min(len(text), match.end() + 60)]
        prefix = text[max(0, match.start() - 80) : match.start()]
        service = infer_nearest_service(prefix, operation) or infer_service(text, operation) or "UNKNOWN"
        operations.append({"service": service, "operation": operation, "context": context.strip()})
    return operations


def analyze_validation_workbook(xlsx_path: Path, registry_path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Analyze hand-written E2E questions and validation methods from data.xlsx."""
    if not xlsx_path.exists():
        return {
            "success": True,
            "skipped": True,
            "xlsx_path": str(xlsx_path),
            "reason": "Workbook does not exist.",
            "status_summary": {"passed": 0, "skipped": 1, "not_covered": 0},
        }

    registered_services = load_registry_services(registry_path)
    registry_operations = load_registry_operations(registry_path)
    registry_execution_paths = load_registry_execution_paths(registry_path)
    schema_errors: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    operation_counter: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    unregistered_operations: list[dict[str, Any]] = []
    unregistered_services: collections.Counter[str] = collections.Counter()
    executable_paths: collections.Counter[str] = collections.Counter()
    execution_path_errors: list[dict[str, Any]] = []
    external_validation_refs: collections.Counter[str] = collections.Counter()
    side_effect_warnings: list[dict[str, Any]] = []
    operation_aliases_applied: collections.Counter[str] = collections.Counter()

    try:
        workbook = read_xlsx_rows(xlsx_path)
    except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
        return {
            "success": False,
            "skipped": False,
            "xlsx_path": str(xlsx_path),
            "schema_errors": [{"error": f"Cannot read workbook: {exc}"}],
            "status_summary": {"passed": 0, "skipped": 0, "not_covered": 1},
        }

    for sheet_name, rows in workbook.items():
        header_index, pairs = question_validation_pairs(rows)
        if header_index is None:
            schema_errors.append({"sheet": sheet_name, "error": "Missing 问题/验证方法 header pair."})
            continue

        for row_index, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
            for pair_index, (question_col, validation_col) in enumerate(pairs, start=1):
                question = row[question_col] if question_col < len(row) else ""
                validation = row[validation_col] if validation_col < len(row) else ""
                if not question and not validation:
                    continue
                if not question or not validation:
                    schema_errors.append(
                        {
                            "sheet": sheet_name,
                            "row": row_index,
                            "pair": pair_index,
                            "error": "Question and validation method must both be present.",
                        }
                    )
                    continue

                operations = extract_validation_operations(validation)
                for item in operations:
                    service = item["service"]
                    operation = item["operation"]
                    canonical_operation = VALIDATION_OPERATION_ALIASES.get((service, operation), operation)
                    if canonical_operation != operation:
                        operation_aliases_applied[f"{service}:{operation}->{canonical_operation}"] += 1
                    operation_counter[service][operation] += 1
                    if service not in registered_services:
                        unregistered_services[service] += 1
                        continue
                    normalized_operation = normalize_operation(canonical_operation)
                    if normalized_operation not in registry_operations.get(service, set()):
                        unregistered_operations.append(
                            {
                                "sheet": sheet_name,
                                "row": row_index,
                                "pair": pair_index,
                                "service": service,
                                "operation": operation,
                                "canonical_operation": canonical_operation,
                            }
                        )
                        continue
                    execution_path = registry_execution_paths.get(service, {}).get(normalized_operation)
                    if not execution_path or execution_path.get("runner") == "missing_planner":
                        execution_path_errors.append(
                            {
                                "sheet": sheet_name,
                                "row": row_index,
                                "pair": pair_index,
                                "service": service,
                                "operation": operation,
                                "canonical_operation": canonical_operation,
                                "error": "Registered validation operation has no executable path.",
                            }
                        )
                    else:
                        executable_paths[f"{service}:{execution_path['scope']}:{execution_path['runner']}"] += 1

                for pattern in EXTERNAL_VALIDATION_PATTERNS:
                    if pattern in validation:
                        external_validation_refs[pattern] += 1
                for pattern in SIDE_EFFECT_VALIDATION_PATTERNS:
                    if pattern in validation:
                        side_effect_warnings.append(
                            {
                                "sheet": sheet_name,
                                "row": row_index,
                                "pair": pair_index,
                                "pattern": pattern,
                            }
                        )

                records.append(
                    {
                        "sheet": sheet_name,
                        "row": row_index,
                        "pair": pair_index,
                        "operation_count": len(operations),
                    }
                )

    passed_count = sum(executable_paths.values())
    not_covered_count = (
        len(unregistered_operations)
        + sum(unregistered_services.values())
        + len(execution_path_errors)
    )

    return {
        "success": not schema_errors and not execution_path_errors,
        "skipped": False,
        "xlsx_path": str(xlsx_path),
        "status_summary": {
            "passed": passed_count,
            "skipped": 0,
            "not_covered": not_covered_count,
        },
        "sheet_count": len(workbook),
        "record_count": len(records),
        "schema_errors": schema_errors,
        "operation_summary_by_service": {
            service: dict(sorted(counter.items())) for service, counter in sorted(operation_counter.items())
        },
        "unregistered_services": dict(sorted(unregistered_services.items())),
        "unregistered_operations_sample": unregistered_operations[:50],
        "unregistered_operation_count": len(unregistered_operations),
        "execution_path_errors_sample": execution_path_errors[:50],
        "execution_path_error_count": len(execution_path_errors),
        "executable_validation_paths": dict(sorted(executable_paths.items())),
        "operation_aliases_applied": dict(sorted(operation_aliases_applied.items())),
        "external_validation_refs": dict(sorted(external_validation_refs.items())),
        "side_effect_warnings_sample": side_effect_warnings[:50],
        "side_effect_warning_count": len(side_effect_warnings),
    }


def analyze_questions(
    questions_dir: Path,
    registry_path: Path = REGISTRY_PATH,
    xlsx_path: Path | None = DEFAULT_XLSX_PATH,
    min_registered_ratios: dict[str, float] | None = None,
    default_min_registered_ratio: float | None = DEFAULT_MIN_REGISTERED_RATIO,
) -> dict[str, Any]:
    """Analyze generated question files for schema, risk, registry, and workbook coverage."""
    if not questions_dir.exists():
        return {
            "success": False,
            "questions_dir": str(questions_dir),
            "error": "Questions directory does not exist.",
        }

    registry_operations = load_registry_operations(registry_path)
    schema_errors: list[dict[str, Any]] = []
    type_errors: list[dict[str, Any]] = []
    risk_errors: list[dict[str, Any]] = []
    weighted_risk_summary: collections.Counter[str] = collections.Counter()
    unique_operations: dict[tuple[str, str], dict[str, Any]] = {}
    registry_by_service: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    file_summaries: list[dict[str, Any]] = []

    for subset, path in iter_question_files(questions_dir):
        data = load_json(path)
        default_service = path.stem.split("_", 1)[0]
        expected_type = expected_crud_type(path) if subset == "crud" else None
        file_counter: collections.Counter[str] = collections.Counter()

        if not isinstance(data, list):
            schema_errors.append({"file": str(path), "error": "Top-level JSON value must be a list."})
            continue

        for index, item in enumerate(data):
            if not isinstance(item, dict):
                schema_errors.append({"file": str(path), "index": index, "error": "Item must be an object."})
                continue
            question = item.get("question")
            apis = item.get("relevant_apis")
            if not isinstance(question, str) or not question.strip():
                schema_errors.append({"file": str(path), "index": index, "error": "Missing non-empty question."})
            if not isinstance(apis, list) or not apis:
                schema_errors.append({"file": str(path), "index": index, "error": "Missing non-empty relevant_apis."})
                continue
            if subset == "crud" and item.get("type") != expected_type:
                type_errors.append(
                    {
                        "file": str(path),
                        "index": index,
                        "actual": item.get("type"),
                        "expected": expected_type,
                    }
                )

            for api in apis:
                service, operation = split_api_reference(str(api), default_service)
                risk = hcloud_change_plan.assess_risk(operation, dryrun_supported=True)
                tokens = hcloud_change_plan.operation_tokens(operation)
                read_only = hcloud_change_plan.looks_read_only(tokens)
                weighted_risk_summary[risk.level] += 1
                file_counter[risk.level] += 1
                unique_operations[(service, normalize_operation(operation))] = {
                    "service": service,
                    "operation": operation,
                    "risk": risk.level,
                    "read_only": read_only,
                }

                registry_counter = registry_by_service[service]
                registry_counter["total"] += 1
                if normalize_operation(operation) in registry_operations.get(service, set()):
                    registry_counter["registered"] += 1

                if subset == "read_type" and risk.level == "medium":
                    risk_errors.append(
                        {
                            "file": str(path),
                            "index": index,
                            "operation": operation,
                            "error": "Read-type dataset operation was conservatively gated as medium risk.",
                        }
                    )
                if subset == "crud" and expected_type == "read" and risk.level == "medium":
                    risk_errors.append(
                        {
                            "file": str(path),
                            "index": index,
                            "operation": operation,
                            "error": "CRUD read operation was conservatively gated as medium risk.",
                        }
                    )
                if subset == "crud" and expected_type == "delete" and not read_only and risk.level != "high":
                    risk_errors.append(
                        {
                            "file": str(path),
                            "index": index,
                            "operation": operation,
                            "risk": risk.level,
                            "error": "Non-read delete operation must be high risk.",
                        }
                    )
                if subset == "crud" and expected_type in {"delete", "update"} and not read_only and not risk.requires_confirmation:
                    risk_errors.append(
                        {
                            "file": str(path),
                            "index": index,
                            "operation": operation,
                            "risk": risk.level,
                            "error": "Non-read delete/update operation must require confirmation.",
                        }
                    )

        file_summaries.append(
            {
                "file": str(path.relative_to(questions_dir)),
                "items": len(data),
                "risk_summary": dict(sorted(file_counter.items())),
            }
        )

    unique_risk_summary = collections.Counter(item["risk"] for item in unique_operations.values())
    xlsx_validation = analyze_validation_workbook(xlsx_path, registry_path) if xlsx_path is not None else None
    workbook_success = True if xlsx_validation is None else xlsx_validation["success"]
    coverage_errors = coverage_errors_from_registry(
        registry_by_service,
        min_registered_ratios or {},
        default_min_registered_ratio,
    )

    return {
        "success": not schema_errors and not type_errors and not risk_errors and not coverage_errors and workbook_success,
        "questions_dir": str(questions_dir),
        "files_checked": len(iter_question_files(questions_dir)),
        "schema_errors": schema_errors,
        "type_errors": type_errors,
        "risk_errors": risk_errors,
        "coverage_errors": coverage_errors,
        "default_min_registered_ratio": default_min_registered_ratio,
        "min_registered_ratios": dict(sorted((min_registered_ratios or {}).items())),
        "weighted_risk_summary": dict(sorted(weighted_risk_summary.items())),
        "unique_operation_count": len(unique_operations),
        "unique_risk_summary": dict(sorted(unique_risk_summary.items())),
        "registry_coverage_by_service": {
            service: dict(counter) for service, counter in sorted(registry_by_service.items())
        },
        "file_summaries": file_summaries,
        "xlsx_validation": xlsx_validation,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions-dir", default=str(DEFAULT_QUESTIONS_DIR), help="Path to generated_questions.")
    parser.add_argument("--xlsx-path", help="Explicit optional path to data.xlsx validation data.")
    parser.add_argument("--skip-xlsx", action="store_true", help="Do not analyze data.xlsx validation data.")
    parser.add_argument("--registry", default=str(REGISTRY_PATH), help="Path to service-registry.json.")
    parser.add_argument(
        "--default-min-registered-ratio",
        type=float,
        default=DEFAULT_MIN_REGISTERED_RATIO,
        help="Default minimum registry coverage ratio for services present in generated_questions. Use -1 to disable.",
    )
    parser.add_argument(
        "--min-registered-ratio",
        action="append",
        default=[],
        help="Per-service registry coverage threshold as SERVICE=RATIO. Can be repeated.",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.default_min_registered_ratio < -1 or args.default_min_registered_ratio > 1:
        parser.error("--default-min-registered-ratio must be between 0 and 1, or -1 to disable.")
    return args


def main() -> int:
    """Run the generated question coverage check."""
    args = parse_args()
    xlsx_path = None if args.skip_xlsx or not args.xlsx_path else Path(args.xlsx_path)
    try:
        min_registered_ratios = parse_min_registered_ratios(args.min_registered_ratio)
    except ValueError as exc:
        result = {"success": False, "error": str(exc)}
    else:
        default_min = None if args.default_min_registered_ratio < 0 else args.default_min_registered_ratio
        result = analyze_questions(
            Path(args.questions_dir),
            Path(args.registry),
            xlsx_path,
            min_registered_ratios=min_registered_ratios,
            default_min_registered_ratio=default_min,
        )
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
