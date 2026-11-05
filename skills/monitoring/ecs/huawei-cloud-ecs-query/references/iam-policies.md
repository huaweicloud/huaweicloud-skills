# IAM Policies — huawei-cloud-ecs-query

使用本技能查询 ECS 实例信息所需的 IAM 权限配置。

## 必需权限

| 权限 | 级别 | 说明 |
|------|------|------|
| `ECS ReadOnlyAccess` | 推荐 | 只读权限，满足全部查询操作 |
| `ECS FullAccess` | 备选 | 完全权限，仅当需要同时执行写操作时使用 |

> 本技能只执行**只读**查询（ListServersDetails / ShowServer / server-status），`ECS ReadOnlyAccess` 即可覆盖。

## 增强字段权限（--detail / --full）

使用 `list-servers` / `show-server` 的 `--detail` / `--full` 参数补全系统盘/数据盘大小类型与 EIP 带宽时，需要额外具备以下只读权限：

| 权限 | 服务 | 用途 |
|------|------|------|
| `EVS ReadOnlyAccess` | 云硬盘 EVS | 补全系统盘/数据盘大小与类型（ListVolumes） |
| `VPC ReadOnlyAccess` | 虚拟私有云 VPC | 补全 EIP 带宽（ListPublicips/v3） |

> 未授予上述权限时，增强字段自动降级为仅展示挂载盘设备名与公网 IP 地址，不影响 ECS 核心查询。

## 授权方式

### 方式一：控制台授权（推荐）

1. 登录华为云控制台 → IAM → 用户组
2. 选择目标用户组 → 权限配置 → 授权
3. 搜索并勾选 `ECS ReadOnlyAccess`（如需 `--detail` 增强，同时勾选 `EVS ReadOnlyAccess`、`VPC ReadOnlyAccess`）→ 确定

### 方式二：CLI 授权

```bash
# 查询策略 ID
hcloud IAM ListPoliciesV5 --cli-region=cn-north-4

# 为用户附加策略（替换为实际 user_id / policy_id）
hcloud IAM AttachUserPolicyV5 --user_id=<user-id> --policy_id=<policy-id> --cli-region=cn-north-4
```

## 验证授权

配置完成后，可执行只读命令验证：

```bash
# 脚本路径
python3 scripts/ecs_query.py list-servers --config config.yaml

# CLI 路径
hcloud ECS ListServersDetails --cli-region=cn-north-4 --limit=1
```

若返回 `403 Forbidden` / 权限不足，说明账号缺少 ECS 只读权限。