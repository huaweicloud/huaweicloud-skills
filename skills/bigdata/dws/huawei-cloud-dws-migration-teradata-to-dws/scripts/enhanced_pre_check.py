#!/usr/bin/env python3
"""
增强预检脚本 — 在原有预检基础上增加：
  1. 时区评估（Teradata vs DWS）
  2. 字符串长度确认（两端 CHAR/VARCHAR 长度一致性）
  3. 大小敏感性检查（库表名大小写敏感性）

使用方法:
    python3 enhanced_pre_check.py \
        --td-config config/teradata_config.ini \
        --dws-config config/dws_config.ini \
        --schemas mig,app_sales \
        --output-dir ./output
"""

import argparse
import configparser
import logging
import os
import sys
import json
import time
import socket
from datetime import datetime
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teradata_reader import TeradataReader, WriteOperationError

try:
    import psycopg2
except ImportError:
    psycopg2 = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('enhanced_pre_check')


def load_config(config_path: str) -> dict:
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


class CheckResult:
    def __init__(self, name: str, status: str, detail: str,
                 data: dict = None, warning: str = None):
        self.name = name
        self.status = status
        self.detail = detail
        self.data = data or {}
        self.warning = warning

    def __str__(self):
        icon = {'pass': '✅', 'fail': '❌', 'warn': '⚠️'}[self.status]
        line = f"  {icon} {self.name}: {self.detail}"
        if self.warning:
            line += f"\n     ⚠️  {self.warning}"
        return line

    def to_dict(self):
        return {
            'name': self.name, 'status': self.status,
            'detail': self.detail, 'data': self.data, 'warning': self.warning,
        }


# ============================================================
# 1. 时区评估
# ============================================================
def check_timezone(td_reader: TeradataReader, dws_config: dict) -> List[CheckResult]:
    """评估两端时区设置是否一致"""
    results = []
    logger.info("检查时区设置...")

    td_tz = None
    td_tz_offset = None

    # Teradata 时区查询
    try:
        td_reader.connect()
        # 查询 Teradata 当前时间和时区偏移
        sql = "SELECT CURRENT_TIME, CURRENT_TIMESTAMP"
        rows = td_reader.execute_query(sql)
        if rows:
            td_current_time = str(rows[0][0])
            td_current_ts = str(rows[0][1])
            # 从时间字符串中提取时区信息
            td_tz = td_current_time
        else:
            td_tz = "unknown"

        # 查询 Teradata 会话时区设置
        td_session_tz = td_tz
        try:
            sql2 = "SELECT SessionTimezone FROM DBC.SessionInfoV WHERE SessionNo = SESSION"
            rows2 = td_reader.execute_query(sql2)
            if rows2:
                td_session_tz = str(rows2[0][0])
        except Exception:
            pass

        # 尝试获取时区偏移小时数
        td_tz_offset = 0
        try:
            sql3 = "SELECT CAST(((CURRENT_TIME - CAST('00:00:00' AS TIME)) HOUR) AS INTEGER)"
            rows3 = td_reader.execute_query(sql3)
            if rows3 and rows3[0][0] is not None:
                td_tz_offset = int(rows3[0][0])
        except Exception:
            try:
                # 备选方案：通过当前时间差推算
                sql4 = "SELECT EXTRACT(HOUR FROM CURRENT_TIME)"
                rows4 = td_reader.execute_query(sql4)
                td_tz_offset = 0  # 无法精确获取偏移，设为0
            except Exception:
                td_tz_offset = 0

        td_tz_str = f"UTC{'+%d' % td_tz_offset if td_tz_offset >= 0 else '%d' % td_tz_offset}"

        results.append(CheckResult(
            'Teradata 时区', 'pass',
            f'当前时间: {td_current_time}, 会话时区: {td_session_tz}, 估算偏移: {td_tz_str}',
            {'timezone': td_tz_str, 'offset_hours': td_tz_offset, 'session_tz': td_session_tz,
             'current_time': td_current_time}
        ))
    except Exception as e:
        results.append(CheckResult(
            'Teradata 时区', 'warn',
            f'查询时区失败: {e}',
        ))
        td_reader.disconnect()
        return results

    td_reader.disconnect()

    # DWS 时区查询
    dws_tz = None
    if psycopg2:
        dws_section = dws_config.get('dws', {})
        try:
            conn = psycopg2.connect(
                host=dws_section.get('host', ''),
                port=int(dws_section.get('port', '8000')),
                dbname=dws_section.get('database', ''),
                user=dws_section.get('user', dws_section.get('username', '')),
                password=dws_section.get('password', ''),
                connect_timeout=10
            )
            cursor = conn.cursor()
            cursor.execute("SHOW timezone")
            dws_tz = cursor.fetchone()[0]

            cursor.execute("SELECT EXTRACT(EPOCH FROM now()) - EXTRACT(EPOCH FROM now() AT TIME ZONE 'UTC')")
            dws_offset_sec = cursor.fetchone()[0]
            dws_offset_hour = int(dws_offset_sec / 3600) if dws_offset_sec else 0

            results.append(CheckResult(
                'DWS 时区', 'pass',
                f'时区设置: {dws_tz}, UTC偏移: {dws_offset_hour}h',
                {'timezone': dws_tz, 'offset_hours': dws_offset_hour}
            ))

            cursor.close()
            conn.close()
        except Exception as e:
            results.append(CheckResult(
                'DWS 时区', 'warn',
                f'查询时区失败: {e}',
            ))
    else:
        results.append(CheckResult(
            'DWS 时区', 'fail',
            'psycopg2 未安装',
        ))

    # 时区一致性评估
    if td_tz and dws_tz:
        td_offset = td_tz_offset or 0
        dws_offset_val = dws_offset_hour if 'dws_offset_hour' in dir() else 0

        if td_offset == dws_offset_val:
            results.append(CheckResult(
                '时区一致性', 'pass',
                f'两端时区偏移一致 (UTC{td_offset}h)，TIMESTAMP 数据迁移无时区转换风险',
                {'td_offset': td_offset, 'dws_offset': dws_offset_val, 'consistent': True}
            ))
        else:
            diff = dws_offset_val - td_offset
            results.append(CheckResult(
                '时区一致性', 'warn',
                f'两端时区偏移不一致: TD=UTC{td_offset}h, DWS=UTC{dws_offset_val}h, 差异={diff}h',
                {'td_offset': td_offset, 'dws_offset': dws_offset_val, 'diff': diff, 'consistent': False},
                warning=f'TIMESTAMP 类型数据迁移时需注意 {diff}h 时差。'
                        f'建议: 1) 迁移前在DWS设置相同时区; 2) 或在迁移脚本中对TIMESTAMP做时区转换; '
                        f'3) 使用TIMESTAMP WITH TIME ZONE类型避免隐式转换'
            ))

    return results


