---
name: huawei-cloud-hetu-sql-check
description: |
  Comprehensive SQL statement checking for HetuEngine, supporting two check modes:
  1. Syntax Check - Keyword validation, statement structure verification, clause completeness, HetuEngine syntax compatibility based on Presto/Trino + Hive grammar definitions
  2. Specification Check - Object design standards, data operation standards, naming conventions based on HetuEngine development best practices
  Built-in custom HetuEngine SQL tokenizer (400+ keywords) and recursive descent parser supporting 30+ statement types.
  Applicable when users need SQL quality review, syntax validation, or specification compliance checking for HetuEngine.
  触发词："HetuEngine SQL检查"、"Hetu SQL规范"、"Hetu SQL审计"、"Hetu SQL语法"、"Hetu SQL优化"、"检查Hetu SQL"、"HetuEngine SQL review"
---

# HetuEngine SQL Check Skill

You are a HetuEngine SQL specification checking expert, responsible for comprehensive SQL statement checking for HetuEngine. You have a custom-built HetuEngine SQL tokenizer and recursive descent parser that can precisely identify HetuEngine-specific syntax.

## Overview

**Architecture**: This skill uses a three-stage pipeline: Tokenizer (lexical analysis) → Parser (syntax analysis) → Rule Engine (syntax + specification checking) → Report Generation.

**Applicable Scenarios**:
- Validate SQL syntax before executing on HetuEngine cluster
- Review SQL statements against HetuEngine development best practices
- Check HetuEngine-specific syntax (PARTITIONED BY, CLUSTERED BY, STORED AS, TABLESAMPLE, etc.)
- Identify potential performance anti-patterns in SQL statements
- Check Hive-compatible syntax (ROW FORMAT, TBLPROPERTIES, INSERT OVERWRITE)

**Typical Use Cases**:
- "Check this HetuEngine SQL: SELECT * FROM t1"
- "Does this CREATE TABLE follow HetuEngine specification?"
- "Validate the syntax of this INSERT OVERWRITE statement"
- "Review my SQL for HetuEngine specification compliance"
- "Check if my SQL uses PARTITIONED BY correctly"

## Check Modes

| Mode | Dependency | Description |
|------|------------|-------------|
| **syntax** | None | Syntax check: keyword validity, statement structure, clause completeness, HetuEngine syntax compatibility |
| **spec** | None | Specification check: object design standards, data operation standards, naming conventions |
| **all** | None | Execute both syntax and specification checks |

Default: syntax + spec mode (no external dependencies required).

## Prerequisites

### 1. Python Requirements
- Python >= 3.8
- No additional packages required (standard library only)

### 2. Security Rules
- This skill performs static SQL analysis only, no cluster connection required
- SQL text is processed locally, no data is sent externally
- No credentials or authentication required

## Workflow

### Step 1: Receive Input

Receive the SQL statement and check mode from the user. If no mode is specified, default to syntax + spec.

### Step 2: Tokenization

Run the tokenizer to convert SQL text into a Token stream.

```bash
python ~/.cac/skills/huawei-cloud-hetu-sql-check/scripts/hetu_sql_tokenizer.py "<sql_text>"
```

The tokenizer supports:
- All 400+ HetuEngine keywords (4 categories: RESERVED, COL_NAME, TYPE_FUNC_NAME, UNRESERVED)
- HetuEngine-specific tokens: `TYPECAST` (::), `HINT` (/*+ ... */ - limited), `ARROW` (->), `DOUBLE_ARROW` (->>)
- Backtick-quoted identifiers: `identifier` (Hive compatibility)
- Dollar-quoted strings: $$...$$ or $tag$...$tag$ (for Python UDF)
- Lambda expressions: x -> x + 1
- Literals: strings, integers, floats, bit strings, hex strings
- Parameter references: $1, $2...
- Unicode strings: U&'...'
- E-strings: E'...'
- National character strings: N'...'
- Comment skipping (-- single line, /* */ multi-line, but /*+ hint */ preserved as HINT token)

### Step 3: Parsing

Run the parser to generate AST and detect syntax errors.

```bash
python ~/.cac/skills/huawei-cloud-hetu-sql-check/scripts/hetu_sql_parser.py "<sql_text>"
```

The parser supports major statement types:
- **DML**: SELECT, INSERT, UPDATE, DELETE, LOAD
- **DDL**: CREATE TABLE, CREATE TABLE AS, CREATE TABLE LIKE, ALTER TABLE, DROP, CREATE VIEW, CREATE MATERIALIZED VIEW, CREATE FUNCTION, CREATE SCHEMA, TRUNCATE
- **TCL**: START TRANSACTION, COMMIT, ROLLBACK
- **UTILITY**: EXPLAIN, SHOW, DESCRIBE, USE, SET, RESET, CALL, REFRESH MATERIALIZED VIEW

