# Huawei ELB Reuse Stack Example

这个示例用于复用现网 ELB，只新增 listener、pool、member 和 health monitor。

适合场景：
- 已经通过 hcloud 确认 ELB、后端 ECS、后端私网 IP 和 subnet。
- 不想重建 ELB，只想把新增后端纳入 Terraform 管理。

使用边界：
1. 先用 hcloud 查询 ELB、listener、pool、member 和后端 ECS/安全组。
2. 确认 `backend_subnet_id` 与后端地址匹配。
3. 运行 `terraform fmt`、`terraform init -backend=false`、`terraform validate`。
4. 运行 `terraform plan` 并审查新增 listener/pool/member。
5. apply 必须等用户确认；apply 后回到 hcloud 查询 listener、member、health monitor 和后端健康状态。

不要把现网 ELB 直接重建成 Terraform 新资源，也不要在没有后端安全组验证的情况下宣称入口可用。
