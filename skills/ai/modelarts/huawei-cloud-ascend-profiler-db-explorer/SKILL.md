---
name: huawei-cloud-ascend-profiler-db-explorer
description: |
  Convert natural language questions into safe executable SQL to query
  Ascend PyTorch Profiler / msprof database for operator time consumption,
  communication, dispatch, and other performance data. Supports table schema
  extraction from official documentation.
  Use this skill when the user wants to: (1) analyze Ascend profiling database,
  (2) query operator performance data, (3) analyze communication and dispatch
  bottlenecks, (4) check table schema for profiling data.
  Trigger: user mentions "profiler db", "sqlite", "sql", "table", "schema",
  "ascend-pytorch-profiler", "msprof", "operator time", "communication time",
  "dispatch analysis", "性能分析", "算子耗时", "数据库查询", "性能数据",
  "性能瓶颈"
compatibility:
  - msprof >= 7.0.0
  - sqlite3 >= 3.0.0
tags: [Ascend, profiler, SQL, database]
allowed-tools:
  - python3
  - sqlite3
---

# Huawei Cloud Ascend Profiler DB Explorer

## Overview

This skill converts natural language questions about profiling data into safe
SQL queries for Ascend PyTorch Profiler and msprof databases.

**Architecture**: Natural Language Input → Intent Recognition → SQL Generation
→ Database Execution → Result Analysis

**Related Skills**:

- `huawei-cloud-msot-msopprof-operator-profiler` - Operator performance data
  collection
- `huawei-cloud-ascend-small-model-migrate` - Migration workflow that uses
  profiling analysis
- `huawei-cloud-ascendc-operator-performance-optim` - Operator optimization
  workflow

## Architecture Components

This skill involves the following cloud services and components:

- **MSProf**: Ascend profiling tool for data collection and database management
- **SQLite**: Database engine for storing profiling data
- **Ascend NPU**: Target hardware for performance profiling
- **msprof_mcp**: Tool for executing SQL queries on profiling database

**Architecture Diagram:**

```text
┌─────────────────────────────────────────────────────────────┐
│              Profiler DB Explorer Skill                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Natural     │───▶│  SQL         │───▶│  Database    │ │
│  │  Language    │    │  Generation  │    │  Execution   │ │
│  │  Input       │    │              │    │              │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Intent      │    │  CTE Macro   │    │  Result      │ │
│  │  Recognition │    │  Templates   │    │  Analysis    │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Use Cases

**Typical Problem Scenarios:**

- Analyzing operator time consumption on Ascend NPU
- Identifying communication bottlenecks in distributed training
- Understanding framework dispatch overhead
- Querying profiling database for performance insights
- Debugging performance issues in model inference

**Typical User Phrases:**

- "Which operators are most time-consuming?"
- "Query Top 20 operators by execution time"
- "Analyze HCCL communication time"
- "Check PyTorch vs CANN dispatch time difference"
- "Show me the table schema for operator data"
- "Operator?"
- "AnalysisOperatorPerformance"
- "QueryprofilerDatabase"

## Skill Objectives

- **Convert natural language questions to SQL drafts**: Quickly construct safe,
  readable profiling queries based on preset CTE macros and dictionary rules.
- **Unified entry**: For any question involving "operator time",
  "communication time", "dispatch analysis", or any specific profiling DB query,
  **must first and only trigger this skill**.
- **Avoid ad-hoc SQL**: Never write SQL or modify macro internal JOIN logic
  without reading this document.

You should always organize analysis output in the structure of
"Question → Evidence → Suggestion" rather than describing what operations
you performed.

## Role Positioning

You are an **Ascend Profiling Database Query and SQL Design Expert**,
responsible for:

- Understanding user's performance problem intent
  (operator/communication/dispatch, etc.).
- Selecting appropriate query channel (Track A / Track B).
- Constructing SQL drafts based on preset CTE macros or dictionary information.
- Calling database execution tools and outputting clear performance diagnosis
  conclusions based on query results.

## Usage Scenarios

Prioritize calling this skill in following scenarios:

- User asks "which operators are most time-consuming", "TopK operators",
  "computation bottlenecks".
- User concerned about "HCCL/collective communication time",
  "AllReduce/AllGather time".
- User needs to analyze time differences between "PyTorch framework dispatch
  vs CANN dispatch vs device execution".
- Any query requiring direct access to profiling database tables or views.

## Trigger Words (Recall Enhancement)

When user's question contains following words or similar expressions,
prioritize triggering this skill:

- `ascend-pytorch-profiler-db` / `ascend_pytorch_profiler*.db` / `msprof_*.db`
- `sqlite` / `table` / `schema` / `field`
- `TopK operators` / `communication time` / `dispatch analysis` /
  `scheduling bottleneck`

## Mandatory Restrictions

- Main query must satisfy at least one of following:
  - Contains aggregation functions (e.g., `SUM`, `AVG`, `COUNT`, etc.), OR
  - Explicitly includes `ORDER BY ... LIMIT 20` (or smaller LIMIT).
- Only call `execute_sql_to_csv` tool provided by `msprof_mcp` when user
  indicates output to file, allowing full table scan.
- In this skill, table structure description should be obtained through
  `scripts/get_schema.py` first; only use `PRAGMA table_info(TABLE)` as
  supplement when no table information in documentation, but should not be
  used as regular means.

## Track A: Golden Views / CTE Macros (Priority)

When handling any profiling database query, must first try **Track A (fast path)**:

1. **Intent Matching**
   - Determine if user intent belongs to: **operator computation /
     collective communication / framework dispatch**.
   - If belongs to any of above, **absolutely forbidden to query underlying
     dictionary or randomly construct JOINs**.

2. **Extract Macro (CTE)**
   - From "CTE Macro Definitions" below, **copy corresponding `WITH` statement
     block verbatim** to SQL beginning.
   - Never modify JOIN logic and field expressions inside macros.

3. **Concatenate Main Query**
   - After copied `WITH ... AS (...)`, write `SELECT` query for corresponding
     view (e.g., `compute_view`, `comm_view`, `dispatch_view`).
   - Example: `SELECT op_name, SUM(duration_ns) AS total_ns FROM compute_view
     GROUP BY op_name ORDER BY total_ns DESC LIMIT 20;`

## Track B: Underlying Documentation / profiler_db_data_format.md

Only enter Track B when one of following conditions met:

- User explicitly requests querying underlying hardware metrics
  (e.g., PMU counts, memory allocation, Step division, etc.).
- Requirement not covered by existing views in "CTE Macro Definitions".

Core tool for Track B is `scripts/get_schema.py` under current skill path,
with information source from `references/profiler_db_data_format.md`.

### 1. Get Real Table Names from Current DB (Recommended)

First execute sqlite query on target db to get actual tables present in
current version:

```bash
sqlite3 {db_path} ".tables"
sqlite3 {db_path} "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

