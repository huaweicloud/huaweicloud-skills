# Huawei ECS ELB RDS Stack Example

这个示例提供一个最小 Web 服务拓扑：VPC/Subnet、安全组、ECS、RDS、ELB、listener、pool、member 和 health monitor。

适合场景：
- 用户要“部署一个带数据库的 Web 服务”并希望沉淀为 Terraform。
- 需要一个端到端示例，而不是多个单资源示例手工拼接。

安全边界：
- `admin_password` 和 `rds_password` 只能放在本地未提交的 tfvars 或外部 secret 流程里。
- `user_data` 不应该写入密码、AK/SK、token 或私钥。
- Web 入方向 CIDR 默认示例使用文档占位网段，生产必须替换成批准来源。

apply 后必须用 hcloud 查询 ECS、ELB member、RDS 状态，并做 HTTP 和数据库连接验证。
