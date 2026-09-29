# Acceptance Criteria - Teradata to DWS Migration

本文档定义 Teradata → DWS 迁移任务的验收标准。全部条件满足后，迁移方可视为完成。

## 1. Pre-migration Checks

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-1 | 源端 Teradata 以只读方式连接成功 | `pre_migration_check.py` 无错误退出 |
| AC-2 | 目标端 DWS 连接信息（主机、端口、库、schema）有效 | 预检通过 |
| AC-3 | 所有待迁移表均可 SELECT 访问 | 预检列出全部表无拒绝项 |
| AC-4 | 无不受支持的数据类型或已识别并给出处理方案 | 预检报告无未处理异常 |

## 2. Schema Migration

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-5 | 全部表结构按映射规则创建成功 | `migrate_schema.py` 日志显示 0 失败 |
| AC-6 | PPI 分区表转换符合规则（单级 RANGE、LIST、降级注释） | 抽查 DDL 与转换规则一致 |
| AC-7 | 视图/宏/存储过程迁移完成且语法正确 | `migrate_views_procs.py` 报告通过 |
| AC-8 | 重复表处理符合要求（交互确认或 `--force`） | 无静默跳过 |

## 3. Data Migration

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-9 | 每张表行数一致：`COUNT(*)` 源端 = 目标端 | `--checks row_count_check` 全通过 |
| AC-10 | 抽样校验一致：抽样列值与类型无异常 | `--checks sample_check` 全通过 |
| AC-11 | TIMESTAMP 精确值一致（含时区补偿正确） | `--checks timestamp_check` 全通过 |
| AC-12 | OBS 方式下 CSV 导出行数 = 目标端导入行数 | 对账一致 |

## 4. Functional Verification

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-13 | 迁移后的视图可查询，返回结构正确 | `validate_functional.py` 通过 |
| AC-14 | 迁移后的存储过程/宏可执行 | 目标端运行成功 |
| AC-15 | QUALIFY 转换（CTE + ROW_NUMBER）执行无误 | 无语法错误 |

## 5. Safety & Compliance

| # | Criterion | Verification |
|---|-----------|--------------|
| AC-16 | 源端全程只读，未发生任何写操作 | 连接配置/日志无写操作 |
| AC-17 | 无硬编码凭据（真实或占位符）落入代码/文档 | 安全扫描通过 |
| AC-18 | 迁移日志、校验报告完整可追溯 | 报告文件生成 |

## Sign-off

- 所有 AC-1 ~ AC-18 达成为「通过」
- 存在任一项失败时，修复后重新运行对应步骤并复测
- 用户确认验收报告后，迁移任务关闭