# ============================================================
# 2. 字符串长度确认
# ============================================================
def check_string_length(td_reader: TeradataReader, dws_config: dict,
                        schemas: List[str]) -> List[CheckResult]:
    """确认两端字符串列长度一致"""
    results = []
    logger.info("检查字符串长度一致性...")

    td_reader.connect()

    # 收集 Teradata 端所有字符串列信息
    td_string_cols = {}  # {schema.table.col: length}
    for schema in schemas:
        try:
            tables = td_reader.list_tables(schema)
            table_list = [t for t, k in tables if k.strip() == 'T']

            for table_name in table_list:
                try:
                    cols = td_reader.get_table_columns(table_name, schema)
                    for col in cols:
                        col_type = col.get('type', '')
                        if 'CHAR' in col_type or 'VARCHAR' in col_type:
                            key = f"{schema}.{table_name}.{col['name']}"
                            td_string_cols[key] = {
                                'type': col_type,
                                'length': col.get('length', 0),
                                'schema': schema,
                                'table': table_name,
                                'column': col['name'],
                            }
                except Exception as e:
                    logger.debug(f"获取 {schema}.{table_name} 列信息失败: {e}")
        except Exception as e:
            logger.warning(f"列出 {schema} 表失败: {e}")

    td_reader.disconnect()

    results.append(CheckResult(
        'Teradata 字符串列统计', 'pass',
        f'共 {len(td_string_cols)} 个字符串列 (CHAR/VARCHAR)',
        {'count': len(td_string_cols)}
    ))

    # 收集 DWS 端字符串列信息
    dws_string_cols = {}
    if psycopg2:
        dws_section = dws_config.get('dws', {})
        try:
            conn = psycopg2.connect(
                host=dws_section.get('host', ''),
                port=int(dws_section.get('port', '8000')),
                dbname=dws_section.get('database', ''),
                user=dws_section.get('user', dws_section.get('username', '')),
                password=dws_section.get('password', ''),
                connect_timeout=10
            )
            cursor = conn.cursor()

            for schema in schemas:
                cursor.execute("""
                    SELECT table_name, column_name, data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND data_type IN ('character', 'character varying', 'text')
                    ORDER BY table_name, ordinal_position
                """, (schema,))
                rows = cursor.fetchall()
                for row in rows:
                    key = f"{schema}.{row[0]}.{row[1]}"
                    dws_string_cols[key] = {
                        'type': row[2],
                        'length': row[3],
                        'schema': schema,
                        'table': row[0],
                        'column': row[1],
                    }

            results.append(CheckResult(
                'DWS 字符串列统计', 'pass',
                f'共 {len(dws_string_cols)} 个字符串列',
                {'count': len(dws_string_cols)}
            ))
            cursor.close()
            conn.close()
        except Exception as e:
            results.append(CheckResult(
                'DWS 字符串列统计', 'warn',
                f'查询DWS字符串列失败: {e}',
            ))
    else:
        results.append(CheckResult(
            'DWS 字符串列统计', 'fail',
            'psycopg2 未安装',
        ))

    # 比较两端字符串长度
    mismatches = []
    matches = 0
    td_only = []

    for key, td_info in td_string_cols.items():
        if key in dws_string_cols:
            dws_info = dws_string_cols[key]
            td_len = td_info.get('length', 0) or 0
            dws_len = dws_info.get('length', 0) or 0

            if td_len != dws_len:
                mismatches.append({
                    'column': key,
                    'td_type': td_info['type'],
                    'td_length': td_len,
                    'dws_type': dws_info['type'],
                    'dws_length': dws_len,
                })
            else:
                matches += 1
        else:
            td_only.append(key)

    if not mismatches:
        results.append(CheckResult(
            '字符串长度一致性', 'pass',
            f'已比对 {matches} 个字符串列，长度全部一致',
            {'matched': matches, 'mismatches': 0, 'td_only': len(td_only)}
        ))
    else:
        mismatch_detail = "; ".join(
            f"{m['column']}: TD={m['td_length']} vs DWS={m['dws_length']}"
            for m in mismatches[:10]
        )
        results.append(CheckResult(
            '字符串长度一致性', 'warn',
            f'比对 {matches + len(mismatches)} 列: {matches} 一致, {len(mismatches)} 不一致. '
            f'示例: {mismatch_detail}',
            {'matched': matches, 'mismatches': len(mismatches),
             'mismatch_details': mismatches, 'td_only': len(td_only)},
            warning=f'发现 {len(mismatches)} 个字符串列长度不一致。'
                    f'Teradata CHAR(n) 按 bytes 计，DWS 按 chars 计（UTF8 多字节字符可能不同）。'
                    f'建议: 1) DWS VARCHAR 长度设为 TD 长度 × 3(UTF8安全); '
                    f'2) 或确认两端字符集一致后保持相同长度'
        ))

    return results


