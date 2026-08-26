# Common Pitfalls & Solutions

This document contains detailed troubleshooting guides for common issues encountered when using the Huawei Cloud SWR Enterprise Instance skill.

## Pitfall 1: Instance Creation Requires Existing VPC and Subnet

**Symptom**: `CreateInstance` fails with VPC/subnet not found error

**Root Cause**: Enterprise instances must be deployed within an existing VPC and subnet. The VPC/subnet must exist before creating the instance.

**Solution**: Verify VPC and subnet exist before creating an instance:

```bash
# Verify VPC exists (use VPC CLI or console)
# Verify subnet exists within the VPC

# Then create instance with valid VPC/subnet IDs
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<valid-vpc-id> --subnet_id=<valid-subnet-id> --enterprise_project_id=0 --cli-region=cn-north-4
```

## Pitfall 2: Instance Not Ready for Operations

**Symptom**: Instance-related operations (namespace creation, credential creation) fail with errors

**Root Cause**: Instance operations cannot be performed while the instance is in `Creating` or `Initial` status. Only `Running` instances are ready for use.

**Solution**: Wait for the instance to reach `Running` status:

```bash
# Check instance status
hcloud SWR ListInstance --cli-region=cn-north-4

# Or check specific instance
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4

# Wait until status is "Running" before proceeding
```

**Instance Status Flow**: `Initial` → `Creating` → `Running` (or `Unavailable` if creation fails)

## Pitfall 3: Invalid Instance Name Format

**Symptom**: `CreateInstance` returns error `400 Bad Request` or name validation error

**Root Cause**: Instance name violates naming rules

**Naming Rules**:
- Start with lowercase letter
- Followed by lowercase letters, digits, or hyphens (`-`)
- No consecutive hyphens (`--` is invalid)
- Cannot end with hyphen (`-`)
- Length: 3-48 characters

**Common Mistakes**:
- ❌ `MyInstance` — starts with uppercase
- ❌ `my--instance` — consecutive hyphens
- ❌ `my-instance-` — ends with hyphen
- ❌ `ab` — too short (minimum 3 chars)
- ❌ Very long names > 48 chars

**Valid Examples**: `my-instance`, `prod-registry01`, `dev-team-app`

## Pitfall 4: Pagination Offset Must Be Multiple of Limit

**Symptom**: `ListInstanceNamespaces`, `ListInstanceRegistries`, `ListInstanceRepositories`, or `ListInstanceArtifacts` pagination returns errors or unexpected results

**Root Cause**: For instance-specific list operations (namespace, registry, repository, artifact), the `offset` parameter must be 0 or a multiple of `limit`. This is different from the basic SWR pagination which allows any offset value.

**Solution**: Always use offset values that are multiples of limit:

```bash
# ✅ CORRECT - offset=0, limit=20 (0 is multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=0 --cli-region=cn-north-4

# ✅ CORRECT - offset=20, limit=20 (20 is multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=20 --cli-region=cn-north-4

# ✅ CORRECT - offset=40, limit=20 (40 is multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=40 --cli-region=cn-north-4

# ❌ WRONG - offset=10, limit=20 (10 is NOT multiple of 20)
hcloud SWR ListInstanceNamespaces --instance_id=<id> --limit=20 --offset=10 --cli-region=cn-north-4
```

⚠️ **Note**: `ListInstance` and `ListInstanceLtCredentials` use standard offset/limit pagination (offset does not need to be multiple of limit). Only instance namespace, registry, repository, and artifact lists require the offset-to-be-multiple constraint.

## Pitfall 5: Namespace metadata.public Required for Update

**Symptom**: `UpdateInstanceNamespace` fails or only changes visibility when other settings were intended

**Root Cause**: `--metadata.public` is a required parameter for `UpdateInstanceNamespace`, even if you only want to change `auto_scan`, `prevent_vul`, or `severity` settings

**Solution**: Always include `--metadata.public` in update commands:

```bash
# ✅ CORRECT - Include metadata.public even when changing only scan settings
hcloud SWR UpdateInstanceNamespace --instance_id=<id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=true --cli-region=cn-north-4

# ❌ WRONG - Missing metadata.public
hcloud SWR UpdateInstanceNamespace --instance_id=<id> --namespace_name=group-dev --metadata.auto_scan=true --cli-region=cn-north-4
```

## Pitfall 6: Registry Instance ID Appears Twice for swr-pro-internal

**Symptom**: `CreateInstanceRegistry` with type `swr-pro-internal` fails with missing parameters

