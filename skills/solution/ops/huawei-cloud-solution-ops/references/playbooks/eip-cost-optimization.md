# EIP Cost Optimization Readiness

## 目标

帮助用户识别可能产生持续费用的 EIP，尤其是未绑定、临时测试、带宽过大、缺 owner/tag 的公网 IP。输出只能是候选和 review checklist，不能把候选资源直接变成释放、删除或降配授权。

## 适用场景

- 用户问“为什么公网 IP 一直扣费”。
- 用户想找闲置 EIP、未绑定 EIP 或高带宽 EIP。
- 用户想做 EIP 成本报告、跨 region 盘点或回收评审。
- 用户准备释放、解绑或复用某个 EIP。

## 标准流程

1. 先做账号/region/project 上下文检查：

```bash
python3 scripts/hcloud_context_inspect.py --pretty
```

2. 生成 EIP 只读盘点命令：

```bash
python3 scripts/hcloud_resource_discovery.py \
  --service EIP \
  --operation ListPublicips \
  --region=<region> \
  --project-id=<project-id> \
  --limit=100 \
  --pretty
```

3. 如果已有保存的查询 JSON，用 idle audit 识别候选：

```bash
python3 scripts/hcloud_idle_audit.py \
  --input-json-file EIP=<list-publicips-result.json> \
  --pretty
```

4. 如果用户要求释放或解绑，先进入回收评审：

```bash
python3 scripts/hcloud_teardown_plan.py \
  --idle-audit-json-file <saved-idle-audit-output.json> \
  --pretty
```

真实解绑、释放或带宽调整必须重新确认 exact EIP、绑定对象、计费影响和回滚方式。

## 候选判断

| 候选类型 | 证据 | 风险 |
| --- | --- | --- |
| 未绑定 EIP | 无 `port_id`、无绑定资源、状态为 `DOWN`/`UNBOUND`/等价状态 | 仍可能有保留费用或带宽费用。 |
| 测试 EIP | 名称/tag 显示 test/dev/temp，或无 owner/tag | 需要确认业务归属，不能仅凭命名释放。 |
| 高带宽 EIP | bandwidth size 明显高于当前访问需求 | 只能建议 review，不能自动降配。 |
| 异常绑定 | 绑定对象和用户预期 ECS/ELB/NAT 不一致 | 停止协议验收，先确认绑定关系。 |

## 必查证据

- EIP ID 和公网 IP。
- region / project / enterprise project。
- 绑定对象：ECS port、ELB、NAT 或其它资源。
- bandwidth size、计费模式、创建时间。
- owner / app / env / expiry tag。
- 最近流量、访问日志或业务依赖。
- 账单侧是否仍有费用记录。

## 用户输出边界

- “候选”不等于“可以释放”。
- 不根据单页账单或单 region 盘点下全局结论。
- 不生成 release/delete/unsubscribe submit 命令。
- 如果用户确认要释放，必须先确认备份、DNS/CDN/ELB/NAT/ECS 依赖和回滚方案。

## 和账单联动

如果用户问“为什么扣费”，先把 EIP 盘点和账单周期对齐：

- 用 `billing-cost-governance.md` 规划 BSS/Cost 只读查询。
- 用 `hcloud_billing_result_summarize.py` 做脱敏摘要。
- 用 EIP ID、资源名称、region、时间范围做人工关联，不能在证据不足时自动归因。
