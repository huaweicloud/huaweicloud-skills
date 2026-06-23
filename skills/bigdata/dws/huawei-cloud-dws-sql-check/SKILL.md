---
name: huawei-cloud-dws-sql-check
description: |
  Comprehensive SQL statement checking for DWS, supporting two check modes:
  1. Syntax Check - Keyword validation, statement structure verification, clause completeness, DWS syntax compatibility based on gram.y grammar definitions
  2. Specification Check - Object design standards, data operation standards, naming conventions based on DWS development design specification
  Built-in custom DWS SQL tokenizer (594 keywords) and recursive descent parser supporting 160+ statement types.
  Applicable when users need SQL quality review, syntax validation, or specification compliance checking.
  触发词："SQL检查"、"SQL规范"、"SQL审计"、"SQL语法"、"SQL优化"、"检查SQL"、"SQL review"
tags: [huawei-cloud, dws, sql, check, lint]
---

# DWS SQL Check Skill

You are a DWS SQL specification checking expert, responsible for comprehensive SQL statement checking for DWS. You have a custom-built DWS SQL tokenizer and recursive descent parser that can precisely identify DWS-specific syntax.

## Overview

**Architecture**: This skill uses a three-stage pipeline: Tokenizer (lexical analysis) → Parser (syntax analysis) → Rule Engine (syntax + specification checking) → Report Generation.

**Applicable Scenarios**:
- Validate SQL syntax before executing on DWS cluster
- Review SQL statements against DWS development design specification
- Check DWS-specific syntax (DISTRIBUTE BY, PARTITION BY, MERGE, etc.)
- Identify potential performance anti-patterns in SQL statements

**Typical Use Cases**:
- "Check this SQL: SELECT * FROM t1"
- "Does this CREATE TABLE follow DWS specification?"
- "Validate the syntax of this MERGE statement"
- "Review my SQL for specification compliance"
- "Check if my SQL uses DWS-specific syntax correctly"

## Check Modes

