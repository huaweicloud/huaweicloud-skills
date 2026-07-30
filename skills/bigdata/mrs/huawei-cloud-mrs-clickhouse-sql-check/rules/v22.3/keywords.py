# -*- coding: utf-8 -*-
"""
ClickHouse 22.3 SQL Keyword Definitions

Source: ClickHouse 22.3 kernel src/Parsers/ (recursive scan of .cpp/.h/.hpp)
        D:\\BigData\\0.code\\22.3\\ClickHouse_Kernel\\src\\Parsers\\
        (including subdirectories Access/, MySQL/, examples/, fuzzers/, tests/)

Extraction method:
  Searched every ParserKeyword("...") call site across the Parsers directory,
  covering four syntactic variants of the call:
    1. ParserKeyword("X")               inline, round-bracket
    2. ParserKeyword name("X")          named local variable, round-bracket
    3. ParserKeyword{"X"}              inline, brace-init
    4. ParserKeyword name{"X"}          named local variable, brace-init
  Regex used:  ParserKeyword(?:\s+\w+)?\s*[(\{]\s*"([^"]+)"
  Quoted strings captured, deduplicated, casing normalized to match 24.8
  conventions (ClickHouse keywords are case-insensitive, so the lowercase
  forms found in 22.3 source like 'by', 'true', 'false', 'currentUser' were
  folded to 'BY', 'TRUE', 'FALSE', 'CURRENTUSER').
  The string 'literal' was excluded because its only occurrence is in a
  code comment inside src/Parsers/CommonParsers.h ("Want to be able to init
  ParserKeyword(\"literal\")") and is not an actual keyword call.

Result: 422 unique keywords (vs 571 in 24.8 and 462 in 23.3).

Differences from 23.3 (462 keywords):
  - 416 keywords are common to both 22.3 and 23.3.
  - 46 keywords present in 23.3 are NOT found in 22.3 ParserKeyword calls.
    These are keywords added between 22.3 and 23.3, or moved to be handled
    by Lexer TokenType matching rather than ParserKeyword calls. Namely:
      ALTER TENANT, AND STDOUT, ATTACH TENANT, AUTO_INCREMENT, BIDIRECTIONAL, CHANGEABLE_IN_READONLY, CLEANUP, cluster_host_ids, CONST, CREATE TENANT, EMPTY, EMPTY AS, EVENT, EXCEPT DATABASE, EXCEPT DATABASES, EXCEPT TABLE, EXCEPT TABLES, FILE, FILESYSTEM CACHE, FILESYSTEM CACHES, GROUPING SETS, H, HDFS, INTERPOLATE, LEVEL, MATERIALIZE, MCS, MICROSECOND, MILLISECOND, MS, NAMED COLLECTION, NANOSECOND, NS, PBKDF2_PASSWORD, QUERY TREE, S3, SALT, SHOW ENGINES, SQL_TSI_MICROSECOND, SQL_TSI_MILLISECOND, SQL_TSI_NANOSECOND, TRIGGER, UNDROP, UPSERT INTO, URL, WITH NAME
  - 6 keywords present in 22.3 are NOT found in 23.3 ParserKeyword calls.
    These are keywords that were removed, renamed, or moved to other parser
    mechanisms (e.g. Lexer TokenType) between 22.3 and 23.3. Namely:
      ALL DATABASES, ALL TEMPORARY TABLES, EVERYTHING, INTO, IS, TIMEOUT
    - ALL DATABASES, ALL TEMPORARY TABLES, EVERYTHING, INTO: appear only in
      22.3's ParserBackupQuery.cpp BACKUP/RESTORE syntax, which was
      restructured in 23.3.
    - IS: used in 22.3 ExpressionListParsers.cpp; in 23.3 handled by the
      Lexer as part of IS NULL / IS NOT NULL token matching.
    - TIMEOUT: appeared as a ParserKeyword in 22.3 ParserCreateQuery.cpp
      but no longer in 23.3 ParserKeyword form.

The 422 keywords here are the ones explicitly referenced through
ParserKeyword calls in 22.3 source. For SQL-lint purposes this captures
the structured / multi-token keywords and most operator keywords.

ClickHouse keywords are case-insensitive and require word boundaries.
Compound keywords (e.g. "ORDER BY") allow whitespace/comments between parts.

Category subsets (DML/DDL/DCL/...) are provided for reporting and rule
targeting only - a keyword may appear in more than one category. They are
filtered from the 23.3 categories to only include the 422 keywords
present in 22.3. They are NOT the source of truth; KEYWORDS is.
"""

