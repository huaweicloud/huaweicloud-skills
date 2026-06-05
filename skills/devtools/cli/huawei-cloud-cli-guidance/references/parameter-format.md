# KooCLI Parameter Format Rules and Examples

## Overview
KooCLI parameter formats have strict rules, and format errors are the most common CLI usage issues. This document details various parameter formats.

## Parameter Type Overview

| Type | Format | Example |
|------|--------|---------|
| Scalar parameter | `--key=value` | `--limit=10`, `--name=my-instance` |
| Boolean parameter | `--key=true/false` | `--delete_publicip=true` |
| Array parameter | `--key.1=val1 --key.2=val2` | `--servers.1.id=abc --servers.2.id=def` |
| Nested object | `--key.sub_key=value` | `--remote_console.protocol=vnc` |
| Array object | `--key.1.sub_key=value` | `--security_group_id.1=sg-xxx` |
| Enum parameter | `--key=<enum-value>` | `--filter=average` |

## 1. Scalar Parameters

Most basic parameter type, directly `--key=value` format.

```bash
# String
--server_id=3d1537a9-9090-4045-8a83-cc6f2c5bc4ac
--name=my-instance
--description="My ECS instance"

# Number
--limit=10
--offset=0
--bandwidth.size=5

# Boolean
--delete_publicip=true
--delete_volume=false
```

⚠️ **Note**: When values contain spaces or special characters, wrap with quotes:
```bash
# Correct
--description="Allow SSH from office"

# Error (shell will split spaces)
--description=Allow SSH from office
```

## 2. Array Parameters

Array parameters use **1-based indexing** (not 0!).

### Basic Arrays

```bash
# Security group ID array (VPC rule query)
--security_group_id.1=sg-abc123
--security_group_id.1=sg-abc123 --security_group_id.2=sg-def456

# Instance ID array (batch operations)
--servers.1.id=i-001 --servers.2.id=i-002 --servers.3.id=i-003

# Batch start
hcloud ECS NovaStartServers \
  --os-start.servers.1.id=i-001 \
  --os-start.servers.2.id=i-002 \
  --cli-region=cn-north-4

# Batch stop
hcloud ECS NovaStopServers \
  --os-stop.servers.1.id=i-001 \
  --os-stop.servers.2.id=i-002 \
  --cli-region=cn-north-4

# Batch reboot
hcloud ECS NovaRebootServers \
  --os-reboot.servers.1.id=i-001 \
  --os-reboot.servers.2.id=i-002 \
  --cli-region=cn-north-4
```

### Batch Delete

```bash
hcloud ECS DeleteServers \
  --servers.1.id=i-001 \
  --servers.2.id=i-002 \
  --delete_publicip=true \
  --delete_volume=true \
  --cli-region=cn-north-4
```

### Dimension Arrays (CES monitoring)

```bash
# Single dimension
--dim.0=instance_id,i-001

# Double dimension (disk metrics need instance_id + name)
--dim.0=instance_id,i-001 --dim.1=name,/dev/vda1
```

## 3. Nested Object Parameters

Nested objects use **dot-separated** hierarchical paths.

### VNC Remote Console

```bash
hcloud ECS ShowServerRemoteConsole \
  --server_id=i-001 \
  --remote_console.protocol=vnc \
  --remote_console.type=novnc \
  --cli-region=cn-north-4
```

### Security Group Rule Creation

```bash
hcloud VPC CreateSecurityGroupRule/v3 \
  --security_group_id=sg-001 \
  --security_group_rule.direction=ingress \
  --security_group_rule.protocol=tcp \
  --security_group_rule.multiport=22 \
  --security_group_rule.remote_ip_prefix=0.0.0.0/0 \
  --security_group_rule.description="Allow SSH" \
  --cli-region=cn-north-4
```

### Create Instance (server nested object)

