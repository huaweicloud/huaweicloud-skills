#!/usr/bin/env python3
"""Build or run a read-only account inventory plan across core services."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import hcloud_checkpoint
import hcloud_common
import hcloud_obs_readonly
import hcloud_project_resolve
import hcloud_resource_discovery

CHECKPOINT_CONTRACT = "huaweicloud_account_inventory_checkpoint_v1"

INVENTORY_TARGETS = (
    {
        "service": "ECS",
        "operation": "ListCloudServers",
        "category": "compute",
        "purpose": "Inventory ECS instances and status distribution.",
    },
    {
        "service": "VPC",
        "operation": "ListVpcs",
        "category": "network",
        "purpose": "Inventory VPC boundaries.",
    },
    {
        "service": "VPC",
        "operation": "ListSubnets",
        "category": "network",
        "purpose": "Inventory subnet and CIDR layout.",
    },
    {
        "service": "VPC",
        "operation": "ListSecurityGroups",
        "category": "security",
        "purpose": "Inventory security group surfaces before changes.",
    },
    {
        "service": "EIP",
        "operation": "ListPublicips",
        "category": "network",
        "purpose": "Inventory public IPs, bindings, and idle EIP candidates.",
    },
    {
        "service": "ELB",
        "operation": "ListLoadbalancers",
        "category": "traffic",
        "purpose": "Inventory load balancers and operating status.",
    },
    {
        "service": "EVS",
        "operation": "ListVolumes",
        "category": "storage",
        "purpose": "Inventory disks and unattached EVS candidates.",
    },
    {
        "service": "NAT",
        "operation": "ListNatGateways",
        "category": "network",
        "purpose": "Inventory NAT gateways before rule-level checks.",
    },
    {
        "service": "RDS",
        "operation": "ListInstances",
        "category": "database",
        "purpose": "Inventory database instances and lifecycle status.",
    },
    {
        "service": "CCE",
        "operation": "ListClusters",
        "category": "container",
        "purpose": "Inventory Kubernetes clusters.",
    },
    {
        "service": "CDN",
        "operation": "ListDomains",
        "category": "edge",
        "purpose": "Inventory CDN domains and online status.",
    },
    {
        "service": "DNS",
        "operation": "ListPublicZones",
        "category": "network",
        "purpose": "Inventory public DNS zones.",
    },
    {
        "service": "SCM",
        "operation": "ListCertificates",
        "category": "security",
        "purpose": "Inventory SSL certificates and expiration status.",
    },
    {
        "service": "OBS",
        "operation": "ListBuckets",
        "category": "storage",
        "purpose": "Inventory OBS buckets through the obsutil adapter.",
    },
)


def selected_targets(services: list[str]) -> list[dict[str, str]]:
    """Return inventory targets filtered by service names when provided."""
    if not services:
        return [dict(target) for target in INVENTORY_TARGETS]
    requested = {service.upper() for service in services}
    return [dict(target) for target in INVENTORY_TARGETS if target["service"] in requested]


def discovery_args(args: argparse.Namespace, service: str, operation: str, region: str | None) -> SimpleNamespace:
    """Return hcloud_resource_discovery arguments for one inventory target."""
    return SimpleNamespace(
        service=service,
        operation=operation,
        region=region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        catalog_max_operations=1,
        execute=False,
        timeout=args.timeout,
    )


def obs_args(args: argparse.Namespace) -> SimpleNamespace:
    """Return hcloud_obs_readonly arguments for the inventory OBS target."""
    return SimpleNamespace(
        operation="ListBuckets",
        bucket=None,
        endpoint=args.obs_endpoint,
        config=args.obs_config,
        payer=args.obs_payer,
        limit=args.limit,
        arg=[],
        execute=args.execute,
        timeout=args.timeout,
    )


def read_region_file(path: str | None) -> list[str]:
    """Return region names from a newline-delimited or JSON list file."""
    if not path:
        return []
    raw_text = Path(path).expanduser().read_text(encoding="utf-8")
    stripped = raw_text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        data = json.loads(stripped)
        return [str(item).strip() for item in data if str(item).strip()]
    return [line.strip() for line in raw_text.splitlines() if line.strip() and not line.strip().startswith("#")]


def normalized_regions(args: argparse.Namespace) -> list[str | None]:
    """Return requested regions while preserving a single default scope when none are provided."""
    raw_regions = getattr(args, "region", None)
    regions: list[str] = []
    if isinstance(raw_regions, str):
        regions.extend([raw_regions])
    elif isinstance(raw_regions, list):
        regions.extend(str(region).strip() for region in raw_regions if str(region).strip())
    regions.extend(read_region_file(getattr(args, "region_file", None)))

    deduped: list[str] = []
    seen: set[str] = set()
    for region in regions:
        if region in seen:
            continue
        deduped.append(region)
        seen.add(region)
    return deduped or [None]


def scope_for(args: argparse.Namespace, region: str | None) -> dict[str, str | None]:
    """Return the read-only inventory scope for one check."""
    return {
        "region": region,
        "project_id": args.project_id,
        "profile": args.profile,
        "enterprise_project_id": getattr(args, "enterprise_project_id", None),
    }


def args_with_project_id(
    args: argparse.Namespace,
    project_id: str | None,
) -> SimpleNamespace:
    """Return one inventory argument set bound to a resolved project ID."""
    values = dict(vars(args))
    values["project_id"] = project_id
    return SimpleNamespace(**values)


def resolve_region_project(
    args: argparse.Namespace,
    region: str | None,
    targets: list[dict[str, str]],
) -> dict[str, Any]:
    """Resolve a regional project once for all project-scoped inventory checks."""
    if not args.execute or not any(target["service"] != "OBS" for target in targets):
        return {
            "success": True,
            "project_id": args.project_id,
            "source": "explicit" if args.project_id else "not_required_for_plan",
            "region": region,
            "remote_lookup_performed": False,
        }
    if not region:
        return {
            "success": True,
            "project_id": args.project_id,
            "source": "explicit" if args.project_id else "runtime_default_region",
            "region": None,
            "remote_lookup_performed": False,
        }

    def remote_lookup(region_name: str) -> dict[str, Any]:
        """Run one bounded IAM fallback for this inventory region."""
        return hcloud_project_resolve.default_remote_lookup(
            region_name,
            timeout=min(args.timeout, 30),
        )

    return hcloud_project_resolve.resolve_project_id(
        region=region,
        explicit_project_id=args.project_id,
        remote_lookup=remote_lookup,
    )


def project_resolution_failure_check(
    args: argparse.Namespace,
    target: dict[str, str],
    region: str | None,
    resolution: dict[str, Any],
) -> dict[str, Any]:
    """Return a stable failed check when one regional project cannot be resolved."""
    return {
        **target,
        "scope": scope_for(args_with_project_id(args, None), region),
        "enterprise_project_scope": {
            "requested": bool(getattr(args, "enterprise_project_id", None)),
            "status": "not_evaluated",
        },
        "success": False,
        "plan": {
            "success": False,
            "error": "Regional project ID could not be resolved.",
            "error_code": resolution.get("error_code") or "PROJECT_ID_NOT_FOUND",
            "retryable": bool(resolution.get("retryable")),
            "project_resolution": resolution,
        },
    }


def operation_supports_enterprise_project(service: str, operation: str) -> bool:
    """Return whether the local operation metadata supports enterprise_project_id."""
    names = {
        name.lower().replace("-", "_")
        for name in hcloud_resource_discovery.operation_param_names(service, operation)
    }
    return "enterprise_project_id" in names or "enterpriseprojectid" in names


def apply_enterprise_project_scope(
    plan: dict[str, Any],
    service: str,
    operation: str,
    enterprise_project_id: str | None,
) -> dict[str, Any]:
    """Append enterprise_project_id to supported command plans and report handling."""
    if not enterprise_project_id:
        return {"requested": False, "status": "not_requested"}

    supported = operation_supports_enterprise_project(service, operation)
    handling = {
        "requested": True,
        "enterprise_project_id": enterprise_project_id,
        "status": "passed_to_command" if supported else "not_supported_by_operation",
    }
    if not supported:
        return handling

    arg = f"--arg=--enterprise_project_id={enterprise_project_id}"
    for command_item in plan.get("commands", []):
        command = command_item.get("command")
        if isinstance(command, list) and arg not in command:
            command.append(arg)
    command = plan.get("command")
    if isinstance(command, list) and arg not in command:
        command.append(arg)
    return handling


def build_target_plan(args: argparse.Namespace, target: dict[str, str]) -> dict[str, Any]:
    """Build or execute one read-only inventory check."""
    return build_target_plan_for_region(args, target, normalized_regions(args)[0])


def build_target_plan_for_region(
    args: argparse.Namespace,
    target: dict[str, str],
    region: str | None,
) -> dict[str, Any]:
    """Build or execute one read-only inventory check for one region scope."""
    service = target["service"]
    if service == "OBS":
        plan = hcloud_obs_readonly.build_plan(obs_args(args))
    else:
        plan = hcloud_resource_discovery.build_plan(discovery_args(args, service, target["operation"], region))
        enterprise_project_scope = apply_enterprise_project_scope(
            plan,
            service,
            target["operation"],
            getattr(args, "enterprise_project_id", None),
        )
        if plan.get("success") and args.execute:
            plan = hcloud_resource_discovery.execute_plan(plan, args.timeout)
    if service == "OBS":
        enterprise_project_scope = {
            "requested": bool(getattr(args, "enterprise_project_id", None)),
            "enterprise_project_id": getattr(args, "enterprise_project_id", None),
            "status": "not_applicable_to_obs_adapter"
            if getattr(args, "enterprise_project_id", None)
            else "not_requested",
        }
    return {
        **target,
        "scope": scope_for(args, region),
        "enterprise_project_scope": enterprise_project_scope,
        "success": bool(plan.get("success")),
        "plan": plan,
    }


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a compact inventory summary without embedding raw cloud results."""
    category_counts = Counter(check["category"] for check in checks)
    service_counts = Counter(check["service"] for check in checks)
    region_counts = Counter((check.get("scope") or {}).get("region") or "default" for check in checks)
    eps_counts = Counter(
        (check.get("scope") or {}).get("enterprise_project_id") or "all_or_unknown"
        for check in checks
    )
    command_count = 0
    failed_checks = []
    for check in checks:
        plan = check.get("plan", {})
        if "command" in plan:
            command_count += 1
        command_count += len(plan.get("commands", []))
        if not check.get("success"):
            failed_checks.append({"service": check["service"], "operation": check["operation"]})
    return {
        "check_count": len(checks),
        "command_count": command_count,
        "service_count": len(service_counts),
        "region_count": len(region_counts),
        "categories": dict(sorted(category_counts.items())),
        "services": dict(sorted(service_counts.items())),
        "regions": dict(sorted(region_counts.items())),
        "enterprise_projects": dict(sorted(eps_counts.items())),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }


