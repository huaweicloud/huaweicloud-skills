# -*- coding: utf-8 -*-
"""
Apache Doris SQL Tokenizer

Lexical analyzer for Apache Doris SQL statements (based on Doris 3.1.4 Nereids grammar).
Tokenizes SQL text into a stream of typed tokens with position information.

Source: Doris 3.1.4 fe/fe-core/src/main/antlr4/org/apache/doris/nereids/DorisLexer.g4
"""

import re
import sys
import os

# Add rules directory to path for keyword imports
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'rules'))
from keywords import (
    is_keyword, get_keyword_info, is_reserved_keyword,
    KeywordCategory, ALL_KEYWORDS, RESERVED_KEYWORDS, NON_RESERVED_KEYWORDS
)


class TokenType:
    """Token type constants (mirrors DorisLexer.g4 token names)"""
    # Punctuation
    SEMICOLON = "SEMICOLON"      # ;
    LEFT_PAREN = "LEFT_PAREN"   # (
    RIGHT_PAREN = "RIGHT_PAREN" # )
    COMMA = "COMMA"             # ,
    DOT = "DOT"                 # .
    DOTDOTDOT = "DOTDOTDOT"     # ...
    LEFT_BRACKET = "LEFT_BRACKET"  # [
    RIGHT_BRACKET = "RIGHT_BRACKET"  # ]
    LEFT_BRACE = "LEFT_BRACE"   # {
    RIGHT_BRACE = "RIGHT_BRACE" # }
    COLON = "COLON"             # :
    ATSIGN = "ATSIGN"           # @
    DOUBLEATSIGN = "DOUBLEATSIGN"  # @@

    # Operators
    EQ = "EQ"                   # = or ==
    NSEQ = "NSEQ"               # <=>
    NEQ = "NEQ"                 # <> or !=
    LT = "LT"                   # <
    LTE = "LTE"                 # <= or !>
    GT = "GT"                   # >
    GTE = "GTE"                 # >= or !<
    PLUS = "PLUS"               # +
    SUBTRACT = "SUBTRACT"       # -
    ASTERISK = "ASTERISK"       # *
    SLASH = "SLASH"             # /
    MOD = "MOD"                 # %
    TILDE = "TILDE"             # ~
    AMPERSAND = "AMPERSAND"     # &
    LOGICALAND = "LOGICALAND"   # &&
    LOGICALNOT = "LOGICALNOT"   # !
    PIPE = "PIPE"               # |
    DOUBLEPIPES = "DOUBLEPIPES"  # ||
    HAT = "HAT"                 # ^
    ARROW = "ARROW"             # ->

    # Literals
    STRING_LITERAL = "STRING_LITERAL"      # 'string' or "string"
    BACKQUOTED_IDENTIFIER = "BACKQUOTED_IDENTIFIER"  # `ident`
    IDENTIFIER = "IDENTIFIER"               # ident (letters/digits/_)
    BIGINT_LITERAL = "BIGINT_LITERAL"       # 123L
    SMALLINT_LITERAL = "SMALLINT_LITERAL"   # 123S
    TINYINT_LITERAL = "TINYINT_LITERAL"     # 123Y
    INTEGER_VALUE = "INTEGER_VALUE"         # 123
    EXPONENT_VALUE = "EXPONENT_VALUE"       # 1E5
    DECIMAL_VALUE = "DECIMAL_VALUE"         # 1.23
    BIGDECIMAL_LITERAL = "BIGDECIMAL_LITERAL"  # 123BD
    PLACEHOLDER = "PLACEHOLDER"             # ?

    # Special
    KEYWORD = "KEYWORD"          # Doris keyword
    HINT = "HINT"                # Optimizer hint /*+ ... */
    COMMENT = "COMMENT"          # SQL comment (skipped)
    EOF = "EOF"                  # End of input
    UNKNOWN = "UNKNOWN"          # Unrecognized character


class Token:
    """Represents a single SQL token with type, value, and position"""

    __slots__ = ('type', 'value', 'line', 'column', 'keyword_category', 'keyword_token')

    def __init__(self, type_, value, line=0, column=0, keyword_category=None, keyword_token=None):
        self.type = type_
        self.value = value
        self.line = line
        self.column = column
        self.keyword_category = keyword_category  # KeywordCategory if keyword
        self.keyword_token = keyword_token         # Grammar token name if keyword

    def __repr__(self):
        cat = f" [{self.keyword_category.value}]" if self.keyword_category else ""
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

    def is_punctuation(self, *types):
        """Check if token is one of the specified punctuation types"""
        return self.type in types


