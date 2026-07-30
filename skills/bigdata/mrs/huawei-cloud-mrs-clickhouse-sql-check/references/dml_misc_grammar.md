# ClickHouse 24.8 DML & 杂项语法参考

Source: `ClickHouse_Kernel/src/Parsers/`

---

## 1. INSERT 语句

**文件**: `ParserInsertQuery.cpp/h`

### 完整语法

```sql
INSERT INTO [TABLE] [db.]table_name [(column_list)]
    [SETTINGS name=value, ...]
    [FORMAT format_name]
    data

INSERT INTO [TABLE] [db.]table_name [(column_list)]
    [SETTINGS name=value, ...]
    SELECT ...

INSERT INTO [TABLE] [db.]table_name [(column_list)]
    FROM INFILE 'filename' [COMPRESSION compression] [FORMAT format_name]

INSERT INTO [TABLE] [db.]table_name [(column_list)]
    VALUES (v1, v2, ...), (v1, v2, ...), ...
```

### 子句说明

| 子句 | 必填 | 说明 |
|------|------|------|
| `INTO [TABLE]` | 必填 | TABLE 关键字可选 |
| `[db.]table_name` | 必填 | 目标表 |
| `[(column_list)]` | 可选 | 列列表 |
| `[SETTINGS ...]` | 可选 | 查询级设置 |
| `FORMAT format_name` | 可选 | 数据格式（默认 TabSeparated） |
| `SELECT ...` | 可选 | 从查询插入 |
| `FROM INFILE ...` | 可选 | 从文件插入 |
| `VALUES ...` | 可选 | 值列表 |

### UPSERT INTO

```sql
UPSERT INTO [db.]table_name [(column_list)]
    [FORMAT format_name]
    data
```

---

## 2. DELETE 语句（轻量量 DELETE）

**文件**: `ParserDeleteQuery.cpp/h`

### 完整语法

```sql
DELETE FROM [db.]table_name
    [ON CLUSTER cluster]
    [IN PARTITION partition_expr]
    WHERE expression
```

- 轻量量 DELETE（Mutation）
- 不同于 ALTER TABLE DELETE（后者是重量级操作）

---

## 3. UPDATE 语句（轻量量 UPDATE）

```sql
UPDATE [db.]table_name
    [ON CLUSTER cluster]
    SET column1 = expr1, column2 = expr2, ...
    [IN PARTITION partition_expr]
    WHERE expression
```

---

## 4. OPTIMIZE TABLE

**文件**: `ParserOptimizeQuery.cpp/h`

### 完整语法

```sql
OPTIMIZE TABLE [db.]table_name
    [ON CLUSTER cluster]
    [PARTITION partition_expr]
    [FINAL]
    [DEDUPLICATE [BY column_list]]
    [CLEANUP]
```

---

## 5. CHECK TABLE

**文件**: `ParserCheckQuery.cpp/h`

```sql
CHECK TABLE [db.]table_name
CHECK TABLE [db.]table_name PARTITION partition_expr
CHECK TABLE [db.]table_name PART 'part_name'
```

---

## 6. USE

**文件**: `ParserUseQuery.cpp/h`

```sql
USE [db.]database_name
```

---

## 7. KILL 语句族

**文件**: `ParserKillQueryQuery.cpp/h`

### 完整语法

```sql
KILL QUERY [WHERE condition] [SYNC | ASYNC | TEST] [ON CLUSTER cluster]
KILL MUTATION [WHERE condition] [SYNC | ASYNC | TEST] [ON CLUSTER cluster]
KILL PART_MOVE_TO_SHARD [WHERE condition] [SYNC | ASYNC | TEST] [ON CLUSTER cluster]
KILL TRANSACTION [WHERE condition] [SYNC | ASYNC | TEST] [ON CLUSTER cluster]
```

---

## 8. WATCH 语句

**文件**: `ParserWatchQuery.cpp/h`

```sql
WATCH [db.]table_name [EVENTS] [LIMIT n]
```