| Mode | Dependency | Description |
|------|------------|-------------|
| **syntax** | None | Syntax check: keyword validity, statement structure, clause completeness, DWS syntax compatibility |
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
python ~/.cac/skills/huawei-cloud-dws-sql-check/scripts/dws_sql_tokenizer.py "<sql_text>"
```

The tokenizer supports:
- All 594 DWS keywords (4 categories: RESERVED=91, COL_NAME=68, TYPE_FUNC_NAME=28, UNRESERVED=407)
- DWS-specific tokens: `ORA_JOINOP` (Oracle (+) join), `TYPECAST` (::), `HINT` (/*+ ... */)
- Literals: strings, integers, floats, bit strings, hex strings
- Parameter references: $1, $2...
- Comment skipping (-- single line, /* */ multi-line, but /*+ hint */ preserved as HINT token)

### Step 3: Parsing

Run the parser to generate AST and detect syntax errors.

```bash
python ~/.cac/skills/huawei-cloud-dws-sql-check/scripts/dws_sql_parser.py "<sql_text>"
```

The parser supports major statement types:
- **DML**: SELECT, INSERT, UPDATE, DELETE, MERGE
- **DDL**: CREATE TABLE, ALTER TABLE, DROP, CREATE INDEX, CREATE VIEW, CREATE MATERIALIZED VIEW, TRUNCATE
- **DCL**: GRANT, REVOKE
- **TCL**: BEGIN, COMMIT, ROLLBACK
- **UTILITY**: EXPLAIN, COPY, VACUUM, SET, SHOW

DWS-specific syntax:
- `DISTRIBUTE BY {HASH|MODULO|REPLICATION|ROUNDROBIN}`
- `PARTITION BY {RANGE|LIST|INTERVAL}`
- `TO {NODE|GROUP}`
- `COMPRESS {YES|NO}`
- `TIMECAPSULE TABLE ... TO BEFORE {DROP|TRUNCATE}`
- `EXPLAIN {PERFORMANCE|WARMUP|PLAN}`
- `INSERT OVERWRITE INTO`
- `REPLACE INTO`
- `ON DUPLICATE KEY UPDATE`
- `MERGE INTO ... USING ... ON ... WHEN MATCHED/NOT MATCHED`
- `CREATE RESOURCE POOL / WORKLOAD GROUP / REDACTION POLICY / OUTLINE`
- Oracle (+) outer join
- Optimizer Hints (/*+ ... */)

### Step 4: Syntax Check

Based on tokenization and parsing results, execute syntax check rules.

**Syntax Check Rules (19 rules)**:

| Rule ID | Name | Level | Description |
|---------|------|-------|-------------|
| SYN-ERR | Lexical Error | ERROR | Unrecognized characters in SQL text |
| SYN001 | Invalid Keyword | ERROR | Keyword not supported by DWS |
| SYN002 | Reserved Keyword as Identifier | ERROR | Reserved keyword used as identifier without quoting |
| SYN003 | Syntax Structure Error | ERROR | Missing required clause or keyword |
| SYN004 | Clause Ordering Error | ERROR | SQL clause order does not conform to grammar |
| SYN005 | DISTRIBUTE BY Syntax Error | ERROR | Invalid distribution strategy |
| SYN006 | PARTITION Syntax Error | ERROR | Invalid partition definition syntax |
| SYN007 | MERGE Syntax Error | ERROR | Incomplete MERGE statement structure |
| SYN008 | EXPLAIN Syntax Error | ERROR | Invalid EXPLAIN option |
| SYN009 | COMPRESS Syntax Error | ERROR | Invalid COMPRESS option |
| SYN010 | TIMECAPSULE Syntax Error | ERROR | Invalid TIMECAPSULE statement structure |
| SYN011 | RESOURCE POOL Syntax Error | ERROR | Invalid CREATE RESOURCE POOL structure |
| SYN012 | WORKLOAD GROUP Syntax Error | ERROR | Invalid CREATE WORKLOAD GROUP structure |
| SYN013 | REDACTION POLICY Syntax Error | ERROR | Invalid CREATE REDACTION POLICY structure |
| SYN014 | OUTLINE Syntax Error | ERROR | Invalid CREATE OUTLINE structure |
| SYN015 | TO NODE/GROUP Syntax Error | ERROR | Invalid TO NODE/GROUP clause syntax |
| SYN016 | INSERT OVERWRITE Syntax Error | ERROR | Invalid INSERT OVERWRITE structure |
| SYN017 | ON DUPLICATE KEY Syntax Error | ERROR | Invalid ON DUPLICATE KEY UPDATE clause |
| SYN018 | Oracle (+) Join Syntax Error | WARNING | Incorrect use of (+) operator |
| SYN019 | Optimizer Hint Syntax Error | WARNING | Invalid hint format |

### Step 5: Specification Check

Based on AST and Token stream, execute specification check rules. Rules are derived from gram.y grammar definitions and DWS development design specification.

**Specification Check Rules (40 rules)**:

| Rule ID | Name | Level | Category | Source | Description |
|---------|------|-------|----------|--------|-------------|
| SPEC001 | Missing DISTRIBUTE BY | ERROR | Object Design | Rule 2.9 | CREATE TABLE without distribution strategy |
| SPEC002 | Missing Primary Key | INFO | Object Design | - | Table without primary key constraint |
| SPEC003 | SELECT * Prohibited | ERROR | Data Operation | Rec 3.14 | Query must specify explicit column list |
| SPEC004 | DELETE/UPDATE without WHERE | ERROR | Data Operation | - | DML must include WHERE condition |
| SPEC005 | NOT IN Subquery | WARNING | Data Operation | - | Recommend NOT EXISTS instead |
| SPEC006 | DISTINCT Performance | INFO | Data Operation | - | DISTINCT may impact performance |
| SPEC007 | Implicit Type Conversion | WARNING | Data Operation | Rule 3.9 | May cause index invalidation |
| SPEC008 | LIKE Leading Wildcard | WARNING | Data Operation | - | Cannot use index |
| SPEC009 | OR Condition | INFO | Data Operation | - | May impact execution plan |
| SPEC010 | IN List Too Long | WARNING | Data Operation | - | >100 values recommend temp table |
| SPEC011 | FROM Subquery | INFO | Data Operation | - | Recommend CTE instead |
| SPEC012 | Cartesian Product | ERROR | Data Operation | Rule 3.8 | Multi-table missing JOIN condition |
| SPEC013 | Oracle Outer Join | INFO | Data Operation | - | Recommend standard JOIN |
| SPEC014 | INSERT Missing Column List | WARNING | Data Operation | - | Relies on default column order |
| SPEC015 | Missing Table Comment | INFO | Object Design | - | Table without comment |
| SPEC016 | Table Naming Convention | WARNING | Naming | - | Should use lowercase with underscores |
| SPEC017 | Column Naming Convention | WARNING | Naming | - | Should use lowercase with underscores |
| SPEC018 | Reserved Keyword as Identifier | ERROR | Naming | - | May cause syntax ambiguity |
| SPEC019 | Distribution Key Column Not Found | WARNING | Object Design | - | Distribution key should be actual table column |
| SPEC020 | Partition Key Same as Distribution Key | INFO | Object Design | - | May cause data skew |
| SPEC021 | REPLICATION on Large Table | WARNING | Object Design | - | Large tables should not use REPLICATION |
| SPEC022 | ROUNDROBIN Performance | INFO | Object Design | Rule 2.9 | Does not support local join |
| SPEC023 | Custom TABLESPACE | WARNING | Object Design | Rule 2.8 | Except column-store v3 tables |
| SPEC024 | Missing Storage Orientation | WARNING | Object Design | Rule 2.10 | Recommend explicit orientation |
| SPEC025 | Row-store COMPRESS Prohibited | ERROR | Object Design | Rule 2.10 | Row-store compressed tables prohibited |
| SPEC026 | Large Table Should Have Partition | INFO | Object Design | Rule 2.11 | Improve query and governance efficiency |
| SPEC027 | Column Should Have NOT NULL | INFO | Object Design | Rec 2.12 | Optimizer can leverage NOT NULL |
| SPEC028 | Avoid SERIAL Types | WARNING | Object Design | Rec 2.13 | SERIAL causes GTM pressure |
| SPEC029 | Index Count > 5 | WARNING | Object Design | Rule 2.14 | Requires cluster: query pg_indexes |
| SPEC030 | DROP Should Use IF EXISTS | WARNING | SQL Dev | Rule 3.2 | Prevent error when object not found |
| SPEC031 | Multi-VALUES Use COPY | WARNING | SQL Dev | Rule 3.3 | INSERT VALUES inefficient |
| SPEC032 | Column-store Real-time INSERT | WARNING | SQL Dev | Rec 3.4 | Small CU bloat |
| SPEC033 | Column-store UPDATE/DELETE | WARNING | SQL Dev | Rec 3.6 | CU bloat + deadlock risk |
| SPEC034 | Non-pushdown SQL Prohibited | ERROR | SQL Dev | Rule 3.7 | Requires cluster: EXPLAIN analysis |
| SPEC035 | Function on Filter Column | WARNING | SQL Dev | Rec 3.10 | Affects statistics accuracy |
| SPEC036 | Row-store Large Table COUNT | WARNING | SQL Dev | Rule 3.12 | Full table scan I/O cost |
| SPEC037 | Query Should Use LIMIT | INFO | SQL Dev | Rec 3.13 | Avoid oversized result sets |
| SPEC038 | Caution with WITH RECURSIVE | WARNING | SQL Dev | Rec 3.15 | Ensure termination condition |
| SPEC039 | Use Schema Prefix | INFO | SQL Dev | Rec 3.16 | Avoid search_path issues |
| SPEC040 | View Nesting Depth ≤ 3 | INFO | Object Design | Rec 2.16 | Requires cluster: query view dependencies |

### Step 6: Generate Report

Use the check engine to generate a Markdown format report:

```bash
python ~/.cac/skills/huawei-cloud-dws-sql-check/scripts/dws_sql_checker.py "<sql_text>" all
```

Report format:

```markdown
# DWS SQL Check Report

