# MRS Hive SQL AST Node Schema

AST node type definitions for Hive SQL parsing.

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
    "set_operation": str|None,     # UNION/UNION ALL/INTERSECT/EXCEPT
    "hint": str|None,              # /*+ hint */
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
    "is_temporary": bool,          # TEMPORARY
    "if_not_exists": bool,         # IF NOT EXISTS
    "columns": list,               # Column definitions
    "partitioned_by": list|None,   # PARTITIONED BY columns
    "clustered_by": dict|None,     # CLUSTERED BY spec
    "sorted_by": list|None,        # SORTED BY columns
    "num_buckets": int|None,       # INTO N BUCKETS
    "row_format": dict|None,       # ROW FORMAT
    "stored_as": str|None,         # STORED AS format
    "location": str|None,          # LOCATION path
    "tblproperties": dict|None,    # TBLPROPERTIES
    "comment": str|None,           # COMMENT
    "as_select": dict|None,        # AS SELECT (CTAS)
}
```

### AlterTableStmt
```python
{
    "node_type": "AlterTableStmt",
    "table_name": str,             # Table name
    "actions": list,               # ALTER action list
}
```

### DropStmt
```python
{
    "node_type": "DropStmt",
    "object_type": str,            # TABLE/VIEW/INDEX/DATABASE/FUNCTION...
    "object_name": str,            # Object name
    "if_exists": bool,             # IF EXISTS
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
| ALTER TABLE | AlterTableStmt |
| DROP TABLE | DropStmt |
| CREATE VIEW | ViewStmt |
| TRUNCATE TABLE | TruncateStmt |
| EXPLAIN | ExplainStmt |
| SET | SetStmt |
| SHOW | ShowStmt |
| DESCRIBE | DescribeStmt |
| MSCK | MsckStmt |
| GRANT | GrantStmt |
| REVOKE | RevokeStmt |
| ANALYZE | AnalyzeStmt |
| LOAD | LoadStmt |