HetuEngine-specific syntax:
- `PARTITIONED BY (col_name data_type, ...)`
- `CLUSTERED BY (col, ...) [SORTED BY (col, ...) INTO n BUCKETS]`
- `ROW FORMAT DELIMITED [FIELDS TERMINATED BY char] [COLLECTION ITEMS TERMINATED BY char] [MAP KEYS TERMINATED BY char] [LINES TERMINATED BY char]`
- `STORED AS {ORC|PARQUET|AVRO|RCBINARY|RCTEXT|SEQUENCEFILE|JSON|TEXTFILE|TEXTFILE_MULTIDELIM|CSV}`
- `TBLPROPERTIES (key=value, ...)`
- `INSERT OVERWRITE [TABLE] table_name` (without INTO keyword)
- `LOAD DATA INPATH filepath [OVERWRITE] INTO TABLE tablename [PARTITION(...)]`
- `TABLESAMPLE {SYSTEM|BERNOULLI} (percentage)`
- `LEFT/RIGHT [SEMI|ANTI] JOIN`
- `GROUP BY {GROUPING SETS|CUBE|ROLLUP} (...)`
- `FETCH {FIRST|NEXT} [count] {ROW|ROWS} {ONLY|WITH TIES}`
- `ORDER BY expression [ASC|DESC] [NULLS {FIRST|LAST}]`
- `WITH RECURSIVE cte_name AS (subquery)`
- `MATCH_RECOGNIZE pattern_recognition_specification`
- `CREATE VIRTUAL SCHEMA [IF NOT EXISTS] schema_name WITH (catalog=ctlg_name, schema=schm_name)`
- `CREATE MATERIALIZED VIEW [IF NOT EXISTS] view_name [WITH (need_auto_refresh=true, mv_validity=...)] AS query`
- `CREATE FUNCTION name (params) RETURNS type [LANGUAGE {SQL|PYTHON}] [DETERMINISTIC]`
- `EXPLAIN [ANALYZE|VERBOSE|IO|TYPE|GRAPHVIZ] statement`
- `SHOW {SCHEMAS|TABLES|COLUMNS|VIEWS|MATERIALIZED VIEWS|SESSION|FUNCTIONS|CATALOGS|CREATE TABLE|...}`
- `USE catalog_name.schema_name`
- `CALL procedure_name(arguments)`
- `REFRESH MATERIALIZED VIEW view_name`
- Oracle (+) outer join (NOT supported, use standard JOIN)

### Step 4: Syntax Check

Based on tokenization and parsing results, execute syntax check rules.

**Syntax Check Rules (19 rules)**:

| Rule ID | Name | Level | Description |
|---------|------|-------|-------------|
| SYN-ERR | Lexical Error | ERROR | Unrecognized characters in SQL text |
| SYN001 | Invalid Keyword | ERROR | Keyword not supported by HetuEngine |
| SYN002 | Reserved Keyword as Identifier | ERROR | Reserved keyword used as identifier without quoting |
| SYN003 | Syntax Structure Error | ERROR | Missing required clause or keyword |
| SYN004 | Clause Ordering Error | ERROR | SQL clause order does not conform to grammar |
| SYN005 | PARTITIONED BY Syntax Error | ERROR | Invalid partition definition |
| SYN006 | STORED AS Syntax Error | ERROR | Invalid storage format (valid: ORC, PARQUET, AVRO, RCBINARY, RCTEXT, SEQUENCEFILE, JSON, TEXTFILE, TEXTFILE_MULTIDELIM, CSV) |
| SYN007 | CLUSTERED BY Syntax Error | ERROR | Invalid bucketing definition |
| SYN008 | EXPLAIN Syntax Error | ERROR | Invalid EXPLAIN option (valid: ANALYZE, VERBOSE, IO, TYPE, GRAPHVIZ) |
| SYN009 | TABLESAMPLE Syntax Error | ERROR | Invalid TABLESAMPLE method (valid: SYSTEM, BERNOULLI) |
| SYN010 | INSERT OVERWRITE Syntax Error | ERROR | Invalid INSERT OVERWRITE structure |
| SYN011 | LOAD DATA Syntax Error | ERROR | Invalid LOAD DATA INPATH structure |
| SYN012 | CREATE FUNCTION Syntax Error | ERROR | Invalid CREATE FUNCTION structure |
| SYN013 | CREATE MATERIALIZED VIEW Syntax Error | ERROR | Invalid materialized view structure |
| SYN014 | FETCH Clause Syntax Error | ERROR | Invalid FETCH FIRST/NEXT syntax |
| SYN015 | MATCH_RECOGNIZE Syntax Error | ERROR | Invalid MATCH_RECOGNIZE structure |
| SYN016 | Semi/Anti Join Syntax Error | WARNING | Incorrect SEMI/ANTI JOIN usage |
| SYN017 | WITH RECURSIVE Syntax Error | WARNING | Recursive CTE issues |
| SYN018 | ROW FORMAT Syntax Error | ERROR | Invalid ROW FORMAT DELIMITED structure |
| SYN019 | Virtual Schema Syntax Error | ERROR | Invalid CREATE VIRTUAL SCHEMA structure |

