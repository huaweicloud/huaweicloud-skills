---
name: huawei-cloud-dws-migration-teradata-to-dws
description: |
  Teradata 到华为云 DWS（数据仓库服务）的全流程迁移 skill。严格遵循源端 Teradata 只读、
  Teradata→DWS 数据类型映射、先迁移表结构(DDL)后迁移数据(DML)、OBS 临时目录导出、
  COPY 命令批量导入等核心规则。包含迁移前预检(pre_migration_check)、表结构迁移(migrate_schema)、
  PPI 分区表转换(ppi_converter)、视图/宏/存储过程迁移(migrate_views_procs)、
  数据迁移(migrate_data)与迁移验证(validate_migration)等完整工具链。
  Applicable when users need to migrate Teradata databases to Huawei Cloud DWS,
  convert Teradata schema/data types to DWS, or move TD workloads to GaussDB DWS.
  触发词："Teradata迁移"、"迁移到DWS"、"Teradata to DWS"、"TD迁移"、"DWS迁移"、
  "Teradata转DWS"、"迁移Teradata"、"TD到DWS"、"Migrate Teradata"、"Teradata to GaussDB"、"migrate to DWS"
tags: [huawei-cloud, dws, teradata, migration, data-warehouse]
---

# Teradata to DWS Migration Skill

## 概述

本 skill 用于将 Teradata 数据库迁移到华为云 DWS（数据仓库服务）。迁移过程严格遵循以下核心规则：

1. **禁止在源端 Teradata 进行任何写操作** — 所有对源端的访问均为只读
2. **遵循 Teradata 到 DWS 的数据类型映射规则** — 参考 https://support.huaweicloud.com/migration-dws/dws_15_0131.html
3. **迁移分为两大步骤** — 先迁移表结构（DDL），后迁移表数据（DML）
4. **重复表需用户确认** — 发现 DWS 中已存在的表时，列出并询问用户确认后才删除重建
5. **OBS 临时目录** — 数据导出到 OBS 而非本地磁盘，避免磁盘容量问题
6. **COPY 命令批量导入** — 使用 COPY 命令替代逐行 INSERT，性能提升 10-100 倍，支持 TB 级数据

## 迁移流程

```
Step 0   迁移前预检     pre_migration_check.py  网络/源端/目标端/业务影响/时间预估（全部只读）
  ↓
Step 1   表结构 DDL    migrate_schema.py       只读提取 DDL → 数据类型映射 → PPI 分区转换(ppi_converter)
                                                  → 生成 DWS DDL → 重复表确认 → 建表
  ↓
Step 2   表数据 DML    migrate_data.py         CSV/OBS 临时目录导出 → 实时进度 → COPY/OBS 外表导入 → 校验
  ↓
Step 2.5 视图/宏/过程  migrate_views_procs.py  提取(SHOW VIEW/MACRO/PROCEDURE) → SQL 语法转换 → DWS 重建
  ↓
Step 3   数据校验       validate_migration.py   表数/行数/列/聚合/抽样/TIMESTAMP 精确值比对
  ↓
Step 3.5 功能性校验     validate_functional.py  宏/存储过程/视图调用与结果比对
```

## 使用前提

### 环境要求

- Python 3.8+
- Teradata ODBC 驱动 或 teradatasql Python 包
- DWS gsql 客户端 或 psycopg2 Python 包
- （可选）DSC 工具 — 用于 SQL 脚本迁移，需 JDK 1.8+
- （可选）obsutil — 用于通过 OBS 中转导入数据

### 安装依赖

```bash
pip3 install teradatasql psycopg2-binary
```

### 配置文件

在使用前，需要准备以下配置文件：

1. **Teradata 连接配置** — 参考 `config/teradata_config_template.ini`
2. **DWS 连接配置** — 参考 `config/dws_config_template.ini`
3. **迁移配置文件**（视图/宏/存储过程迁移与功能性校验使用）— 参考模板 `config/migration_config_template.yaml`，复制为 `config/migration_config.yaml` 并填写 Teradata/DWS 连接信息（含 `source_database`、目标 `schema` 等字段），格式说明见下文「迁移配置文件（migration_config.yaml）」

### 迁移配置文件（migration_config.yaml）

`migrate_views_procs.py`（Step 2.5）与 `validate_functional.py`（Step 3.5）通过 `--config config/migration_config.yaml` 读取 Teradata/DWS 连接信息。该文件不在 skill 包内随附，需从模板创建：

