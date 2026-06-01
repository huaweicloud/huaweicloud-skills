# UCS Policy API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud UCS (Universal Cloud Service) policy governance operations using hcloud CLI. All commands follow the standard format: `hcloud UCS <Operation> --param=value --cli-region=<region>`.

## Authentication

### Environment Variables

```bash
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
```

### hcloud CLI Configuration

```bash
# Interactive configuration
hcloud configure

# Verify configuration (safe - does not expose values)
hcloud configure list
```

✅ **Correct**: Use `hcloud configure list` to verify credentials
❌ **Incorrect**: Never use `echo $HUAWEI_CLOUD_AK` to check credentials

## Policy Instance Operations

### 1. Create Cluster Policy Instance

```bash
# Create a cluster-level policy instance
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --enforcementAction=deny --namespaces.1=default --namespaces.2=production --parameters='{"maxReplicas":"3"}' --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required, path): Target UCS cluster ID
- `--constraintTemplateID` (optional, body): Constraint template ID to reference
- `--enforcementAction` (optional, body): Enforcement action, values: `warn` or `deny`
- `--namespaces.[N]` (optional, body array): Target namespaces, indexed from 1
- `--parameters` (optional, body object): Policy parameters as JSON object string
- `--cli-region` (required): Region ID

**Important**: This operation creates a policy instance scoped to a single cluster. For fleet group-level policies, use `CreateClusterGroupPolicyInstance` instead.

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ShowClusterList/ListPolicyDefinitions patterns]:

UCS API returns Kubernetes-style objects, not flat JSON. Based on verified `ShowClusterList` and `ListPolicyDefinitions` responses, `CreateClusterPolicyInstance` likely returns a k8s-style object with `kind`, `apiVersion`, `metadata`, `spec`, and `status` fields rather than flat fields like `id`, `constraintTemplateID`, `enforcementAction`.

**Key Fields** (expected, format to be verified):
- Instance UUID: Likely in `metadata.uid` (not flat `id`)
- Constraint template reference: Likely in `spec.constraintTemplateID`
- Enforcement action: Likely in `spec.enforcementAction` (`warn` or `deny`)
- Status: Likely in `status.phase` (`Enabled`, `Disabled`, `Pending`)

### 2. Create Cluster Group Policy Instance

```bash
# Create a fleet group-level policy instance
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<template-id> --enforcementAction=warn --parameters='{"cpuLimit":"2"}' --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required, path): Target fleet group ID
- `--constraintTemplateID` (optional, body): Constraint template ID to reference
- `--enforcementAction` (optional, body): Enforcement action, values: `warn` or `deny`
- `--namespaces.[N]` (optional, body array): Target namespaces, indexed from 1
- `--parameters` (optional, body object): Policy parameters as JSON object string
- `--cli-region` (required): Region ID

**Important**: This operation creates a policy instance scoped to a fleet group. For cluster-level policies, use `CreateClusterPolicyInstance` instead.

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ShowClusterList/ListPolicyDefinitions patterns]:

UCS API returns Kubernetes-style objects, not flat JSON. Based on verified responses, `CreateClusterGroupPolicyInstance` likely returns a k8s-style object with `kind`, `apiVersion`, `metadata`, `spec`, and `status` fields rather than flat fields.

### 3. Update Policy Instance

```bash
hcloud UCS UpdatePolicyInstance --policyinstanceid=<instance-id> --enforcementAction=deny --parameters='{"cpuLimit":"4"}' --cli-region=cn-north-4
```

**Parameters**:
- `--policyinstanceid` (required, path): Policy instance UUID
- `--constraintTemplateID` (optional, body): New constraint template ID
- `--enforcementAction` (optional, body): New enforcement action (`warn` or `deny`)
- `--namespaces.[N]` (optional, body array): New target namespaces
- `--parameters` (optional, body object): New policy parameters as JSON object string
- `--cli-region` (required): Region ID

**Note**: You cannot change the target scope (`clusterid`/`clustergroupid`) after creation. To change the scope, delete the instance and create a new one.

### 4. Show Policy Instance Details

```bash
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
```

**Parameters**:
- `--policyinstanceid` (required, path): Policy instance UUID
- `--cli-region` (required): Region ID

**Response**: Returns full policy instance details including status, template reference, and target scope.

### 5. Delete Policy Instance

```bash
hcloud UCS DeletePolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
```

**Parameters**:
- `--policyinstanceid` (required, path): Policy instance UUID
- `--cli-region` (required): Region ID

⚠️ **Warning**: Deleting a policy instance permanently removes the enforcement configuration. Violations will no longer be checked. Consider disabling the policy first before deleting.

### 6. List Policy Instances

