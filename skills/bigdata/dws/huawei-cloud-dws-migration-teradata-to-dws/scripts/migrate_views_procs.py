#!/usr/bin/env python3
"""
视图、宏和存储过程迁移脚本 (Step 3)

将 Teradata 视图、宏和存储过程迁移到 DWS。
流程: 从 Teradata 提取定义（只读）→ SQL 语法转换 → 在 DWS 上执行

支持的转换:
    1. 视图迁移:
       - ZEROIFNULL(expr) → COALESCE(expr, 0)
       - NULLIFZERO(expr) → NULLIF(expr, 0)
       - QUALIFY → 子查询包装
       - GROUP BY 位置引用 → 列名引用
       - Teradata 日期函数 → PostgreSQL 等价函数
       - SUBSTR → SUBSTRING
       - INDEX → STRPOS
       - TRIM/LEADING/TRAILING 语法适配
    2. 宏迁移:
       - Teradata Macro → DWS SQL 函数 (CREATE OR REPLACE FUNCTION)
    3. 存储过程迁移:
       - Teradata SPL → PL/pgSQL PROCEDURE
       - BEGIN/END 语法转换
       - 变量声明转换
       - IF/THEN/ELSE → IF/THEN/ELSE (PL/pgSQL 兼容)
       - WHILE/DO/END WHILE → WHILE/LOOP/END LOOP
       - FOR cursor → FOR loop

使用方法:
    python3 migrate_views_procs.py \\
        --td-config config/teradata_config.ini \\
        --dws-config config/dws_config.ini \\
        --schema <schema_name> \\
        --database <td_database> \\
        --types view macro procedure

核心规则:
    1. 禁止在源端 Teradata 进行任何写操作
    2. 所有 SQL 转换在本地完成，仅在 DWS 上执行
"""

import argparse
import configparser
import logging
import os
import re
import sys
import json
import time
from datetime import datetime
from typing import List, Optional, Tuple, Dict

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teradata_reader import TeradataReader, WriteOperationError
from dws_writer import DWSWriter, quote_ident


# SQL 关键字常量：受控 SQL 构造用（标识符经 quote_ident 白名单校验）
_SQL_CREATE_OR_REPLACE_VIEW = 'CREATE OR REPLACE VIEW'
_SQL_AS = 'AS'


# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('migrate_views_procs')


def load_config(config_path: str) -> dict:
    """加载 INI 配置文件"""
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


# ============================================================
# SQL 语法转换器
# ============================================================

from sql_converter import SQLConverter
from macro_converter import MacroConverter
from procedure_converter import ProcedureConverter

def extract_view_ddl(td_reader: TeradataReader, view_name: str,
                     database: str) -> Optional[str]:
    """
    从 Teradata 提取视图 DDL（只读操作）

    使用 SHOW VIEW 命令获取视图定义
    """
    full_name = f'"{database}"."{view_name}"'
    sql = f'SHOW VIEW {full_name}'

    try:
        results = td_reader.execute_query(sql)
        ddl_lines = []
        for row in results:
            for col in row:
                if col:
                    ddl_lines.append(str(col))
        return '\n'.join(ddl_lines)
    except Exception as e:
        logger.error(f"提取视图 {view_name} DDL 失败: {e}")
        return None


def extract_macro_ddl(td_reader: TeradataReader, macro_name: str,
                      database: str) -> Optional[str]:
    """
    从 Teradata 提取宏 DDL（只读操作）

    使用 SHOW MACRO 命令获取宏定义
    """
    full_name = f'"{database}"."{macro_name}"'
    sql = f'SHOW MACRO {full_name}'

    try:
        results = td_reader.execute_query(sql)
        ddl_lines = []
        for row in results:
            for col in row:
                if col:
                    ddl_lines.append(str(col))
        return '\n'.join(ddl_lines)
    except Exception as e:
        logger.error(f"提取宏 {macro_name} DDL 失败: {e}")
        return None