```bash
cp config/migration_config_template.yaml config/migration_config.yaml
# 编辑 config/migration_config.yaml 填写实际连接信息
```

**格式说明**（YAML，字段说明见模板内注释）：

```yaml
teradata:
  host: <teradata_host>          # Teradata 主机地址
  port: 1025                     # Teradata 端口（默认 1025）
  user: <td_user>                # Teradata 只读账号
  password: <td_password>        # 或通过环境变量 TD_PASSWORD 注入
  database: DBC                  # 连接数据库（默认 DBC）
  logmech: TD2                   # 登录机制（默认 TD2）
  source_database: <source_db>   # 待迁移的源数据库名（必填）
dws:
  host: <dws_host>               # DWS 集群连接端点
  port: 25308                    # DWS 端口（默认 25308）
  database: <dws_database>       # DWS 数据库名
  user: <dws_user>               # DWS 账号
  password: <dws_password>       # 或通过环境变量 DWS_PASSWORD 注入
  schema: public                 # 目标 Schema（默认 public）
  target_schema: public          # target_schema 优先于 schema 用于目标表
```

**密码注入**：`migrate_views_procs.py` 要求配置文件中必须填写 `password` 字段；`validate_functional.py` 支持密码留空并回退读取 `TD_PASSWORD` / `DWS_PASSWORD` 环境变量。为安全起见，可优先通过环境变量注入密码（`validate_functional.py` 场景），避免明文落盘。

## 使用方法

### 迁移前预检（推荐先执行）

```bash
python3 scripts/pre_migration_check.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema <schema_name> \
    --output-dir ./output
```

预检内容包括：
- **网络连通性**：源端 Teradata 和目标端 DWS 端口可达性
- **源端 Teradata**：连接测试、活跃会话数、运行中查询、CPU 使用率、数据量预估
- **目标端 DWS**：连接测试、集群版本、连接数、存储空间、Schema 存在性、节点状态
- **业务影响评估**：根据源端负载评估迁移风险等级（低/中/高），给出建议
- **迁移时间预估**：按 direct/csv/obs 三种方式估算迁移耗时

预检报告保存为 JSON 文件 `{schema}_pre_migration_check.json`。

### 完整迁移（预检 + 表结构 + 表数据 + 校验）

```bash
# Step 0: 预检
python3 scripts/pre_migration_check.py --td-config config/teradata_config.ini --dws-config config/dws_config.ini --schema <schema_name>

# Step 1: 迁移表结构
python3 scripts/migrate_schema.py --td-config config/teradata_config.ini --dws-config config/dws_config.ini --schema <schema_name>

# Step 2: 迁移表数据
python3 scripts/migrate_data.py --td-config config/teradata_config.ini --dws-config config/dws_config.ini --schema <schema_name> \
    --truncate-before-import --timezone-adjust --source-tz UTC-4 --target-tz UTC+8

# Step 2.5: 迁移视图/宏/存储过程
cp config/migration_config_template.yaml config/migration_config.yaml  # 首次使用：从模板创建迁移配置
python3 scripts/migrate_views_procs.py --config config/migration_config.yaml --types views,macros,procedures

# Step 3: 校验验证（含 TIMESTAMP 精确值比对）
python3 scripts/validate_migration.py --td-config config/teradata_config.ini --dws-config config/dws_config.ini --schema <schema_name> \
    --checks table_count row_count columns aggregate sampling timestamp_check \
    --timezone-adjust --source-tz UTC-4 --target-tz UTC+8

# Step 3.5: 功能性校验（宏/存储过程/视图）
python3 scripts/validate_functional.py --config config/migration_config.yaml \
    --output functional_validation_report.json
```

### 功能性校验（Step 3.5）

在数据校验通过后，对迁移的宏、存储过程、视图进行功能性验证：

可通过命令行参数直接指定连接信息（密码一律通过环境变量注入，不写在命令行）：

```bash
export TD_PASSWORD=<teradata-密码>
export DWS_PASSWORD=<dws-密码>

python3 scripts/validate_functional.py \
    --td-host <td_host> --td-user <td_user> \
    --td-database <td_database> \
    --dws-host <dws_host> --dws-port <dws_port> \
    --dws-db <dws_db> --dws-user <dws_user> \
    --dws-schema public \
    --output functional_validation_report.json
```

**校验内容**：