def inventory_outcome_status(
    *,
    check_count: int,
    failed_check_count: int,
    pending_check_count: int = 0,
) -> str:
    """Return the declared aggregate outcome for an inventory result."""
    if pending_check_count:
        return "partially_succeeded" if check_count else "failed"
    if check_count < 1 or failed_check_count >= check_count:
        return "failed"
    if failed_check_count:
        return "partially_succeeded"
    return "succeeded"


def check_identity(region: str | None, target: dict[str, str]) -> str:
    """Return a stable identity for one regional service/operation check."""
    return "|".join((str(region or "default"), target["service"], target["operation"]))


def inventory_checkpoint_scope(
    args: argparse.Namespace,
    regions: list[str | None],
    targets: list[dict[str, str]],
) -> dict[str, Any]:
    """Return the query inputs that must remain identical across resume runs."""
    return {
        "regions": regions,
        "targets": [
            {"service": target["service"], "operation": target["operation"]}
            for target in targets
        ],
        "project_id": args.project_id,
        "enterprise_project_id": getattr(args, "enterprise_project_id", None),
        "profile": args.profile,
        "limit": args.limit,
        "obs_endpoint": args.obs_endpoint,
        "obs_config": args.obs_config,
        "obs_payer": args.obs_payer,
    }


def checkpoint_error_result(
    error: hcloud_checkpoint.CheckpointError,
    checkpoint_path: Path | None,
) -> dict[str, Any]:
    """Return one structured inventory failure before any cloud execution."""
    return {
        "success": False,
        "mode": "execute",
        "planning_only": False,
        "outcome_status": "failed",
        "error_code": error.code,
        "error": str(error),
        "checkpoint": {
            "contract": CHECKPOINT_CONTRACT,
            "path": str(checkpoint_path) if checkpoint_path else None,
        },
    }


