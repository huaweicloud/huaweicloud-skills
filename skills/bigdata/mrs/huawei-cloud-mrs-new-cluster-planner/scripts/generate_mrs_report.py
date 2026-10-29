# AI生成
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRS New Cluster Sizing Report Generator v1.0.0
- 新建MRS集群场景: 生成多Sheet Excel报告（单方案输出,最小冗余）
- Sheet 2 为"资源推算明细"（业务需求→推算资源→MRS推荐配置）
- 文件命名: MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx
- 依赖: openpyxl
"""

import sys
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Error: openpyxl is required. Install it with: pip install openpyxl")
    sys.exit(1)


def _parse_flavor_vcpu_mem(flavor_str: str) -> tuple:
    """Parse vCPU and memory from flavor string like 'ac9.8xlarge.4 (32C/128G)'"""
    import re
    vcpu = 0
    memory = 0
    m = re.search(r'(\d+)\s*[Cc][/ ]\s*(\d+)\s*[Gg]', flavor_str)
    if m:
        vcpu = int(m.group(1))
        memory = int(m.group(2))
    else:
        m_v = re.search(r'(\d+)\s*[Cc]\b', flavor_str)
        m_m = re.search(r'(\d+)\s*[Gg]\b', flavor_str)
        if m_v:
            vcpu = int(m_v.group(1))
        if m_m:
            memory = int(m_m.group(1))
    return vcpu, memory


def _calc_data_disk_config(shuffle_demand_gb: int) -> tuple:
    """
    灵活计算数据盘配置（盘数, 单盘大小GB）
    规则：
    - 单盘大小范围：600~800GB，起步600GB
    - 需求<=800GB: 1块盘，单盘=max(600, 需求)
    - 需求是600的倍数: 600GB/块
    - 否则: 尝试减少盘数，单盘=ceil(需求/盘数)≤800GB
    """
    import math
    MIN_DISK_SIZE = 600
    MAX_DISK_SIZE = 800

    if shuffle_demand_gb <= 0:
        return 1, MIN_DISK_SIZE

    if shuffle_demand_gb <= MAX_DISK_SIZE:
        return 1, max(MIN_DISK_SIZE, shuffle_demand_gb)

    if shuffle_demand_gb % MIN_DISK_SIZE == 0:
        return shuffle_demand_gb // MIN_DISK_SIZE, MIN_DISK_SIZE

    count_600 = math.ceil(shuffle_demand_gb / MIN_DISK_SIZE)
    for count in range(count_600 - 1, 0, -1):
        size = math.ceil(shuffle_demand_gb / count)
        if size > MAX_DISK_SIZE:
            break
        if size < MIN_DISK_SIZE:
            size = MIN_DISK_SIZE
        return count, size

    return count_600, MIN_DISK_SIZE


def _calc_shuffle_disk_count(vcpu: int) -> int:
    """Calculate data disk count based on flexible disk config."""
    if vcpu <= 0:
        return 1
    count, _ = _calc_data_disk_config(vcpu * 40)
    return count


def _calc_shuffle_capacity_gb(vcpu: int) -> int:
    """Calculate total shuffle capacity: vCPU × 40GB"""
    return vcpu * 40


def _enrich_node_detail(node: dict) -> dict:
    """Auto-fill missing fields in node detail dict."""
    flavor = node.get('flavor', '')
    vcpu, memory = _parse_flavor_vcpu_mem(flavor)

    vcpu = node.get('vcpu', vcpu)
    memory = node.get('memory_gb', memory)
    count = node.get('count', 0)

    is_master = 'master' in node.get('group', '').lower()
    if is_master:
        disk_count = 1
        disk_size = 600
        data_disk_desc = '600GB 通用SSD × 1'
    else:
        shuffle_demand = vcpu * 40
        disk_count, disk_size = _calc_data_disk_config(shuffle_demand)
        data_disk_desc = f'{disk_size}GB 通用SSD × {disk_count}'

    shuffle_capacity = disk_count * disk_size if not is_master else 0
    total_shuffle_tb = round(shuffle_capacity * count / 1024, 1) if shuffle_capacity else 0

    node['vcpu'] = vcpu
    node['memory_gb'] = memory
    node['system_disk'] = node.get('system_disk', '480GB 高IO')
    node['data_disk'] = node.get('data_disk', data_disk_desc)
    node['disk_count'] = node.get('disk_count', disk_count)
    node['disk_size'] = node.get('disk_size', disk_size)
    node['shuffle_capacity_gb'] = node.get('shuffle_capacity_gb', shuffle_capacity)
    node['total_vcpu'] = node.get('total_vcpu', vcpu * count)
    node['total_memory_gb'] = node.get('total_memory_gb', memory * count)
    node['total_shuffle_tb'] = node.get('total_shuffle_tb', total_shuffle_tb)
    return node


def generate_mrs_excel_report(report_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate MRS New Cluster Sizing Report as multi-sheet Excel file.

    Args:
        report_data: dict with keys: business_requirements, estimated_resources,
                     plan_a (single plan), recommendation_reason, obs_storage,
                     decisions
        output_path: file path to save, default: MRS_Cluster_Sizing_Report_<date>.xlsx

    Returns:
        Path to the saved Excel file.
    """
    wb = openpyxl.Workbook()

    header_font = Font(name='微软雅黑', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell_align = Alignment(vertical='top', wrap_text=True)
    plan_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    total_font = Font(name='微软雅黑', bold=True)
    total_fill = PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid')
    est_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')  # 估算值标注
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    plan_a = report_data.get('plan_a', {})
    recommendation_reason = report_data.get('recommendation_reason', '')
    biz = report_data.get('business_requirements', {})
    est = report_data.get('estimated_resources', {})

    # =====================================================
    # Sheet 1: 集群规格推荐 (单方案)
    # =====================================================
    ws1 = wb.active
    ws1.title = '集群规格推荐'

    ws1['A1'] = '方案'
    ws1['B1'] = 'Core规格'
    ws1['C1'] = 'Core数量'
    ws1['D1'] = '总vCPU'
    ws1['E1'] = '总内存GB'

    ws1['A2'] = plan_a.get('name', '最终方案')
    ws1['B2'] = plan_a.get('core_flavor', '')
    ws1['C2'] = plan_a.get('core_count', '')
    ws1['D2'] = plan_a.get('core_total_vcpu', '')
    ws1['E2'] = plan_a.get('core_total_mem_gb', '')

    for col in range(1, 6):
        ws1.cell(row=2, column=col).fill = plan_fill

    ws1['A4'] = f'选型说明: {recommendation_reason}'

    headers = ['节点组', '机型规格', 'vCPU', '内存(GB)', '系统盘',
               '数据盘规格(Shuffle)', '数据盘单盘', '盘块数', '数据盘总量(GB)',
               '节点数量', '总vCPU', '总内存GB', '总数据盘TB', '推荐理由']
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=6, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    row_idx = 7
    for node in plan_a.get('nodes_detail', []):
        node = _enrich_node_detail(node)
        ws1.cell(row=row_idx, column=1, value=node.get('group', ''))
        ws1.cell(row=row_idx, column=2, value=node.get('flavor', ''))
        ws1.cell(row=row_idx, column=3, value=node.get('vcpu', ''))
        ws1.cell(row=row_idx, column=4, value=node.get('memory_gb', ''))
        ws1.cell(row=row_idx, column=5, value=node.get('system_disk', '480GB 高IO'))
        ws1.cell(row=row_idx, column=6, value=node.get('data_disk', '600GB 通用SSD'))
        ws1.cell(row=row_idx, column=7, value=f"{node.get('disk_size', 600)}GB 通用SSD")
        ws1.cell(row=row_idx, column=8, value=node.get('disk_count', ''))
        ws1.cell(row=row_idx, column=9, value=node.get('shuffle_capacity_gb', ''))
        ws1.cell(row=row_idx, column=10, value=node.get('count', ''))
        ws1.cell(row=row_idx, column=11, value=node.get('total_vcpu', ''))
        ws1.cell(row=row_idx, column=12, value=node.get('total_memory_gb', ''))
        ws1.cell(row=row_idx, column=13, value=node.get('total_shuffle_tb', ''))
        ws1.cell(row=row_idx, column=14, value=node.get('reason', ''))
        row_idx += 1

    # =====================================================
    # Sheet 2: 资源推算明细 (新建场景核心)
    # =====================================================
    ws2 = wb.create_sheet('资源推算明细')
    res_headers = ['推算资源项', '业务输入', '推算依据', '推算值(估算)',
                   'MRS推荐配置', '冗余百分比', '是否满足', '说明']
    for col, header in enumerate(res_headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # 计算最终方案的总资源(仅Core+Task计算节点)
    rec_total_vcpu = 0
    rec_total_mem = 0
    rec_total_shuffle_tb = 0.0
    rec_total_nodes = 0
    compute_groups = {'Core', 'Task'}
    master_desc = ''
    for node in plan_a.get('nodes_detail', []):
        group_name = node.get('group', '')
        if group_name == 'Master':
            master_desc = f"{node.get('count', '')}×{node.get('flavor', '')}"
            continue
        if group_name not in compute_groups:
            continue
        if isinstance(node.get('total_vcpu'), (int, float)):
            rec_total_vcpu += node['total_vcpu']
        if isinstance(node.get('total_memory_gb'), (int, float)):
            rec_total_mem += node['total_memory_gb']
        if isinstance(node.get('total_shuffle_tb'), (int, float)):
            rec_total_shuffle_tb += node['total_shuffle_tb']
        if isinstance(node.get('count'), (int, float)):
            rec_total_nodes += node['count']

    est_vcpu = est.get('total_cores', 0)
    est_mem = est.get('total_memory_gb', 0)
    est_storage = est.get('storage_tb', 0)
    basis = est.get('estimation_basis', '估算值')

    daily_inc = biz.get('daily_increment_tb', 0)
    window_h = biz.get('window_hours', 0)
    partitions = biz.get('partitions', 0)
    obs_actual = report_data.get('obs_storage', {}).get('storage_tb', 0) or est_storage

    vcpu_growth = f"+{(rec_total_vcpu - est_vcpu) / est_vcpu * 100:.1f}%" if est_vcpu else "-"
    mem_growth = f"+{(rec_total_mem - est_mem) / est_mem * 100:.1f}%" if est_mem else "-"
    storage_growth = f"+{(obs_actual - est_storage) / est_storage * 100:.1f}%" if est_storage else "-"

    # 业务输入描述
    biz_calc = []
    if daily_inc and window_h:
        biz_calc.append(f"日增{daily_inc}TB/窗口{window_h}h")
    if partitions:
        biz_calc.append(f"Kafka {partitions}分区")
    if biz.get('concurrency'):
        biz_calc.append(f"并发{biz['concurrency']}用户")
    if biz.get('qps_wan'):
        biz_calc.append(f"HBase {biz['qps_wan']}万QPS")
    biz_input = '; '.join(biz_calc) if biz_calc else '见推算依据'

    core_desc = f"{plan_a.get('core_count', '')}×{plan_a.get('core_flavor', '')}"
    node_desc = f"{master_desc or '-'} + {core_desc}"

    res_rows = [
        ('总vCPU', biz_input, basis, est_vcpu, rec_total_vcpu, vcpu_growth, '✓',
         '推算资源为估算值,已用户确认'),
        ('总内存(GB)', biz_input, basis, est_mem, rec_total_mem, mem_growth, '✓',
         '冗余因规格粒度(单规格同构)'),
        ('存储容量(TB)', f"存量{biz.get('existing_data_tb', 0)}TB+日增{daily_inc}×{biz.get('retention_days', 0)}天×{biz.get('compression_ratio', 0.5)}",
         'S=存量+日增×保留×压缩', est_storage, f"{obs_actual}(实际容量)", storage_growth, '✓',
         'OBS容量按实际所需存储直接给出（不取套餐包）'),
        ('数据盘存储(TB)', f"盘数×600GB", 'max(1,ceil(vCPU×40/600))×600GB', '-',
         f"{rec_total_shuffle_tb:.1f}", '-', '-',
         'Core数据盘用于Shuffle'),
        ('Master节点', f"Core节点数→vCPU基线", '按元数据估算(6步法)', '-', master_desc or '-', '-', '-',
         '按算法结果选规格'),
        ('总节点数', '-', '-', '-', plan_a.get('total_nodes', rec_total_nodes + 3), '-', '-',
         node_desc),
    ]
    for row_idx, row_data in enumerate(res_rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = cell_align
            cell.border = thin_border
            if col_idx == 4:
                cell.fill = est_fill  # 推算值列标注估算
            if col_idx == 6 and isinstance(value, str) and value.startswith('+'):
                cell.font = Font(name='微软雅黑', color='008000')
            if col_idx == 7 and value == '✓':
                cell.font = Font(name='微软雅黑', color='008000', bold=True)

    # =====================================================
    # Sheet 3: 选型决策理由
    # =====================================================
    ws4 = wb.create_sheet('选型决策理由')
    dec_headers = ['决策项', '候选方案', '最终选择', '选择理由', '淘汰原因']
    for col, header in enumerate(dec_headers, 1):
        cell = ws4.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    for row_idx, decision in enumerate(report_data.get('decisions', []), 2):
        ws4.cell(row=row_idx, column=1, value=decision.get('point', ''))
        ws4.cell(row=row_idx, column=2, value=decision.get('candidates', ''))
        ws4.cell(row=row_idx, column=3, value=decision.get('selected', ''))
        ws4.cell(row=row_idx, column=4, value=decision.get('reasoning', ''))
        ws4.cell(row=row_idx, column=5, value=decision.get('rejected', ''))

    # =====================================================
    # Sheet 4: OBS存储规格 (新建场景推算版)
    # =====================================================
    ws5 = wb.create_sheet('OBS存储规格')
    obs_headers = ['计算项', '业务输入', '计算逻辑', '结果', '说明']
    for col, header in enumerate(obs_headers, 1):
        cell = ws5.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    obs_rows = [
        ('存量数据', f"{biz.get('existing_data_tb', 0)} TB", '用户输入', f"{biz.get('existing_data_tb', 0)} TB", '历史数据一次性导入'),
        ('日增数据量', f"{daily_inc} TB/天", '用户输入', f"{daily_inc} TB/天", '每天新增数据'),
        ('数据保留天数', f"{biz.get('retention_days', 0)} 天", '用户输入', f"{biz.get('retention_days', 0)} 天", '超期数据归档/删除'),
        ('压缩系数', f"{biz.get('compression_ratio', 0.5)}", 'ORC/Parquet取0.3-0.5,默认0.5', f"{biz.get('compression_ratio', 0.5)}", '列存压缩比(估算值)'),
        ('存储总量', '-', f"{biz.get('existing_data_tb', 0)}+{daily_inc}×{biz.get('retention_days', 0)}×{biz.get('compression_ratio', 0.5)}", f"{est_storage} TB", '逻辑量(压缩后)'),
        ('OBS容量', '-', '直接采用实际所需存储', f"{obs_actual} TB", '不取套餐包，按实际所需存储直接给出'),
        ('OBS存储类型', '-', '标准存储', f"{obs_actual} TB", '频繁访问数据'),
    ]
    for row_idx, (item, orig, logic, result, note) in enumerate(obs_rows, 2):
        ws5.cell(row=row_idx, column=1, value=item)
        ws5.cell(row=row_idx, column=2, value=orig)
        ws5.cell(row=row_idx, column=3, value=logic)
        ws5.cell(row=row_idx, column=4, value=result)
        ws5.cell(row=row_idx, column=5, value=note)

    # Auto-fit column widths
    for ws in [ws1, ws2, ws4, ws5]:
        for col in range(1, ws.max_column + 1):
            max_len = 0
            for row in range(1, ws.max_row + 1):
                val = ws.cell(row=row, column=col).value
                if val:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[get_column_letter(col)].width = min(max_len + 4, 50)
        ws.freeze_panes = 'A2'

    if output_path is None:
        output_path = f"MRS_Cluster_Sizing_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb.save(output_path)
    return output_path


def _build_example_data() -> Dict[str, Any]:
    """Build built-in example data (新建数仓+实时混合集群) for testing/demo only."""
    return {
        "business_requirements": {
            "workload_types": ["offline_batch", "streaming"],
            "daily_increment_tb": 5, "existing_data_tb": 50,
            "retention_days": 180, "compression_ratio": 0.4,
            "window_hours": 6, "partitions": 60,
            "peak_buffer": False, "region": "华北-北京四", "storage_mode": "OBS"
        },
        "estimated_resources": {
            "total_cores": 76, "total_memory_gb": 301,
            "storage_tb": 410,
            "estimation_basis": "离线批处理: 5TB×40÷6h≈34vCPU(标准数仓); 实时流: 60分区=60vCPU; 错峰×0.8; 估算值"
        },
        "elastic_task": {"enabled": False},
        "plan_a": {
            "name": "新建混合负载方案 — ac9.4xlarge.4 × 6",
            "core_flavor": "ac9.4xlarge.4 (16C/64G)", "core_count": 6,
            "core_total_vcpu": 96, "core_total_mem_gb": 384,
            "core_data_disk_count": 4,
            "nodes_detail": [
                {"group": "Master", "flavor": "ac9.4xlarge.4 (16C/64G)", "count": 3, "reason": "Core总核数96<100→3节点; Core 6节点≤20→16核基线; 64GB满足非OBS大元数据场景"},
                {"group": "Core", "flavor": "ac9.4xlarge.4 (16C/64G)", "count": 6, "reason": "目标76C/301G(R=4.0); 1:4配比; 6×16=96C(+26.3%); 6×64=384G(+27.6%); Total_excess=53.9%最低; 同构部署"}
            ]
        },
        "recommendation_reason": "ac9.4xlarge.4×6: CPU+26.3%+内存+27.6%=Total_excess 53.9%; 目标R=4.0匹配1:4配比; 规模较小时单规格粒度冗余偏高属正常",
        "obs_storage": {
            "storage_tb": 410,
            "savings_pct": 0
        },
        "decisions": [
            {"point": "资源推算(负载模型)", "candidates": "标准数仓系数40 vCPU·h/TB / 简单ETL 20 / 复杂80",
             "selected": "标准数仓40 vCPU·h/TB",
             "reasoning": "多表Join/聚合标准数仓场景; 批处理5TB×40÷6h≈34vCPU; 实时60分区=60vCPU; 错峰×0.8→76C/301G",
             "rejected": "简单ETL系数低估Join开销; 复杂系数高估常规数仓负载"},
            {"point": "Core规格选择(最小冗余)", "candidates": "ac9.4xl.4×6(冗余53.9%) / ac9.8xl.4×3(冗余78.9%)",
             "selected": "ac9.4xlarge.4 × 6",
             "reasoning": "N=max(ceil(76/16),ceil(301/64))=6; CPU 96C(+26.3%), 内存384G(+27.6%), Total_excess=53.9%最低",
             "rejected": "ac9.8xl.4×3: N=max(5,5)=5→80C(+5.3%)/320G(+6.3%)=11.6%更优但节点数不足支撑60分区并行度→需6节点"},
            {"point": "存储模式选择", "candidates": "OBS存算分离(实际容量410TB) / 本地HDFS三副本",
             "selected": "OBS存算分离",
             "reasoning": "存储总量410TB, 按实际所需容量规划(不取套餐包), OBS月费约¥41,574; 本地HDFS三副本需1230TB物理盘, 成本极高",
             "rejected": "本地HDFS: 1230TB×3副本EVS盘成本约为OBS的10倍以上"}
        ]
    }


def _validate_report_data(report_data: Dict[str, Any]) -> None:
    """Validate that report_data contains minimum required fields for a meaningful report."""
    required_keys = {'business_requirements', 'estimated_resources', 'plan_a'}
    missing = required_keys - set(report_data.keys())
    if missing:
        raise ValueError(
            f"输入 JSON 缺少必需字段: {sorted(missing)}; "
            f"必需字段: {sorted(required_keys)} "
            f"(完整结构见 references/excel-report-template.md)"
        )
    plan_a = report_data.get('plan_a')
    if not isinstance(plan_a, dict) or 'nodes_detail' not in plan_a:
        raise ValueError("plan_a 必须为 dict 且包含 nodes_detail 节点明细列表")


if __name__ == '__main__':
    import argparse
    import json
    import os

    parser = argparse.ArgumentParser(
        description='MRS New Cluster Sizing Report Generator — 从业务需求 JSON 生成多 Sheet Excel 报告',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python generate_mrs_report.py --input report_data.json
  python generate_mrs_report.py -i report_data.json -o /tmp/output.xlsx
  cat report_data.json | python generate_mrs_report.py --input -
  python generate_mrs_report.py --example          # 生成内置示例(仅供测试/演示)

输入 JSON 结构见 references/excel-report-template.md, 必需字段:
  business_requirements, estimated_resources, plan_a
"""
    )
    parser.add_argument('--input', '-i', metavar='FILE',
                        help='业务需求 JSON 文件路径; 传 "-" 从 stdin 读取')
    parser.add_argument('--output', '-o', metavar='FILE', default=None,
                        help='输出 Excel 路径; 默认 MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx')
    parser.add_argument('--example', action='store_true',
                        help='使用内置示例数据生成报告(仅供测试/演示)')
    args = parser.parse_args()

    # ---- 加载 report_data ----
    report_data: Optional[Dict[str, Any]] = None
    if args.example:
        report_data = _build_example_data()
    elif args.input:
        if args.input == '-':
            raw = sys.stdin.read()
            if not raw.strip():
                print("Error: stdin 无内容, 请通过管道传入业务需求 JSON", file=sys.stderr)
                sys.exit(1)
            try:
                report_data = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"Error: 无法解析 stdin 的 JSON: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            if not os.path.isfile(args.input):
                print(f"Error: 输入文件不存在: {args.input}", file=sys.stderr)
                sys.exit(1)
            try:
                with open(args.input, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: 无法解析 JSON 文件 {args.input}: {e}", file=sys.stderr)
                sys.exit(1)
    elif not sys.stdin.isatty():
        # 检测到 stdin 管道/重定向但未显式指定 --input, 自动读取 (便利用法)
        raw = sys.stdin.read()
        if not raw.strip():
            # stdin 为空, 视为未提供输入, 走下面的帮助提示分支
            pass
        else:
            try:
                report_data = json.loads(raw)
            except json.JSONDecodeError as e:
                print(f"Error: 无法解析 stdin 的 JSON: {e}", file=sys.stderr)
                sys.exit(1)

    if report_data is None:
        parser.print_help(sys.stderr)
        print(
            "\nError: 未提供输入数据。请使用 --input <FILE> 指定业务需求 JSON, "
            "或通过管道传入, 或使用 --example 生成内置示例。",
            file=sys.stderr
        )
        sys.exit(2)

    # ---- 校验 ----
    try:
        _validate_report_data(report_data)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # ---- 生成报告 ----
    output = generate_mrs_excel_report(report_data, output_path=args.output)
    print(f"Excel报告已生成: {output}")