| 对象类型 | TD 端调用方式 | DWS 端调用方式 | 比较方式 |
|---------|-------------|--------------|---------|
| 宏 (Macro) | `EXEC macro_name()` | `SELECT * FROM func() AS (col_def)` | 行数 + 前20行数据排序比对 |
| 存储过程 | `CALL proc_name()` | `CALL proc_name()`（事务回滚） | 行数比较 / 执行不报错 |
| 视图 | `SELECT * FROM view` | `SELECT * FROM view` | 行数 + 前20行数据排序比对 |

**关键设计**：

- **宏列类型自动推断**：DWS `SETOF record` 函数调用需提供列定义列表，脚本通过 `pg_attribute` 自动推断返回列类型
- **写操作安全**：写操作存储过程在 DWS 端用事务执行后自动 `ROLLBACK`，不污染数据
- **带参数宏支持**：通过 `--macro-params` JSON 文件指定测试参数值
- **非确定性差异处理**：ROW_NUMBER() tie-breaking 等非确定性问题，比较时关注业务关键字段一致性

**校验报告**：JSON 格式，包含每个对象的校验状态、行数、匹配结果和错误信息

### 仅迁移表结构

```bash
python3 scripts/migrate_schema.py --td-config config/teradata_config.ini --dws-config config/dws_config.ini --schema <schema_name> --output-dir ./output
```

**重复表处理**：执行 DDL 前，脚本会检查 DWS 中已存在的表。如果发现重复表，将列出所有重复表及其行数，并等待用户输入 `yes` 确认后才删除重建。输入 `no` 则跳过这些表。

### 仅迁移表数据

#### 方式 1: CSV 中转（默认，适合中等表）

```bash
python3 scripts/migrate_data.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema <schema_name> \
    --database <td_database> \
    --method csv \
    --truncate-before-import \
    --timezone-adjust --source-tz UTC-4 --target-tz UTC+8
```

使用 COPY 命令批量导入，比逐行 INSERT 快 10-100 倍。

**新增选项**：
- `--truncate-before-import`：导入前自动清空目标表数据，避免重复导入导致数据翻倍
- `--timezone-adjust`：启用 TIMESTAMP 时区转换（自动偏移 TIMESTAMP 列值）
- `--source-tz` / `--target-tz`：指定源端/目标端时区（默认 UTC-4 / UTC+8）

#### 方式 2: OBS 外表并行导入（适合大表/TB级）

```bash
python3 scripts/migrate_data.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema <schema_name> \
    --database <td_database> \
    --method obs \
    --obs-config config/obs_config.ini \
    --obs-temp-dir migration/temp/<schema_name>
```

**OBS 临时目录**：CSV 数据导出到 OBS 而非本地磁盘，避免磁盘容量问题。脚本会显示 OBS 临时路径：
```
☁️ OBS 临时目录: obs://<bucket>/migration/temp/<schema_name>
   CSV 数据将导出到此 OBS 路径，避免本地磁盘容量问题
```

**并行导入**：通过 DWS 外表（Foreign Table）+ INSERT INTO ... SELECT 并行导入，支持配置并行度和分片大小，适合 TB 级数据迁移。

#### 方式 3: 直接导入（适合小表）

```bash
python3 scripts/migrate_data.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema <schema_name> \
    --database <td_database> \
    --method direct
```

#### 实时进度显示

数据迁移过程中，shell 窗口实时显示每张表的迁移进度：

```
┌─ [3/19] 16% ████░░░░░░░░░░░░░░░░░░░░░░░░
│  表: customer_orders
│  已用: 5.2min  预估剩余: 26.3min
└─ 开始迁移...
  📤 导出进度: ████░░░░░░ 40% (56,000/140,000 行, 12,000 rows/s)
  📤 导出完成: 140,000 行, 45.2MB, 11.7s, 12,000 rows/s
  📋 copy: COPY 导入 140,000 行...
  📥 COPY 导入完成: 140,000 行, 3.2s, 43,750 rows/s
  ✅ [3/19] 16% ████░░░░░░ customer_orders: 140,000 行, 15.1s
```

### 迁移视图/宏/存储过程（Step 2.5）

在表结构和数据迁移完成后，可继续迁移视图、宏和存储过程：

```bash
cp config/migration_config_template.yaml config/migration_config.yaml  # 首次使用：从模板创建迁移配置
python3 scripts/migrate_views_procs.py \
    --config config/migration_config.yaml \
    --types views,macros,procedures
```

