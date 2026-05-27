# Common Operation Workflows

## Overview
This document provides complete CLI workflows for common Huawei Cloud operations, from start to finish. Each workflow includes complete command sequences and parameter explanations.

## Workflow 1: Create ECS Instance (Complete Process)

### Steps

```bash
# 1. View available flavors
hcloud ECS ListFlavors --cli-region=cn-north-4

# 2. View available images (via IMS service)
hcloud IMS ListImages --cli-region=cn-north-4 --limit=10

# 3. View VPC and subnets
hcloud VPC ListVpcs --cli-region=cn-north-4
hcloud VPC ListSubnets --cli-region=cn-north-4

# 4. View security groups
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4

# 5. Create instance
hcloud ECS CreateServers \
  --server.name=my-instance \
  --server.imageRef=<image-id> \
  --server.flavorRef=ac8.large.2 \
  --server.vpcid=<vpc-id> \
  --server.subnet_id=<subnet-id> \
  --server.security_groups.1.id=<sg-id> \
  --server.adminPass=MyP@ssw0rd123! \
  --server.publicip.eip.bandwidth.sharetype=PER \
  --server.publicip.eip.bandwidth.size=5 \
  --server.publicip.eip.bandwidth.charge_mode=bandwidth \
  --cli-region=cn-north-4

# 6. Wait for creation to complete (poll status)
hcloud ECS ShowServer --server_id=<new-id> --cli-region=cn-north-4
# Until status=ACTIVE

# 7. Verify SSH connection
sshpass -p 'MyP@ssw0rd123!' ssh -o StrictHostKeyChecking=no root@<public-ip> "echo OK"
```

## Workflow 2: Create VPC + Subnet + Security Group + Instance

### Steps

```bash
# 1. Create VPC
hcloud VPC CreateVpc --vpc.name=my-vpc --vpc.cidr=10.0.0.0/16 --cli-region=cn-north-4
# Record returned vpc.id

# 2. Create subnet
hcloud VPC CreateSubnet \
  --subnet.name=my-subnet \
  --subnet.cidr=10.0.1.0/24 \
  --subnet.vpc_id=<vpc-id> \
  --subnet.gateway_ip=10.0.1.1 \
  --cli-region=cn-north-4
# Record returned subnet.id

# 3. Create security group
hcloud VPC CreateSecurityGroup/v3 \
  --security_group.name=my-sg \
  --security_group.vpc_id=<vpc-id> \
  --cli-region=cn-north-4
# Record returned security_group.id

# 4. Add security group rules
# SSH inbound
hcloud VPC CreateSecurityGroupRule/v3 \
  --security_group_id=<sg-id> \
  --security_group_rule.direction=ingress \
  --security_group_rule.protocol=tcp \
  --security_group_rule.multiport=22 \
  --security_group_rule.remote_ip_prefix=0.0.0.0/0 \
  --security_group_rule.description="Allow SSH" \
  --cli-region=cn-north-4

# HTTP inbound
hcloud VPC CreateSecurityGroupRule/v3 \
  --security_group_id=<sg-id> \
  --security_group_rule.direction=ingress \
  --security_group_rule.protocol=tcp \
  --security_group_rule.multiport=80 \
  --security_group_rule.remote_ip_prefix=0.0.0.0/0 \
  --security_group_rule.description="Allow HTTP" \
  --cli-region=cn-north-4

# 5. Create ECS instance (using newly created resources)
hcloud ECS CreateServers \
  --server.name=my-instance \
  --server.imageRef=<image-id> \
  --server.flavorRef=ac8.large.2 \
  --server.vpcid=<vpc-id> \
  --server.subnet_id=<subnet-id> \
  --server.security_groups.1.id=<sg-id> \
  --server.adminPass=MyP@ssw0rd123! \
  --server.publicip.eip.bandwidth.sharetype=PER \
  --server.publicip.eip.bandwidth.size=5 \
  --server.publicip.eip.bandwidth.charge_mode=bandwidth \
  --cli-region=cn-north-4
```

