---
id: huawei-cloud-swr-enterprise-instance
name: huawei-cloud-swr-enterprise-instance
description: |
  Huawei Cloud SWR enterprise instance management skill using hcloud CLI.
  Use this skill when the user wants to: (1) manage SWR enterprise instances - create/list/show/delete/update configuration, (2) manage instance namespaces - create/list/show/update/delete with security scanning settings, (3) manage instance registries (sync targets) - create/list/show/update/delete, (4) manage instance repositories - list/show/delete/update, (5) manage instance artifacts (image versions) - list/show/delete/scan, (6) manage instance credentials - long-term and temporary, (7) manage instance endpoints - internal/public access, (8) manage instance domains - add/list/show/delete/update, (9) check instance statistics and job status.
  Trigger: user mentions "SWR enterprise instance", "SWR 企业实例", "SWR 企业版", "企业仓库实例", "SWR instance", "SWR 专业版", "swr.ee", "instance namespace", "instance registry", "instance repository", "instance artifact", "instance credential", "instance endpoint", "instance domain", "企业仓库", "实例管理"
tags: [swr, enterprise-instance, container-registry, registry, domain]
version: 1.0.0
---

# Huawei Cloud SWR Enterprise Instance Management

## Overview

This skill provides lifecycle management capabilities for Huawei Cloud SWR (Software Repository for Container) enterprise instances using the `hcloud` CLI. Enterprise instances provide dedicated, isolated container registry environments with advanced features like security scanning, replication policies, and custom domain support.

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

### 3. IAM Permission Requirements

| API Action                                    | Permission                   | Purpose                                        |
| --------------------------------------------- | ---------------------------- | ---------------------------------------------- |
| `swr:instance:create`                         | Create instance              | Create enterprise registry instances            |
| `swr:instance:list`                           | List instances               | Query all enterprise instances                  |
| `swr:instance:get`                            | Get instance                 | View instance details                           |
| `swr:instance:delete`                         | Delete instance              | Remove enterprise instances (irreversible)      |
| `swr:instance:update`                         | Update instance              | Modify instance configuration                   |
| `swr:instanceNamespace:create`                | Create instance namespace    | Create namespaces in instance                   |
| `swr:instanceNamespace:list`                  | List instance namespaces     | Query instance namespaces                       |
| `swr:instanceNamespace:get`                   | Get instance namespace       | View namespace details                          |
| `swr:instanceNamespace:update`                | Update instance namespace    | Modify namespace settings                       |
| `swr:instanceNamespace:delete`                | Delete instance namespace    | Remove namespaces                               |
| `swr:instanceRegistry:create`                 | Create instance registry     | Configure sync target registries                |
| `swr:instanceRegistry:list`                   | List instance registries     | Query sync target registries                    |
| `swr:instanceRegistry:get`                   | Get instance registry        | View registry details                           |
| `swr:instanceRegistry:update`                 | Update instance registry     | Modify registry settings                        |
| `swr:instanceRegistry:delete`                 | Delete instance registry     | Remove sync target registries                   |
| `swr:instanceRepository:list`                 | List instance repos          | Query repositories                              |
| `swr:instanceRepository:get`                  | Get instance repo            | View repository details                         |
| `swr:instanceRepository:delete`               | Delete instance repo         | Remove repositories                             |
| `swr:instanceRepository:update`               | Update instance repo         | Modify repository settings                      |
| `swr:instanceArtifact:list`                   | List instance artifacts      | Query image versions/artifacts                  |
| `swr:instanceArtifact:get`                    | Get instance artifact        | View artifact details                           |
| `swr:instanceArtifact:delete`                 | Delete instance artifact     | Remove image versions                           |
| `swr:instanceArtifact:scan`                   | Scan instance artifact       | Trigger vulnerability scanning                  |
| `swr:instanceCredential:create`               | Create instance credential   | Obtain access credentials                       |
| `swr:instanceCredential:list`                 | List instance credentials    | Query long-term credentials                     |
| `swr:instanceCredential:update`               | Update instance credential   | Enable/disable long-term credentials            |
| `swr:instanceCredential:delete`               | Delete instance credential   | Remove long-term credentials                    |
| `swr:instanceEndpoint:create`                 | Create instance endpoint     | Configure VPC internal endpoints                |
| `swr:instanceEndpoint:list`                   | List instance endpoints      | Query network access endpoints                  |
| `swr:instanceEndpoint:get`                    | Get instance endpoint        | View endpoint details                           |
| `swr:instanceEndpoint:delete`                 | Delete instance endpoint     | Remove internal endpoints                       |
| `swr:instanceEndpoint:update`                 | Update instance endpoint     | Configure public access whitelist               |
| `swr:instanceDomain:add`                      | Add domain name              | Add custom domain                               |
| `swr:instanceDomain:list`                     | List domain names            | Query all domains                               |
| `swr:instanceDomain:get`                      | Get domain overview          | View domain details                             |
| `swr:instanceDomain:delete`                   | Delete domain name           | Remove custom domain                            |
| `swr:instanceDomain:update`                   | Update domain name           | Update domain certificate                       |
| `swr:instanceJob:list`                        | List instance jobs           | Query async job status                          |
| `swr:instanceJob:get`                         | Get instance job             | View job details                                |
| `swr:instanceJob:delete`                      | Delete instance job          | Remove job records                              |
| `swr:instanceStatistic:get`                   | Get instance statistics      | View instance resource statistics               |

