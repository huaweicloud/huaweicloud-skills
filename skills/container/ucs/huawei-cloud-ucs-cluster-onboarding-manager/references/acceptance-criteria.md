# Acceptance Criteria

Acceptance standards and test checklist for this skill.

## 1. Environment Preparation

- [ ] hcloud CLI is installed (`hcloud --version` returns a version number)
- [ ] AK/SK credentials are configured (`hcloud UCS ShowQuota --domainid=<id> --cli-region=cn-north-4` succeeds)
- [ ] Target CCE cluster is created and status is `Available`

## 2. Version Compatibility Verification

- [ ] `hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4` returns version list
- [ ] CCE cluster K8s version is in the UCS supported version list
- [ ] If version is not in the list, registration returns `UCS.01030012` error (not 401)

## 3. CCE Cluster Registration

- [ ] `RegisterCluster` with `--spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete` succeeds
- [ ] `ShowCluster` returns cluster status `Available`
- [ ] `ShowClusterList --category=self` lists registered CCE clusters
- [ ] `ListManagedClusters` returns CCE cluster list with `category=self`, `type=turbo`

## 4. Self-Managed Cluster Registration

- [ ] `RegisterCluster` with `--spec.category=onpremise --spec.provider=self_managed` succeeds
- [ ] `ShowClusterAccessInfo` returns proxy-agent access info (only for onpremise)
- [ ] Cluster status becomes `Available` after proxy-agent deployment

## 5. API Applicability Verification

- [ ] `ShowClusterAccessInfo` on CCE cluster (category=self) returns `UCS.01030011`
- [ ] `RetryClusterActivation` on CCE cluster (category=self) returns `UCS.01000011`
- [ ] `CreateClusterKubeconfig` on CCE cluster returns internal error (use CCE `CreateKubernetesClusterCert` instead)

## 6. Fleet Group Management

- [ ] `RegisterClusterGroup` successfully creates a fleet group
- [ ] `JoinGroup` adds a cluster to the fleet group
- [ ] `ShowClusterGroup` returns info including joined clusters
- [ ] `LeaveGroup` removes a cluster from the fleet group
- [ ] `DeleteClusterGroup` successfully deletes the fleet group (requires user confirmation)

## 7. Kubeconfig Retrieval

- [ ] CCE cluster: Obtain kubeconfig via CCE API `CreateKubernetesClusterCert`
- [ ] Third-party cluster: Obtain kubeconfig via UCS `CreateClusterKubeconfig` (requires proxy-agent first)
- [ ] Retrieved kubeconfig can be verified with `kubectl --kubeconfig=<path> cluster-info`

## 8. Write Operation Safety

- [ ] `DeleteCluster` has user confirmation step before execution
- [ ] `UpdateCluster` has user confirmation step before execution
- [ ] `DeleteClusterGroup` has user confirmation step before execution
- [ ] `UpdateClusterGroup` has user confirmation step before execution

## 9. Deregister Cluster

- [ ] `DeleteCluster` successfully deregisters cluster (requires user confirmation)
- [ ] After deregistration, `ShowCluster` returns 404
- [ ] After deregistration, UCS policy governance stops taking effect

## 10. Error Handling

- [ ] Version incompatibility returns `UCS.01030012` (not 401 Unauthorized)
- [ ] Duplicate registration returns 409 Conflict
- [ ] Cluster not found returns 404 Not Found
- [ ] Insufficient permissions returns 403 Forbidden
- [ ] Quota exceeded returns 403 Quota exceeded
