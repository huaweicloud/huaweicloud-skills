# Task: Instance Artifacts

## Overview

SWR enterprise instance artifacts represent image versions (tags) within repositories. Enterprise instances provide advanced artifact management including vulnerability scanning, build history viewing, and security blocking. This task covers listing, viewing, scanning, and deleting artifacts.

## Operations Catalog

| Operation                            | Method | Description              | Key Parameters                                  |
| ------------------------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ListInstanceArtifacts`              | GET    | 获取制品版本列表         | `--instance_id`, `--namespace_name`, `--repository_name`, `--limit`, `--offset`, `--tags`, `--type` |
| `ListInstanceAllArtifacts`           | GET    | 获取所有制品版本列表     | `--instance_id`, `--limit`, `--marker`          |
| `ShowInstanceArtifact`               | GET    | 获取制品版本详情         | `--instance_id`, `--namespace_name`, `--repository_name`, `--reference`, `--with_scan_overview` |
| `ShowInstanceArtifactAddition`       | GET    | 获取制品附加信息         | `--instance_id`, `--namespace_name`, `--repository_name`, `--reference`, `--addition` |
| `ListInstanceArtifactVulnerabilities`| GET    | 获取制品漏洞信息         | `--instance_id`, `--namespace_name`, `--repository_name`, `--reference` |
| `StartManualScanning`                | POST   | 手动启动制品扫描         | `--instance_id`, `--namespace_name`, `--repository_name`, `--reference` |
| `DeleteInstanceArtifact`             | DELETE | 删除制品版本             | `--instance_id`, `--namespace_name`, `--repository_name`, `--reference` |

## Workflows

### W1: List Artifacts in a Repository

```bash
# List all artifacts in a repository
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# List artifacts with pagination
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --limit=20 --offset=0 --cli-region=cn-north-4

# Filter by type (IMAGE or CHART)
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --type=IMAGE --cli-region=cn-north-4

# Search by tag name (fuzzy match)
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --tags=v1.0 --cli-region=cn-north-4
```

⚠️ **Pagination Note**: `offset` must be 0 or a multiple of `limit` (0, 20, 40...).

### W2: List All Artifacts Across All Repositories

```bash
# List all artifacts in the instance
hcloud SWR ListInstanceAllArtifacts --instance_id=<instance-id> --cli-region=cn-north-4

# List with marker-based pagination
hcloud SWR ListInstanceAllArtifacts --instance_id=<instance-id> --limit=20 --marker=1 --cli-region=cn-north-4

# Next page
hcloud SWR ListInstanceAllArtifacts --instance_id=<instance-id> --limit=20 --marker=<next_marker> --cli-region=cn-north-4
```

⚠️ **Note**: `ListInstanceAllArtifacts` uses marker-based pagination (`--marker/--limit`), not offset/limit.

### W3: View Artifact Details

```bash
# Show artifact details (basic)
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --cli-region=cn-north-4

