# Task: Instance Lifecycle

## Overview

SWR enterprise instances provide dedicated, isolated container registry environments. This task covers creating, listing, showing, updating configuration, and deleting enterprise instances.

## Operations Catalog

| Operation                    | Method | Description              | Key Parameters                                  |
| ---------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateInstance`             | POST   | Create enterprise instance          | `--name`, `--spec`, `--charge_mode`, `--vpc_id`, `--subnet_id`, `--enterprise_project_id` |
| `ListInstance`               | GET    | List instances             | `--status`, `--limit`, `--offset`, `--enterprise_project_id` |
| `ShowInstance`               | GET    | Show instance details             | `--instance_id`                                 |
| `ShowInstanceConfiguration`  | GET    | Show instance configuration             | `--instance_id`                                 |
| `UpdateInstanceConfiguration`| PUT    | Update instance configuration             | `--instance_id`, `--anonymous_access`           |
| `DeleteInstance`             | DELETE | Delete instance                 | `--instance_id`, `--delete_obs`, `--delete_dns` |

## Workflows

### W1: Create an Enterprise Instance

**Pre-creation Checklist**:
1. **Activate SWR enterprise service** — Access `https://console.huaweicloud.com/swr-instance` and complete service activation if not already done
2. **Verify region availability** — Not all specs are available in all regions. Use `hcloud SWR ListInstance --cli-region=<region>` to verify the service is available in the target region
3. Verify VPC exists and is in the target region
4. Verify subnet exists within the VPC
5. Decide instance spec: `swr.ee.basic` or `swr.ee.professional` (verify spec is supported in the target region)
6. Choose instance name (3-48 chars, lowercase start)
7. Determine enterprise project (use `0` for default)
8. **Review billing** — Creating an instance incurs hourly costs based on the selected spec. Inform the user before proceeding

```bash
# Create basic edition instance
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --cli-region=cn-north-4

# Create professional edition instance with description
hcloud SWR CreateInstance --name=prod-instance --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --description="Production enterprise registry" --cli-region=cn-north-4

# Create instance with OBS encryption (AES-256)
hcloud SWR CreateInstance --name=secure-instance --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --obs_encrypt=true --obs_enc_kms_key_id=<kms-key-id> --cli-region=cn-north-4

# Create instance with GM (Chinese national cryptographic standard) encryption
hcloud SWR CreateInstance --name=gm-instance --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --obs_encrypt=true --encrypt_type=gm --cli-region=cn-north-4

# Create instance with resource tags
hcloud SWR CreateInstance --name=tagged-instance --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --resource_tags.1.key=Environment --resource_tags.1.value=Production --resource_tags.2.key=Team --resource_tags.2.value=Backend --cli-region=cn-north-4
```

**Instance Creation Parameters**:
- `--name`: Instance name (3-48 chars, lowercase start, no consecutive hyphens, no ending hyphen)
- `--spec`: `swr.ee.basic` or `swr.ee.professional`
- `--charge_mode`: Only `postPaid` (on-demand) supported currently
- `--spec` details: `swr.ee.basic` (basic tier, limited repos/namespaces) or `swr.ee.professional` (professional tier, higher limits and features)
- `--obs_encrypt`: Enable OBS bucket encryption (`true`/`false`). When `true`, `--obs_enc_kms_key_id` is required.
- `--obs_enc_kms_key_id`: KMS key ID for OBS encryption (required when `obs_encrypt=true`)
- `--encrypt_type`: Image encryption type. `gm` for GM (Chinese national cryptographic standard) encryption, or omit for no image encryption
- `--resource_tags.N.key`/`--resource_tags.N.value`: Resource tags for billing attribution and management (N starts from 1)
- `--description`: Instance description (max 255 characters)
- `--enable_intranet_access`: Default `true`, creates internal VPC access endpoint automatically
- `--vpc_id`: Existing VPC ID in the target region
- `--subnet_id`: Existing subnet ID within the VPC
- `--enterprise_project_id`: Enterprise project ID (use `0` for default)
- `--enable_intranet_access`: Default `true`, creates internal VPC access

**Post-creation Verification**:

Instance creation is asynchronous. Monitor status until `Running`:

```bash
# Check instance creation status
hcloud SWR ListInstance --cli-region=cn-north-4

# Or check specific instance
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

Wait until `status` becomes `Running`. If status becomes `Unavailable`, creation failed.

### W2: List Instances

```bash
# List all instances in project
hcloud SWR ListInstance --cli-region=cn-north-4

# Filter by status (Running instances only)
hcloud SWR ListInstance --status=Running --cli-region=cn-north-4

# Filter by enterprise project
hcloud SWR ListInstance --enterprise_project_id=<ep-id> --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstance --limit=20 --offset=0 --cli-region=cn-north-4
```

**Use Cases**:
- Find instance ID for subsequent operations
- Check instance status after creation
- Audit all enterprise instances in a project
- Monitor for instances stuck in `Creating` or `Unavailable` status

### W3: View Instance Details

```bash
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4
```

**Use Cases**:
- Get instance ID, name, spec, and status
- View VPC/subnet configuration
- Check instance endpoints (internal and public)
- Verify instance is ready for operations

### W4: View and Update Instance Configuration

```bash
# View current configuration
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4