---

## 9. DESCRIBE TABLE

**文件**: `ParserDescribeTableQuery.cpp/h`

```sql
DESCRIBE [TABLE] [db.]table_name [FORMAT format_name]
```

---

## 10. DESCRIBE CACHE

```sql
DESCRIBE CACHE [filesystem_cache_name]
```

---

## 11. SYSTEM 命令族

**文件**: `ParserSystemQuery.cpp/h`, `ASTSystemQuery.h`

### 完整子命令列表

#### 11.1 RELOAD 族

```sql
SYSTEM RELOAD DICTIONARY [db.]dict_name
SYSTEM RELOAD DICTIONARIES
SYSTEM RELOAD MODEL model_name
SYSTEM RELOAD MODELS
SYSTEM RELOAD FUNCTION function_name
SYSTEM RELOAD FUNCTIONS
SYSTEM RELOAD EMBEDDED DICTIONARIES
SYSTEM RELOAD CONFIG
```

#### 11.2 FLUSH 族

```sql
SYSTEM FLUSH DISTRIBUTED [db.]table_name
SYSTEM FLUSH LOGS
```

#### 11.3 START/STOP 族

```sql
SYSTEM START DISTRIBUTED SENDS [db.]table_name
SYSTEM STOP DISTRIBUTED SENDS [db.]table_name
SYSTEM START MERGES [db.]table_name
SYSTEM STOP MERGES [db.]table_name
SYSTEM START TTL MERGES [db.]table_name
SYSTEM STOP TTL MERGES [db.]table_name
SYSTEM START MOVES [db.]table_name
SYSTEM STOP MOVES [db.]table_name
SYSTEM START REPLICATED FETCHES [db.]table_name
SYSTEM STOP REPLICATED FETCHES [db.]table_name
SYSTEM START REPLICATED SENDS [db.]table_name
SYSTEM STOP REPLICATED SENDS [db.]table_name
SYSTEM START FETCHES [db.]table_name
SYSTEM STOP FETCHES [db.]table_name
SYSTEM START REPLICATION QUEUES [db.]table_name
SYSTEM STOP REPLICATION QUEUES [db.]table_name
SYSTEM START PULLING REPLICATION LOG [db.]table_name
SYSTEM STOP PULLING REPLICATION LOG [db.]table_name
SYSTEM START BUFFER FLUSH [db.]table_name
SYSTEM STOP BUFFER FLUSH [db.]table_name
SYSTEM START FILESYSTEM CACHES
SYSTEM STOP FILESYSTEM CACHES
SYSTEM START VIRTUAL PARTS UPDATE
SYSTEM STOP VIRTUAL PARTS UPDATE
SYSTEM START LISTEN
SYSTEM STOP LISTEN
SYSTEM START THREAD FZZ
SYSTEM STOP THREAD FZZ
```

#### 11.4 DROP 族

```sql
SYSTEM DROP DNS CACHE
SYSTEM DROP HOST CACHE
SYSTEM DROP UNCOMPRESSED CACHE
SYSTEM DROP MARK CACHE
SYSTEM DROP PRIMARY INDEX CACHE [db.]table_name
SYSTEM DROP QUERY CACHE
SYSTEM DROP COMPILED EXPRESSION CACHE
SYSTEM DROP FORMAT SCHEMA CACHE
SYSTEM DROP FILESYSTEM CACHE [cache_name]
SYSTEM DROP FILESYSTEM CACHES
SYSTEM DROP REPLICA replica_name [FROM] [DATABASE|TABLE|VIEW|DICTIONARY] [db.]name [ON CLUSTER cluster]
SYSTEM DROP DATABASE REPLICA replica_name ON DATABASE db_name [ON CLUSTER cluster]
SYSTEM DROP DATABASE REPLICA replica_name ON CLUSTER cluster_name [ON CLUSTER cluster]
```

#### 11.5 SYNC/LOAD 族

