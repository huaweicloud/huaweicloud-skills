# IAM Policies — huawei-cloud-computing-query

使用本技能查询华为云计算资源（ECS / BMS / IMS / AS / CCE）所需的 IAM 权限配置。

## 必需权限

本技能仅执行只读查询操作（List / Show / Get），不涉及任何写操作。

### 系统策略（推荐）

| 系统策略 | 覆盖服务 | 说明 |
|----------|----------|------|
| `ECS ReadOnlyAccess` | ECS | 弹性云服务器只读权限 |
| `BMS ReadOnlyAccess` | BMS | 裸金属服务器只读权限 |
| `IMS ReadOnlyAccess` | IMS | 镜像服务只读权限 |
| `AS ReadOnlyAccess` | AS | 弹性伸缩只读权限 |
| `CCEReadOnlyPolicy` | CCE | 云容器引擎只读权限（集群 / 节点 / 节点池 / 标签 / 配额） |

> 若涉及通过 IAM API 自动获取 project_id，还需 `IAM ReadOnlyAccess`（只读查询项目列表）。

### 自定义最小权限策略

如需精细化授权，可创建自定义策略：

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:list",
        "ecs:servers:get",
        "ecs:cloudServers:list",
        "ecs:serverGroups:list",
        "ecs:serverTags:list",
        "ecs:flavors:list",
        "ecs:quotas:list",
        "bms:servers:list",
        "bms:servers:get",
        "bms:flavors:list",
        "bms:quotas:get",
        "bms:serverTags:get",
        "ims:images:list",
        "ims:images:get",
        "ims:tags:list",
        "ims:quotas:get",
        "as:scalingGroups:list",
        "as:scalingGroups:get",
        "as:scalingConfigurations:list",
        "as:scalingConfigurations:get",
        "as:scalingPolicies:list",
        "as:scalingPolicies:get",
        "as:scalingActivityLogs:list",
        "as:lifecycleHooks:list",
        "as:warmPools:get",
        "as:quotas:get",
        "as:tags:list",
        "cce:cluster:list",
        "cce:cluster:get",
        "cce:node:list",
        "cce:node:get",
        "cce:nodepool:list",
        "cce:nodepool:get",
        "cce:quota:get",
        "cce:tag:get",
        "iam:projects:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 授权方式

### 方式一：控制台授权（推荐）

1. 登录华为云控制台 → IAM → 用户组
2. 选择目标用户组 → 权限配置 → 授权
3. 搜索并勾选以下策略：
   - `ECS ReadOnlyAccess`
   - `BMS ReadOnlyAccess`
   - `IMS ReadOnlyAccess`
   - `AS ReadOnlyAccess`
   - `CCEReadOnlyPolicy`
   - `IAM ReadOnlyAccess`（可选，用于自动获取 project_id）
4. 确定

### 方式二：自定义策略授权

1. 登录华为云控制台 → IAM → 权限 → 创建自定义策略
2. 选择 JSON 模式，粘贴上方自定义策略
3. 命名并保存（如 `ComputingQueryReadOnly`）
4. 返回用户组 → 授权 → 选择自定义策略 → 确定

## 验证授权

配置完成后，可执行只读脚本验证：

```bash
# 验证 ECS 查询
python3 scripts/ecs/list_servers_details.py --region cn-north-4

# 验证 BMS 查询
python3 scripts/bms/list_bare_metal_servers.py --region cn-north-4

# 验证 AS 查询
python3 scripts/as/list_scaling_groups.py --region cn-north-4

# 验证 IMS 查询
python3 scripts/ims/list_images.py --region cn-north-4

# 验证 CCE 查询（需要集群 ID 时可由 list_clusters.py 获取）
python3 scripts/cce/list_clusters.py --region cn-north-4
python3 scripts/cce/show_quota.py --region cn-north-4
python3 scripts/cce/list_nodes.py --region cn-north-4 --cluster_id <cluster-id> --all
python3 scripts/cce/list_node_pools.py --region cn-north-4 --cluster_id <cluster-id>
```

`--region` 可省略，省略时回退环境变量 `HW_REGION_NAME`（缺省 cn-north-4），与各脚本参数保持一致。

若返回 `403 Forbidden` / 权限不足，说明账号缺少对应服务的只读权限。

## 特殊说明

- **AS API 版本查询**（`list_api_versions.py` / `show_api_version.py`）为公开接口，无需 IAM 权限即可访问
- **CCE 查询**使用 `huaweicloudsdkcce` v3 只读接口（ListClusters / ShowCluster / ListNodes / ShowNode / ListNodePools / ShowNodePool / GetResourceTags / ShowQuotas），不含任何写操作；集群证书没有读接口，插件与日志分析请转 `container/cce/` 下的对应技能
- **BMS / IMS 查询**部分接口依赖 project_id，若未配置 `HW_PROJECT_ID` 环境变量，脚本会通过 IAM API 自动获取，此时需要 `IAM ReadOnlyAccess` 权限
- 使用临时 AK/SK 时，需同时配置 `HW_SECURITY_TOKEN` 环境变量
