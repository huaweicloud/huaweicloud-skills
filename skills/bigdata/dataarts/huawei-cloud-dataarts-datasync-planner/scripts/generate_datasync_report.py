#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataSync 数据集成链路规划报告生成器 v2.0.0
- 生成多Sheet Excel报告(3 Sheet: 源端数据链路/华为云侧同步链路/无法直接对标方案)
- 第3个Sheet按需生成(当存在无法直接对标的链路时)
- 文件命名: DataSync_Pipeline_Report_<YYYYMMDD>.xlsx
- 用法: python generate_datasync_report.py --input report.json [--output 路径]
       不指定 --input 时使用内置示例数据生成演示报告
- 方案类型 scheme_type 同时兼容中文/英文取值
- 依赖: openpyxl
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, Any, List

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Error: openpyxl is required. Install it with: pip install openpyxl")
    sys.exit(1)


# =====================================================
# 样式定义(集中管理,便于复用)
# =====================================================
def _build_styles() -> Dict[str, Any]:
    """构建并返回公共样式集合,统一各Sheet视觉风格"""
    return {
        # 标题样式:大字号+深蓝填充+白字
        'title_font': Font(name='微软雅黑', bold=True, color='FFFFFF', size=14),
        'title_fill': PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid'),
        'title_align': Alignment(horizontal='center', vertical='center', wrap_text=True),
        # 表头样式:加粗+深蓝填充+白字+居中
        'header_font': Font(name='微软雅黑', bold=True, color='FFFFFF', size=11),
        'header_fill': PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid'),
        'header_align': Alignment(horizontal='center', vertical='center', wrap_text=True),
        # 数据单元格样式:顶部对齐+自动换行
        'cell_align': Alignment(vertical='top', wrap_text=True),
        # 隔行变色(浅蓝/浅白)
        'row_fill_a': PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid'),
        'row_fill_b': PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid'),
        # 方案类型颜色编码
        # 直接对标→浅绿
        'fill_direct': PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'),
        # 华为云可行方案(间接)→浅黄
        'fill_indirect': PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid'),
        # 三方软件方案→浅橙
        'fill_third': PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid'),
        # 细边框
        'thin_border': Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        ),
    }


def _write_title_row(ws, title_text: str, col_count: int, styles: Dict[str, Any]) -> int:
    """写入标题行(报告名+日期),返回下一可用行号"""
    ws.cell(row=1, column=1, value=title_text)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(col_count, 1))
    cell = ws.cell(row=1, column=1)
    cell.font = styles['title_font']
    cell.fill = styles['title_fill']
    cell.alignment = styles['title_align']
    ws.row_dimensions[1].height = 28

    # 副标题:生成日期
    date_text = f"生成日期: {datetime.now().strftime('%Y-%m-%d')}"
    ws.cell(row=2, column=1, value=date_text)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(col_count, 1))
    sub_cell = ws.cell(row=2, column=1)
    sub_cell.font = Font(name='微软雅黑', italic=True, color='595959', size=10)
    sub_cell.alignment = styles['title_align']
    return 3  # 表头从第3行开始


def _write_header_row(ws, headers: List[str], row_idx: int, styles: Dict[str, Any]) -> None:
    """写入表头行,应用深蓝填充+白字加粗样式"""
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_idx, column=col, value=header)
        cell.font = styles['header_font']
        cell.fill = styles['header_fill']
        cell.alignment = styles['header_align']
        cell.border = styles['thin_border']
    ws.row_dimensions[row_idx].height = 32


def _write_data_rows(ws, rows: List[List[Any]], start_row: int, styles: Dict[str, Any]) -> None:
    """写入数据行,应用隔行变色+边框"""
    for r_offset, row_data in enumerate(rows):
        row_idx = start_row + r_offset
        # 隔行变色:偶数行浅蓝,奇数行白
        fill = styles['row_fill_b'] if r_offset % 2 == 1 else styles['row_fill_a']
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = styles['cell_align']
            cell.border = styles['thin_border']
            cell.fill = fill


def _auto_fit_columns(ws) -> None:
    """自动适配列宽(按内容长度估算,上限50)"""
    for col in range(1, ws.max_column + 1):
        max_len = 0
        for row in range(1, ws.max_row + 1):
            val = ws.cell(row=row, column=col).value
            if val is not None:
                # 中文字符按2计算宽度,英文字符按1计算
                cell_len = sum(2 if ord(c) > 127 else 1 for c in str(val))
                max_len = max(max_len, cell_len)
        col_letter = get_column_letter(col)
        ws.column_dimensions[col_letter].width = min(max_len + 4, 50)


