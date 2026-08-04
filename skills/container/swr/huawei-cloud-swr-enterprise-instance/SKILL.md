---
id: huawei-cloud-swr-enterprise-instance
name: huawei-cloud-swr-enterprise-instance
description: |
  Huawei Cloud SWR enterprise instance management skill using hcloud CLI.
  Use this skill when the user wants to: (1) manage SWR enterprise instances - create/list/show/delete/update configuration, (2) manage instance namespaces - create/list/show/update/delete with security scanning settings, (3) manage instance registries (sync targets) - create/list/show/update/delete, (4) manage instance repositories - list/show/delete/update, (5) manage instance artifacts (image versions) - list/show/delete/scan, (6) manage instance credentials - long-term and temporary, (7) manage instance endpoints - internal/public access, (8) manage instance domains - add/list/show/delete/update, (9) check instance statistics and job status.
  Trigger: user mentions "SWR enterprise instance", "SWR 企业实例", "SWR 企业版", "企业仓库实例", "SWR instance", "SWR 专业版", "swr.ee", "instance namespace", "instance registry", "instance repository", "instance artifact", "instance credential", "instance endpoint", "instance domain", "企业仓库", "实例管理", "同步目标仓库", "sync target"
tags: [swr, enterprise-instance, container-registry, registry, domain]
---

# Huawei Cloud SWR Enterprise Instance Management

## Overview

This skill provides lifecycle management capabilities for Huawei Cloud SWR (Software Repository for Container) enterprise instances using the `hcloud` CLI. Enterprise instances provide dedicated, isolated container registry environments with advanced features like security scanning, replication policies, and custom domain support.

> **Note**: Some features mentioned above (e.g., replication policies) are managed via the SWR enterprise instance console, not through this skill's CLI commands. See the **Unsupported Operations** section below for details.

**Architecture**: hcloud CLI → SWR Service API → Instance/Namespace/Registry/Repository/Artifact/Credential/Endpoint/Domain resources

**Related Skills**:
- `huawei-cloud-swr-image-management` - Image lifecycle management (basic SWR namespaces, repos, tags, auth, quotas)
- `huawei-cloud-swr-image-governance` - Image governance (permissions, retention, sharing, tags, immutable rules)
- `huawei-cloud-swr-image-automation` - Image automation ops (sync, triggers, domains)

- Create and manage SWR enterprise instances
- Manage instance namespaces with security scanning and vulnerability blocking
- Configure instance registries for cross-instance image sync
- Query and manage instance repositories and artifacts
- Obtain instance access credentials (long-term and temporary)
- Configure instance network access (internal VPC endpoints, public access with whitelist)
- Manage custom domains for instance access
- Monitor instance statistics and job status

**Typical Use Cases**:

- "Create an SWR enterprise instance for my organization"
- "List all enterprise instances in my project"
- "Create a namespace with auto-scan and vulnerability blocking"
- "Configure a registry for syncing images to another instance"
- "List repositories and artifacts in my instance"
- "Get docker login credentials for my instance"
- "Add a VPC internal endpoint for my instance"
- "Enable public access with IP whitelist"
- "Add a custom domain to my instance"
- "Check instance statistics and resource usage"

## Prerequisites

### 1. hcloud CLI Requirements (MANDATORY)

- hcloud CLI installed (version >= 7.2.2)
- Run `hcloud version` to verify installation
- First-time usage: `printf "y\n" | hcloud version` to accept privacy statement

### 2. Credential Configuration

hcloud CLI supports two credential modes. See [references/credential-configuration.md](references/credential-configuration.md) for full details.

**Quick setup** (choose one):

```bash
# Mode A — Long-term AK/SK
export HUAWEI_CLOUD_AK=<your-ak>
export HUAWEI_CLOUD_SK=<your-sk>
export HUAWEI_CLOUD_REGION=cn-north-4

# Mode B — Temporary AK/SK + SecurityToken
export HUAWEI_CLOUD_AK=<your-temp-ak>
export HUAWEI_CLOUD_SK=<your-temp-sk>
export HUAWEI_CLOUD_SECURITY_TOKEN=<your-security-token>
export HUAWEI_CLOUD_REGION=cn-north-4
```

- **Security rules**: Never expose AK/SK/SecurityToken values. Use `hcloud configure list` to check presence only.