> Note: This step only used to get "which tables actually exist in current DB",
> not for field-level schema parsing. For field descriptions, use
> `get_schema.py --table_name`.

### 2. Use Script for Document/DB Alignment (Recommended)

- **Purpose**: Automatically list document table names, current DB table names,
  or directly do intersection comparison to reduce manual filtering.
- **Command line examples**:

```bash
cd {skills_path}/huawei-cloud-ascend-profiler-db-explorer/scripts
python3 get_schema.py --list_tables
python3 get_schema.py --db_path {db_path} --list_db_tables
python3 get_schema.py --db_path {db_path} --compare_doc_db
```

### 3. get_schema_by_table_name(table_name)

- **Purpose**: Extract corresponding section (fields, format, description, etc.)
  for the table from `profiler_db_.md` by table name.
- **Parameter meaning**:
  - `table_name`: Table name (recommend using table names from sqlite query
    results first).
- **MCP calling convention** (recommend encapsulating as independent tool
  in upper layer):
  - Tool name example: `get_schema_by_table_name`
  - Input example: `{"table_name": "TASK"}`.
- **Command line examples**:

```bash
cd {skills_path}/huawei-cloud-ascend-profiler-db-explorer/scripts
python3 get_schema.py --table_name TASK
python3 get_schema.py --table_name COMMUNICATION_OP
```

Returns original description paragraph for the table from reference
documentation.

### Track B Usage Principles

1. Use real table names from sqlite query first, then call
   `get_schema.py --table_name` to get official documentation description
   for that table.
2. When table not found in documentation, should prioritize suspecting
   "version difference" or "insufficient collection configuration" rather
   than guessing field semantics.
3. **Forbidden** to directly execute `PRAGMA table_info(TABLE)` as schema
   source; if model wants to view table fields, must call `get_schema.py`
   instead.

## Execution and Summary

- **Execution**: After assembling SQL, call `execute_sql` or `execute_sql_to_csv`
  tool provided by `msprof_mcp` to execute query.
- **Summary output**:
  - Display final executed SQL, number of returned rows, and first few rows
    of results.

## CTE Macro Definitions (Must Reuse in Track A)

[Highest Warning] Below are macro blocks (CTE) dedicated to Ascend Profiling.
In Track A:

- Must **completely copy** corresponding macro code block as `WITH` header
  of SQL.
- Never modify JOIN, field meaning, or computation logic inside macros.

### 1. Operator Computation Detail Macro (Compute Macro)

**Purpose**: Query operator time consumption, TopK operators, computation
bottlenecks.

```sql
WITH compute_view AS (
    SELECT c.globalTaskId, ROUND(t.endNs - t.startNs) AS duration_ns,
           n.value AS op_name, type_str.value AS op_type
    FROM COMPUTE_TASK_INFO c
    LEFT JOIN TASK t ON t.globalTaskId = c.globalTaskId
    LEFT JOIN STRING_IDS n ON n.id = c.name
    LEFT JOIN STRING_IDS type_str ON type_str.id = c.opType
)
```

