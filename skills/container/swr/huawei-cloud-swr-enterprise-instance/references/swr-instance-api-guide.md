# SWR Instance API Reference Guide

## Overview

This document provides API reference information for Huawei Cloud SWR enterprise
instance operations using hcloud CLI. All commands follow the standard format:
`hcloud SWR <Operation> --param=value --cli-region=<region>`.
Enterprise instance operations differ from basic SWR operations — they require
`--instance_id` for most operations and use a separate set of API endpoints.

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

## Instance Lifecycle Operations

### 1. Create Instance

**⚠️ hcloud CLI Bug**: `hcloud SWR CreateInstance` has a known bug where
`--project_id` appears as both a path parameter and a body parameter with
the same name. hcloud CLI rejects duplicate parameters, making this command
unusable. Use the Python SDK script instead:

```bash
# ✅ CORRECT - Use Python SDK script (bypasses hcloud CLI duplicate --project_id bug)
python scripts/swr_instance_helper.py create --name=my-instance --spec=swr.ee.basic \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0

# Create professional edition instance with description
python scripts/swr_instance_helper.py create --name=prod-instance --spec=swr.ee.professional \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 \
    --description="Production enterprise registry"

# Create instance with OBS encryption
python scripts/swr_instance_helper.py create --name=secure-instance --spec=swr.ee.professional \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 \
    --obs_encrypt=true --obs_enc_kms_key_id=<kms-key-id>

# ❌ BROKEN - hcloud CLI CreateInstance fails with "重复的参数:project_id" or "缺少必填参数:project_id"
# hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic ...
```

**Parameters**:

- `--name` (required, body): Instance name, 3-48 chars, lowercase start, no consecutive hyphens, cannot end with hyphen
- `--spec` (required, body): `swr.ee.basic` or `swr.ee.professional`
- `--charge_mode` (required, body): `postPaid` (on-demand)
- `--vpc_id` (required, body): VPC ID
- `--subnet_id` (required, body): Subnet ID
- `--enterprise_project_id` (required, body): Enterprise project ID (use `0` for default)
- `--project_id` (required, body): Project ID for VPC and subnet
- `--description` (optional, body): Instance description
- `--enable_intranet_access` (optional, body): Create internal access, default `true`
- `--obs_encrypt` (optional, body): Enable OBS bucket encryption
- `--encrypt_type` (optional, body): Encryption algorithm, `gm` for Chinese national encryption (SM), empty for AES-256
- `--obs_bucket_name` (optional, body): Custom OBS bucket name (skips OBS encryption config)
- `--obs_enc_kms_key_id` (optional, body): KMS key ID for OBS encryption
- `--resource_tags.[N].key` (optional, body): Tag key in indexed format
- `--resource_tags.[N].value` (optional, body): Tag value in indexed format

⚠️ **Note**: Instance creation is asynchronous. After calling `CreateInstance`, check status with `ListInstance` or `ShowInstance` until status becomes `Running`.

### 2. List Instances

```bash
# List all instances
hcloud SWR ListInstance --cli-region=cn-north-4

# List instances by status
hcloud SWR ListInstance --status=Running --cli-region=cn-north-4

# List instances with pagination
hcloud SWR ListInstance --limit=20 --offset=0 --cli-region=cn-north-4

# List instances by enterprise project
hcloud SWR ListInstance --enterprise_project_id=<ep-id> --cli-region=cn-north-4
```

**Parameters**:

- `--cli-region` (required): Region ID
- `--project_id` (required, path, auto-filled): Project ID
- `--status` (optional): Filter by status (`Initial`, `Creating`, `Running`, `Unavailable`)
- `--limit` (optional): Page size, default 100, max 100
- `--offset` (optional): Page offset (must pair with `--limit`)
- `--enterprise_project_id` (optional): Filter by enterprise project

**Response**: Response format needs verification.

### 3. Show Instance Details

```bash
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID

**Response**: Response format needs verification.

### 4. Show Instance Configuration

```bash
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID

**Response**: Response format needs verification — returns configuration including anonymous access setting.

### 5. Update Instance Configuration

```bash
# Enable anonymous access
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=true --cli-region=cn-north-4

# Disable anonymous access
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--anonymous_access` (required, body): Enable/disable anonymous login (`true`/`false`)
- `--project_id` (required, path, auto-filled): Project ID

