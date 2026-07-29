"""
HetuEngine SQL Grammar Rules
Based on Presto/Trino with Hive compatibility
"""

from enum import Enum, auto
from typing import Dict, List, Set, Optional, Tuple


class StatementCategory(Enum):
    """Statement category enumeration"""
    DML = auto()      # Data Manipulation Language
    DDL = auto()      # Data Definition Language
    TCL = auto()      # Transaction Control Language
    UTILITY = auto()  # Utility commands


class ClauseRequirement(Enum):
    """Clause requirement type"""
    REQUIRED = auto()
    OPTIONAL = auto()
    CONDITIONAL = auto()


# ============================================================================
# Statement Rules Definition
# ============================================================================

STATEMENT_RULES: Dict[str, Dict] = {
    # ========================================================================
    # DML Statements
    # ========================================================================
    "SELECT": {
        "category": StatementCategory.DML,
        "clauses": {
            "WITH": ClauseRequirement.OPTIONAL,
            "RECURSIVE": ClauseRequirement.OPTIONAL,
            "SELECT": ClauseRequirement.REQUIRED,
            "ALL": ClauseRequirement.OPTIONAL,
            "DISTINCT": ClauseRequirement.OPTIONAL,
            "FROM": ClauseRequirement.REQUIRED,
            "WHERE": ClauseRequirement.OPTIONAL,
            "GROUP BY": ClauseRequirement.OPTIONAL,
            "HAVING": ClauseRequirement.OPTIONAL,
            "WINDOW": ClauseRequirement.OPTIONAL,
            "ORDER BY": ClauseRequirement.OPTIONAL,
            "OFFSET": ClauseRequirement.OPTIONAL,
            "LIMIT": ClauseRequirement.OPTIONAL,
            "FETCH": ClauseRequirement.OPTIONAL,
            "UNION": ClauseRequirement.OPTIONAL,
            "INTERSECT": ClauseRequirement.OPTIONAL,
            "EXCEPT": ClauseRequirement.OPTIONAL,
            "TABLESAMPLE": ClauseRequirement.OPTIONAL,
            "MATCH_RECOGNIZE": ClauseRequirement.OPTIONAL,
            "FORMAT": ClauseRequirement.OPTIONAL,
        },
        "group_by_extensions": ["GROUPING SETS", "CUBE", "ROLLUP"],
        "set_operators": ["UNION", "INTERSECT", "EXCEPT"],
        "set_quantifiers": ["ALL", "DISTINCT"],
    },

    "INSERT": {
        "category": StatementCategory.DML,
        "clauses": {
            "INSERT": ClauseRequirement.REQUIRED,
            "INTO": ClauseRequirement.OPTIONAL,
            "OVERWRITE": ClauseRequirement.OPTIONAL,
            "TABLE": ClauseRequirement.OPTIONAL,
            "PARTITION": ClauseRequirement.OPTIONAL,
            "SELECT": ClauseRequirement.CONDITIONAL,
            "VALUES": ClauseRequirement.CONDITIONAL,
        },
    },

    "DELETE": {
        "category": StatementCategory.DML,
        "clauses": {
            "DELETE": ClauseRequirement.REQUIRED,
            "FROM": ClauseRequirement.REQUIRED,
            "WHERE": ClauseRequirement.OPTIONAL,
        },
    },

    "UPDATE": {
        "category": StatementCategory.DML,
        "clauses": {
            "UPDATE": ClauseRequirement.REQUIRED,
            "SET": ClauseRequirement.REQUIRED,
            "WHERE": ClauseRequirement.OPTIONAL,
        },
    },

    "LOAD": {
        "category": StatementCategory.DML,
        "clauses": {
            "LOAD": ClauseRequirement.REQUIRED,
            "DATA": ClauseRequirement.REQUIRED,
            "INPATH": ClauseRequirement.REQUIRED,
            "OVERWRITE": ClauseRequirement.OPTIONAL,
            "INTO": ClauseRequirement.REQUIRED,
            "TABLE": ClauseRequirement.OPTIONAL,
            "PARTITION": ClauseRequirement.OPTIONAL,
        },
    },

    # ========================================================================
    # DDL Statements
    # ========================================================================
    "CREATE SCHEMA": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "SCHEMA": ClauseRequirement.OPTIONAL,
            "DATABASE": ClauseRequirement.OPTIONAL,
            "IF NOT EXISTS": ClauseRequirement.OPTIONAL,
            "COMMENT": ClauseRequirement.OPTIONAL,
            "LOCATION": ClauseRequirement.OPTIONAL,
            "WITH": ClauseRequirement.OPTIONAL,
            "DBPROPERTIES": ClauseRequirement.OPTIONAL,
        },
    },

    "CREATE TABLE": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "EXTERNAL": ClauseRequirement.OPTIONAL,
            "TABLE": ClauseRequirement.REQUIRED,
            "IF NOT EXISTS": ClauseRequirement.OPTIONAL,
            "PARTITIONED BY": ClauseRequirement.OPTIONAL,
            "CLUSTERED BY": ClauseRequirement.OPTIONAL,
            "SORTED BY": ClauseRequirement.OPTIONAL,
            "INTO": ClauseRequirement.OPTIONAL,
            "BUCKETS": ClauseRequirement.OPTIONAL,
            "ROW FORMAT": ClauseRequirement.OPTIONAL,
            "STORED AS": ClauseRequirement.OPTIONAL,
            "LOCATION": ClauseRequirement.OPTIONAL,
            "TBLPROPERTIES": ClauseRequirement.OPTIONAL,
            "COMMENT": ClauseRequirement.OPTIONAL,
            "WITH": ClauseRequirement.OPTIONAL,
        },
        "hive_compatible": True,
    },

    "CREATE TABLE AS": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "TABLE": ClauseRequirement.REQUIRED,
            "IF NOT EXISTS": ClauseRequirement.OPTIONAL,
            "AS": ClauseRequirement.REQUIRED,
            "WITH DATA": ClauseRequirement.OPTIONAL,
            "WITH NO DATA": ClauseRequirement.OPTIONAL,
        },
    },

    "CREATE TABLE LIKE": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "TABLE": ClauseRequirement.REQUIRED,
            "IF NOT EXISTS": ClauseRequirement.OPTIONAL,
            "LIKE": ClauseRequirement.REQUIRED,
            "INCLUDING PROPERTIES": ClauseRequirement.OPTIONAL,
            "EXCLUDING PROPERTIES": ClauseRequirement.OPTIONAL,
        },
    },

    "CREATE VIEW": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "OR REPLACE": ClauseRequirement.OPTIONAL,
            "VIEW": ClauseRequirement.REQUIRED,
            "IF NOT EXISTS": ClauseRequirement.OPTIONAL,
            "COMMENT": ClauseRequirement.OPTIONAL,
            "TBLPROPERTIES": ClauseRequirement.OPTIONAL,
            "AS": ClauseRequirement.REQUIRED,
        },
    },

    "CREATE FUNCTION": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "OR REPLACE": ClauseRequirement.OPTIONAL,
            "FUNCTION": ClauseRequirement.REQUIRED,
            "RETURNS": ClauseRequirement.OPTIONAL,
            "LANGUAGE": ClauseRequirement.OPTIONAL,
            "DETERMINISTIC": ClauseRequirement.OPTIONAL,
            "NOT DETERMINISTIC": ClauseRequirement.OPTIONAL,
        },
    },

    "CREATE MATERIALIZED VIEW": {
        "category": StatementCategory.DDL,
        "clauses": {
            "CREATE": ClauseRequirement.REQUIRED,
            "MATERIALIZED VIEW": ClauseRequirement.REQUIRED,
            "IF NOT EXISTS": ClauseRequirement.OPTIONAL,
            "COMMENT": ClauseRequirement.OPTIONAL,
            "WITH": ClauseRequirement.OPTIONAL,
            "AS": ClauseRequirement.REQUIRED,
        },
        "refresh_properties": [
            "need_auto_refresh",
            "mv_validity",
            "refresh_duration",
        ],
    },

    "ALTER TABLE": {
        "category": StatementCategory.DDL,
        "clauses": {
            "ALTER": ClauseRequirement.REQUIRED,
            "TABLE": ClauseRequirement.REQUIRED,
        },
    },

    "ALTER MATERIALIZED VIEW": {
        "category": StatementCategory.DDL,
        "clauses": {
            "ALTER": ClauseRequirement.REQUIRED,
            "MATERIALIZED VIEW": ClauseRequirement.REQUIRED,
        },
    },

    "ALTER SCHEMA": {
        "category": StatementCategory.DDL,
        "clauses": {
            "ALTER": ClauseRequirement.REQUIRED,
            "SCHEMA": ClauseRequirement.OPTIONAL,
            "DATABASE": ClauseRequirement.OPTIONAL,
        },
    },

    "ALTER FUNCTION": {
        "category": StatementCategory.DDL,
        "clauses": {
            "ALTER": ClauseRequirement.REQUIRED,
            "FUNCTION": ClauseRequirement.REQUIRED,
        },
    },

    "DROP TABLE": {
        "category": StatementCategory.DDL,
        "clauses": {
            "DROP": ClauseRequirement.REQUIRED,
            "TABLE": ClauseRequirement.REQUIRED,
            "IF EXISTS": ClauseRequirement.OPTIONAL,
        },
    },

    "DROP VIEW": {
        "category": StatementCategory.DDL,
        "clauses": {
            "DROP": ClauseRequirement.REQUIRED,
            "VIEW": ClauseRequirement.REQUIRED,
            "IF EXISTS": ClauseRequirement.OPTIONAL,
        },
    },

    "DROP SCHEMA": {
        "category": StatementCategory.DDL,
        "clauses": {
            "DROP": ClauseRequirement.REQUIRED,
            "SCHEMA": ClauseRequirement.OPTIONAL,
            "DATABASE": ClauseRequirement.OPTIONAL,
            "IF EXISTS": ClauseRequirement.OPTIONAL,
        },
    },

    "DROP FUNCTION": {
        "category": StatementCategory.DDL,
        "clauses": {
            "DROP": ClauseRequirement.REQUIRED,
            "FUNCTION": ClauseRequirement.REQUIRED,
            "IF EXISTS": ClauseRequirement.OPTIONAL,
        },
    },

    "DROP MATERIALIZED VIEW": {
        "category": StatementCategory.DDL,
        "clauses": {
            "DROP": ClauseRequirement.REQUIRED,
            "MATERIALIZED VIEW": ClauseRequirement.REQUIRED,
            "IF EXISTS": ClauseRequirement.OPTIONAL,
        },
    },

    "TRUNCATE": {
        "category": StatementCategory.DDL,
        "clauses": {
            "TRUNCATE": ClauseRequirement.REQUIRED,
            "TABLE": ClauseRequirement.OPTIONAL,
        },
    },

    # ========================================================================
    # TCL Statements
    # ========================================================================
    "START TRANSACTION": {
        "category": StatementCategory.TCL,
        "clauses": {
            "START": ClauseRequirement.REQUIRED,
            "TRANSACTION": ClauseRequirement.REQUIRED,
        },
    },

    "COMMIT": {
        "category": StatementCategory.TCL,
        "clauses": {
            "COMMIT": ClauseRequirement.REQUIRED,
        },
    },

    "ROLLBACK": {
        "category": StatementCategory.TCL,
        "clauses": {
            "ROLLBACK": ClauseRequirement.REQUIRED,
        },
    },

    # ========================================================================
    # Utility Statements
    # ========================================================================
    "EXPLAIN": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "EXPLAIN": ClauseRequirement.REQUIRED,
            "ANALYZE": ClauseRequirement.OPTIONAL,
            "VERBOSE": ClauseRequirement.OPTIONAL,
            "IO": ClauseRequirement.OPTIONAL,
            "TYPE": ClauseRequirement.OPTIONAL,
            "GRAPHVIZ": ClauseRequirement.OPTIONAL,
        },
    },

    "SHOW": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "SHOW": ClauseRequirement.REQUIRED,
        },
        "show_targets": [
            "SCHEMAS", "TABLES", "TABLE STATUS", "COLUMNS", "PARTITIONS",
            "VIEWS", "MATERIALIZED VIEWS", "CREATE TABLE", "CREATE VIEW",
            "CREATE MATERIALIZED VIEW", "SESSION", "FUNCTIONS", "CATALOGS",
            "STATS", "SCHEMA", "VIEW",
        ],
    },

    "DESCRIBE": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "DESCRIBE": ClauseRequirement.REQUIRED,
            "DESC": ClauseRequirement.OPTIONAL,
        },
    },

    "USE": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "USE": ClauseRequirement.REQUIRED,
        },
    },

    "SET": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "SET": ClauseRequirement.REQUIRED,
        },
    },

    "RESET": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "RESET": ClauseRequirement.REQUIRED,
        },
    },

    "CALL": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "CALL": ClauseRequirement.REQUIRED,
        },
    },

    "REFRESH MATERIALIZED VIEW": {
        "category": StatementCategory.UTILITY,
        "clauses": {
            "REFRESH": ClauseRequirement.REQUIRED,
            "MATERIALIZED VIEW": ClauseRequirement.REQUIRED,
        },
    },
}


