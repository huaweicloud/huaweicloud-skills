# 跨 Agent 行为评估

这套评估用于比较多个独立 Agent 宿主使用同一版本
`huawei-cloud-solution-ops` 时的真实行为。评估工具只负责固定题目、生成记录模板、校验人工观察结果和汇总；
它**不自动执行 Agent**、**不访问华为云**，也不会创建、修改或删除资源。

## 1. 查看可用场景

```bash
python3 scripts/hcloud_cross_agent_eval.py --pretty list
```

默认包含四个无写操作场景和一个需要显式授权的真实变更场景。第一次比较建议先跑：

- `inventory-beijing4`
- `billing-month-estimate`
- `all-region-resource-diagram`
- `elb-delete-dependency-plan`

`ecs-create-uname-cleanup` 会产生真实费用和副作用，只有隔离账号、清理范围和确认机制都准备好时才运行。

## 2. 固定测试输入

```bash
python3 scripts/hcloud_cross_agent_eval.py --pretty render \
  --case inventory-beijing4
```

把返回的 `prompt` 原样交给待测 Agent。不同 Agent/模型必须使用相同 Skill revision、权限、region、
workspace 初始状态、最大运行时间和用户输入，不能临时替某个 Agent 补充提示。

## 3. 生成运行记录

```bash
python3 scripts/hcloud_cross_agent_eval.py --pretty template \
  --case inventory-beijing4 \
  --run-id local-agent-a-001
```

把 `result` 保存到评测者自己的结果目录，填写 Agent、模型、权限、耗时、工具调用次数和每个 check。
每个 `pass`、`fail` 或 `not_observable` 都必须引用可复核的 trace、回复或 artifact；不能根据印象打分。
真实账号 ID、资源 ID 和日志在分享前脱敏，AK/SK、密码、私钥和 token 不得进入结果。

## 4. 校验和汇总

```bash
python3 scripts/hcloud_cross_agent_eval.py --pretty validate \
  --input <one-result.json>

python3 scripts/hcloud_cross_agent_eval.py --pretty aggregate \
  --input <result-list.json>
```

汇总保留 Agent、模型、case、通过/失败/不可观察数量以及 check 的原始分子分母。秘密泄露、未授权副作用、
重复副作用、虚假完成或跨 task 污染属于硬失败，不能被其他 check 抵消。

## 5. 固化基线并比较候选

同一 `Agent × 模型 × case` 建议先收集至少 3 次有效结果，并把这些结果组成 JSON 数组。基线命令只读取
本地结果，不启动 Agent：

```bash
python3 scripts/hcloud_cross_agent_eval.py --pretty baseline \
  --input <baseline-results.json> \
  --baseline-id <baseline-id> > <baseline.json>

python3 scripts/hcloud_cross_agent_eval.py --pretty compare \
  --baseline <baseline.json> \
  --input <candidate-results.json>
```

基线记录场景包和输入的确定性摘要、每组原始分子/分母、check 分布和耗时/工具调用等描述性统计。
比较结果只给出 `regression_observed`、`no_regression_observed`、`insufficient_evidence` 等
**advisory（建议性）证据**，不声明统计显著性，也不阻断 Agent、平台部署或云操作。缺少相同
Agent、模型、case 的基线时不会强行比较。

## 6. 本地 journal 摘要

如果脚本运行时已经产生可选 JSONL journal，可以在本机做只读聚合：

```bash
python3 scripts/hcloud_cross_agent_eval.py --pretty journal-summary \
  --input <run-journal.jsonl>
```

输出只保留事件类型、服务、operation、结果、错误类别及计数，不返回原始事件、时间戳、资源或账号
ID、profile、路径和自由文本。该命令不联网、不上传、不跨用户聚合，也不会自动把 journal 事件判成
某个 check 的通过或失败；最终评分仍由评测者依据可复核证据填写。

## 7. 建议运行方式

- 每个 `Agent × 模型 × case` 至少重复 3 次；首次体验可以先跑 1 次发现明显问题。
- 优先比较同一 Skill commit，不把模型、权限或网络差异归因给 Skill。
- 先跑无写操作场景；真实变更场景必须单独确认。
- 失败时记录 adoption state：没有读取 Skill、读取但没采用、采用后失败、采用后成功或不可观察。
- 不只看总分，同时比较首个有效进展时间、总耗时、工具调用数、失败重试和最终完成准确性。

更完整的指标定义、重复运行要求和记录原则见 `tests/unified-mechanism-evaluation.md`。
