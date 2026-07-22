# -*- coding: utf-8 -*-
"""
MRS Hive SQL Tokenizer

Lexical analyzer for MRS Hive SQL statements.
Tokenizes SQL text into a stream of typed tokens with position information.
"""

import re
import sys
import os

# Add rules directory to path for keyword imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))
from keywords import (
    is_keyword, get_keyword_info, is_reserved_keyword,
    KeywordCategory, ALL_KEYWORDS, RESERVED_KEYWORDS
)


class TokenType:
    """Token type constants"""
    # Non-keyword terminals
    IDENT = "IDENT"
    BACKTICK_IDENT = "BACKTICK_IDENT"  # `identifier`
    SCONST = "SCONST"          # String constant
    ICONST = "ICONST"          # Integer constant
    FCONST = "FCONST"          # Float constant
    OP = "OP"                  # Generic operator
    CMP_OP = "CMP_OP"         # Comparison operator

    # Special
    KEYWORD = "KEYWORD"        # Hive keyword
    COMMENT = "COMMENT"        # SQL comment
    HINT = "HINT"              # Optimizer hint /*+ ... */
    SEMICOLON = "SEMICOLON"    # ;
    COMMA = "COMMA"            # ,
    LPAREN = "LPAREN"          # (
    RPAREN = "RPAREN"          # )
    LBRACKET = "LBRACKET"      # [
    RBRACKET = "RBRACKET"      # ]
    LCURLY = "LCURLY"          # {
    RCURLY = "RCURLY"          # }
    DOT = "DOT"                # .
    STAR = "STAR"              # *
    COLON = "COLON"           # :
    QUESTION = "QUESTION"     # ?
    DOLLAR = "DOLLAR"          # $
    EOF = "EOF"                # End of input


class Token:
    """Represents a single SQL token with type, value, and position"""

    __slots__ = ('type', 'value', 'line', 'column', 'keyword_category', 'keyword_token')

    def __init__(self, type_, value, line=0, column=0, keyword_category=None, keyword_token=None):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column
        self.keyword_category = keyword_category
        self.keyword_token = keyword_token

    def __repr__(self):
        cat = f" [{self.keyword_category.name}]" if self.keyword_category else ""
        return f"Token({self.type}, {self.value!r}, L{self.line}:{self.column}{cat})"

    def is_keyword(self, name=None):
        """Check if token is a keyword, optionally matching specific name"""
        if self.type != TokenType.KEYWORD:
            return False
        if name is None:
            return True
        return self.value.upper() == name.upper()

    def is_reserved(self):
        """Check if token is a reserved keyword"""
        return self.keyword_category == KeywordCategory.RESERVED


class TokenizerError(Exception):
    """Error during tokenization"""

    def __init__(self, message, line=0, column=0):
        super().__init__(message)
        self.line = line
        self.column = column


