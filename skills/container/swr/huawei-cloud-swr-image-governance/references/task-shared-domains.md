# Task: Shared Domains

## Overview

SWR shared download domains allow other organizations or users to download images from your repository without direct repository permissions. This task covers creating, listing, viewing, updating, and deleting shared download domains.

## Operations Catalog

| Operation          | Method | Description              | Key Parameters                                  |
| ------------------ | ------ | ------------------------ | ----------------------------------------------- |
| `ListRepoDomains`  | GET    | List shared accounts     | `--namespace`, `--repository`                   |
| `CreateRepoDomains` | POST  | Create shared account         | `--namespace`, `--repository`, `--access_domain`, `--deadline`, `--permit` |
| `ShowAccessDomain` | GET    | Show shared account details     | `--namespace`, `--repository`, `--access_domain` |
| `UpdateRepoDomains` | PATCH  | Update shared account         | `--namespace`, `--repository`, `--access_domain`, `--deadline`, `--permit` |
| `DeleteRepoDomains` | DELETE | Delete shared account         | `--namespace`, `--repository`, `--access_domain` |

## Workflows

### W1: List Shared Domains

```bash
# List all shared download domains for a repository
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

**Output Fields** (verified against actual API — flat JSON array):

```json
[
  {
    "namespace": "pancake",
    "repository": "openclaw-sandbox",
    "access_domain": "shijingcheng_test",
    "permit": "read",
    "deadline": "forever",
    "description": "",
    "creator_id": "05949eb5350010e21f85c017722182de",
    "creator_name": "hwstaff_p00506267",
    "created": "2026-04-28T09:18:19.830309Z",
    "updated": "2026-04-28T09:18:19.83031Z",
    "status": true
  }
]
```

**Key Fields**:
- `access_domain`: Domain name used for shared access
- `permit`: Permission type (`read`)
- `deadline`: Expiration — `forever` or specific date string
- `description`: Domain description
- `creator_id`/`creator_name`: Who created the domain
- `created`/`updated`: Timestamps (**NOT** `created_at`/`updated_at`)
- `status`: Whether the domain is active (boolean)

### W2: Create a Shared Domain

```bash
# Create a shared download domain
# --access_domain: Huawei Cloud IAM domain name (tenant name) of the target account to share with
# --deadline: Expiration time in UTC format; use "forever" for permanent access
# --permit: Permission type; currently only "read" is supported
hcloud SWR CreateRepoDomains --namespace=pancake --repository=openclaw-sandbox --access_domain=<iam-domain-name> --deadline=forever --permit=read --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name (path parameter)
- `--repository` (required): Repository name (path parameter)
- `--access_domain` (required, body): Huawei Cloud IAM domain name (shared tenant name) of the target account to share with. This is the account's domain name, not a custom identifier.
- `--deadline` (required, body): Expiration time in UTC format (e.g., `2025-12-31T23:59:59Z`). Use `forever` for permanent access.
- `--permit` (required, body): Permission type. Currently only `read` is supported.
- `--description` (optional, body): Human-readable description. Default: empty string.
- `--cli-region` (required): Region ID

**Post-creation Verification**:

```bash
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

### W3: View Shared Domain Details

```bash
hcloud SWR ShowAccessDomain --namespace=pancake --repository=openclaw-sandbox --access_domain=shijingcheng_test --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--access_domain` (required): Domain name to query
- `--cli-region` (required): Region ID

### W4: Update a Shared Domain

```bash
# Update domain permit or deadline
hcloud SWR UpdateRepoDomains --namespace=pancake --repository=openclaw-sandbox --access_domain=<iam-domain-name> --deadline=forever --permit=read --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--access_domain` (required, path): Huawei Cloud IAM domain name (shared tenant name) of the shared account
- `--deadline` (required, body): Expiration time in UTC format. Use `forever` for permanent access.
- `--permit` (required, body): Permission type. Currently only `read` is supported.
- `--description` (optional, body): Human-readable description. Default: empty string.
- `--cli-region` (required): Region ID

### W5: Delete a Shared Domain

⚠️ **CAUTION**: Deleting a shared domain removes the ability for external users to download images via this domain. **Users in the target organization will immediately receive authentication errors and be unable to pull images.** Coordinate with the target organization before proceeding.

```bash
hcloud SWR DeleteRepoDomains --namespace=pancake --repository=openclaw-sandbox --access_domain=shared-domain-name --cli-region=cn-north-4
```

**Parameters**:
- `--namespace` (required): Namespace name
- `--repository` (required): Repository name
- `--access_domain` (required): Domain name to delete
- `--cli-region` (required): Region ID

**Post-deletion Verification**:

```bash
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4
```

## Common Scenarios

### S1: Share Base Image with Other Teams

Allow other teams to pull your base image:

```bash
# Create a shared domain for the base image repository
hcloud SWR CreateRepoDomains --namespace=team-infra --repository=base-ubuntu --access_domain=team-infra-shared --deadline=forever --permit=read --cli-region=cn-north-4

# Verify the domain is active
hcloud SWR ShowAccessDomain --namespace=team-infra --repository=base-ubuntu --access_domain=team-infra-shared --cli-region=cn-north-4
```

### S2: Audit Shared Domains

Review all shared domains across repositories:

```bash
# For each repository, list shared domains
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4

# Check domain details
hcloud SWR ShowAccessDomain --namespace=pancake --repository=openclaw-sandbox --access_domain=<domain-name> --cli-region=cn-north-4
```

### S3: Clean Up Expired or Unnecessary Domains

Remove shared domains that are no longer needed:

```bash
# List domains to identify expired ones
hcloud SWR ListRepoDomains --namespace=pancake --repository=openclaw-sandbox --cli-region=cn-north-4

# Delete unnecessary domains
hcloud SWR DeleteRepoDomains --namespace=pancake --repository=openclaw-sandbox --access_domain=<domain-name> --cli-region=cn-north-4
```