**Root Cause**: When creating a registry of type `swr-pro-internal`, `--instance_id` appears both as a path parameter (the source instance) and a body parameter (the target instance ID). Both must be provided.

**Solution**: Provide both instance IDs when creating `swr-pro-internal` registry:

```bash
# ✅ CORRECT - Both instance_id values provided
hcloud SWR CreateInstanceRegistry --instance_id=<source-instance-id> --name=target-registry --type=swr-pro-internal --url=<target-url> --credential.type=basic --credential.access_key=<key> --credential.access_secret=<secret> --insecure=false --instance_id=<target-instance-id> --project_id=<target-project-id> --region_id=cn-east-3 --cli-region=cn-north-4

# ❌ WRONG - Missing target instance_id body parameter
hcloud SWR CreateInstanceRegistry --instance_id=<source-instance-id> --name=target-registry --type=swr-pro-internal --url=<target-url> --credential.type=basic --credential.access_key=<key> --credential.access_secret=<secret> --insecure=false --cli-region=cn-north-4
```

## Pitfall 7: Deleting Instance Removes ALL Data Permanently

**Symptom**: All namespaces, repositories, artifacts, and configurations disappear after instance deletion

**Root Cause**: `DeleteInstance` removes the entire instance and all associated data permanently

**Solution**: Before deleting an instance, always:

1. Confirm with the user that they understand ALL data will be permanently deleted
2. Consider using `--delete_obs=true` and `--delete_dns=true` for complete cleanup
3. If any data needs to be preserved, sync/migrate it to another instance first

```bash
# Delete with OBS bucket and DNS cleanup
hcloud SWR DeleteInstance --instance_id=<id> --delete_obs=true --delete_dns=true --cli-region=cn-north-4
```

## Pitfall 8: Default Domain Cannot Be Deleted

**Symptom**: `DeleteDomainName` fails when attempting to delete the default domain

**Root Cause**: The SWR-assigned default domain (e.g., `xxx.cn-north-4.myhuaweicloud.com`) cannot be deleted. Only custom domains added via `AddDomainName` can be removed.

**Solution**: Only delete custom domains. Leave the default domain intact:

```bash
# ✅ CORRECT - Delete only custom domain
hcloud SWR DeleteDomainName --instance_id=<id> --domainname_id=<custom-domain-id> --cli-region=cn-north-4

# ❌ WRONG - Attempting to delete default domain will fail
```

## Pitfall 9: Public Access Whitelist is Full Replacement

**Symptom**: Previous whitelist entries disappear after updating the whitelist

**Root Cause**: `UpdateInstanceEndpointPolicy` performs a full replacement of the IP whitelist, not an incremental add. All existing entries are replaced by the new ones provided.

**Solution**: When adding new IPs, include ALL existing IPs plus the new ones:

```bash
# ✅ CORRECT - Include all existing IPs plus new ones
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Existing: Internal" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="Existing: VPN" --ip_list.3.ip=172.16.0.0/12 --ip_list.3.description="New: Docker network" --cli-region=cn-north-4

# ❌ WRONG - Only providing new entries (existing entries will be lost)
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<id> --ip_list.1.ip=172.16.0.0/12 --ip_list.1.description="New: Docker network" --cli-region=cn-north-4
```

**Best Practice**: Before updating the whitelist, check current entries with `ShowInstanceEndpointPolicy` and include all existing entries in the update command.

## Pitfall 10: Artifact Reference Uses Digest, Not Tag Name

**Symptom**: `ShowInstanceArtifact`, `DeleteInstanceArtifact`, `StartManualScanning` fail with "not found" error

**Root Cause**: These operations use `--reference` which must be the artifact's SHA256 digest (e.g., `sha256:abc123...`), NOT the tag name (e.g., `v1.0`)

**Solution**: First obtain the digest from `ListInstanceArtifacts`, then use it for operations:

```bash
# 1. List artifacts to find the digest
hcloud SWR ListInstanceArtifacts --instance_id=<id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# 2. Use the digest value for operations
hcloud SWR ShowInstanceArtifact --instance_id=<id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --cli-region=cn-north-4
```

## Pitfall 11: CreateInstanceEndpointPolicy Status Constraints

**Symptom**: `CreateInstanceEndpointPolicy` fails when trying to enable or disable public access

**Root Cause**: The enable/disable operation has status constraints:
- Can only enable (`--enable=true`) when status is `Disable` or `EnableFailed`
- Can only disable (`--enable=false`) when status is `Enable` or `DisableFailed`

