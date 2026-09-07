# WAF Policy Readiness Candidate Playbook

## 目标

为 WAF 从 metadata-backed 晋级 curated 前建立 host、policy、rule 和 event 的只读检查边界。

## 当前状态

- 已 live-smoked：`ListAntileakagePolicyRules`
- 晋级前还需要至少 1 条额外 read-only `command_shape_ok` evidence。

## 候选检查

```bash
python3 scripts/hcloud_resource_discovery.py --service WAF --operation ListAntileakagePolicyRules --region=<region> --pretty
python3 scripts/hcloud_resource_discovery.py --service WAF --operation ListHost --region=<region> --limit=20 --pretty
python3 scripts/hcloud_resource_discovery.py --service WAF --operation ListInstance --region=<region> --limit=20 --pretty
```

有 policy ID 后：

```bash
python3 scripts/hcloud_resource_query.py --service WAF --operation ListCcRules --region=<region> --param policy_id=<policy-id> --pretty
```

## 风险边界

WAF mutation 直接影响安全策略，默认 hard guard。新增、批量修改或删除规则前必须审查 host、policy、规则类型、动作和误拦截影响；晋级前不允许 submit。
