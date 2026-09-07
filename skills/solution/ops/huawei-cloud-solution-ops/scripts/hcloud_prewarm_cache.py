#!/usr/bin/env python3
"""Prewarm local hcloud metadata and help cache for priority Huawei Cloud services."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from hcloud_common import (
    coerce_output_text,
    collect_known_secrets,
    emit_json,
    redact_command,
    redact_text,
)
from hcloud_context_inspect import build_summary
from hcloud_safe_exec import (
    classify_error,
    trim_text,
)

DEFAULT_SERVICES = ("ECS", "IAM", "VPC", "IMS", "KPS")
CHECKPOINT_VERSION = 1
DEFAULT_PRIORITY_OPERATIONS = {
    "ECS": [
        "ListServersDetails",
        "ListCloudServers",
        "ShowServer",
        "ListFlavors",
        "ListFlavorSellPolicies",
        "ListServerAzInfo",
        "CreateServers",
        "CreatePostPaidServers",
        "ShowJob",
    ],
    "IAM": [],
    "VPC": [],
    "IMS": [],
    "KPS": [],
}


def emit_progress(enabled: bool, message: str) -> None:
    """Print a progress message to stderr when progress output is enabled."""
    if not enabled:
        return
    print(f"[hcloud-prewarm] {message}", file=sys.stderr, flush=True)


def summarize_step_result(result: dict[str, Any]) -> str:
    """Return a compact status label for a command result."""
    if result["success"]:
        return "ok"
    if result.get("error_type"):
        return str(result["error_type"]).lower()
    if result.get("return_code") is None:
        return "failed"
    return f"failed(rc={result['return_code']})"


def derive_checkpoint_path(args: argparse.Namespace) -> Path:
    """Return the checkpoint file path for the current run."""
    if args.checkpoint_file:
        return Path(args.checkpoint_file)
    if args.summary_file:
        summary_path = Path(args.summary_file)
        if summary_path.suffix:
            return summary_path.with_suffix(".checkpoint.json")
        return summary_path.with_name(f"{summary_path.name}.checkpoint.json")
    return Path(".hcloud-prewarm-checkpoint.json")


def build_run_config(
    args: argparse.Namespace,
    services: list[str],
    operations_by_service: dict[str, list[str]],
) -> dict[str, Any]:
    """Build the semantic run configuration used for checkpoint compatibility."""
    return {
        "services": services,
        "skip_meta_download": args.skip_meta_download,
        "profile": args.profile,
        "region": args.region,
        "discovered_operations": args.discovered_operations,
        "max_discovered_operations": args.max_discovered_operations,
        "skip_priority_operations": args.skip_priority_operations,
        "explicit_operations": operations_by_service,
    }


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Atomically write JSON data to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def load_checkpoint(path: Path, run_config: dict[str, Any], show_progress: bool) -> dict[str, Any] | None:
    """Load a compatible checkpoint when available."""
    if not path.exists():
        return None

    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        emit_progress(show_progress, f"ignore invalid checkpoint {path}")
        return None

    if checkpoint.get("checkpoint_version") != CHECKPOINT_VERSION:
        emit_progress(show_progress, f"ignore incompatible checkpoint version from {path}")
        return None
    if checkpoint.get("run_config") != run_config:
        emit_progress(show_progress, f"ignore mismatched checkpoint config from {path}")
        return None

    emit_progress(show_progress, f"resume from checkpoint {path}")
    return checkpoint


def create_empty_checkpoint(run_config: dict[str, Any]) -> dict[str, Any]:
    """Create an empty checkpoint payload."""
    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "run_config": run_config,
        "context_before": None,
        "meta_download": None,
        "services": {},
    }


def save_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    """Persist the checkpoint to disk."""
    write_json_atomic(path, checkpoint)


def build_service_result_from_checkpoint(
    service_name: str,
    service_state: dict[str, Any],
    discovery_sample_size: int,
) -> dict[str, Any]:
    """Build a stable service result from checkpointed state."""
    discovered_operations = service_state.get("discovered_operations", [])
    target_operations = service_state.get("target_operations", [])
    operation_help_by_name = service_state.get("operation_help_by_name", {})
    operations = [
        {
            "name": operation_name,
            "help": operation_help_by_name[operation_name],
        }
        for operation_name in target_operations
        if operation_name in operation_help_by_name
    ]
    service_help_result = dict(service_state["service_help"])
    service_help_result["discovered_operations_count"] = len(discovered_operations)
    service_help_result["discovered_operations_sample"] = discovered_operations[:discovery_sample_size]
    return {
        "service": service_name,
        "service_help": service_help_result,
        "target_operations": target_operations,
        "operations": operations,
        "summary": {
            "target_operation_count": len(target_operations),
            "operation_help_success_count": sum(
                1 for operation in operations if operation["help"]["success"]
            ),
            "operation_help_failure_count": sum(
                1 for operation in operations if not operation["help"]["success"]
            ),
        },
    }


def normalize_token(value: str) -> str:
    """Return a lowercase alphanumeric-only token for loose matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def dedupe_preserve_order(items: list[str]) -> list[str]:
    """Deduplicate values while keeping the first occurrence order."""
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        token = normalize_token(item)
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(item)
    return result