**支持的转换**：

| 对象类型 | Teradata | DWS | 关键转换 |
|---------|----------|-----|---------|
| 视图 | CREATE VIEW | CREATE OR REPLACE VIEW | ZEROIFNULL→COALESCE, QUALIFY→CTE+ROW_NUMBER, GROUP BY 位置→列名 |
| 宏 | REPLACE MACRO | CREATE OR REPLACE FUNCTION | 参数引用 `:param`→`param`, 返回 SETOF record |
| 存储过程 | REPLACE PROCEDURE (SPL) | CREATE OR REPLACE PROCEDURE (PL/pgSQL) | SET→`:=`, WHILE..DO→WHILE..LOOP, LEAVE→EXIT |

**常用参数**：

- `--types`：指定迁移类型（`views,macros,procedures`，默认全部）
- `--views`/`--macros`/`--procedures`：指定对象名（逗号分隔）
- `--output-dir`：输出 DDL 到文件而不执行
- `--dry-run`：只转换不执行（不连接 DWS）

**SQL 语法自动转换**：

- `ZEROIFNULL(expr)` → `COALESCE(expr, 0)`
- `NULLIFZERO(expr)` → `NULLIF(expr, 0)`
- `QUALIFY ROW_NUMBER() OVER(...) = 1` → CTE + ROW_NUMBER() + WHERE 子句
- `GROUP BY 1, 2` → `GROUP BY 列名`（位置引用转列名）
- `EXTRACT(YEAR FROM date_col)` → `EXTRACT(YEAR FROM date_col)`（兼容）
- Teradata 数据库引用 `db.table` → `schema.table`

### PPI 分区表转换（Step 1.3.1）

`ppi_converter.py` 模块将 Teradata PPI (Partitioned Primary Index) 分区语法自动转换为 DWS 分区语法：

**支持的转换模式**：

| Teradata PPI 模式 | DWS 分区语法 | 说明 |
|-----------------|-------------|------|
| 单级 `RANGE_N` with `EACH INTERVAL '1' DAY` | `PARTITION BY RANGE` (按天) | 日级分区 |
| 单级 `RANGE_N` with `EACH INTERVAL 'N' MONTH` | `PARTITION BY RANGE` (按月) | 月级分区 |
| `RANGE_N` with `NO RANGE / UNKNOWN` | DWS 默认分区 | 自动添加默认分区 |
| `CASE_N` | `PARTITION BY LIST` | 列表分区 |
| 多级 `RANGE_N + CASE_N` | 单级 `PARTITION BY RANGE` (降级) | DWS 不支持 SUBPARTITION，降级为单级 RANGE，原 CASE_N 信息保留在注释中 |

**降级说明**：DWS (GaussDB) 不支持 `SUBPARTITION` 语法。当遇到 Teradata 多级 PPI（RANGE_N + CASE_N）时，自动降级为单级 RANGE 分区，原 CASE_N 子分区信息以注释形式保留在 DDL 中，供参考。

### 使用 DSC 工具迁移 SQL 脚本

离线 SQL 脚本迁移可使用 DSC 工具（`runDSC.sh -S teradata -I <input> -O <output> -L <log>`），无需连接数据库即可转换，转换后的脚本在 DWS 端用 gsql 执行（密码通过 `PGPASSWORD` 环境变量注入）。详细步骤见 `references/migration-guide.md`。

## 文件结构

