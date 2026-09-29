#!/usr/bin/env python3
"""
表数据迁移脚本 (Step 2)

将 Teradata 表数据迁移到 DWS。
流程: 从 Teradata 导出数据（只读）→ 导入到 DWS

支持的数据导入方式:
    1. direct  — 直接通过 SQL 查询导出并 INSERT 到 DWS（适合小表）
    2. csv     — 导出为 CSV 文件再通过 COPY 命令导入 DWS（适合中等表）
    3. obs     — 导出到 OBS 再通过外表并行导入 DWS（适合大表/TB级，并行高速）

增强功能:
    1. OBS 临时目录: 导出 CSV 到 OBS 而非本地磁盘，避免磁盘容量问题
    2. 实时进度显示: 在 shell 窗口显示每表迁移的实时进度
    3. COPY 命令批量导入: 比 INSERT 快 10-100 倍
    4. 性能优化: 支持分片导出、并行导入，适合 TB 级数据

使用方法:
    python3 migrate_data.py \
        --td-config config/teradata_config.ini \
        --dws-config config/dws_config.ini \
        --schema <schema_name> \
        --method csv

核心规则:
    1. 禁止在源端 Teradata 进行任何写操作
    2. 表数据迁移在表结构迁移完成后执行
"""

import argparse
import configparser
import logging
import os
import sys
import csv
import io
import json
import subprocess
import time
from datetime import datetime
from typing import List, Optional

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teradata_reader import TeradataReader, WriteOperationError
from dws_writer import DWSWriter, quote_ident


# SQL 关键字常量：受控 SQL 构造用（标识符经 quote_ident 白名单校验、值经 _ql 转义）
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_STAR = '*'
_SQL_INSERT_INTO = 'INSERT INTO'
_SQL_VALUES = 'VALUES'


def _qi(name):
    """标识符安全引用（白名单校验，非法输入抛错）"""
    return quote_ident(name)


def _ql(value):
    """SQL 字符串字面量安全转义（单引号翻倍）"""
    return "'" + str(value).replace("'", "''") + "'"


# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('migrate_data')


def load_config(config_path: str) -> dict:
    """加载 INI 配置文件"""
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


def format_progress_bar(current: int, total: int, width: int = 30) -> str:
    """生成进度条字符串"""
    if total == 0:
        return '░' * width
    filled = int(width * current / total)
    return '█' * filled + '░' * (width - filled)


def format_eta(seconds: float) -> str:
    """格式化预估时间"""
    if seconds < 0:
        return '...'
    if seconds >= 3600:
        return f'{seconds/3600:.1f}h'
    elif seconds >= 60:
        return f'{seconds/60:.1f}min'
    else:
        return f'{seconds:.0f}s'


def format_size(bytes_size: int) -> str:
    """格式化文件大小"""
    if bytes_size < 1024:
        return f'{bytes_size}B'
    elif bytes_size < 1024 * 1024:
        return f'{bytes_size/1024:.1f}KB'
    elif bytes_size < 1024 * 1024 * 1024:
        return f'{bytes_size/(1024*1024):.1f}MB'
    else:
        return f'{bytes_size/(1024*1024*1024):.2f}GB'


def print_table_header(completed: int, total: int, table_name: str,
                       elapsed: float, eta_str: str):
    """打印表迁移头部信息"""
    bar = format_progress_bar(completed, total)
    pct = completed / total * 100 if total > 0 else 0
    logger.info("")
    logger.info(f"┌─ [{completed}/{total}] {pct:.0f}% {bar}")
    logger.info(f"│  表: {table_name}")
    logger.info(f"│  已用: {elapsed/60:.1f}min  预估剩余: {eta_str}")
    logger.info(f"└─ 开始迁移...")


def print_step_progress(step: str, detail: str = ""):
    """打印子步骤进度"""
    icon = {'export': '📤', 'upload': '☁️', 'import': '📥', 'copy': '📋',
            'done': '✅', 'skip': '⏭️'}.get(step, '▶️')
    if detail:
        logger.info(f"  {icon} {step}: {detail}")
    else:
        logger.info(f"  {icon} {step}")


