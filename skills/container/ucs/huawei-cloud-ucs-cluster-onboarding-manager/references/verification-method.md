# Verification Method - UCS Cluster Onboarding Manager Skill

## Overview

This document defines the verification steps for the UCS Cluster Onboarding Manager skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

## Level 1: Installation Verification

### 1.1 hcloud CLI Installation

| Item                 | Command           | Success Criteria                          |
| -------------------- | ------------------ | ----------------------------------------- |
| hcloud installed     | `hcloud version`   | Returns version number >= 7.2.2           |
| kubectl installed    | `kubectl version`  | Returns Kubernetes client version (optional for kubeconfig validation) |

### 1.2 hcloud CLI First Run

```bash
printf "y\n" | hcloud version
```

Expected: Version number displayed without error.

## Level 2: Configuration Verification

### 2.1 Credential Configuration

| Item                    | Command                | Success Criteria                        |
| ----------------------- | ---------------------- | --------------------------------------- |
| Credentials configured  | `hcloud configure list` | Shows valid AK/SK configuration (values masked) |

✅ **Correct**: Use `hcloud configure list` to verify
❌ **Incorrect**: Do NOT use `echo $HUAWEI_CLOUD_AK` to check credentials

### 2.2 Connectivity Test

```bash
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and quota information.

## Level 3: Functional Verification

### 3.1 Cluster Listing

```bash
hcloud UCS ShowClusterList --cli-region=cn-north-4
```

Expected: Displays list of UCS-managed clusters (may be empty).

### 3.2 Cluster Registration (CCE)

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=test-verify-cluster --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-cluster-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4
```

Expected: Cluster registered successfully, returns UCS cluster ID.

```bash
hcloud UCS ShowCluster --clusterid=<ucs-cluster-id-from-response> --cli-region=cn-north-4
```

Expected: Returns cluster details with status transitioning to `Available`.

### 3.3 Cluster Registration (Self-Managed)

```bash
hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=test-self-managed --spec.category=onpremise --spec.provider=self_managed --spec.type=Kubernetes --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.annotations.kubeconfig=<kubeconfig-content> --cli-region=cn-north-4
```

Expected: Cluster registered successfully.

### 3.4 Cluster Update

```bash
hcloud UCS UpdateCluster --clusterid=<ucs-cluster-id> --apiVersion=v1 --kind=Cluster --spec.city=Shanghai --cli-region=cn-north-4
```

Expected: Cluster updated successfully.

### 3.5 Fleet Group Management

```bash
hcloud UCS RegisterClusterGroup --metadata.name=test-verify-group --spec.description="Verification test group" --cli-region=cn-north-4
```

Expected: Fleet group created successfully, returns group ID.

```bash
hcloud UCS ShowClusterGroup --clustergroupid=<group-id-from-response> --cli-region=cn-north-4
```

Expected: Returns group details.

```bash
hcloud UCS ListClusterGroup --cli-region=cn-north-4
```

Expected: Returns list of fleet groups including the test group.

```bash
hcloud UCS DeleteClusterGroup --clustergroupid=<group-id-from-response> --cli-region=cn-north-4
```

Expected: Fleet group deleted successfully.

### 3.6 Kubeconfig & Access

> ⚠️ **ShowClusterAccessInfo only works for `category=onpremise` clusters** (verified: returns `UCS.01030011`). For `category=self` (CCE) clusters, skip this step and use CCE API `CreateKubernetesClusterCert` to get kubeconfig.

```bash
hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Returns cluster access information with API server endpoint (onpremise only). For CCE clusters, this will return "Cluster category not supported".

```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Returns kubeconfig content.

### 3.7 Quota Check

```bash
hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
```

Expected: Returns quota information with limits and current usage.

### 3.8 Clean Up

