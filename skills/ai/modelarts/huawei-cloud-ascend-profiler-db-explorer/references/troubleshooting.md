# Troubleshooting

## 1. Database Issues

### Issue: Database file not found

**Symptom:** `Error: unable to open database`

**Solution:**
```bash
# Find profiling database
find . -name "*.db" -o -name "msprof_*.db"

# Check file permissions
ls -la profiling.db
chmod 644 profiling.db
```

### Issue: Database locked

**Symptom:** `Error: database is locked`

**Solution:**
```bash
# Close other connections
# Wait for other processes to finish
# Or use read-only mode
sqlite3 -readonly profiling.db "SELECT 1;"
```

### Issue: Invalid database format

**Symptom:** `Error: file is not a database`

**Solution:**
```bash
# Check file type
file profiling.db

# May need to use correct database from profiling output
ls -la OPPROF_*/profiling.db
```

## 2. Schema Query Issues

### Issue: Table not found

**Symptom:** `Error: no such table`

**Solution:**
```bash
# List available tables first
sqlite3 profiling.db ".tables"

# Check actual table names
sqlite3 profiling.db "SELECT name FROM sqlite_master WHERE type='table';"

# Verify get_schema.py table list
python3 scripts/get_schema.py --list_tables
```

### Issue: Column not found

**Symptom:** `Error: no such column`

**Solution:**
```bash
# Get table schema
sqlite3 profiling.db ".schema TABLE_NAME"

# Use get_schema.py for reference
python3 scripts/get_schema.py --table_name TABLE_NAME

# Check exact column names
sqlite3 profiling.db "PRAGMA table_info(TABLE_NAME);"
```

## 3. Query Execution Issues

### Issue: Query returns no results

**Possible Causes:**
1. No matching data
2. WHERE condition too restrictive
3. JOIN condition incorrect

**Solution:**
```bash
# Test with simpler query first
sqlite3 profiling.db "SELECT COUNT(*) FROM TASK;"

# Check data exists
sqlite3 profiling.db "SELECT * FROM TASK LIMIT 1;"

# Verify JOIN keys
sqlite3 profiling.db "SELECT COUNT(*) FROM COMPUTE_TASK_INFO c JOIN TASK t ON c.globalTaskId = t.globalTaskId;"
```

### Issue: Query too slow

**Solution:**
```bash
# Add LIMIT
SELECT ... LIMIT 100;

# Use index hints if available
EXPLAIN QUERY PLAN SELECT ...

# Reduce date range
WHERE timestamp BETWEEN '2024-01-01' AND '2024-01-02'
```

## 4. SQL Generation Issues

### Issue: Generated SQL syntax error

**Solution:**
```bash
# Validate SQL syntax
sqlite3 profiling.db "EXPLAIN QUERY PLAN <your_sql>;"

# Check for typos
# Verify table and column names match schema
```

### Issue: Missing aggregation

**Solution:**
```bash
# Ensure GROUP BY is used with aggregate functions
SELECT op_name, SUM(duration_ns)  -- Need GROUP BY
FROM compute_view
GROUP BY op_name;
```

### Issue: Missing LIMIT

**Solution:**
```bash
# Add LIMIT to prevent large result sets
SELECT ...
ORDER BY total_ns DESC
LIMIT 20;
```

## 5. Performance Issues

### Issue: Full table scan

**Solution:**
```bash
# Check query plan
EXPLAIN QUERY PLAN SELECT ...

# Use appropriate indexes
# Limit date range
```

### Issue: Memory issues with large results

**Solution:**
```bash
# Increase LIMIT
# Use pagination
# Process in batches
```

## Quick Diagnostic Commands

```bash
# Check database
file *.db
sqlite3 profiling.db ".tables"

# Check table size
sqlite3 profiling.db "SELECT COUNT(*) FROM TASK;"

# Test simple query
sqlite3 profiling.db "SELECT 1;"

# Get schema
python3 scripts/get_schema.py --table_name TASK
```

## Common SQL Patterns

```sql
-- Top K operators by time
WITH compute_view AS (
    SELECT c.globalTaskId, ROUND(t.endNs - t.startNs) AS duration_ns, n.value AS op_name
    FROM COMPUTE_TASK_INFO c
    LEFT JOIN TASK t ON t.globalTaskId = c.globalTaskId
    LEFT JOIN STRING_IDS n ON n.id = c.name
)
SELECT op_name, SUM(duration_ns) AS total_ns, COUNT(*) AS call_count
FROM compute_view
GROUP BY op_name
ORDER BY total_ns DESC
LIMIT 20;

-- Communication time
WITH comm_view AS (
    SELECT ROUND(c.endNs - c.startNs) AS duration_ns, n.value AS op_name
    FROM COMMUNICATION_OP c
    LEFT JOIN STRING_IDS n ON n.id = c.opName
)
SELECT op_name, SUM(duration_ns) AS total_ns
FROM comm_view
GROUP BY op_name
ORDER BY total_ns DESC
LIMIT 10;
```
