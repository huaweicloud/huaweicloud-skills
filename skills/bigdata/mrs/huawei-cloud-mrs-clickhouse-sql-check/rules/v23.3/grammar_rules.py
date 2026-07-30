# -*- coding: utf-8 -*-
"""
ClickHouse 23.3 SQL Grammar Rules

Source: ClickHouse 23.3 kernel src/Parsers/

This module defines all statement types and their grammar structures
for syntax validation. Each statement type includes:
- Keyword sequence
- Clause order
- Optional/required elements
- ClickHouse-specific syntax

Grammar structures are defined as rule dictionaries that can be used
by a recursive descent parser or syntax checker.

Differences vs ClickHouse 24.8 (master):
  REMOVED statement-level features (not supported in 23.3):
    - QUALIFY clause (added in 24.x; no ParserKeyword s_qualify in 23.3
      ParserSelectQuery.cpp)
    - PASTE JOIN direction (24.8 new join type; absent from
      ParserTablesInSelectQuery.cpp in 23.3)
    - Refreshable Materialized View independent REFRESH strategy
      (24.8 adds ParserRefreshStrategy.cpp + MODIFY REFRESH ALTER action;
      23.3 only has LIVE VIEW ... WITH PERIODIC REFRESH which uses a
      different code path and is NOT a standalone REFRESH clause)
  KEPT features (verified present in 23.3 source):
    - UNDROP query            (ParserUndropQuery.cpp exists)
    - BACKUP / RESTORE        (ParserBackupQuery.cpp exists)
    - WITH TIES               (ParserSelectQuery.cpp s_with_ties)
    - DISTINCT ON             (ParserSelectQuery.cpp s_distinct_on)
    - GROUP BY ALL / ORDER BY ALL
    - INTERPOLATE             (ParserSelectQuery.cpp s_interpolate)
    - FETCH FIRST / FETCH NEXT (OFFSET ... FETCH {FIRST|NEXT} ... ONLY|WITH TIES)
    - Named collections       (handled inside ParserCreateQuery /
                               ParserAlterNamedCollectionQuery /
                               ParserDropNamedCollectionQuery; no separate
                               ParserCreateNamedCollectionQuery file)
    - OFFSET ... ROW | ROWS
  Parser files present in 24.8 but MISSING in 23.3 (new statement types
  or helpers - not represented as new StatementType entries here because
  they are either sub-parsers, Kusto/PRQL dialects, or access-control
  helpers not exposed as top-level SQL statements in this linter):
    - Access/ParserMoveAccessEntityQuery.cpp  (24.8: MOVE ROLE/USER/etc.)
    - Access/ParserPublicSSHKey.cpp
    - Kusto/ParserKQLDateTypeTimespan.cpp, ParserKQLDistinct.cpp,
      ParserKQLExtend.cpp, ParserKQLMVExpand.cpp,
      ParserKQLMakeSeries.cpp, ParserKQLPrint.cpp
    - PRQL/ParserPRQLQuery.cpp               (24.8: PRQL dialect support)
    - ParserRefreshStrategy.cpp               (24.8: Refreshable MV)
    - ParserShowColumnsQuery.cpp,
      ParserShowFunctionsQuery.cpp,
      ParserShowIndexesQuery.cpp,
      ParserShowSettingQuery.cpp
      (24.8: split-out SHOW variants; 23.3 routes them via
       ParserShowTablesQuery / ParserSystemQuery)
    - ParserStringAndSubstitution.cpp
    - ParserTimeInterval.cpp
    - ParserViewTargets.cpp
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set


class StatementType(Enum):
    """All statement types supported by ClickHouse 23.3.

    Compared with 24.8, the same top-level statement kinds are supported
    in 23.3 (UNDROP, BACKUP, RESTORE all exist). The differences are at
    the clause / feature level (see module docstring): QUALIFY, PASTE
    JOIN, and the Refreshable-MV REFRESH strategy are absent.
    """

    # DML
    SELECT = auto()
    INSERT = auto()
    INSERT_SELECT = auto()
    DELETE = auto()
    UPDATE = auto()
    OPTIMIZE = auto()

    # DDL
    CREATE_TABLE = auto()
    CREATE_DATABASE = auto()
    CREATE_VIEW = auto()
    CREATE_MATERIALIZED_VIEW = auto()
    CREATE_DICTIONARY = auto()
    CREATE_FUNCTION = auto()
    CREATE_INDEX = auto()
    ALTER_TABLE = auto()
    ALTER_DATABASE = auto()
    ALTER_VIEW = auto()
    ALTER_DICTIONARY = auto()
    ALTER_FUNCTION = auto()
    DROP_TABLE = auto()
    DROP_DATABASE = auto()
    DROP_VIEW = auto()
    DROP_DICTIONARY = auto()
    DROP_FUNCTION = auto()
    DROP_INDEX = auto()
    RENAME_TABLE = auto()
    RENAME_DATABASE = auto()
    RENAME_DICTIONARY = auto()
    ATTACH = auto()
    DETACH = auto()
    UNDROP = auto()
    CHECK_TABLE = auto()
    DESCRIBE_TABLE = auto()
    USE = auto()
    SET = auto()
    EXTERNAL_DDL = auto()

    # DCL
    GRANT = auto()
    REVOKE = auto()

    # TCL
    BEGIN_TRANSACTION = auto()
    COMMIT = auto()
    ROLLBACK = auto()

    # Utility
    EXPLAIN = auto()
    SHOW = auto()
    KILL = auto()
    SYSTEM = auto()
    BACKUP = auto()
    RESTORE = auto()
    WATCH = auto()


# =============================================================================
# Grammar Rule Structure
# =============================================================================
# Each grammar rule is a dictionary with:
# - type: StatementType enum
# - keywords: List of keywords in order (required)
# - clauses: Dict of clause_name -> clause_definition
# - clickhouse_specific: List of ClickHouse-specific features

class ClauseDefinition:
    """Definition of a SQL clause."""

    def __init__(
        self,
        name: str,
        required: bool = False,
        keywords: List[str] = None,
        subclauses: List[str] = None,
        multiple: bool = False,
    ):
        self.name = name
        self.required = required
        self.keywords = keywords or []
        self.subclauses = subclauses or []
        self.multiple = multiple


# =============================================================================
# DML Grammar Rules
# =============================================================================

SELECT_GRAMMAR = {
    "type": StatementType.SELECT,
    "description": "SELECT statement with full ClickHouse 23.3 extensions",
    "clauses": [
        {
            "name": "WITH",
            "keywords": ["WITH"],
            "required": False,
            "subclauses": [
                "WITH RECURSIVE cte_name AS (subquery)",
                "WITH expr AS alias",
            ],
        },
        {
            "name": "FROM",
            "keywords": ["FROM"],
            "required": False,
            "subclauses": [
                "table_name",
                "table_function(...)",
                "(subquery)",
                "JOIN clause",
                "ARRAY JOIN clause",
            ],
        },
        {
            "name": "SELECT",
            "keywords": ["SELECT"],
            "required": True,
            "modifiers": ["ALL", "DISTINCT", "DISTINCT ON", "TOP N"],
            "subclauses": ["expr_list"],
        },
        {
            "name": "PREWHERE",
            "keywords": ["PREWHERE"],
            "required": False,
            "subclauses": ["expr"],
        },
        {
            "name": "WHERE",
            "keywords": ["WHERE"],
            "required": False,
            "subclauses": ["expr"],
        },
        {
            "name": "GROUP BY",
            "keywords": ["GROUP BY"],
            "required": False,
            "modifiers": ["ROLLUP", "CUBE", "GROUPING SETS", "ALL"],
            "subclauses": ["expr_list"],
        },
        {
            "name": "WITH (aggregation)",
            "keywords": ["WITH"],
            "required": False,
            "modifiers": ["ROLLUP", "CUBE", "TOTALS"],
        },
        {
            "name": "HAVING",
            "keywords": ["HAVING"],
            "required": False,
            "subclauses": ["expr"],
        },
        {
            "name": "WINDOW",
            "keywords": ["WINDOW"],
            "required": False,
            "subclauses": ["window_definition"],
        },
        # NOTE: QUALIFY clause removed - not supported in 23.3
        #       (24.8 adds ParserKeyword s_qualify in ParserSelectQuery.cpp)
        {
            "name": "ORDER BY",
            "keywords": ["ORDER BY"],
            "required": False,
            "modifiers": ["ALL"],
            "subclauses": ["expr [ASC|DESC] [NULLS FIRST|LAST] [WITH FILL]"],
        },
        {
            "name": "INTERPOLATE",
            "keywords": ["INTERPOLATE"],
            "required": False,
            "subclauses": ["(expr = default, ...)"],
        },
        {
            "name": "LIMIT",
            "keywords": ["LIMIT"],
            "required": False,
            "modifiers": ["WITH TIES", "BY"],
            "subclauses": ["[offset,] length", "length BY expr_list"],
        },
        {
            "name": "OFFSET",
            "keywords": ["OFFSET"],
            "required": False,
            "subclauses": ["offset [ROW|ROWS]"],
        },
        {
            "name": "FETCH",
            "keywords": ["FETCH"],
            "required": False,
            "modifiers": ["FIRST", "NEXT", "ROW", "ROWS", "WITH TIES", "ONLY"],
        },
        {
            "name": "SETTINGS",
            "keywords": ["SETTINGS"],
            "required": False,
            "subclauses": ["key = value, ..."],
        },
    ],
    "set_operations": ["UNION", "EXCEPT", "INTERSECT"],
    "set_modifiers": ["ALL", "DISTINCT"],
    "clickhouse_specific": [
        "SAMPLE BY / SAMPLE",
        "FINAL",
        "ARRAY JOIN",
        "LEFT ARRAY JOIN",
        "INNER ARRAY JOIN",
        "PREWHERE",
        "GLOBAL JOIN",
        "LOCAL JOIN",
        "ANY/ALL/ASOF/SEMI/ANTI JOIN",
        # NOTE: "PASTE JOIN" removed - not supported in 23.3
        #       (24.8 adds PASTE join direction in ParserTablesInSelectQuery.cpp)
        "WITH FILL",
        "INTERPOLATE",
        "WITH TIES",
        "TOP N",
        "LIMIT ... BY",
        "WITH TOTALS",
        "WITH ROLLUP",
        "WITH CUBE",
        "GROUP BY ROLLUP/CUBE/GROUPING SETS",
        "GROUP BY ALL",
        "ORDER BY ALL",
        "WITH RECURSIVE",
        "DISTINCT ON",
        "FETCH FIRST/NEXT",
        "OFFSET ... ROW | ROWS",
        "SETTINGS",
        "FROM before SELECT",
    ],
}

INSERT_GRAMMAR = {
    "type": StatementType.INSERT,
    "description": "INSERT statement",
    "clauses": [
        {
            "name": "INSERT INTO",
            "keywords": ["INSERT INTO"],
            "required": True,
            "modifiers": ["TABLE", "FUNCTION", "SELECT"],
        },
        {
            "name": "TABLE",
            "keywords": ["TABLE"],
            "required": False,
        },
        {
            "name": "table_name",
            "required": True,
        },
        {
            "name": "column_list",
            "required": False,
            "subclauses": ["(col1, col2, ...)"],
        },
        {
            "name": "VALUES",
            "keywords": ["VALUES"],
            "required": False,
            "subclauses": ["(val1, val2, ...), ..."],
        },
        {
            "name": "FORMAT",
            "keywords": ["FORMAT"],
            "required": False,
            "subclauses": ["format_name"],
        },
        {
            "name": "FROM INFILE",
            "keywords": ["FROM INFILE"],
            "required": False,
            "subclauses": ["'filename'"],
        },
        {
            "name": "SETTINGS",
            "keywords": ["SETTINGS"],
            "required": False,
            "subclauses": ["key = value, ..."],
        },
    ],
}

INSERT_SELECT_GRAMMAR = {
    "type": StatementType.INSERT_SELECT,
    "description": "INSERT INTO ... SELECT statement",
    "clauses": [
        {
            "name": "INSERT INTO",
            "keywords": ["INSERT INTO"],
            "required": True,
        },
        {
            "name": "TABLE",
            "keywords": ["TABLE"],
            "required": False,
        },
        {
            "name": "table_name",
            "required": True,
        },
        {
            "name": "column_list",
            "required": False,
        },
        {
            "name": "SELECT",
            "keywords": ["SELECT"],
            "required": True,
        },
    ],
}

DELETE_GRAMMAR = {
    "type": StatementType.DELETE,
    "description": "Lightweight DELETE (mutation)",
    "clauses": [
        {
            "name": "DELETE",
            "keywords": ["DELETE"],
            "required": True,
        },
        {
            "name": "FROM",
            "keywords": ["FROM"],
            "required": True,
        },
        {
            "name": "table_name",
            "required": True,
        },
        {
            "name": "WHERE",
            "keywords": ["WHERE"],
            "required": False,
            "subclauses": ["expr"],
        },
    ],
}

UPDATE_GRAMMAR = {
    "type": StatementType.UPDATE,
    "description": "UPDATE statement (mutation)",
    "clauses": [
        {
            "name": "UPDATE",
            "keywords": ["UPDATE"],
            "required": True,
        },
        {
            "name": "table_name",
            "required": True,
        },
        {
            "name": "SET",
            "keywords": ["SET"],
            "required": True,
            "subclauses": ["col = expr, ..."],
        },
        {
            "name": "WHERE",
            "keywords": ["WHERE"],
            "required": False,
            "subclauses": ["expr"],
        },
    ],
}

OPTIMIZE_GRAMMAR = {
    "type": StatementType.OPTIMIZE,
    "description": "OPTIMIZE TABLE statement",
    "clauses": [
        {
            "name": "OPTIMIZE",
            "keywords": ["OPTIMIZE"],
            "required": True,
        },
        {
            "name": "TABLE",
            "keywords": ["TABLE"],
            "required": True,
        },
        {
            "name": "table_name",
            "required": True,
        },
        {
            "name": "ON CLUSTER",
            "keywords": ["ON CLUSTER"],
            "required": False,
        },
        {
            "name": "PARTITION",
            "keywords": ["PARTITION"],
            "required": False,
        },
        {
            "name": "FINAL",
            "keywords": ["FINAL"],
            "required": False,
        },
        {
            "name": "DEDUPLICATE",
            "keywords": ["DEDUPLICATE"],
            "required": False,
            "modifiers": ["BY"],
        },
        {
            "name": "CLEANUP",
            "keywords": ["CLEANUP"],
            "required": False,
        },
    ],
}

# =============================================================================
# DDL Grammar Rules
# =============================================================================

CREATE_TABLE_GRAMMAR = {
    "type": StatementType.CREATE_TABLE,
    "description": "CREATE TABLE statement",
    "clauses": [
        {
            "name": "CREATE",
            "keywords": ["CREATE"],
            "required": True,
        },
        {
            "name": "TEMPORARY",
            "keywords": ["TEMPORARY"],
            "required": False,
        },
        {
            "name": "TABLE",
            "keywords": ["TABLE"],
            "required": True,
        },
        {
            "name": "IF NOT EXISTS",
            "keywords": ["IF NOT EXISTS"],
            "required": False,
        },
        {
            "name": "table_name",
            "required": True,
        },
        {
            "name": "ON CLUSTER",
            "keywords": ["ON CLUSTER"],
            "required": False,
        },
        {
            "name": "UUID",
            "keywords": ["UUID"],
            "required": False,
        },
        {
            "name": "column_definitions",
            "required": False,
            "subclauses": ["(col1 type1, col2 type2, ...)"],
        },
        {
            "name": "ENGINE",
            "keywords": ["ENGINE"],
            "required": False,
            "subclauses": ["= engine_name(params...)"],
        },
        {
            "name": "ORDER BY",
            "keywords": ["ORDER BY"],
            "required": False,  # Required for MergeTree family
            "subclauses": ["expr"],
        },
        {
            "name": "PARTITION BY",
            "keywords": ["PARTITION BY"],
            "required": False,
            "subclauses": ["expr"],
        },
        {
            "name": "PRIMARY KEY",
            "keywords": ["PRIMARY KEY"],
            "required": False,
            "subclauses": ["expr"],
        },
        {
            "name": "SAMPLE BY",
            "keywords": ["SAMPLE BY"],
            "required": False,
            "subclauses": ["expr"],
        },
        {
            "name": "TTL",
            "keywords": ["TTL"],
            "required": False,
            "subclauses": ["expr [, expr, ...]"],
        },
        {
            "name": "SETTINGS",
            "keywords": ["SETTINGS"],
            "required": False,
            "subclauses": ["name = value, ..."],
        },
        {
            "name": "AS SELECT",
            "keywords": ["AS", "SELECT"],
            "required": False,
        },
        {
            "name": "COMMENT",
            "keywords": ["COMMENT"],
            "required": False,
            "subclauses": ["'string'"],
        },
    ],
}

ALTER_TABLE_GRAMMAR = {
    "type": StatementType.ALTER_TABLE,
    "description": "ALTER TABLE statement with all actions",
    "actions": [
        # Column actions
        "ADD COLUMN [IF NOT EXISTS] name type [AFTER name]",
        "DROP COLUMN [IF EXISTS] name",
        "CLEAR COLUMN [IF EXISTS] name [IN PARTITION partition]",
        "MODIFY COLUMN [IF EXISTS] name type [AFTER name]",
        "RENAME COLUMN [IF EXISTS] old_name TO new_name",
        "COMMENT COLUMN [IF EXISTS] name 'string'",
        "MATERIALIZE COLUMN [IF EXISTS] name [IN PARTITION partition]",
        # Index actions
        "ADD INDEX [IF NOT EXISTS] name expr TYPE type GRANULARITY granularity",
        "DROP INDEX [IF EXISTS] name",
        "CLEAR INDEX [IF EXISTS] name [IN PARTITION partition]",
        "MATERIALIZE INDEX [IF EXISTS] name [IN PARTITION partition]",
        # Projection actions
        "ADD PROJECTION [IF NOT EXISTS] name (SELECT ...)",
        "DROP PROJECTION [IF EXISTS] name",
        "CLEAR PROJECTION [IF EXISTS] name [IN PARTITION partition]",
        "MATERIALIZE PROJECTION [IF EXISTS] name [IN PARTITION partition]",
        # Statistics actions
        "ADD STATISTICS [IF NOT EXISTS] col1, col2, ... TYPE type(params)",
        "DROP STATISTICS [IF EXISTS] col1, col2, ...",
        "MODIFY STATISTICS col1, col2, ... TYPE type(params)",
        "CLEAR STATISTICS [IF EXISTS] col1, col2, ... [IN PARTITION partition]",
        "MATERIALIZE STATISTICS [IF EXISTS] col1, col2, ... [IN PARTITION partition]",
        # Constraint actions
        "ADD CONSTRAINT [IF NOT EXISTS] name CHECK|ASSUME (expr)",
        "DROP CONSTRAINT [IF EXISTS] name",
        # Partition actions
        "DROP PARTITION partition_expr",
        "DROP PART 'part_name'",
        "DETACH PARTITION partition_expr",
        "DETACH PART 'part_name'",
        "ATTACH PARTITION partition_expr",
        "ATTACH PART 'part_name'",
        "UNDROP PARTITION partition_expr",
        "UNDROP PART 'part_name'",
        "FORGET PARTITION partition_expr",
        "DROP DETACHED PARTITION partition_expr",
        "DROP DETACHED PART 'part_name'",
        "REPLACE PARTITION partition_expr FROM [db.]table",
        "MOVE PARTITION partition_expr TO DISK|VOLUME 'name' | TO TABLE [db.]table",
        "MOVE PART 'part_name' TO DISK|VOLUME|SHARD 'name'",
        "FETCH PARTITION partition_expr FROM 'source'",
        "FETCH PART 'part_name' FROM 'source'",
        "FREEZE [PARTITION partition_expr]",
        "UNFREEZE [PARTITION partition_expr]",
        # Data manipulation
        "DELETE [IN PARTITION partition] WHERE predicate",
        "UPDATE col = expr, ... [IN PARTITION partition] WHERE predicate",
        # Settings
        "MODIFY SETTING name = value, ...",
        "RESET SETTING name, name, ...",
        # Other
        "MODIFY QUERY SELECT ...",
        "MODIFY SQL SECURITY DEFINER|INVOKER|NONE",
        "MODIFY DEFINER = user_name",
        # NOTE: "MODIFY REFRESH ..." removed - Refreshable MV REFRESH strategy
        # is a 24.8 feature (ParserRefreshStrategy.cpp). 23.3 only supports
        # LIVE VIEW ... WITH PERIODIC REFRESH n via a different syntax tree
        # field (live_view_periodic_refresh), not a standalone ALTER action.
        "MODIFY COMMENT 'string'",
        "APPLY DELETED MASK [IN PARTITION partition]",
    ],
}

# =============================================================================
# JOIN Grammar
# =============================================================================

JOIN_GRAMMAR = {
    "description": "JOIN clause syntax",
    "structure": """
    [GLOBAL | LOCAL]
      [ANY | ALL | ASOF | SEMI | ANTI]          -- Legacy: strictness before direction
      [INNER | LEFT | RIGHT | FULL | CROSS]    -- 23.3: no PASTE JOIN
      [ANY | ALL | ASOF | SEMI | ANTI]          -- Standard: strictness after direction
      [OUTER]                                    -- LEFT/RIGHT/FULL can have OUTER
      JOIN
      table_expression
      [USING (col, ...) | USING col, ...]
      | [ON condition]
    """,
    # NOTE: "PASTE" removed from directions - not supported in 23.3
    "directions": ["INNER", "LEFT", "RIGHT", "FULL", "CROSS"],
    "strictness": ["ANY", "ALL", "ASOF", "SEMI", "ANTI"],
    "locality": ["GLOBAL", "LOCAL"],
    "constraints": [
        "CROSS JOIN cannot specify ANY/ALL",
        "SEMI/ANTI JOIN must be LEFT or RIGHT",
        "Default: SEMI/ANTI default to LEFT, others default to INNER",
        # NOTE: constraint mentioning PASTE JOIN removed (no PASTE in 23.3)
    ],
}

ARRAY_JOIN_GRAMMAR = {
    "description": "ARRAY JOIN clause syntax",
    "structure": "[LEFT | INNER] ARRAY JOIN expr, ...",
    "types": ["LEFT", "INNER"],
}

# =============================================================================
# Grammar Registry
# =============================================================================

GRAMMAR_REGISTRY = {
    StatementType.SELECT: SELECT_GRAMMAR,
    StatementType.INSERT: INSERT_GRAMMAR,
    StatementType.INSERT_SELECT: INSERT_SELECT_GRAMMAR,
    StatementType.DELETE: DELETE_GRAMMAR,
    StatementType.UPDATE: UPDATE_GRAMMAR,
    StatementType.OPTIMIZE: OPTIMIZE_GRAMMAR,
    StatementType.CREATE_TABLE: CREATE_TABLE_GRAMMAR,
    StatementType.ALTER_TABLE: ALTER_TABLE_GRAMMAR,
}


def get_grammar(statement_type: StatementType) -> Optional[Dict]:
    """Get grammar definition for a statement type."""
    return GRAMMAR_REGISTRY.get(statement_type)


def get_all_statement_types() -> List[StatementType]:
    """Get all supported statement types."""
    return list(StatementType)


def get_clickhouse_specific_features(statement_type: StatementType) -> List[str]:
    """Get ClickHouse-specific features for a statement type."""
    grammar = get_grammar(statement_type)
    if grammar:
        return grammar.get("clickhouse_specific", [])
    return []


if __name__ == "__main__":
    print(f"Total statement types: {len(StatementType)}")
    print(f"Grammar rules defined: {len(GRAMMAR_REGISTRY)}")
    print("\nStatement types:")
    for stmt_type in StatementType:
        print(f"  - {stmt_type.name}")
