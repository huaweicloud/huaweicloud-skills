# -*- coding: utf-8 -*-
"""
ClickHouse 23.3 Lexer Token Types

Source: ClickHouse 23.3 kernel src/Parsers/Lexer.h

This module defines all token types recognized by the ClickHouse 23.3 lexer.
Key characteristics:
- Keywords are NOT recognized at lexer level (all words are BareWord)
- Keyword classification happens at parser level using case-insensitive matching
- Multi-character operators are greedy
- Comments nest (/* /* */ */ is valid)

Differences from 24.8:
- No Spaceship (<=>) token (NULL-safe equality added in 24.8)
- No Caret (^) token
- No Ellipsis (...) token
- No Null/True/False as separate token types (they are BareWord in 23.3)
"""

from enum import Enum, auto


class TokenType(Enum):
    """All token types recognized by ClickHouse 23.3 lexer."""

    # Whitespace and comments
    Whitespace = auto()
    Comment = auto()
    HereDoc = auto()

    # Identifiers and literals
    BareWord = auto()
    Number = auto()
    String = auto()
    QuotedIdentifier = auto()

    # Punctuation
    Semicolon = auto()
    Comma = auto()
    Dot = auto()
    OpenRoundBracket = auto()
    CloseRoundBracket = auto()
    OpenSquareBracket = auto()
    CloseSquareBracket = auto()
    OpenCurlyBrace = auto()
    CloseCurlyBrace = auto()

    # Operators
    Plus = auto()
    Minus = auto()
    Asterisk = auto()
    Slash = auto()
    Percent = auto()

    # Comparison operators
    Equals = auto()  # = or ==
    NotEquals = auto()  # != or <>
    Less = auto()
    Greater = auto()
    LessOrEquals = auto()
    GreaterOrEquals = auto()

    # Other operators
    Concatenation = auto()  # ||
    PipeMark = auto()  # |
    Arrow = auto()  # ->
    DoubleColon = auto()  # ::
    Colon = auto()
    At = auto()  # @
    DoubleAt = auto()  # @@
    QuestionMark = auto()
    DollarSign = auto()
    VerticalDelimiter = auto()  # \G

    # Special (suffixed with 'Keyword' because True/False/Null are Python builtins)
    NullKeyword = auto()
    TrueKeyword = auto()
    FalseKeyword = auto()

    # Error conditions
    Error = auto()
    ErrorSingleQuoteIsNotClosed = auto()
    ErrorDoubleQuoteIsNotClosed = auto()
    ErrorBackQuoteIsNotClosed = auto()
    ErrorMultilineCommentIsNotClosed = auto()
    ErrorSingleExclamationMark = auto()
    ErrorSinglePipeMark = auto()
    ErrorWrongNumber = auto()
    ErrorMaxQuerySizeExceeded = auto()


# Token type categories for validation
PUNCTUATION_TOKENS = {
    TokenType.Semicolon, TokenType.Comma, TokenType.Dot,
    TokenType.OpenRoundBracket, TokenType.CloseRoundBracket,
    TokenType.OpenSquareBracket, TokenType.CloseSquareBracket,
    TokenType.OpenCurlyBrace, TokenType.CloseCurlyBrace,
}

OPERATOR_TOKENS = {
    TokenType.Plus, TokenType.Minus, TokenType.Asterisk,
    TokenType.Slash, TokenType.Percent, TokenType.Equals,
    TokenType.NotEquals, TokenType.Less, TokenType.Greater,
    TokenType.LessOrEquals, TokenType.GreaterOrEquals,
    TokenType.Concatenation, TokenType.PipeMark,
    TokenType.Arrow, TokenType.DoubleColon, TokenType.Colon,
    TokenType.At, TokenType.DoubleAt,
    TokenType.QuestionMark, TokenType.DollarSign,
}

LITERAL_TOKENS = {
    TokenType.Number, TokenType.String, TokenType.QuotedIdentifier,
    TokenType.BareWord,
}

ERROR_TOKENS = {
    TokenType.Error, TokenType.ErrorSingleQuoteIsNotClosed,
    TokenType.ErrorDoubleQuoteIsNotClosed, TokenType.ErrorBackQuoteIsNotClosed,
    TokenType.ErrorMultilineCommentIsNotClosed, TokenType.ErrorSingleExclamationMark,
    TokenType.ErrorSinglePipeMark, TokenType.ErrorWrongNumber,
    TokenType.ErrorMaxQuerySizeExceeded,
}


def is_error_token(token_type: TokenType) -> bool:
    """Return True if token_type is an error token."""
    return token_type in ERROR_TOKENS


def is_operator_token(token_type: TokenType) -> bool:
    """Return True if token_type is an operator token."""
    return token_type in OPERATOR_TOKENS


def is_punctuation_token(token_type: TokenType) -> bool:
    """Return True if token_type is a punctuation token."""
    return token_type in PUNCTUATION_TOKENS


def is_literal_token(token_type: TokenType) -> bool:
    """Return True if token_type is a literal token (number/string/identifier)."""
    return token_type in LITERAL_TOKENS


# Token precedence for multi-character operator disambiguation
OPERATOR_PRECEDENCE = {
    # Longer operators must be checked first
    '<=': TokenType.LessOrEquals,
    '>=': TokenType.GreaterOrEquals,
    '<>': TokenType.NotEquals,
    '!=': TokenType.NotEquals,
    '==': TokenType.Equals,
    '=': TokenType.Equals,
    '<': TokenType.Less,
    '>': TokenType.Greater,
    '||': TokenType.Concatenation,
    '|': TokenType.PipeMark,
    '->': TokenType.Arrow,
    '::': TokenType.DoubleColon,
    ':': TokenType.Colon,
    '@@': TokenType.DoubleAt,
    '@': TokenType.At,
}


if __name__ == "__main__":
    print(f"Total token types: {len(TokenType)}")
    print(f"  Punctuation: {len(PUNCTUATION_TOKENS)}")
    print(f"  Operators: {len(OPERATOR_TOKENS)}")
    print(f"  Literals: {len(LITERAL_TOKENS)}")
    print(f"  Errors: {len(ERROR_TOKENS)}")
