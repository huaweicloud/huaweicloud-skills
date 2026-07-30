---
name: huawei-cloud-doris-sql-check
description: |
  Comprehensive SQL statement checking for Apache Doris (based on Doris 3.1.4 Nereids ANTLR4 grammar),
  supporting two check modes:
  1. Syntax Check - Keyword validation, statement structure verification, clause completeness,
     Doris-specific syntax compatibility (DISTRIBUTED BY, PARTITION BY, ENGINE,
     DUPLICATE/AGGREGATE/UNIQUE KEY, INSERT OVERWRITE, LOAD, EXPORT, MTMV, BACKUP/RESTORE etc.)
  2. Specification Check - Object design standards, data operation standards, naming conventions
     based on Apache Doris development best practices.
  Built-in custom Doris SQL tokenizer (504 keywords from DorisLexer.g4) and recursive descent parser
  supporting 100+ Doris statement types.
  Applicable when users need SQL quality review, syntax validation, or specification compliance checking
  for Apache Doris SQL (versions 2.1.x / 3.0.x / 3.1.x / 4.x).
  触发词："Doris SQL检查"、"Doris SQL规范"、"Doris SQL审计"、"Doris SQL语法"、"检查Doris SQL"、"Doris SQL review"
tags: [apache-doris, doris, sql, check, lint, nereids]
---

# Doris SQL Check Skill

You are an Apache Doris SQL specification checking expert, responsible for comprehensive SQL statement checking for Apache Doris (based on Doris 3.1.4 source code). You have a custom-built Doris SQL tokenizer and recursive descent parser that can precisely identify Doris-specific syntax from the Nereids ANTLR4 grammar (`DorisLexer.g4` / `DorisParser.g4`).

## Overview

**Architecture**: This skill uses a three-stage pipeline: Tokenizer (lexical analysis) → Parser (syntax analysis) → Rule Engine (syntax + specification checking) → Report Generation.

**Applicable Scenarios**:

- Validate SQL syntax before executing on a Doris cluster (FE/BE)
- Review SQL statements against Apache Doris development best practices
- Check Doris-specific syntax (DISTRIBUTED BY HASH/RANDOM, PARTITION BY RANGE/LIST/AUTO, BUCKETS, PROPERTIES, ENGINE, DUPLICATE/AGGREGATE/UNIQUE KEY, INSERT OVERWRITE TABLE, LOAD LABEL, ROUTINE LOAD, EXPORT, MTMV, BACKUP/RESTORE SNAPSHOT, ADMIN SET/SHOW, CANCEL, KILL, TABLESAMPLE, OUTFILE, Hint /*+ */, full-text MATCH_*, COLOCATE GROUP)
- Identify potential performance anti-patterns in Doris SQL statements

**Typical Use Cases**:

- "Check this Doris SQL: SELECT * FROM t1"
- "Does this CREATE TABLE follow Doris specification (DISTRIBUTED BY, KEY model, PARTITION)?"
- "Validate the syntax of this INSERT OVERWRITE TABLE statement"
- "Review my Doris SQL for specification compliance"
- "Check if my SQL uses Doris-specific syntax correctly (MTMV, LOAD, EXPORT)"
- "Validate BACKUP/RESTORE SNAPSHOT syntax"
- "Check my ROUTINE LOAD job definition"

## Check Modes

