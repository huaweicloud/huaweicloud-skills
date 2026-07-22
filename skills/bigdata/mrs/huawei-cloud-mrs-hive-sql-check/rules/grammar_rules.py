# -*- coding: utf-8 -*-
"""
MRS Hive SQL Grammar Rules Definition
Hive SQL statement types, clause definitions, and validation rules for MRS Hive.
"""

from enum import Enum


class StatementCategory(Enum):
    """SQL statement category classification."""
    DML = "DML"
    DDL = "DDL"
    DCL = "DCL"
    UTILITY = "UTILITY"


# ============================================================
# Statement Type Definitions
# ============================================================

STATEMENT_RULES = {
    # ---- DML Statements ----
    "SELECT": {
        "required_clauses": ["SELECT"],
        "optional_clauses": [
            "WITH", "DISTINCT", "ALL", "FROM", "WHERE", "GROUP BY",
            "HAVING", "WINDOW", "ORDER BY", "LIMIT", "UNION",
            "INTERSECT", "EXCEPT", "CLUSTER", "DISTRIBUTE", "SORT"
        ],
        "valid_keywords": [
            "WITH", "SELECT", "DISTINCT", "ALL", "FROM", "WHERE",
            "GROUP", "BY", "HAVING", "WINDOW", "ORDER", "LIMIT",
            "UNION", "INTERSECT", "EXCEPT", "ALL", "ASC", "DESC",
            "NULLS", "FIRST", "LAST", "AS", "ON", "AND", "OR",
            "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "CASE",
            "WHEN", "THEN", "ELSE", "END", "JOIN", "INNER", "OUTER",
            "LEFT", "RIGHT", "FULL", "CROSS", "NATURAL", "USING",
            "CLUSTER", "DISTRIBUTE", "SORT", "LATERAL", "TABLE",
            "OVER", "PARTITION", "ROWS", "RANGE", "UNBOUNDED",
            "PRECEDING", "FOLLOWING", "CURRENT", "ROW"
        ],
        "category": StatementCategory.DML,
    },

    "INSERT": {
        "required_clauses": ["INSERT"],
        "optional_clauses": [
            "OVERWRITE", "INTO", "TABLE", "PARTITION", "VALUES",
            "SELECT", "WITH"
        ],
        "valid_keywords": [
            "INSERT", "OVERWRITE", "INTO", "TABLE", "PARTITION",
            "VALUES", "SELECT", "WITH", "DIRECTORY", "FROM"
        ],
        "category": StatementCategory.DML,
    },

    "INSERT OVERWRITE": {
        "required_clauses": ["INSERT", "OVERWRITE"],
        "optional_clauses": [
            "INTO", "TABLE", "PARTITION", "DIRECTORY", "SELECT", "WITH"
        ],
        "valid_keywords": [
            "INSERT", "OVERWRITE", "INTO", "TABLE", "PARTITION",
            "DIRECTORY", "SELECT", "WITH", "LOCAL", "VALUES", "FROM"
        ],
        "category": StatementCategory.DML,
    },

    "UPDATE": {
        "required_clauses": ["UPDATE", "SET"],
        "optional_clauses": ["FROM", "WHERE"],
        "valid_keywords": [
            "UPDATE", "SET", "FROM", "WHERE", "AND", "OR", "NOT",
            "IN", "EXISTS", "BETWEEN", "LIKE", "CASE", "WHEN",
            "THEN", "ELSE", "END", "AS"
        ],
        "category": StatementCategory.DML,
    },

    "DELETE": {
        "required_clauses": ["DELETE", "FROM"],
        "optional_clauses": ["WHERE"],
        "valid_keywords": [
            "DELETE", "FROM", "WHERE", "AND", "OR", "NOT", "IN",
            "EXISTS", "BETWEEN", "LIKE", "CASE", "WHEN", "THEN",
            "ELSE", "END", "AS"
        ],
        "category": StatementCategory.DML,
    },

    "MERGE": {
        "required_clauses": ["MERGE", "INTO", "USING", "ON"],
        "optional_clauses": ["WHEN MATCHED", "WHEN NOT MATCHED"],
        "valid_keywords": [
            "MERGE", "INTO", "USING", "ON", "WHEN", "MATCHED",
            "NOT", "THEN", "UPDATE", "INSERT", "DELETE", "AND",
            "OR", "SET", "VALUES"
        ],
        "category": StatementCategory.DML,
    },

    # ---- DDL Statements ----
    "CREATE TABLE": {
        "required_clauses": ["CREATE", "TABLE"],
        "optional_clauses": [
            "EXTERNAL", "TEMPORARY", "IF NOT EXISTS", "COLUMNS",
            "COMMENT", "PARTITIONED BY", "CLUSTERED BY", "SORTED BY",
            "INTO BUCKETS", "ROW FORMAT", "STORED AS", "LOCATION",
            "TBLPROPERTIES", "AS"
        ],
        "valid_keywords": [
            "CREATE", "EXTERNAL", "TEMPORARY", "TABLE", "IF", "NOT",
            "EXISTS", "COMMENT", "PARTITIONED", "BY", "CLUSTERED",
            "SORTED", "INTO", "BUCKETS", "ROW", "FORMAT", "SERDE",
            "SERDEPROPERTIES", "DELIMITED", "FIELDS", "TERMINATED",
            "COLLECTION", "ITEMS", "MAP", "KEYS", "LINES", "STORED",
            "AS", "LOCATION", "TBLPROPERTIES", "LIKE", "WITH"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE EXTERNAL TABLE": {
        "required_clauses": ["CREATE", "EXTERNAL", "TABLE"],
        "optional_clauses": [
            "IF NOT EXISTS", "COLUMNS", "COMMENT", "PARTITIONED BY",
            "CLUSTERED BY", "SORTED BY", "INTO BUCKETS", "ROW FORMAT",
            "STORED AS", "LOCATION", "TBLPROPERTIES", "AS"
        ],
        "valid_keywords": [
            "CREATE", "EXTERNAL", "TABLE", "IF", "NOT", "EXISTS",
            "COMMENT", "PARTITIONED", "BY", "CLUSTERED", "SORTED",
            "INTO", "BUCKETS", "ROW", "FORMAT", "SERDE",
            "SERDEPROPERTIES", "DELIMITED", "FIELDS", "TERMINATED",
            "COLLECTION", "ITEMS", "MAP", "KEYS", "LINES", "STORED",
            "AS", "LOCATION", "TBLPROPERTIES", "LIKE"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE TEMPORARY TABLE": {
        "required_clauses": ["CREATE", "TEMPORARY", "TABLE"],
        "optional_clauses": [
            "IF NOT EXISTS", "COLUMNS", "COMMENT", "ROW FORMAT",
            "STORED AS", "LOCATION", "TBLPROPERTIES", "AS"
        ],
        "valid_keywords": [
            "CREATE", "TEMPORARY", "TABLE", "IF", "NOT", "EXISTS",
            "COMMENT", "ROW", "FORMAT", "SERDE", "SERDEPROPERTIES",
            "DELIMITED", "FIELDS", "TERMINATED", "COLLECTION", "ITEMS",
            "MAP", "KEYS", "LINES", "STORED", "AS", "LOCATION",
            "TBLPROPERTIES", "LIKE"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE VIEW": {
        "required_clauses": ["CREATE", "VIEW", "AS"],
        "optional_clauses": ["IF NOT EXISTS", "COMMENT", "COLUMNS"],
        "valid_keywords": [
            "CREATE", "VIEW", "IF", "NOT", "EXISTS", "COMMENT",
            "AS", "SELECT", "WITH", "FROM", "WHERE", "GROUP", "BY",
            "HAVING", "ORDER", "LIMIT", "UNION"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE MATERIALIZED VIEW": {
        "required_clauses": ["CREATE", "MATERIALIZED", "VIEW", "AS"],
        "optional_clauses": [
            "IF NOT EXISTS", "COMMENT", "DISABLE REWRITE",
            "TBLPROPERTIES"
        ],
        "valid_keywords": [
            "CREATE", "MATERIALIZED", "VIEW", "IF", "NOT", "EXISTS",
            "COMMENT", "AS", "DISABLE", "REWRITE", "TBLPROPERTIES",
            "SELECT", "WITH", "FROM", "WHERE", "GROUP", "BY",
            "HAVING", "ORDER", "LIMIT", "UNION"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE INDEX": {
        "required_clauses": ["CREATE", "INDEX", "ON"],
        "optional_clauses": ["IF NOT EXISTS", "WITH DEFERRED REBUILD"],
        "valid_keywords": [
            "CREATE", "INDEX", "IF", "NOT", "EXISTS", "ON", "TABLE",
            "AS", "WITH", "DEFERRED", "REBUILD", "IN", "TBLPROPERTIES",
            "COMMENT"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE FUNCTION": {
        "required_clauses": ["CREATE", "FUNCTION"],
        "optional_clauses": [
            "IF NOT EXISTS", "AS", "USING", "TEMPORARY"
        ],
        "valid_keywords": [
            "CREATE", "TEMPORARY", "FUNCTION", "IF", "NOT", "EXISTS",
            "AS", "USING", "CLASS", "JAR", "FILE", "ARCHIVE"
        ],
        "category": StatementCategory.DDL,
    },

    "ALTER TABLE": {
        "required_clauses": ["ALTER", "TABLE"],
        "optional_clauses": [
            "ADD COLUMNS", "ADD PARTITION", "DROP PARTITION",
            "DROP COLUMN", "RENAME TO", "RENAME COLUMN",
            "CHANGE COLUMN", "REPLACE COLUMNS", "SET TBLPROPERTIES",
            "UNSET TBLPROPERTIES", "SET SERDE", "SET LOCATION",
            "SET FILEFORMAT", "ARCHIVE PARTITION",
            "UNARCHIVE PARTITION", "TOUCH", "SET SERDEPROPERTIES",
            "CONCATENATE", "COMPACT", "EXCHANGE", "PARTITION",
            "IF EXISTS"
        ],
        "valid_keywords": [
            "ALTER", "TABLE", "ADD", "DROP", "RENAME", "TO",
            "COLUMN", "COLUMNS", "REPLACE", "CHANGE", "SET",
            "UNSET", "TBLPROPERTIES", "SERDE", "SERDEPROPERTIES",
            "LOCATION", "FILEFORMAT", "PARTITION", "ARCHIVE",
            "UNARCHIVE", "TOUCH", "CONCATENATE", "COMPACT",
            "EXCHANGE", "IF", "EXISTS", "COMMENT", "AFTER",
            "FIRST", "CASCADE", "RESTRICT"
        ],
        "category": StatementCategory.DDL,
    },

    "ALTER DATABASE": {
        "required_clauses": ["ALTER", "DATABASE"],
        "optional_clauses": ["SET DBPROPERTIES", "SET OWNER", "SET LOCATION"],
        "valid_keywords": [
            "ALTER", "DATABASE", "SCHEMA", "SET", "DBPROPERTIES",
            "OWNER", "LOCATION", "USER", "ROLE"
        ],
        "category": StatementCategory.DDL,
    },

    "ALTER VIEW": {
        "required_clauses": ["ALTER", "VIEW"],
        "optional_clauses": [
            "AS", "SET TBLPROPERTIES", "UNSET TBLPROPERTIES",
            "RENAME TO"
        ],
        "valid_keywords": [
            "ALTER", "VIEW", "AS", "SET", "UNSET", "TBLPROPERTIES",
            "RENAME", "TO"
        ],
        "category": StatementCategory.DDL,
    },

    "ALTER INDEX": {
        "required_clauses": ["ALTER", "INDEX"],
        "optional_clauses": ["REBUILD", "SET TBLPROPERTIES"],
        "valid_keywords": [
            "ALTER", "INDEX", "REBUILD", "SET", "TBLPROPERTIES",
            "ON", "TABLE"
        ],
        "category": StatementCategory.DDL,
    },

    "DROP TABLE": {
        "required_clauses": ["DROP", "TABLE"],
        "optional_clauses": ["IF EXISTS", "PURGE"],
        "valid_keywords": ["DROP", "TABLE", "IF", "EXISTS", "PURGE"],
        "category": StatementCategory.DDL,
    },

    "DROP DATABASE": {
        "required_clauses": ["DROP", "DATABASE"],
        "optional_clauses": ["IF EXISTS", "CASCADE", "RESTRICT"],
        "valid_keywords": [
            "DROP", "DATABASE", "SCHEMA", "IF", "EXISTS",
            "CASCADE", "RESTRICT"
        ],
        "category": StatementCategory.DDL,
    },

    "DROP VIEW": {
        "required_clauses": ["DROP", "VIEW"],
        "optional_clauses": ["IF EXISTS"],
        "valid_keywords": ["DROP", "VIEW", "MATERIALIZED", "IF", "EXISTS"],
        "category": StatementCategory.DDL,
    },

    "DROP INDEX": {
        "required_clauses": ["DROP", "INDEX"],
        "optional_clauses": ["IF EXISTS", "ON"],
        "valid_keywords": ["DROP", "INDEX", "IF", "EXISTS", "ON", "TABLE"],
        "category": StatementCategory.DDL,
    },

    "DROP FUNCTION": {
        "required_clauses": ["DROP", "FUNCTION"],
        "optional_clauses": ["IF EXISTS", "TEMPORARY"],
        "valid_keywords": [
            "DROP", "TEMPORARY", "FUNCTION", "IF", "EXISTS"
        ],
        "category": StatementCategory.DDL,
    },

    "TRUNCATE": {
        "required_clauses": ["TRUNCATE"],
        "optional_clauses": ["TABLE", "PARTITION"],
        "valid_keywords": ["TRUNCATE", "TABLE", "PARTITION"],
        "category": StatementCategory.DDL,
    },

    "TRUNCATE TABLE": {
        "required_clauses": ["TRUNCATE", "TABLE"],
        "optional_clauses": ["PARTITION"],
        "valid_keywords": ["TRUNCATE", "TABLE", "PARTITION"],
        "category": StatementCategory.DDL,
    },

    # ---- DCL Statements ----
    "GRANT": {
        "required_clauses": ["GRANT", "ON", "TO"],
        "optional_clauses": ["WITH GRANT OPTION"],
        "valid_keywords": [
            "GRANT", "ALL", "PRIVILEGES", "ALTER", "CREATE",
            "DELETE", "DROP", "INDEX", "INSERT", "SELECT",
            "UPDATE", "ON", "TABLE", "DATABASE", "TO", "USER",
            "ROLE", "WITH", "GRANT", "OPTION"
        ],
        "category": StatementCategory.DCL,
    },

    "REVOKE": {
        "required_clauses": ["REVOKE", "ON", "FROM"],
        "optional_clauses": ["GRANT OPTION FOR"],
        "valid_keywords": [
            "REVOKE", "ALL", "PRIVILEGES", "ALTER", "CREATE",
            "DELETE", "DROP", "INDEX", "INSERT", "SELECT",
            "UPDATE", "ON", "TABLE", "DATABASE", "FROM", "USER",
            "ROLE", "GRANT", "OPTION", "FOR"
        ],
        "category": StatementCategory.DCL,
    },

    # ---- Utility Statements ----
    "EXPLAIN": {
        "required_clauses": ["EXPLAIN"],
        "optional_clauses": ["EXTENDED", "DEPENDENCY", "AUTHORIZATION", "LOCKS", "FORMATTED"],
        "valid_keywords": [
            "EXPLAIN", "EXTENDED", "DEPENDENCY", "AUTHORIZATION",
            "LOCKS", "FORMATTED", "LOGICAL", "AST", "REOPTIMIZATION"
        ],
        "category": StatementCategory.UTILITY,
    },

    "SET": {
        "required_clauses": ["SET"],
        "optional_clauses": [],
        "valid_keywords": ["SET", "MAPREDUCE", "HIVE"],
        "category": StatementCategory.UTILITY,
    },

    "SHOW": {
        "required_clauses": ["SHOW"],
        "optional_clauses": [],
        "valid_keywords": [
            "SHOW", "DATABASES", "TABLES", "PARTITIONS", "COLUMNS",
            "CREATE", "FUNCTIONS", "INDEXES", "LOCKS", "COMPACTIONS",
            "TRANSACTIONS", "CONF", "ROLES", "GRANT", "PRINCIPALS",
            "TABLE", "EXTENDED", "FORMATTED", "LIKE", "IN", "FROM"
        ],
        "category": StatementCategory.UTILITY,
    },

    "SHOW DATABASES": {
        "required_clauses": ["SHOW", "DATABASES"],
        "optional_clauses": ["LIKE"],
        "valid_keywords": ["SHOW", "DATABASES", "SCHEMAS", "LIKE"],
        "category": StatementCategory.UTILITY,
    },

    "SHOW TABLES": {
        "required_clauses": ["SHOW", "TABLES"],
        "optional_clauses": ["IN", "LIKE"],
        "valid_keywords": ["SHOW", "TABLES", "IN", "FROM", "LIKE"],
        "category": StatementCategory.UTILITY,
    },

    "SHOW PARTITIONS": {
        "required_clauses": ["SHOW", "PARTITIONS"],
        "optional_clauses": ["PARTITION_SPEC"],
        "valid_keywords": [
            "SHOW", "PARTITIONS", "PARTITION", "IN", "FROM"
        ],
        "category": StatementCategory.UTILITY,
    },

    "SHOW COLUMNS": {
        "required_clauses": ["SHOW", "COLUMNS"],
        "optional_clauses": ["IN", "FROM"],
        "valid_keywords": ["SHOW", "COLUMNS", "IN", "FROM"],
        "category": StatementCategory.UTILITY,
    },

    "SHOW CREATE TABLE": {
        "required_clauses": ["SHOW", "CREATE", "TABLE"],
        "optional_clauses": [],
        "valid_keywords": ["SHOW", "CREATE", "TABLE"],
        "category": StatementCategory.UTILITY,
    },

    "DESCRIBE": {
        "required_clauses": ["DESCRIBE"],
        "optional_clauses": ["EXTENDED", "FORMATTED", "DATABASE"],
        "valid_keywords": [
            "DESCRIBE", "DESC", "EXTENDED", "FORMATTED", "DATABASE",
            "SCHEMA", "PARTITION"
        ],
        "category": StatementCategory.UTILITY,
    },

    "DESCRIBE DATABASE": {
        "required_clauses": ["DESCRIBE", "DATABASE"],
        "optional_clauses": ["EXTENDED"],
        "valid_keywords": [
            "DESCRIBE", "DESC", "DATABASE", "SCHEMA", "EXTENDED"
        ],
        "category": StatementCategory.UTILITY,
    },

    "DESCRIBE FORMATTED": {
        "required_clauses": ["DESCRIBE", "FORMATTED"],
        "optional_clauses": ["PARTITION"],
        "valid_keywords": [
            "DESCRIBE", "DESC", "FORMATTED", "EXTENDED", "PARTITION",
            "DATABASE"
        ],
        "category": StatementCategory.UTILITY,
    },

    "MSCK": {
        "required_clauses": ["MSCK"],
        "optional_clauses": ["REPAIR", "ADD", "DROP", "SYNC"],
        "valid_keywords": [
            "MSCK", "REPAIR", "ADD", "DROP", "SYNC", "TABLE",
            "PARTITIONS"
        ],
        "category": StatementCategory.UTILITY,
    },

    "MSCK REPAIR": {
        "required_clauses": ["MSCK", "REPAIR"],
        "optional_clauses": ["ADD", "DROP", "SYNC"],
        "valid_keywords": [
            "MSCK", "REPAIR", "ADD", "DROP", "SYNC", "TABLE",
            "PARTITIONS"
        ],
        "category": StatementCategory.UTILITY,
    },

    "USE": {
        "required_clauses": ["USE"],
        "optional_clauses": [],
        "valid_keywords": ["USE", "DEFAULT"],
        "category": StatementCategory.UTILITY,
    },

    "LOAD": {
        "required_clauses": ["LOAD", "INTO"],
        "optional_clauses": [
            "LOCAL", "INPATH", "OVERWRITE", "PARTITION",
            "TABLE"
        ],
        "valid_keywords": [
            "LOAD", "DATA", "LOCAL", "INPATH", "OVERWRITE", "INTO",
            "TABLE", "PARTITION"
        ],
        "category": StatementCategory.UTILITY,
    },

    "EXPORT": {
        "required_clauses": ["EXPORT", "TO"],
        "optional_clauses": ["PARTITION", "TABLE"],
        "valid_keywords": [
            "EXPORT", "TABLE", "PARTITION", "TO", "LOCATION"
        ],
        "category": StatementCategory.UTILITY,
    },

    "IMPORT": {
        "required_clauses": ["IMPORT"],
        "optional_clauses": [
            "FROM", "LOCATION", "TABLE", "PARTITION",
            "EXTERNAL", "IF NOT EXISTS"
        ],
        "valid_keywords": [
            "IMPORT", "TABLE", "PARTITION", "FROM", "LOCATION",
            "EXTERNAL", "IF", "NOT", "EXISTS"
        ],
        "category": StatementCategory.UTILITY,
    },

    "ANALYZE TABLE": {
        "required_clauses": ["ANALYZE", "TABLE"],
        "optional_clauses": [
            "PARTITION", "FOR COLUMNS", "COMPUTE STATISTICS",
            "NOSCAN"
        ],
        "valid_keywords": [
            "ANALYZE", "TABLE", "PARTITION", "COMPUTE", "STATISTICS",
            "FOR", "COLUMNS", "NOSCAN", "CACHE", "METADATA"
        ],
        "category": StatementCategory.UTILITY,
    },
}


# ============================================================
# Multi-Token Statement Detection
# Ordered by specificity: longest match first
# ============================================================

MULTI_TOKEN_STATEMENTS = [
    # CREATE statements - 3-token matches first
    (["CREATE", "EXTERNAL", "TABLE"], "CREATE EXTERNAL TABLE"),
    (["CREATE", "TEMPORARY", "TABLE"], "CREATE TEMPORARY TABLE"),
    (["SHOW", "CREATE", "TABLE"], "SHOW CREATE TABLE"),
    # CREATE statements - 2-token matches
    (["CREATE", "EXTERNAL"], "CREATE EXTERNAL TABLE"),
    (["CREATE", "TABLE"], "CREATE TABLE"),
    (["CREATE", "MATERIALIZED", "VIEW"], "CREATE MATERIALIZED VIEW"),
    (["CREATE", "VIEW"], "CREATE VIEW"),
    (["CREATE", "INDEX"], "CREATE INDEX"),
    (["CREATE", "FUNCTION"], "CREATE FUNCTION"),
    (["CREATE", "ROLE"], "CREATE ROLE"),
    (["CREATE", "DATABASE"], "CREATE DATABASE"),
    (["CREATE", "SCHEMA"], "CREATE DATABASE"),
    # ALTER statements
    (["ALTER", "TABLE"], "ALTER TABLE"),
    (["ALTER", "DATABASE"], "ALTER DATABASE"),
    (["ALTER", "VIEW"], "ALTER VIEW"),
    (["ALTER", "INDEX"], "ALTER INDEX"),
    # DROP statements
    (["DROP", "TABLE"], "DROP TABLE"),
    (["DROP", "DATABASE"], "DROP DATABASE"),
    (["DROP", "VIEW"], "DROP VIEW"),
    (["DROP", "INDEX"], "DROP INDEX"),
    (["DROP", "FUNCTION"], "DROP FUNCTION"),
    (["DROP", "ROLE"], "DROP ROLE"),
    (["DROP", "VIEW"], "DROP VIEW"),
    # INSERT statements
    (["INSERT", "OVERWRITE"], "INSERT OVERWRITE"),
    # TRUNCATE statements
    (["TRUNCATE", "TABLE"], "TRUNCATE TABLE"),
    # SHOW statements
    (["SHOW", "DATABASES"], "SHOW DATABASES"),
    (["SHOW", "TABLES"], "SHOW TABLES"),
    (["SHOW", "PARTITIONS"], "SHOW PARTITIONS"),
    (["SHOW", "COLUMNS"], "SHOW COLUMNS"),
    # DESCRIBE statements
    (["DESCRIBE", "DATABASE"], "DESCRIBE DATABASE"),
    (["DESCRIBE", "FORMATTED"], "DESCRIBE FORMATTED"),
    # ANALYZE statements
    (["ANALYZE", "TABLE"], "ANALYZE TABLE"),
    # MSCK statements
    (["MSCK", "REPAIR"], "MSCK REPAIR"),
]


# ============================================================
# Single-Token Statement Detection
# keyword -> statement_type
# ============================================================

SINGLE_TOKEN_STATEMENTS = {
    "SELECT": "SELECT",
    "INSERT": "INSERT",
    "UPDATE": "UPDATE",
    "DELETE": "DELETE",
    "EXPLAIN": "EXPLAIN",
    "SET": "SET",
    "SHOW": "SHOW",
    "DESCRIBE": "DESCRIBE",
    "DESC": "DESCRIBE",
    "MSCK": "MSCK",
    "GRANT": "GRANT",
    "REVOKE": "REVOKE",
    "USE": "USE",
    "LOAD": "LOAD",
    "EXPORT": "EXPORT",
    "IMPORT": "IMPORT",
    "TRUNCATE": "TRUNCATE",
    "ALTER": "ALTER TABLE",
    "DROP": "DROP TABLE",
    "MERGE": "MERGE",
    "WITH": "SELECT",
}


# ============================================================
# Clause Order Validation Rules
# Maps statement type to ordered list of clause keywords
# ============================================================

CLAUSE_ORDER_MAP = {
    "SELECT": [
        "WITH", "SELECT", "FROM", "WHERE", "GROUP", "HAVING",
        "WINDOW", "ORDER", "LIMIT", "UNION"
    ],
    "INSERT": [
        "INSERT", "OVERWRITE", "INTO", "TABLE", "PARTITION", "SELECT"
    ],
    "INSERT OVERWRITE": [
        "INSERT", "OVERWRITE", "INTO", "TABLE", "PARTITION", "SELECT"
    ],
    "UPDATE": [
        "UPDATE", "SET", "FROM", "WHERE"
    ],
    "DELETE": [
        "DELETE", "FROM", "WHERE"
    ],
    "MERGE": [
        "MERGE", "INTO", "USING", "ON", "WHEN"
    ],
    "CREATE TABLE": [
        "CREATE", "EXTERNAL", "TEMPORARY", "TABLE", "IF", "NOT", "EXISTS",
        "COLUMNS", "COMMENT", "PARTITIONED", "CLUSTERED", "SORTED", "INTO",
        "BUCKETS", "ROW", "FORMAT", "STORED", "LOCATION", "TBLPROPERTIES", "AS"
    ],
    "CREATE EXTERNAL TABLE": [
        "CREATE", "EXTERNAL", "TABLE", "IF", "NOT", "EXISTS",
        "COLUMNS", "COMMENT", "PARTITIONED", "CLUSTERED", "SORTED", "INTO",
        "BUCKETS", "ROW", "FORMAT", "STORED", "LOCATION", "TBLPROPERTIES", "AS"
    ],
    "CREATE TEMPORARY TABLE": [
        "CREATE", "TEMPORARY", "TABLE", "IF", "NOT", "EXISTS",
        "COLUMNS", "COMMENT", "ROW", "FORMAT", "STORED", "LOCATION",
        "TBLPROPERTIES", "AS"
    ],
    "CREATE VIEW": [
        "CREATE", "VIEW", "IF", "NOT", "EXISTS", "COMMENT",
        "COLUMNS", "AS"
    ],
    "CREATE MATERIALIZED VIEW": [
        "CREATE", "MATERIALIZED", "VIEW", "IF", "NOT", "EXISTS",
        "COMMENT", "DISABLE", "REWRITE", "TBLPROPERTIES", "AS"
    ],
    "CREATE INDEX": [
        "CREATE", "INDEX", "IF", "NOT", "EXISTS", "ON", "TABLE",
        "AS", "WITH", "DEFERRED", "REBUILD", "IN", "TBLPROPERTIES"
    ],
    "CREATE FUNCTION": [
        "CREATE", "TEMPORARY", "FUNCTION", "IF", "NOT", "EXISTS",
        "AS", "USING"
    ],
    "ALTER TABLE": [
        "ALTER", "TABLE", "IF", "EXISTS", "ADD", "DROP", "RENAME",
        "CHANGE", "REPLACE", "SET", "UNSET", "PARTITION", "COLUMN",
        "COLUMNS", "TBLPROPERTIES", "SERDE", "SERDEPROPERTIES",
        "LOCATION", "FILEFORMAT"
    ],
    "ALTER DATABASE": [
        "ALTER", "DATABASE", "SET", "DBPROPERTIES", "OWNER", "LOCATION"
    ],
    "ALTER VIEW": [
        "ALTER", "VIEW", "SET", "UNSET", "TBLPROPERTIES", "RENAME", "AS"
    ],
    "ALTER INDEX": [
        "ALTER", "INDEX", "REBUILD", "SET", "TBLPROPERTIES", "ON", "TABLE"
    ],
    "DROP TABLE": [
        "DROP", "TABLE", "IF", "EXISTS", "PURGE"
    ],
    "DROP DATABASE": [
        "DROP", "DATABASE", "IF", "EXISTS", "CASCADE", "RESTRICT"
    ],
    "DROP VIEW": [
        "DROP", "VIEW", "IF", "EXISTS"
    ],
    "DROP INDEX": [
        "DROP", "INDEX", "IF", "EXISTS", "ON", "TABLE"
    ],
    "DROP FUNCTION": [
        "DROP", "TEMPORARY", "FUNCTION", "IF", "EXISTS"
    ],
    "TRUNCATE": [
        "TRUNCATE", "TABLE", "PARTITION"
    ],
    "TRUNCATE TABLE": [
        "TRUNCATE", "TABLE", "PARTITION"
    ],
    "GRANT": [
        "GRANT", "ON", "TO", "WITH"
    ],
    "REVOKE": [
        "REVOKE", "ON", "FROM", "GRANT", "OPTION", "FOR"
    ],
    "EXPLAIN": [
        "EXPLAIN", "EXTENDED", "DEPENDENCY", "AUTHORIZATION", "LOCKS",
        "FORMATTED"
    ],
    "LOAD": [
        "LOAD", "DATA", "LOCAL", "INPATH", "OVERWRITE", "INTO", "TABLE",
        "PARTITION"
    ],
    "EXPORT": [
        "EXPORT", "TABLE", "PARTITION", "TO", "LOCATION"
    ],
    "IMPORT": [
        "IMPORT", "TABLE", "PARTITION", "FROM", "LOCATION", "EXTERNAL",
        "IF", "NOT", "EXISTS"
    ],
    "SHOW DATABASES": [
        "SHOW", "DATABASES", "LIKE"
    ],
    "SHOW TABLES": [
        "SHOW", "TABLES", "IN", "LIKE"
    ],
    "SHOW PARTITIONS": [
        "SHOW", "PARTITIONS", "PARTITION"
    ],
    "SHOW COLUMNS": [
        "SHOW", "COLUMNS", "IN", "FROM"
    ],
    "SHOW CREATE TABLE": [
        "SHOW", "CREATE", "TABLE"
    ],
    "DESCRIBE": [
        "DESCRIBE", "EXTENDED", "FORMATTED", "DATABASE", "PARTITION"
    ],
    "DESCRIBE DATABASE": [
        "DESCRIBE", "DATABASE", "EXTENDED"
    ],
    "DESCRIBE FORMATTED": [
        "DESCRIBE", "FORMATTED", "PARTITION"
    ],
    "MSCK": [
        "MSCK", "REPAIR", "ADD", "DROP", "SYNC", "TABLE"
    ],
    "MSCK REPAIR": [
        "MSCK", "REPAIR", "ADD", "DROP", "SYNC", "TABLE"
    ],
    "ANALYZE TABLE": [
        "ANALYZE", "TABLE", "PARTITION", "COMPUTE", "STATISTICS",
        "FOR", "COLUMNS", "NOSCAN"
    ],
    "SET": [
        "SET"
    ],
    "SHOW": [
        "SHOW", "DATABASES", "TABLES", "PARTITIONS", "COLUMNS",
        "CREATE", "FUNCTIONS", "INDEXES", "LOCKS", "COMPACTIONS",
        "TRANSACTIONS", "CONF", "ROLES", "GRANT", "PRINCIPALS",
        "TABLE", "EXTENDED", "FORMATTED", "LIKE", "IN", "FROM"
    ],
    "USE": [
        "USE"
    ],
}
