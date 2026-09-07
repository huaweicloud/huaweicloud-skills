#!/usr/bin/env python3
"""Build a non-executing CCI workload preflight and acceptance evidence plan."""

from __future__ import annotations

import argparse
import ipaddress
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_query

RESERVED_CCI_SUBNET = ipaddress.ip_network("10.247.0.0/16")
WORKLOAD_LIST_OPERATIONS = {
    "deployment": "listAppsV1NamespacedDeployment",
    "statefulset": "listAppsV1NamespacedStatefulSet",
    "pod": "listCoreV1NamespacedPod",
    "job": "listBatchV1NamespacedJob",
}
DELETE_ACTIONS = {
    "delete_namespace",
    "delete_network",
    "delete_workload",
    "delete_eip_pool",
}


def query_args(args: argparse.Namespace, operation: str, params: list[str]) -> SimpleNamespace:
    """Return planner-only arguments for one CCI read query."""
    return SimpleNamespace(
        service="CCI",
        operation=operation,
        param=params,
        arg=[],
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        execute=False,
        timeout=args.timeout,
        allow_sensitive_read=False,
    )


def compact_query_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return stable, non-sensitive fields from a nested hcloud query plan."""
    fields = (
        "success",
        "mode",
        "service",
        "operation",
        "coverage",
        "metadata_backed",
        "required_params",
        "provided_params",
        "missing_params",
        "command_shell",
        "error",
    )
    return {
        field: plan[field]
        for field in fields
        if field in plan and plan[field] not in (None, [], {}, "")
    }


def query_check(
    args: argparse.Namespace,
    *,
    check_id: str,
    operation: str,
    purpose: str,
    params: list[str],
) -> dict[str, Any]:
    """Build one hcloud-only, non-executing CCI evidence check."""
    plan = hcloud_resource_query.build_plan(query_args(args, operation, params))
    return {
        "id": check_id,
        "source": "hcloud",
        "operation": operation,
        "purpose": purpose,
        "status": "planned" if plan.get("success") else "needs_input",
        "plan": compact_query_plan(plan),
    }


def input_check(check_id: str, value: str | None, purpose: str) -> dict[str, Any]:
    """Return a preflight check for a required non-secret input."""
    return {
        "id": check_id,
        "source": "user_input",
        "purpose": purpose,
        "status": "planned" if value else "needs_input",
    }


def resource_pair_check(
    check_id: str,
    request: str | None,
    limit: str | None,
    resource_name: str,
) -> dict[str, Any]:
    """Require matching CCI request and limit values without unit conversion."""
    if not request and not limit:
        status = "needs_input"
        detail = f"Provide both {resource_name} request and limit values."
    elif not request or not limit:
        status = "needs_input"
        detail = f"Provide both {resource_name} request and limit values; one-sided values are not accepted."
    elif request != limit:
        status = "blocked"
        detail = f"CCI requires matching {resource_name} request and limit values."
    else:
        status = "planned"
        detail = f"{resource_name} request and limit are equal."
    return {
        "id": check_id,
        "source": "input_validation",
        "purpose": "Avoid a CCI resource configuration that is rejected or schedules unexpectedly.",
        "status": status,
        "detail": detail,
    }


def subnet_cidr_check(subnet_cidr: str | None) -> dict[str, Any]:
    """Reject CCI subnet CIDRs that overlap CCI's reserved range."""
    if not subnet_cidr:
        return {
            "id": "subnet_cidr",
            "source": "input_validation",
            "purpose": "Confirm the selected subnet does not overlap CCI reserved addresses.",
            "status": "needs_input",
        }
    try:
        network = ipaddress.ip_network(subnet_cidr, strict=False)
    except ValueError:
        return {
            "id": "subnet_cidr",
            "source": "input_validation",
            "purpose": "Confirm the selected subnet does not overlap CCI reserved addresses.",
            "status": "blocked",
            "detail": "The subnet CIDR is invalid.",
        }
    if network.overlaps(RESERVED_CCI_SUBNET):
        return {
            "id": "subnet_cidr",
            "source": "input_validation",
            "purpose": "Confirm the selected subnet does not overlap CCI reserved addresses.",
            "status": "blocked",
            "detail": f"The subnet CIDR overlaps CCI reserved range {RESERVED_CCI_SUBNET}.",
        }
    return {
        "id": "subnet_cidr",
        "source": "input_validation",
        "purpose": "Confirm the selected subnet does not overlap CCI reserved addresses.",
        "status": "planned",
    }


