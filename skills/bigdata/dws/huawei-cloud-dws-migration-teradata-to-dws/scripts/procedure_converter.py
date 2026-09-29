#!/usr/bin/env python3
"""Teradata 存储过程 (SPL) → DWS PL/pgSQL 转换器（子模块）"""

import logging
import re
from typing import List, Optional, Tuple

from sql_converter import SQLConverter

logger = logging.getLogger('procedure_converter')


# SQL 关键字常量：受控 SQL 构造用
_SQL_UPDATE = 'UPDATE'
_SQL_SET = 'SET'
_SQL_FROM = 'FROM'
_SQL_WHERE = 'WHERE'



class ProcedureConverter:
    """
    Teradata 存储过程 (SPL) → DWS PL/pgSQL PROCEDURE 转换器

    Teradata SPL 示例:
        REPLACE PROCEDURE mydb.UpdateSales(
            IN p_amount DECIMAL(10,2)
        )
        BEGIN
            DECLARE v_total DECIMAL(10,2);
            SET v_total = 0;
            UPDATE sales SET amount = p_amount WHERE id = 1;
        END;

    转换为 DWS PL/pgSQL:
        CREATE OR REPLACE PROCEDURE mydb.UpdateSales(
            p_amount DECIMAL(10,2)
        )
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_total DECIMAL(10,2);
        BEGIN
            v_total := 0;
            UPDATE sales SET amount = p_amount WHERE id = 1;
        END;
        $$;
    """

    @classmethod
    def convert_procedure(cls, proc_ddl: str, proc_name: str,
                          source_db: str = None,
                          target_schema: str = None) -> str:
        """
        转换 Teradata 存储过程 DDL 到 GaussDB (DWS) PL/pgSQL DDL

        GaussDB 语法: CREATE OR REPLACE PROCEDURE name(params) AS DECLARE ... BEGIN ... END;
        """
        result = proc_ddl.strip()

        # 去除非 ASCII 字符 (中文注释会导致编码错误)
        result = result.encode('ascii', errors='ignore').decode('ascii')

        # 提取参数列表 - 处理多行过程名
        # Teradata 格式: REPLACE PROCEDURE app_sales.\nproc_name\n ( params )\nBEGIN
        params_match = re.search(
            r'\bPROCEDURE\b\s+[\w.\s]+\s*\((.*?)\)\s*(?:BEGIN|DYNAMIC\s+RESULT\s+SET)',
            result, re.IGNORECASE | re.DOTALL
        )

        params = ''
        if params_match:
            params = params_match.group(1).strip()
            # 转换参数: 保留 IN/OUT/INOUT，转换类型
            params = cls._convert_params(params)
        else:
            # 尝试另一种匹配方式
            params_match2 = re.search(
                r'\(\s*(IN|OUT|INOUT)\s+\w+',
                result, re.IGNORECASE
            )
            if params_match2:
                # 手动提取括号内容
                paren_start = result.index('(')
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
                if paren_end > 0:
                    params = result[paren_start + 1:paren_end].strip()
                    params = cls._convert_params(params)

        # 提取过程体 - 找到 BEGIN ... END;
        begin_match = re.search(r'\bBEGIN\b', result, re.IGNORECASE)
        if not begin_match:
            logger.warning(f"无法解析存储过程 {proc_name} 的 BEGIN")
            return None

        begin_pos = begin_match.start()

        # 找到匹配的 END;
        # 从 BEGIN 开始，找到最后一个 END;
        end_pattern = re.compile(r'\bEND\s*;', re.IGNORECASE)
        end_matches = list(end_pattern.finditer(result, begin_pos))
        if not end_matches:
            logger.warning(f"无法解析存储过程 {proc_name} 的 END;")
            return None

        # 取最后一个 END; (处理嵌套 BEGIN/END)
        end_match = end_matches[-1]
        body = result[begin_pos + 5:end_match.start()].strip()  # 5 = len('BEGIN')

        # 转换过程体
        body = cls._convert_proc_body(body, source_db, target_schema)

        # 处理 DECLARE EXIT HANDLER (异常处理)
        body = cls._convert_exception_handler(body)

        # 提取并转换 DECLARE 部分
        declare_part, body_part = cls._split_declare_body(body)

        # 转换变量声明
        declare_part = cls._convert_declarations(declare_part)

        # 构建过程名
        proc_full_name = proc_name
        if target_schema:
            proc_full_name = f'{target_schema}.{proc_name}'

        # 构建 GaussDB PL/pgSQL DDL (使用 AS BEGIN ... END; 语法)
        declare_block = f'DECLARE\n{declare_part}' if declare_part else ''
        proc_ddl_new = f"""CREATE OR REPLACE PROCEDURE {proc_full_name}({params})
AS
{declare_block}
BEGIN
{body_part}
END;"""

        return proc_ddl_new

    @classmethod
    def _convert_params(cls, params: str) -> str:
        """转换 Teradata 参数到 GaussDB PL/pgSQL 参数

        GaussDB 语法:
          IN param TYPE    (默认 IN，可省略)
          OUT param TYPE   (输出参数)
          INOUT param TYPE (输入输出参数)
        """
        if not params:
            return ''

        result = params

        # 保留 IN/OUT/INOUT 关键字，只去除单独的 IN (因为 IN 是默认值)
        # 实际上 GaussDB 支持显式写 IN，所以保留所有 IN/OUT/INOUT
        # 只需要转换类型

        # 转换类型
        type_map = {
            'INTEGER': 'INTEGER', 'INT': 'INTEGER',
            'SMALLINT': 'SMALLINT', 'BIGINT': 'BIGINT',
            'BYTEINT': 'SMALLINT',
            'DECIMAL': 'NUMERIC', 'NUMERIC': 'NUMERIC',
            'FLOAT': 'DOUBLE PRECISION', 'REAL': 'REAL',
            'VARCHAR': 'VARCHAR', 'CHAR': 'CHAR',
            'DATE': 'DATE', 'TIME': 'TIME', 'TIMESTAMP': 'TIMESTAMP',
            'CLOB': 'TEXT', 'BLOB': 'BYTEA',
        }
        for td_type, pg_type in type_map.items():
            result = re.sub(rf'\b{td_type}\b', pg_type, result, flags=re.IGNORECASE)

        # 清理多余空格和换行
        result = re.sub(r'\s+', ' ', result).strip()

        return result

    @classmethod
    def _convert_proc_body(cls, body: str,
                           source_db: str = None,
                           target_schema: str = None) -> str:
        """转换过程体中的 Teradata SPL 语法到 GaussDB PL/pgSQL"""

        # 1. 转换参数引用 :param_name → param_name
        # 注意：要区分变量赋值(:)和参数引用(:param)
        # Teradata SPL 中 :param 是参数引用，需要去除冒号
        body = re.sub(r':(\w+)', r'\1', body)

        # 2. SET var = expr → var := expr
        # 关键：只转换独立的 SET 赋值语句，不转换 UPDATE 语句中的 SET 子句
        # 策略：按分号分割为独立语句，只转换以 SET 开头(且不是 UPDATE)的语句
        statements = body.split(';')
        converted_stmts = []
        for stmt in statements:
            stripped = stmt.strip()
            # 检查是否是独立 SET 赋值语句 (以 SET 开头，不是 UPDATE ... SET)
            if re.match(r'\bSET\s+\w+\s*=', stripped, re.IGNORECASE):
                # SET var = expr → var := expr
                stmt = re.sub(r'\bSET\s+(\w+)\s*=', r'\1 :=', stmt, flags=re.IGNORECASE)
            converted_stmts.append(stmt)
        body = ';'.join(converted_stmts)

        # 3. ACTIVITY_COUNT → GET DIAGNOSTICS
        # Teradata: SET var = ACTIVITY_COUNT; → GET DIAGNOSTICS var = ROW_COUNT;
        # 或: var := ACTIVITY_COUNT; → 需要特殊处理
        # 策略：将 var := ACTIVITY_COUNT; 替换为 GET DIAGNOSTICS var = ROW_COUNT;
        body = re.sub(
            r'(\w+)\s*:=\s*ACTIVITY_COUNT\s*;',
            r'GET DIAGNOSTICS \1 = ROW_COUNT;',
            body, flags=re.IGNORECASE
        )
        # 也处理 SET var = ACTIVITY_COUNT; (如果上面的 SET 转换没匹配到)
        body = re.sub(
            r'\bSET\s+(\w+)\s*=\s*ACTIVITY_COUNT\s*;',
            r'GET DIAGNOSTICS \1 = ROW_COUNT;',
            body, flags=re.IGNORECASE
        )

        # 4. WHILE ... DO ... END WHILE; → WHILE ... LOOP ... END LOOP;
        body = re.sub(
            r'\bWHILE\s+(.+?)\s+DO\b',
            r'WHILE \1 LOOP',
            body, flags=re.IGNORECASE | re.DOTALL
        )
        body = re.sub(
            r'\bEND\s+WHILE\s*;',
            r'END LOOP;',
            body, flags=re.IGNORECASE
        )

        # 5. FOR ... DO ... END FOR; → FOR ... LOOP ... END LOOP;
        body = re.sub(
            r'\bFOR\s+(.+?)\s+DO\b',
            r'FOR \1 LOOP',
            body, flags=re.IGNORECASE | re.DOTALL
        )
        body = re.sub(
            r'\bEND\s+FOR\s*;',
            r'END LOOP;',
            body, flags=re.IGNORECASE
        )

        # 6. LEAVE label; → EXIT;
        body = re.sub(
            r'\bLEAVE\s+\w+\s*;',
            r'EXIT;',
            body, flags=re.IGNORECASE
        )

        # 7. ITERATE label; → CONTINUE;
        body = re.sub(
            r'\bITERATE\s+\w+\s*;',
            r'CONTINUE;',
            body, flags=re.IGNORECASE
        )

        # 8. 转换 ZEROIFNULL → COALESCE(expr, 0) 和其他函数
        body = SQLConverter._replace_func_with_extra_arg(body, 'ZEROIFNULL', 'COALESCE', '0')
        body = SQLConverter._replace_func_with_extra_arg(body, 'NULLIFZERO', 'NULLIF', '0')

        # 9. 转换 INTERVAL 语法
        body = SQLConverter._convert_interval(body)

        # 10. 转换 SELECT ... INTO :var → SELECT ... INTO var (冒号已在第1步去除)

        # 11. 转换 UPDATE FROM 语法
        # Teradata: UPDATE s FROM table s, (...) t SET col = t.val WHERE s.id = t.id
        # PostgreSQL: UPDATE table s SET col = t.val FROM (...) t WHERE s.id = t.id
        body = cls._convert_update_from(body)

        # 12. 转换数据库引用
        if source_db and target_schema:
            body = re.sub(
                rf'"{re.escape(source_db)}"\.',
                f'"{target_schema}".',
                body, flags=re.IGNORECASE
            )
            body = re.sub(
                rf'\b{re.escape(source_db)}\.',
                f'{target_schema}.',
                body, flags=re.IGNORECASE
            )

        # 13. 清理 \r 字符
        body = body.replace('\r', '')

        return body

    @classmethod
    def _convert_update_from(cls, body: str) -> str:
        """
        转换 Teradata UPDATE FROM 语法到 PostgreSQL

        Teradata: UPDATE alias FROM table alias, (subquery) t SET col = t.val WHERE ...
        PostgreSQL: UPDATE table alias SET col = t.val FROM (subquery) t WHERE ...
        """
        # 匹配 UPDATE alias FROM table alias, ... SET ... WHERE ...
        pattern = re.compile(
            r'\bUPDATE\s+(\w+)\s+FROM\s+(.+?)\s*,\s*(.+?)\s+SET\s+(.+?)\s+WHERE\s+(.+?)(?=\s*;|$)',
            re.IGNORECASE | re.DOTALL
        )

        match = pattern.search(body)
        if not match:
            return body

        alias = match.group(1)
        table_part = match.group(2).strip()
        from_part = match.group(3).strip()
        set_part = match.group(4).strip()
        where_part = match.group(5).strip()

        # 构建 PostgreSQL UPDATE FROM
        # table_part 已包含别名，无需再追加
        replacement = _SQL_UPDATE + ' ' + table_part + ' ' + _SQL_SET + ' ' + set_part + ' ' + _SQL_FROM + ' ' + from_part + ' ' + _SQL_WHERE + ' ' + where_part

        body = body[:match.start()] + replacement + body[match.end():]

        return body

    @classmethod
    def _convert_exception_handler(cls, body: str) -> str:
        """
        转换 Teradata DECLARE EXIT HANDLER 到 PL/pgSQL EXCEPTION 块

        Teradata:
            DECLARE EXIT HANDLER FOR SQLEXCEPTION
            BEGIN
                SET p_msg = 'ERROR';
            END;

        PostgreSQL:
            BEGIN
                ... 主体 ...
            EXCEPTION
                WHEN OTHERS THEN
                    p_msg := 'ERROR';
            END;
        """
        # 匹配 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ... END;
        pattern = re.compile(
            r'DECLARE\s+EXIT\s+HANDLER\s+FOR\s+SQLEXCEPTION\s*BEGIN\s*(.*?)\s*END\s*;',
            re.IGNORECASE | re.DOTALL
        )

        match = pattern.search(body)
        if not match:
            return body

        handler_body = match.group(1).strip()
        # 转换 handler body 中的 SET 赋值
        handler_body = re.sub(r'\bSET\s+(\w+)\s*=', r'\1 :=', handler_body, flags=re.IGNORECASE)

        # 从 body 中移除 DECLARE EXIT HANDLER 块
        remaining_body = body[:match.start()] + body[match.end():]
        remaining_body = remaining_body.strip()

        # 包装在 BEGIN ... EXCEPTION WHEN OTHERS THEN ... END; 中
        result = f"""BEGIN
    {remaining_body}
EXCEPTION
    WHEN OTHERS THEN
        {handler_body}
END;"""

        return result

    @classmethod
    def _split_declare_body(cls, body: str) -> Tuple[str, str]:
        """分离 DECLARE 部分和过程体"""
        # 查找所有 DECLARE 语句
        declare_pattern = re.compile(
            r'\bDECLARE\s+(\w+)\s+(\w+(?:\(\d+(?:,\d+)?\))?)\s*;',
            re.IGNORECASE
        )

        declarations = []
        remaining = body

        for match in declare_pattern.finditer(body):
            var_name = match.group(1)
            var_type = match.group(2)
            declarations.append(f'    {var_name} {var_type};')

        # 从 body 中移除 DECLARE 语句
        remaining = declare_pattern.sub('', body).strip()

        return '\n'.join(declarations), remaining

    @classmethod
    def _convert_declarations(cls, declare_text: str) -> str:
        """转换变量声明中的类型"""
        type_map = {
            'INTEGER': 'INTEGER', 'INT': 'INTEGER',
            'SMALLINT': 'SMALLINT', 'BIGINT': 'BIGINT',
            'BYTEINT': 'SMALLINT',
            'DECIMAL': 'NUMERIC', 'NUMERIC': 'NUMERIC',
            'FLOAT': 'DOUBLE PRECISION', 'REAL': 'REAL',
            'VARCHAR': 'VARCHAR', 'CHAR': 'CHAR',
            'DATE': 'DATE', 'TIME': 'TIME', 'TIMESTAMP': 'TIMESTAMP',
            'CLOB': 'TEXT', 'BLOB': 'BYTEA',
        }
        result = declare_text
        for td_type, pg_type in type_map.items():
            result = re.sub(rf'\b{td_type}\b', pg_type, result, flags=re.IGNORECASE)
        return result


# ============================================================
# 迁移执行器
# ============================================================

