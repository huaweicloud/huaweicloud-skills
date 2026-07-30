# -*- coding: utf-8 -*-
"""
ClickHouse SQL Parser (Statement Recognizer + Syntax Validator) — multi-version

Source: ClickHouse kernel src/Parsers/Parser*.cpp

This parser identifies the statement type and validates basic syntax structure
based on the version-specific grammar rules extracted from the kernel source.

Usage:
    python ck_sql_parser.py "<sql_text>" [version]

    version: ClickHouse kernel version (e.g., 24.8, 23.3). Default: 24.8
"""

import sys
import os
import json
from typing import List, Dict, Optional, Tuple

# Fix Windows encoding issues
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

from version_loader import load_keywords, DEFAULT_VERSION
from ck_sql_tokenizer import tokenize_full, Token, TokenType, init_version as tokenizer_init_version


# =============================================================================
# Statement Type Detection
# =============================================================================

def detect_statement_type(tokens: List[Token]) -> str:
    """Detect the statement type from the first keyword(s)."""
    if not tokens:
        return "EMPTY"

    # Get first significant token (skip whitespace/comments - already filtered)
    first = tokens[0]
    if first.type not in (TokenType.KEYWORD, TokenType.BARE_WORD):
        return "UNKNOWN"

    first_upper = first.value.upper()

    # Map first keyword(s) to statement type
    type_map = {
        "SELECT": "SELECT",
        "INSERT INTO": "INSERT",
        "INSERT": "INSERT",
        "UPSERT INTO": "UPSERT",
        "DELETE": "DELETE",
        "UPDATE": "UPDATE",
        "OPTIMIZE TABLE": "OPTIMIZE",
        "OPTIMIZE": "OPTIMIZE",
        "CREATE TABLE": "CREATE_TABLE",
        "CREATE TEMPORARY TABLE": "CREATE_TABLE",
        "CREATE DATABASE": "CREATE_DATABASE",
        "CREATE VIEW": "CREATE_VIEW",
        "CREATE MATERIALIZED VIEW": "CREATE_MATERIALIZED_VIEW",
        "CREATE DICTIONARY": "CREATE_DICTIONARY",
        "CREATE FUNCTION": "CREATE_FUNCTION",
        "CREATE INDEX": "CREATE_INDEX",
        "CREATE USER": "CREATE_USER",
        "CREATE ROLE": "CREATE_ROLE",
        "CREATE": "CREATE",
        "ALTER TABLE": "ALTER_TABLE",
        "ALTER DATABASE": "ALTER_DATABASE",
        "ALTER LIVE VIEW": "ALTER_VIEW",
        "ALTER USER": "ALTER_USER",
        "ALTER ROLE": "ALTER_ROLE",
        "ALTER": "ALTER",
        "DROP TABLE": "DROP_TABLE",
        "DROP DATABASE": "DROP_DATABASE",
        "DROP VIEW": "DROP_VIEW",
        "DROP DICTIONARY": "DROP_DICTIONARY",
        "DROP FUNCTION": "DROP_FUNCTION",
        "DROP INDEX": "DROP_INDEX",
        "DROP": "DROP",
        "RENAME TABLE": "RENAME_TABLE",
        "RENAME DATABASE": "RENAME_DATABASE",
        "RENAME DICTIONARY": "RENAME_DICTIONARY",
        "RENAME": "RENAME",
        "ATTACH": "ATTACH",
        "DETACH": "DETACH",
        "UNDROP": "UNDROP",
        "CHECK TABLE": "CHECK_TABLE",
        "CHECK": "CHECK",
        "DESCRIBE": "DESCRIBE",
        "DESC": "DESCRIBE",
        "USE": "USE",
        "SET": "SET",
        "GRANT": "GRANT",
        "REVOKE": "REVOKE",
        "BEGIN TRANSACTION": "BEGIN_TRANSACTION",
        "START TRANSACTION": "BEGIN_TRANSACTION",
        "COMMIT": "COMMIT",
        "ROLLBACK": "ROLLBACK",
        "EXPLAIN": "EXPLAIN",
        "SHOW": "SHOW",
        "KILL": "KILL",
        "SYSTEM": "SYSTEM",
        "BACKUP": "BACKUP",
        "RESTORE": "RESTORE",
        "WATCH": "WATCH",
        "TRUNCATE": "TRUNCATE",
        "EXCHANGE TABLES": "EXCHANGE_TABLES",
        "EXCHANGE DICTIONARIES": "EXCHANGE_DICTIONARIES",
    }

    # Try to match compound keywords first (longest match)
    # Check 3-word, 2-word, 1-word
    for num_words in [3, 2, 1]:
        if len(tokens) >= num_words:
            combined = ' '.join(t.value.upper() for t in tokens[:num_words]
                               if t.type in (TokenType.KEYWORD, TokenType.BARE_WORD))
            if combined in type_map:
                return type_map[combined]

    if first_upper in type_map:
        return type_map[first_upper]

    return "UNKNOWN"


