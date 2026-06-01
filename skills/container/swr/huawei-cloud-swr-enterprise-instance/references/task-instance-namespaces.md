# Task: Instance Namespaces

## Overview

SWR enterprise instance namespaces organize repositories within an instance. Unlike basic SWR namespaces, instance namespaces support advanced features like automatic vulnerability scanning and image blocking. This task covers creating, listing, showing, updating, and deleting instance namespaces.

## Operations Catalog

| Operation                    | Method | Description              | Key Parameters                                  |
| ---------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateInstanceNamespace`    | POST   | 创建命名空间             | `--instance_id`, `--namespace_name`, `--metadata.public`, `--metadata.auto_scan`, `--metadata.prevent_vul`, `--metadata.severity` |
| `ListInstanceNamespaces`     | GET    | 获取命名空间列表         | `--instance_id`, `--limit`, `--offset`, `--name`, `--public` |
| `ShowInstanceNamespace`      | GET    | 获取命名空间详情         | `--instance_id`, `--namespace_name`             |
| `UpdateInstanceNamespace`    | PUT    | 修改命名空间             | `--instance_id`, `--namespace_name`, `--metadata.public`, `--metadata.auto_scan`, `--metadata.prevent_vul`, `--metadata.severity`, `--cve_allowlist` |
| `DeleteInstanceNamespace`    | DELETE | 删除命名空间             | `--instance_id`, `--namespace_name`             |

## Workflows

### W1: Create a Namespace

**Pre-creation Checklist**:
1. Verify instance is in `Running` status:
```bash
hcloud SWR ShowInstance --instance_id=<instance-id> --cli-region=cn-north-4
```
2. Decide namespace visibility (`metadata.public`)
3. Decide security scanning settings (auto_scan, prevent_vul, severity)

```bash
# Create a basic private namespace
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --cli-region=cn-north-4

# Create a namespace with full security features
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=prod-ns --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=high --cli-region=cn-north-4

# Create a public namespace (for shared images)
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=shared-images --metadata.public=true --metadata.auto_scan=true --metadata.prevent_vul=false --cli-region=cn-north-4

# Create a namespace with critical vulnerability blocking
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=secure-ns --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=critical --cli-region=cn-north-4
```

**Namespace Naming Rules**:
- Start with lowercase letter or digit
- Followed by lowercase letters, digits, dots (`.`), underscores (`_`), or hyphens (`-`)
- Dots, underscores, hyphens cannot be directly connected (e.g., `a._b` or `a.-b` invalid)
- End with lowercase letter or digit
- Length: 1-64 characters

**Security Scanning Parameters**:
- `metadata.auto_scan=true`: Automatically scan images on upload
- `metadata.prevent_vul=true`: Block pulling images that have vulnerabilities above the severity threshold
- `metadata.severity`: Vulnerability blocking threshold (`none`, `low`, `medium`, `high`, `critical`)

**Severity Behavior**:
- `none`: Block any image with any vulnerability
- `low`: Block images with low or higher severity vulnerabilities
- `medium`: Block images with medium or higher severity vulnerabilities
- `high`: Block images with high or critical severity vulnerabilities
- `critical`: Block only images with critical severity vulnerabilities

**Post-creation Verification**:

```bash
hcloud SWR ShowInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4
```

### W2: List Namespaces

```bash
# List all namespaces in instance
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4

# List namespaces with pagination
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by name
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --name=group-dev --cli-region=cn-north-4

# Filter by visibility (only private namespaces)
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --public=false --cli-region=cn-north-4

# Sort by update time (most recently updated first)
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --order_column=updated_at --order_type=desc --cli-region=cn-north-4
```

⚠️ **Pagination Note**: `offset` must be 0 or a multiple of `limit`. For example, with `limit=20`, valid offsets are 0, 20, 40, 60...

### W3: View Namespace Details

```bash
hcloud SWR ShowInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4
```

**Use Cases**:
- Check namespace visibility (public/private)
- Verify security scanning settings (auto_scan, prevent_vul, severity)
- View namespace metadata and configuration
- Check CVE whitelist settings

### W4: Update Namespace Settings

```bash
# Change namespace to public
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=true --cli-region=cn-north-4

# Enable auto-scan and vulnerability blocking
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=high --cli-region=cn-north-4

# Disable vulnerability blocking (keep auto-scan)
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=false --cli-region=cn-north-4

# Change blocking severity level
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --metadata.prevent_vul=true --metadata.severity=critical --cli-region=cn-north-4

# Update namespace with CVE whitelist
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --metadata.public=false --cve_allowlist.id=<whitelist-id> --cve_allowlist.namespace_id=<ns-id> --cve_allowlist.expires_at=1735689600 --cve_allowlist.items.1.cve_id=CVE-2023-44487 --cli-region=cn-north-4
```

⚠️ **Important**: `--metadata.public` is required even when only changing security settings. Always include it.

### W5: Delete a Namespace

⚠️ **CAUTION**: Deleting a namespace permanently removes ALL repositories and artifacts under it. This is irreversible.

**Pre-deletion Checklist**:
1. List all repositories in the namespace:
```bash
hcloud SWR ListInstanceRepositories --instance_id=<instance-id> --namespace_id=<ns-id> --cli-region=cn-north-4
```
2. Confirm with the user that ALL repositories and artifacts will be permanently deleted

```bash
hcloud SWR DeleteInstanceNamespace --instance_id=<instance-id> --namespace_name=group-dev --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404 or namespace not appear in list
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4
```

## Common Scenarios

### S1: Production Namespace with Full Security

Set up a production namespace with maximum security features:

```bash
# Create namespace with auto-scan and critical severity blocking
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=production --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=true --metadata.severity=critical --cli-region=cn-north-4
```

Images with any critical vulnerability will be blocked from pulling. All images are automatically scanned on upload.

### S2: Development Namespace with Relaxed Security

Set up a development namespace with minimal blocking:

```bash
# Create namespace with auto-scan but no blocking
hcloud SWR CreateInstanceNamespace --instance_id=<instance-id> --namespace_name=development --metadata.public=false --metadata.auto_scan=true --metadata.prevent_vul=false --cli-region=cn-north-4
```

Images are scanned on upload but can still be pulled regardless of vulnerabilities.

### S3: CVE Whitelist Management

Allow specific CVEs to bypass vulnerability blocking:

```bash
# Update namespace with CVE whitelist
hcloud SWR UpdateInstanceNamespace --instance_id=<instance-id> --namespace_name=production --metadata.public=false --cve_allowlist.id=<whitelist-id> --cve_allowlist.namespace_id=<ns-id> --cve_allowlist.expires_at=1735689600 --cve_allowlist.items.1.cve_id=CVE-2023-44487 --cve_allowlist.items.2.cve_id=CVE-2022-3176 --cli-region=cn-north-4
```

CVEs in the whitelist will not trigger blocking, even if their severity exceeds the threshold.

### S4: Namespace Audit

Review all namespaces and their security configurations:

```bash
# List all namespaces
hcloud SWR ListInstanceNamespaces --instance_id=<instance-id> --cli-region=cn-north-4

# Check each namespace's security settings
hcloud SWR ShowInstanceNamespace --instance_id=<instance-id> --namespace_name=<name> --cli-region=cn-north-4

# Verify namespace has proper security settings
# Expected: auto_scan=true, prevent_vul=true, severity=high for production
```