```
huawei-cloud-dws-migration-teradata-to-dws/
├── SKILL.md                          # 本文档
├── scripts/
│   ├── teradata_reader.py            # Teradata 只读连接器（禁止写操作）
│   ├── dws_writer.py                 # DWS 连接和执行器
│   ├── datatype_mapping.py           # 数据类型映射模块
│   ├── pre_migration_check.py        # 迁移前预检脚本（Step 0）
│   ├── migrate_schema.py             # 表结构迁移脚本（Step 1）
│   ├── migrate_data.py               # 表数据迁移脚本（Step 2）
│   ├── migrate_views_procs.py        # 视图/宏/存储过程迁移脚本（Step 2.5，入口）
│   ├── sql_converter.py              # SQL 语法转换器（视图/宏/过程共用）
│   ├── macro_converter.py            # 宏 (MACRO→FUNCTION) 转换器
│   ├── procedure_converter.py        # 存储过程 (SPL→PL/pgSQL) 转换器
│   ├── ppi_converter.py              # PPI 分区表转换器（Teradata PPI → DWS 分区）
│   ├── validate_migration.py         # 数据校验脚本（Step 3）
│   └── validate_functional.py        # 功能性校验脚本（Step 3.5）
├── config/
│   ├── teradata_config_template.ini  # Teradata 连接配置模板
│   ├── dws_config_template.ini       # DWS 连接配置模板
│   ├── obs_config_template.ini       # OBS 连接配置模板（method=obs 时使用）
│   ├── migration_config_template.yaml # 视图/宏/过程迁移与功能性校验连接配置模板
│   └── features-teradata.properties  # DSC Teradata 配置模板
├── references/
│   ├── datatype-mapping.md           # 数据类型映射详细参考
│   ├── migration-guide.md            # 迁移指南
│   ├── cli-installation-guide.md     # KooCLI 安装与凭证配置
│   ├── iam-policies.md               # 最小权限策略
│   ├── verification-method.md        # 迁移验证方法
│   ├── acceptance-criteria.md        # 验收标准
│   └── forbidden-operations.md       # 高危操作禁止列表
└── examples/
    └── sample_migration.sh           # 示例迁移脚本
```

## 核心规则详解

### 规则 1：禁止源端写操作

`teradata_reader.py` 模块通过以下机制确保不会对源端 Teradata 执行任何写操作：

- SQL 语句白名单过滤：只允许 SELECT、SHOW、HELP、SELECT 等只读语句
- 禁止源端一切数据变更/结构变更类操作（增、删、改、清空、建表、删表、改表结构、事务控制等写操作）
- 连接以只读模式建立
- 所有 SQL 在执行前经过安全检查

**完整的高危操作禁止列表见 `references/forbidden-operations.md`**，涵盖：
- 源端 DDL/DML/事务/权限/会话/数据库管理禁止操作
- 目标端破坏性 DDL/数据操作/权限滥用禁止操作
- 系统环境级禁止操作（文件/网络/进程）
- 数据安全/隐私禁止操作
- 迁移逻辑禁止操作
- AI 决策引擎禁止操作
- 只读白名单和安全校验实现规范

### 规则 2：数据类型映射

数据类型映射严格遵循华为云官方文档：
https://support.huaweicloud.com/migration-dws/dws_15_0131.html

完整映射表见 `references/datatype-mapping.md`。

### 规则 3：先表结构后表数据

迁移严格按顺序执行：
1. **表结构迁移** (`migrate_schema.py`)：提取 Teradata DDL → 数据类型转换 → 在 DWS 创建表
2. **表数据迁移** (`migrate_data.py`)：从 Teradata 导出数据 → 导入到 DWS
3. **校验验证** (`validate_migration.py`)：比对源端和目标端数据一致性

### 规则 4：迁移前预检

在执行迁移前，**强烈建议**先运行预检脚本 `pre_migration_check.py`，以：

- 确认源端和目标端网络连通
- 评估源端 Teradata 当前负载，确保迁移不会影响源端业务
- 检查目标端 DWS 存储空间、连接数等资源是否充足
- 预估迁移时间和风险等级

预检脚本**仅执行只读查询**，不会对源端或目标端产生任何副作用。

### 规则 5：迁移进度显示

`migrate_schema.py` 和 `migrate_data.py` 均内置实时进度显示：

- **整体进度条**：`[3/19] 16% ████░░░░░░` 显示当前表序号和百分比
- **预估剩余时间**：基于已完成表的平均耗时动态估算
- **单表耗时统计**：每张表迁移完成后显示行数、耗时和吞吐率
- **子步骤进度**：导出、上传、导入各子步骤独立显示进度和速度
- **迁移汇总报告**：所有表完成后输出汇总表，含每表状态、行数和耗时

### 规则 6：重复表检测与用户确认

`migrate_schema.py` 在执行 DDL 前自动检测 DWS 中已存在的表：

1. **检测阶段**：对比源端表列表和 DWS 已有表，找出重复表
2. **确认阶段**：列出所有重复表及其当前行数，等待用户输入
   - 输入 `yes`：删除重复表并重建
   - 输入 `no`：跳过重复表，保留现有结构
   - 输入 `全部`：确认删除重建所有重复表
   - 输入 `跳过`：跳过所有重复表，仅迁移新表