```sql
SYSTEM SYNC FILE CACHE
SYSTEM SYNC FILESYSTEM CACHE [cache_name]
SYSTEM SYNC DATABASE REPLICA db_name [ON CLUSTER cluster]
SYSTEM SYNC REPLICA [db.]table_name [ON CLUSTER cluster] [LIGHTWEIGHT | PARTITION partition_expr | PULLING]
SYSTEM SYNC REPLICA [db.]table_name [ON CLUSTER cluster] LIGHTWEIGHT [WAIT name]
```

#### 11.6 ENABLE/DISABLE 族

```sql
SYSTEM ENABLE FAILPOINT name
SYSTEM DISABLE FAILPOINT name
SYSTEM WAIT FAILPOINT name
SYSTEM ENABLE/DISABLE FAILPOINT name
```

#### 11.7 其他

```sql
SYSTEM SUSPEND [ON CLUSTER cluster]
SYSTEM RESUME [ON CLUSTER cluster]
SYSTEM RESTART REPLICA [db.]table_name [ON CLUSTER cluster]
SYSTEM RESTORE REPLICA [db.]table_name [ON CLUSTER cluster]
SYSTEM UNFREEZE [ON CLUSTER cluster]
SYSTEM RESTORE [ON CLUSTER cluster]
SYSTEM KILL [ON CLUSTER cluster]
SYSTEM FLUSH DISTRIBUTED [db.]table_name
```

---

## 12. BACKUP / RESTORE

**文件**: `ParserBackupQuery.cpp/h`

### BACKUP 完整语法

```sql
BACKUP {
    TABLE [db.]table_name [PARTITION partition_expr] [AS [db.]backup_table_name]
    | DATABASE db_name [AS backup_db_name]
    | TEMPORARY TABLE table_name
    | VIEW [db.]view_name
    | DICTIONARY [db.]dict_name
    | FUNCTION function_name
    | ALL
    | DATABASES db1, db2, ... [EXCEPT DATABASE db_name, ...]
    | TABLES table1, table2, ... [EXCEPT TABLE table_name, ...]
}
    [,...]
    TO DISK 'disk_name' [PATH 'path']
    | TO FILE 'filename'
    | TO S3 'url' [AUTH_HEADER ...] [COMPRESSION ...]
    | TO AZURE 'url' [AUTH_HEADER ...] [COMPRESSION ...]
    | TO [user:password@]host[:port]
    [SETTINGS name=value, ...]
    [BASE_BACKUP]
    [ASYNC]
```

### RESTORE 完整语法

```sql
RESTORE {
    TABLE [db.]table_name [AS [db.]restore_table_name]
    | DATABASE db_name [AS restore_db_name]
    | TEMPORARY TABLE table_name
    | VIEW [db.]view_name
    | DICTIONARY [db.]dict_name
    | FUNCTION function_name
    | ALL
    | DATABASES db1, db2, ...
    | TABLES table1, table2, ...
}
    [,...]
    FROM DISK 'disk_name' [PATH 'path']
    | FROM FILE 'filename'
    | FROM S3 'url' [AUTH_HEADER ...] [COMPRESSION ...]
    | FROM AZURE 'url' [AUTH_HEADER ...] [COMPRESSION ...]
    | FROM [user:password@]host[:port]
    [SETTINGS name=value, ...]
    [ASYNC]
```

---

## 13. EXPLAIN

**文件**: `ParserExplainQuery.cpp/h`

### 完整语法

```sql
EXPLAIN [kind] [options] query
```

### EXPLAIN Kind 类型

