# Huawei Cloud Full Service Catalog and Command Quick Reference

## Overview
KooCLI v7.2.2+ supports the following 100+ cloud services. Categorized by functional domain, listing service codes and common operations.

## 🔲 Compute

### ECS - Elastic Cloud Server
```bash
hcloud ECS ListServersDetails --cli-region=<r>          # List instances
hcloud ECS ShowServer --server_id=<id> --cli-region=<r>  # Instance details
hcloud ECS NovaShowServer --server_id=<id> --cli-region=<r>  # Nova details
hcloud ECS CreateServers --server.name=<n> ... --cli-region=<r>  # Create instance
hcloud ECS DeleteServers --servers.1.id=<id> --delete_publicip=true --delete_volume=true --cli-region=<r>  # Delete instance
hcloud ECS NovaStartServers --os-start.servers.1.id=<id> --cli-region=<r>  # Start
hcloud ECS NovaStopServers --os-stop.servers.1.id=<id> --cli-region=<r>   # Stop
hcloud ECS NovaRebootServers --os-reboot.servers.1.id=<id> --cli-region=<r>  # Reboot
hcloud ECS ShowServerRemoteConsole --server_id=<id> --remote_console.protocol=vnc --remote_console.type=novnc --cli-region=<r>  # VNC console
hcloud ECS ListFlavors --cli-region=<r>                  # Available flavors
hcloud ECS NovaListVersions --cli-region=<r>             # API versions
```

### BMS - Bare Metal Server
```bash
hcloud BMS ListServersDetails --cli-region=<r>
hcloud BMS ShowServer --server_id=<id> --cli-region=<r>
```

### AS - Auto Scaling
```bash
hcloud AS ListScalingGroups --cli-region=<r>
hcloud AS ShowScalingGroup --scaling_group_id=<id> --cli-region=<r>
hcloud AS CreateScalingGroup --cli-region=<r>
```

### CCE - Cloud Container Engine
```bash
hcloud CCE ListClusters --cli-region=<r>
hcloud CCE ShowCluster --cluster_id=<id> --cli-region=<r>
hcloud CCE CreateCluster --cli-region=<r>
hcloud CCE ListNodes --cluster_id=<id> --cli-region=<r>
```

### CCI - Cloud Container Instance
```bash
hcloud CCI ListNamespaces --cli-region=<r>
```

### FunctionGraph - FunctionGraph
```bash
hcloud FunctionGraph ListFunctions --cli-region=<r>
hcloud FunctionGraph ShowFunction --function_urn=<urn> --cli-region=<r>
```

## 🌐 Network

### VPC - Virtual Private Cloud
```bash
hcloud VPC ListVpcs --cli-region=<r>                     # List VPCs
hcloud VPC ShowVpc --vpc_id=<id> --cli-region=<r>        # VPC details
hcloud VPC ListSubnets --cli-region=<r>                   # List subnets
hcloud VPC ShowSubnet --subnet_id=<id> --cli-region=<r>   # Subnet details
hcloud VPC ListSecurityGroups/v3 --cli-region=<r>         # Security group list
hcloud VPC ShowSecurityGroup/v3 --security_group_id=<id> --cli-region=<r>  # Security group details
hcloud VPC ListSecurityGroupRules/v3 --security_group_id.1=<id> --cli-region=<r>  # Security group rules
hcloud VPC CreateSecurityGroupRule/v3 --security_group_id=<id> --security_group_rule.direction=ingress --security_group_rule.protocol=tcp --security_group_rule.multiport=<port> --security_group_rule.remote_ip_prefix=<cidr> --cli-region=<r>  # Add rule
hcloud VPC DeleteSecurityGroupRule/v3 --security_group_rule_id=<rule-id> --cli-region=<r>  # Delete rule
```

### EIP - Elastic IP
```bash
hcloud EIP ListPublicips/v3 --cli-region=<r>
hcloud EIP CreatePublicip/v3 --publicip.type=EIP --bandwidth.name=<n> --bandwidth.size=5 --bandwidth.share_type=PER --bandwidth.charge_mode=bandwidth --cli-region=<r>
hcloud EIP AssociatePublicip/v3 --publicip_id=<eip> --publicip_associate.instance_id=<ecs> --publicip_associate.instance_type=ECS --cli-region=<r>
hcloud EIP DisassociatePublicip/v3 --publicip_id=<eip> --cli-region=<r>
hcloud EIP DeletePublicip/v3 --publicip_id=<eip> --cli-region=<r>
```

### ELB - Elastic Load Balancer
```bash
hcloud ELB ListLoadBalancers --cli-region=<r>
hcloud ELB ShowLoadBalancer --loadbalancer_id=<id> --cli-region=<r>
hcloud ELB ListListeners --loadbalancer_id=<id> --cli-region=<r>
hcloud ELB ListPools --loadbalancer_id=<id> --cli-region=<r>
```

### NAT - NAT Gateway
```bash
hcloud NAT ListNatGateways --cli-region=<r>
hcloud NAT ShowNatGateway --nat_gateway_id=<id> --cli-region=<r>
```

