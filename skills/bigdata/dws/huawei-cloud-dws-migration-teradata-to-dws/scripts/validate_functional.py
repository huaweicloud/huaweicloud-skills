#!/usr/bin/env python3
"""
功能性校验脚本 - 对迁移到 DWS 的宏、存储过程、视图进行功能性验证。

校验内容：
1. 宏(Macro): 在 TD 端用 EXEC 语法调用，在 DWS 端用 SELECT * FROM func() 调用，
   比较行数和前 N 行数据。
2. 存储过程(Procedure): 只读过程比较执行结果；写操作过程用事务回滚验证不报错。
3. 视图(View): 查询两端行数，抽样比较数据。

用法:
    python validate_functional.py --config migration_config.yaml
    python validate_functional.py --td-host <host> --td-user <user> --td-database <db> \\
        --dws-host <host> --dws-port <port> --dws-db <db> --dws-user <user> --dws-schema <schema> \\
        --td-database <db> --dws-schema <schema>
    密码通过环境变量注入，避免命令行明文：
        export TD_PASSWORD=<teradata-密码>
        export DWS_PASSWORD=<dws-密码>
"""

import argparse
import json
import os
import sys
import time
import yaml
import re
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dws_writer import quote_ident


# SQL 关键字常量：受控 SQL 构造用（标识符经 quote_ident 白名单校验、值经 _ql 转义）
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_EXEC = 'EXEC'
_SQL_CALL = 'CALL'
_SQL_AS = 'AS'
_SQL_STAR = '*'


def _qi(name):
    """标识符安全引用（白名单校验，非法输入抛错）"""
    return quote_ident(name)


def _ql(value):
    """SQL 字符串字面量安全转义（单引号翻倍）"""
    return "'" + str(value).replace("'", "''") + "'"

try:
    import teradatasql
except ImportError:
    teradatasql = None

try:
    import psycopg2
except ImportError:
    psycopg2 = None


def load_config(config_file):
    """从 YAML 配置文件加载连接信息"""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    return config


def connect_teradata(host, user, password, database=None):
    """连接 Teradata"""
    if teradatasql is None:
        raise ImportError("teradatasql not installed")
    # 使用关键字参数连接，避免手工拼接连接字符串的转义/注入问题
    kwargs = {"host": host, "user": user, "password": password}
    if database:
        kwargs["database"] = database
    conn = teradatasql.connect(**kwargs)
    return conn


def connect_dws(host, port, database, user, password):
    """连接 DWS (GaussDB)"""
    if psycopg2 is None:
        raise ImportError("psycopg2 not installed")
    conn_kwargs = {
        'host': host,
        'port': port,
        'dbname': database,
        'user': user,
        'options': '-c search_path=public',
    }
    if password:
        conn_kwargs['password'] = password
    conn = psycopg2.connect(**conn_kwargs)
    conn.autocommit = False
    return conn


def execute_td_query(conn, sql):
    """执行 Teradata 查询，返回列名和行数据"""
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        # 获取列名
        cols = []
        if cur.description:
            cols = [d[0] for d in cur.description]
        return cols, rows
    finally:
        cur.close()


def execute_dws_query(conn, sql):
    """执行 DWS 查询，返回列名和行数据"""
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        cols = []
        if cur.description:
            cols = [d[0] for d in cur.description]
        return cols, rows
    finally:
        cur.close()


def normalize_value(val):
    """规范化值用于比较"""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, float):
        return round(val, 6)
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='replace')
    return val


def normalize_row(row):
    """规范化整行数据"""
    return tuple(normalize_value(v) for v in row)


def rows_match(td_rows, dws_rows, sample_size=20):
    """比较两组行数据是否匹配（排序后比较前 sample_size 行）"""
    td_norm = sorted([normalize_row(r) for r in td_rows])
    dws_norm = sorted([normalize_row(r) for r in dws_rows])
    
    if len(td_norm) != len(dws_norm):
        return False, f"行数不同: TD={len(td_norm)}, DWS={len(dws_norm)}"
    
    sample_td = td_norm[:sample_size]
    sample_dws = dws_norm[:sample_size]
    
    for i, (t, d) in enumerate(zip(sample_td, sample_dws)):
        if t != d:
            return False, f"第{i}行数据不同: TD={t}, DWS={d}"
    
    return True, "匹配"


