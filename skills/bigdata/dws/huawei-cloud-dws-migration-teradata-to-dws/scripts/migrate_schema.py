#!/usr/bin/env python3
"""
表结构迁移脚本 (Step 1)

将 Teradata 表结构迁移到 DWS。
流程: 提取 Teradata DDL → 数据类型映射转换 → 重复表检测 → 用户确认 → 在 DWS 创建表

增强功能:
    1. 重复表检测: 执行 DDL 前检查 DWS 中已存在的表
    2. 用户确认: 发现重复表时列出并询问用户确认后才删除重建
    3. DDL 执行修复: 正确处理注释行，确保 DROP 语句不被跳过

使用方法:
    python3 migrate_schema.py \
        --td-config config/teradata_config.ini \
        --dws-config config/dws_config.ini \
        --schema <schema_name> \
        --output-dir ./output

核心规则:
    1. 禁止在源端 Teradata 进行任何写操作
    2. 数据类型映射遵循华为云官方文档
    3. 先迁移表结构，后迁移表数据
    4. 重复表需用户确认后才删除重建
"""

import argparse
import configparser
import logging
import os
import sys
import json
import time
from datetime import datetime

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teradata_reader import TeradataReader, WriteOperationError
from dws_writer import DWSWriter, quote_ident
from datatype_mapping import map_teradata_to_dws, map_column_definition
from ppi_converter import convert_ppi_ddl, is_ppi_table, get_distribute_clause


# SQL 关键字常量：受控 SQL 构造用（标识符经 quote_ident 白名单校验）
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_WHERE = 'WHERE'
_SQL_COUNT_STAR = 'COUNT(*)'
_SQL_IS_NULL = 'IS NULL'
_SQL_DROP_TABLE_IF_EXISTS = 'DROP' + ' TABLE IF EXISTS'
_SQL_CREATE_TABLE = 'CREATE TABLE'
_SQL_ALTER_TABLE = 'ALTER TABLE'
_SQL_ALTER_COLUMN = 'ALTER COLUMN'
_SQL_DROP_NOT_NULL = 'DROP NOT NULL'


def _qi(name):
    """标识符安全引用（白名单校验，非法输入抛错）"""
    return quote_ident(name)




# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger('migrate_schema')


def load_config(config_path: str) -> dict:
    """加载 INI 配置文件"""
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


def extract_teradata_schema(td_reader: TeradataReader,
                            database: str,
                            output_dir: str) -> dict:
    """
    从 Teradata 提取表结构（只读操作）

    返回: 表结构信息字典
    """
    logger.info(f"从 Teradata 提取数据库 '{database}' 的表结构...")

    # 获取所有表
    tables = td_reader.list_tables(database)
    table_info = {}

    # 筛选出表对象(T)，跳过视图(V)等
    table_list = [(t, k) for t, k in tables if k.strip() == 'T']
    total_tables = len(table_list)
    logger.info(f"共 {total_tables} 个表需要提取结构")

    schema_start = time.time()

    for idx, (table_name, table_kind) in enumerate(table_list, 1):
        # 进度显示
        bar_len = 30
        filled = int(bar_len * idx / total_tables)
        bar = '█' * filled + '░' * (bar_len - filled)
        pct = idx / total_tables * 100
        elapsed = time.time() - schema_start
        if idx > 1:
            avg = elapsed / (idx - 1)
            eta = avg * (total_tables - idx)
            eta_str = f'{eta/60:.1f}min' if eta >= 60 else f'{eta:.0f}s'
        else:
            eta_str = '...'

        logger.info(f"[{idx}/{total_tables}] {pct:.0f}% {bar} "
                     f"{table_name} (已用 {elapsed:.1f}s, 剩余 {eta_str})")

        # 获取列信息
        columns = td_reader.get_table_columns(table_name, database)

        # 获取 DDL
        try:
            ddl = td_reader.get_table_ddl(table_name, database)
        except Exception as e:
            logger.warning(f"获取 DDL 失败: {table_name}: {e}")
            ddl = None

        # 获取行数
        try:
            row_count = td_reader.get_table_row_count(table_name, database)
        except Exception as e:
            logger.warning(f"获取行数失败: {table_name}: {e}")
            row_count = None

        table_info[table_name] = {
            'name': table_name,
            'kind': table_kind,
            'columns': columns,
            'ddl': ddl,
            'row_count': row_count,
        }

    # 保存到 JSON 文件
    schema_file = os.path.join(output_dir, f'{database}_schema.json')
    with open(schema_file, 'w', encoding='utf-8') as f:
        json.dump(table_info, f, indent=2, ensure_ascii=False, default=str)

    total_time = time.time() - schema_start
    total_rows = sum(t.get('row_count', 0) or 0 for t in table_info.values())
    logger.info(f"表结构已保存到: {schema_file}")
    logger.info(f"━" * 50)
    logger.info(f"  提取完成: {len(table_info)} 个表, "
                f"总行数 {total_rows:,}, 耗时 {total_time:.1f}s")
    logger.info(f"━" * 50)

    return table_info