def public_exposure_gate(args: argparse.Namespace) -> dict[str, Any] | None:
    """Return a hard review gate for CCI public exposure intent."""
    if args.exposure == "internal":
        return None
    missing = []
    if not args.public_access_justification:
        missing.append("public_access_justification")
    if not args.allowed_source_cidr:
        missing.append("allowed_source_cidr")
    if args.exposure == "eip" and not args.eip_pool_name:
        missing.append("eip_pool_name")
    if missing:
        return {
            "id": "public_exposure",
            "source": "risk_gate",
            "status": "blocked",
            "detail": "Public access is blocked until its justification and bounded access evidence are supplied.",
            "missing_inputs": missing,
        }
    if args.allowed_source_cidr == "0.0.0.0/0":
        return {
            "id": "public_exposure",
            "source": "risk_gate",
            "status": "blocked",
            "detail": "Unrestricted 0.0.0.0/0 access is not accepted by the CCI planner.",
        }
    return {
        "id": "public_exposure",
        "source": "risk_gate",
        "status": "review_required",
        "detail": "Public exposure remains planner-only and needs explicit confirmation after security-group and endpoint evidence review.",
    }


def delete_action_gates(actions: list[str]) -> list[dict[str, Any]]:
    """Return non-bypassable planner gates for destructive CCI intents."""
    gates = []
    for action in sorted(set(actions).intersection(DELETE_ACTIONS)):
        detail = "This planner never produces a delete command."
        if action == "delete_namespace":
            detail = (
                "Namespace deletion can cascade to namespaced resources; inventory, backup/rollback, "
                "dependency review, and an explicit later confirmation are required."
            )
        gates.append(
            {
                "id": action,
                "source": "risk_gate",
                "status": "blocked",
                "detail": detail,
            }
        )
    return gates


