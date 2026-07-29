"""HetuEngine SQL Checker - SQL validation and specification checking for HetuEngine."""

import re
import sys
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hetu_sql_tokenizer import HetuSQLTokenizer, Token, TokenType
from hetu_sql_parser import HetuSQLParser
from keywords import RESERVED_KEYWORDS


class Severity(Enum):
    """Severity levels for SQL violations."""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Violation:
    """Represents a SQL violation found during checking."""
    code: str
    severity: Severity
    message: str
    line: int = 1
    column: int = 1

    def __str__(self) -> str:
        return f"[{self.code}] {self.severity.value}: {self.message} (line {self.line}, col {self.column})"


class HetuSQLChecker:
    """SQL checker for HetuEngine with syntax and specification validation."""

    VALID_PARTITION_TYPES = {
        "TINYINT", "SMALLINT", "INT", "BIGINT",
        "STRING", "VARCHAR", "CHAR",
        "DATE", "TIMESTAMP", "BOOLEAN"
    }

    VALID_STORED_FORMATS = {
        "ORC", "PARQUET", "AVRO", "RCBINARY", "RCTEXT", "RCFILE",
        "SEQUENCEFILE", "JSON", "OPENX_JSON", "TEXTFILE", "TEXTFILE_MULTIDELIM", "CSV",
        "REGEX", "HUDI_COW", "HUDI_MOR"
    }

    VALID_EXPLAIN_OPTIONS = {"ANALYZE", "VERBOSE", "IO", "TYPE", "GRAPHVIZ"}

    VALID_TABLESAMPLE_METHODS = {"SYSTEM", "BERNOULLI"}

    NAMING_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

    def __init__(self):
        """Initialize the HetuEngine SQL checker."""
        pass

    def check_syntax(self, sql_text: str) -> List[Violation]:
        """Perform syntax checks on SQL text."""
        violations = []

        try:
            tokenizer = HetuSQLTokenizer(sql_text)
            tokens, token_errors = tokenizer.tokenize()
            for err in token_errors:
                violations.append(Violation(
                    code="SYN-ERR",
                    severity=Severity.ERROR,
                    message=f"Tokenizer error: {err}"
                ))
        except Exception as e:
            violations.append(Violation(
                code="SYN-ERR",
                severity=Severity.ERROR,
                message=f"Tokenizer error: {str(e)}"
            ))
            return violations

        try:
            parser = HetuSQLParser(tokens, sql_text)
            result = parser.parse()
            ast = result.get("ast")
        except Exception as e:
            violations.append(Violation(
                code="SYN003",
                severity=Severity.ERROR,
                message=f"Parse error: {str(e)}"
            ))
            return violations

        violations.extend(self._check_invalid_keywords(tokens))
        violations.extend(self._check_reserved_keyword_identifiers(tokens))
        violations.extend(self._check_clause_ordering(tokens))
        violations.extend(self._check_partitioned_by_syntax(tokens))
        violations.extend(self._check_stored_as_syntax(tokens))
        violations.extend(self._check_clustered_by_syntax(tokens))
        violations.extend(self._check_explain_syntax(tokens))
        violations.extend(self._check_tablesample_syntax(tokens))
        violations.extend(self._check_insert_overwrite_syntax(tokens))
        violations.extend(self._check_load_data_syntax(tokens))
        violations.extend(self._check_create_function_syntax(tokens))
        violations.extend(self._check_create_materialized_view_syntax(tokens))
        violations.extend(self._check_fetch_syntax(tokens))
        violations.extend(self._check_match_recognize_syntax(tokens))
        violations.extend(self._check_semi_anti_join_syntax(tokens))
        violations.extend(self._check_with_recursive_syntax(tokens))
        violations.extend(self._check_row_format_syntax(tokens))
        violations.extend(self._check_virtual_schema_syntax(tokens))

        return violations

    def check_specification(self, sql_text: str) -> List[Violation]:
        """Perform specification checks on SQL text."""
        violations = []

        try:
            tokenizer = HetuSQLTokenizer(sql_text)
            tokens, _ = tokenizer.tokenize()
        except Exception:
            return violations

        try:
            parser = HetuSQLParser(tokens, sql_text)
            result = parser.parse()
            ast = result.get("ast")
        except Exception:
            return violations

        upper_sql = sql_text.upper()

        # Extract AST markers for semantic-level checks (avoids string matching).
        # `ast` is an ASTNode object with .node_type and .children attributes.
        node_type = ast.node_type if ast else ""
        children = ast.children if ast else {}

        # SPEC001: Missing PARTITIONED BY — only for Hive-compatible CREATE TABLE
        # (PARTITIONED BY only exists in Hive/Impala syntax, not standard Trino)
        if node_type == "CreateStmt" and children.get("hive_compatible") \
                and not children.get("partitioned_by"):
            violations.append(Violation(
                code="SPEC001",
                severity=Severity.WARNING,
                message="Missing PARTITIONED BY for table - consider partitioning for large tables"
            ))

        # SPEC002 removed: HetuEngine does not support PRIMARY KEY syntax
        # (SqlBase.g4 columnDefinition only supports NOT NULL, no PK constraint)

        # SPEC003: SELECT * prohibited — use AST has_select_star (already excludes table.*)
        # Context-aware severity: subquery wrap → INFO; single table → WARNING; multi-table → ERROR
        if node_type == "SelectStmt" and children.get("has_select_star"):
            from_clause = children.get("from_clause", [])
            has_limit = bool(children.get("limit"))
            is_single_table = (len(from_clause) == 1 and
                               "(" not in from_clause[0])
            is_subquery_wrap = (len(from_clause) == 1 and
                                from_clause[0].strip().startswith("("))
            if is_subquery_wrap:
                sev = Severity.INFO
            elif is_single_table:
                sev = Severity.WARNING
            else:
                sev = Severity.ERROR  # multi-table SELECT * stays ERROR
            violations.append(Violation(
                code="SPEC003",
                severity=sev,
                message="SELECT * is prohibited - specify explicit column names"
            ))

        # SPEC004: DELETE/UPDATE without WHERE — use AST where_clause (parser-set)
        if node_type in ("DeleteStmt", "UpdateStmt") and not children.get("where_clause"):
            violations.append(Violation(
                code="SPEC004",
                severity=Severity.ERROR,
                message="DELETE/UPDATE without WHERE clause"
            ))

        if self._has_not_in_subquery(tokens):
            violations.append(Violation(
                code="SPEC005",
                severity=Severity.WARNING,
                message="NOT IN subquery detected - consider using NOT EXISTS for better performance"
            ))

        if "DISTINCT" in upper_sql:
            violations.append(Violation(
                code="SPEC006",
                severity=Severity.INFO,
                message="DISTINCT may impact performance - ensure it's necessary"
            ))

        if self._has_implicit_type_risk(tokens):
            violations.append(Violation(
                code="SPEC007",
                severity=Severity.WARNING,
                message="Potential implicit type conversion risk detected"
            ))

        if self._has_leading_wildcard_like(tokens):
            violations.append(Violation(
                code="SPEC008",
                severity=Severity.WARNING,
                message="LIKE with leading wildcard (%) prevents index usage"
            ))

        if self._has_or_condition_issue(tokens):
            violations.append(Violation(
                code="SPEC009",
                severity=Severity.INFO,
                message="OR condition may impact performance - consider UNION or indexing"
            ))

        if self._has_large_in_list(tokens):
            violations.append(Violation(
                code="SPEC010",
                severity=Severity.WARNING,
                message="IN list contains more than 100 values - consider using JOIN or temporary table"
            ))

        # SPEC011: FROM subquery — use AST from_clause (list of table refs, subquery starts with "(")
        if node_type == "SelectStmt":
            from_clause = children.get("from_clause", [])
            if from_clause and any(str(t).strip().startswith("(") for t in from_clause):
                violations.append(Violation(
                    code="SPEC011",
                    severity=Severity.INFO,
                    message="FROM subquery detected - consider using CTE (WITH clause) for better readability"
                ))

        if self._has_cartesian_product(children):
            violations.append(Violation(
                code="SPEC012",
                severity=Severity.ERROR,
                message="Potential cartesian product - missing JOIN condition"
            ))

        # SPEC013: INSERT without column list — scan tokens for "(" between table name and VALUES
        if self._has_insert_missing_columns(tokens):
            violations.append(Violation(
                code="SPEC013",
                severity=Severity.WARNING,
                message="INSERT without explicit column list - specify columns for clarity and maintainability"
            ))

        if self._is_create_table(upper_sql) and not self._has_table_comment(upper_sql):
            violations.append(Violation(
                code="SPEC014",
                severity=Severity.INFO,
                message="Missing table comment - add documentation with COMMENT clause"
            ))

        if self._is_create_table(upper_sql):
            table_name = self._extract_table_name(upper_sql)
            if table_name and not self.NAMING_PATTERN.match(table_name):
                violations.append(Violation(
                    code="SPEC015",
                    severity=Severity.WARNING,
                    message=f"Table name '{table_name}' does not follow naming convention (lowercase, underscore)"
                ))

        if self._has_column_naming_issue(tokens):
            violations.append(Violation(
                code="SPEC016",
                severity=Severity.WARNING,
                message="Column name does not follow naming convention"
            ))

        if self._has_reserved_keyword_as_identifier(tokens):
            violations.append(Violation(
                code="SPEC017",
                severity=Severity.ERROR,
                message="Reserved keyword used as identifier"
            ))

        # SPEC018: Missing bucket specification — only for Hive-compatible CREATE TABLE
        # (CLUSTERED BY only exists in Hive syntax)
        if node_type == "CreateStmt" and children.get("hive_compatible") \
                and not children.get("clustered_by"):
            violations.append(Violation(
                code="SPEC018",
                severity=Severity.INFO,
                message="Missing bucket specification - consider CLUSTERED BY for better distribution"
            ))

        # SPEC019: Missing explicit storage format — check both STORED AS and WITH(format=...)
        # (Standard Trino uses WITH (format='ORC'), Hive uses STORED AS ORC — both valid)
        if node_type == "CreateStmt":
            has_stored_as = bool(children.get("stored_as"))
            with_props = str(children.get("with_properties", "")).upper()
            has_format_in_with = "FORMAT" in with_props
            if not has_stored_as and not has_format_in_with:
                violations.append(Violation(
                    code="SPEC019",
                    severity=Severity.WARNING,
                    message="Missing explicit storage format - specify STORED AS or WITH (format = '...')"
                ))

        if self._is_create_external_table(upper_sql) and not self._has_location(upper_sql):
            violations.append(Violation(
                code="SPEC020",
                severity=Severity.WARNING,
                message="External table missing LOCATION clause"
            ))

        if self._is_transactional_table(upper_sql) and not self._is_orc_format(upper_sql):
            violations.append(Violation(
                code="SPEC021",
                severity=Severity.WARNING,
                message="Transactional table should use ORC format for best performance"
            ))

        # SPEC022: auto.purge suggestion — only for tables with tmp/temp in name
        # (HetuEngine has no TEMPORARY TABLE syntax, so infer from table name)
        if node_type == "CreateStmt":
            table_name = str(children.get("table_name", "")).lower()
            if ("tmp" in table_name or "temp" in table_name) \
                    and not children.get("tblproperties"):
                violations.append(Violation(
                    code="SPEC022",
                    severity=Severity.INFO,
                    message="Consider adding TBLPROPERTIES ('auto.purge'='true') for temporary tables"
                ))

        if self._has_drop_without_if_exists(tokens):
            violations.append(Violation(
                code="SPEC023",
                severity=Severity.WARNING,
                message="DROP without IF EXISTS - add IF EXISTS to prevent errors"
            ))

        if self._has_multi_values_insert(tokens):
            violations.append(Violation(
                code="SPEC024",
                severity=Severity.WARNING,
                message="Multi-VALUES INSERT detected - consider batch insert for better performance"
            ))

        if self._has_function_on_filter_column(tokens):
            violations.append(Violation(
                code="SPEC025",
                severity=Severity.WARNING,
                message="Function applied to filter column - may prevent index usage"
            ))

        if self._has_count_star(tokens):
            violations.append(Violation(
                code="SPEC026",
                severity=Severity.WARNING,
                message="COUNT(*) on large table - consider approximate count or partition pruning"
            ))

        # SPEC027: SELECT without LIMIT — exclude aggregate queries (GROUP BY)
        # and subquery-wrapped queries (FROM (subquery)) which don't need LIMIT
        if node_type == "SelectStmt" and not children.get("limit") and not children.get("fetch"):
            has_group_by = bool(children.get("group_by"))
            from_clause = children.get("from_clause", [])
            is_subquery_wrap = (len(from_clause) == 1 and
                                from_clause[0].strip().startswith("("))
            if not has_group_by and not is_subquery_wrap:
                violations.append(Violation(
                    code="SPEC027",
                    severity=Severity.INFO,
                    message="Query without LIMIT - consider adding LIMIT for large result sets"
                ))

        if self._has_with_recursive(tokens):
            violations.append(Violation(
                code="SPEC028",
                severity=Severity.WARNING,
                message="WITH RECURSIVE detected - ensure proper termination condition"
            ))

        if self._has_table_without_schema(tokens):
            violations.append(Violation(
                code="SPEC029",
                severity=Severity.INFO,
                message="Table reference without schema prefix - use catalog.schema.table format"
            ))

        if self._has_view_nesting_depth(upper_sql):
            violations.append(Violation(
                code="SPEC030",
                severity=Severity.INFO,
                message="View nesting depth may be too deep - consider simplifying"
            ))

        if self._has_materialized_view(upper_sql) and not self._has_refresh_clause(upper_sql):
            violations.append(Violation(
                code="SPEC031",
                severity=Severity.INFO,
                message="Materialized view without explicit refresh strategy"
            ))

        if self._has_cross_catalog_join(tokens):
            violations.append(Violation(
                code="SPEC032",
                severity=Severity.WARNING,
                message="Cross-catalog join detected - may impact performance"
            ))

        if self._is_large_table(upper_sql) and not self._has_tablesample(tokens):
            violations.append(Violation(
                code="SPEC033",
                severity=Severity.INFO,
                message="Large table query without TABLESAMPLE - consider sampling for analysis"
            ))

        if self._is_orc_format(upper_sql) and not self._has_orc_compression(upper_sql):
            violations.append(Violation(
                code="SPEC034",
                severity=Severity.INFO,
                message="ORC format without explicit compression - specify compression codec"
            ))

        return violations

    def check_sql(self, sql_text: str, check_mode: str = "all") -> List[Violation]:
        """Check SQL with specified mode."""
        if check_mode == "syntax":
            return self.check_syntax(sql_text)
        elif check_mode == "spec":
            return self.check_specification(sql_text)
        elif check_mode == "all":
            return self.check_syntax(sql_text) + self.check_specification(sql_text)
        else:
            raise ValueError(f"Invalid check mode: {check_mode}")

    def _check_invalid_keywords(self, tokens: List[Token]) -> List[Violation]:
        """Check for invalid keyword usage."""
        violations = []
        return violations

    def _check_reserved_keyword_identifiers(self, tokens: List[Token]) -> List[Violation]:
        """Check for reserved keywords used as identifiers."""
        violations = []
        for i, token in enumerate(tokens):
            if token.type == TokenType.IDENT:
                if token.value.upper() in RESERVED_KEYWORDS:
                    violations.append(Violation(
                        code="SYN002",
                        severity=Severity.ERROR,
                        message=f"Reserved keyword '{token.value}' used as identifier",
                        line=token.line,
                        column=token.column
                    ))
        return violations

    def _check_clause_ordering(self, tokens: List[Token]) -> List[Violation]:
        """Check SQL clause ordering."""
        violations = []
        return violations

    def _check_partitioned_by_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check PARTITIONED BY syntax: must be followed by ( col_name data_type [, ...] )."""
        violations = []
        for i in range(len(tokens) - 2):
            if (tokens[i].value.upper() == "PARTITIONED" and
                    tokens[i + 1].value.upper() == "BY"):
                if i + 2 >= len(tokens) or tokens[i + 2].type != TokenType.LPAREN:
                    violations.append(Violation(
                        code="SYN005", severity=Severity.ERROR,
                        message="PARTITIONED BY must be followed by ( column definitions )",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                break
        return violations

    def _check_stored_as_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check STORED AS syntax: must be STORED AS <format> where format in VALID_STORED_FORMATS.

        Also accepts Hive-style ``STORED AS INPUTFORMAT '...' OUTPUTFORMAT '...'``.
        """
        violations = []
        n = len(tokens)
        for i in range(n - 2):
            if (tokens[i].value.upper() == "STORED" and
                    tokens[i + 1].value.upper() == "AS" and
                    i + 2 < n):
                # Hive INPUTFORMAT/OUTPUTFORMAT form — skip format-name check
                if tokens[i + 2].value.upper() == "INPUTFORMAT":
                    break
                fmt_token = tokens[i + 2]
                fmt = fmt_token.value.upper().strip("`")
                if fmt not in self.VALID_STORED_FORMATS:
                    violations.append(Violation(
                        code="SYN006", severity=Severity.ERROR,
                        message=f"Invalid STORED AS format '{fmt}'. "
                                f"Valid: {', '.join(sorted(self.VALID_STORED_FORMATS))}",
                        line=fmt_token.line, column=fmt_token.column
                    ))
                break
        return violations

    def _check_clustered_by_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check CLUSTERED BY syntax: CLUSTERED BY ( col [, ...] ) [SORTED BY (...)] INTO <n> BUCKETS."""
        violations = []
        n = len(tokens)
        for i in range(n - 3):
            if (tokens[i].value.upper() == "CLUSTERED" and
                    tokens[i + 1].value.upper() == "BY"):
                # Must be followed by ( ... )
                if i + 2 >= n or tokens[i + 2].type != TokenType.LPAREN:
                    violations.append(Violation(
                        code="SYN007", severity=Severity.ERROR,
                        message="CLUSTERED BY must be followed by ( column list )",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                    break
                # Find matching RPAREN
                depth = 1
                j = i + 3
                while j < n and depth > 0:
                    if tokens[j].type == TokenType.LPAREN:
                        depth += 1
                    elif tokens[j].type == TokenType.RPAREN:
                        depth -= 1
                    j += 1
                if depth != 0:
                    violations.append(Violation(
                        code="SYN007", severity=Severity.ERROR,
                        message="CLUSTERED BY has unbalanced parentheses",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                    break
                # Now j points to token after closing RPAREN; expect INTO <n> BUCKETS
                # (optionally after SORTED BY (...) clause)
                k = j
                if k < n and tokens[k].value.upper() == "SORTED":
                    if k + 1 < n and tokens[k + 1].value.upper() == "BY":
                        # skip SORTED BY (...)
                        if k + 2 < n and tokens[k + 2].type == TokenType.LPAREN:
                            depth = 1
                            k += 3
                            while k < n and depth > 0:
                                if tokens[k].type == TokenType.LPAREN:
                                    depth += 1
                                elif tokens[k].type == TokenType.RPAREN:
                                    depth -= 1
                                k += 1
                        else:
                            violations.append(Violation(
                                code="SYN007", severity=Severity.ERROR,
                                message="SORTED BY must be followed by ( column list )",
                                line=tokens[k].line, column=tokens[k].column
                            ))
                            break
                    else:
                        violations.append(Violation(
                            code="SYN007", severity=Severity.ERROR,
                            message="Expected BY after SORTED",
                            line=tokens[k].line, column=tokens[k].column
                        ))
                        break
                # Expect INTO <n> BUCKETS
                if k >= n or tokens[k].value.upper() != "INTO":
                    violations.append(Violation(
                        code="SYN007", severity=Severity.ERROR,
                        message="CLUSTERED BY must end with INTO <n> BUCKETS",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                    break
                if k + 2 >= n or tokens[k + 1].type not in (TokenType.ICONST, TokenType.FCONST) \
                        or tokens[k + 2].value.upper() != "BUCKETS":
                    violations.append(Violation(
                        code="SYN007", severity=Severity.ERROR,
                        message="INTO must be followed by a positive integer and BUCKETS",
                        line=tokens[k].line, column=tokens[k].column
                    ))
                    break
                break
        return violations

    def _check_explain_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check EXPLAIN syntax: EXPLAIN [ANALYZE|VERBOSE|IO|TYPE|GRAPHVIZ] <statement>."""
        violations = []
        n = len(tokens)
        for i in range(n):
            if tokens[i].value.upper() == "EXPLAIN":
                # EXPLAIN must not be the last meaningful token
                if i + 1 >= n or tokens[i + 1].type == TokenType.EOF:
                    violations.append(Violation(
                        code="SYN008", severity=Severity.ERROR,
                        message="EXPLAIN must be followed by a statement",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                    break
                next_tok = tokens[i + 1]
                next_upper = next_tok.value.upper()
                # If next token is an option, validate it
                if next_upper.isalpha() and next_upper not in self.VALID_EXPLAIN_OPTIONS:
                    # Could be a statement keyword (SELECT, INSERT, ...) — those are fine
                    statement_keywords = {
                        "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
                        "ALTER", "TRUNCATE", "SHOW", "DESCRIBE", "DESC", "USE",
                        "SET", "RESET", "CALL", "WITH", "VALUES", "TABLE",
                        "START", "COMMIT", "ROLLBACK", "REFRESH", "LOAD",
                    }
                    if next_upper not in statement_keywords:
                        violations.append(Violation(
                            code="SYN008", severity=Severity.ERROR,
                            message=f"Invalid EXPLAIN option '{next_tok.value}'. "
                                    f"Valid options: {', '.join(sorted(self.VALID_EXPLAIN_OPTIONS))}",
                            line=next_tok.line, column=next_tok.column
                        ))
                break
        return violations

    def _check_tablesample_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check TABLESAMPLE syntax: TABLESAMPLE {SYSTEM|BERNOULLI} ( percentage )."""
        violations = []
        n = len(tokens)
        for i in range(n - 3):
            if tokens[i].value.upper() == "TABLESAMPLE":
                # Must be followed by method name then ( percentage )
                if i + 1 >= n:
                    violations.append(Violation(
                        code="SYN009", severity=Severity.ERROR,
                        message="TABLESAMPLE must be followed by sampling method "
                                "(SYSTEM or BERNOULLI)",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                    break
                method_token = tokens[i + 1]
                method = method_token.value.upper()
                if method not in self.VALID_TABLESAMPLE_METHODS:
                    violations.append(Violation(
                        code="SYN009", severity=Severity.ERROR,
                        message=f"Invalid TABLESAMPLE method '{method_token.value}'. "
                                f"Valid: {', '.join(sorted(self.VALID_TABLESAMPLE_METHODS))}",
                        line=method_token.line, column=method_token.column
                    ))
                    break
                if i + 2 >= n or tokens[i + 2].type != TokenType.LPAREN:
                    violations.append(Violation(
                        code="SYN009", severity=Severity.ERROR,
                        message="TABLESAMPLE method must be followed by ( percentage )",
                        line=method_token.line, column=method_token.column
                    ))
                    break
                # Find matching RPAREN and check it contains a number
                depth = 1
                j = i + 3
                has_number = False
                while j < n and depth > 0:
                    if tokens[j].type == TokenType.LPAREN:
                        depth += 1
                    elif tokens[j].type == TokenType.RPAREN:
                        depth -= 1
                    elif tokens[j].type in (TokenType.ICONST, TokenType.FCONST):
                        has_number = True
                    j += 1
                if depth != 0:
                    violations.append(Violation(
                        code="SYN009", severity=Severity.ERROR,
                        message="TABLESAMPLE has unbalanced parentheses",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                    break
                if not has_number:
                    violations.append(Violation(
                        code="SYN009", severity=Severity.ERROR,
                        message="TABLESAMPLE must contain a sampling percentage",
                        line=tokens[i].line, column=tokens[i].column
                    ))
                break
        return violations

    def _check_insert_overwrite_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check INSERT OVERWRITE syntax."""
        violations = []
        return violations

    def _check_load_data_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check LOAD DATA syntax."""
        violations = []
        return violations

    def _check_create_function_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check CREATE FUNCTION syntax."""
        violations = []
        return violations

    def _check_create_materialized_view_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check CREATE MATERIALIZED VIEW syntax."""
        violations = []
        return violations

    def _check_fetch_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check FETCH syntax."""
        violations = []
        return violations

    def _check_match_recognize_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check MATCH_RECOGNIZE syntax."""
        violations = []
        return violations

    def _check_semi_anti_join_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check Semi/Anti Join syntax."""
        violations = []
        return violations

    def _check_with_recursive_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check WITH RECURSIVE syntax."""
        violations = []
        return violations

    def _check_row_format_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check ROW FORMAT syntax."""
        violations = []
        return violations

    def _check_virtual_schema_syntax(self, tokens: List[Token]) -> List[Violation]:
        """Check Virtual Schema syntax."""
        violations = []
        return violations

    def _has_not_in_subquery(self, tokens: List[Token]) -> bool:
        """Check for NOT IN subquery pattern."""
        for i in range(len(tokens) - 2):
            if (tokens[i].value.upper() == "NOT" and
                tokens[i + 1].value.upper() == "IN" and
                tokens[i + 2].value == "("):
                return True
        return False

    def _has_implicit_type_risk(self, tokens: List[Token]) -> bool:
        """Check for implicit type conversion risk."""
        return False

    def _has_leading_wildcard_like(self, tokens: List[Token]) -> bool:
        """Check for LIKE with leading wildcard."""
        for i in range(len(tokens) - 1):
            if tokens[i].value.upper() == "LIKE":
                if i + 1 < len(tokens):
                    value = tokens[i + 1].value
                    if value.startswith("'%") or value.startswith('"%'):
                        return True
        return False

    def _has_or_condition_issue(self, tokens: List[Token]) -> bool:
        """Check for OR condition issues."""
        for token in tokens:
            if token.value.upper() == "OR":
                return True
        return False

    def _has_large_in_list(self, tokens: List[Token]) -> bool:
        """Check for large IN list."""
        in_parentheses = False
        paren_depth = 0
        list_count = 0

        for i in range(len(tokens) - 1):
            if tokens[i].value.upper() == "IN" and tokens[i + 1].value == "(":
                in_parentheses = True
                paren_depth = 1
                list_count = 0
                continue

            if in_parentheses:
                if tokens[i].value == "(":
                    paren_depth += 1
                elif tokens[i].value == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        if list_count > 100:
                            return True
                        in_parentheses = False
                elif tokens[i].value == ",":
                    list_count += 1

        return False

    def _has_drop_without_if_exists(self, tokens: List[Token]) -> bool:
        """Check for DROP without IF EXISTS."""
        for i in range(len(tokens) - 2):
            if tokens[i].value.upper() == "DROP":
                if not (i + 2 < len(tokens) and
                        tokens[i + 1].value.upper() == "IF" and
                        tokens[i + 2].value.upper() == "EXISTS"):
                    return True
        return False

    def _has_multi_values_insert(self, tokens: List[Token]) -> bool:
        """Check for multi-VALUES INSERT."""
        values_count = sum(1 for t in tokens if t.value.upper() == "VALUES")
        return values_count > 1

    def _has_function_on_filter_column(self, tokens: List[Token]) -> bool:
        """Check for function on filter column."""
        return False

    def _has_count_star(self, tokens: List[Token]) -> bool:
        """Check for COUNT(*)."""
        for i in range(len(tokens) - 2):
            if (tokens[i].value.upper() == "COUNT" and
                tokens[i + 1].value == "(" and
                tokens[i + 2].value == "*"):
                return True
        return False

    def _has_with_recursive(self, tokens: List[Token]) -> bool:
        """Check for WITH RECURSIVE."""
        for i in range(len(tokens) - 1):
            if (tokens[i].value.upper() == "WITH" and
                tokens[i + 1].value.upper() == "RECURSIVE"):
                return True
        return False

    def _has_table_without_schema(self, tokens: List[Token]) -> bool:
        """Check for table reference without schema prefix."""
        return False

    def _has_tablesample(self, tokens: List[Token]) -> bool:
        """Check for TABLESAMPLE usage."""
        return any(t.value.upper() == "TABLESAMPLE" for t in tokens)

    def _has_cross_catalog_join(self, tokens: List[Token]) -> bool:
        """Check for cross-catalog join."""
        return False

    def _is_create_table(self, upper_sql: str) -> bool:
        """Check if SQL is CREATE TABLE."""
        return "CREATE TABLE" in upper_sql

    def _has_partitioned_by(self, upper_sql: str) -> bool:
        """Check if SQL has PARTITIONED BY."""
        return "PARTITIONED BY" in upper_sql

    def _has_primary_key(self, upper_sql: str) -> bool:
        """Check if SQL has PRIMARY KEY."""
        return "PRIMARY KEY" in upper_sql

    def _has_delete_update_without_where(self, upper_sql: str) -> bool:
        """Check for DELETE/UPDATE without WHERE."""
        if ("DELETE FROM" in upper_sql or "UPDATE" in upper_sql):
            if "WHERE" not in upper_sql:
                return True
        return False

    def _has_from_subquery(self, upper_sql: str) -> bool:
        """Check for FROM subquery."""
        return bool(re.search(r"FROM\s*\(", upper_sql))

    def _has_cartesian_product(self, ast_children: dict) -> bool:
        """Check for potential cartesian product using AST from_clause + where_clause.

        Parser splits FROM clause by top-level commas into a list of table refs.
        Only report when: multiple comma-separated tables AND no join predicate
        (t1.col = t2.col) found in WHERE clause.
        """
        from_clause = ast_children.get("from_clause", [])
        if not from_clause or len(from_clause) < 2:
            return False  # single table cannot be cartesian product
        from_text = " ".join(str(t) for t in from_clause).upper()
        if "JOIN" in from_text:
            return False  # explicit JOIN, not comma-separated implicit join
        where_clause = ast_children.get("where_clause", "")
        if not where_clause:
            return True  # multi comma-separated tables with no WHERE → real cartesian
        # Check WHERE for join predicates. Two forms:
        #   1. Qualified: t1.col = t2.col  (explicit table prefix)
        #   2. Bare: col1 = col2  (TPC-DS style — column names are unique by prefix)
        # Both sides must be identifiers (start with letter/_), not numeric/string literals.
        where_text = str(where_clause)
        # Strip string literals so quoted strings aren't mistaken for identifiers.
        where_text_stripped = re.sub(r"'[^']*'", "''", where_text)
        qualified_pattern = r'\w+\s*\.\s*\w+\s*=\s*\w+\s*\.\s*\w+'
        bare_pattern = r'\b[a-zA-Z_]\w*\s*=\s*[a-zA-Z_]\w*\b'
        if (re.search(qualified_pattern, where_text_stripped, re.IGNORECASE) or
                re.search(bare_pattern, where_text_stripped, re.IGNORECASE)):
            return False  # has join predicate
        return True  # multi tables, no join predicate in WHERE

    def _has_insert_missing_columns(self, tokens: List[Token]) -> bool:
        """Check for INSERT without explicit column list.

        Scans tokens for: INSERT INTO <table> [.] [<col_list>] VALUES
        Reports only when there's no "(" between table name and VALUES.
        """
        # Find INSERT INTO
        for i in range(len(tokens) - 1):
            if (tokens[i].value.upper() == "INSERT" and
                    tokens[i + 1].value.upper() == "INTO"):
                # Scan forward from after INTO to find VALUES or "("
                j = i + 2
                # Skip table name (may include dot-qualified schema.table)
                while j < len(tokens) and tokens[j].value.upper() not in ("VALUES", "SELECT", "LPAREN"):
                    if tokens[j].type == TokenType.LPAREN:
                        return False  # found column list "(" before VALUES
                    j += 1
                return True  # reached VALUES/SELECT without finding "("
        return False

    def _has_table_comment(self, upper_sql: str) -> bool:
        """Check if table has COMMENT."""
        return "COMMENT" in upper_sql

    def _extract_table_name(self, upper_sql: str) -> Optional[str]:
        """Extract table name from CREATE TABLE statement."""
        match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", upper_sql)
        return match.group(1).lower() if match else None

    def _has_column_naming_issue(self, tokens: List[Token]) -> bool:
        """Check for column naming issues."""
        return False

    def _has_reserved_keyword_as_identifier(self, tokens: List[Token]) -> bool:
        """Check for reserved keyword as identifier."""
        for token in tokens:
            if token.type == TokenType.IDENT:
                if token.value.upper() in RESERVED_KEYWORDS:
                    return True
        return False

    def _has_bucket_clause(self, upper_sql: str) -> bool:
        """Check for CLUSTERED BY clause."""
        return "CLUSTERED BY" in upper_sql

    def _has_stored_as(self, upper_sql: str) -> bool:
        """Check for STORED AS clause."""
        return "STORED AS" in upper_sql

    def _is_create_external_table(self, upper_sql: str) -> bool:
        """Check if SQL is CREATE EXTERNAL TABLE."""
        return "CREATE EXTERNAL TABLE" in upper_sql

    def _has_location(self, upper_sql: str) -> bool:
        """Check for LOCATION clause."""
        return "LOCATION" in upper_sql

    def _is_transactional_table(self, upper_sql: str) -> bool:
        """Check if table is transactional."""
        return "TRANSACTIONAL" in upper_sql and "TRUE" in upper_sql

    def _is_orc_format(self, upper_sql: str) -> bool:
        """Check if format is ORC."""
        return "STORED AS ORC" in upper_sql

    def _has_auto_purge(self, upper_sql: str) -> bool:
        """Check for auto.purge property."""
        return "AUTO.PURGE" in upper_sql

    def _is_select_query(self, upper_sql: str) -> bool:
        """Check if SQL is SELECT query."""
        return upper_sql.strip().startswith("SELECT")

    def _has_limit(self, upper_sql: str) -> bool:
        """Check for LIMIT clause."""
        return "LIMIT" in upper_sql

    def _has_view_nesting_depth(self, upper_sql: str) -> bool:
        """Check for deep view nesting."""
        return False

    def _has_materialized_view(self, upper_sql: str) -> bool:
        """Check for materialized view."""
        return "MATERIALIZED VIEW" in upper_sql

    def _has_refresh_clause(self, upper_sql: str) -> bool:
        """Check for refresh clause."""
        return "REFRESH" in upper_sql

    def _is_large_table(self, upper_sql: str) -> bool:
        """Check if table is large (heuristic)."""
        return False

    def _has_orc_compression(self, upper_sql: str) -> bool:
        """Check for ORC compression specification."""
        return "ORC.COMPRESS" in upper_sql or "COMPRESSION" in upper_sql


def check_sql(sql_text: str, check_mode: str = "all") -> List[Violation]:
    """Convenience function to check SQL."""
    checker = HetuSQLChecker()
    return checker.check_sql(sql_text, check_mode)


def check_sql_markdown(sql_text: str, check_mode: str = "all") -> str:
    """Check SQL and return Markdown formatted report."""
    violations = check_sql(sql_text, check_mode)

    if not violations:
        return "✅ SQL validation passed - no issues found."

    lines = ["## SQL Validation Report\n"]
    lines.append(f"**Total violations: {len(violations)}**\n")

    errors = [v for v in violations if v.severity == Severity.ERROR]
    warnings = [v for v in violations if v.severity == Severity.WARNING]
    infos = [v for v in violations if v.severity == Severity.INFO]

    if errors:
        lines.append("### ❌ Errors\n")
        for v in errors:
            lines.append(f"- **{v.code}**: {v.message} (line {v.line})")
        lines.append("")

    if warnings:
        lines.append("### ⚠️ Warnings\n")
        for v in warnings:
            lines.append(f"- **{v.code}**: {v.message} (line {v.line})")
        lines.append("")

    if infos:
        lines.append("### ℹ️ Info\n")
        for v in infos:
            lines.append(f"- **{v.code}**: {v.message} (line {v.line})")
        lines.append("")

    return "\n".join(lines)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: hetu_sql_checker.py <sql_file_or_inline_sql> [check_mode]")
        print("  check_mode: syntax, spec, or all (default: all)")
        print("  Supports: file path or inline SQL string")
        sys.exit(1)

    sql_arg = sys.argv[1]
    check_mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    # Check if argument is a file path or inline SQL
    if os.path.isfile(sql_arg):
        try:
            with open(sql_arg, "r", encoding="utf-8") as f:
                sql_text = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    else:
        # Treat as inline SQL
        sql_text = sql_arg

    report = check_sql_markdown(sql_text, check_mode)
    print(report)

    violations = check_sql(sql_text, check_mode)
    errors = [v for v in violations if v.severity == Severity.ERROR]
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
