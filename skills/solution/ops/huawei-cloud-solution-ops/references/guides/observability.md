# Observability Guide

可观测任务用于判断资源是否真的健康、是否有足够证据支持闲置判断，以及是否需要告警或日志补充。默认只读或 planner-only。

## hcloud-first 路径

1. 读取 `references/playbooks/observability-readiness.md`、`ces-metric-readiness.md` 和 `lts-log-readiness.md`。
2. 用 `hcloud_observability_plan.py` 先做资源状态查询计划和 CES metric discovery。
3. 告警规则只用 `hcloud_ces_alarm_plan.py` 生成草案；真实创建/更新需单独确认。
4. 日志查询用 `hcloud_lts_readonly.py`，限制时间范围、关键词和返回摘要。
5. 闲置审计要结合资源状态、CES 指标、LTS 日志、标签、备份和业务归属，不只看单一字段。

## SDK 补充

- 可用 SDK 补充：`CES:ListMetrics`。
- 用途：补充 metric discovery 的请求结构和参数类型。
- 不用途：不要用 SDK runner 创建告警、通知策略或改日志配置。

## 不要做

- 不要读取大范围日志或原样返回敏感日志内容。
- 不要把没有指标数据直接解释成资源闲置。
- 不要在没有通知对象和阈值确认时创建告警。
