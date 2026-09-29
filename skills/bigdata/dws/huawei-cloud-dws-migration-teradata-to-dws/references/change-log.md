## 更新日志

### v7 (2026-08-18) - PPI 分区表转换 + 实战Bug修复增强版

新增 PPI 分区表自动转换功能，修复实际迁移中发现的 5 类问题：

**新增功能**：

1. **`ppi_converter.py` — PPI 分区表转换器** — `migrate_schema.py` 集成
   - 自动检测 Teradata DDL 中的 PPI 分区语法（`RANGE_N`、`CASE_N`）
   - 单级 `RANGE_N` 按天/按月 → DWS `PARTITION BY RANGE`
   - `CASE_N` → DWS `PARTITION BY LIST`
   - 多级 `RANGE_N + CASE_N` → DWS 单级 `PARTITION BY RANGE`（降级，原 CASE_N 信息保留在注释中）
   - 自动处理 `NO RANGE`/`NO CASE`/`UNKNOWN` → DWS 默认分区
   - 自动提取 DISTRIBUTE BY 子句，保持数据分布一致性
   - `migrate_schema.py` 在 DDL 转换流程中自动调用 PPI 转换

**Bug 修复**：

2. **`dws_writer.py` - 执行失败时事务回滚** — 所有执行方法增加 rollback
   - 问题：DDL/DML 执行失败时未回滚事务，导致连接状态不一致
   - 修复：`execute_ddl`、`execute_ddl_file`、`import_data_via_copy` 等所有方法在 except 块中增加 `self._connection.rollback()`

3. **`migrate_schema.py` - 表删除缺少 CASCADE** — 依赖视图的表无法删除
   - 问题：表删除(IF EXISTS)未加 `CASCADE`，当表被视图依赖时删除失败
   - 修复：所有表删除语句添加 `CASCADE` 关键字

4. **`dws_writer.py` - 中文注释 ASCII 编码错误** — 连接未设置 UTF-8 客户端编码
   - 问题：执行含中文注释的 DDL 时报 `'ascii' codec can't encode character` 错误
   - 修复：连接建立后执行 `SET client_encoding TO 'UTF8'`，确保支持非 ASCII 字符

5. **`migrate_views_procs.py` - QUALIFY 转换为子查询导致语法错误** — 改用 CTE + ROW_NUMBER
   - 问题：`QUALIFY ROW_NUMBER() OVER(...) = N` 转换为子查询包装后，DWS 执行报语法错误
   - 修复：改为 CTE + `ROW_NUMBER() OVER(...)` + `WHERE rn = N` 模式，兼容性更好

6. **`ppi_converter.py` - 多级 PPI SUBPARTITION 语法不支持** — 降级为单级 RANGE
   - 问题：DWS 不支持 `SUBPARTITION BY LIST` 语法，多级 PPI DDL 执行失败
   - 修复：多级 `RANGE_N + CASE_N` 自动降级为单级 `PARTITION BY RANGE`，原 CASE_N 子分区信息以注释保留

7. **`migrate_schema.py` - 非交互环境下重复表确认静默退出** — 改为明确报错
   - 问题：通过脚本/管道等非交互方式运行迁移时，`input()` 抛出 `EOFError`，旧代码返回 `False` + `sys.exit(0)`，以成功码静默退出，DDL 未执行但用户误以为迁移成功
   - 修复：新增 `sys.stdin.isatty()` 检测，非交互环境 + 有重复表 + 无 `--force` 时，打印清晰错误信息并列出所有重复表，以错误码 `sys.exit(1)` 退出，提示用户使用 `--force` 或在终端交互运行

### v6 (2026-08-18) - 实战问题修复 + 时区处理增强版

基于实际迁移 Teradata `mig` 和 `app_sales` 库的经验，修复6类实战问题并新增时区处理功能：

**新增功能**：