# =============================================================================
# Syntax Validation
# =============================================================================

# Version-specific keyword functions (initialized by init_version)
_is_keyword = None
_is_reserved_keyword = None
_CURRENT_VERSION = None


def init_version(version=DEFAULT_VERSION):
    """Initialize parser with the specified ClickHouse version's keyword functions."""
    global _is_keyword, _is_reserved_keyword, _CURRENT_VERSION
    kw_mod = load_keywords(version)
    _is_keyword = kw_mod.is_keyword
    _is_reserved_keyword = kw_mod.is_reserved_keyword
    _CURRENT_VERSION = version
    # Also initialize the tokenizer's keywords to the same version
    tokenizer_init_version(version)


# Initialize with default version
init_version()


def get_current_version():
    """Return the currently active ClickHouse version."""
    return _CURRENT_VERSION


# SELECT clause order (for validation)
SELECT_CLAUSE_ORDER = [
    "WITH", "SELECT", "FROM", "PREWHERE", "WHERE",
    "GROUP BY", "HAVING", "WINDOW", "QUALIFY",
    "ORDER BY", "LIMIT", "OFFSET", "FETCH", "SETTINGS",
]

# Required clauses for each statement type
REQUIRED_CLAUSES = {
    "SELECT": ["SELECT"],
    "INSERT": ["INSERT INTO"],
    "DELETE": ["DELETE", "FROM", "WHERE"],
    "UPDATE": ["UPDATE", "SET", "WHERE"],
    "CREATE_TABLE": [],
    "ALTER_TABLE": [],
    "DROP_TABLE": ["DROP TABLE"],
}

# Clauses that should not appear before SELECT
CLAUSES_BEFORE_SELECT = {"WITH", "FROM"}


def validate_select_syntax(tokens: List[Token]) -> List[Dict]:
    """Validate SELECT statement syntax."""
    violations = []
    found_clauses = []
    clause_positions = {}

    for i, tok in enumerate(tokens):
        upper = tok.value.upper()
        if upper in SELECT_CLAUSE_ORDER:
            found_clauses.append(upper)
            clause_positions[upper] = i

    # Check clause ordering
    last_idx = -1
    for clause in SELECT_CLAUSE_ORDER:
        if clause in clause_positions:
            if clause_positions[clause] < last_idx:
                violations.append({
                    "rule_id": "SYN004",
                    "rule_name": "Clause Ordering Error",
                    "level": "ERROR",
                    "line": tokens[clause_positions[clause]].line,
                    "column": tokens[clause_positions[clause]].column,
                    "message": f"Clause '{clause}' appears out of order",
                    "fix_suggestion": f"Place '{clause}' in the correct position according to ClickHouse grammar",
                })
            else:
                last_idx = clause_positions[clause]

    # Check required clauses
    if "SELECT" not in found_clauses:
        violations.append({
            "rule_id": "SYN003",
            "rule_name": "Missing Required Clause",
            "level": "ERROR",
            "line": 1,
            "column": 1,
            "message": "Missing SELECT clause",
            "fix_suggestion": "Add SELECT clause with column list",
        })

    return violations


