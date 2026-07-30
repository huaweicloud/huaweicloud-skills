---
name: huawei-cloud-mrs-spark-sql-check
description: |
  Huawei Cloud MRS Spark SQL specification checking skill. Performs comprehensive SQL statement checking for MRS Spark, including syntax validation, specification compliance, and performance risk detection.
  triggers: "Spark SQL review", "check Spark SQL", "检查Spark SQL", "Spark SQL检查", "Spark SQL规范", "Spark SQL语法".
tags: [huawei-cloud, mrs, "spark sql", check]
---

# MRS Spark SQL Check Skill

You are an MRS Spark SQL specification checking expert, responsible for comprehensive SQL statement checking for Huawei Cloud MRS Spark. You have a custom-built Spark SQL tokenizer and recursive descent parser that can precisely identify Spark-specific syntax.

## Overview

**Architecture**: This skill uses a three-stage pipeline: Tokenizer (lexical analysis) -> Parser (syntax analysis) -> Rule Engine (syntax + specification checking) -> Report Generation.

**Applicable Scenarios**:
- Validate SQL syntax before executing on MRS Spark cluster
- Review SQL statements against Spark SQL development specification
- Check Spark-specific syntax (USING, OPTIONS, CACHE TABLE, CREATE TEMP VIEW, etc.)
- Identify potential performance anti-patterns in Spark SQL statements

**Typical Use Cases**:
- "Check this Spark SQL: SELECT * FROM t1"
- "Does this CREATE TABLE USING PARQUET follow Spark specification?"
- "Validate the syntax of this INSERT OVERWRITE statement"
- "Review my Spark SQL for specification compliance"

## Check Modes

