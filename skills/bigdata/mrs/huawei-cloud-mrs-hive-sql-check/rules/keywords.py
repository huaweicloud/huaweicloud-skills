# -*- coding: utf-8 -*-
"""
Hive SQL Keywords Definition
Total keywords: defined across RESERVED, COL_NAME, TYPE_FUNC_NAME, and UNRESERVED categories.
Adapted for MRS Hive SQL specification checking.
"""

from enum import Enum


class KeywordCategory(Enum):
    """Hive SQL keyword categories"""
    RESERVED = "RESERVED_KEYWORD"
    COL_NAME = "COL_NAME_KEYWORD"
    TYPE_FUNC_NAME = "TYPE_FUNC_NAME_KEYWORD"
    UNRESERVED = "UNRESERVED_KEYWORD"


class Collabel(Enum):
    """Keyword label classification for grammar parsing"""
    AS_LABEL = "AS_LABEL"
    BARE_LABEL = "BARE_LABEL"


# (name_lower, token_name, category, collabel)
# 组织方式：按类别分组，每组内按字母排序
KEYWORD_ENTRIES = [
    # ============================================================
    # RESERVED keywords - 不能用作标识符（除非加引号）
    # ============================================================
    ("all", "ALL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("alter", "ALTER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("and", "AND", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("any", "ANY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("array", "ARRAY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("as", "AS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("authorization", "AUTHORIZATION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("autocommit", "AUTOCOMMIT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("between", "BETWEEN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("bigint", "BIGINT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("binary", "BINARY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("boolean", "BOOLEAN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("both", "BOTH", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("by", "BY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cache", "CACHE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("char", "CHAR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("concatenate", "CONCATENATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current", "CURRENT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("dec", "DEC", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("do", "DO", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("dump", "DUMP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("exclusive", "EXCLUSIVE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("expression", "EXPRESSION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("floor", "FLOOR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("freeze", "FREEZE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("frozen", "FROZEN", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("isolation", "ISOLATION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("key", "KEY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("less", "LESS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("matched", "MATCHED", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("more", "MORE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("novalidate", "NOVALIDATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("norely", "NORELY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("numeric", "NUMERIC", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("or", "OR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("plan", "PLAN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("plans", "PLANS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("precision", "PRECISION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("preserve", "PRESERVE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("query", "QUERY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("reads", "READS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("references", "REFERENCES", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("rely", "RELY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("repl", "REPL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("show_database", "SHOW_DATABASE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("snapshot", "SNAPSHOT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("ssl", "SSL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("summary", "SUMMARY", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("time", "TIME", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("timestamplocaltz", "TIMESTAMPLOCALTZ", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("transaction", "TRANSACTION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("unfreeze", "UNFREEZE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("uniquejoin", "UNIQUEJOIN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("work", "WORK", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("write", "WRITE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("case", "CASE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cast", "CAST", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("collate", "COLLATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("column", "COLUMN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("commit", "COMMIT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("create", "CREATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cross", "CROSS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cube", "CUBE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current_date", "CURRENT_DATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current_timestamp", "CURRENT_TIMESTAMP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("current_user", "CURRENT_USER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("cursor", "CURSOR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("database", "DATABASE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
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
    ("export", "EXPORT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("extended", "EXTENDED", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("external", "EXTERNAL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("extract", "EXTRACT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("false", "FALSE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("fetch", "FETCH", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("float", "FLOAT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("for", "FOR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("foreign", "FOREIGN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("from", "FROM", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("full", "FULL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("function", "FUNCTION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("grant", "GRANT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("group", "GROUP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("grouping", "GROUPING", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("having", "HAVING", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("if", "IF", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("import", "IMPORT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
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
    ("local", "LOCAL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("macro", "MACRO", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("map", "MAP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("merge", "MERGE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("none", "NONE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("not", "NOT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("null", "NULL", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("of", "OF", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("on", "ON", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("order", "ORDER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("out", "OUT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("outer", "OUTER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("over", "OVER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("partition", "PARTITION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("percent", "PERCENT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("procedure", "PROCEDURE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("range", "RANGE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("reduce", "REDUCE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("revoke", "REVOKE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("right", "RIGHT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("rollback", "ROLLBACK", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("rollup", "ROLLUP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("row", "ROW", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("rows", "ROWS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("select", "SELECT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("set", "SET", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("smallint", "SMALLINT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("some", "SOME", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("sort", "SORT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("start", "START", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("stored", "STORED", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("struct", "STRUCT", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("table", "TABLE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("tablesample", "TABLESAMPLE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("textfile", "TEXTFILE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("then", "THEN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("timestamp", "TIMESTAMP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("to", "TO", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("transform", "TRANSFORM", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("trigger", "TRIGGER", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("true", "TRUE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("truncate", "TRUNCATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("unbounded", "UNBOUNDED", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("union", "UNION", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("unique", "UNIQUE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("update", "UPDATE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("use", "USE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("using", "USING", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("utc_timestamp", "UTC_TIMESTAMP", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("values", "VALUES", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("varchar", "VARCHAR", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("views", "VIEWS", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("when", "WHEN", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("where", "WHERE", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("window", "WINDOW", KeywordCategory.RESERVED, Collabel.AS_LABEL),
    ("with", "WITH", KeywordCategory.RESERVED, Collabel.AS_LABEL),

    # ============================================================
    # COL_NAME keywords - 可以用作列名
    # ============================================================
    ("comment", "COMMENT", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("constraint", "CONSTRAINT", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("default", "DEFAULT", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("div", "DIV", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("index", "INDEX", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("offset", "OFFSET", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("preceding", "PRECEDING", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("primary", "PRIMARY", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("show", "SHOW", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("tblproperties", "TBLPROPERTIES", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("temporary", "TEMPORARY", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("unsigned", "UNSIGNED", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("unsigned_integer", "UNSIGNED_INTEGER", KeywordCategory.COL_NAME, Collabel.AS_LABEL),
    ("zone", "ZONE", KeywordCategory.COL_NAME, Collabel.AS_LABEL),

    # ============================================================
    # TYPE_FUNC_NAME keywords - 类型/函数名关键字
    # ============================================================
    ("bucket", "BUCKET", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("buckets", "BUCKETS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("cascade", "CASCADE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("change", "CHANGE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("cluster", "CLUSTER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("clustered", "CLUSTERED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("clusterstatus", "CLUSTERSTATUS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("collection", "COLLECTION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("columns", "COLUMNS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("compact", "COMPACT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("compactions", "COMPACTIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("compute", "COMPUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("data", "DATA", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("databases", "DATABASES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("datetime", "DATETIME", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("day", "DAY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("days", "DAYS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("dbproperties", "DBPROPERTIES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("defined", "DEFINED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("delimited", "DELIMITED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("dependency", "DEPENDENCY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("desc", "DESC", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("directories", "DIRECTORIES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("directory", "DIRECTORY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("distribute", "DISTRIBUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("escaped", "ESCAPED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("exchange", "EXCHANGE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("exclude", "EXCLUDE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("execute", "EXECUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("file", "FILE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("fileformat", "FILEFORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("first", "FIRST", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("following", "FOLLOWING", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("format", "FORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("formatted", "FORMATTED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("functions", "FUNCTIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("hold_ddltime", "HOLD_DDLTIME", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("hour", "HOUR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("hours", "HOURS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("idxproperties", "IDXPROPERTIES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("ignore", "IGNORE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("indexes", "INDEXES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("inpath", "INPATH", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("inputdriver", "INPUTDRIVER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("inputformat", "INPUTFORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("items", "ITEMS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("jar", "JAR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("keys", "KEYS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("key_type", "KEY_TYPE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("limit", "LIMIT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("lines", "LINES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("load", "LOAD", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("location", "LOCATION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("lock", "LOCK", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("locks", "LOCKS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("logical", "LOGICAL", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("long", "LONG", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("mapjoin", "MAPJOIN", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("materialized", "MATERIALIZED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("metadata", "METADATA", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("minus", "MINUS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("minute", "MINUTE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("minutes", "MINUTES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("month", "MONTH", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("months", "MONTHS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("msck", "MSCK", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("noscan", "NOSCAN", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("no_drop", "NO_DROP", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("offline", "OFFLINE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("operator", "OPERATOR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("option", "OPTION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("outputdriver", "OUTPUTDRIVER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("outputformat", "OUTPUTFORMAT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("overwrite", "OVERWRITE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("owner", "OWNER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("partitioned", "PARTITIONED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("partitions", "PARTITIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("plus", "PLUS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("pretty", "PRETTY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("principals", "PRINCIPALS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("protection", "PROTECTION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("purge", "PURGE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("read", "READ", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("readonly", "READONLY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("rebuild", "REBUILD", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("recordreader", "RECORDREADER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("recordwriter", "RECORDWRITER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("regexp", "REGEXP", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("reload", "RELOAD", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("rename", "RENAME", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("repair", "REPAIR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("replace", "REPLACE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("replication", "REPLICATION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("restrict", "RESTRICT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("rewrite", "REWRITE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("rlike", "RLIKE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("role", "ROLE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("roles", "ROLES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("schema", "SCHEMA", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("schemas", "SCHEMAS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("semi", "SEMI", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("serde", "SERDE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("serdeproperties", "SERDEPROPERTIES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("server", "SERVER", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("sets", "SETS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("shared", "SHARED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("skewed", "SKEWED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("sortby", "SORTBY", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("sorted", "SORTED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("statistics", "STATISTICS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("status", "STATUS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("streamtable", "STREAMTABLE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("string", "STRING", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("tables", "TABLES", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("terminated", "TERMINATED", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("tinyint", "TINYINT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("touch", "TOUCH", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("transactions", "TRANSACTIONS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("unarchive", "UNARCHIVE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("undo", "UNDO", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("uniontype", "UNIONTYPE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("unlock", "UNLOCK", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("unset", "UNSET", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("uri", "URI", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("url", "URL", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("utc", "UTC", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("utctimestamp", "UTCTIMESTAMP", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("value", "VALUE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("vectorization", "VECTORIZATION", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("view", "VIEW", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("while", "WHILE", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("year", "YEAR", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("years", "YEARS", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),
    ("wait", "WAIT", KeywordCategory.TYPE_FUNC_NAME, Collabel.AS_LABEL),

    # ============================================================
    # UNRESERVED keywords - 非保留关键字
    # ============================================================
    ("abort", "ABORT", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("activate", "ACTIVATE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("add", "ADD", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("admin", "ADMIN", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("after", "AFTER", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("alloc_fraction", "ALLOC_FRACTION", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("application", "APPLICATION", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("active", "ACTIVE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("analyze", "ANALYZE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("archive", "ARCHIVE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("asc", "ASC", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("before", "BEFORE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("management", "MANAGEMENT", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("mapping", "MAPPING", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("move", "MOVE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("burst", "BURST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("cached", "CACHED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("cancel", "CANCEL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("capacity", "CAPACITY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("changed", "CHANGED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("check", "CHECK", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("codegen", "CODEGEN", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("compress", "COMPRESS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("conf", "CONF", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("continue", "CONTINUE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("debug", "DEBUG", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("deferred", "DEFERRED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("detail", "DETAIL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("disable", "DISABLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("dow", "DOW", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("dayofweek", "DAYOFWEEK", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("dumped", "DUMPED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("enable", "ENABLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("enforced", "ENFORCED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("fields", "FIELDS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("kill", "KILL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("last", "LAST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("level", "LEVEL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("lifecycle", "LIFECYCLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("list", "LIST", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("nulls", "NULLS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("only", "ONLY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("optimized", "OPTIMIZED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("ordinality", "ORDINALITY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("parse", "PARSE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("partial", "PARTIAL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("path", "PATH", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("pipe", "PIPE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("pool", "POOL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("quarter", "QUARTER", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("qualify", "QUALIFY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("query_parallelism", "QUERY_PARALLELISM", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("reoptimization", "REOPTIMIZATION", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("refresh", "REFRESH", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("repeatable", "REPEATABLE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("resource", "RESOURCE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("respect", "RESPECT", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("scheduling_policy", "SCHEDULING_POLICY", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("second", "SECOND", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("seconds", "SECONDS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("spec", "SPEC", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("sync", "SYNC", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("system_time", "SYSTEM_TIME", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("system_version", "SYSTEM_VERSION", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("transactional", "TRANSACTIONAL", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("type", "TYPE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("types", "TYPES", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("unmanaged", "UNMANAGED", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("validate", "VALIDATE", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("version", "VERSION", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("week", "WEEK", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("weeks", "WEEKS", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("workload", "WORKLOAD", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
    ("user", "USER", KeywordCategory.UNRESERVED, Collabel.AS_LABEL),
]

# 构建查找字典和集合
RESERVED_KEYWORDS = set()
COL_NAME_KEYWORDS = set()
TYPE_FUNC_NAME_KEYWORDS = set()
UNRESERVED_KEYWORDS = set()
ALL_KEYWORDS = {}  # name_lower -> (token_name, category, collabel)

for _name, _token, _category, _collabel in KEYWORD_ENTRIES:
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
    """检查给定的词是否为Hive SQL关键字（不区分大小写）

    Args:
        word: 待检查的词

    Returns:
        bool: 如果是关键字返回True，否则返回False
    """
    return word.lower() in ALL_KEYWORDS


def get_keyword_info(word):
    """获取关键字信息：返回(token_name, category, collabel)元组或None

    Args:
        word: 待查询的关键字

    Returns:
        tuple or None: 关键字信息元组，如果不是关键字则返回None
    """
    return ALL_KEYWORDS.get(word.lower())


def get_keyword_category(word):
    """获取关键字类别

    Args:
        word: 待查询的关键字

    Returns:
        KeywordCategory or None: 关键字类别枚举值，如果不是关键字则返回None
    """
    info = get_keyword_info(word)
    return info[1] if info else None


def is_reserved_keyword(word):
    """检查给定的词是否为Hive SQL保留关键字

    保留关键字不能用作标识符（除非加引号）

    Args:
        word: 待检查的词

    Returns:
        bool: 如果是保留关键字返回True，否则返回False
    """
    return word.lower() in RESERVED_KEYWORDS


def keyword_token_name(word):
    """获取关键字对应的语法token名称

    Args:
        word: 待查询的关键字

    Returns:
        str or None: token名称，如果不是关键字则返回None
    """
    info = get_keyword_info(word)
    return info[0] if info else None