from enum import Enum


class KeywordCategory(Enum):
    """Keyword category for reporting."""
    DML = "DML"
    DDL = "DDL"
    DCL = "DCL"
    TCL = "TCL"
    UTILITY = "Utility"
    ACCESS = "Access Control"
    SELECT_CLAUSE = "SELECT Clause"
    JOIN = "JOIN"
    OPERATOR = "Operator/Predicate"
    DATA_TYPE = "Data Type"
    TIME_UNIT = "Time Unit"
    DATE_TOKEN = "Date Format Token"
    DICTIONARY = "Dictionary"
    PARTITION = "Partition/Part"
    ALTER_ACTION = "ALTER Action"
    SETTING = "Setting"
    SHOW = "SHOW"
    MISC = "Miscellaneous"


# =============================================================================
# Authoritative keyword list (extracted from 22.3 src/Parsers/, 422 entries)
# Case normalized to match 24.8. Matched case-insensitively.
# =============================================================================
KEYWORDS = (
    "ADD", "ADD COLUMN", "ADD CONSTRAINT", "ADD INDEX", "ADD PROJECTION", "ADMIN OPTION FOR", "AFTER", "ALGORITHM", "ALIAS", "ALL", "ALL DATABASES", "ALL TEMPORARY TABLES",
    "ALLOWED_LATENESS", "ALTER", "ALTER COLUMN", "ALTER DATABASE", "ALTER LIVE VIEW", "ALTER POLICY", "ALTER PROFILE", "ALTER QUOTA", "ALTER ROLE", "ALTER ROW POLICY", "ALTER SETTINGS PROFILE", "ALTER TABLE",
    "ALTER USER", "AND", "ANTI", "ANY", "APPLY", "ARRAY JOIN", "AS", "ASC", "ASCENDING", "ASOF", "ASSUME", "AST",
    "ASYNC", "ATTACH", "ATTACH PART", "ATTACH PARTITION", "ATTACH POLICY", "ATTACH PROFILE", "ATTACH QUOTA", "ATTACH ROLE", "ATTACH ROW POLICY", "ATTACH SETTINGS PROFILE", "ATTACH USER", "BACKUP",
    "base_backup", "BEGIN TRANSACTION", "BETWEEN", "BOTH", "BY", "CASCADE", "CASE", "CHANGE", "CHANGED", "CHAR", "CHAR VARYING", "CHARACTER",
    "CHARACTER LARGE OBJECT", "CHARACTER VARYING", "CHECK", "CHECK TABLE", "CHECK TRANSACTION", "CLEAR COLUMN", "CLEAR INDEX", "CLEAR PROJECTION", "CLUSTER", "CLUSTERS", "CN", "CODEC",
    "COLLATE", "COLUMN", "COLUMNS", "COMMENT", "COMMENT COLUMN", "COMMIT", "COMPRESSION", "CONSTRAINT", "CREATE", "CREATE POLICY", "CREATE PROFILE", "CREATE QUOTA",
    "CREATE ROLE", "CREATE ROW POLICY", "CREATE SETTINGS PROFILE", "CREATE TABLE", "CREATE TEMPORARY TABLE", "CREATE USER", "CROSS", "CUBE", "CURRENT QUOTA", "CURRENT ROLES", "CURRENT ROW", "CURRENT TRANSACTION",
    "CURRENTUSER", "CURRENT_USER", "D", "DATABASE", "DATABASES", "DATE", "DAY", "DD", "DEDUPLICATE", "DEFAULT", "DEFAULT DATABASE", "DEFAULT ROLE",
    "DELETE", "DESC", "DESCENDING", "DESCRIBE", "DETACH", "DETACH PART", "DETACH PARTITION", "DICTIONARIES", "DICTIONARY", "DISK", "DISTINCT", "DISTINCT ON",
    "DOUBLE_SHA1_HASH", "DROP", "DROP COLUMN", "DROP CONSTRAINT", "DROP DEFAULT", "DROP DETACHED PART", "DROP DETACHED PARTITION", "DROP INDEX", "DROP PART", "DROP PARTITION", "DROP PROJECTION", "DROP TABLE",
    "ELSE", "ENABLED ROLES", "END", "ENFORCED", "ENGINE", "EPHEMERAL", "ESTIMATE", "EVENTS", "EVERYTHING", "EXCEPT", "EXCHANGE DICTIONARIES", "EXCHANGE TABLES",
    "EXISTS", "EXPLAIN", "EXPRESSION", "EXTERNAL DDL FROM", "FALSE", "FETCH", "FETCH PART", "FETCH PARTITION", "FILTER", "FINAL", "FIRST", "FOLLOWING",
    "FOR", "FOREIGN", "FOREIGN KEY", "FORMAT", "FREEZE", "FROM", "FROM INFILE", "FULL", "FULLTEXT", "FUNCTION", "GLOBAL", "GRANT",
    "GRANT OPTION FOR", "GRANTEES", "GRANULARITY", "GROUP BY", "GROUPS", "HASH", "HAVING", "HH", "HIERARCHICAL", "HOST", "HOUR", "ID",
    "IDENTIFIED", "IF EXISTS", "IF NOT EXISTS", "ILIKE", "IN", "IN PARTITION", "INDEX", "INHERIT", "INJECTIVE", "INNER", "INSERT INTO", "INTERSECT",
    "INTERVAL", "INTO", "INTO OUTFILE", "INVISIBLE", "IP", "IS", "IS_OBJECT_ID", "JOIN", "KEY", "KEY BY", "KEYED BY", "KILL",
    "LARGE OBJECT", "LAST", "LAYOUT", "LEADING", "LEFT", "LEFT ARRAY JOIN", "LESS THAN", "LIFETIME", "LIKE", "LIMIT", "LINEAR", "LIST",
    "LIVE", "LOCAL", "M", "MATCH", "MATERIALIZE COLUMN", "MATERIALIZE INDEX", "MATERIALIZE PROJECTION", "MATERIALIZE TTL", "MATERIALIZED", "MAX", "MEMORY", "MI",
    "MIN", "MINUTE", "MM", "MODIFY", "MODIFY COLUMN", "MODIFY COMMENT", "MODIFY ORDER BY", "MODIFY QUERY", "MODIFY SAMPLE BY", "MODIFY SETTING", "MODIFY TTL", "MONTH",
    "MOVE PART", "MOVE PARTITION", "MUTATION", "N", "NAME", "NEXT", "NO ACTION", "NO DELAY", "NO LIMITS", "NONE", "NOT", "NOT IDENTIFIED",
    "NOT KEYED", "NULL", "NULLS", "OFFSET", "ON", "ON DELETE", "ON UPDATE", "ON VOLUME", "ONLY", "OPTIMIZE TABLE", "OR REPLACE", "ORDER BY",
    "OUTER", "OVER", "PARTIAL", "PARTITION", "PARTITION BY", "PARTITIONS", "PART_MOVE_TO_SHARD", "PERIODIC REFRESH", "PERMANENTLY", "PERMISSIVE", "PIPELINE", "PLAN",
    "POPULATE", "PRECEDING", "PRECISION", "PREWHERE", "PRIMARY", "PRIMARY KEY", "PROFILE", "PROJECTION", "Q", "QQ", "QUARTER", "QUERY",
    "QUOTA", "RANDOMIZED", "RANGE", "READONLY", "REALM", "RECOMPRESS", "REFERENCES", "REFRESH", "REGEXP", "REMOVE", "REMOVE SAMPLE BY", "REMOVE TTL",
    "RENAME", "RENAME COLUMN", "RENAME DATABASE", "RENAME DICTIONARY", "RENAME TABLE", "RENAME TO", "REPLACE", "REPLACE PARTITION", "RESET SETTING", "RESTORE", "RESTRICT", "RESTRICTIVE",
    "RESUME", "REVOKE", "RIGHT", "ROLLBACK", "ROLLUP", "ROW", "ROWS", "S", "SAMPLE", "SAMPLE BY", "SECOND", "SELECT",
    "SEMI", "SERVER", "SET", "SET DEFAULT", "SET DEFAULT ROLE", "SET NULL", "SET ROLE", "SET ROLE DEFAULT", "SET TRANSACTION SNAPSHOT", "SETTINGS", "SHA256_HASH", "SHOW",
    "SHOW ACCESS", "SHOW CREATE", "SHOW GRANTS", "SHOW PRIVILEGES", "SHOW PROCESSLIST", "SIGNED", "SIMPLE", "SOURCE", "SPATIAL", "SQL_TSI_DAY", "SQL_TSI_HOUR", "SQL_TSI_MINUTE",
    "SQL_TSI_MONTH", "SQL_TSI_QUARTER", "SQL_TSI_SECOND", "SQL_TSI_WEEK", "SQL_TSI_YEAR", "SS", "STEP", "STORAGE", "STRICT", "STRICTLY_ASCENDING", "SUBPARTITION", "SUBPARTITION BY",
    "SUBPARTITIONS", "SUSPEND", "SYNC", "SYNTAX", "SYSTEM", "TABLE", "TABLE OVERRIDE", "TABLES", "TEMPORARY", "TEMPORARY TABLE", "TEST", "THEN",
    "TIMEOUT", "TIMESTAMP", "TO", "TO DISK", "TO INNER UUID", "TO SHARD", "TO TABLE", "TO VOLUME", "TOP", "TOTALS", "TRACKING ONLY", "TRAILING",
    "TRANSACTION", "TRUE", "TRUNCATE", "TTL", "TYPE", "UNBOUNDED", "UNFREEZE", "UNION", "UNIQUE", "UNSIGNED", "UPDATE", "USE",
    "USING", "UUID", "VALUES", "VARYING", "VIEW", "VISIBLE", "WATCH", "WATERMARK", "WEEK", "WHEN", "WHERE", "WINDOW",
    "WITH", "WITH ADMIN OPTION", "WITH CHECK", "WITH FILL", "WITH GRANT OPTION", "WITH REPLACE OPTION", "WITH TIES", "WK", "WRITABLE", "WW", "YEAR", "YY",
    "YYYY", "ZKPATH",
)