class TokenizerError(Exception):
    """Error during tokenization"""

    def __init__(self, message, line=0, column=0):
        super().__init__(message)
        self.line = line
        self.column = column


# ============================================================
# Token Patterns (ordered by priority)
# ============================================================

# Multi-char operators (longest first to avoid partial matches)
_MULTI_CHAR_OPS = [
    ('...', TokenType.DOTDOTDOT),
    ('<=>', TokenType.NSEQ),
    ('==', TokenType.EQ),
    ('!=', TokenType.NEQ),
    ('<>', TokenType.NEQ),
    ('<=', TokenType.LTE),
    ('!>', TokenType.LTE),
    ('>=', TokenType.GTE),
    ('!<', TokenType.GTE),
    ('&&', TokenType.LOGICALAND),
    ('||', TokenType.DOUBLEPIPES),
    ('->', TokenType.ARROW),
    ('@@', TokenType.DOUBLEATSIGN),
]

# Single-char operators/punctuation
_SINGLE_CHAR_OPS = {
    ';': TokenType.SEMICOLON,
    '(': TokenType.LEFT_PAREN,
    ')': TokenType.RIGHT_PAREN,
    ',': TokenType.COMMA,
    '.': TokenType.DOT,
    '[': TokenType.LEFT_BRACKET,
    ']': TokenType.RIGHT_BRACKET,
    '{': TokenType.LEFT_BRACE,
    '}': TokenType.RIGHT_BRACE,
    ':': TokenType.COLON,
    '@': TokenType.ATSIGN,
    '=': TokenType.EQ,
    '<': TokenType.LT,
    '>': TokenType.GT,
    '+': TokenType.PLUS,
    '-': TokenType.SUBTRACT,
    '*': TokenType.ASTERISK,
    '/': TokenType.SLASH,
    '%': TokenType.MOD,
    '~': TokenType.TILDE,
    '&': TokenType.AMPERSAND,
    '!': TokenType.LOGICALNOT,
    '|': TokenType.PIPE,
    '^': TokenType.HAT,
    '?': TokenType.PLACEHOLDER,
}

# Regex patterns for literals
_RE_BIGINT = re.compile(r'^\d+[Ll]$')
_RE_SMALLINT = re.compile(r'^\d+[Ss]$')
_RE_TINYINT = re.compile(r'^\d+[Yy]$')
_RE_BIGDECIMAL = re.compile(r'^(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?[Bb][Dd]$')
_RE_EXPONENT = re.compile(r'^(\d+([eE][+-]?\d+)|(\d+\.\d*|\.\d+|\d+\.\d*)([eE][+-]?\d+))$')
_RE_DECIMAL = re.compile(r'^\d+\.\d*$|^\.\d+$')
_RE_INTEGER = re.compile(r'^\d+$')
_RE_IDENTIFIER = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$]*$')