| Mode | Dependency | Description |
|------|------------|-------------|
| **syntax** | None | Syntax check: keyword validity, statement structure, clause completeness, Spark SQL syntax compatibility |
| **spec** | None | Specification check: object design standards, data operation standards, naming conventions, Spark SQL development rules |
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
python ~/.cac/skills/huawei-cloud-mrs-spark-sql-check/scripts/spark_sql_tokenizer.py "<sql_text>"
```

The tokenizer supports:
- All Spark SQL keywords (4 categories: RESERVED, COL_NAME, TYPE_FUNC_NAME, UNRESERVED)
- Spark-specific tokens: `HINT` (/*+ ... */), `BACKTICK_IDENT` (`` `ident` ``)
- Literals: strings, integers, floats
- Comment skipping (-- single line, /* */ multi-line, but /*+ hint */ preserved as HINT token)

### Step 3: Parsing

Run the parser to generate AST and detect syntax errors.

```bash
python ~/.cac/skills/huawei-cloud-mrs-spark-sql-check/scripts/spark_sql_parser.py "<sql_text>"
```

The parser supports major statement types:
- **DML**: SELECT, INSERT (including INSERT OVERWRITE), UPDATE, DELETE, MERGE
- **DDL**: CREATE TABLE (with USING/OPTIONS), ALTER TABLE, DROP, CREATE VIEW/TEMP VIEW/GLOBAL TEMP VIEW, TRUNCATE
- **DCL**: GRANT, REVOKE
- **UTILITY**: EXPLAIN, SET, SHOW, DESCRIBE, ANALYZE TABLE
- **Spark-specific**: CACHE TABLE, UNCACHE TABLE, CLEAR CACHE, REFRESH TABLE/FUNCTION, ADD JAR, LIST JAR, RESET

Spark-specific syntax:
- `CREATE TABLE ... USING {parquet|orc|json|csv|...} [OPTIONS (...)]`
- `CACHE [LAZY] TABLE table_name [AS SELECT ...]`
- `CREATE [OR REPLACE] [GLOBAL] TEMP [MATERIALIZED] VIEW`
- `REFRESH TABLE table_name` / `REFRESH FUNCTION func_name`
- `ADD JAR /path/to/file.jar`
- `/*+ BROADCAST(table) */` and `/*+ COALESCE(N) */` hints
- `LATERAL VIEW ... EXPLODE(...)`
- `PARTITIONED BY (col_name)` (Spark-style, column names only)

### Step 4: Syntax Check

Based on tokenization and parsing results, execute syntax check rules.

**Syntax Check Rules (20 rules)**:

| Rule ID | Name | Level | Description |
|---------|------|-------|-------------|
| SYN-ERR | Lexical Error | ERROR | Unrecognized characters in SQL text |
| SYN001 | Invalid Keyword | ERROR | Keyword not supported by Spark SQL |
| SYN002 | Reserved Keyword as Identifier | ERROR | Reserved keyword used as identifier without quoting |
| SYN003 | Syntax Structure Error | ERROR | Missing required clause or keyword |
| SYN004 | Clause Ordering Error | ERROR | SQL clause order does not conform to grammar |
| SYN005 | PARTITIONED BY Syntax Error | ERROR | Invalid partition definition syntax |
| SYN006 | CLUSTERED BY Syntax Error | ERROR | Invalid bucket definition syntax (Hive compat) |
| SYN007 | STORED AS / USING Syntax Error | ERROR | Invalid storage format or data source |
| SYN008 | ROW FORMAT Syntax Error | ERROR | Invalid ROW FORMAT definition (Hive compat) |
| SYN009 | INSERT OVERWRITE Syntax Error | ERROR | Invalid INSERT OVERWRITE structure |
| SYN010 | LATERAL VIEW Syntax Error | ERROR | Invalid LATERAL VIEW structure |
| SYN011 | Subquery Syntax Error | ERROR | Invalid subquery structure |
| SYN012 | CREATE TABLE Structure Error | ERROR | Missing required elements in CREATE TABLE |
| SYN013 | ALTER TABLE Syntax Error | ERROR | Invalid ALTER TABLE action |
| SYN014 | MERGE Syntax Error | ERROR | Invalid MERGE statement structure |
| SYN016 | USING Clause Error | ERROR | Invalid USING data source specification |
| SYN017 | OPTIONS Clause Error | ERROR | Invalid OPTIONS clause format |
| SYN018 | CACHE TABLE Syntax Error | ERROR | Invalid CACHE TABLE structure |
| SYN019 | REFRESH Syntax Error | ERROR | Invalid REFRESH statement structure |
| SYN020 | ADD/LIST JAR Syntax Error | ERROR | Invalid ADD JAR / LIST JAR structure |

### Step 5: Specification Check

Based on AST and Token stream, execute specification check rules. Rules are derived from Spark SQL development specification and MRS Spark best practices.

**Specification Check Rules (29 rules)**:

| Rule ID | Name | Level | Category | Description |
|---------|------|-------|----------|---------------------------------------------------|
| SPEC001 | SELECT * Prohibited | WARNING | Data Operation | Query must specify explicit column list |
| SPEC002 | DELETE/UPDATE without WHERE | ERROR | Data Operation | DML must include WHERE condition |
| SPEC003 | Cartesian Product | ERROR | Data Operation | Multi-table missing JOIN condition |
| SPEC004 | Implicit Type Conversion | WARNING | Data Operation | May cause unexpected results |
| SPEC005 | LIKE Leading Wildcard | WARNING | Data Operation | Cannot use partition pruning |
| SPEC006 | Partition Field Function | WARNING | Data Operation | Function on partition field prevents pruning |
| SPEC007 | INSERT Missing Column List | WARNING | Data Operation | Relies on default column order |
| SPEC008 | Missing Table Comment | INFO | Object Design | Table without comment |
| SPEC009 | Reserved Keyword as Identifier | ERROR | Naming | May cause syntax ambiguity |
| SPEC010 | Column Name Too Long | WARNING | Naming | Column name exceeds 30 characters |
| SPEC012 | FLOAT/DOUBLE for Money | ERROR | Object Design | Use DECIMAL for monetary fields |
| SPEC013 | Too Many Columns | WARNING | Object Design | Table should not exceed 100 columns |
| SPEC014 | Too Many Partition Fields | WARNING | Object Design | Partition fields should not exceed 3 |
| SPEC015 | Missing Column Comment | INFO | Object Design | Column without comment |
| SPEC016 | CASE WHEN Missing ELSE | WARNING | Data Operation | CASE WHEN should include ELSE clause |
| SPEC017 | NULL Value Handling | WARNING | Data Operation | NULL handling in conditions |
| SPEC018 | String 'null' Prohibited | ERROR | Data Operation | Do not use string 'NULL' |
| SPEC019 | JOIN Field Type Mismatch | WARNING | Data Operation | Join fields should have same type |
| SPEC020 | INSERT INTO VALUES | WARNING | SQL Dev | Use INSERT SELECT instead |
| SPEC021 | Subquery Nesting Depth | WARNING | SQL Dev | Subquery should not exceed 3 levels |
| SPEC022 | Partition Pruning Missing | ERROR | Data Operation | Partitioned table query without partition filter |
| SPEC023 | Non-Standard Join Condition | WARNING | Data Operation | JOIN ON should not contain IF/CASE WHEN |
| SPEC024 | CASCADE Usage Warning | WARNING | SQL Dev | Use CASCADE carefully in ALTER TABLE |
| SPEC025 | Prefer USING over STORED AS | WARNING | SQL Dev | Use Spark native USING syntax |
| SPEC026 | CACHE TABLE Recommendation | INFO | SQL Dev | Cache repeatedly accessed tables |
| SPEC027 | BROADCAST Hint Recommendation | INFO | SQL Dev | Use broadcast join for small tables |
| SPEC028 | DROP Missing IF EXISTS | WARNING | SQL Dev | Use IF EXISTS with DROP |
| SPEC029 | ADD JAR Warning | INFO | SQL Dev | Prefer --jars over ADD JAR |

### Step 6: Generate Report

Use the check engine to generate a Markdown format report:

```bash
python ~/.cac/skills/huawei-cloud-mrs-spark-sql-check/scripts/spark_sql_checker.py "<sql_text>" all
```

Report format:

```markdown
# MRS Spark SQL Check Report