def evidence_checks(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Build ordered CCI lifecycle evidence checks without executing them."""
    checks = [
        query_check(
            args,
            check_id="namespace_inventory",
            operation="listCoreV1Namespace",
            purpose="List namespaces before selecting or changing the workload scope.",
            params=[],
        )
    ]
    if not args.namespace:
        return checks

    namespace_params = [f"namespace={args.namespace}"]
    checks.extend(
        [
            query_check(
                args,
                check_id="network_inventory",
                operation="listNetworkingCciIoV1beta1NamespacedNetwork",
                purpose="Confirm the namespace Network exists before workload readiness is judged.",
                params=namespace_params,
            ),
            query_check(
                args,
                check_id="resource_quota",
                operation="listCoreV1NamespacedResourceQuota",
                purpose="Read namespace resource quotas before rollout.",
                params=namespace_params,
            ),
            query_check(
                args,
                check_id="recent_events",
                operation="listCoreV1NamespacedEvent",
                purpose="Collect scheduling, image-pull, probe, and permission event evidence.",
                params=namespace_params,
            ),
        ]
    )
    workload_operation = WORKLOAD_LIST_OPERATIONS[args.workload_type]
    checks.append(
        query_check(
            args,
            check_id="workload_inventory",
            operation=workload_operation,
            purpose="Read workload inventory and select the target by its declared name.",
            params=namespace_params,
        )
    )
    checks.append(
        query_check(
            args,
            check_id="pod_inventory",
            operation="listCoreV1NamespacedPod",
            purpose="Validate Pod phase, restart, scheduling, and image-pull evidence after workload rollout.",
            params=namespace_params,
        )
    )
    if args.service_name:
        checks.append(
            query_check(
                args,
                check_id="service_inventory",
                operation="listCoreV1NamespacedService",
                purpose="Confirm Service exposure and endpoint configuration before application acceptance.",
                params=namespace_params,
            )
        )
    checks.append(
        {
            "id": "endpoint_probe",
            "source": "manual_evidence",
            "status": "planned" if args.service_name else "needs_input",
            "purpose": "Run a bounded protocol probe only after workload and Service evidence are healthy.",
            "boundary": "Do not treat Pod Running as application availability; redact request headers and tokens.",
        }
    )
    return checks


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a CCI workload readiness plan that cannot submit or mutate resources."""
    actions = list(getattr(args, "planned_action", None) or ["create"])
    preflight_checks = [
        input_check("namespace", args.namespace, "Select the CCI namespace."),
        input_check("namespace_flavor", args.namespace_flavor, "Confirm general-computing or GPU-accelerated namespace intent."),
        input_check("vpc_id", args.vpc_id, "Record the VPC bound by the CCI Network."),
        input_check("subnet_id", args.subnet_id, "Record the Network subnet."),
        input_check("neutron_network_id", args.neutron_network_id, "Record the CCI Network neutronNetwork identifier."),
        input_check("network_name", args.network_name, "Record the namespace Network name."),
        input_check("security_group_id", args.security_group_id, "Record the Network security group."),
        subnet_cidr_check(args.subnet_cidr),
        input_check("workload_name", args.workload_name, "Select the deployment, statefulset, pod, or job name."),
        input_check("image", args.image, "Record the immutable image tag or digest without credentials."),
        resource_pair_check("cpu_request_limit", args.cpu_request, args.cpu_limit, "CPU"),
        resource_pair_check("memory_request_limit", args.memory_request, args.memory_limit, "memory"),
    ]
    risk_gates = delete_action_gates(actions)
    exposure_gate = public_exposure_gate(args)
    if exposure_gate:
        risk_gates.append(exposure_gate)

    checks = [*preflight_checks, *evidence_checks(args)]
    blocker_ids = [item["id"] for item in [*checks, *risk_gates] if item.get("status") == "blocked"]
    needs_input_ids = [item["id"] for item in checks if item.get("status") == "needs_input"]
    review_ids = [item["id"] for item in risk_gates if item.get("status") == "review_required"]
    if blocker_ids:
        readiness = "blocked"
    elif needs_input_ids:
        readiness = "inputs_needed"
    elif review_ids:
        readiness = "review_required"
    else:
        readiness = "ready_to_review"

    return {
        "success": True,
        "planning_only": True,
        "service": "CCI",
        "planned_actions": actions,
        "inputs": {
            "namespace": args.namespace,
            "namespace_flavor": args.namespace_flavor,
            "network_name": args.network_name,
            "workload_type": args.workload_type,
            "workload_name": args.workload_name,
            "service_name": args.service_name,
            "exposure": args.exposure,
            "region": args.region,
            "project_id": args.project_id,
        },
        "preflight_checks": preflight_checks,
        "evidence_plan": evidence_checks(args),
        "risk_gates": risk_gates,
        "hard_gated_actions": sorted(set(actions).intersection(DELETE_ACTIONS)),
        "summary": {
            "readiness": readiness,
            "blockers": blocker_ids,
            "inputs_needed": needs_input_ids,
            "review_required": review_ids,
        },
        "execution_boundary": (
            "This script never calls hcloud, creates resources, submits changes, or accepts credentials. "
            "Use the generated read-only evidence plans first; any later mutation needs a dedicated guarded flow."
        ),
        "recommended_playbooks": [
            "references/playbooks/cci-workload-readiness.md",
            "references/playbooks/swr-image-readiness.md",
            "references/playbooks/vpc-network-readiness.md",
        ],
    }


def parse_args() -> argparse.Namespace:
    """Parse inputs for a CCI workload readiness plan."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", help="CCI namespace.")
    parser.add_argument("--namespace-flavor", choices=("general-computing", "gpu-accelerated"))
    parser.add_argument("--vpc-id", help="VPC identifier for the namespace Network.")
    parser.add_argument("--subnet-id", help="Subnet identifier for the namespace Network.")
    parser.add_argument("--neutron-network-id", help="CCI Network neutronNetwork identifier.")
    parser.add_argument("--subnet-cidr", help="CIDR of the selected CCI Network subnet.")
    parser.add_argument("--security-group-id", help="Security group identifier for the namespace Network.")
    parser.add_argument("--network-name", help="CCI Network resource name in the namespace.")
    parser.add_argument("--workload-type", choices=tuple(WORKLOAD_LIST_OPERATIONS), default="deployment")
    parser.add_argument("--workload-name", help="Deployment, StatefulSet, Pod, or Job name.")
    parser.add_argument("--image", help="Image repository with a tag or digest; do not provide pull credentials.")
    parser.add_argument("--cpu-request", help="CPU request value; must equal --cpu-limit.")
    parser.add_argument("--cpu-limit", help="CPU limit value; must equal --cpu-request.")
    parser.add_argument("--memory-request", help="Memory request value; must equal --memory-limit.")
    parser.add_argument("--memory-limit", help="Memory limit value; must equal --memory-request.")
    parser.add_argument("--service-name", help="Optional CCI Service name for endpoint evidence.")
    parser.add_argument("--exposure", choices=("internal", "elb", "eip"), default="internal")
    parser.add_argument("--eip-pool-name", help="Required when --exposure=eip.")
    parser.add_argument("--public-access-justification", help="Required for ELB/EIP public access intent.")
    parser.add_argument("--allowed-source-cidr", help="Required bounded source CIDR for ELB/EIP public access intent.")
    parser.add_argument("--planned-action", action="append", choices=("create", *sorted(DELETE_ACTIONS)), default=[])
    parser.add_argument("--region", help="Explicit cli-region for generated evidence commands.")
    parser.add_argument("--project-id", help="Optional project_id for generated evidence commands.")
    parser.add_argument("--profile", help="Optional cli-profile for generated evidence commands.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout retained for generated read-only plans.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main() -> int:
    """Emit the non-executing CCI workload readiness plan."""
    args = parse_args()
    hcloud_common.emit_json(build_plan(args), pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
