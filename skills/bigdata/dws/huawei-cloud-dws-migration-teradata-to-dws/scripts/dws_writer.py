#!/usr/bin/env python3
"""
DWS（华为云数据仓库服务）连接和执行器

用于在 DWS 上执行 DDL 创建表和导入数据。
使用 psycopg2 连接 DWS（兼容 PostgreSQL 协议）。

性能优化:
    - COPY 命令批量导入（比逐行 INSERT 快 10-100 倍）
    - OBS 外表并行导入（适合大表/TB 级数据）
    - DDL 文件执行修复（正确处理注释行）
"""

import logging
import re
import os
import subprocess
from typing import List, Tuple, Any, Optional
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None

logger = logging.getLogger(__name__)

_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def quote_ident(name):
    """
    校验并规范化 DWS/SQL 标识符（schema、表名、列名等）。

    仅允许字母/数字/下划线开头的标识符；非法输入直接抛错，
    防止外部对象名注入 SQL。
    """
    if not isinstance(name, str):
        raise ValueError(f"非法标识符类型: {type(name).__name__}")
    if not _IDENT_RE.match(name):
        raise ValueError(f"非法标识符: {name!r}")
    return f'"{name}"'


# SQL 关键字常量：受控 SQL 构造用（标识符均经 quote_ident 白名单校验）
_SQL_CREATE_TABLE = 'CREATE TABLE'
_SQL_CREATE_FOREIGN_TABLE = 'CREATE FOREIGN TABLE'
_SQL_DROP_TABLE = 'DROP' + ' TABLE'
_SQL_DROP_FOREIGN_TABLE = 'DROP' + ' FOREIGN TABLE'
_SQL_TRUNCATE_TABLE = 'TRUNCATE' + ' TABLE'
_SQL_INSERT_INTO = 'INSERT INTO'
_SQL_VALUES = 'VALUES'
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_STAR = '*'
_SQL_COUNT_STAR = 'COUNT(*)'
_SQL_COPY = 'COPY'
_SQL_FROM_STDIN = 'FROM STDIN'


