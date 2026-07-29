# HetuEngine SQL AST Node Schema

AST node type definitions for HetuEngine SQL parser.

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
    "distinct": bool,                    # DISTINCT keyword
    "has_select_star": bool,             # SELECT *
    "target_list": list,                 # Target columns
    "from_clause": list,                 # FROM clause
    "where_clause": dict|None,           # WHERE condition
    "group_clause": list,                # GROUP BY
    "grouping_sets": list|None,          # GROUPING SETS / ROLLUP / CUBE
    "having_clause": dict|None,          # HAVING
    "window_clause": list,               # WINDOW
    "with_clause": dict|None,            # WITH (CTE)
    "sort_clause": list,                 # ORDER BY
    "limit_offset": dict|None,           # OFFSET
    "limit_count": dict|None,            # LIMIT
    "fetch_clause": dict|None,           # FETCH FIRST/NEXT
    "set_operation": str|None,           # UNION/INTERSECT/EXCEPT
    "has_tablesample": bool,             # TABLESAMPLE
    "tablesample_method": str|None,      # BERNOULLI/SYSTEM
    "tablesample_percentage": float|None,# TABLESAMPLE percentage
    "format": str|None,                  # FORMAT clause
    "match_recognize": dict|None,        # MATCH_RECOGNIZE
    "nulls_order": str|None,             # NULLS FIRST/LAST
}
```

### InsertStmt
```python
{
    "node_type": "InsertStmt",
    "table": str,                        # Target table
    "columns": list|None,                # Column list
    "values": list|None,                 # VALUES
    "select": dict|None,                 # SELECT subquery
    "is_overwrite": bool,                # INSERT OVERWRITE
    "partition": dict|None,              # PARTITION clause
    "default_values": bool,              # DEFAULT VALUES
}
```

### UpdateStmt
```python
{
    "node_type": "UpdateStmt",
    "table": str,                        # Target table
    "set_clause": list,                  # SET col=val
    "where_clause": dict|None,           # WHERE
    "missing_where": bool,               # Missing WHERE warning flag
}
```

### DeleteStmt
```python
{
    "node_type": "DeleteStmt",
    "table": str,                        # Target table
    "where_clause": dict|None,           # WHERE
    "missing_where": bool,               # Missing WHERE warning flag
    "partition": dict|None,              # PARTITION clause
}
```

### LoadStmt
```python
{
    "node_type": "LoadStmt",
    "filepath": str,                     # Source file path
    "is_overwrite": bool,                # OVERWRITE
    "table": str,                        # Target table
    "partition": dict|None,              # PARTITION clause
}
```

### CreateStmt
```python
{
    "node_type": "CreateStmt",
    "table_name": str,                   # Table name
    "is_external": bool,                 # EXTERNAL TABLE
    "if_not_exists": bool,               # IF NOT EXISTS
    "columns": list,                     # Column definitions
    "partitioned_by": list|None,         # PARTITIONED BY
    "clustered_by": list|None,           # CLUSTERED BY
    "sorted_by": list|None,              # SORTED BY
    "bucket_count": int|None,            # INTO n BUCKETS
    "row_format": dict|None,             # ROW FORMAT (DELIMITED/SERDE)
    "stored_as": str|None,               # STORED AS (ORC/PARQUET/...)
    "location": str|None,                # LOCATION path
    "tblproperties": dict|None,          # TBLPROPERTIES
    "comment": str|None,                 # COMMENT
    "with_options": dict|None,           # WITH (connector options)
    "has_primary_key": bool,             # Has primary key constraint
    "like_table": str|None,              # LIKE table
    "including_properties": bool,        # INCLUDING PROPERTIES
}
```

### CreateTableAsStmt
```python
{
    "node_type": "CreateTableAsStmt",
    "table_name": str,                   # Table name
    "query": dict,                       # AS SELECT query
    "with_data": bool,                   # WITH DATA
    "partitioned_by": list|None,         # PARTITIONED BY
    "stored_as": str|None,               # STORED AS
    "location": str|None,                # LOCATION path
    "tblproperties": dict|None,          # TBLPROPERTIES
    "comment": str|None,                 # COMMENT
}
```

### CreateTableLikeStmt
```python
{
    "node_type": "CreateTableLikeStmt",
    "table_name": str,                   # Table name
    "like_table": str,                   # LIKE table
    "including_properties": bool,        # INCLUDING PROPERTIES
}
```

### CreateViewStmt
```python
{
    "node_type": "CreateViewStmt",
    "view_name": str,                    # View name
    "or_replace": bool,                  # OR REPLACE
    "columns": list|None,                # Column list
    "as_query": dict,                    # AS SELECT query
    "comment": str|None,                 # COMMENT
    "tblproperties": dict|None,          # TBLPROPERTIES
}
```

### CreateFunctionStmt
```python
{
    "node_type": "CreateFunctionStmt",
    "function_name": str,                # Function name
    "parameters": list,                  # Parameter definitions
    "return_type": str,                  # Return type
    "language": str,                     # LANGUAGE (JAVA/SCALA)
    "deterministic": bool,               # DETERMINISTIC
    "body": str,                         # Function body / AS clause
}
```

### CreateMaterializedViewStmt
```python
{
    "node_type": "CreateMaterializedViewStmt",
    "view_name": str,                    # View name
    "if_not_exists": bool,               # IF NOT EXISTS
    "with_properties": dict|None,        # WITH properties
    "as_query": dict,                    # AS SELECT query
    "comment": str|None,                 # COMMENT
}
```

### AlterTableStmt
```python
{
    "node_type": "AlterTableStmt",
    "table_name": str,                   # Table name
    "actions": list,                     # ALTER action list
}
```

### DropStmt
```python
{
    "node_type": "DropStmt",
    "object_type": str,                  # TABLE/VIEW/FUNCTION/MATERIALIZED VIEW/SCHEMA
    "objects": list,                     # Object name list
    "if_exists": bool,                   # IF EXISTS
    "cascade": bool,                     # CASCADE
}
```

### ExplainStmt
```python
{
    "node_type": "ExplainStmt",
    "options": list,                     # GRAPHVIZ/TYPE/TEXT/DEBUG
    "statement": dict,                   # Analyzed statement
}
```

### ShowStmt
```python
{
    "node_type": "ShowStmt",
    "show_type": str,                    # TABLES/COLUMNS/FUNCTIONS/SCHEMAS/CATALOGS/...
    "target": str|None,                  # Target name or pattern
}
```

### DescribeStmt
```python
{
    "node_type": "DescribeStmt",
    "table_name": str,                   # Table name
}
```

### UseStmt
```python
{
    "node_type": "UseStmt",
    "catalog": str|None,                 # Catalog name
    "schema": str,                       # Schema name
}
```

### SetStmt
```python
{
    "node_type": "SetStmt",
    "parameter": str,                    # Configuration parameter
    "value": str,                        # Parameter value
}
```

### CallStmt
```python
{
    "node_type": "CallStmt",
    "procedure_name": str,               # Procedure name
    "arguments": list,                   # Argument list
}
```

### RefreshMaterializedViewStmt
```python
{
    "node_type": "RefreshMaterializedViewStmt",
    "view_name": str,                    # Materialized view name
}
```

### VirtualSchemaStmt
```python
{
    "node_type": "VirtualSchemaStmt",
    "action": str,                       # CREATE / DROP / SHOW
    "schema_name": str|None,             # Schema name
    "properties": dict|None,             # Schema properties
}
```

### TransactionStmt
```python
{
    "node_type": "TransactionStmt",
    "action": str,                       # START / COMMIT / ROLLBACK
    "isolation_level": str|None,         # READ UNCOMMITTED/COMMITTED/REPEATABLE READ/SERIALIZABLE
    "read_mode": str|None,               # READ ONLY / READ WRITE
}
```

## Statement Type to AST Node Mapping

| Statement Type | AST Node | Description |
|----------------|----------|-------------|
| SELECT | SelectStmt | Query with full clause support |
| INSERT | InsertStmt | INSERT [OVERWRITE] INTO/TABLE |
| UPDATE | UpdateStmt | UPDATE with SET/WHERE |
| DELETE | DeleteStmt | DELETE with WHERE/PARTITION |
| LOAD | LoadStmt | LOAD DATA INPATH |
| CREATE TABLE | CreateStmt | Hive-style CREATE TABLE |
| CREATE TABLE AS | CreateTableAsStmt | CREATE TABLE AS SELECT |
| CREATE TABLE LIKE | CreateTableLikeStmt | CREATE TABLE LIKE |
| CREATE VIEW | CreateViewStmt | CREATE [OR REPLACE] VIEW |
| CREATE FUNCTION | CreateFunctionStmt | CREATE FUNCTION (UDF) |
| CREATE MATERIALIZED VIEW | CreateMaterializedViewStmt | CREATE MATERIALIZED VIEW |
| ALTER TABLE | AlterTableStmt | ALTER TABLE actions |
| DROP | DropStmt | DROP TABLE/VIEW/FUNCTION/... |
| EXPLAIN | ExplainStmt | EXPLAIN plan |
| SHOW | ShowStmt | SHOW TABLES/COLUMNS/... |
| DESCRIBE | DescribeStmt | DESCRIBE table |
| USE | UseStmt | USE catalog.schema |
| SET | SetStmt | SET configuration |
| CALL | CallStmt | CALL procedure |
| REFRESH MATERIALIZED VIEW | RefreshMaterializedViewStmt | Refresh materialized view |
| VIRTUAL SCHEMA | VirtualSchemaStmt | CREATE/DROP/SHOW VIRTUAL SCHEMA |
| START TRANSACTION | TransactionStmt | START TRANSACTION |
| COMMIT | TransactionStmt | COMMIT |
| ROLLBACK | TransactionStmt | ROLLBACK |
