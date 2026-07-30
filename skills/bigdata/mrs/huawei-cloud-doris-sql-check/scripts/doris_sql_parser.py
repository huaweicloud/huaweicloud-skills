# -*- coding: utf-8 -*-
"""
Apache Doris SQL Parser

Recursive descent parser for Apache Doris SQL statements (based on Doris 3.1.4 Nereids grammar).
Generates a simplified AST and detects syntax errors.

Source: Doris 3.1.4 fe/fe-core/src/main/antlr4/org/apache/doris/nereids/DorisParser.g4
"""

import sys
import os
import re

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'rules'))
sys.path.insert(0, _THIS_DIR)

from doris_sql_tokenizer import tokenize, TokenType, Token
from keywords import is_keyword, is_reserved_keyword, KeywordCategory
from grammar_rules import (
    STATEMENT_RULES, detect_statement_type, StatementCategory,
    DORIS_DATA_TYPES, AGGREGATION_TYPES
)


class ParseError(Exception):
    """Error during parsing"""

    def __init__(self, message, line=0, column=0):
        super().__init__(message)
        self.line = line
        self.column = column


class ASTNode:
    """AST node with type, children, and source location"""

    def __init__(self, node_type, **fields):
        self.node_type = node_type
        self.__dict__.update(fields)
        self.fields = fields

    def __repr__(self):
        return f"ASTNode({self.node_type}, {self.fields})"

    def to_dict(self):
        """Convert AST node to a plain dict for JSON output"""
        result = {"node_type": self.node_type}
        for k, v in self.fields.items():
            if isinstance(v, ASTNode):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [item.to_dict() if isinstance(item, ASTNode) else item for item in v]
            else:
                result[k] = v
        return result


class ParseResult:
    """Result of parsing: AST + errors"""

    def __init__(self, ast=None, errors=None, statement_type="UNKNOWN"):
        self.ast = ast
        self.errors = errors or []
        self.statement_type = statement_type

    def is_valid(self):
        return len(self.errors) == 0

    def to_dict(self):
        return {
            "statement_type": self.statement_type,
            "ast": self.ast.to_dict() if self.ast else None,
            "errors": [{"message": str(e), "line": getattr(e, 'line', 0),
                        "column": getattr(e, 'column', 0)} for e in self.errors],
        }


