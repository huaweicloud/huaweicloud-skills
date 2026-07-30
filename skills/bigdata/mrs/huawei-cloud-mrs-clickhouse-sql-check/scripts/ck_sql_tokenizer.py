# -*- coding: utf-8 -*-
"""
ClickHouse SQL Tokenizer (multi-version)

Source: ClickHouse kernel src/Parsers/Lexer.h, CommonParsers.h

Features:
- Version-specific keywords (24.8: 571, 23.3: 462, case-insensitive)
- Compound keyword recognition (ORDER BY, GROUP BY, CREATE TABLE, etc.)
- ClickHouse-specific tokens: ::, ->, ||, <=>, <>
- Literals: strings, numbers (int/float/hex), identifiers (bare/backtick/quoted)
- Comment handling (-- single line, /* */ multi-line with nesting)
- Error detection (unclosed strings/comments, invalid characters)

Usage:
    python ck_sql_tokenizer.py "<sql_text>" [version]

    version: ClickHouse kernel version (e.g., 24.8, 23.3). Default: 24.8

Output: JSON array of tokens with type, value, line, column.
"""

import sys
import os
import json
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# Fix Windows encoding issues (GBK cannot handle emoji characters)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _this_dir)

from version_loader import load_keywords, DEFAULT_VERSION


# =============================================================================
# Token Types (simplified for tokenizer output)
# =============================================================================
class TokenType:
    WHITESPACE = "Whitespace"
    COMMENT = "Comment"
    BARE_WORD = "BareWord"
    NUMBER = "Number"
    STRING = "String"
    QUOTED_IDENTIFIER = "QuotedIdentifier"
    KEYWORD = "Keyword"

    # Punctuation
    COMMA = "Comma"
    SEMICOLON = "Semicolon"
    DOT = "Dot"
    COLON = "Colon"
    DOUBLE_COLON = "DoubleColon"
    OPEN_ROUND_BRACKET = "OpenRoundBracket"
    CLOSE_ROUND_BRACKET = "CloseRoundBracket"
    OPEN_SQUARE_BRACKET = "OpenSquareBracket"
    CLOSE_SQUARE_BRACKET = "CloseSquareBracket"
    OPEN_CURLY_BRACE = "OpenCurlyBrace"
    CLOSE_CURLY_BRACE = "CloseCurlyBrace"

    # Operators
    PLUS = "Plus"
    MINUS = "Minus"
    ASTERISK = "Asterisk"
    SLASH = "Slash"
    PERCENT = "Percent"
    EQUALS = "Equals"
    NOT_EQUALS = "NotEquals"
    LESS = "Less"
    GREATER = "Greater"
    LESS_OR_EQUALS = "LessOrEquals"
    GREATER_OR_EQUALS = "GreaterOrEquals"
    SPACESHIP = "Spaceship"
    CONCATENATION = "Concatenation"
    PIPE_MARK = "PipeMark"
    ARROW = "Arrow"
    AT = "At"
    DOUBLE_AT = "DoubleAt"
    CARET = "Caret"
    QUESTION = "Question"
    DOLLAR = "Dollar"

    ERROR = "Error"


@dataclass
class Token:
    type: str
    value: str
    line: int = 1
    column: int = 1
    is_keyword: bool = False
    is_reserved: bool = False

    def to_dict(self):
        return {
            "type": self.type,
            "value": self.value,
            "line": self.line,
            "column": self.column,
            "is_keyword": self.is_keyword,
            "is_reserved": self.is_reserved,
        }

    def __repr__(self):
        kw = " [KEYWORD]" if self.is_keyword else ""
        return f"Token({self.type}, {self.value!r}, L{self.line}:C{self.column}{kw})"


# Version-specific keyword sets (initialized by init_version)
_KEYWORDS_UPPER = set()
_RESERVED_UPPER = set()
_COMPOUND_KEYWORDS = []
_CURRENT_VERSION = None


