# -*- coding: utf-8 -*-
"""
ClickHouse 22.3 SQL Grammar Rules

Source: ClickHouse 22.3 kernel src/Parsers/ (D:\BigData\0.code\22.3\
        ClickHouse_Kernel\src\Parsers\)

This module defines all statement types and their grammar structures
for syntax validation. Each statement type includes:
- Keyword sequence
- Clause order
- Optional/required elements
- ClickHouse-specific syntax

Grammar structures are defined as rule dictionaries that can be used
by a recursive descent parser or syntax checker.

Differences vs ClickHouse 23.3 (which was the reference template):
  REMOVED statement-level features (not supported in 22.3):
    - UNDROP (top-level statement)  - 22.3 has no ParserUndropQuery.cpp;
      only the ALTER TABLE ... UNDROP PARTITION sub-action is supported
      (added later, present in 23.3's ParserUndropQuery). The 22.3 source
      has no UNDROP keyword in ParserAlterQuery.cpp either, so even the
      partition-level UNDROP is absent in 22.3.
    - INTERPOLATE clause            - no ParserKeyword s_interpolate in
      22.3 ParserSelectQuery.cpp (grep returned no matches); 23.3
      introduces it.
    - GROUP BY ALL / ORDER BY ALL   - 22.3 ParserSelectQuery.cpp has no
      'ALL' modifier for GROUP BY / ORDER BY; the 'has_all' flag there is
      only used to disambiguate SELECT ALL from SELECT DISTINCT.
    - Named collections             - no CREATE/ALTER/DROP NAMED COLLECTION
      parsers in 22.3 (grep for 'named collection' / 'NAMED COLLECTION'
      / 'named_collection' returned no files). 23.3 adds
      ParserAlterNamedCollectionQuery.cpp and ParserDropNamedCollectionQuery.cpp.
  KEPT features (verified present in 22.3 source):
    - BACKUP / RESTORE         (ParserBackupQuery.cpp exists; parses
                                `BACKUP ... TO ...` / `RESTORE ... FROM ...`)
    - WITH TIES               (ParserSelectQuery.cpp s_with_ties, both
                                for LIMIT and TOP)
    - DISTINCT ON             (ParserSelectQuery.cpp s_distinct_on;
                                transformed internally to LIMIT 1 BY ...)
    - FETCH FIRST / FETCH NEXT (OFFSET ... FETCH {FIRST|NEXT} ... ONLY|WITH TIES)
    - OFFSET ... ROW | ROWS
    - EXCHANGE TABLES / EXCHANGE DICTIONARIES (ParserRenameQuery.cpp
                                s_exchange_tables / s_exchange_dictionaries;
                                these are an alternative form of RENAME
                                used to swap two tables/dictionaries
                                atomically)
    - GROUP BY ROLLUP / CUBE / GROUPING SETS (via WITH ROLLUP/CUBE)
    - LIVE VIEW ... WITH PERIODIC REFRESH (NOT a standalone REFRESH
                                clause; the Refreshable-MV REFRESH
                                strategy is a 24.x feature absent in
                                22.3 and 23.3 alike)
  Parser files present in 23.3 but MISSING in 22.3 (new statement types
  or helpers; not all are represented as new StatementType entries here
  because some are sub-parsers or access-control helpers not exposed as
  top-level SQL statements in this linter):
    - Access/ParserCreateTenantQuery.cpp, ParserTenantElement.cpp
      (23.3: TENANT concept for cloud; not exposed in 22.3)
    - Kusto/* (23.3: full KQL/Kusto dialect support; absent in 22.3)
    - ParserAlterNamedCollectionQuery.cpp,
      ParserDropNamedCollectionQuery.cpp (23.3: named collections)
    - ParserAttachAccessEntity.cpp     (23.3: ATTACH for access entities)
    - ParserCreateIndexQuery.cpp,
      ParserDropIndexQuery.cpp          (23.3: split-out CREATE/DROP INDEX;
                                         22.3 routes CREATE/DROP INDEX via
                                         ALTER TABLE ADD/DROP INDEX actions
                                         in ParserAlterQuery.cpp)
    - ParserDeleteQuery.cpp            (23.3: standalone DELETE parser file;
                                         22.3 handles DELETE via mutation
                                         inside ALTER TABLE ... DELETE WHERE
                                         and via lightweight DELETE in
                                         parser tables path)
    - ParserDescribeCacheQuery.cpp     (23.3: DESCRIBE CACHE; 22.3 lacks)
    - ParserUndropQuery.cpp            (23.3: UNDROP query)
    - ParserUpsertQuery.cpp           (23.3: UPSERT/INSERT ... ON CONFLICT;
                                         22.3 lacks)
  Clause-level features present in 23.3 but absent in 22.3:
    - INTERPOLATE (see above)
    - GROUP BY ALL / ORDER BY ALL (see above)
    - Named collections (see above)
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set


class StatementType(Enum):
    """All statement types supported by ClickHouse 22.3.

    Compared with 23.3, the UNDROP statement type is removed (22.3 has no
    ParserUndropQuery and no UNDROP keyword in ParserAlterQuery). All
    other top-level statement kinds supported in 23.3 are also supported
    in 22.3 (BACKUP/RESTORE both exist). The differences are at the
    clause / feature level (see module docstring): INTERPOLATE,
    GROUP BY ALL / ORDER BY ALL, and Named collections are absent.
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
    # NOTE: UNDROP removed - not supported in 22.3 (no ParserUndropQuery.cpp
    #       in src/Parsers/, and no UNDROP keyword in ParserAlterQuery.cpp /
    #       ParserQuery.cpp registration). Even the ALTER TABLE ... UNDROP
    #       PARTITION sub-action is absent - it is added later (23.3+).
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
    "description": "SELECT statement with full ClickHouse 22.3 extensions",
    "clauses": [
        {
            "name": "WITH",
            "keywords": ["WITH"],
            "required": False,
            "subclauses": [
                "WITH expr AS alias",
                # NOTE: WITH RECURSIVE is a later addition (24.x); 22.3 only
                # supports WITH cte_expr AS (...) / WITH alias AS (expr).
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
            # NOTE: 22.3 supports GROUP BY ROLLUP / GROUP BY CUBE (via the
            # explicit 'GROUP BY ROLLUP(...)' / 'GROUP BY CUBE(...)' forms and
            # the 'WITH ROLLUP' / 'WITH CUBE' modifiers), but does NOT support
            # 'GROUP BY ALL' (that modifier is added later; here 'ALL' in the
            # has_all branch of ParserSelectQuery only disambiguates
            # SELECT ALL from SELECT DISTINCT).
            "modifiers": ["ROLLUP", "CUBE", "GROUPING SETS"],
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
        # NOTE: QUALIFY clause removed - not supported in 22.3
        #       (QUALIFY is added much later in 24.x; 22.3 has no
        #       ParserKeyword s_qualify in ParserSelectQuery.cpp)
        {
            "name": "ORDER BY",
            "keywords": ["ORDER BY"],
            "required": False,
            # NOTE: 22.3 does NOT support 'ORDER BY ALL' modifier (added later).
            #       The modifiers list below is intentionally empty of 'ALL'.
            "modifiers": [],
            "subclauses": ["expr [ASC|DESC] [NULLS FIRST|LAST] [WITH FILL]"],
        },
        # NOTE: INTERPOLATE clause removed - not supported in 22.3
        #       (no ParserKeyword s_interpolate in 22.3 ParserSelectQuery.cpp;
        #        23.3+ introduces it: 'INTERPOLATE (expr = default, ...)')
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
        "WITH FILL",
        # NOTE: "INTERPOLATE" removed - not supported in 22.3
        #       (23.3 introduces it via ParserKeyword s_interpolate)
        "WITH TIES",
        "TOP N",
        "LIMIT ... BY",
        "WITH TOTALS",
        "WITH ROLLUP",
        "WITH CUBE",
        "GROUP BY ROLLUP/CUBE/GROUPING SETS",
        # NOTE: "GROUP BY ALL" removed - not supported in 22.3
        #       (only added in later versions)
        # NOTE: "ORDER BY ALL" removed - not supported in 22.3
        #       (only added in later versions)
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
        # NOTE: In 22.3 there is no standalone ParserCreateIndexQuery /
        # ParserDropIndexQuery (those are added in 23.3). CREATE INDEX / DROP
        # INDEX are still supported as ALTER TABLE ADD/DROP INDEX actions,
        # routed through ParserAlterQuery.cpp.
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
        # NOTE: 22.3 does NOT support the UNDROP PARTITION / UNDROP PART
        # sub-actions (added later, present in 23.3). The list below
        # intentionally omits 'UNDROP PARTITION partition_expr' and
        # 'UNDROP PART part_name'.
        "DROP PARTITION partition_expr",
        "DROP PART 'part_name'",
        "DETACH PARTITION partition_expr",
        "DETACH PART 'part_name'",
        "ATTACH PARTITION partition_expr",
        "ATTACH PART 'part_name'",
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
        # is a much later feature (ParserRefreshStrategy.cpp in 24.x). 22.3
        # does not support Refreshable MV at all (only LIVE VIEW ... WITH
        # PERIODIC REFRESH n via a different code path).
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
      [INNER | LEFT | RIGHT | FULL | CROSS]    -- 22.3: no PASTE JOIN
      [ANY | ALL | ASOF | SEMI | ANTI]          -- Standard: strictness after direction
      [OUTER]                                    -- LEFT/RIGHT/FULL can have OUTER
      JOIN
      table_expression
      [USING (col, ...) | USING col, ...]
      | [ON condition]
    """,
    # NOTE: "PASTE" removed from directions - PASTE JOIN is added in 24.8;
    #       22.3 (like 23.3) does not support it.
    "directions": ["INNER", "LEFT", "RIGHT", "FULL", "CROSS"],
    "strictness": ["ANY", "ALL", "ASOF", "SEMI", "ANTI"],
    "locality": ["GLOBAL", "LOCAL"],
    "constraints": [
        "CROSS JOIN cannot specify ANY/ALL",
        "SEMI/ANTI JOIN must be LEFT or RIGHT",
        "Default: SEMI/ANTI default to LEFT, others default to INNER",
        # NOTE: constraint mentioning PASTE JOIN removed (no PASTE in 22.3)
    ],
}

ARRAY_JOIN_GRAMMAR = {
    "description": "ARRAY JOIN clause syntax",
    "structure": "[LEFT | INNER] ARRAY JOIN expr, ...",
    "types": ["LEFT", "INNER"],
}

# =============================================================================
# RENAME / EXCHANGE Grammar (22.3-specific: EXCHANGE TABLES/DICTIONARIES
# is parsed inside ParserRenameQuery.cpp as an alternative swap form)
# =============================================================================

RENAME_GRAMMAR = {
    "description": "RENAME TABLE / RENAME DATABASE / RENAME DICTIONARY "
                   "(also EXCHANGE TABLES / EXCHANGE DICTIONARIES in 22.3)",
    "structure": """
    RENAME TABLE [db.]name TO [db.]new_name [, ...]
    | RENAME DATABASE [db.]name TO [db.]new_name
    | RENAME DICTIONARY [db.]name TO [db.]new_name
    | EXCHANGE TABLES [db.]name AND [db.]other_name   -- 22.3: swap two tables
    | EXCHANGE DICTIONARIES [db.]name AND [db.]other  -- 22.3: swap two dicts
    """,
    "forms": [
        "RENAME TABLE",
        "RENAME DATABASE",
        "RENAME DICTIONARY",
        "EXCHANGE TABLES",       # 22.3 atomic two-table swap via RENAME parser
        "EXCHANGE DICTIONARIES", # 22.3 atomic two-dict swap via RENAME parser
    ],
    "clickhouse_specific": [
        # NOTE: EXCHANGE TABLES / EXCHANGE DICTIONARIES is parsed in
        # ParserRenameQuery.cpp (s_exchange_tables / s_exchange_dictionaries).
        # It is exposed here as a ClickHouse-specific RENAME variant.
        "EXCHANGE TABLES a AND b (atomic table swap)",
        "EXCHANGE DICTIONARIES a AND b (atomic dictionary swap)",
    ],
}

# =============================================================================
# BACKUP / RESTORE Grammar (22.3 supports both; ParserBackupQuery.cpp exists)
# =============================================================================

BACKUP_GRAMMAR = {
    "type": StatementType.BACKUP,
    "description": "BACKUP statement (22.3 supports BACKUP ... TO ...)",
    "clauses": [
        {
            "name": "BACKUP",
            "keywords": ["BACKUP"],
            "required": True,
        },
        {
            "name": "elements",
            "required": True,
            "subclauses": [
                "TABLE [db.]name [AS alias]",
                "DATABASE [db.]name [AS alias]",
                "ALL DATABASES",
                "ALL TEMPORARY TABLES",
                "DICTIONARY [db.]name [AS alias]",
                "TEMPORARY TABLE [db.]name [AS alias]",
                "VIEW [db.]name [AS alias]",
                "ALL VIEWS",
            ],
        },
        {
            "name": "TO",
            "keywords": ["TO"],
            "required": True,
            "subclauses": ["File('path') | Disk('disk', 'path') | S3(...) | "],
        },
        {
            "name": "SETTINGS",
            "keywords": ["SETTINGS"],
            "required": False,
            "subclauses": [
                "compression_method = 'zstd'|'gzip'|'none'",
                "compression_level = N",
                "password = 'pwd'",
                "base_backup = File('path') | ...",
            ],
        },
    ],
}

RESTORE_GRAMMAR = {
    "type": StatementType.RESTORE,
    "description": "RESTORE statement (22.3 supports RESTORE ... FROM ...)",
    "clauses": [
        {
            "name": "RESTORE",
            "keywords": ["RESTORE"],
            "required": True,
        },
        {
            "name": "elements",
            "required": True,
            "subclauses": [
                "TABLE [db.]name [AS alias] [FROM [db.]orig]",
                "DATABASE [db.]name [AS alias] [FROM [db.]orig]",
                "ALL DATABASES",
                "ALL TEMPORARY TABLES",
                "DICTIONARY [db.]name [AS alias] [FROM [db.]orig]",
                "TEMPORARY TABLE [db.]name [AS alias] [FROM [db.]orig]",
                "VIEW [db.]name [AS alias] [FROM [db.]orig]",
                "ALL VIEWS",
            ],
        },
        {
            "name": "FROM",
            "keywords": ["FROM"],
            "required": True,
            "subclauses": ["File('path') | Disk('disk', 'path') | S3(...)"],
        },
        {
            "name": "SETTINGS",
            "keywords": ["SETTINGS"],
            "required": False,
            "subclauses": [
                "compression_method = 'zstd'|'gzip'|'none'",
                "compression_level = N",
                "password = 'pwd'",
                "base_backup = File('path') | ...",
            ],
        },
    ],
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
    StatementType.BACKUP: BACKUP_GRAMMAR,
    StatementType.RESTORE: RESTORE_GRAMMAR,
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
