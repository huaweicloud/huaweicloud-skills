# Task: Instance Domains

## Overview

SWR enterprise instance domains provide custom access URLs for the container registry. Each instance has a default domain assigned by SWR, and you can add custom domains with SSL certificates from SCM (SSL Certificate Manager). This task covers adding, listing, viewing, updating, and deleting custom domains.

## Operations Catalog

| Operation            | Method | Description              | Key Parameters                                  |
| -------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `AddDomainName`      | POST   | 增加域名                 | `--instance_id`, `--domain_name`, `--certificate_id` |
| `ListDomainNames`    | GET    | 查询当前实例的所有域名   | `--instance_id`, `--domain_name`, `--uid`       |
| `ShowDomainOverview` | GET    | 获取租户总览信息         | (none instance-specific)                        |
| `UpdateDomainName`   | PUT    | 更新域名                 | `--instance_id`, `--domainname_id`, `--certificate_id` |
| `DeleteDomainName`   | DELETE | 删除域名                 | `--instance_id`, `--domainname_id`              |

## Workflows

### W1: Add a Custom Domain

**Pre-creation Checklist**:
1. Obtain an SSL certificate from SCM (SSL Certificate Manager) for the domain
2. Get the SCM certificate ID
3. Configure DNS to point the domain to the instance endpoint
4. Verify the domain name follows naming rules

```bash
# Add a custom domain with SCM certificate
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=registry.example.com --certificate_id=<scm-cert-id> --cli-region=cn-north-4

# Add a wildcard domain
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=*.registry.example.com --certificate_id=<scm-cert-id> --cli-region=cn-north-4

# Add a domain for a specific subdomain
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=swr.mycompany.cn --certificate_id=<scm-cert-id> --cli-region=cn-north-4
```

**Domain Naming Rules**:
- Letters, digits, hyphens, and asterisks (wildcard only at start)
- Hyphens cannot be at start or end of individual strings
- At least two strings separated by dots
- Each individual string max 63 characters
- Total length max 100 characters
- Wildcard (`*`) can only appear at the start (e.g., `*.example.com`)

**Valid Examples**: `registry.example.com`, `*.registry.example.com`, `swr.mycompany.cn`
**Invalid Examples**: `-registry.example.com` (hyphen at start), `registry-.example.com` (hyphen at end), `**.example.com` (double wildcard)

**SCM Certificate Requirements**:
- The certificate must cover the domain name (exact match or wildcard)
- The certificate must be issued by a trusted CA
- The certificate must be active (not expired)

**Post-creation**:
- Configure DNS resolution: point the domain to the instance's public endpoint
- Verify domain resolves correctly before using it for docker operations

**Post-creation Verification**:

```bash
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4
```

### W2: List Domain Names

```bash
# List all domains for an instance
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4

# Filter by domain name
hcloud SWR ListDomainNames --instance_id=<instance-id> --domain_name=registry.example.com --cli-region=cn-north-4

# Filter by domain ID
hcloud SWR ListDomainNames --instance_id=<instance-id> --uid=<domain-id> --cli-region=cn-north-4
```

**Use Cases**:
- Verify custom domain was added correctly
- Find domain ID for update/delete operations
- Check domain status (Active, Pending, etc.)
- Review all domains including the default domain

### W3: View Domain Overview

```bash
hcloud SWR ShowDomainOverview --cli-region=cn-north-4
```

⚠️ **Note**: `ShowDomainOverview` is a tenant-level operation that returns overall domain overview for the current tenant, NOT specific to an instance. It provides a summary of domain configuration across the tenant's SWR resources.

### W4: Update Domain Certificate

When the SSL certificate expires or needs to be replaced, update the domain with a new certificate:

```bash
# Update domain with new SCM certificate
hcloud SWR UpdateDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --certificate_id=<new-scm-cert-id> --cli-region=cn-north-4
```

**Common Use Cases**:
- Replace expired SSL certificate
- Switch to a certificate from a different CA
- Update wildcard certificate coverage
- Renew certificate before expiration

**Pre-update Checklist**:
1. Obtain a new SCM certificate
2. Verify the new certificate covers the same domain name
3. Get the new SCM certificate ID

### W5: Delete a Custom Domain

⚠️ **Important**: The default domain assigned by SWR (e.g., `xxx.cn-north-4.myhuaweicloud.com`) **cannot** be deleted. Only custom domains added via `AddDomainName` can be removed.

```bash
# Delete a custom domain
hcloud SWR DeleteDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --cli-region=cn-north-4
```

**Pre-deletion Checklist**:
1. Verify no workloads are using the custom domain for image pull/push
2. Update DNS configuration if needed
3. Confirm with the user that the domain will be removed

**Post-deletion Verification**:

```bash
# Domain should not appear in list (only default domain remains)
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4
```

## Common Scenarios

### S1: Custom Domain Setup for Production

Set up a custom domain with HTTPS for a production registry:

```bash
# 1. Obtain SSL certificate from SCM for registry.mycompany.com
# (This is done via SCM console or CLI, not covered in this skill)

# 2. Add the custom domain to the instance
hcloud SWR AddDomainName --instance_id=<instance-id> --domain_name=registry.mycompany.com --certificate_id=<scm-cert-id> --cli-region=cn-north-4

# 3. Configure DNS: point registry.mycompany.com to instance's public endpoint
# (This is done via DNS provider, not covered in this skill)

# 4. Verify domain works for docker login:
# docker login registry.mycompany.com -u <username> -p <password>

# 5. Push images using custom domain:
# docker push registry.mycompany.com/namespace/repository:tag
```

### S2: Certificate Renewal

Renew an expiring SSL certificate for a custom domain:

```bash
# 1. Obtain new certificate from SCM
# 2. Update domain with new certificate
hcloud SWR UpdateDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --certificate_id=<new-scm-cert-id> --cli-region=cn-north-4

# 3. Verify domain still works
hcloud SWR ListDomainNames --instance_id=<instance-id> --domain_name=registry.mycompany.com --cli-region=cn-north-4
```

### S3: Domain Audit and Cleanup

Review and manage domains periodically:

```bash
# 1. List all domains
hcloud SWR ListDomainNames --instance_id=<instance-id> --cli-region=cn-north-4

# 2. Review domain status and certificate expiration

# 3. Renew certificates for domains approaching expiration
hcloud SWR UpdateDomainName --instance_id=<instance-id> --domainname_id=<domain-id> --certificate_id=<new-cert-id> --cli-region=cn-north-4

# 4. Remove unused custom domains
hcloud SWR DeleteDomainName --instance_id=<instance-id> --domainname_id=<unused-domain-id> --cli-region=cn-north-4

# 5. Check tenant-level domain overview
hcloud SWR ShowDomainOverview --cli-region=cn-north-4
```