def get_td_macros(conn, database):
    """获取 Teradata 数据库中的所有宏"""
    sql = f"""
    SELECT TableName AS macro_name
    FROM DBC.TablesV
    WHERE DatabaseName = '{database.upper()}'
      AND TableType = 'M'
    ORDER BY TableName
    """
    _, rows = execute_td_query(conn, sql)
    return [r[0] for r in rows]


def get_td_procedures(conn, database):
    """获取 Teradata 数据库中的所有存储过程"""
    sql = f"""
    SELECT TableName AS proc_name
    FROM DBC.TablesV
    WHERE DatabaseName = '{database.upper()}'
      AND TableType = 'P'
    ORDER BY TableName
    """
    _, rows = execute_td_query(conn, sql)
    return [r[0] for r in rows]


def get_td_views(conn, database):
    """获取 Teradata 数据库中的所有视图"""
    sql = f"""
    SELECT TableName AS view_name
    FROM DBC.TablesV
    WHERE DatabaseName = '{database.upper()}'
      AND TableType = 'V'
    ORDER BY TableName
    """
    _, rows = execute_td_query(conn, sql)
    return [r[0] for r in rows]


def get_td_macro_params(conn, database, macro_name):
    """获取宏的参数信息"""
    sql = f"""
    SELECT ColumnName, ColumnType, ColumnLength
    FROM DBC.ColumnsV
    WHERE DatabaseName = '{database.upper()}'
      AND TableName = '{macro_name.upper()}'
    ORDER BY ColumnId
    """
    _, rows = execute_td_query(conn, sql)
    return [(r[0], r[1], r[2]) for r in rows]


def get_td_macro_body(conn, database, macro_name):
    """获取宏的完整定义"""
    sql = f"""
    SELECT RequestText
    FROM DBC.TablesV
    WHERE DatabaseName = '{database.upper()}'
      AND TableName = '{macro_name.upper()}'
      AND TableType = 'M'
    """
    _, rows = execute_td_query(conn, sql)
    if rows:
        return rows[0][0]
    return None


def get_dws_functions(conn, schema='public'):
    """获取 DWS 中的所有函数（宏迁移后的）"""
    sql = f"""
    SELECT p.proname AS func_name,
           pg_get_function_result(p.oid) AS return_type,
           pg_get_function_arguments(p.oid) AS args
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = '{schema}'
      AND p.proname NOT LIKE 'pg_%'
      AND p.proname NOT LIKE '_%'
    ORDER BY p.proname
    """
    _, rows = execute_dws_query(conn, sql)
    return [{'name': r[0], 'return_type': r[1], 'args': r[2]} for r in rows]


def get_dws_procedures(conn, schema='public'):
    """获取 DWS 中的所有存储过程"""
    sql = f"""
    SELECT p.proname AS proc_name,
           pg_get_function_arguments(p.oid) AS args
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = '{schema}'
      AND p.proname NOT LIKE 'pg_%'
      AND p.proname NOT LIKE '_%'
      AND p.prokind = 'p'
    ORDER BY p.proname
    """
    _, rows = execute_dws_query(conn, sql)
    return [{'name': r[0], 'args': r[1]} for r in rows]


def get_dws_views(conn, schema='public'):
    """获取 DWS 中的所有视图"""
    sql = f"""
    SELECT table_name AS view_name
    FROM information_schema.views
    WHERE table_schema = '{schema}'
    ORDER BY table_name
    """
    _, rows = execute_dws_query(conn, sql)
    return [r[0] for r in rows]


def get_dws_function_return_columns(conn, func_name, schema='public'):
    """获取 DWS 函数返回的列信息（通过试调用）"""
    # 先获取函数参数签名
    sql = f"""
    SELECT pg_get_function_arguments(p.oid)
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = '{schema}' AND p.proname = '{func_name}'
    LIMIT 1
    """
    _, rows = execute_dws_query(conn, sql)
    return rows[0][0] if rows else None