class HiveSQLTokenizer:
    """
    MRS Hive SQL Lexical Analyzer

    Tokenizes SQL text following the HiveQL lexical rules.
    Supports Hive-specific tokens including:
    - Backtick-quoted identifiers `table_name`
    - Optimizer hints /*+ MAPJOIN(...) */ and /*+ STREAMTABLE(...) */
    - Hive-specific keywords
    """

    # Comparison operators
    CMP_OPS = {'<', '>', '=', '<=', '>=', '<>', '!=', '==', '<=>'}

    # Multi-character operators
    MULTI_CHAR_OPS = {
        '<=': TokenType.CMP_OP,
        '>=': TokenType.CMP_OP,
        '<>': TokenType.CMP_OP,
        '!=': TokenType.CMP_OP,
        '==': TokenType.CMP_OP,
        '<=>': TokenType.CMP_OP,
        '||': TokenType.OP,
        '&&': TokenType.OP,
        '<<': TokenType.OP,
        '>>': TokenType.OP,
    }

    def __init__(self, sql_text):
        self.text = sql_text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []

    def _char(self, offset=0):
        """Get character at current position + offset"""
        p = self.pos + offset
        if p < len(self.text):
            return self.text[p]
        return None

    def _advance(self, n=1):
        """Advance position by n characters, updating line/column"""
        for _ in range(n):
            if self.pos < len(self.text):
                if self.text[self.pos] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1

    def _peek_multi(self, n):
        """Peek at next n characters"""
        return self.text[self.pos:self.pos + n]

    def _make_token(self, type_, value, line=None, column=None, **kwargs):
        """Create a token at given or current position"""
        return Token(
            type_, value,
            line=line or self.line,
            column=column or self.column,
            **kwargs
        )

    def _skip_whitespace(self):
        """Skip whitespace characters"""
        while self.pos < len(self.text) and self.text[self.pos] in ' \t\n\r':
            self._advance()

    def _skip_line_comment(self):
        """Skip -- line comment"""
        self._advance(2)  # skip --
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self._advance()

    def _read_block_comment(self):
        """Read /* ... */ block comment, detect /*+ hint */ """
        start_line = self.line
        start_col = self.column
        self._advance(2)  # skip /*

        # Check for hint /*+ ... */
        is_hint = self.pos < len(self.text) and self.text[self.pos] == '+'

        content = []
        depth = 1
        while self.pos < len(self.text) and depth > 0:
            if self.text[self.pos] == '/' and self._char(1) == '*':
                depth += 1
                content.append('/*')
                self._advance(2)
            elif self.text[self.pos] == '*' and self._char(1) == '/':
                depth -= 1
                if depth > 0:
                    content.append('*/')
                self._advance(2)
            else:
                content.append(self.text[self.pos])
                self._advance()

        comment_text = ''.join(content)

        if is_hint:
            return self._make_token(TokenType.HINT, f'/*{comment_text}*/',
                                   line=start_line, column=start_col)
        # Regular block comment - skip
        return None

    def _read_string(self, quote_char="'"):
        """Read a quoted string constant"""
        start_line = self.line
        start_col = self.column
        result = [quote_char]
        self._advance()  # skip opening quote
        closed = False

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == quote_char:
                result.append(ch)
                self._advance()
                # Check for escaped quote (doubled)
                if self.pos < len(self.text) and self.text[self.pos] == quote_char:
                    result.append(self.text[self.pos])
                    self._advance()
                else:
                    closed = True
                    break  # End of string
            elif ch == '\\':
                # Backslash escape
                result.append(ch)
                self._advance()
                if self.pos < len(self.text):
                    result.append(self.text[self.pos])
                    self._advance()
            elif ch == '\n':
                # Hive allows multi-line string literals (e.g. in TBLPROPERTIES)
                result.append(ch)
                self._advance()
            else:
                result.append(ch)
                self._advance()

        # Check for unclosed string (reached end of input without closing quote)
        if not closed:
            self.errors.append(TokenizerError(
                f"未闭合的字符串: {quote_char}",
                start_line, start_col))

        return self._make_token(TokenType.SCONST, ''.join(result),
                               line=start_line, column=start_col)

    def _read_number(self):
        """Read a numeric constant (integer or float) with Hive literal suffixes.

        Supports Hive literal suffixes:
        - L: BIGINT (e.g., 100L)
        - S: SMALLINT (e.g., 100S)
        - Y: TINYINT (e.g., 100Y)
        - D: DOUBLE (e.g., 3.14D)
        - BD: BigDecimal/DECIMAL (e.g., 123.45BD)
        - b/B/k/K/m/M/g/G: Byte length (e.g., 256M, 100KB)
        """
        start_line = self.line
        start_col = self.column
        start_pos = self.pos

        # Read digits
        is_float = False
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self._advance()

        # Decimal point
        if self.pos < len(self.text) and self.text[self.pos] == '.':
            # Check for .. operator (range) or trailing dot
            if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '.':
                return self._make_token(TokenType.ICONST, self.text[start_pos:self.pos],
                                       line=start_line, column=start_col)
            is_float = True
            self._advance()
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self._advance()

        # Exponent
        if self.pos < len(self.text) and self.text[self.pos] in 'eE':
            is_float = True
            self._advance()
            if self.pos < len(self.text) and self.text[self.pos] in '+-':
                self._advance()
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self._advance()

        # BD suffix for Hive decimal (e.g., 123.45BD)
        if self.pos < len(self.text) and self.text[self.pos] in 'bB':
            if self.pos + 1 < len(self.text) and self.text[self.pos + 1] in 'dD':
                self._advance(2)
                value = self.text[start_pos:self.pos]
                return self._make_token(TokenType.FCONST, value, line=start_line, column=start_col)

        # Integral literal suffixes: L (BIGINT), S (SMALLINT), Y (TINYINT)
        if not is_float and self.pos < len(self.text):
            suffix_char = self.text[self.pos]
            if suffix_char in 'lLsSyY':
                self._advance()
                value = self.text[start_pos:self.pos]
                return self._make_token(TokenType.ICONST, value, line=start_line, column=start_col)

        # Number literal suffix: D (DOUBLE) - only for floats
        if is_float and self.pos < len(self.text) and self.text[self.pos] in 'dD':
            self._advance()
            value = self.text[start_pos:self.pos]
            return self._make_token(TokenType.FCONST, value, line=start_line, column=start_col)

        # Byte length literal suffixes: b/B/k/K/m/M/g/G (only for integers)
        if not is_float and self.pos < len(self.text):
            suffix_char = self.text[self.pos]
            if suffix_char in 'bBkKmMgG':
                self._advance()
                value = self.text[start_pos:self.pos]
                return self._make_token(TokenType.ICONST, value, line=start_line, column=start_col)

        value = self.text[start_pos:self.pos]
        token_type = TokenType.FCONST if is_float else TokenType.ICONST
        return self._make_token(token_type, value, line=start_line, column=start_col)

    def _read_hex_number(self):
        """Read a hexadecimal integer literal like 0x1A, 0XFF (Hive CharSetLiteral form)."""
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        # Skip 0x / 0X
        self._advance(2)
        while self.pos < len(self.text) and self.text[self.pos] in '0123456789abcdefABCDEF':
            self._advance()
        value = self.text[start_pos:self.pos]
        return self._make_token(TokenType.ICONST, value, line=start_line, column=start_col)

    def _read_identifier(self):
        """Read an identifier or keyword"""
        start_line = self.line
        start_col = self.column
        start_pos = self.pos

        # Read identifier characters
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isalnum() or ch == '_' or ord(ch) > 127:
                self._advance()
            else:
                break

        value = self.text[start_pos:self.pos]
        upper = value.upper()

        # Check if it's a keyword
        if is_keyword(upper):
            info = get_keyword_info(upper)
            token_name, category, collabel = info
            return self._make_token(
                TokenType.KEYWORD, upper,
                line=start_line, column=start_col,
                keyword_category=category,
                keyword_token=token_name
            )

        # Regular identifier
        return self._make_token(TokenType.IDENT, value,
                               line=start_line, column=start_col)

    def _read_backtick_identifier(self):
        """Read a backtick-quoted identifier `table_name`"""
        start_line = self.line
        start_col = self.column
        result = ['`']
        self._advance()  # skip opening `

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '`':
                result.append(ch)
                self._advance()
                # Doubled backtick = escaped backtick
                if self.pos < len(self.text) and self.text[self.pos] == '`':
                    result.append('`')
                    self._advance()
                else:
                    break
            else:
                result.append(ch)
                self._advance()

        return self._make_token(TokenType.BACKTICK_IDENT, ''.join(result),
                               line=start_line, column=start_col)

    def _read_operator(self):
        """Read an operator or multi-character token"""
        start_line = self.line
        start_col = self.column

        # Check multi-character operators first (longest match)
        for length in (3, 2):
            candidate = self._peek_multi(length)
            if candidate in self.MULTI_CHAR_OPS:
                token_type = self.MULTI_CHAR_OPS[candidate]
                self._advance(length)
                return self._make_token(token_type, candidate,
                                       line=start_line, column=start_col)

        ch = self.text[self.pos]

        # Single character operators
        single_ops = {
            '+': TokenType.OP, '-': TokenType.OP,
            '/': TokenType.OP, '%': TokenType.OP,
            '^': TokenType.OP, '&': TokenType.OP,
            '|': TokenType.OP, '~': TokenType.OP,
            '!': TokenType.OP,
            '<': TokenType.CMP_OP, '>': TokenType.CMP_OP,
            '=': TokenType.CMP_OP,
        }

        if ch in single_ops:
            self._advance()
            return self._make_token(single_ops[ch], ch,
                                   line=start_line, column=start_col)

        # Should not reach here
        self._advance()
        return self._make_token(TokenType.OP, ch,
                               line=start_line, column=start_col)

    def tokenize(self):
        """
        Tokenize the SQL text and return a list of Token objects.

        Returns:
            tuple: (tokens, errors) where tokens is a list of Token objects
                   and errors is a list of TokenizerError objects
        """
        self.tokens = []
        self.errors = []

        while self.pos < len(self.text):
            self._skip_whitespace()
            if self.pos >= len(self.text):
                break

            ch = self.text[self.pos]
            start_line = self.line
            start_col = self.column

            # ---- Comments ----
            if ch == '-' and self._char(1) == '-':
                self._skip_line_comment()
                continue

            if ch == '/' and self._char(1) == '*':
                token = self._read_block_comment()
                if token is not None:  # hint token
                    self.tokens.append(token)
                continue

            # ---- String constants ----
            # Hive supports both single-quote and double-quote string literals
            if ch == "'" or ch == '"':
                self.tokens.append(self._read_string(ch))
                continue

            # ---- Hex literal (0x..) — must precede plain number detection ----
            if ch == '0' and self._char(1) in ('x', 'X'):
                self.tokens.append(self._read_hex_number())
                continue

            # ---- Numbers ----
            if ch.isdigit():
                self.tokens.append(self._read_number())
                continue

            # ---- Identifiers and Keywords ----
            if ch.isalpha() or ch == '_' or ord(ch) > 127:
                self.tokens.append(self._read_identifier())
                continue

            # Backtick-quoted identifier (Hive-specific)
            if ch == '`':
                self.tokens.append(self._read_backtick_identifier())
                continue

            # ---- Punctuation ----
            if ch == ';':
                self._advance()
                self.tokens.append(self._make_token(TokenType.SEMICOLON, ';',
                                                   line=start_line, column=start_col))
                continue

            if ch == ',':
                self._advance()
                self.tokens.append(self._make_token(TokenType.COMMA, ',',
                                                   line=start_line, column=start_col))
                continue

            if ch == '(':
                self._advance()
                self.tokens.append(self._make_token(TokenType.LPAREN, '(',
                                                   line=start_line, column=start_col))
                continue

            if ch == ')':
                self._advance()
                self.tokens.append(self._make_token(TokenType.RPAREN, ')',
                                                   line=start_line, column=start_col))
                continue

            if ch == '[':
                self._advance()
                self.tokens.append(self._make_token(TokenType.LBRACKET, '[',
                                                   line=start_line, column=start_col))
                continue

            if ch == ']':
                self._advance()
                self.tokens.append(self._make_token(TokenType.RBRACKET, ']',
                                                   line=start_line, column=start_col))
                continue

            if ch == '{':
                self._advance()
                self.tokens.append(self._make_token(TokenType.LCURLY, '{',
                                                   line=start_line, column=start_col))
                continue

            if ch == '}':
                self._advance()
                self.tokens.append(self._make_token(TokenType.RCURLY, '}',
                                                   line=start_line, column=start_col))
                continue

            if ch == ':':
                self._advance()
                self.tokens.append(self._make_token(TokenType.COLON, ':',
                                                   line=start_line, column=start_col))
                continue

            if ch == '?':
                self._advance()
                self.tokens.append(self._make_token(TokenType.QUESTION, '?',
                                                   line=start_line, column=start_col))
                continue

            if ch == '$':
                self._advance()
                self.tokens.append(self._make_token(TokenType.DOLLAR, '$',
                                                   line=start_line, column=start_col))
                continue

            if ch == '.':
                self._advance()
                self.tokens.append(self._make_token(TokenType.DOT, '.',
                                                   line=start_line, column=start_col))
                continue

            if ch == '*':
                self._advance()
                self.tokens.append(self._make_token(TokenType.STAR, '*',
                                                   line=start_line, column=start_col))
                continue

            # ---- Operators ----
            if ch in '+-/%^&|~!<>=':
                self.tokens.append(self._read_operator())
                continue

            # ---- Unknown character ----
            self.errors.append(TokenizerError(
                f"Unexpected character: {ch!r}", start_line, start_col))
            self._advance()

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))

        return self.tokens, self.errors