def init_version(version=DEFAULT_VERSION):
    """Initialize tokenizer with the specified ClickHouse version's keywords."""
    global _KEYWORDS_UPPER, _RESERVED_UPPER, _COMPOUND_KEYWORDS, _CURRENT_VERSION
    kw_mod = load_keywords(version)
    _KEYWORDS_UPPER = {k.upper() for k in kw_mod.ALL_KEYWORDS}
    _RESERVED_UPPER = {k.upper() for k in kw_mod.SOFT_RESERVED_KEYWORDS}
    _COMPOUND_KEYWORDS = sorted(
        [kw for kw in kw_mod.ALL_KEYWORDS if ' ' in kw],
        key=lambda x: len(x.split()),
        reverse=True
    )
    _CURRENT_VERSION = version


# Initialize with default version
init_version()


def get_current_version():
    """Return the currently active ClickHouse version."""
    return _CURRENT_VERSION


def tokenize(sql: str) -> Tuple[List[Token], List[str]]:
    """
    Tokenize a ClickHouse SQL string into a list of tokens.

    Returns:
        (tokens, errors) where tokens is a list of Token objects and
        errors is a list of error message strings.
    """
    tokens = []
    errors = []
    pos = 0
    line = 1
    col = 1
    n = len(sql)

    def advance(count=1):
        nonlocal pos, line, col
        for _ in range(count):
            if pos < n and sql[pos] == '\n':
                line += 1
                col = 1
            else:
                col += 1
            pos += 1

    while pos < n:
        # ---- Whitespace ----
        if sql[pos] in ' \t\r\n\f\v':
            advance()
            continue

        # ---- Single-line comment (-- or #) ----
        if sql[pos:pos+2] == '--':
            while pos < n and sql[pos] != '\n':
                advance()
            continue
        if sql[pos] == '#' and (pos + 1 >= n or sql[pos+1] in ' !'):
            while pos < n and sql[pos] != '\n':
                advance()
            continue

        # ---- Multi-line comment (nestable) ----
        if sql[pos:pos+2] == '/*':
            start_line, start_col = line, col
            advance(2)
            depth = 1
            while pos < n and depth > 0:
                if sql[pos:pos+2] == '/*':
                    depth += 1
                    advance(2)
                elif sql[pos:pos+2] == '*/':
                    depth -= 1
                    advance(2)
                else:
                    advance()
            if depth > 0:
                errors.append(f"Line {start_line}, Col {start_col}: Unclosed multi-line comment")
            continue

        # ---- String literal (single-quoted) ----
        if sql[pos] == "'":
            start_line, start_col = line, col
            advance()  # skip opening quote
            value = "'"
            closed = False
            while pos < n:
                if sql[pos] == '\\' and pos + 1 < n:
                    value += sql[pos:pos+2]
                    advance(2)
                elif sql[pos] == "'":
                    value += "'"
                    advance()
                    closed = True
                    break
                elif sql[pos] == "'" and pos > 0 and sql[pos-1] == '\\':
                    value += sql[pos]
                    advance()
                else:
                    value += sql[pos]
                    advance()
            if closed:
                tokens.append(Token(TokenType.STRING, value, start_line, start_col))
            else:
                errors.append(f"Line {start_line}, Col {start_col}: Unclosed string literal")
            continue

        # ---- Backtick-quoted identifier ----
        if sql[pos] == '`':
            start_line, start_col = line, col
            advance()
            value = '`'
            closed = False
            while pos < n:
                if sql[pos] == '`':
                    value += '`'
                    advance()
                    closed = True
                    break
                else:
                    value += sql[pos]
                    advance()
            if closed:
                tokens.append(Token(TokenType.QUOTED_IDENTIFIER, value, start_line, start_col))
            else:
                errors.append(f"Line {start_line}, Col {start_col}: Unclosed backtick identifier")
            continue

        # ---- Double-quoted identifier ----
        if sql[pos] == '"':
            start_line, start_col = line, col
            advance()
            value = '"'
            closed = False
            while pos < n:
                if sql[pos] == '\\' and pos + 1 < n:
                    value += sql[pos:pos+2]
                    advance(2)
                elif sql[pos] == '"':
                    value += '"'
                    advance()
                    closed = True
                    break
                else:
                    value += sql[pos]
                    advance()
            if closed:
                tokens.append(Token(TokenType.QUOTED_IDENTIFIER, value, start_line, start_col))
            else:
                errors.append(f"Line {start_line}, Col {start_col}: Unclosed double-quoted identifier")
            continue

        # ---- Number ----
        if sql[pos].isdigit() or (sql[pos] == '.' and pos + 1 < n and sql[pos+1].isdigit()):
            start_line, start_col = line, col
            value = ''
            # Hex number
            if sql[pos] == '0' and pos + 1 < n and sql[pos+1] in 'xX':
                value = '0' + sql[pos+1]
                advance(2)
                while pos < n and (sql[pos] in '0123456789abcdefABCDEF_'):
                    value += sql[pos]
                    advance()
            else:
                while pos < n and (sql[pos].isdigit() or sql[pos] == '_'):
                    value += sql[pos]
                    advance()
                if pos < n and sql[pos] == '.':
                    value += '.'
                    advance()
                    while pos < n and (sql[pos].isdigit() or sql[pos] == '_'):
                        value += sql[pos]
                        advance()
                if pos < n and sql[pos] in 'eE':
                    value += sql[pos]
                    advance()
                    if pos < n and sql[pos] in '+-':
                        value += sql[pos]
                        advance()
                    while pos < n and sql[pos].isdigit():
                        value += sql[pos]
                        advance()
            tokens.append(Token(TokenType.NUMBER, value, start_line, start_col))
            continue

        # ---- Identifier / Keyword ----
        if sql[pos].isalpha() or sql[pos] == '_' or sql[pos] == '$':
            start_line, start_col = line, col
            value = ''
            while pos < n and (sql[pos].isalnum() or sql[pos] in '_$'):
                value += sql[pos]
                advance()

            upper_val = value.upper()
            is_kw = upper_val in _KEYWORDS_UPPER
            is_res = upper_val in _RESERVED_UPPER

            tokens.append(Token(
                TokenType.BARE_WORD, value, start_line, start_col,
                is_keyword=is_kw, is_reserved=is_res
            ))
            continue

        # ---- Multi-character operators (greedy, longest first) ----
        three_char = sql[pos:pos+3] if pos + 2 < n else ''
        two_char = sql[pos:pos+2] if pos + 1 < n else ''
        start_line, start_col = line, col

        if three_char == '<=>':
            tokens.append(Token(TokenType.SPACESHIP, '<=>', start_line, start_col))
            advance(3); continue
        if two_char == '::':
            tokens.append(Token(TokenType.DOUBLE_COLON, '::', start_line, start_col))
            advance(2); continue
        if two_char == '->':
            tokens.append(Token(TokenType.ARROW, '->', start_line, start_col))
            advance(2); continue
        if two_char == '||':
            tokens.append(Token(TokenType.CONCATENATION, '||', start_line, start_col))
            advance(2); continue
        if two_char == '<=':
            tokens.append(Token(TokenType.LESS_OR_EQUALS, '<=', start_line, start_col))
            advance(2); continue
        if two_char == '>=':
            tokens.append(Token(TokenType.GREATER_OR_EQUALS, '>=', start_line, start_col))
            advance(2); continue
        if two_char == '!=':
            tokens.append(Token(TokenType.NOT_EQUALS, '!=', start_line, start_col))
            advance(2); continue
        if two_char == '<>':
            tokens.append(Token(TokenType.NOT_EQUALS, '<>', start_line, start_col))
            advance(2); continue
        if two_char == '==':
            tokens.append(Token(TokenType.EQUALS, '==', start_line, start_col))
            advance(2); continue
        if two_char == '@@':
            tokens.append(Token(TokenType.DOUBLE_AT, '@@', start_line, start_col))
            advance(2); continue

        # ---- Single-character operators ----
        c = sql[pos]
        single_char_map = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.ASTERISK,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '=': TokenType.EQUALS,
            '<': TokenType.LESS,
            '>': TokenType.GREATER,
            '(': TokenType.OPEN_ROUND_BRACKET,
            ')': TokenType.CLOSE_ROUND_BRACKET,
            '[': TokenType.OPEN_SQUARE_BRACKET,
            ']': TokenType.CLOSE_SQUARE_BRACKET,
            '{': TokenType.OPEN_CURLY_BRACE,
            '}': TokenType.CLOSE_CURLY_BRACE,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ';': TokenType.SEMICOLON,
            ':': TokenType.COLON,
            '@': TokenType.AT,
            '|': TokenType.PIPE_MARK,
            '^': TokenType.CARET,
            '?': TokenType.QUESTION,
            '$': TokenType.DOLLAR,
        }
        if c in single_char_map:
            tokens.append(Token(single_char_map[c], c, start_line, start_col))
            advance(); continue

        # ---- Error ----
        if c == '!':
            errors.append(f"Line {line}, Col {col}: Unexpected '!' (did you mean '!='?)")
            advance(); continue

        errors.append(f"Line {line}, Col {col}: Unexpected character '{c}'")
        tokens.append(Token(TokenType.ERROR, c, start_line, start_col))
        advance()

    return tokens, errors


