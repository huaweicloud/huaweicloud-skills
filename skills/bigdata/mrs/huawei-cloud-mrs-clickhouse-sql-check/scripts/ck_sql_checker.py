# -*- coding: utf-8 -*-
"""
ClickHouse SQL Checker Engine (multi-version)

Integrates tokenizer, parser, and rule-based checking.

Supports modes:
1. Syntax Check - keyword validation, structure validation, ClickHouse syntax compatibility
2. Specification Check - development spec rules (SPEC001-SPEC034)

Usage:
    python ck_sql_checker.py "<sql_text>" [syntax|spec|all] [version]

    version: ClickHouse kernel version (e.g., 24.8, 23.3). Default: 24.8

Output: JSON (default) or Markdown report (via check_sql_markdown)
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Optional

# Fix Windows encoding issues (GBK cannot handle emoji characters)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

from version_loader import load_spec_rules, get_supported_versions, DEFAULT_VERSION
from ck_sql_tokenizer import tokenize_full, Token, TokenType
from ck_sql_parser import parse_sql, detect_statement_type, init_version as parser_init_version

# Load common spec rules (version-independent)
_spec_mod = load_spec_rules()
SPEC_RULES = _spec_mod.SPEC_RULES
TOTAL_SPEC_RULES = _spec_mod.TOTAL_SPEC_RULES
make_violation = _spec_mod.make_violation


# =============================================================================
# Violation class
# =============================================================================
class Violation:
    """Represents a rule violation."""

    def __init__(self, rule_id, rule_name, level, category, message,
                 line=0, column=0, sql_snippet="", fix_suggestion=""):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.level = level  # ERROR, WARNING, INFO
        self.category = category
        self.message = message
        self.line = line
        self.column = column
        self.sql_snippet = sql_snippet
        self.fix_suggestion = fix_suggestion

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "sql_snippet": self.sql_snippet,
            "fix_suggestion": self.fix_suggestion,
        }


# =============================================================================
# Check Engine
# =============================================================================
class ClickHouseSQLChecker:
    """ClickHouse SQL Check Engine."""

    # Total syntax rules
    TOTAL_SYNTAX_RULES = 15
    # Total specification rules
    TOTAL_SPEC_RULES = TOTAL_SPEC_RULES

    def __init__(self, sql_text, check_mode="syntax", version=DEFAULT_VERSION):
        self.sql_text = sql_text.strip()
        self.check_mode = check_mode  # syntax, spec, all
        self.version = version
        self.violations = []
        self.parse_result = None
        self.statement_type = "UNKNOWN"

    def check(self):
        """Run all checks and return the report."""
        parser_init_version(self.version)

        # Split by semicolon to handle multiple statements
        statements = self._split_statements(self.sql_text)

        for stmt_text in statements:
            if not stmt_text.strip():
                continue
            self._check_one_statement(stmt_text)

        return self._generate_report()

    @staticmethod
    def _split_statements(sql_text):
        """Split SQL text into individual statements by semicolon.

        Handles semicolons inside string literals and parentheses.
        """
        statements = []
        current = []
        depth = 0
        in_string = False
        string_char = None
        i = 0
        n = len(sql_text)
        while i < n:
            ch = sql_text[i]
            if in_string:
                current.append(ch)
                if ch == '\\' and i + 1 < n:
                    current.append(sql_text[i + 1])
                    i += 2
                    continue
                if ch == string_char:
                    if i + 1 < n and sql_text[i + 1] == string_char:
                        current.append(sql_text[i + 1])
                        i += 2
                        continue
                    in_string = False
                    string_char = None
            elif ch in ("'", '"'):
                in_string = True
                string_char = ch
                current.append(ch)
            elif ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
                depth -= 1
                current.append(ch)
            elif ch == ';' and depth == 0:
                stmt = ''.join(current)
                if stmt.strip():
                    statements.append(stmt)
                current = []
            else:
                current.append(ch)
            i += 1

        stmt = ''.join(current)
        if stmt.strip():
            statements.append(stmt)

        return statements

    def _check_one_statement(self, stmt_text):
        """Check a single SQL statement (may be one of several in the input)."""
        self.parse_result = parse_sql(stmt_text)
        stmt_type = self.parse_result["statement_type"]

        # Track statement types across multiple statements
        if self.statement_type == "UNKNOWN":
            self.statement_type = stmt_type
        elif stmt_type != "UNKNOWN":
            self.statement_type = "MULTI"

        # Convert parser violations to Violation objects
        for v in self.parse_result.get("violations", []):
            self.violations.append(Violation(
                rule_id=v["rule_id"],
                rule_name=v["rule_name"],
                level=v["level"],
                category="Syntax",
                message=v["message"],
                line=v.get("line", 0),
                column=v.get("column", 0),
                fix_suggestion=v.get("fix_suggestion", ""),
            ))

        # Run additional syntax checks
        if self.check_mode in ("syntax", "all"):
            self._check_syntax(stmt_text, stmt_type)

        # Run spec checks
        if self.check_mode in ("spec", "all"):
            self._check_spec(stmt_text, stmt_type)

    def _check_syntax(self, sql_text, stmt_type):
        """Run syntax-specific checks."""
        tokens, _ = tokenize_full(sql_text)

        # Check for empty SQL
        if not tokens:
            self.violations.append(Violation(
                "SYN003", "Empty SQL", "ERROR", "Syntax",
                "SQL text is empty or contains no valid tokens",
                1, 1, "", "Provide a valid SQL statement"
            ))
            return

        # Check for unknown statement type
        if stmt_type == "UNKNOWN":
            first_token = tokens[0] if tokens else None
            first_val = first_token.value if first_token else ""
            self.violations.append(Violation(
                "SYN001", "Unrecognized Statement", "WARNING", "Syntax",
                f"Unrecognized statement starting with '{first_val}'",
                first_token.line if first_token else 1,
                first_token.column if first_token else 1,
                first_val, "Check if the statement starts with a valid ClickHouse keyword"
            ))

    def _check_spec(self, sql_text, stmt_type):
        """Run specification checks based on MRS ClickHouse dev standards."""
        tokens, _ = tokenize_full(sql_text)
        if not tokens:
            return

        stmt = stmt_type
        upper_sql = sql_text.upper()

        # Build token value list (upper) for quick lookup
        tok_vals = [t.value.upper() for t in tokens]
        tok_uppers = {t.value.upper() for t in tokens}

        # Helper: find first token index by upper value
        def find_idx(keyword_upper):
            for i, t in enumerate(tokens):
                if t.value.upper() == keyword_upper:
                    return i
            return -1

        # ========== DDL: CREATE TABLE / CREATE MV ==========
        if stmt in ("CREATE_TABLE", "CREATE_MATERIALIZED_VIEW", "CREATE_VIEW"):
            self._check_create_table_spec(tokens, tok_uppers, upper_sql)
        elif stmt == "CREATE_DATABASE":
            pass

        # ========== DDL: ALTER / DROP ==========
        if stmt in ("ALTER_TABLE", "ALTER", "DROP_TABLE", "DROP"):
            self._check_ddl_ops_spec(tokens, tok_uppers, upper_sql)

        # ========== DML: INSERT ==========
        if stmt == "INSERT":
            self._check_insert_spec(tokens, tok_uppers, upper_sql)

        # ========== DML: DELETE / UPDATE ==========
        if stmt == "DELETE":
            self._check_delete_spec(tokens, tok_uppers)
        if stmt == "UPDATE":
            self._check_update_spec(tokens, tok_uppers)

        # ========== DML: OPTIMIZE ==========
        if stmt == "OPTIMIZE":
            self.violations.append(Violation(
                **make_violation("SPEC032", sql_snippet="OPTIMIZE")
            ))

        # ========== Query: SELECT ==========
        if stmt == "SELECT":
            self._check_select_spec(tokens, tok_uppers, upper_sql)

    # ----------------------------------------------------------------------
    # CREATE TABLE spec checks
    # ----------------------------------------------------------------------
    def _check_create_table_spec(self, tokens, tok_uppers, upper_sql):
        # SPEC001: Buffer engine forbidden
        if "BUFFER" in tok_uppers:
            eng_idx = -1
            for i, t in enumerate(tokens):
                if t.value.upper() == "ENGINE":
                    eng_idx = i
                    break
            if eng_idx > 0 and eng_idx + 2 < len(tokens):
                # Look for Buffer after ENGINE = / ENGINE
                for j in range(eng_idx, min(eng_idx + 5, len(tokens))):
                    if tokens[j].value.upper() == "BUFFER":
                        self.violations.append(Violation(
                            **make_violation("SPEC001", line=tokens[j].line,
                                             column=tokens[j].column,
                                             sql_snippet=tokens[j].value)))
                        break

        # SPEC002: Recommend Replicated engine
        if "ENGINE" in tok_uppers:
            has_replicated = any("REPLICATED" in v for v in tok_uppers)
            has_distributed = "DISTRIBUTED" in tok_uppers
            if not has_replicated and not has_distributed:
                eng_idx = find_engine_idx = -1
                for i, t in enumerate(tokens):
                    if t.value.upper() == "ENGINE":
                        find_engine_idx = i
                        break
                if find_engine_idx > 0:
                    self.violations.append(Violation(
                        **make_violation("SPEC002", line=tokens[find_engine_idx].line,
                                         column=tokens[find_engine_idx].column,
                                         sql_snippet=tokens[find_engine_idx].value)))

        # SPEC023: Kafka engine forbidden
        if "KAFKA" in tok_uppers:
            for t in tokens:
                if t.value.upper() == "KAFKA":
                    self.violations.append(Violation(
                        **make_violation("SPEC023", line=t.line,
                                         column=t.column, sql_snippet=t.value)))
                    break

        # SPEC009: column count > 5000
        # Count column definitions: count commas inside the column-list parens
        depth = 0
        col_count = 0
        in_cols = False
        for t in tokens:
            v = t.value.upper()
            if t.type == TokenType.OPEN_ROUND_BRACKET:
                depth += 1
                if depth == 1 and self.statement_type == "CREATE_TABLE":
                    in_cols = True
                    continue
            if t.type == TokenType.CLOSE_ROUND_BRACKET:
                if in_cols and depth == 1:
                    in_cols = False
                depth -= 1
            if in_cols and depth == 1 and t.type == TokenType.COMMA:
                col_count += 1
        if in_cols or col_count > 0:
            col_count += 1  # last column has no trailing comma
        if col_count > 5000:
            self.violations.append(Violation(
                **make_violation("SPEC009", sql_snippet=f"columns={col_count}")))

        # SPEC011: ORDER BY fields > 4
        ob_idx = -1
        for i, t in enumerate(tokens):
            if t.value.upper() == "ORDER BY":
                ob_idx = i
                break
        if ob_idx > 0:
            # Count fields inside ORDER BY (...)
            depth2 = 0
            field_count = 1
            started = False
            for t in tokens[ob_idx + 1:]:
                if t.type == TokenType.OPEN_ROUND_BRACKET:
                    depth2 += 1
                    started = True
                elif t.type == TokenType.CLOSE_ROUND_BRACKET:
                    depth2 -= 1
                    if started and depth2 == 0:
                        break
                elif t.type == TokenType.COMMA and started and depth2 == 1:
                    field_count += 1
                elif started and depth2 == 0 and t.type in (TokenType.KEYWORD, TokenType.BARE_WORD):
                    # ORDER BY col1, col2 (no parens) - stop at next clause
                    upper_w = t.value.upper()
                    if upper_w in ("PARTITION BY", "PRIMARY KEY", "ENGINE",
                                   "SETTINGS", "TTL", "SAMPLE BY", "WHERE",
                                   "GROUP BY", "HAVING", "LIMIT", "OFFSET"):
                        break
            if field_count > 4:
                self.violations.append(Violation(
                    **make_violation("SPEC011", sql_snippet=f"ORDER BY fields={field_count}")))

        # SPEC010: Missing TTL
        if "TTL" not in tok_uppers and "REPLICATED" in upper_sql:
            # Only warn for MergeTree family
            if any(e in upper_sql for e in ("MERGETREE", "REPLACED", "SUMMING",
                                            "AGGREGATING", "COLLAPSING")):
                self.violations.append(Violation(
                    **make_violation("SPEC010", sql_snippet="no TTL")))

        # SPEC015: skip indexes > 5
        idx_count = sum(1 for t in tokens if t.value.upper() == "INDEX")
        if idx_count > 5:
            self.violations.append(Violation(
                **make_violation("SPEC015", sql_snippet=f"INDEX count={idx_count}")))

        # SPEC019: POPULATE forbidden in CREATE MATERIALIZED VIEW
        if "POPULATE" in tok_uppers:
            for t in tokens:
                if t.value.upper() == "POPULATE":
                    self.violations.append(Violation(
                        **make_violation("SPEC019", line=t.line,
                                         column=t.column, sql_snippet="POPULATE")))
                    break

        # SPEC018: MV without TO (aggregation MV)
        if self.statement_type == "CREATE_MATERIALIZED_VIEW":
            if "TO" not in tok_uppers:
                self.violations.append(Violation(
                    **make_violation("SPEC018", sql_snippet="no TO clause")))

        # SPEC006: too many Nullable columns
        nullable_count = sum(1 for t in tokens if t.value.upper() == "NULLABLE")
        if nullable_count > 10:
            self.violations.append(Violation(
                **make_violation("SPEC006", sql_snippet=f"Nullable count={nullable_count}")))

    # ----------------------------------------------------------------------
    # ALTER / DROP spec checks
    # ----------------------------------------------------------------------
    def _check_ddl_ops_spec(self, tokens, tok_uppers, upper_sql):
        # SPEC014: DROP/ALTER without NO DELAY
        if self.statement_type in ("DROP_TABLE", "DROP") and "NO DELAY" not in tok_uppers:
            if "DELAY" not in tok_uppers:
                self.violations.append(Violation(
                    **make_violation("SPEC014", sql_snippet="missing NO DELAY")))

        # SPEC031: UPDATE on index columns (in ALTER TABLE ... UPDATE)
        if self.statement_type == "ALTER_TABLE" and "UPDATE" in tok_uppers:
            self.violations.append(Violation(
                **make_violation("SPEC031", sql_snippet="ALTER ... UPDATE")))

    # ----------------------------------------------------------------------
    # INSERT spec checks
    # ----------------------------------------------------------------------
    def _check_insert_spec(self, tokens, tok_uppers, upper_sql):
        # SPEC021: INSERT into distributed table (heuristic: table name contains _all or _dis)
        # Find table name after INSERT INTO
        into_idx = -1
        for i, t in enumerate(tokens):
            if t.value.upper() in ("INSERT INTO", "INSERT"):
                into_idx = i
                break
        if into_idx > 0 and into_idx + 1 < len(tokens):
            tbl_tok = tokens[into_idx + 1]
            tbl_name = tbl_tok.value.lower()
            # Heuristic: distributed table names often end with _all or _dis
            if tbl_name.endswith("_all") or tbl_name.endswith("_dis") or tbl_name.endswith("_distributed"):
                self.violations.append(Violation(
                    **make_violation("SPEC021", line=tbl_tok.line,
                                     column=tbl_tok.column,
                                     sql_snippet=tbl_tok.value)))

        # SPEC022: INSERT without partition (cannot statically verify, skip)
        # Note: actual single-partition check requires runtime data

    # ----------------------------------------------------------------------
    # DELETE spec checks
    # ----------------------------------------------------------------------
    def _check_delete_spec(self, tokens, tok_uppers):
        # SPEC030: DELETE mutation warning
        self.violations.append(Violation(
            **make_violation("SPEC030", sql_snippet="DELETE")))

    # ----------------------------------------------------------------------
    # UPDATE spec checks
    # ----------------------------------------------------------------------
    def _check_update_spec(self, tokens, tok_uppers):
        # SPEC030: UPDATE mutation warning
        self.violations.append(Violation(
            **make_violation("SPEC030", sql_snippet="UPDATE")))
        # SPEC031: UPDATE on index columns (cannot statically determine, warn generally)
        self.violations.append(Violation(
            **make_violation("SPEC031", sql_snippet="UPDATE")))

    # ----------------------------------------------------------------------
    # SELECT spec checks
    # ----------------------------------------------------------------------
    def _check_select_spec(self, tokens, tok_uppers, upper_sql):
        # SPEC024: SELECT *
        for i, t in enumerate(tokens):
            if t.value.upper() == "SELECT":
                # Check if next non-space token is *
                for j in range(i + 1, min(i + 3, len(tokens))):
                    if tokens[j].type == TokenType.ASTERISK:
                        self.violations.append(Violation(
                            **make_violation("SPEC024", line=tokens[j].line,
                                             column=tokens[j].column,
                                             sql_snippet="SELECT *")))
                        break
                break

        # SPEC025: distinct / countDistinct -> uniqCombined
        if "DISTINCT" in tok_uppers:
            for t in tokens:
                v = t.value.upper()
                if v == "DISTINCT" or "COUNTDISTINCT" in v:
                    self.violations.append(Violation(
                        **make_violation("SPEC025", line=t.line,
                                         column=t.column, sql_snippet=t.value)))
                    break

        # SPEC026: JOIN without GLOBAL (distributed scenario heuristic)
        has_join = any("JOIN" in v for v in tok_uppers)
        has_global_join = any("GLOBAL" in v for v in tok_uppers)
        has_in = "IN" in tok_uppers
        has_global_in = any(v in ("GLOBAL IN", "GLOBAL NOT IN") for v in tok_uppers)
        if has_join and not has_global_join:
            # Warn only if it looks like distributed (cannot know for sure, INFO level)
            for t in tokens:
                if "JOIN" in t.value.upper() and t.value.upper() != "GLOBAL JOIN":
                    self.violations.append(Violation(
                        **make_violation("SPEC026", line=t.line,
                                         column=t.column, sql_snippet=t.value)))
                    break

        # SPEC029: FINAL query
        if "FINAL" in tok_uppers:
            for t in tokens:
                if t.value.upper() == "FINAL":
                    self.violations.append(Violation(
                        **make_violation("SPEC029", line=t.line,
                                         column=t.column, sql_snippet="FINAL")))
                    break

        # SPEC034: Decimal type mismatch in type-sensitive functions
        self._check_decimal_type_consistency(tokens)

        # SPEC035: IN/NOT IN subquery column count mismatch
        self._check_in_subquery_columns(tokens)

    def _check_in_subquery_columns(self, tokens):
        """SPEC035: Check IN/NOT IN subquery column count matches left side."""
        # Find all IN/NOT IN keywords
        for i, t in enumerate(tokens):
            if t.value.upper() not in ("IN", "NOT IN"):
                continue

            # Check if right side is a subquery (starts with '(' followed by SELECT)
            if i + 1 >= len(tokens):
                continue

            next_tok = tokens[i + 1]
            if next_tok.type != TokenType.OPEN_ROUND_BRACKET:
                continue

            # Find matching close bracket
            depth = 1
            subquery_start = i + 2
            subquery_end = -1

            for j in range(subquery_start, len(tokens)):
                if tokens[j].type == TokenType.OPEN_ROUND_BRACKET:
                    depth += 1
                elif tokens[j].type == TokenType.CLOSE_ROUND_BRACKET:
                    depth -= 1
                    if depth == 0:
                        subquery_end = j
                        break

            if subquery_end == -1:
                continue

            # Check if subquery starts with SELECT
            if subquery_start >= len(tokens):
                continue

            first_tok = tokens[subquery_start]
            if first_tok.value.upper() != "SELECT":
                continue

            # Count columns in subquery
            subquery_cols = self._count_select_columns(tokens, subquery_start, subquery_end)

            # Count columns on left side
            left_cols = self._count_left_columns(tokens, i)

            # Compare
            if left_cols > 0 and subquery_cols > 0 and left_cols != subquery_cols:
                self.violations.append(Violation(
                    **make_violation("SPEC035", line=t.line, column=t.column,
                                     sql_snippet=f"{left_cols} vs {subquery_cols}")))

    def _count_select_columns(self, tokens, start, end):
        """Count columns in SELECT statement between start and end positions."""
        # Skip SELECT keyword
        pos = start + 1
        if pos >= end:
            return 0

        # Check for SELECT *
        if tokens[pos].type == TokenType.ASTERISK:
            return -1  # Cannot determine

        columns = 1
        depth = 0

        while pos < end:
            t = tokens[pos]

            # Track nested parentheses
            if t.type == TokenType.OPEN_ROUND_BRACKET:
                depth += 1
            elif t.type == TokenType.CLOSE_ROUND_BRACKET:
                depth -= 1
            elif t.type == TokenType.COMMA and depth == 0:
                columns += 1
            # Stop at FROM clause
            elif t.value.upper() == "FROM" and depth == 0:
                break

            pos += 1

        return columns

    def _count_left_columns(self, tokens, in_pos):
        """Count columns on left side of IN/NOT IN."""
        # Look backwards from IN position
        pos = in_pos - 1

        # Skip whitespace
        while pos >= 0 and tokens[pos].type == TokenType.WHITESPACE:
            pos -= 1

        if pos < 0:
            return 0

        # Skip NOT keyword if present (for NOT IN)
        if tokens[pos].type == TokenType.KEYWORD and tokens[pos].value.upper() == "NOT":
            pos -= 1
            # Skip whitespace again
            while pos >= 0 and tokens[pos].type == TokenType.WHITESPACE:
                pos -= 1

        if pos < 0:
            return 0

        # Check if left side is wrapped in parentheses (tuple)
        if tokens[pos].type == TokenType.CLOSE_ROUND_BRACKET:
            # Save close bracket position before scanning backwards
            close_bracket_pos = pos

            # Find matching open bracket
            depth = 1
            pos -= 1
            while pos >= 0 and depth > 0:
                if tokens[pos].type == TokenType.CLOSE_ROUND_BRACKET:
                    depth += 1
                elif tokens[pos].type == TokenType.OPEN_ROUND_BRACKET:
                    depth -= 1
                pos -= 1

            # pos+1 is at the opening bracket; iterate strictly between brackets
            open_pos = pos + 1

            # Count commas at depth 0 inside the tuple (exclude both brackets)
            columns = 1
            depth = 0
            for j in range(open_pos + 1, close_bracket_pos):
                t = tokens[j]
                if t.type == TokenType.OPEN_ROUND_BRACKET:
                    depth += 1
                elif t.type == TokenType.CLOSE_ROUND_BRACKET:
                    depth -= 1
                elif t.type == TokenType.COMMA and depth == 0:
                    columns += 1

            return columns
        else:
            # Single expression
            return 1

    def _check_decimal_type_consistency(self, tokens):
        """SPEC034: Check Decimal type consistency in coalesce/ifNull/nullIf."""
        import re
        type_sensitive_funcs = {"COALESCE", "IFNULL", "NULLIF"}

        for i, t in enumerate(tokens):
            if (t.type in (TokenType.BARE_WORD, TokenType.KEYWORD) and
                    t.value.upper() in type_sensitive_funcs):
                # Found a type-sensitive function, find its scope
                func_name = t.value.upper()
                func_line, func_col = t.line, t.column

                # Find opening paren
                start = i + 1
                while start < len(tokens) and tokens[start].type != TokenType.OPEN_ROUND_BRACKET:
                    start += 1
                if start >= len(tokens):
                    continue

                # Find matching close paren
                depth = 1
                end = start + 1
                while end < len(tokens) and depth > 0:
                    if tokens[end].type == TokenType.OPEN_ROUND_BRACKET:
                        depth += 1
                    elif tokens[end].type == TokenType.CLOSE_ROUND_BRACKET:
                        depth -= 1
                    end += 1

                # Extract Decimal types from CAST expressions within scope
                decimal_types = []
                j = start + 1
                while j < end - 1:
                    tok_j = tokens[j]
                    if (tok_j.type in (TokenType.BARE_WORD, TokenType.KEYWORD) and
                            tok_j.value.upper() == "CAST"):
                        # Find the CAST's opening paren
                        cast_start = j + 1
                        while cast_start < end and tokens[cast_start].type != TokenType.OPEN_ROUND_BRACKET:
                            cast_start += 1
                        if cast_start >= end:
                            j += 1
                            continue

                        # Find CAST's matching close paren
                        cast_depth = 1
                        cast_end = cast_start + 1
                        while cast_end < end and cast_depth > 0:
                            if tokens[cast_end].type == TokenType.OPEN_ROUND_BRACKET:
                                cast_depth += 1
                            elif tokens[cast_end].type == TokenType.CLOSE_ROUND_BRACKET:
                                cast_depth -= 1
                            cast_end += 1

                        # Find AS keyword within CAST scope
                        k = cast_start + 1
                        while k < cast_end - 1:
                            if tokens[k].value.upper() == "AS":
                                # Collect all tokens after AS until CAST's close paren
                                type_tokens = []
                                m = k + 1
                                while m < cast_end - 1:
                                    type_tokens.append(tokens[m].value)
                                    m += 1
                                if type_tokens:
                                    type_str = ''.join(type_tokens)
                                    # Match Decimal patterns: Decimal(p,s), Decimal64(s), etc.
                                    match = re.match(
                                        r'(Decimal(?:32|64|128|256)?)\s*\(\s*(\d+)\s*'
                                        r'(?:,\s*(\d+)\s*)?\)',
                                        type_str, re.IGNORECASE)
                                    if match:
                                        base = match.group(1).lower()
                                        prec = int(match.group(2))
                                        scale = int(match.group(3)) if match.group(3) else 0
                                        # For Decimal32/64/128/256, first param is scale
                                        if base in ("decimal32", "decimal64",
                                                    "decimal128", "decimal256"):
                                            scale = prec
                                            prec = None
                                        decimal_types.append(
                                            (type_str, prec, scale,
                                             tokens[k + 1].line, tokens[k + 1].column))
                                break
                            k += 1
                        j = cast_end
                    else:
                        j += 1

                # If multiple different Decimal types found, flag it
                if len(decimal_types) >= 2:
                    scales = {dt[2] for dt in decimal_types}
                    bases = {dt[0].lower() for dt in decimal_types}
                    if len(scales) > 1 or len(bases) > 1:
                        type_descs = [f"{dt[0]}" for dt in decimal_types]
                        snippet = f"{func_name}(... {', '.join(type_descs)} ...)"
                        self.violations.append(Violation(
                            **make_violation("SPEC034", line=func_line,
                                             column=func_col,
                                             sql_snippet=snippet)))

                # Heuristic: if there's at least one CAST to Decimal and other column references
                elif len(decimal_types) >= 1:
                    # Check if there are column references (BARE_WORD tokens not inside CAST)
                    has_column_ref = False
                    arg_depth = 1  # Start at 1 because we're already inside the function's parens
                    in_cast = False
                    for k in range(start + 1, end):
                        tok_k = tokens[k]
                        if tok_k.type == TokenType.OPEN_ROUND_BRACKET:
                            arg_depth += 1
                            # Check if this is a CAST opening paren
                            if k > 0 and tokens[k-1].value.upper() == "CAST":
                                in_cast = True
                        elif tok_k.type == TokenType.CLOSE_ROUND_BRACKET:
                            arg_depth -= 1
                            if arg_depth == 0:
                                in_cast = False
                        # Column reference: BARE_WORD at depth 1, not inside CAST, not a keyword
                        elif (tok_k.type == TokenType.BARE_WORD and
                              arg_depth == 1 and
                              not in_cast and
                              not tok_k.is_keyword and
                              tok_k.value.upper() not in ("CAST", "AS")):
                            has_column_ref = True
                            break

                    if has_column_ref:
                        type_descs = [f"{dt[0]}" for dt in decimal_types]
                        snippet = f"{func_name}(... column_ref, {', '.join(type_descs)} ...)"
                        self.violations.append(Violation(
                            **make_violation("SPEC034", line=func_line,
                                             column=func_col,
                                             sql_snippet=snippet)))

    def _generate_report(self):
        """Generate the check report as a dict."""
        errors = sum(1 for v in self.violations if v.level == "ERROR")
        warnings = sum(1 for v in self.violations if v.level == "WARNING")
        infos = sum(1 for v in self.violations if v.level == "INFO")

        # Split violations by category
        syntax_violations = [v for v in self.violations if v.category == "Syntax"]
        spec_violations = [v for v in self.violations if v.category != "Syntax"]

        total_rules = self.TOTAL_SYNTAX_RULES
        if self.check_mode in ("spec", "all"):
            total_rules += self.TOTAL_SPEC_RULES
        passed = max(0, total_rules - len(self.violations))

        return {
            "check_time": datetime.now().isoformat(),
            "ck_version": self.version,
            "statement_type": self.statement_type,
            "check_mode": self.check_mode,
            "summary": {
                "total_rules": total_rules,
                "passed": max(0, passed),
                "violations": len(self.violations),
                "errors": errors,
                "warnings": warnings,
                "infos": infos,
            },
            "syntax_violations": [v.to_dict() for v in syntax_violations],
            "spec_violations": [v.to_dict() for v in spec_violations],
            "violations": [v.to_dict() for v in self.violations],
            "sql_text": self.sql_text,
        }


# =============================================================================
# Markdown Report Generator
# =============================================================================
def check_sql_markdown(sql_text, check_mode="syntax", version=DEFAULT_VERSION):
    """Check SQL and return a Markdown format report."""
    checker = ClickHouseSQLChecker(sql_text, check_mode, version)
    report = checker.check()

    lines = []
    lines.append("# ClickHouse SQL 检查报告")
    lines.append("")
    lines.append(f"**检查时间**: {report['check_time']}")
    lines.append(f"**ClickHouse 版本**: {report['ck_version']}")
    lines.append(f"**语句类型**: {report['statement_type']}")
    lines.append(f"**检查模式**: {report['check_mode']}")
    lines.append("")

    # Summary
    s = report["summary"]
    lines.append("## 检查概要")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|------|")
    lines.append(f"| 检查规则数 | {s['total_rules']} |")
    lines.append(f"| 通过 | {s['passed']} |")
    lines.append(f"| 违规 | {s['violations']} |")
    lines.append(f"| 错误 (ERROR) | {s['errors']} |")
    lines.append(f"| 警告 (WARNING) | {s['warnings']} |")
    lines.append(f"| 提示 (INFO) | {s['infos']} |")
    lines.append("")

    # Violations - split by category
    syntax_vios = report.get("syntax_violations", [])
    spec_vios = report.get("spec_violations", [])

    def _render_violation(v):
        icon = "X" if v["level"] == "ERROR" else ("!" if v["level"] == "WARNING" else "i")
        lines.append(f"### [{icon}] {v['rule_id']}: {v['rule_name']}")
        lines.append("")
        lines.append(f"- **级别**: {v['level']}")
        lines.append(f"- **类别**: {v.get('category', '')}")
        lines.append(f"- **位置**: 行 {v['line']}, 列 {v['column']}")
        lines.append(f"- **描述**: {v['message']}")
        if v.get("sql_snippet"):
            lines.append(f"- **代码片段**: `{v['sql_snippet']}`")
        if v.get("fix_suggestion"):
            lines.append(f"- **修复建议**: {v['fix_suggestion']}")
        lines.append("")

    # Syntax section
    lines.append("## 语法检查")
    lines.append("")
    if syntax_vios:
        for v in syntax_vios:
            _render_violation(v)
    else:
        lines.append("✅ 未发现语法违规。")
        lines.append("")

    # Spec section (only show if spec/all mode)
    if report["check_mode"] in ("spec", "all"):
        lines.append("## 规范检查")
        lines.append("")
        if spec_vios:
            for v in spec_vios:
                _render_violation(v)
        else:
            lines.append("✅ 未发现规范违规。")
            lines.append("")

    # Original SQL
    lines.append("## 原始 SQL")
    lines.append("")
    lines.append("```sql")
    lines.append(report["sql_text"])
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================
def check_sql(sql_text, check_mode="syntax", version=DEFAULT_VERSION):
    """Check SQL and return the report as a dict."""
    checker = ClickHouseSQLChecker(sql_text, check_mode, version)
    return checker.check()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python ck_sql_checker.py "<sql_text>" [syntax|spec|all] [version]')
        print(f'  version: ClickHouse kernel version. Supported: {", ".join(get_supported_versions())}')
        print(f'  default version: {DEFAULT_VERSION}')
        print('Example: python ck_sql_checker.py "SELECT * FROM t1" syntax 24.8')
        sys.exit(1)

    sql_text = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "syntax"
    version = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VERSION

    if version not in get_supported_versions():
        print(f'Error: unsupported version "{version}". Supported: {", ".join(get_supported_versions())}')
        sys.exit(1)

    report = check_sql(sql_text, mode, version)
    print(json.dumps(report, indent=2, ensure_ascii=False))
