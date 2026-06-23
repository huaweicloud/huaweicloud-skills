# -*- coding: utf-8 -*-
"""
DWS SQL Checker Engine
Integrates tokenizer, parser, and rule-based checking.

Supports two modes:
1. Syntax Check - keyword validation, structure validation, DWS syntax compatibility
2. Specification Check - naming conventions, DML/DDL best practices, DWS-specific rules
"""

import sys
import os
import json
import re
from datetime import datetime

_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_this_dir, '..', 'rules'))
sys.path.insert(0, _this_dir)

from dws_sql_tokenizer import tokenize, TokenType
from dws_sql_parser import parse_sql
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


class DWSSQLChecker:
    """
    DWS SQL Check Engine

    Performs syntax and specification checks on SQL statements.
    """

    def __init__(self, sql_text, check_mode="all"):
        self.sql_text = sql_text.strip()
        self.check_mode = check_mode  # syntax, spec, all
        self.violations = []
        self.parse_result = None

    def check(self):
        """Run all checks and return the report"""
        # Step 1: Tokenize
        tokens, token_errors = tokenize(self.sql_text)

        # Step 2: Parse
        self.parse_result = parse_sql(self.sql_text)

        # Step 3: Run checks based on mode
        if self.check_mode in ("syntax", "all"):
            self._check_syntax(tokens, token_errors)

        if self.check_mode in ("spec", "all"):
            self._check_specification(tokens)

        # Step 4: Generate report
        return self._generate_report()

    # ============================================================
    # Syntax Checks
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
            ))

        # SYN001: Check for invalid keyword usage (keywords not in DWS)
        for t in tokens:
            if t.type == TokenType.IDENT:
                upper = t.value.upper()
                # Check if it looks like a keyword but isn't in DWS
                # Common non-DWS keywords that users might try
                pass  # DWS supports most SQL keywords

        # SYN002: Reserved keyword used as identifier
        for t in tokens:
            if t.type == TokenType.IDENT:
                # Check if it's a reserved keyword used without quoting
                if is_reserved_keyword(t.value):
                    self.violations.append(Violation(
                        rule_id="SYN002",
                        rule_name="保留关键字用作标识符",
                        level="ERROR",
                        category="语法检查",
                        message=f"保留关键字 '{t.value}' 不能用作标识符，请使用双引号引用",
                        line=t.line,
                        column=t.column,
                        sql_snippet=self._get_snippet(t.line, t.column),
                        fix_suggestion=f'使用 "{t.value}" 替代 {t.value}',
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
            ))

        # SYN005: DISTRIBUTE BY syntax check
        ast = self.parse_result.get("ast", {})
        if ast and ast.get("node_type") == "CreateStmt":
            dist_type = ast.get("distribute_type")
            if dist_type and dist_type not in ("HASH", "MODULO", "REPLICATION", "ROUNDROBIN"):
                self.violations.append(Violation(
                    rule_id="SYN005",
                    rule_name="DISTRIBUTE BY 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"无效的分布策略 '{dist_type}'，有效值为 HASH/MODULO/REPLICATION/ROUNDROBIN",
                    fix_suggestion="使用 DISTRIBUTE BY HASH(col) / MODULO(col) / REPLICATION / ROUNDROBIN",
                ))

        # SYN007: MERGE statement structure check
        if ast and ast.get("node_type") == "MergeStmt":
            when_clauses = ast.get("when_clauses", [])
            if not when_clauses:
                self.violations.append(Violation(
                    rule_id="SYN007",
                    rule_name="MERGE 语句缺少 WHEN 子句",
                    level="ERROR",
                    category="语法检查",
                    message="MERGE 语句必须至少包含一个 WHEN MATCHED 或 WHEN NOT MATCHED 子句",
                    fix_suggestion="添加 WHEN MATCHED THEN UPDATE/DELETE 或 WHEN NOT MATCHED THEN INSERT 子句",
                ))

    # ============================================================
    # Specification Checks
    # ============================================================

    def _check_specification(self, tokens):
        """Run specification-level checks"""

        ast = self.parse_result.get("ast", {})
        stmt_type = self.parse_result.get("statement_type", "")

        # ---- Object Design Rules ----

        # SPEC001: CREATE TABLE missing DISTRIBUTE BY
        if ast and ast.get("node_type") == "CreateStmt":
            if "distribute_type" not in ast:
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC001",
                    rule_name="CREATE TABLE 缺少 DISTRIBUTE BY",
                    level="ERROR",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 未指定分布策略，可能导致数据分布不均",
                    fix_suggestion="添加 DISTRIBUTE BY HASH(分布键) / REPLICATION / ROUNDROBIN",
                ))

            # SPEC002: CREATE TABLE missing primary key
            if not ast.get("has_primary_key"):
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC002",
                    rule_name="CREATE TABLE 缺少主键",
                    level="INFO",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 未定义主键约束",
                    fix_suggestion="添加 PRIMARY KEY 约束以确保数据唯一性",
                ))

        # ---- Data Operation Rules ----

        # SPEC003: SELECT * prohibited
        if ast and ast.get("node_type") == "SelectStmt":
            if ast.get("has_select_star"):
                self.violations.append(Violation(
                    rule_id="SPEC003",
                    rule_name="禁止使用 SELECT *",
                    level="ERROR",
                    category="数据操作规范",
                    message="查询使用了 SELECT *，应明确指定字段列表",
                    fix_suggestion="将 SELECT * 替换为具体的字段列表",
                ))

        # SPEC004: DELETE/UPDATE without WHERE
        if ast and ast.get("node_type") in ("DeleteStmt", "UpdateStmt"):
            if ast.get("missing_where"):
                stmt_keyword = "DELETE" if ast.get("node_type") == "DeleteStmt" else "UPDATE"
                table_name = ast.get("table", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC004",
                    rule_name=f"{stmt_keyword} 缺少 WHERE 条件",
                    level="ERROR",
                    category="数据操作规范",
                    message=f"{stmt_keyword} 语句缺少 WHERE 条件，将影响全表数据",
                    fix_suggestion=f"添加 WHERE 条件限制 {stmt_keyword} 操作范围",
                ))

        # SPEC005: NOT IN subquery
        if self._has_not_in_subquery(tokens):
            self.violations.append(Violation(
                rule_id="SPEC005",
                rule_name="NOT IN 子查询性能风险",
                level="WARNING",
                category="数据操作规范",
                message="NOT IN 子查询可能导致性能问题，建议改用 NOT EXISTS 或 LEFT JOIN",
                fix_suggestion="将 NOT IN (SELECT ...) 改写为 NOT EXISTS (SELECT ...) 或 LEFT JOIN ... IS NULL",
            ))

        # SPEC006: DISTINCT in SELECT (potential performance issue)
        if ast and ast.get("node_type") == "SelectStmt" and ast.get("distinct"):
            self.violations.append(Violation(
                rule_id="SPEC006",
                rule_name="DISTINCT 可能影响性能",
                level="INFO",
                category="数据操作规范",
                message="使用 DISTINCT 会导致排序去重，大数据量下可能影响性能",
                fix_suggestion="考虑使用 GROUP BY 替代 DISTINCT，或确保查询结果本身已唯一",
            ))

        # SPEC007: Implicit type conversion risk
        if self._has_implicit_type_risk(tokens):
            self.violations.append(Violation(
                rule_id="SPEC007",
                rule_name="隐式类型转换风险",
                level="WARNING",
                category="数据操作规范",
                message="WHERE 条件中可能存在隐式类型转换，导致索引失效",
                fix_suggestion="确保比较操作两侧的数据类型一致，使用显式类型转换",
            ))

        # SPEC008: LIKE with leading wildcard
        if self._has_leading_wildcard_like(tokens):
            self.violations.append(Violation(
                rule_id="SPEC008",
                rule_name="LIKE 前缀通配符导致全表扫描",
                level="WARNING",
                category="数据操作规范",
                message="LIKE '%...' 模式无法使用索引，将导致全表扫描",
                fix_suggestion="避免使用前缀通配符，或考虑全文检索",
            ))

        # SPEC009: OR condition may cause performance issue
        if self._has_or_condition_issue(tokens):
            self.violations.append(Violation(
                rule_id="SPEC009",
                rule_name="OR 条件可能导致性能问题",
                level="INFO",
                category="数据操作规范",
                message="OR 条件可能导致查询优化器无法选择最优执行计划",
                fix_suggestion="考虑将 OR 改写为 UNION ALL，或使用 IN 子句",
            ))

        # SPEC010: Large IN list
        if self._has_large_in_list(tokens):
            self.violations.append(Violation(
                rule_id="SPEC010",
                rule_name="IN 列表过长",
                level="WARNING",
                category="数据操作规范",
                message="IN 列表包含过多值，可能影响性能",
                fix_suggestion="将 IN 列表改写为临时表 JOIN 或子查询",
            ))

        # SPEC011: Subquery in FROM clause
        if ast and ast.get("node_type") == "SelectStmt":
            from_clause = ast.get("from_clause", [])
            for table in from_clause:
                if "SELECT" in str(table).upper():
                    self.violations.append(Violation(
                        rule_id="SPEC011",
                        rule_name="FROM 子句中的子查询",
                        level="INFO",
                        category="数据操作规范",
                        message="FROM 子句中使用子查询可能影响优化器生成最优计划",
                        fix_suggestion="考虑将子查询改写为 CTE (WITH 子句) 或临时表",
                    ))
                    break

        # SPEC012: Cartesian product (comma-separated tables without join condition)
        if ast and ast.get("node_type") == "SelectStmt":
            from_clause = ast.get("from_clause", [])
            if len(from_clause) > 1:
                has_join = any("JOIN" in str(t).upper() for t in from_clause)
                if not has_join and not ast.get("where_clause"):
                    self.violations.append(Violation(
                        rule_id="SPEC012",
                        rule_name="笛卡尔积风险",
                        level="ERROR",
                        category="数据操作规范",
                        message="多表查询缺少 JOIN 条件，可能产生笛卡尔积",
                        fix_suggestion="使用显式 JOIN 语法并指定 ON 条件",
                    ))

        # SPEC013: Oracle (+) outer join syntax
        for t in tokens:
            if t.type == TokenType.ORA_JOINOP:
                self.violations.append(Violation(
                    rule_id="SPEC013",
                    rule_name="Oracle 外连接语法",
                    level="INFO",
                    category="数据操作规范",
                    message="使用了 Oracle 风格的外连接运算符 (+)，建议使用标准 SQL JOIN 语法",
                    line=t.line,
                    column=t.column,
                    fix_suggestion="将 t1.id = t2.id(+) 改写为 t1 LEFT JOIN t2 ON t1.id = t2.id",
                ))
                break

        # SPEC014: INSERT without column list
        if ast and ast.get("node_type") == "InsertStmt":
            if not ast.get("columns") and not ast.get("default_values"):
                self.violations.append(Violation(
                    rule_id="SPEC014",
                    rule_name="INSERT 缺少列列表",
                    level="WARNING",
                    category="数据操作规范",
                    message="INSERT 语句未指定列列表，依赖列的默认顺序，可能导致兼容性问题",
                    fix_suggestion="添加列列表 INSERT INTO table (col1, col2, ...) VALUES ...",
                ))

        # SPEC015: CREATE TABLE without table comment
        if ast and ast.get("node_type") == "CreateStmt":
            if not ast.get("comment"):
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC015",
                    rule_name="CREATE TABLE 缺少表注释",
                    level="INFO",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 未添加注释",
                    fix_suggestion=f"添加 COMMENT '表用途说明'",
                ))

        # ============================================================
        # New rules from DWS Development Design Specification
        # ============================================================

        # SPEC023: Custom TABLESPACE (column-store v3 excluded)
        if ast and ast.get("node_type") == "CreateStmt":
            has_tablespace = self._has_keyword(tokens, "TABLESPACE")
            if has_tablespace:
                is_column_v3 = self._is_column_v3_table(tokens)
                if not is_column_v3:
                    table_name = ast.get("table_name", "unknown")
                    self.violations.append(Violation(
                        rule_id="SPEC023",
                        rule_name="自定义 TABLESPACE 需确认场景",
                        level="WARNING",
                        category="对象设计规范",
                        message=f"表 '{table_name}' 使用了自定义 TABLESPACE，分布式场景可能导致存储倾斜",
                        fix_suggestion="创建表对象使用内置默认表空间，列存v3表指定TABLESPACE除外",
                    ))

        # SPEC024: Missing explicit orientation
        if ast and ast.get("node_type") == "CreateStmt":
            with_options = ast.get("with_options", "")
            has_orientation = "orientation" in str(with_options).lower()
            if not has_orientation:
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC024",
                    rule_name="创建表建议显式指定存储方式",
                    level="WARNING",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 未显式指定存储方式(orientation)，建议明确指定行存或列存",
                    fix_suggestion="添加 WITH (orientation=row) 或 WITH (orientation=column)",
                ))

        # SPEC025: Row-store table with COMPRESS
        if ast and ast.get("node_type") == "CreateStmt":
            with_options = str(ast.get("with_options", "")).lower()
            has_compress = "compress" in with_options
            # Normalize spaces for comparison
            with_options_normalized = with_options.replace(" ", "")
            is_row_store = "orientation=row" in with_options_normalized or \
                           (has_compress and "orientation" not in with_options)
            if has_compress and is_row_store:
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC025",
                    rule_name="行存表禁止指定 compress 属性",
                    level="ERROR",
                    category="对象设计规范",
                    message=f"行存表 '{table_name}' 禁止指定 COMPRESS 属性，禁止使用行存压缩表",
                    fix_suggestion="行存表不要指定 COMPRESS 属性，如需压缩请使用列存表",
                ))

        # SPEC026: Missing partition (INFO suggestion)
        if ast and ast.get("node_type") == "CreateStmt":
            if not ast.get("partition") and not ast.get("partition_by") and not ast.get("has_partition"):
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC026",
                    rule_name="大表建议设计分区",
                    level="INFO",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 未设计分区，大表建议使用分区改善查询性能和数据治理效率",
                    fix_suggestion="添加 PARTITION BY RANGE(时间字段) 或 PARTITION BY LIST(枚举字段)",
                ))

        # SPEC027: Columns without NOT NULL (INFO)
        if ast and ast.get("node_type") == "CreateStmt":
            columns_raw = str(ast.get("columns", ""))
            # Heuristic: count commas as column count, check if NOT NULL appears
            if columns_raw and "NOT NULL" not in columns_raw.upper():
                table_name = ast.get("table_name", "unknown")
                self.violations.append(Violation(
                    rule_id="SPEC027",
                    rule_name="字段建议添加 NOT NULL 约束",
                    level="INFO",
                    category="对象设计规范",
                    message=f"表 '{table_name}' 的字段均未添加 NOT NULL 约束，优化器在特定场景可利用 NOT NULL 优化",
                    fix_suggestion="对明确不存在 NULL 值的字段添加 NOT NULL 约束",
                ))

        # SPEC028: SERIAL/BIGSERIAL/SMALLSERIAL usage
        if self._has_serial_type(tokens):
            self.violations.append(Violation(
                rule_id="SPEC028",
                rule_name="避免使用自增列或自增数据类型",
                level="WARNING",
                category="对象设计规范",
                message="自增序列(SERIAL/BIGSERIAL)在大量使用时会造成 GTM 压力过大及序列生成速度慢",
                fix_suggestion="使用 UUID 替代自增列，或必须使用时设置 CACHE（如 1000）降低 GTM 压力",
            ))

        # SPEC030: DROP without IF EXISTS
        if self._has_drop_without_if_exists(tokens):
            self.violations.append(Violation(
                rule_id="SPEC030",
                rule_name="DROP 操作建议使用 IF EXISTS",
                level="WARNING",
                category="SQL开发规范",
                message="DROP 操作未使用 IF EXISTS，对象不存在时将报错",
                fix_suggestion="使用 DROP ... IF EXISTS 避免对象不存在时报错",
            ))

        # SPEC031: INSERT with multiple VALUES groups
        if self._has_multi_values_insert(tokens):
            self.violations.append(Violation(
                rule_id="SPEC031",
                rule_name="INSERT 多 VALUES 建议使用 COPY 替代",
                level="WARNING",
                category="SQL开发规范",
                message="多 VALUES 批插场景解析耗时、耗资源，入库效率低",
                fix_suggestion="使用 COPY 类接口（如 JDBC 的 CopyManager）代替 INSERT VALUES",
            ))

        # SPEC035: Function on filter column
        if self._has_function_on_filter_column(tokens):
            self.violations.append(Violation(
                rule_id="SPEC035",
                rule_name="避免对过滤条件字段使用函数运算",
                level="WARNING",
                category="SQL开发规范",
                message="WHERE 条件中对字段使用函数运算，导致优化器无法获取准确的字段统计信息",
                fix_suggestion="只对常量列进行函数运算，字段列不进行函数运算",
            ))

        # SPEC036: COUNT(*) on row-store table
        if self._has_count_star(tokens):
            self.violations.append(Violation(
                rule_id="SPEC036",
                rule_name="禁止对行存大表频繁 COUNT",
                level="WARNING",
                category="SQL开发规范",
                message="行存表的 COUNT(*) 需要扫描全表，大表场景频繁 COUNT 会消耗大量 I/O",
                fix_suggestion="降低 COUNT 频率、使用结果缓存、分区级统计等方式",
            ))

        # SPEC037: SELECT without LIMIT
        if ast and ast.get("node_type") == "SelectStmt":
            if not ast.get("limit_count") and not ast.get("limit_offset"):
                self.violations.append(Violation(
                    rule_id="SPEC037",
                    rule_name="查询建议使用 LIMIT 限制结果集",
                    level="INFO",
                    category="SQL开发规范",
                    message="查询未使用 LIMIT 限制结果集，可能返回超大结果集浪费资源",
                    fix_suggestion="添加 LIMIT 限制返回行数，或使用游标分段获取",
                ))

        # SPEC038: WITH RECURSIVE
        if self._has_with_recursive(tokens):
            self.violations.append(Violation(
                rule_id="SPEC038",
                rule_name="谨慎使用 WITH RECURSIVE",
                level="WARNING",
                category="SQL开发规范",
                message="WITH RECURSIVE 需确保有明确的终止条件，否则可能陷入死循环",
                fix_suggestion="根据业务表数据量和数据特征设计合理的递归终止条件",
            ))

        # SPEC039: Table without schema prefix
        if self._has_table_without_schema(tokens):
            self.violations.append(Violation(
                rule_id="SPEC039",
                rule_name="访问对象建议带上 SCHEMA 名称",
                level="INFO",
                category="SQL开发规范",
                message="访问表对象时未指定 SCHEMA 前缀，可能因 search_path 切换导致访问非预期的表",
                fix_suggestion="访问表和函数对象时显式指定 schema.table 格式",
            ))

    # ============================================================
    # Pattern Detection Helpers
    # ============================================================

    def _has_not_in_subquery(self, tokens):
        """Check for NOT IN (SELECT ...) pattern"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("NOT") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("IN"):
                    # Check if followed by SELECT (subquery)
                    for j in range(i + 2, min(i + 5, len(tokens))):
                        if tokens[j].is_keyword("SELECT"):
                            return True
            i += 1
        return False

    def _has_implicit_type_risk(self, tokens):
        """Check for potential implicit type conversion in WHERE"""
        # Look for: column = 'number' where column might be numeric
        # This is a heuristic check
        in_where = False
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("WHERE"):
                in_where = True
            elif tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or \
                 tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT"):
                in_where = False

            if in_where and tokens[i].type == TokenType.CMP_OP and tokens[i].value == "=":
                # Check if one side is string and other is number
                if i > 0 and i + 1 < len(tokens):
                    left = tokens[i - 1]
                    right = tokens[i + 1]
                    if (left.type == TokenType.SCONST and right.type == TokenType.ICONST) or \
                       (left.type == TokenType.ICONST and right.type == TokenType.SCONST):
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

    def _has_or_condition_issue(self, tokens):
        """Check for OR in WHERE clause"""
        in_where = False
        for t in tokens:
            if t.is_keyword("WHERE"):
                in_where = True
            elif t.is_keyword("GROUP") or t.is_keyword("ORDER"):
                in_where = False
            if in_where and t.is_keyword("OR"):
                return True
        return False

    def _has_large_in_list(self, tokens):
        """Check for IN list with many values"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("IN") and i + 1 < len(tokens):
                if tokens[i + 1].type == TokenType.LPAREN:
                    # Count commas until matching RPAREN
                    depth = 1
                    comma_count = 0
                    j = i + 2
                    while j < len(tokens) and depth > 0:
                        if tokens[j].type == TokenType.LPAREN:
                            depth += 1
                        elif tokens[j].type == TokenType.RPAREN:
                            depth -= 1
                        elif tokens[j].type == TokenType.COMMA and depth == 1:
                            comma_count += 1
                        j += 1
                    if comma_count > 100:
                        return True
            i += 1
        return False

    # ============================================================
    # New Detection Helpers (from DWS Design Spec)
    # ============================================================

    def _has_keyword(self, tokens, keyword):
        """Check if a keyword exists in token stream"""
        for t in tokens:
            if t.is_keyword(keyword):
                return True
        return False

    def _is_column_v3_table(self, tokens):
        """Check if CREATE TABLE is column-store v3 (orientation=column + colversion=3.0)"""
        has_column_orientation = False
        has_colversion_3 = False
        for i, t in enumerate(tokens):
            if t.type == TokenType.IDENT and t.value.lower() == "orientation":
                # Look for = column after
                for j in range(i + 1, min(i + 4, len(tokens))):
                    if tokens[j].is_keyword("COLUMN"):
                        has_column_orientation = True
            if t.type == TokenType.IDENT and t.value.lower() == "colversion":
                # Look for = 3.0 after
                for j in range(i + 1, min(i + 4, len(tokens))):
                    if tokens[j].type == TokenType.FCONST and tokens[j].value.startswith("3"):
                        has_colversion_3 = True
        return has_column_orientation and has_colversion_3

    def _has_serial_type(self, tokens):
        """Check for SERIAL/BIGSERIAL/SMALLSERIAL column types"""
        for t in tokens:
            if t.type == TokenType.IDENT:
                upper = t.value.upper()
                if upper in ("SERIAL", "BIGSERIAL", "SMALLSERIAL"):
                    return True
            if t.is_keyword("SERIAL") or t.is_keyword("BIGSERIAL") or t.is_keyword("SMALLSERIAL"):
                return True
        return False

    def _has_drop_without_if_exists(self, tokens):
        """Check for DROP without IF EXISTS"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("DROP"):
                # Look for IF EXISTS in the next few tokens
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

    def _has_multi_values_insert(self, tokens):
        """Check for INSERT with multiple VALUES groups"""
        i = 0
        in_insert = False
        values_count = 0
        while i < len(tokens):
            if tokens[i].is_keyword("INSERT"):
                in_insert = True
            if in_insert and tokens[i].is_keyword("VALUES"):
                values_count += 1
                if values_count > 3:
                    return True
            # Reset on semicolon or new statement
            if tokens[i].type == TokenType.SEMICOLON:
                in_insert = False
                values_count = 0
            i += 1
        return False

    def _has_function_on_filter_column(self, tokens):
        """Check for function calls on filter columns in WHERE clause"""
        in_where = False
        i = 0
        func_names = ("NVL", "COALESCE", "TRIM", "SUBSTR", "SUBSTRING",
                      "UPPER", "LOWER", "TO_CHAR", "TO_DATE", "TO_NUMBER",
                      "CAST", "CONVERT", "DECODE", "LENGTH", "REPLACE")
        while i < len(tokens):
            if tokens[i].is_keyword("WHERE"):
                in_where = True
            elif tokens[i].is_keyword("GROUP") or tokens[i].is_keyword("ORDER") or \
                 tokens[i].is_keyword("HAVING") or tokens[i].is_keyword("LIMIT"):
                in_where = False

            if in_where and i + 2 < len(tokens):
                # Check if current token is a function name (IDENT or KEYWORD)
                val_upper = tokens[i].value.upper()
                is_func = val_upper in func_names
                if is_func and tokens[i + 1].type == TokenType.LPAREN:
                    return True
            i += 1
        return False

    def _has_count_star(self, tokens):
        """Check for COUNT(*) pattern"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("COUNT") and i + 2 < len(tokens):
                if tokens[i + 1].type == TokenType.LPAREN:
                    if tokens[i + 2].type == TokenType.OP and tokens[i + 2].value == "*":
                        return True
                    # Also check for STAR as keyword
                    if tokens[i + 2].is_keyword("*"):
                        return True
            i += 1
        return False

    def _has_with_recursive(self, tokens):
        """Check for WITH RECURSIVE pattern"""
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("WITH") and i + 1 < len(tokens):
                if tokens[i + 1].is_keyword("RECURSIVE"):
                    return True
            i += 1
        return False

    def _has_table_without_schema(self, tokens):
        """Check for table references without schema prefix"""
        # Look for FROM/JOIN followed by IDENT without dot
        i = 0
        while i < len(tokens):
            if tokens[i].is_keyword("FROM") or tokens[i].is_keyword("JOIN") or \
               tokens[i].is_keyword("INTO") or tokens[i].is_keyword("UPDATE") or \
               tokens[i].is_keyword("TABLE"):
                # Next non-keyword IDENT should have a dot if schema-qualified
                for j in range(i + 1, min(i + 3, len(tokens))):
                    if tokens[j].type == TokenType.IDENT:
                        # Check if followed by dot (schema.table)
                        if j + 1 < len(tokens) and tokens[j + 1].value == ".":
                            break  # Has schema prefix
                        else:
                            # No dot - might be without schema
                            # Skip system table patterns
                            upper = tokens[j].value.upper()
                            if upper not in ("SELECT", "SET", "WHERE", "ON", "AS",
                                             "DUAL", "PG_CLASS", "PG_NAMESPACE"):
                                return True
                        break
            i += 1
        return False

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
        return target_line[start:end]

    def _generate_report(self):
        """Generate the final check report"""
        errors = [v for v in self.violations if v.level == "ERROR"]
        warnings = [v for v in self.violations if v.level == "WARNING"]
        infos = [v for v in self.violations if v.level == "INFO"]

        total_rules = 28  # Number of active rules (15 original + 13 new offline rules)
        passed = total_rules - len(self.violations)
        if passed < 0:
            passed = 0

        report = {
            "check_time": datetime.now().isoformat(),
            "check_mode": self.check_mode,
            "statement_type": self.parse_result.get("statement_type", "UNKNOWN") if self.parse_result else "UNKNOWN",
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
        lines.append("# DWS SQL 检查报告")
        lines.append("")
        lines.append(f"**检查时间**: {report['check_time']}")
        lines.append(f"**语句类型**: {report['statement_type']}")
        lines.append(f"**检查模式**: {report['check_mode']}")
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

        for category, violations in by_category.items():
            lines.append(f"## {category}")
            lines.append("")
            for v in violations:
                level_icon = {"ERROR": "X", "WARNING": "!", "INFO": "i"}.get(v['level'], "?")
                lines.append(f"### [{level_icon}] {v['rule_id']}: {v['rule_name']}")
                lines.append("")
                lines.append(f"- **级别**: {v['level']}")
                lines.append(f"- **位置**: 行 {v['line']}, 列 {v['column']}")
                lines.append(f"- **描述**: {v['message']}")
                if v['sql_snippet']:
                    lines.append(f"- **代码片段**: `{v['sql_snippet']}`")
                if v['fix_suggestion']:
                    lines.append(f"- **修复建议**: {v['fix_suggestion']}")
                lines.append("")

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
    checker = DWSSQLChecker(sql_text, check_mode=check_mode)
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
    checker = DWSSQLChecker(sql_text, check_mode=check_mode)
    return checker.generate_markdown_report()


# ---- CLI Entry Point ----
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python dws_sql_checker.py <sql_text_or_file> [syntax|spec|all]")
        sys.exit(1)

    input_text = sys.argv[1]
    if os.path.isfile(input_text):
        with open(input_text, 'r', encoding='utf-8') as f:
            input_text = f.read()

    mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    checker = DWSSQLChecker(input_text, check_mode=mode)
    report = checker.check()

    print(json.dumps(report, indent=2, ensure_ascii=False))