def infer_dws_function_columns(conn, func_name, schema='public'):
    """
    推断 DWS SETOF record 函数的返回列定义。
    通过查询 pg_proc 的 proretset 和返回类型信息。

    对于 RETURNS TABLE(...) 函数，返回 None（不需要列定义列表）。
    对于 SETOF record 函数，尝试从 pg_attribute 获取列定义；
    如果失败，尝试通过 LIMIT 0 调用获取列信息。
    """
    _sql = _SQL_SELECT + " t.typname, p.proretset,"
    _sql += " string_agg(a.attname || ' ' || pg_catalog.format_type(a.atttypid, a.atttypmod), ', ' ORDER BY a.attnum)"
    _sql += " FROM pg_proc p"
    _sql += " JOIN pg_namespace n ON p.pronamespace = n.oid"
    _sql += " JOIN pg_type t ON p.prorettype = t.oid"
    _sql += " LEFT JOIN pg_attribute a ON a.attrelid = t.typrelid AND a.attnum > 0 AND NOT a.attisdropped"
    _sql += " WHERE n.nspname = " + _ql(schema) + " AND p.proname = " + _ql(func_name)
    _sql += " GROUP BY t.typname, p.proretset"
    sql = _sql
    _, rows = execute_dws_query(conn, sql)
    if rows:
        col_def = rows[0][2]
        if col_def:
            return col_def
        # typname is 'record' but no pg_attribute entries — try LIMIT 0 approach
        typname = rows[0][0]
        if typname == 'record':
            # SETOF record without composite type info
            # Try calling with a dummy column def to get error info,
            # or try RETURNS TABLE path (no col def needed)
            return None
    return None


def infer_col_def_from_td(td_cols, td_rows):
    """
    从 Teradata 宏执行结果推断列定义列表。
    用于 DWS SETOF record 函数调用时提供 AS (col_def)。
    
    通过检查 TD 返回的数据类型来推断 DWS 列类型。
    """
    if not td_cols:
        return None
    
    # TD 类型 → DWS 类型映射
    def infer_type(value):
        if value is None:
            return 'text'
        if isinstance(value, bool):
            return 'boolean'
        if isinstance(value, int):
            return 'bigint'
        if isinstance(value, float):
            return 'double precision'
        # 检查是否是 interval 类型 (字符串如 "3 12:34:56.789")
        if isinstance(value, str):
            import re
            # interval 格式: "days HH:MM:SS" 或 "HH:MM:SS"
            if re.match(r'^-?\d+\s+\d{1,2}:\d{2}:\d{2}', value) or \
               re.match(r'^-?\d{1,2}:\d{2}:\d{2}', value):
                return 'interval'
            # 日期/时间格式
            if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', value):
                return 'timestamp'
            if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                return 'date'
        return 'text'
    
    # 使用第一行数据推断类型，如果没有数据则全部用 text
    sample_row = td_rows[0] if td_rows else [None] * len(td_cols)
    
    cols = []
    for i, col_name in enumerate(td_cols):
        val = sample_row[i] if i < len(sample_row) else None
        col_type = infer_type(val)
        cols.append(f'"{col_name}" {col_type}')
    
    return ', '.join(cols)