class DorisSQLTokenizer:
    """
    Apache Doris SQL Lexical Analyzer

    Tokenizes SQL text following the Doris Nereids lexical rules.
    Supports all Doris-specific tokens including:
    - Backtick-quoted identifiers (`table_name`)
    - Optimizer hints /*+ ... */
    - Doris operators: <=> (null-safe), == (alias for =), !> / !< (aliases)
    - Arrow operator -> for JSON/struct field access
    - String concatenation ||
    - Logical && / !
    - Typed integer literals (L/S/Y/BD suffixes)
    """

    def __init__(self, sql_text):
        self.text = sql_text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []

    def _peek(self, offset=0):
        """Peek at character at offset from current position"""
        idx = self.pos + offset
        if idx >= len(self.text):
            return ''
        return self.text[idx]

    def _advance(self, n=1):
        """Advance position by n characters, updating line/column"""
        for _ in range(n):
            if self.pos < len(self.text):
                ch = self.text[self.pos]
                self.pos += 1
                if ch == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1

    def _error(self, msg):
        """Record a tokenizer error"""
        self.errors.append(TokenizerError(msg, self.line, self.column))

    def tokenize(self):
        """Tokenize the SQL text into a list of tokens"""
        while self.pos < len(self.text):
            ch = self._peek()

            # Skip whitespace
            if ch in ' \r\n\t':
                self._advance()
                continue

            # Skip line comments (-- ...)
            if ch == '-' and self._peek(1) == '-':
                self._skip_line_comment()
                continue

            # Handle /*+ ... */ hints and /* ... */ comments
            if ch == '/' and self._peek(1) == '*':
                if self._peek(2) == '+':
                    self._read_hint()
                else:
                    self._skip_block_comment()
                continue

            # Backtick-quoted identifiers
            if ch == '`':
                self._read_backquoted_identifier()
                continue

            # String literals
            if ch == "'" or ch == '"':
                self._read_string_literal(ch)
                continue

            # Numbers
            if ch.isdigit() or (ch == '.' and self._peek(1).isdigit()):
                self._read_number()
                continue

            # Multi-char operators (longest match first)
            matched = False
            for op_str, tok_type in _MULTI_CHAR_OPS:
                if self.text[self.pos:self.pos + len(op_str)] == op_str:
                    self.tokens.append(Token(tok_type, op_str, self.line, self.column))
                    self._advance(len(op_str))
                    matched = True
                    break
            if matched:
                continue

            # Single-char operators/punctuation
            if ch in _SINGLE_CHAR_OPS:
                tok_type = _SINGLE_CHAR_OPS[ch]
                self.tokens.append(Token(tok_type, ch, self.line, self.column))
                self._advance()
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == '_' or ch == '$':
                self._read_identifier_or_keyword()
                continue

            # Unrecognized character
            self._error(f"Unrecognized character: {ch!r}")
            self.tokens.append(Token(TokenType.UNKNOWN, ch, self.line, self.column))
            self._advance()

        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens, self.errors

    def _skip_line_comment(self):
        """Skip a -- single-line comment"""
        start_col = self.column
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self._advance()
        # Comment is skipped (channel HIDDEN in DorisLexer)

    def _skip_block_comment(self):
        """Skip a /* ... */ block comment"""
        # Check for unclosed comment
        start_line, start_col = self.line, self.column
        self._advance(2)  # skip /*
        depth = 1
        while self.pos < len(self.text) and depth > 0:
            if self.text[self.pos] == '*' and self._peek(1) == '/':
                self._advance(2)
                depth -= 1
            elif self.text[self.pos] == '/' and self._peek(1) == '*':
                self._advance(2)
                depth += 1
            else:
                self._advance()
        if depth > 0:
            self._error("Unclosed block comment")

    def _read_hint(self):
        """Read a /*+ ... */ optimizer hint as a HINT token"""
        start_line, start_col = self.line, self.column
        start_pos = self.pos
        self._advance(3)  # skip /*+
        hint_content = '/*+'
        while self.pos < len(self.text):
            if self.text[self.pos] == '*' and self._peek(1) == '/':
                hint_content += '*/'
                self._advance(2)
                self.tokens.append(Token(TokenType.HINT, hint_content, start_line, start_col))
                return
            hint_content += self.text[self.pos]
            self._advance()
        self._error("Unclosed hint")

    def _read_backquoted_identifier(self):
        """Read a `identifier` (backtick-quoted)"""
        start_line, start_col = self.line, self.column
        self._advance()  # skip opening `
        value = ''
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '`':
                # Check for escaped backtick (``)
                if self._peek(1) == '`':
                    value += '`'
                    self._advance(2)
                else:
                    self._advance()  # skip closing `
                    self.tokens.append(Token(
                        TokenType.BACKQUOTED_IDENTIFIER, value,
                        start_line, start_col
                    ))
                    return
            else:
                value += ch
                self._advance()
        self._error("Unclosed backtick-quoted identifier")

    def _read_string_literal(self, quote):
        """Read a 'string' or "string" literal"""
        start_line, start_col = self.line, self.column
        self._advance()  # skip opening quote
        value = ''
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '\\':
                # Escape sequence
                value += ch
                self._advance()
                if self.pos < len(self.text):
                    value += self.text[self.pos]
                    self._advance()
            elif ch == quote:
                # Check for doubled quote escape ('' or "")
                if self._peek(1) == quote:
                    value += quote
                    self._advance(2)
                else:
                    self._advance()  # skip closing quote
                    self.tokens.append(Token(
                        TokenType.STRING_LITERAL, value,
                        start_line, start_col
                    ))
                    return
            else:
                value += ch
                self._advance()
        self._error(f"Unclosed string literal starting with {quote}")

    def _read_number(self):
        """Read a numeric literal (integer, decimal, exponent, bigint, etc.)"""
        start_line, start_col = self.line, self.column
        start_pos = self.pos
        # Read digits and optional decimal/exponent parts
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            self._advance()
        # Check for exponent
        if self.pos < len(self.text) and self.text[self.pos] in 'eE':
            self._advance()
            if self.pos < len(self.text) and self.text[self.pos] in '+-':
                self._advance()
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self._advance()
        # Check for type suffixes (L, S, Y, BD)
        suffix = ''
        if self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch in 'Ll':
                suffix = 'L'
                self._advance()
            elif ch in 'Ss':
                suffix = 'S'
                self._advance()
            elif ch in 'Yy':
                suffix = 'Y'
                self._advance()
            elif ch in 'Bb' and self.pos + 1 < len(self.text) and self.text[self.pos + 1] in 'Dd':
                suffix = 'BD'
                self._advance(2)

        value = self.text[start_pos:self.pos]
        tok_type = self._classify_number(value, suffix)
        self.tokens.append(Token(tok_type, value, start_line, start_col))

    def _classify_number(self, value, suffix):
        """Classify a numeric literal into the right token type"""
        if suffix == 'L':
            return TokenType.BIGINT_LITERAL
        if suffix == 'S':
            return TokenType.SMALLINT_LITERAL
        if suffix == 'Y':
            return TokenType.TINYINT_LITERAL
        if suffix == 'BD':
            return TokenType.BIGDECIMAL_LITERAL
        if _RE_EXPONENT.match(value):
            return TokenType.EXPONENT_VALUE
        if _RE_DECIMAL.match(value):
            return TokenType.DECIMAL_VALUE
        return TokenType.INTEGER_VALUE

    def _read_identifier_or_keyword(self):
        """Read an identifier or keyword"""
        start_line, start_col = self.line, self.column
        start_pos = self.pos
        # Doris IDENTIFIER: (LETTER | DIGIT | '_')+ (note: starts with letter/_/$)
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isalnum() or ch == '_' or ch == '$':
                self._advance()
            else:
                break
        value = self.text[start_pos:self.pos]
        # Check if it's a keyword (case-insensitive)
        kw_info = get_keyword_info(value)
        if kw_info:
            token_name, category = kw_info
            self.tokens.append(Token(
                TokenType.KEYWORD, value.upper(),
                start_line, start_col,
                keyword_category=category,
                keyword_token=token_name
            ))
        else:
            self.tokens.append(Token(
                TokenType.IDENTIFIER, value,
                start_line, start_col
            ))


