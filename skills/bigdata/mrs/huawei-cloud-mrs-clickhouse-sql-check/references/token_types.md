# ClickHouse 24.8 Lexer Token Types

Source: `ClickHouse_Kernel/src/Parsers/Lexer.h` and `Lexer.cpp`

## Key Design Points

1. **No keyword recognition at lexer level** -- all words are `BareWord`,
   keywords are classified by the parser (case-insensitive, exact-length match)
2. **Multi-character operators are greedy** -- `<=>` > `<=` > `<>` > `<`
3. **Comments nest** -- `/* /* */ */` is valid
4. **Unicode support** -- mathematical minus, Unicode quotes, Unicode whitespace
5. **Context-dependent dot** -- `.` is Dot or start-of-float based on previous token
6. **`\G` (VerticalDelimiter)** -- MySQL compatibility

## TokenType Enum (Complete List)

### Whitespace / Comments
| Token | Description |
|-------|-------------|
| `Whitespace` | Spaces, tabs, newlines (ASCII + Unicode whitespace) |
| `Comment` | Single-line `--` or `#` comments |
| `CommentStart` | `/*` opening |
| `CommentEnd` | `*/` closing |
| `Hint` | `/*+ ... */` optimizer hints |

### Identifiers & Literals
| Token | Description |
|-------|-------------|
| `BareWord` | Unquoted identifier (letters, digits, underscores, `$`) |
| `Number` | Integer / float / hex / binary / scientific notation |
| `StringLiteral` | Single-quoted string (with escape support) |
| `QuotedIdentifier` | Backtick-quoted identifier `` `name` `` |

### Delimiters
| Token | Description |
|-------|-------------|
| `Comma` | `,` |
| `Semicolon` | `;` |
| `Dot` | `.` (context-dependent: qualifier or float start) |
| `Colon` | `:` |
| `DoubleColon` | `::` (type cast) |
| `OpenRoundBracket` | `(` |
| `CloseRoundBracket` | `)` |
| `OpenSquareBracket` | `[` |
| `CloseSquareBracket` | `]` |
| `OpenCurlyBrace` | `{` |
| `CloseCurlyBrace` | `}` |
| `VerticalDelimiter` | `\G` (MySQL vertical output) |

### Operators
| Token | Description |
|-------|-------------|
| `Asterisk` | `*` |
| `Plus` | `+` |
| `Minus` | `-` |
| `Slash` | `/` |
| `Percent` | `%` |
| `Equals` | `=` or `==` (both produce same token) |
| `NotEquals` | `!=` or `<>` |
| `Spaceship` | `<=>` (MySQL NULL-safe equality) |
| `Less` | `<` |
| `Greater` | `>` |
| `LessOrEquals` | `<=` |
| `GreaterOrEquals` | `>=` |
| `Concatenation` | `\|\|` (string concatenation) |
| `PipeMark` | `\|` (single pipe) |
| `Arrow` | `->` (lambda / map access) |
| `At` | `@` |
| `DoubleAt` | `@@` |
| `Caret` | `^` |
| `Question` | `?` |
| `DollarSign` | `$` |
| `AtSign` | `@` |
| `Ellipsis` | `...` |
| `Lambda` | `->` (context-dependent) |

### Special
| Token | Description |
|-------|-------------|
| `HereString` | `$name$...$name$` here-document |
| `Null` | `NULL` literal |
| `True` | `TRUE` literal |
| `False` | `FALSE` literal |
| `EndOfStream` | EOF |

### Error Tokens
| Token | Description |
|-------|-------------|
| `Error` | Generic lexer error (unrecognized character) |
| `ErrorSingleExclamationMark` | Lone `!` not followed by `=` |
| `ErrorSingleQuoteIsNotClosed` | Unclosed `'` string |
| `ErrorDoubleQuoteIsNotClosed` | Unclosed `"` identifier |
| `ErrorBackQuoteIsNotClosed` | Unclosed `` ` `` identifier |
| `ErrorMultilineCommentIsNotClosed` | Unclosed `/*` comment (EOF) |
| `ErrorWrongNumber` | Malformed number (e.g. `123-abc`) |
| `ErrorMaxQuerySizeExceeded` | Token exceeds max_query_size |
| `ErrorSinglePipeMark` | (Exists but not used in lexer) |

## Lexical Rules

### Identifiers (BareWord)
- Characters: `[a-zA-Z0-9_]` plus `$`
- Case-insensitive for keyword matching
- Word boundary required (token size must match keyword length exactly)
- `$` is handled as special case (not part of `isWordCharASCII`)

### Numbers
- Integer: `123`, `0x1F`, `0b1010`
- Float: `1.23`, `.123`, `1.23e-5`
- Underscore separators: `1_000_000` (validated mid-block only)
- After Dot: simple integers only (no `.` or exponent)

### Strings
- Single-quoted: `'text'` with escape support
- Backtick-quoted: `` `identifier` ``
- HereDoc: `$name$...$name$` (forward scan for closing delimiter)

### Comments
- Single-line: `-- ...` or `# ...`
- Multi-line: `/* ... */` (nestable)
- Hints: `/*+ ... */` preserved as `Hint` token

### Character Classification
```
isWordCharASCII(c)    = [a-zA-Z0-9_]
isAlphaNumericASCII(c) = [a-zA-Z0-9]
isAlphaASCII(c)       = [a-zA-Z]
isNumericASCII(c)     = [0-9]
isHexDigit(c)         = [0-9a-fA-F]
isWhitespaceASCII(c)  = ' ' | '\t' | '\n' | '\r' | '\f' | '\v'
```

## Special Token Disambiguation

### Dot (`.`)
- **Qualifier/tuple access** when:
  - Not at start of input, AND
  - Next char is NOT a digit, OR previous token is `ClosingRoundBracket`/`ClosingSquareBracket`/`BareWord`/`QuotedIdentifier`/`Number`
- **Float start** when:
  - At start of input, OR
  - Previous token is NOT one of above, AND next char IS a digit

### Operators (greedy matching order)
| Input | Token | Reason |
|-------|-------|--------|
| `<=>` | `Spaceship` | Checked first |
| `<=` | `LessOrEquals` | After `<=>` |
| `<>` | `NotEquals` | After `<=` |
| `<` | `Less` | Fallback |
| `==` | `Equals` | Same as `=` |
| `!=` | `NotEquals` | `!` must be followed by `=` |
| `\|\|` | `Concatenation` | Checked before `\|` |
| `\|` | `PipeMark` | Fallback |
| `::` | `DoubleColon` | Checked before `:` |
| `->` | `Arrow` | Checked before `--` |
| `--` | `Comment` | After `->` |
| `-` | `Minus` | Fallback |

## Error Conditions

| Condition | Error Token |
|-----------|-------------|
| Lone `!` | `ErrorSingleExclamationMark` |
| Lone `\` or `\` + non-`G` | `Error` |
| `#` not followed by space/`!` | `Error` |
| Unclosed `'` | `ErrorSingleQuoteIsNotClosed` |
| Unclosed `"` | `ErrorDoubleQuoteIsNotClosed` |
| Unclosed `` ` `` | `ErrorBackQuoteIsNotClosed` |
| Unclosed `/*` | `ErrorMultilineCommentIsNotClosed` |
| `123-abc` (malformed number) | `ErrorWrongNumber` |
| Exceeds max_query_size | `ErrorMaxQuerySizeExceeded` |
| Unrecognized char | `Error` |