# ============================================================================
# HetuEngine-Specific Grammar Extensions
# ============================================================================

HETU_SPECIFIC_GRAMMAR: Dict[str, Dict] = {
    "partitioned_by": {
        "syntax": "PARTITIONED BY (col_name data_type, ...)",
        "description": "Hive-compatible partition specification",
        "used_in": ["CREATE TABLE"],
    },
    "clustered_by": {
        "syntax": "CLUSTERED BY (col, ...) [SORTED BY (col, ...) INTO n BUCKETS]",
        "description": "Hive-compatible bucketing specification",
        "used_in": ["CREATE TABLE"],
    },
    "row_format": {
        "syntax": "ROW FORMAT DELIMITED [FIELDS TERMINATED BY char] [COLLECTION ITEMS TERMINATED BY char] [MAP KEYS TERMINATED BY char] [LINES TERMINATED BY char]",
        "description": "Hive-compatible row format specification",
        "used_in": ["CREATE TABLE"],
        "sub_clauses": [
            "FIELDS TERMINATED BY",
            "COLLECTION ITEMS TERMINATED BY",
            "MAP KEYS TERMINATED BY",
            "LINES TERMINATED BY",
        ],
    },
    "stored_as": {
        "syntax": "STORED AS {ORC|PARQUET|AVRO|RCBINARY|RCTEXT|SEQUENCEFILE|JSON|TEXTFILE|TEXTFILE_MULTIDELIM|CSV}",
        "description": "Hive-compatible storage format",
        "used_in": ["CREATE TABLE"],
        "formats": [
            "ORC", "PARQUET", "AVRO", "RCBINARY", "RCTEXT",
            "SEQUENCEFILE", "JSON", "TEXTFILE", "TEXTFILE_MULTIDELIM", "CSV",
        ],
    },
    "tblproperties": {
        "syntax": "TBLPROPERTIES (key=value, ...)",
        "description": "Hive-compatible table properties",
        "used_in": ["CREATE TABLE", "CREATE VIEW", "CREATE MATERIALIZED VIEW"],
    },
    "virtual_schema": {
        "syntax": "CREATE/DROP/SHOW VIRTUAL SCHEMA",
        "description": "HetuEngine virtual schema support",
        "operations": ["CREATE", "DROP", "SHOW"],
    },
    "materialized_view": {
        "syntax": "CREATE MATERIALIZED VIEW with auto-refresh properties",
        "description": "HetuEngine materialized view with refresh configuration",
        "properties": [
            "need_auto_refresh",
            "mv_validity",
            "refresh_duration",
        ],
    },
    "insert_overwrite": {
        "syntax": "INSERT OVERWRITE [TABLE] ...",
        "description": "Hive-compatible INSERT OVERWRITE (no INTO keyword needed)",
        "used_in": ["INSERT"],
    },
    "tablesample": {
        "syntax": "TABLESAMPLE {SYSTEM|BERNOULLI} (percentage)",
        "description": "Table sampling for query optimization",
        "methods": ["SYSTEM", "BERNOULLI"],
        "used_in": ["SELECT"],
    },
    "match_recognize": {
        "syntax": "MATCH_RECOGNIZE pattern recognition",
        "description": "Pattern matching in row sequences",
        "used_in": ["SELECT"],
    },
    "semi_anti_join": {
        "syntax": "LEFT/RIGHT [SEMI|ANTI] JOIN",
        "description": "Semi and anti join support",
        "types": ["LEFT SEMI JOIN", "RIGHT SEMI JOIN", "LEFT ANTI JOIN", "RIGHT ANTI JOIN"],
    },
    "group_by_extensions": {
        "syntax": "GROUPING SETS, CUBE, ROLLUP",
        "description": "Advanced GROUP BY extensions",
        "extensions": ["GROUPING SETS", "CUBE", "ROLLUP"],
        "used_in": ["SELECT"],
    },
    "fetch_clause": {
        "syntax": "FETCH {FIRST|NEXT} count {ROW|ROWS} {ONLY|WITH TIES}",
        "description": "ANSI SQL FETCH clause for result limiting",
        "keywords": ["FIRST", "NEXT", "ROW", "ROWS", "ONLY", "WITH TIES"],
        "used_in": ["SELECT"],
    },
    "nulls_order": {
        "syntax": "NULLS {FIRST|LAST} in ORDER BY",
        "description": "NULL sorting order in ORDER BY",
        "options": ["NULLS FIRST", "NULLS LAST"],
        "used_in": ["SELECT"],
    },
    "with_recursive": {
        "syntax": "WITH RECURSIVE",
        "description": "Recursive CTE support",
        "used_in": ["SELECT"],
    },
    "query_rewrite_hint": {
        "syntax": "/*+ query_rewrite_hint */",
        "description": "Query rewrite hint for materialized view usage",
        "hint_type": "query_rewrite_hint",
    },
    "load_data": {
        "syntax": "LOAD DATA INPATH filepath [OVERWRITE] INTO TABLE",
        "description": "Hive-compatible data loading",
        "used_in": ["LOAD"],
    },
    "call_procedure": {
        "syntax": "CALL procedure_name(args)",
        "description": "Stored procedure invocation",
        "used_in": ["CALL"],
    },
}


