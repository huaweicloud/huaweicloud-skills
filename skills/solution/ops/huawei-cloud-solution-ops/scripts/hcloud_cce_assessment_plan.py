#!/usr/bin/env python3
"""Build a non-executing CCE cloud-native assessment evidence plan."""

from __future__ import annotations

import argparse
from types import SimpleNamespace
from typing import Any

import hcloud_common
import hcloud_resource_discovery
import hcloud_resource_query

DIMENSION_ORDER = (
    "control_plane",
    "nodes_capacity",
    "addons",
    "workloads",
    "network_exposure",
    "observability",
    "security",
    "resilience",
    "cost_governance",
)

DIMENSION_LABELS = {
    "control_plane": "集群控制面",
    "nodes_capacity": "节点与容量",
    "addons": "核心插件",
    "workloads": "工作负载",
    "network_exposure": "网络与入口",
    "observability": "可观测",
    "security": "安全与权限",
    "resilience": "韧性与升级",
    "cost_governance": "成本与治理",
}

HARD_GATED_ACTIONS = (
    "CreateCluster",
    "DeleteCluster",
    "HibernateCluster",
    "AwakeCluster",
    "UpgradeCluster",
    "AddNode",
    "DeleteNode",
    "CreateNodePool",
    "DeleteNodePool",
    "UpdateNodePool",
    "CreateAddonInstance",
    "UpdateAddonInstance",
    "DeleteAddonInstance",
    "CreateKubernetesClusterCert",
)


def discovery_args(args: argparse.Namespace, operation: str) -> SimpleNamespace:
    """Return arguments for a CCE discovery plan."""
    return SimpleNamespace(
        service="CCE",
        operation=operation,
        region=args.region,
        project_id=args.project_id,
        profile=args.profile,
        limit=args.limit,
        catalog_max_operations=args.catalog_max_operations,
        execute=False,
        timeout=args.timeout,
    )


