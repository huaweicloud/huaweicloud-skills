# -*- coding: utf-8 -*-
"""
MRS Spark SQL Grammar Rules Definition
Spark SQL statement types, clause definitions, and validation rules for MRS Spark.
Based on Spark 3.x SqlBaseParser.g4 grammar.
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
            "INTERSECT", "EXCEPT", "CLUSTER", "DISTRIBUTE", "SORT",
            "LATERAL VIEW"
        ],
        "valid_keywords": [
            "WITH", "SELECT", "DISTINCT", "ALL", "FROM", "WHERE",
            "GROUP", "BY", "HAVING", "WINDOW", "ORDER", "LIMIT",
            "UNION", "INTERSECT", "EXCEPT", "ASC", "DESC",
            "NULLS", "FIRST", "LAST", "AS", "ON", "AND", "OR",
            "NOT", "IN", "EXISTS", "BETWEEN", "LIKE", "CASE",
            "WHEN", "THEN", "ELSE", "END", "JOIN", "INNER", "OUTER",
            "LEFT", "RIGHT", "FULL", "CROSS", "NATURAL", "USING",
            "ANTI", "SEMI", "LATERAL", "TABLE", "OVER", "PARTITION",
            "ROWS", "RANGE", "UNBOUNDED", "PRECEDING", "FOLLOWING",
            "CURRENT", "ROW", "CLUSTER", "DISTRIBUTE", "SORT"
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
            "INTO BUCKETS", "ROW FORMAT", "STORED AS", "USING",
            "OPTIONS", "LOCATION", "TBLPROPERTIES", "AS", "LIKE"
        ],
        "valid_keywords": [
            "CREATE", "EXTERNAL", "TEMPORARY", "TABLE", "IF", "NOT",
            "EXISTS", "COMMENT", "PARTITIONED", "BY", "CLUSTERED",
            "SORTED", "INTO", "BUCKETS", "ROW", "FORMAT", "SERDE",
            "SERDEPROPERTIES", "DELIMITED", "FIELDS", "TERMINATED",
            "COLLECTION", "ITEMS", "MAP", "KEYS", "LINES", "STORED",
            "AS", "USING", "OPTIONS", "LOCATION", "TBLPROPERTIES",
            "LIKE", "WITH"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE EXTERNAL TABLE": {
        "required_clauses": ["CREATE", "EXTERNAL", "TABLE"],
        "optional_clauses": [
            "IF NOT EXISTS", "COLUMNS", "COMMENT", "PARTITIONED BY",
            "CLUSTERED BY", "SORTED BY", "INTO BUCKETS", "ROW FORMAT",
            "STORED AS", "USING", "OPTIONS", "LOCATION", "TBLPROPERTIES", "AS"
        ],
        "valid_keywords": [
            "CREATE", "EXTERNAL", "TABLE", "IF", "NOT", "EXISTS",
            "COMMENT", "PARTITIONED", "BY", "CLUSTERED", "SORTED",
            "INTO", "BUCKETS", "ROW", "FORMAT", "SERDE",
            "SERDEPROPERTIES", "DELIMITED", "FIELDS", "TERMINATED",
            "COLLECTION", "ITEMS", "MAP", "KEYS", "LINES", "STORED",
            "AS", "USING", "OPTIONS", "LOCATION", "TBLPROPERTIES", "LIKE"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE TEMPORARY TABLE": {
        "required_clauses": ["CREATE", "TEMPORARY", "TABLE"],
        "optional_clauses": [
            "IF NOT EXISTS", "COLUMNS", "COMMENT", "ROW FORMAT",
            "STORED AS", "USING", "OPTIONS", "LOCATION", "TBLPROPERTIES", "AS"
        ],
        "valid_keywords": [
            "CREATE", "TEMPORARY", "TABLE", "IF", "NOT", "EXISTS",
            "COMMENT", "ROW", "FORMAT", "SERDE", "SERDEPROPERTIES",
            "DELIMITED", "FIELDS", "TERMINATED", "COLLECTION", "ITEMS",
            "MAP", "KEYS", "LINES", "STORED", "AS", "USING", "OPTIONS",
            "LOCATION", "TBLPROPERTIES", "LIKE"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE VIEW": {
        "required_clauses": ["CREATE", "VIEW", "AS"],
        "optional_clauses": ["OR REPLACE", "GLOBAL", "TEMPORARY", "IF NOT EXISTS", "COMMENT", "COLUMNS"],
        "valid_keywords": [
            "CREATE", "OR", "REPLACE", "GLOBAL", "TEMPORARY", "VIEW",
            "IF", "NOT", "EXISTS", "COMMENT", "AS", "SELECT", "WITH",
            "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "UNION"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE OR REPLACE TEMP VIEW": {
        "required_clauses": ["CREATE", "OR", "REPLACE", "TEMP", "VIEW", "AS"],
        "optional_clauses": ["IF NOT EXISTS", "COMMENT", "COLUMNS"],
        "valid_keywords": [
            "CREATE", "OR", "REPLACE", "TEMP", "TEMPORARY", "VIEW",
            "IF", "NOT", "EXISTS", "COMMENT", "AS", "SELECT", "WITH",
            "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "UNION"
        ],
        "category": StatementCategory.DDL,
    },

    "CREATE GLOBAL TEMP VIEW": {
        "required_clauses": ["CREATE", "GLOBAL", "TEMP", "VIEW", "AS"],
        "optional_clauses": ["IF NOT EXISTS", "COMMENT", "COLUMNS"],
        "valid_keywords": [
            "CREATE", "GLOBAL", "TEMP", "TEMPORARY", "VIEW",
            "IF", "NOT", "EXISTS", "COMMENT", "AS", "SELECT", "WITH",
            "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT", "UNION"
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
        "optional_clauses": ["EXTENDED", "CODEGEN", "FORMATTED", "SIMPLE", "COST"],
        "valid_keywords": [
            "EXPLAIN", "EXTENDED", "CODEGEN", "FORMATTED", "SIMPLE", "COST"
        ],
        "category": StatementCategory.UTILITY,
    },

    "SET": {
        "required_clauses": ["SET"],
        "optional_clauses": [],
        "valid_keywords": ["SET", "SPARK", "HIVE"],
        "category": StatementCategory.UTILITY,
    },

    "RESET": {
        "required_clauses": ["RESET"],
        "optional_clauses": [],
        "valid_keywords": ["RESET"],
        "category": StatementCategory.UTILITY,
    },

    "SHOW": {
        "required_clauses": ["SHOW"],
        "optional_clauses": [],
        "valid_keywords": [
            "SHOW", "DATABASES", "TABLES", "PARTITIONS", "COLUMNS",
            "CREATE", "FUNCTIONS", "INDEXES", "LOCKS", "COMPACTIONS",
            "TRANSACTIONS", "CONF", "ROLES", "GRANT", "PRINCIPALS",
            "TABLE", "EXTENDED", "FORMATTED", "LIKE", "IN", "FROM",
            "VIEWS", "TBLPROPERTIES"
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

    "SHOW VIEWS": {
        "required_clauses": ["SHOW", "VIEWS"],
        "optional_clauses": ["IN", "LIKE"],
        "valid_keywords": ["SHOW", "VIEWS", "IN", "FROM", "LIKE"],
        "category": StatementCategory.UTILITY,
    },

    "SHOW FUNCTIONS": {
        "required_clauses": ["SHOW", "FUNCTIONS"],
        "optional_clauses": ["LIKE"],
        "valid_keywords": ["SHOW", "FUNCTIONS", "LIKE", "ALL", "USER", "SYSTEM"],
        "category": StatementCategory.UTILITY,
    },

    "DESCRIBE": {
        "required_clauses": ["DESCRIBE"],
        "optional_clauses": ["EXTENDED", "FORMATTED", "DATABASE", "DETAIL", "QUERY"],
        "valid_keywords": [
            "DESCRIBE", "DESC", "EXTENDED", "FORMATTED", "DATABASE",
            "SCHEMA", "PARTITION", "DETAIL", "QUERY"
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

    "CACHE TABLE": {
        "required_clauses": ["CACHE", "TABLE"],
        "optional_clauses": ["LAZY", "AS", "OPTIONS", "SELECT"],
        "valid_keywords": [
            "CACHE", "LAZY", "TABLE", "AS", "OPTIONS", "SELECT", "WITH",
            "FROM", "WHERE", "GROUP", "BY", "HAVING", "ORDER", "LIMIT"
        ],
        "category": StatementCategory.UTILITY,
    },

    "UNCACHE TABLE": {
        "required_clauses": ["UNCACHE", "TABLE"],
        "optional_clauses": ["IF EXISTS"],
        "valid_keywords": ["UNCACHE", "TABLE", "IF", "EXISTS"],
        "category": StatementCategory.UTILITY,
    },

    "CLEAR CACHE": {
        "required_clauses": ["CLEAR", "CACHE"],
        "optional_clauses": [],
        "valid_keywords": ["CLEAR", "CACHE"],
        "category": StatementCategory.UTILITY,
    },

    "REFRESH": {
        "required_clauses": ["REFRESH"],
        "optional_clauses": ["TABLE", "FUNCTION"],
        "valid_keywords": ["REFRESH", "TABLE", "FUNCTION"],
        "category": StatementCategory.UTILITY,
    },

    "REFRESH TABLE": {
        "required_clauses": ["REFRESH", "TABLE"],
        "optional_clauses": [],
        "valid_keywords": ["REFRESH", "TABLE"],
        "category": StatementCategory.UTILITY,
    },

    "REFRESH FUNCTION": {
        "required_clauses": ["REFRESH", "FUNCTION"],
        "optional_clauses": [],
        "valid_keywords": ["REFRESH", "FUNCTION"],
        "category": StatementCategory.UTILITY,
    },

    "ADD JAR": {
        "required_clauses": ["ADD", "JAR"],
        "optional_clauses": [],
        "valid_keywords": ["ADD", "JAR"],
        "category": StatementCategory.UTILITY,
    },

    "LIST JAR": {
        "required_clauses": ["LIST", "JAR"],
        "optional_clauses": [],
        "valid_keywords": ["LIST", "JAR"],
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
    # CREATE statements - 3+ token matches first
    (["CREATE", "OR", "REPLACE", "TEMP", "VIEW"], "CREATE OR REPLACE TEMP VIEW"),
    (["CREATE", "GLOBAL", "TEMP", "VIEW"], "CREATE GLOBAL TEMP VIEW"),
    (["CREATE", "EXTERNAL", "TABLE"], "CREATE EXTERNAL TABLE"),
    (["CREATE", "TEMPORARY", "TABLE"], "CREATE TEMPORARY TABLE"),
    (["CREATE", "MATERIALIZED", "VIEW"], "CREATE MATERIALIZED VIEW"),
    (["SHOW", "CREATE", "TABLE"], "SHOW CREATE TABLE"),
    # CREATE statements - 2-token matches
    (["CREATE", "TABLE"], "CREATE TABLE"),
    (["CREATE", "VIEW"], "CREATE VIEW"),
    (["CREATE", "FUNCTION"], "CREATE FUNCTION"),
    (["CREATE", "ROLE"], "CREATE ROLE"),
    (["CREATE", "DATABASE"], "CREATE DATABASE"),
    (["CREATE", "SCHEMA"], "CREATE DATABASE"),
    # ALTER statements
    (["ALTER", "TABLE"], "ALTER TABLE"),
    (["ALTER", "DATABASE"], "ALTER DATABASE"),
    (["ALTER", "VIEW"], "ALTER VIEW"),
    # DROP statements
    (["DROP", "TABLE"], "DROP TABLE"),
    (["DROP", "DATABASE"], "DROP DATABASE"),
    (["DROP", "VIEW"], "DROP VIEW"),
    (["DROP", "FUNCTION"], "DROP FUNCTION"),
    (["DROP", "ROLE"], "DROP ROLE"),
    # INSERT statements
    (["INSERT", "OVERWRITE"], "INSERT OVERWRITE"),
    # TRUNCATE statements
    (["TRUNCATE", "TABLE"], "TRUNCATE TABLE"),
    # SHOW statements
    (["SHOW", "DATABASES"], "SHOW DATABASES"),
    (["SHOW", "TABLES"], "SHOW TABLES"),
    (["SHOW", "PARTITIONS"], "SHOW PARTITIONS"),
    (["SHOW", "COLUMNS"], "SHOW COLUMNS"),
    (["SHOW", "VIEWS"], "SHOW VIEWS"),
    (["SHOW", "FUNCTIONS"], "SHOW FUNCTIONS"),
    # DESCRIBE statements
    (["DESCRIBE", "DATABASE"], "DESCRIBE DATABASE"),
    # ANALYZE statements
    (["ANALYZE", "TABLE"], "ANALYZE TABLE"),
    # MSCK statements
    (["MSCK", "REPAIR"], "MSCK REPAIR"),
    # Spark-specific statements
    (["CACHE", "TABLE"], "CACHE TABLE"),
    (["UNCACHE", "TABLE"], "UNCACHE TABLE"),
    (["CLEAR", "CACHE"], "CLEAR CACHE"),
    (["REFRESH", "TABLE"], "REFRESH TABLE"),
    (["REFRESH", "FUNCTION"], "REFRESH FUNCTION"),
    (["ADD", "JAR"], "ADD JAR"),
    (["LIST", "JAR"], "LIST JAR"),
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
    "RESET": "RESET",
    "SHOW": "SHOW",
    "DESCRIBE": "DESCRIBE",
    "DESC": "DESCRIBE",
    "MSCK": "MSCK",
    "GRANT": "GRANT",
    "REVOKE": "REVOKE",
    "USE": "USE",
    "LOAD": "LOAD",
    "TRUNCATE": "TRUNCATE",
    "ALTER": "ALTER TABLE",
    "DROP": "DROP TABLE",
    "MERGE": "MERGE",
    "CACHE": "CACHE TABLE",
    "UNCACHE": "UNCACHE TABLE",
    "REFRESH": "REFRESH",
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
        "BUCKETS", "ROW", "FORMAT", "STORED", "USING", "OPTIONS",
        "LOCATION", "TBLPROPERTIES", "AS", "LIKE"
    ],
    "CREATE EXTERNAL TABLE": [
        "CREATE", "EXTERNAL", "TABLE", "IF", "NOT", "EXISTS",
        "COLUMNS", "COMMENT", "PARTITIONED", "CLUSTERED", "SORTED", "INTO",
        "BUCKETS", "ROW", "FORMAT", "STORED", "USING", "OPTIONS",
        "LOCATION", "TBLPROPERTIES", "AS", "LIKE"
    ],
    "CREATE TEMPORARY TABLE": [
        "CREATE", "TEMPORARY", "TABLE", "IF", "NOT", "EXISTS",
        "COLUMNS", "COMMENT", "ROW", "FORMAT", "STORED", "USING", "OPTIONS",
        "LOCATION", "TBLPROPERTIES", "AS", "LIKE"
    ],
    "CREATE VIEW": [
        "CREATE", "OR", "REPLACE", "GLOBAL", "TEMPORARY", "VIEW",
        "IF", "NOT", "EXISTS", "COMMENT", "COLUMNS", "AS"
    ],
    "CREATE OR REPLACE TEMP VIEW": [
        "CREATE", "OR", "REPLACE", "TEMP", "VIEW", "IF", "NOT", "EXISTS",
        "COMMENT", "COLUMNS", "AS"
    ],
    "CREATE GLOBAL TEMP VIEW": [
        "CREATE", "GLOBAL", "TEMP", "VIEW", "IF", "NOT", "EXISTS",
        "COMMENT", "COLUMNS", "AS"
    ],
    "CREATE MATERIALIZED VIEW": [
        "CREATE", "MATERIALIZED", "VIEW", "IF", "NOT", "EXISTS",
        "COMMENT", "DISABLE", "REWRITE", "TBLPROPERTIES", "AS"
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
    "DROP TABLE": [
        "DROP", "TABLE", "IF", "EXISTS", "PURGE"
    ],
    "DROP DATABASE": [
        "DROP", "DATABASE", "IF", "EXISTS", "CASCADE", "RESTRICT"
    ],
    "DROP VIEW": [
        "DROP", "VIEW", "IF", "EXISTS"
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
        "EXPLAIN", "EXTENDED", "CODEGEN", "FORMATTED", "SIMPLE", "COST"
    ],
    "LOAD": [
        "LOAD", "DATA", "LOCAL", "INPATH", "OVERWRITE", "INTO", "TABLE",
        "PARTITION"
    ],
    "SET": [
        "SET"
    ],
    "RESET": [
        "RESET"
    ],
    "SHOW": [
        "SHOW", "DATABASES", "TABLES", "PARTITIONS", "COLUMNS",
        "CREATE", "FUNCTIONS", "VIEWS", "TABLE", "EXTENDED",
        "FORMATTED", "LIKE", "IN", "FROM"
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
    "SHOW VIEWS": [
        "SHOW", "VIEWS", "IN", "LIKE"
    ],
    "SHOW FUNCTIONS": [
        "SHOW", "FUNCTIONS", "LIKE"
    ],
    "DESCRIBE": [
        "DESCRIBE", "EXTENDED", "FORMATTED", "DATABASE", "PARTITION",
        "DETAIL", "QUERY"
    ],
    "DESCRIBE DATABASE": [
        "DESCRIBE", "DATABASE", "EXTENDED"
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
    "USE": [
        "USE"
    ],
    "CACHE TABLE": [
        "CACHE", "LAZY", "TABLE", "AS"
    ],
    "UNCACHE TABLE": [
        "UNCACHE", "TABLE", "IF", "EXISTS"
    ],
    "CLEAR CACHE": [
        "CLEAR", "CACHE"
    ],
    "REFRESH": [
        "REFRESH", "TABLE", "FUNCTION"
    ],
    "REFRESH TABLE": [
        "REFRESH", "TABLE"
    ],
    "REFRESH FUNCTION": [
        "REFRESH", "FUNCTION"
    ],
    "ADD JAR": [
        "ADD", "JAR"
    ],
    "LIST JAR": [
        "LIST", "JAR"
    ],
}
