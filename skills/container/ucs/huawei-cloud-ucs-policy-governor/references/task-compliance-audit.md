# Task: Compliance Audit

## Overview

UCS compliance audit enables fleet-wide governance monitoring by reviewing policy enforcement job status, identifying violations, and tracking compliance across managed clusters. This task covers checking enforcement job status, violation review, and audit reporting using `ListPolicyJobs` and `ShowPolicyJob` (replacing the non-existent `GetPolicyAssignment` operation).

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                    |
| ------------------ | ------ | ------------------------ | --------------------------------- |
| `ListPolicyJobs`   | GET    | 列出策略执行任务         | `--kind` (optional, default "EnablePolicy") |
| `ShowPolicyJob`    | GET    | 获取策略执行任务详情     | `--jobid` (required)              |
| `ListPolicyInstances` | GET  | 列出策略实例             | `--cli-region` only (no filter params) |
| `ShowPolicyInstance`  | GET  | 获取策略实例详情         | `--policyinstanceid`              |

## Workflows

### W1: Fleet-Level Compliance Audit

Audit compliance across all clusters in a fleet group:

```bash
# 1. List all policy instances for the fleet group
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# 2. Check enforcement job status across the fleet
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

**Policy Job Response Fields**:
- `jobid`: Enforcement job UUID
- `kind`: Job type (e.g., `EnablePolicy`)
- `status`: Job execution status (`Success`, `Failed`, `InProgress`)

**Audit Checklist**:
- ✅ All jobs show `status: Success` — Policy enforcement deployed successfully
- ⚠️ Some jobs show `status: Failed` — Investigate specific failures with `ShowPolicyJob`
- ❌ Many jobs show `status: Failed` — Systemic issue, requires immediate action

### W2: Cluster-Level Compliance Review

Review enforcement status for a specific cluster:

```bash
# 1. List all policy instances
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# 2. Check enforcement jobs for the cluster
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# 3. Show specific job details for deeper inspection
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4
```

**Job Status Values**:
- `Success`: Policy enforcement deployed successfully, compliance checks active
- `Failed`: Policy enforcement failed, check job details for error information
- `InProgress`: Policy enforcement being deployed, compliance check pending

### W3: Violation Analysis

When violations are detected, analyze the details:

```bash
# List enforcement jobs to find relevant job
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# Show specific job details for violation information
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4
```

**Violation Details**:
Each failed or partially successful enforcement job includes violation information. UCS responses follow k8s-style format based on verified ListPolicyDefinitions/ListPolicyJobs patterns:

```json
[to be verified for populated response — verified empty ListPolicyJobs returns { "items": null }]
```

The exact violation detail structure has not been verified. Based on verified k8s-style UCS responses, violation information is likely in a structured `status.conditions` or similar field rather than flat fields like `jobid`, `kind`, `details.cluster_id`, `details.violations`.

**Violation Resolution Steps**:
1. Review each violation description from `ShowPolicyJob`
2. Identify the affected Kubernetes resource (namespace, deployment, pod)
3. Apply the required fix on the cluster
4. Re-enable the policy to trigger a fresh enforcement job
5. Verify the job status changes to `Success`

### W4: Cross-Fleet Compliance Comparison

Compare enforcement status across different fleet groups:

```bash
# 1. List all policy instances
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# 2. List all enforcement jobs
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# 3. Show specific job details for each fleet group
hcloud UCS ShowPolicyJob --jobid=<production-job-id> --cli-region=cn-north-4
hcloud UCS ShowPolicyJob --jobid=<staging-job-id> --cli-region=cn-north-4
hcloud UCS ShowPolicyJob --jobid=<development-job-id> --cli-region=cn-north-4
```

**Comparison Framework**:

| Fleet Group | Policy | Job Status | Violations | Notes |
|-------------|--------|------------|------------|-------|
| Production  | Security Baseline | Failed | 1 cluster | Investigate failing cluster |
| Staging     | Security Baseline | Success | 0 | All clusters compliant |
| Development | Security Baseline | InProgress | TBD | Enforcement being deployed |

### W5: Compliance Trend Tracking

Track enforcement job status over time by periodically auditing:

```bash
# Audit 1: Initial baseline
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# Audit 2: After remediation
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# Audit 3: Verify sustained compliance
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
```

**Key Metrics to Track**:
- Job `status` trend (Success vs Failed vs InProgress)
- Violation details from `ShowPolicyJob`
- New failed jobs appearing (regression detection)
- Job completion timestamps

### W6: Remediation Workflow

When violations are detected, follow this remediation workflow:

```bash
# 1. Identify violation details
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4

# 2. Access the cluster with kubeconfig
hcloud UCS CreateClusterKubeconfig --clusterid=<ucs-cluster-id> --cli-region=cn-north-4 > cluster-kubeconfig.yaml

# 3. Fix violations using kubectl
kubectl --kubeconfig=cluster-kubeconfig.yaml apply -f <fix-manifest>

# 4. Re-trigger enforcement
hcloud UCS DisableClusterPolicy --clusterid=<ucs-cluster-id> --cli-region=cn-north-4
hcloud UCS EnableClusterPolicy --clusterid=<ucs-cluster-id> --retry=true --cli-region=cn-north-4

# 5. Verify remediation
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
hcloud UCS ShowPolicyJob --jobid=<new-job-id> --cli-region=cn-north-4
```

Expected: Job status changes from `Failed` to `Success`.

## Common Scenarios

### S1: Production Fleet Compliance Report

Generate a complete compliance report for the production fleet:

```bash
# 1. List all policy instances
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# 2. List all enforcement jobs
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# 3. For each job, show detailed status
for jobid in <job-ids>; do
  echo "=== Policy Job: $jobid ==="
  hcloud UCS ShowPolicyJob --jobid=$jobid --cli-region=cn-north-4
done

# 4. Identify all failed jobs
# 5. Create remediation plan
```

### S2: New Cluster Compliance Validation

When a new cluster joins the fleet, verify it meets compliance standards:

```bash
# 1. Register the new cluster
hcloud UCS RegisterCluster --name=new-cluster --cluster_type=CCE --cluster_id=<cce-id> --cli-region=cn-north-4

# 2. Enable policy on the new cluster
hcloud UCS EnableClusterPolicy --clusterid=<new-ucs-id> --cli-region=cn-north-4

# 3. Check enforcement job status
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4

# 4. If job failed, remediate before deploying production workloads
```

### S3: Compliance Audit for Regulatory Review

For regulatory compliance reviews, document the full audit trail:

```bash
# 1. List all policy definitions
hcloud UCS ListPolicyDefinitions --cli-region=cn-north-4

# 2. List all policy instances
hcloud UCS ListPolicyInstances --cli-region=cn-north-4

# 3. List all enforcement jobs for compliance evidence
hcloud UCS ListPolicyJobs --kind=EnablePolicy --cli-region=cn-north-4

# 4. Show detailed job information for each
hcloud UCS ShowPolicyJob --jobid=<job-id> --cli-region=cn-north-4

# 5. Document job status and violation details
# 6. Record remediation actions taken
# 7. Retain job timestamps for audit trail
```