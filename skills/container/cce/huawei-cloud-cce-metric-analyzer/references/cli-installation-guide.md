# CLI Installation Guide

## Scope

This skill is executed through the bundled dispatcher:

```bash
python3 scripts/huawei-cloud.py <tool-name> key=value key=value
```

Do not ask users to run raw `hcloud` commands for normal skill execution. The dispatcher calls the required CLI or HTTP path internally.

## Required CLIs

| CLI | Purpose | Required For |
| --- | --- | --- |
| `python3` | Run the dispatcher and parse results | All tools |
| `hcloud` / KooCLI | Query Huawei Cloud CCE, ECS, ELB, EIP, NAT, CES, IAM, and add-on metadata | Cloud service and CES metric tools |
| `kubectl` | Read Kubernetes resources only when AOM/hcloud cannot derive them | Pod label filtering, Ingress TLS checks, LoadBalancer Service association |
| `kubectl-cce` | Connect to CCE clusters without direct kubeconfig access | Same Kubernetes resource-read paths |

## hcloud Setup

Install Huawei Cloud KooCLI 7.2.2 or later and verify it is available:

```bash
hcloud version
hcloud configure list
```

Credential priority for hcloud calls is:

1. Explicit tool parameters: `ak`, `sk`, `project_id`
2. Local hcloud profile
3. Environment variables

Environment fallback examples:

```bash
export HUAWEI_AK="<your-ak>"
export HUAWEI_SK="<your-sk>"
export HUAWEI_PROJECT_ID="<your-project-id>"
```

## AOM Prometheus HTTP Setup

AOM Prometheus range queries use signed HTTPS requests instead of hcloud. They require explicit AK/SK parameters or environment credentials because encrypted hcloud profile material cannot be reused for signing.

Temporary credentials are supported with:

```bash
export HUAWEI_SECURITY_TOKEN="<security-token>"
```

## kubectl-cce Setup

Install and use `kubectl-cce` according to [kubectl-cce.md](kubectl-cce.md). The plugin is only needed for Kubernetes resource reads such as Pod labels, Ingress TLS Secrets, and LoadBalancer Services.

## Verification

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN region=<region> cluster_id=<cluster-id> top_n=3 hours=1
python3 scripts/huawei-cloud.py huawei_get_ecs_metrics region=<region> instance_id=<ecs-id>
```