| 关键字 | 内部名称 | 后续查询要求 |
|--------|---------|-------------|
| （默认） | `QueryPlan` | SELECT / CREATE / INSERT / SYSTEM |
| `AST` | `ParsedAST` | 任意查询 |
| `SYNTAX` | `AnalyzedSyntax` | SELECT / CREATE / INSERT / SYSTEM |
| `QUERY TREE` | `QueryTree` | 仅 SELECT |
| `PIPELINE` | `QueryPipeline` | SELECT / CREATE / INSERT / SYSTEM |
| `PLAN` | `QueryPlan` | SELECT / CREATE / INSERT / SYSTEM |
| `ESTIMATE` | `QueryEstimates` | SELECT / CREATE / INSERT / SYSTEM |
| `TABLE OVERRIDE` | `TableOverride` | `table_function table_override_decl` |
| `CURRENT TRANSACTION` | `CurrentTransaction` | 无后续查询 |

---

## 14. SET 语句

**文件**: `ParserSetQuery.cpp/h`

```sql
SET {name = value | name = DEFAULT | _param_name = param_value} [, ...]
```

### 三种赋值形式

1. **设置值**: `name = value`
2. **恢复默认**: `name = DEFAULT`
3. **查询参数**: `_param_name = param_value`（以 `_` 开头）

---

## 15. 事务控制

**文件**: `ParserTransactionControl.cpp/h`

```sql
BEGIN TRANSACTION
START TRANSACTION
COMMIT
ROLLBACK
CHECK TRANSACTION
SET TRANSACTION SNAPSHOT snapshot_number
```

---

## 16. SHOW 命令族

### SHOW TABLES / DATABASES / CLUSTERS / MERGES / DICTIONARIES

```sql
SHOW [FULL] [TEMPORARY] TABLES [FROM|IN db]
    [[NOT] [I]LIKE 'pattern' | WHERE expr] [LIMIT n]
SHOW [FULL] DATABASES [[NOT] [I]LIKE 'pattern'] [LIMIT n]
SHOW [FULL] CLUSTERS [[NOT] [I]LIKE 'pattern'] [LIMIT n]
SHOW [FULL] MERGES [[NOT] [I]LIKE 'pattern'] [LIMIT n]
SHOW DICTIONARIES [FROM|IN db] [[NOT] [I]LIKE 'pattern'] [LIMIT n]
SHOW FILESYSTEM CACHES
SHOW CLUSTER cluster_name_or_identifier
SHOW [CHANGED] SETTINGS [LIKE|ILIKE 'pattern']
```

### SHOW COLUMNS

```sql
SHOW [EXTENDED] [FULL] COLUMNS|FIELDS FROM|IN table [FROM|IN database]
    [[NOT] [I]LIKE 'pattern' | WHERE expr] [LIMIT n]
```

### SHOW INDEX

```sql
SHOW [EXTENDED] INDEX|INDEXES|INDICES|KEYS FROM|IN table [FROM|IN database] [WHERE expr]
```

### SHOW FUNCTIONS

```sql
SHOW FUNCTIONS [LIKE|ILIKE 'pattern']
```

### SHOW SETTING

```sql
SHOW SETTING setting_name
```

### SHOW PROCESSLIST / ENGINES / ACCESS

```sql
SHOW PROCESSLIST
SHOW ENGINES
SHOW ACCESS
```

### SHOW CREATE

```sql
SHOW CREATE USER [name | CURRENT_USER]
SHOW CREATE USERS [name [, name2 ...]]
SHOW CREATE ROLE name
SHOW CREATE ROLES [name [, name2 ...]]
SHOW CREATE [SETTINGS] PROFILE name
SHOW CREATE [SETTINGS] PROFILES [name [, name2 ...]]
SHOW CREATE [ROW] POLICY name ON [database.]table
SHOW CREATE [ROW] POLICIES [name ON [database.]table [, ...] | name | ON database.table]
SHOW CREATE QUOTA [name]
SHOW CREATE QUOTAS [name [, name2 ...]]
SHOW CREATE TENANT name
SHOW CREATE TENANT [name [, name2 ...]]
```

### SHOW GRANTS

```sql
SHOW GRANTS [FOR user_name]
```

### SHOW ACCESS ENTITIES