3. **`--force` 模式**：跳过交互确认，自动删除重建重复表（适用于脚本/CI 环境）
4. **非交互环境处理**：当检测到 stdin 不是终端（如通过脚本/管道运行）且有重复表但未指定 `--force` 时，脚本会打印清晰错误信息并以错误码 1 退出，避免静默跳过 DDL 执行
5. **安全保证**：不会在用户未确认的情况下删除任何表

### 规则 7：OBS 临时目录

`migrate_data.py` 支持将 CSV 数据导出到 OBS 临时目录而非本地磁盘：

- **避免磁盘容量问题**：TB 级数据不再受本地磁盘空间限制
- **路径可见**：脚本启动时显示 OBS 临时目录路径
- **自动清理**：迁移完成后自动清理 OBS 临时文件
- **配置灵活**：通过 `--obs-temp-dir` 参数指定 OBS 路径

### 规则 8：COPY 命令批量导入

`dws_writer.py` 提供三种数据导入方式，性能递增：

| 方式 | 适用场景 | 性能 | 说明 |
|------|---------|------|------|
| 逐行 INSERT | 小表（<1万行） | 1x | 基准 |
| COPY 命令 | 中等表（1万-1亿行） | 10-100x | CSV 文件批量导入 |
| OBS 外表并行 | 大表（>1亿行/TB级） | 50-500x | 外表+并行INSERT SELECT |

**OBS 外表并行导入**通过创建 DWS Foreign Table 读取 OBS 上的 CSV 文件，然后执行 `INSERT INTO target SELECT * FROM foreign_table` 并行导入，是 TB 级数据迁移的最优方案。

## KooCLI 命令格式标准

核心迁移工具链为 Python 脚本，数据迁移不依赖 KooCLI；以下辅助场景使用华为云 KooCLI（`hcloud`）：

1. 查询 DWS 集群列表与连接信息（确认集群状态、版本、连接端点）
2. 查看 OBS 桶列表与对象（`--method obs` 迁移前确认桶可用）

命令格式：区域参数统一通过 `--cli-region` 指定。

```bash
# 查询 DWS 集群列表
hcloud DWS ListClusters --cli-region=cn-south-1 --project_id=<project_id>

# 查询 OBS 桶列表（hcloud obs 为 obsutil 透传命令，使用 obsutil 风格语法）
hcloud obs ls
```

KooCLI 安装、凭证配置与网络排查见 `references/cli-installation-guide.md`。

## 参考文档

- **高危操作禁止列表**：`references/forbidden-operations.md`
- **IAM 权限要求**：`references/iam-policies.md`
- **KooCLI 安装与命令格式**：`references/cli-installation-guide.md`
- **迁移验证方法**：`references/verification-method.md`
- **验收标准**：`references/acceptance-criteria.md`
- **OBS 配置文件模板**：`references/obs-config-template.md`
- **完整变更历史**：`references/change-log.md`
- OBS 参考文档：`obs://cloud-bigdata/teradata_to_dws/dws_doc/`
- 数据类型映射：https://support.huaweicloud.com/migration-dws/dws_15_0131.html
- DWS 数据迁移与同步指南
- DWS 工具指南（DSC、DataCheck）
- DWS SQL 语法参考

## 注意事项

1. **网络连通性**：确保执行环境能同时连接 Teradata 和 DWS
2. **权限要求**：Teradata 需要 SELECT 权限；DWS 需要建表和数据写入权限
3. **数据量评估**：大表数据迁移建议使用 OBS 并行导入或 GDS 工具
4. **字符编码**：确保源端和目标端字符编码一致（推荐 UTF-8）
5. **兼容性**：DWS 兼容 Teradata 模式下，外表不支持 DATE 类型
6. **DSC 工具**：DSC 是离线工具，不需要连接数据库，可零停机迁移 SQL 脚本
7. **OBS 配置**：使用 `--method obs` 时需要准备 OBS 配置文件（包含 bucket、AK/SK、endpoint），并确保 obsutil 已配置
8. **重复表处理**：迁移表结构时如遇到已存在的表，脚本会暂停等待用户确认；非交互环境（脚本/管道）下需使用 `--force` 参数，否则将以错误码退出
9. **TB 级数据**：对于 TB 级数据迁移，推荐使用 `--method obs` + OBS 外表并行导入，避免本地磁盘瓶颈

## OBS 配置文件模板

使用 `--method obs` 时，需准备 OBS 配置文件 `config/obs_config.ini`。完整配置模板与参数说明见 `references/obs-config-template.md`。

## 更新日志

完整变更历史见 `references/change-log.md`。