```bash
hcloud ECS CreateServers \
  --server.name=my-instance \
  --server.imageRef=img-001 \
  --server.flavorRef=ac8.large.2 \
  --server.vpcid=vpc-001 \
  --server.subnet_id=subnet-001 \
  --server.adminPass=MyP@ssw0rd \
  --server.security_groups.1.id=sg-001 \
  --server.publicip.eip.bandwidth.sharetype=PER \
  --server.publicip.eip.bandwidth.size=5 \
  --server.publicip.eip.bandwidth.charge_mode=bandwidth \
  --cli-region=cn-north-4
```

### EIP Binding

```bash
hcloud EIP AssociatePublicip/v3 \
  --publicip_id=eip-001 \
  --publicip_associate.instance_id=i-001 \
  --publicip_associate.instance_type=ECS \
  --cli-region=cn-north-4
```

## 4. V3 Operation Suffix

Some VPC service operations require `/v3` suffix, which distinguishes API versions.

### Operations Requiring /v3 Suffix

| Operation | Full Format |
|-----------|------------|
| ListSecurityGroups | `ListSecurityGroups/v3` |
| ShowSecurityGroup | `ShowSecurityGroup/v3` |
| CreateSecurityGroup | `CreateSecurityGroup/v3` |
| DeleteSecurityGroup | `DeleteSecurityGroup/v3` |
| ListSecurityGroupRules | `ListSecurityGroupRules/v3` |
| CreateSecurityGroupRule | `CreateSecurityGroupRule/v3` |
| DeleteSecurityGroupRule | `DeleteSecurityGroupRule/v3` |

### Operations Not Requiring /v3 Suffix

| Operation | Format |
|-----------|--------|
| ListVpcs | `ListVpcs` |
| ShowVpc | `ShowVpc` |
| ListSubnets | `ListSubnets` |
| ShowSubnet | `ShowSubnet` |

### EIP Service Also Needs /v3

| Operation | Full Format |
|-----------|------------|
| ListPublicips | `ListPublicips/v3` |
| CreatePublicip | `CreatePublicip/v3` |
| DeletePublicip | `DeletePublicip/v3` |
| AssociatePublicip | `AssociatePublicip/v3` |
| DisassociatePublicip | `DisassociatePublicip/v3` |

## 5. Enumeration Value Reference

### Instance Status
| Value | Description |
|-------|-------------|
| ACTIVE | Running |
| SHUTOFF | Shut down |
| ERROR | Error |
| BUILD | Creating |
| REBUILD | Rebuilding |
| HARD_REBOOT | Hard rebooting |
| REBOOT | Rebooting |
| MIGRATING | Migrating |
| RESIZE | Resizing |
| VERIFY_RESIZE | Waiting for resize confirmation |
| LOCKED | Locked |
| PAUSED | Paused |
| SUSPENDED | Suspended |
| SHELVED | Shelved |
| SHELVED_OFFLOADED | Shelved offloaded |

### EIP Status
| Value | Description |
|-------|-------------|
| FREE | Not bound |
| ACTIVE | Bound |
| DOWN | Not activated |
| ERROR | Error |

### Security Group Rule Direction
| Value | Description |
|-------|-------------|
| ingress | Inbound |
| egress | Outbound |

### Security Group Rule Protocol
| Value | Description |
|-------|-------------|
| tcp | TCP protocol |
| udp | UDP protocol |
| icmp | ICMP protocol |

### CES Metric Filter
| Value | Description |
|-------|-------------|
| average | Average |
| max | Maximum |
| min | Minimum |
| variance | Variance |
| sum | Sum |

### CES Metric Period
| Value | Description |
|-------|-------------|
| 1 | Real-time |
| 60 | 1 minute |
| 300 | 5 minutes |
| 1200 | 20 minutes |
| 3600 | 1 hour |
| 14400 | 4 hours |
| 86400 | 1 day |

### Bandwidth Sharing Type
| Value | Description |
|-------|-------------|
| PER | Dedicated bandwidth |
| WHOLE | Shared bandwidth |

