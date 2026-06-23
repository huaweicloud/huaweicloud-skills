# -*- coding: utf-8 -*-
"""
DWS SQL Grammar Rules Definition
Covers 160+ statement types, DWS-specific extensions, operator precedence
"""

from enum import Enum


class StatementCategory(Enum):
    DML = "DML"
    DDL = "DDL"
    DCL = "DCL"
    TCL = "TCL"
    UTILITY = "UTILITY"


class ClauseRequirement(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    DWS_EXTENSION = "dws_extension"


# ============================================================
# Statement Type Definitions
# ============================================================

STATEMENT_RULES = {
    # ---- DML Statements ----
    "SELECT": {
        "category": StatementCategory.DML,
        "start_tokens": ["SELECT", "WITH"],
        "node_type": "SelectStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["/*+"], "description": "Optimizer hint"},
            "distinct": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DISTINCT", "ALL"], "description": "DISTINCT / ALL"},
            "target_list": {"requirement": ClauseRequirement.REQUIRED, "description": "Select target columns"},
            "into": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["INTO"], "description": "SELECT INTO target"},
            "from": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FROM"], "description": "FROM clause"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE condition"},
            "group_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["GROUP"], "next_tokens": ["BY"], "description": "GROUP BY"},
            "having": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["HAVING"], "description": "HAVING condition"},
            "window": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WINDOW"], "description": "WINDOW definition"},
            "order_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ORDER"], "next_tokens": ["BY"], "description": "ORDER BY"},
            "limit": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["LIMIT"], "description": "LIMIT count"},
            "offset": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["OFFSET"], "description": "OFFSET count"},
            "for_update": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FOR"], "next_tokens_any": ["UPDATE", "SHARE", "NO", "KEY"], "description": "FOR UPDATE/SHARE locking"},
        },
        "set_operations": ["UNION", "INTERSECT", "EXCEPT", "MINUS"],
        "clause_order": ["hint", "distinct", "target_list", "into", "from", "where",
                        "group_by", "having", "window", "order_by", "limit", "offset", "for_update"],
        "dws_extensions": ["hint_string", "ora_joinop", "minus_set_op"],
        "grammar_bnf": """
select_no_parens:
    simple_select
  | select_clause sort_clause
  | select_clause opt_sort_clause for_locking_clause opt_select_limit
  | with_clause select_clause ...

simple_select:
    SELECT opt_hint_string opt_distinct target_list
    into_clause from_clause where_clause
    group_clause having_clause window_clause
  | values_clause
  | select_clause UNION|INTERSECT|EXCEPT|MINUS opt_all select_clause
""",
    },

    "INSERT": {
        "category": StatementCategory.DML,
        "start_tokens": ["INSERT", "REPLACE"],
        "node_type": "InsertStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["/*+"], "description": "Optimizer hint"},
            "ignore": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["IGNORE"], "description": "INSERT IGNORE (MySQL compat)"},
            "overwrite": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["OVERWRITE"], "description": "INSERT OVERWRITE"},
            "into": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["INTO"], "description": "Target table"},
            "table": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column list in parentheses"},
            "values": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["VALUES"], "description": "VALUES clause"},
            "select": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["SELECT"], "description": "Subquery source"},
            "default_values": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DEFAULT"], "next_tokens": ["VALUES"], "description": "DEFAULT VALUES"},
            "on_conflict": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ON"], "next_tokens_any": ["CONFLICT", "DUPLICATE"], "description": "ON CONFLICT / ON DUPLICATE KEY UPDATE"},
            "returning": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["RETURNING"], "description": "RETURNING clause"},
        },
        "clause_order": ["hint", "into", "ignore", "overwrite", "table", "columns", "values", "select", "on_conflict", "returning"],
        "dws_extensions": ["REPLACE INTO", "INSERT OVERWRITE", "ON DUPLICATE KEY UPDATE", "IGNORE"],
        "grammar_bnf": """
InsertStmt:
    opt_with_clause INSERT opt_hint_string opt_ignore opt_overwrite
    INTO insert_target insert_rest upsert_clause returning_clause
  | REPLACE opt_hint_string opt_into insert_target insert_rest returning_clause
""",
    },

    "UPDATE": {
        "category": StatementCategory.DML,
        "start_tokens": ["UPDATE"],
        "node_type": "UpdateStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["/*+"], "description": "Optimizer hint"},
            "table": {"requirement": ClauseRequirement.REQUIRED, "description": "Target table"},
            "set": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["SET"], "description": "SET clause"},
            "from": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FROM"], "description": "FROM clause (multi-table update)"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE condition"},
            "returning": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["RETURNING"], "description": "RETURNING clause"},
        },
        "clause_order": ["hint", "table", "set", "from", "where", "returning"],
        "grammar_bnf": """
UpdateStmt:
    opt_with_clause UPDATE opt_hint_string relation_expr_opt_alias
    SET set_clause_list from_clause where_or_current_clause returning_clause
""",
    },

    "DELETE": {
        "category": StatementCategory.DML,
        "start_tokens": ["DELETE"],
        "node_type": "DeleteStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["/*+"], "description": "Optimizer hint"},
            "from": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FROM"], "description": "Target table"},
            "using": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["USING"], "description": "USING clause"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE condition"},
            "returning": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["RETURNING"], "description": "RETURNING clause"},
        },
        "clause_order": ["hint", "from", "using", "where", "returning"],
        "grammar_bnf": """
DeleteStmt:
    opt_with_clause DELETE_P opt_hint_string FROM relation_expr_opt_alias
    using_clause where_or_current_clause returning_clause
""",
    },

    "MERGE": {
        "category": StatementCategory.DML,
        "start_tokens": ["MERGE"],
        "node_type": "MergeStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["/*+"], "description": "Optimizer hint"},
            "into": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["INTO"], "description": "Target table"},
            "using": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["USING"], "description": "Source table/subquery"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "Join condition"},
            "when_matched": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHEN"], "next_tokens": ["MATCHED"], "description": "WHEN MATCHED THEN UPDATE/DELETE"},
            "when_not_matched": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHEN"], "next_tokens": ["NOT"], "description": "WHEN NOT MATCHED THEN INSERT"},
        },
        "clause_order": ["hint", "into", "using", "on", "when_matched", "when_not_matched"],
        "dws_extensions": ["MERGE INTO"],
        "grammar_bnf": """
MergeStmt:
    MERGE opt_hint_string INTO relation_expr_opt_alias
    USING table_ref ON a_expr merge_when_list
""",
    },

    # ---- DDL Statements ----
    "CREATE TABLE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateStmt",
        "second_tokens": ["TEMPORARY", "TEMP", "TABLE", "IF"],
        "clauses": {
            "temp": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TEMPORARY", "TEMP"], "description": "Temporary table"},
            "if_not_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "next_tokens": ["NOT"], "description": "IF NOT EXISTS"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "columns": {"requirement": ClauseRequirement.REQUIRED, "description": "Column/constraint definitions"},
            "inherits": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["INHERITS"], "description": "INHERITS parent table"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "WITH storage options"},
            "on_commit": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ON"], "next_tokens": ["COMMIT"], "description": "ON COMMIT PRESERVE/DELETE ROWS"},
            "compress": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["COMPRESS"], "description": "Compression mode"},
            "partition": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["PARTITION"], "next_tokens": ["BY"], "description": "PARTITION BY RANGE/VALUE/LIST"},
            "distribute_by": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["DISTRIBUTE"], "next_tokens": ["BY"], "description": "DISTRIBUTE BY HASH/MODULO/REPLICATION/ROUNDROBIN"},
            "to_group": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["TO"], "next_tokens_any": ["NODE", "GROUP"], "description": "TO NODE/GROUP subcluster"},
            "tablespace": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TABLESPACE"], "description": "TABLESPACE for table storage"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Table comment"},
            "like": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["LIKE"], "description": "LIKE source table"},
        },
        "clause_order": ["temp", "if_not_exists", "table_name", "columns", "inherits",
                        "with_options", "on_commit", "compress", "partition", "distribute_by", "to_group", "tablespace", "comment"],
        "dws_extensions": ["DISTRIBUTE BY", "TO NODE/GROUP", "PARTITION BY", "COMPRESS", "TABLESPACE"],
        "grammar_bnf": """
CreateStmt:
    CREATE OptTemp TABLE qualified_name '(' OptTableElementList ')'
    OptInherit OptWith OnCommitOption OptCompress OptPartitionElement
    OptDistributeBy OptSubCluster opt_table_partitioning_clause OptTableComment
  | CREATE OptTemp TABLE IF_P NOT EXISTS ... (same structure)
  | CREATE OptTemp TABLE qualified_name OF any_name ...
  | CREATE OptTemp TABLE qualified_name TableLikeClause ...
""",
    },

    "ALTER TABLE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["ALTER"],
        "node_type": "AlterTableStmt",
        "second_tokens": ["TABLE", "INDEX", "SEQUENCE", "VIEW"],
        "clauses": {
            "if_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "next_tokens": ["EXISTS"], "description": "IF EXISTS"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "add_column": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ADD"], "description": "ADD column/constraint"},
            "drop_column": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DROP"], "description": "DROP column/constraint"},
            "alter_column": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ALTER"], "description": "ALTER column"},
            "modify_column": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["MODIFY"], "description": "MODIFY column (Oracle compat)"},
            "rename": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["RENAME"], "description": "RENAME column/table"},
            "distribute_by": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["DISTRIBUTE"], "next_tokens": ["BY"], "description": "DISTRIBUTE BY"},
            "add_partition": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["ADD"], "next_tokens": ["PARTITION"], "description": "ADD PARTITION"},
            "drop_partition": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["DROP"], "next_tokens": ["PARTITION"], "description": "DROP PARTITION"},
            "exchange_partition": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["EXCHANGE"], "next_tokens": ["PARTITION"], "description": "EXCHANGE PARTITION"},
        },
        "dws_extensions": ["MODIFY column", "DISTRIBUTE BY", "ADD/DROP/EXCHANGE PARTITION"],
        "grammar_bnf": """
AlterTableStmt:
    ALTER TABLE relation_expr alter_table_or_partition
  | ALTER TABLE relation_expr MODIFY_P '(' modify_column_cmds ')'
  | ALTER TABLE relation_expr ADD_P '(' add_column_cmds ')'
  | ALTER INDEX qualified_name alter_table_or_partition
  | ALTER SEQUENCE/VIEW qualified_name alter_table_cmds
""",
    },

    "DROP": {
        "category": StatementCategory.DDL,
        "start_tokens": ["DROP"],
        "node_type": "DropStmt",
        "object_types": ["TABLE", "INDEX", "VIEW", "SEQUENCE", "SCHEMA", "DATABASE",
                        "FUNCTION", "PROCEDURE", "TRIGGER", "TYPE", "DOMAIN", "ROLE",
                        "USER", "GROUP", "TABLESPACE", "EXTENSION", "FOREIGN",
                        "SYNONYM", "MATERIALIZED", "NODE", "GROUP_P", "RESOURCE",
                        "WORKLOAD", "OUTLINE", "DIRECTORY", "PUBLICATION", "SUBSCRIPTION"],
        "clauses": {
            "if_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "next_tokens": ["EXISTS"], "description": "IF EXISTS"},
            "cascade": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["CASCADE", "RESTRICT"], "description": "CASCADE / RESTRICT"},
        },
    },

    "CREATE INDEX": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "IndexStmt",
        "second_tokens": ["UNIQUE", "INDEX"],
        "clauses": {
            "unique": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["UNIQUE"], "description": "UNIQUE index"},
            "index_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Index name"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON table"},
            "columns": {"requirement": ClauseRequirement.REQUIRED, "description": "Index column expressions"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "WITH storage options"},
            "tablespace": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TABLESPACE"], "description": "TABLESPACE"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "Partial index predicate"},
        },
    },

    "CREATE VIEW": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "ViewStmt",
        "second_tokens": ["OR", "REPLACE", "VIEW"],
        "clauses": {
            "or_replace": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["OR"], "next_tokens": ["REPLACE"], "description": "OR REPLACE"},
            "view_name": {"requirement": ClauseRequirement.REQUIRED, "description": "View name"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column aliases"},
            "as": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["AS"], "description": "AS query"},
            "with_check": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "next_tokens_any": ["CHECK", "CASCADED", "LOCAL"], "description": "WITH CHECK OPTION"},
        },
    },

    "CREATE MATERIALIZED VIEW": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateMatViewStmt",
        "second_tokens": ["MATERIALIZED"],
        "clauses": {
            "if_not_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "next_tokens": ["NOT"], "description": "IF NOT EXISTS"},
            "view_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Materialized view name"},
            "build_with_data": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["BUILD"], "next_tokens_any": ["IMMEDIATE", "DEFERRED"], "description": "BUILD IMMEDIATE/DEFERRED"},
            "refresh": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["REFRESH"], "next_tokens_any": ["FAST", "COMPLETE", "FORCE", "AUTO"], "description": "REFRESH mode"},
            "enable_query_rewrite": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["ENABLE"], "next_tokens": ["QUERY"], "description": "ENABLE QUERY REWRITE"},
            "keepalive": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["KEEPALIVE"], "description": "KEEPALIVE"},
            "distribute_by": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["DISTRIBUTE"], "next_tokens": ["BY"], "description": "DISTRIBUTE BY"},
            "as": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["AS"], "description": "AS query"},
        },
        "dws_extensions": ["REFRESH FAST/COMPLETE/FORCE/AUTO", "ENABLE QUERY REWRITE", "KEEPALIVE", "DISTRIBUTE BY"],
    },

    "TRUNCATE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["TRUNCATE"],
        "node_type": "TruncateStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TABLE"], "description": "TABLE keyword"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "cascade": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["CASCADE", "RESTRICT"], "description": "CASCADE / RESTRICT"},
            "partition": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["PARTITION"], "description": "PARTITION"},
        },
        "dws_extensions": ["PARTITION truncation"],
    },

    # ---- Utility Statements ----
    "EXPLAIN": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["EXPLAIN"],
        "node_type": "ExplainStmt",
        "clauses": {
            "analyze": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ANALYZE", "ANALYSE"], "description": "ANALYZE - actually execute"},
            "verbose": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["VERBOSE"], "description": "VERBOSE output"},
            "performance": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["PERFORMANCE"], "description": "EXPLAIN PERFORMANCE (DWS)"},
            "warmup": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["WARMUP"], "description": "EXPLAIN WARMUP (DWS)"},
            "plan": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["PLAN"], "description": "EXPLAIN PLAN (DWS)"},
            "options": {"requirement": ClauseRequirement.OPTIONAL, "description": "Explain options in parentheses"},
            "statement": {"requirement": ClauseRequirement.REQUIRED, "description": "The SQL statement to explain"},
        },
        "dws_extensions": ["EXPLAIN PERFORMANCE", "EXPLAIN WARMUP", "EXPLAIN PLAN SET STATEMENT_ID"],
        "grammar_bnf": """
ExplainStmt:
    EXPLAIN ExplainableStmt
  | EXPLAIN PERFORMANCE [options] ExplainableStmt
  | EXPLAIN WARMUP warmup_option_name ExplainableStmt
  | EXPLAIN PLAN [SET STATEMENT_ID = Sconst] FOR ExplainableStmt
""",
    },

    "COPY": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["COPY"],
        "node_type": "CopyStmt",
        "clauses": {
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column list"},
            "from_to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FROM", "TO"], "description": "FROM / TO"},
            "source": {"requirement": ClauseRequirement.REQUIRED, "description": "File path or STDIN/STDOUT"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH", "BINARY", "DELIMITER", "CSV", "NULL", "HEADER", "QUOTE", "ESCAPE", "FORCE", "ENCODING", "FILL_MISSING_FIELDS", "IGNORE_EXTRA_DATA", "DATE_FORMAT", "TIME_FORMAT", "TIMESTAMP_FORMAT", "COMPATIBLE_ILLEGAL_CHARS", "EOL"], "description": "COPY format options"},
        },
        "dws_extensions": ["FILL_MISSING_FIELDS", "IGNORE_EXTRA_DATA", "COMPATIBLE_ILLEGAL_CHARS", "DATE_FORMAT", "TIME_FORMAT", "TIMESTAMP_FORMAT", "EOL"],
    },

    "VACUUM": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["VACUUM"],
        "node_type": "VacuumStmt",
        "clauses": {
            "full": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FULL"], "description": "VACUUM FULL"},
            "freeze": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FREEZE"], "description": "VACUUM FREEZE"},
            "verbose": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["VERBOSE"], "description": "VERBOSE output"},
            "analyze": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ANALYZE", "ANALYSE"], "description": "ANALYZE statistics"},
            "table_name": {"requirement": ClauseRequirement.OPTIONAL, "description": "Table name"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column list for ANALYZE"},
            "partition": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["PARTITION"], "description": "PARTITION"},
            "merge": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["MERGE"], "description": "VACUUM MERGE (delta merge)"},
        },
        "dws_extensions": ["VACUUM MERGE (delta merge)", "PARTITION", "HDFSDIRECTORY"],
    },

    "SET": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["SET"],
        "node_type": "VariableSetStmt",
        "clauses": {
            "parameter": {"requirement": ClauseRequirement.REQUIRED, "description": "Parameter name"},
            "value": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO", "="], "description": "Parameter value"},
        },
    },

    "SHOW": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["SHOW"],
        "node_type": "VariableShowStmt",
        "clauses": {
            "parameter": {"requirement": ClauseRequirement.REQUIRED, "description": "Parameter name"},
        },
    },

    # ---- DCL Statements ----
    "GRANT": {
        "category": StatementCategory.DCL,
        "start_tokens": ["GRANT"],
        "node_type": "GrantStmt",
        "clauses": {
            "privileges": {"requirement": ClauseRequirement.REQUIRED, "description": "Privilege list"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON object"},
            "to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "description": "TO grantees"},
            "with_grant": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "next_tokens": ["GRANT"], "description": "WITH GRANT OPTION"},
        },
    },

    "REVOKE": {
        "category": StatementCategory.DCL,
        "start_tokens": ["REVOKE"],
        "node_type": "RevokeStmt",
        "clauses": {
            "privileges": {"requirement": ClauseRequirement.REQUIRED, "description": "Privilege list"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON object"},
            "from": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FROM"], "description": "FROM grantees"},
        },
    },

    # ---- TCL Statements ----
    "BEGIN": {
        "category": StatementCategory.TCL,
        "start_tokens": ["BEGIN", "START"],
        "node_type": "TransactionStmt",
        "clauses": {
            "isolation_level": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ISOLATION"], "next_tokens": ["LEVEL"], "description": "ISOLATION LEVEL"},
            "read_write": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["READ"], "next_tokens_any": ["ONLY", "WRITE"], "description": "READ ONLY / READ WRITE"},
        },
    },

    "COMMIT": {
        "category": StatementCategory.TCL,
        "start_tokens": ["COMMIT", "END"],
        "node_type": "TransactionStmt",
        "clauses": {
            "chain": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["CHAIN"], "description": "AND CHAIN"},
        },
    },

    "ROLLBACK": {
        "category": StatementCategory.TCL,
        "start_tokens": ["ROLLBACK", "ABORT"],
        "node_type": "TransactionStmt",
        "clauses": {
            "chain": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["CHAIN"], "description": "AND CHAIN"},
            "to_savepoint": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TO"], "description": "TO SAVEPOINT"},
        },
    },

    # ---- DWS-Specific DDL Statements ----
    "CREATE RESOURCE POOL": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateResourcePoolStmt",
        "second_tokens": ["RESOURCE"],
        "clauses": {
            "pool_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Resource pool name"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "WITH options"},
        },
        "dws_extensions": ["RESOURCE POOL"],
    },

    "CREATE WORKLOAD GROUP": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateWorkloadGroupStmt",
        "second_tokens": ["WORKLOAD"],
        "clauses": {
            "group_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Workload group name"},
            "using_resource_pool": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["USING"], "next_tokens": ["RESOURCE"], "description": "USING RESOURCE POOL"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "WITH options"},
        },
        "dws_extensions": ["WORKLOAD GROUP"],
    },

    "TIMECAPSULE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["TIMECAPSULE"],
        "node_type": "TimeCapsuleStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TABLE"], "description": "TABLE keyword"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "to_before": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "next_tokens": ["BEFORE"], "description": "TO BEFORE"},
            "action": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["DROP", "TRUNCATE"], "description": "DROP or TRUNCATE"},
        },
        "dws_extensions": ["TIMECAPSULE (Flashback)"],
    },

    "PURGE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["PURGE"],
        "node_type": "PurgeStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TABLE"], "description": "PURGE TABLE"},
            "table_name": {"requirement": ClauseRequirement.OPTIONAL, "description": "Table name"},
            "recyclebin": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["RECYCLEBIN"], "description": "PURGE RECYCLEBIN"},
        },
        "dws_extensions": ["PURGE (Recyclebin)"],
    },

    "CREATE OUTLINE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateOutlineStmt",
        "second_tokens": ["OUTLINE"],
        "clauses": {
            "outline_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Outline name"},
            "for_sql_hash": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FOR"], "description": "FOR sql_hash"},
            "using": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["USING"], "description": "USING outline_text"},
        },
        "dws_extensions": ["OUTLINE (Query Plan Hint)"],
    },

    "CREATE REDACTION POLICY": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateRedactionPolicyStmt",
        "second_tokens": ["REDACTION"],
        "clauses": {
            "policy_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Policy name"},
            "on_table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON table"},
            "column_add": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ADD"], "next_tokens": ["COLUMN"], "description": "ADD COLUMN with redaction function"},
        },
        "dws_extensions": ["REDACTION POLICY (Data Masking)"],
    },

    "CREATE RLS POLICY": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateRlsPolicyStmt",
        "second_tokens": ["ROW"],
        "clauses": {
            "policy_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Policy name"},
            "on_table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON table"},
            "using": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["USING"], "description": "USING expression"},
        },
        "dws_extensions": ["ROW LEVEL SECURITY POLICY"],
    },

    "CREATE NODE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateNodeStmt",
        "second_tokens": ["NODE"],
        "clauses": {
            "node_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Node name"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "WITH options"},
        },
        "dws_extensions": ["NODE (PGXC)"],
    },

    "CREATE NODE GROUP": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateNodeGroupStmt",
        "second_tokens": ["NODE"],
        "clauses": {
            "group_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Group name"},
            "with_options": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "WITH options"},
            "distribute": {"requirement": ClauseRequirement.DWS_EXTENSION, "tokens": ["DISTRIBUTE"], "next_tokens": ["FROM"], "description": "DISTRIBUTE FROM"},
        },
        "dws_extensions": ["NODE GROUP (PGXC)", "VCGROUP", "ELASTIC"],
    },

    "BARRIER": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["CREATE"],
        "node_type": "BarrierStmt",
        "second_tokens": ["BARRIER"],
        "clauses": {
            "barrier_id": {"requirement": ClauseRequirement.OPTIONAL, "description": "Barrier identifier"},
        },
        "dws_extensions": ["BARRIER (Distributed Transaction)"],
    },

    "EXECUTE DIRECT": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["EXECUTE"],
        "node_type": "ExecDirectStmt",
        "second_tokens": ["DIRECT"],
        "clauses": {
            "on_node": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON node"},
            "statement": {"requirement": ClauseRequirement.REQUIRED, "description": "SQL statement to execute"},
        },
        "dws_extensions": ["EXECUTE DIRECT (PGXC)"],
    },

    "CLEAN CONNECTION": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["CLEAN"],
        "node_type": "CleanConnStmt",
        "second_tokens": ["CONNECTION"],
        "clauses": {
            "to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "description": "TO COORDINATOR/NODE/ALL"},
            "for_database": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FOR"], "next_tokens": ["DATABASE"], "description": "FOR DATABASE"},
            "to_user": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["TO"], "next_tokens": ["USER"], "description": "TO USER"},
        },
        "dws_extensions": ["CLEAN CONNECTION (PGXC)"],
    },

    "ANONYMOUS BLOCK": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["DECLARE", "BEGIN"],
        "node_type": "AnonyBlockStmt",
        "clauses": {
            "body": {"requirement": ClauseRequirement.REQUIRED, "description": "PL/pgSQL block body"},
        },
        "dws_extensions": ["Anonymous PL/pgSQL block"],
    },

    "CALL": {
        "category": StatementCategory.DML,
        "start_tokens": ["CALL"],
        "node_type": "CallFuncStmt",
        "clauses": {
            "function_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Function/procedure name"},
            "arguments": {"requirement": ClauseRequirement.OPTIONAL, "description": "Argument list"},
        },
        "dws_extensions": ["CALL (Oracle/MySQL compatible)"],
    },
}


# ============================================================
# DWS-Specific Grammar Extensions
# ============================================================

DWS_SPECIFIC_GRAMMAR = {
    "distribute_by": {
        "syntax": "DISTRIBUTE BY { HASH | MODULO | REPLICATION | ROUNDROBIN } [(column_list)]",
        "valid_types": ["HASH", "MODULO", "REPLICATION", "ROUNDROBIN"],
        "applies_to": ["CREATE TABLE", "CREATE MATERIALIZED VIEW", "CREATE FOREIGN TABLE", "ALTER TABLE"],
        "description": "Distribution strategy for MPP data placement",
    },
    "subcluster": {
        "syntax": "TO { NODE (node_list) | GROUP group_name }",
        "applies_to": ["CREATE TABLE", "ALTER TABLE"],
        "description": "Subcluster assignment for table data placement",
    },
    "partition_by": {
        "syntax": "PARTITION BY { RANGE | VALUE | LIST } (column) (partition_definitions)",
        "valid_types": ["RANGE", "VALUE", "LIST"],
        "applies_to": ["CREATE TABLE", "ALTER TABLE"],
        "description": "Table partitioning definition",
    },
    "compress": {
        "syntax": "COMPRESS [=] { YES | NO | MEDIUM | HIGH }",
        "valid_values": ["YES", "NO", "MEDIUM", "HIGH"],
        "applies_to": ["CREATE TABLE", "ALTER TABLE"],
        "description": "Column/table compression mode",
    },
    "time_capsule": {
        "syntax": "TIMECAPSULE TABLE name TO BEFORE { DROP [RENAME TO name] | TRUNCATE }",
        "applies_to": ["TIMECAPSULE"],
        "description": "Flashback table to before drop/truncate",
    },
    "purge": {
        "syntax": "PURGE { TABLE name | RECYCLEBIN }",
        "applies_to": ["PURGE"],
        "description": "Purge recyclebin entries",
    },
    "outline": {
        "syntax": "CREATE OUTLINE name FOR sql_hash USING outline_text",
        "applies_to": ["CREATE OUTLINE"],
        "description": "Query plan outline for SQL plan stabilization",
    },
    "explain_performance": {
        "syntax": "EXPLAIN PERFORMANCE [(options)] statement",
        "applies_to": ["EXPLAIN"],
        "description": "DWS-specific EXPLAIN with detailed performance metrics",
    },
    "explain_warmup": {
        "syntax": "EXPLAIN WARMUP warmup_option_name statement",
        "applies_to": ["EXPLAIN"],
        "description": "DWS-specific EXPLAIN WARMUP for plan cache warming",
    },
    "explain_plan": {
        "syntax": "EXPLAIN PLAN [SET STATEMENT_ID = string] FOR statement",
        "applies_to": ["EXPLAIN"],
        "description": "DWS-specific EXPLAIN PLAN for plan capture",
    },
    "merge": {
        "syntax": "MERGE [hint] INTO target USING source ON condition WHEN MATCHED THEN ... WHEN NOT MATCHED THEN ...",
        "applies_to": ["MERGE"],
        "description": "MERGE INTO statement (upsert pattern)",
    },
    "insert_overwrite": {
        "syntax": "INSERT OVERWRITE INTO table ...",
        "applies_to": ["INSERT"],
        "description": "INSERT OVERWRITE - replace existing data",
    },
    "replace_into": {
        "syntax": "REPLACE INTO table ...",
        "applies_to": ["INSERT"],
        "description": "REPLACE INTO (MySQL compatibility)",
    },
    "on_duplicate_key": {
        "syntax": "ON DUPLICATE KEY UPDATE col = val, ...",
        "applies_to": ["INSERT"],
        "description": "MySQL-style upsert",
    },
    "ora_joinop": {
        "syntax": "table1.column(+) = table2.column",
        "applies_to": ["SELECT", "UPDATE", "DELETE"],
        "description": "Oracle-style outer join operator (+)",
    },
    "hint_string": {
        "syntax": "/*+ hint_text */",
        "applies_to": ["SELECT", "INSERT", "UPDATE", "DELETE", "MERGE"],
        "description": "Optimizer hint comment",
    },
    "redaction_policy": {
        "syntax": "CREATE REDACTION POLICY name ON table ADD COLUMN col WITH mask_function",
        "applies_to": ["CREATE REDACTION POLICY"],
        "description": "Dynamic data redaction policy",
    },
    "rls_policy": {
        "syntax": "CREATE ROW LEVEL SECURITY POLICY name ON table USING (expr)",
        "applies_to": ["CREATE RLS POLICY"],
        "description": "Row-level security policy",
    },
    "resource_pool": {
        "syntax": "CREATE RESOURCE POOL name [WITH (options)]",
        "applies_to": ["CREATE RESOURCE POOL"],
        "description": "Resource pool for workload management",
    },
    "workload_group": {
        "syntax": "CREATE WORKLOAD GROUP name [USING RESOURCE POOL pool_name] [WITH (options)]",
        "applies_to": ["CREATE WORKLOAD GROUP"],
        "description": "Workload group for resource isolation",
    },
    "tablespace": {
        "syntax": "TABLESPACE tablespace_name",
        "applies_to": ["CREATE TABLE", "CREATE INDEX", "ALTER TABLE"],
        "description": "Tablespace assignment for table/index storage. Column-store v3 tables (orientation=column, colversion=3.0) may need TABLESPACE for OBS storage.",
    },
    "serial_types": {
        "syntax": "{ SERIAL | BIGSERIAL | SMALLSERIAL }",
        "valid_types": ["SERIAL", "BIGSERIAL", "SMALLSERIAL"],
        "applies_to": ["CREATE TABLE"],
        "description": "Auto-increment column types that cause GTM pressure in distributed environments",
    },
    "with_recursive": {
        "syntax": "WITH RECURSIVE cte_name AS (subquery) SELECT ...",
        "applies_to": ["SELECT"],
        "description": "Recursive CTE - must ensure termination condition to avoid infinite loops",
    },
}


# ============================================================
# Operator Precedence (low to high)
# ============================================================

OPERATOR_PRECEDENCE = [
    # (token_names, description, precedence_level)
    (["SET", "CLUSTER"], "Lowest precedence", 1),
    (["UNION", "EXCEPT", "MINUS"], "Set operations", 2),
    (["INTERSECT"], "Intersect", 3),
    (["OR"], "Logical OR", 4),
    (["AND"], "Logical AND", 5),
    (["NOT"], "Logical NOT", 6),
    (["=", "CmpOp"], "Comparison", 7),
    (["<", ">"], "Less/greater", 8),
    (["LIKE", "ILIKE", "SIMILAR"], "Pattern matching", 9),
    (["ESCAPE", "OVERLAPS", "BETWEEN", "IN"], "Range/membership", 10),
    (["Op", "OPERATOR"], "Generic operators", 11),
    (["NOTNULL", "ISNULL", "IS"], "Null tests", 12),
    (["+", "-"], "Addition/subtraction", 13),
    (["*", "/", "%"], "Multiplication/division/modulo", 14),
    (["^"], "Exponentiation", 15),
    (["AT", "COLLATE"], "Collation/timezone", 16),
    (["UMINUS"], "Unary minus", 17),
    (["TYPECAST", "."], "Typecast/field access", 18),
    (["JOIN", "CROSS", "LEFT", "FULL", "RIGHT", "INNER", "NATURAL"], "Join operators", 19),
]


# ============================================================
# Statement Type Detection Rules
# ============================================================

# Multi-token statement detection: (token_sequence, statement_type)
MULTI_TOKEN_STATEMENTS = [
    (["CREATE", "TEMP"], "CREATE TABLE"),
    (["CREATE", "TEMPORARY"], "CREATE TABLE"),
    (["CREATE", "TABLE"], "CREATE TABLE"),
    (["CREATE", "OR"], "CREATE VIEW"),  # CREATE OR REPLACE VIEW
    (["CREATE", "VIEW"], "CREATE VIEW"),
    (["CREATE", "MATERIALIZED"], "CREATE MATERIALIZED VIEW"),
    (["CREATE", "UNIQUE"], "CREATE INDEX"),
    (["CREATE", "INDEX"], "CREATE INDEX"),
    (["CREATE", "RESOURCE"], "CREATE RESOURCE POOL"),
    (["CREATE", "WORKLOAD"], "CREATE WORKLOAD GROUP"),
    (["CREATE", "NODE"], "CREATE NODE"),
    (["CREATE", "NODE", "GROUP"], "CREATE NODE GROUP"),
    (["CREATE", "OUTLINE"], "CREATE OUTLINE"),
    (["CREATE", "REDACTION"], "CREATE REDACTION POLICY"),
    (["CREATE", "ROW"], "CREATE RLS POLICY"),
    (["CREATE", "BARRIER"], "BARRIER"),
    (["CREATE", "FOREIGN"], "CREATE FOREIGN TABLE"),
    (["CREATE", "EXTERNAL"], "CREATE EXTERNAL SCHEMA"),
    (["ALTER", "TABLE"], "ALTER TABLE"),
    (["ALTER", "INDEX"], "ALTER TABLE"),
    (["ALTER", "SEQUENCE"], "ALTER TABLE"),
    (["ALTER", "VIEW"], "ALTER TABLE"),
    (["ALTER", "RESOURCE"], "ALTER RESOURCE POOL"),
    (["ALTER", "WORKLOAD"], "ALTER WORKLOAD GROUP"),
    (["ALTER", "NODE"], "ALTER NODE"),
    (["ALTER", "CLUSTER"], "ALTER CLUSTER"),
    (["ALTER", "SYSTEM"], "ALTER SYSTEM"),
    (["DROP", "TABLE"], "DROP"),
    (["DROP", "INDEX"], "DROP"),
    (["DROP", "VIEW"], "DROP"),
    (["DROP", "MATERIALIZED"], "DROP"),
    (["EXECUTE", "DIRECT"], "EXECUTE DIRECT"),
    (["CLEAN", "CONNECTION"], "CLEAN CONNECTION"),
    (["EXPLAIN", "PERFORMANCE"], "EXPLAIN"),
    (["EXPLAIN", "WARMUP"], "EXPLAIN"),
    (["EXPLAIN", "PLAN"], "EXPLAIN"),
]

# Single-token statement detection: (token, statement_type)
SINGLE_TOKEN_STATEMENTS = {
    "SELECT": "SELECT",
    "WITH": "SELECT",
    "INSERT": "INSERT",
    "REPLACE": "INSERT",
    "UPDATE": "UPDATE",
    "DELETE": "DELETE",
    "MERGE": "MERGE",
    "CREATE": "CREATE TABLE",  # default, may be overridden by multi-token
    "ALTER": "ALTER TABLE",   # default, may be overridden
    "DROP": "DROP",
    "TRUNCATE": "TRUNCATE",
    "EXPLAIN": "EXPLAIN",
    "COPY": "COPY",
    "VACUUM": "VACUUM",
    "ANALYZE": "VACUUM",
    "ANALYSE": "VACUUM",
    "GRANT": "GRANT",
    "REVOKE": "REVOKE",
    "SET": "SET",
    "SHOW": "SHOW",
    "RESET": "SET",
    "BEGIN": "BEGIN",
    "START": "BEGIN",
    "COMMIT": "COMMIT",
    "END": "COMMIT",
    "ROLLBACK": "ROLLBACK",
    "ABORT": "ROLLBACK",
    "SAVEPOINT": "BEGIN",
    "RELEASE": "BEGIN",
    "TIMECAPSULE": "TIMECAPSULE",
    "PURGE": "PURGE",
    "CALL": "CALL",
    "DECLARE": "ANONYMOUS BLOCK",
    "LOCK": "UTILITY",
    "UNLOCK": "UTILITY",
    "COMMENT": "UTILITY",
    "REINDEX": "UTILITY",
    "CLUSTER": "UTILITY",
    "DISCARD": "UTILITY",
    "LISTEN": "UTILITY",
    "NOTIFY": "UTILITY",
    "UNLISTEN": "UTILITY",
    "LOAD": "UTILITY",
    "DO": "ANONYMOUS BLOCK",
    "PREPARE": "UTILITY",
    "EXECUTE": "UTILITY",
    "DEALLOCATE": "UTILITY",
    "FETCH": "UTILITY",
    "CLOSE": "UTILITY",
    "CHECKPOINT": "UTILITY",
}


# ============================================================
# Clause Order Validation Rules
# ============================================================

SELECT_CLAUSE_ORDER = [
    "WITH", "SELECT", "FROM", "WHERE", "GROUP", "HAVING",
    "WINDOW", "ORDER", "LIMIT", "OFFSET", "FOR"
]

INSERT_CLAUSE_ORDER = [
    "WITH", "INSERT", "INTO", "VALUES", "SELECT", "ON", "RETURNING"
]

UPDATE_CLAUSE_ORDER = [
    "WITH", "UPDATE", "SET", "FROM", "WHERE", "RETURNING"
]

DELETE_CLAUSE_ORDER = [
    "WITH", "DELETE", "FROM", "USING", "WHERE", "RETURNING"
]

CLAUSE_ORDER_MAP = {
    "SELECT": SELECT_CLAUSE_ORDER,
    "INSERT": INSERT_CLAUSE_ORDER,
    "UPDATE": UPDATE_CLAUSE_ORDER,
    "DELETE": DELETE_CLAUSE_ORDER,
}
