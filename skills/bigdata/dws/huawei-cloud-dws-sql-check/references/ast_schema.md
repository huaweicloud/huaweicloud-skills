# DWS SQL AST Node Schema

AST node type definitions based on `parsenodes.h` / `stmt_nodes.h`.

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
    "group_clause": list,          # GROUP BY
    "having_clause": dict|None,    # HAVING
    "window_clause": list,         # WINDOW
    "with_clause": dict|None,      # WITH (CTE)
    "sort_clause": list,           # ORDER BY
    "limit_offset": dict|None,     # OFFSET
    "limit_count": dict|None,      # LIMIT
    "locking_clause": list,        # FOR UPDATE/SHARE
    "set_operation": str|None,     # UNION/INTERSECT/EXCEPT/MINUS
    "has_plus": bool,              # Oracle (+) outer join
    "hint": str|None,              # /*+ hint */
}
```

### InsertStmt
```python
{
    "node_type": "InsertStmt",
    "table": str,                  # Target table
    "columns": list|None,          # Column list
    "values": list|None,           # VALUES
    "select": dict|None,           # SELECT subquery
    "returning": list|None,        # RETURNING
    "on_conflict": dict|None,      # ON CONFLICT
    "is_overwrite": bool,          # INSERT OVERWRITE
    "is_replace": bool,            # REPLACE INTO
    "is_ignore": bool,             # INSERT IGNORE
    "on_duplicate_key": dict|None, # ON DUPLICATE KEY UPDATE
    "default_values": bool,        # DEFAULT VALUES
    "hint": str|None,              # /*+ hint */
}
```

### UpdateStmt
```python
{
    "node_type": "UpdateStmt",
    "table": str,                  # Target table
    "set_clause": list,            # SET col=val
    "from_clause": list|None,      # FROM (DWS extension)
    "where_clause": dict|None,     # WHERE
    "returning": list|None,        # RETURNING
    "missing_where": bool,         # Missing WHERE
    "hint": str|None,              # /*+ hint */
}
```

### DeleteStmt
```python
{
    "node_type": "DeleteStmt",
    "table": str,                  # Target table
    "where_clause": dict|None,     # WHERE
    "returning": list|None,        # RETURNING
    "missing_where": bool,         # Missing WHERE
    "hint": str|None,              # /*+ hint */
}
```

### MergeStmt
```python
{
    "node_type": "MergeStmt",
    "target_table": str,           # MERGE INTO target table
    "source": dict,                # USING source
    "join_condition": dict,        # ON condition
    "when_clauses": list,          # WHEN MATCHED/NOT MATCHED clauses
    "hint": str|None,              # /*+ hint */
}
```

### CreateStmt
```python
{
    "node_type": "CreateStmt",
    "table_name": str,             # Table name
    "is_temp": bool,               # TEMP/TEMPORARY
    "if_not_exists": bool,         # IF NOT EXISTS
    "columns": list,               # Column definitions
    "inherits": list|None,         # INHERITS
    "with_options": dict|None,     # WITH (storage_options)
    "on_commit": str|None,         # ON COMMIT PRESERVE/DELETE ROWS
    "compress": str|None,          # COMPRESS YES/NO
    "partition_by": dict|None,     # PARTITION BY
    "distribute_type": str|None,   # HASH/MODULO/REPLICATION/ROUNDROBIN
    "distribute_columns": list|None, # Distribution key columns
    "to_node": list|None,          # TO NODE
    "to_group": str|None,          # TO GROUP
    "has_primary_key": bool,       # Has primary key constraint
    "comment": str|None,           # COMMENT
    "like_table": str|None,        # LIKE table
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
    "object_type": str,            # TABLE/INDEX/VIEW/MATERIALIZED VIEW...
    "objects": list,               # Object name list
    "if_exists": bool,             # IF EXISTS
    "cascade": bool,               # CASCADE
}
```

### ExplainStmt
```python
{
    "node_type": "ExplainStmt",
    "options": list,               # ANALYZE/VERBOSE/PERFORMANCE/WARMUP/PLAN
    "statement": dict,             # Analyzed statement
}
```

## Statement Type to AST Node Mapping

| Statement Type | AST Node | gram.y Production |
|----------------|----------|-------------------|
| SELECT | SelectStmt | SelectStmt |
| INSERT | InsertStmt | InsertStmt |
| UPDATE | UpdateStmt | UpdateStmt |
| DELETE | DeleteStmt | DeleteStmt |
| MERGE | MergeStmt | MergeStmt |
| CREATE TABLE | CreateStmt | CreateStmt |
| ALTER TABLE | AlterTableStmt | AlterTableStmt |
| DROP | DropStmt | DropStmt |
| CREATE INDEX | IndexStmt | IndexStmt |
| CREATE VIEW | ViewStmt | ViewStmt |
| CREATE MATERIALIZED VIEW | CreateMatViewStmt | CreateMatViewStmt |
| TRUNCATE | TruncateStmt | TruncateStmt |
| EXPLAIN | ExplainStmt | ExplainStmt |
| COPY | CopyStmt | CopyStmt |
| VACUUM | VacuumStmt | VacuumStmt |
| SET | VariableSetStmt | SetStmt |
| SHOW | VariableShowStmt | ShowStmt |
| GRANT | GrantStmt | GrantStmt |
| REVOKE | GrantStmt | RevokeStmt |
| BEGIN | TransactionStmt | BeginStmt |
| COMMIT | TransactionStmt | CommitStmt |
| ROLLBACK | TransactionStmt | RollbackStmt |
| CREATE RESOURCE POOL | CreateResourcePoolStmt | CreateResourcePoolStmt |
| CREATE WORKLOAD GROUP | CreateWorkloadGroupStmt | CreateWorkloadGroupStmt |
| CREATE REDACTION POLICY | CreateRedactionPolicyStmt | CreateRedactionPolicyStmt |
| CREATE OUTLINE | CreateOutlineStmt | CreateOutlineStmt |
| TIMECAPSULE | TimeCapsuleStmt | TimeCapsuleStmt |
