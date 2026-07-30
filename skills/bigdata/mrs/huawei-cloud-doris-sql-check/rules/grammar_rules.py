# -*- coding: utf-8 -*-
"""
Apache Doris SQL Grammar Rules Definition
Source: Doris 3.1.4 Nereids ANTLR4 grammar (DorisParser.g4)
Covers 100+ Doris statement types, Doris-specific extensions, operator precedence
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
    DORIS_EXTENSION = "doris_extension"


# ============================================================
# Statement Type Definitions
# Based on DorisParser.g4 (Nereids grammar)
# ============================================================

STATEMENT_RULES = {
    # ---- DML Statements ----
    "SELECT": {
        "category": StatementCategory.DML,
        "start_tokens": ["SELECT", "WITH", "EXPLAIN"],
        "node_type": "SelectStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DORIS_EXTENSION, "tokens": ["/*+"], "description": "Optimizer hint"},
            "distinct": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DISTINCT", "ALL"], "description": "DISTINCT / ALL"},
            "target_list": {"requirement": ClauseRequirement.REQUIRED, "description": "Select target columns"},
            "from": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FROM"], "description": "FROM clause"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE condition"},
            "group_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["GROUP"], "next_tokens": ["BY"], "description": "GROUP BY"},
            "having": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["HAVING"], "description": "HAVING condition"},
            "order_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ORDER"], "next_tokens": ["BY"], "description": "ORDER BY"},
            "limit": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["LIMIT"], "description": "LIMIT count"},
            "offset": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["OFFSET"], "description": "OFFSET count"},
            "outfile": {"requirement": ClauseRequirement.DORIS_EXTENSION, "tokens": ["INTO"], "next_tokens": ["OUTFILE"], "description": "OUTFILE clause"},
        },
        "set_operations": ["UNION", "INTERSECT", "EXCEPT", "MINUS"],
        "clause_order": ["hint", "distinct", "target_list", "from", "where",
                         "group_by", "having", "order_by", "limit", "offset", "outfile"],
        "doris_extensions": ["hint_block", "backtick_identifier", "outfile_clause",
                             "tablesample", "cte", "window_function", "fulltext_match"],
        "grammar_bnf": """
# From DorisParser.g4 (Nereids)
query: cte? queryTerm outFileClause?
queryTerm: queryTerm (UNION|INTERSECT|EXCEPT|MINUS) ALL? queryTerm | queryPrimary
queryPrimary: querySpecification | subquery
querySpecification: selectHint? SELECT DISTINCT? selectClause fromClause? whereClause? aggClause? havingClause? sortClause? limitClause?
selectClause: selectColumnClause (',' selectColumnClause)*
fromClause: FROM relations
relations: relation (',' relation)*
relation: relationPrimary (joinRelation)*
""",
    },

    "INSERT": {
        "category": StatementCategory.DML,
        "start_tokens": ["INSERT"],
        "node_type": "InsertStmt",
        "clauses": {
            "hint": {"requirement": ClauseRequirement.DORIS_EXTENSION, "tokens": ["["], "description": "Bracket hint"},
            "overwrite": {"requirement": ClauseRequirement.DORIS_EXTENSION, "tokens": ["OVERWRITE"], "next_tokens": ["TABLE"], "description": "INSERT OVERWRITE TABLE"},
            "into": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["INTO"], "description": "INTO target table"},
            "table": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "partition": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PARTITION"], "description": "PARTITION spec"},
            "with_label": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "next_tokens": ["LABEL"], "description": "WITH LABEL"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column list in parentheses"},
            "values": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["VALUES"], "description": "VALUES clause"},
            "select": {"requirement": ClauseRequirement.OPTIONAL, "description": "SELECT subquery"},
            "cte": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "CTE"},
        },
        "clause_order": ["hint", "overwrite", "into", "table", "partition", "with_label", "columns", "cte", "values", "select"],
        "doris_extensions": ["overwrite_table", "with_label", "partition_spec"],
        "grammar_bnf": """
# From DorisParser.g4 #insertTable
INSERT (INTO | OVERWRITE TABLE) tableName=multipartIdentifier
    (partitionSpec)? (WITH LABEL labelName=identifier)? identifierList?
    (LEFT_BRACKET hints=identifierSeq RIGHT_BRACKET)?
    (query)?
""",
    },

    "UPDATE": {
        "category": StatementCategory.DML,
        "start_tokens": ["UPDATE"],
        "node_type": "UpdateStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.REQUIRED, "description": "Target table"},
            "table_alias": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["AS"], "description": "Table alias"},
            "set": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["SET"], "description": "SET col=val"},
            "from": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FROM"], "description": "FROM clause"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE"},
            "cte": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "CTE"},
        },
        "clause_order": ["table", "table_alias", "set", "from", "where", "cte"],
        "grammar_bnf": "UPDATE tableName=multipartIdentifier tableAlias? SET assignmentList fromClause? whereClause?",
    },

    "DELETE": {
        "category": StatementCategory.DML,
        "start_tokens": ["DELETE"],
        "node_type": "DeleteStmt",
        "clauses": {
            "from": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FROM"], "description": "FROM target table"},
            "table_alias": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["AS"], "description": "Table alias"},
            "using": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["USING"], "description": "USING clause"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE"},
            "cte": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "description": "CTE"},
        },
        "clause_order": ["from", "table_alias", "using", "where", "cte"],
        "grammar_bnf": "DELETE FROM tableName=multipartIdentifier tableAlias? usingClause? whereClause?",
    },

    "LOAD": {
        "category": StatementCategory.DML,
        "start_tokens": ["LOAD"],
        "node_type": "LoadStmt",
        "clauses": {
            "label": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["LABEL"], "description": "LOAD LABEL"},
            "data_desc": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["DATA"], "description": "DATA INFILE/FROM TABLE"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
        },
        "clause_order": ["label", "data_desc", "properties", "comment"],
        "doris_extensions": ["broker_load", "merge_type", "delete_on", "sequence_col"],
        "grammar_bnf": """
# From DorisParser.g4 #load
LOAD LABEL labelName=multipartIdentifier LEFT_PAREN dataDescs+=dataDesc (COMMA dataDescs+=dataDesc)* RIGHT_PAREN
    propertyClause? commentSpec?