1. **时区转换（迁移阶段）** — `migrate_data.py`
   - 新增 `--timezone-adjust` CLI 选项，启用后自动对 TIMESTAMP 列做时区偏移
   - 新增 `--source-tz`（默认 UTC-4）和 `--target-tz`（默认 UTC+8）参数
   - 实现 `parse_timezone_offset()` 和 `build_timezone_adjusted_query()` 辅助函数
   - 自动查询 Teradata 列类型，对 TIMESTAMP 列添加 `INTERVAL 'N' HOUR` 偏移
   - 支持 CSV 和 OBS 两种迁移方式

2. **TIMESTAMP 精确值校验** — `validate_migration.py`
   - 新增 `validate_timestamp_values()` 方法（校验项 6: `timestamp_check`）
   - 逐行逐列比对源端和目标端 TIMESTAMP 值，支持时区补偿
   - CLI 选项：`--checks ... timestamp_check`、`--timezone-adjust`、`--source-tz`、`--target-tz`
   - 报告中记录不匹配的行号、列名、源端值、目标端值

3. **导入前自动清空目标表** — `dws_writer.py` + `migrate_data.py`
   - 新增 `truncate_table()` 方法
   - `import_data_via_copy()` / `import_data_from_csv()` / `import_data_from_obs()` 均增加 `truncate_before_import` 参数
   - CLI 选项 `--truncate-before-import`，避免重复导入导致数据翻倍

4. **宏 column definition list 自动推断 fallback** — `validate_functional.py`
   - 新增 `infer_col_def_from_td()` 函数：从 TD 宏执行结果推断列类型
   - `validate_macro()` 和 `validate_macro_with_params()` 增加 fallback 逻辑：
     - 先尝试 `infer_dws_function_columns()` 从 `pg_attribute` 推断
     - 失败后尝试直接调用（适用于 `RETURNS TABLE(...)` 函数）
     - 再失败则从 TD 端宏执行结果推断列类型（适用于 `SETOF record` 函数）
   - 支持 interval 类型推断（OID 1186）

**Bug 修复**：

5. **interval 类型 column definition list** — `migrate_views_procs.py`
   - `_map_pg_type()` 增加 interval 类型映射（OID 1186 → `interval`）

6. **SET 语法转换** — `migrate_views_procs.py`
   - 存储过程转换中自动将 Teradata `SET var = expr` 转换为 DWS `var := expr`
   - 按分号分割独立语句，只转换以 SET 开头的赋值语句，不影响 UPDATE ... SET

### v5 (2026-08-17) - 功能性校验 + 迁移Bug修复增强版

新增功能性校验脚本，修复实际迁移中发现的转换问题：

**新增功能**：

1. **`validate_functional.py` — 功能性校验脚本**
   - 宏校验：TD 端 `EXEC` 调用 vs DWS 端 `SELECT * FROM func() AS (col_def)` 调用，比较行数和前20行数据
   - 存储过程校验：两端 `CALL` 执行，写操作过程用事务回滚避免数据污染
   - 视图校验：两端查询行数 + 抽样数据比对
   - 宏列类型自动推断：通过 `pg_attribute` 查询自动推断 `SETOF record` 返回列定义
   - 带参数宏支持：通过 `--macro-params` JSON 文件指定测试参数值
   - JSON 格式校验报告，含每个对象的校验状态、行数、匹配结果

**Bug 修复**：

2. **`migrate_views_procs.py` - QUALIFY 转换 SELECT * 包含 _qualify_cond 列**
   - 问题：QUALIFY 转换为子查询后，`SELECT *` 会包含内部辅助列 `_qualify_cond`
   - 修复：将 `SELECT *` 改为显式排除 `_qualify_cond` 列

3. **`migrate_views_procs.py` - 宏体中 SET 赋值未转换**
   - 问题：MacroConverter 未对宏函数体中的 `SET` 语句做 `SET → :=` 转换
   - 修复：在宏转换流程中增加函数体 SET → := 转换步骤

4. **`migrate_views_procs.py` - 宏列类型未自动推断**
   - 问题：`SETOF record` 函数调用时需手动提供列定义列表，脚本未自动推断
   - 修复：新增 `_infer_column_types` 方法，通过查询 TD 端宏返回列自动推断 DWS 列类型

### v4 (2026-08-17) - 视图/宏/存储过程迁移 + Bug修复版

