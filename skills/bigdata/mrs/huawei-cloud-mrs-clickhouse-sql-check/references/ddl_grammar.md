# ClickHouse 24.8 DDL 语法参考

本文档从 ClickHouse 24.8 内核源码 `src/Parsers/` 提取，覆盖所有 DDL 语句的完整语法结构。

---

## 1. CREATE TABLE / CREATE TEMPORARY TABLE

**文件**: `ParserCreateQuery.cpp/h`

### 完整语法
```
CREATE [TEMPORARY] TABLE [IF NOT EXISTS] [db.]name
    [ON CLUSTER cluster]
    [UUID 'uuid']
    [AS SELECT ...]
    [(create_columns)]
    [TABLE_OVERRIDE(...), ...]
    [ENGINE = engine_name(params...)]
    [ORDER BY expr]
    [PARTITION BY expr]
    [PRIMARY KEY expr]
    [SAMPLE BY expr]
    [TTL ttl_expr_list]
    [SETTINGS setting_name = value, ...]
    [COMMENT 'string']
```

### 子句顺序与可选性

| 子句 | 关键字 | 可选/必填 |
|------|--------|-----------|
| TEMPORARY | `TEMPORARY` | 可选 |
| IF NOT EXISTS | `IF NOT EXISTS` | 可选 |
| ON CLUSTER | `ON CLUSTER cluster` | 可选 |
| UUID | `UUID 'uuid'` | 可选 |
| AS SELECT | `AS [TABLE] SELECT ...` | 可选 |
| 列定义 | `[(...)]` | 可选（与 AS SELECT 二选一） |
| ENGINE | `ENGINE = engine_name` | 可选（默认 MergeTree） |
| ORDER BY | `ORDER BY expr` | 条件必填（MergeTree 族） |
| PARTITION BY | `PARTITION BY expr` | 可选 |
| PRIMARY KEY | `PRIMARY KEY expr` | 可选 |
| SAMPLE BY | `SAMPLE BY expr` | 可选 |
| TTL | `TTL expr [, expr, ...]` | 可选 |
| SETTINGS | `SETTINGS name = value, ...` | 可选 |
| COMMENT | `COMMENT 'string'` | 可选 |

### 列定义语法
```
column_name data_type
    [NULL | NOT NULL]
    [DEFAULT | MATERIALIZED | ALIAS | EPHEMERAL expr]
    [COMMENT 'string']
    [PRIMARY KEY]
    [CODEC(codec_name, ...)]
    [TTL expr]
    [STATISTICS(stat_type, ...)]
    [CONSTRAINT constraint_name CHECK expr]
```

### 存储子句（Storage Clause）
```
ENGINE = engine_name(params...)
[PARTITION BY expr]
[PRIMARY KEY expr]
[ORDER BY expr]
[SAMPLE BY expr]
[TTL ttl_expr_list]
[SETTINGS setting_name = value, ...]
```

**注意**: 子句可循环匹配，顺序不强制。SETTINGS 必须与 ENGINE 同时出现。

---

## 2. CREATE VIEW

**文件**: `ParserCreateQuery.cpp/h`

### 完整语法
```
CREATE [OR REPLACE] VIEW [IF NOT EXISTS] [db.]name
    [ON CLUSTER cluster]
    [UUID 'uuid']
    [DEFINER = user_name | CURRENT_USER | NONE]
    [SQL SECURITY DEFINER | INVOKER | NONE]
    AS SELECT ...
    [COMMENT 'string']
```

---

## 3. CREATE MATERIALIZED VIEW

**文件**: `ParserCreateQuery.cpp/h`, `ParserViewTargets.cpp/h`

### 完整语法
```
CREATE MATERIALIZED VIEW [IF NOT EXISTS] [db.]name
    [ON CLUSTER cluster]
    [UUID 'uuid']
    [DEFINER = user_name | CURRENT_USER | NONE]
    [SQL SECURITY DEFINER | INVOKER | NONE]
    [TO [db.]table_name | TO INNER UUID 'uuid' | INNER ENGINE = engine(...)]
    [DATA UUID 'uuid' | DATA ENGINE = engine(...)]
    [TAGS UUID 'uuid' | TAGS ENGINE = engine(...)]
    [METRICS UUID 'uuid' | METRICS ENGINE = engine(...)]
    [POPULATE]
    AS SELECT ...
    [ORDER BY expr]
    [PARTITION BY expr]
    [PRIMARY KEY expr]
    [SAMPLE BY expr]
    [TTL ttl_expr_list]
    [SETTINGS setting_name = value, ...]
    [COMMENT 'string']
```