See [IAM Permission Policies](references/iam-policies.md) for complete policy JSON.

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
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4

# View instance configuration
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4

# Update instance configuration (anonymous access)
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4

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

## Parameter Reference

### Common Parameters

| Parameter       | Required/Optional | Description                   | Default                              |
| --------------- | ----------------- | ----------------------------- | ------------------------------------ |
| `--cli-region`  | Required          | Huawei Cloud region ID        | Config value or `HUAWEI_CLOUD_REGION` |
| `--instance_id` | Context-dependent | Enterprise instance ID        | N/A                                  |
| `--project_id`  | Auto-filled       | Project ID                    | Auto from credentials or config      |

### Instance Creation Parameters

| Parameter                  | Required | Description                | Constraints                                    |
| -------------------------- | -------- | -------------------------- | ---------------------------------------------- |
| `--name`                   | Yes      | Instance name              | 3-48 chars, lowercase start, no consecutive hyphens |
| `--spec`                   | Yes      | Instance spec              | `swr.ee.basic` or `swr.ee.professional`        |
| `--charge_mode`            | Yes      | Billing mode               | `postPaid` (on-demand only)                    |
| `--vpc_id`                 | Yes      | VPC ID                     | Existing VPC                                   |
| `--subnet_id`              | Yes      | Subnet ID                  | Existing subnet within VPC                     |
| `--enterprise_project_id`  | Yes      | Enterprise project ID      | Use `0` for default project                    |
| `--description`            | No       | Instance description       | Free text                                      |
| `--enable_intranet_access` | No       | Create internal access     | Default `true`                                 |
| `--obs_encrypt`            | No       | Enable OBS encryption      | `true` or `false`                              |
| `--encrypt_type`           | No       | OBS encryption algorithm   | `gm` (国密), empty for AES-256                 |
| `--obs_bucket_name`        | No       | Custom OBS bucket name     | If specified, OBS encryption not needed        |
| `--obs_enc_kms_key_id`     | No       | KMS key ID for OBS         | Required if obs_encrypt=true (no custom bucket) |

### Namespace Parameters

| Parameter              | Required | Description              | Constraints                                  |
| ---------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--namespace_name`     | Yes      | Namespace name           | 1-64 chars, lowercase/digit start            |
| `--metadata.public`    | Yes      | Public/private           | `true` or `false`                            |
| `--metadata.auto_scan` | No       | Auto scan on upload      | `true` or `false`                            |
| `--metadata.prevent_vul` | No     | Block vulnerable images  | `true` or `false`                            |
| `--metadata.severity`  | No       | Blocking severity level  | `none`, `low`, `medium`, `high`, `critical`  |

### Registry Parameters

| Parameter                   | Required | Description              | Constraints                                  |
| --------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--name`                    | Yes      | Registry display name    | 1-64 chars                                   |
| `--type`                    | Yes      | Registry type            | `swr-pro`, `swr-pro-internal`, `huawei-SWR`  |
| `--url`                     | Yes      | Registry URL             | Target registry address                      |
| `--credential.type`         | Yes      | Auth type                | `basic` only                                 |
| `--credential.access_key`   | Yes      | Access ID/username       | Auth credential                               |
| `--credential.access_secret` | Yes    | Access secret/password   | Auth credential                               |
| `--insecure`                | Yes      | Verify remote cert       | `true` (skip) or `false` (verify)            |
| `--instance_id` (body)      | Cond.    | Target instance ID       | Required when type=swr-pro-internal          |
| `--project_id` (body)       | Cond.    | Target project ID        | Required when type=swr-pro-internal          |
| `--region_id`               | Cond.    | Target region ID         | Required when type=swr-pro-internal          |