def load_inventory_checkpoint(
    path: Path,
    scope: dict[str, Any],
    valid_identities: set[str],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load and validate reusable project resolutions and completed checks."""
    document = hcloud_checkpoint.load_checkpoint(
        path,
        contract=CHECKPOINT_CONTRACT,
        scope=scope,
    )
    state = document["state"]
    project_resolutions = state.get("project_resolutions")
    raw_checks = state.get("checks")
    if not isinstance(project_resolutions, dict) or not isinstance(raw_checks, list):
        raise hcloud_checkpoint.CheckpointError(
            "CHECKPOINT_INVALID",
            "Inventory checkpoint state is missing project resolutions or checks.",
        )
    checks_by_identity: dict[str, dict[str, Any]] = {}
    for check in raw_checks:
        if not isinstance(check, dict):
            raise hcloud_checkpoint.CheckpointError(
                "CHECKPOINT_INVALID",
                "Inventory checkpoint contains a non-object check.",
            )
        target = {
            "service": str(check.get("service") or ""),
            "operation": str(check.get("operation") or ""),
        }
        region = (check.get("scope") or {}).get("region") if isinstance(check.get("scope"), dict) else None
        identity = check_identity(region, target)
        if identity not in valid_identities or identity in checks_by_identity:
            raise hcloud_checkpoint.CheckpointError(
                "CHECKPOINT_INVALID",
                "Inventory checkpoint contains an unknown or duplicate check identity.",
            )
        checks_by_identity[identity] = check
    return project_resolutions, checks_by_identity


def write_inventory_checkpoint(
    path: Path | None,
    scope: dict[str, Any],
    project_resolutions: dict[str, Any],
    checks_by_identity: dict[str, dict[str, Any]],
    *,
    complete: bool,
) -> dict[str, Any] | None:
    """Persist current inventory progress when checkpointing is enabled."""
    if path is None:
        return None
    return hcloud_checkpoint.write_checkpoint(
        path,
        contract=CHECKPOINT_CONTRACT,
        scope=scope,
        state={
            "project_resolutions": project_resolutions,
            "checks": list(checks_by_identity.values()),
            "complete": complete,
        },
    )


def execute_inventory_jobs(
    args: argparse.Namespace,
    jobs: list[tuple[argparse.Namespace, dict[str, str], str | None]],
    checks_by_identity: dict[str, dict[str, Any]],
    *,
    checkpoint_path: Path | None,
    checkpoint_scope: dict[str, Any],
    project_resolutions: dict[str, Any],
    deadline: float | None,
) -> tuple[int, str, dict[str, Any] | None]:
    """Execute unfinished reads, checkpointing each completed check atomically."""
    pending_jobs = list(jobs)
    completed_this_run = 0
    stop_reason = "complete"
    checkpoint_artifact: dict[str, Any] | None = None
    if not pending_jobs:
        checkpoint_artifact = write_inventory_checkpoint(
            checkpoint_path,
            checkpoint_scope,
            project_resolutions,
            checks_by_identity,
            complete=True,
        )
        return completed_this_run, stop_reason, checkpoint_artifact

    max_workers = min(max(1, getattr(args, "max_workers", 4)), len(pending_jobs))
    queue = list(pending_jobs)
    active: dict[Any, tuple[argparse.Namespace, dict[str, str], str | None]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while queue or active:
            within_budget = deadline is None or time.monotonic() < deadline
            while queue and len(active) < max_workers and within_budget:
                job = queue.pop(0)
                active[executor.submit(build_target_plan_for_region, *job)] = job
                within_budget = deadline is None or time.monotonic() < deadline
            if not active:
                if queue:
                    stop_reason = "time_budget_reached"
                break

            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                job = active.pop(future)
                _, target, region = job
                try:
                    check = future.result()
                except Exception as exc:  # noqa: BLE001 - preserve progress for unexpected helper failures
                    check = {
                        **target,
                        "scope": scope_for(args, region),
                        "success": False,
                        "plan": {
                            "success": False,
                            "error_code": "INVENTORY_CHECK_EXCEPTION",
                            "error": str(exc),
                        },
                    }
                checks_by_identity[check_identity(region, target)] = check
                completed_this_run += 1
                checkpoint_artifact = write_inventory_checkpoint(
                    checkpoint_path,
                    checkpoint_scope,
                    project_resolutions,
                    checks_by_identity,
                    complete=False,
                )
            if queue and deadline is not None and time.monotonic() >= deadline and not active:
                stop_reason = "time_budget_reached"
                break

    complete = not queue and not active
    if complete:
        stop_reason = "complete"
    checkpoint_artifact = write_inventory_checkpoint(
        checkpoint_path,
        checkpoint_scope,
        project_resolutions,
        checks_by_identity,
        complete=complete,
    )
    return completed_this_run, stop_reason, checkpoint_artifact


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build or run a read-only account inventory plan."""
    targets = selected_targets(args.service)
    if not targets:
        result = {
            "success": False,
            "mode": "execute" if args.execute else "plan",
            "error": "No inventory targets match the requested service filters.",
            "available_services": sorted({target["service"] for target in INVENTORY_TARGETS}),
        }
        result["outcome_status" if args.execute else "planning_status"] = "failed"
        return result

    regions = normalized_regions(args)
    checkpoint_path = (
        Path(str(getattr(args, "checkpoint_file", ""))).expanduser()
        if getattr(args, "checkpoint_file", None)
        else None
    )
    resume = bool(getattr(args, "resume", False))
    time_budget = getattr(args, "time_budget", None)
    deadline = time.monotonic() + time_budget if args.execute and time_budget is not None else None
    checkpoint_scope = inventory_checkpoint_scope(args, regions, targets)
    valid_identities = {
        check_identity(region, target)
        for region in regions
        for target in targets
    }
    checks_by_identity: dict[str, dict[str, Any]] = {}
    reused_check_count = 0
    if resume:
        if checkpoint_path is None:
            return checkpoint_error_result(
                hcloud_checkpoint.CheckpointError(
                    "CHECKPOINT_REQUIRED",
                    "--resume requires --checkpoint-file.",
                ),
                checkpoint_path,
            )
        try:
            project_resolutions, checks_by_identity = load_inventory_checkpoint(
                checkpoint_path,
                checkpoint_scope,
                valid_identities,
            )
        except hcloud_checkpoint.CheckpointError as exc:
            return checkpoint_error_result(exc, checkpoint_path)
        reused_check_count = len(checks_by_identity)
    else:
        project_resolutions = {
            str(region or "default"): resolve_region_project(args, region, targets)
            for region in regions
        }
        if args.execute:
            write_inventory_checkpoint(
                checkpoint_path,
                checkpoint_scope,
                project_resolutions,
                checks_by_identity,
                complete=False,
            )

    missing_resolution_regions = {
        str(region or "default")
        for region in regions
        if str(region or "default") not in project_resolutions
    }
    if missing_resolution_regions:
        return checkpoint_error_result(
            hcloud_checkpoint.CheckpointError(
                "CHECKPOINT_INVALID",
                "Inventory checkpoint is missing project resolution state.",
            ),
            checkpoint_path,
        )
    jobs: list[tuple[argparse.Namespace, dict[str, str], str | None]] = []
    for region in regions:
        resolution = project_resolutions[str(region or "default")]
        regional_args = args_with_project_id(args, resolution.get("project_id"))
        for target in targets:
            identity = check_identity(region, target)
            if identity in checks_by_identity:
                continue
            if target["service"] != "OBS" and not resolution.get("success"):
                checks_by_identity[identity] = project_resolution_failure_check(
                    args,
                    target,
                    region,
                    resolution,
                )
            else:
                jobs.append((regional_args, target, region))

    if args.execute:
        precomputed_this_run = max(0, len(checks_by_identity) - reused_check_count)
        completed_this_run, stop_reason, checkpoint_artifact = execute_inventory_jobs(
            args,
            jobs,
            checks_by_identity,
            checkpoint_path=checkpoint_path,
            checkpoint_scope=checkpoint_scope,
            project_resolutions=project_resolutions,
            deadline=deadline,
        )
        completed_this_run += precomputed_this_run
    else:
        completed_this_run = 0
        stop_reason = "complete"
        checkpoint_artifact = None
        if jobs:
            max_workers = min(max(1, getattr(args, "max_workers", 4)), len(jobs))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                planned_checks = executor.map(
                    lambda job: build_target_plan_for_region(*job),
                    jobs,
                )
                for job, check in zip(jobs, planned_checks, strict=True):
                    checks_by_identity[check_identity(job[2], job[1])] = check

    checks = list(checks_by_identity.values())
    pending_identities = valid_identities - set(checks_by_identity)
    check_order = {
        (str(region or "default"), target["service"], target["operation"]): index
        for index, (region, target) in enumerate(
            (region, target) for region in regions for target in targets
        )
    }
    checks.sort(
        key=lambda check: check_order[
            (
                str((check.get("scope") or {}).get("region") or "default"),
                check["service"],
                check["operation"],
            )
        ]
    )
    summary = summarize_checks(checks)
    outcome_status = inventory_outcome_status(
        check_count=summary["check_count"],
        failed_check_count=summary["failed_check_count"],
        pending_check_count=len(pending_identities),
    )
    success = outcome_status == "succeeded" if args.strict else bool(checks)
    result = {
        "success": success,
        "mode": "execute" if args.execute else "plan",
        "planning_only": not args.execute,
        "region": regions[0] if len(regions) == 1 else None,
        "regions": regions,
        "project_id": (
            next(iter(project_resolutions.values())).get("project_id")
            if len(project_resolutions) == 1
            else None
        ),
        "project_ids": {
            region: resolution.get("project_id")
            for region, resolution in project_resolutions.items()
        },
        "project_resolution": project_resolutions,
        "profile": args.profile,
        "enterprise_project_id": getattr(args, "enterprise_project_id", None),
        "limit": args.limit,
        "summary": summary,
        "checks": checks,
        "execution_progress": {
            "complete": not pending_identities,
            "total_check_count": len(valid_identities),
            "completed_check_count": len(checks),
            "pending_check_count": len(pending_identities),
            "completed_this_run": completed_this_run,
            "reused_check_count": reused_check_count,
            "resumed": resume,
            "time_budget_seconds": time_budget,
            "stop_reason": stop_reason if pending_identities else "complete",
        },
        "checkpoint": {
            "contract": CHECKPOINT_CONTRACT,
            "enabled": checkpoint_path is not None,
            "path": str(checkpoint_path.absolute()) if checkpoint_path else None,
            "artifact": checkpoint_artifact,
        },
        "next_steps": [
            "Run with --execute only for approved read-only inventory collection.",
            "Save executed JSON output and pass it to hcloud_idle_audit.py for idle-candidate analysis.",
            "For multi-region reviews, keep partial failures visible and rerun only the failed region/service checks after fixing permissions or service enablement.",
            "Do not delete, release, or downsize resources from inventory data alone; confirm owner, tags, recent metrics, backups, and retention first.",
        ],
    }
    result["outcome_status" if args.execute else "planning_status"] = outcome_status
    return result


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", action="append", default=[], help="Limit inventory to a service. Can be repeated.")
    parser.add_argument("--region", action="append", default=[], help="Explicit cli-region for generated commands. Can be repeated.")
    parser.add_argument("--region-file", help="Optional newline-delimited or JSON-list file of regions.")
    parser.add_argument("--project-id", help="Optional project_id for generated commands.")
    parser.add_argument("--enterprise-project-id", help="Optional enterprise_project_id scope for operations that support it.")
    parser.add_argument("--profile", help="Optional cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=50, help="Optional limit for list operations that support it.")
    parser.add_argument("--obs-endpoint", help="Optional OBS endpoint passed to the obsutil adapter.")
    parser.add_argument("--obs-config", help="Optional obsutil config path.")
    parser.add_argument("--obs-payer", help="Optional OBS request payer.")
    parser.add_argument("--execute", action="store_true", help="Execute approved read-only inventory commands.")
    parser.add_argument("--strict", action="store_true", help="Return failure when any inventory check fails.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per executed command.")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum concurrent service queries.")
    parser.add_argument("--checkpoint-file", help="Private progress file for interrupted execute-mode inventory runs.")
    parser.add_argument("--resume", action="store_true", help="Resume unfinished checks from --checkpoint-file.")
    parser.add_argument(
        "--time-budget",
        type=int,
        help="Stop scheduling new checks after this many seconds; already running checks may finish.",
    )
    parser.add_argument("--output-file", help="Write the complete JSON result to this file and emit a compact receipt.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    if args.max_workers < 1 or args.max_workers > 16:
        parser.error("--max-workers must be between 1 and 16.")
    if args.resume and not args.execute:
        parser.error("--resume requires --execute.")
    if args.resume and not args.checkpoint_file:
        parser.error("--resume requires --checkpoint-file.")
    if args.checkpoint_file and not args.execute:
        parser.error("--checkpoint-file requires --execute.")
    if args.time_budget is not None and args.time_budget < 1:
        parser.error("--time-budget must be greater than 0.")
    if args.time_budget is not None and not args.execute:
        parser.error("--time-budget requires --execute.")
    return args


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
        receipt_fields=("planning_status", "summary", "execution_progress", "checkpoint"),
    )


def main() -> int:
    """Build or run the read-only account inventory plan."""
    args = parse_args()
    result = build_plan(args)
    emit_cli_result(
        result,
        output_file=args.output_file,
        pretty=args.pretty,
    )
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