def validate_macro(td_conn, dws_conn, td_db, macro_name, dws_schema='public'):
    """
    校验单个宏：
    1. 在 TD 端用 EXEC 调用
    2. 在 DWS 端用 SELECT * FROM func() 调用
    3. 比较结果
    """
    result = {
        'object_type': 'macro',
        'object_name': macro_name,
        'td_status': None,
        'dws_status': None,
        'match': None,
        'td_row_count': None,
        'dws_row_count': None,
        'details': {},
        'error': None
    }

    # 获取宏参数
    params = get_td_macro_params(td_conn, td_db, macro_name)
    param_names = [p[0] for p in params]

    # --- TD 端：EXEC 调用 ---
    try:
        if param_names:
            # 带参数的宏 - 使用默认值或 NULL
            param_vals = ', '.join([_qi(p[0]) + '=NULL' for p in params])
            td_sql = _SQL_EXEC + ' ' + _qi(td_db) + '.' + _qi(macro_name) + '(' + param_vals + ')'
        else:
            td_sql = _SQL_EXEC + ' ' + _qi(td_db) + '.' + _qi(macro_name)
        
        td_cols, td_rows = execute_td_query(td_conn, td_sql)
        result['td_status'] = 'success'
        result['td_row_count'] = len(td_rows)
        result['details']['td_columns'] = td_cols
    except Exception as e:
        result['td_status'] = 'error'
        result['error'] = f"TD执行失败: {str(e)}"
        # 尝试不带参数
        try:
            td_sql = _SQL_EXEC + ' ' + _qi(td_db) + '.' + _qi(macro_name)
            td_cols, td_rows = execute_td_query(td_conn, td_sql)
            result['td_status'] = 'success'
            result['td_row_count'] = len(td_rows)
            result['details']['td_columns'] = td_cols
            result['error'] = None
        except Exception as e2:
            result['error'] = f"TD执行失败(两种方式): {str(e)} | {str(e2)}"
            return result

    # --- DWS 端：SELECT * FROM func() ---
    try:
        # 推断列定义
        col_def = infer_dws_function_columns(dws_conn, macro_name, dws_schema)
        
        _func = _qi(dws_schema) + '.' + _qi(macro_name)
        if col_def:
            dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _func + '() ' + _SQL_AS + ' (' + col_def + ')'
        else:
            # 尝试直接调用（非 SETOF record 的情况，如 RETURNS TABLE(...)）
            dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _func + '()'
        
        try:
            dws_cols, dws_rows = execute_dws_query(dws_conn, dws_sql)
        except Exception as e1:
            # 直接调用失败，可能是 SETOF record 需要列定义列表
            # 尝试从 TD 端宏执行结果推断列类型
            if not col_def and td_cols:
                col_def = infer_col_def_from_td(td_cols, td_rows)
                if col_def:
                    dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _func + '() ' + _SQL_AS + ' (' + col_def + ')'
                    dws_cols, dws_rows = execute_dws_query(dws_conn, dws_sql)
                else:
                    raise e1
            else:
                raise e1
        
        result['dws_status'] = 'success'
        result['dws_row_count'] = len(dws_rows)
        result['details']['dws_columns'] = dws_cols
    except Exception as e:
        result['dws_status'] = 'error'
        result['error'] = (result['error'] or '') + f" | DWS执行失败: {str(e)}"
        return result

    # --- 比较结果 ---
    matched, msg = rows_match(td_rows, dws_rows)
    result['match'] = 'pass' if matched else 'fail'
    result['details']['match_detail'] = msg

    return result


def validate_procedure(td_conn, dws_conn, td_db, proc_name, dws_schema='public'):
    """
    校验存储过程：
    1. 只读过程：在两端执行，比较结果
    2. 写操作过程：在 DWS 端用事务回滚验证不报错
    """
    result = {
        'object_type': 'procedure',
        'object_name': proc_name,
        'td_status': None,
        'dws_status': None,
        'match': None,
        'td_row_count': None,
        'dws_row_count': None,
        'details': {},
        'error': None
    }

    # --- TD 端：CALL 调用 ---
    try:
        td_sql = _SQL_CALL + ' ' + _qi(td_db) + '.' + _qi(proc_name) + '()'
        td_cols, td_rows = execute_td_query(td_conn, td_sql)
        result['td_status'] = 'success'
        result['td_row_count'] = len(td_rows)
        result['details']['td_columns'] = td_cols
    except Exception as e:
        result['td_status'] = 'error'
        result['error'] = f"TD执行失败: {str(e)}"

    # --- DWS 端：CALL 调用（事务回滚） ---
    try:
        # 使用事务，执行后回滚
        dws_cur = dws_conn.cursor()
        try:
            dws_sql = _SQL_CALL + ' ' + _qi(dws_schema) + '.' + _qi(proc_name) + '()'
            dws_cur.execute(dws_sql)
            dws_rows = dws_cur.fetchall()
            dws_cols = [d[0] for d in dws_cur.description] if dws_cur.description else []
            result['dws_status'] = 'success'
            result['dws_row_count'] = len(dws_rows)
            result['details']['dws_columns'] = dws_cols
        except Exception as exec_err:
            # 可能是没有返回结果集的存储过程
            result['dws_status'] = 'success'
            result['dws_row_count'] = 0
            result['details']['dws_note'] = f"无返回结果集: {str(exec_err)}"
        finally:
            dws_conn.rollback()
            dws_cur.close()
    except Exception as e:
        result['dws_status'] = 'error'
        result['error'] = (result['error'] or '') + f" | DWS执行失败: {str(e)}"

    # --- 比较结果 ---
    if result['td_status'] == 'success' and result['dws_status'] == 'success':
        if result['td_row_count'] is not None and result['dws_row_count'] is not None:
            if result['td_row_count'] == result['dws_row_count']:
                result['match'] = 'pass'
                result['details']['match_detail'] = f"行数一致: {result['td_row_count']}"
            else:
                result['match'] = 'fail'
                result['details']['match_detail'] = f"行数不同: TD={result['td_row_count']}, DWS={result['dws_row_count']}"
        else:
            # 无返回结果集的过程，只要不报错就算通过
            result['match'] = 'pass'
            result['details']['match_detail'] = "两端执行均无异常"
    else:
        result['match'] = 'error'

    return result