### 3. SWR Enterprise Service Activation (MANDATORY)

Before creating SWR enterprise instances, the user **must first activate the SWR enterprise service** in the Huawei Cloud console. This is a one-time enablement step per account/region.

**Activation Steps**:

1. Access the SWR enterprise instance console via direct URL: `https://console.huaweicloud.com/swr-instance`
   - **Important**: The SWR enterprise instance console is **not available from the main console navigation menu**. Users must use this direct URL to access it.
2. If prompted, review and accept the SWR enterprise service terms
3. Confirm the service is activated by verifying the console loads successfully
4. If activation is not available in the target region, the console will display an error or the service will not be listed

**Verification**: After activation, run `hcloud SWR ListInstance --cli-region=<region>` — if the service is activated, this returns an empty list (or existing instances). If not activated, an error will be returned.

**Console Access**:
- SWR Enterprise Instance Console: `https://console.huaweicloud.com/swr-instance`
- This URL provides access to instance management, namespace configuration, repository browsing, and replication policy setup
- The console is region-aware — select the target region in the top-right corner after opening the URL

### 4. IAM Permission Requirements

This skill requires SWR enterprise instance permissions (instance, namespace, registry, repository, artifact, credential, endpoint, domain, job, statistic operations). See [IAM Permission Policies](references/iam-policies.md) for the complete permission table and policy JSON.

**Permission Failure Handling**:

1. When any command fails due to permission errors, read `references/iam-policies.md`
2. Display the required permission list and policy JSON to the user
3. Guide the user to create a custom policy in the IAM console and grant authorization
4. Pause execution and wait for user confirmation that permissions have been granted

## Core Commands

### 1. Instance Lifecycle

See [Task: Instance Lifecycle](references/task-instance-lifecycle.md) for detailed workflows.

```bash
# Create an enterprise instance
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --cli-region=cn-north-4

# List all instances
hcloud SWR ListInstance --cli-region=cn-north-4

# List instances with status filter
hcloud SWR ListInstance --status=Running --cli-region=cn-north-4

# Show instance details
# Show instance details
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4

**Note**: `ShowInstance` does not return endpoint information. To view network access endpoints, use:
- `hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4` for internal VPC endpoints
- `hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4` for public access status and whitelist

# View instance configuration
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4

# Update instance configuration (anonymous access)
# Update instance configuration (anonymous access)
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4

**Configuration Scope**: `UpdateInstanceConfiguration` only supports the `--anonymous_access` parameter (boolean). This is the sole instance-level configuration option available via API. Other settings (spec, VPC, encryption) are set at creation time and cannot be modified afterward.

# Delete instance (CAUTION: removes all data permanently)
hcloud SWR DeleteInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

**Instance Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, or hyphens (`-`)
- No consecutive hyphens
- Cannot end with hyphen
- Length: 3-48 characters

**Instance Spec Options**: `swr.ee.basic` (basic edition), `swr.ee.professional` (professional edition)

**Spec and Region Availability**:
- Not all specs (flavors) are available in all regions. Before creating an instance, verify that the desired spec is supported in the target region.
- Use `hcloud SWR ListInstance --cli-region=<region>` to check if the SWR enterprise service is available in a region. If the API returns an error, the service may not be available in that region.
- Use `hcloud SWR ListSyncRegions --cli-region=<region>` to list regions where SWR service is available for cross-region sync.
- Common regions with SWR enterprise support include: `cn-north-4`, `cn-north-1`, `cn-east-3`, `cn-south-1`, `cn-east-2`, `cn-southwest-2`, `cn-north-9`, `ap-southeast-1`, `ap-southeast-2`, `ap-southeast-3`.
- If instance creation fails with spec/region errors, try a different spec or region. The error message will indicate if the spec is not supported in the target region.

**Billing Details**:
- **WARNING: Creating an SWR enterprise instance incurs hourly costs.** The user must be informed of this before proceeding.
- `--charge_mode`: Only `postPaid` (on-demand/pay-as-you-go) is supported. No prepaid or annual/monthly billing available.
- `--spec=swr.ee.basic`: Basic edition — suitable for small teams, limited features. Lower hourly cost.
- `--spec=swr.ee.professional`: Professional edition — full features including security scanning, replication, custom domains. Higher hourly cost.
- Costs are incurred per hour based on instance spec. No upfront payment required. Billing starts when the instance enters `Running` status.
- To stop billing: delete the instance with `hcloud SWR DeleteInstance`. Billing stops immediately after deletion.
- Use `--enterprise_project_id` to associate the instance with an enterprise project for cost tracking and attribution.
- For detailed pricing information, refer to the Huawei Cloud SWR pricing page or consult the SWR enterprise instance console at `https://console.huaweicloud.com/swr-instance`.

