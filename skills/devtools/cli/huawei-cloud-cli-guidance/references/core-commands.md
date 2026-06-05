# Huawei Cloud KooCLI Core Commands

## Overview

This document provides comprehensive examples of Huawei Cloud KooCLI core commands for managing cloud resources. These commands follow the standard format: `hcloud <service> <operation> [parameters] [options]`.

## Command Structure Rules

### Basic Command Format
```bash
hcloud <SERVICE> <OPERATION> [--parameter=value] [--cli-option=value]
```

### Authentication Options
```bash
# Profile mode (recommended for repeated use)
hcloud <SERVICE> <OPERATION> --cli-profile=<profile> --cli-region=<region>

# Explicit parameter mode (one-time use)
hcloud <SERVICE> <OPERATION> --cli-access-key=<AK> --cli-secret-key=<SK> --cli-region=<region>

# ECS Agency mode (when running on ECS with agency)
hcloud <SERVICE> <OPERATION> --cli-mode=ecsAgency --cli-region=<region>
```

### Output Format Options
```bash
# JSON format (default, recommended for automation)
hcloud <SERVICE> <OPERATION> --cli-output=json

# Table format (human readable)
hcloud <SERVICE> <OPERATION> --cli-output=table

# TSV format (for spreadsheet import)
hcloud <SERVICE> <OPERATION> --cli-output=tsv

# With JMESPath query filtering
hcloud <SERVICE> <OPERATION> --cli-output=json --cli-query="items[?status=='ACTIVE']"
```

## Compute Services

### ECS (Elastic Cloud Server)

#### Instance Management
```bash
# List all instances
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-output=json

# Get instance details
hcloud ECS ShowServer --server_id=i-12345678 --cli-region=cn-north-4

# Create instance
hcloud ECS CreateServers \
  --server.name=my-instance \
  --server.imageRef=img-ubuntu-22-04 \
  --server.flavorRef=ac8.large.2 \
  --server.vpcid=vpc-12345678 \
  --server.subnet_id=subnet-12345678 \
  --server.adminPass=MySecurePass123! \
  --server.security_groups.1.id=sg-12345678 \
  --server.publicip.eip.bandwidth.sharetype=PER \
  --server.publicip.eip.bandwidth.size=5 \
  --server.publicip.eip.bandwidth.charge_mode=bandwidth \
  --cli-region=cn-north-4 \
  --cli-output=json

# Delete instance
hcloud ECS DeleteServers \
  --servers.1.id=i-12345678 \
  --delete_publicip=true \
  --delete_volume=true \
  --cli-region=cn-north-4

# Instance operations
hcloud ECS NovaStartServers --os-start.servers.1.id=i-12345678 --cli-region=cn-north-4
hcloud ECS NovaStopServers --os-stop.servers.1.id=i-12345678 --cli-region=cn-north-4
hcloud ECS NovaRebootServers --os-reboot.servers.1.id=i-12345678 --cli-region=cn-north-4

# Remote console access
hcloud ECS ShowServerRemoteConsole \
  --server_id=i-12345678 \
  --remote_console.protocol=vnc \
  --remote_console.type=novnc \
  --cli-region=cn-north-4

# List available flavors
hcloud ECS ListFlavors --cli-region=cn-north-4 --cli-output=json
```

### CCE (Cloud Container Engine)

#### Cluster Management
```bash
# List clusters
hcloud CCE ListClusters --cli-region=cn-north-4 --cli-output=json

# Get cluster details
hcloud CCE ShowCluster --cluster_id=cluster-12345678 --cli-region=cn-north-4

# Create cluster
hcloud CCE CreateCluster \
  --metadata.name=my-cluster \
  --spec.type=VirtualMachine \
  --spec.version=v1.25 \
  --spec.flavor=cce.s2.small \
  --spec.hostNetwork.vpc_id=vpc-12345678 \
  --spec.hostNetwork.subnet_id=subnet-12345678 \
  --cli-region=cn-north-4 \
  --cli-output=json

# List nodes in cluster
hcloud CCE ListNodes --cluster_id=cluster-12345678 --cli-region=cn-north-4
```

## Network Services

### VPC (Virtual Private Cloud)

#### VPC Management
```bash
# List VPCs
hcloud VPC ListVpcs --cli-region=cn-north-4 --cli-output=json

# Get VPC details
hcloud VPC ShowVpc --vpc_id=vpc-12345678 --cli-region=cn-north-4

# List subnets
hcloud VPC ListSubnets --vpc_id=vpc-12345678 --cli-region=cn-north-4

# Get subnet details
hcloud VPC ShowSubnet --subnet_id=subnet-12345678 --cli-region=cn-north-4
```