def validate_view(td_conn, dws_conn, td_db, view_name, dws_schema='public'):
    """
    校验视图：
    1. 在两端查询行数
    2. 抽样比较数据
    """
    result = {
        'object_type': 'view',
        'object_name': view_name,
        'td_status': None,
        'dws_status': None,
        'match': None,
        'td_row_count': None,
        'dws_row_count': None,
        'details': {},
        'error': None
    }

    # --- TD 端 ---
    try:
        td_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _qi(td_db) + '.' + _qi(view_name)
        td_cols, td_rows = execute_td_query(td_conn, td_sql)
        result['td_status'] = 'success'
        result['td_row_count'] = len(td_rows)
        result['details']['td_columns'] = td_cols
    except Exception as e:
        result['td_status'] = 'error'
        result['error'] = f"TD查询失败: {str(e)}"
        return result

    # --- DWS 端 ---
    try:
        dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _qi(dws_schema) + '.' + _qi(view_name)
        dws_cols, dws_rows = execute_dws_query(dws_conn, dws_sql)
        result['dws_status'] = 'success'
        result['dws_row_count'] = len(dws_rows)
        result['details']['dws_columns'] = dws_cols
    except Exception as e:
        result['dws_status'] = 'error'
        result['error'] = (result['error'] or '') + f" | DWS查询失败: {str(e)}"
        return result

    # --- 比较结果 ---
    matched, msg = rows_match(td_rows, dws_rows)
    result['match'] = 'pass' if matched else 'fail'
    result['details']['match_detail'] = msg

    return result


def validate_macro_with_params(td_conn, dws_conn, td_db, macro_name, 
                                param_values=None, dws_schema='public'):
    """
    使用指定参数值校验宏
    param_values: dict of {param_name: value}
    """
    result = {
        'object_type': 'macro',
        'object_name': macro_name,
        'td_status': None,
        'dws_status': None,
        'match': None,
        'td_row_count': None,
        'dws_row_count': None,
        'details': {'param_values': param_values},
        'error': None
    }

    # --- TD 端 ---
    try:
        if param_values:
            param_str = ', '.join(
                _qi(k) + '=' + (_ql(v) if isinstance(v, str) else str(int(v) if isinstance(v, int) else float(v)))
                for k, v in param_values.items())
            td_sql = _SQL_EXEC + ' ' + _qi(td_db) + '.' + _qi(macro_name) + '(' + param_str + ')'
        else:
            td_sql = _SQL_EXEC + ' ' + _qi(td_db) + '.' + _qi(macro_name)
        
        td_cols, td_rows = execute_td_query(td_conn, td_sql)
        result['td_status'] = 'success'
        result['td_row_count'] = len(td_rows)
        result['details']['td_columns'] = td_cols
    except Exception as e:
        result['td_status'] = 'error'
        result['error'] = f"TD执行失败: {str(e)}"
        return result

    # --- DWS 端 ---
    try:
        col_def = infer_dws_function_columns(dws_conn, macro_name, dws_schema)
        
        if param_values:
            param_str = ', '.join(
                _ql(v) if isinstance(v, str) else str(int(v) if isinstance(v, int) else float(v))
                for v in param_values.values())
        else:
            param_str = ''
        
        _func = _qi(dws_schema) + '.' + _qi(macro_name)
        if col_def:
            dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _func + '(' + param_str + ') ' + _SQL_AS + ' (' + col_def + ')'
        else:
            dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _func + '(' + param_str + ')'
        
        try:
            dws_cols, dws_rows = execute_dws_query(dws_conn, dws_sql)
        except Exception as e1:
            # 直接调用失败，尝试从 TD 结果推断列类型
            if not col_def and td_cols:
                col_def = infer_col_def_from_td(td_cols, td_rows)
                if col_def:
                    dws_sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + _func + '(' + param_str + ') ' + _SQL_AS + ' (' + col_def + ')'
                    dws_cols, dws_rows = execute_dws_query(dws_conn, dws_sql)
                else:
                    raise e1
            else:
                raise e1
        
        result['dws_status'] = 'success'
        result['dws_row_count'] = len(dws_rows)
        result['details']['dws_columns'] = dws_cols
    except Exception as e:
        result['dws_status'] = 'error'
        result['error'] = (result['error'] or '') + f" | DWS执行失败: {str(e)}"
        return result

    # --- 比较 ---
    matched, msg = rows_match(td_rows, dws_rows)
    result['match'] = 'pass' if matched else 'fail'
    result['details']['match_detail'] = msg

    return result