```bash
hcloud UCS DeleteCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Cluster deregistered successfully.

```bash
hcloud UCS ShowClusterList --cli-region=cn-north-4
```

Expected: Test cluster no longer appears in list.

## Verification Checklist

| #  | Check Item                | Command                                             | Status |
| -- | ------------------------- | --------------------------------------------------- | ------ |
| 1  | hcloud version >= 7.2.2   | `hcloud version`                                    | ☐      |
| 2  | Credentials configured    | `hcloud configure list`                             | ☐      |
| 3  | API connectivity          | `hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4` | ☐ |
| 4  | List managed clusters     | `hcloud UCS ShowClusterList --cli-region=cn-north-4`| ☐      |
| 5  | Register CCE cluster      | `hcloud UCS RegisterCluster --apiVersion=v1 --kind=Cluster --metadata.name=test-verify --spec.category=self --spec.provider=huaweicloud --spec.type=turbo --spec.manageType=discrete --spec.country=CN --spec.city=110000 --metadata.uid=<cce-id> --spec.projectID=<project-id> --spec.region=cn-north-4 --cli-region=cn-north-4` | ☐ |
| 6  | Show cluster details      | `hcloud UCS ShowCluster --clusterid=<ucs-id> --cli-region=cn-north-4` | ☐ |
| 7  | Update cluster            | `hcloud UCS UpdateCluster --clusterid=<ucs-id> --apiVersion=v1 --kind=Cluster --spec.city=Shanghai --cli-region=cn-north-4` | ☐ |
| 8  | Show cluster access       | `hcloud UCS ShowClusterAccessInfo --clusterid=<ucs-id> --cli-region=cn-north-4` | ☐ |
| 9  | Create fleet group        | `hcloud UCS RegisterClusterGroup --metadata.name=test-verify-group --cli-region=cn-north-4` | ☐ |
| 10 | Show fleet group          | `hcloud UCS ShowClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4` | ☐ |
| 11 | List fleet groups         | `hcloud UCS ListClusterGroup --cli-region=cn-north-4` | ☐ |
| 12 | Create cluster kubeconfig | `hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-id> --cli-region=cn-north-4` | ☐ |
| 13 | Check quotas              | `hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4` | ☐ |
| 14 | Delete fleet group        | `hcloud UCS DeleteClusterGroup --clustergroupid=<group-id> --cli-region=cn-north-4` | ☐ |
| 15 | Deregister cluster        | `hcloud UCS DeleteCluster --clusterid=<ucs-id> --cli-region=cn-north-4` | ☐ |

## Level 4: Failure Scenario Troubleshooting

The previous verification levels cover the happy path. This section covers common failure scenarios and their troubleshooting workflows.

### 4.1 Registration Fails with UCS.01030012 (Version Not Supported)

**Scenario**: `RegisterCluster` returns `UCS.01030012: Register cce cluster error - cce cluster version not support in UCS service`.

**Troubleshooting Flow**:
```
UCS.01030012 on RegisterCluster
├── Step 1: Verify credentials are valid
│   └── hcloud UCS ShowQuota --domainid=<account-id> --cli-region=cn-north-4
│       ├── Success → Credentials OK, go to Step 2
│       └── Fail → Credential issue, reconfigure AK/SK
├── Step 2: Check K8s version compatibility
│   └── hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4
│       ├── Cluster version not in list → Version incompatibility (root cause found)
│       └── Cluster version in list → Go to Step 3
└── Step 3: Check K8s version compatibility
    └── hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4
    └── Compare cluster version with supported versions list
        └── Read error message for specific root cause
```

### 4.2 Cluster Status Stuck in Registering

**Scenario**: Cluster remains in `Registering` status for an extended period after registration.

**Troubleshooting Flow**:
```
Status stuck in "Registering"
├── Step 1: Check cluster details
│   └── hcloud UCS ShowCluster --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
├── Step 2: Check K8s version compatibility
│   └── hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4
│   └── Compare cluster version with supported versions
│       ├── Returns specific error → Address root cause
│       └── Status transitions to Available → Issue resolved
└── Step 3: If still stuck, check:
    ├── K8s version compatibility (query ListRegisteredClusterVersions)
    ├── Project ID correctness (from ListManagedClusters)
    └── Region match (--cli-region matches CCE cluster region)
```

### 4.3 ShowClusterAccessInfo Returns "Cluster category not supported"

**Scenario**: `ShowClusterAccessInfo` returns error for a CCE cluster.

**Root Cause**: `ShowClusterAccessInfo` only applies to `category=onpremise` clusters.

**Solution**: For `category=self` (CCE) clusters, use `CreateClusterKubeconfig` directly:
```bash
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

### 4.4 Project ID Invalid or Not Found

**Scenario**: Registration fails due to incorrect `--spec.projectID` value.

**Troubleshooting Flow**:
```
Project ID issue
└── Retrieve correct project ID from ListManagedClusters:
    └── hcloud UCS ListManagedClusters --unimported=true --cli-region=cn-north-4
        └── Use the spec.projectID value from the response for RegisterCluster
```

### 4.5 Version Incompatibility Confirmation

**Scenario**: Need to confirm whether K8s version is the root cause of registration failure.

**Troubleshooting Flow**:
```
Confirm version incompatibility
├── Step 1: List unimported clusters with versions
│   └── hcloud UCS ListManagedClusters --unimported=true --cli-region=cn-north-4
├── Step 2: Compare cluster version with UCS supported versions
│   └── hcloud UCS ListRegisteredClusterVersions --cli-region=cn-north-4
│       ├── Cluster version not in list → Version incompatibility confirmed
│       └── Cluster version in list → Version is NOT the issue
└── Step 3: If incompatible, either:
    ├── Downgrade CCE cluster K8s version to one in the supported list, OR
    └── Wait for UCS to support the newer version
```