```bash
# List all policy instances (no filter parameters available)
hcloud UCS ListPolicyInstances --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Important**: `ListPolicyInstances` does NOT support filter parameters. The following parameters DO NOT EXIST: `--name`, `--cluster_id`, `--cluster_group_id`, `--limit`, `--offset`, `--status`. Only `--cli-region` is available. To find specific instances, list all and filter from the response.

**Response Example** (verified for empty result):

When no instances exist, returns `{ "items": null }`. When populated, likely k8s-style objects based on verified UCS pattern:

```json
{
  "items": null
}
```

[to be verified for populated response — likely k8s-style objects with `kind`, `apiVersion`, `metadata`, `spec`, `status` fields rather than flat fields like `id`, `constraintTemplateID`]

## Policy Definition Operations

### 1. List Policy Definitions

```bash
# List all available policy definitions (no filter parameters available)
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4
```

**Parameters**:
- `--cli-region` (required): Region ID

**Important**: `ListPolicyDefinitions` does NOT support filter parameters. The following parameters DO NOT EXIST: `--category`, `--limit`, `--offset`. Only `--cli-region` is available. To find definitions by category, list all and filter from the response.

**Response Example** (verified):

```json
{
  "items": [
    {
      "kind": "ConstraintTemplate",
      "apiVersion": "templates.gatekeeper.sh/v1beta1",
      "metadata": {
        "name": "k8srequiredresources",
        "uid": "3b900254-0086-11ee-924e-0255ac1000d3",
        "creationTimestamp": "2023-06-01T14:11:41Z",
        "annotations": {
          "name-chinese": "K8sRequiredResources",
          "tag-chinese": "集群安全策略",
          "description-chinese": "..."
        }
      },
      "spec": {
        "type": "general",
        "officialTag": "ClusterSecurityPolicies",
        "level": "1",
        "targetKind": "Pod",
        "official": true,
        "description": "Requires containers to have defined resources set...",
        "constraintTemplate": {
          "kind": "ConstraintTemplate",
          "apiVersion": "templates.gatekeeper.sh/v1",
          "metadata": { "name": "k8srequiredresources" },
          "spec": {
            "crd": {
              "spec": {
                "names": { "kind": "K8sRequiredResources" },
                "validation": { "openAPIV3Schema": { "properties": {} } }
              }
            },
            "targets": [
              {
                "target": "admission.k8s.gatekeeper.sh",
                "rego": "...",
                "libs": []
              }
            ]
          }
        }
      }
    }
  ]
}
```

**Key Fields**:
- `metadata.name`: Constraint template name (used as `constraintTemplateID` in CreateClusterPolicyInstance, not flat `id`) — this is the identifier you pass to `--constraintTemplateID`
- `metadata.uid`: Definition UUID
- `spec.officialTag`: Policy category/tag (not flat `category`) — values like `ClusterSecurityPolicies`
- `spec.level`: Severity level (not flat `severity`) — numeric string like `"1"`
- `spec.targetKind`: Target resource type (e.g., `Pod`)
- `spec.description`: Policy description
- `spec.constraintTemplate.spec.crd.spec.validation.openAPIV3Schema.properties`: Parameter definitions (not flat `parameters` array) — parameter types and defaults are defined in the OpenAPI V3 schema inside the constraint template CRD spec
- `spec.type`: Policy type (e.g., `general`)
- `spec.official`: Whether this is an official (built-in) policy

### 2. Show Policy Definition Details

```bash
hcloud UCS ShowPolicyDefinition --policydefinitionid=<definition-id> --cli-region=cn-north-4
```

**Parameters**:
- `--policydefinitionid` (required, path): Policy definition UUID
- `--cli-region` (required): Region ID

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ListPolicyDefinitions pattern]:

UCS API returns Kubernetes-style objects. Based on the verified `ListPolicyDefinitions` response (which returns ConstraintTemplate objects), `ShowPolicyDefinition` likely returns a single k8s-style ConstraintTemplate object with detailed `spec.constraintTemplate.spec.crd.spec.validation.openAPIV3Schema.properties` for parameter definitions.

## Policy Enforcement Operations

### 1. Enable Cluster Policy

```bash
# Enable a policy on a cluster (starts enforcement)
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4

# Enable with retry (for retrying a failed enforcement)
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --retry=true --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required, path): Target UCS cluster ID
- `--retry` (optional, query): Retry flag for re-attempting failed enforcement
- `--cli-region` (required): Region ID

### 2. Enable Cluster Group Policy

