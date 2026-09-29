#!/usr/bin/env python3
"""
PPI (Partitioned Primary Index) 分区表转换器

将 Teradata PPI 分区语法转换为 DWS (GaussDB) 分区语法。

支持的 Teradata PPI 模式:
    1. 单级 RANGE_N with EACH INTERVAL '1' DAY   → DWS RANGE 分区 (按天)
    2. 单级 RANGE_N with EACH INTERVAL '1' MONTH  → DWS RANGE 分区 (按月)
    3. RANGE_N with NO RANGE / UNKNOWN            → DWS 默认分区
    4. CASE_N                                     → DWS LIST 分区
    5. 多级 (RANGE_N + CASE_N)                    → DWS 单级 RANGE 分区 (降级)

DWS 分区语法:
    RANGE:  PARTITION BY RANGE (col) ( PARTITION p1 VALUES LESS THAN (val), ... )
    LIST:   PARTITION BY LIST (col) ( PARTITION p1 VALUES (val), ... )
    多级:   DWS 不支持 SUBPARTITION，降级为单级 RANGE 分区，原 CASE_N 信息保留在注释中

使用方法:
    from ppi_converter import convert_ppi_ddl, is_ppi_table

    if is_ppi_table(td_ddl):
        partition_clause = convert_ppi_ddl(td_ddl)
        # 将 partition_clause 附加到 DWS CREATE TABLE 语句
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)


# ============================================================
# PPI 检测
# ============================================================

def is_ppi_table(ddl: str) -> bool:
    """检测 DDL 是否包含 PPI 分区定义"""
    if not ddl:
        return False
    ddl_upper = ddl.upper()
    return 'PARTITION BY' in ddl_upper and (
        'RANGE_N' in ddl_upper or 'CASE_N' in ddl_upper
    )


# ============================================================
# Teradata PPI 语法解析
# ============================================================

def _extract_partition_clause(ddl: str) -> str:
    """从 DDL 中提取 PARTITION BY 子句"""
    # 找到 PARTITION BY 的位置
    match = re.search(r'PARTITION\s+BY\s*', ddl, re.IGNORECASE)
    if not match:
        return ''

    start = match.end()
    # 从 PARTITION BY 后面开始，找到匹配的括号或分号
    rest = ddl[start:]

    # 检查是否是多级分区 (以括号开头)
    rest_stripped = rest.lstrip()
    if rest_stripped.startswith('('):
        # 多级分区，需要找到匹配的括号
        depth = 0
        end_pos = 0
        for i, ch in enumerate(rest_stripped):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break
        return rest_stripped[:end_pos + 1]
    else:
        # 单级分区，找到分号或 NO RANGE/UNKNOWN 结束
        # 处理 RANGE_N(...) 或 CASE_N(...)
        func_match = re.match(
            r'(RANGE_N|CASE_N)\s*\(', rest_stripped, re.IGNORECASE
        )
        if func_match:
            # 找到匹配的括号
            depth = 0
            end_pos = 0
            in_quote = False
            for i, ch in enumerate(rest_stripped):
                if ch == "'":
                    in_quote = not in_quote
                elif not in_quote:
                    if ch == '(':
                        depth += 1
                    elif ch == ')':
                        depth -= 1
                        if depth == 0:
                            end_pos = i
                            break
            return rest_stripped[:end_pos + 1]

    return ''


def _parse_range_n(range_str: str) -> Optional[Dict]:
    """
    解析 RANGE_N 表达式

    格式: RANGE_N(col BETWEEN val1 AND val2 EACH INTERVAL 'n' UNIT [, NO RANGE] [, UNKNOWN])

    返回:
        {
            'column': col,
            'start': val1,
            'end': val2,
            'interval_n': n,
            'interval_unit': UNIT,
            'has_no_range': bool,
            'has_unknown': bool,
        }
    """
    # 提取列名和范围
    pattern = r'RANGE_N\s*\(\s*(\w+)\s+BETWEEN\s+(.+?)\s+AND\s+(.+?)\s+EACH\s+INTERVAL\s+\'(\d+)\'\s+(\w+)'
    match = re.search(pattern, range_str, re.IGNORECASE | re.DOTALL)
    if not match:
        logger.warning(f"无法解析 RANGE_N: {range_str[:100]}")
        return None

    column = match.group(1)
    start_val = match.group(2).strip()
    end_val = match.group(3).strip()
    interval_n = int(match.group(4))
    interval_unit = match.group(5).upper()

    # 检查 NO RANGE 和 UNKNOWN
    has_no_range = bool(re.search(r'NO\s+RANGE', range_str, re.IGNORECASE))
    has_unknown = bool(re.search(r'UNKNOWN', range_str, re.IGNORECASE))

    return {
        'column': column,
        'start': start_val,
        'end': end_val,
        'interval_n': interval_n,
        'interval_unit': interval_unit,
        'has_no_range': has_no_range,
        'has_unknown': has_unknown,
    }


def _parse_case_n(case_str: str) -> Optional[Dict]:
    """
    解析 CASE_N 表达式

    格式: CASE_N(cond1, cond2, ... [, NO CASE] [, NO CASE OR UNKNOWN] [, UNKNOWN])

    返回:
        {
            'column': col,
            'values': [val1, val2, ...],
            'has_no_case': bool,
            'has_unknown': bool,
        }
    """
    # 提取 CASE_N 内容
    match = re.search(r'CASE_N\s*\((.+)\)', case_str, re.IGNORECASE | re.DOTALL)
    if not match:
        logger.warning(f"无法解析 CASE_N: {case_str[:100]}")
        return None

    content = match.group(1)

    # 分割条件（注意逗号在括号内的情况）
    conditions = []
    depth = 0
    current = []
    for ch in content:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            conditions.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        conditions.append(''.join(current).strip())

    # 解析条件，提取 column = value 模式
    column = None
    values = []
    for cond in conditions:
        cond = cond.strip()
        # 跳过 NO CASE, UNKNOWN 等
        if re.match(r'NO\s+CASE', cond, re.IGNORECASE):
            continue
        if re.match(r'UNKNOWN', cond, re.IGNORECASE):
            continue

        # 匹配 column = value
        eq_match = re.match(r'(\w+)\s*=\s*(\S+)', cond, re.IGNORECASE)
        if eq_match:
            if column is None:
                column = eq_match.group(1)
            values.append(eq_match.group(2))

    has_no_case = bool(re.search(r'NO\s+CASE', content, re.IGNORECASE))
    has_unknown = bool(re.search(r'UNKNOWN', content, re.IGNORECASE))

    return {
        'column': column,
        'values': values,
        'has_no_case': has_no_case,
        'has_unknown': has_unknown,
    }


# ============================================================
# DWS 分区语法生成
# ============================================================

def _parse_date(val: str) -> datetime:
    """解析日期值，支持 DATE 'YYYY-MM-DD' 格式"""
    val = val.strip()
    # 去除 DATE 前缀
    val = re.sub(r"^DATE\s*", '', val, flags=re.IGNORECASE)
    # 去除引号
    val = val.strip("'\"")
    return datetime.strptime(val, '%Y-%m-%d')


def _generate_range_partitions(range_info: Dict) -> str:
    """
    根据 RANGE_N 信息生成 DWS RANGE 分区子句

    返回:
        PARTITION BY RANGE ("col") (
            PARTITION p_20250101 VALUES LESS THAN ('2025-01-02'),
            ...
            PARTITION p_default VALUES LESS THAN (MAXVALUE)
        )
    """
    col = range_info['column']
    start_date = _parse_date(range_info['start'])
    end_date = _parse_date(range_info['end'])
    interval_n = range_info['interval_n']
    interval_unit = range_info['interval_unit']

    # 生成分区边界
    partitions = []
    current = start_date

    if interval_unit == 'DAY':
        delta = timedelta(days=interval_n)
    elif interval_unit == 'MONTH':
        delta = timedelta(days=interval_n * 30)  # 近似，后面会精确处理
    else:
        logger.warning(f"不支持的间隔单位: {interval_unit}")
        delta = timedelta(days=interval_n)

    # 生成每个分区的边界
    part_idx = 0
    while current <= end_date:
        if interval_unit == 'MONTH':
            # 精确的月份计算
            next_date = _add_months(current, interval_n)
        else:
            next_date = current + delta

        # 分区名: p_YYYYMMDD
        part_name = f"p_{current.strftime('%Y%m%d')}"
        # 边界值: 下一个日期（LESS THAN）
        boundary = next_date.strftime('%Y-%m-%d')
        partitions.append(f"    PARTITION {part_name} VALUES LESS THAN ('{boundary}')")

        current = next_date
        part_idx += 1

    # 添加默认分区（对应 NO RANGE / UNKNOWN）
    if range_info['has_no_range'] or range_info['has_unknown']:
        partitions.append("    PARTITION p_default VALUES LESS THAN (MAXVALUE)")

    partition_list = ',\n'.join(partitions)
    return f"PARTITION BY RANGE (\"{col}\") (\n{partition_list}\n)"


def _add_months(date: datetime, months: int) -> datetime:
    """精确的月份加法"""
    year = date.year
    month = date.month + months
    while month > 12:
        year += 1
        month -= 12
    while month < 1:
        year -= 1
        month += 12
    # 处理月末日期
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    day = min(date.day, last_day)
    return datetime(year, month, day)



def _sql_literal(v):
    """将分区键值安全转换为 SQL 字面量，防止注入"""
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _generate_list_partitions(case_info: Dict) -> str:
    """
    根据 CASE_N 信息生成 DWS LIST 分区子句

    返回:
        PARTITION BY LIST ("col") (
            PARTITION p_1 VALUES (1),
            PARTITION p_2 VALUES (2),
            PARTITION p_default VALUES (DEFAULT)
        )
    """
    col = case_info['column']
    values = case_info['values']

    partitions = []
    for i, val in enumerate(values, 1):
        partitions.append(f"    PARTITION p{i} VALUES ({_sql_literal(val)})")

    # 添加默认分区
    if case_info['has_no_case'] or case_info['has_unknown']:
        partitions.append("    PARTITION p_default VALUES (DEFAULT)")

    partition_list = ',\n'.join(partitions)
    return f"PARTITION BY LIST (\"{col}\") (\n{partition_list}\n)"


def _generate_multilevel_partitions(range_info: Dict, case_info: Dict) -> str:
    """
    生成多级分区: RANGE + LIST → DWS 单级 RANGE 分区

    DWS 不支持 SUBPARTITION，因此将多级 PPI 降级为单级 RANGE 分区。
    原 Teradata 的 CASE_N 子分区信息保留在注释中。
    """
    range_col = range_info['column']
    list_col = case_info['column']
    list_values = case_info['values']

    # 生成注释说明原 Teradata 子分区信息
    subpart_comment = f"-- Original Teradata subpartition: CASE_N({list_col}) VALUES {list_values}"
    if case_info['has_no_case'] or case_info['has_unknown']:
        subpart_comment += " + NO CASE/UNKNOWN"

    # 生成 RANGE 分区 (单级)
    start_date = _parse_date(range_info['start'])
    end_date = _parse_date(range_info['end'])
    interval_n = range_info['interval_n']
    interval_unit = range_info['interval_unit']

    partitions = []
    current = start_date
    while current <= end_date:
        if interval_unit == 'MONTH':
            next_date = _add_months(current, interval_n)
        else:
            next_date = current + timedelta(days=interval_n)

        part_name = f"p_{current.strftime('%Y%m%d')}"
        boundary = next_date.strftime('%Y-%m-%d')
        partitions.append(f"    PARTITION {part_name} VALUES LESS THAN ('{boundary}')")

        current = next_date

    # 添加默认分区
    if range_info['has_no_range'] or range_info['has_unknown']:
        partitions.append("    PARTITION p_default VALUES LESS THAN (MAXVALUE)")

    partition_list = ',\n'.join(partitions)

    return (
        f"{subpart_comment}\n"
        f"PARTITION BY RANGE (\"{range_col}\")\n"
        f"(\n{partition_list}\n)"
    )


# ============================================================
# 主转换函数
# ============================================================

def convert_ppi_ddl(ddl: str) -> Optional[str]:
    """
    将 Teradata PPI DDL 转换为 DWS 分区子句

    参数:
        ddl: Teradata SHOW TABLE 输出的 DDL

    返回:
        DWS 分区子句字符串，如果不是 PPI 表则返回 None

    示例返回:
        PARTITION BY RANGE ("snapshot_date") (
            PARTITION p_20250101 VALUES LESS THAN ('2025-01-02'),
            ...
        )
    """
    if not is_ppi_table(ddl):
        return None

    partition_clause = _extract_partition_clause(ddl)
    if not partition_clause:
        logger.warning("无法提取 PARTITION BY 子句")
        return None
    clause_upper = partition_clause.upper().lstrip()

    # 判断分区类型
    if clause_upper.startswith('('):
        # 多级分区: (RANGE_N(...), CASE_N(...))
        logger.info("检测到多级 PPI 分区 (RANGE_N + CASE_N)")

        range_match = re.search(r'RANGE_N\s*\(.+?\)', partition_clause,
                                re.IGNORECASE | re.DOTALL)
        case_match = re.search(r'CASE_N\s*\(.+?\)', partition_clause,
                               re.IGNORECASE | re.DOTALL)

        if not range_match or not case_match:
            logger.warning("多级分区解析失败")
            return None

        range_info = _parse_range_n(range_match.group())
        case_info = _parse_case_n(case_match.group())

        if not range_info or not case_info:
            logger.warning("多级分区信息不完整")
            return None

        return _generate_multilevel_partitions(range_info, case_info)

    elif 'RANGE_N' in clause_upper:
        # 单级 RANGE_N 分区
        logger.info("检测到单级 RANGE_N PPI 分区")
        range_info = _parse_range_n(partition_clause)
        if not range_info:
            return None
        return _generate_range_partitions(range_info)

    elif 'CASE_N' in clause_upper:
        # 单级 CASE_N 分区
        logger.info("检测到单级 CASE_N PPI 分区")
        case_info = _parse_case_n(partition_clause)
        if not case_info:
            return None
        return _generate_list_partitions(case_info)

    logger.warning(f"未知的 PPI 分区类型: {partition_clause[:100]}")
    return None


def extract_primary_index(ddl: str) -> Optional[List[str]]:
    """
    从 Teradata DDL 中提取 PRIMARY INDEX 列

    返回:
        列名列表，如果没有 PRIMARY INDEX 则返回 None
    """
    # 匹配 PRIMARY INDEX (col1, col2, ...)
    pattern = r'PRIMARY\s+INDEX\s*\(\s*([^)]+)\s*\)'
    match = re.search(pattern, ddl, re.IGNORECASE)
    if match:
        cols = [c.strip().strip('"') for c in match.group(1).split(',')]
        return cols
    return None


def get_distribute_clause(ddl: str, fallback_strategy: str = 'roundrobin') -> str:
    """
    根据 Teradata DDL 的 PRIMARY INDEX 生成 DWS DISTRIBUTE BY 子句

    参数:
        ddl: Teradata DDL
        fallback_strategy: 没有 PRIMARY INDEX 时的策略

    返回:
        DISTRIBUTE BY 子句
    """
    pk_cols = extract_primary_index(ddl)
    if pk_cols:
        col_list = ', '.join(f'"{c}"' for c in pk_cols)
        return f'DISTRIBUTE BY HASH({col_list})'
    elif fallback_strategy == 'roundrobin':
        return 'DISTRIBUTE BY ROUNDROBIN'
    elif fallback_strategy == 'replication':
        return 'DISTRIBUTE BY REPLICATION'
    else:
        return 'DISTRIBUTE BY ROUNDROBIN'
