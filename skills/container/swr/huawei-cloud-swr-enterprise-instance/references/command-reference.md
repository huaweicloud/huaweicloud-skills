# SWR Enterprise Instance - Command Reference

## 1. Instance Lifecycle

**⚠️ hcloud CLI CreateInstance Bug**: The `hcloud SWR CreateInstance` command has a known bug where the
`--project_id` parameter appears twice (path and body) with the same name. hcloud CLI rejects duplicate
parameter names (`重复的参数:project_id`), making it impossible to use hcloud CLI for instance creation.
Use the Python SDK script as an alternative:

```bash
# ✅ CORRECT - Use Python SDK script for CreateInstance (bypasses hcloud bug)
python scripts/swr_instance_helper.py create --name=my-instance --spec=swr.ee.basic \
    --vpc_id=<vpc-id> --subnet_id=<subnet-id> \
    --enterprise_project_id=0 --description="My enterprise registry"

# ❌ BROKEN - hcloud CLI CreateInstance fails due to duplicate --project_id bug
# hcloud SWR CreateInstance --name=my-instance --spec=swr.ee.professional ...

# Other instance lifecycle commands work fine with hcloud CLI

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

## 2. Instance Namespaces

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

## 3. Instance Registries (Sync Targets)

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

## 4. Instance Repositories

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

## 5. Instance Artifacts (Image Versions)

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

## 6. Instance Credentials

```bash
# Create a long-term access credential
hcloud SWR CreateInstanceLtcredential --instance_id=<instance-id> --name=my-credential --cli-region=cn-north-4

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

## 7. Instance Endpoints (Network Access)

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

## 8. Instance Domains

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

## 9. Instance Statistics and Jobs

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