def _safe_str(value: Any) -> str:
    """安全转字符串,None返回空串"""
    return '' if value is None else str(value)


# 方案类型中英文别名表(脚本同时兼容中文与英文取值,统一归一化为中文规范名)
_SCHEME_TYPE_ALIASES = {
    '直接对标': '直接对标',
    'direct match': '直接对标',
    '华为云可行方案(间接)': '华为云可行方案(间接)',
    'huawei cloud feasible solution (indirect)': '华为云可行方案(间接)',
    '三方软件方案': '三方软件方案',
    'third-party software solution': '三方软件方案',
}


def _normalize_scheme_type(scheme_type: str) -> str:
    """归一化方案类型为中文规范名,兼容中英文取值;空值返回空串,未知类型原样返回去空格结果"""
    if not scheme_type:
        return ''
    stripped = scheme_type.strip()
    # 精确匹配
    if stripped in _SCHEME_TYPE_ALIASES:
        return _SCHEME_TYPE_ALIASES[stripped]
    # 大小写不敏感兜底
    lower = stripped.lower()
    for alias, canonical in _SCHEME_TYPE_ALIASES.items():
        if alias.lower() == lower:
            return canonical
    return stripped


def _get_scheme_fill(scheme_type: str, styles: Dict[str, Any]) -> Any:
    """根据方案类型返回对应的填充色,未知类型返回None;兼容中英文取值"""
    canonical = _normalize_scheme_type(scheme_type)
    key_map = {
        '直接对标': 'fill_direct',
        '华为云可行方案(间接)': 'fill_indirect',
        '三方软件方案': 'fill_third',
    }
    style_key = key_map.get(canonical)
    return styles.get(style_key) if style_key else None


def _collect_no_direct_match_pipelines(pipelines: List[dict]) -> List[dict]:
    """筛选无法直接对标的链路(存在no_direct_match且方案类型非'直接对标');兼容中英文取值"""
    result = []
    for p in pipelines:
        solution = p.get('huawei_solution', {}) or {}
        scheme_type = _safe_str(solution.get('scheme_type', ''))
        canonical = _normalize_scheme_type(scheme_type)
        no_match = p.get('no_direct_match')
        # 同时满足:存在no_direct_match数据 且 方案类型非"直接对标"
        if no_match and canonical and canonical != '直接对标':
            result.append(p)
    return result