def extract_procedure_ddl(td_reader: TeradataReader, proc_name: str,
                          database: str) -> Optional[str]:
    """
    从 Teradata 提取存储过程 DDL（只读操作）

    使用 SHOW PROCEDURE 命令获取存储过程定义
    """
    full_name = f'"{database}"."{proc_name}"'
    sql = f'SHOW PROCEDURE {full_name}'

    try:
        results = td_reader.execute_query(sql)
        ddl_lines = []
        for row in results:
            for col in row:
                if col:
                    ddl_lines.append(str(col))
        return '\n'.join(ddl_lines)
    except Exception as e:
        logger.error(f"提取存储过程 {proc_name} DDL 失败: {e}")
        return None


def list_objects_by_type(td_reader: TeradataReader, database: str,
                         obj_type: str) -> List[str]:
    """
    列出指定数据库中指定类型的对象（只读操作）

    obj_type: 'V'=视图, 'M'=宏, 'P'=存储过程
    """
    # DBC.TablesV TableKind 值:
    # 'T'=表, 'V'=视图, 'M'=宏, 'P'=存储过程, 'O'=用户定义函数
    sql = """
        SELECT TableName
        FROM DBC.TablesV
        WHERE DatabaseName = ?
          AND TableKind = ?
        ORDER BY TableName
    """
    results = td_reader.execute_query(sql, (database, obj_type))
    return [row[0] for row in results]


def migrate_views(td_reader: TeradataReader, dws_writer: DWSWriter,
                  database: str, schema: str,
                  view_names: List[str] = None) -> dict:
    """
    迁移视图

    参数:
        td_reader: Teradata 只读连接
        dws_writer: DWS 写入器
        database: Teradata 数据库名
        schema: DWS 目标 schema
        view_names: 指定视图名列表，None 则迁移所有视图

    返回:
        迁移结果统计
    """
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'details': []}

    # 获取视图列表
    if view_names is None:
        view_names = list_objects_by_type(td_reader, database, 'V')

    stats['total'] = len(view_names)
    logger.info(f"找到 {len(view_names)} 个视图需要迁移")

    for view_name in view_names:
        logger.info(f"正在迁移视图: {view_name}")

        # 1. 提取视图 DDL
        td_ddl = extract_view_ddl(td_reader, view_name, database)
        if not td_ddl:
            stats['failed'] += 1
            stats['details'].append({
                'name': view_name, 'type': 'view',
                'status': 'failed', 'error': '提取 DDL 失败'
            })
            continue

        # 2. 转换 SQL
        try:
            # 提取 SELECT 语句部分
            select_sql = td_ddl
            # 如果包含 CREATE VIEW，提取 AS 后面的部分
            as_match = re.search(
                r'\bAS\s+(.+?)(?:\bWITH\s+CHECK\s+OPTION\b)?;?\s*$',
                td_ddl, re.IGNORECASE | re.DOTALL
            )
            if as_match:
                select_sql = as_match.group(1).strip()

            converted_sql = SQLConverter.convert_view_sql(
                select_sql, source_db=database, target_schema=schema
            )

            # 3. 构建 DWS CREATE VIEW DDL
            dws_ddl = (_SQL_CREATE_OR_REPLACE_VIEW + ' ' + quote_ident(schema) + '.' + quote_ident(view_name) + ' ' + _SQL_AS + '\n' + converted_sql + ';')

        except Exception as e:
            logger.error(f"转换视图 {view_name} SQL 失败: {e}")
            stats['failed'] += 1
            stats['details'].append({
                'name': view_name, 'type': 'view',
                'status': 'failed', 'error': f'SQL 转换失败: {e}'
            })
            continue

        # 4. 在 DWS 上执行
        try:
            dws_writer.execute_ddl(dws_ddl)
            logger.info(f"  ✓ 视图 {view_name} 迁移成功")
            stats['success'] += 1
            stats['details'].append({
                'name': view_name, 'type': 'view',
                'status': 'success'
            })
        except Exception as e:
            logger.error(f"  ✗ 视图 {view_name} 创建失败: {e}")
            stats['failed'] += 1
            stats['details'].append({
                'name': view_name, 'type': 'view',
                'status': 'failed', 'error': str(e)
            })

    return stats


