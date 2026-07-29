# -*- coding: utf-8 -*-
"""
HetuEngine SQL Tokenizer

Lexical analyzer for HetuEngine SQL statements.
Tokenizes SQL text into a stream of typed tokens with position information.

Supports Presto/Trino + Hive compatibility syntax including:
- Dollar-quoted strings $$...$$ (Python UDF definitions)
- Lambda expressions: x -> x + 1
- Unicode strings U&'...'
- Escape strings E'...'
- Hex strings X'...'
- National character strings N'...'
- Backtick-quoted identifiers `identifier` (Hive compatibility)
- Arrow operators -> and ->> (lambda / JSON path)
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rules'))
from keywords import (
    is_keyword, get_keyword_info, is_reserved_keyword,
    KeywordCategory, ALL_KEYWORDS, RESERVED_KEYWORDS
)


class TokenType:
    IDENT = "IDENT"
    SCONST = "SCONST"
    ICONST = "ICONST"
    FCONST = "FCONST"
    BCONST = "BCONST"
    XCONST = "XCONST"
    PARAM = "PARAM"
    TYPECAST = "TYPECAST"
    ORA_JOINOP = "ORA_JOINOP"
    DOT_DOT = "DOT_DOT"
    COLON_EQUALS = "COLON_EQUALS"
    PARA_EQUALS = "PARA_EQUALS"
    OP = "OP"
    CMP_OP = "CMP_OP"

    KEYWORD = "KEYWORD"
    COMMENT = "COMMENT"
    HINT = "HINT"
    SEMICOLON = "SEMICOLON"
    COMMA = "COMMA"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    DOT = "DOT"
    STAR = "STAR"
    EOF = "EOF"

    DOLLAR = "DOLLAR"
    ARROW = "ARROW"
    DOUBLE_ARROW = "DOUBLE_ARROW"
    QUESTION_MARK = "QUESTION_MARK"


class Token:
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
        if self.type != TokenType.KEYWORD:
            return False
        if name is None:
            return True
        return self.value.upper() == name.upper()

    def is_reserved(self):
        return self.keyword_category == KeywordCategory.RESERVED


class TokenizerError(Exception):
    def __init__(self, message, line=0, column=0):
        super().__init__(message)
        self.line = line
        self.column = column


class HetuSQLTokenizer:
    """
    HetuEngine SQL Lexical Analyzer

    Tokenizes SQL text following HetuEngine (Presto/Trino + Hive) lexical rules.
    Supports all HetuEngine-specific tokens including:
    - Dollar-quoted strings $$...$$ for Python UDF
    - Lambda arrow operators -> and ->>
    - Unicode strings U&'...'
    - Escape strings E'...'
    - Hex strings X'...'
    - National character strings N'...'
    - Backtick-quoted identifiers (Hive compatibility)
    - Oracle-style outer join operator (+) for compatibility
    - Optimizer hints /*+ ... */
    - Type cast operator ::
    """

    CMP_OPS = {'<', '>', '=', '<=', '>=', '<>', '!=', '~', '~*', '!~', '!~*'}

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
        '->': TokenType.ARROW,
        '->>': TokenType.DOUBLE_ARROW,
    }

    def __init__(self, sql_text):
        self.text = sql_text
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self.errors = []

    def _char(self, offset=0):
        p = self.pos + offset
        if p < len(self.text):
            return self.text[p]
        return None

    def _advance(self, n=1):
        for _ in range(n):
            if self.pos < len(self.text):
                if self.text[self.pos] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1

    def _peek_multi(self, n):
        return self.text[self.pos:self.pos + n]

    def _make_token(self, type_, value, line=None, column=None, **kwargs):
        return Token(
            type_, value,
            line=line or self.line,
            column=column or self.column,
            **kwargs
        )

    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in ' \t\n\r':
            self._advance()

    def _skip_line_comment(self):
        start_line = self.line
        start_col = self.column
        self._advance(2)
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self._advance()

    def _read_block_comment(self):
        start_line = self.line
        start_col = self.column
        self._advance(2)

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
        return None

    def _read_string(self, quote_char="'"):
        start_line = self.line
        start_col = self.column
        result = [quote_char]
        self._advance()

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == quote_char:
                result.append(ch)
                self._advance()
                if self.pos < len(self.text) and self.text[self.pos] == quote_char:
                    result.append(self.text[self.pos])
                    self._advance()
                else:
                    break
            elif ch == '\\':
                result.append(ch)
                self._advance()
                if self.pos < len(self.text):
                    result.append(self.text[self.pos])
                    self._advance()
            elif ch == '\n':
                self.errors.append(TokenizerError(
                    f"Unterminated string constant", start_line, start_col))
                break
            else:
                result.append(ch)
                self._advance()

        return self._make_token(TokenType.SCONST, ''.join(result),
                               line=start_line, column=start_col)

    def _read_dollar_string(self):
        start_line = self.line
        start_col = self.column

        self._advance()
        tag = ['$']
        while self.pos < len(self.text) and self.text[self.pos] != '$':
            tag.append(self.text[self.pos])
            self._advance()
        if self.pos < len(self.text):
            tag.append('$')
            self._advance()

        tag_str = ''.join(tag)

        result = [tag_str]
        while self.pos < len(self.text):
            if self.text[self.pos] == '$':
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
        start_line = self.line
        start_col = self.column
        start_pos = self.pos

        if (self.text[self.pos] == '0' and
            self.pos + 1 < len(self.text) and
            self.text[self.pos + 1] in 'xX'):
            self._advance(2)
            while self.pos < len(self.text) and self.text[self.pos] in '0123456789abcdefABCDEF':
                self._advance()
            return self._make_token(TokenType.ICONST, self.text[start_pos:self.pos],
                                   line=start_line, column=start_col)

        is_float = False
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self._advance()

        if self.pos < len(self.text) and self.text[self.pos] == '.':
            if self.pos + 1 < len(self.text) and self.text[self.pos + 1] == '.':
                return self._make_token(TokenType.ICONST, self.text[start_pos:self.pos],
                                       line=start_line, column=start_col)
            is_float = True
            self._advance()
            while self.pos < len(self.text) and self.text[self.pos].isdigit():
                self._advance()

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

    def _read_identifier(self):
        start_line = self.line
        start_col = self.column
        start_pos = self.pos

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch.isalnum() or ch == '_' or ord(ch) > 127:
                self._advance()
            else:
                break

        value = self.text[start_pos:self.pos]
        upper = value.upper()

        if is_keyword(upper):
            info = get_keyword_info(upper)
            if info is not None:
                token_name = info.keyword
                category = info.category
                return self._make_token(
                    TokenType.KEYWORD, upper,
                    line=start_line, column=start_col,
                    keyword_category=category,
                    keyword_token=token_name
                )

        return self._make_token(TokenType.IDENT, value,
                               line=start_line, column=start_col)

    def _read_quoted_identifier(self, quote_char='"'):
        start_line = self.line
        start_col = self.column
        result = [quote_char]
        self._advance()

        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == quote_char:
                result.append(ch)
                self._advance()
                if self.pos < len(self.text) and self.text[self.pos] == quote_char:
                    result.append(quote_char)
                    self._advance()
                else:
                    break
            else:
                result.append(ch)
                self._advance()

        return self._make_token(TokenType.IDENT, ''.join(result),
                               line=start_line, column=start_col)

    def _read_operator(self):
        start_line = self.line
        start_col = self.column

        for length in (3, 2):
            candidate = self._peek_multi(length)
            if candidate in self.MULTI_CHAR_OPS:
                token_type = self.MULTI_CHAR_OPS[candidate]
                self._advance(length)
                return self._make_token(token_type, candidate,
                                       line=start_line, column=start_col)

        ch = self.text[self.pos]

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

        self._advance()
        return self._make_token(TokenType.OP, ch,
                               line=start_line, column=start_col)

    def _check_ora_joinop(self):
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

    def _read_prefixed_string(self, prefix):
        start_line = self.line
        start_col = self.column
        prefix_len = len(prefix)
        self._advance(prefix_len)
        token = self._read_string("'")
        token.value = prefix + token.value
        return token

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

            if ch == '-' and self._char(1) == '-':
                self._skip_line_comment()
                continue

            if ch == '/' and self._char(1) == '*':
                token = self._read_block_comment()
                if token is not None:
                    self.tokens.append(token)
                continue

            if ch == "'":
                self.tokens.append(self._read_string())
                continue

            if ch in 'nN' and self._char(1) == "'":
                self.tokens.append(self._read_prefixed_string(ch))
                continue

            if ch in 'uU' and self._char(1) == '&' and self._char(2) == "'":
                self.tokens.append(self._read_prefixed_string(ch + '&'))
                continue

            if ch in 'eE' and self._char(1) == "'":
                next_next = self._char(2)
                if next_next is None or not next_next.isalpha():
                    self.tokens.append(self._read_prefixed_string(ch))
                    continue

            if ch in 'xX' and self._char(1) == "'":
                self._advance()
                token = self._read_string("'")
                token.type = TokenType.XCONST
                token.value = ch + token.value
                self.tokens.append(token)
                continue

            if ch == '$' and (self._char(1) == '$' or
                              (self._char(1) is not None and
                               (self._char(1).isalpha() or self._char(1) == '_'))):
                is_dollar_string = False
                if self._char(1) == '$':
                    is_dollar_string = True
                else:
                    scan = self.pos + 1
                    while scan < len(self.text) and self.text[scan] != '$':
                        scan += 1
                    if scan < len(self.text) and self.text[scan] == '$':
                        is_dollar_string = True

                if is_dollar_string:
                    self.tokens.append(self._read_dollar_string())
                    continue

            if ch in 'bB' and self._char(1) == "'":
                self._advance()
                token = self._read_string("'")
                token.type = TokenType.BCONST
                token.value = ch + token.value
                self.tokens.append(token)
                continue

            if ch.isdigit():
                self.tokens.append(self._read_number())
                continue

            if ch == '$' and self._char(1) and self._char(1).isdigit():
                self._advance()
                start_pos = self.pos
                while self.pos < len(self.text) and self.text[self.pos].isdigit():
                    self._advance()
                self.tokens.append(self._make_token(
                    TokenType.PARAM, '$' + self.text[start_pos:self.pos],
                    line=start_line, column=start_col))
                continue

            if ch == '?':
                self._advance()
                self.tokens.append(self._make_token(
                    TokenType.QUESTION_MARK, '?',
                    line=start_line, column=start_col))
                continue

            if ch.isalpha() or ch == '_' or ord(ch) > 127:
                self.tokens.append(self._read_identifier())
                continue

            if ch == '"':
                self.tokens.append(self._read_quoted_identifier('"'))
                continue

            if ch == '`':
                self.tokens.append(self._read_quoted_identifier('`'))
                continue

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

            if ch == '-' and self._char(1) == '>':
                if self._char(2) == '>':
                    self._advance(3)
                    self.tokens.append(self._make_token(TokenType.DOUBLE_ARROW, '->>',
                                                       line=start_line, column=start_col))
                    continue
                self._advance(2)
                self.tokens.append(self._make_token(TokenType.ARROW, '->',
                                                   line=start_line, column=start_col))
                continue

            if ch in '+-/%^&|@~!<>=':
                self.tokens.append(self._read_operator())
                continue

            self.errors.append(TokenizerError(
                f"Unexpected character: {ch!r}", start_line, start_col))
            self._advance()

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
    tokenizer = HetuSQLTokenizer(sql_text)
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


if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Usage: python hetu_sql_tokenizer.py <sql_text_or_file>")
        sys.exit(1)

    input_text = sys.argv[1]
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    result = tokenize_to_dict(input_text)

    print(f"Tokens: {len(result['tokens'])}")
    print(f"Errors: {len(result['errors'])}")
    print()

    for t in result['tokens']:
        cat = f" [{t['keyword_category']}]" if t['keyword_category'] else ""
        print(f"  L{t['line']:3d}:{t['column']:3d}  {t['type']:12s}  {t['value']!r}{cat}")

    if result['errors']:
        print("\nErrors:")
        for e in result['errors']:
            print(f"  L{e['line']}:{e['column']}  {e['message']}")

    if '--json' in sys.argv:
        print("\n" + json.dumps(result, indent=2, ensure_ascii=False))