**Instance Status Values**: `Initial`, `Creating`, `Running`, `Unavailable`

### 2. Instance Namespaces

See [Task: Instance Namespaces](references/task-instance-namespaces.md) for detailed workflows.

```bash
# Create a namespace with auto-scan and vulnerability blocking
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=high --cli-region=cn-north-4

# List namespaces
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4

# List namespaces with filter
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --public=false --limit=20 --offset=0 --cli-region=cn-north-4

# Show namespace details
hcloud SWR ShowInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4

# Update namespace (change visibility, scan settings)
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=true --metadata.prevent_vul=false --cli-region=cn-north-4

# Delete namespace (CAUTION: removes all repositories under it)
hcloud SWR DeleteInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4
```

**Namespace Naming Rules**:
- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots, underscores, or hyphens
- Dots, underscores, hyphens cannot be directly connected
- End with lowercase letter or digit
- Length: 1-64 characters

**Vulnerability Severity Levels**: `none`, `low`, `medium`, `high`, `critical`

### 3. Instance Registries (Sync Targets)

See [Task: Instance Registries](references/task-instance-registries.md) for detailed workflows.

```bash
# Create a registry (sync target for another SWR enterprise instance)
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=target-instance --type=swr-pro-internal --url=<target-url> --credential.type=basic --credential.access_key=<ak> --credential.access_secret=<sk> --insecure=false --instance_id=<target-instance-id> --project_id=<target-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# Create a registry for open-source Harbor
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=harbor-target --type=swr-pro --url=https://harbor.example.com --credential.type=basic --credential.access_key=<username> --credential.access_secret=<password> --insecure=false --cli-region=cn-north-4

# List registries
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --cli-region=cn-north-4

# Show registry details
hcloud SWR ShowInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --cli-region=cn-north-4

# Update registry
hcloud SWR UpdateInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --name=new-name --url=<new-url> --credential.type=basic --credential.access_key=<new-ak> --credential.access_secret=<new-sk> --insecure=false --type=swr-pro --cli-region=cn-north-4

# Delete registry
hcloud SWR DeleteInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --cli-region=cn-north-4
```

**Registry Types**: `swr-pro` (open-source Harbor), `swr-pro-internal` (another SWR enterprise instance), `huawei-SWR` (basic SWR)

**Credential Acquisition for Target Registries**:
- For `swr-pro-internal` (another SWR enterprise instance): Use `CreateInstanceLtCredential` on the target instance to obtain `access_key` (credential name) and `access_secret` (credential password).
- For `huawei-SWR` (basic SWR): Use `CreateInstanceTempCredential` or basic SWR `CreateAuthorizationToken` to get temporary credentials.
- For `swr-pro` (Harbor): Use the Harbor account username and password.
- Credentials are stored securely by the instance and used for replication operations only.

### 4. Instance Repositories

See [Task: Instance Registries](references/task-instance-registries.md) for repository section.

```bash
# List repositories in instance
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --cli-region=cn-north-4

# List repositories with filter
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --namespace_id=<ns-id> --limit=20 --offset=0 --order_column=updated_at --order_type=desc --cli-region=cn-north-4

# Show repository details
hcloud SWR ShowInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# Update repository description
hcloud SWR UpdateInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --description="Updated description" --cli-region=cn-north-4

# Delete repository (CAUTION: removes all artifacts)
hcloud SWR DeleteInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

### 5. Instance Artifacts (Image Versions)

See [Task: Instance Artifacts](references/task-instance-artifacts.md) for detailed workflows.

```bash
# List artifacts in a repository
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# List artifacts with filter
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --type=IMAGE --limit=20 --offset=0 --cli-region=cn-north-4

# Show artifact details
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=<digest> --cli-region=cn-north-4

# Show artifact with scan overview
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=<digest> --with_scan_overview=true --cli-region=cn-north-4

