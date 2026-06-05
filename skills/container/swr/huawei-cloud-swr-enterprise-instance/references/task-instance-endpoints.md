# Task: Instance Endpoints

## Overview

SWR enterprise instance endpoints define network access paths for the registry. Enterprise instances support two types of access: internal VPC endpoints (for within-network access) and public access endpoints (with IP whitelist for controlled external access). This task covers creating, listing, showing, deleting internal endpoints, and managing public access.

## Operations Catalog

| Operation                        | Method | Description              | Key Parameters                                  |
| -------------------------------- | ------ | ------------------------ | ----------------------------------------------- |
| `CreateInstanceInternalEndpoint` | POST   | 新增内网访问             | `--instance_id`, `--vpc_id`, `--subnet_id`, `--project_id`, `--description` |
| `ListInstanceInternalEndpoints`  | GET    | 获取内网访问列表         | `--instance_id`, `--limit`, `--offset`          |
| `ShowInstanceInternalEndpoint`   | GET    | 查询内网访问详情         | `--instance_id`, `--internal_endpoints_id`      |
| `DeleteInstanceInternalEndpoint` | DELETE | 删除内网访问             | `--instance_id`, `--internal_endpoints_id`      |
| `CreateInstanceEndpointPolicy`   | POST   | 开启或关闭公网访问       | `--instance_id`, `--enable`                     |
| `ShowInstanceEndpointPolicy`     | GET    | 获取公网访问信息         | `--instance_id`                                 |
| `UpdateInstanceEndpointPolicy`   | PUT    | 更新公网访问白名单       | `--instance_id`, `--ip_list.[N].ip`, `--ip_list.[N].description` |

## Workflows

### W1: Create an Internal VPC Endpoint

Internal endpoints provide private access to the registry from within a VPC, without traversing the public internet.

**Pre-creation Checklist**:
1. Verify VPC and subnet exist
2. Verify the VPC/subnet project ID matches the VPC location
3. Ensure the VPC is in the same region as the instance

```bash
# Create an internal endpoint (basic)
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<vpc-id> --subnet_id=<subnet-id> --project_id=<vpc-project-id> --cli-region=cn-north-4

# Create with description
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<vpc-id> --subnet_id=<subnet-id> --project_id=<vpc-project-id> --description="Production VPC access" --cli-region=cn-north-4
```

**Parameters**:
- `--instance_id` (required, path): Instance ID
- `--vpc_id` (required, body): VPC ID where access is needed
- `--subnet_id` (required, body): Subnet ID within the VPC
- `--project_id` (required, body): Project ID where VPC/subnet reside (may differ from auto-filled path project_id)
- `--description` (optional, body): Endpoint description

⚠️ **Note**: The body `--project_id` specifies the project where the VPC/subnet reside. This may be different from the instance project. If the VPC/subnet are in the same project as the instance, they can be the same value.

**Post-creation Verification**:

```bash
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4
```

### W2: List Internal Endpoints

```bash
# List all internal endpoints
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4

# List with pagination
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --limit=20 --offset=0 --cli-region=cn-north-4
```

### W3: Show Internal Endpoint Details

```bash
hcloud SWR ShowInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4
```

**Use Cases**:
- Get the endpoint URL for docker login configuration
- Verify endpoint status (active/inactive)
- Check VPC/subnet mapping for the endpoint

### W4: Delete an Internal Endpoint

```bash
hcloud SWR DeleteInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4
```

⚠️ **Warning**: Deleting an internal endpoint removes VPC access. Containers in the affected VPC will no longer be able to pull/push images from the instance.

**Best Practice**: Before deleting, verify that no workloads in the VPC are actively using the endpoint.

### W5: Enable Public Access

Public access allows external connections to the instance, controlled by an IP whitelist.

```bash
# Enable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=true --cli-region=cn-north-4
```

**Status Constraints**:
- Can only enable when current status is `Disable` or `EnableFailed`
- Cannot enable if status is `Enable` (already enabled)

**Post-enable Verification**:

```bash
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4
```

### W6: Disable Public Access

```bash
# Disable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=false --cli-region=cn-north-4
```