dataDesc: DATA INFILE '(' file=constant (',' file=constant)* ')' INTO TABLE target
    (mergeType)? (columns=identifierList)? (columnMapping=columnMappingList)?
    (preFilter=preFilterClause)? (where=whereClause)? (deleteOn=deleteOnClause)? (sequenceCol=sequenceColClause)?
""",
    },

    "EXPORT": {
        "category": StatementCategory.DML,
        "start_tokens": ["EXPORT"],
        "node_type": "ExportStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TABLE"], "description": "EXPORT TABLE"},
            "partition": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PARTITION"], "description": "PARTITION spec"},
            "where": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WHERE"], "description": "WHERE"},
            "to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "description": "TO path"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
            "broker": {"requirement": ClauseRequirement.OPTIONAL, "description": "WITH REMOTE STORAGE SYSTEM"},
        },
        "clause_order": ["table", "partition", "where", "to", "properties", "broker"],
        "grammar_bnf": "EXPORT TABLE tableName=multipartIdentifier (PARTITION partition=identifierList)? (whereClause)? TO filePath=constant (propertyClause)? (withRemoteStorageSystem)?",
    },

    "COPY_INTO": {
        "category": StatementCategory.DML,
        "start_tokens": ["COPY"],
        "node_type": "CopyIntoStmt",
        "doris_extensions": ["stage_pattern"],
        "grammar_bnf": "COPY INTO target=multipartIdentifier FROM stageAndPattern (FILES FROM ...)? (PROPERTIES ...)?",
    },

    "TRUNCATE": {
        "category": StatementCategory.DML,
        "start_tokens": ["TRUNCATE"],
        "node_type": "TruncateStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TABLE"], "description": "TRUNCATE TABLE"},
            "partition": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PARTITION"], "description": "PARTITION spec"},
        },
        "clause_order": ["table", "partition"],
        "grammar_bnf": "TRUNCATE TABLE tableName=multipartIdentifier (PARTITION partition=identifierList)?",
    },

    # ---- DDL Statements ----
    "CREATE_TABLE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateStmt",
        "clauses": {
            "if_not_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "next_tokens": ["NOT", "EXISTS"], "description": "IF NOT EXISTS"},
            "table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TABLE"], "description": "TABLE"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "columns": {"requirement": ClauseRequirement.REQUIRED, "description": "Column definitions"},
            "indexes": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["INDEX"], "description": "Index definitions"},
            "engine": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ENGINE"], "description": "ENGINE"},
            "key_model": {"requirement": ClauseRequirement.DORIS_EXTENSION, "tokens": ["DUPLICATE", "AGGREGATE", "UNIQUE"], "next_tokens": ["KEY"], "description": "DUPLICATE/AGGREGATE/UNIQUE KEY"},
            "cluster_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["CLUSTER"], "next_tokens": ["BY"], "description": "CLUSTER BY"},
            "partition_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PARTITION"], "next_tokens": ["BY"], "description": "PARTITION BY"},
            "distributed_by": {"requirement": ClauseRequirement.DORIS_EXTENSION, "tokens": ["DISTRIBUTED"], "next_tokens": ["BY"], "description": "DISTRIBUTED BY HASH/RANDOM"},
            "buckets": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["BUCKETS"], "description": "BUCKETS n or AUTO"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
            "ctas_query": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["AS"], "description": "CREATE TABLE AS SELECT"},
        },
        "clause_order": ["if_not_exists", "table", "table_name", "columns", "indexes",
                         "engine", "key_model", "cluster_by", "partition_by",
                         "distributed_by", "buckets", "properties", "comment", "ctas_query"],
        "doris_extensions": ["distributed_by", "buckets", "key_model", "cluster_by",
                             "properties", "engine", "colocate_group"],
        "valid_distribution_strategies": ["HASH", "RANDOM"],
        "valid_partition_types": ["RANGE", "LIST", "AUTO"],
        "valid_key_models": ["DUPLICATE", "AGGREGATE", "UNIQUE"],
        "valid_engines": ["OLAP", "MYSQL", "ELASTICSEARCH", "HIVE", "HUDI",
                          "ICEBERG", "JDBC", "BROKER", "ODBC"],
        "grammar_bnf": """
# From DorisParser.g4 #createTable
CREATE (TEMPORARY)? TABLE (IF NOT EXISTS)? name=multipartIdentifier
    (LEFT_PAREN colDefs+=columnDef (COMMA colDefs+=columnDef)* (COMMA indexDefs+=indexDef)* (COMMA constraints+=constraint)* RIGHT_PAREN)
    (ENGINE EQ engine=identifier)?
    ((DUPLICATE | AGGREGATE | UNIQUE) KEY keys=identifierList (CLUSTER BY clusterKeys=identifierList)?)?
    (partitionTable)?
    (DISTRIBUTED BY (HASH hashKeys=identifierList | RANDOM) (BUCKETS (INTEGER_VALUE | autoBucket=AUTO))?)?
    propertyClause? commentSpec?
    (AS query)?
""",
    },

    "CREATE_TABLE_LIKE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateStmt",
        "grammar_bnf": "CREATE (TEMPORARY)? TABLE (IF NOT EXISTS)? name=identifier LIKE likeTable=identifier",
    },

    "CREATE_VIEW": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "ViewStmt",
        "clauses": {
            "or_replace": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["OR", "REPLACE"], "description": "CREATE OR REPLACE"},
            "view": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["VIEW"], "description": "VIEW"},
            "view_name": {"requirement": ClauseRequirement.REQUIRED, "description": "View name"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column list"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
            "as": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["AS"], "description": "AS query"},
        },
        "clause_order": ["or_replace", "view", "view_name", "columns", "comment", "as"],
        "grammar_bnf": "CREATE (OR REPLACE)? VIEW name=multipartIdentifier identifierList? (COMMENT comment=STRING_LITERAL)? AS query",
    },

    "CREATE_MTMV": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateMTMVStmt",
        "clauses": {
            "materialized": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["MATERIALIZED"], "next_tokens": ["VIEW"], "description": "MATERIALIZED VIEW"},
            "name": {"requirement": ClauseRequirement.REQUIRED, "description": "MTMV name"},
            "columns": {"requirement": ClauseRequirement.OPTIONAL, "description": "Column list"},
            "key_model": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DUPLICATE"], "next_tokens": ["KEY"], "description": "DUPLICATE KEY"},
            "partition_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PARTITION"], "description": "PARTITION BY"},
            "distributed_by": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DISTRIBUTED"], "description": "DISTRIBUTED BY"},
            "build_mode": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["BUILD"], "description": "BUILD IMMEDIATE/DEFERRED"},
            "refresh_method": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["REFRESH"], "description": "REFRESH COMPLETE/AUTO"},
            "refresh_trigger": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ON"], "description": "ON MANUAL/SCHEDULE/COMMIT"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
            "as": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["AS"], "description": "AS query"},
        },
        "clause_order": ["materialized", "name", "columns", "key_model", "partition_by",
                         "distributed_by", "build_mode", "refresh_method", "refresh_trigger",
                         "properties", "comment", "as"],
        "doris_extensions": ["mtmv_build_mode", "mtmv_refresh", "mtmv_partition"],
        "valid_build_modes": ["IMMEDIATE", "DEFERRED"],
        "valid_refresh_methods": ["COMPLETE", "AUTO"],
        "valid_refresh_triggers": ["MANUAL", "SCHEDULE", "COMMIT"],
        "grammar_bnf": """