# Disable anonymous access (recommended for security)
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4

# Enable anonymous access (for public image sharing)
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=true --cli-region=cn-north-4
```

**Configuration Options**:
- `--anonymous_access`: Whether unauthenticated users can pull images without credentials. Values: `true` or `false`. Default is `false` for security.
  - `true`: Enables anonymous pull access — anyone with network access can pull images (useful for public image distribution)
  - `false`: Requires authentication for all pull operations (recommended for production)
  - **Security Impact**: Setting `anonymous_access=true` bypasses namespace-level access control for pull operations. Only enable for public-facing image registries.
  - **Prerequisite**: The instance must have public access enabled (via `CreateInstanceEndpointPolicy --enable=true`) for anonymous access to work externally.
  - **Verification**: After updating, call `ShowInstanceConfiguration` to confirm the change took effect.

### W5: Delete an Instance

⚠️ **CAUTION**: Deleting an instance permanently removes ALL data — namespaces, repositories, artifacts, credentials, endpoints, domains. This is irreversible.

**Pre-deletion Checklist**:
1. List all namespaces to verify what will be deleted:
```bash
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4
```
2. Check for long-term credentials that will be revoked:
```bash
hcloud SWR ListInstanceLtCredentials --instance_id=<instance-id> --cli-region=cn-north-4
```
3. Check for sync target registries that will be removed:
```bash
hcloud SWR ListInstanceRegistries --instance_id=<instance-id> --cli-region=cn-north-4
```
4. Check for internal endpoints that will be removed:
```bash
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4
```
5. Check for custom domains that will be removed:
```bash
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4
```
6. Review instance statistics to understand total data volume:
```bash
hcloud SWR ListInstanceStatistics --instance_id=<instance-id> --cli-region=cn-north-4
```
7. Confirm with the user that ALL data will be permanently deleted
8. If data needs to be preserved, migrate/sync to another instance first

3. If data needs to be preserved, migrate/sync to another instance first

```bash
# Delete instance (basic — does not delete OBS bucket or DNS)
hcloud SWR DeleteInstance --instance_id=<instance-id> --cli-region=cn-north-4

# Delete instance and OBS bucket
hcloud SWR DeleteInstance --instance_id=<instance-id> --delete_obs=true --cli-region=cn-north-4

# Delete instance and DNS records
hcloud SWR DeleteInstance --instance_id=<instance-id> --delete_dns=true --cli-region=cn-north-4

# Delete instance with full cleanup
hcloud SWR DeleteInstance --instance_id=<instance-id> --delete_obs=true --delete_dns=true --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return empty or not include the deleted instance
hcloud SWR ListInstance --cli-region=cn-north-4
```

### W6: Monitor Instance Jobs

Instance creation and deletion are asynchronous operations tracked as jobs:

```bash
# List all jobs
hcloud SWR ListInstanceJobs --cli-region=cn-north-4

# Filter by job status
hcloud SWR ListInstanceJobs --status=Running --cli-region=cn-north-4

# Show specific job details
hcloud SWR ShowInstanceJob --job_id=<job-id> --cli-region=cn-north-4

# Clean up completed job records
hcloud SWR DeleteInstanceJob --job_id=<job-id> --cli-region=cn-north-4
```

## Common Scenarios

### S1: Standard Production Instance Setup

Set up a production enterprise instance with security features:

```bash
# 1. Create professional edition instance
hcloud SWR CreateInstance --name=prod-registry --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --description="Production container registry" --obs_encrypt=true --obs_enc_kms_key_id=<kms-key-id> --cli-region=cn-north-4

# 2. Wait for Running status, then disable anonymous access
hcloud SWR UpdateInstanceConfiguration --instance_id=<instance-id> --anonymous_access=false --cli-region=cn-north-4

# 3. Create production namespace with security scanning
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=prod --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=high --cli-region=cn-north-4

# 4. Create long-term credential for CI/CD
hcloud SWR CreateInstanceLtCredential --instance_id=<instance-id> --name=ci-credential --cli-region=cn-north-4
```

### S2: Multi-Environment Instance Strategy

Create separate instances for development and production:

```bash
# Development instance
hcloud SWR CreateInstance --name=dev-registry --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<dev-vpc-id> --subnet_id=<dev-subnet-id> --enterprise_project_id=0 --description="Development container registry" --cli-region=cn-north-4

# Production instance
hcloud SWR CreateInstance --name=prod-registry --spec=swr.ee.professional --charge_mode=postPaid --vpc_id=<prod-vpc-id> --subnet_id=<prod-subnet-id> --enterprise_project_id=0 --description="Production container registry" --cli-region=cn-north-4
```

### S3: Instance Audit

Periodically review all instances and their status:

```bash
# 1. List all instances
hcloud SWR ListInstance --cli-region=cn-north-4

# 2. For each Running instance, check statistics
hcloud SWR ListInstanceStatistics --instance_id=<instance-id> --cli-region=cn-north-4

# 3. Check namespaces for each instance
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4

# 4. Review configuration
hcloud SWR ShowInstanceConfiguration --instance_id=<instance-id> --cli-region=cn-north-4
```
