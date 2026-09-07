# Governance Guide

治理任务覆盖审计、标签、备份、账单成本、闲置审计、回收前检查和合规证据。默认 planner-only 或只读证据，不默认做治理写操作。

## hcloud-first 路径

1. 读取 `references/playbooks/cts-audit-readiness.md`、`tms-tag-governance.md`、`billing-cost-governance.md`、`cbr-backup-posture.md`、`rms-config-governance.md`。
2. 账号盘点先走 `hcloud_account_inventory.py`；真实查询必须显式 `--execute`。
3. 闲置候选用 `hcloud_idle_audit.py` 分析保存的只读 JSON；候选不等于删除授权。
4. 回收前检查用 `hcloud_teardown_plan.py` 输出依赖顺序、证据缺口和人工确认点。
5. P1 治理服务用 `hcloud_closure_plan.py --tier governance` 汇总范围、证据、隐私门禁、review plan 和晋级缺口。
6. 账单/成本只用 `hcloud_billing_cost_probe.py` 和 `hcloud_billing_readonly.py` 生成 request spec，不签名、不发送请求。

## SDK 补充

- 候选 SDK 补充：`CTS:ListTraces`，当前 `execute_allowed=false`。
- 用途：未来可补充 trace 查询的请求类型和参数结构。
- 不用途：不要用 SDK runner 修改审计、标签、备份、预算或资源合规策略。

## 不要做

- 不要从资源清单推断真实账单金额。
- 不要在未确认 owner、标签、备份、依赖和业务窗口前生成删除/释放/退订命令。
- 不要输出完整审计 trace、账单、日志或用户隐私字段。