def migrate_macros(td_reader: TeradataReader, dws_writer: DWSWriter,
                   database: str, schema: str,
                   macro_names: List[str] = None) -> dict:
    """
    迁移宏到 DWS SQL 函数
    """
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'details': []}

    # 获取宏列表
    if macro_names is None:
        macro_names = list_objects_by_type(td_reader, database, 'M')

    stats['total'] = len(macro_names)
    logger.info(f"找到 {len(macro_names)} 个宏需要迁移")

    for macro_name in macro_names:
        logger.info(f"正在迁移宏: {macro_name}")

        # 1. 提取宏 DDL
        td_ddl = extract_macro_ddl(td_reader, macro_name, database)
        if not td_ddl:
            stats['failed'] += 1
            stats['details'].append({
                'name': macro_name, 'type': 'macro',
                'status': 'failed', 'error': '提取 DDL 失败'
            })
            continue

        # 2. 转换为函数
        try:
            func_ddl = MacroConverter.convert_macro(
                td_ddl, macro_name,
                source_db=database, target_schema=schema,
                dws_writer=dws_writer
            )
            if not func_ddl:
                stats['failed'] += 1
                stats['details'].append({
                    'name': macro_name, 'type': 'macro',
                    'status': 'failed', 'error': '转换失败'
                })
                continue
        except Exception as e:
            logger.error(f"转换宏 {macro_name} 失败: {e}")
            stats['failed'] += 1
            stats['details'].append({
                'name': macro_name, 'type': 'macro',
                'status': 'failed', 'error': f'转换失败: {e}'
            })
            continue

        # 3. 在 DWS 上执行
        try:
            dws_writer.execute_ddl(func_ddl)
            logger.info(f"  ✓ 宏 {macro_name} 迁移成功（转为函数）")
            stats['success'] += 1
            stats['details'].append({
                'name': macro_name, 'type': 'macro',
                'status': 'success'
            })
        except Exception as e:
            logger.error(f"  ✗ 宏 {macro_name} 创建失败: {e}")
            stats['failed'] += 1
            stats['details'].append({
                'name': macro_name, 'type': 'macro',
                'status': 'failed', 'error': str(e)
            })

    return stats


def migrate_procedures(td_reader: TeradataReader, dws_writer: DWSWriter,
                       database: str, schema: str,
                       proc_names: List[str] = None) -> dict:
    """
    迁移存储过程到 DWS PL/pgSQL PROCEDURE
    """
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'details': []}

    # 获取存储过程列表
    if proc_names is None:
        proc_names = list_objects_by_type(td_reader, database, 'P')

    stats['total'] = len(proc_names)
    logger.info(f"找到 {len(proc_names)} 个存储过程需要迁移")

    for proc_name in proc_names:
        logger.info(f"正在迁移存储过程: {proc_name}")

        # 1. 提取存储过程 DDL
        td_ddl = extract_procedure_ddl(td_reader, proc_name, database)
        if not td_ddl:
            stats['failed'] += 1
            stats['details'].append({
                'name': proc_name, 'type': 'procedure',
                'status': 'failed', 'error': '提取 DDL 失败'
            })
            continue

        # 2. 转换为 PL/pgSQL
        try:
            proc_ddl = ProcedureConverter.convert_procedure(
                td_ddl, proc_name,
                source_db=database, target_schema=schema
            )
            if not proc_ddl:
                stats['failed'] += 1
                stats['details'].append({
                    'name': proc_name, 'type': 'procedure',
                    'status': 'failed', 'error': '转换失败'
                })
                continue
        except Exception as e:
            logger.error(f"转换存储过程 {proc_name} 失败: {e}")
            stats['failed'] += 1
            stats['details'].append({
                'name': proc_name, 'type': 'procedure',
                'status': 'failed', 'error': f'转换失败: {e}'
            })
            continue

        # 3. 在 DWS 上执行
        try:
            dws_writer.execute_ddl(proc_ddl)
            logger.info(f"  ✓ 存储过程 {proc_name} 迁移成功")
            stats['success'] += 1
            stats['details'].append({
                'name': proc_name, 'type': 'procedure',
                'status': 'success'
            })
        except Exception as e:
            logger.error(f"  ✗ 存储过程 {proc_name} 创建失败: {e}")
            stats['failed'] += 1
            stats['details'].append({
                'name': proc_name, 'type': 'procedure',
                'status': 'failed', 'error': str(e)
            })

    return stats