# Show artifact with vulnerability scan overview
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --with_scan_overview=true --cli-region=cn-north-4
```

**Key Fields** (response format needs verification):
- Artifact digest (SHA256 hash)
- Artifact size
- Push time
- Vulnerability scan summary (when `with_scan_overview=true`)

⚠️ **Important**: `--reference` must be the artifact's SHA256 digest, NOT the tag name. Obtain the digest from `ListInstanceArtifacts` first.

### W4: View Artifact Build History

```bash
hcloud SWR ShowInstanceArtifactAddition --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --addition=build_history --cli-region=cn-north-4
```

**Use Cases**:
- View Docker build history layers
- Check build commands and creation timestamps
- Debug image build issues

### W5: View Artifact Vulnerabilities

```bash
hcloud SWR ListInstanceArtifactVulnerabilities --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --cli-region=cn-north-4
```

**Use Cases**:
- Review detailed vulnerability report for an artifact
- Identify specific CVEs affecting an image
- Determine which vulnerabilities need remediation
- Cross-reference with namespace blocking severity settings

### W6: Start Manual Vulnerability Scan

```bash
hcloud SWR StartManualScanning --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --cli-region=cn-north-4
```

**Use Cases**:
- Re-scan an image after it was initially pushed without auto-scan
- Verify vulnerability status before promoting to production
- Trigger scan after updating vulnerability database

**Note**: If the namespace has `metadata.auto_scan=true`, images are automatically scanned on push. Manual scanning is needed only for images pushed before auto-scan was enabled, or for re-scanning.

### W7: Delete an Artifact

⚠️ **CAUTION**: Deleting an artifact permanently removes the image version. This is irreversible.

**Pre-deletion Checklist**:
1. Verify artifact exists and get its digest:
```bash
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```
2. Check if artifact is still being used (pulled by running containers)
3. Confirm with the user that the artifact will be permanently deleted

```bash
hcloud SWR DeleteInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:abc123def456... --cli-region=cn-north-4
```

**Post-deletion Verification**:

```bash
# Should return 404 or artifact should not appear in list
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

## Common Scenarios

### S1: Security Audit for Production Images

Review vulnerability status of production images before deployment:

```bash
# 1. List artifacts in production namespace
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=production --repository_name=my-app --type=IMAGE --cli-region=cn-north-4

# 2. For each artifact, check scan overview
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=production --repository_name=my-app --reference=sha256:abc123... --with_scan_overview=true --cli-region=cn-north-4

# 3. If vulnerabilities exist, review detailed report
hcloud SWR ListInstanceArtifactVulnerabilities --instance_id=<instance-id> --namespace_name=production --repository_name=my-app --reference=sha256:abc123... --cli-region=cn-north-4

# 4. If artifact was not auto-scanned, trigger manual scan
hcloud SWR StartManualScanning --instance_id=<instance-id> --namespace_name=production --repository_name=my-app --reference=sha256:abc123... --cli-region=cn-north-4
```

### S2: Image Cleanup and Storage Management

Periodically remove old image versions to manage storage:

```bash
# 1. List all artifacts sorted by update time
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4

# 2. Identify old/outdated artifacts

# 3. Delete outdated artifacts one by one
hcloud SWR DeleteInstanceArtifact --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --reference=sha256:old_digest... --cli-region=cn-north-4

# 4. Verify cleanup
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --cli-region=cn-north-4
```

### S3: Cross-Repository Artifact Search

Find specific artifacts across all repositories in the instance:

```bash
# Search across all repositories
hcloud SWR ListInstanceAllArtifacts --instance_id=<instance-id> --cli-region=cn-north-4

# Or search by tag name within a specific repository
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=group-dev --repository_name=my-app --tags=v2.0 --cli-region=cn-north-4
```

### S4: Pre-Deployment Vulnerability Check

Ensure an image is safe before deploying to production:

```bash
# 1. Get artifact digest
hcloud SWR ListInstanceArtifacts --instance_id=<instance-id> --namespace_name=staging --repository_name=my-app --tags=v2.1.0 --cli-region=cn-north-4

# 2. Check scan results
hcloud SWR ShowInstanceArtifact --instance_id=<instance-id> --namespace_name=staging --repository_name=my-app --reference=sha256:<digest> --with_scan_overview=true --cli-region=cn-north-4

# 3. If no scan results, trigger manual scan
hcloud SWR StartManualScanning --instance_id=<instance-id> --namespace_name=staging --repository_name=my-app --reference=sha256:<digest> --cli-region=cn-north-4

# 4. Review vulnerabilities
hcloud SWR ListInstanceArtifactVulnerabilities --instance_id=<instance-id> --namespace_name=staging --repository_name=my-app --reference=sha256:<digest> --cli-region=cn-north-4

# 5. If no blocking vulnerabilities, proceed with deployment
```