# ============================================================
# 3. 大小敏感性检查
# ============================================================
def check_case_sensitivity(td_reader: TeradataReader, dws_config: dict,
                           schemas: List[str]) -> List[CheckResult]:
    """检查两端库表名大小写敏感性"""
    results = []
    logger.info("检查大小写敏感性...")

    # Teradata 默认不区分大小写（session mode = Teradata）
    td_reader.connect()

    td_case_mode = None
    try:
        # 查询 Teradata 的事务模式
        sql = "SELECT SessionMode FROM DBC.SessionInfoV WHERE SessionNo = SESSION"
        rows = td_reader.execute_query(sql)
        if rows:
            td_case_mode = str(rows[0][0]).strip()
    except Exception:
        try:
            sql2 = "HELP SESSION"
            rows2 = td_reader.execute_query(sql2)
            td_case_mode = "Teradata (默认不区分大小写)"
        except Exception:
            td_case_mode = "未知"

    # Teradata 对象名检查 — 看是否有混合大小写的对象名
    td_mixed_case_objects = []
    for schema in schemas:
        try:
            tables = td_reader.list_tables(schema)
            for t_name, t_kind in tables:
                if t_name != t_name.upper() and t_name != t_name.lower():
                    td_mixed_case_objects.append(f"{schema}.{t_name}({t_kind.strip()})")
        except Exception:
            pass

    results.append(CheckResult(
        'Teradata 大小写敏感性', 'pass',
        f'会话模式: {td_case_mode}, 混合大小写对象: {len(td_mixed_case_objects)} 个',
        {'mode': td_case_mode, 'mixed_case_objects': td_mixed_case_objects[:20]},
        warning=f'Teradata 默认不区分对象名大小写。发现 {len(td_mixed_case_objects)} 个混合大小写对象名。'
                if td_mixed_case_objects else None
    ))

    td_reader.disconnect()

    # DWS 大小写敏感性检查
    dws_case_info = {}
    if psycopg2:
        dws_section = dws_config.get('dws', {})
        try:
            conn = psycopg2.connect(
                host=dws_section.get('host', ''),
                port=int(dws_section.get('port', '8000')),
                dbname=dws_section.get('database', ''),
                user=dws_section.get('user', dws_section.get('username', '')),
                password=dws_section.get('password', ''),
                connect_timeout=10
            )
            cursor = conn.cursor()

            # DWS/GaussDB 默认区分大小写
            # 尝试查询大小写敏感设置
            dws_case_sensitive = "on (默认区分大小写)"
            try:
                cursor.execute("SHOW enable_case_sensitive")
                dws_case_sensitive = cursor.fetchone()[0]
            except Exception:
                try:
                    conn.rollback()
                    cursor.execute("SELECT setting FROM pg_settings WHERE name = 'enable_case_sensitive'")
                    row_cs = cursor.fetchone()
                    if row_cs:
                        dws_case_sensitive = row_cs[0]
                except Exception:
                    conn.rollback()
                    pass  # 保持默认值

            dws_case_info['case_sensitive'] = str(dws_case_sensitive)

            # 检查 DWS 中对应 schema 的对象名
            dws_mixed_case = []
            for schema in schemas:
                cursor.execute("""
                    SELECT tablename FROM pg_tables WHERE schemaname = %s
                """, (schema,))
                for row in cursor.fetchall():
                    t_name = row[0]
                    if t_name != t_name.upper() and t_name != t_name.lower():
                        dws_mixed_case.append(f"{schema}.{t_name}")

            dws_case_info['mixed_case_objects'] = dws_mixed_case[:20]

            results.append(CheckResult(
                'DWS 大小写敏感性', 'pass',
                f'大小写敏感: {dws_case_sensitive}, 混合大小写对象: {len(dws_mixed_case)} 个',
                dws_case_info
            ))

            cursor.close()
            conn.close()
        except Exception as e:
            results.append(CheckResult(
                'DWS 大小写敏感性', 'warn',
                f'查询大小写设置失败: {e}',
            ))
    else:
        results.append(CheckResult(
            'DWS 大小写敏感性', 'fail',
            'psycopg2 未安装',
        ))

    # 大小写敏感性差异评估
    td_case_insensitive = True  # Teradata 默认不区分大小写
    dws_case_str = str(dws_case_info.get('case_sensitive', '')).lower()
    dws_case_insensitive = 'off' in dws_case_str

    if td_case_insensitive and not dws_case_insensitive:
        results.append(CheckResult(
            '大小写敏感性差异', 'warn',
            'Teradata 不区分大小写, DWS 区分大小写 — 存在差异',
            {'td_case_insensitive': True, 'dws_case_insensitive': False},
            warning='Teradata 对象名不区分大小写，DWS 默认区分大小写。'
                    '建议: 1) 迁移时统一使用小写对象名; '
                    '2) 或在 DWS 设置 enable_case_sensitive=off; '
                    '3) 对混合大小写对象名使用双引号引用'
        ))
    elif td_case_insensitive and dws_case_insensitive:
        results.append(CheckResult(
            '大小写敏感性差异', 'pass',
            '两端均不区分大小写 — 一致',
            {'td_case_insensitive': True, 'dws_case_insensitive': True}
        ))
    else:
        results.append(CheckResult(
            '大小写敏感性差异', 'pass',
            '两端大小写设置兼容',
            {'td_case_insensitive': td_case_insensitive, 'dws_case_insensitive': dws_case_insensitive}
        ))

    return results