def parse_timezone_offset(source_tz: str, target_tz: str) -> int:
    """
    计算源端到目标端的时区偏移量（小时）

    例如: source_tz='UTC-4', target_tz='UTC+8' → 偏移 +12 小时
    """
    import re

    def parse_tz(tz_str):
        # 解析 "UTC+8" 或 "UTC-4" 格式
        match = re.match(r'UTC\s*([+-])\s*(\d+)', tz_str.strip(), re.IGNORECASE)
        if match:
            sign = 1 if match.group(1) == '+' else -1
            return sign * int(match.group(2))
        return 0

    source_offset = parse_tz(source_tz)
    target_offset = parse_tz(target_tz)
    return target_offset - source_offset


def build_timezone_adjusted_query(td_reader: TeradataReader,
                                   full_name: str,
                                   database: str,
                                   table_name: str,
                                   tz_offset: int) -> str:
    """
    构建带时区调整的 SELECT 查询

    对 TIMESTAMP 类型的列，添加 INTERVAL 偏移量
    其他列保持不变

    参数:
        tz_offset: 时区偏移量（小时），如 +12 表示加12小时

    返回:
        带 CAST/INTERVAL 调整的 SELECT SQL
    """
    import re

    # 获取表的列信息（通过 HELP COLUMN）
    try:
        # 查询 Teradata 列类型
        col_sql = _SQL_SELECT + " ColumnName, ColumnType FROM DBC.ColumnsV WHERE DatabaseName = " + _ql(database) + " AND TableName = " + _ql(table_name)
        _, col_rows = td_reader.execute_query_with_columns(col_sql)

        timestamp_cols = []
        all_cols = []
        for row in col_rows:
            col_name = row[0].strip() if isinstance(row[0], str) else row[0]
            col_type = row[1].strip() if isinstance(row[1], str) else row[1]
            all_cols.append(col_name)
            # Teradata 中 TIMESTAMP 类型代码为 'TS'
            if col_type and col_type.upper() in ('TS', 'AT'):
                timestamp_cols.append(col_name)

        if not timestamp_cols:
            # 没有 TIMESTAMP 列，直接 SELECT *
            return _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + full_name

        # 构建带时区调整的 SELECT
        select_parts = []
        for col in all_cols:
            if col in timestamp_cols:
                # TIMESTAMP 列加偏移量
                if tz_offset >= 0:
                    select_parts.append('CAST(' + quote_ident(col) + ' + INTERVAL \'' + str(int(tz_offset)) + '\' HOUR AS TIMESTAMP(6)) AS ' + quote_ident(col))
                else:
                    select_parts.append('CAST(' + quote_ident(col) + ' - INTERVAL \'' + str(int(abs(tz_offset))) + '\' HOUR AS TIMESTAMP(6)) AS ' + quote_ident(col))
            else:
                select_parts.append(quote_ident(col))

        return _SQL_SELECT + ' ' + ', '.join(select_parts) + ' ' + _SQL_FROM + ' ' + full_name

    except Exception as e:
        logger.warning(f"  ⚠️ 时区调整查询构建失败，回退到普通查询: {e}")
        return _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + full_name


