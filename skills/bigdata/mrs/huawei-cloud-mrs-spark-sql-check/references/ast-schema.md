# MRS Spark SQL AST Node Schema

AST node type definitions for Spark SQL parsing.

## Base Node Structure

```python
class ASTNode:
    node_type: str       # Node type name
    children: dict       # Child nodes dict {field_name: ASTNode | list | value}
    tokens: list         # Original Token list
    raw_text: str        # Original SQL fragment
    location: tuple      # (start_line, start_col, end_line, end_col)
```

## Statement Nodes

### SelectStmt
```python
{
    "node_type": "SelectStmt",
    "distinct": bool,              # DISTINCT keyword
    "has_select_star": bool,       # SELECT *
    "target_list": list,           # Target columns
    "from_clause": list,           # FROM clause
    "where_clause": dict|None,     # WHERE condition
    "group_by": dict|None,         # GROUP BY
    "having": dict|None,           # HAVING
    "with_clause": dict|None,      # WITH (CTE)
    "order_by": dict|None,         # ORDER BY
    "limit": dict|None,            # LIMIT
    "lateral_view": list|None,     # LATERAL VIEW
    "lateral_join": list|None,     # LATERAL JOIN (Spark 3.x)
    "lateral_subquery": list|None, # LATERAL subquery (Spark 3.x)
    "set_operation": str|None,     # UNION/UNION ALL/INTERSECT/EXCEPT
    "hint": str|None,              # /*+ hint */ (BROADCAST, COALESCE, REPARTITION)
}
```

### InsertStmt
```python
{
    "node_type": "InsertStmt",
    "table": str,                  # Target table
    "is_overwrite": bool,          # INSERT OVERWRITE
    "columns": list|None,          # Column list
    "partition": dict|None,        # PARTITION spec
    "values": list|None,           # VALUES
    "select": dict|None,           # SELECT subquery
    "hint": str|None,              # /*+ hint */
}
```

### UpdateStmt
```python
{
    "node_type": "UpdateStmt",
    "table": str,                  # Target table
    "set_clause": list,            # SET col=val
    "from_clause": dict|None,      # FROM
    "where_clause": dict|None,     # WHERE
    "missing_where": bool,         # Missing WHERE
}
```

### DeleteStmt
```python
{
    "node_type": "DeleteStmt",
    "table": str,                  # Target table
    "where_clause": dict|None,     # WHERE
    "missing_where": bool,         # Missing WHERE
}
```

### CreateStmt
```python
{
    "node_type": "CreateStmt",
    "table_name": str,             # Table name
    "is_external": bool,           # EXTERNAL
    "is_temporary": bool,          # TEMPORARY / GLOBAL TEMP
    "if_not_exists": bool,         # IF NOT EXISTS
    "columns": list,               # Column definitions
    "partitioned_by": list|None,   # PARTITIONED BY columns
    "clustered_by": dict|None,     # CLUSTERED BY spec (Hive compat)
    "sorted_by": list|None,        # SORTED BY columns (Hive compat)
    "num_buckets": int|None,       # INTO N BUCKETS (Hive compat)
    "row_format": dict|None,       # ROW FORMAT (Hive compat)
    "stored_as": str|None,         # STORED AS format (Hive compat)
    "using": str|None,             # USING data_source (Spark native)
    "options": dict|None,          # OPTIONS (key=value pairs)
    "location": str|None,          # LOCATION path
    "tblproperties": dict|None,    # TBLPROPERTIES
    "comment": str|None,           # COMMENT
    "as_select": dict|None,        # AS SELECT (CTAS)
    "like_table": str|None,        # LIKE table_name
    "stored_by": str|None,         # STORED BY (Hive compat)
}
```

### AlterStmt
```python
{
    "node_type": "AlterStmt",
    "table_name": str,             # Table name
    "action": str,                 # ADD/DROP/RENAME/SET/UNSET/CHANGE/REPLACE/RECOVER
}
```

### DropStmt
```python
{
    "node_type": "DropStmt",
    "object_type": str,            # TABLE/VIEW/DATABASE/FUNCTION...
    "object_name": str,            # Object name
    "if_exists": bool,             # IF EXISTS
}
```