def validate_create_table_syntax(tokens: List[Token]) -> List[Dict]:
    """Validate CREATE TABLE statement syntax."""
    violations = []
    found_keywords = set()
    has_engine = False
    has_order_by = False
    has_create_table = False
    has_open_bracket = False
    has_close_bracket = False
    bracket_count = 0
    engine_name = ""
    expect_engine_name = False  # True when next non-'=' token is the engine name

    for tok in tokens:
        upper = tok.value.upper()
        found_keywords.add(upper)

        if upper == "CREATE TABLE" or (upper == "CREATE" and "TABLE" in found_keywords):
            has_create_table = True
        if upper == "ENGINE":
            has_engine = True
            expect_engine_name = True
        elif expect_engine_name:
            # Next non-'=' token after ENGINE is the engine name
            # (e.g., MergeTree, Distributed, Kafka, Buffer, ...)
            if upper == "=":
                pass  # Skip '=' between ENGINE and engine name
            elif tok.type == TokenType.OPEN_ROUND_BRACKET:
                # Malformed: ENGINE ( without a name — stop expecting
                expect_engine_name = False
            else:
                engine_name = upper
                expect_engine_name = False
        if upper == "ORDER BY":
            has_order_by = True
        if tok.type == TokenType.OPEN_ROUND_BRACKET:
            bracket_count += 1
            has_open_bracket = True
        if tok.type == TokenType.CLOSE_ROUND_BRACKET:
            bracket_count -= 1
            has_close_bracket = True

    # Check unbalanced parentheses
    if bracket_count != 0:
        violations.append({
            "rule_id": "SYN015",
            "rule_name": "Unclosed Parenthesis",
            "level": "ERROR",
            "line": 1,
            "column": 1,
            "message": f"Unbalanced parentheses (diff={bracket_count})",
            "fix_suggestion": "Ensure all parentheses are properly closed",
        })

    # Check missing ENGINE (warning)
    if has_create_table and not has_engine:
        violations.append({
            "rule_id": "SYN010",
            "rule_name": "CREATE TABLE Missing ENGINE",
            "level": "WARNING",
            "line": 1,
            "column": 1,
            "message": "CREATE TABLE without ENGINE clause (default engine will be used)",
            "fix_suggestion": "Add ENGINE = MergeTree() or appropriate engine",
        })

    # Check missing ORDER BY for MergeTree family (warning)
    # Only MergeTree family engines require ORDER BY; other engines
    # (Distributed, Buffer, View, Kafka, File, Memory, Log, etc.) do not.
    # MergeTree family: MergeTree, ReplacingMergeTree, SummingMergeTree,
    # AggregatingMergeTree, CollapsingMergeTree, VersionedCollapsingMergeTree,
    # GraphiteMergeTree, and their Replicated* variants.
    is_mergetree_family = "MERGETREE" in engine_name
    if has_engine and is_mergetree_family and not has_order_by:
        violations.append({
            "rule_id": "SYN011",
            "rule_name": "Missing ORDER BY",
            "level": "WARNING",
            "line": 1,
            "column": 1,
            "message": "MergeTree family tables should have ORDER BY clause",
            "fix_suggestion": "Add ORDER BY (column1, column2, ...)",
        })

    return violations


def validate_insert_syntax(tokens: List[Token]) -> List[Dict]:
    """Validate INSERT statement syntax."""
    violations = []
    has_into = False
    has_table = False

    for tok in tokens:
        upper = tok.value.upper()
        if upper in ("INSERT INTO", "INSERT"):
            has_into = True
        if upper == "TABLE":
            has_table = True

    return violations


def validate_delete_syntax(tokens: List[Token]) -> List[Dict]:
    """Validate DELETE statement syntax."""
    violations = []
    has_where = False
    has_from = False

    for tok in tokens:
        upper = tok.value.upper()
        if upper == "WHERE":
            has_where = True
        if upper == "FROM":
            has_from = True

    if not has_where:
        violations.append({
            "rule_id": "SYN012",
            "rule_name": "DELETE Missing WHERE",
            "level": "WARNING",
            "line": 1,
            "column": 1,
            "message": "DELETE without WHERE clause (will delete all rows)",
            "fix_suggestion": "Add WHERE clause to limit deletion scope",
        })

    if not has_from:
        violations.append({
            "rule_id": "SYN003",
            "rule_name": "Missing Required Clause",
            "level": "ERROR",
            "line": 1,
            "column": 1,
            "message": "Missing FROM clause in DELETE statement",
            "fix_suggestion": "Add FROM clause: DELETE FROM table_name WHERE ...",
        })

    return violations


def validate_update_syntax(tokens: List[Token]) -> List[Dict]:
    """Validate UPDATE statement syntax."""
    violations = []
    has_where = False
    has_set = False

    for tok in tokens:
        upper = tok.value.upper()
        if upper == "WHERE":
            has_where = True
        if upper == "SET":
            has_set = True

    if not has_where:
        violations.append({
            "rule_id": "SYN013",
            "rule_name": "UPDATE Missing WHERE",
            "level": "WARNING",
            "line": 1,
            "column": 1,
            "message": "UPDATE without WHERE clause (will update all rows)",
            "fix_suggestion": "Add WHERE clause to limit update scope",
        })

    if not has_set:
        violations.append({
            "rule_id": "SYN003",
            "rule_name": "Missing Required Clause",
            "level": "ERROR",
            "line": 1,
            "column": 1,
            "message": "Missing SET clause in UPDATE statement",
            "fix_suggestion": "Add SET clause: UPDATE table SET col = value WHERE ...",
        })

    return violations