# Master set (original case) + uppercase index for case-insensitive lookup.
ALL_KEYWORDS = set(KEYWORDS)
_KEYWORDS_UPPER = {k.upper() for k in KEYWORDS}


# =============================================================================
# Category subsets (filtered from 23.3 categories to 22.3 keywords only)
# =============================================================================
DML_KEYWORDS = {
    "DEDUPLICATE", "DELETE", "FINAL", "FROM INFILE", "INSERT INTO", "INTO OUTFILE",
    "OPTIMIZE TABLE", "SELECT", "TRUNCATE", "UPDATE", "VALUES"
}

DDL_KEYWORDS = {
    "ALGORITHM", "ALTER", "ALTER DATABASE", "ALTER LIVE VIEW", "ALTER TABLE", "AS",
    "ATTACH", "ATTACH PART", "ATTACH PARTITION", "CHANGE", "CHANGED", "CHECK",
    "CHECK TABLE", "CHECK TRANSACTION", "CODEC", "COMMENT", "COMMENT COLUMN", "COMPRESSION",
    "CONSTRAINT", "CREATE", "CREATE TABLE", "CREATE TEMPORARY TABLE", "DATABASE", "DATABASES",
    "DESCRIBE", "DETACH", "DETACH PART", "DETACH PARTITION", "DROP", "DROP TABLE",
    "ENGINE", "EXCHANGE DICTIONARIES", "EXCHANGE TABLES", "EXTERNAL DDL FROM", "FOREIGN", "FOREIGN KEY",
    "FUNCTION", "GRANULARITY", "IF EXISTS", "IF NOT EXISTS", "INDEX", "LIVE",
    "MATERIALIZED", "OR REPLACE", "ORDER BY", "PARTITION BY", "POPULATE", "PRIMARY",
    "PRIMARY KEY", "PROJECTION", "RENAME", "RENAME COLUMN", "RENAME DATABASE", "RENAME DICTIONARY",
    "RENAME TABLE", "RENAME TO", "SAMPLE BY", "SETTINGS", "STEP", "TABLE",
    "TABLE OVERRIDE", "TABLES", "TEMPORARY", "TEMPORARY TABLE", "TO INNER UUID", "TRUNCATE",
    "TTL", "TYPE", "UNIQUE", "USE", "VIEW", "WITH"
}

