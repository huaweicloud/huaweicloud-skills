# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud UCS Cluster Onboarding Manager skill.

## Pitfall 1: Invalid Kubeconfig for Self-Managed Cluster Registration

**Symptom**: `RegisterCluster` fails with `InvalidKubeconfig` or validation error for self-managed cluster

**Root Cause**: The kubeconfig YAML is malformed or missing required fields

**Required Kubeconfig Fields**:
- `apiVersion`: Must be `v1`
- `clusters`: At least one cluster entry with `server` URL and `certificate-authority-data`
- `users`: At least one user entry with valid credentials (token or client-certificate/client-key)
- `contexts`: At least one context linking cluster and user
- `current-context`: Must be set to an existing context name

**Common Mistakes**:
- ❌ Missing `certificate-authority-data` — cluster CA must be provided
- ❌ Expired token in user credentials — ensure the token or certificate is still valid
- ❌ Empty `server` field — API server URL must be a valid HTTPS endpoint
- ❌ Kubeconfig with multiple contexts but no `current-context`

**Solution**: Validate kubeconfig before registration:

```bash
kubectl --kubeconfig=<path> cluster-info
```

## Pitfall 2: CCE Cluster ID vs UCS Cluster ID Confusion

**Symptom**: `ShowCluster`, `UpdateCluster`, or `DeleteCluster` fails with `ClusterNotFound`

**Root Cause**: Using the CCE cluster ID instead of the UCS-assigned cluster ID

**Solution**: After registering a cluster, use the UCS-assigned `id` from the registration response, NOT the original CCE cluster ID:

```bash
hcloud UCS ShowCluster --clusterid=ucs-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --cli-region=cn-north-4
```

❌ **WRONG** — Using CCE cluster ID:

```bash
hcloud UCS ShowCluster --clusterid=cce-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx --cli-region=cn-north-4
```

To find the UCS cluster ID, use `ShowClusterList` and match by metadata.

## Pitfall 3: Cluster Already Registered (409 Conflict)

**Symptom**: `RegisterCluster` returns `409 Conflict` error

**Root Cause**: The same cluster has already been registered to UCS

**Solution**: Check existing registrations before attempting to register:

```bash
hcloud UCS ShowClusterList --category=self --managetype=grouped --cli-region=cn-north-4
```

If the cluster exists, either use the existing registration or deregister first.

## Pitfall 4: Self-Managed Cluster API Server Unreachable

**Symptom**: Cluster registration succeeds but status remains `Unavailable` or transitions to `Unavailable`

**Root Cause**: UCS management plane cannot reach the self-managed cluster's API server

**Common Causes**:
- API server is behind a firewall that blocks UCS access
- API server URL uses internal IP that is not externally reachable
- Network ACL or security group rules prevent inbound connections from UCS

**Solution**: Ensure the cluster API server is accessible:
- Use a publicly reachable API server endpoint in the kubeconfig
- Configure firewall rules to allow UCS management plane access
- For private clusters, set up VPN or direct network connectivity between UCS and the cluster

## Pitfall 5: Deregistration Disables Policy Governance

**Symptom**: After deregistering a cluster, policy enforcement stops working on that cluster

**Root Cause**: UCS policy governance depends on the cluster being registered. Deregistration removes all management capabilities including policy enforcement.

**Solution**: Before deregistering a cluster:
1. Review active policy instances on the cluster (use `ucs-policy-governor` skill)
2. Document current policy configurations
3. Consider disabling specific policies rather than deregistering the entire cluster if only policy reduction is needed

## Pitfall 6: Fleet Group Name Collision

**Symptom**: `RegisterClusterGroup` returns `409 Conflict`

**Root Cause**: A fleet group with the same name already exists in the same region

**Solution**: Check existing groups before creating:

```bash
hcloud UCS ListClusterGroup --cli-region=cn-north-4
```

## Pitfall 7: Quota Exceeded When Registering Clusters

**Symptom**: `RegisterCluster` returns `403 Quota limit exceeded`

**Root Cause**: UCS has cluster registration limits

**Solution**: Check quotas before registering new clusters:

```bash
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

If quota is exceeded, consider:
1. Deregister unused clusters to free quota
2. Apply for quota increase through Huawei Cloud support

## Pitfall 8: Federation Kubeconfig Requires Fleet Group

**Symptom**: `DownloadFederationKubeconfig` fails or returns incomplete config

**Root Cause**: Federation kubeconfig requires a fleet group with at least one cluster in `Available` status. Both `--clustergroupid` and `--duration` are required parameters.

**Solution**: Create a fleet group, register clusters, then download federation kubeconfig:

```bash
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4
```

## Pitfall 9: Kubeconfig Validity Period

**Symptom**: Previously obtained kubeconfig no longer works for kubectl access

**Root Cause**: UCS kubeconfig tokens have expiration periods

**Solution**: Regenerate kubeconfig when access fails:

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4
```

## Pitfall 10: Region Mismatch for CCE Cluster Registration

**Symptom**: CCE cluster registration fails with cluster not found error

**Root Cause**: The `--cli-region` must match the region where the CCE cluster resides. Registering a CCE cluster from a different region will fail.

**Solution**: Ensure the region matches the CCE cluster's actual region:

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=my-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
```

## Pitfall 11: RegisterCluster Uses Kubernetes-Style Parameters

**Symptom**: `RegisterCluster` fails with parameter validation errors (e.g., "missing required parameter")

**Root Cause**: `RegisterCluster` uses Kubernetes-style structured parameters (`--apiVersion`, `--kind`, `--metadata.name`, `--spec.category`, `--spec.provider`, etc.), NOT simple flat parameters like `--name` or `--cluster_type`.

**Common Mistakes**:
- ❌ Using `--name=my-cluster` instead of `--metadata.name=my-cluster`
- ❌ Using `--cluster_type=CCE` instead of `--spec.category=self --spec.type=cce`
- ❌ Using `--cluster_id=<cce-id>` instead of `--metadata.uid=<cce-id>`
- ❌ Using `--kubeconfig_file=<content>` instead of `--metadata.annotations.kubeconfig=<content>`
- ❌ Using `--spec.category=CCE` (uppercase) instead of `--spec.category=self` (verified correct value)
- ❌ Using `--spec.provider=huawei_cloud` (with underscore) instead of `--spec.provider=huaweicloud` (no underscore)
- ❌ Using `--spec.type=CCE` (uppercase) instead of `--spec.type=cce` (lowercase)
- ❌ Using `--spec.city=Beijing` (city name) instead of `--spec.city=110000` (city code)
- ❌ Missing required `--apiVersion=v1` and `--kind=Cluster`
- ❌ Missing required `--spec.country` and `--spec.city`

**Correct CCE Example**:

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=prod-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
```

**Correct Self-Managed Example**:

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=datacenter-k8s --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-content> --cli-region=cn-north-4
```

## Pitfall 12: --clusterid vs --cluster_id Confusion

**Symptom**: Commands fail with "unknown parameter" or parameter validation errors

**Root Cause**: UCS hcloud CLI uses `--clusterid` (no underscore), NOT `--cluster_id` (with underscore)

**Common Mistakes**:
- ❌ Using `--cluster_id=<id>` (with underscore)
- ✅ Using `--clusterid=<id>` (no underscore)

**Affected Operations**: `ShowCluster`, `DeleteCluster`, `UpdateCluster`, `ShowClusterAccessInfo`, `CreateClusterKubeconfig`, `CreateClusterConf`, `RetryClusterActivation`, `JoinGroup`, `LeaveGroup`

## Pitfall 13: --clustergroupid vs --group_id Confusion

**Symptom**: Fleet group operations fail with "unknown parameter" or parameter validation errors

**Root Cause**: UCS hcloud CLI uses `--clustergroupid` (no underscore, different name), NOT `--group_id` (with underscore)

**Common Mistakes**:
- ❌ Using `--group_id=<id>` (with underscore, wrong name)
- ✅ Using `--clustergroupid=<id>` (no underscore, correct name)

**Affected Operations**: `ShowClusterGroup`, `DeleteClusterGroup`, `UpdateClusterGroup`, `UpdateClusterGroupAssociatedClusters`, `DownloadFederationKubeconfig`, `ShowClusterList` (filter parameter)

## Pitfall 14: ShowQuota Requires --domainid

**Symptom**: `ShowQuota` fails with missing required parameter error

**Root Cause**: `ShowQuota` requires `--domainid` (account ID) as a mandatory parameter. It cannot be called without it.

**Solution**: Always provide the account domain ID:

```bash
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