# From DorisParser.g4 #createMTMV
CREATE MATERIALIZED VIEW name=multipartIdentifier identifierList? (DUPLICATE KEY keys=identifierList)?
    partitionTable? (DISTRIBUTED BY (HASH hashKeys=identifierList | RANDOM) (BUCKETS ...)?)?
    (BUILD (IMMEDIATE|DEFERRED))? (REFRESH (COMPLETE|AUTO))?
    refreshTrigger? propertyClause? (COMMENT ...)? (AS? query)?
""",
    },

    "CREATE_INDEX": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "IndexStmt",
        "clauses": {
            "index": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["INDEX"], "description": "INDEX"},
            "index_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Index name"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON table"},
            "columns": {"requirement": ClauseRequirement.REQUIRED, "description": "Column list"},
            "using": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["USING"], "description": "USING BITMAP/NGRAM_BF/INVERTED"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
        },
        "valid_index_types": ["BITMAP", "NGRAM_BF", "INVERTED"],
        "grammar_bnf": "CREATE INDEX indexName=identifier ON tableName=multipartIdentifier identifierList (USING (BITMAP|NGRAM_BF|INVERTED))? propertyClause?",
    },

    "ALTER_TABLE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["ALTER"],
        "node_type": "AlterTableStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TABLE"], "description": "TABLE"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "actions": {"requirement": ClauseRequirement.REQUIRED, "description": "ALTER actions"},
        },
        "valid_actions": [
            "ADD_COLUMN", "ADD_COLUMNS", "DROP_COLUMN", "MODIFY_COLUMN", "REORDER_COLUMNS",
            "ADD_PARTITION", "DROP_PARTITION", "MODIFY_PARTITION", "REPLACE_PARTITION",
            "ADD_TEMPORARY_PARTITIONS", "ALTER_MULTI_PARTITION",
            "RENAME", "RENAME_ROLLUP", "RENAME_PARTITION", "RENAME_COLUMN",
            "ADD_INDEX", "DROP_INDEX",
            "ENABLE_FEATURE", "MODIFY_DISTRIBUTION", "MODIFY_ENGINE",
            "MODIFY_TABLE_COMMENT", "MODIFY_COLUMN_COMMENT",
            "CREATE_REPLACE_TAG", "CREATE_REPLACE_BRANCH", "DROP_BRANCH", "DROP_TAG",
            "SET_PROPERTIES",
        ],
        "doris_extensions": ["rollup", "tag_branch", "modify_distribution", "modify_engine"],
        "grammar_bnf": "ALTER TABLE tableName=multipartIdentifier alterTableClause (',' alterTableClause)*",
    },

    "DROP_TABLE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["DROP"],
        "node_type": "DropStmt",
        "clauses": {
            "table": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TABLE"], "description": "TABLE"},
            "if_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "next_tokens": ["EXISTS"], "description": "IF EXISTS"},
            "table_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Table name"},
            "force": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["FORCE"], "description": "FORCE"},
        },
        "clause_order": ["table", "if_exists", "table_name", "force"],
        "grammar_bnf": "DROP TABLE (IF EXISTS)? tableName=multipartIdentifier FORCE?",
    },

    "DROP_VIEW": {
        "category": StatementCategory.DDL,
        "start_tokens": ["DROP"],
        "node_type": "DropStmt",
        "grammar_bnf": "DROP VIEW (IF EXISTS)? viewName=multipartIdentifier",
    },

    "DROP_INDEX": {
        "category": StatementCategory.DDL,
        "start_tokens": ["DROP"],
        "node_type": "DropStmt",
        "grammar_bnf": "DROP INDEX indexName=identifier ON tableName=multipartIdentifier",
    },

    "CREATE_DATABASE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateDbStmt",
        "clauses": {
            "database": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["DATABASE", "SCHEMA"], "description": "DATABASE/SCHEMA"},
            "if_not_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "description": "IF NOT EXISTS"},
            "db_name": {"requirement": ClauseRequirement.REQUIRED, "description": "Database name"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
        },
        "grammar_bnf": "CREATE (DATABASE|SCHEMA) (IF NOT EXISTS)? name=identifier propertyClause?",
    },

    "CREATE_CATALOG": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateCatalogStmt",
        "clauses": {
            "catalog": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["CATALOG"], "description": "CATALOG"},
            "if_not_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "description": "IF NOT EXISTS"},
            "name": {"requirement": ClauseRequirement.REQUIRED, "description": "Catalog name"},
            "with_resource": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["WITH"], "next_tokens": ["RESOURCE"], "description": "WITH RESOURCE"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
        },
        "grammar_bnf": "CREATE CATALOG (IF NOT EXISTS)? catalogName=identifier (WITH RESOURCE resourceName=identifier)? (COMMENT ...)? propertyClause?",
    },

    "CREATE_USER": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateUserStmt",
        "clauses": {
            "user": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["USER"], "description": "USER"},
            "if_not_exists": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["IF"], "description": "IF NOT EXISTS"},
            "user_name": {"requirement": ClauseRequirement.REQUIRED, "description": "User name"},
            "superuser": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["SUPERUSER"], "description": "SUPERUSER"},
            "default_role": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["DEFAULT"], "next_tokens": ["ROLE"], "description": "DEFAULT ROLE"},
            "password": {"requirement": ClauseRequirement.REQUIRED, "description": "Password option"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
        },
        "doris_extensions": ["password_policy", "account_lock"],
        "grammar_bnf": "CREATE USER (IF NOT EXISTS)? grantUserIdentify (SUPERUSER | DEFAULT ROLE ...)? passwordOption* (COMMENT ...)?",
    },

    "CREATE_ROLE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateRoleStmt",
        "grammar_bnf": "CREATE ROLE (IF NOT EXISTS)? name=identifier (COMMENT ...)?",
    },

    "CREATE_RESOURCE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateResourceStmt",
        "grammar_bnf": "CREATE RESOURCE (IF NOT EXISTS)? name=identifier (WITH RESOURCE ...)? propertyClause?",
    },

    "CREATE_STAGE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateStageStmt",
        "grammar_bnf": "CREATE STAGE (IF NOT EXISTS)? name=identifier propertyClause?",
    },

    "CREATE_ENCRYPTKEY": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateEncryptKeyStmt",
        "grammar_bnf": "CREATE ENCRYPTKEY (IF NOT EXISTS)? multipartIdentifier AS STRING_LITERAL",
    },

    "CREATE_JOB": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateJobStmt",
        "clauses": {
            "job": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["JOB"], "description": "JOB"},
            "name": {"requirement": ClauseRequirement.REQUIRED, "description": "Job name"},
            "on_schedule": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "next_tokens": ["SCHEDULE"], "description": "ON SCHEDULE"},
            "schedule": {"requirement": ClauseRequirement.REQUIRED, "description": "EVERY ... / AT ..."},
            "do": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["DO"], "description": "DO dml statement"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
        },
        "doris_extensions": ["scheduled_job", "cron_expr"],
        "grammar_bnf": "CREATE JOB label ON SCHEDULE (EVERY timeUnit (STARTS ...)? (ENDS ...)?) | AT time) commentSpec? DO supportedDmlStatement",
    },

    "CREATE_ROW_POLICY": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateRowPolicyStmt",
        "clauses": {
            "policy": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ROW", "POLICY"], "description": "ROW POLICY"},
            "name": {"requirement": ClauseRequirement.REQUIRED, "description": "Policy name"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON table"},
            "as": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["AS"], "description": "AS RESTRICTIVE/PERMISSIVE"},
            "to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "description": "TO user/ROLE"},
            "using": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["USING"], "description": "USING boolean expression"},
        },
        "valid_policy_types": ["RESTRICTIVE", "PERMISSIVE"],
        "grammar_bnf": "CREATE ROW POLICY name ON table AS (RESTRICTIVE|PERMISSIVE) TO (user|ROLE ...) USING (booleanExpression)",
    },

    "CREATE_SQL_BLOCK_RULE": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateSqlBlockRuleStmt",
        "grammar_bnf": "CREATE SQL_BLOCK_RULE name=identifier propertyClause?",
    },

    "CREATE_STORAGE_VAULT": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateStorageVaultStmt",
        "grammar_bnf": "CREATE STORAGE VAULT name=identifier propertyClause?",
    },

    "CREATE_WORKLOAD_GROUP": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateWorkloadGroupStmt",
        "grammar_bnf": "CREATE WORKLOAD GROUP name=identifier propertyClause?",
    },

    "CREATE_WORKLOAD_POLICY": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateWorkloadPolicyStmt",
        "grammar_bnf": "CREATE WORKLOAD POLICY name=identifier propertyClause?",
    },

    "CREATE_REPOSITORY": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateRepositoryStmt",
        "grammar_bnf": "CREATE REPOSITORY name=identifier WITH broker=identifier ON LOCATION ... propertyClause?",
    },

    "CREATE_FUNCTION": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateFunctionStmt",
        "grammar_bnf": "CREATE (OR REPLACE)? FUNCTION name=identifier (LEFT_PAREN ... RIGHT_PAREN)? RETURNS ... (LANGUAGE ...)? (WITH ...)? (USING ...)?",
    },

    # ---- DCL Statements ----
    "GRANT": {
        "category": StatementCategory.DCL,
        "start_tokens": ["GRANT"],
        "node_type": "GrantStmt",
        "clauses": {
            "privileges": {"requirement": ClauseRequirement.REQUIRED, "description": "Privilege list"},
            "on": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ON"], "description": "ON object"},
            "to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "description": "TO user/ROLE"},
        },
        "valid_privileges": ["SELECT", "INSERT", "UPDATE", "DELETE", "LOAD", "EXPORT",
                             "ALTER", "CREATE", "DROP", "USAGE", "SHOW", "ALL"],
        "valid_resource_types": ["RESOURCE", "CLUSTER", "COMPUTE", "GROUP", "STAGE",
                                 "STORAGE", "VAULT", "WORKLOAD", "CATALOG"],
        "grammar_bnf": """