DCL_KEYWORDS = {
    "ADMIN OPTION FOR", "ALTER POLICY", "ALTER PROFILE", "ALTER QUOTA", "ALTER ROLE", "ALTER ROW POLICY",
    "ALTER SETTINGS PROFILE", "ALTER USER", "ATTACH POLICY", "ATTACH PROFILE", "ATTACH QUOTA", "ATTACH ROLE",
    "ATTACH ROW POLICY", "ATTACH SETTINGS PROFILE", "ATTACH USER", "CREATE POLICY", "CREATE PROFILE", "CREATE QUOTA",
    "CREATE ROLE", "CREATE ROW POLICY", "CREATE SETTINGS PROFILE", "CREATE USER", "CURRENT QUOTA", "CURRENT ROLES",
    "CURRENTUSER", "CURRENT_USER", "DEFAULT ROLE", "DOUBLE_SHA1_HASH", "ENABLED ROLES", "GRANT",
    "GRANT OPTION FOR", "GRANTEES", "HOST", "ID", "IDENTIFIED", "IP",
    "IS_OBJECT_ID", "NAME", "NOT IDENTIFIED", "READONLY", "REALM", "REVOKE",
    "SET DEFAULT", "SET DEFAULT ROLE", "SET NULL", "SET ROLE", "SET ROLE DEFAULT", "SHA256_HASH",
    "SHOW ACCESS", "SHOW CREATE", "SHOW GRANTS", "SHOW PRIVILEGES", "WITH ADMIN OPTION", "WITH GRANT OPTION"
}

