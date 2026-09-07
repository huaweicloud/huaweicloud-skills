#!/usr/bin/env python3
"""Run an explicitly approved read-only Huawei Cloud BSS query and summarize it."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_billing_readonly
import hcloud_billing_result_summarize
import hcloud_checkpoint
import hcloud_common

CONFIRM_TOKEN = "READ_BILLING_DATA"
MAX_LIVE_LIMIT = 50
READ_ONLY_PREFIXES = ("List", "Show")
MAX_PRIVATE_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_AUTO_PAGES = 20
MAX_AUTO_RECORDS = 1000
MAX_MERGED_PAYLOAD_BYTES = 16 * 1024 * 1024
CHECKPOINT_CONTRACT = "huaweicloud_billing_live_read_checkpoint_v1"
PRICING_OPERATIONS = {"on-demand-pricing", "period-pricing"}


def billing_args(args: argparse.Namespace) -> SimpleNamespace:
    """Return the argument namespace expected by the BSS readonly planner."""
    return SimpleNamespace(
        operation=args.operation,
        entry_point=args.entry_point,
        endpoint_base=args.endpoint_base,
        language=args.language,
        bill_cycle=args.bill_cycle,
        shared_month=args.shared_month,
        begin_time=args.begin_time,
        end_time=args.end_time,
        time_measure_id=args.time_measure_id,
        group_by=args.group_by,
        filter=args.filter,
        cost_type=args.cost_type,
        amount_type=args.amount_type,
        project_id=args.project_id,
        service_type_code=args.service_type_code,
        resource_type=args.resource_type,
        resource_spec=args.resource_spec,
        usage_type=args.usage_type,
        region_code=args.region_code,
        pricing_region=args.pricing_region,
        available_zone=args.available_zone,
        pricing_preset=args.pricing_preset,
        resource_size=args.resource_size,
        size_measure_id=args.size_measure_id,
        usage_value=args.usage_value,
        subscription_num=args.subscription_num,
        inquiry_precision=args.inquiry_precision,
        period_type=args.period_type,
        period_num=args.period_num,
        fee_installment_mode=args.fee_installment_mode,
        resource_id=args.resource_id,
        enterprise_project_id=args.enterprise_project_id,
        charge_mode=args.charge_mode,
        bill_type=args.bill_type,
        method=args.method,
        sub_customer_id=args.sub_customer_id,
        customer_id=args.customer_id,
        order_id=args.order_id,
        balance_type=args.balance_type,
        status=args.status,
        free_resource_id=args.free_resource_id,
        quota_id=args.quota_id,
        include_zero_record=args.include_zero_record,
        statistic_type=args.statistic_type,
        offset=args.offset,
        limit=args.limit,
        query=args.query,
        body_json_file=args.body_json_file,
        body_json_text=args.body_json_text,
    )


def planned_int_field(request_spec: dict[str, Any], field: str, fallback: int) -> int:
    """Return an integer pagination field from the final planned BSS call."""
    for container_name in ("query", "body"):
        container = request_spec.get(container_name)
        if isinstance(container, dict) and container.get(field) not in (None, ""):
            try:
                return int(container[field])
            except (TypeError, ValueError):
                return fallback
    return fallback


def validate_live_read_plan(billing_plan: dict[str, Any], *, fallback_limit: int) -> list[str]:
    """Return blocking errors for a candidate live Billing/BSS read."""
    errors: list[str] = []
    command_plan = billing_plan.get("hcloud_command_plan", {})
    operation = str(command_plan.get("operation") or "")
    defaults = command_plan.get("cli_defaults", {})
    request_spec = billing_plan.get("request_spec", {})
    headers = request_spec.get("headers", {}) if isinstance(request_spec, dict) else {}
    x_language = str(headers.get("X-Language") or "") if isinstance(headers, dict) else ""
    supports_x_language = hcloud_billing_readonly.operation_supports_x_language(operation)
    limit = planned_int_field(request_spec, "limit", fallback_limit)

    if not billing_plan.get("success"):
        errors.append("Billing request plan is invalid; fix validation.errors before live read.")
    if not billing_plan.get("execution_supported") or not command_plan.get("supported"):
        errors.append("Billing request plan is not executable through the reviewed hcloud command plan.")
    if command_plan.get("service") != "BSS":
        errors.append("Only BSS live reads are allowed by this wrapper.")
    if not operation.startswith(READ_ONLY_PREFIXES):
        errors.append(f"Only read-only BSS List*/Show* operations are allowed, got {operation or '<missing>'}.")
    if defaults.get("cli_region") != hcloud_billing_readonly.BSS_CLI_REGION:
        errors.append("BSS live reads must use the reviewed fixed cli-region cn-north-1.")
    if supports_x_language and x_language not in hcloud_billing_readonly.SUPPORTED_X_LANGUAGES:
        errors.append("BSS live reads must pass an official X-Language value: zh_CN or en_US.")
    if not supports_x_language and x_language:
        errors.append(f"BSS operation {operation} does not accept X-Language and must omit that header.")
    pricing_operation = billing_plan.get("operation") in PRICING_OPERATIONS
    if not pricing_operation and limit > MAX_LIVE_LIMIT:
        errors.append(f"Live BSS read limit must be <= {MAX_LIVE_LIMIT}; got {limit}.")
    if not pricing_operation and limit < 1:
        errors.append("Live BSS read limit must be greater than 0.")
    return errors


def safe_exec_command(command_plan: dict[str, Any], args: argparse.Namespace) -> list[str] | None:
    """Return the safe_exec command with runtime bounds attached."""
    command = command_plan.get("safe_exec_command")
    if not isinstance(command, list):
        return None
    return [str(item) for item in command] + [
        "--timeout",
        str(args.timeout),
        "--max-output-chars",
        str(args.max_output_chars),
    ]


def parse_safe_exec_stdout(stdout: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse a safe_exec JSON result from stdout."""
    try:
        value = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(value, dict):
        return None, "safe_exec stdout must decode to a JSON object."
    return value, None


