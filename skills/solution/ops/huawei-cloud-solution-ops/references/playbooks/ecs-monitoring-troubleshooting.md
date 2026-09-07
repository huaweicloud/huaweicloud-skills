# ECS Monitoring Troubleshooting

## 目标

帮助用户排查 ECS 监控指标为空、内存指标不存在、告警创建失败、指标命名不匹配等问题。重点是先确认 namespace、metric、dimension、period、Agent 状态和采集延迟，而不是把无数据直接判断成 ECS 正常或异常。

## 适用场景

- 用户说 ECS CPU、内存、磁盘、网络指标查不到。
- CES 告警提示指标不存在。
- 用户把 `mem_used_percent`、`mem_util`、`mem_usedPercent` 混用。
- 用户要给 ECS 配内存、磁盘或进程类告警。

## namespace 选择

| namespace | 含义 | Agent 依赖 | 常见指标 |
| --- | --- | --- | --- |
| `SYS.ECS` | 基础监控，来自云侧/虚拟化层 | 通常不需要 Agent，但部分指标依赖镜像工具 | `cpu_util`、`mem_util`、`disk_util_inband` |
| `AGT.ECS` | 操作系统监控，来自主机监控 Agent | 需要 Telescope/主机监控 Agent 安装并上报 | `cpu_usage`、`mem_usedPercent`、`disk_usedPercent`、`load_average1` |

用户要“内存使用率告警”时，不要直接把旧写法 `mem_used_percent` 放到 `SYS.ECS`。优先建议：

- 先用 `ListMetrics` 确认目标 ECS 当前真实上报了哪些指标。
- 如果需要 OS 内存，通常使用 `AGT.ECS:mem_usedPercent`，并确认 Agent 已安装。
- 如果只能使用基础监控，则先确认 `SYS.ECS:mem_util` 是否存在并有数据。
- 如果直接用 `SYS.ECS:mem_used_percent` 创建告警返回 `400` / `ces.0014` / `Some content in message body is not correct`，优先按“指标不属于该 namespace 或 Agent 未上报”排查，不要只把它当成 JSON 参数拼错。

## 标准流程

1. 确认目标 ECS：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service ECS \
  --operation NovaListServersDetails \
  --region=<region> \
  --limit=20 \
  --pretty
```

2. 查询 CES 指标列表：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service CES \
  --operation ListMetrics \
  --region=<region> \
  --limit=50 \
  --pretty
```

3. 查询一个已确认指标的 datapoints：

```bash
python3 scripts/hcloud_ces_datapoint_plan.py \
  --region=<region> \
  --project-id=<project-id> \
  --namespace SYS.ECS \
  --metric-name cpu_util \
  --dimension instance_id=<instance_id> \
  --period 300 \
  --lookback-minutes 30 \
  --pretty
```

如果返回 `empty_datapoints`，先按 planner 的 `likely_causes` 检查 Agent、namespace、dimension、period、采集延迟和 region/project，不要直接判断 ECS 正常或异常。

4. 生成告警草案或指标建议：

```bash
python3 scripts/hcloud_ces_alarm_plan.py \
  --metric-name mem_used_percent \
  --namespace SYS.ECS \
  --dimension instance_id=<instance_id> \
  --pretty
```

如果 planner 返回 `metric_guidance`，先处理 guidance，不要直接重试创建告警。

## 常见问题判断

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| CPU 有数据，内存无数据 | `SYS.ECS:mem_util` 依赖镜像工具；OS 内存需要 Agent | 查 `AGT.ECS:mem_usedPercent` 是否存在，必要时安装 Agent。 |
| `mem_used_percent` 不存在 | 旧资料或非规范命名 | 改用 `AGT.ECS:mem_usedPercent`，并先查 `ListMetrics`。 |
| 创建内存告警返回 `ces.0014` | 目标 metric/namespace 不匹配，或 OS Agent 指标未上报 | 先查 `ListMetrics`，确认 `AGT.ECS` 和 `mem_usedPercent`；安装 Agent 后等待采集。 |
| 刚创建 ECS 没指标 | 采集延迟 | 等待 5-10 分钟后重查，或先做业务协议验收。 |
| 指标维度错误 | dimension name/value 不匹配 | ECS 通常用 `instance_id`，不要混用 name、IP 或 server name。 |
| period 不支持 | namespace 最小周期不同 | `SYS.ECS` 常用 300 秒；`AGT.ECS` 常用 60 秒。 |
| 403/权限失败 | 缺 CES 或 ECS 只读权限 | 进入 `iam-permission-diagnostics.md`。 |

## 告警模板建议

- Web 类 ECS：优先覆盖 `cpu_util`、公网/私网网络速率、系统盘使用率、HTTP/ELB 健康检查；内存告警需先确认 Agent。
- Database/中间件类 ECS：优先覆盖 CPU、OS 内存、磁盘使用率、磁盘 IO、进程或端口探测；避免只用云侧 `ACTIVE` 判断业务健康。
- 推荐先生成 planner-only 草案，再让用户确认阈值、period、通知渠道和噪声接受度。
- 常见起点：CPU warning 80%、critical 95%；内存 warning 可从 80%-85% 起步，但必须结合业务峰值和历史曲线，不要把模板阈值当成普适标准。

## 验收

成功排障不是“告警已创建”，而是能说明：

- 当前 ECS 的指标 namespace 和 metric 是否存在。
- 目标 dimension 是否正确。
- 指标无数据的原因是 Agent、镜像工具、采集延迟、权限、region/project 还是指标名错误。
- 如果要创建告警，下一步需要用户确认 metric、threshold、period、通知方式和费用/噪声影响。

## 输出给用户时

对小白用户要少讲内部术语，先说结论：

- “这个指标属于基础监控还是主机监控。”
- “是否需要安装 Agent。”
- “现在缺哪一步证据。”
- “下一条只读查询或 planner 命令是什么。”