TCL_KEYWORDS = {
    "BEGIN TRANSACTION", "CHECK TRANSACTION", "COMMIT", "CURRENT TRANSACTION", "ROLLBACK", "SET TRANSACTION SNAPSHOT",
    "TRANSACTION"
}

UTILITY_KEYWORDS = {
    "AST", "BACKUP", "ESTIMATE", "EXPLAIN", "FETCH", "FETCH PART",
    "FETCH PARTITION", "FREEZE", "KILL", "MUTATION", "OPTIMIZE TABLE", "PART_MOVE_TO_SHARD",
    "PIPELINE", "PLAN", "QUERY", "RESTORE", "RESUME", "SET",
    "SHOW", "SUSPEND", "SYNTAX", "SYSTEM", "TEST", "TRACKING ONLY",
    "UNFREEZE", "WATCH"
}

SELECT_CLAUSE_KEYWORDS = {
    "ALIAS", "ALL", "ANY", "ARRAY JOIN", "AS", "ASC",
    "ASCENDING", "BETWEEN", "BY", "CUBE", "CURRENT ROW", "DESC",
    "DESCENDING", "DISTINCT", "DISTINCT ON", "EXCEPT", "FINAL", "FIRST",
    "FOLLOWING", "FORMAT", "FROM", "FROM INFILE", "GROUP BY", "GROUPS",
    "HAVING", "INTERSECT", "INTO OUTFILE", "LAST", "LEFT ARRAY JOIN", "LIMIT",
    "NO LIMITS", "NULLS", "OFFSET", "ON", "ONLY", "ORDER BY",
    "OVER", "PARTIAL", "PRECEDING", "PREWHERE", "RANGE", "ROLLUP",
    "ROW", "ROWS", "SAMPLE", "SAMPLE BY", "SELECT", "SETTINGS",
    "TO", "TOP", "TOTALS", "UNBOUNDED", "UNION", "USING",
    "VALUES", "WHERE", "WINDOW", "WITH", "WITH FILL", "WITH TIES"
}

