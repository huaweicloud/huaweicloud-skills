# Naming Conventions Quick Reference

> Refer to this file when creating a new Skill to ensure naming follows Huawei Cloud conventions.

## Skill Naming Formula

```
{platform}-{product}-{function}
```

- **platform**: Always `huawei-cloud`
- **product**: Huawei Cloud service/product abbreviation
- **function**: Capability descriptor

## Huawei Cloud Service Abbreviation Mapping

| Domain | Abbreviation | Full Name | Description |
|--------|-------------|-----------|-------------|
| compute | ecs | Elastic Cloud Server | Elastic Cloud Server |
| compute | as | Auto Scaling | Auto Scaling |
| compute | ims | Image Management Service | Image Management |
| network | vpc | Virtual Private Cloud | Virtual Private Cloud |
| network | elb | Elastic Load Balance | Elastic Load Balancer |
| network | nat | NAT Gateway | NAT Gateway |
| network | vpn | Virtual Private Network | VPN Gateway |
| network | eip | Elastic IP | Elastic Public IP |
| storage | obs | Object Storage Service | Object Storage |
| storage | evs | Elastic Volume Service | Elastic Volume |
| storage | sfs | Scalable File Service | Scalable File Service |
| database | rds | Relational Database Service | Relational Database |
| database | dds | Document Database Service | Document Database |
| database | gaussdb | GaussDB | GaussDB |
| database | dcs | Distributed Cache Service | Distributed Cache |
| security | iam | Identity and Access Management | Identity & Access Mgmt |
| security | waf | Web Application Firewall | Web App Firewall |
| security | cbr | Cloud Backup and Recovery | Cloud Backup & Recovery |
| monitoring | ces | Cloud Eye Service | Cloud Eye |
| monitoring | lts | Log Tank Service | Log Service |
| monitoring | aom | Application Operations Management | App Ops Management |
| middleware | cce | Cloud Container Engine | Cloud Container Engine |
| middleware | dms | Distributed Message Service | Distributed Message |
| middleware | elasticsearch | CSS (Cloud Search Service) | Cloud Search Service |
| devtools | devcloud | DevCloud | DevCloud |
| devtools | codehub | CodeHub | Code Repository |
| solution | aom | AOM | App Ops |

## Function Descriptors

| Function Word | Use Case | Example |
|---------------|----------|---------|
| manage | General management (CRUD) | huawei-cloud-ecs-manage |
| diagnosis-workflow | Diagnosis workflow | huawei-cloud-ecs-diagnosis-workflow |
| deploy | Deployment operations | huawei-cloud-cce-deploy |
| monitor | Monitoring & alerting | huawei-cloud-ces-monitor |
| migrate | Migration operations | huawei-cloud-rds-migrate |
| backup | Backup & recovery | huawei-cloud-ebs-backup |
| security-audit | Security audit | huawei-cloud-iam-security-audit |
| cost-optimizer | Cost optimization | huawei-cloud-ecs-cost-optimizer |
| cli-guidance | CLI usage guide | huawei-cloud-cli-guidance |
| copilot | Ops copilot | huawei-cloud-rds-copilot |

## Domain Directory Naming

| Domain | Directory | Services |
|--------|-----------|----------|
| Compute | compute | ECS, AS, IMS |
| Network | network | VPC, ELB, NAT, EIP |
| Storage | storage | OBS, EVS, SFS |
| Database | database | RDS, DDS, GaussDB, DCS |
| Security | security | IAM, WAF, CBR |
| Monitoring | monitoring | CES, LTS, AOM |
| Middleware | middleware | CCE, DMS, CSS |
| Dev Tools | devtools | DevCloud, CodeHub |
| Solutions | solution | Cross-service orchestration |

## File Naming Conventions

| Type | Rule | Example |
|------|------|---------|
| Reference docs | kebab-case | `cli-installation-guide.md` |
| Script files | kebab-case, verb+noun | `analyze-ingress.sh` |
| Template files | kebab-case | `config.yaml` |
| Example data | kebab-case | `example.json` |

## Naming Checklist

- [ ] Skill name starts with `huawei-cloud-`
- [ ] Product abbreviation is in the service mapping table
- [ ] Function word is in the function descriptors table
- [ ] Domain directory is in the domain directory table
- [ ] All filenames use kebab-case
- [ ] No uppercase letters (except SKILL.md itself)
