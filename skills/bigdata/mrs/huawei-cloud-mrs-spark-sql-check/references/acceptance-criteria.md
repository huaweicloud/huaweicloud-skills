# Acceptance Criteria

## Functional Requirements

1. **Syntax Check**: The skill must correctly identify syntax errors in Spark SQL statements, including but not limited to:
   - Invalid keywords
   - Reserved keywords used as identifiers
   - Missing required clauses or keywords
   - Incorrect clause ordering
   - Invalid partition/bucket definitions

2. **Specification Check**: The skill must validate SQL against MRS Spark SQL development specifications:
   - Object design standards (comments, column limits, data types)
   - Data operation standards (no SELECT *, WHERE conditions on DML)
   - Naming conventions
   - Performance anti-patterns detection

3. **Report Generation**: The skill must generate a structured Markdown report containing:
   - Summary table with total rules, passed, violations by level
   - Syntax check violations with rule ID, level, position, description, and fix suggestion
   - Specification check violations with the same detail level

## Non-Functional Requirements

1. **No External Dependencies**: Must work with Python standard library only (>= 3.8)
2. **Offline Operation**: No cluster connection required for syntax and specification checks
3. **Security**: No credentials or authentication required; SQL text processed locally
4. **Performance**: Must handle large SQL statements efficiently

## Test Coverage

- All 20 syntax rules (SYN001-SYN020) must have test cases
- All 29 specification rules (SPEC001-SPEC029) must have test cases
- All 7 interception rules (INTERCEPT001-INTERCEPT007) must have test cases
- Edge cases: empty input, malformed SQL, multi-statement input

## Deliverables

- [x] Custom Spark SQL tokenizer (`spark_sql_tokenizer.py`)
- [x] Recursive descent parser (`spark_sql_parser.py`)
- [x] Check engine with rule definitions (`spark_sql_checker.py`)
- [x] Syntax rules (`syntax_rules.yaml`)
- [x] Specification rules (`spec_rules.yaml`)
- [x] Performance rules (`perf_rules.yaml`)
- [x] Keyword definitions (`keywords.py`)
- [x] AST schema documentation (`ast-schema.md`)
- [x] Report template (`report_template.md`)