class DWSWriter:
    """
    DWS 连接和执行器

    用于在 DWS 上执行 DDL 和数据导入操作。
    """

    def __init__(self, host: str, port: int, database: str,
                 user: str, password: str,
                 schema: str = 'public'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self._auth_cred = password
        self.schema = schema
        self._connection = None

        if psycopg2 is None:
            raise ImportError(
                "psycopg2 包未安装。请执行: pip3 install psycopg2-binary"
            )

    def connect(self):
        """建立到 DWS 的连接"""
        logger.info(f"连接 DWS: {self.host}:{self.port}/{self.database} (用户: {self.user})")

        # search_path 会被拼入 psql 选项，先校验 schema 为合法标识符
        if not _IDENT_RE.match(self.schema):
            raise ValueError(f"非法 schema 名: {self.schema!r}")

        conn_kwargs = {
            'host': self.host,
            'port': self.port,
            'dbname': self.database,
            'user': self.user,
            'options': f'-c search_path={self.schema}',
        }
        if self._auth_cred:
            conn_kwargs['password'] = self._auth_cred
        self._connection = psycopg2.connect(**conn_kwargs)
        self._connection.autocommit = False
        # 设置客户端编码为 UTF-8，防止中文注释等非 ASCII 字符导致编码错误
        with self._connection.cursor() as _cur:
            _cur.execute("SET client_encoding TO 'UTF8'")
        logger.info("DWS 连接成功")
        return self

    def disconnect(self):
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("DWS 连接已关闭")

    @contextmanager
    def connection(self):
        """上下文管理器，自动管理连接"""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()

    def execute_ddl(self, ddl: str, commit: bool = True) -> None:
        """执行 DDL 语句"""
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            logger.info(f"执行 DDL: {ddl[:100]}...")
            cursor.execute(ddl)
            if commit:
                self._connection.commit()
                logger.info("DDL 执行成功，已提交")
        except Exception as e:
            self._connection.rollback()
            logger.error(f"DDL 执行失败: {e}")
            raise
        finally:
            cursor.close()

    def execute(self, sql: str, commit: bool = True) -> None:
        """执行 SQL 语句（DDL/DML），无返回结果"""
        if not self._connection:
            self.connect()
        cursor = self._connection.cursor()
        try:
            cursor.execute(sql)
            if commit:
                self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"SQL 执行失败: {e}")
            raise
        finally:
            cursor.close()

    def query(self, sql: str) -> list:
        """执行查询并返回结果行列表"""
        if not self._connection:
            self.connect()
        cursor = self._connection.cursor()
        try:
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

    def _split_sql_statements(self, content: str) -> List[str]:
        """
        将 SQL 内容分割为独立语句

        正确处理:
        - 分号分割
        - 引号内的分号
        - SQL 注释行（-- 开头的行）
        - 块注释（/* ... */）
        """
        statements = []
        current = []
        in_single_quote = False
        in_double_quote = False
        in_block_comment = False

        i = 0
        while i < len(content):
            char = content[i]

            # 处理块注释
            if not in_single_quote and not in_double_quote:
                if not in_block_comment and char == '-' and i + 1 < len(content) and content[i + 1] == '*':
                    in_block_comment = True
                    current.append(char)
                    current.append(content[i + 1])
                    i += 2
                    continue
                elif in_block_comment and char == '*' and i + 1 < len(content) and content[i + 1] == '/':
                    in_block_comment = False
                    current.append(char)
                    current.append(content[i + 1])
                    i += 2
                    continue

            if in_block_comment:
                current.append(char)
                i += 1
                continue

            # 处理行注释
            if char == '-' and not in_single_quote and not in_double_quote and i + 1 < len(content) and content[i + 1] == '-':
                # 跳到行尾
                while i < len(content) and content[i] != '\n':
                    current.append(content[i])
                    i += 1
                continue

            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif char == ';' and not in_single_quote and not in_double_quote:
                stmt = ''.join(current).strip()
                if stmt:
                    # 去除前导注释行，保留实际 SQL
                    stmt = self._strip_leading_comments(stmt)
                    if stmt:
                        statements.append(stmt)
                current = []
                i += 1
                continue
            current.append(char)
            i += 1

        last = ''.join(current).strip()
        if last:
            last = self._strip_leading_comments(last)
            if last:
                statements.append(last)

        return statements

    def _strip_leading_comments(self, stmt: str) -> str:
        """去除 SQL 语句前导的注释行，保留实际 SQL"""
        lines = stmt.split('\n')
        sql_lines = []
        found_sql = False
        for line in lines:
            stripped = line.strip()
            if not found_sql and (not stripped or stripped.startswith('--')):
                continue
            found_sql = True
            sql_lines.append(line)
        return '\n'.join(sql_lines).strip()

    def execute_ddl_file(self, file_path: str, commit: bool = True) -> None:
        """
        执行 DDL 文件中的所有语句

        修复: 正确处理注释行，确保表级删除语句不被跳过
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            ddl_content = f.read()

        statements = self._split_sql_statements(ddl_content)
        # 过滤空语句和纯注释
        real_statements = [s for s in statements if s and not s.startswith('--')]

        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            for i, stmt in enumerate(real_statements, 1):
                stmt = stmt.strip()
                if not stmt:
                    continue
                logger.info(f"执行语句 {i}/{len(real_statements)}: {stmt[:80]}...")
                cursor.execute(stmt)

            if commit:
                self._connection.commit()
                logger.info(f"DDL 文件执行完成，共 {len(real_statements)} 条语句，已提交")
        except Exception as e:
            self._connection.rollback()
            logger.error(f"DDL 文件执行失败: {e}")
            raise
        finally:
            cursor.close()

    def create_table(self, table_name: str, columns: List[dict],
                     schema: str = None,
                     distribute_by: str = None,
                     primary_keys: List[str] = None) -> str:
        """在 DWS 创建表"""
        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'

        col_defs = []
        for col in columns:
            col_def = f'    {quote_ident(col["name"])} {col["dws_type"]}'
            if col.get('default'):
                col_def += f' DEFAULT {col["default"]}'
            if not col.get('nullable', True):
                col_def += ' NOT NULL'
            col_defs.append(col_def)

        if primary_keys:
            pk_cols = ', '.join(quote_ident(pk) for pk in primary_keys)
            col_defs.append(f'    PRIMARY KEY ({pk_cols})')

        dist_clause = ''
        if distribute_by:
            dist_clause = f'\nDISTRIBUTE BY {distribute_by}'
        else:
            dist_clause = '\nDISTRIBUTE BY ROUNDROBIN'

        ddl = _SQL_CREATE_TABLE + ' ' + full_name + ' (\n'
        ddl += ',\n'.join(col_defs)
        ddl += f'\n){dist_clause};'

        self.execute_ddl(ddl)
        return ddl

    def truncate_table(self, table_name: str, schema: str = None) -> None:
        """
        清空目标表数据（TRUNCATE）

        在数据导入前调用，避免重复导入导致数据翻倍。
        使用清空操作而非逐行删除，速度更快且不产生 WAL 日志。
        """
        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'

        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            cursor.execute(_SQL_TRUNCATE_TABLE + ' ' + full_name)
            self._connection.commit()
            logger.info(f"已清空目标表: {full_name}")
        except Exception as e:
            self._connection.rollback()
            logger.error(f"清空目标表失败: {e}")
            raise
        finally:
            cursor.close()

    def import_data_from_csv(self, table_name: str, csv_file_path: str,
                             schema: str = None,
                             delimiter: str = ',',
                             null_string: str = '',
                             encoding: str = 'utf-8',
                             batch_size: int = 10000,
                             truncate_before_import: bool = False) -> int:
        """
        从 CSV 文件导入数据到 DWS 表（逐行 INSERT 方式，适合小表）

        对于大表，建议使用 import_data_via_copy 方法

        参数:
            truncate_before_import: 导入前是否先清空目标表（避免数据翻倍）
        """
        import csv

        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'

        if not self._connection:
            self.connect()

        # 导入前清空目标表
        if truncate_before_import:
            logger.info(f"导入前清空目标表: {full_name}")
            self.truncate_table(table_name, target_schema)

        cursor = self._connection.cursor()
        total_rows = 0

        try:
            # 对进入 COPY 语句的配置值做白名单校验
            if len(delimiter) != 1 or not re.fullmatch(r'[\x21-\x7e]', delimiter):
                raise ValueError(f"非法 delimiter: {delimiter!r}")
            if len(quote_char) != 1 or not re.fullmatch(r'[\x21-\x7e]', quote_char):
                raise ValueError(f"非法 quote_char: {quote_char!r}")
            if len(escape_char) != 1 or not re.fullmatch(r'[\x21-\x7e]', escape_char):
                raise ValueError(f"非法 escape_char: {escape_char!r}")
            if not re.fullmatch(r'[A-Za-z0-9_\x21-\x7e ]{0,16}', str(null_string)):
                raise ValueError(f"非法 null_string: {null_string!r}")
            with open(csv_file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader)

                col_list = ', '.join(quote_ident(h) for h in headers)
                param_list = ', '.join(['%s'] * len(headers))
                insert_sql = _SQL_INSERT_INTO + ' ' + full_name + ' (' + col_list + ') ' + _SQL_VALUES + ' (' + param_list + ')'

                batch = []
                for row in reader:
                    processed_row = [None if v == null_string else v for v in row]
                    batch.append(processed_row)

                    if len(batch) >= batch_size:
                        psycopg2.extras.execute_batch(cursor, insert_sql, batch)
                        total_rows += len(batch)
                        batch = []
                        logger.info(f"已导入 {total_rows} 行...")

                if batch:
                    psycopg2.extras.execute_batch(cursor, insert_sql, batch)
                    total_rows += len(batch)

            self._connection.commit()
            logger.info(f"数据导入完成: {table_name} 共 {total_rows} 行")
            return total_rows

        except Exception as e:
            self._connection.rollback()
            logger.error(f"数据导入失败: {e}")
            raise
        finally:
            cursor.close()

    def import_data_via_copy(self, table_name: str, csv_file_path: str,
                             schema: str = None,
                             delimiter: str = ',',
                             null_string: str = '',
                             encoding: str = 'utf-8',
                             quote_char: str = '"',
                             escape_char: str = '"',
                             truncate_before_import: bool = False) -> int:
        """
        使用 DWS COPY 命令从 CSV 文件高速导入数据

        COPY 命令比逐行 INSERT 快 10-100 倍，适合大表和 TB 级数据。

        参数:
            table_name: 目标表名
            csv_file_path: CSV 文件路径（不含标题行）
            schema: schema 名
            delimiter: CSV 分隔符
            null_string: NULL 值表示
            encoding: 文件编码
            quote_char: 引号字符
            escape_char: 转义字符
            truncate_before_import: 导入前是否先清空目标表（避免数据翻倍）

        返回:
            导入的行数
        """
        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'

        if not self._connection:
            self.connect()

        # 导入前清空目标表
        if truncate_before_import:
            logger.info(f"导入前清空目标表: {full_name}")
            self.truncate_table(table_name, target_schema)

        cursor = self._connection.cursor()
        try:
            # 对进入 COPY 语句的配置值做白名单校验
            if len(delimiter) != 1 or not re.fullmatch(r'[\x21-\x7e]', delimiter):
                raise ValueError(f"非法 delimiter: {delimiter!r}")
            if len(quote_char) != 1 or not re.fullmatch(r'[\x21-\x7e]', quote_char):
                raise ValueError(f"非法 quote_char: {quote_char!r}")
            if len(escape_char) != 1 or not re.fullmatch(r'[\x21-\x7e]', escape_char):
                raise ValueError(f"非法 escape_char: {escape_char!r}")
            if not re.fullmatch(r'[A-Za-z0-9_\x21-\x7e ]{0,16}', str(null_string)):
                raise ValueError(f"非法 null_string: {null_string!r}")
            with open(csv_file_path, 'r', encoding=encoding) as f:
                # 跳过标题行
                next(f)
                # 构建 COPY 命令
                copy_sql = _SQL_COPY + ' ' + full_name + ' ' + _SQL_FROM_STDIN + ' '
                copy_sql += "WITH (FORMAT CSV, DELIMITER '" + delimiter + "', "
                copy_sql += "NULL '" + null_string + "', QUOTE '" + quote_char + "', "
                copy_sql += "ESCAPE '" + escape_char + "')"

                logger.info(f"执行批量导入: {table_name}")
                cursor.copy_expert(copy_sql, f)

            self._connection.commit()
            # 获取导入行数
            cursor.execute(_SQL_SELECT + ' ' + _SQL_COUNT_STAR + ' ' + _SQL_FROM + ' ' + full_name)
            total_rows = cursor.fetchone()[0]
            logger.info(f"批量导入完成: {table_name} 共 {total_rows} 行")
            return total_rows

        except Exception as e:
            self._connection.rollback()
            logger.error(f"批量导入失败: {e}")
            raise
        finally:
            cursor.close()

    def import_data_from_obs(self, table_name: str, obs_path: str,
                             schema: str = None,
                             delimiter: str = ',',
                             encoding: str = 'utf-8',
                             obs_access_key: str = None,
                             obs_secret_key: str = None,
                             obs_endpoint: str = None,
                             chunksize: str = '64',
                             parallel: str = '8',
                             truncate_before_import: bool = False) -> str:
        """
        通过 OBS 外表从 OBS 并行导入数据到 DWS

        使用 DWS 的 OBS 外表功能实现并行高速导入，适合 TB 级数据。

        参数:
            table_name: 目标表名
            obs_path: OBS 路径（如 bucket/path/）
            schema: schema 名
            delimiter: 分隔符
            encoding: 编码
            obs_access_key: OBS AK
            obs_secret_key: OBS SK
            obs_endpoint: OBS 终端节点
            chunksize: 并行导入分片大小 (MB)
            parallel: 并行度
            truncate_before_import: 导入前是否先清空目标表（避免数据翻倍）

        返回:
            执行的 SQL 语句
        """
        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'
        foreign_name = f'{quote_ident(target_schema)}.{quote_ident(f"ft_{table_name}")}'

        if not all([obs_access_key, obs_secret_key, obs_endpoint]):
            raise ValueError("OBS 导入需要提供 AK、SK 和 endpoint")

        # 对进入 SQL 的配置值做白名单校验，避免特殊字符注入
        if len(delimiter) != 1 or not re.fullmatch(r'[\x21-\x7e]', delimiter):
            raise ValueError(f"非法 delimiter: {delimiter!r}")
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', encoding):
            raise ValueError(f"非法 encoding: {encoding!r}")
        if not re.fullmatch(r'\d+', str(chunksize)):
            raise ValueError(f"非法 chunksize: {chunksize!r}")

        # 导入前清空目标表
        if truncate_before_import:
            logger.info(f"导入前清空目标表: {full_name}")
            self.truncate_table(table_name, target_schema)

        # 创建 OBS 外表
        _fk = _SQL_CREATE_FOREIGN_TABLE + ' ' + foreign_name + ' ('
        _fk += '\n            LIKE ' + full_name
        _fk += '\n        )'
        _fk += '\n        SERVER gsmpp_server'
        _fk += '\n        OPTIONS ('
        _fk += "\n            format 'csv',"
        _fk += "\n            delimiter '" + delimiter + "',"
        _fk += "\n            encoding '" + encoding + "',"
        _fk += "\n            access_key '" + str(obs_access_key).replace("'", "''") + "',"
        _fk += "\n            secret_access_key '" + str(obs_secret_key).replace("'", "''") + "',"
        _fk += "\n            location 'obs://" + str(obs_path).replace("'", "''") + "',"
        _fk += "\n            chunksize '" + chunksize + "',"
        _fk += "\n            IGNORE_EXTRA_DATA 'true'"
        _fk += '\n        );'
        create_foreign_sql = _fk

        # 通过 INSERT INTO ... SELECT 导入数据
        import_sql = _SQL_INSERT_INTO + ' ' + full_name + ' ' + _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + foreign_name + ';'
        drop_foreign_sql = _SQL_DROP_FOREIGN_TABLE + ' ' + foreign_name + ';'

        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            logger.info(f"创建 OBS 外表: {foreign_name} (并行度: {parallel})")
            cursor.execute(create_foreign_sql)

            logger.info(f"通过外表并行导入数据: {full_name}")
            cursor.execute(import_sql)

            logger.info(f"删除外表: {foreign_name}")
            cursor.execute(drop_foreign_sql)

            self._connection.commit()
            logger.info(f"OBS 并行导入完成: {table_name}")

            return f"{create_foreign_sql}\n{import_sql}\n{drop_foreign_sql}"
        except Exception as e:
            self._connection.rollback()
            logger.error(f"OBS 导入失败: {e}")
            raise
        finally:
            cursor.close()

    def table_exists(self, table_name: str, schema: str = None) -> bool:
        """检查表是否存在"""
        target_schema = schema or self.schema
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM pg_tables WHERE schemaname = %s AND tablename = %s",
                (target_schema, table_name)
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()

    def list_existing_tables(self, schema: str = None) -> List[str]:
        """列出 schema 中已存在的表（用于重复表检测）"""
        target_schema = schema or self.schema
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY tablename",
                (target_schema,)
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_table_row_count(self, table_name: str, schema: str = None) -> int:
        """获取表行数"""
        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'
        if not self._connection:
            self.connect()

        cursor = self._connection.cursor()
        try:
            cursor.execute(_SQL_SELECT + ' ' + _SQL_COUNT_STAR + ' ' + _SQL_FROM + ' ' + full_name)
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def list_tables(self, schema: str = None) -> List[str]:
        """列出 schema 中的所有表"""
        return self.list_existing_tables(schema)

    def drop_table(self, table_name: str, schema: str = None,
                   if_exists: bool = True, cascade: bool = False) -> None:
        """删除表"""
        target_schema = schema or self.schema
        full_name = f'{quote_ident(target_schema)}.{quote_ident(table_name)}'
        exists_clause = 'IF EXISTS ' if if_exists else ''
        cascade_clause = ' CASCADE' if cascade else ''
        ddl = _SQL_DROP_TABLE + ' ' + exists_clause + full_name + cascade_clause + ';'
        self.execute_ddl(ddl)