# ============================================================
# 网络连通性检查
# ============================================================
def check_tcp_connectivity(host: str, port: int, timeout: int = 10) -> Tuple[bool, float]:
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        latency_ms = (time.time() - start) * 1000
        return True, latency_ms
    except Exception:
        return False, 0


def check_network(td_host: str, td_port: int, dws_host: str, dws_port: int) -> List[CheckResult]:
    results = []
    td_ok, td_latency = check_tcp_connectivity(td_host, td_port)
    if td_ok:
        results.append(CheckResult('Teradata 网络连通性', 'pass',
            f'{td_host}:{td_port} 可连接, 延迟 {td_latency:.1f}ms'))
    else:
        results.append(CheckResult('Teradata 网络连通性', 'fail',
            f'{td_host}:{td_port} 无法连接'))

    dws_ok, dws_latency = check_tcp_connectivity(dws_host, dws_port)
    if dws_ok:
        results.append(CheckResult('DWS 网络连通性', 'pass',
            f'{dws_host}:{dws_port} 可连接, 延迟 {dws_latency:.1f}ms'))
    else:
        results.append(CheckResult('DWS 网络连通性', 'fail',
            f'{dws_host}:{dws_port} 无法连接'))

    return results


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='增强预检脚本')
    parser.add_argument('--td-config', required=True)
    parser.add_argument('--dws-config', required=True)
    parser.add_argument('--schemas', required=True, help='逗号分隔的 schema 列表')
    parser.add_argument('--output-dir', default='./output')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    schemas = [s.strip() for s in args.schemas.split(',')]

    td_config = load_config(args.td_config)
    dws_config = load_config(args.dws_config)

    td_section = td_config.get('teradata', {})
    dws_section = dws_config.get('dws', {})

    td_host = td_section.get('host', '')
    td_port = int(td_section.get('port', '1025'))
    dws_host = dws_section.get('host', '')
    dws_port = int(dws_section.get('port', '8000'))

    print("\n" + "=" * 70)
    print("  增强预检：网络 + 时区 + 字符串长度 + 大小敏感性")
    print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Schemas: {', '.join(schemas)}")
    print("=" * 70)

    all_results = []

    # 1. 网络连通性
    print("\n  ── 网络连通性检查 ──")
    net_results = check_network(td_host, td_port, dws_host, dws_port)
    all_results.extend(net_results)
    for r in net_results:
        print(r)

    net_fail = any(r.status == 'fail' for r in net_results)
    if net_fail:
        print("\n  ❌ 网络不通，无法继续！")
        sys.exit(1)

    # 创建 Teradata reader
    td_reader = TeradataReader(
        host=td_host,
        user=td_section.get('user', td_section.get('username', '')),
        password=td_section.get('password', ''),
        database=td_section.get('database', ''),
        port=td_port,
        logmech=td_section.get('logmech', 'TD2'),
    )

    # 2. 时区评估
    print("\n  ── 时区评估 ──")
    tz_results = check_timezone(td_reader, dws_config)
    all_results.extend(tz_results)
    for r in tz_results:
        print(r)

    # 3. 字符串长度确认
    print("\n  ── 字符串长度确认 ──")
    str_results = check_string_length(td_reader, dws_config, schemas)
    all_results.extend(str_results)
    for r in str_results:
        print(r)

    # 4. 大小敏感性检查
    print("\n  ── 大小敏感性检查 ──")
    case_results = check_case_sensitivity(td_reader, dws_config, schemas)
    all_results.extend(case_results)
    for r in case_results:
        print(r)

    # 汇总
    pass_count = sum(1 for r in all_results if r.status == 'pass')
    warn_count = sum(1 for r in all_results if r.status == 'warn')
    fail_count = sum(1 for r in all_results if r.status == 'fail')

    print("\n" + "=" * 70)
    print(f"  汇总: ✅ 通过 {pass_count}  ⚠️  警告 {warn_count}  ❌ 失败 {fail_count}")
    if fail_count > 0:
        print("  ❌ 存在失败项，请修复后再迁移！")
    elif warn_count > 0:
        print("  ⚠️  存在警告项，请确认后再迁移")
    else:
        print("  ✅ 所有检查通过，可以执行迁移")
    print("=" * 70)

    # 保存 JSON 报告
    report_data = {
        'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'schemas': schemas,
        'summary': {'pass': pass_count, 'warn': warn_count, 'fail': fail_count},
        'results': [r.to_dict() for r in all_results],
    }
    report_file = os.path.join(args.output_dir, 'enhanced_pre_check.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  报告已保存: {report_file}")

    return fail_count == 0


if __name__ == '__main__':
    main()
