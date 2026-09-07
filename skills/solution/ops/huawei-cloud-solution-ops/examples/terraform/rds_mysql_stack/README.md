# Huawei RDS MySQL Stack Example

这个示例创建单机 MySQL RDS 实例，补齐上游 MySQL single 形态。

密码必须放在本地未提交的 tfvars 或外部 secret 流程中。apply 后用 hcloud 查询实例状态、内网地址、备份策略和安全组规则。