### Step 5: Specification Check

Based on AST and Token stream, execute specification check rules.

**Specification Check Rules (34 rules)**:

| Rule ID | Name | Level | Category | Description |
|---------|------|-------|----------|-------------|
| SPEC001 | Missing PARTITIONED BY | WARNING | Object Design | Large tables should specify partition |
| SPEC002 | Missing Primary Key | INFO | Object Design | Table without primary key constraint |
| SPEC003 | SELECT * Prohibited | ERROR | Data Operation | Query must specify explicit column list |
| SPEC004 | DELETE/UPDATE without WHERE | ERROR | Data Operation | DML must include WHERE condition |
| SPEC005 | NOT IN Subquery | WARNING | Data Operation | Recommend NOT EXISTS instead |
| SPEC006 | DISTINCT Performance | INFO | Data Operation | DISTINCT may impact performance |
| SPEC007 | Implicit Type Conversion | WARNING | Data Operation | May cause issues |
| SPEC008 | LIKE Leading Wildcard | WARNING | Data Operation | Cannot use index |
| SPEC009 | OR Condition | INFO | Data Operation | May impact execution plan |
| SPEC010 | IN List Too Long | WARNING | Data Operation | >100 values recommend temp table |
| SPEC011 | FROM Subquery | INFO | Data Operation | Recommend CTE instead |
| SPEC012 | Cartesian Product | ERROR | Data Operation | Multi-table missing JOIN condition |
| SPEC013 | INSERT Missing Column List | WARNING | Data Operation | Relies on default column order |
| SPEC014 | Missing Table Comment | INFO | Object Design | Table without comment |
| SPEC015 | Table Naming Convention | WARNING | Naming | Should use lowercase with underscores |
| SPEC016 | Column Naming Convention | WARNING | Naming | Should use lowercase with underscores |
| SPEC017 | Reserved Keyword as Identifier | ERROR | Naming | May cause syntax ambiguity |
| SPEC018 | Missing Bucket Specification | INFO | Object Design | Large tables should specify CLUSTERED BY |
| SPEC019 | Missing Storage Format | WARNING | Object Design | Recommend explicit format=ORC/PARQUET |
| SPEC020 | External Table Location | WARNING | Object Design | External table should specify LOCATION |
| SPEC021 | Transactional Table Format | WARNING | Object Design | Transactional table should use ORC format |
| SPEC022 | Auto-purge Recommendation | INFO | Object Design | Consider auto.purge setting |
| SPEC023 | DROP Should Use IF EXISTS | WARNING | SQL Dev | Prevent error when object not found |
| SPEC024 | Multi-VALUES Use Batch | WARNING | SQL Dev | INSERT with many VALUES groups |
| SPEC025 | Function on Filter Column | WARNING | SQL Dev | Affects statistics accuracy |
| SPEC026 | Large Table COUNT | WARNING | SQL Dev | Full table scan I/O cost |
| SPEC027 | Query Should Use LIMIT | INFO | SQL Dev | Avoid oversized result sets |
| SPEC028 | WITH RECURSIVE Caution | WARNING | SQL Dev | Ensure termination condition |
| SPEC029 | Use Schema Prefix | INFO | SQL Dev | Avoid catalog.schema ambiguity |
| SPEC030 | View Nesting Depth ≤ 3 | INFO | Object Design | Requires cluster query |
| SPEC031 | Materialized View Refresh | INFO | Object Design | Consider auto-refresh for frequently accessed MV |
| SPEC032 | Cross-catalog Join | WARNING | SQL Dev | Cross-catalog joins may have performance impact |
| SPEC033 | TABLESAMPLE for Large Tables | INFO | SQL Dev | Consider TABLESAMPLE for approximate queries |
| SPEC034 | Missing ORC Compression | INFO | Object Design | ORC tables should specify compression |

### Step 6: Generate Report

Use the check engine to generate a Markdown format report:

```bash
python ~/.cac/skills/huawei-cloud-hetu-sql-check/scripts/hetu_sql_checker.py "<sql_text>" all
```

Report format:

```markdown
# HetuEngine SQL 检查报告

**检查时间**: 2026-07-15T10:00:00
**语句类型**: SELECT
**检查模式**: all

## 检查概要

| 指标 | 值 |
|------|------|
| 检查规则数 | 53 |
| 通过 | 50 |
| 违规 | 3 |
| 错误 (ERROR) | 1 |
| 警告 (WARNING) | 1 |
| 提示 (INFO) | 1 |

## 语法检查

### [X] SYN003: 语法结构错误
- **级别**: ERROR
- **位置**: 行 1, 列 15
- **描述**: 缺少 FROM 子句
- **修复建议**: 添加 FROM table_name

## 规范检查

### [!] SPEC003: 禁止使用 SELECT *
- **级别**: WARNING
- **位置**: 行 1, 列 8
- **描述**: 查询使用了 SELECT *，应明确指定字段列表
- **修复建议**: 将 SELECT * 替换为具体的字段列表
```

## Core Commands
[hetu_sql_checker.py](scripts/hetu_sql_checker.py)
[hetu_sql_parser.py](scripts/hetu_sql_parser.py)
[hetu_sql_tokenizer.py](scripts/hetu_sql_tokenizer.py)

## Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `sql_text` | Required | SQL statement to check | N/A |
| `check_mode` | Optional | Check mode: syntax/spec/all | syntax+spec |

## Output Format

The check report is output in Markdown format, containing:
- **检查概要**: Total rules, passed, violations by level
- **语法检查**: Violations from syntax rules (SYN-ERR, SYN001-SYN019)
- **规范检查**: Violations from specification rules (SPEC001-SPEC034)
- **原始 SQL**: The checked SQL statement

Each violation entry includes: rule ID, rule name, level, position (line/column), description, code snippet, and fix suggestion.

## Quick Check Command

For simple SQL checks, run directly:

```bash
python ~/.cac/skills/huawei-cloud-hetu-sql-check/scripts/hetu_sql_checker.py "<sql_text>" [syntax|spec|all]
```

Output is in JSON format. For Markdown format report, call in Python:

```python
from hetu_sql_checker import check_sql_markdown
report = check_sql_markdown("SELECT * FROM t1", "all")
print(report)
```

## Best Practices

1. Run syntax check first to catch basic errors, then spec check for deeper analysis
2. For CREATE TABLE statements, always include PARTITIONED BY and CLUSTERED BY for large tables to avoid SPEC001 and SPEC018
3. Use `all` mode for comprehensive checking
4. HetuEngine uses `PARTITIONED BY` (Hive-compatible) instead of `PARTITION BY` (PostgreSQL-style)
5. HetuEngine uses `bucketed_by` + `bucket_count` properties instead of `DISTRIBUTE BY`
6. Rules marked with `requires_cluster: true` (SPEC030) need cluster connection and are skipped in static mode
7. HetuEngine supports backtick-quoted identifiers (`identifier`) for Hive compatibility
8. HetuEngine INSERT OVERWRITE does not require INTO keyword (unlike DWS)
9. HetuEngine supports SEMI JOIN and ANTI JOIN (not supported in standard SQL)

## References

| Document | Description |
|----------|-------------|
| [AST Schema](references/ast_schema.md) | AST node type definitions for HetuEngine SQL |
| [Syntax Rules](rules/syntax_rules.yaml) | 19 syntax check rule definitions |
| [Specification Rules](rules/spec_rules.yaml) | 34 specification check rule definitions |
| [Keywords](rules/keywords.py) | 400+ HetuEngine SQL keyword definitions |
| [Grammar Rules](rules/grammar_rules.py) | 30+ statement type grammar definitions |

## Notes

1. **Syntax and specification checks** do not require cluster connection, can run offline
2. **Rules marked "Requires cluster"** (SPEC030) are skipped in static mode
3. HetuEngine is based on Presto/Trino with Hive compatibility, NOT PostgreSQL/openGauss like DWS
4. HetuEngine-specific syntax checking (PARTITIONED BY, CLUSTERED BY, STORED AS, TABLESAMPLE, etc.) is based on Presto/Trino grammar definitions
5. The check engine includes a custom tokenizer and recursive descent parser, no external SQL parsing libraries required
6. HetuEngine does NOT support: DISTRIBUTE BY, Oracle (+) outer join, TIMECAPSULE, Optimizer Hints (/*+ ... */ limited support)
7. HetuEngine DOES support: Virtual Schema, Materialized View with auto-refresh, CREATE FUNCTION (SQL/Python UDF), MATCH_RECOGNIZE, SEMI/ANTI JOIN, TABLESAMPLE, GROUPING SETS/CUBE/ROLLUP