# ============================================================================
# Operator Precedence (Presto/Trino style, highest to lowest)
# ============================================================================

OPERATOR_PRECEDENCE: List[List[str]] = [
    ["."],                                              # Member access
    ["::"],                                             # Type cast
    ["[", "]"],                                         # Array subscript
    ["-"],                                              # Unary minus
    ["+", "~"],                                         # Unary plus, bitwise NOT
    ["*", "/", "%"],                                    # Multiplication, division, modulo
    ["+", "-"],                                         # Addition, subtraction
    ["||"],                                             # String concatenation
    ["<<", ">>"],                                       # Bitwise shift
    ["&"],                                              # Bitwise AND
    ["^"],                                              # Bitwise XOR
    ["|"],                                              # Bitwise OR
    ["<", ">", "<=", ">="],                            # Comparison
    ["=", "!=", "<>"],                                  # Equality
    ["NOT"],                                            # Logical NOT
    ["AND"],                                            # Logical AND
    ["OR"],                                             # Logical OR
    ["BETWEEN", "IN", "LIKE", "ILIKE", "SIMILAR TO"],  # Predicates
    ["IS NULL", "IS NOT NULL", "IS TRUE", "IS FALSE", "IS UNKNOWN"],  # NULL tests
]


# ============================================================================
# Statement Detection Rules
# ============================================================================