**Check Time**: yyyy-mm-ddThh:mm:ss
**Statement Type**: SELECT
**Check Mode**: all

## Summary

| Metric | Value |
|--------|-------|
| Total Rules | 56 |
| Passed | 51 |
| Violations | 5 |
| Errors (ERROR) | 2 |
| Warnings (WARNING) | 2 |
| Infos (INFO) | 1 |

## Syntax Check

### [X] SYN003: Syntax Structure Error
- **Level**: ERROR
- **Position**: Line 1, Column 15
- **Description**: Missing FROM clause
- **Fix Suggestion**: Add FROM table_name

## Specification Check

### [!] SPEC001: SELECT * Prohibited
- **Level**: WARNING
- **Position**: Line 1, Column 8
- **Description**: Query uses SELECT *, should specify explicit column list
- **Fix Suggestion**: Replace SELECT * with specific column list

```

## Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `sql_text` | Required | SQL statement to check | N/A |
| `check_mode` | Optional | Check mode: syntax/spec/all | syntax+spec |

## Output Format

The check report is output in Markdown format, containing:
- **Summary table**: Total rules, passed, violations by level
- **Syntax check section**: Violations from syntax rules (SYN-ERR, SYN001-SYN020)
- **Specification check section**: Violations from specification rules (SPEC001-SPEC029)
- **Large SQL interception section**: Violations from interception rules (INTERCEPT001-INTERCEPT007)
- **Original SQL**: The checked SQL statement

Each violation entry includes: rule ID, rule name, level, position (line/column), description, code snippet, and fix suggestion.

## Core Commands

[spark_sql_checker.py](scripts/spark_sql_checker.py)
[spark_sql_parser.py](scripts/spark_sql_parser.py)
[spark_sql_tokenizer.py](scripts/spark_sql_tokenizer.py)


## Best Practices

1. Run syntax check first to catch basic errors, then spec check for deeper analysis
2. For CREATE TABLE statements, prefer `USING parquet` over `STORED AS PARQUET`
3. Use ORC or Parquet storage format for better compression and query performance
4. Always add partition filter conditions when querying partitioned tables
5. Use `all` mode for comprehensive checking
6. Use `/*+ BROADCAST(small_table) */` hint for small-large table joins

## References

| Document | Description |
|----------|-------------|
| [AST Schema](references/ast-schema.md) | AST node type definitions for Spark SQL |
| [Syntax Rules](rules/syntax_rules.yaml) | 20 syntax check rule definitions |
| [Specification Rules](rules/spec_rules.yaml) | 29 specification check rule definitions |
| [Keywords](rules/keywords.py) | Spark SQL keyword definitions |
| [Grammar Rules](rules/grammar_rules.py) | Statement type grammar definitions |

## Notes

1. **Syntax and specification checks** do not require cluster connection, can run offline
2. Spark-specific syntax checking (USING, OPTIONS, CACHE TABLE, etc.) is based on Spark SQL grammar definitions
3. The check engine includes a custom tokenizer and recursive descent parser, no external SQL parsing libraries required
4. Spark SQL is derived from HiveQL; Hive-compatible syntax (STORED AS, CLUSTERED BY, ROW FORMAT) is also supported
