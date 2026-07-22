# -*- coding: utf-8 -*-
"""
MRS Hive SQL Checker Engine
Integrates tokenizer, parser, and rule-based checking.

Three-stage pipeline:
  1. Syntax Check - keyword validation, structure validation, Hive syntax compatibility
  2. Specification Check - naming conventions, DML/DDL best practices, Hive-specific rules
  3. Large SQL Interception - high-risk SQL that may exhaust cluster resources
"""

import sys
import os
import json
import re
from datetime import datetime

_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_this_dir, '..', 'rules'))
sys.path.insert(0, _this_dir)

from hive_sql_tokenizer import tokenize, TokenType
from hive_sql_parser import parse_sql
from keywords import is_keyword, is_reserved_keyword, KeywordCategory


class Violation:
    """Represents a rule violation"""

    def __init__(self, rule_id, rule_name, level, category, message,
                 line=0, column=0, sql_snippet="", fix_suggestion=""):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.level = level  # ERROR, WARNING, INFO
        self.category = category
        self.message = message
        self.line = line
        self.column = column
        self.sql_snippet = sql_snippet
        self.fix_suggestion = fix_suggestion

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "sql_snippet": self.sql_snippet,
            "fix_suggestion": self.fix_suggestion,
        }


class HiveSQLChecker:
    """
    MRS Hive SQL Check Engine

    Performs syntax, specification, and interception checks on Hive SQL statements.
    """

    # Hive-specific storage formats (ORCFILE is a legacy alias for ORC;
    # CUSTOMTEXTSERDE is a built-in alias for MetadataTypedColumnsetSerDe)
    VALID_STORED_AS = {
        "ORC", "ORCFILE", "TEXTFILE", "PARQUET", "SEQUENCEFILE", "AVRO", "RCFILE",
        "INPUTFORMAT", "ORG.APACHE.HADOOP.HIVE.QL.IO.ORC.ORCINPUTFORMAT",
        "CUSTOMTEXTSERDE",
    }

    # Hive data types
    NUMERIC_TYPES = {
        "TINYINT", "SMALLINT", "INT", "INTEGER", "BIGINT",
        "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC",
    }
    DATE_TYPES = {"DATE", "TIMESTAMP", "INTERVAL"}
    STRING_TYPES = {"STRING", "VARCHAR", "CHAR", "NVARCHAR", "NCHAR"}

    def __init__(self, sql_text, check_mode="all", partitioned_tables=None, partition_fields=None):
        self.sql_text = sql_text.strip()
        self.check_mode = check_mode  # syntax, spec, intercept, all
        self.violations = []
        self.parse_result = None
        self.tokens = []
        # Infer partitioned tables from the SQL text itself,
        # or use externally provided set (for multi-statement context)
        if partitioned_tables is not None:
            self._partitioned_tables = partitioned_tables
        else:
            self._partitioned_tables = self._infer_partitioned_tables()
        # Infer partition field names from the SQL text itself,
        # or use externally provided set (for multi-statement context)
        if partition_fields is not None:
            self._partition_fields = partition_fields
        else:
            self._partition_fields = self._infer_partition_fields()

    def check(self):
        """Run all checks and return the report"""
        # Step 1: Tokenize
        self.tokens, token_errors = tokenize(self.sql_text)

        # Step 2: Parse
        self.parse_result = parse_sql(self.sql_text)

        # Step 3: Run checks based on mode
        if self.check_mode in ("syntax", "all"):
            self._check_syntax(self.tokens, token_errors)

        if self.check_mode in ("spec", "all"):
            self._check_specification(self.tokens)

        if self.check_mode in ("intercept", "spec", "all"):
            self._check_interception(self.tokens)

        # Step 4: Generate report
        return self._generate_report()

    # ============================================================
    # Syntax Checks (SYN-ERR, SYN001-SYN013)
    # ============================================================

    def _check_syntax(self, tokens, token_errors):
        """Run syntax-level checks"""

        # SYN-ERR: Tokenizer errors
        for err in token_errors:
            self.violations.append(Violation(
                rule_id="SYN-ERR",
                rule_name="词法错误",
                level="ERROR",
                category="语法检查",
                message=str(err),
                line=err.line,
                column=err.column,
                sql_snippet=self._get_snippet(err.line, err.column),
                fix_suggestion="检查 SQL 文本中是否存在非法字符、未闭合的引号或注释",
            ))

        # SYN002: Reserved keyword used as identifier (without backticks)
        for t in tokens:
            if t.type == TokenType.IDENT:
                if is_reserved_keyword(t.value):
                    self.violations.append(Violation(
                        rule_id="SYN002",
                        rule_name="保留关键字用作标识符",
                        level="ERROR",
                        category="语法检查",
                        message=f"保留关键字 '{t.value}' 不能用作标识符，请使用反引号引用",
                        line=t.line,
                        column=t.column,
                        sql_snippet=self._get_snippet(t.line, t.column),
                        fix_suggestion=f"使用 `{t.value}` 替代 {t.value}，或更换标识符名称",
                    ))

        # SYN002: Reserved keyword used after AS (alias position)
        # Excludes legal Hive syntax: STORED AS <format>, CAST AS <type>, CREATE VIEW/TABLE AS SELECT, WITH ... AS (CTE), etc.
        for i, t in enumerate(tokens):
            if t.is_keyword("AS") and i + 1 < len(tokens):
                next_t = tokens[i + 1]
                if next_t.type == TokenType.KEYWORD and next_t.is_reserved() and \
                   next_t.value.upper() not in ("ALL", "DISTINCT"):
                    # Skip STORED AS <format> (legal Hive storage format syntax)
                    prev_t = tokens[i - 1] if i > 0 else None
                    if prev_t and prev_t.is_keyword("STORED"):
                        continue
                    # Skip CAST AS <type> (legal Hive type conversion syntax)
                    # Scan backwards to find CAST keyword (CAST may be several tokens before AS,
                    # e.g. CAST('hello' AS BINARY) where AS is preceded by SCONST, not CAST)
                    found_cast = False
                    for j in range(i - 1, max(-1, i - 10), -1):
                        if tokens[j].is_keyword("CAST"):
                            found_cast = True
                            break
                        # Stop scanning if we hit a statement-level keyword or unmatched RPAREN
                        if tokens[j].is_keyword("SELECT") or tokens[j].is_keyword("FROM") or tokens[j].is_keyword("WHERE"):
                            break
                    if found_cast:
                        continue
                    # Skip AS WITH ... AS (...) (legal CTAS + CTE syntax)
                    # Pattern: CREATE TABLE ... AS WITH <name> AS (...) SELECT
                    # Here WITH follows AS and starts the CTE clause, not an alias
                    if next_t.is_keyword("WITH"):
                        continue
                    # Skip WITH ... AS (CTE - Common Table Expression syntax)
                    # Pattern: WITH <name> AS or WITH <name> AS (...), <name> AS
                    # Scan backwards through IDENT/COMMA tokens to find WITH
                    if i >= 2:
                        found_with_cte = False
                        for j in range(i - 1, max(-1, i - 20), -1):
                            if tokens[j].is_keyword("WITH"):
                                found_with_cte = True
                                break
                            # Allow IDENT (CTE name) and COMMA (between CTEs)
                            if tokens[j].type == TokenType.IDENT or tokens[j].value == ",":
                                continue
                            break
                        if found_with_cte:
                            continue
                    # Skip CREATE VIEW/TABLE AS SELECT (legal CTAS syntax)
                    # Scan backwards to find CREATE VIEW or CREATE TABLE pattern
                    if next_t.is_keyword("SELECT"):
                        found_ctas = False
                        # Look back up to 10 tokens for CREATE VIEW/TABLE
                        for j in range(i - 1, max(-1, i - 11), -1):
                            if tokens[j].is_keyword("CREATE"):
                                # Check if next token after CREATE is VIEW or TABLE
                                if j + 1 < len(tokens) and \
                                   (tokens[j + 1].is_keyword("VIEW") or tokens[j + 1].is_keyword("TABLE")):
                                    found_ctas = True
                                break
                        if found_ctas:
                            continue
                    # Skip <type> AS in CAST expressions (e.g., CAST(col AS INT))
                    # and other type-conversion contexts
                    if next_t.value.upper() in self.NUMERIC_TYPES or \
                       next_t.value.upper() in self.DATE_TYPES or \
                       next_t.value.upper() in self.STRING_TYPES:
                        continue
                    self.violations.append(Violation(
                        rule_id="SYN002",
                        rule_name="保留关键字用作标识符",
                        level="ERROR",
                        category="语法检查",
                        message=f"保留关键字 '{next_t.value}' 用作别名，请使用反引号引用",
                        line=next_t.line,
                        column=next_t.column,
                        sql_snippet=self._get_snippet(next_t.line, next_t.column),
                        fix_suggestion=f"使用 `{next_t.value}` 替代 {next_t.value}，或更换别名",
                    ))

        # SYN003: Parse errors
        for err in self.parse_result.get("errors", []):
            self.violations.append(Violation(
                rule_id="SYN003",
                rule_name="语法结构错误",
                level="ERROR",
                category="语法检查",
                message=err["message"],
                line=err.get("line", 0),
                column=err.get("column", 0),
                sql_snippet=self._get_snippet(err.get("line", 0), err.get("column", 0)),
                fix_suggestion="检查 SQL 语句的语法结构是否正确",
            ))

        ast = self.parse_result.get("ast", {})

        # SYN005: PARTITIONED BY syntax check
        if ast and ast.get("node_type") == "CreateStmt":
            part_by = ast.get("partitioned_by")
            if part_by is not None:
                # Parser may return partitioned_by as string or dict
                if isinstance(part_by, str):
                    # Check if the string is effectively empty
                    stripped = part_by.strip("() \t\n")
                    if not stripped:
                        self.violations.append(Violation(
                            rule_id="SYN005",
                            rule_name="PARTITIONED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="PARTITIONED BY 定义为空或语法无效",
                            fix_suggestion="添加分区字段定义，如 PARTITIONED BY (dt STRING)",
                        ))
                elif isinstance(part_by, dict):
                    if not part_by.get("columns"):
                        self.violations.append(Violation(
                            rule_id="SYN005",
                            rule_name="PARTITIONED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="PARTITIONED BY 定义为空或语法无效",
                            fix_suggestion="添加分区字段定义，如 PARTITIONED BY (dt STRING)",
                        ))

        # SYN006: CLUSTERED BY syntax check
        if ast and ast.get("node_type") == "CreateStmt":
            clustered = ast.get("clustered_by")
            if clustered:
                # Parser may return clustered_by as string or dict
                if isinstance(clustered, str):
                    stripped = clustered.strip("() \t\n")
                    if not stripped:
                        self.violations.append(Violation(
                            rule_id="SYN006",
                            rule_name="CLUSTERED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="CLUSTERED BY 缺少分桶字段定义",
                            fix_suggestion="添加分桶字段，如 CLUSTERED BY (user_id) INTO 10 BUCKETS",
                        ))
                elif isinstance(clustered, dict):
                    if not clustered.get("columns"):
                        self.violations.append(Violation(
                            rule_id="SYN006",
                            rule_name="CLUSTERED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="CLUSTERED BY 缺少分桶字段定义",
                            fix_suggestion="添加分桶字段，如 CLUSTERED BY (user_id) INTO 10 BUCKETS",
                        ))
                    if not clustered.get("num_buckets"):
                        self.violations.append(Violation(
                            rule_id="SYN006",
                            rule_name="CLUSTERED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="CLUSTERED BY 缺少 INTO N BUCKETS 定义",
                            fix_suggestion="添加分桶数量，如 CLUSTERED BY (col) INTO 10 BUCKETS",
                        ))
            # Check num_buckets separately - covers both string and dict formats
            if clustered and not ast.get("num_buckets"):
                if isinstance(clustered, dict) and not clustered.get("num_buckets"):
                    self.violations.append(Violation(
                        rule_id="SYN006",
                        rule_name="CLUSTERED BY 语法错误",
                        level="ERROR",
                        category="语法检查",
                        message="CLUSTERED BY 缺少 INTO N BUCKETS 定义",
                        fix_suggestion="添加分桶数量，如 CLUSTERED BY (col) INTO 10 BUCKETS",
                    ))
                elif isinstance(clustered, str) and clustered.strip("() \t\n"):
                    # String format clustered_by present but no num_buckets
                    self.violations.append(Violation(
                        rule_id="SYN006",
                        rule_name="CLUSTERED BY 语法错误",
                        level="ERROR",
                        category="语法检查",
                        message="CLUSTERED BY 缺少 INTO N BUCKETS 定义",
                        fix_suggestion="添加分桶数量，如 CLUSTERED BY (col) INTO 10 BUCKETS",
                    ))

        # SYN007: STORED AS syntax check
        if ast and ast.get("node_type") == "CreateStmt":
            stored_as = ast.get("stored_as")
            if stored_as:
                fmt = stored_as.upper().strip("'\"")
                if fmt and fmt not in self.VALID_STORED_AS and not stored_as.upper().startswith("INPUTFORMAT"):
                    self.violations.append(Violation(
                        rule_id="SYN007",
                        rule_name="STORED AS 语法错误",
                        level="ERROR",
                        category="语法检查",
                        message=f"无效的存储格式 '{stored_as}'",
                        fix_suggestion="使用 ORC/TEXTFILE/PARQUET/SEQUENCEFILE/AVRO/RCFILE 或自定义 INPUTFORMAT/OUTPUTFORMAT",
                    ))

        # SYN009: INSERT OVERWRITE syntax check
        if ast and ast.get("node_type") == "InsertStmt":
            if ast.get("is_overwrite"):
                table_name = ast.get("table_name") or ast.get("table")
                if not table_name:
                    self.violations.append(Violation(
                        rule_id="SYN009",
                        rule_name="INSERT OVERWRITE 语法错误",
                        level="ERROR",
                        category="语法检查",
                        message="INSERT OVERWRITE 缺少目标表名",
                        fix_suggestion="添加 TABLE 关键字和表名，如 INSERT OVERWRITE TABLE t1",
                    ))
                else:
                    # Check if TABLE keyword is missing after INSERT OVERWRITE
                    # Token pattern: INSERT OVERWRITE <IDENT> SELECT -> missing TABLE
                    has_table_kw = False
                    for i, t in enumerate(tokens):
                        if t.is_keyword("OVERWRITE"):
                            for j in range(i + 1, min(i + 3, len(tokens))):
                                if tokens[j].is_keyword("TABLE"):
                                    has_table_kw = True
                                    break
                            break
                    if not has_table_kw:
                        self.violations.append(Violation(
                            rule_id="SYN009",
                            rule_name="INSERT OVERWRITE 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="INSERT OVERWRITE 缺少 TABLE 关键字，Hive 不支持省略 TABLE",
                            fix_suggestion="使用 INSERT OVERWRITE TABLE t1 而非 INSERT OVERWRITE t1",
                        ))

        # SYN010: LATERAL VIEW syntax check
        if self._has_lateral_view(tokens):
            if not self._validate_lateral_view(tokens):
                self.violations.append(Violation(
                    rule_id="SYN010",
                    rule_name="LATERAL VIEW 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message="LATERAL VIEW 语法结构不正确",
                    fix_suggestion="正确格式: LATERAL VIEW explode(array_col) table_alias AS col_alias",
                ))

        # SYN012: CREATE TABLE structure check
        # Tables with external schema definitions are valid:
        # - Avro tables define columns via TBLPROPERTIES ('avro.schema.literal'/'avro.schema.url')
        # - SerDe tables define columns via ROW FORMAT SERDE (e.g., Thrift)
        # - Storage Handler tables define columns via STORED BY
        if ast and ast.get("node_type") == "CreateStmt":
            if not ast.get("columns") and not ast.get("as_select") and \
               not ast.get("like_table") and not ast.get("tblproperties") and \
               not ast.get("row_format") and not ast.get("stored_by"):
                self.violations.append(Violation(
                    rule_id="SYN012",
                    rule_name="CREATE TABLE 结构错误",
                    level="ERROR",
                    category="语法检查",
                    message="CREATE TABLE 缺少列定义或 AS SELECT 子句",
                    fix_suggestion="添加列定义或使用 CREATE TABLE ... AS SELECT 语法，"
                                   "或通过 TBLPROPERTIES/ROW FORMAT SERDE/STORED BY 定义外部 schema",
                ))

        # SYN003: Column definition order check (type before name)
        if ast and ast.get("node_type") == "CreateStmt":
            # Check column definitions
            columns_raw = ast.get("columns", "")
            if isinstance(columns_raw, str) and columns_raw.strip():
                for err_msg in self._check_col_def_order(columns_raw, "列定义"):
                    self.violations.append(Violation(
                        rule_id="SYN003",
                        rule_name="语法结构错误",
                        level="ERROR",
                        category="语法检查",
                        message=err_msg,
                        fix_suggestion="列定义顺序应为: 列名 类型，例如 s INT 而非 INT s",
                    ))
            # Check partitioned_by definitions
            part_raw = ast.get("partitioned_by", "")
            if isinstance(part_raw, str) and part_raw.strip():
                for err_msg in self._check_col_def_order(part_raw, "分区字段定义"):
                    self.violations.append(Violation(
                        rule_id="SYN003",
                        rule_name="语法结构错误",
                        level="ERROR",
                        category="语法检查",
                        message=err_msg,
                        fix_suggestion="分区字段定义顺序应为: 列名 类型，例如 dt STRING 而非 STRING dt",
                    ))

        # SYN013: ALTER TABLE syntax check
        if ast and ast.get("node_type") == "AlterStmt":
            action = ast.get("action", "").upper()
            valid_actions = {
                "ADD", "DROP", "RENAME", "MODIFY", "CHANGE",
                "SET", "UNSET", "ARCHIVE", "UNARCHIVE",
                "TOUCH", "COMPACT", "CONCATENATE",
            }
            if action and action not in valid_actions:
                self.violations.append(Violation(
                    rule_id="SYN013",
                    rule_name="ALTER TABLE 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"无效的 ALTER TABLE 操作 '{action}'",
                    fix_suggestion="支持的操作: ADD/DROP/RENAME/MODIFY/CHANGE/SET/UNSET 等",
                ))

        # SYN014: MERGE statement syntax check
        stmt_type = self.parse_result.get("statement_type", "")
        if stmt_type == "MERGE":
            required = ["MERGE", "INTO", "USING", "ON", "WHEN", "MATCHED"]
            token_upper = [t.value.upper() for t in tokens if t.type == TokenType.KEYWORD]
            missing = [kw for kw in required if kw not in token_upper]
            if missing:
                self.violations.append(Violation(
                    rule_id="SYN014",
                    rule_name="MERGE 语句语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"MERGE 语句缺少必选关键字: {', '.join(missing)}",
                    fix_suggestion="使用 MERGE INTO target USING source ON condition WHEN MATCHED THEN UPDATE/DELETE",
                ))

        # SYN015: LOAD DATA syntax check
        if stmt_type == "LOAD":
            required = ["LOAD", "DATA", "INPATH", "INTO", "TABLE"]
            token_upper = [t.value.upper() for t in tokens if t.type == TokenType.KEYWORD]
            missing = [kw for kw in required if kw not in token_upper]
            if missing:
                self.violations.append(Violation(
                    rule_id="SYN015",
                    rule_name="LOAD DATA 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"LOAD DATA 语句缺少必选关键字: {', '.join(missing)}",
                    fix_suggestion="使用 LOAD DATA [LOCAL] INPATH 'path' [OVERWRITE] INTO TABLE table_name",
                ))

        # SYN003: UNION ALL with LIMIT before UNION (Hive does not support)
        # Pattern: ... LIMIT N UNION ALL ... - Hive requires subquery wrapping
        # But LIMIT inside a subquery before UNION is OK: (SELECT ... LIMIT N) UNION ALL ...
        for i, t in enumerate(tokens):
            if t.is_keyword("LIMIT"):
                # Check if UNION appears after this LIMIT (before next clause boundary)
                for j in range(i + 1, min(i + 10, len(tokens))):
                    # If we hit RPAREN before UNION, the LIMIT is inside a subquery - OK
                    if tokens[j].type == TokenType.RPAREN:
                        break
                    if tokens[j].is_keyword("UNION"):
                        self.violations.append(Violation(
                            rule_id="SYN003",
                            rule_name="语法结构错误",
                            level="ERROR",
                            category="语法检查",
                            message="LIMIT 不能直接出现在 UNION ALL 之前，需使用子查询包裹",
                            line=t.line,
                            column=t.column,
                            sql_snippet=self._get_snippet(t.line, t.column),
                            fix_suggestion="使用 (SELECT ... LIMIT N) UNION ALL (SELECT ... LIMIT M) 子查询形式",
                        ))
                        break
                    # Stop at clause boundary keywords
                    if tokens[j].is_keyword("SELECT") or tokens[j].is_keyword("FROM") or \
                       tokens[j].is_keyword("WHERE") or tokens[j].is_keyword("GROUP") or \
                       tokens[j].is_keyword("ORDER") or tokens[j].is_keyword("HAVING"):
                        break

        # SYN003: CREATE INDEX not supported in Hive
        # Hive does not support CREATE INDEX syntax
        if len(tokens) >= 2 and tokens[0].is_keyword("CREATE") and tokens[1].is_keyword("INDEX"):
            self.violations.append(Violation(
                rule_id="SYN003",
                rule_name="语法结构错误",
                level="ERROR",
                category="语法检查",
                message="Hive 不支持 CREATE INDEX 语法",
                line=tokens[0].line,
                column=tokens[0].column,
                sql_snippet=self._get_snippet(tokens[0].line, tokens[0].column),
                fix_suggestion="Hive 不支持索引，考虑优化查询或使用物化视图",
            ))


    # ============================================================
    # Specification Checks (SPEC001-SPEC025)
    # ============================================================

    def _check_specification(self, tokens):
        """Run specification-level checks"""

        ast = self.parse_result.get("ast", {})
        stmt_type = self.parse_result.get("statement_type", "")

        # ---- Object Design Rules ----

        # SPEC008: Missing table comment
        if ast and ast.get("node_type") == "CreateStmt":
            if not ast.get("comment"):
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC008",
                    rule_name="CREATE TABLE 缺少表注释",
                    level="INFO",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 未添加注释",
                    fix_suggestion="添加 COMMENT '表用途说明'",
                ))

        # SPEC009: Reserved keyword as identifier
        if ast and ast.get("node_type") == "CreateStmt":
            # Check table name
            table_name = ast.get("table_name", "")
            if table_name and is_reserved_keyword(table_name):
                self.violations.append(Violation(
                    rule_id="SPEC009",
                    rule_name="保留关键字用作标识符",
                    level="ERROR",
                    category="命名规范",
                    message=f"表名 '{table_name}' 是 Hive 保留关键字，可能导致语法歧义",
                    fix_suggestion=f"使用 `{table_name}` 反引号引用或更换表名",
                ))
            # Check column names
            col_names = self._get_column_names(ast)
            for col_name in col_names:
                if col_name and is_reserved_keyword(col_name):
                    self.violations.append(Violation(
                        rule_id="SPEC009",
                        rule_name="保留关键字用作标识符",
                        level="ERROR",
                        category="命名规范",
                        message=f"字段名 '{col_name}' 是 Hive 保留关键字，可能导致语法歧义",
                        fix_suggestion=f"使用 `{col_name}` 反引号引用或更换字段名",
                    ))
                    break

        # SPEC010: Column name too long
        if ast and ast.get("node_type") == "CreateStmt":
            col_names = self._get_column_names(ast)
            for col_name in col_names:
                if col_name and len(col_name) > 30:
                    self.violations.append(Violation(
                        rule_id="SPEC010",
                        rule_name="字段名过长",
                        level="WARNING",
                        category="命名规范",
                        message=f"字段名 '{col_name}' 超过30个字符（当前{len(col_name)}个字符）",
                        fix_suggestion="字段名不超过30个字符（华为规范）",
                    ))
                    break

        # SPEC012: FLOAT/DOUBLE for money
        if ast and ast.get("node_type") == "CreateStmt":
            col_defs = self._get_column_defs(ast)
            for col_name, col_type in col_defs:
                money_hints = ("amount", "price", "fee", "salary", "money",
                               "cost", "pay", "income", "revenue")
                if col_type in ("FLOAT", "DOUBLE") and \
                   any(h in col_name.lower() for h in money_hints):
                    self.violations.append(Violation(
                        rule_id="SPEC012",
                        rule_name="金额字段使用 FLOAT/DOUBLE",
                        level="ERROR",
                        category="对象设计规范",
                        message=f"金额字段 '{col_name}' 使用 {col_type} 类型，存在精度丢失风险",
                        fix_suggestion="使用 DECIMAL(p,s) 类型存储金额",
                    ))
                    break

        # SPEC013: Too many columns
        if ast and ast.get("node_type") == "CreateStmt":
            col_count = self._count_create_table_columns()
            if col_count > 100:
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC013",
                    rule_name="字段数量过多",
                    level="WARNING",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 有 {col_count} 个字段，超过100个字段可能导致 ORC 压缩 OOM",
                    fix_suggestion="Hive 每个表字段个数不建议超过100个（华为规范）",
                ))

        # SPEC014: Too many partition fields
        if ast and ast.get("node_type") == "CreateStmt":
            part_count = ast.get("partition_count", 0)
            if isinstance(part_count, int) and part_count > 3:
                self.violations.append(Violation(
                    rule_id="SPEC014",
                    rule_name="分区字段过多",
                    level="WARNING",
                    category="对象设计规范",
                    message=f"分区字段有 {part_count} 个，超过3个会导致大量小文件",
                    fix_suggestion="Hive 建表分区字段不超过3个（华为规范）",
                ))

        # SPEC015: Missing column comment
        if ast and ast.get("node_type") == "CreateStmt":
            col_count = self._count_create_table_columns()
            comment_count = self._count_column_comments()
            if comment_count < col_count:
                cols_without_comment = col_count - comment_count
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC015",
                    rule_name="字段缺少注释",
                    level="INFO",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 有 {cols_without_comment} 个字段缺少注释",
                    fix_suggestion="所有字段都应根据字段的作用添加注释（华为规范）",
                ))

        # ---- Data Operation Rules ----

        # SPEC001: SELECT * prohibited
        if ast and ast.get("node_type") == "SelectStmt":
            if ast.get("has_select_star"):
                self.violations.append(Violation(
                    rule_id="SPEC001",
                    rule_name="禁止使用 SELECT *",
                    level="WARNING",
                    category="数据操作规范",
                    message="查询使用了 SELECT *，应明确指定字段列表",
                    fix_suggestion="将 SELECT * 替换为具体的字段列表",
                ))

        # SPEC002: DELETE/UPDATE without WHERE
        if ast and ast.get("node_type") in ("DeleteStmt", "UpdateStmt"):
            if ast.get("missing_where"):
                stmt_kw = "DELETE" if ast.get("node_type") == "DeleteStmt" else "UPDATE"
                table_name = ast.get("table", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC002",
                    rule_name=f"{stmt_kw} 缺少 WHERE 条件",
                    level="ERROR",
                    category="数据操作规范",
                    message=f"{stmt_kw} 语句缺少 WHERE 条件，将影响全表数据",
                    fix_suggestion=f"添加 WHERE 条件限制 {stmt_kw} 操作范围",
                ))

        # SPEC003: Cartesian product / Old-style join / JOIN without ON
        if ast and ast.get("node_type") == "SelectStmt":
            cartesian_result = self._has_cartesian_product(tokens)
            join_no_on_result = self._has_join_without_on(tokens)
            if cartesian_result == "cartesian":
                self.violations.append(Violation(
                    rule_id="SPEC003",
                    rule_name="笛卡尔积",
                    level="ERROR",
                    category="数据操作规范",
                    message="多表查询缺少 JOIN 条件，将产生笛卡尔积",
                    fix_suggestion="使用显式 JOIN 语法并指定 ON 条件（华为规范：笛卡尔积只有1个reduce，可能导致节点挂掉）",
                ))
            elif cartesian_result == "old_style_join":
                self.violations.append(Violation(
                    rule_id="SPEC003",
                    rule_name="旧式逗号JOIN",
                    level="ERROR",
                    category="数据操作规范",
                    message="使用旧式逗号JOIN（FROM t1, t2 WHERE ...），CBO=false时Hive可能无法识别连接条件导致笛卡尔积",
                    fix_suggestion="改为标准JOIN语法：FROM t1 JOIN t2 ON t1.col = t2.col，确保Hive能正确识别join key",
                ))
            if join_no_on_result:
                for join_info in join_no_on_result:
                    self.violations.append(Violation(
                        rule_id="SPEC003",
                        rule_name="JOIN缺少ON条件",
                        level="ERROR",
                        category="数据操作规范",
                        message=f"{join_info['join_type']} JOIN 缺少 ON 条件，将产生笛卡尔积",
                        fix_suggestion=f"为 {join_info['join_type']} JOIN 添加 ON 条件（华为规范：笛卡尔积只有1个reduce，可能导致节点挂掉）",
                    ))

        # SPEC004: Implicit type conversion risk
        if self._has_implicit_type_risk(tokens):
            self.violations.append(Violation(
                rule_id="SPEC004",
                rule_name="隐式类型转换风险",
                level="WARNING",
                category="数据操作规范",
                message="WHERE 条件中可能存在隐式类型转换，导致分区裁剪失效或结果异常",
                fix_suggestion="确保比较操作两侧的数据类型一致，使用显式类型转换",
            ))

        # SPEC005: LIKE with leading wildcard
        if self._has_leading_wildcard_like(tokens):
            self.violations.append(Violation(
                rule_id="SPEC005",
                rule_name="LIKE 前缀通配符",
                level="WARNING",
                category="数据操作规范",
                message="LIKE '%...' 模式无法使用分区裁剪，将导致全表扫描",
                fix_suggestion="避免使用前缀通配符",
            ))

        # SPEC006: Partition field function
        if self._has_partition_field_function(tokens):
            self.violations.append(Violation(
                rule_id="SPEC006",
                rule_name="分区字段使用函数",
                level="WARNING",
                category="数据操作规范",
                message="WHERE 条件中对分区字段使用函数，导致无法使用分区裁剪",
                fix_suggestion="使用范围条件替代函数，如 WHERE dt >= '20240501' AND dt < '20240601'",
            ))

        # SPEC007: INSERT missing column list
        if ast and ast.get("node_type") == "InsertStmt":
            has_columns = ast.get("columns")
            # Parser may store table as "t1 ( col1, col2 )" with columns embedded
            if not has_columns:
                table_val = ast.get("table", "")
                if isinstance(table_val, str) and "(" in table_val:
                    has_columns = True
            if not has_columns and not ast.get("is_overwrite"):
                self.violations.append(Violation(
                    rule_id="SPEC007",
                    rule_name="INSERT 缺少列列表",
                    level="WARNING",
                    category="数据操作规范",
                    message="INSERT 语句未指定列列表，依赖列的默认顺序",
                    fix_suggestion="添加列列表 INSERT INTO table (col1, col2, ...) SELECT ...",
                ))

        # SPEC016: CASE WHEN missing ELSE
        if self._has_case_without_else(tokens):
            self.violations.append(Violation(
                rule_id="SPEC016",
                rule_name="CASE WHEN 缺少 ELSE",
                level="WARNING",
                category="数据操作规范",
                message="CASE WHEN 语句未包含 ELSE 子句，可能导致 NULL 值",
                fix_suggestion="CASE WHEN 必须加 ELSE（华为规范）",
            ))

        # SPEC017: NULL value handling
        for risk in self._check_null_handling_risk(tokens):
            self.violations.append(Violation(
                rule_id="SPEC017",
                rule_name="NULL 值处理风险",
                level="WARNING",
                category="数据操作规范",
                message=risk["message"],
                line=risk["line"],
                column=risk["column"],
                sql_snippet=risk["snippet"],
                fix_suggestion="显式处理 NULL 逻辑，使用 IS NOT NULL 或 COALESCE",
            ))

        # SPEC018: String 'null' prohibited
        if self._has_string_null(tokens):
            self.violations.append(Violation(
                rule_id="SPEC018",
                rule_name="禁止使用字符串 'null'",
                level="ERROR",
                category="数据操作规范",
                message="数据处理中使用了字符串 'NULL'/'null'，可能导致误解",
                fix_suggestion="使用 NULL 关键字替代字符串 'NULL'（华为规范）",
            ))

        # SPEC019: JOIN field type mismatch
        if self._has_join_type_mismatch(tokens):
            self.violations.append(Violation(
                rule_id="SPEC019",
                rule_name="关联字段类型不一致",
                level="WARNING",
                category="数据操作规范",
                message="JOIN 关联字段类型可能不一致，导致隐式转换",
                fix_suggestion="确保关联字段类型一致，使用显式类型转换（华为规范）",
            ))

        # ---- SQL Development Rules ----

        # SPEC020: INSERT INTO VALUES
        if self._has_insert_values(tokens):
            self.violations.append(Violation(
                rule_id="SPEC020",
                rule_name="避免 INSERT INTO VALUES",
                level="WARNING",
                category="SQL开发规范",
                message="INSERT INTO VALUES 效率低，建议使用 LOAD DATA 或 INSERT SELECT",
                fix_suggestion="使用 LOAD DATA 或 INSERT INTO ... SELECT 替代（华为规范）",
            ))

        # SPEC021: Subquery nesting depth
        if self._get_subquery_depth(tokens) > 3:
            self.violations.append(Violation(
                rule_id="SPEC021",
                rule_name="子查询嵌套过深",
                level="WARNING",
                category="SQL开发规范",
                message="子查询嵌套超过3层，建议拆分为中间表",
                fix_suggestion="子查询不超过3层，拆分为多层中间表（华为规范）",
            ))

        # SPEC022: Partition pruning missing
        if self._has_partition_table_without_filter(tokens):
                self.violations.append(Violation(
                    rule_id="SPEC022",
                    rule_name="缺少分区裁剪",
                    level="ERROR",
                    category="数据操作规范",
                    message="分区表查询未使用分区过滤条件，将导致全分区扫描",
                    fix_suggestion="添加分区过滤条件，如 WHERE dt='20240501'（华为规范）",
                ))

        # SPEC023: Non-standard join condition
        if self._has_non_standard_join_condition(tokens):
            self.violations.append(Violation(
                rule_id="SPEC023",
                rule_name="非标准关联条件",
                level="WARNING",
                category="数据操作规范",
                message="JOIN ON 条件中包含 IF/CASE WHEN，可能影响执行计划",
                fix_suggestion="将 IF/CASE WHEN 逻辑移到 WHERE 子句中",
            ))

        # SPEC024: CASCADE usage warning
        if self._has_cascade_usage(tokens):
            self.violations.append(Violation(
                rule_id="SPEC024",
                rule_name="CASCADE 使用警告",
                level="WARNING",
                category="SQL开发规范",
                message="ALTER TABLE 使用 CASCADE 需谨慎，确认影响范围后再使用",
                fix_suggestion="确认 CASCADE 影响范围后再使用",
            ))

        # SPEC025: Hive on Spark prohibited
        if self._has_hive_on_spark(tokens):
            self.violations.append(Violation(
                rule_id="SPEC025",
                rule_name="禁止 Hive on Spark",
                level="WARNING",
                category="SQL开发规范",
                message="应使用 Hive on Tez，禁止使用 Hive on Spark",
                fix_suggestion="使用 Hive on Tez 执行引擎（华为规范）",
            ))

    # ============================================================
    # Large SQL Interception Checks (INTERCEPT001-INTERCEPT011)
    # ============================================================

    def _check_interception(self, tokens):
        """Run large SQL interception checks"""

        # INTERCEPT001: COUNT(DISTINCT) over limit
        count_distinct_count = self._count_distinct_count(tokens)
        if count_distinct_count > 10:
            self.violations.append(Violation(
                rule_id="INTERCEPT001",
                rule_name="COUNT(DISTINCT) 次数超限",
                level="ERROR",
                category="大SQL拦截",
                message=f"SQL 中有 {count_distinct_count} 个 COUNT(DISTINCT)，超过阈值10",
                fix_suggestion="将多个 COUNT(DISTINCT) 拆分为多个子查询，利用 UNION ALL 合并结果",
            ))

        # INTERCEPT002: NOT IN subquery

        # INTERCEPT003: JOIN count over limit
        join_count = self._count_joins(tokens)
        if join_count > 20:
            self.violations.append(Violation(
                rule_id="INTERCEPT003",
                rule_name="JOIN 次数过多",
                level="ERROR",
                category="大SQL拦截",
                message=f"SQL 中有 {join_count} 个 JOIN，超过阈值20",
                fix_suggestion="减少 JOIN 次数，可将多个小表合并后再进行 JOIN",
            ))

        # INTERCEPT004: UNION ALL count over limit
        union_count = self._count_union_all(tokens)
        if union_count > 20:
            self.violations.append(Violation(
                rule_id="INTERCEPT004",
                rule_name="UNION ALL 次数超限",
                level="ERROR",
                category="大SQL拦截",
                message=f"SQL 中有 {union_count} 个 UNION ALL，超过阈值20",
                fix_suggestion="拆分 SQL 或使用 INSERT INTO 分开写入",
            ))

        # INTERCEPT005: Subquery nesting over limit
        subquery_depth = self._get_subquery_depth(tokens)
        if subquery_depth > 20:
            self.violations.append(Violation(
                rule_id="INTERCEPT005",
                rule_name="子查询嵌套层数超限",
                level="ERROR",
                category="大SQL拦截",
                message=f"子查询嵌套深度 {subquery_depth} 层，超过阈值20",
                fix_suggestion="优化 SQL，避免多重嵌套查询，拆分为中间表",
            ))

        # INTERCEPT006: SQL length over limit - check individual statements, not entire file
        statements = self._split_sql_statements()
        for i, stmt in enumerate(statements):
            sql_len = len(stmt)
            if sql_len > 10240:  # 10KB
                stmt_preview = stmt[:100].replace('\n', ' ') + ('...' if len(stmt) > 100 else '')
                self.violations.append(Violation(
                    rule_id="INTERCEPT006",
                    rule_name="SQL 语句长度超限",
                    level="WARNING",
                    category="大SQL拦截",
                    message=f"第 {i+1} 条 SQL 长度 {sql_len} 字节，超过阈值10KB",
                    sql_snippet=stmt_preview,
                    fix_suggestion="将复杂 SQL 拆分为多个简单 SQL 或使用中间表",
                ))

        # INTERCEPT007: Cartesian product (duplicate with SPEC003 but different category)
        # Already handled in SPEC003

    # ============================================================
    # Pattern Detection Helpers
    # ============================================================

    def _is_valid_naming(self, name):
        """Check if name follows Hive naming convention (lowercase + underscore)"""
        if not name:
            return True
        # Strip backticks
        name = name.strip('`')
        # Handle qualified names like "db . table" (spaces from tokenization)
        # Take only the last segment after the dot
        if '.' in name:
            parts = name.split('.')
            name = parts[-1].strip()
        name = name.strip()
        if not name:
            return True
        if name[0].isdigit():
            return False
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name))

    def _extract_column_names(self, columns_str):
        """Extract column names from parser's string representation of columns"""
        names = []
        if not columns_str:
            return names
        # Strip outer parens if present
        stripped = columns_str.strip()
        if stripped.startswith('(') and stripped.endswith(')'):
            stripped = stripped[1:-1].strip()
        # Split by comma at paren/angle depth 0 only (to handle types like decimal(38,18) and struct<name:STRING,age:INT>)
        segments = []
        current = []
        depth = 0
        for ch in stripped:
            if ch in ('(', '<'):
                depth += 1
                current.append(ch)
            elif ch in (')', '>'):
                depth = max(0, depth - 1)
                current.append(ch)
            elif ch == ',' and depth == 0:
                segments.append(''.join(current))
                current = []
            else:
                current.append(ch)
        if current:
            segments.append(''.join(current))
        for seg in segments:
            seg = seg.strip()
            # Match pattern: identifier followed by type
            m = re.match(r'^(\w+)\s+', seg)
            if m:
                names.append(m.group(1))
        return names

    def _get_column_names(self, ast):
        """Get column names from AST, handling both string and list formats"""
        columns = ast.get("columns", [])
        if isinstance(columns, str):
            return self._extract_column_names(columns)
        elif isinstance(columns, list):
            return [col.get("name", "") if isinstance(col, dict) else str(col) for col in columns]
        return []

    def _get_column_defs(self, ast):
        """Get (column_name, column_type) pairs from AST"""
        columns = ast.get("columns", "")
        result = []
        if isinstance(columns, str):
            # Strip outer parens if present
            stripped = columns.strip()
            if stripped.startswith('(') and stripped.endswith(')'):
                stripped = stripped[1:-1].strip()
            # Parse from string format: "col1 TYPE1 COMMENT 'xxx' , col2 TYPE2 ..."
            segments = self._split_col_defs(stripped)
            for seg in segments:
                seg = seg.strip()
                # Match: identifier type [COMMENT ...]
                m = re.match(r'^(\w+)\s+(\w+(?:\s*\([^)]*\))?)', seg)
                if m:
                    result.append((m.group(1), m.group(2).upper()))
        elif isinstance(columns, list):
            for col in columns:
                if isinstance(col, dict):
                    result.append((col.get("name", ""), col.get("type", "").upper()))
        return result

    # Hive type keywords used for column definition order validation
    HIVE_TYPE_KEYWORDS = frozenset({
        "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT",
        "FLOAT", "DOUBLE", "DECIMAL", "DEC",
        "BOOLEAN", "STRING", "CHAR", "VARCHAR", "BINARY",
        "DATE", "DATETIME", "TIMESTAMP", "LONG", "NUMERIC",
    })

    def _check_col_def_order(self, raw_text, context):
        """Check if column definitions have type-before-name order errors.

        Args:
            raw_text: Raw column definition text from AST (e.g., "( int s, string name )")
            context: Context description for error messages (e.g., "列定义")

        Returns:
            List of error message strings for violations found.
        """
        errors = []
        # Strip outer parens if present (AST wraps column defs in parens)
        stripped = raw_text.strip()
        if stripped.startswith('(') and stripped.endswith(')'):
            stripped = stripped[1:-1].strip()
        # Split by comma at depth 0 (respecting nested parens like DECIMAL(10,2))
        segments = self._split_col_defs(stripped)
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            # Remove COMMENT clause to avoid false positives
            # e.g., "id INT COMMENT 'int type'" -> "id INT"
            seg_no_comment = re.sub(r"\bCOMMENT\s+'[^']*'", "", seg, flags=re.IGNORECASE).strip()
            seg_no_comment = re.sub(r'\bCOMMENT\s+"[^"]*"', "", seg_no_comment, flags=re.IGNORECASE).strip()
            # Match pattern: TYPE [params] IDENT
            # e.g., "int s", "decimal(10,2) s", "string name"
            m = re.match(r'^(\w+)\s*(?:\([^)]*\))?\s+(\w+)', seg_no_comment, re.IGNORECASE)
            if m:
                first_word = m.group(1).upper()
                second_word = m.group(2).upper()
                if first_word in self.HIVE_TYPE_KEYWORDS and second_word not in self.HIVE_TYPE_KEYWORDS:
                    errors.append(f"{context}顺序错误: '{seg.strip()}'，应为 列名 类型 而非 类型 列名")
        return errors

    def _split_col_defs(self, raw_text):
        """Split column definition text by commas, respecting parenthesis and angle bracket depth."""
        segments = []
        depth = 0
        current = []
        for ch in raw_text:
            if ch in ('(', '<'):
                depth += 1
                current.append(ch)
            elif ch in (')', '>'):
                depth -= 1
                current.append(ch)
            elif ch == ',' and depth == 0:
                segments.append(''.join(current))
                current = []
            else:
                current.append(ch)
        if current:
            segments.append(''.join(current))
        return segments

    def _has_not_in_subquery(self, tokens):
        """Check for NOT IN (SELECT ...) pattern"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("NOT") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("IN"):
                    for j in range(i + 2, min(i + 5, len(tokens))):
                        if tokens[j].is_keyword("SELECT"):
                            return True
            i += 1
        return False

    def _has_implicit_type_risk(self, tokens):
        """Check for potential implicit type conversion in WHERE"""
        in_where = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("WHERE"):
                in_where = True
            elif tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or \
                 tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT"):
                in_where = False

            if in_where and tokens[i].type == TokenType.CMP_OP and tokens[i].value == "=":
                if i > 0 and i + 1 < len(tokens):
                    left = tokens[i - 1]
                    right = tokens[i + 1]
                    if (left.type == TokenType.SCONST and right.type in (TokenType.ICONST, TokenType.FCONST)) or \
                       (left.type in (TokenType.ICONST, TokenType.FCONST) and right.type == TokenType.SCONST):
                        return True
            i += 1
        return False

    def _has_leading_wildcard_like(self, tokens):
        """Check for LIKE '%...' pattern"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("LIKE") and i + 1 < len(tokens):
                next_t = tokens[i + 1]
                if next_t.type == TokenType.SCONST and next_t.value.startswith("'%"):
                    return True
            i += 1
        return False

    def _has_cartesian_product(self, tokens):
        """Check for comma-separated tables without JOIN condition.

        Returns:
            None: no comma-separated tables (safe)
            "cartesian": comma tables with NO join condition in WHERE (true cartesian product)
            "old_style_join": comma tables with join condition in WHERE (old-style join,
                              may degrade to cartesian product when CBO=false or Hive
                              cannot infer join keys from bare column names)
        """
        in_from = False
        has_comma_table = False
        has_where = False
        has_where_join_explicit = False  # WHERE has a.col = b.col pattern (table-prefixed)
        has_where_join_bare = False      # WHERE has col = col pattern (bare column names)
        paren_depth = 0
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("FROM"):
                in_from = True
            elif tokens[i].is_keyword("WHERE"):
                in_from = False
                has_where = True
            elif (tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or
                  tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT") or
                  tokens[i].is_keyword("JOIN") or tokens[i].is_keyword("UNION") or
                  tokens[i].is_keyword("INTERSECT") or tokens[i].is_keyword("MINUS") or
                  tokens[i].is_keyword("EXCEPT") or tokens[i].is_keyword("SELECT") or
                  tokens[i].is_keyword("INSERT")):
                in_from = False
                if tokens[i].is_keyword("SELECT") or tokens[i].is_keyword("INSERT") or \
                   tokens[i].is_keyword("UNION") or tokens[i].is_keyword("INTERSECT") or \
                   tokens[i].is_keyword("MINUS") or tokens[i].is_keyword("EXCEPT"):
                    has_where = False

            # Track parenthesis depth to ignore commas inside subqueries
            if tokens[i].type == TokenType.LPAREN:
                paren_depth += 1
            elif tokens[i].type == TokenType.RPAREN:
                paren_depth = max(0, paren_depth - 1)
                if paren_depth == 0:
                    in_from = False

            # Only flag commas at top-level FROM (not inside subqueries)
            if in_from and paren_depth == 0 and tokens[i].type == TokenType.COMMA:
                has_comma_table = True

            # Check for join condition in WHERE
            if has_where and paren_depth == 0 and \
               tokens[i].type == TokenType.CMP_OP and tokens[i].value == "=":
                # Pattern 1: table.col = table.col (explicit table-prefixed join)
                # Token sequence: IDENT DOT IDENT CMP_OP(=) IDENT DOT IDENT
                if i >= 3 and i + 2 < len(tokens):
                    left_is_tablecol = (tokens[i - 3].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT)
                                         and tokens[i - 2].type == TokenType.DOT)
                    right_is_tablecol = (tokens[i + 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT)
                                          and tokens[i + 2].type == TokenType.DOT)
                    if left_is_tablecol and right_is_tablecol:
                        has_where_join_explicit = True

                # Pattern 2: bare col = col or col = table.col (implicit join)
                # e.g. cs_sold_date_sk = d_date_sk
                # Left side: IDENT (not preceded by DOT) or IDENT DOT IDENT
                # Right side: IDENT (not followed by DOT) or IDENT DOT IDENT
                left_is_col = False
                right_is_col = False

                # Check left side of =
                if i >= 1:
                    # ... IDENT DOT IDENT = ... (table.col pattern)
                    if i >= 2 and tokens[i - 2].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) \
                            and tokens[i - 1].type == TokenType.DOT:
                        left_is_col = True
                    # ... DOT IDENT = ... (col part of table.col, e.g. cs1.col = bare_col)
                    elif i >= 2 and tokens[i - 2].type == TokenType.DOT \
                            and tokens[i - 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        left_is_col = True
                    # ... IDENT = ... (bare column, not preceded by DOT)
                    elif tokens[i - 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        if i < 2 or tokens[i - 2].type != TokenType.DOT:
                            left_is_col = True

                # Check right side of =
                if i + 1 < len(tokens):
                    # ... = IDENT DOT IDENT
                    if i + 3 < len(tokens) and tokens[i + 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) \
                            and tokens[i + 2].type == TokenType.DOT \
                            and tokens[i + 3].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        right_is_col = True
                    # ... = IDENT (bare column, not followed by DOT)
                    elif tokens[i + 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        if i + 2 >= len(tokens) or tokens[i + 2].type != TokenType.DOT:
                            right_is_col = True

                if left_is_col and right_is_col:
                    has_where_join_bare = True

            i += 1

        if not has_comma_table:
            return None

        has_any_join = has_where_join_explicit or has_where_join_bare
        if not has_any_join:
            return "cartesian"
        elif not has_where_join_explicit and has_where_join_bare:
            # Only bare-column joins: Hive may not recognize as join keys
            return "old_style_join"
        else:
            # Has explicit table.col = table.col joins, but still uses old-style syntax
            return "old_style_join"

    def _has_join_without_on(self, tokens):
        """Check for JOIN (LEFT/RIGHT/INNER/FULL) without ON clause.

        Returns:
            list of dicts with 'join_type' key, or empty list if no violation.
        """
        results = []
        join_type_keywords = ("LEFT", "RIGHT", "INNER", "FULL")
        i = 0
        while i < len(tokens):
            # Detect: [LEFT|RIGHT|INNER|FULL] JOIN ... without ON
            # Track: after JOIN keyword, the next ON/WHERE/JOIN/LEFT/RIGHT/INNER/FULL/GROUP/ORDER/HAVING/LIMIT/UNION
            # If no ON appears before these terminators, it's a missing ON condition
            if tokens[i].is_keyword("JOIN") or \
               (tokens[i].value.upper() in join_type_keywords and
                i + 1 < len(tokens) and tokens[i + 1].is_keyword("JOIN")):
                # Determine join type
                if tokens[i].is_keyword("JOIN"):
                    join_type = "INNER"
                else:
                    join_type = tokens[i].value.upper()
                    i += 1  # skip to JOIN keyword

                # Now scan forward from after JOIN to find ON or a terminator
                j = i + 1
                paren_depth = 0
                found_on = False
                while j < len(tokens):
                    if tokens[j].type == TokenType.LPAREN:
                        paren_depth += 1
                    elif tokens[j].type == TokenType.RPAREN:
                        paren_depth = max(0, paren_depth - 1)

                    # ON found at top level -> this JOIN has a condition
                    if paren_depth == 0 and tokens[j].is_keyword("ON"):
                        found_on = True
                        break

                    # Terminators: another JOIN, WHERE, GROUP, ORDER, HAVING, LIMIT, UNION, etc.
                    if paren_depth == 0 and (
                        tokens[j].is_keyword("LEFT") or tokens[j].is_keyword("RIGHT") or
                        tokens[j].is_keyword("INNER") or tokens[j].is_keyword("FULL") or
                        tokens[j].is_keyword("CROSS") or tokens[j].is_keyword("JOIN") or
                        tokens[j].is_keyword("WHERE") or tokens[j].is_keyword("GROUP") or
                        tokens[j].is_keyword("ORDER") or tokens[j].is_keyword("HAVING") or
                        tokens[j].is_keyword("LIMIT") or tokens[j].is_keyword("UNION") or
                        tokens[j].is_keyword("INTERSECT") or tokens[j].is_keyword("MINUS") or
                        tokens[j].is_keyword("EXCEPT") or tokens[j].type == TokenType.SEMICOLON
                    ):
                        # This is a terminator, but skip if it's the JOIN keyword right after LEFT/RIGHT etc.
                        if j == i + 1 and tokens[j].is_keyword("JOIN"):
                            j += 1
                            continue
                        break

                    j += 1

                if not found_on:
                    results.append({"join_type": join_type})

            i += 1

        return results

    def _has_partition_field_function(self, tokens):
        """Check for function on partition field in WHERE"""
        in_where = False
        partition_fields = self._detect_partition_fields(tokens)
        func_names = ("SUBSTR", "SUBSTRING", "TRIM", "UPPER", "LOWER", "CONCAT",
                      "REPLACE", "LENGTH", "DATE_FORMAT", "YEAR", "MONTH", "DAY",
                      "HOUR", "MINUTE", "SECOND", "TO_DATE", "TO_CHAR")

        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("WHERE"):
                in_where = True
            elif tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or \
                 tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT"):
                in_where = False

            if in_where and i + 2 < len(tokens):
                val_upper = tokens[i].value.upper()
                if val_upper in func_names and tokens[i + 1].type == TokenType.LPAREN:
                    # Check if any partition field is used as argument
                    for j in range(i + 2, min(i + 8, len(tokens))):
                        if tokens[j].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                            field_name = tokens[j].value.strip('`').lower()
                            if field_name in partition_fields:
                                return True
            i += 1
        return False

    def _detect_partition_fields(self, tokens):
        """Detect partition field names from PARTITIONED BY clause"""
        fields = set()
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("PARTITIONED") and i + 2 < len(tokens):
                if tokens[i + 1].is_keyword("BY") and tokens[i + 2].type == TokenType.LPAREN:
                    # Read partition column names
                    depth = 1
                    j = i + 3
                    while j < len(tokens) and depth > 0:
                        if tokens[j].type == TokenType.LPAREN:
                            depth += 1
                        elif tokens[j].type == TokenType.RPAREN:
                            depth -= 1
                        elif tokens[j].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) and depth == 1:
                            fields.add(tokens[j].value.strip('`').lower())
                        j += 1
            i += 1
        # Common partition field names
        fields.update({"dt", "day", "hour", "month", "year", "pt_d", "p_date", "event_date"})
        return fields

    def _has_case_without_else(self, tokens):
        """Check for CASE WHEN without ELSE"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("CASE"):
                has_else = False
                j = i + 1
                depth = 0
                while j < len(tokens):
                    if tokens[j].type == TokenType.LPAREN:
                        depth += 1
                    elif tokens[j].type == TokenType.RPAREN:
                        depth -= 1
                    elif depth == 0:
                        if tokens[j].is_keyword("ELSE"):
                            has_else = True
                        elif tokens[j].is_keyword("END"):
                            if not has_else:
                                return True
                            break
                        elif tokens[j].is_keyword("CASE"):
                            # Nested CASE, skip
                            depth += 1
                    j += 1
            i += 1
        return False

    def _check_null_handling_risk(self, tokens):
        """Check for NULL handling risk in conditions, return list of violation details"""
        risks = []
        in_where = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("WHERE"):
                in_where = True
            elif tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or \
                 tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT"):
                in_where = False

            if in_where and tokens[i].type == TokenType.CMP_OP:
                op = tokens[i].value
                # Risk 1: col = NULL (wrong, should use IS NULL)
                if op == "=" and i + 1 < len(tokens):
                    right = tokens[i + 1]
                    if right.type == TokenType.KEYWORD and right.value.upper() == "NULL":
                        # Check it's NOT part of "IS NULL" or "IS NOT NULL"
                        is_is_null = False
                        if i >= 1 and tokens[i - 1].is_keyword("IS"):
                            is_is_null = True
                        if i >= 2 and tokens[i - 1].is_keyword("NULL") and tokens[i - 2].is_keyword("NOT") and i >= 3 and tokens[i - 3].is_keyword("IS"):
                            is_is_null = True
                        if not is_is_null:
                            snippet = self._build_snippet(tokens, i, 2)
                            risks.append({
                                "line": tokens[i].line if hasattr(tokens[i], 'line') else 0,
                                "column": tokens[i].col if hasattr(tokens[i], 'col') else 0,
                                "snippet": snippet,
                                "message": "使用 = NULL 无法匹配 NULL 值，应使用 IS NULL",
                            })

                # Risk 2: col <> value / col != value (NULL rows silently excluded)
                if op in ("<>", "!=", "<=>"):
                    if i + 1 < len(tokens):
                        right = tokens[i + 1]
                        right_val = right.value.strip("'\"") if right.type == TokenType.SCONST else None
                        # Skip if comparing with NULL literal (that's Risk 1)
                        is_null_cmp = right.type == TokenType.KEYWORD and right.value.upper() == "NULL"
                        if not is_null_cmp and right_val is not None and right_val.upper() != "NULL":
                            snippet = self._build_snippet(tokens, i, 2)
                            risks.append({
                                "line": tokens[i].line if hasattr(tokens[i], 'line') else 0,
                                "column": tokens[i].col if hasattr(tokens[i], 'col') else 0,
                                "snippet": snippet,
                                "message": f"条件 {snippet} 中 NULL 值行将被排除，需显式处理 NULL 逻辑",
                            })
            i += 1
        return risks

    def _build_snippet(self, tokens, center_idx, radius=2):
        """Build a short SQL snippet around a token for context, skipping keywords like WHERE/AND/;"""
        start = max(0, center_idx - radius)
        end = min(len(tokens), center_idx + radius + 1)
        skip_values = {"WHERE", "AND", "OR", ";", "ON", "HAVING", "GROUP", "ORDER", "LIMIT"}
        parts = []
        for j in range(start, end):
            t = tokens[j]
            if hasattr(t, 'value') and t.value.upper() not in skip_values:
                parts.append(t.value)
        return " ".join(parts)

    def _has_string_null(self, tokens):
        """Check for string 'NULL'/'null' usage"""
        for t in tokens:
            if t.type == TokenType.SCONST:
                val = t.value.strip("'\"")
                if val.upper() == "NULL" and val != "NULL":
                    # Lowercase 'null' or mixed case
                    return True
                # Check for string NULL in SELECT list
                if val == "NULL":
                    # Check if it's in a SELECT context (not IS NULL / IS NOT NULL)
                    return True
        return False

    def _has_join_type_mismatch(self, tokens):
        """Heuristic check for JOIN field type mismatch"""
        # Look for pattern: JOIN ON col1 = col2 where one has CAST
        in_join_on = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("ON"):
                in_join_on = True
            elif tokens[i].is_keyword("AND") and in_join_on:
                pass  # Continue in ON clause
            elif tokens[i].is_keyword("WHERE") or tokens[i].is_keyword("JOIN") or \
                 tokens[i].is_keyword("LEFT") or tokens[i].is_keyword("RIGHT") or \
                 tokens[i].is_keyword("INNER") or tokens[i].is_keyword("FULL"):
                in_join_on = False

            if in_join_on and tokens[i].type == TokenType.CMP_OP and tokens[i].value == "=":
                if i > 0 and i + 1 < len(tokens):
                    left = tokens[i - 1]
                    right = tokens[i + 1]
                    # String = number pattern
                    if (left.type == TokenType.SCONST and right.type in (TokenType.ICONST, TokenType.FCONST)) or \
                       (left.type in (TokenType.ICONST, TokenType.FCONST) and right.type == TokenType.SCONST):
                        return True
            i += 1
        return False

    def _split_sql_statements(self):
        """Split SQL text into individual statements using tokenizer.

        Splits by semicolons while respecting SQL syntax (strings, comments, etc.).
        Returns a list of non-empty SQL statements.
        """
        if not self.tokens:
            # Tokenize if not already done
            self.tokens, _ = tokenize(self.sql_text)

        statements = []
        current_stmt_tokens = []

        for token in self.tokens:
            if token.type == TokenType.SEMICOLON:
                # End of statement
                if current_stmt_tokens:
                    # Reconstruct the statement from tokens
                    stmt_text = ' '.join(t.value for t in current_stmt_tokens if t.value)
                    if stmt_text.strip():
                        statements.append(stmt_text.strip())
                    current_stmt_tokens = []
            else:
                current_stmt_tokens.append(token)

        # Handle last statement (may not end with semicolon)
        if current_stmt_tokens:
            stmt_text = ' '.join(t.value for t in current_stmt_tokens if t.value)
            if stmt_text.strip():
                statements.append(stmt_text.strip())

        return statements if statements else [self.sql_text]

    def _infer_partitioned_tables(self):
        """Infer partitioned table names from the SQL text itself.

        A table is considered partitioned if any of these patterns appear:
        1. CREATE TABLE ... PARTITIONED BY ...
        2. INSERT INTO/OVERWRITE ... PARTITION(...) ...
        3. ALTER TABLE ... ADD/DROP PARTITION ...

        Returns:
            set of lowercased table names known to be partitioned
        """
        partitioned = set()
        text_upper = self.sql_text.upper()

        # Tokenize the full text to get structured tokens
        try:
            tokens, _ = tokenize(self.sql_text)
        except Exception:
            return partitioned

        i = 0
        while i < len(tokens):
            t = tokens[i]

            # Pattern 1: CREATE TABLE <name> ... PARTITIONED BY ...
            if t.is_keyword("CREATE") and i + 2 < len(tokens) and tokens[i + 1].is_keyword("TABLE"):
                # Find table name (skip optional EXTERNAL/TEMPORARY)
                name_idx = i + 2
                while name_idx < len(tokens) and tokens[name_idx].is_keyword() and \
                        tokens[name_idx].value.upper() in ("EXTERNAL", "TEMPORARY", "MANAGED"):
                    name_idx += 1
                if name_idx < len(tokens) and tokens[name_idx].type in (
                        TokenType.IDENT, TokenType.BACKTICK_IDENT):
                    table_name = tokens[name_idx].value.strip('`').lower()
                    # Look ahead for PARTITIONED BY within this statement
                    for j in range(name_idx + 1, min(name_idx + 50, len(tokens))):
                        if tokens[j].is_keyword("PARTITIONED"):
                            partitioned.add(table_name)
                            break
                        # Stop at next statement boundary
                        if tokens[j].value == ';':
                            break

            # Pattern 2: INSERT INTO/OVERWRITE <table> PARTITION(...) ...
            elif t.is_keyword("INSERT") and i + 2 < len(tokens):
                ins_idx = i + 1
                if tokens[ins_idx].is_keyword("INTO") or tokens[ins_idx].is_keyword("OVERWRITE"):
                    # Skip optional TABLE keyword
                    tbl_idx = ins_idx + 1
                    if tbl_idx < len(tokens) and tokens[tbl_idx].is_keyword("TABLE"):
                        tbl_idx += 1
                    if tbl_idx < len(tokens) and tokens[tbl_idx].type in (
                            TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        table_name = tokens[tbl_idx].value.strip('`').lower()
                        # Check if PARTITION follows
                        part_idx = tbl_idx + 1
                        if part_idx < len(tokens) and tokens[part_idx].is_keyword("PARTITION"):
                            partitioned.add(table_name)

            # Pattern 3: ALTER TABLE <name> ADD/DROP PARTITION ...
            elif t.is_keyword("ALTER") and i + 3 < len(tokens) and tokens[i + 1].is_keyword("TABLE"):
                name_idx = i + 2
                if name_idx < len(tokens) and tokens[name_idx].type in (
                        TokenType.IDENT, TokenType.BACKTICK_IDENT):
                    table_name = tokens[name_idx].value.strip('`').lower()
                    action_idx = name_idx + 1
                    if action_idx < len(tokens) and (tokens[action_idx].is_keyword("ADD") or tokens[action_idx].is_keyword("DROP")):
                        part_idx = action_idx + 1
                        if part_idx < len(tokens) and tokens[part_idx].is_keyword("PARTITION"):
                            partitioned.add(table_name)

            i += 1

        return partitioned

    def _infer_partition_fields(self):
        """Infer partition field names from the SQL text itself.

        Extracts column names from PARTITIONED BY (...) clauses in CREATE TABLE
        statements. Works on the full SQL text so that multi-statement input
        can share partition field knowledge across statements.

        Returns:
            set of lowercased partition field names
        """
        fields = set()
        try:
            tokens, _ = tokenize(self.sql_text)
        except Exception:
            return fields

        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("PARTITIONED") and i + 2 < len(tokens) and tokens[i + 1].is_keyword("BY"):
                j = i + 2
                if j < len(tokens) and tokens[j].value == '(':
                    j += 1
                    depth = 1
                    while j < len(tokens) and depth > 0:
                        if tokens[j].value == '(':
                            depth += 1
                        elif tokens[j].value == ')':
                            depth -= 1
                        elif tokens[j].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) and depth == 1:
                            val = tokens[j].value.strip('`').lower()
                            if not tokens[j].is_keyword():
                                fields.add(val)
                        j += 1
            i += 1
        return fields

    def _extract_from_tables(self, tokens):
        """Extract table names from FROM and JOIN clauses in the token stream.

        Returns:
            set of lowercased table names referenced in FROM/JOIN
        """
        tables = set()
        i = 0
        while i < len(tokens):
            t = tokens[i]
            # FROM <table> or JOIN <table>
            if t.is_keyword("FROM") or t.is_keyword("JOIN"):
                j = i + 1
                # Skip qualifiers: LEFT, RIGHT, OUTER, INNER, FULL, CROSS, SEMI
                _join_qualifiers = {"LEFT", "RIGHT", "OUTER", "INNER", "FULL", "CROSS", "SEMI", "ANTI"}
                while j < len(tokens) and tokens[j].is_keyword() and \
                        tokens[j].value.upper() in _join_qualifiers:
                    j += 1
                if j < len(tokens) and tokens[j].type in (
                        TokenType.IDENT, TokenType.BACKTICK_IDENT):
                    tables.add(tokens[j].value.strip('`').lower())
            i += 1
        return tables

    def _has_partition_table_without_filter(self, tokens):
        """Check for partitioned table query without partition filter.

        Only triggers when the SQL text itself provides evidence that the
        queried table is partitioned (via CREATE TABLE...PARTITIONED BY,
        INSERT...PARTITION, or ALTER TABLE...PARTITION). If no such evidence
        exists, the rule does NOT fire to avoid false positives.
        """
        if not self._partitioned_tables:
            return False

        # Extract tables referenced in FROM/JOIN
        from_tables = self._extract_from_tables(tokens)

        # Only check tables that are confirmed partitioned
        queried_partitioned = from_tables & self._partitioned_tables
        if not queried_partitioned:
            return False

        # Check if WHERE contains any partition field filter
        # Use pre-inferred partition fields (shared across multi-statement context)
        partition_fields = self._partition_fields
        has_partition_filter = False

        in_where = False
        for t in tokens:
            if t.is_keyword("WHERE"):
                in_where = True
            elif t.is_keyword("GROUP") or t.is_keyword("ORDER") or \
                 t.is_keyword("HAVING") or t.is_keyword("LIMIT"):
                in_where = False

            if in_where and t.type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                if t.value.strip('`').lower() in partition_fields:
                    has_partition_filter = True
                    break

        return not has_partition_filter

    def _extract_partition_fields(self, tokens):
        """Extract partition column names from PARTITIONED BY clauses.

        Returns:
            set of lowercased partition field names
        """
        fields = set()
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("PARTITIONED") and i + 2 < len(tokens) and tokens[i + 1].is_keyword("BY"):
                # Skip PARTITIONED BY and opening paren
                j = i + 2
                if j < len(tokens) and tokens[j].value == '(':
                    j += 1
                    # Read column names until closing paren
                    depth = 1
                    while j < len(tokens) and depth > 0:
                        if tokens[j].value == '(':
                            depth += 1
                        elif tokens[j].value == ')':
                            depth -= 1
                        elif tokens[j].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) and depth == 1:
                            # This is a partition column name (skip type keywords)
                            val = tokens[j].value.strip('`').lower()
                            # Skip if it's a type keyword
                            if not tokens[j].is_keyword():
                                fields.add(val)
                        j += 1
            i += 1
        return fields

    def _has_non_standard_join_condition(self, tokens):
        """Check for IF/CASE WHEN in JOIN ON condition"""
        in_on = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("ON"):
                in_on = True
            elif tokens[i].is_keyword("WHERE") or tokens[i].is_keyword("JOIN") or \
                 tokens[i].is_keyword("LEFT") or tokens[i].is_keyword("RIGHT") or \
                 tokens[i].is_keyword("INNER") or tokens[i].is_keyword("FULL"):
                in_on = False

            if in_on and (tokens[i].is_keyword("CASE") or
                          (tokens[i].is_keyword("IF") and i + 1 < len(tokens) and
                           tokens[i + 1].type == TokenType.LPAREN)):
                return True
            i += 1
        return False

    def _has_large_small_join_without_mapjoin(self, tokens):
        """Check for JOIN without MAPJOIN hint (heuristic)"""
        has_join = False
        has_mapjoin_hint = False
        for t in tokens:
            if t.is_keyword("JOIN"):
                has_join = True
            if t.type == TokenType.HINT and "MAPJOIN" in t.value.upper():
                has_mapjoin_hint = True
        return has_join and not has_mapjoin_hint

    def _has_drop_without_if_exists(self, tokens):
        """Check for DROP without IF EXISTS"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("DROP"):
                has_if_exists = False
                for j in range(i + 1, min(i + 6, len(tokens))):
                    if tokens[j].is_keyword("IF"):
                        for k in range(j + 1, min(j + 3, len(tokens))):
                            if tokens[k].is_keyword("EXISTS"):
                                has_if_exists = True
                                break
                if not has_if_exists:
                    return True
            i += 1
        return False

    def _has_insert_values(self, tokens):
        """Check for INSERT INTO ... VALUES pattern"""
        i = 0
        in_insert = False
        has_values = False
        while i < len(tokens):
            if tokens[i].is_keyword("INSERT"):
                in_insert = True
                has_values = False
            if in_insert and tokens[i].is_keyword("VALUES"):
                has_values = True
            if tokens[i].type == TokenType.SEMICOLON:
                if in_insert and has_values:
                    return True
                in_insert = False
                has_values = False
            i += 1
        # Check end of statement
        if in_insert and has_values:
            return True
        return False

    def _has_cascade_usage(self, tokens):
        """Check for CASCADE in ALTER TABLE"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("ALTER") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("TABLE"):
                    for j in range(i + 2, min(i + 15, len(tokens))):
                        if tokens[j].is_keyword("CASCADE"):
                            return True
            i += 1
        return False

    def _has_hive_on_spark(self, tokens):
        """Check for Hive on Spark execution engine setting"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("SET") and i + 2 < len(tokens):
                # Check for hive.execution.engine=spark
                # Tokenized as: SET IDENT(hive) DOT IDENT(execution) DOT IDENT(engine) CMP_OP(=) IDENT(spark)
                # Or: SET IDENT(hive.execution.engine) CMP_OP(=) IDENT(spark)
                for j in range(i + 1, min(i + 10, len(tokens))):
                    t = tokens[j]
                    # Pattern 1: single token "hive.execution.engine"
                    if t.type == TokenType.IDENT and "execution.engine" in t.value.lower():
                        for k in range(j + 1, min(j + 4, len(tokens))):
                            if tokens[k].type == TokenType.IDENT and "spark" in tokens[k].value.lower():
                                return True
                            if tokens[k].type == TokenType.SCONST and "spark" in tokens[k].value.lower():
                                return True
                    # Pattern 2: hive . execution . engine = spark
                    if t.type == TokenType.IDENT and t.value.lower() == "hive":
                        # Look for .execution.engine=spark pattern
                        remaining = " ".join(
                            tokens[x].value for x in range(j, min(j + 8, len(tokens)))
                            if tokens[x].type in (TokenType.IDENT, TokenType.DOT, TokenType.CMP_OP)
                        ).replace(" ", "")
                        if "engine=spark" in remaining.lower() or "engine=spark" in remaining.lower():
                            return True
            i += 1
        return False

    def _has_lateral_view(self, tokens):
        """Check if LATERAL VIEW exists"""
        for i, t in enumerate(tokens):
            if t.is_keyword("LATERAL") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("VIEW") or tokens[i + 1].is_keyword("TABLE"):
                    return True
        return False

    def _validate_lateral_view(self, tokens):
        """Validate LATERAL VIEW syntax structure.

        Hive syntax: LATERAL VIEW [OUTER] func(args) table_alias [AS col_alias[, ...]]
        - AS is optional: LATERAL VIEW explode(map(...)) myTab  (alias serves as both)
        - Search until FROM/WHERE/end of tokens, not just 15 tokens ahead
        """
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("LATERAL") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("VIEW"):
                    # LATERAL VIEW [OUTER] func(...)
                    j = i + 2
                    # Skip optional OUTER
                    if j < len(tokens) and tokens[j].is_keyword("OUTER"):
                        j += 1
                    # Must have a function name next
                    if j >= len(tokens) or tokens[j].type not in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        return False
                    j += 1  # skip function name
                    # Must have opening paren
                    if j >= len(tokens) or tokens[j].type != TokenType.LPAREN:
                        return False
                    # Skip to matching close paren
                    depth = 0
                    while j < len(tokens):
                        if tokens[j].type == TokenType.LPAREN:
                            depth += 1
                        elif tokens[j].type == TokenType.RPAREN:
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    j += 1  # skip RPAREN
                    # After func(...), must have table alias (an identifier)
                    if j < len(tokens) and tokens[j].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        return True  # has table alias — valid
                    return False
            i += 1
        return True  # No LATERAL VIEW found

    def _count_distinct_count(self, tokens):
        """Count number of COUNT(DISTINCT ...) expressions"""
        count = 0
        i = 0
        while i < len(tokens):
            if tokens[i].value.upper() == "COUNT" and i + 3 < len(tokens):
                if tokens[i + 1].type == TokenType.LPAREN and tokens[i + 2].is_keyword("DISTINCT"):
                    count += 1
            i += 1
        return count

    def _count_joins(self, tokens):
        """Count number of JOIN keywords"""
        count = 0
        for t in tokens:
            if t.is_keyword("JOIN"):
                count += 1
        return count

    def _count_union_all(self, tokens):
        """Count number of UNION ALL"""
        count = 0
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("UNION") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("ALL"):
                    count += 1
            i += 1
        return count

    def _get_subquery_depth(self, tokens):
        """Calculate maximum subquery nesting depth"""
        max_depth = 0
        current_depth = 0
        i = 0
        while i < len(tokens):
            if tokens[i].type == TokenType.LPAREN:
                # Check if this starts a subquery
                for j in range(i + 1, min(i + 3, len(tokens))):
                    if tokens[j].is_keyword("SELECT"):
                        current_depth += 1
                        max_depth = max(max_depth, current_depth)
                        break
            elif tokens[i].type == TokenType.RPAREN:
                if current_depth > 0:
                    current_depth -= 1
            i += 1
        return max_depth

    # ============================================================
    # Helper: Accurate column counting from tokens
    # ============================================================

    def _count_create_table_columns(self):
        """
        Count the number of column definitions in a CREATE TABLE statement
        by counting top-level commas (paren_depth==1, angle_depth==0) between
        the first LPAREN after TABLE and its matching RPAREN. This avoids
        counting commas inside DECIMAL(10,2), MAP<string, string>,
        STRUCT<name:string, age:int>, COMMENT '...', etc.
        """
        in_create = False
        paren_depth = 0
        angle_depth = 0
        col_comma_count = 0
        for t in self.tokens:
            if t.is_keyword("TABLE"):
                in_create = True
            if in_create:
                if t.type == TokenType.LPAREN:
                    paren_depth += 1
                elif t.type == TokenType.RPAREN:
                    paren_depth -= 1
                    if paren_depth == 0:
                        break
                elif t.type == TokenType.CMP_OP and t.value == '<' and angle_depth >= 0:
                    angle_depth += 1
                elif t.type == TokenType.CMP_OP and t.value == '>' and angle_depth > 0:
                    angle_depth -= 1
                elif t.type == TokenType.OP and t.value == '>>' and angle_depth >= 2:
                    angle_depth -= 2
                elif t.type == TokenType.OP and t.value == '>>' and angle_depth == 1:
                    angle_depth = 0
                elif t.type == TokenType.COMMA and paren_depth == 1 and angle_depth == 0:
                    col_comma_count += 1
        return col_comma_count + 1 if col_comma_count > 0 else 0

    def _count_column_comments(self):
        """
        Count the number of column COMMENT clauses in a CREATE TABLE statement
        by counting COMMENT keywords at paren_depth == 1 and angle_depth == 0
        (inside column list only, not inside MAP/STRUCT type parameters).
        """
        in_create = False
        paren_depth = 0
        angle_depth = 0
        comment_count = 0
        for t in self.tokens:
            if t.is_keyword("TABLE"):
                in_create = True
            if in_create:
                if t.type == TokenType.LPAREN:
                    paren_depth += 1
                elif t.type == TokenType.RPAREN:
                    paren_depth -= 1
                    if paren_depth == 0:
                        break
                elif t.type == TokenType.CMP_OP and t.value == '<' and angle_depth >= 0:
                    angle_depth += 1
                elif t.type == TokenType.CMP_OP and t.value == '>' and angle_depth > 0:
                    angle_depth -= 1
                elif t.type == TokenType.OP and t.value == '>>' and angle_depth >= 2:
                    angle_depth -= 2
                elif t.type == TokenType.OP and t.value == '>>' and angle_depth == 1:
                    angle_depth = 0
                elif t.is_keyword("COMMENT") and paren_depth == 1 and angle_depth == 0:
                    comment_count += 1
        return comment_count

    # ============================================================
    # Report Generation
    # ============================================================

    def _get_snippet(self, line, column, context=30):
        """Get a code snippet around the given position"""
        if not self.sql_text:
            return ""
        lines = self.sql_text.split('\n')
        if line < 1 or line > len(lines):
            return ""
        target_line = lines[line - 1]
        start = max(0, column - context)
        end = min(len(target_line), column + context)
        return target_line[start:end].strip()

    def _generate_report(self):
        """Generate the final check report"""
        errors = [v for v in self.violations if v.level == "ERROR"]
        warnings = [v for v in self.violations if v.level == "WARNING"]
        infos = [v for v in self.violations if v.level == "INFO"]

        total_rules = 50  # 14 syntax + 25 spec + 11 interception
        passed = total_rules - len(self.violations)
        if passed < 0:
            passed = 0

        report = {
            "check_time": datetime.now().isoformat(),
            "check_mode": self.check_mode,
            "statement_type": self.parse_result.get("statement_type", "UNKNOWN") if self.parse_result else "UNKNOWN",
            "sql_length": len(self.sql_text),
            "summary": {
                "total_rules_checked": total_rules,
                "passed": passed,
                "failed": len(self.violations),
                "errors": len(errors),
                "warnings": len(warnings),
                "infos": len(infos),
            },
            "violations": [v.to_dict() for v in self.violations],
        }

        return report

    def generate_markdown_report(self):
        """Generate a human-readable Markdown report"""
        report = self.check()

        lines = []
        lines.append("# MRS Hive SQL 检查报告")
        lines.append("")
        lines.append(f"**检查时间**: {report['check_time']}")
        lines.append(f"**语句类型**: {report['statement_type']}")
        lines.append(f"**检查模式**: {report['check_mode']}")
        lines.append(f"**SQL 长度**: {report['sql_length']} 字符")
        lines.append("")

        # Summary table
        s = report['summary']
        lines.append("## 检查概要")
        lines.append("")
        lines.append("| 指标 | 值 |")
        lines.append("|------|------|")
        lines.append(f"| 检查规则数 | {s['total_rules_checked']} |")
        lines.append(f"| 通过 | {s['passed']} |")
        lines.append(f"| 违规 | {s['failed']} |")
        lines.append(f"| 错误 (ERROR) | {s['errors']} |")
        lines.append(f"| 警告 (WARNING) | {s['warnings']} |")
        lines.append(f"| 提示 (INFO) | {s['infos']} |")
        lines.append("")

        if not report['violations']:
            lines.append("**所有检查项均已通过**")
            return '\n'.join(lines)

        # Group by category
        by_category = {}
        for v in report['violations']:
            cat = v['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(v)

        # Category order
        category_order = ["语法检查", "对象设计规范", "数据操作规范", "命名规范",
                          "SQL开发规范", "大SQL拦截"]

        for category in category_order:
            if category not in by_category:
                continue
            violations = by_category[category]
            lines.append(f"## {category}")
            lines.append("")
            for v in violations:
                level_icon = {"ERROR": "X", "WARNING": "!", "INFO": "i"}.get(v['level'], "?")
                lines.append(f"### [{level_icon}] {v['rule_id']}: {v['rule_name']}")
                lines.append("")
                lines.append(f"- **级别**: {v['level']}")
                if v['line'] > 0:
                    lines.append(f"- **位置**: 行 {v['line']}, 列 {v['column']}")
                lines.append(f"- **描述**: {v['message']}")
                if v['sql_snippet']:
                    lines.append(f"- **代码片段**: `{v['sql_snippet']}`")
                if v['fix_suggestion']:
                    lines.append(f"- **修复建议**: {v['fix_suggestion']}")
                lines.append("")

        # Original SQL
        lines.append("## 原始 SQL")
        lines.append("")
        lines.append("```sql")
        # Truncate very long SQL
        display_sql = self.sql_text
        if len(display_sql) > 2000:
            display_sql = display_sql[:2000] + "\n... (truncated)"
        lines.append(display_sql)
        lines.append("```")

        return '\n'.join(lines)


def split_sql_statements(sql_text):
    """
    Split multi-statement SQL text into individual statements,
    respecting string literals and comments (semicolons inside
    strings or comments are NOT treated as statement separators).

    Uses the tokenizer to find SEMICOLON tokens at the top level,
    then slices the original text accordingly.

    Args:
        sql_text: SQL text that may contain multiple statements

    Returns:
        list[str]: List of individual SQL statement strings
    """
    tokens, _ = tokenize(sql_text)

    # Find positions of top-level semicolons in the original text
    semicolon_positions = []
    for t in tokens:
        if t.type == TokenType.SEMICOLON:
            # Find the ';' character position in the original text at this line/column
            # Walk the text to find the exact offset
            lines = sql_text.split('\n')
            offset = 0
            for i in range(t.line - 1):
                offset += len(lines[i]) + 1  # +1 for the newline
            offset += t.column - 1
            semicolon_positions.append(offset)

    if not semicolon_positions:
        stmt = sql_text.strip()
        return [stmt] if stmt else []

    # Split the text at semicolon positions
    statements = []
    prev = 0
    for pos in semicolon_positions:
        stmt = sql_text[prev:pos].strip()
        if stmt and not stmt.startswith('--'):
            statements.append(stmt)
        prev = pos + 1

    # Handle trailing text after the last semicolon
    trailing = sql_text[prev:].strip()
    if trailing and not trailing.startswith('--'):
        statements.append(trailing)

    return statements


def check_sql(sql_text, check_mode="all"):
    """
    Convenience function to check SQL text.
    Supports multi-statement SQL: each statement is checked independently,
    and violations are aggregated into a single report.

    Args:
        sql_text: SQL text to check (single or multi-statement)
        check_mode: "syntax", "spec", "intercept", or "all"

    Returns:
        dict: Check report
    """
    statements = split_sql_statements(sql_text)

    if len(statements) <= 1:
        checker = HiveSQLChecker(sql_text, check_mode=check_mode)
        return checker.check()

    # Multi-statement: infer partitioned tables and partition fields from the
    # FULL SQL text first, then pass the knowledge to each sub-checker so that
    # SELECT statements can benefit from CREATE TABLE ... PARTITIONED BY in
    # other statements.
    full_checker = HiveSQLChecker(sql_text, check_mode=check_mode)
    shared_partitioned_tables = full_checker._partitioned_tables
    shared_partition_fields = full_checker._partition_fields

    all_violations = []
    primary_type = "UNKNOWN"
    total_rules = 0
    total_passed = 0
    statement_types = []

    for idx, stmt in enumerate(statements):
        checker = HiveSQLChecker(stmt, check_mode=check_mode,
                                 partitioned_tables=shared_partitioned_tables,
                                 partition_fields=shared_partition_fields)
        report = checker.check()
        # Tag each violation with its source statement index
        for v in report.get("violations", []):
            v["statement_index"] = idx
            v["statement_text"] = stmt
        all_violations.extend(report.get("violations", []))
        stmt_type = report.get("statement_type", "UNKNOWN")
        statement_types.append(stmt_type)
        if primary_type == "UNKNOWN" and stmt_type != "UNKNOWN":
            primary_type = stmt_type
        total_rules += report.get("summary", {}).get("total_rules_checked", 0)
        total_passed += report.get("summary", {}).get("passed", 0)

    total_failed = len(all_violations)
    errors = sum(1 for v in all_violations if v.get("level") == "ERROR")
    warnings = sum(1 for v in all_violations if v.get("level") == "WARNING")
    infos = sum(1 for v in all_violations if v.get("level") == "INFO")

    return {
        "check_time": datetime.now().isoformat(),
        "check_mode": check_mode,
        "statement_type": primary_type,
        "sql_length": len(sql_text),
        "summary": {
            "total_rules_checked": total_rules,
            "passed": total_passed,
            "failed": total_failed,
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
        },
        "violations": all_violations,
        "statements": [{"index": i, "type": t, "text": s}
                       for i, (t, s) in enumerate(zip(statement_types, statements))],
    }


def check_sql_markdown(sql_text, check_mode="all"):
    """
    Check SQL and return Markdown report.
    Supports multi-statement SQL: partition info from CREATE TABLE
    statements is shared with subsequent SELECT/INSERT statements.

    Args:
        sql_text: SQL text to check (single or multi-statement)
        check_mode: "syntax", "spec", "intercept", or "all"

    Returns:
        str: Markdown report
    """
    report = check_sql(sql_text, check_mode=check_mode)

    lines = []
    lines.append("# MRS Hive SQL 检查报告")
    lines.append("")
    lines.append(f"**检查时间**: {report['check_time']}")
    lines.append(f"**语句类型**: {report['statement_type']}")
    lines.append(f"**检查模式**: {report['check_mode']}")
    lines.append(f"**SQL 长度**: {report['sql_length']} 字符")
    lines.append("")

    # Summary table
    s = report['summary']
    lines.append("## 检查概要")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|------|")
    lines.append(f"| 检查规则数 | {s['total_rules_checked']} |")
    lines.append(f"| 通过 | {s['passed']} |")
    lines.append(f"| 违规 | {s['failed']} |")
    lines.append(f"| 错误 (ERROR) | {s['errors']} |")
    lines.append(f"| 警告 (WARNING) | {s['warnings']} |")
    lines.append(f"| 提示 (INFO) | {s['infos']} |")
    lines.append("")

    if not report['violations']:
        lines.append("**所有检查项均已通过**")
        return '\n'.join(lines)

    # Group by category
    by_category = {}
    for v in report['violations']:
        cat = v['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(v)

    # Category order
    category_order = ["语法检查", "对象设计规范", "数据操作规范", "命名规范",
                      "SQL开发规范", "大SQL拦截"]

    for category in category_order:
        if category not in by_category:
            continue
        violations = by_category[category]
        lines.append(f"## {category}")
        lines.append("")
        for v in violations:
            level_icon = {"ERROR": "X", "WARNING": "!", "INFO": "i"}.get(v['level'], "?")
            lines.append(f"### [{level_icon}] {v['rule_id']}: {v['rule_name']}")
            lines.append("")
            lines.append(f"- **级别**: {v['level']}")
            if v.get('statement_index') is not None:
                lines.append(f"- **所属语句**: 第 {v['statement_index'] + 1} 条")
            if v['line'] > 0:
                lines.append(f"- **位置**: 行 {v['line']}, 列 {v['column']}")
            lines.append(f"- **描述**: {v['message']}")
            if v['sql_snippet']:
                lines.append(f"- **代码片段**: `{v['sql_snippet']}`")
            if v['fix_suggestion']:
                lines.append(f"- **修复建议**: {v['fix_suggestion']}")
            lines.append("")

    # Original SQL
    lines.append("## 原始 SQL")
    lines.append("")
    lines.append("```sql")
    # Truncate very long SQL
    display_sql = sql_text
    if len(display_sql) > 2000:
        display_sql = display_sql[:2000] + "\n... (truncated)"
    lines.append(display_sql)
    lines.append("```")

    return '\n'.join(lines)


# ---- CLI Entry Point ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python hive_sql_checker.py <sql_text_or_file> [syntax|spec|intercept|all]")
        sys.exit(1)

    input_text = sys.argv[1]
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    report = check_sql(input_text, check_mode=mode)

    print(json.dumps(report, indent=2, ensure_ascii=False))