**Solution**: Check current status before changing:

```bash
# Check current public access status
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<id> --cli-region=cn-north-4

# Then enable or disable based on current status
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<id> --enable=true --cli-region=cn-north-4
```

## Pitfall 12: Registry Credential Security

**Symptom**: Registry sync fails with authentication error

**Root Cause**: Registry credentials (`--credential.access_key` and `--credential.access_secret`) must be correct and current. If the target registry changes its credentials, sync will fail.

**Solution**:
- Never expose or log credential values
- Update registry credentials when they change on the target side
- Verify credentials work by testing manually before configuring in SWR

```bash
# Update registry credentials when target credentials change
hcloud SWR UpdateInstanceRegistry --instance_id=<id> --registry_id=<reg-id> --name=target --type=swr-pro --url=<url> --credential.type=basic --credential.access_key=<new-key> --credential.access_secret=<new-secret> --insecure=false --cli-region=cn-north-4
```

## Pitfall 13: Instance VPC Project ID Confusion

**Symptom**: `CreateInstance` or `CreateInstanceInternalEndpoint` fails with project ID errors

**Root Cause**: The `--project_id` body parameter for VPC/subnet configuration may differ from the auto-filled path `--project_id`. If the VPC/subnet is in a different project, the body `--project_id` must specify the VPC/subnet project.

**Solution**: Ensure the body `--project_id` matches the project where the VPC and subnet reside:

```bash
# If VPC/subnet are in a different project, specify that project ID
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --project_id=<vpc-project-id> --cli-region=cn-north-4
```

## Pitfall 14: ListAllInstanceRepositories Uses Marker-Based Pagination

**Symptom**: Pagination with `--offset/--limit` returns unexpected results for `ListAllInstanceRepositories`

**Root Cause**: `ListAllInstanceRepositories` uses `--marker/--limit` pagination, not `--offset/--limit`. The `--marker` value comes from the `next_marker` field in the previous response.

**Solution**: Use marker-based pagination:

```bash
# ✅ CORRECT - First page (no marker needed)
hcloud SWR ListAllInstanceRepositories --limit=20 --cli-region=cn-north-4

# ✅ CORRECT - Next page (use next_marker from previous response)
hcloud SWR ListAllInstanceRepositories --limit=20 --marker=<next_marker> --cli-region=cn-north-4

# ❌ WRONG - Using offset for this operation
hcloud SWR ListAllInstanceRepositories --limit=20 --offset=0 --cli-region=cn-north-4
```

## P8: SWR Enterprise Service Not Activated

**Symptom**: API calls return errors indicating the service is not available or not activated.

**Cause**: The SWR enterprise service has not been activated in the target region.

**Solution**:
1. Access the SWR enterprise instance console: `https://console.huaweicloud.com/swr-instance`
2. Complete the service activation process if prompted
3. Verify activation by running `hcloud SWR ListInstance --cli-region=<region>`
4. If the service is not available in the region, try a different region

## P9: Spec Not Available in Region

**Symptom**: `CreateInstance` fails with an error about invalid or unsupported spec.

**Cause**: The selected instance spec (`swr.ee.basic` or `swr.ee.professional`) is not available in the target region.

**Solution**:
1. Try the other spec (e.g., switch from `swr.ee.basic` to `swr.ee.professional` or vice versa)
2. Try a different region where the spec is known to be available
3. Use `hcloud SWR ListSyncRegions --cli-region=<region>` to check available regions
4. Consult the SWR enterprise instance console at `https://console.huaweicloud.com/swr-instance` for current spec/region availability

## Pitfall 15: Same-Name Parameter Conflict (path vs body)

**Symptom**: Commands like `CreateInstance`, `CreateInstanceInternalEndpoint`, or `CreateInstanceRegistry` fail with "missing required parameter" or "duplicate parameter" errors when using `--project_id` or `--instance_id` CLI arguments.

**Root Cause**: Some SWR API operations define the same parameter name in both the request path and request body. The hcloud CLI cannot distinguish between path and body parameters with the same name:
- `CreateInstance`: `project_id` appears in both path (auto-filled) and body (VPC/subnet project)
- `CreateInstanceInternalEndpoint`: `project_id` appears in both path (auto-filled) and body (VPC/subnet project)
- `CreateInstanceRegistry`: `instance_id` appears in both path (source instance) and body (target instance for `swr-pro-internal`)

**Solution**: Use `--cli-jsonInput` to pass all parameters via a JSON file with `path` and `body` sections (required by hcloud to distinguish same-name parameters):