新增视图、宏、存储过程迁移功能，并修复实际迁移中发现的更多bug：

**新增功能**：

1. **`migrate_views_procs.py` — 视图/宏/存储过程迁移脚本**
   - 视图迁移：提取 Teradata 视图 DDL，自动转换 SQL 语法，在 DWS 创建视图
   - 宏迁移：将 Teradata 宏转换为 DWS SQL 函数（CREATE OR REPLACE FUNCTION）
   - 存储过程迁移：将 Teradata SPL 转换为 DWS PL/pgSQL PROCEDURE
   - 支持 `--dry-run` 和 `--output-dir` 模式
   - SQL 语法自动转换：ZEROIFNULL→COALESCE、QUALIFY→子查询、GROUP BY 位置→列名等

**Bug 修复**：

2. **`migrate_data.py` - TeradataReader 缺少 port/database/logmech 参数**
   - 问题：TeradataReader 初始化时未传递 port、database、logmech 参数，导致连接失败
   - 修复：添加 port、database、logmech 参数传递

3. **`migrate_data.py` - `--output` 指向目录时 IsADirectoryError**
   - 问题：当 `--output` 参数指向目录路径时，尝试写入文件失败
   - 修复：检测路径是否为目录，如果是目录则在目录下生成文件名

4. **`migrate_data.py` - 添加 `--force` 参数**
   - 问题：缺少 `--force` 参数，与 `migrate_schema.py` 参数不一致
   - 修复：添加 `--force` 参数，支持跳过确认提示

5. **`migrate_schema.py` - NOT NULL 约束冲突**
   - 问题：源端 Teradata 表定义为 NOT NULL 但实际数据包含 NULL，导致 DWS 导入失败
   - 修复：添加 `--safe-null` 选项，生成 DDL 时将 NOT NULL 列改为可空；添加 `--fix-not-null` 子命令自动检测并修复冲突

6. **`dws_writer.py` - DWSWriter 缺少 query 和 execute 方法**
   - 问题：DWSWriter 类缺少 `query` 和 `execute` 方法，其他脚本调用时报错
   - 修复：添加 `query` 方法（执行查询返回结果）和 `execute` 方法（执行 SQL 无返回）

### v3 (2026-08-12) - Bug修复版

修复在实际迁移过程中发现的所有bug：

1. **`migrate_data.py` - 配置键名 `username` → `user` 兼容**
   - 问题：脚本使用 `td_config['teradata']['username']` 读取用户名，但 `TeradataReader` 类参数名为 `user`，配置模板也使用 `user` 键
   - 修复：改为 `td_config['teradata'].get('user', td_config['teradata'].get('username', ''))`，同时兼容两种键名

2. **`migrate_data.py` - 方法名 `get_table_list` → `list_tables`**
   - 问题：调用 `td_reader.get_table_list(database)` 但 `TeradataReader` 类中方法名为 `list_tables`
   - 修复：改为 `td_reader.list_tables(database)`

3. **`migrate_data.py` - 方法名 `close` → `disconnect`**
   - 问题：调用 `td_reader.close()` 和 `dws_writer.close()` 但两个类的断开方法名为 `disconnect`
   - 修复：改为 `td_reader.disconnect()` 和 `dws_writer.disconnect()`

4. **`migrate_data.py` - TableKind 过滤器空格问题**
   - 问题：`list_tables` 返回的 `table_kind` 为 `'T '`（带尾部空格），但过滤器使用 `t[1] == 'T'` 导致无法匹配
   - 修复：改为 `t[1].strip() == 'T'`

5. **`migrate_data.py` - 临时目录未自动创建**
   - 问题：CSV 导出时使用 `/tmp` 作为临时目录，但未调用 `os.makedirs` 确保目录存在
   - 修复：添加 `os.makedirs(args.temp_dir, exist_ok=True)`

6. **配置键名统一兼容（所有脚本）**
   - 问题：`pre_migration_check.py`、`migrate_schema.py`、`validate_migration.py` 仅使用 `.get('user', '')`，不兼容旧配置中的 `username` 键
   - 修复：所有脚本统一使用 `.get('user', section.get('username', ''))` 模式，向后兼容

