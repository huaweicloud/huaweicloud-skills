# IAM Policies - huawei-cloud-architecture-resource-archive

## Overview

This skill is a **read-only query tool** and only requires List/Show permissions of each service. It performs no modification operations. The read-only permissions required by all 35 services are listed below.

## Read-Only Permission List

### Compute

| API Action | Permission | Purpose |
|------------|------------|---------|
| ecs:servers:list | View instance list | Query ECS instances |
| ecs:servers:get | View instance details | Get instance details |
| bms:servers:list | View bare metal list | Query BMS instances |
| as:groups:list | View auto-scaling groups | Query AS groups |
| cci:deployments:list | View CCI deployments | Query CCI resources |

### Network

| API Action | Permission | Purpose |
|------------|------------|---------|
| vpc:vpcs:list | View VPC list | Query VPCs |
| vpc:subnets:get | View subnets | Query subnets |
| vpc:securityGroups:get | View security groups | Query security group rules |
| vpc:routeTables:list | View route tables | Query route tables |
| vpc:peerings:list | View peerings | Query VPC peerings |
| eip:publicips:list | View elastic public IPs | Query EIPs |
| elb:loadbalancers:list | View load balancers | Query ELBs |
| nat:natGateways:list | View NAT gateways | Query NAT gateways |
| vpn:gateways:list | View VPN gateways | Query VPN gateways |
| dns:zones:list | View DNS zones | Query DNS zones |
| er:instances:list | View ER instances | Query enterprise routers |

### Storage

| API Action | Permission | Purpose |
|------------|------------|---------|
| obs:bucket:list | View bucket list | Query OBS buckets |
| evs:volumes:list | View cloud volumes | Query EVS |
| sfs:shares:list | View file systems | Query SFS Turbo |

### Database

| API Action | Permission | Purpose |
|------------|------------|---------|
| rds:instances:list | View RDS instances | Query RDS |
| dcs:instances:list | View DCS instances | Query DCS caches |
| dds:instances:list | View DDS instances | Query document databases |
| gaussdb:instances:list | View GaussDB instances | Query GaussDB |
| css:clusters:list | View CSS clusters | Query Elasticsearch |
| mrs:clusters:list | View MRS clusters | Query MapReduce |

### Security

| API Action | Permission | Purpose |
|------------|------------|---------|
| iam:users:list | View user list | Query IAM users |
| waf:policies:list | View WAF policies | Query WAF |
| cnad:instances:list | View DDoS protection | Query CNAD |

### Middleware

| API Action | Permission | Purpose |
|------------|------------|---------|
| cce:clusters:list | View cluster list | Query CCE clusters |
| cce:clusters:get | View cluster details | Get cluster configuration |
| dms:instances:list | View DMS instances | Query message queues |

### Others

| API Action | Permission | Purpose |
|------------|------------|---------|
| rms:resources:list | View resource list | Resource quota query |
| eps:enterprises:list | View enterprise projects | Query enterprise projects |
| cdn:domains:list | View domain list | Query CDN |
| dli:jobs:list | View DLI jobs | Query data lake exploration |
| cloudtable:clusters:list | View clusters | Query CloudTable |

## Least-Privilege Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:list",
        "ecs:servers:get",
        "bms:servers:list",
        "as:groups:list",
        "vpc:vpcs:list",
        "vpc:subnets:get",
        "vpc:securityGroups:get",
        "vpc:routeTables:list",
        "vpc:peerings:list",
        "eip:publicips:list",
        "elb:loadbalancers:list",
        "nat:natGateways:list",
        "vpn:gateways:list",
        "dns:zones:list",
        "er:instances:list",
        "obs:bucket:list",
        "evs:volumes:list",
        "sfs:shares:list",
        "rds:instances:list",
        "dcs:instances:list",
        "dds:instances:list",
        "gaussdb:instances:list",
        "css:clusters:list",
        "mrs:clusters:list",
        "iam:users:list",
        "waf:policies:list",
        "cnad:instances:list",
        "cce:clusters:list",
        "cce:clusters:get",
        "dms:instances:list",
        "rms:resources:list",
        "eps:enterprises:list",
        "cdn:domains:list",
        "dli:jobs:list",
        "cloudtable:clusters:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Permission Failure Handling Flow

1. When any command fails due to a permission error (HTTP 403), read this document
2. Show the user the required permission list and the policy JSON above
3. Guide the user to create a custom policy and grant it in the IAM console
4. Pause execution and wait for the user to confirm the permission has been granted

## Permission Configuration Examples

✅ Correct: create a custom policy and grant read-only permissions

```bash
# Create a custom policy in the IAM console and paste the least-privilege policy JSON above
# Then grant the policy to the target IAM user/group
```

❌ Wrong: use the main account AK/SK directly (high security risk)

```bash
# Not recommended: run queries with main account credentials
export HW_ACCESS_KEY=<main-account-ak>
export HW_SECRET_KEY=<main-account-sk>
```
