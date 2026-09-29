# Teradata 到 DWS 迁移指南

## 1. 迁移概述

本文档描述将 Teradata 数据库迁移到华为云 DWS（数据仓库服务）的完整流程。

### 1.1 核心原则

1. **禁止源端写操作** — 所有对 Teradata 的访问均为只读，不修改源端任何数据
2. **先表结构后表数据** — 先完成 DDL 迁移（建表），再进行 DML 迁移（数据导入）
3. **数据类型映射** — 严格遵循华为云官方映射规则

### 1.2 迁移架构

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Teradata    │  只读   │  迁移执行机   │  写入   │    DWS       │
│  (源端)      │ ──────→ │              │ ──────→ │  (目标端)    │
└──────────────┘         └──────────────┘         └──────────────┘
                              │
                              │ (可选中转)
                              ▼
                         ┌──────────────┐
                         │     OBS      │
                         │  (对象存储)   │
                         └──────────────┘
```

## 2. 迁移步骤

### Step 1: 表结构迁移 (DDL)

#### 1.1 提取 Teradata 表结构

使用 `SHOW TABLE` 命令（只读操作）提取 DDL：

```sql
SHOW TABLE "database"."table_name";
```

或通过 DBC 元数据表查询列信息：

```sql
SELECT ColumnName, ColumnType, ColumnLength, DecimalTotalDigits,
       DecimalFractionalDigits, Nullable
FROM DBC.ColumnsV
WHERE DatabaseName = 'db' AND TableName = 'tbl'
ORDER BY ColumnId;
```

#### 1.2 数据类型转换

将 Teradata 类型映射为 DWS 类型，详见 `references/datatype-mapping.md`。

#### 1.3 在 DWS 创建表

执行转换后的 DDL，注意添加 `DISTRIBUTE BY` 子句：

```sql
CREATE TABLE "schema"."table_name" (
    col1 INTEGER,
    col2 VARCHAR(100),
    ...
)
DISTRIBUTE BY HASH(col1);
```

**分布策略选择建议：**
- **HASH(列)**：适合大表，选择高基数列作为分布键
- **ROUNDROBIN**：适合无法确定合适分布键的表
- **REPLICATION**：适合小表（维度表），每个节点存储完整副本

### Step 2: 表数据迁移 (DML)

#### 2.1 小表迁移（直接导入）

对于小表（< 100万行），可直接通过 Python 导出导入：

```bash
python3 scripts/migrate_data.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema mydb \
    --method direct
```

#### 2.2 大表迁移（通过 OBS 中转）

对于大表（> 100万行），建议通过 OBS 中转：

1. 从 Teradata 导出数据到 CSV 文件
2. 上传 CSV 到 OBS 桶
3. 在 DWS 创建 OBS 外表
4. 通过 `INSERT INTO ... SELECT` 从外表导入

```bash
python3 scripts/migrate_data.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema mydb \
    --method obs \
    --obs-bucket my-bucket \
    --obs-prefix migration/
```

#### 2.3 使用 DSC 工具迁移 SQL 脚本

DSC（Database Schema Convertor）是华为提供的离线 SQL 脚本迁移工具：

```bash
# 执行 DSC 转换
./runDSC.sh -S teradata -I <input_folder> -O <output_folder> -L <log_folder>

# 在 DWS 执行转换后的脚本
gsql -d <database> -p <port> -U <user> -W <password> -h <ip> -f <output_folder>/converted.sql
```

### Step 3: 校验与验证

迁移完成后，执行校验确保数据一致性：

```bash
python3 scripts/validate_migration.py \
    --td-config config/teradata_config.ini \
    --dws-config config/dws_config.ini \
    --schema mydb
```

校验内容包括：
1. **表数量校验** — 源端和目标端表数量是否一致
2. **行数一致性** — 每个表的行数是否一致
3. **列结构校验** — 列名和类型是否匹配
4. **聚合值校验** — COUNT/SUM/MAX/MIN 比对
5. **数据抽样比对** — 随机抽样数据比对

## 3. 工具参考

### 3.1 DSC (Database Schema Convertor)

- **用途**：离线 SQL 脚本迁移工具，支持 Teradata → DWS
- **支持类型**：DDL 和 PL/SQL 迁移
- **环境要求**：JDK 1.8+
- **配置文件**：
  - `application.properties`：通用配置
  - `features-teradata.properties`：Teradata 特有配置
  - `gaussdb.properties`：DWS 连接配置
- **命令**：`./runDSC.sh -S teradata -I <input> -O <output> -L <log>`

### 3.2 DataCheck

- **用途**：数据一致性校验工具
- **功能**：比对源端和目标端数据，生成差异报告
- **配置**：通过 `datacheck-config.properties` 配置源端和目标端连接

### 3.3 GDS (General Data Service)

- **用途**：DWS 数据导入导出工具
- **优势**：并行导入，适合大数据量
- **使用**：在 DWS 服务器部署 GDS，通过外表导入

## 4. 最佳实践

### 4.1 大表迁移优化

1. **分批导出**：按主键范围分批导出，避免单次查询过大
2. **并行导入**：使用 OBS 外表并行导入，提高吞吐量
3. **压缩传输**：CSV 文件压缩后上传 OBS，减少网络传输
4. **选择合适分布键**：避免数据倾斜

### 4.2 安全注意事项

1. **源端只读**：确保 Teradata 连接用户只有 SELECT 权限
2. **网络安全**：使用加密连接（SSL/TLS）
3. **凭证管理**：配置文件中的密码应使用密文存储或环境变量
4. **审计日志**：记录所有迁移操作，便于追溯

### 4.3 错误处理

1. **DDL 执行失败**：检查类型映射是否正确，DWS 是否支持对应语法
2. **数据导入失败**：检查字符编码、NULL 值处理、日期格式
3. **校验不一致**：检查数据类型转换是否丢失精度，字符截断等

## 5. 参考文档

- 数据类型映射：https://support.huaweicloud.com/migration-dws/dws_15_0131.html
- DWS 数据迁移指南：https://support.huaweicloud.com/migration-dws/
- DSC 工具指南：https://support.huaweicloud.com/migration-dws/dws_15_0132.html
- OBS 文档：obs://cloud-bigdata/teradata_to_dws/dws_doc/