MULTI_TOKEN_STATEMENTS: Dict[str, List[str]] = {
    "CREATE SCHEMA": ["CREATE SCHEMA", "CREATE DATABASE"],
    "CREATE TABLE": ["CREATE TABLE", "CREATE EXTERNAL TABLE"],
    "CREATE TABLE AS": ["CREATE TABLE AS"],
    "CREATE TABLE LIKE": ["CREATE TABLE LIKE"],
    "CREATE VIEW": ["CREATE VIEW", "CREATE OR REPLACE VIEW"],
    "CREATE FUNCTION": ["CREATE FUNCTION", "CREATE OR REPLACE FUNCTION"],
    "CREATE MATERIALIZED VIEW": ["CREATE MATERIALIZED VIEW"],
    "ALTER TABLE": ["ALTER TABLE"],
    "ALTER MATERIALIZED VIEW": ["ALTER MATERIALIZED VIEW"],
    "ALTER SCHEMA": ["ALTER SCHEMA", "ALTER DATABASE"],
    "ALTER FUNCTION": ["ALTER FUNCTION"],
    "DROP TABLE": ["DROP TABLE"],
    "DROP VIEW": ["DROP VIEW"],
    "DROP SCHEMA": ["DROP SCHEMA", "DROP DATABASE"],
    "DROP FUNCTION": ["DROP FUNCTION"],
    "DROP MATERIALIZED VIEW": ["DROP MATERIALIZED VIEW"],
    "START TRANSACTION": ["START TRANSACTION"],
    "REFRESH MATERIALIZED VIEW": ["REFRESH MATERIALIZED VIEW"],
}

