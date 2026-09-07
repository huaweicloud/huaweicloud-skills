# Huawei CCE CoreDNS Addon Stack Example

这个示例复用现网 CCE 集群，管理 CoreDNS addon。

使用前必须先用 hcloud 或 CCE 控制台确认：
- cluster ID 和版本。
- CoreDNS addon 可用版本。
- 当前 CoreDNS 配置和业务 DNS 解析依赖。

不要在没有业务 DNS 回归验证的情况下直接替换生产 CoreDNS 配置。apply 后需要查询 addon 状态，并做集群内 DNS 解析验证。