### 6. Delete Instance

⚠️ **Warning**: This operation is irreversible. ALL data (namespaces, repositories, artifacts, configurations) will be permanently deleted.

```bash
# Delete instance (basic)
hcloud SWR DeleteInstance --instance_id=<instance-id> --cli-region=cn-north-4

# Delete instance and also delete OBS bucket
hcloud SWR DeleteInstance --instance_id=<instance-id> --delete_obs=true --cli-region=cn-north-4

# Delete instance and also delete DNS records
hcloud SWR DeleteInstance --instance_id=<instance-id> --delete_dns=true --cli-region=cn-north-4

# Delete instance with both OBS and DNS cleanup
hcloud SWR DeleteInstance --instance_id=<instance-id> --delete_obs=true --delete_dns=true --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--delete_dns` (optional, body): Whether to delete DNS domain info
- `--delete_obs` (optional, body): Whether to delete OBS bucket

## Instance Namespace Operations

### 1. Create Instance Namespace

```bash
# Create private namespace (basic)
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --cli-region=cn-north-4

# Create public namespace with auto-scan and vulnerability blocking
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=prod-ns --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=high --cli-region=cn-north-4

# Create namespace with only vulnerability blocking (no auto-scan)
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=secure-ns --metadata.public=false --metadata.auto_scan=false --metadata.prevent_vul=true --metadata.severity=critical --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, body): Namespace name, 1-64 chars
- `--metadata.public` (required, body): Public visibility (`true`/`false`)
- `--metadata.auto_scan` (optional, body): Auto scan on upload (`true`/`false`)
- `--metadata.prevent_vul` (optional, body): Block vulnerable images (`true`/`false`)
- `--metadata.severity` (optional, body): Blocking severity (`none`, `low`, `medium`, `high`, `critical`)
- `--project_id` (required, path, auto-filled): Project ID

**Namespace Naming Rules**:

- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots (`.`), underscores (`_`), or hyphens (`-`)
- Dots, underscores, hyphens cannot be directly connected (e.g., `a._b` is invalid)
- End with lowercase letter or digit
- Length: 1-64 characters

### 2. List Instance Namespaces

```bash
# List all namespaces
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4

# List namespaces with pagination
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by name
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --name=group-dev --cli-region=cn-north-4

# Filter by visibility
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --public=false --cli-region=cn-north-4

# Sort by update time
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --order_column=updated_at --order_type=desc --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 10, max 100
- `--offset` (optional): Page offset, must be 0 or multiple of limit
- `--name` (optional): Filter by namespace name
- `--public` (optional): Filter by visibility
- `--order_column` (optional): Sort column (`updated_at`)
- `--order_type` (optional): Sort direction (`desc`, `asc`)

**Response**: Response format needs verification.

### 3. Show Instance Namespace

```bash
hcloud SWR ShowInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--project_id` (required, path, auto-filled): Project ID

### 4. Update Instance Namespace

```bash
# Change namespace to public
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=true --cli-region=cn-north-4

# Enable vulnerability blocking with medium severity
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --metadata.prevent_vul=true --metadata.severity=medium --cli-region=cn-north-4

# Disable auto-scan
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=false --cli-region=cn-north-4

# Update namespace with CVE whitelist
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --cve_allowlist.id=<whitelist-id> --cve_allowlist.namespace_id=<ns-id> --cve_allowlist.expires_at=1735689600 --cve_allowlist.items.1.cve_id=CVE-2019-10164 --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--metadata.public` (required, body): Public visibility
- `--metadata.auto_scan` (optional, body): Auto scan on upload
- `--metadata.prevent_vul` (optional, body): Block vulnerable images
- `--metadata.severity` (optional, body): Blocking severity
- `--cve_allowlist.id` (optional, body): Whitelist ID
- `--cve_allowlist.namespace_id` (optional, body): Namespace ID for whitelist
- `--cve_allowlist.expires_at` (optional, body): Whitelist expiry (Unix timestamp)
- `--cve_allowlist.items.[N].cve_id` (optional, body): CVE ID entries in indexed format

⚠️ **Note**: `--metadata.public` is required even if you only want to change scan settings.

