#!/usr/bin/env python3
"""
Teradata 到 DWS 数据类型映射模块

严格遵循华为云官方文档：
https://support.huaweicloud.com/migration-dws/dws_15_0131.html

映射规则来源：DWS 数据迁移与同步文档 - 2.4 Teradata 迁移到 DWS 的数据类型映射
"""

import re

# SQL 关键字常量：受控 SQL 构造用
_SQL_CREATE_TABLE = 'CREATE TABLE'
from typing import Tuple, Optional


# ============================================================
# Teradata → DWS 数据类型映射表
# ============================================================
# 格式: (Teradata类型正则模式, DWS类型模板, 说明)
# 模板中使用 {n} 和 {m} 作为精度和标度的占位符

TYPE_MAPPING = {
    # --- 整数类型 ---
    'BIGINT':               ('BIGINT',              '直接映射'),
    'BYTEINT':              ('SMALLINT',            'Teradata BYTEINT 范围 -128~127，映射为 DWS SMALLINT'),
    'INT':                  ('INTEGER',             '直接映射'),
    'INTEGER':              ('INTEGER',             '直接映射'),
    'SMALLINT':             ('SMALLINT',            '直接映射'),

    # --- 精确小数类型 ---
    'DECIMAL':              ('DECIMAL',             '带精度标度直接映射'),
    'NUMBER':               ('NUMERIC',             'NUMBER 映射为 NUMERIC'),
    'NUMERIC':              ('NUMERIC',             '直接映射'),

    # --- 近似数值类型 ---
    'DOUBLE PRECISION':     ('DOUBLE PRECISION',    '直接映射'),
    'FLOAT':                ('DOUBLE PRECISION',    'Teradata FLOAT 映射为 DWS DOUBLE PRECISION'),
    'REAL':                 ('REAL',                '直接映射'),

    # --- 字符类型 ---
    'CHAR':                 ('CHAR',                '带长度直接映射'),
    'CHARACTER':            ('CHAR',                'CHARACTER 映射为 CHAR'),
    'VARCHAR':              ('VARCHAR',             '带长度直接映射'),
    'CHAR VARYING':         ('VARCHAR',             'CHAR VARYING 映射为 VARCHAR'),
    'CHARACTER VARYING':    ('VARCHAR',             'CHARACTER VARYING 映射为 VARCHAR'),
    'LONG VARCHAR':         ('TEXT',                'LONG VARCHAR 映射为 TEXT'),
    'CLOB':                 ('CLOB',                '直接映射'),

    # --- 日期时间类型 ---
    'DATE':                 ('DATE',                '直接映射'),
    'TIME':                 ('TIME',                '带精度直接映射'),
    'TIMESTAMP':            ('TIMESTAMP',           '带精度直接映射'),

    # --- 二进制类型 ---
    'BLOB':                 ('blob',                '带长度映射'),
    'BYTE':                 ('bytea',               'BYTE 映射为 bytea'),
    'VARBYTE':              ('bytea',               'VARBYTE 映射为 bytea'),

    # --- PERIOD 类型 ---
    # PERIOD 类型在下方通过专用函数处理
}


# PERIOD 类型映射（需要解析内部类型）
PERIOD_MAPPING = {
    'DATE':                  'daterange',
    'TIME':                  'tsrange',
    'TIME WITH TIME ZONE':   'tstzrange',
    'TIMESTAMP':             'tsrange',
    'TIMESTAMP WITH TIME ZONE': 'tstzrange',
}


# 不支持映射的类型（如有发现将报警）
UNSUPPORTED_TYPES = set()


def normalize_type_string(type_str: str) -> str:
    """
    规范化类型字符串：去除多余空格、统一大写、去除括号内空格
    """
    if not type_str:
        return ''
    # 去除首尾空格
    s = type_str.strip()
    # 统一多个空格为单个
    s = re.sub(r'\s+', ' ', s)
    # 去除括号内空格: DECIMAL ( n , m ) -> DECIMAL(n,m)
    s = re.sub(r'\s*\(\s*', '(', s)
    s = re.sub(r'\s*\,\s*', ',', s)
    s = re.sub(r'\s*\)\s*', ')', s)
    return s