```bash
# CreateInstance example
cat > create_instance.json << 'EOF'
{
  "path": {
    "project_id": "<project-id>"
  },
  "body": {
    "name": "my-instance",
    "spec": "swr.ee.professional",
    "charge_mode": "postPaid",
    "vpc_id": "<vpc-id>",
    "subnet_id": "<subnet-id>",
    "enterprise_project_id": "0",
    "project_id": "<vpc-project-id>"
  }
}
EOF

hcloud SWR CreateInstance --cli-jsonInput=create_instance.json --cli-region=cn-north-4
```

```bash
# CreateInstanceInternalEndpoint example
cat > create_endpoint.json << 'EOF'
{
  "path": {
    "instance_id": "<instance-id>",
    "project_id": "<project-id>"
  },
  "body": {
    "vpc_id": "<vpc-id>",
    "subnet_id": "<subnet-id>",
    "project_id": "<vpc-project-id>"
  }
}
EOF

hcloud SWR CreateInstanceInternalEndpoint --cli-jsonInput=create_endpoint.json --cli-region=cn-north-4
```

```bash
# CreateInstanceRegistry example (swr-pro-internal type)
cat > create_registry.json << 'EOF'
{
  "path": {
    "instance_id": "<source-instance-id>",
    "project_id": "<project-id>"
  },
  "body": {
    "name": "target-registry",
    "type": "swr-pro-internal",
    "url": "https://<target-instance>.cn-east-3.myhuaweicloud.com",
    "credential": {
      "type": "basic",
      "access_key": "<access-key>",
      "access_secret": "<access-secret>"
    },
    "insecure": false,
    "instance_id": "<target-instance-id>",
    "project_id": "<target-project-id>",
    "region_id": "cn-east-3"
  }
}
EOF

hcloud SWR CreateInstanceRegistry --cli-jsonInput=create_registry.json --cli-region=cn-north-4
```

**Note**: The `path`/`body` separation in the JSON file is mandatory — hcloud uses it to route same-name parameters to the correct API location. A flat JSON without `path`/`body` keys will be rejected.

### Alternative: Python SDK Script (Recommended for CreateInstance)

For `CreateInstance` specifically, a Python SDK helper script is available that bypasses the hcloud CLI duplicate parameter bug entirely by calling the Huawei Cloud SDK directly:

```bash
# ✅ Recommended - Use Python SDK script for CreateInstance
python scripts/swr_instance_helper.py create --name=my-instance --spec=swr.ee.basic \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --description="My registry"

# ❌ BROKEN - hcloud CLI CreateInstance cannot handle duplicate --project_id
# hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic ...
```

The SDK script requires `huaweicloudsdkcore` and `huaweicloudsdkswr` packages and uses the same AK/SK credentials as hcloud CLI (via environment variables). All other hcloud CLI SWR operations (ListInstance, ShowInstance, DeleteInstance, namespace/credential/endpoint/domain management) work correctly without the script.

## Pitfall 16: Description Parameter with Spaces Causes Errors

**Symptom**: `CreateInstance` or `CreateInstanceNamespace` fails when the `--description` parameter contains spaces, even when quoted.

**Root Cause**: The hcloud CLI may not correctly parse `--description` values containing spaces when using the standard `--key=value` format. The shell may split the value at spaces, or the CLI may not handle the quoting correctly.

**Solution**: Use one of the following approaches:

```bash
# ✅ Option 1: Use --cli-jsonInput for descriptions with spaces
cat > create_instance.json << 'EOF'
{
  "path": {
    "project_id": "<project-id>"
  },
  "body": {
    "name": "my-instance",
    "spec": "swr.ee.basic",
    "charge_mode": "postPaid",
    "vpc_id": "<vpc-id>",
    "subnet_id": "<subnet-id>",
    "enterprise_project_id": "0",
    "description": "Production registry for team dev"
  }
}
EOF
hcloud SWR CreateInstance --cli-jsonInput=create_instance.json --cli-region=cn-north-4

# ✅ Option 2: Use shell-quoted value (ensure proper quoting)
hcloud SWR CreateInstanceNamespace --instance_id=<id> --namespace_name=group-dev --description='Production namespace' --cli-region=cn-north-4

# ❌ WRONG - Unquoted description with spaces
hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.basic --charge_mode=postPaid --vpc_id=<vpc-id> --subnet_id=<subnet-id> --enterprise_project_id=0 --description=Production registry for team dev --cli-region=cn-north-4
```