### 5. Delete Instance Namespace

```bash
hcloud SWR DeleteInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--project_id` (required, path, auto-filled): Project ID

⚠️ **Warning**: This operation is irreversible. ALL repositories and artifacts under the namespace will be permanently deleted.

## Instance Registry Operations

### 1. Create Instance Registry

```bash
# Create registry for another SWR enterprise instance (internal)
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=target-registry --type=swr-pro-internal --url=https://<target-instance>.cn-east-3.myhuaweicloud.com --credential.type=basic --credential.access_key=<username> --credential.access_secret=<password> --insecure=false --instance_id=<target-instance-id> --project_id=<target-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# Create registry for open-source Harbor
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=harbor-reg --type=swr-pro --url=https://harbor.example.com --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=true --cli-region=cn-north-4

# Create registry for basic SWR
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=swr-basic --type=huawei-SWR --url=https://swr.cn-north-4.myhuaweicloud.com --credential.type=basic --credential.access_key=<ak> --credential.access_secret=<sk> --insecure=false --cli-region=cn-north-4

# Create registry with description
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=prod-harbor --type=swr-pro --url=https://harbor.example.com --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=false --description="Production Harbor instance" --cli-region=cn-north-4

# Create registry with DNS host mapping
hcloud SWR CreateInstanceRegistry --instance_id=<instance-id> --name=custom-harbor --type=swr-pro --url=https://harbor.internal.example.com --credential.type=basic --credential.access_key=admin --credential.access_secret=<password> --insecure=false --dns_conf.hosts.harbor.internal.example.com=10.0.1.100 --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Source instance ID
- `--name` (required, body): Registry display name, 1-64 chars
- `--type` (required, body): `swr-pro`, `swr-pro-internal`, `huawei-SWR`
- `--url` (required, body): Registry URL
- `--credential.type` (required, body): Auth type, only `basic` supported
- `--credential.access_key` (required, body): Access ID/username
- `--credential.access_secret` (required, body): Access secret/password
- `--insecure` (required, body): Verify remote cert (`true`=skip, `false`=verify)
- `--description` (optional, body): Registry description
- `--instance_id` (optional, body): Target instance ID (required for `swr-pro-internal`)
- `--project_id` (optional, body): Target project ID (required for `swr-pro-internal`)
- `--region_id` (optional, body): Target region (required for `swr-pro-internal`)
- `--dns_conf.hosts.{*}` (optional, body): DNS host mapping entries

⚠️ **Note**: `--instance_id` appears twice in parameters — once as path
parameter (source instance), and once as body parameter (target instance
for `swr-pro-internal` type). When using `swr-pro-internal`, both are needed.

### 2. List Instance Registries

```bash
# List all registries
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --cli-region=cn-north-4

# List registries with pagination
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by name (fuzzy match)
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --name=harbor --cli-region=cn-north-4

# Filter by type
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --type=swr-pro --cli-region=cn-north-4

# Sort by updated time
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --order_column=updated_at --order_type=desc --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 10, max 100
- `--offset` (optional): Page offset, must be 0 or multiple of limit
- `--name` (optional): Filter by name (fuzzy)
- `--type` (optional): Filter by registry type
- `--order_column` (optional): `created_at`, `updated_at`, `name` (default `created_at`)
- `--order_type` (optional): `desc`, `asc` (default `desc`)

### 3. Show Instance Registry

```bash
hcloud SWR ShowInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--registry_id` (required, path): Registry ID (numeric)
- `--project_id` (required, path, auto-filled): Project ID

### 4. Update Instance Registry

```bash
hcloud SWR UpdateInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --name=updated-name --type=swr-pro --url=https://harbor.example.com --credential.type=basic --credential.access_key=<new-key> --credential.access_secret=<new-secret> --insecure=false --cli-region=cn-north-4
```

**Parameters**:

- Same as CreateInstanceRegistry, plus `--registry_id` (required, path) for identifying the registry to update
- All required body parameters from CreateInstanceRegistry must be provided even for partial updates

### 5. Delete Instance Registry

```bash
hcloud SWR DeleteInstanceRegistry --instance_id=<instance-id> --registry_id=<registry-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--registry_id` (required, path): Registry ID (numeric)
- `--project_id` (required, path, auto-filled): Project ID