### Bandwidth Billing Mode
| Value | Description |
|-------|-------------|
| bandwidth | Bandwidth billing |
| traffic | Traffic billing |

## 6. Common Format Errors

| Wrong Format | Correct Format | Description |
|-------------|---------------|-------------|
| `hcloud ecs ListServers` | `hcloud ECS ListServersDetails` | Service name uppercase |
| `--region=cn-north-4` | `--cli-region=cn-north-4` | Region parameter name |
| `--limit 10` | `--limit=10` | Equal sign connection |
| `--servers=[id1,id2]` | `--servers.1.id=id1 --servers.2.id=id2` | Array format |
| `--remote_console={protocol:vnc}` | `--remote_console.protocol=vnc` | Nested object format |
| `hcloud VPC ListPublicips` | `hcloud EIP ListPublicips/v3` | EIP independent service |
| `hcloud VPC ListSecurityGroups` | `hcloud VPC ListSecurityGroups/v3` | v3 suffix |
| `--os-start.1=<id>` | `--os-start.servers.1.id=<id>` | Batch operation format |
| `--delete_publicip` | `--delete_publicip=true` | Boolean requires explicit value |
| `--dim=instance_id:id` | `--dim.0=instance_id,id` | Dimensions comma-separated |

## 7. Parameter Format Checklist

### Check Steps
1. **Service name uppercase**: `hcloud ECS` not `hcloud ecs`
2. **Operation name correct**: `ListServersDetails` not `ListServers`
3. **Parameter name correct**: Use `--help` to view exact parameter names
4. **Array indexing starts from 1**: `--servers.1.id` not `--servers.0.id`
5. **Nested objects use dots**: `--server.name` not `--server[name]`
6. **Boolean values explicit**: `--delete_publicip=true` not `--delete_publicip`
7. **Strings with quotes**: `--description="My instance"` when containing spaces
8. **V3 suffix**: Security group and EIP operations need `/v3`

### Verification Commands
```bash
# View operation help to confirm parameters
hcloud <SERVICE> <OPERATION> --help

# Test command (not actually executed)
hcloud <SERVICE> <OPERATION> --dry-run --cli-region=cn-north-4

# View parameter list
hcloud <SERVICE> <OPERATION> --list-parameters --cli-region=cn-north-4
```

## 8. Best Practices

### Parameter Organization
```bash
# Organize parameters by functional groups
hcloud ECS CreateServers \
  # Basic parameters
  --server.name=my-instance \
  --server.imageRef=img-001 \
  --server.flavorRef=ac8.large.2 \
  --server.adminPass=MyP@ssw0rd \
  # Network parameters
  --server.vpcid=vpc-001 \
  --server.subnet_id=subnet-001 \
  --server.security_groups.1.id=sg-001 \
  # EIP parameters
  --server.publicip.eip.bandwidth.sharetype=PER \
  --server.publicip.eip.bandwidth.size=5 \
  --server.publicip.eip.bandwidth.charge_mode=bandwidth \
  # System parameters
  --cli-region=cn-north-4 \
  --cli-output=json
```

### Variable Usage
```bash
# Use variables for better readability
INSTANCE_NAME="my-instance"
IMAGE_ID="img-001"
VPC_ID="vpc-001"
SUBNET_ID="subnet-001"
SG_ID="sg-001"

hcloud ECS CreateServers \
  --server.name="${INSTANCE_NAME}" \
  --server.imageRef="${IMAGE_ID}" \
  --server.vpcid="${VPC_ID}" \
  --server.subnet_id="${SUBNET_ID}" \
  --server.security_groups.1.id="${SG_ID}" \
  --cli-region=cn-north-4
```

### Error Debugging
```bash
# Enable debug mode
hcloud <SERVICE> <OPERATION> \
  --cli-debug=true \
  --cli-region=cn-north-4

# View raw requests
hcloud <SERVICE> <OPERATION> \
  --cli-output=raw \
  --cli-region=cn-north-4
```