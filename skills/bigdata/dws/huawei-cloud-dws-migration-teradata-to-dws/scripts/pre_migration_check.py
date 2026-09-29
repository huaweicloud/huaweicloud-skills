#!/usr/bin/env python3
"""
迁移前预检脚本 (Step 0)

在正式迁移前对源端 Teradata 和目标端 DWS 进行全面检查：
  1. 连通性检查 — 确认源端/目标端可连接
  2. 性能检查 — 源端负载、目标端集群状态
  3. 资源检查 — 磁盘空间、连接数、AMP/CPU 使用率
  4. 业务影响评估 — 评估迁移对源端业务的影响，给出建议
  5. 迁移可行性预判 — 表数量、数据量、预估时间

使用方法:
    python3 pre_migration_check.py \
        --td-config config/teradata_config.ini \
        --dws-config config/dws_config.ini \
        --schema <schema_name>

核心规则:
    1. 所有对源端 Teradata 的查询均为只读
    2. 不修改任何源端或目标端数据
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

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from teradata_reader import TeradataReader, WriteOperationError

try:
    import psycopg2
except ImportError:
    psycopg2 = None


# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('pre_check')


def load_config(config_path: str) -> dict:
    """加载 INI 配置文件"""
    parser = configparser.ConfigParser()
    parser.read(config_path)
    config = {}
    for section in parser.sections():
        config[section] = dict(parser[section])
    return config


# ============================================================
# 进度条工具
# ============================================================
class ProgressBar:
    """简单的文本进度条"""

    def __init__(self, total: int, desc: str = '', width: int = 40):
        self.total = total
        self.desc = desc
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, current: int, extra: str = ''):
        self.current = current
        elapsed = time.time() - self.start_time
        if current > 0 and elapsed > 0:
            speed = current / elapsed
            remaining = (self.total - current) / speed
        else:
            speed = 0
            remaining = 0

        pct = current / self.total * 100 if self.total > 0 else 0
        filled = int(self.width * current / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (self.width - filled)

        line = f"\r  {self.desc} |{bar}| {current}/{self.total} ({pct:.1f}%)"
        if speed > 0:
            line += f" 速度:{speed:.1f}/s 剩余:{remaining:.0f}s"
        if extra:
            line += f" {extra}"
        sys.stdout.write(line)
        sys.stdout.flush()

    def finish(self):
        elapsed = time.time() - self.start_time
        sys.stdout.write(f"  耗时:{elapsed:.1f}s\n")
        sys.stdout.flush()


# ============================================================
# 检查结果类
# ============================================================
class CheckResult:
    """单项检查结果"""

    def __init__(self, name: str, status: str, detail: str,
                 data: dict = None, warning: str = None):
        self.name = name
        self.status = status  # 'pass', 'fail', 'warn'
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
            'name': self.name,
            'status': self.status,
            'detail': self.detail,
            'data': self.data,
            'warning': self.warning,
        }


# ============================================================
# 网络连通性检查
# ============================================================
def check_tcp_connectivity(host: str, port: int, timeout: int = 10) -> Tuple[bool, float]:
    """
    检查 TCP 端口连通性，返回 (是否成功, 延迟毫秒)
    """
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


def check_network(td_host: str, td_port: int,
                  dws_host: str, dws_port: int) -> List[CheckResult]:
    """网络连通性检查"""
    results = []

    # 检查 Teradata 连通性
    logger.info("检查网络连通性...")
    td_ok, td_latency = check_tcp_connectivity(td_host, td_port)
    if td_ok:
        results.append(CheckResult(
            'Teradata 网络连通性', 'pass',
            f'{td_host}:{td_port} 可连接, 延迟 {td_latency:.1f}ms',
            {'latency_ms': round(td_latency, 1)}
        ))
    else:
        results.append(CheckResult(
            'Teradata 网络连通性', 'fail',
            f'{td_host}:{td_port} 无法连接',
        ))

    # 检查 DWS 连通性
    dws_ok, dws_latency = check_tcp_connectivity(dws_host, dws_port)
    if dws_ok:
        results.append(CheckResult(
            'DWS 网络连通性', 'pass',
            f'{dws_host}:{dws_port} 可连接, 延迟 {dws_latency:.1f}ms',
            {'latency_ms': round(dws_latency, 1)}
        ))
    else:
        results.append(CheckResult(
            'DWS 网络连通性', 'fail',
            f'{dws_host}:{dws_port} 无法连接',
        ))

    # 延迟评估
    if td_ok and dws_ok:
        max_latency = max(td_latency, dws_latency)
        if max_latency > 500:
            results.append(CheckResult(
                '网络延迟评估', 'warn',
                f'最大延迟 {max_latency:.1f}ms，可能影响迁移速度',
                warning='建议在同一 VPC 或使用内网地址进行迁移'
            ))
        elif max_latency > 200:
            results.append(CheckResult(
                '网络延迟评估', 'warn',
                f'最大延迟 {max_latency:.1f}ms，延迟偏高',
            ))
        else:
            results.append(CheckResult(
                '网络延迟评估', 'pass',
                f'最大延迟 {max_latency:.1f}ms，网络状况良好',
            ))

    return results


# ============================================================
# Teradata 源端检查
# ============================================================
def check_teradata(td_reader: TeradataReader, database: str) -> List[CheckResult]:
    """Teradata 源端全面检查"""
    results = []

    # 1. 连接测试
    logger.info("检查 Teradata 源端...")
    try:
        td_reader.connect()
        results.append(CheckResult(
            'Teradata 连接', 'pass',
            f'成功连接到 {td_reader.host}:{td_reader.port}',
        ))
    except Exception as e:
        results.append(CheckResult(
            'Teradata 连接', 'fail',
            f'连接失败: {e}',
        ))
        return results

    # 2. 数据库存在性检查
    try:
        dbs = td_reader.list_databases()
        if database in dbs:
            results.append(CheckResult(
                '数据库存在性', 'pass',
                f'数据库 {database} 存在',
                {'total_databases': len(dbs)}
            ))
        else:
            results.append(CheckResult(
                '数据库存在性', 'fail',
                f'数据库 {database} 不存在',
                warning=f'可用数据库: {", ".join(dbs[:10])}...'
            ))
            return results
    except Exception as e:
        results.append(CheckResult(
            '数据库存在性', 'fail',
            f'查询失败: {e}',
        ))
        return results

    # 3. 表列表和数量
    try:
        tables = td_reader.list_tables(database)
        table_list = [(t, k) for t, k in tables if k.strip() == 'T']
        view_list = [(t, k) for t, k in tables if k.strip() == 'V']

        results.append(CheckResult(
            '表对象统计', 'pass',
            f'表 {len(table_list)} 个, 视图 {len(view_list)} 个',
            {'tables': len(table_list), 'views': len(view_list),
             'table_names': [t for t, _ in table_list]}
        ))
    except Exception as e:
        results.append(CheckResult(
            '表对象统计', 'fail',
            f'查询失败: {e}',
        ))
        table_list = []

    # 4. 活跃会话数检查（评估源端负载）
    try:
        # 查询当前活跃会话数
        sql = """
            SELECT COUNT(*) AS ActiveSessions
            FROM DBC.SessionInfoV
            WHERE SessionNo IS NOT NULL
        """
        active_sessions = td_reader.execute_query(sql)
        session_count = active_sessions[0][0] if active_sessions else 0

        if session_count > 50:
            results.append(CheckResult(
                '源端活跃会话数', 'warn',
                f'当前活跃会话 {session_count} 个，负载较高',
                {'active_sessions': session_count},
                warning='迁移可能影响源端业务性能，建议在业务低峰期执行'
            ))
        elif session_count > 20:
            results.append(CheckResult(
                '源端活跃会话数', 'warn',
                f'当前活跃会话 {session_count} 个，负载中等',
                {'active_sessions': session_count},
            ))
        else:
            results.append(CheckResult(
                '源端活跃会话数', 'pass',
                f'当前活跃会话 {session_count} 个，负载较低',
                {'active_sessions': session_count},
            ))
    except Exception as e:
        results.append(CheckResult(
            '源端活跃会话数', 'warn',
            f'无法查询会话信息: {e}',
        ))

    # 5. AMP 使用情况检查
    try:
        # 查询 AMP 状态
        sql = """
            SELECT
                COUNT(*) AS TotalAMPs,
                SUM(CASE WHEN VprocType = 'AM' THEN 1 ELSE 0 END) AS ActiveAMPs
            FROM DBC.HostInfoV
        """
        amp_info = td_reader.execute_query(sql)
        if amp_info:
            total_amps = amp_info[0][0] or 0
            active_amps = amp_info[0][1] or 0
            results.append(CheckResult(
                'AMP 节点状态', 'pass',
                f'总 AMP {total_amps} 个, 活跃 {active_amps} 个',
                {'total_amps': total_amps, 'active_amps': active_amps}
            ))
    except Exception as e:
        results.append(CheckResult(
            'AMP 节点状态', 'warn',
            f'无法查询 AMP 信息: {e}',
        ))

    # 6. 表数据量预估
    try:
        table_sizes = []
        total_rows = 0
        pb = ProgressBar(len(table_list), '源端表数据量统计')
        for i, (table_name, _) in enumerate(table_list):
            try:
                row_count = td_reader.get_table_row_count(table_name, database)
                table_sizes.append({'table': table_name, 'rows': row_count})
                total_rows += row_count
            except Exception:
                table_sizes.append({'table': table_name, 'rows': -1})
            pb.update(i + 1, f"当前表: {table_name[:20]}")
        pb.finish()

        # 估算数据量 (假设平均每行 200 字节)
        est_size_mb = total_rows * 200 / 1024 / 1024

        results.append(CheckResult(
            '源端数据量预估', 'pass',
            f'总行数 {total_rows:,}, 预估 {est_size_mb:.1f} MB',
            {'total_rows': total_rows, 'est_size_mb': round(est_size_mb, 1),
             'table_sizes': table_sizes}
        ))
    except Exception as e:
        results.append(CheckResult(
            '源端数据量预估', 'warn',
            f'统计数据量失败: {e}',
        ))

    # 7. 当前正在运行的查询数
    try:
        sql = """
            SELECT COUNT(*) AS RunningQueries
            FROM DBC.QryLogV
            WHERE StartTime IS NOT NULL
              AND FinishTime IS NULL
        """
        running = td_reader.execute_query(sql)
        running_count = running[0][0] if running else 0

        if running_count > 10:
            results.append(CheckResult(
                '源端运行中查询', 'warn',
                f'当前有 {running_count} 个查询正在运行',
                {'running_queries': running_count},
                warning='源端查询负载较高，迁移可能需要等待资源'
            ))
        else:
            results.append(CheckResult(
                '源端运行中查询', 'pass',
                f'当前有 {running_count} 个查询正在运行',
                {'running_queries': running_count},
            ))
    except Exception as e:
        results.append(CheckResult(
            '源端运行中查询', 'warn',
            f'无法查询运行状态: {e}',
        ))

    td_reader.disconnect()
    return results


# ============================================================
# DWS 目标端检查
# ============================================================
def check_dws(dws_config: dict, schema: str) -> List[CheckResult]:
    """DWS 目标端全面检查"""
    results = []

    if psycopg2 is None:
        results.append(CheckResult(
            'DWS 依赖', 'fail',
            'psycopg2 未安装，无法检查 DWS',
        ))
        return results

    dws_section = dws_config.get('dws', {})
    host = dws_section.get('host', '')
    port = int(dws_section.get('port', '8000'))
    database = dws_section.get('database', '')
    user = dws_section.get('user', dws_section.get('username', ''))
    password = dws_section.get('password', '')

    # 1. 连接测试
    logger.info("检查 DWS 目标端...")
    conn = None
    try:
        conn_kwargs = {
            'host': host, 'port': port, 'dbname': database,
            'user': user, 'connect_timeout': 10,
        }
        if password:
            conn_kwargs['password'] = password
        conn = psycopg2.connect(**conn_kwargs)
        results.append(CheckResult(
            'DWS 连接', 'pass',
            f'成功连接到 {host}:{port}/{database}',
        ))
    except Exception as e:
        results.append(CheckResult(
            'DWS 连接', 'fail',
            f'连接失败: {e}',
        ))
        return results

    cursor = conn.cursor()

    # 2. 集群版本和状态
    try:
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        results.append(CheckResult(
            'DWS 集群版本', 'pass',
            f'{version[:60]}',
            {'version': version}
        ))
    except Exception as e:
        results.append(CheckResult(
            'DWS 集群版本', 'warn',
            f'查询版本失败: {e}',
        ))

    # 3. 当前连接数和最大连接数
    try:
        cursor.execute("SELECT count(*) FROM pg_stat_activity")
        current_conns = cursor.fetchone()[0]

        cursor.execute("SHOW max_connections")
        max_conns = int(cursor.fetchone()[0])

        conn_pct = current_conns / max_conns * 100 if max_conns > 0 else 0
        if conn_pct > 80:
            results.append(CheckResult(
                'DWS 连接数', 'warn',
                f'当前 {current_conns}/{max_conns} 连接 ({conn_pct:.0f}%)，接近上限',
                {'current': current_conns, 'max': max_conns},
                warning='连接数过高，迁移可能因连接不足而失败'
            ))
        else:
            results.append(CheckResult(
                'DWS 连接数', 'pass',
                f'当前 {current_conns}/{max_conns} 连接 ({conn_pct:.0f}%)',
                {'current': current_conns, 'max': max_conns}
            ))
    except Exception as e:
        results.append(CheckResult(
            'DWS 连接数', 'warn',
            f'查询连接数失败: {e}',
        ))

    # 4. 磁盘空间检查
    try:
        cursor.execute("""
            SELECT
                schemaname,
                pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))) as total_size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            GROUP BY schemaname
            ORDER BY sum(pg_total_relation_size(schemaname||'.'||tablename)) DESC
            LIMIT 5
        """)
        top_schemas = cursor.fetchall()

        # 查询总磁盘使用
        cursor.execute("""
            SELECT
                pg_size_pretty(pg_database_size(current_database())) as db_size
        """)
        db_size = cursor.fetchone()[0]

        results.append(CheckResult(
            'DWS 存储空间', 'pass',
            f'数据库总大小: {db_size}',
            {'db_size': db_size, 'top_schemas': [list(r) for r in top_schemas]}
        ))
    except Exception as e:
        results.append(CheckResult(
            'DWS 存储空间', 'warn',
            f'查询存储空间失败: {e}',
        ))

    # 5. Schema 存在性检查
    try:
        cursor.execute(
            "SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,)
        )
        schema_exists = cursor.fetchone() is not None

        if schema_exists:
            # 检查 schema 下已有表
            cursor.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = %s ORDER BY tablename",
                (schema,)
            )
            existing_tables = [r[0] for r in cursor.fetchall()]

            if existing_tables:
                results.append(CheckResult(
                    'DWS Schema 检查', 'warn',
                    f'Schema {schema} 已存在，含 {len(existing_tables)} 个表',
                    {'schema': schema, 'existing_tables': existing_tables},
                    warning='目标 schema 已有表，迁移时将先 DROP 再 CREATE，请确认无重要数据'
                ))
            else:
                results.append(CheckResult(
                    'DWS Schema 检查', 'pass',
                    f'Schema {schema} 已存在，无表',
                    {'schema': schema}
                ))
        else:
            results.append(CheckResult(
                'DWS Schema 检查', 'pass',
                f'Schema {schema} 不存在，将在迁移时创建',
                {'schema': schema}
            ))
    except Exception as e:
        results.append(CheckResult(
            'DWS Schema 检查', 'warn',
            f'查询 schema 失败: {e}',
        ))

    # 6. 集群节点状态
    try:
        cursor.execute("""
            SELECT node_name, node_status
            FROM pg_node_env
            LIMIT 20
        """)
        nodes = cursor.fetchall()
        active_nodes = [n for n in nodes if 'ready' in str(n[1]).lower() or 'ok' in str(n[1]).lower()]

        results.append(CheckResult(
            'DWS 集群节点', 'pass',
            f'总节点 {len(nodes)} 个, 正常 {len(active_nodes)} 个',
            {'total_nodes': len(nodes), 'active_nodes': len(active_nodes)}
        ))
    except Exception as e:
        results.append(CheckResult(
            'DWS 集群节点', 'warn',
            f'查询节点状态失败: {e}',
        ))

    # 7. CPU/内存使用率（通过 pg_stat_activity 估算）
    try:
        cursor.execute("""
            SELECT state, count(*)
            FROM pg_stat_activity
            WHERE state IS NOT NULL
            GROUP BY state
        """)
        states = cursor.fetchall()
        state_info = {s: c for s, c in states}

        active_queries = state_info.get('active', 0)
        if active_queries > 20:
            results.append(CheckResult(
                'DWS 查询负载', 'warn',
                f'活跃查询 {active_queries} 个，负载较高',
                {'states': state_info},
            ))
        else:
            results.append(CheckResult(
                'DWS 查询负载', 'pass',
                f'活跃查询 {active_queries} 个，负载正常',
                {'states': state_info},
            ))
    except Exception as e:
        results.append(CheckResult(
            'DWS 查询负载', 'warn',
            f'查询负载状态失败: {e}',
        ))

    cursor.close()
    conn.close()
    return results


# ============================================================
# 业务影响评估
# ============================================================
def assess_impact(td_results: List[CheckResult],
                  dws_results: List[CheckResult]) -> CheckResult:
    """评估迁移对源端业务的影响"""
    warnings = []
    risk_level = '低'

    # 从检查结果中提取关键数据
    for r in td_results:
        if r.name == '源端活跃会话数' and r.data:
            sessions = r.data.get('active_sessions', 0)
            if sessions > 50:
                risk_level = '高'
                warnings.append(f'源端活跃会话 {sessions} 个，迁移期间可能加剧资源竞争')
            elif sessions > 20:
                if risk_level != '高':
                    risk_level = '中'
                warnings.append(f'源端活跃会话 {sessions} 个，建议关注性能影响')

        if r.name == '源端运行中查询' and r.data:
            running = r.data.get('running_queries', 0)
            if running > 10:
                if risk_level != '高':
                    risk_level = '中'
                warnings.append(f'源端有 {running} 个查询在运行，迁移将增加负载')

        if r.name == '源端数据量预估' and r.data:
            total_rows = r.data.get('total_rows', 0)
            est_mb = r.data.get('est_size_mb', 0)
            if est_mb > 5000:
                if risk_level != '高':
                    risk_level = '中'
                warnings.append(f'数据量较大 ({est_mb:.0f} MB)，迁移耗时较长')
            elif est_mb > 500:
                warnings.append(f'数据量中等 ({est_mb:.0f} MB)')

    for r in dws_results:
        if r.name == 'DWS 连接数' and r.data:
            current = r.data.get('current', 0)
            max_c = r.data.get('max', 1)
            if current / max_c > 0.8:
                if risk_level != '高':
                    risk_level = '中'
                warnings.append(f'DWS 连接使用率 {current/max_c*100:.0f}%，可能影响导入性能')

    # 生成建议
    suggestions = []
    if risk_level == '高':
        suggestions.append('🚫 建议暂缓迁移，等待源端负载降低后在业务低峰期执行')
    elif risk_level == '中':
        suggestions.append('⚠️  建议在业务低峰期（如夜间）执行迁移')
    else:
        suggestions.append('✅ 当前条件适合执行迁移')

    suggestions.append('📋 迁移过程中源端仅执行只读 SELECT，不会修改源端数据')
    suggestions.append('🔒 迁移脚本内置安全机制，禁止对源端执行任何写操作')

    detail = f'风险等级: {risk_level}'
    if warnings:
        detail += f'\n     风险点: {"; ".join(warnings)}'
    detail += f'\n     建议: {"; ".join(suggestions)}'

    status = {'低': 'pass', '中': 'warn', '高': 'fail'}[risk_level]

    return CheckResult(
        '业务影响评估', status, detail,
        {'risk_level': risk_level, 'warnings': warnings, 'suggestions': suggestions}
    )


# ============================================================
# 迁移可行性预判
# ============================================================
def estimate_migration(td_results: List[CheckResult],
                       dws_results: List[CheckResult]) -> CheckResult:
    """预估迁移时间和可行性"""
    table_count = 0
    total_rows = 0
    est_mb = 0

    for r in td_results:
        if r.name == '表对象统计' and r.data:
            table_count = r.data.get('tables', 0)
        if r.name == '源端数据量预估' and r.data:
            total_rows = r.data.get('total_rows', 0)
            est_mb = r.data.get('est_size_mb', 0)

    # 预估迁移时间 (基于经验值)
    # CSV 方式: 约 5000 行/秒 (导出+导入)
    # direct 方式: 约 3000 行/秒
    # obs 方式: 约 20000 行/秒 (并行)
    csv_time = total_rows / 5000 if total_rows > 0 else 0
    direct_time = total_rows / 3000 if total_rows > 0 else 0
    obs_time = total_rows / 20000 if total_rows > 0 else 0

    # 加上每表的固定开销 (连接、DDL 等) 约 10 秒
    csv_time += table_count * 10
    direct_time += table_count * 10
    obs_time += table_count * 10

    def fmt_time(s):
        if s < 60:
            return f'{s:.0f}秒'
        elif s < 3600:
            return f'{s/60:.1f}分钟'
        else:
            return f'{s/3600:.1f}小时'

    detail = (
        f'表数量: {table_count}, 总行数: {total_rows:,}, 预估大小: {est_mb:.1f} MB\n'
        f'     预估迁移时间:\n'
        f'       direct 方式: {fmt_time(direct_time)}\n'
        f'       csv    方式: {fmt_time(csv_time)}\n'
        f'       obs    方式: {fmt_time(obs_time)}'
    )

    data = {
        'table_count': table_count,
        'total_rows': total_rows,
        'est_size_mb': est_mb,
        'est_time': {
            'direct_seconds': round(direct_time),
            'csv_seconds': round(csv_time),
            'obs_seconds': round(obs_time),
        }
    }

    return CheckResult('迁移时间预估', 'pass', detail, data)


# ============================================================
# 报告输出
# ============================================================
def print_report(td_results: List[CheckResult],
                 dws_results: List[CheckResult],
                 net_results: List[CheckResult],
                 impact: CheckResult,
                 estimate: CheckResult,
                 output_dir: str,
                 schema: str):
    """打印检查报告并保存 JSON"""
    all_results = net_results + td_results + dws_results + [impact, estimate]

    print()
    print("=" * 70)
    print("  迁移前预检报告")
    print(f"  检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  迁移 Schema: {schema}")
    print("=" * 70)

    # 网络检查
    print("\n  ── 网络连通性检查 ──")
    for r in net_results:
        print(r)

    # 源端检查
    print("\n  ── 源端 Teradata 检查 ──")
    for r in td_results:
        print(r)

    # 目标端检查
    print("\n  ── 目标端 DWS 检查 ──")
    for r in dws_results:
        print(r)

    # 业务影响评估
    print("\n  ── 业务影响评估 ──")
    print(impact)

    # 迁移预估
    print("\n  ── 迁移时间预估 ──")
    print(estimate)

    # 汇总
    pass_count = sum(1 for r in all_results if r.status == 'pass')
    warn_count = sum(1 for r in all_results if r.status == 'warn')
    fail_count = sum(1 for r in all_results if r.status == 'fail')

    print("\n" + "=" * 70)
    print(f"  汇总: ✅ 通过 {pass_count}  ⚠️  警告 {warn_count}  ❌ 失败 {fail_count}")

    if fail_count > 0:
        print("  ❌ 存在检查失败项，请修复后再执行迁移！")
    elif warn_count > 0:
        print("  ⚠️  存在警告项，建议确认后再执行迁移")
    else:
        print("  ✅ 所有检查通过，可以执行迁移")
    print("=" * 70)

    # 保存 JSON 报告
    report_data = {
        'check_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'schema': schema,
        'summary': {
            'pass': pass_count, 'warn': warn_count, 'fail': fail_count
        },
        'results': [r.to_dict() for r in all_results],
    }
    report_file = os.path.join(output_dir, f'{schema}_pre_migration_check.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  报告已保存: {report_file}")

    return fail_count == 0


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='Teradata 到 DWS 迁移前预检脚本'
    )
    parser.add_argument('--td-config', required=True,
                        help='Teradata 连接配置文件路径')
    parser.add_argument('--dws-config', required=True,
                        help='DWS 连接配置文件路径')
    parser.add_argument('--schema', required=True,
                        help='要迁移的 schema/database 名称')
    parser.add_argument('--output-dir', default='./output',
                        help='输出目录（默认: ./output）')
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

    td_host = td_section.get('host', '')
    td_port = int(td_section.get('port', '1025'))
    dws_host = dws_section.get('host', '')
    dws_port = int(dws_section.get('port', '8000'))

    logger.info("=" * 60)
    logger.info("Step 0: 迁移前预检")
    logger.info(f"  源端: Teradata {td_host}:{td_port}")
    logger.info(f"  目标: DWS {dws_host}:{dws_port}")
    logger.info(f"  Schema: {args.schema}")
    logger.info("=" * 60)

    # 1. 网络连通性检查
    print("\n  ── 开始网络连通性检查 ──")
    net_results = check_network(td_host, td_port, dws_host, dws_port)
    for r in net_results:
        print(r)

    # 如果网络不通，直接退出
    net_fail = any(r.status == 'fail' for r in net_results)
    if net_fail:
        print("\n  ❌ 网络连通性检查失败，无法继续预检！")
        sys.exit(1)

    # 2. Teradata 源端检查
    print("\n  ── 开始源端 Teradata 检查 ──")
    td_reader = TeradataReader(
        host=td_host,
        user=td_section.get('user', td_section.get('username', '')),
        password=td_section.get('password', ''),
        database=td_section.get('database', args.schema),
        port=td_port,
        logmech=td_section.get('logmech', 'TD2'),
    )
    td_results = check_teradata(td_reader, args.schema)
    for r in td_results:
        print(r)

    # 3. DWS 目标端检查
    print("\n  ── 开始目标端 DWS 检查 ──")
    dws_results = check_dws(dws_config, args.schema)
    for r in dws_results:
        print(r)

    # 4. 业务影响评估
    print("\n  ── 业务影响评估 ──")
    impact = assess_impact(td_results, dws_results)
    print(impact)

    # 5. 迁移时间预估
    print("\n  ── 迁移时间预估 ──")
    estimate = estimate_migration(td_results, dws_results)
    print(estimate)

    # 6. 输出报告
    all_pass = print_report(
        td_results, dws_results, net_results,
        impact, estimate, args.output_dir, args.schema
    )

    if all_pass:
        logger.info("预检完成，可以执行迁移")
    else:
        logger.warning("预检发现问题，请检查报告后决定是否继续")
        sys.exit(1)


if __name__ == '__main__':
    main()