# Get artifact build history
hcloud SWR ShowInstanceArtifactAddition --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=<digest> --addition=build_history --cli-region=cn-north-4

# List artifact vulnerabilities
hcloud SWR ListInstanceArtifactVulnerabilities --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=<digest> --cli-region=cn-north-4

# Start manual vulnerability scan
hcloud SWR StartManualScanning --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=<digest> --cli-region=cn-north-4

# Delete artifact (CAUTION: removes the image version permanently)
hcloud SWR DeleteInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=<digest> --cli-region=cn-north-4
```

**Artifact Types**: `IMAGE` (container image), `CHART` (Helm chart)

> ⚠️ **Image Vulnerability Scanning Limitation**: Image vulnerability scanning depends on Huawei Cloud HSS (Host Security Service). The current skill does not support HSS configuration or management. To use scanning features:
> - **Basic edition (`swr.ee.basic`)**: Scanning is not supported. Upgrade to professional edition.
> - **Professional edition (`swr.ee.professional`)**: Scanning requires HSS to be enabled. Please activate HSS in the Huawei Cloud console first, then use the SWR enterprise instance console (`https://console.huaweicloud.com/swr-instance`) to verify scanning is functional before relying on it in automation workflows.
> - If scanning fails on a professional edition instance, check HSS service status and ensure HSS is properly activated for the target region.

### 6. Instance Credentials

See [Task: Instance Credentials](references/task-instance-credentials.md) for detailed workflows.

```bash
# Create a long-term access credential
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=my-credential --cli-region=cn-north-4

# Create a temporary access credential
hcloud SWR CreateInstanceTempCredential --instance_id=<instance-id> --cli-region=cn-north-4

# List long-term credentials
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --cli-region=cn-north-4

# Enable/disable a long-term credential
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --enable=false --cli-region=cn-north-4

# Delete a long-term credential
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --cli-region=cn-north-4
```

**Credential Naming Rules** (same as namespace): lowercase/digit start, 1-64 chars

### 7. Instance Endpoints (Network Access)

See [Task: Instance Endpoints](references/task-instance-endpoints.md) for detailed workflows.

```bash
# Create internal VPC endpoint
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<vpc-id> --subnet_id=<subnet-id> --project_id=<vpc-project-id> --cli-region=cn-north-4

# List internal endpoints
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4

# Show internal endpoint details
hcloud SWR ShowInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4

# Delete internal endpoint
hcloud SWR DeleteInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4

# Enable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=true --cli-region=cn-north-4

# Disable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=false --cli-region=cn-north-4

# View public access status and whitelist
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4

# Update public access whitelist (full replacement)
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Internal network" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="VPN network" --cli-region=cn-north-4
```

### 8. Instance Domains

See [Task: Instance Domains](references/task-instance-domains.md) for detailed workflows.

```bash
# Add a custom domain
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=registry.example.com --certificate_id=<scm-cert-id> --cli-region=cn-north-4

# List all domains
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4

# Get domain overview
hcloud SWR ShowDomainOverview --cli-region=cn-north-4

# Delete a domain (default domain cannot be deleted)
hcloud SWR DeleteDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --cli-region=cn-north-4

# Update domain certificate
hcloud SWR UpdateDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --certificate_id=<new-cert-id> --cli-region=cn-north-4
```

### 9. Instance Statistics and Jobs

```bash
# Get instance statistics
hcloud SWR ListInstanceStatistics --instance_id=<instance-id> --cli-region=cn-north-4

# List instance jobs (async operations)
hcloud SWR ListInstanceJobs --cli-region=cn-north-4

# Show job details
hcloud SWR ShowInstanceJob --job_id=<job-id> --cli-region=cn-north-4

# Delete a job record
hcloud SWR DeleteInstanceJob --job_id=<job-id> --cli-region=cn-north-4
```

### 10. Instance Audit Logs

SWR enterprise instances provide built-in audit logging via `ListAuditLogs` API (pull/delete/create operations). No dependency on CTS required.

```bash
hcloud SWR ListAuditLogs --instance_id=<instance-id> --project_id=<project-id> --operation=pull --cli-region=cn-north-4
# --operation: pull, delete, or create; --limit/--offset for pagination
```