SINGLE_TOKEN_STATEMENTS: Dict[str, str] = {
    "SELECT": "SELECT",
    "INSERT": "INSERT",
    "DELETE": "DELETE",
    "UPDATE": "UPDATE",
    "LOAD": "LOAD",
    "TRUNCATE": "TRUNCATE",
    "COMMIT": "COMMIT",
    "ROLLBACK": "ROLLBACK",
    "EXPLAIN": "EXPLAIN",
    "SHOW": "SHOW",
    "DESCRIBE": "DESCRIBE",
    "DESC": "DESC",
    "USE": "USE",
    "SET": "SET",
    "RESET": "RESET",
    "CALL": "CALL",
}


# ============================================================================
# Clause Order Validation
# ============================================================================

CLAUSE_ORDER_MAP: Dict[str, List[str]] = {
    "SELECT": [
        "WITH",
        "RECURSIVE",
        "SELECT",
        "ALL",
        "DISTINCT",
        "FROM",
        "WHERE",
        "GROUP BY",
        "GROUPING SETS",
        "CUBE",
        "ROLLUP",
        "HAVING",
        "WINDOW",
        "ORDER BY",
        "OFFSET",
        "LIMIT",
        "FETCH",
        "UNION",
        "INTERSECT",
        "EXCEPT",
    ],

    "INSERT": [
        "INSERT",
        "INTO",
        "OVERWRITE",
        "TABLE",
        "PARTITION",
        "SELECT",
        "VALUES",
    ],

    "UPDATE": [
        "UPDATE",
        "SET",
        "WHERE",
    ],

    "DELETE": [
        "DELETE",
        "FROM",
        "WHERE",
    ],
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_statement_category(statement_type: str) -> Optional[StatementCategory]:
    """Get the category of a statement type"""
    rule = STATEMENT_RULES.get(statement_type)
    if rule:
        return rule["category"]
    return None


def get_required_clauses(statement_type: str) -> List[str]:
    """Get all required clauses for a statement type"""
    rule = STATEMENT_RULES.get(statement_type)
    if not rule:
        return []
    return [
        clause for clause, req in rule["clauses"].items()
        if req == ClauseRequirement.REQUIRED
    ]


def get_optional_clauses(statement_type: str) -> List[str]:
    """Get all optional clauses for a statement type"""
    rule = STATEMENT_RULES.get(statement_type)
    if not rule:
        return []
    return [
        clause for clause, req in rule["clauses"].items()
        if req in (ClauseRequirement.OPTIONAL, ClauseRequirement.CONDITIONAL)
    ]


def is_hetu_specific_grammar(grammar_name: str) -> bool:
    """Check if a grammar feature is HetuEngine-specific"""
    return grammar_name in HETU_SPECIFIC_GRAMMAR


def detect_statement_type(sql_tokens: List[str]) -> Optional[str]:
    """
    Detect statement type from SQL tokens
    Returns the detected statement type or None
    """
    if not sql_tokens:
        return None

    sql_upper = [t.upper() for t in sql_tokens]

    # Check multi-token statements first (more specific)
    for stmt_type, patterns in MULTI_TOKEN_STATEMENTS.items():
        for pattern in patterns:
            pattern_tokens = pattern.split()
            if len(pattern_tokens) <= len(sql_upper):
                match = True
                for i, pt in enumerate(pattern_tokens):
                    if sql_upper[i] != pt:
                        match = False
                        break
                if match:
                    return stmt_type

    # Check single-token statements
    first_token = sql_upper[0]
    if first_token in SINGLE_TOKEN_STATEMENTS:
        return SINGLE_TOKEN_STATEMENTS[first_token]

    return None


def validate_clause_order(statement_type: str, found_clauses: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that clauses appear in the correct order
    Returns (is_valid, error_message)
    """
    expected_order = CLAUSE_ORDER_MAP.get(statement_type)
    if not expected_order:
        return True, None

    found_upper = [c.upper() for c in found_clauses]
    last_index = -1

    for clause in found_upper:
        if clause in expected_order:
            current_index = expected_order.index(clause)
            if current_index < last_index:
                return False, f"Clause '{clause}' appears out of order in {statement_type} statement"
            last_index = current_index

    return True, None


def get_operator_precedence(operator: str) -> int:
    """
    Get the precedence level of an operator (lower number = higher precedence)
    Returns -1 if operator not found
    """
    op_upper = operator.upper()
    for level, ops in enumerate(OPERATOR_PRECEDENCE):
        if op_upper in [o.upper() for o in ops]:
            return level
    return -1
