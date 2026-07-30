# -*- coding: utf-8 -*-
"""
MRS Spark SQL Checker Engine
Integrates tokenizer, parser, and rule-based checking.

Three-stage pipeline:
  1. Syntax Check - keyword validation, structure validation, Spark SQL compatibility
  2. Specification Check - naming conventions, DML/DDL best practices, Spark-specific rules
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

from spark_sql_tokenizer import tokenize, TokenType
from spark_sql_parser import parse_sql
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


class SparkSQLChecker:
    """
    MRS Spark SQL Check Engine

    Performs syntax, specification, and interception checks on Spark SQL statements.
    """

    # Spark data sources (native) + Hive-compat storage formats
    VALID_DATA_SOURCES = {
        # Spark native data sources
        "PARQUET", "ORC", "JSON", "CSV", "TEXT", "JDBC", "AVRO",
        "DELTA", "LIBSVM", "BINARYFILE",
        # Hive-compat formats (supported via Spark SQL Hive integration)
        "TEXTFILE", "SEQUENCEFILE", "RCFILE",
        "ORCFILE",
        "INPUTFORMAT", "ORG.APACHE.HADOOP.HIVE.QL.IO.ORC.ORCINPUTFORMAT",
        "CUSTOMTEXTSERDE",
    }

    # Spark data types
    NUMERIC_TYPES = {
        "TINYINT", "SMALLINT", "INT", "INTEGER", "BIGINT",
        "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC",
        "SHORT", "LONG", "BYTE",
    }
    DATE_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMP_NTZ", "TIMESTAMP_LTZ", "INTERVAL"}
    STRING_TYPES = {"STRING", "VARCHAR", "CHAR"}

    def __init__(self, sql_text, check_mode="all"):
        self.sql_text = sql_text.strip()
        self.check_mode = check_mode  # syntax, spec, all
        self.violations = []
        self.parse_result = None
        self.tokens = []
        # Infer partitioned tables from the SQL text itself
        self._partitioned_tables = self._infer_partitioned_tables()

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
            self._check_interception(self.tokens)

        # Step 4: Generate report
        return self._generate_report()

    # ============================================================
    # Syntax Checks (SYN-ERR, SYN001-SYN020)
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
                if isinstance(part_by, str):
                    stripped = part_by.strip("() \t\n")
                    if not stripped:
                        self.violations.append(Violation(
                            rule_id="SYN005",
                            rule_name="PARTITIONED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="PARTITIONED BY 定义为空或语法无效",
                            fix_suggestion="添加分区字段，如 PARTITIONED BY (dt)",
                        ))
                elif isinstance(part_by, dict):
                    if not part_by.get("columns"):
                        self.violations.append(Violation(
                            rule_id="SYN005",
                            rule_name="PARTITIONED BY 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message="PARTITIONED BY 定义为空或语法无效",
                            fix_suggestion="添加分区字段，如 PARTITIONED BY (dt)",
                        ))

        # SYN006: CLUSTERED BY syntax check (Hive-compat, kept for Spark Hive integration)
        if ast and ast.get("node_type") == "CreateStmt":
            clustered = ast.get("clustered_by")
            if clustered:
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

        # SYN007: STORED AS / USING syntax check
        if ast and ast.get("node_type") == "CreateStmt":
            # Check STORED AS (Hive-compat)
            stored_as = ast.get("stored_as")
            if stored_as:
                fmt = stored_as.upper().strip("'\"")
                if fmt and fmt not in self.VALID_DATA_SOURCES and not stored_as.upper().startswith("INPUTFORMAT"):
                    self.violations.append(Violation(
                        rule_id="SYN007",
                        rule_name="STORED AS 语法错误",
                        level="ERROR",
                        category="语法检查",
                        message=f"无效的存储格式 '{stored_as}'",
                        fix_suggestion="使用 PARQUET/ORC/JSON/CSV/TEXT/AVRO/DELTA 或 Hive 兼容格式",
                    ))
            # Check USING (Spark native)
            using = ast.get("using")
            if using:
                src = using.upper().strip("'\"")
                if src and src not in self.VALID_DATA_SOURCES:
                    self.violations.append(Violation(
                        rule_id="SYN007",
                        rule_name="USING 数据源错误",
                        level="ERROR",
                        category="语法检查",
                        message=f"无效的数据源 '{using}'",
                        fix_suggestion="使用 PARQUET/ORC/JSON/CSV/TEXT/JDBC/AVRO/DELTA/LIBSVM/BINARYFILE",
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
        if ast and ast.get("node_type") == "CreateStmt":
            # For Spark: USING clause provides schema externally, like Hive's STORED BY
            has_external_schema = (
                ast.get("using") or
                ast.get("tblproperties") or
                ast.get("row_format") or
                ast.get("stored_by")
            )
            if not ast.get("columns") and not ast.get("as_select") and \
               not ast.get("like_table") and not has_external_schema:
                self.violations.append(Violation(
                    rule_id="SYN012",
                    rule_name="CREATE TABLE 结构错误",
                    level="ERROR",
                    category="语法检查",
                    message="CREATE TABLE 缺少列定义、AS SELECT 子句或 USING 数据源",
                    fix_suggestion="添加列定义、使用 CREATE TABLE ... AS SELECT 语法，"
                                   "或指定 USING 数据源 / TBLPROPERTIES 定义外部 schema",
                ))

        # SYN013: ALTER TABLE syntax check
        if ast and ast.get("node_type") == "AlterStmt":
            action = ast.get("action", "").upper()
            valid_actions = {
                "ADD", "DROP", "RENAME", "SET", "UNSET",
                "CHANGE", "REPLACE", "RECOVER",
            }
            if action and action not in valid_actions:
                self.violations.append(Violation(
                    rule_id="SYN013",
                    rule_name="ALTER TABLE 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"无效的 ALTER TABLE 操作 '{action}'",
                    fix_suggestion="支持的操作: ADD/DROP/RENAME/SET/UNSET/CHANGE/REPLACE/RECOVER PARTITIONS",
                ))

        # SYN014: MERGE statement syntax check (Spark 3.x supports MERGE)
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

        # SYN016: USING clause syntax check
        if ast and ast.get("node_type") == "CreateStmt":
            using = ast.get("using")
            if using and not isinstance(using, str):
                self.violations.append(Violation(
                    rule_id="SYN016",
                    rule_name="USING 子句语法错误",
                    level="ERROR",
                    category="语法检查",
                    message="USING 后需要指定数据源名称",
                    fix_suggestion="使用 USING parquet/orc/json/csv/text/jdbc/avro/delta 等",
                ))

        # SYN017: OPTIONS clause syntax check
        if ast and ast.get("node_type") == "CreateStmt":
            options = ast.get("options")
            if options and not isinstance(options, dict):
                self.violations.append(Violation(
                    rule_id="SYN017",
                    rule_name="OPTIONS 子句语法错误",
                    level="ERROR",
                    category="语法检查",
                    message="OPTIONS 子句格式无效，应为 OPTIONS (key 'value', ...)",
                    fix_suggestion="使用 OPTIONS (key1 'value1', key2 'value2') 格式",
                ))

        # SYN018: CACHE TABLE syntax check
        if ast and ast.get("node_type") == "CacheStmt":
            if not (ast.get("table_name") or ast.get("table")):
                self.violations.append(Violation(
                    rule_id="SYN018",
                    rule_name="CACHE TABLE 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message="CACHE TABLE 缺少表名或查询语句",
                    fix_suggestion="使用 CACHE TABLE table_name 或 CACHE TABLE query_name AS SELECT ...",
                ))

        # SYN019: REFRESH syntax check
        if ast and ast.get("node_type") == "RefreshStmt":
            if not ast.get("target"):
                self.violations.append(Violation(
                    rule_id="SYN019",
                    rule_name="REFRESH 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message="REFRESH 缺少目标表名或函数名",
                    fix_suggestion="使用 REFRESH TABLE table_name 或 REFRESH FUNCTION func_name",
                ))

        # SYN020: ADD/LIST JAR syntax check
        if ast and ast.get("node_type") in ("AddJarStmt", "ListJarStmt"):
            if not ast.get("path") and ast.get("node_type") == "AddJarStmt":
                self.violations.append(Violation(
                    rule_id="SYN020",
                    rule_name="ADD JAR 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message="ADD JAR 缺少 JAR 路径",
                    fix_suggestion="使用 ADD JAR /path/to/file.jar",
                ))

    # ============================================================
    # Specification Checks (SPEC001-SPEC029)
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
            col_names = self._get_column_names(ast)
            for col_name in col_names:
                if col_name and is_reserved_keyword(col_name):
                    self.violations.append(Violation(
                        rule_id="SPEC009",
                        rule_name="保留关键字用作标识符",
                        level="ERROR",
                        category="命名规范",
                        message=f"字段名 '{col_name}' 是 Spark SQL 保留关键字，可能导致语法歧义",
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
                        fix_suggestion="字段名不超过30个字符",
                    ))
                    break

        # SPEC012: FLOAT/DOUBLE for money
        if ast and ast.get("node_type") == "CreateStmt":
            col_defs = self._get_column_defs(ast)
            money_hints = ("amount", "price", "fee", "salary", "money",
                           "cost", "pay", "income", "revenue")
            for col_name, col_type in col_defs:
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
            columns = ast.get("columns", "")
            col_count = 0
            if isinstance(columns, str):
                col_count = columns.count(",") + 1
            elif isinstance(columns, list):
                col_count = len(columns)
            if col_count > 100:
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC013",
                    rule_name="字段数量过多",
                    level="WARNING",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 有 {col_count} 个字段，超过100个字段",
                    fix_suggestion="每个表字段个数不建议超过100个",
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
                    fix_suggestion="建表分区字段不超过3个",
                ))

        # SPEC015: Missing column comment
        if ast and ast.get("node_type") == "CreateStmt":
            columns = ast.get("columns", "")
            if isinstance(columns, str):
                col_count = columns.count(",") + 1
                comment_count = columns.upper().count("COMMENT")
                if comment_count < col_count:
                    cols_without_comment = col_count - comment_count
                    table_name = ast.get("table_name", "unknown")
                    self.violations.append(Violation(
                        rule_id="SPEC015",
                        rule_name="字段缺少注释",
                        level="INFO",
                        category="对象设计规范",
                        message=f"表 '{table_name}' 有 {cols_without_comment} 个字段缺少注释",
                        fix_suggestion="所有字段都应根据字段的作用添加注释",
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

        # SPEC003: Cartesian product / Old-style join
        if ast and ast.get("node_type") == "SelectStmt":
            cartesian_result = self._has_cartesian_product(tokens)
            if cartesian_result == "cartesian":
                self.violations.append(Violation(
                    rule_id="SPEC003",
                    rule_name="笛卡尔积",
                    level="ERROR",
                    category="数据操作规范",
                    message="多表查询缺少 JOIN 条件，将产生笛卡尔积",
                    fix_suggestion="使用显式 JOIN 语法并指定 ON 条件",
                ))
            elif cartesian_result == "old_style_join":
                self.violations.append(Violation(
                    rule_id="SPEC003",
                    rule_name="旧式逗号JOIN",
                    level="WARNING",
                    category="数据操作规范",
                    message="使用旧式逗号JOIN（FROM t1, t2 WHERE ...），可能导致笛卡尔积",
                    fix_suggestion="改为标准JOIN语法：FROM t1 JOIN t2 ON t1.col = t2.col",
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
                level="ERROR",
                category="数据操作规范",
                message="WHERE 条件中对分区字段使用函数，导致无法使用分区裁剪",
                fix_suggestion="使用范围条件替代函数，如 WHERE dt >= '20240501' AND dt < '20240601'",
            ))

        # SPEC007: INSERT missing column list
        if ast and ast.get("node_type") == "InsertStmt":
            if not ast.get("columns") and not ast.get("is_overwrite"):
                self.violations.append(Violation(
                    rule_id="SPEC007",
                    rule_name="INSERT 缺少列列表",
                    level="INFO",
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
                fix_suggestion="CASE WHEN 必须加 ELSE",
            ))

        # SPEC017: NULL value handling
        if self._has_null_handling_risk(tokens):
            self.violations.append(Violation(
                rule_id="SPEC017",
                rule_name="NULL 值处理风险",
                level="WARNING",
                category="数据操作规范",
                message="条件判断中未考虑 NULL 对结果的影响",
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
                fix_suggestion="使用 NULL 关键字替代字符串 'NULL'",
            ))

        # SPEC019: JOIN field type mismatch
        if self._has_join_type_mismatch(tokens):
            self.violations.append(Violation(
                rule_id="SPEC019",
                rule_name="关联字段类型不一致",
                level="WARNING",
                category="数据操作规范",
                message="JOIN 关联字段类型可能不一致，导致隐式转换",
                fix_suggestion="确保关联字段类型一致，使用显式类型转换",
            ))

        # ---- SQL Development Rules ----

        # SPEC020: INSERT INTO VALUES
        if self._has_insert_values(tokens):
            self.violations.append(Violation(
                rule_id="SPEC020",
                rule_name="避免 INSERT INTO VALUES",
                level="INFO",
                category="SQL开发规范",
                message="INSERT INTO VALUES 效率低，建议使用 INSERT SELECT",
                fix_suggestion="使用 INSERT INTO ... SELECT 替代",
            ))

        # SPEC021: Subquery nesting depth
        if self._get_subquery_depth(tokens) > 3:
            self.violations.append(Violation(
                rule_id="SPEC021",
                rule_name="子查询嵌套过深",
                level="WARNING",
                category="SQL开发规范",
                message="子查询嵌套超过3层，建议拆分为中间表",
                fix_suggestion="子查询不超过3层，拆分为多层中间表",
            ))

        # SPEC022: Partition pruning missing
        if self._has_partition_table_without_filter(tokens):
            self.violations.append(Violation(
                rule_id="SPEC022",
                rule_name="缺少分区裁剪",
                level="INFO",
                category="数据操作规范",
                message="分区表查询未使用分区过滤条件，将导致全分区扫描",
                fix_suggestion="添加分区过滤条件，如 WHERE dt='20240501'",
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

        # SPEC025: Prefer USING over STORED AS (Spark-specific)
        if ast and ast.get("node_type") == "CreateStmt":
            if ast.get("stored_as") and not ast.get("using"):
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC025",
                    rule_name="优先使用 USING 替代 STORED AS",
                    level="WARNING",
                    category="SQL开发规范",
                    message=f"表 '{table_name}' 使用 STORED AS（Hive 兼容语法），建议使用 Spark 原生 USING 语法",
                    fix_suggestion="将 STORED AS ORC 改为 USING ORC，或使用 CREATE TABLE ... USING parquet",
                ))

        # SPEC026: CACHE TABLE recommendation for repeated access
        if self._has_repeated_table_access(tokens):
            if not self._has_cache_table(tokens):
                self.violations.append(Violation(
                    rule_id="SPEC026",
                    rule_name="重复访问表建议使用 CACHE",
                    level="INFO",
                    category="SQL开发规范",
                    message="同一表在查询中被多次引用，建议使用 CACHE TABLE 缓存以提升性能",
                    fix_suggestion="在查询前使用 CACHE TABLE table_name 或 CACHE LAZY TABLE table_name",
                ))

        # SPEC027: Broadcast join hint for small tables
        if self._has_broadcast_opportunity(tokens):
            if not self._has_broadcast_hint(tokens):
                self.violations.append(Violation(
                    rule_id="SPEC027",
                    rule_name="建议使用 BROADCAST hint",
                    level="INFO",
                    category="SQL开发规范",
                    message="大小表 JOIN 时建议使用 /*+ BROADCAST(small_table) */ 优化 shuffle",
                    fix_suggestion="使用 /*+ BROADCAST(small_table) */ 提示优化 join 策略",
                ))

        # SPEC028: DROP without IF EXISTS
        if self._has_drop_without_if_exists(tokens):
            self.violations.append(Violation(
                rule_id="SPEC028",
                rule_name="DROP 缺少 IF EXISTS",
                level="WARNING",
                category="SQL开发规范",
                message="DROP 语句未使用 IF EXISTS，对象不存在时会报错",
                fix_suggestion="使用 DROP TABLE IF EXISTS / DROP VIEW IF EXISTS",
            ))

        # SPEC029: ADD JAR usage warning
        if self._has_add_jar(tokens):
            self.violations.append(Violation(
                rule_id="SPEC029",
                rule_name="ADD JAR 使用警告",
                level="INFO",
                category="SQL开发规范",
                message="ADD JAR 仅在当前 Session 有效，建议使用 --jars 参数或在 Spark 配置中注册",
                fix_suggestion="使用 spark-submit --jars 或 spark.jars 配置项替代 ADD JAR",
            ))

    # ============================================================
    # Large SQL Interception Checks (INTERCEPT001-INTERCEPT006)
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

        # INTERCEPT006: SQL length over limit
        sql_len = len(self.sql_text)
        if sql_len > 10240:  # 10KB
            self.violations.append(Violation(
                rule_id="INTERCEPT006",
                rule_name="SQL 语句长度超限",
                level="WARNING",
                category="大SQL拦截",
                message=f"SQL 字符串长度 {sql_len} 字节，超过阈值10KB",
                fix_suggestion="将复杂 SQL 拆分为多个简单 SQL 或使用中间表",
            ))

    # ============================================================
    # Pattern Detection Helpers
    # ============================================================

    def _is_valid_naming(self, name):
        """Check if name follows naming convention (lowercase + underscore)"""
        if not name:
            return True
        name = name.strip('`')
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
        segments = []
        current = []
        depth = 0
        for ch in columns_str:
            if ch == '(':
                depth += 1
                current.append(ch)
            elif ch == ')':
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
            segments = columns.split(",")
            for seg in segments:
                seg = seg.strip()
                m = re.match(r'^(\w+)\s+(\w+(?:\s*\([^)]*\))?)', seg)
                if m:
                    result.append((m.group(1), m.group(2).upper()))
        elif isinstance(columns, list):
            for col in columns:
                if isinstance(col, dict):
                    result.append((col.get("name", ""), col.get("type", "").upper()))
        return result

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
            "cartesian": comma tables with NO join condition in WHERE
            "old_style_join": comma tables with join condition in WHERE
        """
        in_from = False
        has_comma_table = False
        has_where = False
        has_where_join_explicit = False
        has_where_join_bare = False
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

            if tokens[i].type == TokenType.LPAREN:
                paren_depth += 1
            elif tokens[i].type == TokenType.RPAREN:
                paren_depth = max(0, paren_depth - 1)
                if paren_depth == 0:
                    in_from = False

            if in_from and paren_depth == 0 and tokens[i].type == TokenType.COMMA:
                has_comma_table = True

            if has_where and paren_depth == 0 and \
               tokens[i].type == TokenType.CMP_OP and tokens[i].value == "=":
                # Pattern 1: table.col = table.col
                if i >= 3 and i + 2 < len(tokens):
                    left_is_tablecol = (tokens[i - 3].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT)
                                         and tokens[i - 2].type == TokenType.DOT)
                    right_is_tablecol = (tokens[i + 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT)
                                          and tokens[i + 2].type == TokenType.DOT)
                    if left_is_tablecol and right_is_tablecol:
                        has_where_join_explicit = True

                # Pattern 2: bare col = col
                left_is_col = False
                right_is_col = False

                if i >= 1:
                    if i >= 2 and tokens[i - 2].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) \
                            and tokens[i - 1].type == TokenType.DOT:
                        left_is_col = True
                    elif i >= 2 and tokens[i - 2].type == TokenType.DOT \
                            and tokens[i - 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        left_is_col = True
                    elif tokens[i - 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        if i < 2 or tokens[i - 2].type != TokenType.DOT:
                            left_is_col = True

                if i + 1 < len(tokens):
                    if i + 3 < len(tokens) and tokens[i + 1].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT) \
                            and tokens[i + 2].type == TokenType.DOT \
                            and tokens[i + 3].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        right_is_col = True
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
            return "old_style_join"
        else:
            return "old_style_join"

    def _has_partition_field_function(self, tokens):
        """Check for function on partition field in WHERE"""
        in_where = False
        partition_fields = self._detect_partition_fields(tokens)
        func_names = ("SUBSTR", "SUBSTRING", "TRIM", "UPPER", "LOWER", "CONCAT",
                      "REPLACE", "LENGTH", "DATE_FORMAT", "YEAR", "MONTH", "DAY",
                      "HOUR", "MINUTE", "SECOND", "TO_DATE", "DATE_TRUNC")

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
                            depth += 1
                    j += 1
            i += 1
        return False

    def _has_null_handling_risk(self, tokens):
        """Check for NULL handling risk in conditions"""
        in_where = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("WHERE"):
                in_where = True
            elif tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or \
                 tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT"):
                in_where = False

            if in_where and tokens[i].type == TokenType.CMP_OP:
                if tokens[i].value in ("<>", "!=", "<=>"):
                    if i + 1 < len(tokens):
                        right = tokens[i + 1]
                        if right.type == TokenType.SCONST and \
                           right.value.strip("'\"").upper() not in ("NULL",):
                            return True
            i += 1
        return False

    def _has_string_null(self, tokens):
        """Check for string 'NULL'/'null' usage"""
        for t in tokens:
            if t.type == TokenType.SCONST:
                val = t.value.strip("'\"")
                if val.upper() == "NULL" and val != "NULL":
                    return True
                if val == "NULL":
                    return True
        return False

    def _has_join_type_mismatch(self, tokens):
        """Heuristic check for JOIN field type mismatch"""
        in_join_on = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("ON"):
                in_join_on = True
            elif tokens[i].is_keyword("AND") and in_join_on:
                pass
            elif tokens[i].is_keyword("WHERE") or tokens[i].is_keyword("JOIN") or \
                 tokens[i].is_keyword("LEFT") or tokens[i].is_keyword("RIGHT") or \
                 tokens[i].is_keyword("INNER") or tokens[i].is_keyword("FULL"):
                in_join_on = False

            if in_join_on and tokens[i].type == TokenType.CMP_OP and tokens[i].value == "=":
                if i > 0 and i + 1 < len(tokens):
                    left = tokens[i - 1]
                    right = tokens[i + 1]
                    if (left.type == TokenType.SCONST and right.type in (TokenType.ICONST, TokenType.FCONST)) or \
                       (left.type in (TokenType.ICONST, TokenType.FCONST) and right.type == TokenType.SCONST):
                        return True
            i += 1
        return False

    def _infer_partitioned_tables(self):
        """Infer partitioned table names from the SQL text itself."""
        partitioned = set()
        try:
            tokens, _ = tokenize(self.sql_text)
        except Exception:
            return partitioned

        i = 0
        while i < len(tokens):
            t = tokens[i]

            # Pattern 1: CREATE TABLE <name> ... PARTITIONED BY ...
            if t.is_keyword("CREATE") and i + 2 < len(tokens) and tokens[i + 1].is_keyword("TABLE"):
                name_idx = i + 2
                while name_idx < len(tokens) and tokens[name_idx].is_keyword() and \
                        tokens[name_idx].value.upper() in ("EXTERNAL", "TEMPORARY", "MANAGED", "OR", "REPLACE", "GLOBAL"):
                    name_idx += 1
                if name_idx < len(tokens) and tokens[name_idx].type in (
                        TokenType.IDENT, TokenType.BACKTICK_IDENT):
                    table_name = tokens[name_idx].value.strip('`').lower()
                    for j in range(name_idx + 1, min(name_idx + 50, len(tokens))):
                        if tokens[j].is_keyword("PARTITIONED"):
                            partitioned.add(table_name)
                            break
                        if tokens[j].value == ';':
                            break

            # Pattern 2: INSERT INTO/OVERWRITE <table> PARTITION(...)
            elif t.is_keyword("INSERT") and i + 2 < len(tokens):
                ins_idx = i + 1
                if tokens[ins_idx].is_keyword("INTO") or tokens[ins_idx].is_keyword("OVERWRITE"):
                    tbl_idx = ins_idx + 1
                    if tbl_idx < len(tokens) and tokens[tbl_idx].is_keyword("TABLE"):
                        tbl_idx += 1
                    if tbl_idx < len(tokens) and tokens[tbl_idx].type in (
                            TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        table_name = tokens[tbl_idx].value.strip('`').lower()
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

    def _extract_from_tables(self, tokens):
        """Extract table names from FROM and JOIN clauses."""
        tables = set()
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.is_keyword("FROM") or t.is_keyword("JOIN"):
                j = i + 1
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
        """Check for partitioned table query without partition filter."""
        if not self._partitioned_tables:
            return False

        from_tables = self._extract_from_tables(tokens)
        queried_partitioned = from_tables & self._partitioned_tables
        if not queried_partitioned:
            return False

        partition_fields = self._extract_partition_fields(tokens)
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
        """Extract partition column names from PARTITIONED BY clauses."""
        fields = set()
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
                            if not tokens[j].is_keyword():
                                fields.add(tokens[j].value.strip('`').lower())
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

    def _has_lateral_view(self, tokens):
        """Check if LATERAL VIEW exists"""
        for i, t in enumerate(tokens):
            if t.is_keyword("LATERAL") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("VIEW") or tokens[i + 1].is_keyword("TABLE"):
                    return True
        return False

    def _validate_lateral_view(self, tokens):
        """Validate LATERAL VIEW syntax structure."""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("LATERAL") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("VIEW"):
                    j = i + 2
                    if j < len(tokens) and tokens[j].is_keyword("OUTER"):
                        j += 1
                    if j >= len(tokens) or tokens[j].type not in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        return False
                    j += 1
                    if j >= len(tokens) or tokens[j].type != TokenType.LPAREN:
                        return False
                    depth = 0
                    while j < len(tokens):
                        if tokens[j].type == TokenType.LPAREN:
                            depth += 1
                        elif tokens[j].type == TokenType.RPAREN:
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    j += 1
                    if j < len(tokens) and tokens[j].type in (TokenType.IDENT, TokenType.BACKTICK_IDENT):
                        return True
                    return False
            i += 1
        return True

    def _has_repeated_table_access(self, tokens):
        """Check if the same table is referenced multiple times in FROM/JOIN"""
        table_counts = {}
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("FROM") or tokens[i].is_keyword("JOIN"):
                j = i + 1
                _qualifiers = {"LEFT", "RIGHT", "OUTER", "INNER", "FULL", "CROSS", "SEMI", "ANTI"}
                while j < len(tokens) and tokens[j].is_keyword() and \
                        tokens[j].value.upper() in _qualifiers:
                    j += 1
                if j < len(tokens) and tokens[j].type in (
                        TokenType.IDENT, TokenType.BACKTICK_IDENT):
                    tbl = tokens[j].value.strip('`').lower()
                    table_counts[tbl] = table_counts.get(tbl, 0) + 1
            i += 1
        return any(c >= 3 for c in table_counts.values())

    def _has_cache_table(self, tokens):
        """Check if CACHE TABLE is used"""
        for t in tokens:
            if t.is_keyword("CACHE"):
                return True
        return False

    def _has_broadcast_opportunity(self, tokens):
        """Heuristic: detect large-small table join patterns"""
        # Check if there are multiple joins with different tables
        tables_in_joins = []
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("JOIN"):
                j = i + 1
                _qualifiers = {"LEFT", "RIGHT", "OUTER", "INNER", "FULL", "CROSS", "SEMI", "ANTI"}
                while j < len(tokens) and tokens[j].is_keyword() and \
                        tokens[j].value.upper() in _qualifiers:
                    j += 1
                if j < len(tokens) and tokens[j].type in (
                        TokenType.IDENT, TokenType.BACKTICK_IDENT):
                    tables_in_joins.append(tokens[j].value.strip('`').lower())
            i += 1
        # If there are at least 2 joins, there may be a broadcast opportunity
        return len(tables_in_joins) >= 2

    def _has_broadcast_hint(self, tokens):
        """Check if BROADCAST hint is used"""
        for t in tokens:
            if t.type == TokenType.HINT:
                hint_upper = t.value.upper()
                if "BROADCAST" in hint_upper:
                    return True
        return False

    def _has_add_jar(self, tokens):
        """Check if ADD JAR is used"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("ADD") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("JAR"):
                    return True
            i += 1
        return False

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

        total_rules = 56  # 20 syntax + 29 spec + 7 interception (approx)
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
        lines.append("# MRS Spark SQL 检查报告")
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
        display_sql = self.sql_text
        if len(display_sql) > 2000:
            display_sql = display_sql[:2000] + "\n... (truncated)"
        lines.append(display_sql)
        lines.append("```")

        return '\n'.join(lines)


def check_sql(sql_text, check_mode="all"):
    """
    Convenience function to check SQL text.

    Args:
        sql_text: SQL text to check
        check_mode: "syntax", "spec", or "all"

    Returns:
        dict: Check report
    """
    checker = SparkSQLChecker(sql_text, check_mode=check_mode)
    return checker.check()


def check_sql_markdown(sql_text, check_mode="all"):
    """
    Check SQL and return Markdown report.

    Args:
        sql_text: SQL text to check
        check_mode: "syntax", "spec", or "all"

    Returns:
        str: Markdown report
    """
    checker = SparkSQLChecker(sql_text, check_mode=check_mode)
    return checker.generate_markdown_report()


# ---- CLI Entry Point ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python spark_sql_checker.py <sql_text_or_file> [syntax|spec|all]")
        sys.exit(1)

    input_text = sys.argv[1]
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    checker = SparkSQLChecker(input_text, check_mode=mode)
    report = checker.check()

    print(json.dumps(report, indent=2, ensure_ascii=False))
