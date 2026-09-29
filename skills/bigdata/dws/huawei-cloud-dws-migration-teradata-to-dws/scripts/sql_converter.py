#!/usr/bin/env python3
"""Teradata SQL → DWS 通用 SQL 转换器（视图/宏/存储过程共用子模块）"""

import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger('sql_converter')


# QUALIFY 子查询包装模板（{cond}/{before} 由调用方替换，均为转换产物或源 DDL 片段）
_QUALIFY_WINDOW_STAR_TPL = ('SELECT * EXCEPT (_qualify_cond) FROM (\n'
                            '    SELECT *, ({cond}) AS _qualify_cond FROM (\n'
                            '        {before}\n'
                            '    ) AS _qualify_inner\n'
                            ') AS _qualify_sub WHERE _qualify_cond')
_QUALIFY_WINDOW_COLS_TPL = ('SELECT {cols} FROM (\n'
                            '    SELECT *, ({cond}) AS _qualify_cond FROM (\n'
                            '        {before}\n'
                            '    ) AS _qualify_inner\n'
                            ') AS _qualify_sub WHERE _qualify_cond')
_QUALIFY_SIMPLE_TPL = ('SELECT * FROM (\n'
                       '    {before}\n'
                       ') AS _qualify_sub WHERE {cond}')