def tokenize(sql_text):
    """
    Convenience function to tokenize SQL text.

    Args:
        sql_text: The SQL text to tokenize

    Returns:
        tuple: (tokens, errors)
    """
    tokenizer = HiveSQLTokenizer(sql_text)
    return tokenizer.tokenize()


def tokenize_to_dict(sql_text):
    """
    Tokenize SQL text and return as list of dicts (for JSON serialization).

    Args:
        sql_text: The SQL text to tokenize

    Returns:
        dict: {"tokens": [...], "errors": [...]}
    """
    tokens, errors = tokenize(sql_text)
    return {
        "tokens": [
            {
                "type": t.type,
                "value": t.value,
                "line": t.line,
                "column": t.column,
                "keyword_category": t.keyword_category.value if t.keyword_category else None,
                "keyword_token": t.keyword_token,
            }
            for t in tokens
        ],
        "errors": [
            {"message": str(e), "line": e.line, "column": e.column}
            for e in errors
        ],
    }


# ---- CLI Entry Point ----
if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python hive_sql_tokenizer.py <sql_text_or_file>")
        sys.exit(1)

    input_text = sys.argv[1]
    # If it's a file path, read the file
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    result = tokenize_to_dict(input_text)

    # Print summary
    print(f"Tokens: {len(result['tokens'])}")
    print(f"Errors: {len(result['errors'])}")
    print()

    # Print tokens
    for t in result['tokens']:
        cat = f" [{t['keyword_category']}]" if t['keyword_category'] else ""
        print(f"  L{t['line']:3d}:{t['column']:3d}  {t['type']:20s}  {t['value']!r}{cat}")

    if result['errors']:
        print("\nErrors:")
        for e in result['errors']:
            print(f"  L{e['line']}:{e['column']}  {e['message']}")

    # Also output JSON
    if '--json' in sys.argv:
        print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