def parse_operation_specs(specs: list[str]) -> dict[str, list[str]]:
    """Parse repeated SERVICE:OPERATION strings into a per-service mapping."""
    operations_by_service: dict[str, list[str]] = {}
    for spec in specs:
        if ":" not in spec:
            raise ValueError(
                f"Invalid --operation value '{spec}'. Use the SERVICE:OPERATION format."
            )
        service, operation = spec.split(":", 1)
        service_name = service.strip()
        operation_name = operation.strip()
        if not service_name or not operation_name:
            raise ValueError(
                f"Invalid --operation value '{spec}'. Both service and operation are required."
            )
        service_token = normalize_token(service_name)
        operations_by_service.setdefault(service_token, []).append(operation_name)
    return {
        service_token: dedupe_preserve_order(operation_names)
        for service_token, operation_names in operations_by_service.items()
    }


def build_service_list(args: argparse.Namespace) -> list[str]:
    """Build the final ordered service list."""
    configured = args.service or list(DEFAULT_SERVICES)
    services = dedupe_preserve_order(configured)
    known_tokens = {normalize_token(service) for service in services}

    for raw_spec in args.operation:
        service_name = raw_spec.split(":", 1)[0].strip()
        service_token = normalize_token(service_name)
        if service_token not in known_tokens:
            services.append(service_name)
            known_tokens.add(service_token)

    return services


def build_common_hcloud_args(args: argparse.Namespace) -> list[str]:
    """Build common hcloud arguments shared across commands."""
    common_args: list[str] = []
    if args.profile:
        common_args.append(f"--cli-profile={args.profile}")
    if args.region:
        common_args.append(f"--cli-region={args.region}")
    if args.hcloud_connect_timeout is not None:
        common_args.append(f"--cli-connect-timeout={args.hcloud_connect_timeout}")
    if args.hcloud_read_timeout is not None:
        common_args.append(f"--cli-read-timeout={args.hcloud_read_timeout}")
    return common_args


def parse_available_operations(stdout: str) -> list[str]:
    """Parse operation names from a service-level `hcloud <service> --help` output."""
    operations: list[str] = []
    capture = False
    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        if line.strip() == "Available Operations:":
            capture = True
            continue
        if not capture:
            continue
        if not line.strip():
            continue
        if line.startswith("Run `hcloud "):
            break
        if line.startswith("  "):
            operations.append(line.strip())
            continue
        break
    return operations


def run_hcloud_command(
    command: list[str],
    timeout: int,
    known_secrets: set[str],
    max_output_chars: int,
    show_progress: bool,
    progress_label: str,
) -> tuple[dict[str, Any], str]:
    """Run an hcloud command and return a structured result plus raw stdout."""
    started_at = time.time()
    emit_progress(show_progress, f"start {progress_label}")
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        raw_stdout = completed.stdout
        raw_stderr = completed.stderr
        error_type = classify_error(raw_stdout, raw_stderr)
        redacted_stdout = redact_text(raw_stdout, known_secrets)
        redacted_stderr = redact_text(raw_stderr, known_secrets)
        stdout_trimmed, stdout_truncated = trim_text(redacted_stdout, max_output_chars)
        stderr_trimmed, stderr_truncated = trim_text(redacted_stderr, max_output_chars)
        result = {
            "success": completed.returncode == 0 and error_type is None,
            "return_code": completed.returncode,
            "duration_seconds": round(time.time() - started_at, 3),
            "command": redact_command(command, known_secrets),
            "stdout": stdout_trimmed,
            "stderr": stderr_trimmed,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "error_type": error_type,
        }
        emit_progress(
            show_progress,
            f"done  {progress_label} -> {summarize_step_result(result)} in {result['duration_seconds']}s",
        )
        return result, raw_stdout
    except subprocess.TimeoutExpired as exc:
        stdout_text = coerce_output_text(exc.stdout)
        stderr_text = coerce_output_text(exc.stderr)
        result = {
            "success": False,
            "return_code": None,
            "duration_seconds": round(time.time() - started_at, 3),
            "command": redact_command(command, known_secrets),
            "stdout": redact_text(stdout_text, known_secrets),
            "stderr": redact_text(stderr_text, known_secrets),
            "stdout_truncated": False,
            "stderr_truncated": False,
            "error_type": "TIMEOUT",
        }
        emit_progress(
            show_progress,
            f"done  {progress_label} -> {summarize_step_result(result)} in {result['duration_seconds']}s",
        )
        return result, stdout_text