# ============================================================
# 主函数和 CLI
# ============================================================

def run_migration(config: dict, object_types: List[str],
                  specific_objects: dict = None,
                  output_dir: str = None,
                  dry_run: bool = False) -> dict:
    """
    执行视图/宏/存储过程迁移

    参数:
        config: 连接配置字典
        object_types: 要迁移的对象类型列表 ['views', 'macros', 'procedures']
        specific_objects: 指定对象名 {'views': [...], 'macros': [...], ...}
        output_dir: 输出 DDL 到文件而不执行
        dry_run: 只转换不执行

    返回:
        所有迁移结果统计
    """
    all_stats = {}

    # 连接 Teradata（只读）
    td_reader = TeradataReader(
        host=config['teradata']['host'],
        port=config['teradata'].get('port', 1025),
        user=config['teradata'].get('user', config['teradata'].get('username', '')),
        password=config['teradata']['password'],
        database=config['teradata'].get('database', 'DBC'),
        logmech=config['teradata'].get('logmech', 'TD2'),
    )

    td_reader.connect()

    # 连接 DWS
    dws_writer = None
    if not dry_run and not output_dir:
        dws_writer = DWSWriter(
            host=config['dws']['host'],
            port=config['dws'].get('port', 25308),
            database=config['dws'].get('database', 'postgres'),
            user=config['dws'].get('user', config['dws'].get('username', '')),
            password=config['dws']['password'],
            schema=config['dws'].get('target_schema', config['dws'].get('schema', 'public')),
        )
        dws_writer.connect()

    database = config['teradata']['source_database']
    schema = config['dws'].get('target_schema', database)

    try:
        # 迁移视图
        if 'views' in object_types:
            view_names = specific_objects.get('views') if specific_objects else None
            if output_dir or dry_run:
                all_stats['views'] = _migrate_views_to_file(
                    td_reader, database, schema, view_names, output_dir
                )
            else:
                all_stats['views'] = migrate_views(
                    td_reader, dws_writer, database, schema, view_names
                )

        # 迁移宏
        if 'macros' in object_types:
            macro_names = specific_objects.get('macros') if specific_objects else None
            if output_dir or dry_run:
                all_stats['macros'] = _migrate_macros_to_file(
                    td_reader, database, schema, macro_names, output_dir
                )
            else:
                all_stats['macros'] = migrate_macros(
                    td_reader, dws_writer, database, schema, macro_names
                )

        # 迁移存储过程
        if 'procedures' in object_types:
            proc_names = specific_objects.get('procedures') if specific_objects else None
            if output_dir or dry_run:
                all_stats['procedures'] = _migrate_procedures_to_file(
                    td_reader, database, schema, proc_names, output_dir
                )
            else:
                all_stats['procedures'] = migrate_procedures(
                    td_reader, dws_writer, database, schema, proc_names
                )

    finally:
        td_reader.disconnect()
        if dws_writer:
            dws_writer.disconnect()

    return all_stats


