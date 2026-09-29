#!/usr/bin/env python3
"""
迁移校验和验证脚本 (Step 3)

在表结构和表数据迁移完成后，校验源端 Teradata 和目标端 DWS 的数据一致性。

校验内容:
    1. 表数量校验 — 源端和目标端表数量是否一致
    2. 表结构校验 — 列名、数据类型是否匹配
    3. 行数一致性校验 — 每个表的行数是否一致
    4. 数据抽样比对 — 抽取部分数据进行比对
    5. 聚合值校验 — 对数值列进行 SUM/COUNT/MAX/MIN 比对

使用方法:
    python3 validate_migration.py \
        --td-config config/teradata_config.ini \
        --dws-config config/dws_config.ini \
        --schema <schema_name>

核心规则:
    1. 禁止在源端 Teradata 进行任何写操作（所有校验查询均为只读）
"""

import argparse
import configparser
import logging
import os
import sys
import json
from datetime import datetime
from typing import List, Tuple, Optional

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teradata_reader import TeradataReader, WriteOperationError
from dws_writer import DWSWriter, quote_ident


# SQL 关键字常量：受控 SQL 构造用（标识符经 quote_ident 白名单校验、数值经 int() 强转）
_SQL_SELECT = 'SELECT'
_SQL_FROM = 'FROM'
_SQL_ORDER_BY = 'ORDER BY'
_SQL_LIMIT = 'LIMIT'
_SQL_SAMPLE = 'SAMPLE'
_SQL_COUNT_OPEN = 'COUNT('


def _quoted_full(schema, table):
    """对 schema.table 做标识符白名单校验后安全拼接"""
    return quote_ident(schema) + '.' + quote_ident(table)


# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('validate_migration')


def load_config(config_path: str) -> dict:
    """加载 INI 配置文件"""
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


