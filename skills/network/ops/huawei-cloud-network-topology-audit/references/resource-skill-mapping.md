# Resource-Skill Mapping

## Overview

This document maps Huawei Cloud resource types to their corresponding query skills (path A) or
self-written scripts (path B). Resource types with an existing query skill in the repository use
path A; those without one use path B based on official documentation.

## Resource Type → Query Skill Mapping

| Resource Type | find-skills Keywords | Preferred Query Skill | Collection Path | Self-Written Script |
|---------------|---------------------|-----------------------|-----------------|---------------------|
| VPC / Subnet / Security Group / Route Table / EIP / ELB / NAT | vpc, security group, elb, nat, eip | huawei-cloud-network-query | A | — |
| ECS / NIC / Keypair | ecs | huawei-cloud-computing-query | A | — |
| RDS | rds, 关系型数据库 | huawei-cloud-rds-smart-service | A | — |
| CCE (cluster / node / service / ingress) | cce | huawei-cloud-cce-cluster-management | A | — |
| DCS (instance) | dcs | (no query skill found) | B | scripts/query-dcs-instances.py |

## Path A: Query Skills Reference

### huawei-cloud-network-query

- **Location**: `skills/network/ops/huawei-cloud-network-query/`
- **Capabilities**: VPCs, subnets, security groups, ELBs, EIPs, NAT gateways, VPN, DNS
- **Execution**: Python SDK scripts via `skill action=exec`
- **Key scripts**: `scripts/vpc/*`, `scripts/elb/*`, `scripts/eip/*`, `scripts/nat/*`

### huawei-cloud-computing-query

- **Location**: `skills/computing/ops/huawei-cloud-computing-query/`
- **Capabilities**: ECS instances, flavors, keypairs, quotas, server groups
- **Execution**: Python SDK scripts via `skill action=exec`

### huawei-cloud-rds-smart-service

- **Location**: `skills/storage/rds/huawei-cloud-rds-smart-service/`
- **Capabilities**: RDS instance listing, queries, diagnostics
- **Execution**: hcloud CLI or Python SDK

### huawei-cloud-cce-cluster-management

- **Location**: `skills/container/cce/huawei-cloud-cce-cluster-management/`
- **Capabilities**: List clusters, list nodes, cluster details
- **Execution**: hcloud CLI

## Path B: Self-Written Scripts

### DCS Instance Query

- **Script**: `scripts/query-dcs-instances.py`
- **SDK**: `huaweicloudsdkdcs.v2`
- **Purpose**: List DCS instances, security groups, ports for audit
- **Documentation**: See `references/official-doc-index.md` for API references

## Engine Steps 2/3 Usage

1. **Step 2** (Path Parsing): Read this table to map each recognized resource type to its
   collection path (A or B). Do NOT hardcode — use find-skills to re-verify the preferred
   query skill exists in the current index.
2. **Step 3** (Real Topology): For path A resources, invoke the target query skill. For path B
   resources, run the self-written script.
3. **Fallback**: If find-skills returns a different skill than what this table lists, use
   find-skills' result (the index is more current than this static reference).