JOIN_KEYWORDS = {
    "ALL", "ANTI", "ANY", "ARRAY JOIN", "ASOF", "CROSS",
    "FULL", "GLOBAL", "HIERARCHICAL", "IN", "IN PARTITION", "INNER",
    "JOIN", "KEY BY", "KEYED BY", "LEFT", "LEFT ARRAY JOIN", "NOT KEYED",
    "ON", "OUTER", "RIGHT", "SEMI", "USING"
}

OPERATOR_KEYWORDS = {
    "AND", "ASSUME", "BETWEEN", "CASE", "COLLATE", "CONSTRAINT",
    "ELSE", "END", "EXISTS", "FALSE", "FILTER", "FULLTEXT",
    "ILIKE", "IN", "INTERVAL", "LIKE", "MATCH", "NOT",
    "NULL", "OVER", "REFERENCES", "REGEXP", "THEN", "TRUE",
    "WHEN"
}

DATA_TYPE_KEYWORDS = {
    "CHAR", "CHAR VARYING", "CHARACTER", "CHARACTER LARGE OBJECT", "CHARACTER VARYING", "DATE",
    "LARGE OBJECT", "PRECISION", "SIGNED", "SIMPLE", "TIMESTAMP", "UNSIGNED",
    "UUID", "VARYING"
}

TIME_UNIT_KEYWORDS = {
    "DAY", "HOUR", "INTERVAL", "MINUTE", "MONTH", "QUARTER",
    "SECOND", "SQL_TSI_DAY", "SQL_TSI_HOUR", "SQL_TSI_MINUTE", "SQL_TSI_MONTH", "SQL_TSI_QUARTER",
    "SQL_TSI_SECOND", "SQL_TSI_WEEK", "SQL_TSI_YEAR", "WEEK", "YEAR"
}

DATE_TOKEN_KEYWORDS = {
    "D", "DD", "HH", "M", "MI", "MM",
    "N", "Q", "QQ", "S", "SS", "WK",
    "WW", "YY", "YYYY"
}

DICTIONARY_KEYWORDS = {
    "DICTIONARIES", "DICTIONARY", "EVENTS", "EXPRESSION", "HIERARCHICAL", "INJECTIVE",
    "LAYOUT", "LIFETIME", "RANGE", "SOURCE"
}

PARTITION_KEYWORDS = {
    "ATTACH PART", "ATTACH PARTITION", "DETACH PART", "DETACH PARTITION", "DISK", "DROP DETACHED PART",
    "DROP DETACHED PARTITION", "DROP PART", "DROP PARTITION", "FETCH PART", "FETCH PARTITION", "FREEZE",
    "MOVE PART", "MOVE PARTITION", "PARTITION", "PARTITION BY", "PARTITIONS", "PART_MOVE_TO_SHARD",
    "RECOMPRESS", "REPLACE PARTITION", "SUBPARTITION", "SUBPARTITION BY", "SUBPARTITIONS", "TO DISK",
    "TO INNER UUID", "TO SHARD", "TO TABLE", "TO VOLUME", "UNFREEZE"
}