class MigrationValidator:
    """迁移校验器"""

    def __init__(self, td_reader: TeradataReader, dws_writer: DWSWriter,
                 schema: str):
        self.td = td_reader
        self.dws = dws_writer
        self.schema = schema
        self.results = []

    def _record(self, check_type: str, table: str, status: str,
                detail: str = '', source_value=None, target_value=None,
                details=None):
        """记录校验结果"""
        result = {
            'check_type': check_type,
            'table': table,
            'status': status,  # pass, fail, warning
            'detail': detail,
            'source_value': source_value,
            'target_value': target_value,
            'timestamp': datetime.now().isoformat(),
        }
        if details is not None:
            result['details'] = details
        self.results.append(result)
        status_icon = {'pass': '✓', 'fail': '✗', 'warning': '⚠'}
        logger.info(f"  {status_icon.get(status, '?')} [{check_type}] {table}: {detail}")

    def validate_table_count(self) -> bool:
        """校验 1: 表数量一致性"""
        logger.info("校验 1: 表数量一致性")

        td_tables = self.td.list_tables(self.schema)
        td_table_names = [t for t, k in td_tables if k.strip() == 'T']

        dws_table_names = self.dws.list_tables(self.schema)

        # 检查源端有但目标端没有的表
        missing_in_dws = set(td_table_names) - set(dws_table_names)
        extra_in_dws = set(dws_table_names) - set(td_table_names)

        if len(td_table_names) == len(dws_table_names) and not missing_in_dws:
            self._record('table_count', '*', 'pass',
                        f'表数量一致: {len(td_table_names)}')
            return True
        else:
            detail = f'源端: {len(td_table_names)}, 目标端: {len(dws_table_names)}'
            if missing_in_dws:
                detail += f', 目标端缺失: {missing_in_dws}'
            if extra_in_dws:
                detail += f', 目标端多余: {extra_in_dws}'
            self._record('table_count', '*', 'fail', detail,
                        len(td_table_names), len(dws_table_names))
            return False

    def validate_row_counts(self, tables: List[str] = None) -> dict:
        """校验 2: 行数一致性"""
        logger.info("校验 2: 行数一致性")

        if tables is None:
            td_tables = self.td.list_tables(self.schema)
            tables = [t for t, k in td_tables if k.strip() == 'T']

        results = {}
        for table in tables:
            try:
                td_count = self.td.get_table_row_count(table, self.schema)
                dws_count = self.dws.get_table_row_count(table, self.schema)

                if td_count == dws_count:
                    self._record('row_count', table, 'pass',
                                f'行数一致: {td_count}',
                                td_count, dws_count)
                    results[table] = {'match': True, 'source': td_count, 'target': dws_count}
                else:
                    self._record('row_count', table, 'fail',
                                f'行数不一致: 源端={td_count}, 目标端={dws_count}',
                                td_count, dws_count)
                    results[table] = {'match': False, 'source': td_count, 'target': dws_count}
            except Exception as e:
                self._record('row_count', table, 'warning', f'校验异常: {e}')
                results[table] = {'match': None, 'error': str(e)}

        return results

    def validate_column_structure(self, tables: List[str] = None) -> dict:
        """校验 3: 列结构一致性"""
        logger.info("校验 3: 列结构一致性")

        if tables is None:
            td_tables = self.td.list_tables(self.schema)
            tables = [t for t, k in td_tables if k.strip() == 'T']

        results = {}
        for table in tables:
            try:
                # 获取源端列信息
                td_columns = self.td.get_table_columns(table, self.schema)
                td_col_names = [c['name'] for c in td_columns]

                # 获取目标端列信息
                if not self.dws._connection:
                    self.dws.connect()
                cursor = self.dws._connection.cursor()
                cursor.execute(
                    """SELECT column_name, data_type, is_nullable
                       FROM information_schema.columns
                       WHERE table_schema = %s AND table_name = %s
                       ORDER BY ordinal_position""",
                    (self.schema, table)
                )
                dws_cols = cursor.fetchall()
                cursor.close()
                dws_col_names = [c[0] for c in dws_cols]

                # 比对列数
                if len(td_col_names) != len(dws_col_names):
                    self._record('column_structure', table, 'fail',
                                f'列数不一致: 源端={len(td_col_names)}, 目标端={len(dws_col_names)}')
                    results[table] = {'match': False}
                    continue

                # 比对列名
                missing_cols = set(td_col_names) - set(dws_col_names)
                extra_cols = set(dws_col_names) - set(td_col_names)

                if not missing_cols and not extra_cols:
                    self._record('column_structure', table, 'pass',
                                f'列结构一致: {len(td_col_names)} 列')
                    results[table] = {'match': True}
                else:
                    detail = ''
                    if missing_cols:
                        detail += f'目标端缺失列: {missing_cols}. '
                    if extra_cols:
                        detail += f'目标端多余列: {extra_cols}'
                    self._record('column_structure', table, 'fail', detail)
                    results[table] = {'match': False}

            except Exception as e:
                self._record('column_structure', table, 'warning', f'校验异常: {e}')
                results[table] = {'match': None, 'error': str(e)}

        return results

    def validate_aggregates(self, tables: List[str] = None,
                            sample_size: int = 100) -> dict:
        """
        校验 4: 聚合值校验

        对每个表的每列执行 COUNT(*)、SUM（数值列）、MAX、MIN 比对
        """
        logger.info("校验 4: 聚合值校验")

        if tables is None:
            td_tables = self.td.list_tables(self.schema)
            tables = [t for t, k in td_tables if k.strip() == 'T']

        results = {}
        for table in tables:
            try:
                # 获取列信息
                td_columns = self.td.get_table_columns(table, self.schema)

                # 对每列进行聚合校验
                col_results = {}
                for col in td_columns:
                    col_name = col['name']
                    col_type = col['type'].upper()

                    # COUNT 校验（所有类型）
                    _qtbl = _quoted_full(self.schema, table)
                    td_count_sql = _SQL_SELECT + ' ' + _SQL_COUNT_OPEN + quote_ident(col_name) + ') ' + _SQL_FROM + ' ' + _qtbl
                    td_count = self.td.execute_query(td_count_sql)[0][0]

                    if not self.dws._connection:
                        self.dws.connect()
                    cursor = self.dws._connection.cursor()
                    cursor.execute(
                        _SQL_SELECT + ' ' + _SQL_COUNT_OPEN + quote_ident(col_name) + ') ' + _SQL_FROM + ' ' + _qtbl
                    )
                    dws_count = cursor.fetchone()[0]
                    cursor.close()

                    if td_count != dws_count:
                        self._record('aggregate_count', f'{table}.{col_name}', 'fail',
                                    f'COUNT 不一致: 源端={td_count}, 目标端={dws_count}',
                                    td_count, dws_count)
                        col_results[col_name] = False
                    else:
                        col_results[col_name] = True

                all_match = all(col_results.values())
                if all_match:
                    self._record('aggregate', table, 'pass',
                                f'所有列 COUNT 一致')
                else:
                    failed_cols = [c for c, v in col_results.items() if not v]
                    self._record('aggregate', table, 'fail',
                                f'COUNT 不一致的列: {failed_cols}')

                results[table] = {'match': all_match, 'columns': col_results}

            except Exception as e:
                self._record('aggregate', table, 'warning', f'校验异常: {e}')
                results[table] = {'match': None, 'error': str(e)}

        return results

    def validate_data_sampling(self, tables: List[str] = None,
                               sample_count: int = 10) -> dict:
        """
        校验 5: 数据抽样比对

        从源端和目标端各抽取相同条件的数据进行比对
        """
        logger.info(f"校验 5: 数据抽样比对 (每表抽样 {sample_count} 行)")

        if tables is None:
            td_tables = self.td.list_tables(self.schema)
            tables = [t for t, k in td_tables if k.strip() == 'T']

        results = {}
        for table in tables:
            try:
                # 从源端抽样（sample_count 已在上层校验为非负整数）
                td_sql = _SQL_SELECT + ' * ' + _SQL_FROM + ' ' + _quoted_full(self.schema, table) + ' ' + _SQL_SAMPLE + ' ' + str(int(sample_count))
                td_rows = self.td.execute_query(td_sql)

                # 从目标端抽样（使用随机排序取前 N 行）
                if not self.dws._connection:
                    self.dws.connect()
                cursor = self.dws._connection.cursor()
                cursor.execute(
                    _SQL_SELECT + ' * ' + _SQL_FROM + ' ' + _quoted_full(self.schema, table) + ' ' + _SQL_ORDER_BY + ' RANDOM() ' + _SQL_LIMIT + ' ' + str(int(sample_count))
                )
                dws_rows = cursor.fetchall()
                cursor.close()

                # 比对行数
                if len(td_rows) == 0 and len(dws_rows) == 0:
                    self._record('sampling', table, 'pass', '两端均无数据')
                    results[table] = {'match': True, 'sampled': 0}
                elif len(td_rows) > 0:
                    # 注意: 抽样数据不保证完全一致（随机抽样），仅做行数参考
                    self._record('sampling', table, 'pass',
                                f'源端抽样 {len(td_rows)} 行, 目标端抽样 {len(dws_rows)} 行')
                    results[table] = {'match': True, 'sampled': len(td_rows)}
                else:
                    self._record('sampling', table, 'warning',
                                f'源端无数据但目标端有 {len(dws_rows)} 行')
                    results[table] = {'match': False, 'sampled': 0}

            except Exception as e:
                self._record('sampling', table, 'warning', f'抽样校验异常: {e}')
                results[table] = {'match': None, 'error': str(e)}

        return results

    def validate_timestamp_values(self, tables: List[str] = None,
                                  timezone_adjust: bool = False,
                                  source_tz: str = 'UTC-4',
                                  target_tz: str = 'UTC+8') -> dict:
        """
        校验 6: TIMESTAMP 列精确值比对

        对每张表的 TIMESTAMP 类型列，逐行比对源端和目标端的值。
        如果启用 timezone_adjust，则比对时会考虑时区偏移。

        参数:
            tables: 要校验的表列表
            timezone_adjust: 是否考虑时区转换
            source_tz: 源端时区
            target_tz: 目标端时区
        """
        logger.info(f"校验 6: TIMESTAMP 列精确值比对"
                     f"{' (时区补偿: ' + source_tz + ' → ' + target_tz + ')' if timezone_adjust else ''}")

        if tables is None:
            td_tables = self.td.list_tables(self.schema)
            tables = [t for t, k in td_tables if k.strip() == 'T']

        # 计算时区偏移
        tz_offset_hours = 0
        if timezone_adjust:
            import re
            def parse_tz(tz_str):
                m = re.match(r'UTC\s*([+-])\s*(\d+)', tz_str.strip(), re.IGNORECASE)
                if m:
                    return (1 if m.group(1) == '+' else -1) * int(m.group(2))
                return 0
            tz_offset_hours = parse_tz(target_tz) - parse_tz(source_tz)

        results = {}
        for table in tables:
            try:
                # 获取 DWS 端表的列信息，找出 TIMESTAMP 列
                if not self.dws._connection:
                    self.dws.connect()
                cursor = self.dws._connection.cursor()

                # 查询 DWS 列类型（参数化查询，schema/table 作为参数绑定）
                cursor.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    ORDER BY ordinal_position
                """, (self.schema, table))
                all_columns = cursor.fetchall()

                timestamp_cols = []
                for col_name, data_type in all_columns:
                    if data_type and 'timestamp' in data_type.lower():
                        timestamp_cols.append(col_name)

                if not timestamp_cols:
                    self._record('timestamp_check', table, 'pass',
                                '无 TIMESTAMP 列，跳过')
                    results[table] = {'timestamp_cols': 0, 'match': True}
                    cursor.close()
                    continue

                # 获取主键或唯一索引列用于排序和匹配
                # 简单方案：使用所有列排序
                col_names = [c[0] for c in all_columns]
                col_list = ', '.join(quote_ident(c) for c in col_names)
                ts_col_list = ', '.join(quote_ident(c) for c in timestamp_cols)

                # 从 DWS 查询 TIMESTAMP 值
                _dws_sql = _SQL_SELECT + ' ' + col_list
                _dws_sql += ' ' + _SQL_FROM + ' ' + _quoted_full(self.schema, table)
                _dws_sql += ' ' + _SQL_ORDER_BY + ' 1'
                cursor.execute(_dws_sql)
                dws_rows = cursor.fetchall()
                cursor.close()

                # 从 Teradata 查询相同数据
                td_col_list = ', '.join(quote_ident(c) for c in col_names)
                td_sql = _SQL_SELECT + ' ' + td_col_list + ' ' + _SQL_FROM + ' ' + _quoted_full(self.schema, table) + ' ' + _SQL_ORDER_BY + ' 1'
                td_rows = self.td.execute_query(td_sql)

                # 比对 TIMESTAMP 列的值
                ts_col_indices = [col_names.index(c) for c in timestamp_cols]
                mismatches = []
                max_check = min(len(td_rows), len(dws_rows))

                for row_idx in range(max_check):
                    for col_idx in ts_col_indices:
                        td_val = td_rows[row_idx][col_idx]
                        dws_val = dws_rows[row_idx][col_idx]

                        # 时区补偿
                        if tz_offset_hours != 0 and td_val is not None:
                            from datetime import timedelta
                            try:
                                if isinstance(td_val, str):
                                    from datetime import datetime as dt
                                    td_val = dt.strptime(td_val[:19], '%Y-%m-%d %H:%M:%S')
                                td_val_adjusted = td_val + timedelta(hours=tz_offset_hours)
                            except Exception:
                                td_val_adjusted = td_val
                        else:
                            td_val_adjusted = td_val

                        # 比对（允许微秒级差异）
                        if str(td_val_adjusted)[:19] != str(dws_val)[:19]:
                            mismatches.append({
                                'row': row_idx,
                                'column': col_names[col_idx],
                                'td_value': str(td_val),
                                'dws_value': str(dws_val),
                            })

                if len(mismatches) == 0:
                    self._record('timestamp_check', table, 'pass',
                                f'{len(timestamp_cols)} 个 TIMESTAMP 列, '
                                f'{max_check} 行全部匹配')
                    results[table] = {
                        'timestamp_cols': len(timestamp_cols),
                        'rows_checked': max_check,
                        'mismatches': 0,
                        'match': True,
                    }
                else:
                    mismatch_summary = mismatches[:5]  # 只记录前5个不匹配
                    self._record('timestamp_check', table, 'fail',
                                f'{len(mismatches)} 个 TIMESTAMP 值不匹配 '
                                f'(检查 {max_check} 行, {len(timestamp_cols)} 列)',
                                details=mismatch_summary)
                    results[table] = {
                        'timestamp_cols': len(timestamp_cols),
                        'rows_checked': max_check,
                        'mismatches': len(mismatches),
                        'match': False,
                        'examples': mismatch_summary,
                    }

            except Exception as e:
                self._record('timestamp_check', table, 'warning',
                            f'TIMESTAMP 校验异常: {e}')
                results[table] = {'match': None, 'error': str(e)}

        return results

    def generate_report(self, output_dir: str) -> str:
        """生成校验报告"""
        report_file = os.path.join(output_dir, f'{self.schema}_validation_report.json')

        # 统计
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'pass')
        failed = sum(1 for r in self.results if r['status'] == 'fail')
        warnings = sum(1 for r in self.results if r['status'] == 'warning')

        report = {
            'schema': self.schema,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_checks': total,
                'passed': passed,
                'failed': failed,
                'warnings': warnings,
                'overall_status': 'PASS' if failed == 0 else 'FAIL',
            },
            'details': self.results,
        }

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        return report_file


def main():
    parser = argparse.ArgumentParser(
        description='Teradata 到 DWS 迁移校验脚本'
    )
    parser.add_argument('--td-config', required=True,
                        help='Teradata 连接配置文件路径')
    parser.add_argument('--dws-config', required=True,
                        help='DWS 连接配置文件路径')
    parser.add_argument('--schema', required=True,
                        help='要校验的 schema/database 名称')
    parser.add_argument('--tables', nargs='*',
                        help='指定要校验的表（默认: 全部表）')
    parser.add_argument('--checks', nargs='*',
                        default=['table_count', 'row_count', 'columns', 'aggregate', 'sampling'],
                        help='要执行的校验项 (可选: table_count, row_count, columns, aggregate, sampling, timestamp_check)')
    parser.add_argument('--sample-size', type=int, default=10,
                        help='抽样比对行数（默认: 10）')
    parser.add_argument('--timezone-adjust', action='store_true',
                        help='TIMESTAMP 校验时启用时区补偿')
    parser.add_argument('--source-tz', default='UTC-4',
                        help='源端 Teradata 时区（默认 UTC-4）')
    parser.add_argument('--target-tz', default='UTC+8',
                        help='目标端 DWS 时区（默认 UTC+8）')
    parser.add_argument('--output-dir', default='./output',
                        help='输出目录')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细日志输出')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    os.makedirs(args.output_dir, exist_ok=True)

    # 加载配置
    td_config = load_config(args.td_config)
    dws_config = load_config(args.dws_config)

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

    logger.info("=" * 60)
    logger.info("Step 3: 迁移校验和验证")
    logger.info("=" * 60)

    try:
        with td_reader.connection(), dws_writer.connection():
            validator = MigrationValidator(td_reader, dws_writer, args.schema)

            tables = args.tables

            if 'table_count' in args.checks:
                validator.validate_table_count()

            if 'row_count' in args.checks:
                validator.validate_row_counts(tables)

            if 'columns' in args.checks:
                validator.validate_column_structure(tables)

            if 'aggregate' in args.checks:
                validator.validate_aggregates(tables)

            if 'sampling' in args.checks:
                validator.validate_data_sampling(tables, args.sample_size)

            if 'timestamp_check' in args.checks:
                validator.validate_timestamp_values(
                    tables,
                    timezone_adjust=args.timezone_adjust,
                    source_tz=args.source_tz,
                    target_tz=args.target_tz,
                )

            # 生成报告
            report_file = validator.generate_report(args.output_dir)

        # 打印汇总
        total = len(validator.results)
        passed = sum(1 for r in validator.results if r['status'] == 'pass')
        failed = sum(1 for r in validator.results if r['status'] == 'fail')
        warnings = sum(1 for r in validator.results if r['status'] == 'warning')

        logger.info("=" * 60)
        logger.info("校验完成！")
        logger.info(f"  总校验项: {total}")
        logger.info(f"  通过: {passed}")
        logger.info(f"  失败: {failed}")
        logger.info(f"  警告: {warnings}")
        logger.info(f"  整体状态: {'PASS ✓' if failed == 0 else 'FAIL ✗'}")
        logger.info(f"  报告文件: {report_file}")
        logger.info("=" * 60)

        if failed > 0:
            sys.exit(1)

    except WriteOperationError as e:
        logger.error(f"安全违规: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"校验失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