To find your account ID: Log in to Huawei Cloud console → My Credentials → Account ID.

## Pitfall 15: DownloadFederationKubeconfig Requires --clustergroupid and --duration

**Symptom**: `DownloadFederationKubeconfig` fails with missing required parameter error

**Root Cause**: Both `--clustergroupid` and `--duration` are required parameters for `DownloadFederationKubeconfig`. It cannot be called with only `--cli-region`.

**Common Mistakes**:
- ❌ Using `DownloadFederationKubeConfig` (uppercase C) instead of `DownloadFederationKubeconfig` (lowercase c)
- ❌ Calling without `--clustergroupid`
- ❌ Calling without `--duration`

**Solution**:

```bash
hcloud UCS DownloadFederationKubeconfig --clustergroupid=<group-id> --duration=86400 --cli-region=cn-north-4
```

## Pitfall 16: Invalid RegisterCluster Parameter Values (category/provider/type/city)

**Symptom**: `RegisterCluster` fails with `UCS.01000012 - Invalid request body, reason: invalid category` or similar validation error

**Root Cause**: The UCS API uses specific enum values for `spec.category`, `spec.provider`, `spec.type`, and `spec.city` that differ from common assumptions. These values were verified through `ListManagedClusters` and `ShowClusterList` API calls.

**Verified Correct Values**:

| Parameter        | CCE Cluster (华为云CCE)         | Self-Managed Cluster (自管集群)  |
| ---------------- | ------------------------------- | -------------------------------- |
| `--spec.category`| `self`                          | `onpremise`                      |
| `--spec.provider`| `huaweicloud` (no underscore)   | `self_managed`                   |
| `--spec.type`    | `cce` (lowercase)               | `Kubernetes` or `baremetal`      |
| `--spec.city`    | City code, e.g., `110000`       | City code, e.g., `110000`        |

**Common Mistakes**:
- ❌ Using `--spec.category=CCE` → API returns "invalid category"
- ❌ Using `--spec.category=AttachedCluster` → API returns "invalid category"
- ❌ Using `--spec.provider=huawei_cloud` (with underscore) → causes registration failure
- ❌ Using `--spec.type=CCE` (uppercase) → causes registration failure
- ❌ Using `--spec.city=Beijing` (city name) → should use city code like `110000`

**How to Find Correct Values**: Use `ListManagedClusters` to view unimported clusters with their correct parameter values before registration:

```bash
hcloud UCS ListManagedClusters --cli-region=cn-north-4
```

The response includes `spec.category`, `spec.provider`, `spec.type`, `spec.city`, and `spec.projectID` fields that should be used exactly as-is in the `RegisterCluster` command.

**Solution**: Always use the verified parameter values:

```bash
# CCE cluster registration (verified correct)
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=my-cce-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=cce --spec.manageType=grouped --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4

# Self-managed cluster registration (verified category)
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=datacenter-k8s --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-content> --cli-region=cn-north-4
```

**Common City Codes** (for `--spec.city` parameter):

| City        | Code     |
| ----------- | -------- |
| Beijing     | `110000` |
| Shanghai    | `310000` |
| Guangzhou   | `440100` |
| Shenzhen    | `440300` |
| Chengdu     | `510100` |
| Hangzhou    | `330100` |

## Common Error Response Reference

| Error Code          | HTTP Status | Description                  | Recommended Action                    |
| ------------------- | ----------- | ---------------------------- | ------------------------------------- |
| `UCS.001`           | 400         | Invalid parameter            | Check parameter format and rules      |
| `UCS.002`           | 404         | Resource not found           | Verify resource exists first          |
| `UCS.003`           | 409         | Resource already exists      | Use Show operation to check           |
| `UCS.004`           | 403         | Permission denied            | Check IAM policies                    |
| `UCS.005`           | 403         | Quota exceeded               | Check quotas, clean up or apply       |
| `UCS.006`           | 401         | Authentication failed        | Regenerate or check credentials       |
| `UCS.007`           | 429         | Too many requests            | Add delay, reduce request rate        |
| `UCS.008`           | 400         | Invalid kubeconfig           | Verify kubeconfig format and validity |