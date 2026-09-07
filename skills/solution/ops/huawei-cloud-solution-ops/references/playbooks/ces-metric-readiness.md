# CES Metric Readiness Playbook

## 目标

确认云监控指标 namespace、dimension、period 和时间范围，避免空结果被误判为资源异常。

## 适用场景

- 查询可用指标
- 为 ECS、ELB、RDS 等服务做监控前置检查
- 排查监控数据为空、维度错误或时间范围错误

## 标准检查

```bash
python3 scripts/hcloud_resource_discovery.py --service CES --operation ListMetrics --region=<region> --limit=50 --pretty
```

查询具体指标前必须先从目标服务确认：

- namespace
- metric name
- dimension name/value
- period
- from/to 时间范围

ECS 指标特别注意：

- `SYS.ECS` 是基础监控，通常不需要 Agent，最小 period 通常按 300 秒处理。
- `AGT.ECS` 是操作系统监控，需要主机监控 Agent/Telescope 已安装并上报，适合 OS 内存、挂载点磁盘、load、进程等指标。
- 如果用户要做 ECS 内存告警，优先从 `ListMetrics` 确认可用指标。`mem_used_percent` 是旧资料中常见写法，planner 会建议规范到 `AGT.ECS:mem_usedPercent`；不要把它当成 `SYS.ECS` 指标直接创建。
- `SYS.ECS:mem_util` 也可能依赖镜像工具，返回空时先检查镜像工具/Agent/采集延迟，不要直接判断为 ECS 正常或异常。

## 风险边界

- 当前 curated 覆盖只承诺只读 metric discovery。
- 告警规则、通知屏蔽、资源组等 mutation 不纳入当前 registry。
- 监控无数据不直接等于资源故障；先检查 region、namespace、dimension 和采集延迟。
- 告警草案用 `hcloud_ces_alarm_plan.py` 输出 `metric_guidance`，真实创建/更新告警必须另走单独确认的变更流程。

## 验收

成功时输出 namespace、metric、dimension 和可查询时间范围。失败时说明是维度不匹配、时间范围不合理、指标未上报还是权限/region 问题。