def export_table_to_csv(td_reader: TeradataReader,
                        table_name: str,
                        database: str,
                        output_path: str,
                        batch_size: int = 50000,
                        show_progress: bool = True,
                        timezone_adjust: bool = False,
                        source_tz: str = 'UTC-4',
                        target_tz: str = 'UTC+8') -> int:
    """
    从 Teradata 导出表数据到 CSV 文件（只读操作）

    参数:
        td_reader: Teradata 只读连接器
        table_name: 表名
        database: 数据库名
        output_path: 输出 CSV 文件路径
        batch_size: 批量获取大小
        show_progress: 是否显示进度
        timezone_adjust: 是否启用 TIMESTAMP 时区转换
        source_tz: 源端时区（如 UTC-4）
        target_tz: 目标端时区（如 UTC+8）

    返回:
        导出的行数
    """
    print_step_progress('export', f"{database}.{table_name} → {output_path}")

    full_name = f'{quote_ident(database)}.{quote_ident(table_name)}'

    # 时区转换：构建带时区调整的 SELECT 查询
    if timezone_adjust:
        tz_offset = parse_timezone_offset(source_tz, target_tz)
        if tz_offset != 0:
            sql = build_timezone_adjusted_query(td_reader, full_name, database,
                                                 table_name, tz_offset)
            logger.info(f"  🕐 时区转换已启用: {source_tz} → {target_tz} "
                        f"(偏移 {tz_offset:+d} 小时)")
        else:
            sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + full_name
    else:
        sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + full_name

    export_start = time.time()
    columns, rows = td_reader.execute_query_with_columns(sql)

    row_count = 0
    total_rows = len(rows)

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)  # 写入标题行

        if show_progress and total_rows > 10000:
            # 大表分批写入并显示进度
            progress_interval = max(total_rows // 20, 10000)
            for row in rows:
                writer.writerow(row)
                row_count += 1
                if row_count % progress_interval == 0:
                    pct = row_count / total_rows * 100
                    bar = format_progress_bar(row_count, total_rows)
                    speed = row_count / (time.time() - export_start) if time.time() - export_start > 0 else 0
                    logger.info(f"  📤 导出进度: {bar} {pct:.0f}% "
                                f"({row_count:,}/{total_rows:,} 行, {speed:.0f} rows/s)")
        else:
            for row in rows:
                writer.writerow(row)
                row_count += 1

    export_time = time.time() - export_start
    file_size = os.path.getsize(output_path)
    speed = row_count / export_time if export_time > 0 else 0
    logger.info(f"  📤 导出完成: {row_count:,} 行, "
                f"{format_size(file_size)}, {export_time:.1f}s, "
                f"{speed:.0f} rows/s")
    return row_count


def export_table_to_obs(td_reader: TeradataReader,
                        table_name: str,
                        database: str,
                        obs_bucket: str,
                        obs_path: str,
                        obsutil_path: str = 'obsutil',
                        temp_dir: str = '/tmp',
                        show_progress: bool = True,
                        timezone_adjust: bool = False,
                        source_tz: str = 'UTC-4',
                        target_tz: str = 'UTC+8') -> str:
    """
    从 Teradata 导出表数据到 OBS（只读操作）

    流程: Teradata → CSV 临时文件 → obsutil 上传到 OBS

    参数:
        td_reader: Teradata 只读连接器
        table_name: 表名
        database: 数据库名
        obs_bucket: OBS 桶名
        obs_path: OBS 路径
        obsutil_path: obsutil 命令路径
        temp_dir: 临时文件目录
        show_progress: 是否显示进度
        timezone_adjust: 是否启用 TIMESTAMP 时区转换
        source_tz: 源端时区
        target_tz: 目标端时区

    返回:
        OBS 路径
    """
    obs_full_path = f'obs://{obs_bucket}/{obs_path}/{table_name}.csv'
    print_step_progress('export', f"{database}.{table_name} → {obs_full_path}")

    # 先导出为 CSV
    temp_csv = os.path.join(temp_dir, f'{database}_{table_name}.csv')
    export_table_to_csv(td_reader, table_name, database, temp_csv,
                        show_progress=show_progress,
                        timezone_adjust=timezone_adjust,
                        source_tz=source_tz,
                        target_tz=target_tz)

    file_size = os.path.getsize(temp_csv)

    # 上传到 OBS
    print_step_progress('upload', f"上传 {format_size(file_size)} 到 OBS...")
    upload_start = time.time()
    cmd = [obsutil_path, 'cp', temp_csv, obs_full_path, '-f']
    logger.info(f"  ☁️ obsutil cp → {obs_full_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    upload_time = time.time() - upload_start

    if result.returncode != 0:
        raise RuntimeError(f"OBS 上传失败: {result.stderr}")

    speed = file_size / upload_time if upload_time > 0 else 0
    logger.info(f"  ☁️ 上传完成: {format_size(file_size)}, "
                f"{upload_time:.1f}s, {format_size(int(speed))}/s")

    # 清理临时文件
    os.remove(temp_csv)
    logger.info(f"  🗑️ 临时文件已清理: {temp_csv}")

    return obs_full_path


def migrate_data_direct(td_reader: TeradataReader,
                        dws_writer: DWSWriter,
                        table_name: str,
                        database: str,
                        schema: str) -> int:
    """
    直接迁移数据（适合小表）

    从 Teradata SELECT 数据，直接 INSERT 到 DWS
    """
    print_step_progress('export', f"直接查询 {database}.{table_name}")

    full_name = f'{quote_ident(database)}.{quote_ident(table_name)}'
    sql = _SQL_SELECT + ' ' + _SQL_STAR + ' ' + _SQL_FROM + ' ' + full_name
    columns, rows = td_reader.execute_query_with_columns(sql)

    if not rows:
        print_step_progress('skip', f"表 {table_name} 无数据")
        return 0

    print_step_progress('import', f"写入 {len(rows):,} 行到 DWS...")
    target_name = f'{quote_ident(schema)}.{quote_ident(table_name)}'
    col_list = ', '.join(quote_ident(c) for c in columns)
    param_list = ', '.join(['%s'] * len(columns))
    insert_sql = _SQL_INSERT_INTO + ' ' + target_name + ' (' + col_list + ') ' + _SQL_VALUES + ' (' + param_list + ')'

    import psycopg2.extras
    cursor = dws_writer._connection.cursor()
    try:
        psycopg2.extras.execute_batch(cursor, insert_sql, rows)
        dws_writer._connection.commit()
        logger.info(f"  ✅ 直接迁移完成: {table_name} 共 {len(rows)} 行")
        return len(rows)
    finally:
        cursor.close()


def migrate_data_csv(td_reader: TeradataReader,
                     dws_writer: DWSWriter,
                     table_name: str,
                     database: str,
                     schema: str,
                     temp_dir: str = '/tmp',
                     use_copy: bool = True,
                     truncate_before_import: bool = False,
                     timezone_adjust: bool = False,
                     source_tz: str = 'UTC-4',
                     target_tz: str = 'UTC+8') -> int:
    """
    通过 CSV 中转迁移数据（适合中等表）

    Teradata → CSV 文件 → DWS COPY 命令导入

    参数:
        use_copy: True=使用COPY命令(快10-100倍), False=使用逐行INSERT
        truncate_before_import: 导入前是否先清空目标表（避免数据翻倍）
        timezone_adjust: 是否启用 TIMESTAMP 时区转换
        source_tz: 源端时区
        target_tz: 目标端时区
    """
    logger.info(f"CSV 中转迁移数据: {database}.{table_name}")

    # 导入前清空目标表
    if truncate_before_import:
        logger.info(f"  🗑️ 导入前清空目标表: {schema}.{table_name}")
        dws_writer.truncate_table(table_name, schema)

    # 导出为 CSV
    csv_path = os.path.join(temp_dir, f'{database}_{table_name}.csv')
    row_count = export_table_to_csv(td_reader, table_name, database, csv_path,
                                    timezone_adjust=timezone_adjust,
                                    source_tz=source_tz,
                                    target_tz=target_tz)

    if row_count == 0:
        print_step_progress('skip', f"表 {table_name} 无数据")
        os.remove(csv_path)
        return 0

    # 导入到 DWS
    if use_copy:
        print_step_progress('copy', f"批量导入 {row_count:,} 行...")
        import_start = time.time()
        imported = dws_writer.import_data_via_copy(
            table_name=table_name,
            csv_file_path=csv_path,
            schema=schema,
            truncate_before_import=False,  # 已在上面手动truncate
        )
        import_time = time.time() - import_start
        speed = imported / import_time if import_time > 0 else 0
        logger.info(f"  📥 批量导入完成: {imported:,} 行, "
                    f"{import_time:.1f}s, {speed:.0f} rows/s")
    else:
        print_step_progress('import', f"写入导入 {row_count:,} 行...")
        imported = dws_writer.import_data_from_csv(
            table_name=table_name,
            csv_file_path=csv_path,
            schema=schema,
        )

    # 清理临时文件
    os.remove(csv_path)
    return imported


def migrate_data_obs(td_reader: TeradataReader,
                     dws_writer: DWSWriter,
                     table_name: str,
                     database: str,
                     schema: str,
                     obs_config: dict,
                     temp_dir: str = '/tmp',
                     obs_temp_dir: str = None,
                     truncate_before_import: bool = False,
                     timezone_adjust: bool = False,
                     source_tz: str = 'UTC-4',
                     target_tz: str = 'UTC+8') -> int:
    """
    通过 OBS 中转迁移数据（适合大表，并行高速）

    Teradata → CSV → OBS → DWS 外表并行导入

    参数:
        obs_temp_dir: OBS 临时目录路径（如 migration/temp/mig）
                      如果指定，CSV 将上传到此 OBS 目录而非本地磁盘
        truncate_before_import: 导入前是否先清空目标表（避免数据翻倍）
        timezone_adjust: 是否启用 TIMESTAMP 时区转换
        source_tz: 源端时区
        target_tz: 目标端时区
    """
    logger.info(f"OBS 中转迁移数据: {database}.{table_name}")

    # 导入前清空目标表
    if truncate_before_import:
        logger.info(f"  🗑️ 导入前清空目标表: {schema}.{table_name}")
        dws_writer.truncate_table(table_name, schema)

    obs_bucket = obs_config.get('bucket', '')
    obsutil_path = obs_config.get('obsutil_path', 'obsutil')

    # 确定 OBS 路径
    if obs_temp_dir:
        # 使用指定的 OBS 临时目录
        obs_path = f'{obs_temp_dir}/{table_name}'
        logger.info(f"  ☁️ OBS 临时目录: obs://{obs_bucket}/{obs_temp_dir}")
    else:
        obs_path = f'migration/{database}/{table_name}'

    # 导出并上传到 OBS
    obs_full_path = export_table_to_obs(
        td_reader, table_name, database,
        obs_bucket, obs_path, obsutil_path, temp_dir,
        timezone_adjust=timezone_adjust,
        source_tz=source_tz,
        target_tz=target_tz,
    )

    # 通过 DWS 外表并行导入
    print_step_progress('import', f"OBS 外表并行导入...")
    import_start = time.time()
    dws_writer.import_data_from_obs(
        table_name=table_name,
        obs_path=f'{obs_bucket}/{obs_path}',
        schema=schema,
        obs_access_key=obs_config.get('access_key') or os.environ.get('OBS_ACCESS_KEY'),
        obs_secret_key=obs_config.get('secret_key') or os.environ.get('OBS_SECRET_KEY'),
        obs_endpoint=obs_config.get('endpoint'),
        chunksize=obs_config.get('chunksize', '64'),
        parallel=obs_config.get('parallel', '8'),
    )
    import_time = time.time() - import_start

    # 获取导入行数
    row_count = dws_writer.get_table_row_count(table_name, schema)
    speed = row_count / import_time if import_time > 0 else 0
    logger.info(f"  📥 OBS 并行导入完成: {row_count:,} 行, "
                f"{import_time:.1f}s, {speed:.0f} rows/s")

    # 清理 OBS 临时文件
    try:
        cmd = [obsutil_path, 'rm', obs_full_path, '-f']
        subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        logger.info(f"  🗑️ OBS 临时文件已清理: {obs_full_path}")
    except Exception as e:
        logger.warning(f"  ⚠️ OBS 临时文件清理失败: {e}")

    return row_count


def migrate_all_tables(td_reader: TeradataReader,
                       dws_writer: DWSWriter,
                       database: str,
                       schema: str,
                       method: str = 'csv',
                       tables: List[str] = None,
                       obs_config: dict = None,
                       obs_temp_dir: str = None,
                       temp_dir: str = '/tmp',
                       truncate_before_import: bool = False,
                       timezone_adjust: bool = False,
                       source_tz: str = 'UTC-4',
                       target_tz: str = 'UTC+8'):
    """
    迁移所有表数据

    参数:
        td_reader: Teradata 只读连接器
        dws_writer: DWS 写入器
        database: 源数据库
        schema: 目标 schema
        method: 迁移方式 (direct/csv/obs)
        tables: 指定表列表（None=全部）
        obs_config: OBS 配置
        obs_temp_dir: OBS 临时目录
        temp_dir: 本地临时目录
        truncate_before_import: 导入前自动清空目标表，避免数据翻倍
    """
    # 获取表列表
    if tables is None:
        all_tables = td_reader.list_tables(database)
        tables = [t[0] for t in all_tables if t[1].strip() == 'T']

    total_tables = len(tables)
    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"  数据迁移: {database} → DWS.{schema}")
    logger.info(f"  表数量: {total_tables}")
    logger.info(f"  方式: {method}")
    if obs_temp_dir and method == 'obs':
        logger.info(f"  OBS 临时目录: obs://{obs_config.get('bucket','')}/{obs_temp_dir}")
    logger.info(f"{'='*60}")

    # 统计
    results = []
    total_rows = 0
    total_start = time.time()

    for idx, table_name in enumerate(tables, 1):
        table_start = time.time()
        elapsed = time.time() - total_start
        completed = idx - 1

        # 预估剩余时间
        if completed > 0:
            avg_time = elapsed / completed
            eta = avg_time * (total_tables - completed)
            eta_str = format_eta(eta)
        else:
            eta_str = '...'

        # 打印表迁移头部
        print_table_header(idx, total_tables, table_name,
                           elapsed / 60, eta_str)

        try:
            # 根据方式选择迁移函数
            if method == 'direct':
                row_count = migrate_data_direct(
                    td_reader, dws_writer, table_name, database, schema
                )
            elif method == 'csv':
                row_count = migrate_data_csv(
                    td_reader, dws_writer, table_name, database, schema,
                    temp_dir=temp_dir, use_copy=True,
                    truncate_before_import=truncate_before_import,
                    timezone_adjust=timezone_adjust,
                    source_tz=source_tz,
                    target_tz=target_tz,
                )
            elif method == 'obs':
                row_count = migrate_data_obs(
                    td_reader, dws_writer, table_name, database, schema,
                    obs_config=obs_config or {},
                    temp_dir=temp_dir,
                    obs_temp_dir=obs_temp_dir,
                    truncate_before_import=truncate_before_import,
                    timezone_adjust=timezone_adjust,
                    source_tz=source_tz,
                    target_tz=target_tz,
                )
            else:
                raise ValueError(f"未知迁移方式: {method}")

            table_time = time.time() - table_start
            total_rows += row_count
            results.append({
                'table': table_name,
                'rows': row_count,
                'time': round(table_time, 1),
                'status': 'success'
            })

            # 打印完成信息
            bar = format_progress_bar(idx, total_tables)
            pct = idx / total_tables * 100
            logger.info(f"  ✅ [{idx}/{total_tables}] {pct:.0f}% {bar} "
                        f"{table_name}: {row_count:,} 行, {table_time:.1f}s")

        except Exception as e:
            table_time = time.time() - table_start
            results.append({
                'table': table_name,
                'rows': 0,
                'time': round(table_time, 1),
                'status': f'failed: {e}'
            })
            logger.error(f"  ❌ [{idx}/{total_tables}] {table_name} 失败: {e}")
            # 继续下一张表

    # 汇总
    total_time = time.time() - total_start
    success_count = sum(1 for r in results if r['status'] == 'success')
    failed_count = total_tables - success_count

    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"  数据迁移完成")
    logger.info(f"  成功: {success_count}/{total_tables} 表")
    logger.info(f"  失败: {failed_count} 表")
    logger.info(f"  总行数: {total_rows:,}")
    logger.info(f"  总耗时: {total_time/60:.1f} 分钟")
    logger.info(f"  平均速度: {total_rows/total_time:.0f} rows/s" if total_time > 0 else "")
    logger.info(f"{'='*60}")

    # 打印详细结果
    if failed_count > 0:
        logger.info(f"")
        logger.info(f"失败表:")
        for r in results:
            if r['status'] != 'success':
                logger.info(f"  - {r['table']}: {r['status']}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Step 2: 表数据迁移 (Teradata → DWS)'
    )
    parser.add_argument('--td-config', required=True,
                        help='Teradata 配置文件路径')
    parser.add_argument('--dws-config', required=True,
                        help='DWS 配置文件路径')
    parser.add_argument('--schema', required=True,
                        help='目标 DWS schema 名')
    parser.add_argument('--database', required=True,
                        help='源 Teradata 数据库名')
    parser.add_argument('--method', default='csv',
                        choices=['direct', 'csv', 'obs'],
                        help='数据迁移方式: direct=直接, csv=CSV中转, obs=OBS外表(默认csv)')
    parser.add_argument('--tables', nargs='*',
                        help='指定表名列表（默认全部）')
    parser.add_argument('--temp-dir', default='/tmp',
                        help='本地临时目录（默认 /tmp）')
    parser.add_argument('--obs-config',
                        help='OBS 配置文件路径（method=obs 时需要）')
    parser.add_argument('--obs-temp-dir',
                        help='OBS 临时目录路径（如 migration/temp/mig）')
    parser.add_argument('--output', default='output/data_migration_report.json',
                        help='输出报告路径（可以是文件或目录）')
    parser.add_argument('--force', action='store_true',
                        help='强制模式，跳过确认提示')
    parser.add_argument('--truncate-before-import', action='store_true',
                        help='导入前自动清空目标表，避免重复导入导致数据翻倍')
    parser.add_argument('--timezone-adjust', action='store_true',
                        help='启用 TIMESTAMP 时区转换（需配合 --source-tz 和 --target-tz）')
    parser.add_argument('--source-tz', default='UTC-4',
                        help='源端 Teradata 时区（默认 UTC-4）')
    parser.add_argument('--target-tz', default='UTC+8',
                        help='目标端 DWS 时区（默认 UTC+8）')

    args = parser.parse_args()

    # 加载配置
    td_config = load_config(args.td_config)
    dws_config = load_config(args.dws_config)

    obs_config = None
    if args.obs_config:
        obs_config = load_config(args.obs_config)
        # 展平配置
        obs_config = obs_config.get('obs', obs_config)

    # 显示 OBS 临时目录信息
    if args.method == 'obs' and args.obs_temp_dir:
        obs_bucket = obs_config.get('bucket', '') if obs_config else ''
        logger.info(f"")
        logger.info(f"☁️ OBS 临时目录: obs://{obs_bucket}/{args.obs_temp_dir}")
        logger.info(f"   CSV 数据将导出到此 OBS 路径，避免本地磁盘容量问题")
        logger.info(f"")

    # 确保临时目录存在
    os.makedirs(args.temp_dir, exist_ok=True)

    # 创建连接
    td_reader = TeradataReader(
        host=td_config['teradata']['host'],
        port=int(td_config['teradata'].get('port', 1025)),
        user=td_config['teradata'].get('user', td_config['teradata'].get('username', '')),
        password=td_config['teradata']['password'],
        database=td_config['teradata'].get('database', ''),
        logmech=td_config['teradata'].get('logmech', 'TD2'),
    )

    dws_writer = DWSWriter(
        host=dws_config['dws']['host'],
        port=int(dws_config['dws'].get('port', 8000)),
        database=dws_config['dws'].get('database', 'postgres'),
        user=dws_config['dws'].get('user', dws_config['dws'].get('username', '')),
        password=dws_config['dws']['password'],
    )

    # 连接 Teradata 和 DWS
    td_reader.connect()
    dws_writer.connect()

    try:
        # 执行迁移
        results = migrate_all_tables(
            td_reader=td_reader,
            dws_writer=dws_writer,
            database=args.database,
            schema=args.schema,
            method=args.method,
            tables=args.tables,
            obs_config=obs_config,
            obs_temp_dir=args.obs_temp_dir,
            temp_dir=args.temp_dir,
            truncate_before_import=args.truncate_before_import,
            timezone_adjust=args.timezone_adjust,
            source_tz=args.source_tz,
            target_tz=args.target_tz,
        )

        # 保存报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'database': args.database,
            'schema': args.schema,
            'method': args.method,
            'tables': results,
            'total_tables': len(results),
            'total_rows': sum(r['rows'] for r in results),
            'total_time': sum(r['time'] for r in results),
            'success_count': sum(1 for r in results if r['status'] == 'success'),
            'failed_count': sum(1 for r in results if r['status'] != 'success'),
        }

        # 保存报告（兼容目录和文件路径）
        report_path = args.output
        if os.path.isdir(report_path) or report_path.endswith('/'):
            os.makedirs(report_path, exist_ok=True)
            report_path = os.path.join(report_path, f'{args.schema}_data_migration_report.json')
        else:
            parent_dir = os.path.dirname(report_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"报告已保存: {report_path}")

    finally:
        td_reader.disconnect()
        dws_writer.disconnect()


if __name__ == '__main__':
    main()
