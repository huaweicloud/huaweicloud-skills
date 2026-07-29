# -*- coding: utf-8 -*-
"""
HetuEngine SQL Keywords Definition

This module defines SQL keywords for HetuEngine (based on Presto/Trino + Hive compatibility).
Keywords are categorized into four types:
- RESERVED: Reserved keywords that cannot be used as identifiers
- COL_NAME: Keywords that can be used as column names
- TYPE_FUNC_NAME: Keywords that are type or function names
- UNRESERVED: Unreserved keywords that can be used as identifiers in most contexts
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, NamedTuple


class KeywordCategory(Enum):
    """SQL keyword categories"""
    RESERVED = auto()
    COL_NAME = auto()
    TYPE_FUNC_NAME = auto()
    UNRESERVED = auto()


class Collabel(NamedTuple):
    """Keyword entry with category information"""
    keyword: str
    category: KeywordCategory
    description: Optional[str] = None


# ============================================================================
# KEYWORD ENTRIES
# ============================================================================

KEYWORD_ENTRIES: List[Collabel] = [
    # ========================================================================
    # RESERVED KEYWORDS - Standard SQL reserved keywords
    # ========================================================================
    Collabel("SELECT", KeywordCategory.RESERVED, "Query selection"),
    Collabel("FROM", KeywordCategory.RESERVED, "Table source"),
    Collabel("WHERE", KeywordCategory.RESERVED, "Filter condition"),
    Collabel("GROUP", KeywordCategory.RESERVED, "Grouping clause"),
    Collabel("HAVING", KeywordCategory.RESERVED, "Group filter"),
    Collabel("ORDER", KeywordCategory.RESERVED, "Ordering clause"),
    Collabel("LIMIT", KeywordCategory.RESERVED, "Row limit"),
    Collabel("OFFSET", KeywordCategory.RESERVED, "Row offset"),
    Collabel("JOIN", KeywordCategory.RESERVED, "Join operation"),
    Collabel("INNER", KeywordCategory.RESERVED, "Inner join"),
    Collabel("LEFT", KeywordCategory.RESERVED, "Left outer join"),
    Collabel("RIGHT", KeywordCategory.RESERVED, "Right outer join"),
    Collabel("FULL", KeywordCategory.RESERVED, "Full outer join"),
    Collabel("CROSS", KeywordCategory.RESERVED, "Cross join"),
    Collabel("ON", KeywordCategory.RESERVED, "Join condition"),
    Collabel("AS", KeywordCategory.RESERVED, "Alias"),
    Collabel("AND", KeywordCategory.RESERVED, "Logical AND"),
    Collabel("OR", KeywordCategory.RESERVED, "Logical OR"),
    Collabel("NOT", KeywordCategory.RESERVED, "Logical NOT"),
    Collabel("IN", KeywordCategory.RESERVED, "In list"),
    Collabel("EXISTS", KeywordCategory.RESERVED, "Exists predicate"),
    Collabel("BETWEEN", KeywordCategory.RESERVED, "Between predicate"),
    Collabel("LIKE", KeywordCategory.RESERVED, "Pattern match"),
    Collabel("IS", KeywordCategory.RESERVED, "Is predicate"),
    Collabel("NULL", KeywordCategory.RESERVED, "Null value"),
    Collabel("TRUE", KeywordCategory.RESERVED, "Boolean true"),
    Collabel("FALSE", KeywordCategory.RESERVED, "Boolean false"),
    Collabel("CASE", KeywordCategory.RESERVED, "Case expression"),
    Collabel("WHEN", KeywordCategory.RESERVED, "Case when"),
    Collabel("THEN", KeywordCategory.RESERVED, "Case then"),
    Collabel("ELSE", KeywordCategory.RESERVED, "Case else"),
    Collabel("END", KeywordCategory.RESERVED, "End block"),
    Collabel("UNION", KeywordCategory.RESERVED, "Set union"),
    Collabel("INTERSECT", KeywordCategory.RESERVED, "Set intersect"),
    Collabel("EXCEPT", KeywordCategory.RESERVED, "Set except"),
    Collabel("ALL", KeywordCategory.RESERVED, "All quantifier"),
    Collabel("DISTINCT", KeywordCategory.RESERVED, "Distinct values"),
    Collabel("INTO", KeywordCategory.RESERVED, "Into clause"),
    Collabel("VALUES", KeywordCategory.RESERVED, "Values list"),
    Collabel("SET", KeywordCategory.RESERVED, "Set clause"),
    Collabel("UPDATE", KeywordCategory.RESERVED, "Update statement"),
    Collabel("DELETE", KeywordCategory.RESERVED, "Delete statement"),
    Collabel("INSERT", KeywordCategory.RESERVED, "Insert statement"),
    Collabel("CREATE", KeywordCategory.RESERVED, "Create statement"),
    Collabel("DROP", KeywordCategory.RESERVED, "Drop statement"),
    Collabel("ALTER", KeywordCategory.RESERVED, "Alter statement"),
    Collabel("TABLE", KeywordCategory.RESERVED, "Table object"),
    Collabel("VIEW", KeywordCategory.RESERVED, "View object"),
    Collabel("SCHEMA", KeywordCategory.RESERVED, "Schema object"),
    Collabel("DATABASE", KeywordCategory.RESERVED, "Database object"),
    Collabel("INDEX", KeywordCategory.RESERVED, "Index object"),
    Collabel("WITH", KeywordCategory.RESERVED, "With clause (CTE)"),
    Collabel("BY", KeywordCategory.RESERVED, "By clause"),
    Collabel("ASC", KeywordCategory.RESERVED, "Ascending order"),
    Collabel("DESC", KeywordCategory.RESERVED, "Descending order"),
    Collabel("FETCH", KeywordCategory.RESERVED, "Fetch clause"),
    Collabel("FIRST", KeywordCategory.RESERVED, "First rows"),
    Collabel("NEXT", KeywordCategory.RESERVED, "Next rows"),
    Collabel("ROW", KeywordCategory.RESERVED, "Row"),
    Collabel("ROWS", KeywordCategory.RESERVED, "Multiple rows"),
    Collabel("ONLY", KeywordCategory.RESERVED, "Only modifier"),
    Collabel("TIES", KeywordCategory.RESERVED, "Ties modifier"),
    Collabel("GRANT", KeywordCategory.RESERVED, "Grant privilege"),
    Collabel("REVOKE", KeywordCategory.RESERVED, "Revoke privilege"),
    Collabel("PRIMARY", KeywordCategory.RESERVED, "Primary key"),
    Collabel("KEY", KeywordCategory.RESERVED, "Key"),
    Collabel("FOREIGN", KeywordCategory.RESERVED, "Foreign key"),
    Collabel("REFERENCES", KeywordCategory.RESERVED, "References"),
    Collabel("CONSTRAINT", KeywordCategory.RESERVED, "Constraint"),
    Collabel("CHECK", KeywordCategory.RESERVED, "Check constraint"),
    Collabel("DEFAULT", KeywordCategory.RESERVED, "Default value"),
    Collabel("UNIQUE", KeywordCategory.RESERVED, "Unique constraint"),
    Collabel("CASCADE", KeywordCategory.RESERVED, "Cascade action"),
    Collabel("RESTRICT", KeywordCategory.RESERVED, "Restrict action"),
    Collabel("NO", KeywordCategory.RESERVED, "No action"),
    Collabel("ACTION", KeywordCategory.RESERVED, "Action"),
    Collabel("ADD", KeywordCategory.RESERVED, "Add column"),
    Collabel("COLUMN", KeywordCategory.RESERVED, "Column"),
    Collabel("RENAME", KeywordCategory.RESERVED, "Rename"),
    Collabel("TO", KeywordCategory.RESERVED, "To"),
    Collabel("IF", KeywordCategory.RESERVED, "Conditional"),
    Collabel("TEMPORARY", KeywordCategory.RESERVED, "Temporary object"),
    Collabel("TEMP", KeywordCategory.RESERVED, "Temporary (short)"),
    Collabel("REPLACE", KeywordCategory.RESERVED, "Replace"),
    Collabel("TRUNCATE", KeywordCategory.RESERVED, "Truncate table"),
    Collabel("MERGE", KeywordCategory.RESERVED, "Merge statement"),
    Collabel("MATCHED", KeywordCategory.RESERVED, "Merge matched"),
    Collabel("SOURCE", KeywordCategory.RESERVED, "Merge source"),
    Collabel("TARGET", KeywordCategory.RESERVED, "Merge target"),
    Collabel("OUTPUT", KeywordCategory.RESERVED, "Output clause"),
    Collabel("WHERE", KeywordCategory.RESERVED, "Where clause"),
    
    # ========================================================================
    # COL_NAME KEYWORDS - Data types (can be used as column names)
    # ========================================================================
    Collabel("TINYINT", KeywordCategory.COL_NAME, "8-bit integer"),
    Collabel("SMALLINT", KeywordCategory.COL_NAME, "16-bit integer"),
    Collabel("INTEGER", KeywordCategory.COL_NAME, "32-bit integer"),
    Collabel("INT", KeywordCategory.COL_NAME, "32-bit integer (alias)"),
    Collabel("BIGINT", KeywordCategory.COL_NAME, "64-bit integer"),
    Collabel("DECIMAL", KeywordCategory.COL_NAME, "Decimal type"),
    Collabel("NUMERIC", KeywordCategory.COL_NAME, "Numeric type"),
    Collabel("REAL", KeywordCategory.COL_NAME, "Single precision float"),
    Collabel("DOUBLE", KeywordCategory.COL_NAME, "Double precision float"),
    Collabel("FLOAT", KeywordCategory.COL_NAME, "Float type"),
    Collabel("VARCHAR", KeywordCategory.COL_NAME, "Variable length string"),
    Collabel("CHAR", KeywordCategory.COL_NAME, "Fixed length string"),
    Collabel("CHARACTER", KeywordCategory.COL_NAME, "Character type"),
    Collabel("VARBINARY", KeywordCategory.COL_NAME, "Variable length binary"),
    Collabel("JSON", KeywordCategory.COL_NAME, "JSON type"),
    Collabel("STRING", KeywordCategory.COL_NAME, "String type (Hive)"),
    Collabel("BINARY", KeywordCategory.COL_NAME, "Binary type"),
    Collabel("DATE", KeywordCategory.COL_NAME, "Date type"),
    Collabel("TIME", KeywordCategory.COL_NAME, "Time type"),
    Collabel("TIMESTAMP", KeywordCategory.COL_NAME, "Timestamp type"),
    Collabel("INTERVAL", KeywordCategory.COL_NAME, "Interval type"),
    Collabel("BOOLEAN", KeywordCategory.COL_NAME, "Boolean type"),
    Collabel("BOOL", KeywordCategory.COL_NAME, "Boolean (alias)"),
    Collabel("ARRAY", KeywordCategory.COL_NAME, "Array type"),
    Collabel("MAP", KeywordCategory.COL_NAME, "Map type"),
    Collabel("ROW", KeywordCategory.COL_NAME, "Row type"),
    Collabel("IPADDRESS", KeywordCategory.COL_NAME, "IP address type"),
    Collabel("UUID", KeywordCategory.COL_NAME, "UUID type"),
    Collabel("HYPERLOGLOG", KeywordCategory.COL_NAME, "HyperLogLog type"),
    Collabel("QDIGEST", KeywordCategory.COL_NAME, "QDigest type"),
    Collabel("STRUCT", KeywordCategory.COL_NAME, "Struct type (Hive)"),
    Collabel("VOID", KeywordCategory.COL_NAME, "Void type"),
    
    # ========================================================================
    # COL_NAME KEYWORDS - Function names that can be column names
    # ========================================================================
    Collabel("COALESCE", KeywordCategory.COL_NAME, "Coalesce function"),
    Collabel("NULLIF", KeywordCategory.COL_NAME, "Nullif function"),
    Collabel("IF", KeywordCategory.COL_NAME, "If function"),
    Collabel("CAST", KeywordCategory.COL_NAME, "Cast function"),
    Collabel("TRY_CAST", KeywordCategory.COL_NAME, "Try cast function"),
    Collabel("TYPEOF", KeywordCategory.COL_NAME, "Typeof function"),
    Collabel("SUBSTRING", KeywordCategory.COL_NAME, "Substring function"),
    Collabel("TRIM", KeywordCategory.COL_NAME, "Trim function"),
    Collabel("POSITION", KeywordCategory.COL_NAME, "Position function"),
    Collabel("OVERLAY", KeywordCategory.COL_NAME, "Overlay function"),
    
    # ========================================================================
    # TYPE_FUNC_NAME KEYWORDS - Type/Function names
    # ========================================================================
    Collabel("COUNT", KeywordCategory.TYPE_FUNC_NAME, "Count aggregate"),
    Collabel("SUM", KeywordCategory.TYPE_FUNC_NAME, "Sum aggregate"),
    Collabel("AVG", KeywordCategory.TYPE_FUNC_NAME, "Average aggregate"),
    Collabel("MIN", KeywordCategory.TYPE_FUNC_NAME, "Minimum aggregate"),
    Collabel("MAX", KeywordCategory.TYPE_FUNC_NAME, "Maximum aggregate"),
    
    # ========================================================================
    # UNRESERVED KEYWORDS - Can be used as identifiers in most contexts
    # ========================================================================
    
    # HetuEngine-specific keywords (Hive compatibility)
    Collabel("PARTITIONED", KeywordCategory.UNRESERVED, "Partitioned table"),
    Collabel("CLUSTERED", KeywordCategory.UNRESERVED, "Clustered table"),
    Collabel("BUCKETS", KeywordCategory.UNRESERVED, "Number of buckets"),
    Collabel("STORED", KeywordCategory.UNRESERVED, "Storage format"),
    Collabel("FORMAT", KeywordCategory.UNRESERVED, "Format specification"),
    Collabel("DELIMITED", KeywordCategory.UNRESERVED, "Delimited format"),
    Collabel("FIELDS", KeywordCategory.UNRESERVED, "Fields specification"),
    Collabel("TERMINATED", KeywordCategory.UNRESERVED, "Terminated by"),
    Collabel("COLLECTION", KeywordCategory.UNRESERVED, "Collection items"),
    Collabel("ITEMS", KeywordCategory.UNRESERVED, "Collection items"),
    Collabel("KEYS", KeywordCategory.UNRESERVED, "Map keys"),
    Collabel("LINES", KeywordCategory.UNRESERVED, "Lines terminated"),
    Collabel("TBLPROPERTIES", KeywordCategory.UNRESERVED, "Table properties"),
    Collabel("EXTERNAL", KeywordCategory.UNRESERVED, "External table"),
    Collabel("LOCATION", KeywordCategory.UNRESERVED, "Storage location"),
    Collabel("SORT", KeywordCategory.UNRESERVED, "Sort specification"),
    Collabel("ORC", KeywordCategory.UNRESERVED, "ORC format"),
    Collabel("PARQUET", KeywordCategory.UNRESERVED, "Parquet format"),
    Collabel("AVRO", KeywordCategory.UNRESERVED, "Avro format"),
    Collabel("TEXTFILE", KeywordCategory.UNRESERVED, "Text file format"),
    Collabel("RCBINARY", KeywordCategory.UNRESERVED, "RC binary format"),
    Collabel("RCTEXT", KeywordCategory.UNRESERVED, "RC text format"),
    Collabel("SEQUENCEFILE", KeywordCategory.UNRESERVED, "Sequence file format"),
    Collabel("CSV", KeywordCategory.UNRESERVED, "CSV format"),
    Collabel("SNAPPY", KeywordCategory.UNRESERVED, "Snappy compression"),
    Collabel("ZLIB", KeywordCategory.UNRESERVED, "Zlib compression"),
    Collabel("GZIP", KeywordCategory.UNRESERVED, "Gzip compression"),
    Collabel("LZ4", KeywordCategory.UNRESERVED, "LZ4 compression"),
    Collabel("ZSTD", KeywordCategory.UNRESERVED, "Zstandard compression"),
    
    # Function-related keywords
    Collabel("FUNCTION", KeywordCategory.UNRESERVED, "Function definition"),
    Collabel("RETURNS", KeywordCategory.UNRESERVED, "Function returns"),
    Collabel("RETURN", KeywordCategory.UNRESERVED, "Return statement"),
    Collabel("LANGUAGE", KeywordCategory.UNRESERVED, "Function language"),
    Collabel("DETERMINISTIC", KeywordCategory.UNRESERVED, "Deterministic function"),
    Collabel("PYTHON", KeywordCategory.UNRESERVED, "Python language"),
    Collabel("HANDLER", KeywordCategory.UNRESERVED, "Function handler"),
    Collabel("BEGIN", KeywordCategory.UNRESERVED, "Begin block"),
    Collabel("DECLARE", KeywordCategory.UNRESERVED, "Declare variable"),
    Collabel("ITERATE", KeywordCategory.UNRESERVED, "Iterate loop"),
    Collabel("LEAVE", KeywordCategory.UNRESERVED, "Leave loop"),
    Collabel("LOOP", KeywordCategory.UNRESERVED, "Loop statement"),
    Collabel("REPEAT", KeywordCategory.UNRESERVED, "Repeat loop"),
    Collabel("WHILE", KeywordCategory.UNRESERVED, "While loop"),
    Collabel("UNTIL", KeywordCategory.UNRESERVED, "Until condition"),
    Collabel("ELSEIF", KeywordCategory.UNRESERVED, "Else if"),
    
    # Virtual schema
    Collabel("VIRTUAL", KeywordCategory.UNRESERVED, "Virtual schema"),
    
    # Materialized view
    Collabel("MATERIALIZED", KeywordCategory.UNRESERVED, "Materialized view"),
    Collabel("REFRESH", KeywordCategory.UNRESERVED, "Refresh materialized view"),
    Collabel("MV_VALIDITY", KeywordCategory.UNRESERVED, "MV validity period"),
    
    # Transaction keywords
    Collabel("START", KeywordCategory.UNRESERVED, "Start transaction"),
    Collabel("TRANSACTION", KeywordCategory.UNRESERVED, "Transaction"),
    Collabel("COMMIT", KeywordCategory.UNRESERVED, "Commit transaction"),
    Collabel("ROLLBACK", KeywordCategory.UNRESERVED, "Rollback transaction"),
    Collabel("ISOLATION", KeywordCategory.UNRESERVED, "Isolation level"),
    Collabel("LEVEL", KeywordCategory.UNRESERVED, "Isolation level"),
    Collabel("READ", KeywordCategory.UNRESERVED, "Read access"),
    Collabel("WRITE", KeywordCategory.UNRESERVED, "Write access"),
    Collabel("SERIALIZABLE", KeywordCategory.UNRESERVED, "Serializable isolation"),
    Collabel("UNCOMMITTED", KeywordCategory.UNRESERVED, "Read uncommitted"),
    Collabel("COMMITTED", KeywordCategory.UNRESERVED, "Read committed"),
    Collabel("REPEATABLE", KeywordCategory.UNRESERVED, "Repeatable read"),
    
    # Show/Describe keywords
    Collabel("SHOW", KeywordCategory.UNRESERVED, "Show statement"),
    Collabel("DESCRIBE", KeywordCategory.UNRESERVED, "Describe statement"),
    Collabel("EXPLAIN", KeywordCategory.UNRESERVED, "Explain statement"),
    Collabel("ANALYZE", KeywordCategory.UNRESERVED, "Analyze statement"),
    Collabel("CATALOGS", KeywordCategory.UNRESERVED, "Show catalogs"),
    Collabel("SCHEMAS", KeywordCategory.UNRESERVED, "Show schemas"),
    Collabel("TABLES", KeywordCategory.UNRESERVED, "Show tables"),
    Collabel("VIEWS", KeywordCategory.UNRESERVED, "Show views"),
    Collabel("COLUMNS", KeywordCategory.UNRESERVED, "Show columns"),
    Collabel("PARTITIONS", KeywordCategory.UNRESERVED, "Show partitions"),
    Collabel("SESSION", KeywordCategory.UNRESERVED, "Session properties"),
    Collabel("FUNCTIONS", KeywordCategory.UNRESERVED, "Show functions"),
    Collabel("STATS", KeywordCategory.UNRESERVED, "Statistics"),
    Collabel("STATUS", KeywordCategory.UNRESERVED, "Status information"),
    
    # Session management
    Collabel("CALL", KeywordCategory.UNRESERVED, "Call procedure"),
    Collabel("USE", KeywordCategory.UNRESERVED, "Use catalog/schema"),
    Collabel("RESET", KeywordCategory.UNRESERVED, "Reset property"),
    
    # Grouping and window functions
    Collabel("GROUPING", KeywordCategory.UNRESERVED, "Grouping function"),
    Collabel("SETS", KeywordCategory.UNRESERVED, "Grouping sets"),
    Collabel("CUBE", KeywordCategory.UNRESERVED, "Cube grouping"),
    Collabel("ROLLUP", KeywordCategory.UNRESERVED, "Rollup grouping"),
    Collabel("OVER", KeywordCategory.UNRESERVED, "Window specification"),
    Collabel("WINDOW", KeywordCategory.UNRESERVED, "Window clause"),
    Collabel("PARTITION", KeywordCategory.UNRESERVED, "Window partition"),
    
    # Join types
    Collabel("SEMI", KeywordCategory.UNRESERVED, "Semi join"),
    Collabel("ANTI", KeywordCategory.UNRESERVED, "Anti join"),
    
    # Table sampling
    Collabel("TABLESAMPLE", KeywordCategory.UNRESERVED, "Table sampling"),
    Collabel("SYSTEM", KeywordCategory.UNRESERVED, "System sampling"),
    Collabel("BERNOULLI", KeywordCategory.UNRESERVED, "Bernoulli sampling"),
    
    # Pattern matching
    Collabel("MATCH_RECOGNIZE", KeywordCategory.UNRESERVED, "Pattern matching"),
    Collabel("PATTERN", KeywordCategory.UNRESERVED, "Match pattern"),
    Collabel("DEFINE", KeywordCategory.UNRESERVED, "Define pattern variable"),
    Collabel("CLASSIFIER", KeywordCategory.UNRESERVED, "Pattern classifier"),
    Collabel("RUNNING", KeywordCategory.UNRESERVED, "Running measure"),
    Collabel("FINAL", KeywordCategory.UNRESERVED, "Final measure"),
    Collabel("ONE", KeywordCategory.UNRESERVED, "One row per match"),
    Collabel("PER", KeywordCategory.UNRESERVED, "Per match"),
    Collabel("MATCH", KeywordCategory.UNRESERVED, "Match clause"),
    
    # Insert overwrite
    Collabel("OVERWRITE", KeywordCategory.UNRESERVED, "Insert overwrite"),
    
    # Load data
    Collabel("LOAD", KeywordCategory.UNRESERVED, "Load data"),
    Collabel("DATA", KeywordCategory.UNRESERVED, "Data specification"),
    Collabel("INPATH", KeywordCategory.UNRESERVED, "Input path"),
    
    # Comment
    Collabel("COMMENT", KeywordCategory.UNRESERVED, "Comment"),
    
    # Pattern matching operators
    Collabel("RLIKE", KeywordCategory.UNRESERVED, "Regex like"),
    Collabel("REGEXP", KeywordCategory.UNRESERVED, "Regular expression"),
    
    # Window frame
    Collabel("PRECEDING", KeywordCategory.UNRESERVED, "Frame preceding"),
    Collabel("FOLLOWING", KeywordCategory.UNRESERVED, "Frame following"),
    Collabel("UNBOUNDED", KeywordCategory.UNRESERVED, "Unbounded frame"),
    Collabel("CURRENT", KeywordCategory.UNRESERVED, "Current row"),
    Collabel("RANGE", KeywordCategory.UNRESERVED, "Range frame"),
    Collabel("GROUPS", KeywordCategory.UNRESERVED, "Groups frame"),
    
    # Create table options
    Collabel("INCLUDING", KeywordCategory.UNRESERVED, "Including properties"),
    Collabel("EXCLUDING", KeywordCategory.UNRESERVED, "Excluding properties"),
    Collabel("PROPERTIES", KeywordCategory.UNRESERVED, "Properties map"),
    
    # Bucketing
    Collabel("BUCKET", KeywordCategory.UNRESERVED, "Bucket specification"),
    Collabel("BUCKET_COUNT", KeywordCategory.UNRESERVED, "Bucket count"),
    Collabel("BUCKETED_BY", KeywordCategory.UNRESERVED, "Bucketed by columns"),
    
    # Transactional
    Collabel("TRANSACTIONAL", KeywordCategory.UNRESERVED, "Transactional table"),
    Collabel("AUTO_PURGE", KeywordCategory.UNRESERVED, "Auto purge"),
    
    # Escape
    Collabel("ESCAPE", KeywordCategory.UNRESERVED, "Escape character"),
    Collabel("UESCAPE", KeywordCategory.UNRESERVED, "Unicode escape"),
    
    # Similar
    Collabel("SIMILAR", KeywordCategory.UNRESERVED, "Similar to"),
    
    # Normalize
    Collabel("NORMALIZE", KeywordCategory.UNRESERVED, "Normalize function"),
    Collabel("NFC", KeywordCategory.UNRESERVED, "NFC normalization"),
    Collabel("NFD", KeywordCategory.UNRESERVED, "NFD normalization"),
    Collabel("NFKC", KeywordCategory.UNRESERVED, "NFKC normalization"),
    Collabel("NFKD", KeywordCategory.UNRESERVED, "NFKD normalization"),
    
    # Catalog
    Collabel("CATALOG", KeywordCategory.UNRESERVED, "Catalog"),
    
    # Time zone
    Collabel("AT", KeywordCategory.UNRESERVED, "At time zone"),
    Collabel("ZONE", KeywordCategory.UNRESERVED, "Time zone"),
    Collabel("LOCAL", KeywordCategory.UNRESERVED, "Local time"),
    
    # Trim specification
    Collabel("LEADING", KeywordCategory.UNRESERVED, "Leading trim"),
    Collabel("TRAILING", KeywordCategory.UNRESERVED, "Trailing trim"),
    Collabel("BOTH", KeywordCategory.UNRESERVED, "Both trim"),
    
    # Nulls ordering
    Collabel("NULLS", KeywordCategory.UNRESERVED, "Nulls ordering"),
    
    # Within group
    Collabel("WITHIN", KeywordCategory.UNRESERVED, "Within group"),
    
    # Lateral
    Collabel("LATERAL", KeywordCategory.UNRESERVED, "Lateral join"),
    
    # Unnest
    Collabel("UNNEST", KeywordCategory.UNRESERVED, "Unnest array"),
    Collabel("APPLY", KeywordCategory.UNRESERVED, "Cross apply"),
    
    # Filter
    Collabel("FILTER", KeywordCategory.UNRESERVED, "Filter clause"),
    
    # Additional reserved keywords
    Collabel("RECURSIVE", KeywordCategory.RESERVED, "Recursive CTE"),
    Collabel("NATURAL", KeywordCategory.RESERVED, "Natural join"),
    Collabel("USING", KeywordCategory.RESERVED, "Using clause"),
    Collabel("FULL", KeywordCategory.RESERVED, "Full join"),
    Collabel("OUTER", KeywordCategory.RESERVED, "Outer join"),
    Collabel("SOME", KeywordCategory.RESERVED, "Some quantifier"),
    Collabel("ANY", KeywordCategory.RESERVED, "Any quantifier"),
    Collabel("CORRESPONDING", KeywordCategory.RESERVED, "Corresponding"),
    Collabel("TABLESAMPLE", KeywordCategory.RESERVED, "Table sample"),
    
    # More reserved keywords
    Collabel("GROUPING", KeywordCategory.RESERVED, "Grouping"),
    Collabel("CUBE", KeywordCategory.RESERVED, "Cube"),
    Collabel("ROLLUP", KeywordCategory.RESERVED, "Rollup"),
    Collabel("OVER", KeywordCategory.RESERVED, "Over"),
    Collabel("WINDOW", KeywordCategory.RESERVED, "Window"),
    Collabel("LATERAL", KeywordCategory.RESERVED, "Lateral"),
    Collabel("UNNEST", KeywordCategory.RESERVED, "Unnest"),
    
    # Additional data types
    Collabel("CHAR", KeywordCategory.COL_NAME, "Character"),
    Collabel("CHARACTER", KeywordCategory.COL_NAME, "Character"),
    Collabel("CHARACTER_VARYING", KeywordCategory.COL_NAME, "Character varying"),
    Collabel("CHAR_VARYING", KeywordCategory.COL_NAME, "Char varying"),
    Collabel("CHAR_LARGE_OBJECT", KeywordCategory.COL_NAME, "Char large object"),
    Collabel("CLOB", KeywordCategory.COL_NAME, "Character large object"),
    Collabel("BINARY_LARGE_OBJECT", KeywordCategory.COL_NAME, "Binary large object"),
    Collabel("BLOB", KeywordCategory.COL_NAME, "Binary large object"),
    Collabel("BINARY_VARYING", KeywordCategory.COL_NAME, "Binary varying"),
    Collabel("TIME_WITH_TIME_ZONE", KeywordCategory.COL_NAME, "Time with time zone"),
    Collabel("TIMESTAMP_WITH_TIME_ZONE", KeywordCategory.COL_NAME, "Timestamp with time zone"),
    
    # More unreserved keywords
    Collabel("ADMIN", KeywordCategory.UNRESERVED, "Admin"),
    Collabel("BERNOULLI", KeywordCategory.UNRESERVED, "Bernoulli"),
    Collabel("CATALOG", KeywordCategory.UNRESERVED, "Catalog"),
    Collabel("DAY", KeywordCategory.UNRESERVED, "Day interval"),
    Collabel("HOUR", KeywordCategory.UNRESERVED, "Hour interval"),
    Collabel("MINUTE", KeywordCategory.UNRESERVED, "Minute interval"),
    Collabel("MONTH", KeywordCategory.UNRESERVED, "Month interval"),
    Collabel("SECOND", KeywordCategory.UNRESERVED, "Second interval"),
    Collabel("YEAR", KeywordCategory.UNRESERVED, "Year interval"),
    Collabel("ZONE", KeywordCategory.UNRESERVED, "Time zone"),
    
    # Privileges
    Collabel("PRIVILEGE", KeywordCategory.UNRESERVED, "Privilege"),
    Collabel("ROLE", KeywordCategory.UNRESERVED, "Role"),
    Collabel("USER", KeywordCategory.UNRESERVED, "User"),
    Collabel("USAGE", KeywordCategory.UNRESERVED, "Usage privilege"),
    Collabel("EXECUTE", KeywordCategory.UNRESERVED, "Execute privilege"),
    Collabel("SELECT", KeywordCategory.UNRESERVED, "Select privilege"),
    Collabel("INSERT", KeywordCategory.UNRESERVED, "Insert privilege"),
    Collabel("DELETE", KeywordCategory.UNRESERVED, "Delete privilege"),
    Collabel("UPDATE", KeywordCategory.UNRESERVED, "Update privilege"),
    
    # Explain options
    Collabel("VERBOSE", KeywordCategory.UNRESERVED, "Verbose explain"),
    Collabel("COSTS", KeywordCategory.UNRESERVED, "Show costs"),
    Collabel("FORMAT", KeywordCategory.UNRESERVED, "Explain format"),
    Collabel("TYPE", KeywordCategory.UNRESERVED, "Explain type"),
    
    # Analyze options
    Collabel("VERBOSE", KeywordCategory.UNRESERVED, "Verbose analyze"),
    Collabel("COLUMNS", KeywordCategory.UNRESERVED, "Analyze columns"),
    
    # Additional Presto/Trino keywords
    Collabel("ARRAY_AGG", KeywordCategory.TYPE_FUNC_NAME, "Array aggregate"),
    Collabel("MAP_AGG", KeywordCategory.TYPE_FUNC_NAME, "Map aggregate"),
    Collabel("ROW_NUMBER", KeywordCategory.TYPE_FUNC_NAME, "Row number"),
    Collabel("RANK", KeywordCategory.TYPE_FUNC_NAME, "Rank function"),
    Collabel("DENSE_RANK", KeywordCategory.TYPE_FUNC_NAME, "Dense rank"),
    Collabel("NTILE", KeywordCategory.TYPE_FUNC_NAME, "Ntile function"),
    Collabel("LAG", KeywordCategory.TYPE_FUNC_NAME, "Lag function"),
    Collabel("LEAD", KeywordCategory.TYPE_FUNC_NAME, "Lead function"),
    Collabel("FIRST_VALUE", KeywordCategory.TYPE_FUNC_NAME, "First value"),
    Collabel("LAST_VALUE", KeywordCategory.TYPE_FUNC_NAME, "Last value"),
    Collabel("NTH_VALUE", KeywordCategory.TYPE_FUNC_NAME, "Nth value"),
    
    # More function names
    Collabel("ABS", KeywordCategory.TYPE_FUNC_NAME, "Absolute value"),
    Collabel("CEIL", KeywordCategory.TYPE_FUNC_NAME, "Ceiling"),
    Collabel("CEILING", KeywordCategory.TYPE_FUNC_NAME, "Ceiling"),
    Collabel("FLOOR", KeywordCategory.TYPE_FUNC_NAME, "Floor"),
    Collabel("ROUND", KeywordCategory.TYPE_FUNC_NAME, "Round"),
    Collabel("POWER", KeywordCategory.TYPE_FUNC_NAME, "Power"),
    Collabel("SQRT", KeywordCategory.TYPE_FUNC_NAME, "Square root"),
    Collabel("MOD", KeywordCategory.TYPE_FUNC_NAME, "Modulo"),
    Collabel("LOG", KeywordCategory.TYPE_FUNC_NAME, "Logarithm"),
    Collabel("LN", KeywordCategory.TYPE_FUNC_NAME, "Natural log"),
    Collabel("EXP", KeywordCategory.TYPE_FUNC_NAME, "Exponential"),
    Collabel("RAND", KeywordCategory.TYPE_FUNC_NAME, "Random"),
    Collabel("RANDOM", KeywordCategory.TYPE_FUNC_NAME, "Random"),
    Collabel("SIGN", KeywordCategory.TYPE_FUNC_NAME, "Sign"),
    Collabel("PI", KeywordCategory.TYPE_FUNC_NAME, "Pi"),
    Collabel("SIN", KeywordCategory.TYPE_FUNC_NAME, "Sine"),
    Collabel("COS", KeywordCategory.TYPE_FUNC_NAME, "Cosine"),
    Collabel("TAN", KeywordCategory.TYPE_FUNC_NAME, "Tangent"),
    Collabel("ASIN", KeywordCategory.TYPE_FUNC_NAME, "Arcsine"),
    Collabel("ACOS", KeywordCategory.TYPE_FUNC_NAME, "Arccosine"),
    Collabel("ATAN", KeywordCategory.TYPE_FUNC_NAME, "Arctangent"),
    Collabel("ATAN2", KeywordCategory.TYPE_FUNC_NAME, "Arctangent2"),
    
    # String functions
    Collabel("LENGTH", KeywordCategory.TYPE_FUNC_NAME, "String length"),
    Collabel("LEN", KeywordCategory.TYPE_FUNC_NAME, "String length"),
    Collabel("CHAR_LENGTH", KeywordCategory.TYPE_FUNC_NAME, "Character length"),
    Collabel("CHARACTER_LENGTH", KeywordCategory.TYPE_FUNC_NAME, "Character length"),
    Collabel("UPPER", KeywordCategory.TYPE_FUNC_NAME, "Uppercase"),
    Collabel("LOWER", KeywordCategory.TYPE_FUNC_NAME, "Lowercase"),
    Collabel("CONCAT", KeywordCategory.TYPE_FUNC_NAME, "Concatenate"),
    Collabel("REPLACE", KeywordCategory.TYPE_FUNC_NAME, "Replace"),
    Collabel("REVERSE", KeywordCategory.TYPE_FUNC_NAME, "Reverse"),
    Collabel("LEFT", KeywordCategory.TYPE_FUNC_NAME, "Left substring"),
    Collabel("RIGHT", KeywordCategory.TYPE_FUNC_NAME, "Right substring"),
    Collabel("LPAD", KeywordCategory.TYPE_FUNC_NAME, "Left pad"),
    Collabel("RPAD", KeywordCategory.TYPE_FUNC_NAME, "Right pad"),
    Collabel("SUBSTR", KeywordCategory.TYPE_FUNC_NAME, "Substring"),
    Collabel("INSTR", KeywordCategory.TYPE_FUNC_NAME, "Instr"),
    Collabel("LOCATE", KeywordCategory.TYPE_FUNC_NAME, "Locate"),
    Collabel("FIND_IN_SET", KeywordCategory.TYPE_FUNC_NAME, "Find in set"),
    Collabel("REGEXP_EXTRACT", KeywordCategory.TYPE_FUNC_NAME, "Regex extract"),
    Collabel("REGEXP_REPLACE", KeywordCategory.TYPE_FUNC_NAME, "Regex replace"),
    Collabel("REGEXP_LIKE", KeywordCategory.TYPE_FUNC_NAME, "Regex like"),
    Collabel("SPLIT", KeywordCategory.TYPE_FUNC_NAME, "Split"),
    Collabel("SPLIT_PART", KeywordCategory.TYPE_FUNC_NAME, "Split part"),
    Collabel("STARTS_WITH", KeywordCategory.TYPE_FUNC_NAME, "Starts with"),
    Collabel("ENDS_WITH", KeywordCategory.TYPE_FUNC_NAME, "Ends with"),
    Collabel("CONTAINS", KeywordCategory.TYPE_FUNC_NAME, "Contains"),
    Collabel("POSITION", KeywordCategory.TYPE_FUNC_NAME, "Position"),
    Collabel("STRPOS", KeywordCategory.TYPE_FUNC_NAME, "String position"),
    
    # Date/time functions
    Collabel("NOW", KeywordCategory.TYPE_FUNC_NAME, "Current timestamp"),
    Collabel("CURRENT_DATE", KeywordCategory.TYPE_FUNC_NAME, "Current date"),
    Collabel("CURRENT_TIME", KeywordCategory.TYPE_FUNC_NAME, "Current time"),
    Collabel("CURRENT_TIMESTAMP", KeywordCategory.TYPE_FUNC_NAME, "Current timestamp"),
    Collabel("LOCALTIME", KeywordCategory.TYPE_FUNC_NAME, "Local time"),
    Collabel("LOCALTIMESTAMP", KeywordCategory.TYPE_FUNC_NAME, "Local timestamp"),
    Collabel("DATE_ADD", KeywordCategory.TYPE_FUNC_NAME, "Date add"),
    Collabel("DATE_DIFF", KeywordCategory.TYPE_FUNC_NAME, "Date diff"),
    Collabel("DATE_FORMAT", KeywordCategory.TYPE_FUNC_NAME, "Date format"),
    Collabel("DATE_PARSE", KeywordCategory.TYPE_FUNC_NAME, "Date parse"),
    Collabel("YEAR", KeywordCategory.TYPE_FUNC_NAME, "Extract year"),
    Collabel("QUARTER", KeywordCategory.TYPE_FUNC_NAME, "Extract quarter"),
    Collabel("MONTH", KeywordCategory.TYPE_FUNC_NAME, "Extract month"),
    Collabel("WEEK", KeywordCategory.TYPE_FUNC_NAME, "Extract week"),
    Collabel("DAY", KeywordCategory.TYPE_FUNC_NAME, "Extract day"),
    Collabel("DAY_OF_WEEK", KeywordCategory.TYPE_FUNC_NAME, "Day of week"),
    Collabel("DAY_OF_YEAR", KeywordCategory.TYPE_FUNC_NAME, "Day of year"),
    Collabel("HOUR", KeywordCategory.TYPE_FUNC_NAME, "Extract hour"),
    Collabel("MINUTE", KeywordCategory.TYPE_FUNC_NAME, "Extract minute"),
    Collabel("SECOND", KeywordCategory.TYPE_FUNC_NAME, "Extract second"),
    Collabel("EXTRACT", KeywordCategory.TYPE_FUNC_NAME, "Extract"),
    Collabel("DATE_TRUNC", KeywordCategory.TYPE_FUNC_NAME, "Date truncate"),
    
    # Conditional functions
    Collabel("IF", KeywordCategory.TYPE_FUNC_NAME, "If function"),
    Collabel("IFNULL", KeywordCategory.TYPE_FUNC_NAME, "If null"),
    Collabel("ISNULL", KeywordCategory.TYPE_FUNC_NAME, "Is null"),
    Collabel("NULLIF", KeywordCategory.TYPE_FUNC_NAME, "Null if"),
    Collabel("COALESCE", KeywordCategory.TYPE_FUNC_NAME, "Coalesce"),
    Collabel("NVL", KeywordCategory.TYPE_FUNC_NAME, "NVL"),
    Collabel("NVL2", KeywordCategory.TYPE_FUNC_NAME, "NVL2"),
    Collabel("DECODE", KeywordCategory.TYPE_FUNC_NAME, "Decode"),
    
    # Conversion functions
    Collabel("CAST", KeywordCategory.TYPE_FUNC_NAME, "Cast"),
    Collabel("TRY_CAST", KeywordCategory.TYPE_FUNC_NAME, "Try cast"),
    Collabel("TYPEOF", KeywordCategory.TYPE_FUNC_NAME, "Type of"),
    Collabel("TO_CHAR", KeywordCategory.TYPE_FUNC_NAME, "To character"),
    Collabel("TO_DATE", KeywordCategory.TYPE_FUNC_NAME, "To date"),
    Collabel("TO_TIMESTAMP", KeywordCategory.TYPE_FUNC_NAME, "To timestamp"),
    Collabel("TO_UNIX_TIMESTAMP", KeywordCategory.TYPE_FUNC_NAME, "To unix timestamp"),
    Collabel("FROM_UNIXTIME", KeywordCategory.TYPE_FUNC_NAME, "From unix time"),
    
    # Array functions
    Collabel("ARRAY", KeywordCategory.TYPE_FUNC_NAME, "Array constructor"),
    Collabel("ARRAY_JOIN", KeywordCategory.TYPE_FUNC_NAME, "Array join"),
    Collabel("ARRAY_DISTINCT", KeywordCategory.TYPE_FUNC_NAME, "Array distinct"),
    Collabel("ARRAY_SORT", KeywordCategory.TYPE_FUNC_NAME, "Array sort"),
    Collabel("ARRAY_INTERSECT", KeywordCategory.TYPE_FUNC_NAME, "Array intersect"),
    Collabel("ARRAY_UNION", KeywordCategory.TYPE_FUNC_NAME, "Array union"),
    Collabel("ARRAY_EXCEPT", KeywordCategory.TYPE_FUNC_NAME, "Array except"),
    Collabel("ARRAY_MAX", KeywordCategory.TYPE_FUNC_NAME, "Array max"),
    Collabel("ARRAY_MIN", KeywordCategory.TYPE_FUNC_NAME, "Array min"),
    Collabel("ARRAY_POSITION", KeywordCategory.TYPE_FUNC_NAME, "Array position"),
    Collabel("ARRAY_REMOVE", KeywordCategory.TYPE_FUNC_NAME, "Array remove"),
    Collabel("ARRAY_SORT", KeywordCategory.TYPE_FUNC_NAME, "Array sort"),
    Collabel("ARRAYS_OVERLAP", KeywordCategory.TYPE_FUNC_NAME, "Arrays overlap"),
    Collabel("SIZE", KeywordCategory.TYPE_FUNC_NAME, "Array size"),
    Collabel("CARDINALITY", KeywordCategory.TYPE_FUNC_NAME, "Cardinality"),
    Collabel("ELEMENT_AT", KeywordCategory.TYPE_FUNC_NAME, "Element at"),
    Collabel("FLATTEN", KeywordCategory.TYPE_FUNC_NAME, "Flatten"),
    Collabel("SEQUENCE", KeywordCategory.TYPE_FUNC_NAME, "Sequence"),
    Collabel("SHUFFLE", KeywordCategory.TYPE_FUNC_NAME, "Shuffle"),
    Collabel("SLICE", KeywordCategory.TYPE_FUNC_NAME, "Slice"),
    
    # Map functions
    Collabel("MAP", KeywordCategory.TYPE_FUNC_NAME, "Map constructor"),
    Collabel("MAP_KEYS", KeywordCategory.TYPE_FUNC_NAME, "Map keys"),
    Collabel("MAP_VALUES", KeywordCategory.TYPE_FUNC_NAME, "Map values"),
    Collabel("MAP_ENTRIES", KeywordCategory.TYPE_FUNC_NAME, "Map entries"),
    Collabel("MAP_FROM_ENTRIES", KeywordCategory.TYPE_FUNC_NAME, "Map from entries"),
    Collabel("MAP_CONCAT", KeywordCategory.TYPE_FUNC_NAME, "Map concat"),
    Collabel("MAP_FILTER", KeywordCategory.TYPE_FUNC_NAME, "Map filter"),
    Collabel("MAP_ZIP", KeywordCategory.TYPE_FUNC_NAME, "Map zip"),
    Collabel("ELEMENT_AT", KeywordCategory.TYPE_FUNC_NAME, "Element at"),
    
    # JSON functions
    Collabel("JSON_EXTRACT", KeywordCategory.TYPE_FUNC_NAME, "JSON extract"),
    Collabel("JSON_EXTRACT_SCALAR", KeywordCategory.TYPE_FUNC_NAME, "JSON extract scalar"),
    Collabel("JSON_FORMAT", KeywordCategory.TYPE_FUNC_NAME, "JSON format"),
    Collabel("JSON_PARSE", KeywordCategory.TYPE_FUNC_NAME, "JSON parse"),
    Collabel("JSON_SIZE", KeywordCategory.TYPE_FUNC_NAME, "JSON size"),
    Collabel("IS_JSON", KeywordCategory.TYPE_FUNC_NAME, "Is JSON"),
    
    # Mathematical functions
    Collabel("ABS", KeywordCategory.TYPE_FUNC_NAME, "Absolute"),
    Collabel("CEIL", KeywordCategory.TYPE_FUNC_NAME, "Ceiling"),
    Collabel("CEILING", KeywordCategory.TYPE_FUNC_NAME, "Ceiling"),
    Collabel("FLOOR", KeywordCategory.TYPE_FUNC_NAME, "Floor"),
    Collabel("ROUND", KeywordCategory.TYPE_FUNC_NAME, "Round"),
    Collabel("TRUNCATE", KeywordCategory.TYPE_FUNC_NAME, "Truncate"),
    Collabel("MOD", KeywordCategory.TYPE_FUNC_NAME, "Modulo"),
    Collabel("POWER", KeywordCategory.TYPE_FUNC_NAME, "Power"),
    Collabel("POW", KeywordCategory.TYPE_FUNC_NAME, "Power"),
    Collabel("SQRT", KeywordCategory.TYPE_FUNC_NAME, "Square root"),
    Collabel("CBRT", KeywordCategory.TYPE_FUNC_NAME, "Cube root"),
    Collabel("EXP", KeywordCategory.TYPE_FUNC_NAME, "Exponential"),
    Collabel("LN", KeywordCategory.TYPE_FUNC_NAME, "Natural log"),
    Collabel("LOG2", KeywordCategory.TYPE_FUNC_NAME, "Log base 2"),
    Collabel("LOG10", KeywordCategory.TYPE_FUNC_NAME, "Log base 10"),
    Collabel("LOG", KeywordCategory.TYPE_FUNC_NAME, "Logarithm"),
    Collabel("SIGN", KeywordCategory.TYPE_FUNC_NAME, "Sign"),
    Collabel("PI", KeywordCategory.TYPE_FUNC_NAME, "Pi"),
    Collabel("E", KeywordCategory.TYPE_FUNC_NAME, "Euler number"),
    Collabel("RAND", KeywordCategory.TYPE_FUNC_NAME, "Random"),
    Collabel("RANDOM", KeywordCategory.TYPE_FUNC_NAME, "Random"),
    Collabel("CRC32", KeywordCategory.TYPE_FUNC_NAME, "CRC32"),
    Collabel("MD5", KeywordCategory.TYPE_FUNC_NAME, "MD5"),
    Collabel("SHA1", KeywordCategory.TYPE_FUNC_NAME, "SHA1"),
    Collabel("SHA2", KeywordCategory.TYPE_FUNC_NAME, "SHA2"),
    Collabel("SHA256", KeywordCategory.TYPE_FUNC_NAME, "SHA256"),
    Collabel("SHA512", KeywordCategory.TYPE_FUNC_NAME, "SHA512"),
    
    # Aggregate functions
    Collabel("COUNT", KeywordCategory.TYPE_FUNC_NAME, "Count"),
    Collabel("SUM", KeywordCategory.TYPE_FUNC_NAME, "Sum"),
    Collabel("AVG", KeywordCategory.TYPE_FUNC_NAME, "Average"),
    Collabel("MIN", KeywordCategory.TYPE_FUNC_NAME, "Minimum"),
    Collabel("MAX", KeywordCategory.TYPE_FUNC_NAME, "Maximum"),
    Collabel("STDDEV", KeywordCategory.TYPE_FUNC_NAME, "Standard deviation"),
    Collabel("STDDEV_SAMP", KeywordCategory.TYPE_FUNC_NAME, "Sample standard deviation"),
    Collabel("STDDEV_POP", KeywordCategory.TYPE_FUNC_NAME, "Population standard deviation"),
    Collabel("VARIANCE", KeywordCategory.TYPE_FUNC_NAME, "Variance"),
    Collabel("VAR_SAMP", KeywordCategory.TYPE_FUNC_NAME, "Sample variance"),
    Collabel("VAR_POP", KeywordCategory.TYPE_FUNC_NAME, "Population variance"),
    Collabel("COVAR_POP", KeywordCategory.TYPE_FUNC_NAME, "Population covariance"),
    Collabel("COVAR_SAMP", KeywordCategory.TYPE_FUNC_NAME, "Sample covariance"),
    Collabel("CORR", KeywordCategory.TYPE_FUNC_NAME, "Correlation"),
    Collabel("REGR_SLOPE", KeywordCategory.TYPE_FUNC_NAME, "Regression slope"),
    Collabel("REGR_INTERCEPT", KeywordCategory.TYPE_FUNC_NAME, "Regression intercept"),
    Collabel("REGR_R2", KeywordCategory.TYPE_FUNC_NAME, "Regression R-squared"),
    Collabel("APPROX_DISTINCT", KeywordCategory.TYPE_FUNC_NAME, "Approximate distinct count"),
    Collabel("APPROX_PERCENTILE", KeywordCategory.TYPE_FUNC_NAME, "Approximate percentile"),
    Collabel("APPROX_MOST_FREQUENT", KeywordCategory.TYPE_FUNC_NAME, "Approximate most frequent"),
    Collabel("BOOL_AND", KeywordCategory.TYPE_FUNC_NAME, "Boolean AND"),
    Collabel("BOOL_OR", KeywordCategory.TYPE_FUNC_NAME, "Boolean OR"),
    Collabel("EVERY", KeywordCategory.TYPE_FUNC_NAME, "Every"),
    Collabel("BIT_AND", KeywordCategory.TYPE_FUNC_NAME, "Bitwise AND"),
    Collabel("BIT_OR", KeywordCategory.TYPE_FUNC_NAME, "Bitwise OR"),
    Collabel("BIT_XOR", KeywordCategory.TYPE_FUNC_NAME, "Bitwise XOR"),
    
    # Window functions
    Collabel("ROW_NUMBER", KeywordCategory.TYPE_FUNC_NAME, "Row number"),
    Collabel("RANK", KeywordCategory.TYPE_FUNC_NAME, "Rank"),
    Collabel("DENSE_RANK", KeywordCategory.TYPE_FUNC_NAME, "Dense rank"),
    Collabel("PERCENT_RANK", KeywordCategory.TYPE_FUNC_NAME, "Percent rank"),
    Collabel("CUME_DIST", KeywordCategory.TYPE_FUNC_NAME, "Cumulative distribution"),
    Collabel("NTILE", KeywordCategory.TYPE_FUNC_NAME, "Ntile"),
    Collabel("LAG", KeywordCategory.TYPE_FUNC_NAME, "Lag"),
    Collabel("LEAD", KeywordCategory.TYPE_FUNC_NAME, "Lead"),
    Collabel("FIRST_VALUE", KeywordCategory.TYPE_FUNC_NAME, "First value"),
    Collabel("LAST_VALUE", KeywordCategory.TYPE_FUNC_NAME, "Last value"),
    Collabel("NTH_VALUE", KeywordCategory.TYPE_FUNC_NAME, "Nth value"),
    
    # Hash functions
    Collabel("HASH", KeywordCategory.TYPE_FUNC_NAME, "Hash"),
    Collabel("HASH_CODE", KeywordCategory.TYPE_FUNC_NAME, "Hash code"),
    
    # URL functions
    Collabel("URL_EXTRACT_HOST", KeywordCategory.TYPE_FUNC_NAME, "URL extract host"),
    Collabel("URL_EXTRACT_PATH", KeywordCategory.TYPE_FUNC_NAME, "URL extract path"),
    Collabel("URL_EXTRACT_QUERY", KeywordCategory.TYPE_FUNC_NAME, "URL extract query"),
    Collabel("URL_ENCODE", KeywordCategory.TYPE_FUNC_NAME, "URL encode"),
    Collabel("URL_DECODE", KeywordCategory.TYPE_FUNC_NAME, "URL decode"),
    
    # Encoding functions
    Collabel("TO_BASE64", KeywordCategory.TYPE_FUNC_NAME, "To base64"),
    Collabel("FROM_BASE64", KeywordCategory.TYPE_FUNC_NAME, "From base64"),
    Collabel("TO_HEX", KeywordCategory.TYPE_FUNC_NAME, "To hex"),
    Collabel("FROM_HEX", KeywordCategory.TYPE_FUNC_NAME, "From hex"),
    Collabel("TO_UTF8", KeywordCategory.TYPE_FUNC_NAME, "To UTF8"),
    Collabel("FROM_UTF8", KeywordCategory.TYPE_FUNC_NAME, "From UTF8"),
    
    # IP address functions
    Collabel("IP_PREFIX", KeywordCategory.TYPE_FUNC_NAME, "IP prefix"),
    Collabel("SUBNET", KeywordCategory.TYPE_FUNC_NAME, "Subnet"),
    
    # UUID functions
    Collabel("UUID", KeywordCategory.TYPE_FUNC_NAME, "UUID"),
    
    # Miscellaneous functions
    Collabel("CURRENT_USER", KeywordCategory.TYPE_FUNC_NAME, "Current user"),
    Collabel("CURRENT_CATALOG", KeywordCategory.TYPE_FUNC_NAME, "Current catalog"),
    Collabel("CURRENT_SCHEMA", KeywordCategory.TYPE_FUNC_NAME, "Current schema"),
    Collabel("CURRENT_TIMEZONE", KeywordCategory.TYPE_FUNC_NAME, "Current timezone"),
    Collabel("FORMAT", KeywordCategory.TYPE_FUNC_NAME, "Format"),
    Collabel("FORMAT_NUMBER", KeywordCategory.TYPE_FUNC_NAME, "Format number"),
    Collabel("PRINTF", KeywordCategory.TYPE_FUNC_NAME, "Printf"),
    Collabel("CONCAT_WS", KeywordCategory.TYPE_FUNC_NAME, "Concat with separator"),
    Collabel("SPACE", KeywordCategory.TYPE_FUNC_NAME, "Space"),
    Collabel("REPEAT", KeywordCategory.TYPE_FUNC_NAME, "Repeat"),
    
    # More reserved keywords
    Collabel("ADD", KeywordCategory.RESERVED, "Add"),
    Collabel("ALL", KeywordCategory.RESERVED, "All"),
    Collabel("ALTER", KeywordCategory.RESERVED, "Alter"),
    Collabel("ANALYZE", KeywordCategory.RESERVED, "Analyze"),
    Collabel("AND", KeywordCategory.RESERVED, "And"),
    Collabel("AS", KeywordCategory.RESERVED, "As"),
    Collabel("ASC", KeywordCategory.RESERVED, "Asc"),
    Collabel("BETWEEN", KeywordCategory.RESERVED, "Between"),
    Collabel("BY", KeywordCategory.RESERVED, "By"),
    Collabel("CALL", KeywordCategory.RESERVED, "Call"),
    Collabel("CASE", KeywordCategory.RESERVED, "Case"),
    Collabel("CAST", KeywordCategory.RESERVED, "Cast"),
    Collabel("CHECK", KeywordCategory.RESERVED, "Check"),
    Collabel("COLUMN", KeywordCategory.RESERVED, "Column"),
    Collabel("CONSTRAINT", KeywordCategory.RESERVED, "Constraint"),
    Collabel("CREATE", KeywordCategory.RESERVED, "Create"),
    Collabel("CROSS", KeywordCategory.RESERVED, "Cross"),
    Collabel("CURRENT_DATE", KeywordCategory.RESERVED, "Current date"),
    Collabel("CURRENT_TIME", KeywordCategory.RESERVED, "Current time"),
    Collabel("CURRENT_TIMESTAMP", KeywordCategory.RESERVED, "Current timestamp"),
    Collabel("DEALLOCATE", KeywordCategory.RESERVED, "Deallocate"),
    Collabel("DELETE", KeywordCategory.RESERVED, "Delete"),
    Collabel("DESC", KeywordCategory.RESERVED, "Desc"),
    Collabel("DESCRIBE", KeywordCategory.RESERVED, "Describe"),
    Collabel("DISTINCT", KeywordCategory.RESERVED, "Distinct"),
    Collabel("DROP", KeywordCategory.RESERVED, "Drop"),
    Collabel("ELSE", KeywordCategory.RESERVED, "Else"),
    Collabel("END", KeywordCategory.RESERVED, "End"),
    Collabel("ESCAPE", KeywordCategory.RESERVED, "Escape"),
    Collabel("EXCEPT", KeywordCategory.RESERVED, "Except"),
    Collabel("EXECUTE", KeywordCategory.RESERVED, "Execute"),
    Collabel("EXISTS", KeywordCategory.RESERVED, "Exists"),
    Collabel("EXPLAIN", KeywordCategory.RESERVED, "Explain"),
    Collabel("FALSE", KeywordCategory.RESERVED, "False"),
    Collabel("FETCH", KeywordCategory.RESERVED, "Fetch"),
    Collabel("FOR", KeywordCategory.RESERVED, "For"),
    Collabel("FROM", KeywordCategory.RESERVED, "From"),
    Collabel("FULL", KeywordCategory.RESERVED, "Full"),
    Collabel("GROUP", KeywordCategory.RESERVED, "Group"),
    Collabel("GROUPING", KeywordCategory.RESERVED, "Grouping"),
    Collabel("HAVING", KeywordCategory.RESERVED, "Having"),
    Collabel("IN", KeywordCategory.RESERVED, "In"),
    Collabel("INNER", KeywordCategory.RESERVED, "Inner"),
    Collabel("INSERT", KeywordCategory.RESERVED, "Insert"),
    Collabel("INTERSECT", KeywordCategory.RESERVED, "Intersect"),
    Collabel("INTO", KeywordCategory.RESERVED, "Into"),
    Collabel("IS", KeywordCategory.RESERVED, "Is"),
    Collabel("JOIN", KeywordCategory.RESERVED, "Join"),
    Collabel("LEFT", KeywordCategory.RESERVED, "Left"),
    Collabel("LIKE", KeywordCategory.RESERVED, "Like"),
    Collabel("LOCALTIME", KeywordCategory.RESERVED, "Localtime"),
    Collabel("LOCALTIMESTAMP", KeywordCategory.RESERVED, "Localtimestamp"),
    Collabel("NATURAL", KeywordCategory.RESERVED, "Natural"),
    Collabel("NORMALIZE", KeywordCategory.RESERVED, "Normalize"),
    Collabel("NOT", KeywordCategory.RESERVED, "Not"),
    Collabel("NULL", KeywordCategory.RESERVED, "Null"),
    Collabel("ON", KeywordCategory.RESERVED, "On"),
    Collabel("OR", KeywordCategory.RESERVED, "Or"),
    Collabel("ORDER", KeywordCategory.RESERVED, "Order"),
    Collabel("OUTER", KeywordCategory.RESERVED, "Outer"),
    Collabel("PREPARE", KeywordCategory.RESERVED, "Prepare"),
    Collabel("RECURSIVE", KeywordCategory.RESERVED, "Recursive"),
    Collabel("RIGHT", KeywordCategory.RESERVED, "Right"),
    Collabel("ROLLUP", KeywordCategory.RESERVED, "Rollup"),
    Collabel("ROW", KeywordCategory.RESERVED, "Row"),
    Collabel("SELECT", KeywordCategory.RESERVED, "Select"),
    Collabel("SKIP", KeywordCategory.RESERVED, "Skip"),
    Collabel("SOME", KeywordCategory.RESERVED, "Some"),
    Collabel("TABLE", KeywordCategory.RESERVED, "Table"),
    Collabel("THEN", KeywordCategory.RESERVED, "Then"),
    Collabel("TRUE", KeywordCategory.RESERVED, "True"),
    Collabel("UESCAPE", KeywordCategory.RESERVED, "Uescape"),
    Collabel("UNION", KeywordCategory.RESERVED, "Union"),
    Collabel("UNNEST", KeywordCategory.RESERVED, "Unnest"),
    Collabel("USING", KeywordCategory.RESERVED, "Using"),
    Collabel("VALUES", KeywordCategory.RESERVED, "Values"),
    Collabel("WHEN", KeywordCategory.RESERVED, "When"),
    Collabel("WHERE", KeywordCategory.RESERVED, "Where"),
    Collabel("WITH", KeywordCategory.RESERVED, "With"),
]


# ============================================================================
# LOOKUP SETS
# ============================================================================

def _build_keyword_set(category: KeywordCategory) -> Set[str]:
    """Build a set of keywords for a specific category."""
    return {entry.keyword.upper() for entry in KEYWORD_ENTRIES if entry.category == category}


RESERVED_KEYWORDS: Set[str] = _build_keyword_set(KeywordCategory.RESERVED)
COL_NAME_KEYWORDS: Set[str] = _build_keyword_set(KeywordCategory.COL_NAME)
TYPE_FUNC_NAME_KEYWORDS: Set[str] = _build_keyword_set(KeywordCategory.TYPE_FUNC_NAME)
UNRESERVED_KEYWORDS: Set[str] = _build_keyword_set(KeywordCategory.UNRESERVED)
ALL_KEYWORDS: Set[str] = RESERVED_KEYWORDS | COL_NAME_KEYWORDS | TYPE_FUNC_NAME_KEYWORDS | UNRESERVED_KEYWORDS


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_keyword(word: str) -> bool:
    """
    Check if a word is a SQL keyword.
    
    Args:
        word: The word to check
        
    Returns:
        True if the word is a keyword, False otherwise
    """
    return word.upper() in ALL_KEYWORDS


def get_keyword_info(keyword: str) -> Optional[Collabel]:
    """
    Get detailed information about a keyword.
    
    Args:
        keyword: The keyword to look up
        
    Returns:
        Collabel object with keyword information, or None if not found
    """
    keyword_upper = keyword.upper()
    for entry in KEYWORD_ENTRIES:
        if entry.keyword.upper() == keyword_upper:
            return entry
    return None


def get_keyword_category(keyword: str) -> Optional[KeywordCategory]:
    """
    Get the category of a keyword.
    
    Args:
        keyword: The keyword to look up
        
    Returns:
        KeywordCategory enum value, or None if not found
    """
    info = get_keyword_info(keyword)
    return info.category if info else None


def is_reserved_keyword(keyword: str) -> bool:
    """
    Check if a keyword is a reserved keyword.
    
    Args:
        keyword: The keyword to check
        
    Returns:
        True if the keyword is reserved, False otherwise
    """
    return keyword.upper() in RESERVED_KEYWORDS


def keyword_token_name(keyword: str) -> Optional[str]:
    """
    Get the token name for a keyword (used in parser error messages).
    
    Args:
        keyword: The keyword to look up
        
    Returns:
        Token name string, or None if not found
    """
    info = get_keyword_info(keyword)
    if info is None:
        return None
    
    # Generate token name based on category
    category_prefix = {
        KeywordCategory.RESERVED: "T_RESERVED",
        KeywordCategory.COL_NAME: "T_COL_NAME",
        KeywordCategory.TYPE_FUNC_NAME: "T_TYPE_FUNC",
        KeywordCategory.UNRESERVED: "T_UNRESERVED",
    }
    
    prefix = category_prefix.get(info.category, "T_KEYWORD")
    return f"{prefix}_{info.keyword}"


def get_keywords_by_category(category: KeywordCategory) -> List[str]:
    """
    Get all keywords in a specific category.
    
    Args:
        category: The category to filter by
        
    Returns:
        List of keyword strings
    """
    return [entry.keyword for entry in KEYWORD_ENTRIES if entry.category == category]


def get_all_keywords_list() -> List[str]:
    """
    Get all keywords as a list.
    
    Returns:
        List of all keyword strings
    """
    return [entry.keyword for entry in KEYWORD_ENTRIES]


def get_keyword_count() -> Dict[KeywordCategory, int]:
    """
    Get the count of keywords in each category.
    
    Returns:
        Dictionary mapping category to count
    """
    counts = {cat: 0 for cat in KeywordCategory}
    for entry in KEYWORD_ENTRIES:
        counts[entry.category] += 1
    return counts


# ============================================================================
# MAIN - For testing and debugging
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("HetuEngine SQL Keywords Statistics")
    print("=" * 70)
    
    counts = get_keyword_count()
    total = sum(counts.values())
    
    print(f"\nTotal keywords: {total}")
    print(f"\nBreakdown by category:")
    for category, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category.name:20s}: {count:4d}")
    
    print(f"\nReserved keywords sample: {list(RESERVED_KEYWORDS)[:10]}")
    print(f"COL_NAME keywords sample: {list(COL_NAME_KEYWORDS)[:10]}")
    print(f"UNRESERVED keywords sample: {list(UNRESERVED_KEYWORDS)[:10]}")
    
    print("\n" + "=" * 70)