#### Security Group Management
```bash
# List security groups (v3 API)
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4 --cli-output=json

# Get security group details
hcloud VPC ShowSecurityGroup/v3 --security_group_id=sg-12345678 --cli-region=cn-north-4

# List security group rules
hcloud VPC ListSecurityGroupRules/v3 --security_group_id.1=sg-12345678 --cli-region=cn-north-4

# Create security group rule
hcloud VPC CreateSecurityGroupRule/v3 \
  --security_group_id=sg-12345678 \
  --security_group_rule.direction=ingress \
  --security_group_rule.protocol=tcp \
  --security_group_rule.multiport=22 \
  --security_group_rule.remote_ip_prefix=0.0.0.0/0 \
  --security_group_rule.description="Allow SSH" \
  --cli-region=cn-north-4

# Delete security group rule
hcloud VPC DeleteSecurityGroupRule/v3 --security_group_rule_id=rule-12345678 --cli-region=cn-north-4
```

### EIP (Elastic IP)

#### EIP Management
```bash
# List EIPs (v3 API)
hcloud EIP ListPublicips/v3 --cli-region=cn-north-4 --cli-output=json

# Create EIP
hcloud EIP CreatePublicip/v3 \
  --publicip.type=EIP \
  --bandwidth.name=my-eip \
  --bandwidth.size=5 \
  --bandwidth.share_type=PER \
  --bandwidth.charge_mode=bandwidth \
  --cli-region=cn-north-4

# Associate EIP with instance
hcloud EIP AssociatePublicip/v3 \
  --publicip_id=eip-12345678 \
  --publicip_associate.instance_id=i-12345678 \
  --publicip_associate.instance_type=ECS \
  --cli-region=cn-north-4

# Disassociate EIP
hcloud EIP DisassociatePublicip/v3 --publicip_id=eip-12345678 --cli-region=cn-north-4

# Delete EIP
hcloud EIP DeletePublicip/v3 --publicip_id=eip-12345678 --cli-region=cn-north-4
```

## Storage Services

### EVS (Elastic Volume Service)

#### Volume Management
```bash
# List volumes
hcloud EVS ListVolumes --cli-region=cn-north-4 --cli-output=json

# Get volume details
hcloud EVS ShowVolume --volume_id=vol-12345678 --cli-region=cn-north-4

# Create volume
hcloud EVS CreateVolume \
  --volume.name=my-volume \
  --volume.size=100 \
  --volume.volume_type=SSD \
  --volume.availability_zone=cn-north-4a \
  --cli-region=cn-north-4

# Attach volume to instance
hcloud EVS AttachVolume \
  --volume_id=vol-12345678 \
  --server_id=i-12345678 \
  --device=/dev/vdb \
  --cli-region=cn-north-4

# Detach volume
hcloud EVS DetachVolume \
  --volume_id=vol-12345678 \
  --server_id=i-12345678 \
  --cli-region=cn-north-4

# Extend volume size
hcloud EVS ExtendVolume \
  --volume_id=vol-12345678 \
  --volume.size=200 \
  --cli-region=cn-north-4
```

## Database Services

### RDS (Relational Database Service)

#### Instance Management
```bash
# List RDS instances
hcloud RDS ListInstances --cli-region=cn-north-4 --cli-output=json

# Get instance details
hcloud RDS ShowInstance --instance_id=rds-12345678 --cli-region=cn-north-4

# Create RDS instance
hcloud RDS CreateInstance \
  --name=my-rds \
  --datastore.type=MySQL \
  --datastore.version=8.0 \
  --flavor_ref=rds.mysql.s1.large \
  --volume.type=ULTRAHIGH \
  --volume.size=100 \
  --availability_zone=cn-north-4a,cn-north-4b \
  --vpc_id=vpc-12345678 \
  --subnet_id=subnet-12345678 \
  --security_group_id=sg-12345678 \
  --password=MySecurePass123! \
  --cli-region=cn-north-4

# List backups
hcloud RDS ListBackups --instance_id=rds-12345678 --cli-region=cn-north-4
```

## Security Services

### IAM (Identity and Access Management)

#### User Management
```bash
# List users
hcloud IAM KeystoneListUsers --cli-region=cn-north-4 --cli-output=json

# Get user details
hcloud IAM KeystoneShowUser --user_id=user-12345678 --cli-region=cn-north-4

# List policies
hcloud IAM ListPolicies --cli-region=cn-north-4 --cli-output=json

# Get policy details
hcloud IAM ShowPolicy --policy_id=policy-12345678 --cli-region=cn-north-4

# List roles
hcloud IAM ListRoles --cli-region=cn-north-4 --cli-output=json

# List groups
hcloud IAM ListGroups --cli-region=cn-north-4 --cli-output=json
```

## Monitoring Services

### CES (Cloud Eye Service)

#### Metric Management
```bash
# List metrics
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=cn-north-4 --cli-output=json

# Get metric data
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=cpu_util \
  --dim.0=instance_id,i-12345678 \
  --from=1704067200000 \
  --to=1704153600000 \
  --period=300 \
  --filter=average \
  --cli-region=cn-north-4 \
  --cli-output=json

# List alarms
hcloud CES ListAlarms --cli-region=cn-north-4 --cli-output=json

# Get alarm details
hcloud CES ShowAlarm --alarm_id=alarm-12345678 --cli-region=cn-north-4
```