**Check Time**: 2026-06-18T10:00:00
**Statement Type**: SELECT
**Check Mode**: all

## Summary

| Metric | Value |
|--------|-------|
| Total Rules | 41 |
| Passed | 38 |
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

## Parameters

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `sql_text` | Required | SQL statement to check | N/A |
| `check_mode` | Optional | Check mode: syntax/spec/all | syntax+spec |

## Output Format

The check report is output in Markdown format, containing:
- **Summary table**: Total rules, passed, violations by level
- **Syntax check section**: Violations from syntax rules (SYN-ERR, SYN001-SYN019)
- **Specification check section**: Violations from specification rules (SPEC001-SPEC040)
- **Original SQL**: The checked SQL statement

Each violation entry includes: rule ID, rule name, level, position (line/column), description, code snippet, and fix suggestion.

## Quick Check Command

For simple SQL checks, run directly:

```bash
python ~/.cac/skills/huawei-cloud-dws-sql-check/scripts/dws_sql_checker.py "<sql_text>" [syntax|spec|all]
```

Output is in JSON format. For Markdown format report, call in Python:

```python
from dws_sql_checker import check_sql_markdown
report = check_sql_markdown("SELECT * FROM t1", "all")
print(report)
```

## Best Practices

1. Run syntax check first to catch basic errors, then spec check for deeper analysis
2. For CREATE TABLE statements, always include DISTRIBUTE BY to avoid SPEC001
3. Use `all` mode for comprehensive checking
4. Rules marked with `requires_mcp: true` or "Requires cluster" (SPEC029, SPEC034, SPEC040) need cluster connection and are skipped in static mode

## References

| Document | Description |
|----------|-------------|
| [AST Schema](references/ast_schema.md) | AST node type definitions for DWS SQL |
| [Syntax Rules](rules/syntax_rules.yaml) | 19 syntax check rule definitions |
| [Specification Rules](rules/spec_rules.yaml) | 40 specification check rule definitions |
| [Performance Rules](rules/perf_rules.yaml) | 11 performance check rule definitions (requires cluster) |
| [Keywords](rules/keywords.py) | 594 DWS SQL keyword definitions |
| [Grammar Rules](rules/grammar_rules.py) | 160+ statement type grammar definitions |

## Notes

1. **Syntax and specification checks** do not require cluster connection, can run offline
2. **Rules marked "Requires cluster"** (SPEC029, SPEC034, SPEC040) are skipped in static mode
3. **Performance rules** (PERF001-PERF011) are defined in rules/perf_rules.yaml but require cluster connection for execution
4. DWS-specific syntax checking (DISTRIBUTE BY, PARTITION BY, MERGE, etc.) is based on gram.y grammar definitions
5. The check engine includes a custom tokenizer and recursive descent parser, no external SQL parsing libraries required
