# 命名规范速查

> 当创建新 Skill 时参考此文件，确保命名符合华为云规范。

## Skill 命名公式

```
{platform}-{product}-{function}
```

- **platform**：固定为 `huawei-cloud`
- **product**：华为云服务/产品缩写
- **function**：功能描述词

## 华为云服务缩写映射

| 领域 | 服务缩写 | 全称 | 说明 |
|------|----------|------|------|
| compute | ecs | Elastic Cloud Server | 弹性云服务器 |
| compute | as | Auto Scaling | 弹性伸缩 |
| compute | ims | Image Management Service | 镜像服务 |
| network | vpc | Virtual Private Cloud | 虚拟私有云 |
| network | elb | Elastic Load Balance | 弹性负载均衡 |
| network | nat | NAT Gateway | NAT 网关 |
| network | vpn | Virtual Private Network | VPN 网关 |
| network | eip | Elastic IP | 弹性公网 IP |
| storage | obs | Object Storage Service | 对象存储 |
| storage | evs | Elastic Volume Service | 弹性云硬盘 |
| storage | sfs | Scalable File Service | 弹性文件服务 |
| database | rds | Relational Database Service | 关系型数据库 |
| database | dds | Document Database Service | 文档数据库 |
| database | gaussdb | GaussDB | 高斯数据库 |
| database | dcs | Distributed Cache Service | 分布式缓存 |
| security | iam | Identity and Access Management | 统一身份认证 |
| security | waf | Web Application Firewall | Web 应用防火墙 |
| security | cbr | Cloud Backup and Recovery | 云备份恢复 |
| monitoring | ces | Cloud Eye Service | 云监控 |
| monitoring | lts | Log Tank Service | 日志服务 |
| monitoring | aom | Application Operations Management | 应用运维管理 |
| middleware | cce | Cloud Container Engine | 云容器引擎 |
| middleware | dms | Distributed Message Service | 分布式消息服务 |
| middleware | elasticsearch | CSS (Cloud Search Service) | 云搜索服务 |
| devtools | devcloud | DevCloud | 开发云 |
| devtools | codehub | CodeHub | 代码托管 |
| solution | aom | AOM | 应用运维 |

## 功能描述词

| 功能词 | 适用场景 | 示例 |
|--------|----------|------|
| manage | 通用管理（CRUD） | huawei-cloud-ecs-manage |
| diagnosis-workflow | 诊断工作流 | huawei-cloud-ecs-diagnosis-workflow |
| deploy | 部署操作 | huawei-cloud-cce-deploy |
| monitor | 监控告警 | huawei-cloud-ces-monitor |
| migrate | 迁移操作 | huawei-cloud-rds-migrate |
| backup | 备份恢复 | huawei-cloud-ebs-backup |
| security-audit | 安全审计 | huawei-cloud-iam-security-audit |
| cost-optimizer | 成本优化 | huawei-cloud-ecs-cost-optimizer |
| cli-guidance | CLI 使用指南 | huawei-cloud-cli-guidance |
| copilot | 运维助手 | huawei-cloud-rds-copilot |

## 领域目录命名

| 领域 | 目录名 | 说明 |
|------|--------|------|
| 计算 | compute | ECS、AS、IMS |
| 网络 | network | VPC、ELB、NAT、EIP |
| 存储 | storage | OBS、EVS、SFS |
| 数据库 | database | RDS、DDS、GaussDB、DCS |
| 安全 | security | IAM、WAF、CBR |
| 监控 | monitoring | CES、LTS、AOM |
| 中间件 | middleware | CCE、DMS、CSS |
| 开发工具 | devtools | DevCloud、CodeHub |
| 解决方案 | solution | 跨服务编排 |

## 文件命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 参考文档 | kebab-case | `cli-installation-guide.md` |
| 脚本文件 | kebab-case，动词+名词 | `analyze-ingress.sh` |
| 模板文件 | kebab-case | `config.yaml` |
| 示例数据 | kebab-case | `example.json` |

## 命名检查清单

- [ ] Skill 名称以 `huawei-cloud-` 开头
- [ ] 产品缩写在服务映射表中
- [ ] 功能词在功能描述词表中
- [ ] 领域目录在领域目录表中
- [ ] 文件名全部 kebab-case
- [ ] 无大写字母（除 SKILL.md 本身）
