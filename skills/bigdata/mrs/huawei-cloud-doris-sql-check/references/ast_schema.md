# Doris SQL AST Node Schema

AST node type definitions based on Doris 3.1.4 Nereids ANTLR4 grammar (`DorisParser.g4`) and corresponding Java parser node classes (`org.apache.doris.nereids.trees.plans`).

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
    "cte": dict|None,              # WITH (CTE)
    "sort_clause": list,           # ORDER BY
    "limit_count": dict|None,      # LIMIT
    "limit_offset": dict|None,     # OFFSET
    "set_operation": str|None,     # UNION/INTERSECT/EXCEPT/MINUS
    "outfile": dict|None,          # INTO OUTFILE clause
    "hint": str|None,              # /*+ hint */
    "tablesample": dict|None,      # TABLESAMPLE clause
    "has_recursive_cte": bool,     # Recursive CTE detection
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
    "partition_spec": dict|None,   # PARTITION spec
    "with_label": str|None,        # WITH LABEL name
    "is_overwrite": bool,          # INSERT OVERWRITE TABLE
    "cte": dict|None,              # CTE
    "hints": list|None,            # [hints]
    "default_values": bool,       # DEFAULT VALUES
    "hint": str|None,              # /*+ hint */
}
```

### UpdateStmt
```python
{
    "node_type": "UpdateStmt",
    "table": str,                  # Target table
    "table_alias": str|None,       # Table alias
    "set_clause": list,            # SET col=val
    "from_clause": list|None,      # FROM clause
    "where_clause": dict|None,     # WHERE
    "missing_where": bool,         # Missing WHERE
    "cte": dict|None,              # CTE
    "hint": str|None,              # /*+ hint */
}
```

### DeleteStmt
```python
{
    "node_type": "DeleteStmt",
    "table": str,                  # Target table
    "table_alias": str|None,       # Table alias
    "using_clause": list|None,     # USING clause
    "where_clause": dict|None,     # WHERE
    "missing_where": bool,          # Missing WHERE
    "cte": dict|None,              # CTE
    "hint": str|None,              # /*+ hint */
}
```

### LoadStmt (BROKER LOAD)
```python
{
    "node_type": "LoadStmt",
    "label": str,                  # LOAD LABEL label_name
    "data_descs": list,             # DATA INFILE/FROM TABLE descriptions
    "properties": dict|None,        # PROPERTIES
    "comment": str|None,           # Comment
}
# data_desc item:
{
    "data_type": "INFILE|FROM_TABLE",  # DATA INFILE or DATA FROM TABLE
    "files": list,                     # File paths
    "target_table": str,               # INTO TABLE target
    "merge_type": str|None,            # APPEND|DELETE|MERGE
    "columns": list|None,              # Column list
    "column_mapping": dict|None,       # Column mapping
    "pre_filter": str|None,             # Pre-filter
    "where": str|None,                  # WHERE
    "delete_on": str|None,              # DELETE ON
    "sequence_col": str|None,           # SEQUENCE COL
}
```

### ExportStmt
```python
{
    "node_type": "ExportStmt",
    "table": str,                  # EXPORT TABLE name
    "partition": list|None,        # PARTITION spec
    "where_clause": dict|None,     # WHERE
    "to_path": str,                # TO 'path'
    "properties": dict|None,       # PROPERTIES
    "remote_storage": dict|None,   # WITH REMOTE STORAGE SYSTEM
}
```

### CreateStmt (CREATE TABLE)
```python
{
    "node_type": "CreateStmt",
    "table_name": str,             # Table name
    "is_temporary": bool,          # TEMPORARY
    "if_not_exists": bool,         # IF NOT EXISTS
    "columns": list,               # Column definitions
    "indexes": list|None,          # Index definitions (BITMAP/NGRAM_BF/INVERTED)
    "constraints": list|None,      # Constraints
    "engine": str|None,            # ENGINE = olap | mysql | hive | ...
    "key_model": str|None,         # DUPLICATE | AGGREGATE | UNIQUE KEY
    "key_columns": list|None,      # KEY columns
    "cluster_by": list|None,       # CLUSTER BY columns
    "partition_by": dict|None,     # PARTITION BY (RANGE/LIST/AUTO)
    "distribute_type": str|None,   # HASH | RANDOM
    "distribute_columns": list|None, # Distribution key columns
    "buckets": int|str|None,       # BUCKETS n or AUTO
    "properties": dict|None,       # PROPERTIES
    "comment": str|None,           # COMMENT
    "like_table": str|None,        # LIKE table
    "ctas_query": dict|None,       # CREATE TABLE AS SELECT query
    "colocate_group": str|None,    # COLOCATE WITH group (from properties)
}
```

### CreateMTMVStmt (CREATE MATERIALIZED VIEW)
```python
{
    "node_type": "CreateMTMVStmt",
    "name": str,                   # MTMV name
    "columns": list|None,          # Column list
    "key_model": str|None,         # DUPLICATE KEY (default)
    "key_columns": list|None,      # KEY columns
    "partition_by": dict|None,     # PARTITION BY
    "distribute_type": str|None,   # HASH | RANDOM
    "distribute_columns": list|None, # Distribution key columns
    "buckets": int|str|None,       # BUCKETS n or AUTO
    "build_mode": str|None,        # IMMEDIATE | DEFERRED
    "refresh_method": str|None,    # COMPLETE | AUTO
    "refresh_trigger": str|None,   # ON MANUAL | ON SCHEDULE | ON COMMIT
    "schedule": dict|None,         # Schedule definition
    "properties": dict|None,       # PROPERTIES
    "comment": str|None,           # COMMENT
    "as_query": dict|None,         # AS query
}
```

### AlterTableStmt
```python
{
    "node_type": "AlterTableStmt",
    "table_name": str,             # Table name
    "actions": list,               # ALTER action list
}
# action item:
{
    "action_type": str,            # ADD_COLUMN | DROP_COLUMN | ADD_PARTITION | ...
    "details": dict,                # Action-specific details
}
```

### DropStmt
```python
{
    "node_type": "DropStmt",
    "object_type": str,            # TABLE|INDEX|VIEW|DATABASE|ROLE|...
    "objects": list,                # Object name list
    "if_exists": bool,             # IF EXISTS
    "force": bool,                 # FORCE (for DROP TABLE)
}
```

### ExplainStmt
```python
{
    "node_type": "ExplainStmt",
    "plan_type": str|None,         # PARSED|ANALYZED|REWRITTEN|LOGICAL|OPTIMIZED|PHYSICAL|SHAPE|MEMO|DISTRIBUTED|ALL
    "level": str|None,             # VERBOSE|TREE|GRAPH|PLAN|DUMP
    "process": bool,               # PROCESS flag
    "statement": dict,             # Analyzed statement
}
```

### BackupStmt / RestoreStmt
```python
{
    "node_type": "BackupStmt",  # or RestoreStmt
    "snapshot_name": str,          # SNAPSHOT name
    "repository": str,             # TO/FROM repository
    "tables": list|None,           # ON tables
    "exclude_tables": list|None,   # EXCLUDE tables
    "properties": dict|None,       # PROPERTIES
}
```

### KillStmt
```python
{
    "node_type": "KillStmt",
    "kill_type": str,              # CONNECTION | QUERY
    "connection_id": int,          # Connection ID
}
```

### CancelStmt
```python
{
    "node_type": "CancelStmt",
    "cancel_type": str,            # LOAD | EXPORT | ALTER TABLE | BACKUP | RESTORE | WARM UP | MTMV TASK
    "details": dict,               # Type-specific details
}
```

### GrantStmt / RevokeStmt
```python
{
    "node_type": "GrantStmt",  # or RevokeStmt
    "grant_type": str,             # TABLE | RESOURCE | ROLE
    "privileges": list,            # Privilege list
    "object": str|None,            # ON object (for TABLE type)
    "resource_type": str|None,     # RESOURCE|CLUSTER|COMPUTE GROUP|STAGE|STORAGE VAULT|WORKLOAD GROUP
    "resource_name": str|None,     # Resource name
    "grantee": str,                # TO/FROM user or ROLE
    "is_role_grant": bool,         # GRANT role TO user
}
```

## Statement Type to AST Node Mapping

| Statement Type | AST Node | DorisParser.g4 Production |
|----------------|----------|---------------------------|
| SELECT | SelectStmt | query / querySpecification |
| INSERT | InsertStmt | #insertTable |
| UPDATE | UpdateStmt | #update |
| DELETE | DeleteStmt | #delete |
| LOAD (BROKER LOAD) | LoadStmt | #load |
| EXPORT | ExportStmt | #export |
| COPY INTO | CopyIntoStmt | #copyInto |
| TRUNCATE | TruncateStmt | #truncateTable |
| CREATE TABLE | CreateStmt | #createTable |
| CREATE TABLE LIKE | CreateStmt | #createTableLike |
| CREATE VIEW | ViewStmt | #createView |
| CREATE MTMV | CreateMTMVStmt | #createMTMV |
| CREATE INDEX | IndexStmt | #createIndex (unsupported) |
| ALTER TABLE | AlterTableStmt | #alterTable (unsupported) |
| DROP TABLE/VIEW/INDEX | DropStmt | #dropTable / #dropView / #dropIndex |
| CREATE DATABASE | CreateDbStmt | #createDatabase (unsupported) |
| CREATE CATALOG | CreateCatalogStmt | #createCatalog (unsupported) |
| CREATE USER | CreateUserStmt | #createUser (unsupported) |
| CREATE ROLE | CreateRoleStmt | #createRole (unsupported) |
| CREATE RESOURCE | CreateResourceStmt | #createResource (unsupported) |
| CREATE STAGE | CreateStageStmt | #createStage (unsupported) |
| CREATE ENCRYPTKEY | CreateEncryptKeyStmt | #createEncryptkey (unsupported) |
| CREATE JOB | CreateJobStmt | #createScheduledJob |
| CREATE ROW POLICY | CreateRowPolicyStmt | #createRowPolicy |
| CREATE SQL_BLOCK_RULE | CreateSqlBlockRuleStmt | #createSqlBlockRule (unsupported) |
| CREATE STORAGE VAULT | CreateStorageVaultStmt | #createStorageVault (unsupported) |
| CREATE WORKLOAD GROUP | CreateWorkloadGroupStmt | #createWorkloadGroup (unsupported) |
| CREATE REPOSITORY | CreateRepositoryStmt | #createRepository (unsupported) |
| CREATE FUNCTION | CreateFunctionStmt | #createUserDefineFunction / #createAliasFunction (unsupported) |
| ROUTINE LOAD | CreateRoutineLoadStmt | #createRoutineLoadJob (unsupported) |
| GRANT | GrantStmt | #grantTablePrivilege / #grantResourcePrivilege / #grantRole |
| REVOKE | RevokeStmt | (same labels as GRANT) |
| BEGIN/START TRANSACTION | TransactionStmt | #transactionBegin |
| COMMIT | TransactionStmt | #transcationCommit |
| ROLLBACK | TransactionStmt | #transactionRollback |
| EXPLAIN | ExplainStmt | explain |
| DESCRIBE | DescribeStmt | #describeTable / #describeTableAll / #describeTableValuedFunction |
| SET | SetStmt | #setOptions / #setTransaction / ...
| SHOW | ShowStmt | #show* (50+ variants) |
| ADMIN SET/SHOW | AdminStmt | #adminSet* / #adminShow* |
| KILL | KillStmt | #killConnection / #killQuery |
| CANCEL | CancelStmt | #cancelLoad / #cancelExport / ... |
| BACKUP | BackupStmt | #backup |
| RESTORE | RestoreStmt | #restore |
| RECOVER | RecoverStmt | #recoverDatabase / #recoverTable / #recoverPartition |
| CLEAN | CleanStmt | #cleanLabel / #cleanAllProfile / ... |
| INSTALL PLUGIN | InstallPluginStmt | #installPlugin |
| UNINSTALL PLUGIN | UninstallPluginStmt | #uninstallPlugin |
| LOCK TABLES | LockTablesStmt | #lockTables |
| USE | UseStmt | #useDatabase / #useCloudCluster / #switchCatalog |
| SWITCH | SwitchStmt | (within unsupportedUseStatement) |
| CALL PROCEDURE | CallStmt | #callProcedure |
| HELP | HelpStmt | #help |
| SYNC | SyncStmt | #sync |
| WARM UP | WarmUpStmt | #warmUpCluster |
| PAUSE | PauseStmt | #pauseJob / #pauseMTMV / #pauseRoutineLoad |
| RESUME | ResumeStmt | #resumeJob / #resumeMTMV / #resumeRoutineLoad |
| STOP ROUTINE LOAD | StopRoutineLoadStmt | #stopRoutineLoad |
| REFRESH | RefreshStmt | #refreshTable / #refreshMTMV / ... |
| ALTER COLOCATE GROUP | AlterColocateGroupStmt | #alterColocateGroup |

## Note on "supported" vs "unsupported" in DorisParser.g4

The Nereids parser marks some statements as `unsupported*` (e.g., `unsupportedCreateStatement`, `unsupportedAlterStatement`). This means the statement is **parseable** by the grammar but **not yet fully implemented** in the Nereids optimizer. For static SQL checking purposes, both `supported` and `unsupported` variants are treated as valid Doris SQL syntax — the checker validates grammar, not execution.