## Best Practices for Core Commands

### 1. Always Use Help Command First
```bash
# Check available services
hcloud --help

# Check operations for a specific service
hcloud ECS --help

# Check parameters for a specific operation
hcloud ECS ListServersDetails --help
```

### 2. Use JSON Output for Automation
```bash
# Always use --cli-output=json for script processing
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-output=json
```

### 3. Filter Results with JMESPath
```bash
# Filter active instances
hcloud ECS ListServersDetails \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --cli-query="servers[?status=='ACTIVE'].{ID:id,Name:name,Status:status,Flavor:flavor.name}"

# Filter by tag
hcloud ECS ListServersDetails \
  --cli-region=cn-north-4 \
  --cli-output=json \
  --cli-query="servers[?tags[?Key=='Environment' && Value=='production']]"
```

### 4. Use Debug Mode for Troubleshooting
```bash
# Enable debug mode to see request/response details
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-debug=true
```

### 5. Batch Operations
```bash
# Batch start instances
hcloud ECS NovaStartServers \
  --os-start.servers.1.id=i-12345678 \
  --os-start.servers.2.id=i-23456789 \
  --os-start.servers.3.id=i-34567890 \
  --cli-region=cn-north-4

# Batch stop instances
hcloud ECS NovaStopServers \
  --os-stop.servers.1.id=i-12345678 \
  --os-stop.servers.2.id=i-23456789 \
  --cli-region=cn-north-4
```

### 6. Parameter Validation
```bash
# Use --dry-run to validate parameters without execution
hcloud ECS CreateServers \
  --server.name=test-instance \
  --server.imageRef=img-ubuntu-22-04 \
  --server.flavorRef=ac8.large.2 \
  --cli-region=cn-north-4 \
  --dry-run
```

### 7. Script Examples

#### Create Instance with Variables
```bash
#!/bin/bash

# Define variables
INSTANCE_NAME="my-instance"
IMAGE_ID="img-ubuntu-22-04"
FLAVOR="ac8.large.2"
VPC_ID="vpc-12345678"
SUBNET_ID="subnet-12345678"
SG_ID="sg-12345678"
REGION="cn-north-4"

# Create instance
hcloud ECS CreateServers \
  --server.name="${INSTANCE_NAME}" \
  --server.imageRef="${IMAGE_ID}" \
  --server.flavorRef="${FLAVOR}" \
  --server.vpcid="${VPC_ID}" \
  --server.subnet_id="${SUBNET_ID}" \
  --server.security_groups.1.id="${SG_ID}" \
  --server.adminPass="$(openssl rand -base64 16)" \
  --cli-region="${REGION}" \
  --cli-output=json
```

#### Monitor Instance Status
```bash
#!/bin/bash

INSTANCE_ID="i-12345678"
REGION="cn-north-4"

# Get instance status
hcloud ECS ShowServer \
  --server_id="${INSTANCE_ID}" \
  --cli-region="${REGION}" \
  --cli-output=json \
  --cli-query="server.status"
```

## Common Command Patterns

### Resource Creation Pattern
1. **Check prerequisites** (VPC, subnet, security group)
2. **Validate parameters** using `--help` and `--dry-run`
3. **Create resource** with detailed configuration
4. **Verify creation** by querying resource status

### Resource Update Pattern
1. **Get current configuration**
2. **Prepare update parameters**
3. **Apply changes** with validation
4. **Verify update** success

### Resource Deletion Pattern
1. **Check dependencies** (attached resources)
2. **Confirm deletion** (use `--dry-run`)
3. **Execute deletion** with cleanup options
4. **Verify deletion** and cleanup

## Error Handling Examples

### Handle API Errors
```bash
# Use --cli-debug to see detailed error information
hcloud ECS ListServersDetails --cli-region=invalid-region --cli-debug=true
```

### Validate Before Execution
```bash
# Check if instance exists before operations
INSTANCE_STATUS=$(hcloud ECS ShowServer --server_id=i-12345678 --cli-region=cn-north-4 --cli-output=json --cli-query="server.status" 2>/dev/null || echo "NOT_FOUND")

if [ "$INSTANCE_STATUS" = "ACTIVE" ]; then
    echo "Instance is active, proceeding with operation..."
    # Perform operation
elif [ "$INSTANCE_STATUS" = "NOT_FOUND" ]; then
    echo "Instance not found, cannot proceed."
    exit 1
else
    echo "Instance status: $INSTANCE_STATUS"
fi
```

## Command Reference Quick Links

For complete command reference, see:
- `./references/service-catalog.md` - Full service catalog with commands
- `./references/parameter-format.md` - Parameter format rules
- `./references/common-workflows.md` - Common operation workflows
- `./references/cli-troubleshooting.md` - Error troubleshooting guide