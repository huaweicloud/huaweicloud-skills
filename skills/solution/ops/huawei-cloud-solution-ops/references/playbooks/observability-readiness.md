# Observability Readiness Playbook

## Goal

Confirm that a cloud resource can be observed through resource state, CES metrics, optional CES alarms, and LTS logs before declaring it healthy, idle, or ready for production.

## Standard Flow

1. Confirm the resource exists with the service-specific `Show*` or `List*` query.
2. Discover CES metric namespace, metric names, and dimensions:

```bash
python3 scripts/hcloud_observability_plan.py \
  --service ECS \
  --target-id <server-id> \
  --region=<region> \
  --project-id=<project-id> \
  --pretty
```

3. Review existing CES alarm rules and draft alarm intent without submitting:

```bash
python3 scripts/hcloud_ces_alarm_plan.py \
  --region=<region> \
  --project-id=<project-id> \
  --alarm-name <name> \
  --namespace <namespace> \
  --metric-name <metric-name> \
  --threshold <number> \
  --pretty
```

For ECS memory or disk alarms, read `references/playbooks/ces-metric-readiness.md` first. The CES alarm planner returns `metric_guidance` so the agent can distinguish basic `SYS.ECS` metrics from Agent-backed `AGT.ECS` metrics before proposing thresholds.

4. Discover LTS log groups and streams, then query a bounded time window:

```bash
python3 scripts/hcloud_lts_readonly.py \
  --region=<region> \
  --project-id=<project-id> \
  --log-group-id <group-id> \
  --log-stream-id <stream-id> \
  --start-time <start> \
  --end-time <end> \
  --keyword <keyword> \
  --pretty
```

## ModelArts 训练作业渐进诊断

排查 ModelArts 训练失败或长时间无进展时，按成本和敏感度从低到高收集证据：

1. job detail：状态、创建/开始/结束时间、资源规格、当前 stage 和最近更新时间；
2. failure analysis / task message：平台给出的失败摘要和目标 task；
3. error events / stages：失败阶段、相关事件和受影响 task；
4. target task log preview：只读取目标 task 的有限时间窗和错误附近片段；
5. 临时 OBS 完整日志 URL：只有前面证据不足时才使用。

判断边界：

- job 为 `Running` 不等于没有卡住；需要同时看 stage、最近进度时间和日志是否持续前进。
- traceback 往往给出直接失败点，但 wrapper 异常或 collective abort 可能只是其他 task 先失败后的连锁结果，需要跨 task 证据。
- 报告必须写明置信度和缺失证据。只有状态、没有进度/日志变化时，不输出确定根因。
- 临时 OBS 日志 URL 属于敏感且短时有效的信息，不写入最终输出、planning 文件或提交内容。
- 诊断流程不自动修改训练代码、资源规格、镜像、网络或安全设置，也不使用跳过 TLS 验证的方式取日志。

## Boundaries

- CES alarm creation and notification changes are planner-only until a separate reviewed change flow exists.
- Empty metrics are not automatically a fault. Check region, namespace, dimension, period, time range, and collection delay first.
- Logs can contain sensitive application data. Keep queries narrow and summarize only the fields needed for the task.
- A job ID, `Running`, task accepted, log URL, or one traceback does not by itself prove the training job is healthy, complete, or fully diagnosed.
