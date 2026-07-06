# 验证方法

## 概述

本文档说明如何验证每个部署步骤是否成功执行。

## 1. AK/SK 认证验证

### 验证方法

✅ **正确示例**：
```bash
python3 -c "
from huaweicloudsdkcore.auth.credentials import BasicCredentials
credentials = BasicCredentials(ak='AKEXAMPLE123456', sk='SKEXAMPLE789012', project_id='PROJECT123456')
print('Authentication successful')
"
```

### 预期结果
- 无错误输出
- 打印 "Authentication successful"

## 2. ECS 实例创建验证

### 验证方法

✅ **正确示例**：
```bash
# Check server status
hcloud ECS ListServers --cli-region=cn-north-4 --project_id=PROJECT123456

# Or via API
python3 -c "
from huaweicloudsdkecs.v2 import EcsClient
# ... check server status
"
```

### 预期结果
- 服务器状态为 `ACTIVE`
- 有公网 IP 地址
- 有安全组 sg-sqlbot

## 3. 安全组验证

### 验证方法

✅ **正确示例**：
```bash
# List security group rules
hcloud VPC ListSecurityGroupRules --cli-region=cn-north-4 --security_group_id=sg-sqlbot-id
```

### 预期结果
- 包含 SQLBot 端口 8000 规则

## 4. EIP 绑定验证

### 验证方法

✅ **正确示例**：
```bash
# Check EIP binding
hcloud EIP ListPublicIps --cli-region=cn-north-4
```

### 预期结果
- EIP 状态为 `BIND`
- 绑定到正确的 ECS 实例

## 5. COC 部署验证

### 验证方法

✅ **正确示例**：
```bash
# Check UniAgent status (must be ONLINE before COC script execution)
# UniAgent auto-installs on ECS instance, usually takes 30-60s

# Check COC script execution status
# Script status: READY → PROCESSING → FINISHED
# Execution result: SUCCESS / FAIL
```

### 预期结果
- UniAgent 状态为 `ONLINE`
- COC 脚本执行状态为 `FINISHED`
- COC 脚本执行结果为 `SUCCESS`

## 6. SQLBot 部署验证

### 验证方法

✅ **正确示例**：
```bash
# Check SQLBot service status
curl -s http://<public_ip>:8000/health || echo "SQLBot not ready"
```

### 预期结果
- HTTP 200 响应或健康检查通过

## 7. 完整部署验证

### 验证清单

| 步骤 | 验证命令 | 预期结果 |
|------|----------|----------|
| 认证 | 检查凭证有效性 | 无错误 |
| ECS 创建 | 查询服务器状态 | ACTIVE |
| 安全组 | 列出安全组规则 | 包含 8000 |
| EIP 绑定 | 查询 EIP 状态 | BIND |
| COC 部署 | 检查 UniAgent + 脚本执行 | ONLINE + SUCCESS |
| SQLBot | 访问健康检查接口 | HTTP 200 |

## 常见问题排查

### Q: SQLBot 无法访问？

✅ **解决方案**：
- 检查安全组是否开放 8000 端口
- 检查 Docker 容器是否运行
- 查看容器日志：`docker logs sqlbot`
