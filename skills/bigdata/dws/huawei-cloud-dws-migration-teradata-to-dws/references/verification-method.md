# Verification Method - Teradata to DWS Migration

本文档描述 Teradata → DWS 迁移的验证方法，覆盖迁移前预检、结构迁移验证、数据迁移验证与功能验证。

## Overview

| 阶段 | 验证点 | 工具/脚本 |
|------|--------|-----------|
| 迁移前 | 源端可读性、目标端连通性、类型兼容性 | `pre_migration_check.py` |
| 结构迁移 | DDL 转换正确性、PPI 分区转换、视图/宏/存储过程 | `migrate_schema.py`、`migrate_views_procs.py` |
| 数据迁移 | 行数一致、抽样比对、TIMESTAMP 精确值 | `migrate_data.py`、`validate_migration.py` |
| 功能验证 | 视图/存储过程可执行、关键查询结果一致 | `validate_functional.py` |

## 1. Pre-migration Check

```bash
python pre_migration_check.py --source-host <td-host> --source-db <td-db> \
  --target-host <dws-host> --target-db <dws-db> --target-schema <schema>
```

**Expected results**：

- 源端 Teradata 以只读模式连接成功，所有表可访问（SELECT 权限）
- 目标端 DWS 可连接，目标 schema 存在
- 数据类型映射无不支持项（例如 DWS 外表场景下 DATE 类型限制已识别）
- 未检测到禁止的源端写操作

## 2. Schema Migration Verification

```bash
python migrate_schema.py --source-host <td-host> --source-db <td-db> \
  --target-host <dws-host> --target-db <dws-db> --target-schema <schema>
```

**Expected results**：

- 所有表结构按 `references/datatype-mapping.md` 映射成功创建
- PPI 分区表按 SKILL.md「PPI 分区表转换」章节规则转换（含默认分区/降级注释）
- 重复表场景：交互模式确认、非交互模式使用 `--force`
- 执行含中文注释的 DDL 无编码错误（连接已 `SET client_encoding TO 'UTF8'`）

## 3. Data Migration Verification

```bash
python migrate_data.py --source-host <td-host> --source-db <td-db> \
  --target-host <dws-host> --target-db <dws-db> --target-schema <schema> \
  --method copy

python validate_migration.py --source-host <td-host> --source-db <td-db> \
  --target-host <dws-host> --target-db <dws-db> --target-schema <schema> \
  --checks row_count_check sample_check timestamp_check --sample-ratio 0.01
```

**Expected results**：

- 每张表的 `COUNT(*)` 源端与目标端一致
- 抽样列值（col_schema）逐行一致，无类型转换异常
- TIMESTAMP 列精确值一致（启用 `--timezone-adjust` 时按 `--source-tz` → `--target-tz` 补偿）
- OBS 方式（`--method obs`）下导出的 CSV 文件行数与目标端导入行数一致

## 4. Functional Verification

```bash
python validate_functional.py --target-host <dws-host> --target-db <dws-db> \
  --target-schema <schema> --objs "view_sales,proc_monthly_rollup"
```

**Expected results**：

- 迁移后的视图可成功查询（与源端返回结构对应）
- 迁移后的宏/存储过程可编译并执行
- QUALIFY 转换（CTE + ROW_NUMBER）执行无语法错误

## 5. Automation / CI Integration

验证脚本提供 `--exit-on-error` 参数：任一校验失败时以非零退出码结束，便于接入 CI 流水线；日志与校验报告输出到指定目录，供人工复核。