### Endpoint Whitelist Parameters

| Parameter                    | Required | Description              | Constraints                                  |
| ---------------------------- | -------- | ------------------------ | -------------------------------------------- |
| `--ip_list.[N].ip`           | Yes      | IP or CIDR range         | Indexed array format                         |
| `--ip_list.[N].description`  | No       | Description for IP entry | Indexed array format                         |

## Output Format

See [Output Format](references/output-format.md) for detailed response format examples (Instance List, Instance Details, Namespace List, Internal Endpoint List, Domain Name List, Long-term Credential).

## Verification

See [Verification Method](references/verification-method.md) for step-by-step verification.

## Best Practices

1. **Instance naming**: Use descriptive names like `prod-instance`, `dev-instance` that reflect the environment
2. **VPC selection**: Choose VPC/subnet that matches your workload deployment environment
3. **Namespace security**: Enable `auto_scan=true` and `prevent_vul=true` for production namespaces to block vulnerable images
4. **Severity blocking**: Set `severity=high` or `critical` for production; use `none` or `low` for development
5. **Registry credentials**: Store registry credentials securely; rotate access keys periodically
6. **Public access whitelist**: Always configure IP whitelist when enabling public access; use `UpdateInstanceEndpointPolicy` for full whitelist management
6. **Custom domains**: Use SCM (SSL Certificate Manager) certificates for custom domain HTTPS
7. **Delete with caution**: Deleting an instance removes ALL data permanently; deleting a namespace removes ALL repositories
8. **Long-term credentials**: Use `CreateInstanceLtCredential` for CI/CD pipelines; use `CreateInstanceTempCredential` for temporary access
9. **Instance spec selection**: Use `swr.ee.basic` for small teams; `swr.ee.professional` for enterprise requirements with advanced features

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

## Notes

- **Instance deletion is irreversible** — removes ALL namespaces, repositories, artifacts, and data permanently
- **Namespace deletion is irreversible** — removes all repositories and artifacts under it
- **Artifact deletion is irreversible** — the image version cannot be recovered
- **Default domain cannot be deleted** — only custom domains can be removed
- **AK/SK must never be hardcoded** — credentials should only be obtained via environment variables
- **hcloud CLI is the only supported method** — all operations use `hcloud SWR <Operation>` format
- **Pagination offset must be multiple of limit** — `offset` must be 0 or a multiple of `limit`
- **Registry credential.access_secret is sensitive** — never expose or log access secrets

## Common Pitfalls

See [Common Pitfalls & Solutions](references/common-pitfalls.md) for detailed troubleshooting guides.

**Quick Reference**:

| Pitfall                         | Symptom                         | Quick Fix                                    |
| ------------------------------- | ------------------------------- | -------------------------------------------- |
| Invalid instance name           | 400 Bad Request                 | 3-48 chars, lowercase start, no consecutive hyphens |
| VPC/subnet not found            | Instance creation fails         | Verify VPC/subnet exist in region            |
| Instance still creating         | Operations fail                 | Wait for Running, check with ListInstance    |
| Offset not multiple of limit    | Pagination returns error        | offset must be 0 or multiple of limit        |
| Registry credential wrong       | Sync fails                      | Verify access_key/access_secret              |
| Domain cert not found           | Domain creation fails           | Verify certificate_id in SCM                 |
| Cannot delete default domain    | Delete fails                    | Only custom domains can be deleted           |
| Public access whitelist format  | Whitelist update fails          | Use indexed: --ip_list.1.ip=value            |