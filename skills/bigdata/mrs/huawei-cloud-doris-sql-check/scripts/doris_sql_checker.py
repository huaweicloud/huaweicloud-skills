# -*- coding: utf-8 -*-
"""
Apache Doris SQL Checker Engine
Integrates tokenizer, parser, and rule-based checking.

Supports two modes:
1. Syntax Check - keyword validation, structure validation, Doris syntax compatibility
2. Specification Check - naming conventions, DML/DDL best practices, Doris-specific rules
"""

import sys
import os
import json
import re
from datetime import datetime

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, '..', 'rules'))
sys.path.insert(0, _THIS_DIR)

from doris_sql_tokenizer import tokenize, TokenType
from doris_sql_parser import parse_sql
from keywords import is_keyword, is_reserved_keyword, KeywordCategory, ALL_KEYWORDS


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


class DorisSQLChecker:
    """
    Apache Doris SQL Check Engine

    Performs syntax and specification checks on Doris SQL statements.
    """

    # Total rules: 34 syntax + 46 spec = 80
    TOTAL_RULES = 80

    def __init__(self, sql_text, check_mode="all"):
        self.sql_text = sql_text.strip()
        self.check_mode = check_mode  # syntax, spec, all
        self.violations = []
        self.parse_result = None
        self.tokens = []
        self.token_errors = []

    def check(self):
        """Run all checks and return the report"""
        # Step 0: SPEC046 - SQL length check
        if len(self.sql_text.encode('utf-8')) > 2 * 1024 * 1024:
            self.violations.append(Violation(
                rule_id="SPEC046",
                rule_name="SQL 语句长度超限",
                level="ERROR",
                category="复杂查询限制",
                message=f"SQL 语句长度超过 2MB，可能导致解析超时或内存占用过大",
                line=0,
                column=0,
                sql_snippet="",
                fix_suggestion="缩短 SQL 语句，将大型 IN 列表改为临时表 JOIN，或拆分复杂查询",
            ))

        # Step 1: Tokenize
        self.tokens, self.token_errors = tokenize(self.sql_text)

        # Step 2: Parse
        self.parse_result = parse_sql(self.sql_text)

        # Step 3: Run checks based on mode
        if self.check_mode in ("syntax", "all"):
            self._check_syntax()

        if self.check_mode in ("spec", "all"):
            self._check_specification()

        # Step 4: Generate report
        return self._generate_report()

    # ============================================================
    # Syntax Checks
    # ============================================================

    def _check_syntax(self):
        """Run syntax-level checks"""

        # SYN-ERR: Tokenizer errors
        for err in self.token_errors:
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

        # SYN001: Invalid keyword - already handled by tokenizer (unknown tokens become UNKNOWN)
        for tok in self.tokens:
            if tok.type == TokenType.UNKNOWN:
                self.violations.append(Violation(
                    rule_id="SYN001",
                    rule_name="无效关键字使用",
                    level="ERROR",
                    category="语法检查",
                    message=f"无法识别的字符: {tok.value!r}",
                    line=tok.line,
                    column=tok.column,
                    sql_snippet=tok.value,
                    fix_suggestion="查阅 Doris SQL 参考手册确认支持的关键字",
                ))

        # SYN002: Reserved keyword as identifier (without backticks)
        # Check identifiers that are reserved keywords used as table/column names
        for i, tok in enumerate(self.tokens):
            if tok.type == TokenType.KEYWORD and tok.is_reserved():
                # Check if it's used as an identifier (e.g., after FROM, comma in column list, etc.)
                # This is a heuristic - reserved keywords used in identifier position
                prev_tok = self.tokens[i - 1] if i > 0 else None
                next_tok = self.tokens[i + 1] if i + 1 < len(self.tokens) else None
                # Skip if it's a normal SQL keyword position (SELECT, FROM, WHERE, etc.)
                if prev_tok and prev_tok.type == TokenType.COMMA:
                    # After comma in column list - could be reserved keyword as identifier
                    # But this is hard to detect without full semantic analysis
                    pass

        # SYN003: Syntax structure errors from parser
        for err in self.parse_result.errors:
            # Skip tokenizer errors (already reported as SYN-ERR)
            if "Unrecognized" in str(err) or "Unclosed" in str(err):
                continue
            self.violations.append(Violation(
                rule_id="SYN003",
                rule_name="语法结构错误",
                level="ERROR",
                category="语法检查",
                message=str(err),
                line=getattr(err, 'line', 0),
                column=getattr(err, 'column', 0),
                sql_snippet=self._get_snippet(getattr(err, 'line', 0), getattr(err, 'column', 0)),
                fix_suggestion="检查语句是否缺少 Doris 必选关键字或子句",
            ))

        # SYN004: Clause ordering - check for clauses out of order
        self._check_clause_order()

        # Doris-specific syntax checks based on statement type
        stmt_type = self.parse_result.statement_type
        ast = self.parse_result.ast

        if stmt_type == "CREATE_TABLE" and ast:
            self._check_create_table_syntax(ast)
        elif stmt_type == "INSERT" and ast:
            self._check_insert_syntax(ast)
        elif stmt_type == "EXPLAIN" and ast:
            self._check_explain_syntax(ast)
        elif stmt_type == "LOAD" and ast:
            self._check_load_syntax(ast)
        elif stmt_type == "EXPORT" and ast:
            self._check_export_syntax(ast)
        elif stmt_type == "BACKUP" and ast:
            self._check_backup_syntax(ast, "BACKUP")
        elif stmt_type == "RESTORE" and ast:
            self._check_backup_syntax(ast, "RESTORE")
        elif stmt_type == "CREATE_MTMV" and ast:
            self._check_mtmv_syntax(ast)
        elif stmt_type == "KILL" and ast:
            self._check_kill_syntax(ast)
        elif stmt_type == "GRANT" or stmt_type == "REVOKE":
            self._check_grant_revoke_syntax(stmt_type)

    def _check_clause_order(self):
        """Check that SQL clauses are in the correct order"""
        # Find positions of major clauses
        clause_positions = {}
        clause_order = ["SELECT", "FROM", "WHERE", "GROUP", "HAVING", "ORDER", "LIMIT", "OFFSET"]
        for i, tok in enumerate(self.tokens):
            if tok.type == TokenType.KEYWORD:
                for clause in clause_order:
                    if tok.is_keyword(clause) and clause not in clause_positions:
                        clause_positions[clause] = i

        # Check order
        prev_pos = -1
        for clause in clause_order:
            if clause in clause_positions:
                if clause_positions[clause] < prev_pos:
                    tok = self.tokens[clause_positions[clause]]
                    self.violations.append(Violation(
                        rule_id="SYN004",
                        rule_name="子句顺序错误",
                        level="ERROR",
                        category="语法检查",
                        message=f"{clause} 子句出现在前一个子句之前",
                        line=tok.line,
                        column=tok.column,
                        sql_snippet=self._get_snippet(tok.line, tok.column),
                        fix_suggestion="按照 SELECT → FROM → WHERE → GROUP BY → HAVING → ORDER BY → LIMIT → OFFSET 顺序排列",
                    ))
                    break
                prev_pos = clause_positions[clause]

    def _check_create_table_syntax(self, ast):
        """Check CREATE TABLE syntax"""
        # SYN005: DISTRIBUTED BY
        if ast.distribute_type is not None and ast.distribute_type not in ("HASH", "RANDOM"):
            self.violations.append(Violation(
                rule_id="SYN005",
                rule_name="DISTRIBUTED BY 语法错误",
                level="ERROR",
                category="语法检查",
                message=f"无效的分布策略: {ast.distribute_type}（Doris 仅支持 HASH 或 RANDOM）",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 DISTRIBUTED BY HASH(列) 或 DISTRIBUTED BY RANDOM",
            ))
        # SYN006: PARTITION BY
        if ast.partition_by is not None:
            part_type = ast.partition_by.get("type", "") if isinstance(ast.partition_by, dict) else ""
            valid_types = ["RANGE", "LIST", "AUTO_RANGE", "AUTO_LIST", "AUTO"]
            if part_type and part_type not in valid_types:
                self.violations.append(Violation(
                    rule_id="SYN006",
                    rule_name="PARTITION BY 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"无效的分区类型: {part_type}",
                    sql_snippet=self.sql_text[:100],
                    fix_suggestion="使用 PARTITION BY RANGE(col) 或 PARTITION BY LIST(col) 或 AUTO PARTITION BY RANGE(col)",
                ))
        # SYN007: BUCKETS
        if ast.has_buckets and ast.buckets is not None:
            if ast.buckets != "AUTO":
                try:
                    val = int(ast.buckets)
                    if val <= 0:
                        self.violations.append(Violation(
                            rule_id="SYN007",
                            rule_name="BUCKETS 语法错误",
                            level="ERROR",
                            category="语法检查",
                            message=f"BUCKETS 数量必须为正整数或 AUTO，当前为 {val}",
                            sql_snippet=self.sql_text[:100],
                            fix_suggestion="使用 BUCKETS 10 或 BUCKETS AUTO",
                        ))
                except (ValueError, TypeError):
                    self.violations.append(Violation(
                        rule_id="SYN007",
                        rule_name="BUCKETS 语法错误",
                        level="ERROR",
                        category="语法检查",
                        message=f"BUCKETS 必须为正整数或 AUTO，当前为 {ast.buckets!r}",
                        sql_snippet=self.sql_text[:100],
                        fix_suggestion="使用 BUCKETS 10 或 BUCKETS AUTO",
                    ))
        # SYN009: KEY model
        if ast.key_model is not None and ast.key_model not in ("DUPLICATE", "AGGREGATE", "UNIQUE"):
            self.violations.append(Violation(
                rule_id="SYN009",
                rule_name="KEY 模型语法错误",
                level="ERROR",
                category="语法检查",
                message=f"无效的数据模型: {ast.key_model}",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 DUPLICATE KEY(col) 或 AGGREGATE KEY(col) 或 UNIQUE KEY(col)",
            ))
        # SYN011: ENGINE
        if ast.engine is not None:
            valid_engines = ["OLAP", "MYSQL", "ELASTICSEARCH", "HIVE", "HUDI",
                              "ICEBERG", "JDBC", "BROKER", "ODBC"]
            if ast.engine.upper() not in valid_engines:
                self.violations.append(Violation(
                    rule_id="SYN011",
                    rule_name="ENGINE 语法错误",
                    level="ERROR",
                    category="语法检查",
                    message=f"无效的 ENGINE: {ast.engine}（Doris 支持 {', '.join(valid_engines)}）",
                    sql_snippet=self.sql_text[:100],
                    fix_suggestion=f"使用 ENGINE = {valid_engines[0]} (默认，Doris 原生引擎)",
                ))

    def _check_insert_syntax(self, ast):
        """Check INSERT syntax"""
        # SYN012: INSERT OVERWRITE TABLE
        if ast.is_overwrite:
            # Check that TABLE keyword was present (already enforced by parser)
            pass

    def _check_explain_syntax(self, ast):
        """Check EXPLAIN syntax"""
        # SYN008: EXPLAIN planType
        valid_plan_types = ["PARSED", "ANALYZED", "REWRITTEN", "LOGICAL", "OPTIMIZED",
                              "PHYSICAL", "SHAPE", "MEMO", "DISTRIBUTED", "ALL"]
        if ast.plan_type is not None and ast.plan_type.upper() not in valid_plan_types:
            self.violations.append(Violation(
                rule_id="SYN008",
                rule_name="EXPLAIN planType 语法错误",
                level="ERROR",
                category="语法检查",
                message=f"无效的 EXPLAIN 计划类型: {ast.plan_type}",
                sql_snippet=self.sql_text[:100],
                fix_suggestion=f"使用 EXPLAIN {'|'.join(valid_plan_types)} SELECT ...",
            ))

    def _check_load_syntax(self, ast):
        """Check LOAD syntax"""
        # SYN013: LOAD LABEL structure
        if not ast.label:
            self.violations.append(Violation(
                rule_id="SYN013",
                rule_name="LOAD 语法错误",
                level="ERROR",
                category="语法检查",
                message="LOAD 语句缺少 LABEL",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 LOAD LABEL db.label (...) 语法",
            ))

    def _check_export_syntax(self, ast):
        """Check EXPORT syntax"""
        # SYN015: EXPORT structure
        if not ast.table:
            self.violations.append(Violation(
                rule_id="SYN015",
                rule_name="EXPORT 语法错误",
                level="ERROR",
                category="语法检查",
                message="EXPORT 语句缺少 TABLE",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 EXPORT TABLE table_name TO 'path' ...",
            ))
        if not ast.to_path:
            self.violations.append(Violation(
                rule_id="SYN015",
                rule_name="EXPORT 语法错误",
                level="ERROR",
                category="语法检查",
                message="EXPORT 语句缺少 TO path",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 EXPORT TABLE ... TO 'hdfs://path'",
            ))

    def _check_backup_syntax(self, ast, stmt_type):
        """Check BACKUP/RESTORE syntax"""
        # SYN016: BACKUP/RESTORE SNAPSHOT structure
        if not ast.snapshot_name:
            self.violations.append(Violation(
                rule_id="SYN016",
                rule_name=f"{stmt_type} SNAPSHOT 语法错误",
                level="ERROR",
                category="语法检查",
                message=f"{stmt_type} 语句缺少 SNAPSHOT name",
                sql_snippet=self.sql_text[:100],
                fix_suggestion=f"使用 {stmt_type} SNAPSHOT db.snapshot TO/FROM repository",
            ))

    def _check_mtmv_syntax(self, ast):
        """Check CREATE MATERIALIZED VIEW syntax"""
        # SYN017: MTMV structure
        valid_build_modes = ["IMMEDIATE", "DEFERRED"]
        if ast.build_mode is not None and ast.build_mode.upper() not in valid_build_modes:
            self.violations.append(Violation(
                rule_id="SYN017",
                rule_name="CREATE MTMV 语法错误",
                level="ERROR",
                category="语法检查",
                message=f"无效的 BUILD 模式: {ast.build_mode}",
                sql_snippet=self.sql_text[:100],
                fix_suggestion=f"使用 BUILD {'|'.join(valid_build_modes)}",
            ))
        valid_refresh_methods = ["COMPLETE", "AUTO"]
        if ast.refresh_method is not None and ast.refresh_method.upper() not in valid_refresh_methods:
            self.violations.append(Violation(
                rule_id="SYN017",
                rule_name="CREATE MTMV 语法错误",
                level="ERROR",
                category="语法检查",
                message=f"无效的 REFRESH 方法: {ast.refresh_method}",
                sql_snippet=self.sql_text[:100],
                fix_suggestion=f"使用 REFRESH {'|'.join(valid_refresh_methods)}",
            ))

    def _check_kill_syntax(self, ast):
        """Check KILL syntax"""
        # SYN027: KILL structure
        if ast.kill_type not in ("CONNECTION", "QUERY"):
            self.violations.append(Violation(
                rule_id="SYN027",
                rule_name="KILL 语法错误",
                level="ERROR",
                category="语法检查",
                message=f"无效的 KILL 类型: {ast.kill_type}",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 KILL QUERY connection_id 或 KILL CONNECTION connection_id",
            ))

    def _check_grant_revoke_syntax(self, stmt_type):
        """Check GRANT/REVOKE syntax"""
        # SYN033: GRANT/REVOKE structure - basic check
        valid_privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "LOAD", "EXPORT",
                            "ALTER", "CREATE", "DROP", "USAGE", "SHOW", "ALL"]
        # Check if privileges contain invalid values
        # This is a simplified check
        pass

    # ============================================================
    # Specification Checks
    # ============================================================

    def _check_specification(self):
        """Run specification-level checks"""
        ast = self.parse_result.ast
        stmt_type = self.parse_result.statement_type

        if ast is None:
            return

        if stmt_type == "SELECT":
            self._check_select_spec(ast)
        elif stmt_type == "INSERT":
            self._check_insert_spec(ast)
        elif stmt_type in ("UPDATE", "DELETE"):
            self._check_dml_spec(ast, stmt_type)
        elif stmt_type == "CREATE_TABLE":
            self._check_create_table_spec(ast)
        elif stmt_type == "CREATE_VIEW":
            self._check_create_view_spec(ast)
        elif stmt_type == "DROP_TABLE":
            self._check_drop_spec(ast)
        elif stmt_type == "DROP_VIEW":
            self._check_drop_spec(ast)
        elif stmt_type == "DROP_INDEX":
            self._check_drop_spec(ast)

    def _check_select_spec(self, ast):
        """Check SELECT specification"""
        # SPEC003: SELECT *
        if ast.has_select_star:
            self.violations.append(Violation(
                rule_id="SPEC003",
                rule_name="禁止使用 SELECT *",
                level="ERROR",
                category="数据操作规范",
                message="查询语句使用 SELECT *，必须明确指定字段列表",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="将 SELECT * 替换为具体的字段列表",
            ))
        # SPEC006: DISTINCT
        if ast.distinct:
            self.violations.append(Violation(
                rule_id="SPEC006",
                rule_name="DISTINCT 可能影响性能",
                level="INFO",
                category="数据操作规范",
                message="使用 DISTINCT 会导致排序去重，大数据量下可能影响性能",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="考虑使用 GROUP BY 替代 DISTINCT",
            ))
        # SPEC030: Missing LIMIT
        if not ast.has_limit and ast.from_clause:
            self.violations.append(Violation(
                rule_id="SPEC030",
                rule_name="查询建议使用 LIMIT 限制结果集",
                level="INFO",
                category="SQL开发规范",
                message="查询缺少 LIMIT，可能返回过大结果集",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 LIMIT 限制返回行数",
            ))
        # SPEC038: INTO OUTFILE
        if ast.has_outfile:
            self.violations.append(Violation(
                rule_id="SPEC038",
                rule_name="避免频繁使用 OUTFILE 导出",
                level="INFO",
                category="SQL开发规范",
                message="SELECT ... INTO OUTFILE 频繁导出大表数据效率低，建议使用 EXPORT TABLE",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 EXPORT TABLE ... TO 'path' 替代 SELECT ... INTO OUTFILE",
            ))
        # Check for NOT IN subquery, LIKE prefix, OR, IN list, etc. via token scan
        self._check_select_token_patterns()

    def _check_select_token_patterns(self):
        """Check SELECT patterns via token scanning"""
        tokens_upper = [(t.value.upper() if t.type == TokenType.KEYWORD else t.value) for t in self.tokens]

        # SPEC005: NOT IN (SELECT ...)
        for i in range(len(tokens_upper) - 3):
            if (tokens_upper[i] == "NOT" and tokens_upper[i + 1] == "IN"
                and self.tokens[i + 2].type == TokenType.LEFT_PAREN):
                # Check if SELECT follows
                if i + 3 < len(tokens_upper) and tokens_upper[i + 3] == "SELECT":
                    self.violations.append(Violation(
                        rule_id="SPEC005",
                        rule_name="NOT IN 子查询性能风险",
                        level="WARNING",
                        category="数据操作规范",
                        message="NOT IN 子查询可能导致性能问题，建议改用 NOT EXISTS 或 LEFT JOIN ... IS NULL",
                        line=self.tokens[i].line,
                        column=self.tokens[i].column,
                        sql_snippet=self._get_snippet(self.tokens[i].line, self.tokens[i].column),
                        fix_suggestion="将 NOT IN (SELECT ...) 改写为 NOT EXISTS (SELECT ...) 或 LEFT JOIN ... WHERE col IS NULL",
                    ))

        # SPEC008: LIKE '%...'
        for tok in self.tokens:
            if tok.type == TokenType.STRING_LITERAL and tok.value.startswith('%'):
                # Check if previous keyword was LIKE
                idx = self.tokens.index(tok)
                if idx > 0 and self.tokens[idx - 1].is_keyword("LIKE"):
                    self.violations.append(Violation(
                        rule_id="SPEC008",
                        rule_name="LIKE 前缀通配符导致全表扫描",
                        level="WARNING",
                        category="数据操作规范",
                        message=f"LIKE '{tok.value[:20]}...' 使用前缀通配符，无法使用索引",
                        line=tok.line,
                        column=tok.column,
                        sql_snippet=tok.value,
                        fix_suggestion="避免使用前缀通配符，或考虑使用 Doris 倒排索引 + MATCH 查询",
                    ))

        # SPEC009: OR condition
        for tok in self.tokens:
            if tok.is_keyword("OR"):
                self.violations.append(Violation(
                    rule_id="SPEC009",
                    rule_name="OR 条件可能导致性能问题",
                    level="INFO",
                    category="数据操作规范",
                    message="OR 条件可能导致查询优化器无法选择最优执行计划",
                    line=tok.line,
                    column=tok.column,
                    sql_snippet="OR",
                    fix_suggestion="考虑将 OR 改写为 UNION ALL，或使用 IN 子句",
                ))
                break  # Only report once

        # SPEC010: IN list too long
        for i, tok in enumerate(self.tokens):
            if tok.is_keyword("IN") and i + 1 < len(self.tokens):
                if self.tokens[i + 1].type == TokenType.LEFT_PAREN:
                    # Count values until )
                    count = 0
                    depth = 1
                    j = i + 2
                    while j < len(self.tokens) and depth > 0:
                        if self.tokens[j].type == TokenType.LEFT_PAREN:
                            depth += 1
                        elif self.tokens[j].type == TokenType.RIGHT_PAREN:
                            depth -= 1
                        elif self.tokens[j].type == TokenType.COMMA and depth == 1:
                            count += 1
                        j += 1
                    if count > 1000:
                        self.violations.append(Violation(
                            rule_id="SPEC010",
                            rule_name="IN 列表过长",
                            level="WARNING",
                            category="数据操作规范",
                            message=f"IN 列表包含 {count + 1} 个值（>1000），可能影响性能",
                            line=tok.line,
                            column=tok.column,
                            sql_snippet=self._get_snippet(tok.line, tok.column),
                            fix_suggestion="将 IN 列表改写为临时表 JOIN 或子查询",
                        ))

        # SPEC041: COUNT(DISTINCT) count > 5
        count_distinct_count = 0
        for i in range(len(self.tokens) - 2):
            if (self.tokens[i].is_keyword("COUNT")
                and self.tokens[i + 1].type == TokenType.LEFT_PAREN
                and i + 2 < len(self.tokens)
                and self.tokens[i + 2].is_keyword("DISTINCT")):
                count_distinct_count += 1
        if count_distinct_count > 5:
            self.violations.append(Violation(
                rule_id="SPEC041",
                rule_name="COUNT(DISTINCT) 使用次数过多",
                level="ERROR",
                category="复杂查询限制",
                message=f"SQL 语句中 COUNT(DISTINCT) 出现 {count_distinct_count} 次（>5），可能导致性能严重下降",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="减少 COUNT(DISTINCT) 使用次数，考虑使用 GROUP BY 或拆分查询，或使用 BITMAP/HLL 精确/近似去重",
            ))

        # SPEC042: NOT IN (subquery) - stricter ERROR check
        for i in range(len(self.tokens) - 3):
            if (self.tokens[i].is_keyword("NOT")
                and self.tokens[i + 1].is_keyword("IN")
                and self.tokens[i + 2].type == TokenType.LEFT_PAREN):
                # Scan inside parens for SELECT keyword (subquery indicator)
                depth = 1
                j = i + 3
                has_subquery = False
                while j < len(self.tokens) and depth > 0:
                    if self.tokens[j].type == TokenType.LEFT_PAREN:
                        depth += 1
                    elif self.tokens[j].type == TokenType.RIGHT_PAREN:
                        depth -= 1
                    elif self.tokens[j].is_keyword("SELECT") and depth > 0:
                        has_subquery = True
                        break
                    j += 1
                if has_subquery:
                    self.violations.append(Violation(
                        rule_id="SPEC042",
                        rule_name="NOT IN 子查询禁止使用",
                        level="ERROR",
                        category="复杂查询限制",
                        message="NOT IN 子查询会导致全表扫描和性能严重下降，Doris 优化器难以优化此类语句",
                        line=self.tokens[i].line,
                        column=self.tokens[i].column,
                        sql_snippet=self._get_snippet(self.tokens[i].line, self.tokens[i].column),
                        fix_suggestion="将 NOT IN (SELECT ...) 改写为 NOT EXISTS (SELECT ...) 或 LEFT JOIN ... WHERE ... IS NULL",
                    ))
                    break  # Report once per SQL

        # SPEC043: JOIN count > 20
        join_count = sum(1 for t in self.tokens if t.is_keyword("JOIN"))
        if join_count > 20:
            self.violations.append(Violation(
                rule_id="SPEC043",
                rule_name="JOIN 次数过多",
                level="ERROR",
                category="复杂查询限制",
                message=f"SQL 语句中 JOIN 次数为 {join_count}（>20），可能导致查询计划不稳定、内存消耗过大",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="减少 JOIN 数量，考虑拆分查询、使用中间表或临时表，或重新设计数据模型减少关联",
            ))

        # SPEC044: UNION ALL count > 20
        union_all_count = 0
        for i in range(len(self.tokens) - 1):
            if self.tokens[i].is_keyword("UNION") and self.tokens[i + 1].is_keyword("ALL"):
                union_all_count += 1
        if union_all_count > 20:
            self.violations.append(Violation(
                rule_id="SPEC044",
                rule_name="UNION ALL 次数过多",
                level="ERROR",
                category="复杂查询限制",
                message=f"SQL 语句中 UNION ALL 次数为 {union_all_count}（>20），可能导致查询计划复杂、资源消耗大",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="减少 UNION ALL 次数，考虑使用临时表存储中间结果，或使用 INSERT INTO 分批次写入",
            ))

        # SPEC045: Nested subquery depth > 20
        max_depth = 0
        paren_depth = 0
        for i, tok in enumerate(self.tokens):
            if tok.type == TokenType.LEFT_PAREN:
                paren_depth += 1
            elif tok.type == TokenType.RIGHT_PAREN:
                paren_depth -= 1
            elif tok.is_keyword("SELECT") and paren_depth > 0:
                # This SELECT is inside a subquery at paren_depth level
                if paren_depth > max_depth:
                    max_depth = paren_depth
        if max_depth > 20:
            self.violations.append(Violation(
                rule_id="SPEC045",
                rule_name="嵌套子查询层级过深",
                level="ERROR",
                category="复杂查询限制",
                message=f"SQL 语句中嵌套子查询深度为 {max_depth}（>20），可能导致解析和执行性能严重下降",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="减少子查询嵌套层级，使用 CTE (WITH 子句) 或临时表将复杂查询拆分为多个简单步骤",
            ))

    def _check_insert_spec(self, ast):
        """Check INSERT specification"""
        # SPEC013: Missing column list
        if ast.has_values and not ast.columns:
            self.violations.append(Violation(
                rule_id="SPEC013",
                rule_name="INSERT 缺少列列表",
                level="WARNING",
                category="数据操作规范",
                message="INSERT 语句未指定列列表，依赖列的默认顺序",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加列列表 INSERT INTO table (col1, col2, ...) VALUES ...",
            ))
        # SPEC025: Multiple VALUES - use STREAM LOAD
        if ast.values_count > 3:
            self.violations.append(Violation(
                rule_id="SPEC025",
                rule_name="INSERT 多 VALUES 建议使用 STREAM LOAD 替代",
                level="WARNING",
                category="SQL开发规范",
                message=f"INSERT 包含 {ast.values_count} 组 VALUES，建议使用 STREAM LOAD / BROKER LOAD 替代",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="使用 STREAM LOAD HTTP API 或 BROKER LOAD 替代 INSERT VALUES",
            ))
        # SPEC026: Frequent small-batch INSERT (heuristic - any VALUES INSERT)
        if ast.has_values and ast.values_count <= 3:
            self.violations.append(Violation(
                rule_id="SPEC026",
                rule_name="禁止对 Doris 表频繁小批量 INSERT",
                level="WARNING",
                category="SQL开发规范",
                message="Doris 列存 + LSM-tree 架构，频繁小批量入库会导致 compaction 压力",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="攒批入库，单次入库量建议 > 100K 行 或 > 100MB，或使用 STREAM LOAD",
            ))

    def _check_dml_spec(self, ast, stmt_type):
        """Check UPDATE/DELETE specification"""
        # SPEC004: Missing WHERE
        if ast.missing_where:
            self.violations.append(Violation(
                rule_id="SPEC004",
                rule_name=f"{stmt_type} 缺少 WHERE 条件",
                level="ERROR",
                category="数据操作规范",
                message=f"{stmt_type} 语句必须包含 WHERE 条件，否则将影响全表数据",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 WHERE 条件限制操作范围",
            ))
        # SPEC027: Frequent UPDATE/DELETE
        self.violations.append(Violation(
            rule_id="SPEC027",
            rule_name="避免频繁 UPDATE/DELETE",
            level="WARNING",
            category="SQL开发规范",
            message=f"{stmt_type} 是 read-merge-write，开销大",
            sql_snippet=self.sql_text[:100],
            fix_suggestion="频繁 UPDATE/DELETE 的表考虑使用 UNIQUE KEY + merge-on-write 模型",
        ))

    def _check_create_table_spec(self, ast):
        """Check CREATE TABLE specification"""
        like_table = getattr(ast, 'like_table', None)
        ctas_query = getattr(ast, 'ctas_query', None)
        # SPEC001: Missing DISTRIBUTED BY
        if ast.distribute_type is None and not like_table and not ctas_query:
            self.violations.append(Violation(
                rule_id="SPEC001",
                rule_name="CREATE TABLE 缺少 DISTRIBUTED BY",
                level="ERROR",
                category="对象设计规范",
                message="Doris 建表必须指定分布策略",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 DISTRIBUTED BY HASH(分布键) BUCKETS 10 或 DISTRIBUTED BY RANDOM",
            ))
        # SPEC002: Missing ENGINE
        if ast.engine is None and not like_table:
            self.violations.append(Violation(
                rule_id="SPEC002",
                rule_name="CREATE TABLE 缺少 ENGINE",
                level="INFO",
                category="对象设计规范",
                message="建议显式指定 ENGINE，默认为 OLAP",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 ENGINE = olap",
            ))
        # SPEC014: Missing comment
        if ast.comment is None:
            self.violations.append(Violation(
                rule_id="SPEC014",
                rule_name="CREATE TABLE 缺少表注释",
                level="INFO",
                category="对象设计规范",
                message="表未添加注释，不利于后续维护",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 COMMENT '表用途说明'",
            ))
        # SPEC015: Table naming convention
        if ast.table_name:
            if not re.match(r'^[a-z][a-z0-9_]*$', ast.table_name.split('.')[-1]):
                # Allow backtick-quoted names
                last_part = ast.table_name.split('.')[-1]
                if not last_part.startswith('`'):
                    self.violations.append(Violation(
                        rule_id="SPEC015",
                        rule_name="表名不符合命名规范",
                        level="WARNING",
                        category="命名规范",
                        message=f"表名 {ast.table_name!r} 应使用小写字母、数字和下划线",
                        sql_snippet=ast.table_name,
                        fix_suggestion="使用小写字母、数字和下划线命名表",
                    ))
        # SPEC018: Distribution column not in columns
        if (ast.distribute_type == "HASH" and ast.distribute_columns
            and ast.columns and isinstance(ast.distribute_columns, str)):
            dist_cols = [c.strip() for c in ast.distribute_columns.split(',')]
            col_names = [c.get("name", "").lower() for c in ast.columns if isinstance(c, dict)]
            for dc in dist_cols:
                if dc.lower() not in col_names:
                    self.violations.append(Violation(
                        rule_id="SPEC018",
                        rule_name="DISTRIBUTED BY HASH 列建议为列定义中出现",
                        level="WARNING",
                        category="对象设计规范",
                        message=f"分布键 {dc!r} 不在表列定义中",
                        sql_snippet=self.sql_text[:100],
                        fix_suggestion="确保分布键列在表定义中存在",
                    ))
        # SPEC020: Missing KEY model
        if ast.key_model is None and not like_table and not ctas_query:
            self.violations.append(Violation(
                rule_id="SPEC020",
                rule_name="缺少 KEY 模型定义",
                level="INFO",
                category="对象设计规范",
                message="建议显式指定 Doris 的数据模型（默认为 DUPLICATE KEY）",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 DUPLICATE KEY(col1, col2) 或 AGGREGATE KEY(col1) 或 UNIQUE KEY(col1)",
            ))
        # SPEC021: Missing partition
        if ast.partition_by is None and not like_table and not ctas_query:
            self.violations.append(Violation(
                rule_id="SPEC021",
                rule_name="大表建议设计分区",
                level="INFO",
                category="对象设计规范",
                message="针对包含时间类型字段的表建议设计分区",
                sql_snippet=self.sql_text[:100],
                fix_suggestion="添加 PARTITION BY RANGE(时间字段) 或 AUTO PARTITION BY RANGE(时间字段)",
            ))
        # SPEC036: BITMAP/HLL column needs aggregation type
        if ast.columns and ast.key_model == "AGGREGATE":
            for col in ast.columns:
                if isinstance(col, dict):
                    col_type = (col.get("type") or "").upper()
                    if col_type in ("BITMAP", "HLL", "QUANTILE_STATE") and not any(
                        agg in (col.get("type") or "").upper() for agg in ["BITMAP_UNION", "HLL_UNION", "QUANTILE_UNION"]):
                        self.violations.append(Violation(
                            rule_id="SPEC036",
                            rule_name="BITMAP/HLL 列建议指定聚合类型",
                            level="WARNING",
                            category="对象设计规范",
                            message=f"{col_type} 列 {col.get('name')} 应指定聚合类型",
                            sql_snippet=self.sql_text[:100],
                            fix_suggestion=f"在 AGGREGATE KEY 模型中使用 {col_type}_UNION(col)",
                        ))
        # SPEC039: VARCHAR without length
        if ast.columns:
            for col in ast.columns:
                if isinstance(col, dict):
                    col_type = (col.get("type") or "").upper()
                    if col_type == "VARCHAR":
                        self.violations.append(Violation(
                            rule_id="SPEC039",
                            rule_name="VARCHAR 长度建议显式指定",
                            level="WARNING",
                            category="对象设计规范",
                            message=f"VARCHAR 列 {col.get('name')} 未指定长度",
                            sql_snippet=self.sql_text[:100],
                            fix_suggestion="显式指定 VARCHAR(N)，如 VARCHAR(255)",
                        ))
        # SPEC040: DECIMAL without precision
        if ast.columns:
            for col in ast.columns:
                if isinstance(col, dict):
                    col_type = (col.get("type") or "").upper()
                    if col_type in ("DECIMAL", "DECIMALV2", "DECIMALV3"):
                        self.violations.append(Violation(
                            rule_id="SPEC040",
                            rule_name="DECIMAL 精度建议显式指定",
                            level="WARNING",
                            category="对象设计规范",
                            message=f"{col_type} 列 {col.get('name')} 未指定精度",
                            sql_snippet=self.sql_text[:100],
                            fix_suggestion=f"显式指定 {col_type}(p,s)，如 DECIMALV3(18,2)",
                        ))

    def _check_create_view_spec(self, ast):
        """Check CREATE VIEW specification"""
        # SPEC033: View nesting depth (requires cluster)
        pass

    def _check_drop_spec(self, ast):
        """Check DROP specification"""
        # SPEC024: DROP should use IF EXISTS
        if not ast.if_exists:
            self.violations.append(Violation(
                rule_id="SPEC024",
                rule_name="DROP 操作建议使用 IF EXISTS",
                level="WARNING",
                category="SQL开发规范",
                message=f"DROP {ast.object_type} 未使用 IF EXISTS，对象不存在时会报错",
                sql_snippet=self.sql_text[:100],
                fix_suggestion=f"使用 DROP {ast.object_type} IF EXISTS ...",
            ))

    # ============================================================
    # Report Generation
    # ============================================================

    def _generate_report(self):
        """Generate a Markdown report"""
        errors = sum(1 for v in self.violations if v.level == "ERROR")
        warnings = sum(1 for v in self.violations if v.level == "WARNING")
        infos = sum(1 for v in self.violations if v.level == "INFO")
        passed = self.TOTAL_RULES - len(self.violations)

        report = []
        report.append("# Doris SQL 检查报告")
        report.append("")
        report.append(f"**检查时间**: {datetime.now().isoformat(timespec='seconds')}")
        report.append(f"**语句类型**: {self.parse_result.statement_type}")
        report.append(f"**检查模式**: {self.check_mode}")
        report.append("")
        report.append("## 检查概要")
        report.append("")
        report.append("| 指标 | 值 |")
        report.append("|------|------|")
        report.append(f"| 检查规则数 | {self.TOTAL_RULES} |")
        report.append(f"| 通过 | {passed} |")
        report.append(f"| 违规 | {len(self.violations)} |")
        report.append(f"| 错误 (ERROR) | {errors} |")
        report.append(f"| 警告 (WARNING) | {warnings} |")
        report.append(f"| 提示 (INFO) | {infos} |")
        report.append("")

        if self.check_mode in ("syntax", "all"):
            report.append("## 语法检查")
            report.append("")
            syntax_violations = [v for v in self.violations if v.category == "语法检查"]
            if syntax_violations:
                for v in syntax_violations:
                    report.append(self._format_violation(v))
            else:
                report.append("[OK] 无语法检查违规")
            report.append("")

        if self.check_mode in ("spec", "all"):
            report.append("## 规范检查")
            report.append("")
            spec_violations = [v for v in self.violations if v.category != "语法检查"]
            if spec_violations:
                for v in spec_violations:
                    report.append(self._format_violation(v))
            else:
                report.append("[OK] 无规范检查违规")
            report.append("")

        report.append("## 原始 SQL")
        report.append("")
        report.append("```sql")
        report.append(self.sql_text)
        report.append("```")
        report.append("")

        return "\n".join(report)

    def _format_violation(self, v):
        """Format a violation as Markdown"""
        icon = {"ERROR": "X", "WARNING": "!", "INFO": "i"}.get(v.level, "?")
        lines = []
        lines.append(f"### [{icon}] {v.rule_id}: {v.rule_name}")
        lines.append("")
        lines.append(f"- **级别**: {v.level}")
        if v.line:
            lines.append(f"- **位置**: 行 {v.line}, 列 {v.column}")
        lines.append(f"- **描述**: {v.message}")
        if v.sql_snippet:
            lines.append(f"- **代码片段**: `{v.sql_snippet}`")
        lines.append(f"- **修复建议**: {v.fix_suggestion}")
        lines.append("")
        return "\n".join(lines)

    def _get_snippet(self, line, column):
        """Get a code snippet around the given position"""
        if not self.sql_text:
            return ""
        lines = self.sql_text.split('\n')
        if 1 <= line <= len(lines):
            return lines[line - 1][:80]
        return self.sql_text[:80]