### ViewTargets 结构
```
TO [db.]table_name
TO INNER UUID 'uuid'
ENGINE = engine_name(params...) [ORDER BY ...] [SETTINGS ...]
INNER ENGINE = engine_name(params...) [ORDER BY ...] [SETTINGS ...]
DATA UUID 'uuid'
DATA ENGINE = engine(...)
TAGS UUID 'uuid'
TAGS ENGINE = engine(...)
METRICS UUID 'uuid'
METRICS ENGINE = engine(...)
```

---

## 4. CREATE DICTIONARY

**文件**: `ParserDictionary.cpp/h`

### 完整语法
```
CREATE DICTIONARYARY [IF NOT EXISTS] [db.]name
    [ON CLUSTER cluster]
    [UUID 'uuid']
    (
        key_column1 type1 [DEFAULT | EXPRESSION | OBJECT ID] [HIERARCHICAL | INJECTIVE | IS_OBJECT_ID],
        key_column2 type2 [DEFAULT | EXPRESSION | OBJECT ID] [HIERARCHICAL | INJECTIVE | IS_OBJECT_ID],
        ...,
        attr1 type1 [DEFAULT | EXPRESSION | OBJECT ID] [HIERARCHICAL | INJECTIVE | IS_OBJECT_ID],
        attr2 type2 [DEFAULT | EXPRESSION | OBJECT ID] [HIERARCHICAL | INJECTIVE | IS_OBJECT_ID],
        ...
    )
    PRIMARY KEY key1, key2, ...
    SOURCE(name(...) [PARAMS ...])
    LIFETIME(MIN min_sec MAX max_sec)
    LAYOUT(layout_name(params...))
    [RANGE(MIN min_expr MAX max_expr)]
    [COMMENT 'string']
```

---

## 5. CREATE FUNCTION

**文件**: `ParserCreateFunctionQuery.cpp/h`

### 完整语法
```
CREATE FUNCTION [IF NOT EXISTS] [db.]name
    [ON CLUSTER cluster]
    AS (param1, param2, ...) -> expr
    [COMMENT 'string']
```

---

## 6. CREATE INDEX (已废弃)

**文件**: `ParserCreateIndexQuery.cpp/h`

### 完整语法
```
CREATE INDEX [IF NOT EXISTS] [db.]name
    [ON CLUSTER cluster]
    ON [db.]table_name (expr)
    TYPE type_name
    GRANULARITY granularity
    [COMMENT 'string']
```

**注意**: 此语法已废弃，推荐使用 `ALTER TABLE ADD INDEX`。

---

## 7. ALTER TABLE

**文件**: `ParserAlterQuery.cpp/h`

### 完整语法
```
ALTER TABLE [db.]name
    [ON CLUSTER cluster]
    action1, action2, ...
```

### ALTER Actions 完整列表

#### 7.1 列操作 (Column Actions)

| Action | 语法 | 关键字 |
|--------|------|--------|
| ADD COLUMN | `ADD COLUMN [IF NOT EXISTS] name type [AFTER name]` | ADD_COLUMN |
| DROP COLUMN | `DROP COLUMN [IF EXISTS] name` | DROP_COLUMN |
| CLEAR COLUMN | `CLEAR COLUMN [IF EXISTS] name [IN PARTITION partition]` | CLEAR_COLUMN |
| MODIFY COLUMN | `MODIFY COLUMN [IF EXISTS] name type [AFTER name]` | MODIFY_COLUMN |
| RENAME COLUMN | `RENAME COLUMN [IF EXISTS] old_name TO new_name` | RENAME_COLUMN |
| COMMENT COLUMN | `COMMENT COLUMN [IF EXISTS] name 'string'` | COMMENT_COLUMN |
| MATERIALIZE COLUMN | `MATERIALIZE COLUMN [IF EXISTS] name [IN PARTITION partition]` | MATERIALIZE_COLUMN |
| ALTER COLUMN | `ALTER COLUMN [IF EXISTS] name type` | ALTER_COLUMN |
| CHANGE COLUMN | `CHANGE COLUMN [IF EXISTS] old_name new_name type` | CHANGE_COLUMN |

#### 7.2 约束操作 (Constraint Actions)

| Action | 语法 | 关键字 |
|--------|------|--------|
| ADD CONSTRAINT | `ADD CONSTRAINT [IF NOT EXISTS] name CHECK|ASSUME (expr)` | ADD_CONSTRAINT |
| DROP CONSTRAINT | `DROP CONSTRAINT [IF EXISTS] name` | DROP_CONSTRAINT |