### DNS - Domain Name Service
```bash
hcloud DNS ListPublicZones --cli-region=<r>
hcloud DNS ListPrivateZones --type=private --cli-region=<r>
hcloud DNS ShowPublicZone --zone_id=<id> --cli-region=<r>
hcloud DNS ListRecordSets --zone_id=<id> --cli-region=<r>
```

### VPN - Virtual Private Network
```bash
hcloud VPN ListVpnGateways --cli-region=<r>
hcloud VPN ShowVpnGateway --vpn_gateway_id=<id> --cli-region=<r>
```

### ER - Enterprise Router
```bash
hcloud ER ListInstances --cli-region=<r>
hcloud ER ShowInstance --instance_id=<id> --cli-region=<r>
```

### CFW - Cloud Firewall
```bash
hcloud CFW ListFirewalls --cli-region=<r>
```

## 💾 Storage

### EVS - Elastic Volume Service
```bash
hcloud EVS ListVolumes --cli-region=<r>
hcloud EVS ShowVolume --volume_id=<id> --cli-region=<r>
hcloud EVS CreateVolume --volume.name=<n> --volume.size=<gb> --volume.volume_type=SSD --volume.availability_zone=<az> --cli-region=<r>
hcloud EVS AttachVolume --volume_id=<id> --server_id=<ecs-id> --cli-region=<r>
hcloud EVS DetachVolume --volume_id=<id> --server_id=<ecs-id> --cli-region=<r>
hcloud EVS ExtendVolume --volume_id=<id> --volume.size=<new-gb> --cli-region=<r>
```

### CBR - Cloud Backup and Recovery
```bash
hcloud CBR ListVaults --cli-region=<r>
hcloud CBR ShowVault --vault_id=<id> --cli-region=<r>
```

### SFSTurbo - Scalable File Service
```bash
hcloud SFSTurbo ListShares --cli-region=<r>
hcloud SFSTurbo ShowShare --share_id=<id> --cli-region=<r>
```

## 🗄️ Database

### RDS - Relational Database Service
```bash
hcloud RDS ListInstances --cli-region=<r>
hcloud RDS ShowInstance --instance_id=<id> --cli-region=<r>
hcloud RDS ListBackups --instance_id=<id> --cli-region=<r>
hcloud RDS CreateInstance --cli-region=<r>
```

### GaussDB - Distributed Database
```bash
hcloud GaussDB ListInstances --cli-region=<r>
hcloud GaussDB ShowInstance --instance_id=<id> --cli-region=<r>
```

### GaussDBforNoSQL - NoSQL Database
```bash
hcloud GaussDBforNoSQL ListInstances --cli-region=<r>
```

### GaussDBforopenGauss - openGauss
```bash
hcloud GaussDBforopenGauss ListInstances --cli-region=<r>
```

### DCS - Distributed Cache Service
```bash
hcloud DCS ListInstances --cli-region=<r>
hcloud DCS ShowInstance --instance_id=<id> --cli-region=<r>
```

### DDS - Document Database Service
```bash
hcloud DDS ListInstances --cli-region=<r>
```

### DRS - Data Replication Service
```bash
hcloud DRS ListJobs --cli-region=<r>
```

## 🔒 Security

### IAM - Identity and Access Management
```bash
hcloud IAM KeystoneListUsers --cli-region=<r>
hcloud IAM KeystoneShowUser --user_id=<id> --cli-region=<r>
hcloud IAM ListPolicies --cli-region=<r>
hcloud IAM ShowPolicy --policy_id=<id> --cli-region=<r>
hcloud IAM ListRoles --cli-region=<r>
hcloud IAM ListGroups --cli-region=<r>
```

### HSS - Host Security Service
```bash
hcloud HSS ListHosts --cli-region=<r>
```

### WAF - Web Application Firewall
```bash
hcloud WAF ListInstances --cli-region=<r>
```

### KMS - Key Management Service
```bash
hcloud KMS ListKeys --cli-region=<r>
hcloud KMS ShowKey --key_id=<id> --cli-region=<r>
```

### Anti-DDoS - Anti-DDoS
```bash
hcloud Anti-DDoS ListConfigs --cli-region=<r>
```

### CTS - Cloud Trace Service
```bash
hcloud CTS ListTraces --cli-region=<r>
```

### CSMS - Cloud Secret Management Service
```bash
hcloud CSMS ListSecrets --cli-region=<r>
```

## 📊 Monitoring and Operations

### CES - Cloud Eye Service
```bash
hcloud CES ListMetrics --namespace=SYS.ECS --cli-region=<r>
hcloud CES ShowMetricData --namespace=SYS.ECS --metric_name=cpu_util --dim.0=instance_id,<id> --from=<ts>000 --to=<ts>000 --period=300 --filter=average --cli-region=<r>
hcloud CES ListAlarms --cli-region=<r>
hcloud CES ShowAlarm --alarm_id=<id> --cli-region=<r>
```

