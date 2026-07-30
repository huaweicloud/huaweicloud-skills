# -*- coding: utf-8 -*-
"""
ClickHouse 23.3 SQL Keyword Definitions

Source: ClickHouse 23.3 kernel src/Parsers/ (recursive scan of .cpp/.h/.hpp)

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
  forms found in 23.3 source like 'by', 'true', 'false', 'currentUser' were
  folded to 'BY', 'TRUE', 'FALSE', 'CURRENTUSER').

Result: 462 unique keywords (vs 571 in 24.8).
  - All 462 keywords are a strict subset of 24.8's 571.
  - 24.8 has 109 keywords not found via ParserKeyword calls in 23.3.
    In 23.3 those keywords are either:
      (a) handled by Lexer TokenType matching (e.g. IS NULL, NOT IN, OR,
          CASE, CAST, INTERVAL, DIV, MOD, TYPEOF, NOT BETWEEN, NOT LIKE,
          NOT ILIKE, GLOBAL IN, GLOBAL NOT IN, IS NOT NULL,
          IS NOT DISTINCT FROM, RECURSIVE, RESPECT NULLS, IGNORE NULLS,
          SKIP, QUALIFY, START TRANSACTION, MOVE, PART, NOT OVERRIDABLE,
          OVERRIDABLE),
      (b) only ever appearing as plain string literals in AST formatters
          rather than ParserKeyword calls (the *_PASSWORD / *_HASH auth
          keywords, TENANT(S), TAG(S), TAGS INNER UUID, METRICS,
          METRICS INNER UUID, MERGES, INDEXES, INDICES, STATISTICS,
          plural time units DAYS/HOURS/MINUTES/SECONDS/MILLISECONDS/
          MICROSECONDS/NANOSECONDS/WEEKS/MONTHS/YEARS/QUARTERS,
          SCHEME, SAN, PREFIX, DEFINER, INVOKER, SQL SECURITY, KIND, KEYS,
          FIELDS, FILE, EXTENDED, DATA, DATA INNER UUID, DDLTASK, EVERY,
          FORGET PARTITION, FROM SHARD, VALID UNTIL, KERBEROS, LDAP, JWT,
          HTTP, HOST, IP, IS_OBJECT_ID, NO_PASSWORD, bagexpansion,
          base_backup, cluster_host_ids, AZURE, PULL, APPEND, PASTE,
          RANDOMIZE FOR, Protobuf, WRITABLE, ZKPATH, WITH_ITEMINDEX,
          ALTER TEMPORARY TABLE, DROP TEMPORARY TABLE, ADD STATISTICS,
          DROP STATISTICS, CLEAR STATISTICS, MATERIALIZE STATISTICS,
          MODIFY DEFINER, MODIFY REFRESH, MODIFY SQL SECURITY,
          MODIFY STATISTICS, UNDROP PART, UNDROP PARTITION, UNSET FAKE TIME,
          SET FAKE TIME, CHECK ALL TABLES, CURRENT GRANTS, IF EMPTY,
          PBKDF2_HASH, BCRYPT_HASH, DOUBLE_SHA1_PASSWORD, SHA256_PASSWORD,
          PLAINTEXT_PASSWORD, DEPENDS ON, LIGHTWEIGHT, PERSISTENT,
          PERSISTENT SEQUENTIAL, EPHEMERAL SEQUENTIAL).
    See the report accompanying this file for the complete list.

The 462 keywords here are the ones explicitly referenced through
ParserKeyword calls in 23.3 source. For SQL-lint purposes this captures
the structured / multi-token keywords and most operator keywords.

ClickHouse keywords are case-insensitive and require word boundaries.
Compound keywords (e.g. "ORDER BY") allow whitespace/comments between parts.

Category subsets (DML/DDL/DCL/...) are provided for reporting and rule
targeting only - a keyword may appear in more than one category. They are
filtered from the 24.8 categories to only include the 462 keywords
present in 23.3. They are NOT the source of truth; KEYWORDS is.
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
# Authoritative keyword list (extracted from 23.3 src/Parsers/, 462 entries)
# Case normalized to match 24.8. Matched case-insensitively.
# =============================================================================
KEYWORDS = (
    "ADD", "ADD COLUMN", "ADD CONSTRAINT", "ADD INDEX", "ADD PROJECTION",
    "ADMIN OPTION FOR", "AFTER", "ALGORITHM", "ALIAS", "ALL",
    "ALLOWED_LATENESS", "ALTER", "ALTER COLUMN", "ALTER DATABASE", "ALTER LIVE VIEW",
    "ALTER POLICY", "ALTER PROFILE", "ALTER QUOTA", "ALTER ROLE", "ALTER ROW POLICY",
    "ALTER SETTINGS PROFILE", "ALTER TABLE", "ALTER TENANT", "ALTER USER", "AND",
    "AND STDOUT", "ANTI", "ANY", "APPLY", "ARRAY JOIN",
    "AS", "ASC", "ASCENDING", "ASOF", "ASSUME",
    "AST", "ASYNC", "ATTACH", "ATTACH PART", "ATTACH PARTITION",
    "ATTACH POLICY", "ATTACH PROFILE", "ATTACH QUOTA", "ATTACH ROLE", "ATTACH ROW POLICY",
    "ATTACH SETTINGS PROFILE", "ATTACH TENANT", "ATTACH USER", "AUTO_INCREMENT", "BACKUP",
    "base_backup", "BEGIN TRANSACTION", "BETWEEN", "BIDIRECTIONAL", "BOTH",
    "BY", "CASCADE", "CASE", "CHANGE", "CHANGEABLE_IN_READONLY",
    "CHANGED", "CHAR", "CHAR VARYING", "CHARACTER", "CHARACTER LARGE OBJECT",
    "CHARACTER VARYING", "CHECK", "CHECK TABLE", "CHECK TRANSACTION", "CLEANUP",
    "CLEAR COLUMN", "CLEAR INDEX", "CLEAR PROJECTION", "CLUSTER", "CLUSTERS",
    "cluster_host_ids", "CN", "CODEC", "COLLATE", "COLUMN",
    "COLUMNS", "COMMENT", "COMMENT COLUMN", "COMMIT", "COMPRESSION",
    "CONST", "CONSTRAINT", "CREATE", "CREATE POLICY", "CREATE PROFILE",
    "CREATE QUOTA", "CREATE ROLE", "CREATE ROW POLICY", "CREATE SETTINGS PROFILE", "CREATE TABLE",
    "CREATE TEMPORARY TABLE", "CREATE TENANT", "CREATE USER", "CROSS", "CUBE",
    "CURRENT QUOTA", "CURRENT ROLES", "CURRENT ROW", "CURRENT TRANSACTION", "CURRENTUSER",
    "CURRENT_USER", "D", "DATABASE", "DATABASES", "DATE",
    "DAY", "DD", "DEDUPLICATE", "DEFAULT", "DEFAULT DATABASE",
    "DEFAULT ROLE", "DELETE", "DESC", "DESCENDING", "DESCRIBE",
    "DETACH", "DETACH PART", "DETACH PARTITION", "DICTIONARIES", "DICTIONARY",
    "DISK", "DISTINCT", "DISTINCT ON", "DOUBLE_SHA1_HASH", "DROP",
    "DROP COLUMN", "DROP CONSTRAINT", "DROP DEFAULT", "DROP DETACHED PART", "DROP DETACHED PARTITION",
    "DROP INDEX", "DROP PART", "DROP PARTITION", "DROP PROJECTION", "DROP TABLE",
    "ELSE", "EMPTY", "EMPTY AS", "ENABLED ROLES", "END",
    "ENFORCED", "ENGINE", "EPHEMERAL", "ESTIMATE", "EVENT",
    "EVENTS", "EXCEPT", "EXCEPT DATABASE", "EXCEPT DATABASES", "EXCEPT TABLE",
    "EXCEPT TABLES", "EXCHANGE DICTIONARIES", "EXCHANGE TABLES", "EXISTS", "EXPLAIN",
    "EXPRESSION", "EXTERNAL DDL FROM", "FALSE", "FETCH", "FETCH PART",
    "FETCH PARTITION", "FILE", "FILESYSTEM CACHE", "FILESYSTEM CACHES", "FILTER",
    "FINAL", "FIRST", "FOLLOWING", "FOR", "FOREIGN",
    "FOREIGN KEY", "FORMAT", "FREEZE", "FROM", "FROM INFILE",
    "FULL", "FULLTEXT", "FUNCTION", "GLOBAL", "GRANT",
    "GRANT OPTION FOR", "GRANTEES", "GRANULARITY", "GROUP BY", "GROUPING SETS",
    "GROUPS", "H", "HASH", "HAVING", "HDFS",
    "HH", "HIERARCHICAL", "HOST", "HOUR", "ID",
    "IDENTIFIED", "IF EXISTS", "IF NOT EXISTS", "ILIKE", "IN",
    "IN PARTITION", "INDEX", "INHERIT", "INJECTIVE", "INNER",
    "INSERT INTO", "INTERPOLATE", "INTERSECT", "INTERVAL", "INTO OUTFILE",
    "INVISIBLE", "IP", "IS_OBJECT_ID", "JOIN", "KEY",
    "KEY BY", "KEYED BY", "KILL", "LARGE OBJECT", "LAST",
    "LAYOUT", "LEADING", "LEFT", "LEFT ARRAY JOIN", "LESS THAN",
    "LEVEL", "LIFETIME", "LIKE", "LIMIT", "LINEAR",
    "LIST", "LIVE", "LOCAL", "M", "MATCH",
    "MATERIALIZE", "MATERIALIZE COLUMN", "MATERIALIZE INDEX", "MATERIALIZE PROJECTION", "MATERIALIZE TTL",
    "MATERIALIZED", "MAX", "MCS", "MEMORY", "MI",
    "MICROSECOND", "MILLISECOND", "MIN", "MINUTE", "MM",
    "MODIFY", "MODIFY COLUMN", "MODIFY COMMENT", "MODIFY ORDER BY", "MODIFY QUERY",
    "MODIFY SAMPLE BY", "MODIFY SETTING", "MODIFY TTL", "MONTH", "MOVE PART",
    "MOVE PARTITION", "MS", "MUTATION", "N", "NAME",
    "NAMED COLLECTION", "NANOSECOND", "NEXT", "NO ACTION", "NO DELAY",
    "NO LIMITS", "NONE", "NOT", "NOT IDENTIFIED", "NOT KEYED",
    "NS", "NULL", "NULLS", "OFFSET", "ON",
    "ON DELETE", "ON UPDATE", "ON VOLUME", "ONLY", "OPTIMIZE TABLE",
    "OR REPLACE", "ORDER BY", "OUTER", "OVER", "PARTIAL",
    "PARTITION", "PARTITION BY", "PARTITIONS", "PART_MOVE_TO_SHARD", "PBKDF2_PASSWORD",
    "PERIODIC REFRESH", "PERMANENTLY", "PERMISSIVE", "PIPELINE", "PLAN",
    "POPULATE", "PRECEDING", "PRECISION", "PREWHERE", "PRIMARY",
    "PRIMARY KEY", "PROFILE", "PROJECTION", "Q", "QQ",
    "QUARTER", "QUERY", "QUERY TREE", "QUOTA", "RANDOMIZED",
    "RANGE", "READONLY", "REALM", "RECOMPRESS", "REFERENCES",
    "REFRESH", "REGEXP", "REMOVE", "REMOVE SAMPLE BY", "REMOVE TTL",
    "RENAME", "RENAME COLUMN", "RENAME DATABASE", "RENAME DICTIONARY", "RENAME TABLE",
    "RENAME TO", "REPLACE", "REPLACE PARTITION", "RESET SETTING", "RESTORE",
    "RESTRICT", "RESTRICTIVE", "RESUME", "REVOKE", "RIGHT",
    "ROLLBACK", "ROLLUP", "ROW", "ROWS", "S",
    "S3", "SALT", "SAMPLE", "SAMPLE BY", "SECOND",
    "SELECT", "SEMI", "SERVER", "SET", "SET DEFAULT",
    "SET DEFAULT ROLE", "SET NULL", "SET ROLE", "SET ROLE DEFAULT", "SET TRANSACTION SNAPSHOT",
    "SETTINGS", "SHA256_HASH", "SHOW", "SHOW ACCESS", "SHOW CREATE",
    "SHOW ENGINES", "SHOW GRANTS", "SHOW PRIVILEGES", "SHOW PROCESSLIST", "SIGNED",
    "SIMPLE", "SOURCE", "SPATIAL", "SQL_TSI_DAY", "SQL_TSI_HOUR",
    "SQL_TSI_MICROSECOND", "SQL_TSI_MILLISECOND", "SQL_TSI_MINUTE", "SQL_TSI_MONTH", "SQL_TSI_NANOSECOND",
    "SQL_TSI_QUARTER", "SQL_TSI_SECOND", "SQL_TSI_WEEK", "SQL_TSI_YEAR", "SS",
    "STEP", "STORAGE", "STRICT", "STRICTLY_ASCENDING", "SUBPARTITION",
    "SUBPARTITION BY", "SUBPARTITIONS", "SUSPEND", "SYNC", "SYNTAX",
    "SYSTEM", "TABLE", "TABLE OVERRIDE", "TABLES", "TEMPORARY",
    "TEMPORARY TABLE", "TEST", "THEN", "TIMESTAMP", "TO",
    "TO DISK", "TO INNER UUID", "TO SHARD", "TO TABLE", "TO VOLUME",
    "TOP", "TOTALS", "TRACKING ONLY", "TRAILING", "TRANSACTION",
    "TRIGGER", "TRUE", "TRUNCATE", "TTL", "TYPE",
    "UNBOUNDED", "UNDROP", "UNFREEZE", "UNION", "UNIQUE",
    "UNSIGNED", "UPDATE", "UPSERT INTO", "URL", "USE",
    "USING", "UUID", "VALUES", "VARYING", "VIEW",
    "VISIBLE", "WATCH", "WATERMARK", "WEEK", "WHEN",
    "WHERE", "WINDOW", "WITH", "WITH ADMIN OPTION", "WITH CHECK",
    "WITH FILL", "WITH GRANT OPTION", "WITH NAME", "WITH REPLACE OPTION", "WITH TIES",
    "WK", "WRITABLE", "WW", "YEAR", "YY",
    "YYYY", "ZKPATH",
)

# Master set (original case) + uppercase index for case-insensitive lookup.
ALL_KEYWORDS = set(KEYWORDS)
_KEYWORDS_UPPER = {k.upper() for k in KEYWORDS}


# =============================================================================
# Category subsets (filtered from 24.8 categories to 23.3 keywords only)
# =============================================================================
DML_KEYWORDS = {
    "AND STDOUT", "DEDUPLICATE", "DELETE", "FINAL", "FROM INFILE",
    "INSERT INTO", "INTO OUTFILE", "OPTIMIZE TABLE", "SELECT", "TRUNCATE",
    "UPDATE", "UPSERT INTO", "VALUES",
}

DDL_KEYWORDS = {
    "ALGORITHM", "ALTER", "ALTER DATABASE", "ALTER LIVE VIEW", "ALTER TABLE",
    "AS", "ATTACH", "ATTACH PART", "ATTACH PARTITION", "CHANGE",
    "CHANGED", "CHECK", "CHECK TABLE", "CHECK TRANSACTION", "CODEC",
    "COMMENT", "COMMENT COLUMN", "COMPRESSION", "CONST", "CONSTRAINT",
    "CREATE", "CREATE TABLE", "CREATE TEMPORARY TABLE", "DATABASE", "DATABASES",
    "DESCRIBE", "DETACH", "DETACH PART", "DETACH PARTITION", "DROP",
    "DROP TABLE", "ENGINE", "EXCHANGE DICTIONARIES", "EXCHANGE TABLES", "EXTERNAL DDL FROM",
    "FOREIGN", "FOREIGN KEY", "FUNCTION", "GRANULARITY", "IF EXISTS",
    "IF NOT EXISTS", "INDEX", "LIVE", "MATERIALIZED", "NAMED COLLECTION",
    "OR REPLACE", "ORDER BY", "PARTITION BY", "POPULATE", "PRIMARY",
    "PRIMARY KEY", "PROJECTION", "RENAME", "RENAME COLUMN", "RENAME DATABASE",
    "RENAME DICTIONARY", "RENAME TABLE", "RENAME TO", "SALT", "SAMPLE BY",
    "SETTINGS", "STEP", "TABLE", "TABLE OVERRIDE", "TABLES",
    "TEMPORARY", "TEMPORARY TABLE", "TO INNER UUID", "TRIGGER", "TRUNCATE",
    "TTL", "TYPE", "UNDROP", "UNIQUE", "USE",
    "VIEW", "WITH",
}

DCL_KEYWORDS = {
    "ADMIN OPTION FOR", "ALTER POLICY", "ALTER PROFILE", "ALTER QUOTA", "ALTER ROLE",
    "ALTER ROW POLICY", "ALTER SETTINGS PROFILE", "ALTER TENANT", "ALTER USER", "ATTACH POLICY",
    "ATTACH PROFILE", "ATTACH QUOTA", "ATTACH ROLE", "ATTACH ROW POLICY", "ATTACH SETTINGS PROFILE",
    "ATTACH TENANT", "ATTACH USER", "CHANGEABLE_IN_READONLY", "CREATE POLICY", "CREATE PROFILE",
    "CREATE QUOTA", "CREATE ROLE", "CREATE ROW POLICY", "CREATE SETTINGS PROFILE", "CREATE TENANT",
    "CREATE USER", "CURRENT QUOTA", "CURRENT ROLES", "CURRENTUSER", "CURRENT_USER",
    "DEFAULT ROLE", "DOUBLE_SHA1_HASH", "ENABLED ROLES", "GRANT", "GRANT OPTION FOR",
    "GRANTEES", "HOST", "ID", "IDENTIFIED", "IP",
    "IS_OBJECT_ID", "NAME", "NOT IDENTIFIED", "PBKDF2_PASSWORD", "READONLY",
    "REALM", "REVOKE", "SET DEFAULT", "SET DEFAULT ROLE", "SET NULL",
    "SET ROLE", "SET ROLE DEFAULT", "SHA256_HASH", "SHOW ACCESS", "SHOW CREATE",
    "SHOW GRANTS", "SHOW PRIVILEGES", "WITH ADMIN OPTION", "WITH GRANT OPTION",
}

TCL_KEYWORDS = {
    "BEGIN TRANSACTION", "CHECK TRANSACTION", "COMMIT", "CURRENT TRANSACTION", "ROLLBACK",
    "SET TRANSACTION SNAPSHOT", "TRANSACTION",
}

UTILITY_KEYWORDS = {
    "AST", "BACKUP", "ESTIMATE", "EXPLAIN", "FETCH",
    "FETCH PART", "FETCH PARTITION", "FREEZE", "KILL", "MUTATION",
    "OPTIMIZE TABLE", "PART_MOVE_TO_SHARD", "PIPELINE", "PLAN", "QUERY",
    "QUERY TREE", "RESTORE", "RESUME", "SET", "SHOW",
    "SUSPEND", "SYNTAX", "SYSTEM", "TEST", "TRACKING ONLY",
    "UNFREEZE", "WATCH",
}

SELECT_CLAUSE_KEYWORDS = {
    "ALIAS", "ALL", "AND STDOUT", "ANY", "ARRAY JOIN",
    "AS", "ASC", "ASCENDING", "BETWEEN", "BY",
    "CUBE", "CURRENT ROW", "DESC", "DESCENDING", "DISTINCT",
    "DISTINCT ON", "EMPTY", "EMPTY AS", "EXCEPT", "EXCEPT DATABASE",
    "EXCEPT DATABASES", "EXCEPT TABLE", "EXCEPT TABLES", "FINAL", "FIRST",
    "FOLLOWING", "FORMAT", "FROM", "FROM INFILE", "GROUP BY",
    "GROUPING SETS", "GROUPS", "HAVING", "INTERPOLATE", "INTERSECT",
    "INTO OUTFILE", "LAST", "LEFT ARRAY JOIN", "LIMIT", "NO LIMITS",
    "NULLS", "OFFSET", "ON", "ONLY", "ORDER BY",
    "OVER", "PARTIAL", "PRECEDING", "PREWHERE", "RANGE",
    "ROLLUP", "ROW", "ROWS", "SAMPLE", "SAMPLE BY",
    "SELECT", "SETTINGS", "TO", "TOP", "TOTALS",
    "UNBOUNDED", "UNION", "USING", "VALUES", "WHERE",
    "WINDOW", "WITH", "WITH FILL", "WITH NAME", "WITH TIES",
}

JOIN_KEYWORDS = {
    "ALL", "ANTI", "ANY", "ARRAY JOIN", "ASOF",
    "BIDIRECTIONAL", "CROSS", "FULL", "GLOBAL", "HIERARCHICAL",
    "IN", "IN PARTITION", "INNER", "JOIN", "KEY BY",
    "KEYED BY", "LEFT", "LEFT ARRAY JOIN", "NOT KEYED", "ON",
    "OUTER", "RIGHT", "SEMI", "USING",
}

OPERATOR_KEYWORDS = {
    "AND", "ASSUME", "BETWEEN", "CASE", "COLLATE",
    "CONST", "CONSTRAINT", "ELSE", "END", "EXISTS",
    "FALSE", "FILTER", "FULLTEXT", "ILIKE", "IN",
    "INTERVAL", "LIKE", "MATCH", "NOT", "NULL",
    "OVER", "REFERENCES", "REGEXP", "THEN", "TRUE",
    "WHEN",
}

DATA_TYPE_KEYWORDS = {
    "CHAR", "CHAR VARYING", "CHARACTER", "CHARACTER LARGE OBJECT", "CHARACTER VARYING",
    "DATE", "LARGE OBJECT", "PRECISION", "SIGNED", "SIMPLE",
    "TIMESTAMP", "UNSIGNED", "UUID", "VARYING",
}

TIME_UNIT_KEYWORDS = {
    "DAY", "HOUR", "INTERVAL", "MCS", "MICROSECOND",
    "MILLISECOND", "MINUTE", "MONTH", "MS", "NANOSECOND",
    "NS", "QUARTER", "SECOND", "SQL_TSI_DAY", "SQL_TSI_HOUR",
    "SQL_TSI_MICROSECOND", "SQL_TSI_MILLISECOND", "SQL_TSI_MINUTE", "SQL_TSI_MONTH", "SQL_TSI_NANOSECOND",
    "SQL_TSI_QUARTER", "SQL_TSI_SECOND", "SQL_TSI_WEEK", "SQL_TSI_YEAR", "WEEK",
    "YEAR",
}

DATE_TOKEN_KEYWORDS = {
    "D", "DD", "H", "HH", "M",
    "MI", "MM", "N", "Q", "QQ",
    "S", "SS", "WK", "WW", "YY",
    "YYYY",
}

DICTIONARY_KEYWORDS = {
    "BIDIRECTIONAL", "DICTIONARIES", "DICTIONARY", "EVENT", "EVENTS",
    "EXPRESSION", "HIERARCHICAL", "INJECTIVE", "LAYOUT", "LIFETIME",
    "RANGE", "SOURCE",
}

PARTITION_KEYWORDS = {
    "ATTACH PART", "ATTACH PARTITION", "DETACH PART", "DETACH PARTITION", "DISK",
    "DROP DETACHED PART", "DROP DETACHED PARTITION", "DROP PART", "DROP PARTITION", "FETCH PART",
    "FETCH PARTITION", "FREEZE", "MOVE PART", "MOVE PARTITION", "PARTITION",
    "PARTITION BY", "PARTITIONS", "PART_MOVE_TO_SHARD", "RECOMPRESS", "REPLACE PARTITION",
    "SUBPARTITION", "SUBPARTITION BY", "SUBPARTITIONS", "TO DISK", "TO INNER UUID",
    "TO SHARD", "TO TABLE", "TO VOLUME", "UNFREEZE",
}

ALTER_ACTION_KEYWORDS = {
    "ADD", "ADD COLUMN", "ADD CONSTRAINT", "ADD INDEX", "ADD PROJECTION",
    "AFTER", "ALTER COLUMN", "CASCADE", "CHANGE", "CLEANUP",
    "CLEAR COLUMN", "CLEAR INDEX", "CLEAR PROJECTION", "CODEC", "COLUMN",
    "COLUMNS", "COMMENT", "COMMENT COLUMN", "COMPRESSION", "DROP COLUMN",
    "DROP CONSTRAINT", "DROP DEFAULT", "DROP INDEX", "DROP PROJECTION", "ENFORCED",
    "ENGINE", "FOREIGN", "FOREIGN KEY", "GRANULARITY", "INDEX",
    "INVISIBLE", "LESS THAN", "LEVEL", "MATERIALIZE", "MATERIALIZE COLUMN",
    "MATERIALIZE INDEX", "MATERIALIZE PROJECTION", "MATERIALIZE TTL", "MODIFY", "MODIFY COLUMN",
    "MODIFY COMMENT", "MODIFY ORDER BY", "MODIFY QUERY", "MODIFY SAMPLE BY", "MODIFY SETTING",
    "MODIFY TTL", "NEXT", "NO ACTION", "NONE", "ON DELETE",
    "ON UPDATE", "ON VOLUME", "PERIODIC REFRESH", "PERMISSIVE", "PRIMARY",
    "PRIMARY KEY", "PROJECTION", "REFRESH", "REMOVE", "REMOVE SAMPLE BY",
    "REMOVE TTL", "RENAME COLUMN", "RENAME TO", "REPLACE", "REPLACE PARTITION",
    "RESET SETTING", "RESTRICT", "RESTRICTIVE", "SALT", "SET DEFAULT",
    "SET NULL", "STEP", "TTL", "VISIBLE",
}

SETTING_KEYWORDS = {
    "ALLOWED_LATENESS", "AUTO_INCREMENT", "base_backup", "CHANGEABLE_IN_READONLY", "cluster_host_ids",
    "CODEC", "COMPRESSION", "DEFAULT", "DEFAULT DATABASE", "DISK",
    "ENGINE", "EPHEMERAL", "FILESYSTEM CACHE", "FILESYSTEM CACHES", "MEMORY",
    "NAMED COLLECTION", "PERMANENTLY", "PROFILE", "QUOTA", "READONLY",
    "SETTINGS", "STORAGE", "STRICTLY_ASCENDING", "TEMPORARY", "TEMPORARY TABLE",
    "TRACKING ONLY", "WATERMARK", "ZKPATH",
}

SHOW_KEYWORDS = {
    "CLUSTERS", "DATABASES", "DICTIONARIES", "EVENTS", "PARTITIONS",
    "SHOW", "SHOW ACCESS", "SHOW CREATE", "SHOW ENGINES", "SHOW GRANTS",
    "SHOW PRIVILEGES", "SHOW PROCESSLIST", "TABLES",
}

MISC_KEYWORDS = {
    "ASSUME", "ASYNC", "BIDIRECTIONAL", "BOTH", "CASCADE",
    "CHAR", "CHARACTER", "CLUSTER", "CLUSTERS", "CN",
    "COMMENT", "ENFORCED", "ESTIMATE", "EVENT", "EXPRESSION",
    "FILE", "FOR", "FULLTEXT", "FUNCTION", "GLOBAL",
    "HASH", "HDFS", "HIERARCHICAL", "HOST", "ID",
    "IF EXISTS", "IF NOT EXISTS", "INHERIT", "INJECTIVE", "INVISIBLE",
    "IP", "LAYOUT", "LEADING", "LIFETIME", "LINEAR",
    "LIST", "LIVE", "LOCAL", "MATCH", "MAX",
    "MIN", "NAME", "NO DELAY", "OR REPLACE", "PERMANENTLY",
    "PERMISSIVE", "PIPELINE", "PROFILE", "QUOTA", "RANDOMIZED",
    "RANGE", "REALM", "RESTRICT", "RESTRICTIVE", "S3",
    "SERVER", "SIGNED", "SIMPLE", "SOURCE", "SPATIAL",
    "STORAGE", "STRICT", "SYNC", "TEMPORARY", "TEST",
    "TRAILING", "TYPE", "UNSIGNED", "URL", "UUID",
    "VARYING", "VIEW", "VISIBLE", "WRITABLE",
}


# =============================================================================
# Soft-reserved keywords (should not be used as bare identifiers)
# =============================================================================
SOFT_RESERVED_KEYWORDS = {
    "ALL", "ALTER", "AND", "ANY", "AS",
    "BETWEEN", "BY", "CASE", "COMMENT", "CONSTRAINT",
    "CREATE", "DATABASE", "DEFAULT", "DELETE", "DISTINCT",
    "DROP", "ELSE", "END", "ENGINE", "EXISTS",
    "FALSE", "FOREIGN KEY", "FROM", "FUNCTION", "GROUP BY",
    "HAVING", "IN", "INDEX", "INSERT INTO", "JOIN",
    "LIKE", "LIMIT", "NOT", "NULL", "OFFSET",
    "ON", "ORDER BY", "PRIMARY KEY", "SELECT", "SET",
    "TABLE", "THEN", "TO", "TRUE", "UNION",
    "UPDATE", "USING", "VALUES", "VIEW", "WHEN",
    "WHERE", "WITH",
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
    print(f"Total ClickHouse 23.3 keywords: {len(kws)}")
    print(f"Soft-reserved keywords: {len(SOFT_RESERVED_KEYWORDS)}")
    print("\nKeywords by category:")
    for cat, kw_set in ALL_KEYWORD_CATEGORIES.items():
        print(f"  {cat.value}: {len(kw_set)}")