#### 7.3 索引操作 (Index Actions)

| Action | 语法 | 关键字 |
|--------|------|--------|
| ADD INDEX | `ADD INDEX [IF NOT EXISTS] name expr TYPE type GRANULARITY granularity [AFTER name]` | ADD_INDEX |
| DROP INDEX | `DROP INDEX [IF EXISTS] name` | DROP_INDEX |
| CLEAR INDEX | `CLEAR INDEX [IF EXISTS] name [IN PARTITION partition]` | CLEAR_INDEX |
| MATERIALIZE INDEX | `MATERIALIZE INDEX [IF EXISTS] name [IN PARTITION partition]` | MATERIALIZE_INDEX |

#### 7.4 统计信息操作 (Statistics Actions)

| Action | 语法 | 关键字 |
|--------|------|--------|
| ADD STATISTICS | `ADD STATISTICS [IF NOT EXISTS] col1, col2, ... TYPE type(params)` | ADD_STATISTICS |
| DROP STATISTICS | `DROP STATISTICS [IF EXISTS] col1, col2, ...` | DROP_STATISTICS |
| MODIFY STATISTICS | `MODIFY STATISTICS col1, col2, ... TYPE type(params)` | MODIFY_STATISTICS |
| CLEAR STATISTICS | `CLEAR STATISTICS [IF EXISTS] col1, col2, ... [IN PARTITION partition]` | CLEAR_STATISTICS |
| MATERIALIZE STATISTICS | `MATERIALIZE STATISTICS [IF EXISTS] col1, col2, ... [IN PARTITION partition]` | MATERIALIZE_STATISTICS |

#### 7.5 投影操作 (Projection Actions)

| Action | 语法 | 关键字 |
|--------|------|--------|
| ADD PROJECTION | `ADD PROJECTION [IF NOT EXISTS] name (SELECT ...) [FIRST | AFTER name]` | ADD_PROJECTION |
| DROP PROJECTION | `DROP PROJECTION [IF EXISTS] name` | DROP_PROJECTION |
| CLEAR PROJECTION | `CLEAR PROJECTION [IF EXISTS] name [IN PARTITION partition]` | CLEAR_PROJECTION |
| MATERIALIZE PROJECTION | `MATERIALIZE PROJECTION [IF EXISTS] name [IN PARTITION partition]` | MATERIALIZE_PROJECTION |

#### 7.6 分区操作 (Partition Actions)

| Action | 语法 | 关键字 |
|--------|------|--------|
| DROP PARTITION | `DROP PARTITION partition_expr` | DROP_PARTITION |
| DROP PART | `DROP PART 'part_name'` | DROP_PARTITION + part=true |
| DETACH PARTITION | `DETACH PARTITION partition_expr` | DETACH_PARTITION |
| DETACH PART | `DETACH PART 'part_name'` | DETACH_PART |
| ATTACH PARTITION | `ATTACH PARTITION partition_expr [FROM [db.]table]` | ATTACH_PARTITION |
| ATTACH PART | `ATTACH PART 'part_name'` | ATTACH_PART |
| UNDROP PARTITION | `UNDROP PARTITION partition_expr` | UNDROP_PARTITION |
| UNDROP PART | `UNDROP PART 'part_name'` | UNDROP_PART |
| FORGET PARTITION | `FORGET PARTITION partition_expr` | FORGET_PARTITION |
| DROP DETACHED PARTITION | `DROP DETACHED PARTITION partition_expr` | DROP_DETACHED_PARTITION |
| DROP DETACHED PART | `DROP DETACHED PART 'part_name'` | DROP_DETACHED_PART |
| REPLACE PARTITION | `REPLACE PARTITION partition_expr FROM [db.]table` | REPLACE_PARTITION |
| MOVE PARTITION | `MOVE PARTITION partition_expr TO DISK|VOLUME 'name' | TO TABLE [db.]table` | MOVE_PARTITION |
| MOVE PART | `MOVE PART 'part_name' TO DISK|VOLUME|SHARD 'name'` | MOVE_PART |
| FETCH PARTITION | `FETCH PARTITION partition_expr FROM 'source' [TO 'path']` | FETCH_PARTITION |
| FETCH PART | `FETCH PART 'part_name' FROM 'source' [TO 'path']` | FETCH_PART |
| FREEZE | `FREEZE [PARTITION partition_expr] [WITH NAME 'name']` | FREEZE |
| UNFREEZE | `UNFREEZE [PARTITION partition_expr] WITH NAME 'name'` | UNFREEZE |

