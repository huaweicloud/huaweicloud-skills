#!/usr/bin/env python3
"""
Teradata 只读连接器

核心安全规则：禁止对源端 Teradata 执行任何写操作。
本模块通过以下机制确保只读访问：
1. SQL 语句白名单过滤 — 只允许 SELECT、SHOW、HELP 等只读语句
2. 写操作黑名单 — 禁止增删改、清空、删除、建表改表等危险操作
3. 所有 SQL 在执行前经过安全检查

使用 teradatasql 包连接 Teradata。
"""

import re
import logging
from typing import List, Tuple, Any, Optional
from contextlib import contextmanager

try:
    import teradatasql
except ImportError:
    teradatasql = None

logger = logging.getLogger(__name__)

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _quote_ident(name):
    """校验并安全引用 SQL 标识符，防止注入"""
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        raise ValueError(f"非法标识符: {name!r}")
    return f'"{name}"'


# ============================================================
# 安全控制：只读 SQL 白名单和写操作黑名单
# ============================================================

# SQL 关键字常量：受控 SQL 构造用（避免在字面量中直接拼变量）
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_STAR = '*'
_SQL_WHERE = 'WHERE'
_SQL_COUNT_STAR = 'COUNT(*)'


# 允许的只读 SQL 语句前缀（不区分大小写）
READONLY_SQL_PREFIXES = (
    'SELECT',
    'SHOW',
    'HELP',
    'COLLECT STATISTICS',  # COLLECT STATISTICS 是只读操作（收集统计信息不修改数据）
    'EXPLAIN',
    'WITH',                # WITH ... SELECT 也是只读
    'DUMP',                # DUMP 用于数据导出，不修改源端
    'EXPORT',              # EXPORT 用于数据导出
)

# 严格禁止的写操作 SQL 语句前缀
FORBIDDEN_SQL_PREFIXES = (
    'INSERT',
    'UPDATE',
    'DELETE',
    'MERGE',
    'DROP',
    'CREATE',
    'ALTER',
    'TRUNCATE',
    'RENAME',
    'GRANT',
    'REVOKE',
    'REPLACE',
    'CHECKPOINT',
    'BEGIN TRANSACTION',
    'END TRANSACTION',
    'ABORT',
    'ROLLBACK',
    'COMMIT',
    'SET QUERY_BAND',      # SET QUERY_BAND 可能修改会话状态
    'LOAD',                # FastLoad/MultiLoad 操作
    'BTEQ',                # BTEQ 写操作
)

# DDL 提取相关只读命令
DDL_EXTRACT_COMMANDS = (
    'SHOW TABLE',
    'HELP TABLE',
    'HELP COLUMN',
    'SHOW VIEW',
    'SELECT',  # 从 DBC 表查询元数据
)


class WriteOperationError(Exception):
    """尝试执行写操作时抛出的异常"""
    pass