def _migrate_views_to_file(td_reader: TeradataReader, database: str,
                           schema: str, view_names: List[str],
                           output_dir: str) -> dict:
    """将视图 DDL 转换后输出到文件"""
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'details': []}

    if view_names is None:
        view_names = list_objects_by_type(td_reader, database, 'V')

    stats['total'] = len(view_names)
    os.makedirs(output_dir, exist_ok=True)

    for view_name in view_names:
        td_ddl = extract_view_ddl(td_reader, view_name, database)
        if not td_ddl:
            stats['failed'] += 1
            continue

        try:
            as_match = re.search(
                r'\bAS\s+(.+?)(?:\bWITH\s+CHECK\s+OPTION\b)?;?\s*$',
                td_ddl, re.IGNORECASE | re.DOTALL
            )
            select_sql = as_match.group(1).strip() if as_match else td_ddl
            converted_sql = SQLConverter.convert_view_sql(
                select_sql, source_db=database, target_schema=schema
            )
            dws_ddl = (_SQL_CREATE_OR_REPLACE_VIEW + ' ' + quote_ident(schema) + '.' + quote_ident(view_name) + ' ' + _SQL_AS + '\n' + converted_sql + ';\n')

            filepath = os.path.join(output_dir, f'view_{view_name}.sql')
            with open(filepath, 'w') as f:
                f.write(dws_ddl)

            stats['success'] += 1
            logger.info(f"  ✓ 视图 {view_name} DDL 已写入 {filepath}")
        except Exception as e:
            logger.error(f"  ✗ 视图 {view_name} 转换失败: {e}")
            stats['failed'] += 1

    return stats


def _migrate_macros_to_file(td_reader: TeradataReader, database: str,
                            schema: str, macro_names: List[str],
                            output_dir: str) -> dict:
    """将宏 DDL 转换后输出到文件"""
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'details': []}

    if macro_names is None:
        macro_names = list_objects_by_type(td_reader, database, 'M')

    stats['total'] = len(macro_names)
    os.makedirs(output_dir, exist_ok=True)

    for macro_name in macro_names:
        td_ddl = extract_macro_ddl(td_reader, macro_name, database)
        if not td_ddl:
            stats['failed'] += 1
            continue

        try:
            func_ddl = MacroConverter.convert_macro(
                td_ddl, macro_name, source_db=database, target_schema=schema
            )
            if func_ddl:
                filepath = os.path.join(output_dir, f'macro_{macro_name}.sql')
                with open(filepath, 'w') as f:
                    f.write(func_ddl + '\n')
                stats['success'] += 1
                logger.info(f"  ✓ 宏 {macro_name} DDL 已写入 {filepath}")
            else:
                stats['failed'] += 1
        except Exception as e:
            logger.error(f"  ✗ 宏 {macro_name} 转换失败: {e}")
            stats['failed'] += 1

    return stats


def _migrate_procedures_to_file(td_reader: TeradataReader, database: str,
                                schema: str, proc_names: List[str],
                                output_dir: str) -> dict:
    """将存储过程 DDL 转换后输出到文件"""
    stats = {'total': 0, 'success': 0, 'failed': 0, 'skipped': 0, 'details': []}

    if proc_names is None:
        proc_names = list_objects_by_type(td_reader, database, 'P')

    stats['total'] = len(proc_names)
    os.makedirs(output_dir, exist_ok=True)

    for proc_name in proc_names:
        td_ddl = extract_procedure_ddl(td_reader, proc_name, database)
        if not td_ddl:
            stats['failed'] += 1
            continue

        try:
            proc_ddl = ProcedureConverter.convert_procedure(
                td_ddl, proc_name, source_db=database, target_schema=schema
            )
            if proc_ddl:
                filepath = os.path.join(output_dir, f'proc_{proc_name}.sql')
                with open(filepath, 'w') as f:
                    f.write(proc_ddl + '\n')
                stats['success'] += 1
                logger.info(f"  ✓ 存储过程 {proc_name} DDL 已写入 {filepath}")
            else:
                stats['failed'] += 1
        except Exception as e:
            logger.error(f"  ✗ 存储过程 {proc_name} 转换失败: {e}")
            stats['failed'] += 1

    return stats


