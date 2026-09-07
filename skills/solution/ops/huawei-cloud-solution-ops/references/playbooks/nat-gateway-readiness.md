# NAT Gateway Readiness Playbook

## 目标

确认 NAT 网关、DNAT/SNAT 规则和关联网络对象处于可解释状态，避免把连通性问题误判为 ECS 或安全组问题。

## 适用场景

- 查询公网 NAT 或私网 NAT 配置
- 创建、修改、删除 NAT 网关或 DNAT/SNAT 规则前的前置检查
- 排查内网资源出公网或公网端口映射失败

## 标准检查

1. 先确认上下文：

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

2. 查询网关和规则：

```bash
python3 scripts/hcloud_resource_discovery.py --service NAT --operation ListNatGateways --region=<region> --limit=20 --pretty
python3 scripts/hcloud_resource_discovery.py --service NAT --operation ListNatGatewayDnatRules --region=<region> --limit=20 --pretty
python3 scripts/hcloud_resource_discovery.py --service NAT --operation ListNatGatewaySnatRules --region=<region> --limit=20 --pretty
```

3. 有明确 ID 时再做资源级查询：

```bash
python3 scripts/hcloud_resource_query.py --service NAT --operation ShowNatGateway --region=<region> --param nat_gateway_id=<id> --pretty
```

## 风险边界

- NAT 变更会影响入口映射或出网路径，默认只生成 planner。
- DNAT 规则涉及公网端口暴露时，必须和安全组来源 CIDR 一起审查。
- 删除网关或规则前必须先列出受影响的 EIP、端口、私网 IP 和业务说明。

## 验收

成功时输出 NAT 网关 ID、状态、VPC/subnet、EIP 绑定、DNAT/SNAT 规则和最小连通性探测结论。失败时输出当前规则事实和下一条最小排查命令。