## Workflow 3: Add Security Group Rules to Instance

### Steps

```bash
# 1. View instance's security groups
hcloud ECS ShowServer --server_id=<instance-id> --cli-region=cn-north-4
# Get sg-id from returned security_groups

# 2. View current rules
hcloud VPC ShowSecurityGroup/v3 --security_group_id=<sg-id> --cli-region=cn-north-4

# 3. Add rule (e.g., add HTTPS)
hcloud VPC CreateSecurityGroupRule/v3 \
  --security_group_id=<sg-id> \
  --security_group_rule.direction=ingress \
  --security_group_rule.protocol=tcp \
  --security_group_rule.multiport=443 \
  --security_group_rule.remote_ip_prefix=0.0.0.0/0 \
  --security_group_rule.description="Allow HTTPS" \
  --cli-region=cn-north-4

# 4. Verify rule is effective
hcloud VPC ShowSecurityGroup/v3 --security_group_id=<sg-id> --cli-region=cn-north-4

# 5. Test port connectivity
nc -zv <public-ip> 443
```

## Workflow 4: Bind/Unbind Elastic Public IP

### Bind EIP to Instance

```bash
# 1. Apply for EIP
hcloud EIP CreatePublicip/v3 \
  --publicip.type=EIP \
  --bandwidth.name=my-eip-bw \
  --bandwidth.size=5 \
  --bandwidth.share_type=PER \
  --bandwidth.charge_mode=bandwidth \
  --cli-region=cn-north-4
# Record returned publicip_id and publicip_address

# 2. Bind to instance
hcloud EIP AssociatePublicip/v3 \
  --publicip_id=<eip-id> \
  --publicip_associate.instance_id=<instance-id> \
  --publicip_associate.instance_type=ECS \
  --cli-region=cn-north-4

# 3. Verify binding
hcloud EIP ListPublicips/v3 --cli-region=cn-north-4
```

### Unbind and Release EIP

```bash
# 1. Unbind
hcloud EIP DisassociatePublicip/v3 \
  --publicip_id=<eip-id> \
  --cli-region=cn-north-4

# 2. Release EIP
hcloud EIP DeletePublicip/v3 \
  --publicip_id=<eip-id> \
  --cli-region=cn-north-4
```

## Workflow 5: Expand Cloud Disk

### Steps

```bash
# 1. View current cloud disks
hcloud EVS ListVolumes --cli-region=cn-north-4

# 2. View disk details
hcloud EVS ShowVolume --volume_id=<vol-id> --cli-region=cn-north-4

# 3. Expand (online expansion, no downtime required)
hcloud EVS ExtendVolume \
  --volume_id=<vol-id> \
  --volume.size=<new-size-gb> \
  --cli-region=cn-north-4

# 4. SSH login to extend filesystem
sshpass -p '<password>' ssh root@<ip> "
  # View disks
  lsblk
  # Expand partition (e.g., /dev/vda1)
  growpart /dev/vda 1
  # Extend filesystem
  resize2fs /dev/vda1   # ext4
  # or xfs_growfs /       # xfs
"
```

## Workflow 6: Clean Up Resources (Delete Instance + Release Resources)

### Steps

```bash
# 1. List all instances
hcloud ECS ListServersDetails --cli-region=cn-north-4

# 2. Delete instance (simultaneously release EIP and cloud disk)
hcloud ECS DeleteServers \
  --servers.1.id=<instance-id> \
  --delete_publicip=true \
  --delete_volume=true \
  --cli-region=cn-north-4

# 3. Confirm deletion completed
hcloud ECS ListServersDetails --cli-region=cn-north-4

# 4. Clean up security group (if no longer needed)
hcloud VPC DeleteSecurityGroup/v3 \
  --security_group_id=<sg-id> \
  --cli-region=cn-north-4

# 5. Clean up VPC and subnet (if no longer needed)
hcloud VPC DeleteSubnet --vpc_id=<vpc-id> --subnet_id=<subnet-id> --cli-region=cn-north-4
hcloud VPC DeleteVpc --vpc_id=<vpc-id> --cli-region=cn-north-4
```

