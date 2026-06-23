# -*- coding: utf-8 -*-
"""
DWS SQL Parser

Recursive descent parser for DWS SQL statements.
Parses token stream into AST and detects syntax errors.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))

from dws_sql_tokenizer import Token, TokenType, tokenize
from grammar_rules import (
    STATEMENT_RULES, DWS_SPECIFIC_GRAMMAR, MULTI_TOKEN_STATEMENTS,
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
            "raw_text": self.raw_text[:200],  # Truncate long text
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


class DWSSQLParser:
    """
    DWS SQL Recursive Descent Parser

    Parses token stream into AST following the DWS SQL grammar rules.
    Supports statement type detection, clause validation, and syntax error reporting.
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

        Returns:
            str: Statement type name (e.g., "SELECT", "CREATE TABLE", "ALTER TABLE")
        """
        # Try multi-token matches first (longest match)
        for token_seq, stmt_type in MULTI_TOKEN_STATEMENTS:
            match = True
            for i, expected in enumerate(token_seq):
                peek_token = self._peek(i) if i > 0 else self._current()
                if peek_token.type != TokenType.KEYWORD or peek_token.value.upper() != expected.upper():
                    match = False
                    break
            if match:
                return stmt_type

        # Single token match
        token = self._current()
        if token.type == TokenType.KEYWORD:
            upper = token.value.upper()
            if upper in SINGLE_TOKEN_STATEMENTS:
                return SINGLE_TOKEN_STATEMENTS[upper]

        # Unknown statement
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

        # Detect statement type
        stmt_type = self.detect_statement_type()

        # Parse based on statement type
        ast = None
        if stmt_type == "SELECT":
            ast = self._parse_select()
        elif stmt_type == "INSERT":
            ast = self._parse_insert()
        elif stmt_type == "UPDATE":
            ast = self._parse_update()
        elif stmt_type == "DELETE":
            ast = self._parse_delete()
        elif stmt_type == "MERGE":
            ast = self._parse_merge()
        elif stmt_type == "CREATE TABLE":
            ast = self._parse_create_table()
        elif stmt_type == "ALTER TABLE":
            ast = self._parse_alter_table()
        elif stmt_type == "DROP":
            ast = self._parse_drop()
        elif stmt_type == "EXPLAIN":
            ast = self._parse_explain()
        elif stmt_type in ("CREATE VIEW", "CREATE MATERIALIZED VIEW",
                          "CREATE INDEX", "TRUNCATE", "COPY", "VACUUM",
                          "SET", "SHOW", "GRANT", "REVOKE",
                          "BEGIN", "COMMIT", "ROLLBACK"):
            ast = self._parse_generic(stmt_type)
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
            with_tokens = self._collect_until("SELECT")
            node.children["with_clause"] = ASTNode("WithClause", tokens=with_tokens,
                                                     raw_text=self._tokens_to_text(with_tokens))

        # SELECT keyword
        if self._current().is_keyword("SELECT"):
            self._advance()

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = ASTNode("HintState", tokens=[hint_token],
                                            raw_text=hint_token.value)

        # DISTINCT / ALL
        if self._current().is_keyword("DISTINCT"):
            dist_token = self._advance()
            node.children["distinct"] = True
            # DISTINCT ON (...)
            if self._current().is_keyword("ON"):
                self._advance()
                on_tokens = self._collect_until("FROM", "WHERE", "GROUP", "HAVING",
                                                "WINDOW", "ORDER", "LIMIT", "UNION",
                                                "INTERSECT", "EXCEPT", "MINUS")
                node.children["distinct_on"] = self._tokens_to_text(on_tokens)
        elif self._current().is_keyword("ALL"):
            self._advance()
            node.children["distinct"] = False

        # Target list
        target_tokens = self._collect_until("FROM", "WHERE", "GROUP", "HAVING",
                                           "WINDOW", "ORDER", "LIMIT", "OFFSET", "FOR",
                                           "UNION", "INTERSECT", "EXCEPT", "MINUS")
        node.children["target_list"] = self._parse_target_list(target_tokens)

        # Check for SELECT *
        if self._has_select_star(target_tokens):
            node.children["has_select_star"] = True

        # INTO clause
        if self._current().is_keyword("INTO"):
            into_tokens = self._collect_until("FROM", "WHERE", "GROUP", "HAVING")
            node.children["into_clause"] = self._tokens_to_text(into_tokens)

        # FROM clause
        if self._current().is_keyword("FROM"):
            self._advance()
            from_tokens = self._collect_until("WHERE", "GROUP", "HAVING", "WINDOW",
                                             "ORDER", "LIMIT", "OFFSET", "FOR",
                                             "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["from_clause"] = self._parse_from_clause(from_tokens)

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("GROUP", "HAVING", "WINDOW", "ORDER",
                                              "LIMIT", "OFFSET", "FOR",
                                              "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["where_clause"] = self._tokens_to_text(where_tokens)

        # GROUP BY
        if self._current().is_keyword("GROUP"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            group_tokens = self._collect_until("HAVING", "WINDOW", "ORDER", "LIMIT",
                                              "OFFSET", "FOR",
                                              "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["group_by"] = self._tokens_to_text(group_tokens)

        # HAVING
        if self._current().is_keyword("HAVING"):
            self._advance()
            having_tokens = self._collect_until("WINDOW", "ORDER", "LIMIT", "OFFSET",
                                               "FOR", "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["having"] = self._tokens_to_text(having_tokens)

        # WINDOW
        if self._current().is_keyword("WINDOW"):
            self._advance()
            win_tokens = self._collect_until("ORDER", "LIMIT", "OFFSET", "FOR",
                                            "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["window"] = self._tokens_to_text(win_tokens)

        # ORDER BY
        if self._current().is_keyword("ORDER"):
            self._advance()
            if self._current().is_keyword("BY"):
                self._advance()
            order_tokens = self._collect_until("LIMIT", "OFFSET", "FOR",
                                              "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["order_by"] = self._tokens_to_text(order_tokens)

        # LIMIT
        if self._current().is_keyword("LIMIT"):
            self._advance()
            limit_tokens = self._collect_until("OFFSET", "FOR",
                                              "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["limit"] = self._tokens_to_text(limit_tokens)

        # OFFSET
        if self._current().is_keyword("OFFSET"):
            self._advance()
            offset_tokens = self._collect_until("FOR",
                                               "UNION", "INTERSECT", "EXCEPT", "MINUS")
            node.children["offset"] = self._tokens_to_text(offset_tokens)

        # FOR UPDATE/SHARE
        if self._current().is_keyword("FOR"):
            for_tokens = [self._advance()]
            while not self._at_end() and not self._current().is_keyword("UNION"):
                for_tokens.append(self._advance())
            node.children["locking_clause"] = self._tokens_to_text(for_tokens)

        # Set operations (UNION/INTERSECT/EXCEPT/MINUS)
        if self._current().is_keyword("UNION") or self._current().is_keyword("INTERSECT") or \
           self._current().is_keyword("EXCEPT") or self._current().is_keyword("MINUS"):
            op_token = self._advance()
            all_flag = False
            if self._current().is_keyword("ALL"):
                self._advance()
                all_flag = True
            node.children["set_operation"] = op_token.value
            node.children["set_all"] = all_flag

        # Oracle (+) join detection
        for t in self.tokens:
            if t.type == TokenType.ORA_JOINOP:
                node.children["has_ora_joinop"] = True
                break

        # Build location
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

        # REPLACE INTO
        if self._current().is_keyword("REPLACE"):
            self._advance()
            node.children["is_replace"] = True

        # INSERT
        if self._current().is_keyword("INSERT"):
            self._advance()

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = ASTNode("HintState", tokens=[hint_token],
                                            raw_text=hint_token.value)

        # OVERWRITE
        if self._current().is_keyword("OVERWRITE"):
            self._advance()
            node.children["is_overwrite"] = True

        # IGNORE
        if self._current().is_keyword("IGNORE"):
            self._advance()
            node.children["is_ignore"] = True

        # INTO
        if self._current().is_keyword("INTO"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("VALUES", "SELECT", "DEFAULT",
                                          "ON", "RETURNING", "WITH",
                                          stop_types=[TokenType.LPAREN])
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # Column list
        if self._current().type == TokenType.LPAREN:
            col_tokens = self._collect_balanced_parens()
            node.children["columns"] = self._tokens_to_text(col_tokens)

        # VALUES or SELECT or DEFAULT VALUES
        if self._current().is_keyword("VALUES"):
            self._advance()
            values_tokens = self._collect_until("ON", "RETURNING")
            node.children["values"] = self._tokens_to_text(values_tokens)
        elif self._current().is_keyword("SELECT"):
            # Subquery
            node.children["subquery"] = True
        elif self._current().is_keyword("DEFAULT"):
            self._advance()
            if self._current().is_keyword("VALUES"):
                self._advance()
            node.children["default_values"] = True

        # ON CONFLICT / ON DUPLICATE KEY UPDATE
        if self._current().is_keyword("ON"):
            on_token = self._advance()
            if self._current().is_keyword("CONFLICT"):
                self._advance()
                node.children["on_conflict"] = "CONFLICT"
            elif self._current().is_keyword("DUPLICATE"):
                self._advance()
                if self._current().is_keyword("KEY"):
                    self._advance()
                node.children["on_conflict"] = "DUPLICATE_KEY"

        # RETURNING
        if self._current().is_keyword("RETURNING"):
            self._advance()
            ret_tokens = self._collect_until("SEMICOLON")
            node.children["returning"] = self._tokens_to_text(ret_tokens)

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

        self._advance()  # skip UPDATE

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = ASTNode("HintState", tokens=[hint_token],
                                            raw_text=hint_token.value)

        # Table name
        table_tokens = self._collect_until("SET")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # SET clause
        if self._current().is_keyword("SET"):
            self._advance()
            set_tokens = self._collect_until("FROM", "WHERE", "RETURNING")
            node.children["set_clause"] = self._tokens_to_text(set_tokens)

        # FROM clause
        if self._current().is_keyword("FROM"):
            self._advance()
            from_tokens = self._collect_until("WHERE", "RETURNING")
            node.children["from_clause"] = self._tokens_to_text(from_tokens)

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("RETURNING")
            node.children["where_clause"] = self._tokens_to_text(where_tokens)
        else:
            node.children["missing_where"] = True

        # RETURNING
        if self._current().is_keyword("RETURNING"):
            self._advance()
            ret_tokens = self._collect_until("SEMICOLON")
            node.children["returning"] = self._tokens_to_text(ret_tokens)

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

        self._advance()  # skip DELETE

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = ASTNode("HintState", tokens=[hint_token],
                                            raw_text=hint_token.value)

        # FROM
        if self._current().is_keyword("FROM"):
            self._advance()

        # Table name
        table_tokens = self._collect_until("USING", "WHERE", "RETURNING")
        node.children["table"] = self._tokens_to_text(table_tokens).strip()

        # USING clause
        if self._current().is_keyword("USING"):
            self._advance()
            using_tokens = self._collect_until("WHERE", "RETURNING")
            node.children["using_clause"] = self._tokens_to_text(using_tokens)

        # WHERE clause
        if self._current().is_keyword("WHERE"):
            self._advance()
            where_tokens = self._collect_until("RETURNING")
            node.children["where_clause"] = self._tokens_to_text(where_tokens)
        else:
            node.children["missing_where"] = True

        # RETURNING
        if self._current().is_keyword("RETURNING"):
            self._advance()
            ret_tokens = self._collect_until("SEMICOLON")
            node.children["returning"] = self._tokens_to_text(ret_tokens)

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # MERGE Statement Parser
    # ============================================================

    def _parse_merge(self):
        """Parse MERGE statement"""
        node = ASTNode("MergeStmt")
        start_token = self._current()

        self._advance()  # skip MERGE

        # Hint
        if self._current().type == TokenType.HINT:
            hint_token = self._advance()
            node.children["hint"] = ASTNode("HintState", tokens=[hint_token],
                                            raw_text=hint_token.value)

        # INTO
        if self._current().is_keyword("INTO"):
            self._advance()

        # Target table
        target_tokens = self._collect_until("USING")
        node.children["target_table"] = self._tokens_to_text(target_tokens).strip()

        # USING
        if self._current().is_keyword("USING"):
            self._advance()
            source_tokens = self._collect_until("ON")
            node.children["source"] = self._tokens_to_text(source_tokens).strip()

        # ON condition
        if self._current().is_keyword("ON"):
            self._advance()
            on_tokens = self._collect_until("WHEN")
            node.children["join_condition"] = self._tokens_to_text(on_tokens).strip()

        # WHEN clauses
        when_clauses = []
        while self._current().is_keyword("WHEN"):
            self._advance()
            matched = True
            if self._current().is_keyword("NOT"):
                self._advance()
                matched = False
            if self._current().is_keyword("MATCHED"):
                self._advance()
            # THEN
            if self._current().is_keyword("THEN"):
                self._advance()
            # Collect the rest
            action_tokens = self._collect_until("WHEN")
            when_clauses.append({
                "matched": matched,
                "action": self._tokens_to_text(action_tokens).strip(),
            })
        node.children["when_clauses"] = when_clauses

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # CREATE TABLE Parser
    # ============================================================

    def _parse_create_table(self):
        """Parse CREATE TABLE statement"""
        node = ASTNode("CreateStmt")
        start_token = self._current()

        self._advance()  # skip CREATE

        # TEMPORARY / TEMP
        if self._current().is_keyword("TEMPORARY") or self._current().is_keyword("TEMP"):
            temp_token = self._advance()
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

        # Table name (collect until LPAREN or next keyword)
        table_name_parts = []
        while not self._at_end():
            t = self._current()
            if t.type == TokenType.LPAREN:
                break
            if t.type == TokenType.KEYWORD and t.value.upper() in (
                "INHERITS", "WITH", "ON", "COMPRESS", "PARTITION",
                "DISTRIBUTE", "TO", "COMMENT", "LIKE", "AS", "OF"):
                break
            table_name_parts.append(self._advance())
        node.children["table_name"] = self._tokens_to_text(table_name_parts).strip()

        # Column/constraint definitions
        if self._current().type == TokenType.LPAREN:
            col_tokens = self._collect_balanced_parens()
            node.children["columns"] = self._tokens_to_text(col_tokens)
            # Check for primary key
            col_text = self._tokens_to_text(col_tokens).upper()
            node.children["has_primary_key"] = "PRIMARY KEY" in col_text or "PRIMARY" in col_text

        # Scan remaining tokens for DWS extensions
        remaining = []
        while not self._at_end():
            token = self._current()
            remaining.append(token)

            # INHERITS
            if token.is_keyword("INHERITS"):
                self._advance()
                inh_tokens = self._collect_until("WITH", "ON", "COMPRESS", "PARTITION",
                                                "DISTRIBUTE", "TO", "COMMENT")
                node.children["inherits"] = self._tokens_to_text(inh_tokens).strip()

            # WITH options
            elif token.is_keyword("WITH") and not self._peek().is_keyword("CHECK") and \
                 not self._peek().is_keyword("DATA") and not self._peek().is_keyword("TIME"):
                self._advance()
                if self._current().type == TokenType.LPAREN:
                    with_tokens = self._collect_balanced_parens()
                    node.children["with_options"] = self._tokens_to_text(with_tokens)

            # ON COMMIT
            elif token.is_keyword("ON") and self._peek().is_keyword("COMMIT"):
                self._advance()
                on_tokens = self._collect_until("COMPRESS", "PARTITION", "DISTRIBUTE", "TO", "COMMENT")
                node.children["on_commit"] = self._tokens_to_text(on_tokens).strip()

            # COMPRESS
            elif token.is_keyword("COMPRESS"):
                self._advance()
                comp_tokens = self._collect_until("PARTITION", "DISTRIBUTE", "TO", "COMMENT")
                node.children["compress"] = self._tokens_to_text(comp_tokens).strip()

            # PARTITION BY
            elif token.is_keyword("PARTITION"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                part_tokens = self._collect_until("DISTRIBUTE", "TO", "COMMENT")
                node.children["partition"] = self._tokens_to_text(part_tokens).strip()

            # DISTRIBUTE BY
            elif token.is_keyword("DISTRIBUTE"):
                self._advance()
                if self._current().is_keyword("BY"):
                    self._advance()
                # Distribution type
                dist_type = self._current().value.upper()
                if dist_type in ("HASH", "MODULO", "REPLICATION", "ROUNDROBIN"):
                    node.children["distribute_type"] = dist_type
                    self._advance()
                    # Column list for HASH/MODULO
                    if self._current().type == TokenType.LPAREN:
                        dist_tokens = self._collect_balanced_parens()
                        node.children["distribute_columns"] = self._tokens_to_text(dist_tokens).strip()
                else:
                    node.children["distribute_type"] = dist_type
                    self._advance()

            # TO NODE/GROUP
            elif token.is_keyword("TO"):
                self._advance()
                if self._current().is_keyword("NODE"):
                    self._advance()
                    node_tokens = self._collect_until("PARTITION", "COMMENT")
                    node.children["to_node"] = self._tokens_to_text(node_tokens).strip()
                elif self._current().is_keyword("GROUP"):
                    self._advance()
                    group_tokens = self._collect_until("PARTITION", "COMMENT")
                    node.children["to_group"] = self._tokens_to_text(group_tokens).strip()

            # COMMENT
            elif token.is_keyword("COMMENT"):
                self._advance()
                if self._current().type == TokenType.SCONST:
                    node.children["comment"] = self._advance().value

            # LIKE
            elif token.is_keyword("LIKE"):
                self._advance()
                like_tokens = self._collect_until("WITH", "DISTRIBUTE", "TO", "COMMENT")
                node.children["like"] = self._tokens_to_text(like_tokens).strip()

            else:
                self._advance()

        node.tokens = [start_token]
        node.raw_text = self._get_raw_text(start_token)
        return node

    # ============================================================
    # ALTER TABLE Parser
    # ============================================================

    def _parse_alter_table(self):
        """Parse ALTER TABLE statement"""
        node = ASTNode("AlterTableStmt")
        start_token = self._current()

        self._advance()  # skip ALTER

        # Object type
        obj_type = "TABLE"
        if self._current().is_keyword("TABLE"):
            self._advance()
        elif self._current().is_keyword("INDEX"):
            obj_type = "INDEX"
            self._advance()
        elif self._current().is_keyword("SEQUENCE"):
            obj_type = "SEQUENCE"
            self._advance()
        elif self._current().is_keyword("VIEW"):
            obj_type = "VIEW"
            self._advance()
        node.children["object_type"] = obj_type

        # IF EXISTS
        if self._current().is_keyword("IF"):
            self._advance()
            if self._current().is_keyword("EXISTS"):
                self._advance()
            node.children["if_exists"] = True

        # Table name
        table_tokens = self._collect_until("ADD", "DROP", "ALTER", "MODIFY", "RENAME",
                                          "DISTRIBUTE", "EXCHANGE", "PARTITION", "SET", "RESET")
        node.children["table_name"] = self._tokens_to_text(table_tokens).strip()

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

    def _parse_drop(self):
        """Parse DROP statement"""
        node = ASTNode("DropStmt")
        start_token = self._current()

        self._advance()  # skip DROP

        # Object type
        obj_types = ["TABLE", "INDEX", "VIEW", "SEQUENCE", "SCHEMA", "DATABASE",
                    "FUNCTION", "PROCEDURE", "TRIGGER", "TYPE", "DOMAIN", "ROLE",
                    "USER", "GROUP", "TABLESPACE", "EXTENSION", "FOREIGN",
                    "SYNONYM", "MATERIALIZED", "NODE", "OUTLINE", "DIRECTORY",
                    "PUBLICATION", "SUBSCRIPTION", "RESOURCE", "WORKLOAD"]
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
    # EXPLAIN Parser
    # ============================================================

    def _parse_explain(self):
        """Parse EXPLAIN statement"""
        node = ASTNode("ExplainStmt")
        start_token = self._current()

        self._advance()  # skip EXPLAIN

        # Options
        if self._current().is_keyword("ANALYZE") or self._current().is_keyword("ANALYSE"):
            self._advance()
            node.children["analyze"] = True
        if self._current().is_keyword("VERBOSE"):
            self._advance()
            node.children["verbose"] = True
        if self._current().is_keyword("PERFORMANCE"):
            self._advance()
            node.children["performance"] = True
        if self._current().is_keyword("WARMUP"):
            self._advance()
            node.children["warmup"] = True
        if self._current().is_keyword("PLAN"):
            self._advance()
            node.children["plan"] = True

        # Options in parentheses
        if self._current().type == TokenType.LPAREN:
            opt_tokens = self._collect_balanced_parens()
            node.children["options"] = self._tokens_to_text(opt_tokens)

        # The explained statement
        remaining = []
        while not self._at_end():
            remaining.append(self._advance())
        node.children["statement"] = self._tokens_to_text(remaining).strip()

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
        """Check if target list contains SELECT *"""
        i = 0
        while i < len(target_tokens):
            t = target_tokens[i]
            if t.type == TokenType.STAR:
                # Check if it's a top-level * (not table.*)
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
                    "is_star": any(tt.type == TokenType.STAR for tt in tokens[tokens.index(t) - len(current):tokens.index(t)] if current),
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
    # Tokenize first
    tokens, token_errors = tokenize(sql_text)

    # Parse
    parser = DWSSQLParser(tokens, raw_sql=sql_text)
    result = parser.parse()

    # Build output
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
        print("Usage: python dws_sql_parser.py <sql_text_or_file>")
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