### LTS - Log Tank Service
```bash
hcloud LTS ListLogGroups --cli-region=<r>
hcloud LTS ListLogStreams --group_id=<id> --cli-region=<r>
```

### AOM - Application Operations Management
```bash
hcloud AOM ListApplications --cli-region=<r>
```

### Config - Config Audit
```bash
hcloud Config ListResources --cli-region=<r>
```

## 📨 Messaging and Notification

### SMN - Simple Message Notification
```bash
hcloud SMN ListTopics --cli-region=<r>
hcloud SMN ShowTopic --topic_urn=<urn> --cli-region=<r>
hcloud SMN ListSubscriptions --topic_urn=<urn> --cli-region=<r>
```

### Kafka - Distributed Message Kafka
```bash
hcloud Kafka ListInstances --cli-region=<r>
```

### RabbitMQ - Distributed Message RabbitMQ
```bash
hcloud RabbitMQ ListInstances --cli-region=<r>
```

### RocketMQ - Distributed Message RocketMQ
```bash
hcloud RocketMQ ListInstances --cli-region=<r>
```

## 🔧 Development Tools

### APIG - API Gateway
```bash
hcloud APIG ListInstances --cli-region=<r>
hcloud APIG ListApis --instance_id=<id> --cli-region=<r>
```

### CSE - Cloud Service Engine
```bash
hcloud CSE ListEngines --cli-region=<r>
```

### CodeArts Series
```bash
hcloud CodeArtsRepo ListRepositories --cli-region=<r>
hcloud CodeArtsBuild ListBuildRecords --cli-region=<r>
hcloud CodeArtsPipeline ListPipelines --cli-region=<r>
hcloud CodeArtsDeploy ListDeployTasks --cli-region=<r>
```

## 🧠 Big Data and AI

### ModelArts
```bash
hcloud ModelArts ListNotebooks --cli-region=<r>
hcloud ModelArts ListTrainingJobs --cli-region=<r>
```

### DLI - Data Lake Insight
```bash
hcloud DLI ListQueues --cli-region=<r>
```

### DWS - Data Warehouse Service
```bash
hcloud DWS ListClusters --cli-region=<r>
```

### MRS - MapReduce Service
```bash
hcloud MRS ListClusters --cli-region=<r>
```

### DIS - Data Ingestion Service
```bash
hcloud DIS ListStreams --cli-region=<r>
```

## 📺 Media

### VOD - Video on Demand
```bash
hcloud VOD ListAssets --cli-region=<r>
```

### Live - Live Streaming
```bash
hcloud Live ListDomains --cli-region=<r>
```

### MPC - Media Processing Center
```bash
hcloud MPC ListTranscodingTasks --cli-region=<r>
```

## 🏢 Enterprise and Management

### EPS - Enterprise Project
```bash
hcloud EPS ListEnterpriseProjects --cli-region=<r>
```

### Organizations - Organization Management
```bash
hcloud Organizations ListAccounts --cli-region=<r>
```

### TMS - Tag Management Service
```bash
hcloud TMS ListTags --resource_type=ecs --cli-region=<r>
```

### RMS - Resource Management Service
```bash
hcloud RMS ListResources --cli-region=<r>
```

## ⚠️ Services Not Supported by KooCLI

The following services require console or other dedicated CLI tools:

| Service | Alternative |
|---------|------------|
| BSS (Billing) | Browser access https://bss.huaweicloud.com |
| OBS (Object Storage) | Use obsutil CLI |
| Console | Browser access |

## Usage Instructions

### Parameter Description
- `<r>`: Region (e.g., cn-north-4)
- `<id>`: Resource ID
- `<n>`: Name
- `<urn>`: Resource URN
- `<az>`: Availability Zone
- `<ts>`: Unix timestamp (seconds) ×1000

### Common Parameters
All commands require the following parameters:
- `--cli-region=<region>`: Specify region
- `--cli-profile=<profile>`: Specify configuration profile (optional)
- `--cli-output=json`: Specify JSON output format (recommended)

### Service Category Description
- **Compute**: Virtual machines, containers, functions, and other compute resources
- **Network**: VPC, EIP, load balancer, and other network services
- **Storage**: Cloud disks, backup, file storage, etc.
- **Database**: Relational, NoSQL, cache, and other databases
- **Security**: IAM, firewall, key management, etc.
- **Monitoring and Operations**: Monitoring, logging, auditing, etc.
- **Messaging and Notification**: Message queues, notification services
- **Development Tools**: API gateway, microservices, CI/CD
- **Big Data and AI**: Data lake, data warehouse, AI services
- **Media**: Video on demand, live streaming, media processing
- **Enterprise and Management**: Enterprise projects, organization management, tag management

### Quick Search
- Use `hcloud help` to view all services
- Use `hcloud <service> help` to view service operations
- Use `hcloud <service> <operation> --help` to view operation parameters

### Best Practices
1. Always use `--cli-region` parameter to specify region
2. Use `--cli-output=json` for easier program parsing
3. Use `--help` to view operation parameters
4. Use `--cli-debug=true` to debug errors
5. Use `--cli-query` to filter JSON output