ALTER_ACTION_KEYWORDS = {
    "ADD", "ADD COLUMN", "ADD CONSTRAINT", "ADD INDEX", "ADD PROJECTION", "AFTER",
    "ALTER COLUMN", "CASCADE", "CHANGE", "CLEAR COLUMN", "CLEAR INDEX", "CLEAR PROJECTION",
    "CODEC", "COLUMN", "COLUMNS", "COMMENT", "COMMENT COLUMN", "COMPRESSION",
    "DROP COLUMN", "DROP CONSTRAINT", "DROP DEFAULT", "DROP INDEX", "DROP PROJECTION", "ENFORCED",
    "ENGINE", "FOREIGN", "FOREIGN KEY", "GRANULARITY", "INDEX", "INVISIBLE",
    "LESS THAN", "MATERIALIZE COLUMN", "MATERIALIZE INDEX", "MATERIALIZE PROJECTION", "MATERIALIZE TTL", "MODIFY",
    "MODIFY COLUMN", "MODIFY COMMENT", "MODIFY ORDER BY", "MODIFY QUERY", "MODIFY SAMPLE BY", "MODIFY SETTING",
    "MODIFY TTL", "NEXT", "NO ACTION", "NONE", "ON DELETE", "ON UPDATE",
    "ON VOLUME", "PERIODIC REFRESH", "PERMISSIVE", "PRIMARY", "PRIMARY KEY", "PROJECTION",
    "REFRESH", "REMOVE", "REMOVE SAMPLE BY", "REMOVE TTL", "RENAME COLUMN", "RENAME TO",
    "REPLACE", "REPLACE PARTITION", "RESET SETTING", "RESTRICT", "RESTRICTIVE", "SET DEFAULT",
    "SET NULL", "STEP", "TTL", "VISIBLE"
}

SETTING_KEYWORDS = {
    "ALLOWED_LATENESS", "base_backup", "CODEC", "COMPRESSION", "DEFAULT", "DEFAULT DATABASE",
    "DISK", "ENGINE", "EPHEMERAL", "MEMORY", "PERMANENTLY", "PROFILE",
    "QUOTA", "READONLY", "SETTINGS", "STORAGE", "STRICTLY_ASCENDING", "TEMPORARY",
    "TEMPORARY TABLE", "TRACKING ONLY", "WATERMARK", "ZKPATH"
}

SHOW_KEYWORDS = {
    "CLUSTERS", "DATABASES", "DICTIONARIES", "EVENTS", "PARTITIONS", "SHOW",
    "SHOW ACCESS", "SHOW CREATE", "SHOW GRANTS", "SHOW PRIVILEGES", "SHOW PROCESSLIST", "TABLES"
}

MISC_KEYWORDS = {
    "ASSUME", "ASYNC", "BOTH", "CASCADE", "CHAR", "CHARACTER",
    "CLUSTER", "CLUSTERS", "CN", "COMMENT", "ENFORCED", "ESTIMATE",
    "EXPRESSION", "FOR", "FULLTEXT", "FUNCTION", "GLOBAL", "HASH",
    "HIERARCHICAL", "HOST", "ID", "IF EXISTS", "IF NOT EXISTS", "INHERIT",
    "INJECTIVE", "INVISIBLE", "IP", "LAYOUT", "LEADING", "LIFETIME",
    "LINEAR", "LIST", "LIVE", "LOCAL", "MATCH", "MAX",
    "MIN", "NAME", "NO DELAY", "OR REPLACE", "PERMANENTLY", "PERMISSIVE",
    "PIPELINE", "PROFILE", "QUOTA", "RANDOMIZED", "RANGE", "REALM",
    "RESTRICT", "RESTRICTIVE", "SERVER", "SIGNED", "SIMPLE", "SOURCE",
    "SPATIAL", "STORAGE", "STRICT", "SYNC", "TEMPORARY", "TEST",
    "TRAILING", "TYPE", "UNSIGNED", "UUID", "VARYING", "VIEW",
    "VISIBLE", "WRITABLE"
}

