# Service Guides

这些服务指南用于把自然语言目标快速定位到本 Skill 的服务知识、hcloud 默认路径、SDK 程序化候选
和 Terraform IaC 资产。它们不替代 registry、playbook、官方 API/schema 和当前工具证据。

## 使用规则

- 先按 `scripts/hcloud_scenario_router.py` 或用户明确服务定位到场景。
- 再读取对应服务指南和 `references/playbooks/` 下的 playbook。
- 查询和一次性变更默认优先 hcloud；SDK 更适合复杂程序化处理或 hcloud 实际障碍时可以成为任务
  后端。`sdk-supplement-registry.json` 只限制便捷只读 runner。
- Terraform 只在用户需要可重复 IaC、环境复制或长期纳管时接入，详见 `references/terraform-workflow.md`。

## 指南索引

| 服务/主题 | 指南 | 主要目标 |
| --- | --- | --- |
| ECS | `ecs.md` | 计算规格、镜像、实例创建、job、SSH 和应用验收。 |
| VPC/网络 | `vpc.md` | VPC、子网、安全组、EIP、NAT 和 DNS 依赖。 |
| ELB | `elb.md` | 监听器、后端服务器组、member 健康和协议探测。 |
| RDS | `rds.md` | 实例配置、备份、连接证据和参数组只读检查。 |
| CCE | `cce.md` | 集群、节点、网络、监控和平台 readiness。 |
| OBS | `obs.md` | bucket 只读、生命周期/策略计划和静态站资产边界。 |
| 可观测 | `observability.md` | CES、LTS、告警计划和健康证据。 |
| 治理 | `governance.md` | 审计、标签、成本、备份、闲置和回收前检查。 |
