# -*- coding: utf-8 -*-
"""
MRS Hive SQL Parser

Recursive descent parser for MRS Hive SQL statements.
Parses token stream into AST and detects syntax errors.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))

from hive_sql_tokenizer import Token, TokenType, tokenize
from grammar_rules import (
    STATEMENT_RULES, MULTI_TOKEN_STATEMENTS,
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


class HiveSQLParser:
    """
    MRS Hive SQL Recursive Descent Parser

    Parses token stream into AST following the HiveQL grammar rules.
    Supports Hive-specific syntax including PARTITIONED BY, CLUSTERED BY,
    STORED AS, ROW FORMAT, INSERT OVERWRITE, LATERAL VIEW, etc.
    """

    def __init__(self, tokens, raw_sql=""):
        self.tokens = tokens
        self.raw_sql = raw_sql
        self.pos = 0
        self.errors = []
        self.warnings = []

    def _current(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, '', 0, 0)

    def _peek(self, offset=1):
        p = self.pos + offset
        if p < len(self.tokens):
            return self.tokens[p]
        return Token(TokenType.EOF, '', 0, 0)

    def _advance(self):
        token = self._current()
        if self.pos < len(self.tokens):
            self.pos += 1
        return token

    def _expect(self, type_=None, value=None, or_eof=False):
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
        token = self._current()
        if type_ and token.type != type_:
            return None
        if value and token.value.upper() != value.upper():
            return None
        return self._advance()

    def _at_end(self):
        return self._current().type == TokenType.EOF or self._current().type == TokenType.SEMICOLON

    def _collect_until(self, *stop_values, stop_types=None, nested_parens=True):
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
        for token_seq, stmt_type in MULTI_TOKEN_STATEMENTS:
            match = True
            for i, expected in enumerate(token_seq):
                peek_token = self._peek(i) if i > 0 else self._current()
                if peek_token.type != TokenType.KEYWORD or peek_token.value.upper() != expected.upper():
                    match = False
                    break
            if match:
                return stmt_type

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
        elif stmt_type in ("INSERT", "INSERT OVERWRITE"):
            ast = self._parse_insert()
        elif stmt_type == "UPDATE":
            ast = self._parse_update()
        elif stmt_type == "DELETE":
            ast = self._parse_delete()
        elif stmt_type in ("CREATE TABLE", "CREATE EXTERNAL TABLE", "CREATE TEMPORARY TABLE"):
            ast = self._parse_create_table()
        elif stmt_type == "ALTER TABLE":
            ast = self._parse_alter_table()
        elif stmt_type == "DROP TABLE":
            ast = self._parse_drop()
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
        node = ASTNode("SelectStmt")
        start_token = self._current()

        # WITH clause (CTE)
        if self._current().is_keyword("WITH"):
            with_tokens = self._collect_until("SELECT")
            node.children["with_clause"] = ASTNode("WithClause", tokens=with_tokens,
                                                     raw_text=self._tokens_to_text(with_tokens))

        # SELECT keyword
        if self._current().is_keyword("SELECT"):
            self._advance()

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = hint_token.value

        # DISTINCT / ALL
        if self._current().is_keyword("DISTINCT"):
            self._advance()
            node.children["distinct"] = True
        elif self._current().is_keyword("ALL"):
            self._advance()
            node.children["distinct"] = False

        # Target list
        target_tokens = self._collect_until("FROM", "WHERE", "GROUP", "HAVING",
                                           "ORDER", "LIMIT", "UNION",
                                           "INTERSECT", "EXCEPT", "LATERAL",
                                           "CLUSTER", "DISTRIBUTE", "SORT",
                                           "TABLESAMPLE")
        node.children["target_list"] = self._parse_target_list(target_tokens)

        # Check for SELECT *
        if self._has_select_star(target_tokens):
            node.children["has_select_star"] = True

        # FROM clause
        if self._current().is_keyword("FROM"):
            self._advance()
            from_tokens = self._collect_until("WHERE", "GROUP", "HAVING",
                                             "ORDER", "LIMIT", "UNION",
                                             "INTERSECT", "EXCEPT", "LATERAL",
                                             "CLUSTER", "DISTRIBUTE", "SORT",
                                             "TABLESAMPLE")
            node.children["from_clause"] = self._parse_from_clause(from_tokens)

        # TABLESAMPLE
        if self._current().is_keyword("TABLESAMPLE"):
            self._advance()
            ts_tokens = self._collect_until("WHERE", "GROUP", "HAVING",
                                            "ORDER", "LIMIT", "UNION",
                                            "INTERSECT", "EXCEPT", "LATERAL",
                                            "CLUSTER", "DISTRIBUTE", "SORT")
            node.children["tablesample"] = self._tokens_to_text(ts_tokens).strip()

        # LATERAL VIEW (with optional OUTER)
        while self._current().is_keyword("LATERAL"):
            self._advance()
            if self._current().is_keyword("VIEW"):
                self._advance()
            # LATERAL VIEW OUTER
            if self._current().is_keyword("OUTER"):
                self._advance()
            lateral_tokens = self._collect_until("WHERE", "GROUP", "HAVING",
                                                "ORDER", "LIMIT", "UNION",
                                                "INTERSECT", "EXCEPT", "LATERAL",
                                                "CLUSTER", "DISTRIBUTE", "SORT")
            if "lateral_views" not in node.children:
                node.children["lateral_views"] = []
            node.children["lateral_views"].append(self._tokens_to_text(lateral_tokens).strip())

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("GROUP", "HAVING", "ORDER",
                                              "LIMIT", "UNION",
                                              "INTERSECT", "EXCEPT",
                                              "CLUSTER", "DISTRIBUTE", "SORT")
            node.children["where_clause"] = self._tokens_to_text(where_tokens).strip()

        # GROUP BY
        if self._current().is_keyword("GROUP"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            group_tokens = self._collect_until("HAVING", "ORDER", "LIMIT",
                                              "UNION", "INTERSECT", "EXCEPT",
                                              "CLUSTER", "DISTRIBUTE", "SORT")
            node.children["group_by"] = self._tokens_to_text(group_tokens).strip()

        # HAVING
        if self._current().is_keyword("HAVING"):
            self._advance()
            having_tokens = self._collect_until("ORDER", "LIMIT", "UNION",
                                               "INTERSECT", "EXCEPT",
                                               "CLUSTER", "DISTRIBUTE", "SORT")
            node.children["having"] = self._tokens_to_text(having_tokens).strip()

        # ORDER BY
        if self._current().is_keyword("ORDER"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            order_tokens = self._collect_until("LIMIT", "UNION",
                                              "INTERSECT", "EXCEPT",
                                              "CLUSTER", "DISTRIBUTE", "SORT")
            node.children["order_by"] = self._tokens_to_text(order_tokens).strip()

        # DISTRIBUTE BY
        if self._current().is_keyword("DISTRIBUTE"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            dist_tokens = self._collect_until("SORT", "CLUSTER", "LIMIT",
                                             "UNION", "INTERSECT", "EXCEPT")
            node.children["distribute_by"] = self._tokens_to_text(dist_tokens).strip()

        # SORT BY
        if self._current().is_keyword("SORT"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            sort_tokens = self._collect_until("CLUSTER", "LIMIT",
                                             "UNION", "INTERSECT", "EXCEPT")
            node.children["sort_by"] = self._tokens_to_text(sort_tokens).strip()

        # CLUSTER BY
        if self._current().is_keyword("CLUSTER"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            cluster_tokens = self._collect_until("LIMIT", "UNION",
                                                "INTERSECT", "EXCEPT")
            node.children["cluster_by"] = self._tokens_to_text(cluster_tokens).strip()

        # LIMIT
        if self._current().is_keyword("LIMIT"):
            self._advance()
            limit_tokens = self._collect_until("UNION", "INTERSECT", "EXCEPT")
            node.children["limit"] = self._tokens_to_text(limit_tokens).strip()

        # Set operations
        if self._current().is_keyword("UNION") or self._current().is_keyword("INTERSECT") or \
           self._current().is_keyword("EXCEPT") or self._current().is_keyword("MINUS"):
            op_token = self._advance()
            all_flag = False
            if self._current().is_keyword("ALL"):
                self._advance()
                all_flag = True
            node.children["set_operation"] = op_token.value
            node.children["set_all"] = all_flag

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # INSERT Statement Parser
    # ============================================================

    def _parse_insert(self):
        node = ASTNode("InsertStmt")
        start_token = self._current()

        # INSERT
        if self._current().is_keyword("INSERT"):
            self._advance()

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = hint_token.value

        # OVERWRITE
        if self._current().is_keyword("OVERWRITE"):
            self._advance()
            node.children["is_overwrite"] = True

        # INTO / TABLE
        if self._current().is_keyword("INTO"):
            self._advance()
        elif self._current().is_keyword("TABLE"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("PARTITION", "VALUES", "SELECT",
                                          "WITH", stop_types=[TokenType.LPAREN])
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # Column list
        if self._current().type == TokenType.LPAREN:
            # Check if this is PARTITION or column list
            # Look ahead for PARTITION keyword
            if not node.children.get("is_overwrite"):
                col_tokens = self._collect_balanced_parens()
                node.children["columns"] = self._tokens_to_text(col_tokens)

        # PARTITION spec
        if self._current().is_keyword("PARTITION"):
            self._advance()
            if self._current().type == TokenType.LPAREN:
                part_tokens = self._collect_balanced_parens()
                node.children["partition"] = self._tokens_to_text(part_tokens).strip()

        # VALUES or SELECT
        if self._current().is_keyword("VALUES"):
            self._advance()
            values_tokens = self._collect_until("SEMICOLON")
            node.children["values"] = self._tokens_to_text(values_tokens).strip()
        elif self._current().is_keyword("SELECT"):
            node.children["subquery"] = True
        elif self._current().is_keyword("WITH"):
            node.children["subquery"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # UPDATE Statement Parser
    # ============================================================

    def _parse_update(self):
        node = ASTNode("UpdateStmt")
        start_token = self._current()

        self._advance()  # skip UPDATE

        # Table name
        table_tokens = self._collect_until("SET")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # SET clause
        if self._current().is_keyword("SET"):
            self._advance()
            set_tokens = self._collect_until("WHERE")
            node.children["set_clause"] = self._tokens_to_text(set_tokens).strip()

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("SEMICOLON")
            node.children["where_clause"] = self._tokens_to_text(where_tokens).strip()
        else:
            node.children["missing_where"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # DELETE Statement Parser
    # ============================================================

    def _parse_delete(self):
        node = ASTNode("DeleteStmt")
        start_token = self._current()

        self._advance()  # skip DELETE

        # FROM
        if self._current().is_keyword("FROM"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("WHERE")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("SEMICOLON")
            node.children["where_clause"] = self._tokens_to_text(where_tokens).strip()
        else:
            node.children["missing_where"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE TABLE Parser
    # ============================================================

    def _parse_create_table(self):
        node = ASTNode("CreateStmt")
        start_token = self._current()

        self._advance()  # skip CREATE

        # EXTERNAL
        if self._current().is_keyword("EXTERNAL"):
            self._advance()
            node.children["is_external"] = True

        # TEMPORARY
        if self._current().is_keyword("TEMPORARY"):
            self._advance()
            node.children["is_temporary"] = True

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
                "COMMENT", "PARTITIONED", "CLUSTERED", "ROW", "STORED",
                "LOCATION", "TBLPROPERTIES", "AS", "LIKE",
                "SKEWED", "CONSTRAINT"):
                break
            table_name_parts.append(self._advance())
        node.children["table_name"] = self._tokens_to_text(table_name_parts).strip()

        # Column/constraint definitions
        if self._current().type == TokenType.LPAREN:
            col_tokens = self._collect_balanced_parens()
            node.children["columns"] = self._tokens_to_text(col_tokens)
            col_text = self._tokens_to_text(col_tokens).upper()
            node.children["has_primary_key"] = "PRIMARY KEY" in col_text
            node.children["has_foreign_key"] = "FOREIGN KEY" in col_text
            node.children["has_references"] = "REFERENCES" in col_text
            node.children["has_check"] = "CHECK" in col_text
            node.children["has_constraint"] = "CONSTRAINT" in col_text

        # Scan remaining tokens for Hive extensions
        while not self._at_end():
            token = self._current()

            # COMMENT
            if token.is_keyword("COMMENT") and "columns" in node.children:
                self._advance()
                if self._current().type == TokenType.SCONST:
                    node.children["comment"] = self._advance().value

            # PARTITIONED BY
            elif token.is_keyword("PARTITIONED"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                if self._current().type == TokenType.LPAREN:
                    part_tokens = self._collect_balanced_parens()
                    node.children["partitioned_by"] = self._tokens_to_text(part_tokens).strip()
                    # Count partition columns
                    part_text = self._tokens_to_text(part_tokens)
                    node.children["partition_count"] = part_text.count(',') + 1

            # CLUSTERED BY
            elif token.is_keyword("CLUSTERED"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                if self._current().type == TokenType.LPAREN:
                    cluster_tokens = self._collect_balanced_parens()
                    node.children["clustered_by"] = self._tokens_to_text(cluster_tokens).strip()

                # SORTED BY
                if self._current().is_keyword("SORTED"):
                    self._advance()
                    if self._current().is_keyword("BY"):
                        self._advance()
                    if self._current().type == TokenType.LPAREN:
                        sort_tokens = self._collect_balanced_parens()
                        node.children["sorted_by"] = self._tokens_to_text(sort_tokens).strip()

                # INTO N BUCKETS
                if self._current().is_keyword("INTO"):
                    self._advance()
                    bucket_tokens = self._collect_until("BUCKETS", "ROW", "STORED",
                                                        "LOCATION", "TBLPROPERTIES",
                                                        "COMMENT", "AS", "SKEWED")
                    if self._current().is_keyword("BUCKETS"):
                        self._advance()
                    node.children["num_buckets"] = self._tokens_to_text(bucket_tokens).strip()

            # SKEWED BY
            elif token.is_keyword("SKEWED"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                if self._current().type == TokenType.LPAREN:
                    skew_tokens = self._collect_balanced_parens()
                    node.children["skewed_by"] = self._tokens_to_text(skew_tokens).strip()
                # optional ON ((val1, val2), ...)
                if self._current().is_keyword("ON"):
                    self._advance()
                    if self._current().type == TokenType.LPAREN:
                        on_tokens = self._collect_balanced_parens()
                        node.children["skewed_on"] = self._tokens_to_text(on_tokens).strip()
                # optional STORED AS DIRECTORIES
                if self._current().is_keyword("STORED"):
                    self._advance()
                    if self._current().is_keyword("AS"):
                        self._advance()
                    if self._current().is_keyword("DIRECTORIES"):
                        self._advance()
                        node.children["skewed_directories"] = True

            # STORED BY (storage handler)
            elif token.is_keyword("STORED") and self._peek().is_keyword("BY"):
                self._advance()  # STORED
                self._advance()  # BY
                sb_tokens = self._collect_until("LOCATION", "TBLPROPERTIES",
                                                "COMMENT", "AS", "SKEWED")
                node.children["stored_by"] = self._tokens_to_text(sb_tokens).strip()

            # ROW FORMAT
            elif token.is_keyword("ROW"):
                self._advance()
                if self._current().is_keyword("FORMAT"):
                    self._advance()
                # Collect the rest of ROW FORMAT spec
                rf_tokens = self._collect_until("STORED", "LOCATION", "TBLPROPERTIES",
                                                "COMMENT", "AS")
                node.children["row_format"] = self._tokens_to_text(rf_tokens).strip()

            # STORED AS
            elif token.is_keyword("STORED"):
                self._advance()
                if self._current().is_keyword("AS"):
                    self._advance()
                # Get storage format
                if self._current().type == TokenType.KEYWORD:
                    node.children["stored_as"] = self._advance().value.upper()
                elif self._current().type == TokenType.SCONST:
                    node.children["stored_as"] = self._advance().value
                else:
                    # INPUTFORMAT/OUTPUTFORMAT
                    stored_tokens = self._collect_until("LOCATION", "TBLPROPERTIES",
                                                        "COMMENT", "AS")
                    node.children["stored_as"] = self._tokens_to_text(stored_tokens).strip()

            # LOCATION
            elif token.is_keyword("LOCATION"):
                self._advance()
                if self._current().type == TokenType.SCONST:
                    node.children["location"] = self._advance().value

            # TBLPROPERTIES
            elif token.is_keyword("TBLPROPERTIES"):
                self._advance()
                if self._current().type == TokenType.LPAREN:
                    prop_tokens = self._collect_balanced_parens()
                    node.children["tblproperties"] = self._tokens_to_text(prop_tokens).strip()

            # AS SELECT (CTAS)
            elif token.is_keyword("AS"):
                self._advance()
                node.children["as_select"] = True

            # LIKE
            elif token.is_keyword("LIKE"):
                self._advance()
                like_tokens = self._collect_until("STORED", "LOCATION", "TBLPROPERTIES",
                                                  "COMMENT", "ROW")
                node.children["like_table"] = self._tokens_to_text(like_tokens).strip()

            else:
                self._advance()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # ALTER TABLE Parser
    # ============================================================

    def _parse_alter_table(self):
        node = ASTNode("AlterTableStmt")
        start_token = self._current()

        self._advance()  # skip ALTER

        # TABLE
        if self._current().is_keyword("TABLE"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("ADD", "DROP", "ALTER", "MODIFY", "RENAME",
                                          "SET", "REPLACE", "CHANGE", "ARCHIVE",
                                          "UNARCHIVE", "TOUCH", "CLUSTERED",
                                          "NOT", "COMPACT", "CONCATENATE",
                                          "PARTITION", "CASCADE", "EXCHANGE")
        node.children["table_name"] = self._tokens_to_text(table_tokens).strip()

        # Remaining actions
        action_tokens = []
        while not self._at_end():
            action_tokens.append(self._advance())
        node.children["actions"] = self._tokens_to_text(action_tokens).strip()

        # Check for CASCADE
        if "CASCADE" in node.children.get("actions", "").upper():
            node.children["has_cascade"] = True

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # DROP Parser
    # ============================================================

    def _parse_drop(self):
        node = ASTNode("DropStmt")
        start_token = self._current()

        self._advance()  # skip DROP

        # Object type
        obj_types = ["TABLE", "INDEX", "VIEW", "DATABASE", "SCHEMA", "FUNCTION",
                    "MATERIALIZED", "PROCEDURE", "PACKAGE"]
        obj_type = None
        for ot in obj_types:
            if self._current().is_keyword(ot):
                obj_type = ot
                self._advance()
                break
        node.children["object_type"] = obj_type or "UNKNOWN"

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
    # Generic Parser (fallback)
    # ============================================================

    def _parse_generic(self, stmt_type):
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
        return " ".join(t.value for t in tokens)

    def _get_raw_text(self, start_token):
        if start_token:
            return f"[L{start_token.line}:{start_token.column} ...]"
        return ""

    def _collect_balanced_parens(self):
        if self._current().type != TokenType.LPAREN:
            return []
        result = [self._advance()]  # (
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
        i = 0
        while i < len(target_tokens):
            t = target_tokens[i]
            if t.type == TokenType.STAR:
                prev = target_tokens[i - 1] if i > 0 else None
                nxt = target_tokens[i + 1] if i + 1 < len(target_tokens) else None
                # Skip table.column.* pattern (t1.*)
                if prev is not None and prev.type == TokenType.DOT:
                    pass
                # Skip aggregate functions like COUNT(*), SUM(*)
                elif prev is not None and prev.type == TokenType.LPAREN:
                    pass
                # Skip multiplication: STAR after RPAREN (e.g. sum(x)*100),
                # IDENT (e.g. segment*50), ICONST/FCONST (e.g. 100*50)
                elif prev is not None and prev.type in (TokenType.RPAREN, TokenType.IDENT,
                                                         TokenType.ICONST, TokenType.FCONST):
                    pass
                # Skip multiplication: STAR before ICONST/FCONST/IDENT/LPAREN
                # (e.g. *100, *col, *func(...))
                elif nxt is not None and nxt.type in (TokenType.ICONST, TokenType.FCONST,
                                                       TokenType.IDENT, TokenType.LPAREN):
                    pass
                else:
                    return True
            i += 1
        return False

    def _parse_target_list(self, tokens):
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
                targets.append({"text": " ".join(current).strip()})
                current = []
            else:
                current.append(t.value)
        if current:
            targets.append({"text": " ".join(current).strip()})
        return targets

    def _parse_from_clause(self, tokens):
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
    """
    tokens, token_errors = tokenize(sql_text)

    parser = HiveSQLParser(tokens, raw_sql=sql_text)
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
    import json

    if len(sys.argv) < 2:
        print("Usage: python hive_sql_parser.py <sql_text_or_file>")
        sys.exit(1)

    input_text = sys.argv[1]
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    result = parse_sql(input_text)

    print(f"Statement Type: {result['statement_type']}")
    print(f"Token Count: {result['token_count']}")
    print(f"Errors: {len(result['errors'])}")
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