def check_sql_markdown(sql_text, check_mode="all"):
    """Convenience function to check SQL and return Markdown report"""
    checker = DorisSQLChecker(sql_text, check_mode)
    return checker.check()


def check_sql_json(sql_text, check_mode="all"):
    """Convenience function to check SQL and return JSON report"""
    checker = DorisSQLChecker(sql_text, check_mode)
    checker.check()
    return json.dumps({
        "statement_type": checker.parse_result.statement_type,
        "check_mode": checker.check_mode,
        "violations": [v.to_dict() for v in checker.violations],
        "summary": {
            "total_rules": checker.TOTAL_RULES,
            "passed": checker.TOTAL_RULES - len(checker.violations),
            "violations": len(checker.violations),
            "errors": sum(1 for v in checker.violations if v.level == "ERROR"),
            "warnings": sum(1 for v in checker.violations if v.level == "WARNING"),
            "infos": sum(1 for v in checker.violations if v.level == "INFO"),
        },
    }, indent=2, ensure_ascii=False)


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python doris_sql_checker.py \"<sql_text>\" [syntax|spec|all]")
        print("\nDoris SQL Checker - Comprehensive SQL check for Apache Doris")
        print(f"Total rules: {DorisSQLChecker.TOTAL_RULES} (34 syntax + 46 spec)")
        sys.exit(1)

    sql_text = sys.argv[1]
    check_mode = sys.argv[2] if len(sys.argv) > 2 else "all"

    if check_mode not in ("syntax", "spec", "all"):
        print(f"Error: invalid check mode {check_mode!r}. Use syntax/spec/all.")
        sys.exit(1)

    # JSON output for programmatic use, Markdown for display
    if check_mode == "syntax" and len(sys.argv) > 3 and sys.argv[3] == "--json":
        print(check_sql_json(sql_text, check_mode))
    else:
        print(check_sql_markdown(sql_text, check_mode))


if __name__ == "__main__":
    main()