def tokenize(sql_text):
    """
    Tokenize SQL text into a list of tokens.
    Returns: (tokens, errors)
    """
    tokenizer = DorisSQLTokenizer(sql_text)
    return tokenizer.tokenize()


def tokenize_for_display(sql_text):
    """
    Tokenize SQL text and return formatted string for display.
    """
    tokens, errors = tokenize(sql_text)
    lines = []
    for tok in tokens:
        if tok.type == TokenType.EOF:
            continue
        lines.append(str(tok))
    if errors:
        lines.append("\nErrors:")
        for err in errors:
            lines.append(f"  L{err.line}:{err.column} - {err}")
    return "\n".join(lines)


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python doris_sql_tokenizer.py \"<sql_text>\"")
        print("\nDoris SQL Tokenizer - Lexical analyzer for Apache Doris SQL")
        print(f"Total keywords: {len(ALL_KEYWORDS)} (Reserved: {len(RESERVED_KEYWORDS)}, Non-reserved: {len(NON_RESERVED_KEYWORDS)})")
        sys.exit(1)

    sql_text = sys.argv[1]
    tokens, errors = tokenize(sql_text)

    print(f"# Doris SQL Tokenizer Output")
    print(f"# Total keywords in lexicon: {len(ALL_KEYWORDS)}")
    print(f"# Tokens: {len([t for t in tokens if t.type != TokenType.EOF])}")
    print()

    for tok in tokens:
        if tok.type == TokenType.EOF:
            continue
        cat = f" [{tok.keyword_category.value}]" if tok.keyword_category else ""
        print(f"{tok.type:25s} | {tok.value!r:30s} | L{tok.line}:{tok.column}{cat}")

    if errors:
        print(f"\n# Errors ({len(errors)}):")
        for err in errors:
            print(f"  L{err.line}:{err.column} - {err}")


if __name__ == "__main__":
    main()