class DorisSQLParser:
    """
    Apache Doris SQL Recursive Descent Parser

    Parses Doris SQL statements based on DorisParser.g4 (Nereids ANTLR4 grammar).
    Generates a simplified AST for use by the rule engine.

    Supports major Doris statement types: SELECT, INSERT, UPDATE, DELETE, LOAD,
    EXPORT, CREATE TABLE, ALTER TABLE, DROP, CREATE MTMV, CREATE INDEX,
    CREATE CATALOG/USER/ROLE/STAGE/ENCRYPTKEY/JOB, CREATE ROW POLICY,
    CREATE SQL_BLOCK_RULE, BACKUP/RESTORE SNAPSHOT, EXPLAIN, KILL, CANCEL,
    ADMIN, GRANT/REVOKE, BEGIN/COMMIT/ROLLBACK, etc.
    """

    def __init__(self, sql_text):
        self.sql_text = sql_text
        self.tokens = []
        self.token_errors = []
        self.pos = 0
        self.errors = []

    def _peek(self, offset=0):
        """Peek at token at offset"""
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return Token(TokenType.EOF, '')
        return self.tokens[idx]

    def _current(self):
        return self._peek(0)

    def _next(self):
        """Consume and return the current token"""
        if self.pos >= len(self.tokens):
            return Token(TokenType.EOF, '')
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, type_, value=None):
        """Expect a specific token type (and optionally value), error if not matched"""
        tok = self._current()
        if tok.type != type_:
            self._error(f"Expected {type_} but got {tok.type} ({tok.value!r})",
                         tok.line, tok.column)
            return tok
        if value is not None and tok.value.upper() != value.upper():
            self._error(f"Expected keyword {value} but got {tok.value!r}",
                         tok.line, tok.column)
        return self._next()

    def _expect_keyword(self, name):
        """Expect a specific keyword"""
        tok = self._current()
        if not tok.is_keyword(name):
            self._error(f"Expected keyword {name} but got {tok.value!r}",
                         tok.line, tok.column)
            return tok
        return self._next()

    def _match_keyword(self, *names):
        """If current token matches one of the keywords, consume it; return True"""
        tok = self._current()
        for name in names:
            if tok.is_keyword(name):
                self._next()
                return True
        return False

    def _is_keyword(self, *names):
        """Check if current token is one of the keywords (no consume)"""
        tok = self._current()
        for name in names:
            if tok.is_keyword(name):
                return True
        return False

    def _error(self, msg, line=0, column=0):
        """Record a parse error"""
        err = ParseError(msg, line, column)
        self.errors.append(err)
        return err

    def parse(self):
        """Parse the SQL text and return a ParseResult"""
        # Tokenize first
        self.tokens, self.token_errors = tokenize(self.sql_text)
        # Convert token errors to parse errors (they'll be reported as SYN-ERR)
        for err in self.token_errors:
            self.errors.append(ParseError(str(err), err.line, err.column))

        if not self.tokens or self._current().type == TokenType.EOF:
            return ParseResult(None, self.errors, "EMPTY")

        # Detect statement type from first tokens
        stmt_type = detect_statement_type(self.sql_text)
        if stmt_type == "UNKNOWN":
            # Try to detect from first token
            first_tok = self._current()
            if first_tok.type == TokenType.KEYWORD:
                self._error(f"Unknown statement starting with keyword {first_tok.value!r}",
                             first_tok.line, first_tok.column)
            else:
                self._error(f"Unknown statement starting with {first_tok.type}",
                             first_tok.line, first_tok.column)
            return ParseResult(None, self.errors, "UNKNOWN")

        # Dispatch to statement-specific parser
        try:
            ast = self._dispatch(stmt_type)
        except ParseError as e:
            self.errors.append(e)
            ast = None
        except Exception as e:
            self._error(f"Internal parse error: {e}")
            ast = None

        return ParseResult(ast, self.errors, stmt_type)

    def _dispatch(self, stmt_type):
        """Dispatch to the appropriate statement parser"""
        if stmt_type == "SELECT":
            return self._parse_select()
        if stmt_type == "INSERT":
            return self._parse_insert()
        if stmt_type == "UPDATE":
            return self._parse_update()
        if stmt_type == "DELETE":
            return self._parse_delete()
        if stmt_type == "CREATE_TABLE":
            return self._parse_create_table()
        if stmt_type == "CREATE_TABLE_LIKE":
            return self._parse_create_table_like()
        if stmt_type == "CREATE_VIEW":
            return self._parse_create_view()
        if stmt_type == "CREATE_MTMV":
            return self._parse_create_mtmv()
        if stmt_type == "CREATE_INDEX":
            return self._parse_create_index()
        if stmt_type == "ALTER_TABLE":
            return self._parse_alter_table()
        if stmt_type == "DROP_TABLE":
            return self._parse_drop("TABLE")
        if stmt_type == "DROP_VIEW":
            return self._parse_drop("VIEW")
        if stmt_type == "DROP_INDEX":
            return self._parse_drop("INDEX")
        if stmt_type == "TRUNCATE":
            return self._parse_truncate()
        if stmt_type == "LOAD":
            return self._parse_load()
        if stmt_type == "EXPORT":
            return self._parse_export()
        if stmt_type == "GRANT":
            return self._parse_grant_revoke("GRANT")
        if stmt_type == "REVOKE":
            return self._parse_grant_revoke("REVOKE")
        if stmt_type in ("BEGIN", "COMMIT", "ROLLBACK"):
            return self._parse_transaction(stmt_type)
        if stmt_type == "EXPLAIN":
            return self._parse_explain()
        if stmt_type == "KILL":
            return self._parse_kill()
        if stmt_type == "CANCEL":
            return self._parse_cancel()
        if stmt_type == "BACKUP":
            return self._parse_backup_restore("BACKUP")
        if stmt_type == "RESTORE":
            return self._parse_backup_restore("RESTORE")
        # For other statement types, return a generic node
        return self._parse_generic(stmt_type)

    def _parse_generic(self, stmt_type):
        """Generic parser for unrecognized statement types - just consume all tokens"""
        rule = STATEMENT_RULES.get(stmt_type)
        node_type = rule["node_type"] if rule else "GenericStmt"
        # Consume all tokens
        while self._current().type != TokenType.EOF and self._current().type != TokenType.SEMICOLON:
            self._next()
        return ASTNode(node_type, raw_text=self.sql_text)

    def _parse_select(self):
        """Parse SELECT statement (simplified)"""
        has_select_star = False
        distinct = False
        with_cte = False
        from_clause = None
        where_clause = None
        missing_from = False
        has_limit = False
        has_outfile = False
        has_tablesample = False
        has_recursive_cte = False
        has_or_in_where = False
        has_not_in_subquery = False
        has_cartesian_risk = False

        # WITH (CTE)
        if self._match_keyword("WITH"):
            with_cte = True
            # Consume CTE definition
            while not self._is_keyword("SELECT") and self._current().type not in (TokenType.EOF, TokenType.SEMICOLON):
                self._next()

        # SELECT
        self._expect_keyword("SELECT")

        # DISTINCT / ALL
        if self._match_keyword("DISTINCT"):
            distinct = True
        elif self._match_keyword("ALL"):
            pass

        # Target list - check for SELECT *
        if self._current().type == TokenType.ASTERISK:
            has_select_star = True
            self._next()
        else:
            # Consume target list until FROM or end
            self._consume_until_keywords("FROM", "WHERE", "GROUP", "HAVING",
                                          "ORDER", "LIMIT", "OFFSET", "INTO", TokenType.EOF, TokenType.SEMICOLON)

        # FROM
        if self._match_keyword("FROM"):
            from_clause = self._consume_table_refs()
        else:
            missing_from = True

        # Check for TABLESAMPLE
        if self._is_keyword("TABLESAMPLE"):
            has_tablesample = True
            self._next()
            if self._current().type == TokenType.LEFT_PAREN:
                self._consume_parens()

        # WHERE
        if self._match_keyword("WHERE"):
            where_clause = self._consume_expression()

        # GROUP BY
        if self._match_keyword("GROUP"):
            self._expect_keyword("BY")
            self._consume_until_keywords("HAVING", "ORDER", "LIMIT", "OFFSET", "INTO",
                                          TokenType.EOF, TokenType.SEMICOLON)

        # HAVING
        if self._match_keyword("HAVING"):
            self._consume_until_keywords("ORDER", "LIMIT", "OFFSET", "INTO",
                                          TokenType.EOF, TokenType.SEMICOLON)

        # ORDER BY
        if self._match_keyword("ORDER"):
            self._expect_keyword("BY")
            self._consume_until_keywords("LIMIT", "OFFSET", "INTO",
                                          TokenType.EOF, TokenType.SEMICOLON)

        # LIMIT
        if self._match_keyword("LIMIT"):
            has_limit = True
            self._consume_until_keywords("OFFSET", "INTO", TokenType.EOF, TokenType.SEMICOLON)

        # OFFSET
        if self._match_keyword("OFFSET"):
            self._consume_until_keywords("INTO", TokenType.EOF, TokenType.SEMICOLON)

        # INTO OUTFILE
        if self._match_keyword("INTO"):
            if self._match_keyword("OUTFILE"):
                has_outfile = True
                # Consume outfile path and options
                self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)
            else:
                self._error("Expected OUTFILE after INTO", self._current().line, self._current().column)

        # Consume trailing semicolon
        self._match_semicolon()

        return ASTNode(
            "SelectStmt",
            distinct=distinct,
            has_select_star=has_select_star,
            from_clause=from_clause,
            where_clause=where_clause,
            missing_from=missing_from,
            has_cte=with_cte,
            has_limit=has_limit,
            has_outfile=has_outfile,
            has_tablesample=has_tablesample,
            has_recursive_cte=has_recursive_cte,
        )

    def _parse_insert(self):
        """Parse INSERT statement"""
        is_overwrite = False
        table = None
        columns = None
        has_values = False
        values_count = 0
        has_select = False
        partition_spec = None
        with_label = None
        missing_table = False

        self._expect_keyword("INSERT")

        # OVERWRITE TABLE or INTO
        if self._match_keyword("OVERWRITE"):
            if not self._match_keyword("TABLE"):
                tok = self._current()
                self._error("Expected TABLE after OVERWRITE (Doris requires INSERT OVERWRITE TABLE)",
                             tok.line, tok.column)
            is_overwrite = True
        elif self._match_keyword("INTO"):
            pass
        else:
            tok = self._current()
            self._error("Expected INTO or OVERWRITE after INSERT",
                         tok.line, tok.column)

        # Table name
        table = self._consume_qualified_name()

        # PARTITION spec
        if self._match_keyword("PARTITION"):
            partition_spec = self._consume_parens_content()

        # WITH LABEL
        if self._match_keyword("WITH"):
            if self._match_keyword("LABEL"):
                with_label = self._consume_identifier()

        # Column list
        if self._current().type == TokenType.LEFT_PAREN:
            columns = self._consume_parens_content()

        # WITH (CTE)
        if self._is_keyword("WITH"):
            self._next()
            # Consume CTE definition
            while not self._is_keyword("VALUES", "SELECT") and self._current().type not in (TokenType.EOF, TokenType.SEMICOLON):
                self._next()

        # VALUES or SELECT
        if self._match_keyword("VALUES"):
            has_values = True
            # Count VALUES groups
            while self._current().type == TokenType.LEFT_PAREN:
                self._consume_parens()
                values_count += 1
                if self._match_keyword(","):
                    continue
                break
        elif self._is_keyword("SELECT") or self._is_keyword("WITH"):
            has_select = True
            # Don't consume - leave for next iteration

        self._match_semicolon()

        return ASTNode(
            "InsertStmt",
            table=table,
            columns=columns,
            is_overwrite=is_overwrite,
            has_values=has_values,
            values_count=values_count,
            has_select=has_select,
            partition_spec=partition_spec,
            with_label=with_label,
            missing_table=missing_table,
        )

    def _parse_update(self):
        """Parse UPDATE statement"""
        self._expect_keyword("UPDATE")
        table = self._consume_qualified_name()

        # Table alias (AS)
        if self._match_keyword("AS"):
            self._consume_identifier()

        # SET
        self._expect_keyword("SET")
        # Consume SET clause until FROM/WHERE/EOF
        self._consume_until_keywords("FROM", "WHERE", TokenType.EOF, TokenType.SEMICOLON)

        # FROM
        if self._match_keyword("FROM"):
            self._consume_table_refs()

        # WHERE
        where_present = self._match_keyword("WHERE")
        if where_present:
            self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)

        self._match_semicolon()

        return ASTNode(
            "UpdateStmt",
            table=table,
            missing_where=not where_present,
        )

    def _parse_delete(self):
        """Parse DELETE statement"""
        self._expect_keyword("DELETE")
        self._expect_keyword("FROM")
        table = self._consume_qualified_name()

        # Table alias
        if self._match_keyword("AS"):
            self._consume_identifier()

        # USING
        if self._match_keyword("USING"):
            self._consume_table_refs()

        # WHERE
        where_present = self._match_keyword("WHERE")
        if where_present:
            self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)

        self._match_semicolon()

        return ASTNode(
            "DeleteStmt",
            table=table,
            missing_where=not where_present,
        )

    def _parse_create_table(self):
        """Parse CREATE TABLE statement"""
        self._expect_keyword("CREATE")
        is_temporary = self._match_keyword("TEMPORARY")
        self._expect_keyword("TABLE")
        if_not_exists = False
        if self._match_keyword("IF"):
            self._expect_keyword("NOT")
            self._expect_keyword("EXISTS")
            if_not_exists = True

        table_name = self._consume_qualified_name()

        columns = []
        indexes = []
        engine = None
        key_model = None
        key_columns = None
        cluster_by = None
        partition_by = None
        distribute_type = None
        distribute_columns = None
        buckets = None
        has_buckets = False
        properties = None
        comment = None
        ctas_query = None

        # Column definitions
        if self._current().type == TokenType.LEFT_PAREN:
            self._next()  # (
            while self._current().type not in (TokenType.RIGHT_PAREN, TokenType.EOF):
                # Parse column or index definition (simplified)
                if self._is_keyword("INDEX"):
                    self._next()
                    idx_name = self._consume_identifier() if self._current().type in (TokenType.IDENTIFIER, TokenType.BACKQUOTED_IDENTIFIER) else None
                    indexes.append({"name": idx_name})
                elif self._is_keyword("CONSTRAINT"):
                    self._next()
                    self._consume_identifier()
                else:
                    col_name = self._consume_identifier()
                    col_type = self._consume_identifier()
                    # Capture type parameters if present (e.g., VARCHAR(100), DECIMAL(18,2))
                    if self._current().type == TokenType.LEFT_PAREN:
                        type_params = self._consume_parens_content()
                        col_type = f"{col_type}({type_params})"
                    columns.append({"name": col_name, "type": col_type})
                # Skip to next comma or ) respecting paren depth
                depth = 0
                while True:
                    tok = self._current()
                    if tok.type == TokenType.EOF:
                        break
                    if tok.type == TokenType.LEFT_PAREN:
                        depth += 1
                    elif tok.type == TokenType.RIGHT_PAREN:
                        if depth == 0:
                            break  # end of column list
                        depth -= 1
                    elif tok.type == TokenType.COMMA and depth == 0:
                        break
                    self._next()
                if self._current().type == TokenType.COMMA:
                    self._next()
            self._expect(TokenType.RIGHT_PAREN)

        # ENGINE = ...
        if self._match_keyword("ENGINE"):
            self._expect(TokenType.EQ)
            engine = self._consume_identifier()

        # KEY model: DUPLICATE/AGGREGATE/UNIQUE KEY
        if self._is_keyword("DUPLICATE", "AGGREGATE", "UNIQUE"):
            key_model = self._current().value
            self._next()
            self._expect_keyword("KEY")
            key_columns = self._consume_parens_content()
            # CLUSTER BY
            if self._match_keyword("CLUSTER"):
                self._expect_keyword("BY")
                cluster_by = self._consume_parens_content()

        # PARTITION BY
        if self._match_keyword("PARTITION"):
            # Handle AUTO PARTITION BY ...
            is_auto = self._match_keyword("AUTO")
            if self._match_keyword("BY"):
                # Optional RANGE/LIST keyword
                part_type = "RANGE"  # default
                if self._is_keyword("RANGE"):
                    part_type = "RANGE"
                    self._next()
                elif self._is_keyword("LIST"):
                    part_type = "LIST"
                    self._next()
                if is_auto:
                    part_type = "AUTO_" + part_type
                # Consume partition key columns in parens
                part_cols = self._consume_parens_content() if self._current().type == TokenType.LEFT_PAREN else None
                # Consume partition definitions until DISTRIBUTED/PROPERTIES/COMMENT/AS/EOF/semicolon
                self._consume_until_keywords("DISTRIBUTED", "PROPERTIES", "COMMENT", "AS",
                                             TokenType.EOF, TokenType.SEMICOLON)
                partition_by = {"type": part_type, "columns": part_cols}

        # DISTRIBUTED BY
        if self._match_keyword("DISTRIBUTED"):
            self._expect_keyword("BY")
            if self._match_keyword("HASH"):
                distribute_type = "HASH"
                distribute_columns = self._consume_parens_content()
            elif self._match_keyword("RANDOM"):
                distribute_type = "RANDOM"
            else:
                tok = self._current()
                self._error(f"Expected HASH or RANDOM after DISTRIBUTED BY, got {tok.value!r}",
                             tok.line, tok.column)
            # BUCKETS
            if self._match_keyword("BUCKETS"):
                has_buckets = True
                if self._is_keyword("AUTO"):
                    buckets = "AUTO"
                    self._next()
                else:
                    buckets = self._current().value
                    self._next()

        # PROPERTIES
        if self._match_keyword("PROPERTIES"):
            properties = self._consume_parens_content()

        # COMMENT
        if self._match_keyword("COMMENT"):
            comment = self._current().value
            self._next()

        # AS query (CTAS)
        if self._match_keyword("AS"):
            ctas_query = "SELECT"  # Mark as CTAS

        self._match_semicolon()

        return ASTNode(
            "CreateStmt",
            table_name=table_name,
            is_temporary=is_temporary,
            if_not_exists=if_not_exists,
            columns=columns,
            indexes=indexes,
            engine=engine,
            key_model=key_model,
            key_columns=key_columns,
            cluster_by=cluster_by,
            partition_by=partition_by,
            distribute_type=distribute_type,
            distribute_columns=distribute_columns,
            buckets=buckets,
            has_buckets=has_buckets,
            properties=properties,
            comment=comment,
            ctas_query=ctas_query,
        )

    def _parse_create_table_like(self):
        """Parse CREATE TABLE LIKE"""
        self._expect_keyword("CREATE")
        self._match_keyword("TEMPORARY")
        self._expect_keyword("TABLE")
        if self._match_keyword("IF"):
            self._expect_keyword("NOT")
            self._expect_keyword("EXISTS")
        name = self._consume_identifier()
        self._expect_keyword("LIKE")
        like_table = self._consume_identifier()
        self._match_semicolon()
        return ASTNode("CreateStmt", table_name=name, like_table=like_table)

    def _parse_create_view(self):
        """Parse CREATE VIEW"""
        self._expect_keyword("CREATE")
        or_replace = False
        if self._match_keyword("OR"):
            self._expect_keyword("REPLACE")
            or_replace = True
        self._expect_keyword("VIEW")
        name = self._consume_qualified_name()
        # Optional column list
        columns = None
        if self._current().type == TokenType.LEFT_PAREN:
            columns = self._consume_parens_content()
        comment = None
        if self._match_keyword("COMMENT"):
            comment = self._current().value
            self._next()
        self._expect_keyword("AS")
        # Consume the SELECT query
        self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)
        self._match_semicolon()
        return ASTNode("ViewStmt", table_name=name, columns=columns,
                        comment=comment, or_replace=or_replace)

    def _parse_create_mtmv(self):
        """Parse CREATE MATERIALIZED VIEW (MTMV)"""
        self._expect_keyword("CREATE")
        self._expect_keyword("MATERIALIZED")
        self._expect_keyword("VIEW")
        name = self._consume_qualified_name()

        columns = None
        if self._current().type == TokenType.LEFT_PAREN:
            columns = self._consume_parens_content()

        key_model = None
        key_columns = None
        if self._match_keyword("DUPLICATE"):
            self._expect_keyword("KEY")
            key_model = "DUPLICATE"
            key_columns = self._consume_parens_content()

        partition_by = None
        if self._match_keyword("PARTITION"):
            self._expect_keyword("BY")
            partition_by = self._consume_parens_content()

        distribute_type = None
        distribute_columns = None
        buckets = None
        if self._match_keyword("DISTRIBUTED"):
            self._expect_keyword("BY")
            if self._match_keyword("HASH"):
                distribute_type = "HASH"
                distribute_columns = self._consume_parens_content()
            elif self._match_keyword("RANDOM"):
                distribute_type = "RANDOM"
            if self._match_keyword("BUCKETS"):
                buckets = self._current().value
                self._next()

        build_mode = None
        if self._match_keyword("BUILD"):
            if self._match_keyword("IMMEDIATE"):
                build_mode = "IMMEDIATE"
            elif self._match_keyword("DEFERRED"):
                build_mode = "DEFERRED"

        refresh_method = None
        if self._match_keyword("REFRESH"):
            if self._match_keyword("COMPLETE"):
                refresh_method = "COMPLETE"
            elif self._match_keyword("AUTO"):
                refresh_method = "AUTO"

        refresh_trigger = None
        if self._match_keyword("ON"):
            if self._match_keyword("MANUAL"):
                refresh_trigger = "MANUAL"
            elif self._match_keyword("SCHEDULE"):
                refresh_trigger = "SCHEDULE"
            elif self._match_keyword("COMMIT"):
                refresh_trigger = "COMMIT"

        properties = None
        if self._match_keyword("PROPERTIES"):
            properties = self._consume_parens_content()

        if self._match_keyword("COMMENT"):
            self._next()  # skip comment string

        if self._match_keyword("AS"):
            pass  # Consume the query
        self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)
        self._match_semicolon()

        return ASTNode(
            "CreateMTMVStmt",
            name=name,
            columns=columns,
            key_model=key_model,
            key_columns=key_columns,
            partition_by=partition_by,
            distribute_type=distribute_type,
            distribute_columns=distribute_columns,
            buckets=buckets,
            build_mode=build_mode,
            refresh_method=refresh_method,
            refresh_trigger=refresh_trigger,
            properties=properties,
        )

    def _parse_create_index(self):
        """Parse CREATE INDEX"""
        self._expect_keyword("CREATE")
        self._expect_keyword("INDEX")
        index_name = self._consume_identifier()
        self._expect_keyword("ON")
        table = self._consume_qualified_name()
        columns = self._consume_parens_content()
        index_type = None
        if self._match_keyword("USING"):
            index_type = self._consume_identifier()
        properties = None
        if self._match_keyword("PROPERTIES"):
            properties = self._consume_parens_content()
        self._match_semicolon()
        return ASTNode("IndexStmt", index_name=index_name, table=table,
                        columns=columns, index_type=index_type, properties=properties)

    def _parse_alter_table(self):
        """Parse ALTER TABLE (simplified - just record actions)"""
        self._expect_keyword("ALTER")
        self._expect_keyword("TABLE")
        table = self._consume_qualified_name()
        actions = []
        while True:
            action = self._parse_alter_action()
            if action:
                actions.append(action)
            if not self._match_keyword(","):
                break
        self._match_semicolon()
        return ASTNode("AlterTableStmt", table_name=table, actions=actions)

    def _parse_alter_action(self):
        """Parse a single ALTER TABLE action"""
        if self._match_keyword("ADD"):
            if self._match_keyword("COLUMN"):
                col = self._consume_identifier()
                col_type = self._consume_identifier()
                return {"action": "ADD_COLUMN", "column": col, "type": col_type}
            if self._match_keyword("PARTITION"):
                return {"action": "ADD_PARTITION", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
            return {"action": "ADD_COLUMNS", "details": self._consume_parens_content()}
        if self._match_keyword("DROP"):
            if self._match_keyword("COLUMN"):
                return {"action": "DROP_COLUMN", "column": self._consume_identifier()}
            if self._match_keyword("PARTITION"):
                return {"action": "DROP_PARTITION", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
            if self._match_keyword("INDEX"):
                return {"action": "DROP_INDEX", "name": self._consume_identifier()}
        if self._match_keyword("MODIFY"):
            if self._match_keyword("COLUMN"):
                return {"action": "MODIFY_COLUMN", "column": self._consume_identifier()}
            return {"action": "MODIFY", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
        if self._match_keyword("RENAME"):
            if self._match_keyword("COLUMN"):
                return {"action": "RENAME_COLUMN", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
            if self._match_keyword("PARTITION"):
                return {"action": "RENAME_PARTITION", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
            return {"action": "RENAME", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
        if self._match_keyword("REPLACE"):
            return {"action": "REPLACE_PARTITION", "details": self._consume_until_keywords(",", TokenType.SEMICOLON, TokenType.EOF)}
        if self._match_keyword("SET"):
            return {"action": "SET_PROPERTIES", "details": self._consume_parens_content()}
        # Unknown action - consume one token
        self._next()
        return None

    def _parse_drop(self, object_type):
        """Parse DROP TABLE/VIEW/INDEX"""
        self._expect_keyword("DROP")
        self._expect_keyword(object_type)
        if_exists = False
        if self._match_keyword("IF"):
            self._expect_keyword("EXISTS")
            if_exists = True
        name = self._consume_qualified_name()
        force = self._match_keyword("FORCE")
        self._match_semicolon()
        return ASTNode("DropStmt", object_type=object_type, objects=[name],
                        if_exists=if_exists, force=force)

    def _parse_truncate(self):
        """Parse TRUNCATE TABLE"""
        self._expect_keyword("TRUNCATE")
        self._expect_keyword("TABLE")
        table = self._consume_qualified_name()
        partition = None
        if self._match_keyword("PARTITION"):
            partition = self._consume_parens_content()
        self._match_semicolon()
        return ASTNode("TruncateStmt", table=table, partition=partition)

    def _parse_load(self):
        """Parse LOAD LABEL (BROKER LOAD)"""
        self._expect_keyword("LOAD")
        self._expect_keyword("LABEL")
        label = self._consume_qualified_name()
        # ( DATA INFILE ... INTO TABLE ... )
        data_descs = self._consume_parens_content()
        properties = None
        if self._match_keyword("PROPERTIES"):
            properties = self._consume_parens_content()
        comment = None
        if self._match_keyword("COMMENT"):
            comment = self._current().value
            self._next()
        self._match_semicolon()
        return ASTNode("LoadStmt", label=label, data_descs=data_descs,
                        properties=properties, comment=comment)

    def _parse_export(self):
        """Parse EXPORT TABLE"""
        self._expect_keyword("EXPORT")
        self._expect_keyword("TABLE")
        table = self._consume_qualified_name()
        partition = None
        if self._match_keyword("PARTITION"):
            partition = self._consume_parens_content()
        where_present = self._match_keyword("WHERE")
        if where_present:
            self._consume_until_keywords("TO", TokenType.EOF, TokenType.SEMICOLON)
        self._expect_keyword("TO")
        path = self._current().value
        self._next()
        properties = None
        if self._match_keyword("PROPERTIES"):
            properties = self._consume_parens_content()
        self._match_semicolon()
        return ASTNode("ExportStmt", table=table, partition=partition,
                        to_path=path, properties=properties)

    def _parse_grant_revoke(self, stmt_type):
        """Parse GRANT/REVOKE"""
        self._expect_keyword(stmt_type)
        privileges = []
        # Consume privilege list
        privileges.append(self._consume_identifier())
        while self._match_keyword(","):
            privileges.append(self._consume_identifier())
        self._expect_keyword("ON")
        # Object
        object_name = self._consume_qualified_name()
        if stmt_type == "GRANT":
            self._expect_keyword("TO")
        else:
            self._expect_keyword("FROM")
        grantee = self._consume_identifier()
        if self._match_keyword("ROLE"):
            grantee = self._consume_identifier()
        self._match_semicolon()
        return ASTNode(stmt_type.title() + "Stmt", privileges=privileges,
                        object=object_name, grantee=grantee)

    def _parse_transaction(self, stmt_type):
        """Parse BEGIN/COMMIT/ROLLBACK"""
        self._expect_keyword(stmt_type)
        if stmt_type == "BEGIN" and self._match_keyword("TRANSACTION"):
            pass
        if self._match_keyword("AND"):
            self._match_keyword("CHAIN")
        self._match_semicolon()
        return ASTNode("TransactionStmt", transaction_type=stmt_type)

    def _parse_explain(self):
        """Parse EXPLAIN"""
        # EXPLAIN / DESC / DESCRIBE
        self._next()  # consume EXPLAIN/DESC/DESCRIBE
        plan_type = None
        for pt in ["PARSED", "ANALYZED", "REWRITTEN", "LOGICAL", "OPTIMIZED",
                    "PHYSICAL", "SHAPE", "MEMO", "DISTRIBUTED", "ALL"]:
            if self._is_keyword(pt):
                plan_type = pt
                self._next()
                break
        level = None
        for lvl in ["VERBOSE", "TREE", "GRAPH", "PLAN", "DUMP"]:
            if self._is_keyword(lvl):
                level = lvl
                self._next()
                break
        self._match_keyword("PROCESS")
        # Consume the rest of the statement
        self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)
        self._match_semicolon()
        return ASTNode("ExplainStmt", plan_type=plan_type, level=level)

    def _parse_kill(self):
        """Parse KILL"""
        self._expect_keyword("KILL")
        kill_type = "CONNECTION"
        if self._match_keyword("CONNECTION"):
            kill_type = "CONNECTION"
        elif self._match_keyword("QUERY"):
            kill_type = "QUERY"
        conn_id = self._current().value
        self._next()
        self._match_semicolon()
        return ASTNode("KillStmt", kill_type=kill_type, connection_id=conn_id)

    def _parse_cancel(self):
        """Parse CANCEL"""
        self._expect_keyword("CANCEL")
        cancel_type = None
        for ct in ["LOAD", "EXPORT", "ALTER", "BUILD", "DECOMMISSION",
                    "BACKUP", "RESTORE", "WARM"]:
            if self._is_keyword(ct):
                cancel_type = ct
                self._next()
                break
        self._consume_until_keywords(TokenType.EOF, TokenType.SEMICOLON)
        self._match_semicolon()
        return ASTNode("CancelStmt", cancel_type=cancel_type)

    def _parse_backup_restore(self, stmt_type):
        """Parse BACKUP/RESTORE SNAPSHOT"""
        self._expect_keyword(stmt_type)
        self._expect_keyword("SNAPSHOT")
        snapshot = self._consume_qualified_name()
        if stmt_type == "BACKUP":
            self._expect_keyword("TO")
        else:
            self._expect_keyword("FROM")
        repository = self._consume_identifier()
        # ON | EXCLUDE
        tables = None
        exclude = None
        if self._match_keyword("ON"):
            tables = self._consume_parens_content()
        elif self._match_keyword("EXCLUDE"):
            exclude = self._consume_parens_content()
        properties = None
        if self._match_keyword("PROPERTIES"):
            properties = self._consume_parens_content()
        self._match_semicolon()
        return ASTNode(stmt_type.title() + "Stmt", snapshot_name=snapshot,
                        repository=repository, tables=tables,
                        exclude_tables=exclude, properties=properties)

    # ============================================================
    # Helper methods
    # ============================================================

    def _consume_until_keywords(self, *stop_tokens):
        """Consume tokens until one of the stop keywords/tokens is reached"""
        while True:
            tok = self._current()
            if tok.type == TokenType.EOF:
                return
            if tok.type in stop_tokens:
                return
            if tok.type == TokenType.KEYWORD:
                # Check if any of the stop tokens are keyword names
                for stop in stop_tokens:
                    if isinstance(stop, str) and tok.is_keyword(stop):
                        return
            if tok.type == TokenType.SEMICOLON:
                return
            self._next()

    def _consume_parens(self):
        """Consume a balanced parenthesized expression"""
        if self._current().type != TokenType.LEFT_PAREN:
            return None
        depth = 0
        start = self.pos
        while self.pos < len(self.tokens):
            tok = self._current()
            if tok.type == TokenType.LEFT_PAREN:
                depth += 1
            elif tok.type == TokenType.RIGHT_PAREN:
                depth -= 1
                if depth == 0:
                    self._next()
                    break
            elif tok.type == TokenType.EOF:
                self._error("Unclosed parenthesis")
                return None
            self._next()
        return "(...)"

    def _consume_parens_content(self):
        """Consume (...) and return its content as a string"""
        if self._current().type != TokenType.LEFT_PAREN:
            return None
        depth = 0
        content = []
        while self.pos < len(self.tokens):
            tok = self._current()
            if tok.type == TokenType.LEFT_PAREN:
                depth += 1
                if depth > 1:
                    content.append(tok.value)
            elif tok.type == TokenType.RIGHT_PAREN:
                depth -= 1
                if depth == 0:
                    self._next()
                    break
                content.append(tok.value)
            elif tok.type == TokenType.EOF:
                self._error("Unclosed parenthesis")
                return None
            else:
                content.append(tok.value)
            self._next()
        return ' '.join(content)

    def _consume_table_refs(self):
        """Consume table references in FROM clause"""
        refs = []
        refs.append(self._consume_qualified_name())
        # Skip alias / JOIN / ON / etc.
        while True:
            tok = self._current()
            if tok.type in (TokenType.EOF, TokenType.SEMICOLON):
                break
            if tok.type == TokenType.KEYWORD and tok.value in ("WHERE", "GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET", "INTO"):
                break
            if tok.type == TokenType.KEYWORD and tok.value in ("JOIN", "INNER", "LEFT", "RIGHT", "FULL", "CROSS", "OUTER", "ON", "USING"):
                self._next()
                continue
            if tok.type == TokenType.COMMA:
                self._next()
                refs.append(self._consume_qualified_name())
                continue
            self._next()
        return refs

    def _consume_qualified_name(self):
        """Consume a qualified name (catalog.db.table or table)"""
        parts = []
        # Handle backtick-quoted or plain identifier
        tok = self._current()
        if tok.type in (TokenType.IDENTIFIER, TokenType.BACKQUOTED_IDENTIFIER):
            parts.append(tok.value)
            self._next()
        elif tok.type == TokenType.KEYWORD and not is_reserved_keyword(tok.value):
            # Non-reserved keyword used as identifier
            parts.append(tok.value)
            self._next()
        else:
            return None
        # Consume .ident chains
        while self._current().type == TokenType.DOT:
            self._next()
            tok = self._current()
            if tok.type in (TokenType.IDENTIFIER, TokenType.BACKQUOTED_IDENTIFIER):
                parts.append(tok.value)
                self._next()
            elif tok.type == TokenType.ASTERISK:
                # catalog.db.* pattern
                parts.append("*")
                self._next()
                break
        return '.'.join(parts)

    def _consume_identifier(self):
        """Consume a single identifier"""
        tok = self._current()
        if tok.type in (TokenType.IDENTIFIER, TokenType.BACKQUOTED_IDENTIFIER):
            self._next()
            return tok.value
        if tok.type == TokenType.KEYWORD and not is_reserved_keyword(tok.value):
            self._next()
            return tok.value
        self._error(f"Expected identifier, got {tok.type} ({tok.value!r})", tok.line, tok.column)
        return None

    def _consume_expression(self):
        """Consume an expression (simplified)"""
        depth = 0
        while self.pos < len(self.tokens):
            tok = self._current()
            if tok.type == TokenType.EOF or tok.type == TokenType.SEMICOLON:
                break
            if tok.type == TokenType.LEFT_PAREN:
                depth += 1
            elif tok.type == TokenType.RIGHT_PAREN:
                if depth == 0:
                    break
                depth -= 1
            elif tok.type == TokenType.KEYWORD and depth == 0:
                if tok.value in ("GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET", "INTO"):
                    break
            self._next()
        return "(expression)"

    def _match_semicolon(self):
        """Consume optional trailing semicolon"""
        if self._current().type == TokenType.SEMICOLON:
            self._next()
            return True
        return False


def parse_sql(sql_text):
    """
    Parse a Doris SQL statement and return a ParseResult.
    """
    parser = DorisSQLParser(sql_text)
    return parser.parse()


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python doris_sql_parser.py \"<sql_text>\"")
        print("\nDoris SQL Parser - Recursive descent parser for Apache Doris SQL")
        sys.exit(1)

    sql_text = sys.argv[1]
    result = parse_sql(sql_text)

    print(f"# Doris SQL Parser Output")
    print(f"# Statement Type: {result.statement_type}")
    print(f"# Valid: {result.is_valid()}")
    print(f"# Errors: {len(result.errors)}")
    print()

    if result.ast:
        print("AST:")
        import json
        print(json.dumps(result.ast.to_dict(), indent=2, default=str))

    if result.errors:
        print(f"\nErrors:")
        for err in result.errors:
            line = getattr(err, 'line', 0)
            col = getattr(err, 'column', 0)
            print(f"  L{line}:{col} - {err}")


if __name__ == "__main__":
    main()