| Mode       | Dependency | Description                                                                                          |
| ---------- | ---------- | ---------------------------------------------------------------------------------------------------- |
| **syntax** | None       | Syntax check: keyword validity, statement structure, clause completeness, Doris syntax compatibility |
| **spec**   | None       | Specification check: object design standards, data operation standards, naming conventions           |
| **all**    | None       | Execute both syntax and specification checks                                                         |

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
python ~/.cac/skills/huawei-cloud-doris-sql-check/scripts/doris_sql_tokenizer.py "<sql_text>"
```

The tokenizer supports:

- All 504 Doris keywords (from `DorisLexer.g4` between `--DORIS-KEYWORD-LIST-START` and `--DORIS-KEYWORD-LIST-END`)
- Doris-specific tokens: `HINT` (`/*+ ... */`), `BACKQUOTED` (`` `ident` ``), `ARROW` (`->`), `NSEQ` (`<=>` null-safe eq), `EQ` (`=` or `==`), `NEQ` (`<>` or `!=`), `LTE` (`<=` or `!>`), `GTE` (`>=` or `!<`), `DOUBLEPIPES` (`||`), `LOGICALAND` (`&&`), `LOGICALNOT` (`!`)
- Literals: strings (`'...'` / `"..."`), integers, decimals, bigints (`123L`), smallints (`123S`), tinyints (`123Y`), bigdecimals (`123BD`), exponents
- Backquoted identifiers: `` `table_name` `` (Doris-style, preferred over double quotes)
- Comment skipping (`--` single line, `/* */` multi-line, but `/*+ hint */` preserved as HINT token)
- Full-text search operators: `MATCH_ALL`, `MATCH_ANY`, `MATCH_PHRASE`, `MATCH_PHRASE_PREFIX`, `MATCH_PHRASE_EDGE`, `MATCH_REGEXP`, `MATCH_NAME`, `MATCH_NAME_GLOB`

### Step 3: Parsing

Run the parser to generate AST and detect syntax errors.

```bash
python ~/.cac/skills/huawei-cloud-doris-sql-check/scripts/doris_sql_parser.py "<sql_text>"
```

The parser supports major Doris statement types (based on `DorisParser.g4`):

- **DML**: SELECT (with CTE, set ops, window, TABLESAMPLE), INSERT INTO/OVERWRITE TABLE, UPDATE, DELETE, LOAD (BROKER LOAD), EXPORT, COPY INTO, TRUNCATE
- **DDL**: CREATE TABLE (with DISTRIBUTED BY, PARTITION BY, KEY model, ENGINE, PROPERTIES), CREATE TABLE LIKE, CREATE VIEW, CREATE MTMV (Multi-Table Materialized View), CREATE INDEX (BITMAP/NGRAM_BF/INVERTED), ALTER TABLE (ADD/MODIFY/DROP/RENAME COLUMN, ADD/DROP PARTITION, ADD/DROP INDEX, ROLLUP, TAG/BRANCH), DROP TABLE/VIEW/INDEX, CREATE CATALOG, CREATE DATABASE, CREATE USER/ROLE, CREATE RESOURCE, CREATE STAGE, CREATE ENCRYPTKEY, CREATE JOB, CREATE ROW POLICY, CREATE SQL_BLOCK_RULE, CREATE STORAGE VAULT/POLICY, CREATE WORKLOAD GROUP/POLICY
- **DCL**: GRANT/REVOKE (table/resource/role privileges)
- **TCL**: BEGIN/START TRANSACTION, COMMIT, ROLLBACK
- **Utility**: EXPLAIN (PARSED/ANALYZED/REWRITTEN/LOGICAL/OPTIMIZED/PHYSICAL/SHAPE/MEMO/DISTRIBUTED/ALL, VERBOSE/TREE/GRAPH/PLAN), SET (variables/options), SHOW (50+ variants), DESC/DESCRIBE, ADMIN SET/SHOW (replica, frontend config, tablet diagnose, trash, TDE), KILL (CONNECTION/QUERY), CANCEL (LOAD/EXPORT/ALTER TABLE/BACKUP/RESTORE/WARM UP), BACKUP/RESTORE SNAPSHOT, RECOVER (DATABASE/TABLE/PARTITION), CLEAN (LABEL/PROFILE/QUERY STATS), INSTALL/UNINSTALL PLUGIN, LOCK/UNLOCK TABLES, WARM UP, SYNC, HELP, CALL PROCEDURE

Doris-specific syntax:

- `DISTRIBUTED BY {HASH(cols) | RANDOM} (BUCKETS n | AUTO)?`
- `PARTITION BY (RANGE | LIST)? ... (AUTO)?` (auto partition, step partition, less-than, fixed, in-list)
- `(DUPLICATE | AGGREGATE | UNIQUE) KEY (cols) (CLUSTER BY cols)?`
- `ENGINE = olap | mysql | elasticsearch | hive | hudi | iceberg | jdbc | ...`
- `PROPERTIES ('key'='value', ...)`
- `INSERT OVERWRITE TABLE ...`
- `LOAD LABEL ... (DATA INFILE (...) INTO TABLE ...)`
- `CREATE ROUTINE LOAD ... FROM type (...)`
- `EXPORT TABLE ... TO ...`
- `BACKUP SNAPSHOT ... TO repo (ON|EXCLUDE (...))?`
- `RESTORE SNAPSHOT ... FROM repo (ON|EXCLUDE (...))?`
- `EXPLAIN {PARSED|ANALYZED|REWRITTEN|LOGICAL|OPTIMIZED|PHYSICAL|SHAPE|MEMO|DISTRIBUTED|ALL} [VERBOSE|TREE|GRAPH|PLAN] [PROCESS]`
- `CREATE MATERIALIZED VIEW ... (DUPLICATE KEY ...)? PARTITION BY ... DISTRIBUTED BY ... AS query`
  - `BUILD [IMMEDIATE|DEFERRED]`, `REFRESH [COMPLETE|AUTO]`, `ON [MANUAL|SCHEDULE|COMMIT]`
- `TABLESAMPLE (...) (REPEATABLE n)?`
- `WITH cte_name AS (...)` (CTE; Doris does not require explicit RECURSIVE keyword)
- Window functions: `OVER (PARTITION BY ... ORDER BY ... ROWS/RANGE ...)`
- `OUTFILE 'path' (FORMAT AS ...)? (PROPERTIES (...))?`
- Hints: `/*+ hint_name(...) */` and `[hint_name]` relation hints
- `ALTER COLOCATE GROUP name SET (...)`
- Full-text search: `col MATCH_ALL '...'`, `MATCH_PHRASE`, `MATCH_PHRASE_PREFIX`, `MATCH_PHRASE_EDGE`, `MATCH_ANY`, `MATCH_REGEXP`
- Aggregate unions: `HLL_UNION`, `BITMAP_UNION`, `QUANTILE_UNION`, `REPLACE_IF_NOT_NULL`
- Doris data types: TINYINT, SMALLINT, INT, BIGINT, LARGEINT, BOOLEAN, FLOAT, DOUBLE, DATE, DATETIME, DATEV2, DATETIMEV2, DATEV1, DATETIMEV1, BITMAP, QUANTILE_STATE, HLL, AGG_STATE, STRING, JSON, JSONB, TEXT, VARCHAR, CHAR, DECIMAL, DECIMALV2, DECIMALV3, IPV4, IPV6, ARRAY, MAP, STRUCT, VARIANT

### Step 4: Syntax Check

Based on tokenization and parsing results, execute syntax check rules.

**Syntax Check Rules (34 rules)**:

| Rule ID | Name                                 | Level   | Description                                                                                                 |
| ------- | ------------------------------------ | ------- | ----------------------------------------------------------------------------------------------------------- |
| SYN-ERR | Lexical Error                        | ERROR   | Unrecognized characters in SQL text                                                                         |
| SYN001  | Invalid Keyword                      | ERROR   | Keyword not supported by Doris (not in 504-keyword list)                                                    |
| SYN002  | Reserved Keyword as Identifier       | ERROR   | Reserved keyword used as identifier without backticks                                                       |
| SYN003  | Syntax Structure Error               | ERROR   | Missing required clause or keyword                                                                          |
| SYN004  | Clause Ordering Error                | ERROR   | SQL clause order does not conform to grammar                                                                |
| SYN005  | DISTRIBUTED BY Syntax Error          | ERROR   | Invalid distribution strategy (only HASH/RANDOM supported)                                                  |
| SYN006  | PARTITION BY Syntax Error            | ERROR   | Invalid partition definition (RANGE/LIST/AUTO)                                                              |
| SYN007  | BUCKETS Syntax Error                 | ERROR   | Invalid BUCKETS clause (must be INTEGER or AUTO)                                                            |
| SYN008  | EXPLAIN planType Syntax Error        | ERROR   | Invalid EXPLAIN plan type (PARSED/ANALYZED/REWRITTEN/LOGICAL/OPTIMIZED/PHYSICAL/SHAPE/MEMO/DISTRIBUTED/ALL) |
| SYN009  | KEY Model Syntax Error               | ERROR   | Invalid data model (DUPLICATE/AGGREGATE/UNIQUE KEY)                                                         |
| SYN010  | PROPERTIES Syntax Error              | ERROR   | Invalid PROPERTIES clause structure                                                                         |
| SYN011  | ENGINE Syntax Error                  | ERROR   | Invalid ENGINE clause                                                                                       |
| SYN012  | INSERT OVERWRITE Syntax Error        | ERROR   | Invalid INSERT OVERWRITE TABLE structure                                                                    |
| SYN013  | LOAD Syntax Error                    | ERROR   | Invalid LOAD LABEL / BROKER LOAD structure                                                                  |
| SYN014  | ROUTINE LOAD Syntax Error            | ERROR   | Invalid CREATE ROUTINE LOAD structure                                                                       |
| SYN015  | EXPORT Syntax Error                  | ERROR   | Invalid EXPORT TABLE ... TO structure                                                                       |
| SYN016  | BACKUP/RESTORE SNAPSHOT Syntax Error | ERROR   | Invalid BACKUP/RESTORE SNAPSHOT structure                                                                   |
| SYN017  | CREATE MTMV Syntax Error             | ERROR   | Invalid CREATE MATERIALIZED VIEW structure                                                                  |
| SYN018  | CREATE CATALOG Syntax Error          | ERROR   | Invalid CREATE CATALOG structure                                                                            |
| SYN019  | CREATE USER/ROLE Syntax Error        | ERROR   | Invalid CREATE USER/ROLE structure                                                                          |
| SYN020  | CREATE ROW POLICY Syntax Error       | ERROR   | Invalid CREATE ROW POLICY structure                                                                         |
| SYN021  | CREATE SQL_BLOCK_RULE Syntax Error   | ERROR   | Invalid CREATE SQL_BLOCK_RULE structure                                                                     |
| SYN022  | CREATE STAGE Syntax Error            | ERROR   | Invalid CREATE STAGE structure                                                                              |
| SYN023  | CREATE JOB Syntax Error              | ERROR   | Invalid CREATE JOB ON SCHEDULE structure                                                                    |
| SYN024  | CREATE ENCRYPTKEY Syntax Error       | ERROR   | Invalid CREATE ENCRYPTKEY structure                                                                         |
| SYN025  | ADMIN SET/SHOW Syntax Error          | ERROR   | Invalid ADMIN statement structure                                                                           |
| SYN026  | CANCEL Syntax Error                  | ERROR   | Invalid CANCEL statement (LOAD/EXPORT/ALTER/BACKUP/RESTORE/WARM UP)                                         |
| SYN027  | KILL Syntax Error                    | ERROR   | Invalid KILL (CONNECTION/QUERY) statement                                                                   |
| SYN028  | TABLESAMPLE Syntax Error             | ERROR   | Invalid TABLESAMPLE clause (PERCENT/ROWS, REPEATABLE)                                                       |
| SYN029  | OUTFILE Syntax Error                 | ERROR   | Invalid OUTFILE clause (FORMAT AS, PROPERTIES)                                                              |
| SYN030  | Hint Syntax Error                    | WARNING | Invalid hint format (must be `/*+ name(...) */` or `[name]`)                                                |
| SYN031  | Full-text MATCH Syntax Error         | ERROR   | Invalid MATCH_ALL/MATCH_ANY/MATCH_PHRASE/MATCH_REGEXP usage                                                 |
| SYN032  | COLOCATE GROUP Syntax Error          | ERROR   | Invalid ALTER COLOCATE GROUP structure                                                                      |
| SYN033  | GRANT/REVOKE Syntax Error            | ERROR   | Invalid GRANT/REVOKE privilege structure                                                                    |

### Step 5: Specification Check

Based on AST and Token stream, execute specification check rules. Rules are derived from `DorisParser.g4` grammar definitions and Apache Doris development best practices.

**Specification Check Rules (46 rules)**:

| Rule ID | Name                                     | Level   | Category            | Description                                                                               |
| ------- | ---------------------------------------- | ------- | ------------------- | ----------------------------------------------------------------------------------------- |
| SPEC001 | Missing DISTRIBUTED BY                   | ERROR   | Object Design       | CREATE TABLE without distribution strategy (Doris requires DISTRIBUTED BY HASH or RANDOM) |
| SPEC002 | Missing ENGINE                           | INFO    | Object Design       | CREATE TABLE without explicit ENGINE (defaults to OLAP)                                   |
| SPEC003 | SELECT * Prohibited                      | ERROR   | Data Operation      | Query must specify explicit column list                                                   |
| SPEC004 | DELETE/UPDATE without WHERE              | ERROR   | Data Operation      | DML must include WHERE condition                                                          |
| SPEC005 | NOT IN Subquery                          | WARNING | Data Operation      | Recommend NOT EXISTS or LEFT JOIN ... IS NULL                                             |
| SPEC006 | DISTINCT Performance                     | INFO    | Data Operation      | DISTINCT may impact performance                                                           |
| SPEC007 | Implicit Type Conversion                 | WARNING | Data Operation      | May cause index/zone-map invalidation                                                     |
| SPEC008 | LIKE Leading Wildcard                    | WARNING | Data Operation      | Cannot use zone-map or index                                                              |
| SPEC009 | OR Condition                             | INFO    | Data Operation      | May impact execution plan                                                                 |
| SPEC010 | IN List Too Long                         | WARNING | Data Operation      | >1000 values recommend temp table                                                         |
| SPEC011 | FROM Subquery                            | INFO    | Data Operation      | Recommend CTE instead                                                                     |
| SPEC012 | Cartesian Product                        | ERROR   | Data Operation      | Multi-table missing JOIN condition                                                        |
| SPEC013 | INSERT Missing Column List               | WARNING | Data Operation      | Relies on default column order                                                            |
| SPEC014 | Missing Table Comment                    | INFO    | Object Design       | Table without COMMENT                                                                     |
| SPEC015 | Table Naming Convention                  | WARNING | Naming              | Should use lowercase with underscores                                                     |
| SPEC016 | Column Naming Convention                 | WARNING | Naming              | Should use lowercase with underscores                                                     |
| SPEC017 | Reserved Keyword as Identifier           | ERROR   | Naming              | May cause syntax ambiguity                                                                |
| SPEC018 | Distribution Key Column Not Found        | WARNING | Object Design       | Distribution key should be actual table column                                            |
| SPEC019 | Partition Key Same as Distribution Key   | INFO    | Object Design       | May cause data skew                                                                       |
| SPEC020 | Missing KEY Model Definition             | INFO    | Object Design       | Recommend explicit DUPLICATE/AGGREGATE/UNIQUE KEY                                         |
| SPEC021 | Large Table Should Have Partition        | INFO    | Object Design       | Improve query and governance efficiency                                                   |
| SPEC022 | BUCKETS Count Recommendation             | INFO    | Object Design       | Recommend appropriate bucket count for table size                                         |
| SPEC023 | Column Should Have NOT NULL              | INFO    | Object Design       | Optimizer can leverage NOT NULL                                                           |
| SPEC024 | DROP Should Use IF EXISTS                | WARNING | SQL Dev             | Prevent error when object not found                                                       |
| SPEC025 | INSERT Multi-VALUES                      | WARNING | SQL Dev             | Multiple VALUES groups inefficient; use STREAM LOAD / BROKER LOAD                         |
| SPEC026 | Column-store Real-time INSERT            | WARNING | SQL Dev             | Frequent small-batch INSERT into Doris (columnar) causes compaction pressure              |
| SPEC027 | Frequent UPDATE/DELETE                   | WARNING | SQL Dev             | Doris UPDATE/DELETE is costly (read-merge-write)                                          |
| SPEC028 | Function on Filter Column                | WARNING | SQL Dev             | Affects statistics accuracy and zone-map usage                                            |
| SPEC029 | Large Table COUNT                        | WARNING | SQL Dev             | Full table scan I/O cost                                                                  |
| SPEC030 | Query Should Use LIMIT                   | INFO    | SQL Dev             | Avoid oversized result sets                                                               |
| SPEC031 | CTE Recursion Safety                     | WARNING | SQL Dev             | Ensure termination condition for recursive CTE                                            |
| SPEC032 | Use Catalog/DB Prefix                    | INFO    | SQL Dev             | Avoid ambiguity in multi-catalog scenarios                                                |
| SPEC033 | View Nesting Depth ≤ 3                   | INFO    | Object Design       | Requires cluster: query view dependencies                                                 |
| SPEC034 | Index Count > 5                          | WARNING | Object Design       | Requires cluster: query table indexes                                                     |
| SPEC035 | Non-pushdown SQL Prohibited              | ERROR   | SQL Dev             | Requires cluster: EXPLAIN analysis                                                        |
| SPEC036 | BITMAP/HLL Column Needs Aggregation Type | WARNING | Object Design       | BITMAP/HLL columns should specify BITMAP_UNION/HLL_UNION                                  |
| SPEC037 | Use MTMV for Repeated Complex Queries    | INFO    | Object Design       | Recommend MTMV for repeated aggregation queries                                           |
| SPEC038 | Avoid Frequent OUTFILE Export            | INFO    | SQL Dev             | Use EXPORT or broker for large exports                                                    |
| SPEC039 | VARCHAR Length Should Be Explicit        | WARNING | Object Design       | Avoid VARCHAR without length for large strings                                            |
| SPEC040 | DECIMAL Precision Should Be Explicit     | WARNING | Object Design       | Use DECIMAL(p,s) or DECIMALV3(p,s), avoid bare DECIMAL                                    |
| SPEC041 | COUNT(DISTINCT) Excessive Use            | ERROR   | Complex Query Limit | COUNT(DISTINCT) count > 5, may cause severe performance degradation                       |
| SPEC042 | NOT IN Subquery Prohibited               | ERROR   | Complex Query Limit | NOT IN subquery causes full scan and severe performance drop; use NOT EXISTS or LEFT JOIN |
| SPEC043 | Excessive JOINs                          | ERROR   | Complex Query Limit | JOIN count > 20, may cause unstable query plans and high memory usage                     |
| SPEC044 | Excessive UNION ALLs                     | ERROR   | Complex Query Limit | UNION ALL count > 20, may cause complex plans and high resource consumption               |
| SPEC045 | Deeply Nested Subqueries                 | ERROR   | Complex Query Limit | Subquery nesting depth > 20, may cause severe parse and execution performance issues      |
| SPEC046 | SQL Statement Too Long                   | ERROR   | Complex Query Limit | SQL text length > 2MB, may cause parse timeout or excessive memory usage                  |

### Step 6: Generate Report

Use the check engine to generate a Markdown format report:

```bash
python ~/.cac/skills/huawei-cloud-doris-sql-check/scripts/doris_sql_checker.py "<sql_text>" all
```

Report format:

```markdown
# Doris SQL Check Report

