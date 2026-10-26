# KooCLI Command Reference (verified on KooCLI 7.2.2)

## Overview

This document is a Huawei Cloud KooCLI (`hcloud`) command quick reference, covering the CLI command formats, parameter descriptions, and common error handling for all 35 services used by this skill. All commands have been verified on KooCLI 7.2.2.

Huawei Cloud KooCLI (`hcloud`) calls API Explorer cloud service APIs. Format:

```bash
hcloud <SERVICE> <Operation> --cli-region=<region> [--param=value ...]
```

## Configuration

```bash
# Regular AK/SK
hcloud configure set \
  --cli-access-key=<AK> --cli-secret-key=<SK> --cli-region=cn-north-4

# Temporary STS credentials (all three elements must be configured together; missing token causes Unauthorized)
hcloud configure set \
  --cli-access-key=<AK> --cli-secret-key=<SK> --cli-security-token=<TOKEN> \
  --cli-region=cn-north-4 --cli-domain-id=<domain_id>

# Show configuration
hcloud configure list
```

> Environment variables take higher priority and are not written to disk: `HW_ACCESS_KEY` / `HW_SECRET_KEY` / `HW_SECURITY_TOKEN`.

## Service Commands (differences from older documentation)

| Service | Command | Notes |
|---------|---------|-------|
| CCE cluster | `hcloud CCE ListClusters --cli-region=<r> --Content-Type="application/json"` | Returns `{"items":[...]}` |
| CCE node | `hcloud CCE ListNodes --cli-region=<r> --cluster_id=<uid>` | Requires cluster UID |
| CCE node pool | `hcloud CCE ListNodePools --cli-region=<r> --cluster_id=<uid>` | |
| CCE cluster certificate | `hcloud CCE CreateKubernetesClusterCert --cli-region=<r> --cluster_id=<uid> --duration=1` | Returns kubeconfig (with internal/external endpoints); returns Status Failure when no usable endpoint |
| VPC | `hcloud VPC ListVpcs --cli-region=<r>` | Returns `{"vpcs":[...]}` |
| VPC subnet | `hcloud VPC ListSubnets --cli-region=<r>` | |
| OBS bucket | `hcloud RMS ListAllResources --cli-region=<r> --type=obs.buckets` | ⚠️ KooCLI has no `OBS ListBuckets` (the obs subcommand is obsutil style, not JSON) |
| RMS summary | `hcloud RMS CollectAllResourcesSummary --cli-region=<r>` | provider/types summary (top-level is a JSON array) |
| RMS all resources | `hcloud RMS ListAllResources --cli-region=<r> --type=<provider.type>` | `--type` looks like `obs.buckets` / `live.domains` |
| ECS | `hcloud ECS ListServersDetails --cli-region=<r>` | ⚠️ Not `ListServers` (that operation does not exist) |
| GEIP | `hcloud GEIP ListGlobalEips --cli-region=<r>` | Returns `{"global_eips":[...]}`, contains `associate_instance_id/type` (used for binding inference) |
| ELB load balancer | `hcloud ELB ListLoadBalancers --cli-region=<r>` | Query `ListPools --loadbalancer_id.1=<id>` per LB (array parameter with `.1` index, verified) → query `ListMembers --pool_id=<id>` per Pool (used for backend binding inference) |
| LIVE | `hcloud RMS ListAllResources --cli-region=<r> --type=live.domains` | ⚠️ KooCLI Live has no domain list operation |
| CDN | `hcloud CDN ListDomains --cli-region=cn-north-1` | ⚠️ Global service, only supports cn-north-1 / ap-southeast-1; querying cn-north-4 reports region not supported |
| CC (cloud connect) | `hcloud CC ListCloudConnections --cli-region=<r>` | Corresponds to CCAAS |
| EPS enterprise project | `hcloud EPS ListEnterpriseProject --cli-region=<r>` | enterprise project id→name mapping; `ShowResourceBindEnterpriseProject` requires projects+resource_types (strict enumeration, prone to EPS.0025) |

## Multi-Version Interfaces

Some services have multiple API versions (e.g., VPC v2/v3). KooCLI defaults to the latest version. To specify a version:

```bash
hcloud VPC ListVpcs/v3 --cli-region=cn-north-4
```

To view the available operations of a service:

```bash
hcloud CCE --help
hcloud VPC ListVpcs --help
```

> **Prompt lines**: when an interface has multiple versions, KooCLI prints `Xxx有多个版本,默认使用该API版本vX...` before stdout. The prompt line must be stripped before parsing JSON, starting from the first `{`/`[` (`query_resources.py` handles this automatically).

## Output

- Default output is the native API Explorer JSON (e.g., `{"items":[...]}`)
- The script `query_resources.py` saves raw JSON to `<SERVICE>/temp/` and counts the entries

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `[NETWORK_ERROR]connection timeout` | Network unreachable / target endpoint not reachable | Check network and target endpoint connectivity |
| `APIGW.0301 Incorrect IAM authentication information: Unauthorized` | Temporary credentials missing security token / wrong AK-SK / expired | Configure `--cli-security-token` (or `HW_SECURITY_TOKEN`); check AK/SK |
| `Failed to get project ID` / `Missing required parameter: project_id` | IAM authentication failure prevents auto-acquiring project_id | Fix authentication first (see above) |
| `Unsupported operation: ListServers` etc. | Wrong operation name | Run `hcloud <SERVICE> --help` to find the correct operation name (ECS uses ListServersDetails) |
| `Incorrect parameter: Content-Type` | This interface does not accept Content-Type | Remove that parameter (only CCE ListClusters needs it) |
| `No such command: "ListBuckets"` | OBS has no REST operation | Use RMS `ListAllResources --type=obs.buckets` |
| `cli-region value not supported` | Global service region restriction | Use cn-north-1 / ap-southeast-1 for CDN |
| No data `items: []` | No such resource in this region | Switch region or use RMS to find the region of the resource |

## Correct/Wrong Command Format Examples

| Scenario | ✅ Correct | ❌ Wrong |
|----------|-----------|----------|
| Service name | `hcloud ECS ListServersDetails` | `hcloud ecs ListServersDetails` |
| Operation name | `hcloud VPC ListSecurityGroups/v3` | `hcloud VPC listsecuritygroups` |
| Region parameter | `--cli-region=cn-north-4` | `--region=cn-north-4` |
| IAM operation | `hcloud IAM KeystoneListUsers` | `hcloud IAM ListUsers` |
| ECS list | `hcloud ECS ListServersDetails` | `hcloud ECS ListServers` |
| OBS bucket | `hcloud RMS ListAllResources --type=obs.buckets` | `hcloud OBS ListBuckets` |
| Version command | `hcloud version` | `hcloud --version` |
| AK/SK configuration | `hcloud configure set --cli-access-key=AK --cli-secret-key=SK` | Setting the two parameters separately |