def generate_datasync_excel_report(report_data: dict, output_path: str = None) -> str:
    """
    生成 DataSync 数据集成链路规划报告为多Sheet Excel文件.

    Args:
        report_data: dict 包含 pipelines(链路列表)
        output_path: 保存路径,默认: DataSync_Pipeline_Report_<date>.xlsx

    Returns:
        保存后的Excel文件路径.
    """
    wb = openpyxl.Workbook()
    styles = _build_styles()

    pipelines: List[dict] = report_data.get('pipelines', [])

    # =====================================================
    # Sheet 1: 源端数据链路(始终生成)
    # =====================================================
    ws1 = wb.active
    ws1.title = '源端数据链路'
    s1_headers = ['链路编号', '链路名称', '源端数据源', '源端版本', '源端部署',
                  '目标端数据源', '目标端版本', '目标端部署', '同步模式',
                  '日同步数据量(GB)', '同步频率', '延迟要求', '现有工具']
    next_row = _write_title_row(ws1, '源端数据集成链路清单', len(s1_headers), styles)
    _write_header_row(ws1, s1_headers, next_row, styles)
    s1_data_start = next_row + 1

    s1_rows = []
    for p in pipelines:
        source = p.get('source', {}) or {}
        target = p.get('target', {}) or {}
        s1_rows.append([
            p.get('id', ''),
            p.get('name', ''),
            source.get('type', ''),
            source.get('version', ''),
            source.get('deploy', ''),
            target.get('type', ''),
            target.get('version', ''),
            target.get('deploy', ''),
            p.get('mode', ''),
            p.get('daily_volume_gb', ''),
            p.get('frequency', ''),
            p.get('latency', ''),
            p.get('tool', ''),
        ])
    _write_data_rows(ws1, s1_rows, s1_data_start, styles)

    # =====================================================
    # Sheet 2: 华为云侧同步链路(始终生成)
    # =====================================================
    ws2 = wb.create_sheet('华为云侧同步链路')
    s2_headers = ['链路编号', '源端链路', '集成模式', '方案类型', '推荐产品',
                  '链路拓扑', '日同步数据量(GB)', '配置建议', '约束条件', '备选方案']
    next_row = _write_title_row(ws2, '华为云侧同步链路设计', len(s2_headers), styles)
    _write_header_row(ws2, s2_headers, next_row, styles)
    s2_data_start = next_row + 1

    # 方案类型列(第4列)按类型上色,其余列保持隔行变色
    for r_offset, p in enumerate(pipelines):
        row_idx = s2_data_start + r_offset
        solution = p.get('huawei_solution', {}) or {}
        scheme_type = _safe_str(solution.get('scheme_type', ''))
        row_fill = styles['row_fill_b'] if r_offset % 2 == 1 else styles['row_fill_a']
        row_values = [
            p.get('id', ''),
            p.get('name', ''),
            solution.get('mode', ''),
            scheme_type,
            solution.get('product', ''),
            solution.get('topology', ''),
            p.get('daily_volume_gb', ''),
            solution.get('config', ''),
            solution.get('constraints', ''),
            solution.get('alternative', ''),
        ]
        scheme_fill = _get_scheme_fill(scheme_type, styles)
        for col_idx, value in enumerate(row_values, 1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = styles['cell_align']
            cell.border = styles['thin_border']
            # 方案类型列按类型上色;其余列采用隔行变色
            if col_idx == 4 and scheme_fill is not None:
                cell.fill = scheme_fill
                cell.font = Font(name='微软雅黑', bold=True)
            else:
                cell.fill = row_fill

    # =====================================================
    # Sheet 3: 无法直接对标方案(条件生成)
    # 仅当存在 no_direct_match 数据 且 scheme_type != "直接对标" 时生成
    # =====================================================
    no_match_pipelines = _collect_no_direct_match_pipelines(pipelines)
    if no_match_pipelines:
        ws3 = wb.create_sheet('无法直接对标方案')
        s3_headers = ['链路编号', '源端链路', '无法直接对标原因',
                      '华为云可行方案(优先)', '华为云方案拓扑',
                      '三方软件方案(次选)', '三方方案拓扑', '优缺点对比']
        next_row = _write_title_row(ws3, '无法直接对标链路方案对比', len(s3_headers), styles)
        _write_header_row(ws3, s3_headers, next_row, styles)
        s3_data_start = next_row + 1

        s3_rows = []
        for p in no_match_pipelines:
            nm = p.get('no_direct_match', {}) or {}
            s3_rows.append([
                p.get('id', ''),
                p.get('name', ''),
                nm.get('reason', ''),
                nm.get('huawei_feasible', ''),
                nm.get('huawei_topology', ''),
                nm.get('third_party', ''),
                nm.get('third_party_topology', ''),
                nm.get('pros_cons', ''),
            ])
        _write_data_rows(ws3, s3_rows, s3_data_start, styles)

        # 华为云方案列(第4列)浅黄高亮,三方方案列(第6列)浅橙高亮
        for r_offset in range(len(s3_rows)):
            row_idx = s3_data_start + r_offset
            huawei_cell = ws3.cell(row=row_idx, column=4)
            if huawei_cell.value:
                huawei_cell.fill = styles['fill_indirect']
                huawei_cell.font = Font(name='微软雅黑', bold=True)
            third_cell = ws3.cell(row=row_idx, column=6)
            if third_cell.value:
                third_cell.fill = styles['fill_third']
                third_cell.font = Font(name='微软雅黑', bold=True)

    # =====================================================
    # 列宽自适应 + 冻结首行(标题+表头)
    # =====================================================
    sheets_to_finalize = [ws1, ws2]
    if no_match_pipelines:
        sheets_to_finalize.append(ws3)
    for ws in sheets_to_finalize:
        _auto_fit_columns(ws)
        # 冻结表头(数据从第4行开始,冻结至第3行)
        ws.freeze_panes = 'A4'

    # 保存文件
    if output_path is None:
        output_path = f"DataSync_Pipeline_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb.save(output_path)
    return output_path


def _load_report_data(input_path: str) -> dict:
    """从JSON文件加载调研结果数据(report.json)"""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _build_example_data() -> dict:
    """构造示例数据:覆盖3类场景(P001/P002 直接对标, P003 三方软件方案含 no_direct_match)"""
    return {
        "pipelines": [
            {
                "id": "P001",
                "name": "Oracle到MRS ClickHouse离线同步",
                "source": {"type": "Oracle", "version": "12c R2", "deploy": "本地自建"},
                "target": {"type": "MRS ClickHouse", "version": "21.3.4.X", "deploy": "华为云MRS"},
                "mode": "全量+增量",
                "daily_volume_gb": 50,
                "frequency": "每天1次",
                "latency": "小时级",
                "tool": "Kettle",
                "huawei_solution": {
                    "mode": "离线集成",
                    "scheme_type": "直接对标",
                    "product": "DataArts Studio 离线作业",
                    "topology": "Oracle → [专线] → DataArts Studio → MRS ClickHouse",
                    "config": "DataArts Studio 离线作业调度,每天凌晨2点定时执行,通过JDBC从Oracle抽取并写入ClickHouse",
                    "constraints": "源端Oracle需开启日志归档;目标ClickHouse表需预创建;专线带宽≥100Mbps",
                    "alternative": "CDM批量迁移作业(适合首次全量历史数据迁移)"
                }
            },
            {
                "id": "P002",
                "name": "MySQL到MRS Kafka实时同步",
                "source": {"type": "MySQL", "version": "8.0", "deploy": "本地自建"},
                "target": {"type": "MRS Kafka", "version": "2.8", "deploy": "华为云MRS"},
                "mode": "增量",
                "daily_volume_gb": 10,
                "frequency": "持续",
                "latency": "秒级",
                "tool": "Canal",
                "huawei_solution": {
                    "mode": "实时集成",
                    "scheme_type": "直接对标",
                    "product": "DRS实时同步",
                    "topology": "MySQL → [VPC对等连接] → DRS → MRS Kafka",
                    "config": "DRS实时链路基于Binlog捕获,秒级投递到Kafka Topic,支持断点续传",
                    "constraints": "源端MySQL需开启Binlog;目标Kafka Topic需预创建;DRS实例规格按峰值流量选择",
                    "alternative": "CDM实时作业(延迟略高,适合准实时场景)"
                }
            },
            {
                "id": "P003",
                "name": "SQL Server到MRS HBase实时同步",
                "source": {"type": "SQL Server", "version": "2016 Enterprise", "deploy": "本地自建"},
                "target": {"type": "MRS HBase", "version": "2.2.3", "deploy": "华为云MRS"},
                "mode": "增量",
                "daily_volume_gb": 30,
                "frequency": "持续",
                "latency": "秒级",
                "tool": "Debezium+Kafka Connect",
                "huawei_solution": {
                    "mode": "实时集成",
                    "scheme_type": "三方软件方案",
                    "product": "Debezium+Kafka Connect(自管)",
                    "topology": "SQL Server → [专线] → MRS Kafka(自管Debezium) → MRS HBase(BulkLoad)",
                    "config": "在MRS节点部署Debezium Connector,捕获SQL Server CDC变更投递Kafka,经Spark Streaming消费写入HBase",
                    "constraints": "需自管Debezium高可用;SQL Server需开启CDC;HBase表需预建RowKey设计;运维复杂度高",
                    "alternative": "DRS不支持SQL Server到HBase直连,需自管链路"
                },
                "no_direct_match": {
                    "reason": "华为云DRS不支持SQL Server作为源端到HBase的直连同步,且DataArts Studio实时作业不支持SQL Server CDC捕获,无法直接对标原Debezium方案",
                    "huawei_feasible": "采用 MRS Kafka中转 + Spark Streaming消费写入HBase 方案,SQL Server侧仍需自管CDC工具(如Debezium)捕获变更投递至MRS Kafka",
                    "huawei_topology": "SQL Server → [专线] → 自管Debezium → MRS Kafka → Spark Streaming → MRS HBase",
                    "third_party": "Debezium+Kafka Connect全自管方案,部署于MRS节点或独立ECS,完整复刻原链路架构",
                    "third_party_topology": "SQL Server → [专线] → MRS节点(Debezium+Kafka Connect) → MRS Kafka → MRS HBase(BulkLoad)",
                    "pros_cons": "华为云方案优点:复用MRS Kafka与Spark,降低部分运维成本;缺点:仍需自管CDC工具。三方方案优点:架构与原链路完全一致,迁移成本最低;缺点:全链路自管,高可用与监控需自行建设。综合推荐:华为云方案(优先),保留MRS托管组件优势"
                }
            }
        ]
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='DataSync 数据集成链路规划报告生成器 (多Sheet Excel)'
    )
    parser.add_argument(
        '--input', '-i',
        help='调研结果JSON文件路径(report.json); 不指定时使用内置示例数据生成演示报告',
    )
    parser.add_argument(
        '--output', '-o',
        help='输出Excel文件路径; 不指定时使用默认命名 DataSync_Pipeline_Report_<YYYYMMDD>.xlsx',
    )
    args = parser.parse_args()

    if args.input:
        report_data = _load_report_data(args.input)
        print(f"已加载调研结果: {args.input}")
    else:
        report_data = _build_example_data()
        print("未指定 --input, 使用内置示例数据生成演示报告")

    output = generate_datasync_excel_report(report_data, output_path=args.output)
    print(f"Excel报告已生成: {output}")