**Check Time**: 2026-07-17T10:00:00
**Statement Type**: SELECT
**Check Mode**: all

## Summary

| Metric | Value |
|--------|-------|
| Total Rules | 74 |
| Passed | 71 |
| Violations | 3 |
| Errors (ERROR) | 1 |
| Warnings (WARNING) | 1 |
| Infos (INFO) | 1 |

## Syntax Check

### [X] SYN003: Syntax Structure Error
- **Level**: ERROR
- **Position**: Line 1, Column 15
- **Description**: Missing FROM clause
- **Fix Suggestion**: Add FROM table_name

## Specification Check

### [!] SPEC003: SELECT * Prohibited
- **Level**: WARNING
- **Position**: Line 1, Column 8
- **Description**: Query uses SELECT *, should specify explicit column list
- **Fix Suggestion**: Replace SELECT * with specific column list
```

## Core Commands
[doris_sql_checker.py](scripts/doris_sql_checker.py)
[doris_sql_parser.py](scripts/doris_sql_parser.py)
[doris_sql_tokenizer.py](scripts/doris_sql_tokenizer.py)
     
## Parameters

| Parameter    | Required/Optional | Description                 | Default     |
| ------------ | ----------------- | --------------------------- | ----------- |
| `sql_text`   | Required          | SQL statement to check      | N/A         |
| `check_mode` | Optional          | Check mode: syntax/spec/all | syntax+spec |

## Output Format

The check report is output in Markdown format, containing:

- **Summary table**: Total rules, passed, violations by level
- **Syntax check section**: Violations from syntax rules (SYN-ERR, SYN001-SYN033)
- **Specification check section**: Violations from specification rules (SPEC001-SPEC040)
- **Original SQL**: The checked SQL statement

Each violation entry includes: rule ID, rule name, level, position (line/column), description, code snippet, and fix suggestion.

## Quick Check Command

For simple SQL checks, run directly:

```bash
python ~/.cac/skills/huawei-cloud-doris-sql-check/scripts/doris_sql_checker.py "<sql_text>" [syntax|spec|all]
```

Output is in JSON format. For Markdown format report, call in Python:

```python
from doris_sql_checker import check_sql_markdown
report = check_sql_markdown("SELECT * FROM t1", "all")
print(report)
```

## Best Practices

1. Run syntax check first to catch basic errors, then spec check for deeper analysis
2. For CREATE TABLE statements, always include `DISTRIBUTED BY HASH(分布键)` or `DISTRIBUTED BY RANDOM` to avoid SPEC001
3. For Doris tables, explicitly specify the KEY model (`DUPLICATE KEY`/`AGGREGATE KEY`/`UNIQUE KEY`)
4. Use `all` mode for comprehensive checking
5. Rules marked with `requires_mcp: true` or "Requires cluster" (SPEC033, SPEC034, SPEC035) need cluster connection and are skipped in static mode
6. Doris does NOT support `MERGE INTO ... WHEN MATCHED` or `ON DUPLICATE KEY UPDATE` — these will be flagged as syntax errors
7. Doris identifiers use backticks (`` ` ``), not double quotes — using double quotes for identifiers will trigger a warning
8. For large data loading, prefer STREAM LOAD / BROKER LOAD / ROUTINE LOAD over multi-row INSERT VALUES (SPEC025)