def validate_parentheses(tokens: List[Token]) -> List[Dict]:
    """Check for unbalanced parentheses."""
    violations = []
    depth = 0
    for tok in tokens:
        if tok.type == TokenType.OPEN_ROUND_BRACKET:
            depth += 1
        elif tok.type == TokenType.CLOSE_ROUND_BRACKET:
            depth -= 1
            if depth < 0:
                violations.append({
                    "rule_id": "SYN015",
                    "rule_name": "Unclosed Parenthesis",
                    "level": "ERROR",
                    "line": tok.line,
                    "column": tok.column,
                    "message": "Extra closing parenthesis",
                    "fix_suggestion": "Remove extra ')' or add matching '('",
                })
    if depth > 0:
        violations.append({
            "rule_id": "SYN015",
            "rule_name": "Unclosed Parenthesis",
            "level": "ERROR",
            "line": 1,
            "column": 1,
            "message": f"Missing {depth} closing parenthesis(es)",
            "fix_suggestion": f"Add {depth} ')' to close open parentheses",
        })
    return violations


def parse_sql(sql_text: str, version: str = None) -> Dict:
    """
    Parse a ClickHouse SQL statement.

    Args:
        sql_text: SQL statement to parse
        version: ClickHouse kernel version (e.g., "24.8", "23.3").
                 If None, uses the currently initialized version.

    Returns a dict with:
    - statement_type: detected statement type
    - tokens: list of tokens
    - violations: list of syntax violations
    - errors: lexer errors
    - version: the ClickHouse version used
    """
    if version is not None and version != _CURRENT_VERSION:
        init_version(version)

    tokens, lexer_errors = tokenize_full(sql_text)

    stmt_type = detect_statement_type(tokens)
    violations = []

    # Add lexer errors as violations
    for err in lexer_errors:
        violations.append({
            "rule_id": "SYN-ERR",
            "rule_name": "Lexical Error",
            "level": "ERROR",
            "line": 1,
            "column": 1,
            "message": err,
            "fix_suggestion": "Fix the lexical error in the SQL text",
        })

    # Check for reserved keywords used as identifiers
    for tok in tokens:
        if (tok.type == TokenType.BARE_WORD and
                _is_reserved_keyword(tok.value) and
                not tok.is_keyword):
            violations.append({
                "rule_id": "SYN002",
                "rule_name": "Reserved Keyword as Identifier",
                "level": "WARNING",
                "line": tok.line,
                "column": tok.column,
                "message": f"Reserved keyword '{tok.value}' used as identifier",
                "fix_suggestion": f"Quote the identifier with backticks: `{tok.value}`",
            })

    # Validate parentheses
    violations.extend(validate_parentheses(tokens))

    # Statement-specific validation
    if stmt_type == "SELECT":
        violations.extend(validate_select_syntax(tokens))
    elif stmt_type == "CREATE_TABLE":
        violations.extend(validate_create_table_syntax(tokens))
    elif stmt_type == "INSERT":
        violations.extend(validate_insert_syntax(tokens))
    elif stmt_type == "DELETE":
        violations.extend(validate_delete_syntax(tokens))
    elif stmt_type == "UPDATE":
        violations.extend(validate_update_syntax(tokens))

    return {
        "statement_type": stmt_type,
        "token_count": len(tokens),
        "keyword_count": sum(1 for t in tokens if t.is_keyword),
        "violations": violations,
        "errors": lexer_errors,
        "version": _CURRENT_VERSION,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python ck_sql_parser.py "<sql_text>" [version]')
        print(f'  version: ClickHouse kernel version. Supported: 24.8, 23.3')
        print(f'  default: {DEFAULT_VERSION}')
        sys.exit(1)

    sql_text = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VERSION

    from version_loader import get_supported_versions
    if version not in get_supported_versions():
        print(f'Error: unsupported version "{version}". Supported: {", ".join(get_supported_versions())}')
        sys.exit(1)

    result = parse_sql(sql_text, version)
    print(json.dumps(result, indent=2, ensure_ascii=False))