#### 7.7 数据修改操作 (Data Manipulation)

| Action | 语法 | 关键字 |
|--------|------|--------|
| DELETE | `DELETE [IN PARTITION partition] WHERE predicate` | DELETE |
| UPDATE | `UPDATE col = expr, ... [IN PARTITION partition] WHERE predicate` | UPDATE |

#### 7.8 设置操作 (Settings)

| Action | 语法 | 关键字 |
|--------|------|--------|
| MODIFY SETTING | `MODIFY SETTING name = value, ...` | MODIFY_SETTING |
| RESET SETTING | `RESET SETTING name, name, ...` | RESET_SETTING |

#### 7.9 其他操作

| Action | 语法 | 关键字 |
|--------|------|--------|
| MODIFY QUERY | `MODIFY QUERY SELECT ...` | MODIFY_QUERY |
| MODIFY SQL SECURITY | `MODIFY SQL SECURITY DEFINER|INVOKER|NONE` | MODIFY_SQL_SECURITY |
| MODIFY DEFINER | `MODIFY DEFINER = user_name` | MODIFY_DEFINER |
| MODIFY REFRESH | `MODIFY REFRESH (EVERY|AFTER interval ...)` | MODIFY_REFRESH |
| MODIFY COMMENT | `MODIFY COMMENT 'string'` | MODIFY_COMMENT |
| APPLY DELETED MASK | `APPLY DELETED MASK [IN PARTITION partition]` | APPLY_DELETED_MASK |

### ALTER DATABASE
```
ALTER DATABASE db_name MODIFY SETTING name = value, ...
```
- 仅支持 `MODIFY DATABASE_SETTING` 一种 action

---

## 8. DROP

**文件**: `ParserDropQuery.cpp/h`

### 完整语法
```
DROP [TEMPORARY] TABLE [IF EXISTS] [db.]name [ON CLUSTER cluster] [NO DELAY]
DROP DATABASE [IF EXISTS] db_name [ON CLUSTER cluster]
DROP VIEW [IF EXISTS] [db.]name [ON CLUSTER cluster]
DROP DICTIONARY [IF EXISTS] [db.]name [ON CLUSTER cluster]
DROP [USER | ROLE | QUOTA | POLICY | PROFILE] [IF EXISTS] name [ON CLUSTER cluster]
```

---

## 9. RENAME

**文件**: `ParserRenameQuery.cpp/h`

### 完整语法

**RENAME TABLE:**
```
RENAME TABLE [IF EXISTS] [db.]old_name TO [db.]new_name
    [, [IF EXISTS] [db.]old_name2 TO [db.]new_name2, ...]
    [ON CLUSTER cluster]
```

**EXCHANGE TABLES:**
```
EXCHANGE TABLES [db.]table1 AND [db.]table2
    [, [db.]table3 AND [db.]table4, ...]
    [ON CLUSTER cluster]
```

**RENAME DICTIONARY:**
```
RENAME DICTIONARY [IF EXISTS] [db.]old_name TO [db.]new_name
    [, [IF EXISTS] [db.]old_name2 TO [db.]new_name2, ...]
    [ON CLUSTER cluster]
```

**EXCHANGE DICTIONARIES:**
```
EXCHANGE DICTIONARIES [db.]dict1 AND [db.]dict2
    [, [db.]dict3 AND [db.]dict4, ...]
    [ON CLUSTER cluster]
```

**RENAME DATABASE:**
```
RENAME DATABASE [IF EXISTS] old_db TO new_db [ON CLUSTER cluster]
```

---

## 10. UNDROP TABLE

**文件**: `ParserUndropQuery.cpp/h`

### 完整语法
```
UNDROP TABLE [db.]table_name [UUID 'uuid'] [ON CLUSTER cluster]
```

---

## 11. ATTACH

**文件**: `ParserAttachAccessEntity.cpp/h`

ATTACH 用于访问控制实体的挂载，支持以下子类型：
- `ATTACH USER`
- `ATTACH ROLE`
- `ATTACH ROW POLICY`
- `ATTACH QUOTA`
- `ATTACH SETTINGS PROFILE`
- `ATTACH TENANT`
- `ATTACH GRANT`

语法与对应的 CREATE 语句相同，只是将 `CREATE` 替换为 `ATTACH`。

---

## 12. CHECK TABLE