def extract_precision_scale(type_str: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    从类型字符串中提取精度(n)和标度(m)

    返回: (精度, 标度, 去除括号后的基础类型名)
    """
    match = re.match(r'^([A-Za-z\s]+)\((\d+)(?:,(\d+))?\)', type_str)
    if match:
        base_type = match.group(1).strip()
        precision = match.group(2)
        scale = match.group(3)
        return precision, scale, base_type
    return None, None, type_str


def map_period_type(type_str: str) -> Tuple[str, str]:
    """
    处理 PERIOD 类型的映射

    PERIOD(DATE) → daterange
    PERIOD(TIME[(n)]) → tsrange[(n)]
    PERIOD(TIME WITH TIME ZONE) → tstzrange
    PERIOD(TIMESTAMP[(n)]) → tsrange[(n)]
    PERIOD(TIMESTAMP WITH TIME ZONE) → tstzrange
    """
    # 提取 PERIOD 内部类型
    match = re.match(r'^PERIOD\((.+)\)$', type_str, re.IGNORECASE)
    if not match:
        return type_str, '无法解析 PERIOD 类型'

    inner_type = match.group(1).strip().upper()
    precision_match = re.search(r'\((\d+)\)', inner_type)
    precision = precision_match.group(1) if precision_match else None

    # 去除精度部分用于匹配
    inner_base = re.sub(r'\(\d+\)', '', inner_type).strip()

    if inner_base in PERIOD_MAPPING:
        dws_type = PERIOD_MAPPING[inner_base]
        if precision and 'tsrange' in dws_type:
            dws_type = f'tsrange({precision})'
        return dws_type, f'PERIOD({inner_type}) → {dws_type}'

    return type_str, f'未知的 PERIOD 内部类型: {inner_type}'


def map_teradata_to_dws(teradata_type: str) -> Tuple[str, str]:
    """
    将 Teradata 数据类型映射为 DWS 数据类型

    参数:
        teradata_type: Teradata 数据类型字符串，如 'DECIMAL(10,2)'

    返回:
        (dws_type, description): DWS 数据类型和映射说明
    """
    if not teradata_type:
        return '', '空类型'

    # 规范化
    normalized = normalize_type_string(teradata_type)
    upper = normalized.upper()

    # 处理 PERIOD 类型
    if upper.startswith('PERIOD'):
        return map_period_type(normalized)

    # 处理 WITH TIME ZONE 后缀
    has_time_zone = 'WITH TIME ZONE' in upper
    base_without_tz = re.sub(r'\s+WITH\s+TIME\s+ZONE', '', upper).strip()

    # 提取精度和标度
    precision, scale, base_type = extract_precision_scale(base_without_tz)
    base_type_upper = base_type.upper().strip()

    # 查找映射
    if base_type_upper in TYPE_MAPPING:
        dws_base, desc = TYPE_MAPPING[base_type_upper]

        # 构建带精度标度的 DWS 类型
        if precision is not None:
            if scale is not None:
                dws_type = f'{dws_base}({precision},{scale})'
            else:
                dws_type = f'{dws_base}({precision})'
        else:
            dws_type = dws_base

        # 添加 WITH TIME ZONE 后缀
        if has_time_zone:
            dws_type = f'{dws_type} WITH TIME ZONE'

        return dws_type, f'{teradata_type} → {dws_type} ({desc})'

    # 尝试匹配带空格的类型（如 DOUBLE PRECISION, LONG VARCHAR, CHAR VARYING）
    for td_type, (dws_type, desc) in TYPE_MAPPING.items():
        if ' ' in td_type and base_type_upper == td_type:
            if precision is not None:
                if scale is not None:
                    dws_type = f'{dws_type}({precision},{scale})'
                else:
                    dws_type = f'{dws_type}({precision})'
            return dws_type, f'{teradata_type} → {dws_type} ({desc})'

    # 未知类型
    UNSUPPORTED_TYPES.add(teradata_type)
    return teradata_type, f'警告: 未知类型 "{teradata_type}"，保持原样'


def map_column_definition(column_name: str, teradata_type: str,
                           nullable: bool = True,
                           default_value: str = None) -> str:
    """
    生成 DWS 列定义

    参数:
        column_name: 列名
        teradata_type: Teradata 数据类型
        nullable: 是否允许 NULL
        default_value: 默认值

    返回:
        DWS 列定义 SQL 片段
    """
    dws_type, desc = map_teradata_to_dws(teradata_type)

    parts = [f'    "{column_name}"', dws_type]

    if default_value is not None:
        parts.append(f'DEFAULT {default_value}')

    if not nullable:
        parts.append('NOT NULL')

    return ' '.join(parts)


def convert_create_table(td_ddl: str) -> str:
    """
    将 Teradata CREATE TABLE 语句转换为 DWS CREATE TABLE 语句

    这是一个简化版的 DDL 转换器，处理基本的 CREATE TABLE 语法。
    对于复杂的 DDL，建议使用 DSC 工具。
    """
    lines = td_ddl.strip().split('\n')
    output_lines = []
    in_create = False
    table_name = ''

    for line in lines:
        stripped = line.strip()

        # 检测 CREATE TABLE
        create_match = re.match(
            r'CREATE\s+(?:SET|MULTISET\s+)?TABLE\s+(?:\.?\.)?("?[\w.]+"?)',
            stripped, re.IGNORECASE
        )
        if create_match:
            in_create = True
            table_name = create_match.group(1)
            output_lines.append(_SQL_CREATE_TABLE + ' ' + table_name + ' (')
            continue

        if in_create:
            # 检测列定义
            col_match = re.match(
                r'("?[\w]+"?)\s+([\w\s\(\),]+?)(?:\s+(?:NOT\s+)?NULL)?(?:,?)$',
                stripped, re.IGNORECASE
            )
            if col_match and not stripped.upper().startswith(('PRIMARY', 'UNIQUE', 'INDEX', 'CONSTRAINT', ');', ')')):
                col_name = col_match.group(1)
                col_type = col_match.group(2).strip().rstrip(',')
                dws_type, _ = map_teradata_to_dws(col_type)
                is_not_null = 'NOT NULL' in stripped.upper()
                nullable_str = ' NOT NULL' if is_not_null else ''
                comma = ',' if not stripped.rstrip().endswith(')') else ''
                output_lines.append(f'    "{col_name}" {dws_type}{nullable_str}{comma}')
            elif stripped.upper().startswith(');') or stripped == ');':
                output_lines.append(');')
                in_create = False
            elif stripped == ');':
                output_lines.append(');')
                in_create = False

    return '\n'.join(output_lines)


def print_mapping_table():
    """打印完整的类型映射表"""
    print("=" * 70)
    print("Teradata → DWS 数据类型映射表")
    print("=" * 70)
    print(f"{'Teradata 类型':<40} {'DWS 类型':<20} {'说明'}")
    print("-" * 70)

    for td_type, (dws_type, desc) in TYPE_MAPPING.items():
        print(f"{td_type:<40} {dws_type:<20} {desc}")

    print("-" * 70)
    print("PERIOD 类型映射:")
    for inner, dws in PERIOD_MAPPING.items():
        print(f"PERIOD({inner}){'':<28} {dws}")

    print("=" * 70)


if __name__ == '__main__':
    print_mapping_table()

    # 测试示例
    print("\n映射示例:")
    test_types = [
        'BIGINT', 'BYTEINT', 'DECIMAL(10,2)', 'FLOAT',
        'VARCHAR(255)', 'LONG VARCHAR', 'CHAR(10)',
        'TIMESTAMP(6)', 'TIMESTAMP(6) WITH TIME ZONE',
        'PERIOD(DATE)', 'PERIOD(TIMESTAMP(6))',
        'BLOB(1024)', 'BYTE(16)', 'VARBYTE(256)',
    ]
    for t in test_types:
        dws, desc = map_teradata_to_dws(t)
        print(f"  {t:<35} → {dws:<25} ({desc})")