**Note**: For `CreateInstance`, prefer `--cli-jsonInput` as it also resolves the same-name `project_id` parameter conflict (see Pitfall 15).

## Pitfall 17: Default Internal Endpoint Conflict (SWR.400005)

**Symptom**: `CreateInstanceInternalEndpoint` fails with error `SWR.400005` — "endpoint already exists" or similar conflict error.

**Root Cause**: When an enterprise instance is created, a default internal endpoint is automatically created for the instance's VPC and subnet. Attempting to create another internal endpoint for the same VPC/subnet combination will conflict with the default endpoint.

**Solution**: Before creating a new internal endpoint, check existing endpoints:

```bash
# 1. List existing internal endpoints
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4

# 2. If the VPC/subnet already has an endpoint, use the existing one
#    (Look for matching vpc_id and subnet_id in the response)

# 3. Only create a new endpoint for a DIFFERENT VPC/subnet
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<different-vpc-id> --subnet_id=<different-subnet-id> --project_id=<vpc-project-id> --cli-region=cn-north-4
```

**Note**: If you need to create an endpoint for the same VPC but a different subnet, verify that no existing endpoint covers that subnet first. Each VPC/subnet combination can only have one internal endpoint.

## Pitfall 18: SWR Service Tenant Quota Exceeded (Misleading Error)

**Symptom**: `CreateInstance` (via SDK or API) returns job status `Failed`
with reason containing `"Quota exceeded for instances: Requested 1,
but already used 200 of 200 instances"` (error code `Ecs.0204`, HTTP 403)

**Root Cause**: SWR enterprise instances are hosted on a shared CCE cluster
managed by the SWR service tenant. When the service tenant's ECS quota is full
(e.g., 200/200 instances used by other users' enterprise instances),
new instance creation fails. The error message is misleading — it refers to
the **SWR service tenant's** quota, not the user's own ECS quota.
The user's quota may show 0/200 used while still encountering this error.

**Diagnosis Steps**:

1. Check the job status to see the full error:

```bash
# Via SDK script
python scripts/swr_instance_helper.py show --instance_id=<instance-id>

# Via hcloud CLI (for job details, use ShowInstanceJob)
hcloud SWR ShowInstanceJob --job_id=<job-id> --cli-region=cn-north-4
```

2. Verify the error message contains `"Quota exceeded for instances"` with `"Ecs.0204"` error code

3. Confirm the user's own ECS quota is NOT the issue:

```bash
# User's quota is separate from the service tenant's quota
hcloud ECS ShowServerLimits --cli-region=cn-north-4
# maxTotalInstances: 200, totalInstancesUsed: 0 ← NOT the issue
```

**Solution**: This is a SWR service-side quota issue. Contact Huawei Cloud SWR team to expand the service tenant's ECS quota. No action is required on the user side.

**Error Log Example** (from `ShowInstanceJob`):

```
reason: [[CreateServiceTenantCCENode.DoError] wait cycle error, failed to create cce node:
  [[CreateNodeVM.DoError] wait create user node(name: swr-ee-<id>-registry-1, ...)
    job <job-id> failed: create machine job failed:
    {"sub_jobs":[{"entities":{"errorcode_message":"{\"forbidden\": {\"code\": 403,
      \"message\": \"Quota exceeded for instances: Requested 1, but already used 200 of 200 instances\"}}"},
    "error_code":"Ecs.0204","fail_reason":"CreateServerWithRootVolumeAndDataVolumeTask-fail: ..."}]}]
```

## Common Error Response Reference

| Error Code          | HTTP Status | Description                  | Recommended Action                    |
| ------------------- | ----------- | ---------------------------- | ------------------------------------- |
| `SVCSTG.SWR.401`    | 401         | Authentication failed        | Check AK/SK configuration            |
| `SVCSTG.SWR.403`    | 403         | Permission denied            | Check IAM policies                    |
| `SVCSTG.SWR.404`    | 404         | Resource not found           | Verify resource exists first          |
| `SVCSTG.SWR.409`    | 409         | Resource already exists      | Use Show operation to check           |
| `SVCSTG.SWR.400`    | 400         | Invalid parameter            | Check parameter format and rules      |
| `SVCSTG.SWR.400005` | 400         | Endpoint already exists / conflict | Check existing endpoints with ListInstanceInternalEndpoints before creating (see Pitfall 17) |
| `SVCSTG.SWR.500`    | 500         | Internal server error        | Retry or contact support              |
| `SVCSTG.SWR.429`    | 429         | Too many requests            | Add delay, reduce request rate        |
