# 验收标准 — huawei-cloud-voucher-assistant

## 功能验收

| # | 场景 | 预期行为 |
|---|------|---------|
| 1 | 查询代金券（`list_vouchers`） | BSS 可用时返回已有余额+明细；未配置 AK/SK 时返回配置提示 |
| 2 | 查询任务列表（`list_tasks`） | fwdo 匿名可用，返回成长中心公开任务列表（含周期类型 LIMIT/DAILY/WEEKLY/MONTHLY） |
| 3 | 推荐任务（`recommend_tasks`） | fwdo 匿名可用，按积分收益排序返回推荐列表 + 月潜力汇总 |
| 4 | 余额足够购买 | 计算全额抵扣方案，让用户确认 |
| 5 | 余额不足购买 | 输出 ①低规格推荐 ②券+现金组合 |

## 能力分级验收

| 级别 | 行为 |
|------|------|
| R3 查询/分析 | 自动执行，无人值守，只读 |
| R2 写操作 | 预览 + `--confirm` 显式确认后执行；金额二次校验 |

## 数据验收

- 余额/代金券数据必须来自数据层 Adapter，分析层不得直接访问网络。
- 分析层输出为结构化 JSON，字段稳定可被上层消费。

## 文件规范验收

- 目录 `skills/bss/voucher/huawei-cloud-voucher-assistant/`
- 含 `SKILL.md`、`scripts/`、`references/`
- `SKILL.md` frontmatter 含 `name` 与 `description`（含中英触发词）
- Python 3.6+ 纯标准库，零第三方依赖（BSS 客户端用 `urllib`）

## 安全验收

- 代金券抵扣金额须二次校验，不得超余额。
- 写操作缺 `--confirm` 一律不执行。
- 不记录、不回显 AK/SK。