def select_operations(
    service_name: str,
    discovered_operations: list[str],
    operations_by_service: dict[str, list[str]],
    args: argparse.Namespace,
) -> list[str]:
    """Select priority, explicit, and discovered operations for a service."""
    service_token = normalize_token(service_name)
    operations: list[str] = []
    if not args.skip_priority_operations:
        operations.extend(DEFAULT_PRIORITY_OPERATIONS.get(service_name.upper(), []))
    operations.extend(operations_by_service.get(service_token, []))
    known_operations = {normalize_token(operation_name) for operation_name in operations}

    if args.discovered_operations == "sample":
        selected_count = 0
        for operation_name in discovered_operations:
            if normalize_token(operation_name) in known_operations:
                continue
            operations.append(operation_name)
            known_operations.add(normalize_token(operation_name))
            selected_count += 1
            if selected_count >= args.max_discovered_operations:
                break
    elif args.discovered_operations == "all":
        operations.extend(discovered_operations)

    return dedupe_preserve_order(operations)


def warm_service(
    service_name: str,
    service_index: int,
    service_total: int,
    binary: str,
    common_args: list[str],
    args: argparse.Namespace,
    known_secrets: set[str],
    operations_by_service: dict[str, list[str]],
    checkpoint: dict[str, Any],
    checkpoint_path: Path,
) -> dict[str, Any]:
    """Warm a single service and its selected operations."""
    service_state = checkpoint.setdefault("services", {}).setdefault(service_name, {})

    if (
        service_state.get("service_help") is not None
        and service_state.get("discovered_operations") is not None
        and service_state.get("target_operations") is not None
    ):
        emit_progress(
            not args.no_progress,
            f"step 3/4 service {service_index}/{service_total}: reuse {service_name} from checkpoint",
        )
    else:
        emit_progress(
            not args.no_progress,
            f"step 3/4 service {service_index}/{service_total}: discover {service_name}",
        )
        service_command = [binary, service_name] + common_args + ["--help"]
        service_help_result, raw_stdout = run_hcloud_command(
            service_command,
            timeout=args.command_timeout,
            known_secrets=known_secrets,
            max_output_chars=args.max_output_chars,
            show_progress=not args.no_progress,
            progress_label=f"service help {service_name}",
        )
        discovered_operations = parse_available_operations(raw_stdout)
        target_operations = select_operations(
            service_name=service_name,
            discovered_operations=discovered_operations,
            operations_by_service=operations_by_service,
            args=args,
        )
        service_state["service_help"] = service_help_result
        service_state["discovered_operations"] = discovered_operations
        service_state["target_operations"] = target_operations
        service_state.setdefault("operation_help_by_name", {})
        save_checkpoint(checkpoint_path, checkpoint)

    discovered_operations = service_state.get("discovered_operations", [])
    target_operations = service_state.get("target_operations", [])
    operation_help_by_name = service_state.setdefault("operation_help_by_name", {})

    emit_progress(
        not args.no_progress,
        (
            f"step 3/4 service {service_index}/{service_total}: "
            f"{service_name} selected {len(target_operations)} operations"
        ),
    )

    for operation_index, operation_name in enumerate(target_operations, start=1):
        if operation_name in operation_help_by_name:
            emit_progress(
                not args.no_progress,
                (
                    f"step 3/4 service {service_index}/{service_total}: "
                    f"reuse operation {operation_index}/{len(target_operations)} "
                    f"{service_name}.{operation_name} from checkpoint"
                ),
            )
            continue

        emit_progress(
            not args.no_progress,
            (
                f"step 3/4 service {service_index}/{service_total}: "
                f"operation {operation_index}/{len(target_operations)} {service_name}.{operation_name}"
            ),
        )
        operation_command = [binary, service_name, operation_name] + common_args + ["--help"]
        operation_help_result, _ = run_hcloud_command(
            operation_command,
            timeout=args.command_timeout,
            known_secrets=known_secrets,
            max_output_chars=args.max_output_chars,
            show_progress=not args.no_progress,
            progress_label=f"operation help {service_name}.{operation_name}",
        )
        operation_help_by_name[operation_name] = operation_help_result
        save_checkpoint(checkpoint_path, checkpoint)

    return build_service_result_from_checkpoint(
        service_name=service_name,
        service_state=service_state,
        discovery_sample_size=args.discovery_sample_size,
    )