def main():
    """CLI 入口"""
    import argparse
    import json
    import yaml

    parser = argparse.ArgumentParser(
        description='迁移 Teradata 视图/宏/存储过程到 DWS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 迁移所有视图、宏、存储过程
  python migrate_views_procs.py --config config.yaml --types views,macros,procedures

  # 只迁移视图
  python migrate_views_procs.py --config config.yaml --types views

  # 指定视图名
  python migrate_views_procs.py --config config.yaml --types views --views view1,view2

  # 只转换 DDL 不执行
  python migrate_views_procs.py --config config.yaml --types views --output-dir ./ddl_output

  # dry-run 模式
  python migrate_views_procs.py --config config.yaml --types views --dry-run
        """
    )

    parser.add_argument('--config', required=True,
                        help='连接配置文件 (YAML/JSON)')
    parser.add_argument('--types', default='views,macros,procedures',
                        help='要迁移的对象类型 (逗号分隔): views,macros,procedures')
    parser.add_argument('--views', help='指定视图名 (逗号分隔)')
    parser.add_argument('--macros', help='指定宏名 (逗号分隔)')
    parser.add_argument('--procedures', help='指定存储过程名 (逗号分隔)')
    parser.add_argument('--output-dir', help='输出 DDL 到文件而不执行')
    parser.add_argument('--dry-run', action='store_true',
                        help='只转换不执行（不连接 DWS）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细日志输出')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 加载配置
    config_path = args.config
    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        with open(config_path) as f:
            config = json.load(f)

    # 解析参数
    object_types = [t.strip() for t in args.types.split(',')]
    specific_objects = {}
    if args.views:
        specific_objects['views'] = [v.strip() for v in args.views.split(',')]
    if args.macros:
        specific_objects['macros'] = [m.strip() for m in args.macros.split(',')]
    if args.procedures:
        specific_objects['procedures'] = [p.strip() for p in args.procedures.split(',')]

    # 执行迁移
    logger.info("=" * 60)
    logger.info("Teradata → DWS 视图/宏/存储过程迁移工具")
    logger.info("=" * 60)
    logger.info(f"对象类型: {object_types}")
    logger.info(f"源数据库: {config['teradata'].get('source_database', 'N/A')}")
    logger.info(f"目标 Schema: {config['dws'].get('target_schema', 'N/A')}")

    if args.dry_run:
        logger.info("【DRY-RUN 模式】只转换不执行")
    elif args.output_dir:
        logger.info(f"【输出到文件】目录: {args.output_dir}")

    all_stats = run_migration(
        config=config,
        object_types=object_types,
        specific_objects=specific_objects if specific_objects else None,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )

    # 打印统计
    logger.info("=" * 60)
    logger.info("迁移结果统计:")
    logger.info("=" * 60)

    total_all = 0
    success_all = 0
    failed_all = 0

    for obj_type, stats in all_stats.items():
        total = stats['total']
        success = stats['success']
        failed = stats['failed']
        total_all += total
        success_all += success
        failed_all += failed

        logger.info(f"\n{obj_type}:")
        logger.info(f"  总数: {total}")
        logger.info(f"  成功: {success}")
        logger.info(f"  失败: {failed}")

        if args.verbose and stats.get('details'):
            for detail in stats['details']:
                status_icon = '✓' if detail['status'] == 'success' else '✗'
                logger.info(f"    {status_icon} {detail['name']}: {detail['status']}")
                if 'error' in detail:
                    logger.info(f"        错误: {detail['error']}")

    logger.info(f"\n总计: {total_all} 个对象, 成功 {success_all}, 失败 {failed_all}")

    if failed_all > 0:
        logger.warning(f"有 {failed_all} 个对象迁移失败，请检查日志")
        sys.exit(1)
    else:
        logger.info("所有对象迁移成功！")


if __name__ == '__main__':
    main()
