# Acceptance Criteria

## Functional Acceptance Criteria

### 1. SQL Generation

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-1.1 | Should generate valid SQL from natural language | Execute and verify results |
| AC-1.2 | Should use Track A CTE macros for common queries | Check CTE usage |
| AC-1.3 | Should follow security rules (aggregation/LIMIT) | Verify query structure |

### 2. Track Selection

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-2.1 | Should select Track A for common queries | Check intent matching |
| AC-2.2 | Should select Track B for edge cases | Verify conditions met |
| AC-2.3 | Should explain track selection reasoning | Check output explanation |

### 3. Schema Query

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-3.1 | Should use get_schema.py for table info | Check script usage |
| AC-3.2 | Should handle missing tables gracefully | Verify error handling |
| AC-3.3 | Should document table structure | Check reference updates |

### 4. Query Execution

| Criteria | Description | Verification Method |
|----------|-------------|---------------------|
| AC-4.1 | Should execute SQL via msprof_mcp tool | Verify tool call |
| AC-4.2 | Should present results clearly | Check output format |
| AC-4.3 | Should limit output rows | Verify LIMIT usage |

## Correct/Error Pattern Comparison

### SQL Generation

**Correct:** Include aggregation and LIMIT
```sql
SELECT op_name, SUM(duration_ns) AS total_ns
FROM compute_view
GROUP BY op_name
ORDER BY total_ns DESC
LIMIT 20;
```

**Error:** Missing aggregation or LIMIT
```sql
SELECT op_name, duration_ns  -- No aggregation
FROM compute_view;
-- Missing LIMIT can return too many rows
```

### CTE Macro Usage

**Correct:** Use Track A macros for common queries
```sql
-- Operator time query
WITH compute_view AS (
    SELECT c.globalTaskId, ROUND(t.endNs - t.startNs) AS duration_ns, ...
    FROM COMPUTE_TASK_INFO c
    LEFT JOIN TASK t ON ...
)
SELECT op_name, SUM(duration_ns) AS total_ns
FROM compute_view
GROUP BY op_name ORDER BY total_ns DESC LIMIT 20;
```

**Error:** Ignore Track A for common queries
```sql
-- Rewriting Track A logic from scratch is error-prone
SELECT op_name, SUM(ROUND(t.endNs - t.startNs)) AS total_ns
FROM TASK t, COMPUTE_TASK_INFO c, STRING_IDS n
WHERE ...  -- Complex manual join
```

### Schema Reference

**Correct:** Use get_schema.py
```bash
python3 scripts/get_schema.py --table_name TASK
```

**Error:** Use PRAGMA as primary source
```bash
sqlite3 profiling.db "PRAGMA table_info(TASK)"  # Not recommended as primary
```

## Non-Functional Acceptance Criteria

| Criteria | Description | Threshold |
|----------|-------------|-----------|
| NAC-1.1 | SQL generation time | < 10 seconds |
| NAC-1.2 | Query execution time | < 60 seconds |
| NAC-1.3 | Result accuracy | > 95% |

## Test Cases Summary

### Positive Test Cases

1. TC-001: TopK operator query (Track A)
2. TC-002: Communication time query (Track A)
3. TC-003: Dispatch analysis query (Track A)
4. TC-004: Custom table schema query (Track B)
5. TC-005: Cross-table join query

### Negative Test Cases

1. TC-N01: Query without aggregation
2. TC-N02: Query without LIMIT
3. TC-N03: Using PRAGMA instead of get_schema.py
4. TC-N04: Ignoring Track A for common query
5. TC-N05: Invalid table name in query
