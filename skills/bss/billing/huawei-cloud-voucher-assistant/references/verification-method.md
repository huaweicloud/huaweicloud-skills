# 验证方法 — huawei-cloud-voucher-assistant

## 离线验证（分析层，无需数据源）

```bash
cd scripts

# 1) 余额判断：全额 / 部分 / 不足
python voucher_assistant.py analyze_voucher_coverage --balance 100 --price 80
python voucher_assistant.py analyze_voucher_coverage --balance 50 --price 80
python voucher_assistant.py analyze_voucher_coverage --balance 0 --price 80

# 2) 低规格 + 组合方案推荐
python voucher_assistant.py recommend_discount_plan --balance 50 --price 80 \
  --alt "ecs:c7.large.2:40" --alt "ecs:s6.large.2:30"
```

预期：分析类 action 均输出结构化 JSON，无报错。

## BSS 数据源验证（需配置 AK/SK）

```bash
cd scripts

# 配置
export HW_ACCESS_KEY=<你的AK>
export HW_SECRET_KEY=<你的SK>
export HW_DOMAIN_ID=<租户ID>

# 1) 查询代金券余额 + 明细
python voucher_assistant.py list_vouchers

# 2) 代金券适用服务（本地知识库）
python voucher_assistant.py list_voucher_applicable_services
```

## fwdo 任务列表验证（零配置，匿名）

```bash
cd scripts

# 查询成长中心公开任务列表
python voucher_assistant.py list_tasks

# 根据任务列表推荐值得优先做的任务
python voucher_assistant.py recommend_tasks
python voucher_assistant.py recommend_tasks --top-n 3
```

预期：返回任务列表 JSON，含 title/bonus/categoryName/周期类型等字段；无需 AK/SK。`recommend_tasks` 返回按积分收益降序排列的推荐列表 + 月潜力汇总。

## 数据源接入后验证

- `list_vouchers` 返回真实余额与明细（BSS）
- `apply_voucher`（不带 `--confirm`）仅预览
- 带 `--confirm` 执行抵扣前，先核对预览金额

## 单测（可选）

```bash
python -m pytest tests/test_analyzer.py -v
```