```sql
SHOW USERS
SHOW [CURRENT|ENABLED] ROLES
SHOW [SETTINGS] PROFILES
SHOW [ROW] POLICIES [name | ON [database.]table]
SHOW QUOTAS
SHOW [CURRENT] QUOTA
```

---

## 17. REFRESH 策略

**文件**: `ParserRefreshStrategy.cpp/h`

```sql
REFRESH (AFTER time_interval | EVERY time_interval [OFFSET time_interval])
    [RANDOMIZE FOR time_interval]
    [DEPENDS ON table1, table2, ...]
    [SETTINGS key=value, ...]
```

| 子句 | 必填/可选 | 说明 |
|------|----------|------|
| `AFTER time_interval` | 必填(二选一) | 数据变更后延迟刷新 |
| `EVERY time_interval` | 必填(二选一) | 周期性刷新 |
| `OFFSET time_interval` | 可选 | 仅跟随 EVERY |
| `RANDOMIZE FOR time_interval` | 可选 | 随机化扩散 |
| `DEPENDS ON table1, ...` | 可选 | 依赖表列表 |
| `SETTINGS key=value, ...` | 可选 | 刷新设置 |

---

## 文件索引

| 文件 | 路径 |
|------|------|
| ParserInsertQuery.cpp | `src/Parsers/ParserInsertQuery.cpp` |
| ParserDeleteQuery.cpp | `src/Parsers/ParserDeleteQuery.cpp` |
| ParserUpsertQuery.cpp | `src/Parsers/ParserUpsertQuery.cpp` |
| ParserOptimizeQuery.cpp | `src/Parsers/ParserOptimizeQuery.cpp` |
| ParserCheckQuery.cpp | `src/Parsers/ParserCheckQuery.cpp` |
| ParserUseQuery.cpp | `src/Parsers/ParserUseQuery.cpp` |
| ParserKillQueryQuery.cpp | `src/Parsers/ParserKillQueryQuery.cpp` |
| ParserWatchQuery.cpp | `src/Parsers/ParserWatchQuery.cpp` |
| ParserDescribeTableQuery.cpp | `src/Parsers/ParserDescribeTableQuery.cpp` |
| ParserDescribeCacheQuery.cpp | `src/Parsers/ParserDescribeCacheQuery.cpp` |
| ParserSystemQuery.cpp | `src/Parsers/ParserSystemQuery.cpp` |
| ASTSystemQuery.h | `src/Parsers/ASTSystemQuery.h` |
| ParserBackupQuery.cpp | `src/Parsers/ParserBackupQuery.cpp` |
| ParserExplainQuery.cpp | `src/Parsers/ParserExplainQuery.cpp` |
| ParserSetQuery.cpp | `src/Parsers/ParserSetQuery.cpp` |
| ParserTransactionControl.cpp | `src/Parsers/ParserTransactionControl.cpp` |
| ParserShowTablesQuery.cpp | `src/Parsers/ParserShowTablesQuery.cpp` |
| ParserShowColumnsQuery.cpp | `src/Parsers/ParserShowColumnsQuery.cpp` |
| ParserShowFunctionsQuery.cpp | `src/Parsers/ParserShowFunctionsQuery.cpp` |
| ParserShowIndexesQuery.cpp | `src/Parsers/ParserShowIndexesQuery.cpp` |
| ParserShowSettingQuery.cpp | `src/Parsers/ParserShowSettingQuery.cpp` |
| ParserShowProcesslistQuery.h | `src/Parsers/ParserShowProcesslistQuery.h` |
| ParserShowEngineQuery.h | `src/Parsers/ParserShowEngineQuery.h` |
| ParserQuery.cpp | `src/Parsers/ParserQuery.cpp` |
| ParserQueryWithOutput.cpp | `src/Parsers/ParserQueryWithOutput.cpp` |
| ParserRefreshStrategy.cpp | `src/Parsers/ParserRefreshStrategy.cpp` |
| ParserStringAndSubstitution.cpp | `src/Parsers/ParserStringAndSubstitution.cpp` |