# =============================================================================
# Soft-reserved keywords (should not be used as bare identifiers)
# =============================================================================
SOFT_RESERVED_KEYWORDS = {
    "ALL", "ALTER", "AND", "ANY", "AS", "BETWEEN",
    "BY", "CASE", "COMMENT", "CONSTRAINT", "CREATE", "DATABASE",
    "DEFAULT", "DELETE", "DISTINCT", "DROP", "ELSE", "END",
    "ENGINE", "EXISTS", "FALSE", "FOREIGN KEY", "FROM", "FUNCTION",
    "GROUP BY", "HAVING", "IN", "INDEX", "INSERT INTO", "JOIN",
    "LIKE", "LIMIT", "NOT", "NULL", "OFFSET", "ON",
    "ORDER BY", "PRIMARY KEY", "SELECT", "SET", "TABLE", "THEN",
    "TO", "TRUE", "UNION", "UPDATE", "USING", "VALUES",
    "VIEW", "WHEN", "WHERE", "WITH"
}


# =============================================================================
# Category map for reporting
# =============================================================================
ALL_KEYWORD_CATEGORIES = {
    KeywordCategory.DML: DML_KEYWORDS,
    KeywordCategory.DDL: DDL_KEYWORDS,
    KeywordCategory.DCL: DCL_KEYWORDS,
    KeywordCategory.TCL: TCL_KEYWORDS,
    KeywordCategory.UTILITY: UTILITY_KEYWORDS,
    KeywordCategory.ACCESS: DCL_KEYWORDS,  # access-control subset of DCL
    KeywordCategory.SELECT_CLAUSE: SELECT_CLAUSE_KEYWORDS,
    KeywordCategory.JOIN: JOIN_KEYWORDS,
    KeywordCategory.OPERATOR: OPERATOR_KEYWORDS,
    KeywordCategory.DATA_TYPE: DATA_TYPE_KEYWORDS,
    KeywordCategory.TIME_UNIT: TIME_UNIT_KEYWORDS,
    KeywordCategory.DATE_TOKEN: DATE_TOKEN_KEYWORDS,
    KeywordCategory.DICTIONARY: DICTIONARY_KEYWORDS,
    KeywordCategory.PARTITION: PARTITION_KEYWORDS,
    KeywordCategory.ALTER_ACTION: ALTER_ACTION_KEYWORDS,
    KeywordCategory.SETTING: SETTING_KEYWORDS,
    KeywordCategory.SHOW: SHOW_KEYWORDS,
    KeywordCategory.MISC: MISC_KEYWORDS,
}


def is_keyword(text: str) -> bool:
    """Return True if text (case-insensitive) is a known ClickHouse keyword."""
    if not text:
        return False
    return text.upper() in _KEYWORDS_UPPER


def is_reserved_keyword(text: str) -> bool:
    """Return True if text is a soft-reserved keyword (should not be a bare identifier)."""
    if not text:
        return False
    return text.upper() in {k.upper() for k in SOFT_RESERVED_KEYWORDS}


def get_keyword_category(text: str):
    """Return the KeywordCategory for a keyword, or None if unknown."""
    if not text:
        return None
    up = text.upper()
    for cat, kw_set in ALL_KEYWORD_CATEGORIES.items():
        if up in {k.upper() for k in kw_set}:
            return cat
    return None


def get_all_keywords() -> list:
    """Return a sorted list of all keywords (original case)."""
    return sorted(ALL_KEYWORDS)


def get_keyword_count() -> int:
    """Return the total number of unique keywords."""
    return len(ALL_KEYWORDS)


if __name__ == "__main__":
    kws = get_all_keywords()
    print(f"Total ClickHouse 22.3 keywords: {len(kws)}")
    print(f"Soft-reserved keywords: {len(SOFT_RESERVED_KEYWORDS)}")
    print("\nKeywords by category:")
    for cat, kw_set in ALL_KEYWORD_CATEGORIES.items():
        print(f"  {cat.value}: {len(kw_set)}")