def merge_compound_keywords(tokens: List[Token]) -> List[Token]:
    """
    Merge adjacent BareWord tokens into compound keywords (ORDER BY, GROUP BY, etc.)
    using greedy longest-match strategy.
    """
    if not tokens:
        return tokens

    result = []
    i = 0
    while i < len(tokens):
        if tokens[i].type == TokenType.BARE_WORD:
            matched = False
            for ck in _COMPOUND_KEYWORDS:
                parts = ck.upper().split()
                if len(parts) <= 1:
                    continue
                if i + len(parts) > len(tokens):
                    continue
                match = True
                for j, part in enumerate(parts):
                    t = tokens[i + j]
                    if t.type != TokenType.BARE_WORD or t.value.upper() != part:
                        match = False
                        break
                if match:
                    combined = ' '.join(tokens[i + j].value for j in range(len(parts)))
                    result.append(Token(
                        TokenType.KEYWORD, combined,
                        tokens[i].line, tokens[i].column,
                        is_keyword=True,
                        is_reserved=(ck in _RESERVED_UPPER)
                    ))
                    i += len(parts)
                    matched = True
                    break
            if not matched:
                if tokens[i].is_keyword:
                    tokens[i].type = TokenType.KEYWORD
                result.append(tokens[i])
                i += 1
        else:
            result.append(tokens[i])
            i += 1

    return result


def tokenize_full(sql: str) -> Tuple[List[Token], List[str]]:
    """Full tokenization: tokenize + merge compound keywords."""
    tokens, errors = tokenize(sql)
    tokens = merge_compound_keywords(tokens)
    return tokens, errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python ck_sql_tokenizer.py "<sql_text>" [version]')
        print(f'  version: ClickHouse kernel version. Supported: {", ".join(get_supported_versions())}')
        print(f'  default: {DEFAULT_VERSION}')
        sys.exit(1)

    sql_text = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VERSION

    from version_loader import get_supported_versions
    if version not in get_supported_versions():
        print(f'Error: unsupported version "{version}". Supported: {", ".join(get_supported_versions())}')
        sys.exit(1)

    init_version(version)
    toks, errs = tokenize_full(sql_text)

    print(json.dumps({
        "version": version,
        "tokens": [t.to_dict() for t in toks],
        "errors": errs,
        "token_count": len(toks),
        "keyword_count": sum(1 for t in toks if t.is_keyword),
    }, indent=2, ensure_ascii=False))