# From DorisParser.g4 #grantTablePrivilege / #grantResourcePrivilege / #grantRole
GRANT privilegeList ON multipartIdentifierOrAsterisk TO (user | ROLE ...)
GRANT privilegeList ON (RESOURCE | CLUSTER | COMPUTE GROUP | STAGE | STORAGE VAULT | WORKLOAD GROUP) name TO ...
GRANT roles TO user
""",
    },

    "REVOKE": {
        "category": StatementCategory.DCL,
        "start_tokens": ["REVOKE"],
        "node_type": "RevokeStmt",
        "grammar_bnf": "REVOKE privilegeList ON ... FROM (user | ROLE ...) | REVOKE roles FROM user",
    },

    # ---- TCL Statements ----
    "BEGIN": {
        "category": StatementCategory.TCL,
        "start_tokens": ["BEGIN", "START"],
        "node_type": "TransactionStmt",
        "grammar_bnf": "BEGIN | START TRANSACTION (WITH ...)?",
    },

    "COMMIT": {
        "category": StatementCategory.TCL,
        "start_tokens": ["COMMIT"],
        "node_type": "TransactionStmt",
        "grammar_bnf": "COMMIT (AND CHAIN)?",
    },

    "ROLLBACK": {
        "category": StatementCategory.TCL,
        "start_tokens": ["ROLLBACK"],
        "node_type": "TransactionStmt",
        "grammar_bnf": "ROLLBACK (AND CHAIN)?",
    },

    # ---- Utility Statements ----
    "EXPLAIN": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["EXPLAIN", "DESC", "DESCRIBE"],
        "node_type": "ExplainStmt",
        "clauses": {
            "plan_type": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PARSED", "ANALYZED", "REWRITTEN", "LOGICAL", "OPTIMIZED", "PHYSICAL", "SHAPE", "MEMO", "DISTRIBUTED", "ALL"], "description": "Plan type"},
            "level": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["VERBOSE", "TREE", "GRAPH", "PLAN", "DUMP"], "description": "Explain level"},
            "process": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROCESS"], "description": "PROCESS flag"},
            "statement": {"requirement": ClauseRequirement.REQUIRED, "description": "Analyzed statement"},
        },
        "valid_plan_types": ["PARSED", "ANALYZED", "REWRITTEN", "LOGICAL",
                              "OPTIMIZED", "PHYSICAL", "SHAPE", "MEMO", "DISTRIBUTED", "ALL"],
        "valid_levels": ["VERBOSE", "TREE", "GRAPH", "PLAN", "DUMP"],
        "grammar_bnf": "explainCommand planType? level=(VERBOSE|TREE|GRAPH|PLAN|DUMP)? PROCESS? query",
    },

    "DESCRIBE": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["DESC", "DESCRIBE"],
        "node_type": "DescribeStmt",
        "grammar_bnf": "DESCRIBE multipartIdentifier | DESCRIBE ... ALL | DESCRIBE FUNCTION ...",
    },

    "SET": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["SET"],
        "node_type": "SetStmt",
        "clauses": {
            "variable": {"requirement": ClauseRequirement.REQUIRED, "description": "Variable name"},
            "value": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO", "EQ"], "description": "Value"},
        },
        "doris_extensions": ["set_session_variable", "set_user_property",
                             "set_default_storage_vault", "set_transaction"],
        "grammar_bnf": "SET (GLOBAL | SESSION | LOCAL)? variable (TO | EQ) value | SET DEFAULT STORAGE VAULT name | SET TRANSACTION ...",
    },

    "SHOW": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["SHOW"],
        "node_type": "ShowStmt",
        "valid_show_types": [
            "DATABASES", "TABLES", "COLUMNS", "VIEWS", "PROCESSLIST", "STATUS",
            "VARIABLES", "CREATE TABLE", "CREATE VIEW", "CREATE DATABASE",
            "CREATE CATALOG", "CREATE FUNCTION", "LOAD", "EXPORT", "DATA",
            "PARTITIONS", "TABLETS", "BACKENDS", "FRONTENDS", "BROKER",
            "REPOSITORIES", "SNAPSHOT", "REPLICA", "COPY", "GRANTS", "ROLES",
            "PRIVILEGES", "FUNCTIONS", "ENGINES", "STAGES", "ENCRYPTKEYS",
            "BUILD INDEX", "CLUSTERS", "CONVERT_LSC", "WARM UP", "QUERY PROFILE",
            "MTMV", "JOB", "ROW POLICY", "SQL_BLOCK_RULE", "INDEX",
            "STORAGE VAULT", "WORKLOAD GROUP", "WORKLOAD POLICY", "TABLE CREATION",
            "STORAGE ENGINES", "CACHE HOTSPOT", "TABLET", "TABLETS BELONG",
            "VIEW", "TRIGGERS", "REPLICA DISTRIBUTION", "REPLICA STATUS",
            "REPLICA DIAGNOSIS", "TABLE STORAGE FORMAT", "ANALYZE",
        ],
        "grammar_bnf": "SHOW (various sub-types - 50+ variants)",
    },

    "ADMIN": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["ADMIN"],
        "node_type": "AdminStmt",
        "valid_admin_actions": [
            "SET_REPLICA_STATUS", "SET_REPLICA_VERSION", "SET_PARTITION_VERSION",
            "SET_FRONTEND_CONFIG", "SET_TABLE_STATUS", "SET_ENCRYPTION_ROOT_KEY",
            "SHOW_REPLICA_STATUS", "SHOW_REPLICA_DISTRIBUTION", "SHOW_TABLET_STORAGE_FORMAT",
            "SHOW_TABLET_DIAGNOSE", "SHOW_FRONTEND_CONFIG", "COPY_TABLET",
            "REPAIR_TABLE", "CANCEL_REPAIR_TABLE", "COMPACT_TABLE",
            "CHECK_TABLETS", "REBALANCE_DISK", "CANCEL_REBALANCE_DISK",
            "CLEAN_TRASH", "ROTATE_TDE_ROOT_KEY", "SET_CONFIG", "SHOW_CONFIG",
        ],
        "grammar_bnf": "ADMIN SET/SHOW ... (50+ variants)",
    },

    "KILL": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["KILL"],
        "node_type": "KillStmt",
        "valid_kill_types": ["CONNECTION", "QUERY"],
        "grammar_bnf": "KILL (CONNECTION | QUERY)? connectionId=INTEGER_VALUE",
    },

    "CANCEL": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["CANCEL"],
        "node_type": "CancelStmt",
        "valid_cancel_types": ["LOAD", "EXPORT", "ALTER TABLE", "BUILD INDEX",
                                "DECOMMISSION BACKEND", "BACKUP", "RESTORE",
                                "WARM UP", "MTMV TASK"],
        "grammar_bnf": "CANCEL LOAD/EXPORT/ALTER TABLE/BACKUP/RESTORE/WARM UP/MTMV TASK ...",
    },

    "BACKUP": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["BACKUP"],
        "node_type": "BackupStmt",
        "clauses": {
            "snapshot": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["SNAPSHOT"], "description": "SNAPSHOT name"},
            "to": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["TO"], "description": "TO repository"},
            "on": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ON"], "description": "ON tables"},
            "exclude": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["EXCLUDE"], "description": "EXCLUDE tables"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
        },
        "clause_order": ["snapshot", "to", "on", "exclude", "properties"],
        "grammar_bnf": "BACKUP SNAPSHOT labelName=identifier TO repoName=identifier (ON|EXCLUDE (baseTableRef,...))? propertyClause?",
    },

    "RESTORE": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["RESTORE"],
        "node_type": "RestoreStmt",
        "clauses": {
            "snapshot": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["SNAPSHOT"], "description": "SNAPSHOT name"},
            "from": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FROM"], "description": "FROM repository"},
            "on": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["ON"], "description": "ON tables"},
            "exclude": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["EXCLUDE"], "description": "EXCLUDE tables"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
        },
        "clause_order": ["snapshot", "from", "on", "exclude", "properties"],
        "grammar_bnf": "RESTORE SNAPSHOT labelName=identifier FROM repoName=identifier (ON|EXCLUDE (baseTableRef,...))? propertyClause?",
    },

    "RECOVER": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["RECOVER"],
        "node_type": "RecoverStmt",
        "valid_recover_types": ["DATABASE", "TABLE", "PARTITION"],
        "grammar_bnf": "RECOVER (DATABASE | TABLE | PARTITION) ...",
    },

    "CLEAN": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["CLEAN"],
        "node_type": "CleanStmt",
        "valid_clean_types": ["LABEL", "ALL PROFILE", "QUERY STATS", "ALL QUERY STATS"],
        "grammar_bnf": "CLEAN (LABEL | ALL PROFILE | QUERY STATS | ALL QUERY STATS) ...",
    },

    "INSTALL_PLUGIN": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["INSTALL"],
        "node_type": "InstallPluginStmt",
        "grammar_bnf": "INSTALL PLUGIN name=identifier FROM source=identifier",
    },

    "UNINSTALL_PLUGIN": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["UNINSTALL"],
        "node_type": "UninstallPluginStmt",
        "grammar_bnf": "UNINSTALL PLUGIN name=identifier",
    },

    "LOCK_TABLES": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["LOCK"],
        "node_type": "LockTablesStmt",
        "grammar_bnf": "LOCK TABLES lockTable (',' lockTable)* | UNLOCK TABLES",
    },

    "USE": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["USE"],
        "node_type": "UseStmt",
        "grammar_bnf": "USE database=identifier | USE CATALOG catalogName=identifier | USE cloudClusterName=identifier",
    },

    "SWITCH": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["SWITCH"],
        "node_type": "SwitchStmt",
        "grammar_bnf": "SWITCH catalogName=identifier",
    },

    "CALL": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["CALL"],
        "node_type": "CallStmt",
        "grammar_bnf": "CALL name=identifier LEFT_PAREN (expression (',' expression)*)? RIGHT_PAREN",
    },

    "HELP": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["HELP"],
        "node_type": "HelpStmt",
        "grammar_bnf": "HELP identifier",
    },

    "SYNC": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["SYNC"],
        "node_type": "SyncStmt",
        "grammar_bnf": "SYNC",
    },

    "WARM_UP": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["WARM"],
        "node_type": "WarmUpStmt",
        "grammar_bnf": "WARM UP (CLUSTER clusterName=identifier)? warmUpItem (',' warmUpItem)*",
    },

    "PAUSE": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["PAUSE"],
        "node_type": "PauseStmt",
        "valid_pause_types": ["ROUTINE LOAD", "MTMV", "JOB"],
        "grammar_bnf": "PAUSE (ROUTINE LOAD | MATERIALIZED VIEW | JOB) ...",
    },

    "RESUME": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["RESUME"],
        "node_type": "ResumeStmt",
        "valid_resume_types": ["ROUTINE LOAD", "MTMV", "JOB"],
        "grammar_bnf": "RESUME (ROUTINE LOAD | MATERIALIZED VIEW | JOB) ...",
    },

    "STOP_ROUTINE_LOAD": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["STOP"],
        "node_type": "StopRoutineLoadStmt",
        "grammar_bnf": "STOP ROUTINE LOAD jobName=identifier",
    },

    "REFRESH": {
        "category": StatementCategory.UTILITY,
        "start_tokens": ["REFRESH"],
        "node_type": "RefreshStmt",
        "valid_refresh_types": ["TABLE", "DATABASE", "CATALOG", "LDAP", "MTMV"],
        "grammar_bnf": "REFRESH (TABLE | DATABASE | CATALOG | LDAP | MATERIALIZED VIEW) ...",
    },

    "ALTER_COLOCATE_GROUP": {
        "category": StatementCategory.DDL,
        "start_tokens": ["ALTER"],
        "node_type": "AlterColocateGroupStmt",
        "grammar_bnf": "ALTER COLOCATE GROUP name=identifier SET propertyClause",
    },

    "ROUTINE_LOAD": {
        "category": StatementCategory.DDL,
        "start_tokens": ["CREATE"],
        "node_type": "CreateRoutineLoadStmt",
        "clauses": {
            "routine_load": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["ROUTINE", "LOAD"], "description": "ROUTINE LOAD"},
            "name": {"requirement": ClauseRequirement.REQUIRED, "description": "Job name"},
            "from": {"requirement": ClauseRequirement.REQUIRED, "tokens": ["FROM"], "description": "FROM type"},
            "properties": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["PROPERTIES"], "description": "PROPERTIES"},
            "comment": {"requirement": ClauseRequirement.OPTIONAL, "tokens": ["COMMENT"], "description": "Comment"},
        },
        "doris_extensions": ["routine_load_properties", "kafka_properties", "merge_type"],
        "grammar_bnf": """
