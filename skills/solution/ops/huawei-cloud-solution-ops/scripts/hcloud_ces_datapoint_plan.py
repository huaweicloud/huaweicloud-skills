#!/usr/bin/env python3
"""Build, run, or interpret a read-only CES datapoint query plan."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_ces_alarm_plan
import hcloud_common

ALLOWED_FILTERS = {"average", "variance", "min", "max", "sum"}
ALLOWED_PERIODS = {1, 60, 300, 1200, 3600, 14400, 86400}
MAX_BATCH_QUERY_POINTS = 3000
DEFAULT_LOOKBACK_MINUTES = 30


def scalar_cli_value(value: Any) -> str:
    """Return a stable KooCLI scalar argument value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_cli_args(prefix: str, value: Any) -> list[str]:
    """Flatten a JSON-like body into KooCLI dot-notation arguments."""
    if value in (None, "", []):
        return []
    if isinstance(value, dict):
        args: list[str] = []
        for key, child in value.items():
            args.extend(flatten_cli_args(f"{prefix}.{key}", child))
        return args
    if isinstance(value, list):
        args = []
        for index, child in enumerate(value, start=1):
            args.extend(flatten_cli_args(f"{prefix}.{index}", child))
        return args
    return [f"--{prefix}={scalar_cli_value(value)}"]