## Instance Repository Operations

### 1. List Instance Repositories

```bash
# List all repositories in instance
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --cli-region=cn-north-4

# List repositories with pagination
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by namespace
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --namespace_id=<ns-id> --cli-region=cn-north-4

# Sort by update time
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --order_column=updated_at --order_type=desc --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--namespace_id` (optional): Filter by namespace ID (numeric)
- `--limit` (optional): Page size, default 10, max 100
- `--offset` (optional): Page offset, must be 0 or multiple of limit
- `--order_column` (optional): `created_at`, `updated_at` (default `created_at`)
- `--order_type` (optional): `desc`, `asc` (default `desc`)

### 2. List All Instance Repositories (Cross-Instance)

```bash
# List repositories across all instances in project
hcloud SWR ListAllInstanceRepositories --cli-region=cn-north-4

# Filter by name
hcloud SWR ListAllInstanceRepositories --name=my-app --cli-region=cn-north-4

# List with pagination using marker
hcloud SWR ListAllInstanceRepositories --limit=20 --marker=<next-marker> --cli-region=cn-north-4
```

**Parameters**:

- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 100, max 100
- `--marker` (optional): Pagination marker (use `next_marker` from previous response)
- `--name` (optional): Filter by repository name

⚠️ **Note**: `ListAllInstanceRepositories` uses `--marker` pagination instead of `--offset/--limit`.

### 3. Show Instance Repository

```bash
hcloud SWR ShowInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID

### 4. Update Instance Repository

```bash
hcloud SWR UpdateInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --description="Updated repository description" --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--repository_name` (required, path): Repository name
- `--description` (required, body): New description
- `--project_id` (required, path, auto-filled): Project ID

### 5. Delete Instance Repository

```bash
hcloud SWR DeleteInstanceRepository --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID

⚠️ **Warning**: This operation is irreversible. ALL artifacts in the repository will be permanently deleted.

## Instance Artifact Operations

### 1. List Instance Artifacts

```bash
# List artifacts in a repository
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# List artifacts with pagination
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by type
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --type=IMAGE --cli-region=cn-north-4

# Search by tag name
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --tags=v1.0 --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 10, max 100
- `--offset` (optional): Page offset, must be 0 or multiple of limit
- `--tags` (optional): Fuzzy match on tag/version names
- `--type` (optional): Artifact type (`IMAGE`, `CHART`)

### 2. List All Instance Artifacts (Cross-Repository)

```bash
# List all artifacts across all repositories in instance
hcloud SWR ListInstanceAllArtifacts --instance_id=<instance-id> --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceAllArtifacts --instance_id=<instance-id> --limit=20 --marker=1 --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 10, max 100
- `--marker` (optional): Pagination marker (default 1)

⚠️ **Note**: `ListInstanceAllArtifacts` uses `--marker` pagination instead of `--offset/--limit`.

### 3. Show Instance Artifact

```bash
# Show artifact details
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123... --cli-region=cn-north-4

# Show artifact with scan overview
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123... --with_scan_overview=true --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--reference` (required, path): Artifact digest (SHA256 hash)
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID
- `--with_scan_overview` (optional, query): Include scan results (`true`/`false`)

### 4. Show Instance Artifact Addition (Build History)

```bash
hcloud SWR ShowInstanceArtifactAddition --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123... --addition=build_history --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--reference` (required, path): Artifact digest
- `--repository_name` (required, path): Repository name
- `--addition` (required, path): Addition type (`build_history`)
- `--project_id` (required, path, auto-filled): Project ID

### 5. List Instance Artifact Vulnerabilities

```bash
hcloud SWR ListInstanceArtifactVulnerabilities --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123... --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--reference` (required, path): Artifact digest
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID

### 6. Start Manual Scanning

```bash
hcloud SWR StartManualScanning --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123... --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--reference` (required, path): Artifact digest
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID

### 7. Delete Instance Artifact

```bash
hcloud SWR DeleteInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123... --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--namespace_name` (required, path): Namespace name
- `--reference` (required, path): Artifact digest
- `--repository_name` (required, path): Repository name
- `--project_id` (required, path, auto-filled): Project ID

⚠️ **Warning**: This operation is irreversible. The artifact (image version) will be permanently deleted.