def generate_dws_ddl(table_info: dict, database: str,
                     output_dir: str,
                     distribute_strategy: str = 'roundrobin',
                     safe_null: bool = False) -> str:
    """
    根据表结构信息生成 DWS DDL 脚本

    参数:
        table_info: 表结构信息
        database: 目标 schema 名
        output_dir: 输出目录
        distribute_strategy: 分布策略 (roundrobin, hash, replication)
        safe_null: 安全模式，将所有 NOT NULL 列改为可空（避免源端有 NULL 数据时导入失败）

    返回:
        DDL 文件路径
    """
    logger.info(f"生成 DWS DDL 脚本...")

    ddl_lines = [
        f"-- ============================================",
        f"-- DWS DDL 脚本 - 由 Teradata 迁移生成",
        f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"-- 源数据库: {database}",
        f"-- ============================================",
        f"",
    ]

    mapping_report = []
    total_tables = len(table_info)
    ddl_start = time.time()

    for idx, (table_name, info) in enumerate(table_info.items(), 1):
        bar_len = 30
        filled = int(bar_len * idx / total_tables)
        bar = '█' * filled + '░' * (bar_len - filled)
        logger.info(f"[{idx}/{total_tables}] {bar} 转换表: {table_name}")

        columns = info['columns']
        col_defs = []
        table_mapping = []

        for col in columns:
            td_type = col['type']
            dws_type, desc = map_teradata_to_dws(td_type)

            col_def = f'    "{col["name"]}" {dws_type}'
            if not col.get('nullable', True) and not safe_null:
                col_def += ' NOT NULL'
            col_defs.append(col_def)

            table_mapping.append({
                'column': col['name'],
                'teradata_type': td_type,
                'dws_type': dws_type,
                'description': desc,
            })

        # 分布策略: 优先使用 Teradata PRIMARY INDEX 作为 DWS DISTRIBUTE BY
        td_ddl = info.get('ddl', '')
        partition_clause = ''
        if td_ddl and is_ppi_table(td_ddl):
            # PPI 表: 使用 PRIMARY INDEX 作为分布键
            dist_clause = get_distribute_clause(td_ddl, distribute_strategy)
            # 生成 DWS 分区子句
            partition_clause = convert_ppi_ddl(td_ddl)
            if partition_clause:
                logger.info(f"  📊 PPI 表: {table_name} → 已生成 DWS 分区子句")
            else:
                partition_clause = ''
        elif distribute_strategy == 'roundrobin':
            dist_clause = 'DISTRIBUTE BY ROUNDROBIN'
        elif distribute_strategy == 'replication':
            dist_clause = 'DISTRIBUTE BY REPLICATION'
        elif distribute_strategy == 'hash':
            # 使用第一列作为 hash 列
            first_col = columns[0]['name'] if columns else 'id'
            dist_clause = f'DISTRIBUTE BY HASH("{first_col}")'
        else:
            dist_clause = 'DISTRIBUTE BY ROUNDROBIN'

        if partition_clause:
            # PPI 表: 包含分区子句
            _qdb = _qi(database)
            _qtbl = _qi(table_name)
            ddl_lines.extend([
                f"-- 表: {table_name} (源行数: {info.get('row_count', '未知')}) [PPI 分区表]",
                _SQL_DROP_TABLE_IF_EXISTS + ' ' + _qdb + '.' + _qtbl + ' CASCADE;',
                _SQL_CREATE_TABLE + ' ' + _qdb + '.' + _qtbl + ' (',
                ',\n'.join(col_defs),
                ")",
                f"{dist_clause}",
                f"{partition_clause};",
                "",
            ])
        else:
            # 普通表
            _qdb = _qi(database)
            _qtbl = _qi(table_name)
            ddl_lines.extend([
                f"-- 表: {table_name} (源行数: {info.get('row_count', '未知')})",
                _SQL_DROP_TABLE_IF_EXISTS + ' ' + _qdb + '.' + _qtbl + ' CASCADE;',
                _SQL_CREATE_TABLE + ' ' + _qdb + '.' + _qtbl + ' (',
                ',\n'.join(col_defs),
                ")",
                f"{dist_clause};",
                "",
            ])

        mapping_report.extend(table_mapping)

    # 写入 DDL 文件
    ddl_file = os.path.join(output_dir, f'{database}_dws_ddl.sql')
    with open(ddl_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(ddl_lines))
    logger.info(f"DWS DDL 脚本已保存到: {ddl_file}")

    # 写入映射报告
    report_file = os.path.join(output_dir, f'{database}_mapping_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(mapping_report, f, indent=2, ensure_ascii=False, default=str)
    logger.info(f"类型映射报告已保存到: {report_file}")

    ddl_time = time.time() - ddl_start
    logger.info(f"━" * 50)
    logger.info(f"  DDL 生成完成: {total_tables} 个表, 耗时 {ddl_time:.1f}s")
    logger.info(f"━" * 50)

    return ddl_file


def check_existing_tables(dws_writer: DWSWriter,
                          table_info: dict,
                          schema: str) -> list:
    """
    检查 DWS 中已存在的表（重复表检测）

    参数:
        dws_writer: DWS 连接器
        table_info: 要迁移的表信息
        schema: 目标 schema

    返回:
        已存在的表名列表
    """
    source_tables = set(table_info.keys())
    existing_tables = set(dws_writer.list_existing_tables(schema))
    duplicate_tables = sorted(source_tables & existing_tables)

    return duplicate_tables


def confirm_duplicate_tables(duplicate_tables: list,
                             dws_writer: DWSWriter,
                             schema: str,
                             force: bool = False) -> bool:
    """
    重复表确认: 列出已存在的表，询问用户是否确认删除重建

    参数:
        duplicate_tables: 已存在的表名列表
        dws_writer: DWS 连接器
        schema: 目标 schema
        force: 是否跳过确认（--force 模式）

    返回:
        True=用户确认继续, False=用户取消
    """
    if not duplicate_tables:
        return True

    logger.info("")
    logger.info("⚠️  " + "═" * 56)
    logger.info(f"⚠️  检测到 {len(duplicate_tables)} 个表在 DWS 中已存在:")
    logger.info("⚠️  " + "═" * 56)
    logger.info("")

    # 列出每个重复表及其行数
    for idx, table_name in enumerate(duplicate_tables, 1):
        try:
            row_count = dws_writer.get_table_row_count(table_name, schema)
            logger.info(f"  {idx:>3}. {table_name:<40s} 已有 {row_count:>10,} 行")
        except Exception:
            logger.info(f"  {idx:>3}. {table_name:<40s} (无法获取行数)")

    logger.info("")
    logger.info("⚠️  继续迁移将 DROP 并重建以上表，数据将丢失！")
    logger.info("")

    if force:
        logger.info("⚡ --force 模式: 自动确认，跳过用户交互")
        return True

    # 非交互环境检测
    if not sys.stdin.isatty():
        logger.error("")
        logger.error("❌ " + "═" * 56)
        logger.error(f"❌ 检测到 {len(duplicate_tables)} 个重复表，但当前为非交互环境（stdin 不是终端）")
        logger.error("❌ 无法获取用户确认。请选择以下方式之一：")
        logger.error("❌   1. 在终端中直接运行迁移命令（交互式确认）")
        logger.error("❌   2. 添加 --force 参数自动确认删除重建")
        logger.error("❌   3. 在终端交互运行，选择「跳过」仅迁移新表")
        logger.error("❌ " + "═" * 56)
        logger.error("")
        sys.exit(1)

    # 交互式确认
    while True:
        try:
            choice = input("是否确认删除并重建以上表？ [y/N/全部/跳过]: ").strip().lower()
        except EOFError:
            # 兜底：非交互环境，明确报错退出
            logger.error("❌ 非交互环境（EOFError），未获得用户确认，迁移中止")
            logger.error("❌ 请添加 --force 参数或在终端中交互运行")
            sys.exit(1)

        if choice in ('y', 'yes'):
            logger.info("✅ 用户确认: 删除并重建重复表")
            return True
        elif choice in ('n', 'no', ''):
            logger.info("❌ 用户取消: 不迁移重复表")
            return False
        elif choice in ('全部', 'all', 'a'):
            logger.info("✅ 用户确认: 删除并重建所有重复表")
            return True
        elif choice in ('跳过', 'skip', 's'):
            logger.info("⏭️ 用户选择: 跳过重复表，仅迁移新表")
            return 'skip'
        else:
            logger.info("请输入: y=确认, n=取消, 全部=全部确认, 跳过=跳过重复表")


def execute_dws_ddl(dws_writer: DWSWriter, ddl_file: str) -> None:
    """在 DWS 执行 DDL 脚本"""
    logger.info(f"在 DWS 执行 DDL: {ddl_file}")
    dws_writer.execute_ddl_file(ddl_file)
    logger.info("DDL 执行完成")


def fix_not_null_violations(dws_writer: DWSWriter, schema: str,
                            tables: list = None) -> dict:
    """
    检测 DWS 表中 NOT NULL 列是否包含 NULL 数据，自动 DROP NOT NULL 约束。

    参数:
        dws_writer: DWS 连接对象
        schema: schema 名
        tables: 表名列表（默认全部）

    返回:
        修复结果字典 {table: [columns_fixed]}
    """
    logger.info("=" * 60)
    logger.info("检测并修复 NOT NULL 约束冲突")
    logger.info("=" * 60)

    if tables is None:
        # 获取 schema 下所有表
        sql = f"""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        result = dws_writer.query(sql)
        tables = [r[0] for r in result]

    fix_results = {}

    for table_name in tables:
        # 获取 NOT NULL 列
        sql = f"""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = '{schema}'
              AND table_name = '{table_name}'
              AND is_nullable = 'NO'
            ORDER BY ordinal_position
        """
        result = dws_writer.query(sql)
        not_null_cols = [r[0] for r in result]

        if not not_null_cols:
            continue

        # 检查每列是否有 NULL 数据
        violated_cols = []
        for col in not_null_cols:
            check_sql = _SQL_SELECT + ' ' + _SQL_COUNT_STAR + ' ' + _SQL_FROM + ' ' + _qi(schema) + '.' + _qi(table_name) + ' ' + _SQL_WHERE + ' ' + _qi(col) + ' ' + _SQL_IS_NULL
            result = dws_writer.query(check_sql)
            null_count = result[0][0] if result else 0
            if null_count > 0:
                violated_cols.append((col, null_count))
                logger.warning(f"  ⚠️ {table_name}.{col} 有 {null_count} 个 NULL 值，但约束为 NOT NULL")

        # 修复冲突
        if violated_cols:
            for col, _ in violated_cols:
                alter_sql = _SQL_ALTER_TABLE + ' ' + _qi(schema) + '.' + _qi(table_name) + ' ' + _SQL_ALTER_COLUMN + ' ' + _qi(col) + ' ' + _SQL_DROP_NOT_NULL
                try:
                    dws_writer.execute(alter_sql)
                    logger.info(f"  ✅ 已修复: 表 {table_name} 字段 {col} 取消 NOT NULL 约束")
                except Exception as e:
                    logger.error(f"  ❌ 修复失败 {table_name}.{col}: {e}")

            fix_results[table_name] = [col for col, _ in violated_cols]

    if fix_results:
        logger.info(f"━" * 50)
        logger.info(f"  共修复 {len(fix_results)} 个表的 NOT NULL 约束冲突")
    else:
        logger.info(f"  ✅ 未发现 NOT NULL 约束冲突")

    return fix_results


def main():
    parser = argparse.ArgumentParser(
        description='Teradata 到 DWS 表结构迁移脚本'
    )
    parser.add_argument('--td-config', required=True,
                        help='Teradata 连接配置文件路径')
    parser.add_argument('--dws-config', required=True,
                        help='DWS 连接配置文件路径')
    parser.add_argument('--schema', required=True,
                        help='要迁移的 schema/database 名称')
    parser.add_argument('--output-dir', default='./output',
                        help='输出目录（默认: ./output）')
    parser.add_argument('--distribute', default='roundrobin',
                        choices=['roundrobin', 'hash', 'replication'],
                        help='DWS 分布策略（默认: roundrobin）')
    parser.add_argument('--execute', action='store_true', default=True,
                        help='生成 DDL 后自动在 DWS 执行（默认开启）')
    parser.add_argument('--no-execute', dest='execute', action='store_false',
                        help='仅生成 DDL，不在 DWS 执行')
    parser.add_argument('--force', action='store_true',
                        help='跳过重复表确认，自动删除重建（非交互模式）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细日志输出')
    parser.add_argument('--safe-null', action='store_true',
                        help='安全模式：将所有 NOT NULL 列改为可空（避免源端有 NULL 数据时导入失败）')
    parser.add_argument('--fix-not-null', action='store_true',
                        help='检测并修复 DWS 中 NOT NULL 约束冲突（数据导入后使用）')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    # 加载配置
    td_config = load_config(args.td_config)
    dws_config = load_config(args.dws_config)

    # 初始化连接
    td_section = td_config.get('teradata', {})
    dws_section = dws_config.get('dws', {})

    td_reader = TeradataReader(
        host=td_section.get('host', ''),
        user=td_section.get('user', td_section.get('username', '')),
        password=td_section.get('password', ''),
        database=td_section.get('database', args.schema),
        port=int(td_section.get('port', '1025')),
        logmech=td_section.get('logmech', 'TD2'),
    )

    dws_writer = DWSWriter(
        host=dws_section.get('host', ''),
        port=int(dws_section.get('port', '8000')),
        database=dws_section.get('database', ''),
        user=dws_section.get('user', dws_section.get('username', '')),
        password=dws_section.get('password', ''),
        schema=args.schema,
    )

    # --fix-not-null 模式：仅检测修复 NOT NULL 冲突，不做表结构迁移
    if args.fix_not_null:
        with dws_writer.connection():
            fix_not_null_violations(dws_writer, args.schema)
        return

    # Step 1.1: 提取 Teradata 表结构（只读）
    logger.info("=" * 60)
    logger.info("Step 1: 表结构迁移")
    logger.info("=" * 60)

    try:
        with td_reader.connection():
            table_info = extract_teradata_schema(td_reader, args.schema, args.output_dir)

        logger.info(f"共提取 {len(table_info)} 个表的结构")

        # Step 1.2: 生成 DWS DDL
        ddl_file = generate_dws_ddl(table_info, args.schema, args.output_dir,
                                     args.distribute,
                                     safe_null=args.safe_null)

        # Step 1.3: 重复表检测 + 用户确认
        if args.execute:
            with dws_writer.connection():
                # 检查 DWS 中已存在的表
                logger.info("")
                logger.info("检查 DWS 中已存在的表...")
                duplicate_tables = check_existing_tables(
                    dws_writer, table_info, args.schema
                )

                if duplicate_tables:
                    # 有重复表，需要用户确认
                    confirm_result = confirm_duplicate_tables(
                        duplicate_tables, dws_writer, args.schema, args.force
                    )

                    if confirm_result is False:
                        logger.info("用户取消迁移，退出")
                        sys.exit(0)
                    elif confirm_result == 'skip':
                        # 跳过重复表，仅迁移新表
                        new_tables = {
                            k: v for k, v in table_info.items()
                            if k not in duplicate_tables
                        }
                        if new_tables:
                            logger.info(f"仅迁移 {len(new_tables)} 个新表")
                            # 重新生成仅包含新表的 DDL
                            ddl_file = generate_dws_ddl(
                                new_tables, args.schema, args.output_dir,
                                args.distribute
                            )
                            execute_dws_ddl(dws_writer, ddl_file)
                        else:
                            logger.info("没有新表需要迁移")
                    else:
                        # 用户确认，执行完整 DDL（包含 DROP + CREATE）
                        logger.info("开始执行 DDL（删除重复表并重建）...")
                        execute_dws_ddl(dws_writer, ddl_file)
                else:
                    # 没有重复表，直接执行
                    logger.info("✅ DWS 中无重复表，直接执行 DDL")
                    execute_dws_ddl(dws_writer, ddl_file)

        logger.info("=" * 60)
        logger.info("表结构迁移完成！")
        logger.info(f"  DDL 文件: {ddl_file}")
        logger.info(f"  输出目录: {args.output_dir}")
        logger.info("=" * 60)

    except WriteOperationError as e:
        logger.error(f"安全违规: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
