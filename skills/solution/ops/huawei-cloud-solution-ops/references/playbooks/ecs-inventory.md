# ECS Inventory Playbook

## 目标

稳定查询当前 scope 下的 ECS 实例，并输出可读的摘要而不是整份杂乱结果。

## 适用场景

- 查 ECS 列表
- 按状态汇总 ECS
- 查某个实例名、IP、tag 对应的实例
- 为后续创建、迁移、排障做现网摸底

## 已验证的 ECS operation

当前环境里已确认 `hcloud ECS --help` 可列出至少这些 operation：

- `ListServersDetails`
- `ListCloudServers`
- `NovaListServers`
- `NovaListServersDetails`
- `ListFlavors`
- `ListFlavorSellPolicies`
- `ListServerAzInfo`

默认优先顺序：

1. `ListServersDetails`
2. `ListCloudServers`
3. `NovaListServersDetails`
4. `NovaListServers`

## 标准步骤

### 1. 确认上下文

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

### 2. 小样本查询

优先尝试：

```bash
python3 scripts/hcloud_safe_exec.py \
  --service ECS \
  --operation ListServersDetails \
  --arg=--cli-region=cn-north-4 \
  --arg=--project_id=<project-id> \
  --arg=--limit=20 \
  --arg=--cli-output=json \
  --expect-json \
  --pretty
```

如果当前租户或版本下这个 operation 不适合，再切换 `ListCloudServers` 或 Nova 路线。

### 3. 按需求加过滤

常见过滤条件：

- `name`
- `status`
- `ip`
- `flavor`
- `tags`

真实参数名称以当前 `operation --help` 和实际返回为准。

## 推荐输出方式

### 先看原始小样本 JSON

先确认：

- 顶层 key 是什么
- 实例数组在哪个字段
- 状态字段叫什么

### 再做摘要

推荐只返回：

- 实例总数
- 状态分布
- 每台实例的名称 / ID / 状态 / 私网 IP / 公网 IP

## 示例：只保留简要字段

当你已经确认字段结构后，再考虑增加 `--cli-query`。

## 失败时的处理

### operation 帮助失败

- 先不要猜 body 或 query 参数
- 退回 service 列表和本地缓存

### 缺少 `project_id`

- 不要继续无脑重试
- 先回到上下文 bootstrap

### 大结果过多

- 优先减小 `limit`
- 或改成名字 / 状态 / tag 条件

## 推荐交付

- 一段摘要
- 一个简表风格结果
- 必要时给后续动作建议，例如：
  - 是否继续按某个状态深挖
  - 是否继续看规格或 AZ