**文件**: `ParserCheckQuery.cpp/h`

### 完整语法
```
CHECK TABLE [db.]table_name
CHECK TABLE [db.]table_name PARTITION partition_expr
CHECK TABLE [db.]table_name PART part_name
```

---

## 13. DESCRIBE TABLE

**文件**: `ParserDescribeTableQuery.cpp/h`

### 完整语法
```
DESCRIBE [TABLE] [db.]table_name
DESCRIBE [TABLE] [db.]table_name FORMAT format_name
```

---

## 14. OPTIMIZE TABLE

**文件**: `ParserOptimizeQuery.cpp/h`

### 完整语法
```
OPTIMIZE TABLE [db.]table_name [ON CLUSTER cluster]
    [PARTITION partition_expr]
    [FINAL]
    [DEDUPLICATE [BY column_list]]
    [CLEANUP]
```

---

## 15. USE

**文件**: `ParserUseQuery.cpp/h`

### 完整语法
```
USE db_name
```

---

## 16. SET

**文件**: `ParserSetQuery.cpp/h`

### 完整语法
```
SET name = value
SET profile = profile_name
SET ROLE { role_name | NONE | DEFAULT }
SET DEFAULT ROLE { role_name | NONE | DEFAULT } TO user_name
```

---

## 17. EXTERNAL DDL

**文件**: `ParserExternalDDLQuery.cpp/h`

### 完整语法
```
EXTERNAL DDL FROM MySQL(db_clickhouse, db_mysql) DROP TABLE mysql_db.name;
EXTERNAL DDL FROM MySQL(db_clickhouse, db_mysql) CREATE TABLE ...;
EXTERNAL DDL FROM MySQL(db_clickhouse, db_mysql) ALTER TABLE ...;
EXTERNAL DDL FROM MySQL(db_clickhouse, db_mysql) RENAME TABLE ...;
```

---

## 18. PARTITION 表达式

**文件**: `ParserPartition.cpp/h`

分区表达式有三种形式：
```
ID 'partition_id_string'
ALL
literal_value | tuple(a, b, c) | substitution
```

---

## 19. SQL SECURITY / DEFINER 结构

**文件**: `ParserCreateQuery.cpp`

```
DEFINER = user_name [SQL SECURITY DEFINER]
DEFINER = CURRENT_USER [SQL SECURITY DEFINER]
SQL SECURITY DEFINER
SQL SECURITY INVOKER
SQL SECURITY NONE
```

DEFINER 和 SQL SECURITY 可以按任意顺序出现。

---

## 文件索引

| 文件 | 路径 |
|------|------|
| ParserCreateQuery.cpp | `src/Parsers/ParserCreateQuery.cpp` |
| ParserAlterQuery.cpp | `src/Parsers/ParserAlterQuery.cpp` |
| ParserDropQuery.cpp | `src/Parsers/ParserDropQuery.cpp` |
| ParserCreateIndexQuery.cpp | `src/Parsers/ParserCreateIndexQuery.cpp` |
| ParserDropIndexQuery.cpp | `src/Parsers/ParserDropIndexQuery.cpp` |
| ParserCreateFunctionQuery.cpp | `src/Parsers/ParserCreateFunctionQuery.cpp` |
| ParserDropFunctionQuery.cpp | `src/Parsers/ParserDropFunctionQuery.cpp` |
| ParserDictionary.cpp | `src/Parsers/ParserDictionary.cpp` |
| ParserViewTargets.cpp | `src/Parsers/ParserViewTargets.cpp` |
| ParserPartition.cpp | `src/Parsers/ParserPartition.cpp` |
| ParserAttachAccessEntity.cpp | `src/Parsers/ParserAttachAccessEntity.cpp` |
| ParserUndropQuery.cpp | `src/Parsers/ParserUndropQuery.cpp` |
| ParserRenameQuery.cpp | `src/Parsers/ParserRenameQuery.cpp` |
| ParserExternalDDLQuery.cpp | `src/Parsers/ParserExternalDDLQuery.cpp` |
| ParserCheckQuery.cpp | `src/Parsers/ParserCheckQuery.cpp` |
| ParserDescribeTableQuery.cpp | `src/Parsers/ParserDescribeTableQuery.cpp` |
| ParserOptimizeQuery.cpp | `src/Parsers/ParserOptimizeQuery.cpp` |
| ParserUseQuery.cpp | `src/Parsers/ParserUseQuery.cpp` |
| ParserSetQuery.cpp | `src/Parsers/ParserSetQuery.cpp` |
