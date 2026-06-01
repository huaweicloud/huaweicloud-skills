# Acceptance Criteria: Correct vs Error Patterns for CCI Operations

## Namespace Creation

| Correct Pattern | Error Pattern |
|---|---|
| `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing` included | Missing flavor annotation — creation request rejected |
| `--metadata.name=my-namespace` specified | Missing metadata.name — parameter error |

## Network Creation

| Correct Pattern | Error Pattern |
|---|---|
| Valid subnet ID and VPC ID from `hcloud VPC ListSubnets` | Invalid or non-existent subnet/VPC ID — creation fails |
| `--namespace=<ns-name>` specified | Missing namespace — operation targets wrong context |
| CIDR != `10.247.0.0/16` (e.g., `10.0.0.0/24`) | CIDR overlaps `10.247.0.0/16` — reserved for CCI internal routing |

## Deployment Creation

| Correct Pattern | Error Pattern |
|---|---|
| `spec.selector.matchLabels` matches `spec.template.metadata.labels` | Selector mismatch — pods not managed by Deployment |
| `spec.template.spec.containers.1.resources.limits.cpu` and `memory` specified | Missing resource limits — pod may fail scheduling or exceed quota |
| **limits == requests** (e.g., both `500m/1Gi`) | limits != requests — CCI rejects with "limit and request doesn't equal" error |
| `--namespace=<ns-name>` specified | Missing namespace — Deployment created in wrong/default namespace |

## Pod Creation

| Correct Pattern | Error Pattern |
|---|---|
| `spec.containers.1.resources.limits.cpu` and `memory` specified | Bare pod without resources — may fail scheduling |
| `--namespace=<ns-name>` specified | Missing namespace — Pod created in wrong context |

## EIPPool Creation

| Correct Pattern | Error Pattern |
|---|---|
| `--apiVersion=crd.yangtse.cni/v1` and `--kind=EIPPool` included | Missing apiVersion or kind — 400 error "Object 'Kind' is missing" |
| `--spec.eipAttributes.networkType=5_bgp` specified | Missing networkType — 422 validation error |
| `--spec.eipAttributes.bandwidth.chargeMode=bandwidth` and `name=<bw-name>` specified | Missing chargeMode or name — 403 validation error |
| `--namespace=<ns-name>` specified | Missing namespace — EIPPool created in wrong context |

## Parameter Format Patterns

| Correct Pattern | Error Pattern | Explanation |
|---|---|---|
| `--spec.template.spec.containers.1.image=nginx` | `--spec.template.spec.containers={"image":"nginx"}` | hcloud CLI uses dotted path with `{*}` indexing, not JSON objects |
| `--spec.template.spec.containers.1.image=nginx` (1-based index) | `--spec.template.spec.containers.0.image=nginx` (0-based index) | hcloud CLI uses 1-based indexing for arrays |
| `--metadata.name=my-ns` | `--metadata.name my-ns` (space separation) | hcloud CLI requires `=` between key and value |
| `--cli-region=cn-north-4` | `--region=cn-north-4` | CLI region flag is `--cli-region`, not `--region` |
| `--spec.template.spec.containers.1.resources.limits.cpu=500m` | `--spec.containers.1.resources.limits.cpu=500m` (shallow path) | Must use full deep nested path as shown in `--help` output |
| `--metadata.annotations.namespace-kubernetes-io/flavor=general-computing` | `--metadata.annotations.flavor=general-computing` (abbreviated key) | Annotation keys must be the exact full key name, not abbreviated |