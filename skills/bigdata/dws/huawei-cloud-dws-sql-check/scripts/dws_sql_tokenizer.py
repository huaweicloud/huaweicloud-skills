# -*- coding: utf-8 -*-
"""
DWS SQL Tokenizer

Lexical analyzer for DWS SQL statements.
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
    SCONST = "SCONST"          # String constant
    ICONST = "ICONST"          # Integer constant
    FCONST = "FCONST"          # Float constant
    BCONST = "BCONST"          # Bit-string constant
    XCONST = "XCONST"          # Hex constant
    PARAM = "PARAM"            # $1, $2, ...
    TYPECAST = "TYPECAST"      # ::
    ORA_JOINOP = "ORA_JOINOP"  # (+)
    DOT_DOT = "DOT_DOT"       # ..
    COLON_EQUALS = "COLON_EQUALS"  # :=
    PARA_EQUALS = "PARA_EQUALS"    # ==
    OP = "OP"                  # Generic operator
    CMP_OP = "CMP_OP"         # Comparison operator

    # Special
    KEYWORD = "KEYWORD"        # DWS keyword
    COMMENT = "COMMENT"        # SQL comment
    HINT = "HINT"              # Optimizer hint /*+ ... */
    SEMICOLON = "SEMICOLON"    # ;
    COMMA = "COMMA"            # ,
    LPAREN = "LPAREN"          # (
    RPAREN = "RPAREN"          # )
    LBRACKET = "LBRACKET"      # [
    RBRACKET = "RBRACKET"      # ]
    DOT = "DOT"                # .
    STAR = "STAR"              # *
    EOF = "EOF"                # End of input


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


class DWSSQLTokenizer:
    """
    DWS SQL Lexical Analyzer

    Tokenizes SQL text following the DWS SQL lexical rules.
    Supports all DWS-specific tokens including:
    - Oracle-style outer join operator (+)
    - Optimizer hints /*+ ... */
    - Type cast operator ::
    - Dollar-quoted strings $$...$$
    - National character strings N'...'
    - E-strings E'...'
    """

    # Comparison operators
    CMP_OPS = {'<', '>', '=', '<=', '>=', '<>', '!=', '~', '~*', '!~', '!~*'}

    # Multi-character operators
    MULTI_CHAR_OPS = {
        '<=': TokenType.CMP_OP,
        '>=': TokenType.CMP_OP,
        '<>': TokenType.CMP_OP,
        '!=': TokenType.CMP_OP,
        '::': TokenType.TYPECAST,
        ':=': TokenType.COLON_EQUALS,
        '==': TokenType.PARA_EQUALS,
        '..': TokenType.DOT_DOT,
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
        start_line = self.line
        start_col = self.column
        self._advance(2)  # skip --
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self._advance()
        # Comments are not emitted as tokens by default

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
            # The comment_text already starts with + since we read past /*
            # before checking for +. The + is the first char of content.
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
                    break  # End of string
            elif ch == '\\':
                # Backslash escape
                result.append(ch)
                self._advance()
                if self.pos < len(self.text):
                    result.append(self.text[self.pos])
                    self._advance()
            elif ch == '\n':
                # Unterminated string
                self.errors.append(TokenizerError(
                    f"Unterminated string constant", start_line, start_col))
                break
            else:
                result.append(ch)
                self._advance()

        return self._make_token(TokenType.SCONST, ''.join(result),
                               line=start_line, column=start_col)

    def _read_dollar_string(self):
        """Read a dollar-quoted string $$...$$ or $tag$...$tag$"""
        start_line = self.line
        start_col = self.column

        # Read the opening tag
        self._advance()  # skip $
        tag = ['$']
        while self.pos < len(self.text) and self.text[self.pos] != '$':
            tag.append(self.text[self.pos])
            self._advance()
        if self.pos < len(self.text):
            tag.append('$')
            self._advance()  # skip closing $

        tag_str = ''.join(tag)

        # Read until matching closing tag
        result = [tag_str]
        while self.pos < len(self.text):
            if self.text[self.pos] == '$':
                # Check for closing tag
                candidate = self.text[self.pos:self.pos + len(tag_str)]
                if candidate == tag_str:
                    result.append(tag_str)
                    self._advance(len(tag_str))
                    break
            result.append(self.text[self.pos])
            self._advance()

        return self._make_token(TokenType.SCONST, ''.join(result),
                               line=start_line, column=start_col)

    def _read_number(self):
        """Read a numeric constant (integer or float)"""
        start_line = self.line
        start_col = self.column
        start_pos = self.pos

        # Check for hex integer 0x...
        if (self.text[self.pos] == '0' and
            self.pos + 1 < len(self.text) and
            self.text[self.pos + 1] in 'xX'):
            self._advance(2)
            while self.pos < len(self.text) and self.text[self.pos] in '0123456789abcdefABCDEF':
                self._advance()
            return self._make_token(TokenType.ICONST, self.text[start_pos:self.pos],
                                   line=start_line, column=start_col)

        # Read digits
        is_float = False
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self._advance()

        # Decimal point
        if self.pos < len(self.text) and self.text[self.pos] == '.':
            # Check for .. operator (range)
            if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '.':
                # It's the .. operator, don't consume the dot
                if self.pos == start_pos + 0:
                    # No digits before .. - this shouldn't happen normally
                    pass
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

        value = self.text[start_pos:self.pos]
        token_type = TokenType.FCONST if is_float else TokenType.ICONST
        return self._make_token(token_type, value, line=start_line, column=start_col)

    def _read_bit_string(self):
        """Read a bit-string constant b'...' or B'...'"""
        start_line = self.line
        start_col = self.column
        start_pos = self.pos
        self._advance()  # skip b/B
        # Read the string part
        token = self._read_string("'")
        # Reconstruct full value
        return self._make_token(TokenType.BCONST, self.text[start_pos:token.column + len(token.value)],
                               line=start_line, column=start_col)

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

    def _read_quoted_identifier(self):
        """Read a double-quoted identifier"""
        start_line = self.line
        start_col = self.column
        result = ['"']
        self._advance()  # skip opening "

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == '"':
                result.append(ch)
                self._advance()
                # Doubled quote = escaped quote
                if self.pos < len(self.text) and self.text[self.pos] == '"':
                    result.append('"')
                    self._advance()
                else:
                    break
            else:
                result.append(ch)
                self._advance()

        return self._make_token(TokenType.IDENT, ''.join(result),
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
            '|': TokenType.OP, '#': TokenType.OP,
            '@': TokenType.OP, '~': TokenType.OP,
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

    def _check_ora_joinop(self):
        """Check for Oracle-style outer join operator (+)

        This appears as: column(+) in WHERE clause
        We detect (+) pattern when we see '(' followed by '+' followed by ')'
        """
        if (self.pos + 2 < len(self.text) and
            self.text[self.pos] == '(' and
            self.text[self.pos + 1] == '+' and
            self.text[self.pos + 2] == ')'):
            start_line = self.line
            start_col = self.column
            self._advance(3)
            return self._make_token(TokenType.ORA_JOINOP, '(+)',
                                   line=start_line, column=start_col)
        return None

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
            if ch == "'":
                self.tokens.append(self._read_string())
                continue

            # National character string N'...'
            if ch in 'nN' and self._char(1) == "'":
                self._advance()  # skip N
                token = self._read_string("'")
                token.value = 'N' + token.value
                self.tokens.append(token)
                continue

            # E-string E'...'
            if ch in 'eE' and self._char(1) == "'":
                self._advance()  # skip E
                token = self._read_string("'")
                token.value = 'E' + token.value
                self.tokens.append(token)
                continue

            # Dollar-quoted string
            if ch == '$' and (self._char(1) == '$' or
                              (self._char(1) and self._char(1).isalpha())):
                self.tokens.append(self._read_dollar_string())
                continue

            # ---- Bit-string constants ----
            if ch in 'bB' and self._char(1) == "'":
                start_line_save = self.line
                start_col_save = self.column
                prefix = ch
                self._advance()  # skip b/B
                token = self._read_string("'")
                token.type = TokenType.BCONST
                token.value = prefix + token.value
                self.tokens.append(token)
                continue

            # Hex string X'...'
            if ch in 'xX' and self._char(1) == "'":
                start_line_save = self.line
                start_col_save = self.column
                prefix = ch
                self._advance()  # skip x/X
                token = self._read_string("'")
                token.type = TokenType.XCONST
                token.value = prefix + token.value
                self.tokens.append(token)
                continue

            # ---- Numbers ----
            if ch.isdigit():
                self.tokens.append(self._read_number())
                continue

            # ---- Parameter reference ----
            if ch == '$' and self._char(1) and self._char(1).isdigit():
                self._advance()  # skip $
                start_pos = self.pos
                while self.pos < len(self.text) and self.text[self.pos].isdigit():
                    self._advance()
                self.tokens.append(self._make_token(
                    TokenType.PARAM, '$' + self.text[start_pos:self.pos],
                    line=start_line, column=start_col))
                continue

            # ---- Identifiers and Keywords ----
            if ch.isalpha() or ch == '_' or ord(ch) > 127:
                self.tokens.append(self._read_identifier())
                continue

            # Quoted identifier
            if ch == '"':
                self.tokens.append(self._read_quoted_identifier())
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
                # Check for Oracle (+) join operator
                ora_token = self._check_ora_joinop()
                if ora_token:
                    self.tokens.append(ora_token)
                    continue
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

            if ch == '.':
                # Check for .. operator
                if self._char(1) == '.':
                    self._advance(2)
                    self.tokens.append(self._make_token(TokenType.DOT_DOT, '..',
                                                       line=start_line, column=start_col))
                    continue
                self._advance()
                self.tokens.append(self._make_token(TokenType.DOT, '.',
                                                   line=start_line, column=start_col))
                continue

            if ch == '*':
                self._advance()
                self.tokens.append(self._make_token(TokenType.STAR, '*',
                                                   line=start_line, column=start_col))
                continue

            if ch == ':':
                # Check for :: (typecast) and := (assignment)
                if self._char(1) == ':':
                    self._advance(2)
                    self.tokens.append(self._make_token(TokenType.TYPECAST, '::',
                                                       line=start_line, column=start_col))
                    continue
                if self._char(1) == '=':
                    self._advance(2)
                    self.tokens.append(self._make_token(TokenType.COLON_EQUALS, ':=',
                                                       line=start_line, column=start_col))
                    continue
                self._advance()
                self.tokens.append(self._make_token(TokenType.OP, ':',
                                                   line=start_line, column=start_col))
                continue

            # ---- Operators ----
            if ch in '+-/%^&|@~!<>=':
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
    tokenizer = DWSSQLTokenizer(sql_text)
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
        print("Usage: python dws_sql_tokenizer.py <sql_text_or_file>")
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
        print(f"  L{t['line']:3d}:{t['column']:3d}  {t['type']:12s}  {t['value']!r}{cat}")

    if result['errors']:
        print("\nErrors:")
        for e in result['errors']:
            print(f"  L{e['line']}:{e['column']}  {e['message']}")

    # Also output JSON
    if '--json' in sys.argv:
        print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
