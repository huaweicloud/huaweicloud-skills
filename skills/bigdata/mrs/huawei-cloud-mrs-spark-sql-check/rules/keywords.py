# -*- coding: utf-8 -*-
"""
Spark SQL Keywords Definition
Total keywords: defined across RESERVED, COL_NAME, TYPE_FUNC_NAME, and UNRESERVED categories.
Adapted for MRS Spark SQL specification checking (Spark 3.x).
"""

from enum import Enum


class KeywordCategory(Enum):
    """Spark SQL keyword categories"""
    RESERVED = "RESERVED_KEYWORD"
    COL_NAME = "COL_NAME_KEYWORD"
    TYPE_FUNC_NAME = "TYPE_FUNC_NAME_KEYWORD"
    UNRESERVED = "UNRESERVED_KEYWORD"


class Collabel(Enum):
    """Keyword label classification for grammar parsing"""
    AS_LABEL = "AS_LABEL"
    BARE_LABEL = "BARE_LABEL"


# (name_lower, token_name, category, collabel)
KEYWORD_ENTRIES = [
    # ============================================================
    # RESERVED keywords - cannot be used as identifiers (unless quoted)
    # ============================================================
    ("all", "ALL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("and", "AND", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("any", "ANY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("anti", "ANTI", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("array", "ARRAY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("as", "AS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("between", "BETWEEN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("bigint", "BIGINT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("binary", "BINARY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("boolean", "BOOLEAN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("both", "BOTH", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("by", "BY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("case", "CASE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cast", "CAST", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("collate", "COLLATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("column", "COLUMN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("create", "CREATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cross", "CROSS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current", "CURRENT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current_date", "CURRENT_DATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current_timestamp", "CURRENT_TIMESTAMP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current_user", "CURRENT_USER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("date", "DATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("decimal", "DECIMAL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("delete", "DELETE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("describe", "DESCRIBE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("distinct", "DISTINCT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("double", "DOUBLE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("drop", "DROP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("else", "ELSE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("end", "END", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("except", "EXCEPT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("exists", "EXISTS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("explain", "EXPLAIN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("false", "FALSE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("fetch", "FETCH", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("filter", "FILTER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("float", "FLOAT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("for", "FOR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("from", "FROM", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("full", "FULL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("function", "FUNCTION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("grant", "GRANT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("group", "GROUP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("grouping", "GROUPING", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("having", "HAVING", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("in", "IN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("inner", "INNER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("insert", "INSERT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("int", "INT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("integer", "INTEGER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("intersect", "INTERSECT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("interval", "INTERVAL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("into", "INTO", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("is", "IS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("join", "JOIN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("lateral", "LATERAL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("left", "LEFT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("like", "LIKE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("map", "MAP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("merge", "MERGE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("not", "NOT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("null", "NULL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("of", "OF", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("on", "ON", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("order", "ORDER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("outer", "OUTER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("over", "OVER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("partition", "PARTITION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("percent", "PERCENT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("range", "RANGE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("revoke", "REVOKE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("right", "RIGHT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("row", "ROW", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("rows", "ROWS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("select", "SELECT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("semi", "SEMI", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("set", "SET", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("smallint", "SMALLINT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("struct", "STRUCT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("table", "TABLE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("tablesample", "TABLESAMPLE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("then", "THEN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("timestamp", "TIMESTAMP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("timestamp_ntz", "TIMESTAMP_NTZ", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("timestamp_ltz", "TIMESTAMP_LTZ", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("tinyint", "TINYINT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("to", "TO", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("true", "TRUE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("truncate", "TRUNCATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("unbounded", "UNBOUNDED", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("union", "UNION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("update", "UPDATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("use", "USE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("using", "USING", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("values", "VALUES", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("varchar", "VARCHAR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("when", "WHEN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("where", "WHERE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("window", "WINDOW", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("with", "WITH", KeywordCategory.RESERVED, Collabel.AS_LABEL),

    # ============================================================
    # COL_NAME keywords - can be used as column names
    # ============================================================
    ("comment", "COMMENT", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("constraint", "CONSTRAINT", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("default", "DEFAULT", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("if", "IF", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("index", "INDEX", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("offset", "OFFSET", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("primary", "PRIMARY", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("show", "SHOW", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("temporary", "TEMPORARY", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("zone", "ZONE", KeywordCategory.COL_NAME, Collabel.AS_LABEL),

    # ============================================================
    # TYPE_FUNC_NAME keywords - type/function name keywords
    # ============================================================
    ("buckets", "BUCKETS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("cascade", "CASCADE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("change", "CHANGE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("cluster", "CLUSTER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("clustered", "CLUSTERED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("columns", "COLUMNS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("compute", "COMPUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("data", "DATA", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("databases", "DATABASES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("day", "DAY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("days", "DAYS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("dbproperties", "DBPROPERTIES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("defined", "DEFINED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("delimited", "DELIMITED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("desc", "DESC", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("directory", "DIRECTORY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("distribute", "DISTRIBUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("escaped", "ESCAPED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("exchange", "EXCHANGE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("file", "FILE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("fileformat", "FILEFORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("first", "FIRST", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("format", "FORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("formatted", "FORMATTED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("functions", "FUNCTIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("hour", "HOUR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("hours", "HOURS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("index", "INDEX", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("indexes", "INDEXES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("inpath", "INPATH", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("inputformat", "INPUTFORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("items", "ITEMS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("jar", "JAR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("keys", "KEYS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("limit", "LIMIT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("lines", "LINES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("load", "LOAD", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("location", "LOCATION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("lock", "LOCK", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("locks", "LOCKS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("minute", "MINUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("minutes", "MINUTES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("month", "MONTH", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("months", "MONTHS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("noscan", "NOSCAN", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("option", "OPTION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("options", "OPTIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("outputformat", "OUTPUTFORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("overwrite", "OVERWRITE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("partitioned", "PARTITIONED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("partitions", "PARTITIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("preceding", "PRECEDING", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("purge", "PURGE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("recordreader", "RECORDREADER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("recordwriter", "RECORDWRITER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("regexp", "REGEXP", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("rename", "RENAME", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("repair", "REPAIR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("replace", "REPLACE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("reset", "RESET", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("restrict", "RESTRICT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("rlike", "RLIKE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("role", "ROLE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("roles", "ROLES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("schema", "SCHEMA", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("schemas", "SCHEMAS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("second", "SECOND", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("seconds", "SECONDS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("serde", "SERDE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("serdeproperties", "SERDEPROPERTIES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("sets", "SETS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("short", "SHORT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("sort", "SORT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("sorted", "SORTED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("statistics", "STATISTICS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("stored", "STORED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("string", "STRING", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("tables", "TABLES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("terminated", "TERMINATED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("touch", "TOUCH", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("uri", "URI", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("view", "VIEW", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("views", "VIEWS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("year", "YEAR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("years", "YEARS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),

    # ============================================================
    # UNRESERVED keywords - non-reserved keywords
    # ============================================================
    ("add", "ADD", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("admin", "ADMIN", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("after", "AFTER", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("analyze", "ANALYZE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("archive", "ARCHIVE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("asc", "ASC", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("before", "BEFORE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("broadcast", "BROADCAST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("cache", "CACHE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("cached", "CACHED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("cancel", "CANCEL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("changed", "CHANGED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("clear", "CLEAR", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("codegen", "CODEGEN", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("compact", "COMPACT", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("compactions", "COMPACTIONS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("cost", "COST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("data", "DATA", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("database", "DATABASE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("debug", "DEBUG", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("deferred", "DEFERRED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("disable", "DISABLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("enable", "ENABLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("enforced", "ENFORCED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("fields", "FIELDS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("format", "FORMAT", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("global", "GLOBAL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("if", "IF", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("ignore", "IGNORE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("kill", "KILL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("last", "LAST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("lazy", "LAZY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("list", "LIST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("materialized", "MATERIALIZED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("metadata", "METADATA", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("msck", "MSCK", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("novalidate", "NOVALIDATE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("norely", "NORELY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("nulls", "NULLS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("only", "ONLY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("optimized", "OPTIMIZED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("parse", "PARSE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("partial", "PARTIAL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("path", "PATH", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("query", "QUERY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("raw", "RAW", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("rebuild", "REBUILD", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("refresh", "REFRESH", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("rely", "RELY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("repair", "REPAIR", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("replication", "REPLICATION", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("simple", "SIMPLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("streaming", "STREAMING", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("sync", "SYNC", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("transactional", "TRANSACTIONAL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("truncate", "TRUNCATE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("type", "TYPE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("types", "TYPES", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("uncache", "UNCACHE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("unarchive", "UNARCHIVE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("unlock", "UNLOCK", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("unset", "UNSET", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("user", "USER", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("while", "WHILE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
]

# Build lookup dictionaries and sets
RESERVED_KEYWORDS = set()
COL_NAME_KEYWORDS = set()
TYPE_FUNC_NAME_KEYWORDS = set()
UNRESERVED_KEYWORDS = set()
ALL_KEYWORDS = {}  # name_lower -> (token_name, category, collabel)

for _name, _token, _category, _collabel in KEYWORD_ENTRIES:
    # If a keyword appears in multiple categories, keep the first (most restrictive)
    if _name in ALL_KEYWORDS:
        continue
    ALL_KEYWORDS[_name] = (_token, _category, _collabel)
    if _category == KeywordCategory.RESERVED:
        RESERVED_KEYWORDS.add(_name)
    elif _category == KeywordCategory.COL_NAME:
        COL_NAME_KEYWORDS.add(_name)
    elif _category == KeywordCategory.TYPE_FUNC_NAME:
        TYPE_FUNC_NAME_KEYWORDS.add(_name)
    else:
        UNRESERVED_KEYWORDS.add(_name)


def is_keyword(word):
    """Check if the given word is a Spark SQL keyword (case-insensitive).

    Args:
        word: The word to check

    Returns:
        bool: True if the word is a keyword, False otherwise
    """
    return word.lower() in ALL_KEYWORDS


def get_keyword_info(word):
    """Get keyword info: returns (token_name, category, collabel) tuple or None.

    Args:
        word: The keyword to query

    Returns:
        tuple or None: keyword info tuple, or None if not a keyword
    """
    return ALL_KEYWORDS.get(word.lower())


def get_keyword_category(word):
    """Get keyword category.

    Args:
        word: The keyword to query

    Returns:
        KeywordCategory or None: keyword category enum value, or None if not a keyword
    """
    info = get_keyword_info(word)
    return info[1] if info else None


def is_reserved_keyword(word):
    """Check if the given word is a Spark SQL reserved keyword.

    Reserved keywords cannot be used as identifiers (unless quoted)

    Args:
        word: The word to check

    Returns:
        bool: True if the word is a reserved keyword, False otherwise
    """
    return word.lower() in RESERVED_KEYWORDS


def keyword_token_name(word):
    """Get the grammar token name for a keyword.

    Args:
        word: The keyword to query

    Returns:
        str or None: token name, or None if not a keyword
    """
    info = get_keyword_info(word)
    return info[0] if info else None