class SQLConverter:
    """
    Teradata SQL → DWS (PostgreSQL) SQL 转换器

    处理 Teradata 特有语法到 PostgreSQL/DWS 等价语法的转换。
    """

    # Teradata 函数 → PostgreSQL 函数映射
    FUNCTION_MAP = {
        'ZEROIFNULL': '_zeroifnull',
        'NULLIFZERO': '_nullifzero',
        'SUBSTR': 'SUBSTRING',
        'INDEX': 'STRPOS',
        'CHARACTERS': 'LENGTH',
        'CHAR_LENGTH': 'LENGTH',
        'CHARS': 'LENGTH',
        'TRIM_': 'TRIM',
        'LASTDAY': 'LAST_DAY',
        'MONTHS_BETWEEN': '_months_between',
        'ADD_MONTHS': '_add_months',
        'NEXT_DAY': '_next_day',
        'RANDOM': 'RANDOM',
        'SOUNDEX': 'SOUNDEX',
        'NVP': '_nvp',
        'OTRANSLATE': 'TRANSLATE',
        'OREPLACE': 'REPLACE',
        'REGEXP_SIMILAR': '~',
        'REGEXP_REPLACE': 'REGEXP_REPLACE',
        'REGEXP_SUBSTR': 'REGEXP_SUBSTR',
        'REGEXP_INSTR': '_regexp_instr',
        'TO_CHAR': 'TO_CHAR',
        'TO_DATE': 'TO_DATE',
        'TO_TIMESTAMP': 'TO_TIMESTAMP',
        'TO_NUMBER': 'TO_NUMBER',
        'CAST': 'CAST',
        'COALESCE': 'COALESCE',
        'NVL': 'COALESCE',
        'NVL2': '_nvl2',
        'DECODE': '_decode',
        'GREATEST': 'GREATEST',
        'LEAST': 'LEAST',
        'RANK': 'RANK',
        'DENSE_RANK': 'DENSE_RANK',
        'ROW_NUMBER': 'ROW_NUMBER',
        'CSUM': '_csum',
        'MSUM': '_msum',
        'MAVG': '_mavg',
        'MDIFF': '_mdiff',
        'MLINEAR': '_mlinear',
        'QUARTER': '_quarter',
        'WEEK': '_week',
        'DAYOFWEEK': '_dayofweek',
        'DAYOFMONTH': '_dayofmonth',
        'DAYOFYEAR': '_dayofyear',
        'EXTRACT': 'EXTRACT',
        'CURRENT_DATE': 'CURRENT_DATE',
        'CURRENT_TIME': 'CURRENT_TIME',
        'CURRENT_TIMESTAMP': 'CURRENT_TIMESTAMP',
        'USER': 'CURRENT_USER',
        'SESSION': 'CURRENT_SESSION',
    }

    @classmethod
    def convert_view_sql(cls, sql: str, source_db: str = None,
                         target_schema: str = None) -> str:
        """
        转换 Teradata 视图 SQL 到 DWS 兼容的 SQL

        步骤:
        1. 提取 SELECT 语句
        2. 转换函数调用
        3. 转换 QUALIFY → 子查询
        4. 转换 GROUP BY 位置引用
        5. 转换数据库引用
        6. 转换其他语法差异
        """
        result = sql

        # 去除 Teradata 特有的前缀
        result = cls._strip_td_prefixes(result)

        # 转换 QUALIFY → 子查询 (在函数转换之前，以便正确处理窗口函数)
        result = cls._convert_qualify(result)

        # 转换函数调用 (包括 ZEROIFNULL → COALESCE(expr, 0))
        result = cls._convert_functions(result)

        # 转换 GROUP BY 位置引用
        result = cls._convert_group_by_position(result)

        # 转换数据库/表引用
        result = cls._convert_db_references(result, source_db, target_schema)

        # 转换日期/时间字面量
        result = cls._convert_date_literals(result)

        # 转换 INTERVAL 语法: INTERVAL 'N' UNIT → INTERVAL 'N unit'
        result = cls._convert_interval(result)

        # 转换类型转换
        result = cls._convert_cast(result)

        # 转换字符串连接
        result = cls._convert_string_concat(result)

        # 清理多余空格
        result = re.sub(r'\n{3,}', '\n\n\n', result)
        result = re.sub(r' {2,}', ' ', result)
        # 清理 \r 字符 (替换为空格避免粘连)
        result = result.replace('\r', ' ')
        # 再次清理可能产生的多余空格
        result = re.sub(r' {2,}', ' ', result)

        return result.strip()

    @classmethod
    def _strip_td_prefixes(cls, sql: str) -> str:
        """去除 Teradata 特有的前缀关键字"""
        # 去除 LOCKING ROW FOR ACCESS 等锁定修饰
        sql = re.sub(r'LOCKING\s+(?:TABLE|ROW|OBJECT)\s+\w+\s+FOR\s+(?:ACCESS|EXCLUSIVE|READ|WRITE)',
                     '', sql, flags=re.IGNORECASE)
        # 去除 WITH CHECK OPTION 等
        # 保留 WITH CHECK OPTION 因为 PostgreSQL 也支持
        return sql

    @classmethod
    def _convert_qualify(cls, sql: str) -> str:
        """
        转换 QUALIFY 子句为子查询

        Teradata: SELECT col1, col2, ROW_NUMBER() OVER(...) AS rn FROM t WHERE ... QUALIFY rn = 1
        PostgreSQL: SELECT * FROM (SELECT col1, col2, ROW_NUMBER() OVER(...) AS rn FROM t WHERE ...) sub WHERE rn = 1
        """
        # 检查是否包含 QUALIFY
        qualify_idx = re.search(r'\bQUALIFY\b', sql, re.IGNORECASE)
        if not qualify_idx:
            return sql

        qualify_pos = qualify_idx.start()

        # 提取 QUALIFY 条件 (到语句末尾或分号)
        qualify_condition = sql[qualify_pos + 8:].strip()  # 8 = len('QUALIFY')
        qualify_condition = qualify_condition.rstrip(';').strip()

        # QUALIFY 之前的 SQL (SELECT ... FROM ... WHERE ... GROUP BY ...)
        before_qualify = sql[:qualify_pos].strip()

        # 清理 \r 字符
        before_qualify = before_qualify.replace('\r', ' ')
        qualify_condition = qualify_condition.replace('\r', ' ')

        # 检查 QUALIFY 条件是否包含窗口函数 (OVER 关键字)
        if re.search(r'\bOVER\b', qualify_condition, re.IGNORECASE):
            # 包含窗口函数: 需要嵌套子查询
            # 注意: 外层不能用 SELECT *，否则会包含 _qualify_cond 列
            # 方案: 先提取内层 SELECT 的列列表，外层只选这些列
            inner_select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM\b', before_qualify, re.IGNORECASE | re.DOTALL)
            if inner_select_match:
                inner_cols = inner_select_match.group(1).strip()
                # 如果内层是 SELECT *，外层也用 SELECT * 但通过子查询排除 _qualify_cond
                if inner_cols.strip() == '*':
                    result = (_QUALIFY_WINDOW_STAR_TPL
                              .replace('{before}', before_qualify)
                              .replace('{cond}', qualify_condition))
                else:
                    result = (_QUALIFY_WINDOW_COLS_TPL
                              .replace('{cols}', inner_cols)
                              .replace('{before}', before_qualify)
                              .replace('{cond}', qualify_condition))
            else:
                # 回退方案: 使用 SELECT * EXCEPT 排除 _qualify_cond
                result = (_QUALIFY_WINDOW_STAR_TPL
                          .replace('{before}', before_qualify)
                          .replace('{cond}', qualify_condition))
        else:
            # 不包含窗口函数: 直接将 QUALIFY 条件作为外层 WHERE
            result = (_QUALIFY_SIMPLE_TPL
                      .replace('{before}', before_qualify)
                      .replace('{cond}', qualify_condition))

        return result

    @classmethod
    def _convert_functions(cls, sql: str) -> str:
        """转换 Teradata 函数到 PostgreSQL 等价函数"""

        # ZEROIFNULL(expr) → COALESCE(expr, 0)
        sql = cls._replace_func_with_extra_arg(sql, 'ZEROIFNULL', 'COALESCE', '0')
        # NULLIFZERO(expr) → NULLIF(expr, 0)
        sql = cls._replace_func_with_extra_arg(sql, 'NULLIFZERO', 'NULLIF', '0')

        # NVL(expr, default) → COALESCE(expr, default)
        sql = re.sub(r'\bNVL\s*\(', 'COALESCE(', sql, flags=re.IGNORECASE)

        # SUBSTR → SUBSTRING
        sql = re.sub(r'\bSUBSTR\s*\(', 'SUBSTRING(', sql, flags=re.IGNORECASE)

        # INDEX(str, substr) → STRPOS(str, substr)
        sql = re.sub(r'\bINDEX\s*\(', 'STRPOS(', sql, flags=re.IGNORECASE)

        # CHARACTERS / CHARS / CHAR_LENGTH → LENGTH
        sql = re.sub(r'\b(?:CHARACTERS|CHARS|CHAR_LENGTH)\s*\(', 'LENGTH(', sql, flags=re.IGNORECASE)

        # LASTDAY → LAST_DAY
        sql = re.sub(r'\bLASTDAY\s*\(', 'LAST_DAY(', sql, flags=re.IGNORECASE)

        # OREPLACE → REPLACE (PostgreSQL 原生支持)
        sql = re.sub(r'\bOREPLACE\s*\(', 'REPLACE(', sql, flags=re.IGNORECASE)

        # OTRANSLATE → TRANSLATE
        sql = re.sub(r'\bOTRANSLATE\s*\(', 'TRANSLATE(', sql, flags=re.IGNORECASE)

        # DAYOFWEEK → EXTRACT(DOW FROM ...) + 1 (Teradata 1=Sunday, PG 0=Sunday)
        # DAYOFMONTH → EXTRACT(DAY FROM ...)
        # DAYOFYEAR → EXTRACT(DOY FROM ...)
        # 这些需要特殊处理，暂时用简单替换
        sql = re.sub(r'\bDAYOFMONTH\s*\(', 'EXTRACT(DAY FROM ', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bDAYOFYEAR\s*\(', 'EXTRACT(DOY FROM ', sql, flags=re.IGNORECASE)

        # QUARTER → EXTRACT(QUARTER FROM ...)
        sql = re.sub(r'\bQUARTER\s*\(', 'EXTRACT(QUARTER FROM ', sql, flags=re.IGNORECASE)

        # WEEK → EXTRACT(WEEK FROM ...)
        sql = re.sub(r'\bWEEK\s*\(', 'EXTRACT(WEEK FROM ', sql, flags=re.IGNORECASE)

        # USER → CURRENT_USER
        sql = re.sub(r'\bUSER\b', 'CURRENT_USER', sql, flags=re.IGNORECASE)

        # SESSION → CURRENT_SESSION (DWS 可能不支持，用 cast 替代)
        # 保留原样，让用户手动处理

        return sql

    @classmethod
    def _add_coalesce_default(cls, sql: str, func_name: str, default: str) -> str:
        """
        为 ZEROIFNULL/NULLIFZERO 添加默认值参数 (已废弃，保留兼容)
        """
        return sql

    @classmethod
    def _replace_func_with_extra_arg(cls, sql: str, old_func: str,
                                      new_func: str, extra_arg: str) -> str:
        """
        替换函数并添加额外参数: OLD_FUNC(expr) → NEW_FUNC(expr, extra_arg)

        通过找到匹配的括号来正确处理嵌套表达式。
        """
        result = sql
        pattern = re.compile(rf'\b{old_func}\s*\(', re.IGNORECASE)

        while True:
            match = pattern.search(result)
            if not match:
                break

            # 找到函数开始位置
            func_start = match.start()
            paren_start = match.end() - 1  # '(' 的位置

            # 找到匹配的右括号
            depth = 0
            paren_end = -1
            for i in range(paren_start, len(result)):
                if result[i] == '(':
                    depth += 1
                elif result[i] == ')':
                    depth -= 1
                    if depth == 0:
                        paren_end = i
                        break

            if paren_end == -1:
                break  # 括号不匹配，跳过

            # 提取参数表达式
            args = result[paren_start + 1:paren_end]

            # 构建替换: NEW_FUNC(args, extra_arg)
            replacement = f'{new_func}({args}, {extra_arg})'

            # 执行替换
            result = result[:func_start] + replacement + result[paren_end + 1:]

        return result


    @classmethod
    def _convert_group_by_position(cls, sql: str) -> str:
        """
        转换 GROUP BY 位置引用为列名引用

        Teradata: SELECT col1, col2, SUM(col3) FROM t GROUP BY 1, 2
        PostgreSQL: SELECT col1, col2, SUM(col3) FROM t GROUP BY col1, col2
        """
        # 匹配 GROUP BY 后的数字引用
        group_by_pattern = re.compile(
            r'\bGROUP\s+BY\s+(.+?)(?=\bHAVING\b|\bORDER\s+BY\b|\bQUALIFY\b|\bLIMIT\b|;|$)',
            re.IGNORECASE | re.DOTALL
        )

        match = group_by_pattern.search(sql)
        if not match:
            return sql

        group_by_clause = match.group(1).strip()

        # 检查是否包含位置引用（纯数字）
        if not re.search(r'^\d+\s*(?:,\s*\d+\s*)*$', group_by_clause.strip()):
            return sql  # 不是位置引用，无需转换

        # 提取 SELECT 列表
        select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM\b', sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return sql

        select_list = select_match.group(1).strip()

        # 解析 SELECT 列表中的列（跳过聚合函数）
        columns = cls._parse_select_columns(select_list)

        # 解析位置引用
        positions = [int(p.strip()) for p in group_by_clause.split(',') if p.strip().isdigit()]

        # 构建新的 GROUP BY 子句
        new_group_by_cols = []
        for pos in positions:
            if 1 <= pos <= len(columns):
                col = columns[pos - 1]
                # 使用列别名或列表达式
                new_group_by_cols.append(col)

        if new_group_by_cols:
            new_group_by = 'GROUP BY ' + ', '.join(new_group_by_cols)
            sql = sql[:match.start()] + new_group_by + sql[match.end():]

        return sql

    @classmethod
    def _parse_select_columns(cls, select_list: str) -> List[str]:
        """解析 SELECT 列表，返回各列的表达式或别名"""
        columns = []
        # 简单按逗号分割（不处理嵌套括号中的逗号）
        depth = 0
        current = ''
        for char in select_list:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                columns.append(cls._extract_column_name(current.strip()))
                current = ''
            else:
                current += char
        if current.strip():
            columns.append(cls._extract_column_name(current.strip()))
        return columns

    @classmethod
    def _extract_column_name(cls, expr: str) -> str:
        """从列表达式中提取列名或别名"""
        # 检查是否有 AS 别名
        as_match = re.search(r'\bAS\s+(\w+)', expr, re.IGNORECASE)
        if as_match:
            return as_match.group(1)
        # 检查隐式别名 (expr alias)
        parts = expr.rsplit(None, 1)
        if len(parts) == 2 and not parts[1].upper() in ('FROM', 'WHERE', 'AND', 'OR'):
            # 可能是隐式别名
            if re.match(r'^\w+$', parts[1]):
                return parts[1]
        # 返回整个表达式
        return expr.strip()

    @classmethod
    def _convert_db_references(cls, sql: str, source_db: str = None,
                               target_schema: str = None) -> str:
        """
        转换数据库引用

        Teradata: "dbname"."tablename" → DWS: "schema"."tablename"
        Teradata: dbname.tablename → DWS: schema.tablename
        """
        if not source_db or not target_schema:
            return sql

        # 替换 "source_db". → "target_schema".
        sql = re.sub(
            rf'"{re.escape(source_db)}"\.',
            f'"{target_schema}".',
            sql, flags=re.IGNORECASE
        )

        # 替换 source_db. (不带引号)
        sql = re.sub(
            rf'\b{re.escape(source_db)}\.',
            f'{target_schema}.',
            sql, flags=re.IGNORECASE
        )

        return sql

    @classmethod
    def _convert_date_literals(cls, sql: str) -> str:
        """
        转换 Teradata 日期字面量

        Teradata: DATE 'YYYY-MM-DD' → PostgreSQL: DATE 'YYYY-MM-DD' (兼容)
        Teradata: 'YY/MM/DD' (DATE) → PostgreSQL: DATE 'YYYY-MM-DD'
        """
        # Teradata 格式: 'YY/MM/DD' (DATE) → DATE '19YY-MM-DD' 或 '20YY-MM-DD'
        # 简化处理：保留 DATE 'YYYY-MM-DD' 格式
        return sql

    @classmethod
    def _convert_interval(cls, sql: str) -> str:
        """
        转换 Teradata INTERVAL 语法到 PostgreSQL

        Teradata: INTERVAL '1' DAY   → PostgreSQL: INTERVAL '1 day'
        Teradata: INTERVAL '1' MONTH → PostgreSQL: INTERVAL '1 month'
        Teradata: INTERVAL '1' YEAR  → PostgreSQL: INTERVAL '1 year'
        Teradata: INTERVAL '1' HOUR  → PostgreSQL: INTERVAL '1 hour'
        Teradata: INTERVAL '1' MINUTE → PostgreSQL: INTERVAL '1 minute'
        Teradata: INTERVAL '1' SECOND → PostgreSQL: INTERVAL '1 second'
        """
        units = ['DAY', 'MONTH', 'YEAR', 'HOUR', 'MINUTE', 'SECOND',
                 'DAYS', 'MONTHS', 'YEARS', 'HOURS', 'MINUTES', 'SECONDS']
        for unit in units:
            # INTERVAL 'N' UNIT → INTERVAL 'N unit'
            pattern = rf"INTERVAL\s*'(\d+)'\s*{unit}"
            pg_unit = unit.lower().rstrip('s')  # 去掉复数
            sql = re.sub(pattern, f"INTERVAL '\\1 {pg_unit}'", sql, flags=re.IGNORECASE)

        return sql

    @classmethod
    def _convert_cast(cls, sql: str) -> str:
        """
        转换 CAST 表达式

        Teradata: CAST(expr AS INTEGER) → PostgreSQL: CAST(expr AS INTEGER)
        Teradata: expr (INTEGER) → PostgreSQL: CAST(expr AS INTEGER)
        """
        # 转换 Teradata 隐式类型转换: expr (type) → CAST(expr AS type)
        td_types = [
            'INTEGER', 'INT', 'SMALLINT', 'BIGINT', 'BYTEINT',
            'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL', 'DOUBLE PRECISION',
            'VARCHAR', 'CHAR', 'DATE', 'TIME', 'TIMESTAMP',
            'CLOB', 'BLOB', 'BYTE', 'VARBYTE'
        ]

        # 匹配 expr (TYPE) 模式 — 但要避免匹配函数调用
        # 这是一个复杂的问题，简化处理
        for td_type in td_types:
            # 匹配 ... ) (TYPE) 模式
            pattern = rf'\)\s*\(\s*{td_type}(?:\(\d+(?:,\d+)?\))?\s*\)'
            # 这个模式有误报风险，暂时跳过隐式转换
            pass

        return sql

    @classmethod
    def _convert_string_concat(cls, sql: str) -> str:
        """
        转换字符串连接操作

        Teradata: 'a' || 'b' → PostgreSQL: 'a' || 'b' (兼容)
        无需转换，PostgreSQL 也支持 ||
        """
        return sql


# ============================================================
# 宏转换器
# ============================================================