def query_args(args: argparse.Namespace, operation: str, params: list[str]) -> SimpleNamespace:
    """Return arguments for a CCE explicit read query plan."""
    return SimpleNamespace(
        service="CCE",
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


def compact_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a compact, stable subset of a hcloud plan."""
    result = {
        "success": bool(plan.get("success")),
        "service": plan.get("service"),
        "operation": plan.get("operation"),
        "mode": plan.get("mode", "plan"),
        "coverage": plan.get("coverage"),
        "metadata_backed": bool(plan.get("metadata_backed")),
        "required_params": plan.get("required_params", []),
        "provided_params": plan.get("provided_params", []),
        "missing_params": plan.get("missing_params", []),
        "error": plan.get("error"),
    }
    if "command_shell" in plan:
        result["command_shell"] = plan["command_shell"]
    elif plan.get("commands"):
        result["commands"] = plan["commands"]
    return {key: value for key, value in result.items() if value not in (None, [], {})}


def hcloud_discovery_check(args: argparse.Namespace, dimension: str, operation: str, purpose: str) -> dict[str, Any]:
    """Build one hcloud discovery evidence check."""
    plan = hcloud_resource_discovery.build_plan(discovery_args(args, operation))
    return {
        "id": f"{dimension}:{operation}",
        "dimension": dimension,
        "label": DIMENSION_LABELS[dimension],
        "source": "hcloud",
        "operation": operation,
        "purpose": purpose,
        "status": "planned" if plan.get("success") else "blocked",
        "plan": compact_plan(plan),
    }


def hcloud_query_check(args: argparse.Namespace, dimension: str, operation: str, purpose: str) -> dict[str, Any]:
    """Build one hcloud target-scoped evidence check."""
    params = [f"cluster_id={args.cluster_id}"] if args.cluster_id else []
    plan = hcloud_resource_query.build_plan(query_args(args, operation, params))
    return {
        "id": f"{dimension}:{operation}",
        "dimension": dimension,
        "label": DIMENSION_LABELS[dimension],
        "source": "hcloud",
        "operation": operation,
        "purpose": purpose,
        "status": "planned" if plan.get("success") else "needs_input",
        "plan": compact_plan(plan),
    }


def kubectl_check(args: argparse.Namespace, dimension: str, name: str, command: list[str], purpose: str) -> dict[str, Any]:
    """Build one non-executing Kubernetes-layer evidence check."""
    return {
        "id": f"{dimension}:{name}",
        "dimension": dimension,
        "label": DIMENSION_LABELS[dimension],
        "source": "kubectl",
        "purpose": purpose,
        "status": "planned" if args.include_kubernetes else "optional",
        "command": command,
        "boundary": "Run only after kubeconfig/RBAC is approved; do not persist tokens or print kubeconfig content.",
    }


def manual_check(dimension: str, name: str, purpose: str, evidence: list[str]) -> dict[str, Any]:
    """Build one manual evidence check."""
    return {
        "id": f"{dimension}:{name}",
        "dimension": dimension,
        "label": DIMENSION_LABELS[dimension],
        "source": "manual_review",
        "purpose": purpose,
        "status": "planned",
        "expected_evidence": evidence,
    }


def workload_scope(args: argparse.Namespace) -> list[str]:
    """Return kubectl namespace/workload selector tokens."""
    tokens: list[str] = []
    if args.namespace:
        tokens.extend(["-n", args.namespace])
    if args.workload:
        tokens.extend(["--selector", args.workload])
    return tokens


def dimension_checks(args: argparse.Namespace, dimension: str) -> list[dict[str, Any]]:
    """Return assessment checks for one dimension."""
    scope = workload_scope(args)
    if dimension == "control_plane":
        return [
            hcloud_discovery_check(args, dimension, "ListClusters", "发现集群清单、版本、状态、VPC 和集群类型。"),
            hcloud_query_check(args, dimension, "ShowCluster", "读取目标集群详情，确认控制面、网络和版本事实。"),
            hcloud_query_check(args, dimension, "ShowClusterEndpoints", "读取 API server endpoint，区分公网/私网访问边界。"),
            hcloud_query_check(args, dimension, "ShowClusterUpgradeInfo", "读取升级可用性和升级风险线索。"),
        ]
    if dimension == "nodes_capacity":
        return [
            hcloud_query_check(args, dimension, "ListNodes", "读取节点状态、规格、可用区和异常节点。"),
            hcloud_query_check(args, dimension, "ListNodePools", "读取节点池容量、伸缩边界和节点池状态。"),
            hcloud_query_check(args, dimension, "ShowNodePoolConfigurations", "读取节点池配置项，辅助容量和弹性评估。"),
            kubectl_check(args, dimension, "top-nodes", ["kubectl", "top", "nodes"], "确认节点资源使用率。"),
        ]
    if dimension == "addons":
        return [
            hcloud_query_check(args, dimension, "ListAddonInstances", "读取 CoreDNS、Everest、metrics-server 等核心插件安装状态。"),
            hcloud_query_check(args, dimension, "ListAddonTemplates", "读取插件模板版本，辅助升级/兼容性评估。"),
            manual_check(
                dimension,
                "core-addon-review",
                "确认 DNS、存储、网络、监控插件是否满足当前业务。",
                ["CoreDNS 状态", "存储插件状态", "metrics-server 状态", "插件版本和升级建议"],
            ),
        ]
    if dimension == "workloads":
        return [
            hcloud_query_check(args, dimension, "ListReleases", "读取 CCE release 视角的应用发布线索。"),
            kubectl_check(args, dimension, "pods", ["kubectl", "get", "pods", *scope, "-o", "wide"], "确认 Pod 状态、重启次数和调度位置。"),
            kubectl_check(args, dimension, "deployments", ["kubectl", "get", "deploy,sts,ds", *scope], "确认副本数、可用副本和 rollout 状态。"),
            kubectl_check(args, dimension, "events", ["kubectl", "get", "events", *scope, "--sort-by=.lastTimestamp"], "收集最近调度、拉镜像、探针和权限事件。"),
        ]
    if dimension == "network_exposure":
        return [
            hcloud_query_check(args, dimension, "ShowClusterEndpoints", "确认集群 API endpoint 和访问边界。"),
            kubectl_check(args, dimension, "services", ["kubectl", "get", "svc,ingress", *scope, "-o", "wide"], "确认 Service/Ingress 暴露方式。"),
            manual_check(
                dimension,
                "cloud-entry-review",
                "把 Kubernetes 入口和云侧 ELB/EIP/DNS/CDN/WAF 串起来验证。",
                ["ELB listener/member health", "安全组来源 CIDR", "DNS/HTTPS 探测", "CDN/WAF 源站配置"],
            ),
        ]
    if dimension == "observability":
        return [
            hcloud_query_check(args, dimension, "ShowClusterConfig", "读取集群配置，辅助日志和监控接入判断。"),
            kubectl_check(args, dimension, "pod-metrics", ["kubectl", "top", "pods", *scope], "确认 Pod 资源指标是否可用。"),
            manual_check(
                dimension,
                "logs-and-alarms",
                "确认 CES/LTS/告警覆盖控制面、节点、Pod 和入口链路。",
                ["CES 指标", "LTS 日志", "告警规则", "关键业务探针"],
            ),
        ]
    if dimension == "security":
        return [
            hcloud_query_check(args, dimension, "ListAccessPolicy", "读取 CCE access policy，确认集群访问授权边界。"),
            kubectl_check(args, dimension, "rbac", ["kubectl", "get", "role,rolebinding,clusterrolebinding", "-A"], "检查 RBAC 高权限绑定。"),
            manual_check(
                dimension,
                "secret-and-image-policy",
                "确认 Secret、镜像来源和最小权限边界。",
                ["SWR 镜像来源", "Secret 管理方式", "ServiceAccount 权限", "公网 API server 暴露情况"],
            ),
        ]
    if dimension == "resilience":
        return [
            hcloud_query_check(args, dimension, "ListClusterUpgradePaths", "读取升级路径，评估版本生命周期。"),
            hcloud_query_check(args, dimension, "ListClusterMasterSnapshotTasks", "读取控制面备份/快照任务线索。"),
            kubectl_check(args, dimension, "pdb", ["kubectl", "get", "pdb", *scope], "确认关键工作负载是否有 PDB。"),
            manual_check(
                dimension,
                "ha-review",
                "确认多 AZ、反亲和、滚动升级、备份和回滚能力。",
                ["节点跨 AZ", "副本数", "PDB", "备份/恢复", "升级窗口"],
            ),
        ]
    if dimension == "cost_governance":
        return [
            hcloud_query_check(args, dimension, "ListNodePools", "读取节点池容量，识别闲置或过量节点。"),
            hcloud_query_check(args, dimension, "GetResourceTags", "读取集群标签，用于 owner/env/cost-center 治理。"),
            manual_check(
                dimension,
                "cost-review",
                "确认 CCE 节点、EVS、ELB、EIP、NAT、日志和镜像仓库成本边界。",
                ["节点规格与利用率", "包周期/按需", "闲置 EIP/ELB", "日志保留", "标签覆盖"],
            ),
        ]
    raise ValueError(f"Unsupported dimension: {dimension}")


def selected_dimensions(args: argparse.Namespace) -> list[str]:
    """Return selected assessment dimensions in stable order."""
    if not args.dimension or "all" in args.dimension:
        return list(DIMENSION_ORDER)
    selected = []
    for dimension in DIMENSION_ORDER:
        if dimension in args.dimension:
            selected.append(dimension)
    return selected


def summarize_gaps(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize planned and missing evidence states."""
    by_status: dict[str, int] = {}
    missing_inputs = []
    for check in checks:
        status = str(check.get("status") or "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        missing = check.get("plan", {}).get("missing_params", [])
        if missing:
            missing_inputs.append({"check": check["id"], "missing_params": missing})
    return {
        "check_count": len(checks),
        "status_counts": by_status,
        "missing_inputs": missing_inputs,
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Build a CCE assessment evidence plan."""
    dimensions = selected_dimensions(args)
    checks: list[dict[str, Any]] = []
    for dimension in dimensions:
        checks.extend(dimension_checks(args, dimension))

    return {
        "success": True,
        "planning_only": True,
        "service": "CCE",
        "cluster_id": args.cluster_id,
        "cluster_name": args.cluster_name,
        "namespace": args.namespace,
        "workload": args.workload,
        "dimensions": [{"id": item, "label": DIMENSION_LABELS[item]} for item in dimensions],
        "checks": checks,
        "summary": summarize_gaps(checks),
        "hard_gated_actions": list(HARD_GATED_ACTIONS),
        "execution_boundary": (
            "This planner does not download kubeconfig, run kubectl, create/delete/upgrade clusters, "
            "resize node pools, install addons, or change workloads."
        ),
        "recommended_playbooks": [
            "references/playbooks/cce-cloud-native-assessment.md",
            "references/playbooks/cce-cluster-readiness.md",
            "references/playbooks/swr-image-readiness.md",
            "references/playbooks/vpc-network-readiness.md",
            "references/playbooks/observability-readiness.md",
            "references/playbooks/billing-cost-governance.md",
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-id", help="Target CCE cluster ID. Enables cluster-scoped hcloud evidence checks.")
    parser.add_argument("--cluster-name", help="Optional user-facing cluster name for reports.")
    parser.add_argument("--namespace", help="Optional Kubernetes namespace for workload evidence templates.")
    parser.add_argument("--workload", help="Optional Kubernetes label selector for workload evidence templates.")
    parser.add_argument("--dimension", action="append", choices=("all", *DIMENSION_ORDER), help="Assessment dimension. Repeatable. Default: all.")
    parser.add_argument("--include-kubernetes", action="store_true", help="Include kubectl evidence templates as planned checks.")
    parser.add_argument("--region", help="Optional hcloud cli-region for generated commands.")
    parser.add_argument("--project-id", help="Optional Huawei Cloud project_id for generated commands.")
    parser.add_argument("--profile", help="Optional hcloud cli-profile for generated commands.")
    parser.add_argument("--limit", type=int, default=20, help="Limit for list-style evidence commands.")
    parser.add_argument("--catalog-max-operations", type=int, default=5, help="Max metadata operations in fallback discovery plans.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for generated safe_exec commands if executed later.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("--limit must be greater than 0.")
    if args.catalog_max_operations < 1:
        parser.error("--catalog-max-operations must be greater than 0.")
    if args.timeout < 1:
        parser.error("--timeout must be greater than 0.")
    return args


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    hcloud_common.emit_json(build_plan(args), pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
