# Verification Methods

## Prerequisite Verification

### 1. Verify Database Files

```bash
# Check profiling database exists
ls -la *.db
ls -la msprof_*.db

# Verify database format
file profiling.db
```

### 2. Verify sqlite3 CLI

```bash
# Check sqlite3 installation
sqlite3 --version

# Test basic query
sqlite3 profiling.db "SELECT 1;"
```

### 3. Verify get_schema.py Script

```bash
# Check script exists
ls -la scripts/get_schema.py

# Test script help
python3 scripts/get_schema.py --help
```

## Functional Verification

### 1. List Available Tables

```bash
# Method 1: Using sqlite3
sqlite3 profiling.db ".tables"

# Method 2: Using get_schema.py
python3 scripts/get_schema.py --list_tables

# Method 3: Using SQL
sqlite3 profiling.db "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
```

### 2. Query Table Schema

```bash
# Get schema for specific table
python3 scripts/get_schema.py --table_name TASK

# Compare with actual database
python3 scripts/get_schema.py --db_path profiling.db --compare_doc_db
```

### 3. Execute Query

```bash
# Using sqlite3 CLI for testing
sqlite3 profiling.db "
WITH compute_view AS (
    SELECT c.globalTaskId, ROUND(t.endNs - t.startNs) AS duration_ns, n.value AS op_name
    FROM COMPUTE_TASK_INFO c
    LEFT JOIN TASK t ON t.globalTaskId = c.globalTaskId
    LEFT JOIN STRING_IDS n ON n.id = c.name
)
SELECT op_name, SUM(duration_ns) AS total_ns
FROM compute_view
GROUP BY op_name
ORDER BY total_ns DESC
LIMIT 20;
"

# Save results to CSV
sqlite3 profiling.db <<EOF
.headers on
.mode csv
.output results.csv
-- Your SQL here
EOF
```

### 4. Verify Query Results

```bash
# Check result row count
wc -l results.csv

# Preview results
head -20 results.csv

# Validate data types
python3 -c "
import csv
with open('results.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row)
        break
"
```

## End-to-End Verification Script

```bash
#!/bin/bash
set -e

DB="profiling.db"

echo "=== 1. Verify Prerequisites ==="
sqlite3 --version
test -f ${DB} && echo "Database exists"

echo "=== 2. List Tables ==="
sqlite3 ${DB} ".tables"

echo "=== 3. Get Schema ==="
python3 scripts/get_schema.py --list_tables

echo "=== 4. Execute Sample Query ==="
sqlite3 ${DB} "
WITH compute_view AS (
    SELECT c.globalTaskId, ROUND(t.endNs - t.startNs) AS duration_ns, n.value AS op_name
    FROM COMPUTE_TASK_INFO c
    LEFT JOIN TASK t ON t.globalTaskId = c.globalTaskId
    LEFT JOIN STRING_IDS n ON n.id = c.name
)
SELECT op_name, SUM(duration_ns) AS total_ns
FROM compute_view
GROUP BY op_name
ORDER BY total_ns DESC
LIMIT 5;
"

echo "=== All verifications passed ==="
```

## Verification Checklist

| Check | Expected Result |
|-------|-----------------|
| sqlite3 installed | Version displayed |
| Database exists | File readable |
| .tables works | List of table names |
| get_schema.py works | Schema output |
| SELECT 1 works | Returns 1 |
| CTE query works | Returns results |
| LIMIT works | Limited rows |
| CSV output works | Valid CSV format |