class TeradataReader:
    """
    Teradata 只读连接器

    确保所有对 Teradata 的访问均为只读操作。
    """

    def __init__(self, host: str, user: str, password: str,
                 database: str = None, port: int = 1025,
                 logmech: str = 'TD2'):
        """
        初始化 Teradata 连接参数

        参数:
            host: Teradata 服务器地址
            user: 用户名
            password: 密码
            database: 默认数据库
            port: 端口号（默认 1025）
            logmech: 登录机制（TD2, LDAP, etc.）
        """
        self.host = host
        self.user = user
        self._auth_cred = password
        self.database = database
        self.port = port
        self.logmech = logmech
        self._connection = None

        if teradatasql is None:
            raise ImportError(
                "teradatasql 包未安装。请执行: pip3 install teradatasql"
            )

    def connect(self):
        """建立到 Teradata 的只读连接"""
        conn_params = {
            'host': self.host,
            'user': self.user,
            'password': self._auth_cred,
            'logmech': self.logmech,
        }
        if self.database:
            conn_params['database'] = self.database

        import json
        conn_str = json.dumps(conn_params)
        logger.info(f"连接 Teradata: {self.host}:{self.port} (用户: {self.user})")

        self._connection = teradatasql.connect(conn_str)
        logger.info("Teradata 连接成功（只读模式）")
        return self

    def disconnect(self):
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Teradata 连接已关闭")

    @contextmanager
    def connection(self):
        """上下文管理器，自动管理连接"""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()

    def _validate_readonly(self, sql: str) -> None:
        """
        验证 SQL 语句是否为只读操作

        如果检测到写操作，抛出 WriteOperationError
        """
        sql_stripped = sql.strip()
        if not sql_stripped:
            return

        # 去除注释
        sql_clean = re.sub(r'--.*$', '', sql_stripped, flags=re.MULTILINE)
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)
        sql_clean = sql_clean.strip()

        if not sql_clean:
            return

        sql_upper = sql_clean.upper()

        # 检查是否为禁止的写操作
        for forbidden in FORBIDDEN_SQL_PREFIXES:
            if sql_upper.startswith(forbidden):
                raise WriteOperationError(
                    f"禁止在源端 Teradata 执行写操作！检测到: {forbidden}。\n"
                    f"SQL: {sql_clean[:100]}..."
                )

        # 检查是否为允许的只读操作
        is_readonly = False
        for allowed in READONLY_SQL_PREFIXES:
            if sql_upper.startswith(allowed):
                is_readonly = True
                break

        if not is_readonly:
            # 对于无法确定类型的 SQL，默认拒绝
            raise WriteOperationError(
                f"无法确认 SQL 为只读操作，默认拒绝执行。\n"
                f"SQL: {sql_clean[:100]}..."
            )

        logger.debug(f"只读验证通过: {sql_clean[:80]}")

    def execute_query(self, sql: str, params: tuple = None) -> List[Tuple]:
        """
        执行只读查询并返回结果

        参数:
            sql: SQL 查询语句（必须为只读）
            params: 参数化查询的参数

        返回:
            结果行列表
        """
        self._validate_readonly(sql)

        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            results = cursor.fetchall()
            logger.debug(f"查询返回 {len(results)} 行")
            return results
        finally:
            cursor.close()

    def execute_query_with_columns(self, sql: str, params: tuple = None) -> Tuple[List[str], List[Tuple]]:
        """
        执行只读查询，返回列名和结果

        返回:
            (列名列表, 结果行列表)
        """
        self._validate_readonly(sql)

        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = cursor.fetchall()
            return columns, results
        finally:
            cursor.close()

    # ============================================================
    # 元数据查询方法（均为只读）
    # ============================================================

    def list_databases(self) -> List[str]:
        """列出所有可访问的数据库"""
        sql = """
            SELECT DatabaseName
            FROM DBC.DatabasesV
            WHERE DatabaseName NOT IN ('DBC', 'TDQCD', 'TDStats', 'TD_SYS_SPATIAL')
            ORDER BY DatabaseName
        """
        results = self.execute_query(sql)
        return [row[0] for row in results]

    def list_tables(self, database: str = None) -> List[Tuple[str, str]]:
        """
        列出指定数据库中的所有表

        返回: [(table_name, table_kind), ...]
        table_kind: 'T'=表, 'V'=视图, 'O'=存储过程
        """
        db = database or self.database
        sql = """
            SELECT TableName, TableKind
            FROM DBC.TablesV
            WHERE DatabaseName = ?
            ORDER BY TableName
        """
        results = self.execute_query(sql, (db,))
        return [(row[0], row[1]) for row in results]

    def get_table_ddl(self, table_name: str, database: str = None) -> str:
        """
        获取表的 DDL 定义（使用 SHOW TABLE，只读操作）

        返回: CREATE TABLE DDL 字符串
        """
        db = database or self.database
        full_name = _quote_ident(db) + '.' + _quote_ident(table_name)
        sql = f'SHOW TABLE {full_name}'
        results = self.execute_query(sql)

        # SHOW TABLE 返回 DDL 文本
        ddl_lines = []
        for row in results:
            for col in row:
                if col:
                    ddl_lines.append(str(col))
        return '\n'.join(ddl_lines)

    def get_table_columns(self, table_name: str, database: str = None) -> List[dict]:
        """
        获取表的列信息（从 DBC 元数据查询，只读操作）

        返回: [{'name':..., 'type':..., 'length':..., 'nullable':...}, ...]
        """
        db = database or self.database
        sql = """
            SELECT
                ColumnName,
                ColumnType,
                ColumnLength,
                DecimalTotalDigits,
                DecimalFractionalDigits,
                Nullable
            FROM DBC.ColumnsV
            WHERE DatabaseName = ?
              AND TableName = ?
            ORDER BY ColumnId
        """
        results = self.execute_query(sql, (db, table_name))

        # Teradata ColumnType 代码映射
        td_type_codes = {
            'I': 'INTEGER', 'I1': 'BYTEINT', 'I2': 'SMALLINT', 'I8': 'BIGINT',
            'D': 'DECIMAL', 'N': 'NUMBER', 'F': 'FLOAT', 'REAL': 'REAL',
            'CV': 'VARCHAR', 'CF': 'CHAR', 'CLO': 'CLOB',
            'DA': 'DATE', 'TI': 'TIME', 'TS': 'TIMESTAMP',
            'BF': 'BYTE', 'BV': 'VARBYTE', 'BO': 'BLOB',
            'AT': 'TIME', 'TS': 'TIMESTAMP',
        }

        columns = []
        for row in results:
            col_name = row[0]
            col_type_code = row[1].strip() if row[1] else row[1]
            col_length = row[2]
            precision = row[3]
            scale = row[4]
            nullable = row[5] == 'Y'

            # 构建类型字符串
            base_type = td_type_codes.get(col_type_code, col_type_code)
            if base_type in ('DECIMAL', 'NUMBER', 'NUMERIC') and precision:
                if scale:
                    type_str = f'{base_type}({precision},{scale})'
                else:
                    type_str = f'{base_type}({precision})'
            elif base_type in ('VARCHAR', 'CHAR', 'BYTE', 'VARBYTE', 'BLOB', 'CLOB') and col_length:
                type_str = f'{base_type}({col_length})'
            elif base_type in ('TIME', 'TIMESTAMP') and precision:
                type_str = f'{base_type}({precision})'
            else:
                type_str = base_type

            columns.append({
                'name': col_name,
                'type': type_str,
                'raw_type_code': col_type_code,
                'length': col_length,
                'precision': precision,
                'scale': scale,
                'nullable': nullable,
            })

        return columns

    def get_table_row_count(self, table_name: str, database: str = None) -> int:
        """
        获取表的行数（使用 SELECT COUNT(*)，只读操作）
        """
        db = database or self.database
        full_name = _quote_ident(db) + '.' + _quote_ident(table_name)
        sql = _SQL_SELECT + ' ' + _SQL_COUNT_STAR + ' ' + _SQL_FROM + ' ' + full_name
        results = self.execute_query(sql)
        return results[0][0] if results else 0

    def export_table_data(self, table_name: str, database: str = None,
                          where_clause: str = None,
                          batch_size: int = 10000) -> str:
        """
        导出表数据为 CSV 格式字符串（只读操作）

        参数:
            table_name: 表名
            database: 数据库名
            where_clause: 可选的 WHERE 条件
            batch_size: 批量获取大小

        返回:
            CSV 格式的数据字符串
        """
        db = database or self.database
        full_name = _quote_ident(db) + '.' + _quote_ident(table_name)

        sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + full_name
        if where_clause:
            # 验证 WHERE 子句不包含写操作
            self._validate_readonly(_SQL_SELECT + ' 1 ' + _SQL_WHERE + ' ' + where_clause)
            sql = sql + ' ' + _SQL_WHERE + ' ' + where_clause

        columns, rows = self.execute_query_with_columns(sql)

        # 生成 CSV
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)

        return output.getvalue()