# From DorisParser.g4 #createRoutineLoadJob
CREATE ROUTINE LOAD name=identifier ON table=multipartIdentifier
    (loadProperty (',' loadProperty)*)?
    (FROM type=identifier LEFT_PAREN kafkaPropertyList RIGHT_PAREN)?
    propertyClause? commentSpec?
""",
    },
}


# ============================================================
# Operator Precedence (from DorisParser.g4)
# ============================================================
OPERATOR_PRECEDENCE = [
    # (level, operators, associativity)
    (1, ["OR"], "left"),
    (2, ["XOR"], "left"),
    (3, ["AND"], "left"),
    (4, ["NOT"], "unary"),
    (5, ["LOGICALAND", "LOGICALNOT"], "left"),
    (6, ["IN", "BETWEEN", "LIKE", "RLIKE", "REGEXP",
         "IS", "ISNULL", "IS_NULL_PRED", "IS_NOT_NULL_PRED"], "left"),
    (7, ["MATCH_ALL", "MATCH_ANY", "MATCH_PHRASE", "MATCH_PHRASE_PREFIX",
         "MATCH_PHRASE_EDGE", "MATCH_REGEXP", "MATCH_NAME", "MATCH_NAME_GLOB"], "left"),
    (8, ["<", "<=", ">", ">=", "=", "==", "<>", "!="], "left"),
    (9, ["BITOR", "|"], "left"),
    (10, ["BITAND", "&"], "left"),
    (11, ["^"], "left"),
    (12, ["+", "-"], "left"),
    (13, ["*", "/", "DIV", "%", "MOD"], "left"),
    (14, ["->"], "left"),
    (15, ["UMINUS", "UPLUS", "UTILDE"], "unary"),
    (16, ["CAST", "EXTRACT", "POSITION"], "left"),
]


# ============================================================
# Doris Data Types
# ============================================================
DORIS_DATA_TYPES = {
    # Integer types
    "TINYINT": {"size": 1, "signed": True, "category": "integer"},
    "SMALLINT": {"size": 2, "signed": True, "category": "integer"},
    "INT": {"size": 4, "signed": True, "category": "integer", "alias": "INTEGER"},
    "INTEGER": {"size": 4, "signed": True, "category": "integer"},
    "BIGINT": {"size": 8, "signed": True, "category": "integer"},
    "LARGEINT": {"size": 16, "signed": False, "category": "integer"},  # Doris-specific
    # Boolean
    "BOOLEAN": {"size": 1, "category": "boolean"},
    # Floating point
    "FLOAT": {"size": 4, "category": "float"},
    "DOUBLE": {"size": 8, "category": "float"},
    "REAL": {"size": 8, "category": "float", "alias": "DOUBLE"},
    # Decimal
    "DECIMAL": {"category": "decimal"},
    "DECIMALV2": {"category": "decimal", "precision": 27, "scale": 9},
    "DECIMALV3": {"category": "decimal"},
    # Date/Time
    "DATE": {"category": "date"},
    "DATETIME": {"category": "datetime"},
    "DATEV2": {"category": "date", "doris_specific": True},
    "DATETIMEV2": {"category": "datetime", "doris_specific": True},
    "DATEV1": {"category": "date", "doris_specific": True},
    "DATETIMEV1": {"category": "datetime", "doris_specific": True},
    "TIME": {"category": "time"},
    # String
    "CHAR": {"category": "string", "fixed_length": True},
    "VARCHAR": {"category": "string"},
    "STRING": {"category": "string"},
    "TEXT": {"category": "string"},
    # JSON
    "JSON": {"category": "json"},
    "JSONB": {"category": "json", "doris_specific": True, "binary": True},
    # Bitmap / HLL / Quantile
    "BITMAP": {"category": "bitmap", "doris_specific": True},
    "HLL": {"category": "hll", "doris_specific": True},
    "QUANTILE_STATE": {"category": "quantile", "doris_specific": True},
    "AGG_STATE": {"category": "agg_state", "doris_specific": True},
    # IP
    "IPV4": {"category": "ip", "doris_specific": True},
    "IPV6": {"category": "ip", "doris_specific": True},
    # Complex types
    "ARRAY": {"category": "complex"},
    "MAP": {"category": "complex"},
    "STRUCT": {"category": "complex"},
    "VARIANT": {"category": "variant", "doris_specific": True},
    # Misc
    "BLOB": {"category": "blob"},
}


# ============================================================
# Aggregate Function Types (Doris-specific)
# ============================================================
AGGREGATION_TYPES = {
    "MAX": {"description": "Max value"},
    "MIN": {"description": "Min value"},
    "SUM": {"description": "Sum value"},
    "REPLACE": {"description": "Replace value (default for UNIQUE KEY)", "doris_specific": True},
    "REPLACE_IF_NOT_NULL": {"description": "Replace if not null", "doris_specific": True},
    "HLL_UNION": {"description": "HLL union", "doris_specific": True, "requires_type": "HLL"},
    "BITMAP_UNION": {"description": "Bitmap union", "doris_specific": True, "requires_type": "BITMAP"},
    "QUANTILE_UNION": {"description": "Quantile union", "doris_specific": True, "requires_type": "QUANTILE_STATE"},
    "GENERIC": {"description": "Generic aggregation", "doris_specific": True},
}


# ============================================================
# Doris Properties (common)
# ============================================================
COMMON_PROPERTIES = {
    # Storage
    "replication_num": {"description": "Number of replicas", "default": "1"},
    "replication_allocation": {"description": "Replica allocation"},
    "storage_medium": {"description": "Storage medium: SSD/HDD"},
    "storage_cooldown_time": {"description": "Cool down to HDD after time"},
    # Compaction
    "disable_auto_compaction": {"description": "Disable auto compaction", "default": "false"},
    "enable_single_replica_compaction": {"description": "Single replica compaction", "default": "false"},
    # Compression
    "compress_type": {"description": "Compression: LZ4/ZSTD/DEFLATE"},
    # Index
    "inverted_index": {"description": "Inverted index storage format"},
    "bloom_filter_columns": {"description": "Bloom filter columns"},
    "bloom_filter_fpp": {"description": "Bloom filter false positive rate"},
    # Schema change
    "light_schema_change": {"description": "Enable light schema change", "default": "false"},
    "store_row_column": {"description": "Store row column for light schema change"},
    # Partition
    "dynamic_partition.enable": {"description": "Dynamic partition"},
    "dynamic_partition.time_unit": {"description": "DAY/WEEK/MONTH"},
    "dynamic_partition.start": {"description": "Start offset"},
    "dynamic_partition.end": {"description": "End offset"},
    "dynamic_partition.replication_num": {"description": "Replica count"},
    # Misc
    "colocate_with": {"description": "Colocation group name"},
    "partition.live_number": {"description": "Live partition count"},
    "default_partition_num": {"description": "Default partition count"},
    "estimate_partition_size": {"description": "Estimate partition size"},
    "partition_type": {"description": "Partition type"},
    "in_memory": {"description": "In-memory table", "default": "false"},
    "enable_unique_key_merge_on_write": {"description": "Unique key merge-on-write", "default": "false"},
    "function_column.mode": {"description": "Variant mode"},
    "function_column.sequence_type": {"description": "Sequence column type"},
    "function_column.sequence_col": {"description": "Sequence column name"},
}


# ============================================================
# Statement Type Detection (heuristic)
# ============================================================
def detect_statement_type(sql_text):
    """
    Heuristic detection of statement type from first tokens.
    Returns one of STATEMENT_RULES keys or 'UNKNOWN'.
    """
    text = sql_text.strip().upper()
    # Remove leading comments and whitespace
    while text.startswith("--") or text.startswith("/*"):
        if text.startswith("--"):
            nl = text.find("\n")
            if nl == -1:
                return "UNKNOWN"
            text = text[nl + 1:].lstrip()
        elif text.startswith("/*"):
            end = text.find("*/")
            if end == -1:
                return "UNKNOWN"
            text = text[end + 2:].lstrip()
        text = text.lstrip()

    tokens = text.split()
    if not tokens:
        return "UNKNOWN"
    first = tokens[0]
    second = tokens[1] if len(tokens) > 1 else ""
    third = tokens[2] if len(tokens) > 2 else ""

    if first == "WITH" or first == "SELECT":
        return "SELECT"
    if first == "EXPLAIN" or first == "DESC" or first == "DESCRIBE":
        return "EXPLAIN"
    if first == "INSERT":
        return "INSERT"
    if first == "UPDATE":
        return "UPDATE"
    if first == "DELETE":
        return "DELETE"
    if first == "TRUNCATE":
        return "TRUNCATE"
    if first == "LOAD":
        return "LOAD"
    if first == "EXPORT":
        return "EXPORT"
    if first == "COPY":
        return "COPY_INTO"
    if first == "CREATE":
        if second == "TABLE":
            if "LIKE" in tokens[2:5]:
                return "CREATE_TABLE_LIKE"
            return "CREATE_TABLE"
        if second == "VIEW":
            return "CREATE_VIEW"
        if second == "MATERIALIZED":
            return "CREATE_MTMV"
        if second == "INDEX":
            return "CREATE_INDEX"
        if second in ("DATABASE", "SCHEMA"):
            return "CREATE_DATABASE"
        if second == "CATALOG":
            return "CREATE_CATALOG"
        if second == "USER":
            return "CREATE_USER"
        if second == "ROLE":
            return "CREATE_ROLE"
        if second == "RESOURCE":
            return "CREATE_RESOURCE"
        if second == "STAGE":
            return "CREATE_STAGE"
        if second == "ENCRYPTKEY":
            return "CREATE_ENCRYPTKEY"
        if second == "JOB":
            return "CREATE_JOB"
        if second == "ROW" and third == "POLICY":
            return "CREATE_ROW_POLICY"
        if second == "SQL_BLOCK_RULE":
            return "CREATE_SQL_BLOCK_RULE"
        if second == "STORAGE" and third == "VAULT":
            return "CREATE_STORAGE_VAULT"
        if second == "WORKLOAD" and third == "GROUP":
            return "CREATE_WORKLOAD_GROUP"
        if second == "WORKLOAD" and third == "POLICY":
            return "CREATE_WORKLOAD_POLICY"
        if second == "REPOSITORY":
            return "CREATE_REPOSITORY"
        if second == "FUNCTION":
            return "CREATE_FUNCTION"
        if second == "ROUTINE" and third == "LOAD":
            return "ROUTINE_LOAD"
        return "UNKNOWN"
    if first == "ALTER":
        if second == "TABLE":
            return "ALTER_TABLE"
        if second == "COLOCATE" and third == "GROUP":
            return "ALTER_COLOCATE_GROUP"
        return "UNKNOWN"
    if first == "DROP":
        if second == "TABLE":
            return "DROP_TABLE"
        if second == "VIEW":
            return "DROP_VIEW"
        if second == "INDEX":
            return "DROP_INDEX"
        return "UNKNOWN"
    if first == "GRANT":
        return "GRANT"
    if first == "REVOKE":
        return "REVOKE"
    if first in ("BEGIN", "START"):
        return "BEGIN"
    if first == "COMMIT":
        return "COMMIT"
    if first == "ROLLBACK":
        return "ROLLBACK"
    if first == "SET":
        return "SET"
    if first == "SHOW":
        return "SHOW"
    if first == "ADMIN":
        return "ADMIN"
    if first == "KILL":
        return "KILL"
    if first == "CANCEL":
        return "CANCEL"
    if first == "BACKUP":
        return "BACKUP"
    if first == "RESTORE":
        return "RESTORE"
    if first == "RECOVER":
        return "RECOVER"
    if first == "CLEAN":
        return "CLEAN"
    if first == "INSTALL":
        return "INSTALL_PLUGIN"
    if first == "UNINSTALL":
        return "UNINSTALL_PLUGIN"
    if first == "LOCK":
        return "LOCK_TABLES"
    if first == "USE":
        return "USE"
    if first == "SWITCH":
        return "SWITCH"
    if first == "CALL":
        return "CALL"
    if first == "HELP":
        return "HELP"
    if first == "SYNC":
        return "SYNC"
    if first == "WARM":
        return "WARM_UP"
    if first == "PAUSE":
        return "PAUSE"
    if first == "RESUME":
        return "RESUME"
    if first == "STOP":
        return "STOP_ROUTINE_LOAD"
    if first == "REFRESH":
        return "REFRESH"
    return "UNKNOWN"


def get_statement_rule(stmt_type):
    """Get the grammar rule for a statement type"""
    return STATEMENT_RULES.get(stmt_type)


if __name__ == "__main__":
    print(f"Total statement types: {len(STATEMENT_RULES)}")
    for category in StatementCategory:
        count = sum(1 for r in STATEMENT_RULES.values() if r["category"] == category)
        print(f"  {category.value}: {count}")
    print(f"\nData types: {len(DORIS_DATA_TYPES)}")
    print(f"Aggregate types: {len(AGGREGATION_TYPES)}")
    # Test detection
    test_sql = "SELECT * FROM t1"
    print(f"\nTest: '{test_sql}' -> {detect_statement_type(test_sql)}")
    test_sql = "CREATE TABLE t1 (id INT) DISTRIBUTED BY HASH(id) BUCKETS 10"
    print(f"Test: '{test_sql[:50]}...' -> {detect_statement_type(test_sql)}")