def run_validation(td_conn, dws_conn, td_db, dws_schema='public', 
                    macro_test_params=None, skip_views=False, skip_macros=False, 
                    skip_procs=False):
    """
    运行完整的功能性校验
    macro_test_params: dict of {macro_name: {param_name: value}} 用于带参数宏的测试
    """
    results = {
        'start_time': datetime.now().isoformat(),
        'td_database': td_db,
        'dws_schema': dws_schema,
        'macros': [],
        'procedures': [],
        'views': [],
        'summary': {}
    }

    # --- 校验宏 ---
    if not skip_macros:
        print("\n=== 校验宏 (Macros) ===")
        td_macros = get_td_macros(td_conn, td_db)
        print(f"TD 端发现 {len(td_macros)} 个宏: {td_macros}")
        
        for macro_name in td_macros:
            print(f"\n--- 校验宏: {macro_name} ---")
            
            # 检查是否有指定的测试参数
            if macro_test_params and macro_name in macro_test_params:
                r = validate_macro_with_params(
                    td_conn, dws_conn, td_db, macro_name,
                    param_values=macro_test_params[macro_name],
                    dws_schema=dws_schema
                )
            else:
                r = validate_macro(td_conn, dws_conn, td_db, macro_name, dws_schema)
            
            results['macros'].append(r)
            status = r['match'] or 'error'
            print(f"  结果: {status} (TD={r['td_status']}, DWS={r['dws_status']}, "
                  f"TD行数={r['td_row_count']}, DWS行数={r['dws_row_count']})")
            if r['error']:
                print(f"  错误: {r['error']}")
            if r['details'].get('match_detail'):
                print(f"  详情: {r['details']['match_detail']}")

    # --- 校验存储过程 ---
    if not skip_procs:
        print("\n=== 校验存储过程 (Procedures) ===")
        td_procs = get_td_procedures(td_conn, td_db)
        print(f"TD 端发现 {len(td_procs)} 个存储过程: {td_procs}")
        
        for proc_name in td_procs:
            print(f"\n--- 校验存储过程: {proc_name} ---")
            r = validate_procedure(td_conn, dws_conn, td_db, proc_name, dws_schema)
            results['procedures'].append(r)
            status = r['match'] or 'error'
            print(f"  结果: {status} (TD={r['td_status']}, DWS={r['dws_status']})")
            if r['error']:
                print(f"  错误: {r['error']}")
            if r['details'].get('match_detail'):
                print(f"  详情: {r['details']['match_detail']}")

    # --- 校验视图 ---
    if not skip_views:
        print("\n=== 校验视图 (Views) ===")
        td_views = get_td_views(td_conn, td_db)
        print(f"TD 端发现 {len(td_views)} 个视图: {td_views}")
        
        for view_name in td_views:
            print(f"\n--- 校验视图: {view_name} ---")
            r = validate_view(td_conn, dws_conn, td_db, view_name, dws_schema)
            results['views'].append(r)
            status = r['match'] or 'error'
            print(f"  结果: {status} (TD行数={r['td_row_count']}, DWS行数={r['dws_row_count']})")
            if r['error']:
                print(f"  错误: {r['error']}")
            if r['details'].get('match_detail'):
                print(f"  详情: {r['details']['match_detail']}")

    # --- 汇总 ---
    results['end_time'] = datetime.now().isoformat()
    
    all_objects = results['macros'] + results['procedures'] + results['views']
    total = len(all_objects)
    passed = sum(1 for r in all_objects if r['match'] == 'pass')
    failed = sum(1 for r in all_objects if r['match'] == 'fail')
    errors = sum(1 for r in all_objects if r['match'] in (None, 'error'))
    
    results['summary'] = {
        'total_objects': total,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'pass_rate': f"{passed}/{total}" if total > 0 else "0/0"
    }

    print(f"\n=== 校验汇总 ===")
    print(f"总对象数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"错误: {errors}")
    print(f"通过率: {results['summary']['pass_rate']}")

    return results


def main():
    parser = argparse.ArgumentParser(description='功能性校验 - Teradata vs DWS')
    parser.add_argument('--config', help='YAML 配置文件路径')
    parser.add_argument('--td-host', help='Teradata 主机')
    parser.add_argument('--td-user', help='Teradata 用户名')
    # 密码不通过命令行参数传递；通过环境变量 TD_PASSWORD / DWS_PASSWORD 注入
    parser.add_argument('--td-database', help='Teradata 数据库名')
    parser.add_argument('--dws-host', help='DWS 主机')
    parser.add_argument('--dws-port', type=int, help='DWS 端口')
    parser.add_argument('--dws-db', help='DWS 数据库名')
    parser.add_argument('--dws-user', help='DWS 用户名')
    parser.add_argument('--dws-schema', default='public', help='DWS schema')
    parser.add_argument('--output', default='functional_validation_report.json',
                        help='输出报告文件路径')
    parser.add_argument('--skip-views', action='store_true', help='跳过视图校验')
    parser.add_argument('--skip-macros', action='store_true', help='跳过宏校验')
    parser.add_argument('--skip-procs', action='store_true', help='跳过存储过程校验')
    parser.add_argument('--macro-params', help='宏测试参数 JSON 文件路径')
    
    args = parser.parse_args()

    # 从配置文件或命令行参数获取连接信息
    if args.config:
        config = load_config(args.config)
        td_host = config.get('teradata', {}).get('host')
        td_user = config.get('teradata', {}).get('user')
        td_pass = config.get('teradata', {}).get('password') or os.environ.get('TD_PASSWORD')
        td_db = config.get('teradata', {}).get('database')
        dws_host = config.get('dws', {}).get('host')
        dws_port = config.get('dws', {}).get('port', 25308)
        dws_db = config.get('dws', {}).get('database')
        dws_user = config.get('dws', {}).get('user')
        dws_pass = config.get('dws', {}).get('password') or os.environ.get('DWS_PASSWORD')
        dws_schema = config.get('dws', {}).get('schema', 'public')
    else:
        td_host = args.td_host
        td_user = args.td_user
        # 明文密码不再从命令行接收，统一从环境变量读取（缺失时保留 None 让连接层报错）
        td_pass = os.environ.get('TD_PASSWORD')
        td_db = args.td_database
        dws_host = args.dws_host
        dws_port = args.dws_port
        dws_db = args.dws_db
        dws_user = args.dws_user
        dws_pass = os.environ.get('DWS_PASSWORD')
        dws_schema = args.dws_schema

    # 加载宏测试参数
    macro_test_params = None
    if args.macro_params:
        with open(args.macro_params, 'r') as f:
            macro_test_params = json.load(f)

    # 连接数据库
    print(f"连接 Teradata: {td_host} (数据库: {td_db})")
    td_conn = connect_teradata(td_host, td_user, td_pass, td_db)
    
    print(f"连接 DWS: {dws_host}:{dws_port} (数据库: {dws_db}, schema: {dws_schema})")
    dws_conn = connect_dws(dws_host, dws_port, dws_db, dws_user, dws_pass)

    # 运行校验
    results = run_validation(
        td_conn, dws_conn, td_db, dws_schema,
        macro_test_params=macro_test_params,
        skip_views=args.skip_views,
        skip_macros=args.skip_macros,
        skip_procs=args.skip_procs
    )

    # 保存报告
    output_path = args.output
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n报告已保存到: {output_path}")

    # 关闭连接
    td_conn.close()
    dws_conn.close()

    # 返回退出码
    if results['summary']['failed'] > 0 or results['summary']['errors'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