## Instance Credential Operations

### 1. Create Long-term Access Credential

```bash
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=my-credential --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--name` (required, body): Credential name, same naming rules as namespace (1-64 chars)
- `--project_id` (required, path, auto-filled): Project ID

**Use Case**: Long-term credentials for CI/CD pipelines and automation tools.

### 2. Create Temporary Access Credential

```bash
hcloud SWR CreateInstanceTempCredential --instance_id=<instance-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID

**Use Case**: Short-lived credentials for temporary access (e.g., developer testing).

### 3. List Long-term Credentials

```bash
# List all credentials (admin view)
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --cli-region=cn-north-4

# List only self-created credentials
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --self_only=true --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 100, max 100
- `--offset` (optional): Page offset
- `--self_only` (optional): Only show self-created credentials (`true`/`false`)

### 4. Enable/Disable Long-term Credential

```bash
# Disable a credential
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --enable=false --cli-region=cn-north-4

# Re-enable a credential
hcloud SWR UpdateInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --enable=true --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--credential_id` (required, path): Credential ID (token_id)
- `--enable` (required, body): Enable/disable (`true`/`false`)
- `--project_id` (required, path, auto-filled): Project ID

### 5. Delete Long-term Credential

```bash
hcloud SWR DeleteInstanceLtCredential --instance_id=<instance-id> --credential_id=<cred-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--credential_id` (required, path): Credential ID (token_id)
- `--project_id` (required, path, auto-filled): Project ID

## Instance Endpoint Operations

### 1. Create Internal VPC Endpoint

```bash
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<vpc-id> --subnet_id=<subnet-id> --project_id=<vpc-project-id> --cli-region=cn-north-4

# Create with description
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<vpc-id> --subnet_id=<subnet-id> --project_id=<vpc-project-id> --description="Production VPC endpoint" --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--vpc_id` (required, body): VPC ID
- `--subnet_id` (required, body): Subnet ID
- `--project_id` (required, body): VPC/subnet project ID
- `--description` (optional, body): Endpoint description

⚠️ **Note**: `--project_id` appears as both path (auto-filled) and body parameter. The body `--project_id` specifies the project where the VPC/subnet resides.

### 2. List Internal Endpoints

```bash
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--limit` (optional): Page size, default 100, max 100
- `--offset` (optional): Page offset

### 3. Show Internal Endpoint

```bash
hcloud SWR ShowInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--internal_endpoints_id` (required, path): Endpoint ID
- `--project_id` (required, path, auto-filled): Project ID

### 4. Delete Internal Endpoint

```bash
hcloud SWR DeleteInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--internal_endpoints_id` (required, path): Endpoint ID
- `--project_id` (required, path, auto-filled): Project ID

### 5. Enable/Disable Public Access

```bash
# Enable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=true --cli-region=cn-north-4

# Disable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=false --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--enable` (required, body): Enable/disable (`true`/`false`)
- `--project_id` (required, path, auto-filled): Project ID

**Status Constraints**:

- Can only enable when status is `Disable` or `EnableFailed`
- Can only disable when status is `Enable` or `DisableFailed`

### 6. Show Public Access (Endpoint Policy)

```bash
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID

### 7. Update Public Access Whitelist

```bash
# Update whitelist (full replacement)
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Internal network" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="VPN access" --cli-region=cn-north-4

# Allow single IP
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.1.100 --ip_list.1.description="Build server" --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--ip_list.[N].ip` (required, body): IP or CIDR in indexed format
- `--ip_list.[N].description` (optional, body): Description in indexed format
- `--project_id` (required, path, auto-filled): Project ID

⚠️ **Note**: Whitelist update is full replacement — specifying new entries replaces all existing entries. To add entries, you must include all existing ones plus the new ones.

## Instance Domain Operations

### 1. Add Domain Name

```bash
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=registry.example.com --certificate_id=<scm-cert-id> --cli-region=cn-north-4

