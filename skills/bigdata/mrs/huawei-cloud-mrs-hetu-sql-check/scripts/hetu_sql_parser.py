# -*- coding: utf-8 -*-
"""
HetuEngine SQL Parser

Recursive descent parser for HetuEngine SQL statements.
Parses token stream into AST and detects syntax errors.
Supports Presto/Trino + Hive compatibility syntax.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))

from hetu_sql_tokenizer import Token, TokenType, tokenize
from grammar_rules import (
    STATEMENT_RULES, HETU_SPECIFIC_GRAMMAR, MULTI_TOKEN_STATEMENTS,
    SINGLE_TOKEN_STATEMENTS, CLAUSE_ORDER_MAP, StatementCategory
)
from keywords import is_keyword, is_reserved_keyword, KeywordCategory


class SyntaxError:
    """Represents a syntax error in SQL text"""

    def __init__(self, message, line=0, column=0, severity="ERROR", rule_id=None):
        self.message = message
        self.line = line
        self.column = column
        self.severity = severity
        self.rule_id = rule_id

    def to_dict(self):
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "rule_id": self.rule_id,
        }

    def __repr__(self):
        return f"SyntaxError({self.severity}, L{self.line}:{self.column}, {self.message!r})"


class ASTNode:
    """Base AST node representing a parsed SQL construct"""

    def __init__(self, node_type, children=None, tokens=None, raw_text=""):
        self.node_type = node_type
        self.children = children or {}
        self.tokens = tokens or []
        self.raw_text = raw_text
        self.location = None
        if tokens:
            first = tokens[0]
            last = tokens[-1]
            self.location = {
                "start_line": first.line,
                "start_column": first.column,
                "end_line": last.line,
                "end_column": last.column,
            }

    def to_dict(self):
        result = {
            "node_type": self.node_type,
            "location": self.location,
            "raw_text": self.raw_text[:200],
        }
        for key, value in self.children.items():
            if isinstance(value, ASTNode):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [
                    v.to_dict() if isinstance(v, ASTNode) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result

    def __repr__(self):
        return f"ASTNode({self.node_type}, children={list(self.children.keys())})"


class HetuSQLParser:
    """
    HetuEngine SQL Recursive Descent Parser

    Parses token stream into AST following the HetuEngine SQL grammar rules.
    Supports Presto/Trino + Hive compatibility syntax.
    """

    def __init__(self, tokens, raw_sql=""):
        self.tokens = tokens
        self.raw_sql = raw_sql
        self.pos = 0
        self.errors = []
        self.warnings = []

    def _current(self):
        """Get current token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, '', 0, 0)

    def _peek(self, offset=1):
        """Peek at token at current position + offset"""
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return Token(TokenType.EOF, '', 0, 0)

    def _advance(self):
        """Advance to next token and return current"""
        token = self._current()
        if self.pos < len(self.tokens):
            self.pos += 1
        return token

    def _expect(self, type_=None, value=None, or_eof=False):
        """Expect a specific token type or value, advance if matched"""
        token = self._current()
        if type_ and token.type != type_:
            if or_eof and token.type == TokenType.EOF:
                return None
            self.errors.append(SyntaxError(
                f"Expected {type_} but got {token.type} ({token.value!r})",
                token.line, token.column, severity="ERROR", rule_id="SYN003"
            ))
            return None
        if value and token.value.upper() != value.upper():
            self.errors.append(SyntaxError(
                f"Expected {value!r} but got {token.value!r}",
                token.line, token.column, severity="ERROR", rule_id="SYN003"
            ))
            return None
        return self._advance()

    def _match(self, type_=None, value=None):
        """Check if current token matches, advance if so"""
        token = self._current()
        if type_ and token.type != type_:
            return None
        if value and token.value.upper() != value.upper():
            return None
        return self._advance()

    def _at_end(self):
        """Check if at end of token stream"""
        return self._current().type == TokenType.EOF or self._current().type == TokenType.SEMICOLON

    def _collect_until(self, *stop_values, stop_types=None, nested_parens=True):
        """Collect tokens until a stop value is found, respecting nesting"""
        collected = []
        depth = 0
        while not self._at_end():
            token = self._current()
            if token.type == TokenType.LPAREN:
                depth += 1
            elif token.type == TokenType.RPAREN:
                if depth > 0:
                    depth -= 1
                else:
                    break
            if depth == 0:
                if stop_types and token.type in stop_types:
                    break
                if token.value.upper() in [v.upper() for v in stop_values]:
                    break
            collected.append(self._advance())
        return collected

    # ============================================================
    # Statement Type Detection
    # ============================================================

    def detect_statement_type(self):
        """
        Detect the SQL statement type from the current token position.
        Uses multi-token lookahead for disambiguation.

        MULTI_TOKEN_STATEMENTS format: Dict[str, List[str]]
          key = statement type name (e.g. "CREATE TABLE")
          value = list of pattern strings (e.g. ["CREATE TABLE", "CREATE EXTERNAL TABLE"])

        Returns:
            str: Statement type name (e.g., "SELECT", "CREATE TABLE", "ALTER TABLE")
        """
        best_match = None
        best_match_len = 0

        for stmt_type, patterns in MULTI_TOKEN_STATEMENTS.items():
            for pattern in patterns:
                pattern_tokens = pattern.split()
                if len(pattern_tokens) < best_match_len:
                    continue
                match = True
                for i, expected in enumerate(pattern_tokens):
                    if i == 0:
                        peek_token = self._current()
                    else:
                        peek_token = self._peek(i)
                    if peek_token.type != TokenType.KEYWORD or peek_token.value.upper() != expected.upper():
                        match = False
                        break
                if match and len(pattern_tokens) > best_match_len:
                    best_match = stmt_type
                    best_match_len = len(pattern_tokens)

        if best_match:
            return best_match

        token = self._current()
        if token.type == TokenType.KEYWORD:
            upper = token.value.upper()
            if upper in SINGLE_TOKEN_STATEMENTS:
                return SINGLE_TOKEN_STATEMENTS[upper]

        return "UNKNOWN"

    # ============================================================
    # Main Parse Entry Point
    # ============================================================

    def parse(self):
        """
        Parse the token stream and return an AST + syntax errors.

        Returns:
            dict: {
                "ast": ASTNode or None,
                "statement_type": str,
                "errors": [SyntaxError],
                "warnings": [SyntaxError],
            }
        """
        if not self.tokens or self._current().type == TokenType.EOF:
            return {
                "ast": None,
                "statement_type": "EMPTY",
                "errors": [SyntaxError("Empty SQL input", 0, 0, "ERROR", "SYN003")],
                "warnings": [],
            }

        stmt_type = self.detect_statement_type()

        ast = None
        if stmt_type == "SELECT":
            ast = self._parse_select()
        elif stmt_type == "INSERT":
            ast = self._parse_insert()
        elif stmt_type == "UPDATE":
            ast = self._parse_update()
        elif stmt_type == "DELETE":
            ast = self._parse_delete()
        elif stmt_type == "LOAD":
            ast = self._parse_load()
        elif stmt_type == "CREATE TABLE":
            ast = self._parse_create_table()
        elif stmt_type == "CREATE TABLE AS":
            ast = self._parse_create_table_as()
        elif stmt_type == "CREATE TABLE LIKE":
            ast = self._parse_create_table_like()
        elif stmt_type == "CREATE VIEW":
            ast = self._parse_create_view()
        elif stmt_type == "CREATE FUNCTION":
            ast = self._parse_create_function()
        elif stmt_type == "CREATE MATERIALIZED VIEW":
            ast = self._parse_create_materialized_view()
        elif stmt_type in ("CREATE SCHEMA", "ALTER TABLE", "ALTER SCHEMA",
                          "ALTER MATERIALIZED VIEW", "ALTER FUNCTION"):
            ast = self._parse_alter(stmt_type)
        elif stmt_type in ("DROP TABLE", "DROP VIEW", "DROP SCHEMA",
                          "DROP FUNCTION", "DROP MATERIALIZED VIEW"):
            ast = self._parse_drop(stmt_type)
        elif stmt_type == "TRUNCATE":
            ast = self._parse_truncate()
        elif stmt_type == "EXPLAIN":
            ast = self._parse_explain()
        elif stmt_type == "SHOW":
            ast = self._parse_show()
        elif stmt_type in ("DESCRIBE", "DESC"):
            ast = self._parse_describe()
        elif stmt_type == "USE":
            ast = self._parse_use()
        elif stmt_type in ("SET", "RESET"):
            ast = self._parse_set_reset(stmt_type)
        elif stmt_type == "CALL":
            ast = self._parse_call()
        elif stmt_type == "REFRESH MATERIALIZED VIEW":
            ast = self._parse_refresh_materialized_view()
        elif stmt_type in ("START TRANSACTION", "COMMIT", "ROLLBACK"):
            ast = self._parse_transaction(stmt_type)
        else:
            ast = self._parse_generic(stmt_type)

        return {
            "ast": ast,
            "statement_type": stmt_type,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    # ============================================================
    # SELECT Statement Parser
    # ============================================================

    def _parse_select(self):
        """Parse SELECT statement"""
        node = ASTNode("SelectStmt")
        start_token = self._current()

        # WITH clause (CTE)
        if self._current().is_keyword("WITH"):
            self._advance()
            # WITH RECURSIVE
            if self._current().is_keyword("RECURSIVE"):
                self._advance()
                node.children["recursive"] = True
            with_tokens = self._collect_until("SELECT")
            node.children["with_clause"] = ASTNode("WithClause", tokens=with_tokens,
                                                     raw_text=self._tokens_to_text(with_tokens))

        # SELECT keyword
        if self._current().is_keyword("SELECT"):
            self._advance()

        # ALL / DISTINCT
        if self._current().is_keyword("DISTINCT"):
            self._advance()
            node.children["distinct"] = True
        elif self._current().is_keyword("ALL"):
            self._advance()
            node.children["all"] = True

        # Target list
        target_tokens = self._collect_until("FROM", "WHERE", "GROUP", "HAVING",
                                           "WINDOW", "ORDER", "LIMIT", "OFFSET",
                                           "FETCH", "UNION", "INTERSECT", "EXCEPT",
                                           "TABLESAMPLE", "MATCH_RECOGNIZE", "FORMAT")
        node.children["target_list"] = self._parse_target_list(target_tokens)

        if self._has_select_star(target_tokens):
            node.children["has_select_star"] = True

        # FROM clause
        if self._current().is_keyword("FROM"):
            self._advance()
            from_tokens = self._collect_until("WHERE", "GROUP", "HAVING", "WINDOW",
                                             "ORDER", "LIMIT", "OFFSET", "FETCH",
                                             "UNION", "INTERSECT", "EXCEPT",
                                             "TABLESAMPLE", "MATCH_RECOGNIZE")
            node.children["from_clause"] = self._parse_from_clause(from_tokens)

            # Detect semi/anti join
            from_text = self._tokens_to_text(from_tokens).upper()
            if "SEMI JOIN" in from_text:
                node.children["has_semi_join"] = True
            if "ANTI JOIN" in from_text:
                node.children["has_anti_join"] = True

            # TABLESAMPLE
            if self._current().is_keyword("TABLESAMPLE"):
                self._advance()
                sample_tokens = self._collect_until("WHERE", "GROUP", "HAVING", "WINDOW",
                                                   "ORDER", "LIMIT", "OFFSET", "FETCH",
                                                   "UNION", "INTERSECT", "EXCEPT")
                node.children["tablesample"] = self._tokens_to_text(sample_tokens)

        # MATCH_RECOGNIZE
        if self._current().is_keyword("MATCH_RECOGNIZE"):
            self._advance()
            mr_tokens = self._collect_balanced_parens()
            node.children["match_recognize"] = self._tokens_to_text(mr_tokens)

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("GROUP", "HAVING", "WINDOW", "ORDER",
                                              "LIMIT", "OFFSET", "FETCH",
                                              "UNION", "INTERSECT", "EXCEPT")
            node.children["where_clause"] = self._tokens_to_text(where_tokens)

        # GROUP BY
        if self._current().is_keyword("GROUP"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            group_tokens = self._collect_until("HAVING", "WINDOW", "ORDER", "LIMIT",
                                              "OFFSET", "FETCH",
                                              "UNION", "INTERSECT", "EXCEPT")
            group_text = self._tokens_to_text(group_tokens).upper()
            node.children["group_by"] = self._tokens_to_text(group_tokens)
            if "GROUPING SETS" in group_text:
                node.children["has_grouping_sets"] = True
            if "CUBE" in group_text:
                node.children["has_cube"] = True
            if "ROLLUP" in group_text:
                node.children["has_rollup"] = True

        # HAVING
        if self._current().is_keyword("HAVING"):
            self._advance()
            having_tokens = self._collect_until("WINDOW", "ORDER", "LIMIT", "OFFSET",
                                               "FETCH", "UNION", "INTERSECT", "EXCEPT")
            node.children["having"] = self._tokens_to_text(having_tokens)

        # WINDOW
        if self._current().is_keyword("WINDOW"):
            self._advance()
            win_tokens = self._collect_until("ORDER", "LIMIT", "OFFSET", "FETCH",
                                            "UNION", "INTERSECT", "EXCEPT")
            node.children["window"] = self._tokens_to_text(win_tokens)

        # ORDER BY
        if self._current().is_keyword("ORDER"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            order_tokens = self._collect_until("LIMIT", "OFFSET", "FETCH",
                                              "UNION", "INTERSECT", "EXCEPT")
            node.children["order_by"] = self._tokens_to_text(order_tokens)
            order_text = self._tokens_to_text(order_tokens).upper()
            if "NULLS FIRST" in order_text:
                node.children["has_nulls_first"] = True
            if "NULLS LAST" in order_text:
                node.children["has_nulls_last"] = True

        # OFFSET
        if self._current().is_keyword("OFFSET"):
            self._advance()
            offset_tokens = self._collect_until("LIMIT", "FETCH",
                                               "UNION", "INTERSECT", "EXCEPT")
            node.children["offset"] = self._tokens_to_text(offset_tokens)

        # LIMIT
        if self._current().is_keyword("LIMIT"):
            self._advance()
            limit_tokens = self._collect_until("FETCH",
                                              "UNION", "INTERSECT", "EXCEPT")
            node.children["limit"] = self._tokens_to_text(limit_tokens)

        # FETCH clause
        if self._current().is_keyword("FETCH"):
            self._advance()
            fetch_tokens = self._collect_until("UNION", "INTERSECT", "EXCEPT")
            node.children["fetch"] = self._tokens_to_text(fetch_tokens)
            fetch_text = self._tokens_to_text(fetch_tokens).upper()
            if "WITH TIES" in fetch_text:
                node.children["fetch_with_ties"] = True
            if "FIRST" in fetch_text:
                node.children["fetch_first"] = True
            elif "NEXT" in fetch_text:
                node.children["fetch_next"] = True

        # FORMAT clause
        if self._current().is_keyword("FORMAT"):
            self._advance()
            fmt_token = self._advance()
            node.children["format"] = fmt_token.value if fmt_token else None

        # Set operations (UNION/INTERSECT/EXCEPT)
        if self._current().is_keyword("UNION") or self._current().is_keyword("INTERSECT") or \
           self._current().is_keyword("EXCEPT"):
            op_token = self._advance()
            all_flag = False
            distinct_flag = False
            if self._current().is_keyword("ALL"):
                self._advance()
                all_flag = True
            elif self._current().is_keyword("DISTINCT"):
                self._advance()
                distinct_flag = True
            node.children["set_operation"] = op_token.value
            node.children["set_all"] = all_flag
            node.children["set_distinct"] = distinct_flag

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        if node.location is None and start_token:
            node.location = {"start_line": start_token.line, "start_column": start_token.column,
                            "end_line": 0, "end_column": 0}

        return node

    # ============================================================
    # INSERT Statement Parser
    # ============================================================

    def _parse_insert(self):
        """Parse INSERT statement"""
        node = ASTNode("InsertStmt")
        start_token = self._current()

        # INSERT
        self._advance()

        # INTO or OVERWRITE
        if self._current().is_keyword("OVERWRITE"):
            self._advance()
            node.children["is_overwrite"] = True
        elif self._current().is_keyword("INTO"):
            self._advance()

        # Optional TABLE keyword
        if self._current().is_keyword("TABLE"):
            self._advance()
            node.children["has_table_keyword"] = True

        # Table name
        table_tokens = self._collect_until("VALUES", "SELECT", "WITH", "PARTITION",
                                          stop_types=[TokenType.LPAREN])
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # Column list
        if self._current().type == TokenType.LPAREN:
            col_tokens = self._collect_balanced_parens()
            node.children["columns"] = self._tokens_to_text(col_tokens)

        # PARTITION specification
        if self._current().is_keyword("PARTITION"):
            self._advance()
            if self._current().type == TokenType.LPAREN:
                part_tokens = self._collect_balanced_parens()
                node.children["partition"] = self._tokens_to_text(part_tokens)

        # VALUES or SELECT
        if self._current().is_keyword("VALUES"):
            self._advance()
            values_tokens = self._collect_until()
            node.children["values"] = self._tokens_to_text(values_tokens)
        elif self._current().is_keyword("SELECT") or self._current().is_keyword("WITH"):
            node.children["subquery"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # UPDATE Statement Parser
    # ============================================================

    def _parse_update(self):
        """Parse UPDATE statement"""
        node = ASTNode("UpdateStmt")
        start_token = self._current()

        self._advance()

        # Table name
        table_tokens = self._collect_until("SET")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # SET clause
        if self._current().is_keyword("SET"):
            self._advance()
            set_tokens = self._collect_until("WHERE")
            node.children["set_clause"] = self._tokens_to_text(set_tokens)

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until()
            node.children["where_clause"] = self._tokens_to_text(where_tokens)
        else:
            node.children["missing_where"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # DELETE Statement Parser
    # ============================================================

    def _parse_delete(self):
        """Parse DELETE statement"""
        node = ASTNode("DeleteStmt")
        start_token = self._current()

        self._advance()

        # FROM
        if self._current().is_keyword("FROM"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("WHERE")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until()
            node.children["where_clause"] = self._tokens_to_text(where_tokens)
        else:
            node.children["missing_where"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # LOAD Statement Parser
    # ============================================================

    def _parse_load(self):
        """Parse LOAD DATA statement (Hive-compatible)"""
        node = ASTNode("LoadStmt")
        start_token = self._current()

        self._advance()

        # DATA
        if self._current().is_keyword("DATA"):
            self._advance()

        # INPATH
        if self._current().is_keyword("INPATH"):
            self._advance()
            path_token = self._advance()
            node.children["inpath"] = path_token.value

        # OVERWRITE
        if self._current().is_keyword("OVERWRITE"):
            self._advance()
            node.children["is_overwrite"] = True

        # INTO TABLE
        if self._current().is_keyword("INTO"):
            self._advance()
        if self._current().is_keyword("TABLE"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("PARTITION")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # PARTITION
        if self._current().is_keyword("PARTITION"):
            self._advance()
            if self._current().type == TokenType.LPAREN:
                part_tokens = self._collect_balanced_parens()
                node.children["partition"] = self._tokens_to_text(part_tokens)

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE TABLE Parser
    # ============================================================

    def _parse_create_table(self):
        """Parse CREATE TABLE statement (standard + Hive-compatible)"""
        node = ASTNode("CreateStmt")
        start_token = self._current()

        self._advance()

        # EXTERNAL
        if self._current().is_keyword("EXTERNAL"):
            self._advance()
            node.children["is_external"] = True

        # TABLE
        if self._current().is_keyword("TABLE"):
            self._advance()

        # IF NOT EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("NOT"):
                self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_not_exists"] = True

        # Table name
        table_name_parts = []
        while not self._at_end():
            t = self._current()
            if t.type == TokenType.LPAREN:
                break
            if t.type == TokenType.KEYWORD and t.value.upper() in (
                "PARTITIONED", "CLUSTERED", "ROW", "STORED", "LOCATION",
                "TBLPROPERTIES", "COMMENT", "WITH", "LIKE", "AS"):
                break
            table_name_parts.append(self._advance())
        node.children["table_name"] = self._tokens_to_text(table_name_parts).strip()

        # Column definitions
        if self._current().type == TokenType.LPAREN:
            col_tokens = self._collect_balanced_parens()
            node.children["columns"] = self._tokens_to_text(col_tokens)

        # Hive-compatible extensions
        remaining = []
        while not self._at_end():
            token = self._current()
            remaining.append(token)

            # COMMENT
            if token.is_keyword("COMMENT"):
                self._advance()
                comment_token = self._advance()
                node.children["comment"] = comment_token.value if comment_token else None

            # PARTITIONED BY
            elif token.is_keyword("PARTITIONED"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                if self._current().type == TokenType.LPAREN:
                    part_tokens = self._collect_balanced_parens()
                    node.children["partitioned_by"] = self._tokens_to_text(part_tokens)
                    node.children["hive_compatible"] = True

            # CLUSTERED BY
            elif token.is_keyword("CLUSTERED"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                if self._current().type == TokenType.LPAREN:
                    cluster_tokens = self._collect_balanced_parens()
                    node.children["clustered_by"] = self._tokens_to_text(cluster_tokens)
                    node.children["hive_compatible"] = True

                # SORTED BY
                if self._current().is_keyword("SORTED"):
                    self._advance()
                    if self._current().is_keyword("BY"):
                        self._advance()
                    if self._current().type == TokenType.LPAREN:
                        sort_tokens = self._collect_balanced_parens()
                        node.children["sorted_by"] = self._tokens_to_text(sort_tokens)

                # INTO n BUCKETS
                if self._current().is_keyword("INTO"):
                    self._advance()
                    bucket_count = self._advance()
                    node.children["buckets"] = bucket_count.value if bucket_count else None
                    if self._current().is_keyword("BUCKETS"):
                        self._advance()

            # ROW FORMAT
            elif token.is_keyword("ROW"):
                self._advance()
                if self._current().is_keyword("FORMAT"):
                    self._advance()
                    row_fmt_tokens = self._collect_until("STORED", "LOCATION", "TBLPROPERTIES", "WITH")
                    node.children["row_format"] = self._tokens_to_text(row_fmt_tokens)
                    node.children["hive_compatible"] = True

            # STORED AS
            elif token.is_keyword("STORED"):
                self._advance()
                if self._current().is_keyword("AS"):
                    self._advance()
                    fmt_token = self._advance()
                    node.children["stored_as"] = fmt_token.value.upper() if fmt_token else None
                    node.children["hive_compatible"] = True

            # LOCATION
            elif token.is_keyword("LOCATION"):
                self._advance()
                loc_token = self._advance()
                node.children["location"] = loc_token.value if loc_token else None

            # TBLPROPERTIES
            elif token.is_keyword("TBLPROPERTIES"):
                self._advance()
                if self._current().type == TokenType.LPAREN:
                    tblprop_tokens = self._collect_balanced_parens()
                    node.children["tblproperties"] = self._tokens_to_text(tblprop_tokens)
                    node.children["hive_compatible"] = True

            # WITH properties
            elif token.is_keyword("WITH"):
                self._advance()
                if self._current().type == TokenType.LPAREN:
                    with_tokens = self._collect_balanced_parens()
                    node.children["with_properties"] = self._tokens_to_text(with_tokens)

            else:
                self._advance()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE TABLE AS Parser
    # ============================================================

    def _parse_create_table_as(self):
        """Parse CREATE TABLE AS SELECT statement"""
        node = ASTNode("CreateTableAsStmt")
        start_token = self._current()

        self._advance()

        # TABLE
        if self._current().is_keyword("TABLE"):
            self._advance()

        # IF NOT EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("NOT"):
                self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_not_exists"] = True

        # Table name
        table_name_parts = []
        while not self._at_end():
            t = self._current()
            if t.is_keyword("WITH") or t.is_keyword("AS"):
                break
            table_name_parts.append(self._advance())
        node.children["table_name"] = self._tokens_to_text(table_name_parts).strip()

        # WITH properties
        if self._current().is_keyword("WITH"):
            self._advance()
            if self._current().type == TokenType.LPAREN:
                with_tokens = self._collect_balanced_parens()
                node.children["with_properties"] = self._tokens_to_text(with_tokens)

        # AS
        if self._current().is_keyword("AS"):
            self._advance()

        # Subquery
        node.children["subquery"] = True

        # WITH [NO] DATA
        if self._current().is_keyword("WITH"):
            self._advance()
            if self._current().is_keyword("NO"):
                self._advance()
                node.children["with_data"] = False
            else:
                node.children["with_data"] = True
            if self._current().is_keyword("DATA"):
                self._advance()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE TABLE LIKE Parser
    # ============================================================

    def _parse_create_table_like(self):
        """Parse CREATE TABLE LIKE statement"""
        node = ASTNode("CreateTableLikeStmt")
        start_token = self._current()

        self._advance()

        # TABLE
        if self._current().is_keyword("TABLE"):
            self._advance()

        # IF NOT EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("NOT"):
                self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_not_exists"] = True

        # New table name
        table_name_parts = []
        while not self._at_end():
            t = self._current()
            if t.is_keyword("LIKE"):
                break
            table_name_parts.append(self._advance())
        node.children["table_name"] = self._tokens_to_text(table_name_parts).strip()

        # LIKE
        if self._current().is_keyword("LIKE"):
            self._advance()

        # Source table name
        source_name_parts = self._collect_until("INCLUDING", "EXCLUDING")
        node.children["like_table"] = self._tokens_to_text(source_name_parts).strip()

        # INCLUDING/EXCLUDING PROPERTIES
        if self._current().is_keyword("INCLUDING"):
            self._advance()
            if self._current().is_keyword("PROPERTIES"):
                self._advance()
            node.children["including_properties"] = True
        elif self._current().is_keyword("EXCLUDING"):
            self._advance()
            if self._current().is_keyword("PROPERTIES"):
                self._advance()
            node.children["excluding_properties"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE VIEW Parser
    # ============================================================

    def _parse_create_view(self):
        """Parse CREATE VIEW statement"""
        node = ASTNode("CreateViewStmt")
        start_token = self._current()

        self._advance()

        # OR REPLACE
        if self._current().is_keyword("OR"):
            self._advance()
            if self._current().is_keyword("REPLACE"):
                self._advance()
            node.children["or_replace"] = True

        # VIEW
        if self._current().is_keyword("VIEW"):
            self._advance()

        # IF NOT EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("NOT"):
                self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_not_exists"] = True

        # View name
        view_name_parts = []
        while not self._at_end():
            t = self._current()
            if t.is_keyword("COMMENT") or t.is_keyword("TBLPROPERTIES") or t.is_keyword("AS"):
                break
            if t.type == TokenType.LPAREN:
                break
            view_name_parts.append(self._advance())
        node.children["view_name"] = self._tokens_to_text(view_name_parts).strip()

        # Column list
        if self._current().type == TokenType.LPAREN:
            col_tokens = self._collect_balanced_parens()
            node.children["columns"] = self._tokens_to_text(col_tokens)

        # COMMENT
        if self._current().is_keyword("COMMENT"):
            self._advance()
            comment_token = self._advance()
            node.children["comment"] = comment_token.value if comment_token else None

        # TBLPROPERTIES
        if self._current().is_keyword("TBLPROPERTIES"):
            self._advance()
            if self._current().type == TokenType.LPAREN:
                tblprop_tokens = self._collect_balanced_parens()
                node.children["tblproperties"] = self._tokens_to_text(tblprop_tokens)

        # AS
        if self._current().is_keyword("AS"):
            self._advance()

        node.children["subquery"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE FUNCTION Parser
    # ============================================================

    def _parse_create_function(self):
        """Parse CREATE FUNCTION statement"""
        node = ASTNode("CreateFunctionStmt")
        start_token = self._current()

        self._advance()

        # OR REPLACE
        if self._current().is_keyword("OR"):
            self._advance()
            if self._current().is_keyword("REPLACE"):
                self._advance()
            node.children["or_replace"] = True

        # FUNCTION
        if self._current().is_keyword("FUNCTION"):
            self._advance()

        # Function name
        func_name_parts = []
        while not self._at_end() and self._current().type != TokenType.LPAREN:
            func_name_parts.append(self._advance())
        node.children["function_name"] = self._tokens_to_text(func_name_parts).strip()

        # Parameters
        if self._current().type == TokenType.LPAREN:
            param_tokens = self._collect_balanced_parens()
            node.children["parameters"] = self._tokens_to_text(param_tokens)

        # RETURNS
        if self._current().is_keyword("RETURNS"):
            self._advance()
            ret_type_parts = self._collect_until("LANGUAGE", "DETERMINISTIC", "NOT", "BEGIN",
                                                  "AS", "RETURN")
            node.children["return_type"] = self._tokens_to_text(ret_type_parts).strip()

        # LANGUAGE
        if self._current().is_keyword("LANGUAGE"):
            self._advance()
            lang_token = self._advance()
            node.children["language"] = lang_token.value.upper() if lang_token else None

        # DETERMINISTIC / NOT DETERMINISTIC
        if self._current().is_keyword("DETERMINISTIC"):
            self._advance()
            node.children["deterministic"] = True
        elif self._current().is_keyword("NOT"):
            self._advance()
            if self._current().is_keyword("DETERMINISTIC"):
                self._advance()
            node.children["deterministic"] = False

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE MATERIALIZED VIEW Parser
    # ============================================================

    def _parse_create_materialized_view(self):
        """Parse CREATE MATERIALIZED VIEW statement"""
        node = ASTNode("CreateMaterializedViewStmt")
        start_token = self._current()

        self._advance()

        # MATERIALIZED VIEW
        if self._current().is_keyword("MATERIALIZED"):
            self._advance()
        if self._current().is_keyword("VIEW"):
            self._advance()

        # IF NOT EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("NOT"):
                self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_not_exists"] = True

        # View name
        mv_name_parts = []
        while not self._at_end():
            t = self._current()
            if t.is_keyword("COMMENT") or t.is_keyword("WITH") or t.is_keyword("AS"):
                break
            mv_name_parts.append(self._advance())
        node.children["mv_name"] = self._tokens_to_text(mv_name_parts).strip()

        # COMMENT
        if self._current().is_keyword("COMMENT"):
            self._advance()
            comment_token = self._advance()
            node.children["comment"] = comment_token.value if comment_token else None

        # WITH properties
        if self._current().is_keyword("WITH"):
            self._advance()
            if self._current().type == TokenType.LPAREN:
                with_tokens = self._collect_balanced_parens()
                node.children["with_properties"] = self._tokens_to_text(with_tokens)

        # AS
        if self._current().is_keyword("AS"):
            self._advance()

        node.children["subquery"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # ALTER Statement Parser
    # ============================================================

    def _parse_alter(self, stmt_type):
        """Parse ALTER statement"""
        node = ASTNode("AlterTableStmt")
        start_token = self._current()

        self._advance()

        # Object type
        obj_type = "TABLE"
        if self._current().is_keyword("TABLE"):
            obj_type = "TABLE"
            self._advance()
        elif self._current().is_keyword("SCHEMA") or self._current().is_keyword("DATABASE"):
            obj_type = "SCHEMA"
            self._advance()
        elif self._current().is_keyword("MATERIALIZED"):
            self._advance()
            if self._current().is_keyword("VIEW"):
                self._advance()
            obj_type = "MATERIALIZED VIEW"
        elif self._current().is_keyword("FUNCTION"):
            obj_type = "FUNCTION"
            self._advance()
        node.children["object_type"] = obj_type

        # IF EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_exists"] = True

        # Object name
        name_tokens = self._collect_until("RENAME", "ADD", "DROP", "ALTER", "SET",
                                          "CHANGE", "OWNER", "EXECUTE")
        node.children["object_name"] = self._tokens_to_text(name_tokens).strip()

        # Remaining actions
        action_tokens = []
        while not self._at_end():
            action_tokens.append(self._advance())
        node.children["actions"] = self._tokens_to_text(action_tokens).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # DROP Parser
    # ============================================================

    def _parse_drop(self, stmt_type):
        """Parse DROP statement"""
        node = ASTNode("DropStmt")
        start_token = self._current()

        self._advance()

        # Object type
        obj_type = "UNKNOWN"
        if stmt_type == "DROP TABLE":
            obj_type = "TABLE"
        elif stmt_type == "DROP VIEW":
            obj_type = "VIEW"
        elif stmt_type == "DROP SCHEMA":
            obj_type = "SCHEMA"
        elif stmt_type == "DROP FUNCTION":
            obj_type = "FUNCTION"
        elif stmt_type == "DROP MATERIALIZED VIEW":
            obj_type = "MATERIALIZED VIEW"

        # Consume type keywords if multi-token
        if obj_type == "MATERIALIZED VIEW":
            if self._current().is_keyword("MATERIALIZED"):
                self._advance()
            if self._current().is_keyword("VIEW"):
                self._advance()
        elif obj_type == "SCHEMA":
            if self._current().is_keyword("SCHEMA"):
                self._advance()
            elif self._current().is_keyword("DATABASE"):
                self._advance()
        else:
            if self._current().is_keyword(obj_type):
                self._advance()

        node.children["object_type"] = obj_type

        # IF EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_exists"] = True

        # Object name
        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["object_name"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # TRUNCATE Parser
    # ============================================================

    def _parse_truncate(self):
        """Parse TRUNCATE statement"""
        node = ASTNode("TruncateStmt")
        start_token = self._current()

        self._advance()

        # Optional TABLE
        if self._current().is_keyword("TABLE"):
            self._advance()

        # Table name
        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["table_name"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # EXPLAIN Parser
    # ============================================================

    def _parse_explain(self):
        """Parse EXPLAIN statement"""
        node = ASTNode("ExplainStmt")
        start_token = self._current()

        self._advance()

        # Options
        while not self._at_end():
            if self._current().is_keyword("ANALYZE"):
                self._advance()
                node.children["analyze"] = True
            elif self._current().is_keyword("VERBOSE"):
                self._advance()
                node.children["verbose"] = True
            elif self._current().is_keyword("IO"):
                self._advance()
                node.children["io"] = True
            elif self._current().is_keyword("TYPE"):
                self._advance()
                type_token = self._advance()
                node.children["explain_type"] = type_token.value.upper() if type_token else None
            elif self._current().is_keyword("GRAPHVIZ"):
                self._advance()
                node.children["graphviz"] = True
            else:
                break

        # The explained statement
        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["statement"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # SHOW Parser
    # ============================================================

    def _parse_show(self):
        """Parse SHOW statement"""
        node = ASTNode("ShowStmt")
        start_token = self._current()

        self._advance()

        # Show target
        show_type = None
        if self._current().is_keyword("SCHEMAS"):
            self._advance()
            show_type = "SCHEMAS"
        elif self._current().is_keyword("TABLES"):
            self._advance()
            show_type = "TABLES"
        elif self._current().is_keyword("VIEWS"):
            self._advance()
            show_type = "VIEWS"
        elif self._current().is_keyword("COLUMNS"):
            self._advance()
            show_type = "COLUMNS"
        elif self._current().is_keyword("PARTITIONS"):
            self._advance()
            show_type = "PARTITIONS"
        elif self._current().is_keyword("SESSION"):
            self._advance()
            show_type = "SESSION"
        elif self._current().is_keyword("FUNCTIONS"):
            self._advance()
            show_type = "FUNCTIONS"
        elif self._current().is_keyword("CATALOGS"):
            self._advance()
            show_type = "CATALOGS"
        elif self._current().is_keyword("STATS"):
            self._advance()
            show_type = "STATS"
        elif self._current().is_keyword("STATUS"):
            self._advance()
            show_type = "STATUS"
        elif self._current().is_keyword("MATERIALIZED"):
            self._advance()
            if self._current().is_keyword("VIEWS"):
                self._advance()
                show_type = "MATERIALIZED VIEWS"
        elif self._current().is_keyword("CREATE"):
            self._advance()
            if self._current().is_keyword("TABLE"):
                self._advance()
                show_type = "CREATE TABLE"
            elif self._current().is_keyword("VIEW"):
                self._advance()
                show_type = "CREATE VIEW"
            elif self._current().is_keyword("MATERIALIZED"):
                self._advance()
                if self._current().is_keyword("VIEW"):
                    self._advance()
                show_type = "CREATE MATERIALIZED VIEW"
        elif self._current().is_keyword("TABLE"):
            self._advance()
            if self._current().is_keyword("STATUS"):
                self._advance()
                show_type = "TABLE STATUS"

        node.children["show_type"] = show_type

        # Target (FROM clause)
        if self._current().is_keyword("FROM"):
            self._advance()
            from_tokens = self._collect_until("LIKE")
            node.children["from_target"] = self._tokens_to_text(from_tokens).strip()

        # LIKE pattern
        if self._current().is_keyword("LIKE"):
            self._advance()
            pattern_token = self._advance()
            node.children["like_pattern"] = pattern_token.value if pattern_token else None

        # Remaining
        if not self._at_end():
            remaining = []
            while not self._at_end():
                remaining.append(self._advance())
            node.children["target"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # DESCRIBE Parser
    # ============================================================

    def _parse_describe(self):
        """Parse DESCRIBE/DESC statement"""
        node = ASTNode("DescribeStmt")
        start_token = self._current()

        self._advance()

        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["target"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # USE Parser
    # ============================================================

    def _parse_use(self):
        """Parse USE statement"""
        node = ASTNode("UseStmt")
        start_token = self._current()

        self._advance()

        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        target_text = self._tokens_to_text(remaining).strip()
        node.children["target"] = target_text

        # Parse catalog.schema
        parts = target_text.split(".")
        if len(parts) == 2:
            node.children["catalog"] = parts[0].strip()
            node.children["schema"] = parts[1].strip()
        elif len(parts) == 1:
            node.children["schema"] = parts[0].strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # SET/RESET Parser
    # ============================================================

    def _parse_set_reset(self, stmt_type):
        """Parse SET/RESET statement"""
        node = ASTNode("SetStmt")
        start_token = self._current()

        self._advance()

        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        remaining_text = self._tokens_to_text(remaining).strip()
        node.children["raw"] = remaining_text

        # Parse property = value
        if "=" in remaining_text:
            parts = remaining_text.split("=", 1)
            node.children["property"] = parts[0].strip()
            node.children["value"] = parts[1].strip()
        else:
            node.children["property"] = remaining_text

        node.children["action"] = stmt_type

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CALL Parser
    # ============================================================

    def _parse_call(self):
        """Parse CALL statement"""
        node = ASTNode("CallStmt")
        start_token = self._current()

        self._advance()

        # Procedure name
        proc_name_parts = []
        while not self._at_end() and self._current().type != TokenType.LPAREN:
            proc_name_parts.append(self._advance())
        node.children["procedure_name"] = self._tokens_to_text(proc_name_parts).strip()

        # Arguments
        if self._current().type == TokenType.LPAREN:
            arg_tokens = self._collect_balanced_parens()
            node.children["arguments"] = self._tokens_to_text(arg_tokens)

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # REFRESH MATERIALIZED VIEW Parser
    # ============================================================

    def _parse_refresh_materialized_view(self):
        """Parse REFRESH MATERIALIZED VIEW statement"""
        node = ASTNode("RefreshMaterializedViewStmt")
        start_token = self._current()

        self._advance()

        # MATERIALIZED VIEW
        if self._current().is_keyword("MATERIALIZED"):
            self._advance()
        if self._current().is_keyword("VIEW"):
            self._advance()

        # View name
        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["mv_name"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # Transaction Parser
    # ============================================================

    def _parse_transaction(self, stmt_type):
        """Parse transaction statement"""
        node = ASTNode("TransactionStmt")
        start_token = self._current()

        if stmt_type == "START TRANSACTION":
            self._advance()
            if self._current().is_keyword("TRANSACTION"):
                self._advance()
            node.children["action"] = "START TRANSACTION"

            # Isolation level
            if self._current().is_keyword("ISOLATION"):
                self._advance()
                if self._current().is_keyword("LEVEL"):
                    self._advance()
                iso_tokens = self._collect_until("READ", "WRITE")
                node.children["isolation_level"] = self._tokens_to_text(iso_tokens).strip()

            # READ/WRITE
            if self._current().is_keyword("READ"):
                self._advance()
                node.children["read_mode"] = "READ"
            elif self._current().is_keyword("WRITE"):
                self._advance()
                node.children["read_mode"] = "WRITE"

        elif stmt_type == "COMMIT":
            self._advance()
            node.children["action"] = "COMMIT"

        elif stmt_type == "ROLLBACK":
            self._advance()
            node.children["action"] = "ROLLBACK"

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # Generic Parser (fallback)
    # ============================================================

    def _parse_generic(self, stmt_type):
        """Generic parser for less common statement types"""
        node = ASTNode(stmt_type.replace(" ", "") + "Stmt")
        start_token = self._current()

        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["raw"] = self._tokens_to_text(remaining).strip()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # Helper Methods
    # ============================================================

    def _tokens_to_text(self, tokens):
        """Convert token list back to text"""
        return " ".join(t.value for t in tokens)

    def _get_raw_text(self, start_token):
        """Get raw SQL text from start token to current position"""
        if start_token:
            return f"[L{start_token.line}:{start_token.column} ...]"
        return ""

    def _collect_balanced_parens(self):
        """Collect tokens within balanced parentheses (including the parens)"""
        if self._current().type != TokenType.LPAREN:
            return []
        result = [self._advance()]
        depth = 1
        while not self._at_end() and depth > 0:
            token = self._current()
            if token.type == TokenType.LPAREN:
                depth += 1
            elif token.type == TokenType.RPAREN:
                depth -= 1
            result.append(self._advance())
        return result

    def _has_select_star(self, target_tokens):
        """Check if target list contains SELECT *"""
        i = 0
        while i < len(target_tokens):
            t = target_tokens[i]
            if t.type == TokenType.STAR:
                prev = target_tokens[i - 1] if i > 0 else None
                if prev is None or prev.type != TokenType.DOT:
                    return True
            i += 1
        return False

    def _parse_target_list(self, tokens):
        """Parse target list into structured data"""
        targets = []
        current = []
        depth = 0
        for t in tokens:
            if t.type == TokenType.LPAREN:
                depth += 1
                current.append(t.value)
            elif t.type == TokenType.RPAREN:
                depth -= 1
                current.append(t.value)
            elif t.type == TokenType.COMMA and depth == 0:
                targets.append({
                    "text": " ".join(current).strip(),
                })
                current = []
            else:
                current.append(t.value)
        if current:
            targets.append({"text": " ".join(current).strip()})
        return targets

    def _parse_from_clause(self, tokens):
        """Parse FROM clause into structured data"""
        tables = []
        current = []
        depth = 0
        for t in tokens:
            if t.type == TokenType.LPAREN:
                depth += 1
                current.append(t.value)
            elif t.type == TokenType.RPAREN:
                depth -= 1
                current.append(t.value)
            elif t.type == TokenType.COMMA and depth == 0:
                table_text = " ".join(current).strip()
                if table_text:
                    tables.append(table_text)
                current = []
            else:
                current.append(t.value)
        if current:
            table_text = " ".join(current).strip()
            if table_text:
                tables.append(table_text)
        return tables


def parse_sql(sql_text):
    """
    Parse SQL text and return AST + syntax errors.

    Args:
        sql_text: The SQL text to parse

    Returns:
        dict: {
            "ast": dict representation of AST,
            "statement_type": str,
            "errors": [dict],
            "warnings": [dict],
            "tokens": [dict],
        }
    """
    tokens, token_errors = tokenize(sql_text)

    parser = HetuSQLParser(tokens, raw_sql=sql_text)
    result = parser.parse()

    ast_dict = result["ast"].to_dict() if result["ast"] else None

    return {
        "ast": ast_dict,
        "statement_type": result["statement_type"],
        "errors": [e.to_dict() for e in result["errors"]] + [
            {"message": str(e), "line": e.line, "column": e.column, "severity": "ERROR"}
            for e in token_errors
        ],
        "warnings": [w.to_dict() for w in result["warnings"]],
        "token_count": len(tokens),
    }


# ---- CLI Entry Point ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hetu_sql_parser.py <sql_text_or_file>")
        sys.exit(1)

    input_text = sys.argv[1]
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    result = parse_sql(input_text)

    print(f"Statement Type: {result['statement_type']}")
    print(f"Token Count: {result['token_count']}")
    print(f"Errors: {len(result['errors'])}")
    print(f"Warnings: {len(result['warnings'])}")
    print()

    if result['ast']:
        print("AST:")
        print(json.dumps(result['ast'], indent=2, ensure_ascii=False)[:2000])

    if result['errors']:
        print("\nErrors:")
        for e in result['errors']:
            print(f"  L{e['line']}:{e['column']} [{e['severity']}] {e['message']}")

    if '--json' in sys.argv:
        print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
