# IAM 权限策略

## 概述

本文档说明本技能所需的 IAM 权限列表及配置方法。

## 所需权限

### ECS 相关权限

| API Action | 权限 | 用途 |
|------------|------|------|
| ecs:servers:create | 创建云服务器 | 创建 ECS 实例 |
| ecs:servers:get | 查询云服务器详情 | 检查服务器状态 |
| ecs:servers:list | 查询云服务器列表 | 列出所有服务器 |
| ecs:serverVolumes:attach | 挂载云硬盘 | 挂载系统盘 |
| ecs:cloudServerFlavors:list | 查询规格列表 | 获取可用规格 |
| ecs:cloudImages:list | 查询镜像列表 | 获取可用镜像 |

### VPC 相关权限

| API Action | 权限 | 用途 |
|------------|------|------|
| vpc:vpcs:create | 创建 VPC | 创建虚拟私有云 |
| vpc:vpcs:get | 查询 VPC 详情 | 获取 VPC 信息 |
| vpc:subnets:create | 创建子网 | 创建子网 |
| vpc:subnets:get | 查询子网详情 | 获取子网信息 |
| vpc:securityGroups:create | 创建安全组 | 创建 sg-sqlbot |
| vpc:securityGroupRules:create | 创建安全组规则 | 配置端口规则 |

### EIP 相关权限

| API Action | 权限 | 用途 |
|------------|------|------|
| eip:publicIps:create | 创建弹性公网IP | 绑定 EIP |
| eip:publicIps:get | 查询弹性公网IP | 获取 EIP 信息 |
| eip:publicIps:bind | 绑定弹性公网IP | 绑定到 ECS |

## IAM 策略配置

### 方式一：使用预设策略

在 IAM 控制台为用户添加以下预设策略：
- `ECS FullAccess` - ECS 完整访问权限
- `VPC FullAccess` - VPC 完整访问权限
- `EIP FullAccess` - EIP 完整访问权限

### 方式二：自定义策略

✅ **正确示例**：
```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:create",
        "ecs:servers:get",
        "ecs:servers:list",
        "ecs:serverVolumes:attach",
        "ecs:cloudServerFlavors:list",
        "ecs:cloudImages:list",
        "vpc:vpcs:create",
        "vpc:vpcs:get",
        "vpc:subnets:create",
        "vpc:subnets:get",
        "vpc:securityGroups:create",
        "vpc:securityGroupRules:create",
        "eip:publicIps:create",
        "eip:publicIps:get",
        "eip:publicIps:bind"
      ]
    }
  ]
}
```

❌ **错误示例**：
```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:*"  // Too permissive - violates least privilege principle
      ]
    }
  ]
}
```

## 权限失败处理

如果遇到权限不足错误（403 Unauthorized）：

1. **检查 IAM 策略**
   - 确认策略已正确附加到用户/角色
   - 检查策略中的 Action 是否包含所需权限

2. **验证 AK/SK**
   - 确认 AK/SK 未过期
   - 确认 AK/SK 属于有权限的用户

3. **确认区域配置**
   - 检查 Region 参数是否正确
   - 某些权限可能需要区域级配置

4. **查看错误详情**

✅ **正确示例**：
```bash
# Check error details
hcloud ECS ListServers --cli-region=cn-north-4
# Error: {"error_code": "APIGW.0101", "error_msg": "API not exist or not published"}
```

## 最小权限原则

建议按照最小权限原则配置：
- 仅授予必需的 API Action
- 限制资源范围（如特定项目/区域）
- 定期审查和清理不必要的权限