# Add wildcard domain
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=*.registry.example.com --certificate_id=<scm-cert-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--domain_name` (required, body): Domain name
- `--certificate_id` (required, body): SCM certificate ID
- `--project_id` (required, path, auto-filled): Project ID

**Domain Naming Rules**:

- Letters, digits, hyphens, and asterisks (wildcard only at start)
- Hyphens cannot be at start or end
- At least two strings separated by dots
- Each string max 63 chars
- Total length max 100 chars
- Examples: `registry.example.com`, `*.registry.example.com`

### 2. List Domain Names

```bash
# List all domains for an instance
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4

# Filter by domain name
hcloud SWR ListDomainNames --instance_id=<instance-id> --domain_name=registry.example.com --cli-region=cn-north-4

# Filter by domain ID
hcloud SWR ListDomainNames --instance_id=<instance-id> --uid=<domain-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID
- `--domain_name` (optional): Filter by domain name
- `--uid` (optional): Filter by domain ID

### 3. Show Domain Overview

```bash
hcloud SWR ShowDomainOverview --cli-region=cn-north-4
```

⚠️ **Note**: `ShowDomainOverview` is a tenant-level operation, not instance-specific. It returns overall domain overview for the current tenant.

### 4. Update Domain Name (Certificate)

```bash
hcloud SWR UpdateDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --certificate_id=<new-scm-cert-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--domainname_id` (required, path): Domain ID
- `--certificate_id` (required, body): New SCM certificate ID
- `--project_id` (required, path, auto-filled): Project ID

### 5. Delete Domain Name

```bash
hcloud SWR DeleteDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--domainname_id` (required, path): Domain ID
- `--project_id` (required, path, auto-filled): Project ID

⚠️ **Warning**: The default domain assigned by SWR cannot be deleted. Only custom domains can be removed.

## Instance Statistics and Job Operations

### 1. List Instance Statistics

```bash
hcloud SWR ListInstanceStatistics --instance_id=<instance-id> --cli-region=cn-north-4
```

**Parameters**:

- `--instance_id` (required, path): Instance ID
- `--project_id` (required, path, auto-filled): Project ID

**Response**: Response format needs verification — returns resource statistics for the instance.

### 2. List Instance Jobs

```bash
# List all jobs
hcloud SWR ListInstanceJobs --cli-region=cn-north-4

# Filter by status
hcloud SWR ListInstanceJobs --status=Success --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceJobs --limit=20 --offset=0 --cli-region=cn-north-4
```

**Parameters**:

- `--project_id` (required, path, auto-filled): Project ID
- `--status` (optional): Job status (`Creating`, `Initializing`, `Running`, `Failed`, `Success`)
- `--limit` (optional): Page size, default 100, max 100
- `--offset` (optional): Page offset

### 3. Show Instance Job

```bash
hcloud SWR ShowInstanceJob --job_id=<job-id> --cli-region=cn-north-4
```

**Parameters**:

- `--job_id` (required, path): Job ID
- `--project_id` (required, path, auto-filled): Project ID

### 4. Delete Instance Job

```bash
hcloud SWR DeleteInstanceJob --job_id=<job-id> --cli-region=cn-north-4
```

**Parameters**:

- `--job_id` (required, path): Job ID
- `--project_id` (required, path, auto-filled): Project ID

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
| `InstanceNotFound`      | Instance does not exist     | Verify instance ID with `ListInstance`          |
| `NamespaceNotFound`     | Namespace does not exist    | Verify namespace with `ShowInstanceNamespace`   |
| `RegistryNotFound`      | Registry ID invalid         | Verify with `ListInstanceRegistries`            |
| `ArtifactNotFound`      | Artifact digest invalid     | Verify digest with `ListInstanceArtifacts`      |
| `InstanceNotReady`      | Instance still creating     | Wait for status=Running, check with `ShowInstance` |
| `QuotaExceeded`         | Resource quota limit        | Check quotas or apply for increase              |
| `RequestLimitExceeded`  | Too many requests           | Add delay between batch requests                  |
| `DomainNameInvalid`     | Domain naming violation     | Follow domain naming rules                      |
| `DefaultDomainCannotDelete` | Cannot delete default domain | Only custom domains can be deleted           |

## Related Documentation

- [Huawei Cloud SWR Documentation](https://support.huaweicloud.com/swr/index.html)
- [hcloud CLI Documentation](https://support.huaweicloud.com/cli/index.html)
- [Huawei Cloud API Explorer](https://apiexplorer.developer.huaweicloud.com/)