### CacheStmt (Spark-specific)
```python
{
    "node_type": "CacheStmt",
    "table_name": str|None,        # Table name (CACHE TABLE name)
    "query": dict|None,            # AS SELECT query (CACHE TABLE name AS SELECT ...)
    "is_lazy": bool,               # CACHE LAZY TABLE
    "if_not_exists": bool,         # IF NOT EXISTS
}
```

### UncacheStmt (Spark-specific)
```python
{
    "node_type": "UncacheStmt",
    "table_name": str|None,        # Table name
    "if_exists": bool,             # IF EXISTS
    "purge": bool,                 # PURGE (UNCACHE TABLE ... PURGE)
}
```

### ClearCacheStmt (Spark-specific)
```python
{
    "node_type": "ClearCacheStmt",
}
```

### RefreshStmt (Spark-specific)
```python
{
    "node_type": "RefreshStmt",
    "target_type": str|None,       # TABLE / FUNCTION / None
    "target": str|None,            # Table name or function name
}
```

### AddJarStmt (Spark-specific)
```python
{
    "node_type": "AddJarStmt",
    "path": str|None,              # JAR file path
}
```

### ListJarStmt (Spark-specific)
```python
{
    "node_type": "ListJarStmt",
    "path": str|None,              # JAR file path (optional)
}
```

### CreateViewStmt (Spark-specific extensions)
```python
{
    "node_type": "CreateViewStmt",
    "view_name": str,              # View name
    "is_temporary": bool,          # TEMP VIEW
    "is_global": bool,             # GLOBAL TEMP VIEW
    "is_materialized": bool,       # MATERIALIZED VIEW
    "or_replace": bool,            # OR REPLACE
    "columns": list|None,          # Column aliases
    "comment": str|None,           # COMMENT
    "as_select": dict|None,        # AS SELECT query
}
```

## Statement Type to AST Node Mapping

| Statement Type | AST Node |
|----------------|----------|
| SELECT | SelectStmt |
| INSERT | InsertStmt |
| INSERT OVERWRITE | InsertStmt (is_overwrite=True) |
| UPDATE | UpdateStmt |
| DELETE | DeleteStmt |
| CREATE TABLE | CreateStmt |
| CREATE EXTERNAL TABLE | CreateStmt (is_external=True) |
| CREATE TABLE ... USING | CreateStmt (using=data_source) |
| ALTER TABLE | AlterStmt |
| DROP TABLE | DropStmt |
| CREATE VIEW | CreateViewStmt |
| CREATE TEMP VIEW | CreateViewStmt (is_temporary=True) |
| CREATE GLOBAL TEMP VIEW | CreateViewStmt (is_global=True) |
| CREATE OR REPLACE VIEW | CreateViewStmt (or_replace=True) |
| TRUNCATE TABLE | TruncateStmt |
| EXPLAIN | ExplainStmt |
| SET | SetStmt |
| SHOW | ShowStmt |
| DESCRIBE | DescribeStmt |
| GRANT | GrantStmt |
| REVOKE | RevokeStmt |
| ANALYZE TABLE | AnalyzeStmt |
| CACHE TABLE | CacheStmt |
| CACHE LAZY TABLE | CacheStmt (is_lazy=True) |
| UNCACHE TABLE | UncacheStmt |
| CLEAR CACHE | ClearCacheStmt |
| REFRESH TABLE | RefreshStmt (target_type="TABLE") |
| REFRESH FUNCTION | RefreshStmt (target_type="FUNCTION") |
| REFRESH | RefreshStmt |
| ADD JAR | AddJarStmt |
| LIST JAR | ListJarStmt |
| RESET | ResetStmt |
| MERGE | MergeStmt |

## Spark-Specific Hint Types

| Hint | Description |
|------|-------------|
| `/*+ BROADCAST(table) */` | Broadcast join hint |
| `/*+ BROADCASTJOIN(table) */` | Alias for BROADCAST |
| `/*+ MAPJOIN(table) */` | Alias for BROADCAST (Hive compat) |
| `/*+ SHUFFLE_HASH(table) */` | Shuffle hash join hint |
| `/*+ SHUFFLE_MERGE(table) */` | Shuffle sort-merge join hint |
| `/*+ SHUFFLE_REPLICATE_NL(table) */` | Shuffle replicated nested-loop join hint |
| `/*+ COALESCE(N) */` | Coalesce output partitions |
| `/*+ REPARTITION(N) */` | Repartition output |
| `/*+ REPARTITION(col, ...) */` | Repartition by columns |