See [API Guide](references/swr-instance-api-guide.md#instance-audit-log-operations) for full details.

## Parameter Reference

See [Parameter Reference](references/parameter-reference.md) for complete parameter tables including: common parameters, instance creation (name, spec, VPC, subnet, encryption), namespace (public, auto_scan, prevent_vul, severity), registry (type, url, credential), and endpoint whitelist parameters.

## Output Format

See [Output Format](references/output-format.md) for detailed response format examples (Instance List, Instance Details, Namespace List, Internal Endpoint List, Domain Name List, Long-term Credential).

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Best Practices

1. **Instance naming & VPC**: Use descriptive names (`prod-instance`, `dev-instance`); choose VPC/subnet matching your workload environment
2. **Namespace security**: Enable `auto_scan=true` and `prevent_vul=true` for production; set `severity=high`/`critical` for prod, `none`/`low` for dev
3. **Credentials**: Store registry credentials securely and rotate periodically; use `CreateInstanceLtCredential` for CI/CD, `CreateInstanceTempCredential` for temp access
4. **Public access**: Always configure IP whitelist when enabling public access via `UpdateInstanceEndpointPolicy`; use SCM certificates for custom domain HTTPS
5. **Delete with caution**: Deleting an instance removes ALL data permanently; deleting a namespace removes ALL repositories
6. **Instance spec**: Use `swr.ee.basic` for small teams; `swr.ee.professional` for enterprise with advanced features

## 参数确认

| Operation | CLI Command | Risk Level | Confirmation Required |
| --------- | ----------- | ---------- | -------------------- |
| CreateInstance | `hcloud SWR CreateInstance` | High | Creating a paid instance incurs costs. Confirm instance spec (`swr.ee.basic` or `swr.ee.professional`), VPC/subnet configuration, and enterprise project before proceeding. |
| UpdateInstanceConfiguration | `hcloud SWR UpdateInstanceConfiguration --anonymous_access=true` | High | Enabling anonymous access allows unauthenticated users to pull images, reducing security. Confirm this is intended before proceeding. |
| CreateInstanceEndpointPolicy | `hcloud SWR CreateInstanceEndpointPolicy --enable=true` | Medium | Enabling public access exposes the instance to the internet. Must configure IP whitelist via `UpdateInstanceEndpointPolicy` to restrict access. Confirm before proceeding. |
| DeleteInstanceLtCredential | `hcloud SWR DeleteInstanceLtCredential` | Medium | Deleting a credential immediately revokes access for CI/CD pipelines using it. Recommend disabling the credential first (`UpdateInstanceLtCredential --enable=false`), verifying no active pipelines, then deleting. |
| CreateInstanceRegistry | `hcloud SWR CreateInstanceRegistry` | Medium | Creating a sync target registry stores the target registry authentication credentials (`access_key`/`access_secret`). Confirm the target registry URL and credential information before proceeding. |

## Unsupported Operations

The following operations are not supported by the SWR enterprise instance API and require alternative approaches:

| Unsupported Operation | Reason | Alternative Approach |
| -------------------- | ------ | ------------------- |
| Push images to instance | Docker CLI operation, not an API call | Use `CreateInstanceTempCredential` or `CreateInstanceLtCredential` to get credentials, then `docker login` and `docker push` |
| Pull images from instance | Docker CLI operation, not an API call | Use `CreateInstanceTempCredential` or `CreateInstanceLtCredential` to get credentials, then `docker login` and `docker pull` |
| Build images | SWR is a registry, not a build service | Use CodeArts Build, CCE, or local Docker build, then push to SWR |
| Image replication/sync policies | CLI available but not documented in this skill | Use `hcloud SWR CreateInstanceReplicationPolicy` / `ListInstanceReplicationPolicies` etc., or SWR enterprise instance console (`https://console.huaweicloud.com/swr-instance`) |
| Instance backup/restore | No backup API available | Use OBS bucket backup for data persistence, or migrate namespaces/repositories manually |
| Image retention/aging policies | CLI available but not documented in this skill | Use `hcloud SWR CreateInstanceRetentionPolicy` / `ListInstanceRetentionPolicies` etc., or SWR enterprise instance console |
| Webhook notification configuration | CLI available but not documented in this skill | Use `hcloud SWR CreateInstanceWebhook` / `ListInstanceWebhooks` etc., or SWR enterprise instance console |
| Image signing policies | CLI available but not documented in this skill | Use `hcloud SWR CreateInstanceSignPolicy` / `ListInstanceSignPolicies` etc., or SWR enterprise instance console |
| Resource tag management | CLI available but not documented in this skill | Use `hcloud SWR CreateInstanceResourceTags` / `ListInstanceResourceTags` etc., or TMS console |
| IAM delegation management | Not supported by this skill | Use IAM console to configure delegation. `CheckAgency`/`CreateAgency` in hcloud are for SWR→CCE/CCI direction, not enterprise instance delegation |

## 工作流

This skill follows a standard workflow for SWR enterprise instance management:

1. **Prerequisites Check** — Verify hcloud CLI installation and credential configuration
2. **Instance Identification** — List or show existing instances to obtain `instance_id`
3. **Operation Execution** — Execute the requested operation (create/update/delete/query)
4. **Result Verification** — Confirm the operation succeeded by querying the resulting state
5. **Credential Management** — For write operations, obtain and securely store any returned credentials
6. **Cleanup Confirmation** — For destructive operations, confirm with the user before proceeding

## KooCLI命令格式标准

All CLI commands use `hcloud SWR <Operation> --param1=value1 --cli-region=<region>` format.

**Key rules**: Use `--key=value` format, always specify `--cli-region`, never expose AK/SK, confirm before write operations, use `--cli-output=json` for structured output.

**Known CLI Limitation**: Some commands (CreateInstance, CreateInstanceInternalEndpoint, CreateInstanceRegistry) have same-name parameter conflicts between path and body. Use `--cli-jsonInput` with `path`/`body` sections to resolve. See [CLI Format Guide](references/cli-format-guide.md) for full details and examples.

## Reference Documents

| Document                                               | Description                              |
| ------------------------------------------------------ | ---------------------------------------- |
| [SWR Instance API Guide](references/swr-instance-api-guide.md) | hcloud SWR instance API reference |
| [Output Format](references/output-format.md)          | Response format examples (Instance, Namespace, Endpoint, Domain, Credential) |
| [Credential Configuration](references/credential-configuration.md) | Credential setup (long-term AK/SK & temporary AK/SK+SecurityToken) |
| [IAM Permission Policies](references/iam-policies.md)  | Required permissions and policy JSON     |
| [Verification Method](references/verification-method.md) | Step-by-step verification              |
| [Common Pitfalls](references/common-pitfalls.md)       | Troubleshooting guides                   |
| [Task: Instance Lifecycle](references/task-instance-lifecycle.md) | Instance create, list, show, update config |
| [Task: Instance Namespaces](references/task-instance-namespaces.md) | Namespace CRUD workflows |
| [Task: Instance Registries](references/task-instance-registries.md) | Registry CRUD and repositories |
| [Task: Instance Artifacts](references/task-instance-artifacts.md) | Artifact management and scanning |
| [Task: Instance Credentials](references/task-instance-credentials.md) | Credential management workflows |
| [Task: Instance Endpoints](references/task-instance-endpoints.md) | Internal and public access configuration |
| [Task: Instance Domains](references/task-instance-domains.md) | Custom domain management |
| [CLI Installation Guide](references/cli-installation-guide.md) | hcloud CLI installation and configuration |
| [Acceptance Criteria](references/acceptance-criteria.md) | Success criteria for all operations |

## Notes

- **Instance deletion is irreversible** — removes ALL namespaces, repositories, artifacts, and data permanently
- **Namespace deletion is irreversible** — removes all repositories and artifacts under it
- **Artifact deletion is irreversible** — the image version cannot be recovered
- **Default domain cannot be deleted** — only custom domains can be removed
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud SWR <Operation>` format
- **Pagination offset must be multiple of limit** — `offset` must be 0 or a multiple of `limit`
- **Registry credential.access_secret is sensitive** — never expose or log access secrets
- **SWR enterprise service must be activated first** — access `https://console.huaweicloud.com/swr-instance` to activate before creating instances
- **Console access requires direct URL** — the SWR enterprise instance console is not in the main navigation menu; use `https://console.huaweicloud.com/swr-instance`
- **Spec availability varies by region** — not all specs are available in all regions; verify before creating instances
- **Instance creation incurs hourly costs** — inform the user of billing implications before creating an instance

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides covering: invalid instance names, VPC/subnet errors, instance creation state, pagination offset rules, registry credential issues, domain certificate problems, public access whitelist format, SWR service activation, and spec availability.