def parse_dimensions(values: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    """Parse repeated CES dimension name=value arguments."""
    dimensions: list[dict[str, str]] = []
    errors: list[str] = []
    seen_names: set[str] = set()
    for item in values:
        if "=" not in item:
            errors.append(f"Invalid --dimension value, expected name=value: {item}")
            continue
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            errors.append(f"Invalid --dimension value, expected non-empty name=value: {item}")
            continue
        if name in seen_names:
            errors.append(f"Duplicate CES dimension name: {name}.")
            continue
        seen_names.add(name)
        dimensions.append({"name": name, "value": value})
    return dimensions, errors


def resolve_time_window(args: argparse.Namespace) -> tuple[int | None, int | None, list[str]]:
    """Return from/to timestamps in milliseconds for the datapoint query."""
    errors: list[str] = []
    to_ms = args.to_ms if args.to_ms is not None else int(time.time() * 1000)
    from_ms = args.from_ms
    if from_ms is None:
        from_ms = to_ms - args.lookback_minutes * 60 * 1000
    if from_ms >= to_ms:
        errors.append("--from-ms must be earlier than --to-ms.")
    return from_ms, to_ms, errors


def metric_guidance(namespace: str | None, metric_name: str | None, period: int) -> dict[str, Any] | None:
    """Return local CES metric guidance for the requested metric when available."""
    if not namespace or not metric_name:
        return None
    return hcloud_ces_alarm_plan.metric_guidance(
        SimpleNamespace(namespace=namespace, metric_name=metric_name, period=period)
    )


def build_request_body(
    args: argparse.Namespace,
    dimensions: list[dict[str, str]],
    from_ms: int | None,
    to_ms: int | None,
) -> dict[str, Any]:
    """Build a CES BatchListMetricData request body."""
    return {
        "filter": args.filter,
        "from": from_ms,
        "to": to_ms,
        "period": args.period,
        "metrics": [
            {
                "namespace": args.namespace,
                "metric_name": args.metric_name,
                "dimensions": dimensions,
            }
        ],
    }


def validate_plan_inputs(
    args: argparse.Namespace,
    dimensions: list[dict[str, str]],
    from_ms: int | None,
    to_ms: int | None,
    guidance: dict[str, Any] | None,
    prior_errors: list[str],
) -> tuple[list[str], list[str], dict[str, Any]]:
    """Return validation errors, warnings, and query-bound metadata."""
    errors = list(prior_errors)
    warnings: list[str] = []
    if not args.region:
        errors.append("Missing required field: region.")
    if not args.project_id:
        errors.append("Missing required field: project_id.")
    if not args.namespace:
        errors.append("Missing required field: namespace.")
    if not args.metric_name:
        errors.append("Missing required field: metric_name.")
    if not dimensions:
        errors.append("Missing required field: dimension.")
    if args.filter not in ALLOWED_FILTERS:
        errors.append(f"--filter must be one of: {', '.join(sorted(ALLOWED_FILTERS))}.")
    if args.period not in ALLOWED_PERIODS:
        errors.append(f"--period must be one of: {', '.join(str(item) for item in sorted(ALLOWED_PERIODS))}.")

    span_seconds = max(((to_ms or 0) - (from_ms or 0)) / 1000, 0)
    query_units = span_seconds / args.period if args.period else 0
    query_bounds = {
        "metric_count": 1,
        "span_seconds": span_seconds,
        "period": args.period,
        "query_units": query_units,
        "max_query_units": MAX_BATCH_QUERY_POINTS,
        "within_batch_limit": query_units <= MAX_BATCH_QUERY_POINTS,
        "rule": "metric_count * ((to - from) / 1000) / period must be <= 3000.",
    }
    if query_units > MAX_BATCH_QUERY_POINTS:
        errors.append("CES BatchListMetricData query window is too wide for one metric and period.")

    if guidance:
        warnings.extend(f"metric_guidance: {warning}" for warning in guidance.get("warnings", []))
        min_period = guidance.get("min_period")
        if min_period and args.period < int(min_period):
            warnings.append(f"Requested period {args.period} is below local guidance minimum {min_period}.")
    return errors, warnings, query_bounds


def build_safe_exec_command(args: argparse.Namespace, body: dict[str, Any]) -> list[str]:
    """Return the safe_exec command for CES BatchListMetricData."""
    command = hcloud_common.safe_exec_command_prefix() + [
        "--service",
        "CES",
        "--operation",
        "BatchListMetricData",
        "--arg=--cli-output=json",
        "--expect-json",
    ]
    if args.profile:
        command.append(f"--arg=--cli-profile={args.profile}")
    command.append(f"--arg=--cli-region={args.region}")
    command.append(f"--arg=--project_id={args.project_id}")
    for key, value in body.items():
        command.extend(f"--arg={item}" for item in flatten_cli_args(key, value))
    command.extend(["--timeout", str(args.timeout), "--max-output-chars", str(args.max_output_chars)])
    return command


def safe_exec_status(value: dict[str, Any] | None, completed: subprocess.CompletedProcess[str] | None = None) -> dict[str, Any]:
    """Return safe execution metadata without embedding raw metric datapoints."""
    if not isinstance(value, dict):
        return {
            "success": False,
            "return_code": completed.returncode if completed is not None else None,
        }
    if "success" not in value and any(key in value for key in ("metrics", "metric_datas", "datapoints", "data_points")):
        return {
            "success": True,
            "return_code": 0,
            "duration_seconds": None,
            "service": "CES",
            "operation": "BatchListMetricData",
            "error_type": None,
            "error_details": None,
            "advice": None,
            "stdout_truncated": None,
            "stderr_truncated": None,
        }
    return {
        "success": bool(value.get("success")),
        "return_code": value.get("return_code"),
        "duration_seconds": value.get("duration_seconds"),
        "service": value.get("service"),
        "operation": value.get("operation"),
        "error_type": value.get("error_type"),
        "error_details": value.get("error_details"),
        "advice": value.get("advice"),
        "stdout_truncated": value.get("stdout_truncated"),
        "stderr_truncated": value.get("stderr_truncated"),
    }


def parse_safe_exec_stdout(stdout: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse safe_exec JSON output."""
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "safe_exec output must decode to a JSON object."
    return value, None


def payload_from_safe_exec(value: dict[str, Any]) -> dict[str, Any]:
    """Return the parsed CES payload from a safe_exec result or direct payload."""
    parsed = value.get("parsed_json")
    if isinstance(parsed, dict):
        return parsed
    if any(key in value for key in ("metrics", "metric_datas", "datapoints", "data_points")):
        return value
    return {}


def collect_lists_by_key(value: Any, keys: set[str]) -> list[list[Any]]:
    """Collect list values from a nested JSON-like object by key."""
    found: list[list[Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and isinstance(child, list):
                found.append(child)
            found.extend(collect_lists_by_key(child, keys))
    elif isinstance(value, list):
        for child in value:
            found.extend(collect_lists_by_key(child, keys))
    return found


def interpret_result(value: dict[str, Any], guidance: dict[str, Any] | None) -> dict[str, Any]:
    """Interpret a CES datapoint safe_exec result without returning raw datapoints."""
    status = safe_exec_status(value)
    payload = payload_from_safe_exec(value)
    metric_lists = collect_lists_by_key(payload, {"metrics", "metric_datas"})
    datapoint_lists = collect_lists_by_key(payload, {"datapoints", "data_points"})
    metric_entry_count = sum(len(items) for items in metric_lists)
    datapoint_count = sum(len(items) for items in datapoint_lists)
    non_empty_datapoint_series = sum(1 for items in datapoint_lists if items)

    findings: list[str] = []
    likely_causes: list[str] = []
    next_actions: list[str] = []
    error_blob = json.dumps(status, ensure_ascii=False)

    if not status["success"]:
        state = "live_read_failed"
        if "ces.0014" in error_blob or "Some content in message body is not correct" in error_blob:
            state = "metric_request_invalid"
            likely_causes.append("The namespace, metric name, dimensions, or body shape does not match CES reported metrics.")
        next_actions.append("Inspect safe_exec_status.error_details and re-run ListMetrics for the same region/project.")
    elif datapoint_count > 0:
        state = "datapoints_present"
        findings.append("CES returned one or more datapoints for the requested metric window.")
    elif metric_entry_count > 0 or datapoint_lists:
        state = "empty_datapoints"
        findings.append("CES returned metric entries but no datapoints in the requested window.")
        likely_causes.extend(
            [
                "The time window is too recent or outside retention for this period.",
                "The dimension value does not match the actual CES metric dimension.",
                "The metric exists but has not reported during this period.",
            ]
        )
    else:
        state = "empty_metric_result"
        findings.append("CES did not return metric entries or datapoints for this request.")
        likely_causes.extend(
            [
                "Region, project, namespace, metric name, or dimensions may not match the resource.",
                "ListMetrics evidence is needed before treating this as a resource health signal.",
            ]
        )

    if guidance:
        if guidance.get("agent_required"):
            likely_causes.append("The requested metric namespace requires the host monitoring Agent to be installed and reporting.")
            next_actions.extend(guidance.get("next_actions", []))
        if guidance.get("recommended_namespace") and guidance.get("recommended_namespace") != guidance.get("requested_namespace"):
            likely_causes.append("Local guidance indicates a namespace mismatch for this metric name.")
        if guidance.get("known_error"):
            next_actions.append("Check known_error guidance for this metric before retrying the datapoint query.")

    if state in {"empty_datapoints", "empty_metric_result"}:
        next_actions.extend(
            [
                "Run CES ListMetrics for the same region/project and confirm namespace, metric_name, and dimensions.",
                "Try a wider but bounded historical window or the namespace minimum period.",
                "Check resource state and collection delay before declaring the service healthy or unhealthy.",
            ]
        )

    return {
        "success": status["success"],
        "state": state,
        "safe_exec_status": status,
        "metric_entry_count": metric_entry_count,
        "datapoint_count": datapoint_count,
        "non_empty_datapoint_series": non_empty_datapoint_series,
        "raw_datapoints_returned": False,
        "findings": sorted(set(findings)),
        "likely_causes": sorted(set(likely_causes)),
        "next_actions": sorted(set(next_actions)),
    }


def load_result_json_file(path: str | None) -> tuple[dict[str, Any] | None, str | None]:
    """Load a saved safe_exec JSON result for local interpretation."""
    if not path:
        return None, None
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "Result JSON file must contain an object."
    return value, None


def execute_command(command: list[str], timeout: int) -> tuple[dict[str, Any] | None, str | None, subprocess.CompletedProcess[str]]:
    """Execute a safe_exec command and parse its JSON result."""
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=timeout + 5,
    )
    value, parse_error = parse_safe_exec_stdout(completed.stdout)
    return value, parse_error, completed


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build, optionally execute, and optionally interpret a CES datapoint query plan."""
    dimensions, dimension_errors = parse_dimensions(args.dimension)
    from_ms, to_ms, time_errors = resolve_time_window(args)
    guidance = metric_guidance(args.namespace, args.metric_name, args.period)
    body = build_request_body(args, dimensions, from_ms, to_ms)
    errors, warnings, query_bounds = validate_plan_inputs(
        args,
        dimensions,
        from_ms,
        to_ms,
        guidance,
        dimension_errors + time_errors,
    )
    command = build_safe_exec_command(args, body) if not errors else None
    result_file_value, result_file_error = load_result_json_file(args.result_json_file)
    if result_file_error:
        errors.append(f"Cannot read --result-json-file: {result_file_error}")

    interpretation = interpret_result(result_file_value, guidance) if result_file_value else None
    execution_result = None
    if args.execute and command is not None:
        safe_exec_value, parse_error, completed = execute_command(command, args.timeout)
        if parse_error:
            execution_result = {
                "executed": True,
                "success": False,
                "safe_exec_status": safe_exec_status(None, completed),
                "safe_exec_parse_error": parse_error,
                "interpretation": None,
            }
        else:
            execution_result = {
                "executed": True,
                "success": bool(safe_exec_value and safe_exec_value.get("success")),
                "safe_exec_parse_error": None,
                "interpretation": interpret_result(safe_exec_value or {}, guidance),
            }
            interpretation = execution_result["interpretation"]

    mode = "execute" if args.execute else "analyze" if args.result_json_file else "plan"
    success = not errors and (execution_result is None or bool(execution_result.get("success")))
    return {
        "success": success,
        "mode": mode,
        "planning_only": not args.execute,
        "service": "CES",
        "operation": "BatchListMetricData",
        "request_spec": {
            "method": "POST",
            "path": "/V1.0/{project_id}/batch-query-metric-data",
            "body": hcloud_common.redact_json(body, set()),
            "requires_auth": "hcloud profile, environment, or token handled by KooCLI; credentials are not accepted by this planner.",
        },
        "hcloud_command_plan": {
            "supported": command is not None,
            "service": "CES",
            "operation": "BatchListMetricData",
            "safe_exec_command": command,
            "command_shell": shlex.join(command) if command else None,
            "execution_requires_execute_flag": True,
            "output_boundary": {
                "summarize_by_default": True,
                "raw_datapoints_returned": False,
            },
        },
        "metric_guidance": guidance,
        "query_bounds": query_bounds,
        "validation": {
            "errors": errors,
            "warnings": warnings,
        },
        "execution": {
            "requested": bool(args.execute),
            "executed": bool(execution_result),
            "result": execution_result,
        },
        "result_interpretation": interpretation,
        "next_steps": [
            "Run ListMetrics for the same region/project before trusting namespace, metric_name, or dimensions.",
            "Use BatchListMetricData to distinguish metric absence from empty recent datapoints.",
            "Treat empty datapoints as unknown until Agent state, collection delay, period, and dimension are checked.",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", help="CES cli-region for the datapoint query.")
    parser.add_argument("--project-id", help="Project ID for the CES path parameter.")
    parser.add_argument("--profile", help="Optional hcloud CLI profile.")
    parser.add_argument("--namespace", help="CES metric namespace, for example SYS.ECS or AGT.ECS.")
    parser.add_argument("--metric-name", help="CES metric name, for example cpu_util.")
    parser.add_argument("--dimension", action="append", default=[], help="Metric dimension as name=value. Can be repeated.")
    parser.add_argument("--filter", default="average", help="Statistic filter: average, variance, min, max, or sum.")
    parser.add_argument("--period", type=int, default=300, help="Monitoring period in seconds.")
    parser.add_argument("--from-ms", type=int, help="Start timestamp in Unix epoch milliseconds.")
    parser.add_argument("--to-ms", type=int, help="End timestamp in Unix epoch milliseconds.")
    parser.add_argument("--lookback-minutes", type=int, default=DEFAULT_LOOKBACK_MINUTES, help="Default lookback when --from-ms is omitted.")
    parser.add_argument("--result-json-file", help="Optional saved hcloud_safe_exec.py result JSON to interpret.")
    parser.add_argument("--execute", action="store_true", help="Execute the generated read-only safe_exec command.")
    parser.add_argument("--timeout", type=int, default=120, help="safe_exec timeout in seconds.")
    parser.add_argument("--max-output-chars", type=int, default=20000, help="Maximum stdout/stderr chars retained by safe_exec.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.lookback_minutes < 1:
        parser.error("--lookback-minutes must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.max_output_chars < 1:
        parser.error("--max-output-chars must be greater than 0.")
    return args


def main() -> int:
    """Build, execute, or interpret a CES datapoint query plan."""
    args = parse_args()
    result = build_plan(args)
    hcloud_common.emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
