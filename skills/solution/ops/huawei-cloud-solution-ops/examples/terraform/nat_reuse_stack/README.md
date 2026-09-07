# Huawei NAT Reuse Stack Example

这个示例用于复用现网 NAT Gateway 和 EIP，只新增 SNAT/DNAT 规则。

适合场景：
- 已经通过 hcloud 确认 NAT Gateway、EIP、subnet 或 backend port。
- 不想重建 NAT，只想把新增规则纳入 Terraform 管理。

使用边界：
1. 先用 hcloud 查询 NAT Gateway、EIP、SNAT/DNAT 现有规则，避免端口冲突。
2. SNAT 按 subnet 或 CIDR 二选一；DNAT 必须确认 backend port 和安全组。
3. `terraform plan` 必须只包含预期新增规则。
4. apply 后用 hcloud 查询规则状态，并从目标网络做出网或入站连通性验证。
