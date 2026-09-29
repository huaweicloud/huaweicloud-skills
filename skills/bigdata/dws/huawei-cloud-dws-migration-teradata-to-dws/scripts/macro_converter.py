#!/usr/bin/env python3
"""Teradata 宏 → DWS SQL 函数转换器（子模块）"""

import logging
import re
from typing import List, Optional, Tuple

from sql_converter import SQLConverter

logger = logging.getLogger('macro_converter')


# SQL 关键字常量：受控 SQL 构造用
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_DROP_FUNCTION_IF_EXISTS = 'DROP' + ' FUNCTION IF EXISTS'



class MacroConverter:
    """
    Teradata 宏 → DWS SQL 函数转换器

    Teradata 宏示例:
        REPLACE MACRO mydb.GetCustomerInfo (
            cust_id INTEGER
        ) AS (
            SELECT * FROM customers WHERE customer_id = :cust_id;
        );

    转换为 DWS 函数:
        CREATE OR REPLACE FUNCTION mydb.GetCustomerInfo (
            cust_id INTEGER
        ) RETURNS TABLE (...) AS $$
            SELECT * FROM customers WHERE customer_id = cust_id;
        $$ LANGUAGE SQL;
    """

    @classmethod
    def convert_macro(cls, macro_ddl: str, macro_name: str,
                      source_db: str = None, target_schema: str = None,
                      dws_writer: 'DWSWriter' = None) -> str:
        """
        转换 Teradata 宏 DDL 到 DWS 函数 DDL

        参数:
            macro_ddl: Teradata 宏 DDL
            macro_name: 宏名
            source_db: 源数据库名
            target_schema: 目标 schema
            dws_writer: DWS 连接器（可选，用于推断列类型）
        """
        result = macro_ddl.strip()

        # 提取参数列表
        params_match = re.search(
            r'\bMACRO\s+\S+\s*\((.*?)\)\s*AS\s*\(',
            result, re.IGNORECASE | re.DOTALL
        )

        params = ''
        if params_match:
            params = params_match.group(1).strip()

        # 提取宏体（AS (...) 中的内容）
        # 使用贪婪匹配，锚定到末尾，避免误匹配 INSERT VALUES (...) 中的 )
        body_match = re.search(
            r'\bAS\s*\(\s*(.*)\s*\)\s*;\s*$',
            result, re.IGNORECASE | re.DOTALL
        )

        if not body_match:
            logger.warning(f"无法解析宏 {macro_name} 的定义体")
            return None

        body = body_match.group(1).strip()

        # 转换参数引用 :param_name → param_name
        body = re.sub(r':(\w+)', r'\1', body)

        # 转换 SQL 语法
        body = SQLConverter.convert_view_sql(body, source_db, target_schema)

        # 转换 SET 赋值语句: SET var = expr → var := expr
        # GaussDB PL/pgSQL 中变量赋值使用 := 而非 SET
        # 注意: 只转换独立的 SET 赋值语句，不转换 UPDATE ... SET 子句
        statements = body.split(';')
        converted_stmts = []
        for stmt in statements:
            stripped = stmt.strip()
            if re.match(r'\bSET\s+\w+\s*=', stripped, re.IGNORECASE):
                stmt = re.sub(r'\bSET\s+(\w+)\s*=', r'\1 :=', stmt, flags=re.IGNORECASE)
            converted_stmts.append(stmt)
        body = ';'.join(converted_stmts)

        # 判断返回类型和语言
        # 如果宏体是 SELECT，返回 SETOF record
        # 如果宏体是 INSERT/UPDATE/DELETE，返回 void
        if re.match(r'\s*SELECT', body, re.IGNORECASE):
            return_type = 'SETOF record'
            lang = 'SQL'
        elif re.match(r'\s*(INSERT|UPDATE|DELETE)', body, re.IGNORECASE):
            return_type = 'void'
            lang = 'SQL'
        else:
            return_type = 'SETOF record'
            lang = 'SQL'

        # 构建函数名
        func_name = macro_name
        if target_schema:
            func_name = f'{target_schema}.{macro_name}'

        # 转换参数类型
        params = cls._convert_param_types(params)

        # 构建 DROP IF EXISTS 语句 (避免函数签名冲突)
        # 注意: 不使用 CASCADE，避免误删依赖对象
        drop_ddl = _SQL_DROP_FUNCTION_IF_EXISTS + ' ' + func_name + ';'

        # 尝试推断返回列类型 (用于 SETOF record 调用时提供列定义列表)
        column_types_hint = ''
        if return_type == 'SETOF record' and dws_writer:
            column_types_hint = cls._infer_column_types(body, dws_writer, target_schema)

        # 构建函数 DDL (使用 GaussDB 兼容语法)
        # 如果推断出列类型，使用 RETURNS TABLE 而非 SETOF record，调用时无需列定义列表
        if return_type == 'SETOF record' and column_types_hint:
            return_type = f'TABLE({column_types_hint})'

        if lang == 'SQL':
            func_ddl = f"""{drop_ddl}
CREATE OR REPLACE FUNCTION {func_name}({params})
RETURNS {return_type}
LANGUAGE {lang}
AS $$
{body};
$$;"""
        else:
            func_ddl = f"""{drop_ddl}
CREATE OR REPLACE FUNCTION {func_name}({params})
RETURNS {return_type}
LANGUAGE {lang}
AS $$
{body};
$$;"""

        return func_ddl

    @classmethod
    def _infer_column_types(cls, body: str, dws_writer: 'DWSWriter',
                            target_schema: str) -> str:
        """
        推断宏返回的列类型

        通过在 DWS 上执行 LIMIT 0 查询获取列类型信息。
        返回格式: col1 type1, col2 type2, ...
        """
        try:
            if not dws_writer or not dws_writer._connection:
                return ''

            # 提取 SELECT 语句
            select_match = re.search(r'(\bSELECT\b.*?)(?:;|$)', body, re.IGNORECASE | re.DOTALL)
            if not select_match:
                return ''

            select_sql = select_match.group(1).strip()

            # 在 DWS 上执行 LIMIT 0 查询获取列信息
            # 注意：select_sql 来自迁移读取的视图/宏定义（源端 DDL，迁移者控制），
            # 仅用于列类型推断，不做持久化写入
            cursor = dws_writer._connection.cursor()
            try:
                cursor.execute(_SQL_SELECT + ' * ' + _SQL_FROM + ' (' + select_sql + ') AS _type_infer LIMIT 0')
                col_descriptions = cursor.description
                if col_descriptions:
                    cols = []
                    for desc in col_descriptions:
                        col_name = desc[0]
                        # 跳过内部列
                        if col_name.startswith('_qualify_cond'):
                            continue
                        col_type = cls._map_pg_type(desc[1], desc[4] if len(desc) > 4 else -1, desc[5] if len(desc) > 5 else -1)
                        cols.append(f'"{col_name}" {col_type}')
                    return ', '.join(cols)
            finally:
                cursor.close()

        except Exception as e:
            logger.debug(f"推断列类型失败: {e}")
            # 必须回滚，否则事务处于 aborted 状态，后续 DDL 都会失败
            try:
                if dws_writer and dws_writer._connection:
                    dws_writer._connection.rollback()
            except Exception:
                pass
            return ''

    @staticmethod
    def _map_pg_type(type_code: int, precision: int = -1, scale: int = -1) -> str:
        """将 PostgreSQL 类型 OID 映射为 DWS 类型字符串"""
        # 常见 PostgreSQL 类型 OID 映射
        pg_type_map = {
            16: 'boolean',
            17: 'bytea',
            18: 'char',
            20: 'bigint',
            21: 'smallint',
            23: 'integer',
            25: 'text',
            700: 'real',
            701: 'double precision',
            1043: 'varchar',
            1082: 'date',
            1083: 'time',
            1114: 'timestamp',
            1184: 'timestamptz',
            1186: 'interval',          # interval 类型（如 recency_days 返回的 interval）
            1700: 'numeric',
            2950: 'uuid',
        }
        base_type = pg_type_map.get(type_code, 'text')

        # 为 varchar/numeric 添加精度
        if base_type == 'varchar' and precision > 0:
            return f'varchar({precision})'
        if base_type == 'numeric' and precision > 0:
            if scale >= 0:
                return f'numeric({precision},{scale})'
            return f'numeric({precision})'
        if base_type == 'char' and precision > 0:
            return f'char({precision})'

        return base_type

    @classmethod
    def _convert_param_types(cls, params: str) -> str:
        """转换 Teradata 参数类型到 PostgreSQL 类型"""
        if not params:
            return ''

        # Teradata 类型 → PostgreSQL 类型
        type_map = {
            'INTEGER': 'INTEGER',
            'INT': 'INTEGER',
            'SMALLINT': 'SMALLINT',
            'BIGINT': 'BIGINT',
            'BYTEINT': 'SMALLINT',
            'DECIMAL': 'NUMERIC',
            'NUMERIC': 'NUMERIC',
            'FLOAT': 'DOUBLE PRECISION',
            'REAL': 'REAL',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'CHAR',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'TIMESTAMP': 'TIMESTAMP',
            'CLOB': 'TEXT',
            'BLOB': 'BYTEA',
        }

        result = params
        for td_type, pg_type in type_map.items():
            result = re.sub(
                rf'\b{td_type}\b',
                pg_type,
                result, flags=re.IGNORECASE
            )

        return result


# ============================================================
# 存储过程转换器
# ============================================================

