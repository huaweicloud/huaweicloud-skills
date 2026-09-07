# VPC And Network Guide

VPC/网络指南覆盖 VPC、子网、安全组、EIP、NAT 和 DNS。网络任务要优先建立 canonical VPC/subnet，再做公网入口和服务暴露。

## hcloud-first 路径

1. 读取 `references/playbooks/vpc-network-readiness.md`、`vpc-resource-discovery.md`、`eip-public-ip-readiness.md`、`nat-gateway-readiness.md`、`dns-zone-record-readiness.md`。
2. 用 `hcloud_resource_discovery.py` 先列 VPC、subnet、安全组、EIP、NAT 和 DNS 资源。
3. 已知资源 ID 后，用 `hcloud_resource_query.py` 做 `ShowVpc`、`ShowPublicip`、`ShowNatGateway`、`ShowRecordSet` 等目标查询。
4. 安全组、EIP、NAT、DNS 变更先走 `hcloud_service_change_plan.py` 或 `hcloud_guarded_change_flow.py`；EIP 优先用 `hcloud_eip_change_flow.py`。
5. 对公网可达服务，验证安全组、EIP/ELB/NAT/DNS 绑定和协议探测结果。

## SDK 补充

- 可用 SDK 补充：`VPC:ShowVpc`。
- 用途：补充 `vpc_id` path 参数类型和 SDK path 证据。
- 不用途：不要用 SDK runner 批量改安全组、路由、EIP 或 NAT。

## 不要做

- 不要在 VPC/subnet 不一致时反复重建 ELB listener/member。
- 不要为 SSH `22` 或常见开发端口自动放开 `0.0.0.0/0`。
- 只有用户确认 EIP 直连 ECS 的公网网站方案后，才可用 `--allow-public-web` 规划精确 TCP `80/443`；ELB/CDN/WAF 后端仍限制到上游来源。
- 不要把 DNS 解析配置完成等同于公网服务已可访问。