## Workflow 7: View Monitoring Metrics

### Steps

```bash
# 1. View available metrics
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=cn-north-4

# 2. View CPU utilization (last 1 hour)
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=cpu_util \
  --dim.0=instance_id,<instance-id> \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region=cn-north-4

# 3. View memory utilization
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=mem_util \
  --dim.0=instance_id,<instance-id> \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region=cn-north-4

# 4. View disk utilization
hcloud CES ShowMetricData \
  --namespace=SYS.ECS \
  --metric_name=disk_util_inband \
  --dim.0=instance_id,<instance-id> \
  --dim.1=name,/dev/vda1 \
  --from=$(date -d '1 hour ago' +%s)000 \
  --to=$(date +%s)000 \
  --period=300 \
  --filter=average \
  --cli-region=cn-north-4

# 5. View alarms
hcloud CES ListAlarms --cli-region=cn-north-4
```

## Workflow 8: SSH Deep Diagnostics

### Prerequisites
- Instance has public IP
- Security group allows port 22
- Know root password

### Steps

```bash
# 1. Basic connection test
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no root@<ip> "echo OK"

# 2. System overview
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no root@<ip> "
  echo '=== System ===' && uname -a
  echo '=== Uptime ===' && uptime
  echo '=== Memory ===' && free -h
  echo '=== Disk ===' && df -h
  echo '=== CPU ===' && nproc
"

# 3. Network check
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no root@<ip> "
  echo '=== Interfaces ===' && ip addr show
  echo '=== Routes ===' && ip route show
  echo '=== Listening ===' && ss -tlnp
  echo '=== Firewall ===' && (iptables -L -n 2>/dev/null || firewall-cmd --list-all 2>/dev/null)
"

# 4. Process check
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no root@<ip> "
  echo '=== Top CPU ===' && ps aux --sort=-%cpu | head -10
  echo '=== Top Mem ===' && ps aux --sort=-%mem | head -10
  echo '=== Failed ===' && systemctl list-units --state=failed
"

# 5. Log check
sshpass -p '<password>' ssh -o StrictHostKeyChecking=no root@<ip> "
  echo '=== Errors ===' && (tail -200 /var/log/syslog 2>/dev/null || tail -200 /var/log/messages 2>/dev/null) | grep -i 'error\\|fail' | tail -20
"
```

### Use VNC when SSH fails

```bash
# Get VNC console URL
hcloud ECS ShowServerRemoteConsole \
  --server_id=<instance-id> \
  --remote_console.protocol=vnc \
  --remote_console.type=novnc \
  --cli-region=cn-north-4
# Open URL in browser for console operations
```

## Usage Instructions

### Common Parameters
All commands require the following parameters:
- `--cli-region=<region>`: Specify region (e.g., cn-north-4)
- `--cli-profile=<profile>`: Specify configuration profile (optional)
- `--cli-output=json`: Specify JSON output format (recommended)

### Variable Substitution
All `<placeholder>` need to be replaced with actual values:
- `<image-id>`: Image ID
- `<vpc-id>`: VPC ID
- `<subnet-id>`: Subnet ID
- `<sg-id>`: Security group ID
- `<instance-id>`: Instance ID
- `<vol-id>`: Cloud disk ID
- `<eip-id>`: Elastic public IP ID
- `<ip>`: Instance public IP
- `<password>`: Instance root password

### Security Considerations
1. Use strong passwords (e.g., MyP@ssw0rd123!)
2. Restrict security group rule source IPs
3. Regularly rotate credentials
4. Delete unused resources