```bash
# Enable a policy on a fleet group (starts enforcement)
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4

# Enable with retry
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --retry=true --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required, path): Target fleet group ID
- `--retry` (optional, query): Retry flag for re-attempting failed enforcement
- `--cli-region` (required): Region ID

### 3. Disable Cluster Policy

```bash
# Disable a policy on a cluster (suspends enforcement)
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clusterid` (required, path): Target UCS cluster ID
- `--cli-region` (required): Region ID

**Effect**: Policy enforcement is suspended. Violations will not be checked while the policy is disabled. The policy instance configuration is preserved.

### 4. Disable Cluster Group Policy

```bash
# Disable a policy on a fleet group (suspends enforcement)
hcloud UCS DisableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4
```

**Parameters**:
- `--clustergroupid` (required, path): Target fleet group ID
- `--cli-region` (required): Region ID

## Policy Enforcement Job Operations

### 1. List Policy Jobs

```bash
# List all policy enforcement jobs
hcloud UCS ListPolicyJobs --cli-region=cn-north-4

# List enforcement jobs filtered by kind
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

**Parameters**:
- `--kind` (optional, query): Job type filter, default `EnablePolicy`
- `--cli-region` (required): Region ID

**Response Example** (verified for empty result):

When no jobs exist, returns `{ "items": null }`. When populated, likely k8s-style objects based on verified UCS pattern:

```json
{
  "items": null
}
```

[to be verified for populated response — likely k8s-style objects with `kind`, `apiVersion`, `metadata`, `spec`, `status` fields]

**Key Fields** (expected, format to be verified):
- Job UUID: Likely in `metadata.uid` (not flat `jobid`)
- Job type: Likely in `spec.kind` (`EnablePolicy`, etc.)
- Job status: Likely in `status.phase` (`Success`, `Failed`, `InProgress`)

### 2. Show Policy Job

```bash
# Show detailed policy enforcement job information
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4
```

**Parameters**:
- `--jobid` (required, path): Policy enforcement job UUID
- `--cli-region` (required): Region ID

**Response Example** [to be verified — UCS responses follow k8s-style format based on verified ListPolicyDefinitions/ListPolicyJobs patterns]:

UCS API returns Kubernetes-style objects. Based on verified responses, `ShowPolicyJob` likely returns a k8s-style object rather than flat fields like `jobid`, `kind`, `status`.

**Key Fields** (expected, format to be verified):
- Job UUID: Likely in `metadata.uid`
- Job type: Likely in `spec.kind` (`EnablePolicy`, etc.)
- Status: Likely in `status.phase` (`Success`, `Failed`, `InProgress`)
- Violation details: Likely in `status.conditions` or similar structured field

**Important**: `GetPolicyAssignment` does NOT exist as a UCS API operation. Use `ListPolicyJobs` and `ShowPolicyJob` to check policy enforcement status and compliance information.

## Common Region IDs

| Region Name                    | Region ID        |
| ------------------------------ | ---------------- |
| North China - Beijing 4        | `cn-north-4`     |
| North China - Beijing 1        | `cn-north-1`     |
| East China - Shanghai 1        | `cn-east-3`      |
| East China - Shanghai 2        | `cn-east-2`      |
| South China - Guangzhou        | `cn-south-1`     |
| South China - Shenzhen         | `cn-south-4`     |
| Southwest China - Guiyang 1    | `cn-southwest-2` |
| Asia Pacific - Bangkok         | `ap-southeast-2` |
| Asia Pacific - Singapore       | `ap-southeast-1` |
| Asia Pacific - Hong Kong       | `ap-southeast-3` |
| Europe - Paris                 | `eu-west-0`      |

## Common Errors

| Error                   | Cause                       | Solution                                        |
| ----------------------- | --------------------------- | ------------------------------------------------ |
| `InvalidAccessKeyId`    | Invalid AK/SK               | Check credential configuration via `hcloud configure list` |
| `PolicyDefinitionNotFound` | Template ID invalid      | Use `ListPolicyDefinitions` to find valid ID    |
| `PolicyInstanceNotFound` | Instance ID invalid        | Use `ListPolicyInstances` to verify ID          |
| `ClusterNotRegistered`  | Cluster not in UCS         | Register cluster with `ucs-cluster-onboarding-manager` |
| `GroupNotFound`         | Fleet group doesn't exist   | Verify group ID with `ShowClusterGroup`         |
| `QuotaExceeded`         | Policy instance limit       | Delete unused instances or request quota increase |
| `OperationNotFound`     | Wrong operation name        | Use correct scope-specific operation (e.g., CreateClusterPolicyInstance vs CreateClusterGroupPolicyInstance) |
| `RequestLimitExceeded`  | Too many requests           | Add delay between batch requests                 |

## Related Documentation

- [Huawei Cloud UCS Documentation](https://support.huaweicloud.com/ucs/index.html)
- [hcloud CLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)