**Status Constraints**:
- Can only disable when current status is `Enable` or `DisableFailed`
- Cannot disable if status is `Disable` (already disabled)

### W7: View Public Access Status and Whitelist

```bash
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4
```

**Use Cases**:
- Check if public access is enabled or disabled
- View current IP whitelist configuration
- Verify whitelist entries before updating

### W8: Update Public Access Whitelist

⚠️ **Important**: Whitelist update is a **full replacement** operation. All existing entries are replaced by the new entries provided. To add entries, include all existing ones plus the new ones.

**Pre-update Checklist**:
1. View current whitelist:
```bash
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4
```
2. Include all existing entries plus any new entries in the update command

```bash
# Set a single IP whitelist entry
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.1.100 --ip_list.1.description="Build server" --cli-region=cn-north-4

# Set multiple IP whitelist entries
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Internal network" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="VPN access" --ip_list.3.ip=203.0.113.50 --ip_list.3.description="External CI server" --cli-region=cn-north-4

# Add a new entry while keeping existing ones (must re-specify all)
# Assume existing entries are 10.0.0.0/8 and 192.168.0.0/16
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Internal network" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="VPN access" --ip_list.3.ip=172.16.0.0/12 --ip_list.3.description="New: Docker network" --cli-region=cn-north-4

# Allow all IPs (for fully public access, use with caution)
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=0.0.0.0/0 --ip_list.1.description="Allow all" --cli-region=cn-north-4
```

**IP Whitelist Format**:
- `--ip_list.[N].ip`: IP address or CIDR range (e.g., `10.0.1.100` or `10.0.0.0/8`)
- `--ip_list.[N].description`: Description for the entry
- Indexed array format starting from 1

## Common Scenarios

### S1: Production Instance Network Setup

Set up network access for a production instance with both VPC internal and controlled public access:

```bash
# 1. Create internal endpoint for production VPC
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<prod-vpc-id> --subnet_id=<prod-subnet-id> --project_id=<prod-project-id> --description="Production VPC" --cli-region=cn-north-4

# 2. Create internal endpoint for CI/CD VPC
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<ci-vpc-id> --subnet_id=<ci-subnet-id> --project_id=<ci-project-id> --description="CI/CD VPC" --cli-region=cn-north-4

# 3. Enable public access with IP whitelist for external CI servers
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=true --cli-region=cn-north-4

# 4. Configure IP whitelist
hcloud SWR UpdateInstanceEndpointPolicy --instance_id=<instance-id> --ip_list.1.ip=10.0.0.0/8 --ip_list.1.description="Production VPC" --ip_list.2.ip=192.168.0.0/16 --ip_list.2.description="VPN access" --ip_list.3.ip=203.0.113.50 --ip_list.3.description="External CI server" --cli-region=cn-north-4
```

### S2: Disable Public Access for Security

Disable public access during a security incident:

```bash
# 1. Check current public access status
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4

# 2. Disable public access
hcloud SWR CreateInstanceEndpointPolicy --instance_id=<instance-id> --enable=false --cli-region=cn-north-4

# 3. Verify public access is disabled
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4
```

### S3: Add VPC Endpoint for New Environment

Add internal access for a new development environment:

```bash
# Create endpoint for development VPC
hcloud SWR CreateInstanceInternalEndpoint --instance_id=<instance-id> --vpc_id=<dev-vpc-id> --subnet_id=<dev-subnet-id> --project_id=<dev-project-id> --description="Development VPC access" --cli-region=cn-north-4

# Verify new endpoint
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4
```

### S4: Endpoint Audit

Review all network access configurations:

```bash
# 1. List all internal endpoints
hcloud SWR ListInstanceInternalEndpoints --instance_id=<instance-id> --cli-region=cn-north-4

# 2. Check each endpoint details
hcloud SWR ShowInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<endpoint-id> --cli-region=cn-north-4

# 3. Review public access configuration
hcloud SWR ShowInstanceEndpointPolicy --instance_id=<instance-id> --cli-region=cn-north-4

# 4. Remove unused endpoints
hcloud SWR DeleteInstanceInternalEndpoint --instance_id=<instance-id> --internal_endpoints_id=<unused-id> --cli-region=cn-north-4
```