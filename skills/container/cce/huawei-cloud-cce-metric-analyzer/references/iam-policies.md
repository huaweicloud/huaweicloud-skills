# IAM Policies

## Scope

This skill is read-only. It queries monitoring data and cloud resource metadata. It must not create, update, delete, restart, scale, or remediate Huawei Cloud or Kubernetes resources.

## Required Permissions

| Service | Permission / API Action | Purpose |
| --- | --- | --- |
| CCE | `cce:cluster:get` | Read CCE cluster details and network binding |
| CCE | `cce:addonInstance:list` / add-on list equivalent | Discover the cluster AOM Prometheus binding |
| AOM | `aom:instance:list` | Locate AOM Prometheus instances |
| AOM | `aom:metricsData:get` | Query Pod, Node, CoreDNS, ingress, autoscaler, control-plane, GPU, and xGPU metrics |
| CES | `ces:metricsData:get` | Query ECS, ELB, EIP, and NAT Gateway metrics |
| ECS | `ecs:cloudServers:list` / `ecs:cloudServers:get` | Resolve and query ECS instances |
| ELB | `elb:loadbalancers:list` / `elb:loadbalancers:get` | Resolve ELB resources associated with the cluster |
| VPC | `vpc:eips:list` / `vpc:eips:get` | Resolve EIP resources associated with ELB/NAT/Service IPs |
| NAT | `nat:natGateways:list` / `nat:natGateways:get` | Resolve NAT Gateways in the cluster VPC |
| IAM | `iam:projects:list` | Resolve `project_id` when it is not provided |

## Kubernetes RBAC

When `kubectl`/`kubectl-cce` is used, the effective cluster identity needs read-only access to:

| Resource | Verb | Purpose |
| --- | --- | --- |
| Pods | `get`, `list` | Optional Pod label filtering |
| Services | `get`, `list` | LoadBalancer Service discovery for ELB/EIP association |
| Ingresses | `get`, `list` | TLS Secret discovery |
| Secrets | `get` | Read TLS certificate data for expiration checks |

Do not grant write verbs such as `create`, `update`, `patch`, or `delete` for this skill.

## Example Custom Policy Guidance

Create a least-privilege read-only IAM policy that includes only the actions above. If a tool fails with a permission error, report the missing service/action and ask the user to grant it before retrying.

## Security Requirements

- Never print or persist AK/SK, security tokens, kubeconfig content, or TLS Secret content.
- Prefer hcloud profile for normal hcloud calls.
- Use explicit AK/SK or environment credentials only for AOM signed HTTP and kubectl-cce paths that require signing material.
- Keep all metric queries scoped by `cluster="<cluster_id>"` where possible.