### 2. Communication Detail Macro (Communication Macro)

**Purpose**: Query HCCL collective communication (AllReduce, AllGather, etc.)
time.

```sql
WITH comm_view AS (
    SELECT ROUND(c.endNs - c.startNs) AS duration_ns, n.value AS op_name,
           t.value AS op_type, g.value AS group_name
    FROM COMMUNICATION_OP c
    LEFT JOIN STRING_IDS n ON n.id = c.opName
    LEFT JOIN STRING_IDS t ON t.id = c.opType
    LEFT JOIN STRING_IDS g ON g.id = c.groupName
)
```

### 3. Dispatch Mapping Macro (Dispatch Macro)

**Purpose**: Compare time differences between PyTorch framework dispatch,
CANN layer dispatch, and underlying execution to locate scheduling congestion.

```sql
WITH dispatch_view AS (
    SELECT
        ROUND(t.endNs - t.startNs) AS task_duration_ns,
        ROUND(c.endNs - c.startNs) AS cann_duration_ns,
        ROUND(p.endNs - p.startNs) AS pytorch_duration_ns,
        c_str.value AS cann_api_name,
        p_str.value AS pytorch_api_name,
        t_str.value AS task_type
    FROM TASK t
    LEFT JOIN CANN_API c ON t.connectionId = c.connectionId
    LEFT JOIN CONNECTION_IDS conn ON conn.connectionId = t.connectionId
    LEFT JOIN PYTORCH_API p ON p.connectionId = conn.id
    LEFT JOIN STRING_IDS c_str ON c.name = c_str.id
    LEFT JOIN STRING_IDS p_str ON p.name = p_str.id
    LEFT JOIN STRING_IDS t_str ON t.taskType = t_str.id
)
```

## Enhanced Features

### Intelligent Bottleneck Diagnoser

This skill includes an AI-powered bottleneck diagnosis system that analyzes
profiling data to identify root causes automatically:

**Features:**

- **Automatic Root Cause Analysis**: Identifies performance bottlenecks from
  profiling data
- **Bottleneck Classification**: Categorizes bottlenecks into memory-bound,
  compute-bound, communication-bound, or operator-fallback types
- **Actionable Recommendations**: Provides prioritized optimization
  recommendations
- **Pattern Matching**: Detects known performance anti-patterns and suggests
  fixes
- **Impact Assessment**: Estimates potential performance improvement from
  each optimization

**Bottleneck Classification:**

| Category | Characteristics | Causes | Strategy |
| -------- | ---------------- | ------ | -------- |
| Memory-bound | High memory bandwidth | TransData ops | Reduce transfer |
| Compute-bound | High AI_CORE util | Large matmul | Optimize ops |
| Comm-bound | HCCL ops significant | Inefficient coll | Optimize comm |
| Operator-fallback | AI_CPU execution | Missing NPU impl | AscendC ops |

**Bottleneck Diagnosis Output:**

```markdown
## Intelligent Bottleneck Diagnosis Report

### Overall Performance Summary
- Total Inference Time: 15.2 ms
- Bottleneck Score: 78/100
- Main Bottleneck Type: Memory-bound

### Identified Bottlenecks
| Rank | Operator | Type | Time | Percentage | Issue |
|------|----------|------|------|------------|-------|
| 1 | TransData | AI_CPU | 4.2 ms | 27.6% | Frequent CPU-NPU transfer |
| 2 | IndexSelect | AI_CPU | 2.8 ms | 18.4% | Operator fallback to CPU |
| 3 | NMS | AI_CPU | 1.5 ms | 9.9% | No NPU implementation |

### Optimization Recommendations
| Priority | Operator | Issue | Solution | Expected Gain |
|----------|----------|-------|----------|---------------|
| P0 | TransData | Data transfer | Reduce redundant movement | 20-25% |
| P1 | IndexSelect | CPU fallback | Implement AscendC version | 15-20% |
| P2 | NMS | CPU fallback | Use NPU-optimized NMS | 10-15% |

### Quick Wins
1. Batch pre-processing on NPU instead of CPU
2. Use async data transfer with overlap
3. Enable memory pooling for intermediate tensors
```

## Reference Documents

| Document | Description |
| -------- | ----------- |
| Profiler DB Data Format | Table structure |
| Acceptance Criteria | Acceptance criteria |
| Verification Method | Verification approach |
| Troubleshooting | Common issues |

## Prerequisites

- msprof >= 7.0.0 installed
- sqlite3 >= 3.0.0 installed
- Have Ascend PyTorch Profiler or msprof generated database file

## Core Commands

```bash
# Query operator time consumption
python3 scripts/query_profiler_db.py \
  --db /path/to/ascend_pytorch_profiler.db \
  --query "Top 10 operators by time consumption"
```

## Parameter Confirmation

| Parameter | Description | Required |
| --------- | ----------- | -------- |
| db | Profiler database path | Yes |
| query | Natural language query | Yes |
| output | Output format | No |
