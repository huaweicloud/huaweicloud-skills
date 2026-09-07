# RDS Instance Readiness Playbook

## 目标

确认 RDS 实例、配置和备份策略达到可用状态，并把云侧状态和数据库连接可用性分开验收。

## 适用场景

- 创建 RDS 实例
- 查询或修改规格、存储、备份策略
- 创建数据库或账号
- 检查性能指标和慢查询

## 标准检查

1. 查询 RDS 实例列表：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service RDS \
  --operation ListInstances \
  --region=<region> \
  --project-id=<project-id> \
  --limit=20 \
  --pretty
```

2. 对实例 JSON 结果做状态验收：

```bash
python3 scripts/hcloud_resource_verify.py \
  --service RDS \
  --json-file=<safe-exec-result.json> \
  --target-name=<instance-name> \
  --expect-status AVAILABLE \
  --require-match \
  --pretty
```

## 验收字段

- Instance ID
- 名称
- `status`
- 引擎和版本
- flavor / vCPU / memory
- storage type / size
- VPC、subnet、安全组
- 内网地址、端口
- 备份策略和保留天数

## 数据库连接验收

如果用户目标包括业务连接、主从复制或 SQL 执行，RDS `available` 仍不等于任务完成。还需要：

- 确认安全组允许客户端来源访问数据库端口
- 使用明确的数据库账号执行只读探测，例如 `SELECT 1`
- 主从或只读实例场景下检查复制延迟和只读状态
- 参数变更后确认是否需要重启或已经生效

## 最终输出

成功时给出实例 ID、状态、地址、规格、备份策略和连接探测结果。失败时给出当前状态、阻塞字段和下一条最小排查命令。
