# Verification Method - UCS Policy Governor Skill

## Overview

This document defines the verification steps for the UCS Policy Governor skill. Verification is divided into three levels: installation verification, configuration verification, and functional verification.

## Level 1: Installation Verification

### 1.1 hcloud CLI Installation

| Item                 | Command           | Success Criteria                          |
| -------------------- | ------------------ | ----------------------------------------- |
| hcloud installed     | `hcloud version`   | Returns version number >= 7.2.2           |

### 1.2 hcloud CLI First Run

```bash
# Accept privacy statement (first time only)
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
# Test API connectivity with a read-only operation
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4
```

Expected: Returns HTTP 200 and list of policy definitions.

## Level 3: Functional Verification

### 3.1 Policy Definition Query

```bash
# List all policy definitions (read-only, no filter params)
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4
```

Expected: Displays list of available policy definitions.

```bash
# Show a specific policy definition
hcloud UCS ShowPolicyDefinition --policydefinitionid=<definition-id> --cli-region=cn-north-4
```

Expected: Returns definition details including parameters and checks.

### 3.2 Policy Instance Management (Cluster-Level)

```bash
# Create a cluster-level test policy instance
hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-cluster-id> --constraintTemplateID=<template-id> --enforcementAction=warn --parameters='{"maxReplicas":"3"}' --cli-region=cn-north-4
```

Expected: Policy instance created successfully.

```bash
# Show policy instance details
hcloud UCS ShowPolicyInstance --policyinstanceid=<instance-id-from-response> --cli-region=cn-north-4
```

Expected: Returns policy instance details with status.

```bash
# Update policy instance
hcloud UCS UpdatePolicyInstance --policyinstanceid=<instance-id> --enforcementAction=deny --cli-region=cn-north-4
```

Expected: Policy instance updated successfully.

### 3.3 Policy Instance Management (Fleet Group-Level)

```bash
# Create a fleet group-level test policy instance
hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<fleet-group-id> --constraintTemplateID=<template-id> --enforcementAction=warn --cli-region=cn-north-4
```

Expected: Policy instance created successfully.

### 3.4 Policy Enforcement (Cluster)

```bash
# Enable policy on cluster
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Policy enforcement enabled, enforcement job created.

```bash
# Disable policy on cluster (for testing)
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
```

Expected: Policy enforcement suspended.

```bash
# Re-enable policy on cluster with retry
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --retry=true --cli-region=cn-north-4
```

Expected: Policy enforcement resumed.

### 3.5 Policy Enforcement (Fleet Group)

```bash
# Enable policy on fleet group
hcloud UCS EnableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4
```

Expected: Policy enforcement enabled across fleet group.

```bash
# Disable policy on fleet group
hcloud UCS DisableClusterGroupPolicy --clustergroupid=<fleet-group-id> --cli-region=cn-north-4
```

Expected: Policy enforcement suspended across fleet group.

### 3.6 Enforcement Job Status

```bash
# List policy enforcement jobs
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

Expected: Returns list of enforcement jobs with status.

```bash
# Show specific enforcement job details
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4
```

Expected: Returns detailed job information including status and any violations.

### 3.7 List Policy Instances

```bash
# List all policy instances (no filter params available)
hcloud UCS ListPolicyInstances --cli-region=cn-north-4
```

Expected: Displays list of all policy instances.

### 3.8 Clean Up

```bash
# Delete test policy instance (CAUTION: irreversible)
hcloud UCS DeletePolicyInstance --policyinstanceid=<instance-id> --cli-region=cn-north-4
```

Expected: Policy instance deleted successfully.

```bash
# Verify deletion
hcloud UCS ListPolicyInstances --cli-region=cn-north-4
```

Expected: Test policy no longer appears in list.

## Verification Checklist

| #  | Check Item                | Command                                             | Status |
| -- | ------------------------- | --------------------------------------------------- | ------ |
| 1  | hcloud version >= 7.2.2   | `hcloud version`                                    | ☐      |
| 2  | Credentials configured    | `hcloud configure list`                             | ☐      |
| 3  | API connectivity          | `hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4` | ☐ |
| 4  | List policy definitions   | `hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4` | ☐ |
| 5  | Show policy definition    | `hcloud UCS ShowPolicyDefinition --policydefinitionid=<id> --cli-region=cn-north-4` | ☐ |
| 6  | Create cluster policy     | `hcloud UCS CreateClusterPolicyInstance --clusterid=<ucs-id> --constraintTemplateID=<tid> --enforcementAction=warn --cli-region=cn-north-4` | ☐ |
| 7  | Create fleet group policy | `hcloud UCS CreateClusterGroupPolicyInstance --clustergroupid=<gid> --constraintTemplateID=<tid> --enforcementAction=warn --cli-region=cn-north-4` | ☐ |
| 8  | Show policy instance      | `hcloud UCS ShowPolicyInstance --policyinstanceid=<id> --cli-region=cn-north-4` | ☐ |
| 9  | Update policy instance    | `hcloud UCS UpdatePolicyInstance --policyinstanceid=<id> --enforcementAction=deny --cli-region=cn-north-4` | ☐ |
| 10 | Enable cluster policy     | `hcloud UCS EnableClusterPolicy --clusterid=<ucs-id> --cli-region=cn-north-4` | ☐ |
| 11 | Disable cluster policy    | `hcloud UCS DisableClusterPolicy --clusterid=<ucs-id> --cli-region=cn-north-4` | ☐ |
| 12 | Enable fleet group policy | `hcloud UCS EnableClusterGroupPolicy --clustergroupid=<gid> --cli-region=cn-north-4` | ☐ |
| 13 | Disable fleet group policy| `hcloud UCS DisableClusterGroupPolicy --clustergroupid=<gid> --cli-region=cn-north-4` | ☐ |
| 14 | List policy jobs          | `hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4` | ☐ |
| 15 | Show policy job           | `hcloud UCS ShowPolicyJob --jobid=<jid> --cli-region=cn-north-4` | ☐ |
| 16 | List policy instances     | `hcloud UCS ListPolicyInstances --cli-region=cn-north-4` | ☐ |
| 17 | Delete policy instance    | `hcloud UCS DeletePolicyInstance --policyinstanceid=<id> --cli-region=cn-north-4` | ☐ |