## References

| Document                                     | Description                                                         |
| -------------------------------------------- | ------------------------------------------------------------------- |
| [AST Schema](references/ast_schema.md)       | AST node type definitions for Doris SQL                             |
| [Syntax Rules](rules/syntax_rules.yaml)      | 34 syntax check rule definitions                                    |
| [Specification Rules](rules/spec_rules.yaml) | 40 specification check rule definitions                             |
| [Performance Rules](rules/perf_rules.yaml)   | 11 performance check rule definitions (requires cluster)            |
| [Keywords](rules/keywords.py)                | 504 Doris SQL keyword definitions (from DorisLexer.g4)              |
| [Grammar Rules](rules/grammar_rules.py)      | 100+ Doris statement type grammar definitions (from DorisParser.g4) |

## Notes

1. **Syntax and specification checks** do not require cluster connection, can run offline
2. **Rules marked "Requires cluster"** (SPEC033, SPEC034, SPEC035) are skipped in static mode
3. **Performance rules** (PERF001-PERF011) are defined in rules/perf_rules.yaml but require cluster connection for execution (EXPLAIN ANALYZE, system tables like `information_schema.tables`, `backends`, etc.)
4. Doris-specific syntax checking (DISTRIBUTED BY, PARTITION BY, BUCKETS, PROPERTIES, ENGINE, DUPLICATE/AGGREGATE/UNIQUE KEY, INSERT OVERWRITE, LOAD, EXPORT, MTMV, BACKUP/RESTORE, ADMIN, CANCEL, KILL, TABLESAMPLE, OUTFILE, Hint, MATCH, COLOCATE GROUP) is based on `DorisParser.g4` (Nereids ANTLR4 grammar) from Doris 3.1.4 source
5. The check engine includes a custom tokenizer and recursive descent parser, no external SQL parsing libraries required (no ANTLR runtime needed)
6. **Version compatibility**: This skill is based on Doris 3.1.4 grammar. Doris 2.1.x / 3.0.x / 3.1.x / 4.x share the same Nereids grammar for most constructs; minor differences may exist for newer syntax (e.g., 4.x added features). Verify against your cluster's version before relying on specific rules.