def safe_exec_status(
    value: dict[str, Any] | None,
    completed: subprocess.CompletedProcess[str] | None = None,
) -> dict[str, Any]:
    """Return safe execution metadata without embedding raw BSS payload rows."""
    if not isinstance(value, dict):
        return {
            "success": False,
            "return_code": completed.returncode if completed is not None else None,
        }
    return {
        "success": bool(value.get("success")),
        "return_code": value.get("return_code"),
        "duration_seconds": value.get("duration_seconds"),
        "service": value.get("service"),
        "operation": value.get("operation"),
        "command": value.get("command"),
        "error_type": value.get("error_type"),
        "error_details": value.get("error_details"),
        "advice": value.get("advice"),
        "stdout_truncated": value.get("stdout_truncated"),
        "stderr_truncated": value.get("stderr_truncated"),
    }


def page_args(
    args: argparse.Namespace,
    *,
    offset: int,
    timeout: int | None = None,
) -> SimpleNamespace:
    """Return a copy of live-read arguments for one bounded page."""
    values = dict(vars(args))
    values["offset"] = offset
    if timeout is not None:
        values["timeout"] = timeout
    return SimpleNamespace(**values)


def request_scope_signature(request_spec: dict[str, Any]) -> str:
    """Return a stable request signature excluding pagination fields."""
    query = deepcopy(request_spec.get("query") or {})
    body = deepcopy(request_spec.get("body"))
    if isinstance(query, dict):
        query.pop("offset", None)
        query.pop("limit", None)
    if isinstance(body, dict):
        body.pop("offset", None)
        body.pop("limit", None)
    scope = {
        "method": request_spec.get("method"),
        "path": request_spec.get("path"),
        "headers": request_spec.get("headers"),
        "query": query,
        "body": body,
    }
    return json.dumps(scope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_page_info(payload: Any) -> tuple[str | None, list[Any], int | None, str | None]:
    """Return the sole record field, rows, total count, and validation error."""
    if not isinstance(payload, dict):
        return None, [], None, "billing payload must be a JSON object"
    record_lists = hcloud_billing_result_summarize.iter_record_lists(payload)
    if len(record_lists) != 1:
        return None, [], None, "billing payload must expose exactly one top-level record list"
    record_field, records = record_lists[0]
    total_count = payload.get("total_count")
    if not isinstance(total_count, int) or total_count < 0:
        return record_field, records, None, "billing payload has no valid total_count"
    return record_field, records, total_count, None


def stable_page_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Return cross-page metadata that must remain identical."""
    return {
        "currency": payload.get("currency"),
        "monetary_totals": hcloud_billing_result_summarize.monetary_totals(payload),
    }


def merged_payload(
    payloads: list[dict[str, Any]],
    *,
    record_field: str,
) -> dict[str, Any]:
    """Return one private payload containing all accepted billing rows."""
    merged = deepcopy(payloads[0])
    merged[record_field] = []
    for payload in payloads:
        merged[record_field].extend(deepcopy(payload[record_field]))
    return merged


def billing_checkpoint_scope(
    args: argparse.Namespace,
    initial_plan: dict[str, Any],
) -> dict[str, Any]:
    """Return the billing query scope that must remain stable across resumes."""
    request_spec = initial_plan.get("request_spec", {})
    return {
        "operation": initial_plan.get("operation"),
        "request_scope_signature": request_scope_signature(request_spec),
        "initial_offset": planned_int_field(request_spec, "offset", args.offset),
        "page_limit": planned_int_field(request_spec, "limit", args.limit),
    }


def validate_billing_checkpoint_state(
    state: dict[str, Any],
    *,
    initial_offset: int,
) -> dict[str, Any]:
    """Validate and recompute accepted-page state without trusting stored counters."""
    accepted_payloads = state.get("accepted_payloads")
    page_statuses = state.get("page_statuses")
    if not isinstance(accepted_payloads, list) or not isinstance(page_statuses, list):
        raise hcloud_checkpoint.CheckpointError(
            "CHECKPOINT_INVALID",
            "Billing checkpoint state is missing accepted payloads or page statuses.",
        )
    if len(page_statuses) != len(accepted_payloads):
        raise hcloud_checkpoint.CheckpointError(
            "CHECKPOINT_INVALID",
            "Billing checkpoint page statuses do not match accepted payloads.",
        )
    if any(not isinstance(status, dict) for status in page_statuses):
        raise hcloud_checkpoint.CheckpointError(
            "CHECKPOINT_INVALID",
            "Billing checkpoint contains a non-object page status.",
        )

    record_field: str | None = None
    total_count: int | None = None
    expected_metadata: dict[str, Any] | None = None
    fetched_count = 0
    merged_payload_bytes = 0
    for payload in accepted_payloads:
        if not isinstance(payload, dict):
            raise hcloud_checkpoint.CheckpointError(
                "CHECKPOINT_INVALID",
                "Billing checkpoint contains a non-object payload page.",
            )
        current_field, records, current_total, page_error = payload_page_info(payload)
        if page_error:
            raise hcloud_checkpoint.CheckpointError("CHECKPOINT_INVALID", page_error)
        current_metadata = stable_page_metadata(payload)
        if record_field is None:
            record_field = current_field
            total_count = current_total
            expected_metadata = current_metadata
        elif (
            current_field != record_field
            or current_total != total_count
            or current_metadata != expected_metadata
        ):
            raise hcloud_checkpoint.CheckpointError(
                "CHECKPOINT_INVALID",
                "Billing checkpoint page metadata changed across accepted pages.",
            )
        if (
            total_count is None
            or initial_offset + fetched_count + len(records) > total_count
        ):
            raise hcloud_checkpoint.CheckpointError(
                "CHECKPOINT_INVALID",
                "Billing checkpoint record count exceeds its declared total.",
            )
        payload_bytes = len(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        fetched_count += len(records)
        merged_payload_bytes += payload_bytes
    if fetched_count > MAX_AUTO_RECORDS or merged_payload_bytes > MAX_MERGED_PAYLOAD_BYTES:
        raise hcloud_checkpoint.CheckpointError(
            "CHECKPOINT_INVALID",
            "Billing checkpoint exceeds the supported merged result bounds.",
        )
    return {
        "accepted_payloads": accepted_payloads,
        "page_statuses": page_statuses,
        "record_field": record_field,
        "total_count": total_count,
        "expected_metadata": expected_metadata,
        "fetched_count": fetched_count,
        "merged_payload_bytes": merged_payload_bytes,
        "next_offset": initial_offset + fetched_count,
    }


def load_billing_checkpoint(
    path: Path,
    scope: dict[str, Any],
) -> dict[str, Any]:
    """Load and validate private accepted-page state for one billing query."""
    document = hcloud_checkpoint.load_checkpoint(
        path,
        contract=CHECKPOINT_CONTRACT,
        scope=scope,
    )
    return validate_billing_checkpoint_state(
        document["state"],
        initial_offset=int(scope["initial_offset"]),
    )


def write_billing_checkpoint(
    path: Path | None,
    scope: dict[str, Any],
    *,
    accepted_payloads: list[dict[str, Any]],
    page_statuses: list[dict[str, Any]],
    complete: bool,
) -> dict[str, Any] | None:
    """Persist private accepted billing pages when checkpointing is enabled."""
    if path is None:
        return None
    return hcloud_checkpoint.write_checkpoint(
        path,
        contract=CHECKPOINT_CONTRACT,
        scope=scope,
        state={
            "accepted_payloads": accepted_payloads,
            "page_statuses": page_statuses,
            "complete": complete,
        },
    )


def load_private_billing_payload(path: Path, root: Path) -> Any:
    """Load one bounded 0600 parsed-JSON artifact owned by this execution."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("private parsed billing payload is unavailable")
    resolved_root = root.resolve(strict=True)
    resolved_path = path.resolve(strict=True)
    if resolved_path.parent != resolved_root:
        raise ValueError("private parsed billing payload escaped its execution directory")
    metadata = resolved_path.stat()
    if metadata.st_mode & 0o077:
        raise ValueError("private parsed billing payload permissions are too broad")
    if metadata.st_size > MAX_PRIVATE_PAYLOAD_BYTES:
        raise ValueError("private parsed billing payload is too large")
    value = json.loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(value, (dict, list)):
        raise ValueError("private parsed billing payload must contain JSON data")
    return value


def run_safe_exec_page(
    command: list[str],
    args: argparse.Namespace,
    request_spec: dict[str, Any],
    *,
    pricing: bool = False,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Run one safe-exec page and return its public result and private payload."""
    with tempfile.TemporaryDirectory(prefix="hcloud-billing-read-") as temp_dir:
        artifact_root = Path(temp_dir)
        artifact_root.chmod(0o700)
        parsed_json_path = artifact_root / "parsed-billing-response.json"
        execution_command = [
            *command,
            f"--parsed-json-file={parsed_json_path}",
        ]
        try:
            completed = subprocess.run(
                execution_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=args.timeout + 5,
            )
        except subprocess.TimeoutExpired:
            return (
                {
                    "executed": True,
                    "success": False,
                    "safe_exec_status": {
                        "success": False,
                        "return_code": None,
                        "error_type": "subprocess_timeout",
                    },
                    "safe_exec_parse_error": (
                        f"safe_exec subprocess timed out after {args.timeout + 5} seconds"
                    ),
                    "summary": None,
                },
                None,
            )
        safe_exec_result, parse_error = parse_safe_exec_stdout(completed.stdout)
        if parse_error:
            return (
                {
                    "executed": True,
                    "success": False,
                    "safe_exec_status": safe_exec_status(None, completed),
                    "safe_exec_parse_error": parse_error,
                    "stderr": completed.stderr,
                    "summary": None,
                },
                None,
            )

        summary_input = dict(safe_exec_result)
        private_payload: dict[str, Any] | None = None
        try:
            if parsed_json_path.exists():
                loaded_payload = load_private_billing_payload(
                    parsed_json_path,
                    artifact_root,
                )
                if not isinstance(loaded_payload, dict):
                    raise ValueError("private parsed billing payload must contain a JSON object")
                private_payload = loaded_payload
                summary_input["parsed_json"] = private_payload
            elif summary_input.get("parsed_json") is None and summary_input.get("success"):
                raise ValueError("safe_exec returned no parsed billing payload")
            elif isinstance(summary_input.get("parsed_json"), dict):
                private_payload = summary_input["parsed_json"]
        except (json.JSONDecodeError, OSError, UnicodeError, ValueError) as exc:
            return (
                {
                    "executed": True,
                    "success": False,
                    "safe_exec_status": safe_exec_status(safe_exec_result, completed),
                    "safe_exec_parse_error": str(exc),
                    "summary": None,
                },
                None,
            )

        if pricing:
            summary = hcloud_billing_result_summarize.build_pricing_summary(
                summary_input,
                request_spec=request_spec,
                observed_at=datetime.now(UTC).isoformat(),
            )
        else:
            summary = hcloud_billing_result_summarize.build_summary(
                summary_input,
                offset=planned_int_field(request_spec, "offset", args.offset),
                limit=planned_int_field(request_spec, "limit", args.limit),
                include_redacted_records=args.include_redacted_records,
                request_spec=request_spec,
            )
        return (
            {
                "executed": True,
                "success": bool(safe_exec_result.get("success")) and bool(summary.get("success")),
                "safe_exec_status": safe_exec_status(safe_exec_result, completed),
                "safe_exec_parse_error": None,
                "summary": summary,
            },
            private_payload,
        )


def run_safe_exec(
    command: list[str],
    args: argparse.Namespace,
    request_spec: dict[str, Any],
    *,
    pricing: bool = False,
) -> dict[str, Any]:
    """Run one safe-exec page and discard its private payload after summarizing."""
    result, _ = run_safe_exec_page(
        command,
        args,
        request_spec,
        pricing=pricing,
    )
    return result


def run_paginated_safe_exec(
    args: argparse.Namespace,
    initial_plan: dict[str, Any],
) -> dict[str, Any]:
    """Execute and merge bounded BSS pages without exposing private payload rows."""
    initial_request_spec = initial_plan.get("request_spec", {})
    initial_offset = planned_int_field(initial_request_spec, "offset", args.offset)
    page_limit = planned_int_field(initial_request_spec, "limit", args.limit)
    expected_scope = request_scope_signature(initial_request_spec)
    checkpoint_path = (
        Path(str(getattr(args, "checkpoint_file", ""))).expanduser()
        if getattr(args, "checkpoint_file", None)
        else None
    )
    resume = bool(getattr(args, "resume", False))
    checkpoint_scope = billing_checkpoint_scope(args, initial_plan)
    effective_time_budget = getattr(args, "time_budget", None) or args.timeout
    deadline = time.monotonic() + effective_time_budget

    if resume and checkpoint_path is None:
        error = hcloud_checkpoint.CheckpointError(
            "CHECKPOINT_REQUIRED",
            "--resume requires --checkpoint-file.",
        )
        return {
            "executed": False,
            "success": False,
            "outcome_status": "failed",
            "error_code": error.code,
            "error": str(error),
            "summary": None,
        }
    if resume:
        try:
            restored = load_billing_checkpoint(checkpoint_path, checkpoint_scope)
        except hcloud_checkpoint.CheckpointError as exc:
            return {
                "executed": False,
                "success": False,
                "outcome_status": "failed",
                "error_code": exc.code,
                "error": str(exc),
                "summary": None,
                "checkpoint": {
                    "contract": CHECKPOINT_CONTRACT,
                    "path": str(checkpoint_path.absolute()),
                },
            }
    else:
        restored = {
            "accepted_payloads": [],
            "page_statuses": [],
            "record_field": None,
            "total_count": None,
            "expected_metadata": None,
            "fetched_count": 0,
            "merged_payload_bytes": 0,
            "next_offset": initial_offset,
        }

    accepted_payloads: list[dict[str, Any]] = list(restored["accepted_payloads"])
    accepted_page_statuses: list[dict[str, Any]] = list(restored["page_statuses"])
    reported_page_statuses = list(accepted_page_statuses)
    record_field: str | None = restored["record_field"]
    total_count: int | None = restored["total_count"]
    expected_metadata: dict[str, Any] | None = restored["expected_metadata"]
    fetched_count = int(restored["fetched_count"])
    merged_payload_bytes = int(restored["merged_payload_bytes"])
    next_offset = int(restored["next_offset"])
    reused_page_count = len(accepted_payloads)
    attempted_this_run = 0
    stop_reason = "page_execution_failed"
    last_parse_error: str | None = None
    checkpoint_artifact: dict[str, Any] | None = None

    try:
        checkpoint_artifact = write_billing_checkpoint(
            checkpoint_path,
            checkpoint_scope,
            accepted_payloads=accepted_payloads,
            page_statuses=accepted_page_statuses,
            complete=(
                initial_offset == 0
                and total_count is not None
                and fetched_count == total_count
            ),
        )
    except OSError as exc:
        return {
            "executed": False,
            "success": False,
            "outcome_status": "failed",
            "error_code": "CHECKPOINT_WRITE_FAILED",
            "error": str(exc),
            "summary": None,
        }

    if initial_offset == 0 and total_count is not None and fetched_count == total_count:
        stop_reason = "all_records_fetched"

    while stop_reason != "all_records_fetched" and len(accepted_payloads) < MAX_AUTO_PAGES:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            stop_reason = "time_budget_reached"
            break
        per_page_timeout = max(1, min(args.timeout, int(remaining_seconds)))
        current_args = page_args(
            args,
            offset=next_offset,
            timeout=per_page_timeout,
        )
        page_plan = (
            initial_plan
            if not accepted_payloads and attempted_this_run == 0 and next_offset == initial_offset
            else hcloud_billing_readonly.build_request_spec(billing_args(current_args))
        )
        guard_errors = validate_live_read_plan(page_plan, fallback_limit=page_limit)
        request_spec = page_plan.get("request_spec", {})
        command = safe_exec_command(page_plan.get("hcloud_command_plan", {}), current_args)
        if guard_errors or command is None:
            stop_reason = "page_plan_invalid"
            break
        if request_scope_signature(request_spec) != expected_scope:
            stop_reason = "page_request_scope_changed"
            break

        page_result, payload = run_safe_exec_page(command, current_args, request_spec)
        attempted_this_run += 1
        page_status = dict(page_result.get("safe_exec_status") or {})
        page_status["offset"] = next_offset
        reported_page_statuses.append(page_status)
        last_parse_error = page_result.get("safe_exec_parse_error")
        if not page_result.get("success") or payload is None:
            stop_reason = "page_execution_failed"
            break

        current_field, records, current_total, page_error = payload_page_info(payload)
        if page_error:
            stop_reason = "page_contract_invalid"
            break
        if record_field is None:
            record_field = current_field
            total_count = current_total
            expected_metadata = stable_page_metadata(payload)
        elif current_field != record_field or current_total != total_count or stable_page_metadata(payload) != expected_metadata:
            stop_reason = "page_metadata_changed"
            break

        remaining_records = total_count - next_offset
        if len(records) > remaining_records:
            stop_reason = "page_record_count_exceeds_remaining"
            break

        payload_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        if merged_payload_bytes + payload_bytes > MAX_MERGED_PAYLOAD_BYTES:
            stop_reason = "merged_payload_limit_reached"
            break
        if fetched_count + len(records) > MAX_AUTO_RECORDS:
            stop_reason = "max_records_reached"
            break

        accepted_payloads.append(payload)
        accepted_page_statuses.append(page_status)
        merged_payload_bytes += payload_bytes
        fetched_count += len(records)
        next_offset = initial_offset + fetched_count

        if total_count == 0 or next_offset == total_count:
            stop_reason = "all_records_fetched" if initial_offset == 0 else "started_from_nonzero_offset"
            break
        if not records:
            stop_reason = "empty_page_before_total_count"
            break
        try:
            checkpoint_artifact = write_billing_checkpoint(
                checkpoint_path,
                checkpoint_scope,
                accepted_payloads=accepted_payloads,
                page_statuses=accepted_page_statuses,
                complete=(
                    initial_offset == 0
                    and total_count is not None
                    and fetched_count == total_count
                ),
            )
        except OSError as exc:
            last_parse_error = str(exc)
            stop_reason = "checkpoint_write_failed"
            break
        if len(accepted_payloads) >= MAX_AUTO_PAGES:
            stop_reason = "max_pages_reached"
            break

    complete = stop_reason == "all_records_fetched" and initial_offset == 0 and total_count is not None and fetched_count == total_count
    try:
        checkpoint_artifact = write_billing_checkpoint(
            checkpoint_path,
            checkpoint_scope,
            accepted_payloads=accepted_payloads,
            page_statuses=accepted_page_statuses,
            complete=complete,
        )
    except OSError as exc:
        last_parse_error = str(exc)
        if not complete:
            stop_reason = "checkpoint_write_failed"
    summary: dict[str, Any] | None = None
    if accepted_payloads and record_field is not None:
        private_merged_payload = merged_payload(
            accepted_payloads,
            record_field=record_field,
        )
        operation = next(
            (
                status.get("operation")
                for status in reported_page_statuses
                if status.get("operation")
            ),
            initial_plan.get("title"),
        )
        summary = hcloud_billing_result_summarize.build_summary(
            {
                "service": "BSS",
                "operation": operation,
                "parsed_json": private_merged_payload,
            },
            offset=initial_offset,
            limit=page_limit,
            include_redacted_records=args.include_redacted_records,
            request_spec=initial_request_spec,
        )
        summary["pagination"].update(
            {
                "auto_paginated": True,
                "page_count": len(accepted_payloads),
                "attempted_page_count": len(reported_page_statuses),
                "record_count": fetched_count,
                "total_count": total_count,
                "complete": complete,
                "next_offset": None if complete else next_offset,
                "stop_reason": stop_reason,
                "complete_result_claim_allowed": complete,
                "resumed": resume,
                "reused_page_count": reused_page_count,
                "time_budget_seconds": effective_time_budget,
            }
        )
        if not complete:
            summary["summary"].pop("verified_monetary_totals", None)

    outcome_status = "succeeded" if complete else "partially_succeeded" if accepted_payloads else "failed"
    return {
        "executed": attempted_this_run > 0,
        "success": complete,
        "outcome_status": outcome_status,
        "safe_exec_status": reported_page_statuses[-1] if reported_page_statuses else None,
        "safe_exec_statuses": reported_page_statuses,
        "safe_exec_parse_error": last_parse_error,
        "summary": summary,
        "pagination_stop_reason": stop_reason,
        "checkpoint": {
            "contract": CHECKPOINT_CONTRACT,
            "enabled": checkpoint_path is not None,
            "path": str(checkpoint_path.absolute()) if checkpoint_path else None,
            "artifact": checkpoint_artifact,
        },
    }


def build_live_read(args: argparse.Namespace) -> dict[str, Any]:
    """Build or execute a guarded read-only Billing/BSS live-read workflow."""
    plan = hcloud_billing_readonly.build_request_spec(billing_args(args))
    guard_errors = validate_live_read_plan(plan, fallback_limit=args.limit)
    command_plan = plan.get("hcloud_command_plan", {})
    command = safe_exec_command(command_plan, args)
    approval_ok = args.confirm_live_billing_read == CONFIRM_TOKEN
    pricing_operation = plan.get("operation") in PRICING_OPERATIONS
    if pricing_operation and (
        getattr(args, "checkpoint_file", None) or getattr(args, "resume", False)
    ):
        guard_errors.append(
            "Pricing inquiries are one non-paginated request and do not support checkpoint or resume."
        )

    result: dict[str, Any] = {
        "success": not guard_errors and not args.execute,
        "mode": "execute" if args.execute else "plan",
        "planning_only": not args.execute,
        "operation": plan.get("operation"),
        "title": plan.get("title"),
        "billing_request_plan": plan,
        "live_read_plan": {
            "supported": not guard_errors and command is not None,
            "guard_errors": guard_errors,
            "safe_exec_command": command,
            "max_live_limit": MAX_LIVE_LIMIT,
            "confirmation": {
                "required": True,
                "token": CONFIRM_TOKEN,
                "accepted": approval_ok,
            },
            "output_boundary": {
                "default_output": "redacted_summary_only",
                "raw_safe_exec_result_returned": False,
                "full_payload_transport": "execution_local_0600_artifact",
            },
            "pagination": {
                "mode": "not_applicable" if pricing_operation else "automatic",
                "page_size": planned_int_field(
                    plan.get("request_spec", {}),
                    "limit",
                    args.limit,
                ) if not pricing_operation else None,
                "max_pages": None if pricing_operation else MAX_AUTO_PAGES,
                "max_records": None if pricing_operation else MAX_AUTO_RECORDS,
                "total_timeout_seconds": args.timeout
                if pricing_operation
                else getattr(args, "time_budget", None) or args.timeout,
                "checkpoint_contract": None
                if pricing_operation
                else CHECKPOINT_CONTRACT,
            },
        },
        "execution": {
            "requested": bool(args.execute),
            "executed": False,
            "result": None,
        },
    }
    result["outcome_status" if args.execute else "planning_status"] = (
        "succeeded" if result["success"] else "failed"
    )

    if not args.execute:
        return result
    if guard_errors:
        result["success"] = False
        return result
    if command is None:
        result["success"] = False
        result["live_read_plan"]["guard_errors"].append("No safe_exec command was generated.")
        return result
    if not approval_ok:
        result["success"] = False
        result["live_read_plan"]["guard_errors"].append(f"Live billing read requires --confirm-live-billing-read {CONFIRM_TOKEN}.")
        return result

    if pricing_operation:
        execution_result = run_safe_exec(
            command,
            args,
            plan.get("request_spec", {}),
            pricing=True,
        )
        execution_result["outcome_status"] = (
            "succeeded" if execution_result.get("success") else "failed"
        )
    else:
        execution_result = run_paginated_safe_exec(args, plan)
    result["execution"] = {
        "requested": True,
        "executed": bool(execution_result.get("executed")),
        "result": execution_result,
    }
    result["outcome_status"] = str(execution_result.get("outcome_status") or "failed")
    result["success"] = result["outcome_status"] == "succeeded"
    if execution_result.get("error_code"):
        result["error_code"] = execution_result["error_code"]
        result["error"] = execution_result.get("error")
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--operation",
        choices=sorted(list(hcloud_billing_readonly.OPERATIONS) + list(hcloud_billing_readonly.OPERATION_ALIASES)),
    )
    parser.add_argument("--entry-point", choices=hcloud_billing_readonly.semantic_entry_point_names())
    parser.add_argument("--endpoint-base", default=hcloud_billing_readonly.DEFAULT_ENDPOINT_BASE)
    parser.add_argument("--language", default="zh_CN")
    parser.add_argument("--bill-cycle")
    parser.add_argument("--shared-month")
    parser.add_argument("--begin-time")
    parser.add_argument("--end-time")
    parser.add_argument("--time-measure-id", type=int, default=1, choices=[1, 2])
    parser.add_argument("--group-by", action="append", default=None)
    parser.add_argument("--filter", action="append", default=[])
    parser.add_argument("--cost-type", default="ORIGINAL_COST", choices=["ORIGINAL_COST", "AMORTIZED_COST"])
    parser.add_argument("--amount-type", default="PAYMENT_AMOUNT", choices=["PAYMENT_AMOUNT", "NET_AMOUNT"])
    parser.add_argument("--project-id")
    parser.add_argument("--service-type-code")
    parser.add_argument("--resource-type")
    parser.add_argument("--resource-spec", action="append")
    parser.add_argument("--usage-type")
    parser.add_argument("--region-code")
    parser.add_argument("--pricing-region")
    parser.add_argument("--available-zone")
    parser.add_argument("--pricing-preset")
    parser.add_argument("--resource-size", type=int, action="append")
    parser.add_argument("--size-measure-id", type=int, action="append")
    parser.add_argument("--usage-value", type=float, action="append")
    parser.add_argument("--subscription-num", type=int, action="append")
    parser.add_argument("--inquiry-precision", type=int, default=1, choices=[0, 1])
    parser.add_argument("--period-type", action="append")
    parser.add_argument("--period-num", type=int, action="append")
    parser.add_argument("--fee-installment-mode", choices=["HALF_PAY", "ZERO_PAY", "NA"])
    parser.add_argument("--resource-id")
    parser.add_argument("--enterprise-project-id")
    parser.add_argument("--charge-mode")
    parser.add_argument("--bill-type", type=int)
    parser.add_argument("--method")
    parser.add_argument("--sub-customer-id")
    parser.add_argument("--customer-id")
    parser.add_argument("--order-id")
    parser.add_argument("--balance-type")
    parser.add_argument("--status")
    parser.add_argument("--free-resource-id")
    parser.add_argument("--quota-id")
    parser.add_argument("--include-zero-record")
    parser.add_argument("--statistic-type", type=int)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--body-json-file")
    parser.add_argument("--body-json-text")
    parser.add_argument("--execute", action="store_true", help="Execute the reviewed BSS safe_exec command.")
    parser.add_argument("--confirm-live-billing-read", help=f"Must equal {CONFIRM_TOKEN} when --execute is used.")
    parser.add_argument("--include-redacted-records", action="store_true", help="Include redacted BSS records in the summary.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--time-budget",
        type=int,
        help="Total seconds available for this run; --timeout remains the per-page bound.",
    )
    parser.add_argument("--max-output-chars", type=int, default=20000)
    parser.add_argument("--checkpoint-file", help="Private accepted-page state for interrupted execute-mode reads.")
    parser.add_argument("--resume", action="store_true", help="Resume accepted pages from --checkpoint-file.")
    parser.add_argument("--output-file", help="Write the complete JSON result to this file and emit a compact receipt.")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if args.operation is None and args.entry_point:
        route = hcloud_billing_readonly.build_semantic_route(args.entry_point)
        supported = route.get("supported_planner_operations", []) if route else []
        args.operation = supported[0] if supported else "monthly-sum"
    args.operation = hcloud_billing_readonly.operation_name(args.operation or "monthly-sum")
    args.group_by = args.group_by or ["CLOUD_SERVICE_TYPE"]
    if args.offset < 0:
        parser.error("--offset must be greater than or equal to 0.")
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.time_budget is not None and args.time_budget < 1:
        parser.error("--time-budget must be greater than 0.")
    if args.time_budget is not None and not args.execute:
        parser.error("--time-budget requires --execute.")
    if args.max_output_chars < 1:
        parser.error("--max-output-chars must be greater than 0.")
    if args.resume and not args.execute:
        parser.error("--resume requires --execute.")
    if args.resume and not args.checkpoint_file:
        parser.error("--resume requires --checkpoint-file.")
    if args.checkpoint_file and not args.execute:
        parser.error("--checkpoint-file requires --execute.")
    return args


def billing_receipt_summary(result: dict[str, Any]) -> dict[str, Any] | None:
    """Return bounded billing summary fields suitable for stdout."""
    execution = result.get("execution")
    execution_result = execution.get("result") if isinstance(execution, dict) else None
    summary = execution_result.get("summary") if isinstance(execution_result, dict) else None
    if not isinstance(summary, dict):
        return None
    pagination = summary.get("pagination")
    pricing_quote = summary.get("pricing_quote")
    if isinstance(pricing_quote, dict):
        return {
            "pagination": pagination,
            "pricing_quote": pricing_quote,
        }
    public_summary = summary.get("summary")
    if isinstance(public_summary, dict):
        public_summary = {
            key: value
            for key, value in public_summary.items()
            if key not in {"records", "redacted_records"}
        }
    return {
        "pagination": pagination,
        "summary": public_summary,
    }


def billing_receipt_checkpoint(result: dict[str, Any]) -> dict[str, Any] | None:
    """Return bounded checkpoint metadata without private accepted pages."""
    execution = result.get("execution")
    execution_result = execution.get("result") if isinstance(execution, dict) else None
    checkpoint = execution_result.get("checkpoint") if isinstance(execution_result, dict) else None
    return checkpoint if isinstance(checkpoint, dict) else None


def emit_cli_result(
    result: dict[str, Any],
    *,
    output_file: str | None,
    pretty: bool,
) -> None:
    """Emit the full result or persist it and emit a compact file receipt."""
    hcloud_common.emit_public_result(
        result,
        output_file=Path(output_file) if output_file else None,
        pretty=pretty,
        receipt_fields=("planning_status",),
        receipt_extra={
            "summary": billing_receipt_summary(result),
            "checkpoint": billing_receipt_checkpoint(result),
        },
    )


def main() -> int:
    """Build or execute the guarded BSS live-read workflow."""
    args = parse_args()
    result = build_live_read(args)
    emit_cli_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