def build_overall_summary(
    services_result: list[dict[str, Any]],
    meta_download_result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build top-level counts for the full prewarm run."""
    service_help_success_count = sum(
        1 for service in services_result if service["service_help"]["success"]
    )
    operation_attempt_count = sum(
        len(service["operations"]) for service in services_result
    )
    operation_success_count = sum(
        service["summary"]["operation_help_success_count"] for service in services_result
    )
    operation_failure_count = sum(
        service["summary"]["operation_help_failure_count"] for service in services_result
    )
    return {
        "meta_download_attempted": meta_download_result is not None,
        "meta_download_success": meta_download_result["success"] if meta_download_result else None,
        "service_count": len(services_result),
        "service_help_success_count": service_help_success_count,
        "service_help_failure_count": len(services_result) - service_help_success_count,
        "operation_attempt_count": operation_attempt_count,
        "operation_help_success_count": operation_success_count,
        "operation_help_failure_count": operation_failure_count,
    }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--service",
        action="append",
        default=[],
        help="Target service to prewarm. Repeatable. Defaults to ECS/IAM/VPC/IMS/KPS.",
    )
    parser.add_argument(
        "--operation",
        action="append",
        default=[],
        help="Explicit operation to prewarm in SERVICE:OPERATION form. Repeatable.",
    )
    parser.add_argument(
        "--skip-priority-operations",
        action="store_true",
        help="Do not include the built-in priority operation set.",
    )
    parser.add_argument(
        "--discovered-operations",
        choices=("none", "sample", "all"),
        default="sample",
        help="How to use operations discovered from `hcloud <service> --help`.",
    )
    parser.add_argument(
        "--max-discovered-operations",
        type=int,
        default=12,
        help="When discovered-operations=sample, prewarm at most this many discovered operations per service.",
    )
    parser.add_argument(
        "--discovery-sample-size",
        type=int,
        default=20,
        help="How many discovered operation names to keep in the JSON summary sample.",
    )
    parser.add_argument(
        "--skip-meta-download",
        action="store_true",
        help="Skip `hcloud meta download` and only warm service/operation help.",
    )
    parser.add_argument(
        "--profile",
        help="Optional cli-profile passed to hcloud commands.",
    )
    parser.add_argument(
        "--region",
        help="Optional cli-region passed to hcloud help commands.",
    )
    parser.add_argument(
        "--hcloud-connect-timeout",
        type=int,
        help="Optional cli-connect-timeout passed to hcloud commands.",
    )
    parser.add_argument(
        "--hcloud-read-timeout",
        type=int,
        help="Optional cli-read-timeout passed to hcloud commands.",
    )
    parser.add_argument(
        "--command-timeout",
        type=int,
        default=120,
        help="Python subprocess timeout in seconds for each hcloud command.",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=12000,
        help="Maximum number of chars preserved for stdout and stderr in the summary.",
    )
    parser.add_argument(
        "--summary-file",
        help="Optional path to save the full prewarm summary JSON.",
    )
    parser.add_argument(
        "--checkpoint-file",
        help="Optional checkpoint path used for resume after interruption.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore any existing checkpoint and start from scratch.",
    )
    parser.add_argument(
        "--keep-checkpoint",
        action="store_true",
        help="Keep the checkpoint file even after a successful run.",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Do not print live progress messages to stderr.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON result.",
    )
    args = parser.parse_args()
    if args.max_discovered_operations < 0:
        parser.error("--max-discovered-operations must be >= 0.")
    if args.discovery_sample_size < 0:
        parser.error("--discovery-sample-size must be >= 0.")
    return args


def main() -> int:
    """Run the cache prewarm workflow and print a structured summary."""
    args = parse_args()
    binary = shutil.which("hcloud")
    if not binary:
        raise SystemExit("hcloud binary not found in PATH.")

    operations_by_service = parse_operation_specs(args.operation)
    services = build_service_list(args)
    common_args = build_common_hcloud_args(args)
    known_secrets = collect_known_secrets()
    checkpoint_path = derive_checkpoint_path(args)
    run_config = build_run_config(args, services, operations_by_service)

    started_at = time.time()
    checkpoint = None if args.no_resume else load_checkpoint(
        checkpoint_path,
        run_config=run_config,
        show_progress=not args.no_progress,
    )
    if checkpoint is None:
        checkpoint = create_empty_checkpoint(run_config)

    if checkpoint.get("context_before") is not None:
        emit_progress(not args.no_progress, "step 1/4 reuse context before prewarm from checkpoint")
        context_before = checkpoint["context_before"]
    else:
        emit_progress(not args.no_progress, "step 1/4 inspect context before prewarm")
        context_before = build_summary(include_meta_files=False)
        checkpoint["context_before"] = context_before
        save_checkpoint(checkpoint_path, checkpoint)

    meta_download_result = checkpoint.get("meta_download")
    if not args.skip_meta_download:
        if meta_download_result is not None:
            emit_progress(not args.no_progress, "step 2/4 reuse offline metadata download result from checkpoint")
        else:
            emit_progress(not args.no_progress, "step 2/4 download offline metadata package")
            meta_download_result, _ = run_hcloud_command(
                [binary, "meta", "download"] + common_args,
                timeout=args.command_timeout,
                known_secrets=known_secrets,
                max_output_chars=args.max_output_chars,
                show_progress=not args.no_progress,
                progress_label="meta download",
            )
            checkpoint["meta_download"] = meta_download_result
            save_checkpoint(checkpoint_path, checkpoint)
    else:
        emit_progress(not args.no_progress, "step 2/4 skip offline metadata package download")

    services_result = [
        warm_service(
            service_name=service_name,
            service_index=index,
            service_total=len(services),
            binary=binary,
            common_args=common_args,
            args=args,
            known_secrets=known_secrets,
            operations_by_service=operations_by_service,
            checkpoint=checkpoint,
            checkpoint_path=checkpoint_path,
        )
        for index, service_name in enumerate(services, start=1)
    ]
    emit_progress(not args.no_progress, "step 4/4 inspect context after prewarm")
    context_after = build_summary(include_meta_files=False)
    service_help_all_success = all(
        service["service_help"]["success"] for service in services_result
    )
    operation_help_all_success = all(
        operation["help"]["success"]
        for service in services_result
        for operation in service["operations"]
    )
    meta_download_success = meta_download_result is None or meta_download_result["success"]

    result = {
        "success": meta_download_success and service_help_all_success and operation_help_all_success,
        "duration_seconds": round(time.time() - started_at, 3),
        "config": {
            "services": services,
            "skip_meta_download": args.skip_meta_download,
            "profile": args.profile,
            "region": args.region,
            "discovered_operations": args.discovered_operations,
            "max_discovered_operations": args.max_discovered_operations,
            "skip_priority_operations": args.skip_priority_operations,
        },
        "checkpoint": {
            "path": str(checkpoint_path),
            "used": not args.no_resume and checkpoint_path.exists(),
            "will_remain": args.keep_checkpoint or not (
                meta_download_success and service_help_all_success and operation_help_all_success
            ),
        },
        "context_before": context_before,
        "meta_download": meta_download_result,
        "services": services_result,
        "context_after": context_after,
        "summary": build_overall_summary(services_result, meta_download_result),
    }
    emit_progress(
        not args.no_progress,
        (
            "complete "
            f"services={result['summary']['service_help_success_count']}/{result['summary']['service_count']} "
            f"operations={result['summary']['operation_help_success_count']}/{result['summary']['operation_attempt_count']} "
            f"overall={summarize_step_result({'success': result['success'], 'error_type': None, 'return_code': 0 if result['success'] else 1})}"
        ),
    )

    if args.summary_file:
        summary_path = Path(args.summary_file)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if result["success"] and not args.keep_checkpoint and checkpoint_path.exists():
        checkpoint_path.unlink()
        result["checkpoint"]["used"] = False
        result["checkpoint"]["will_remain"] = False

    emit_json(result, pretty=args.pretty)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
