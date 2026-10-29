# AI生成
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRS Cluster Sizing Report Generator v3.0.0
- 生成多Sheet Excel报告（单方案输出,最小冗余）
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
    # Match patterns like "32C/128G" or "32C 128G" or "32 vCPU 128GB"
    m = re.search(r'(\d+)\s*[Cc][/ ]\s*(\d+)\s*[Gg]', flavor_str)
    if m:
        vcpu = int(m.group(1))
        memory = int(m.group(2))
    else:
        # Try "32C" and "128G" separately
        m_v = re.search(r'(\d+)\s*[Cc]\b', flavor_str)
        m_m = re.search(r'(\d+)\s*[Gg]\b', flavor_str)
        if m_v:
            vcpu = int(m_v.group(1))
        if m_m:
            memory = int(m_m.group(1))
    return vcpu, memory


def _calc_shuffle_disk(vcpu: int) -> tuple:
    """Flexible shuffle disk planning for one node.

    Per-node shuffle requirement = vCPU × 40 GB.
    Single disk size is flexible: 600 GB minimum, 800 GB maximum.
    Use the fewest disks that fit while keeping each disk within 600-800 GB
    (i.e. prefer the smallest disks of at least 600 GB).

    Returns (disk_count, disk_size_gb).
    """
    if vcpu <= 0:
        return 1, 600
    need = vcpu * 40

    # N = max(1, floor(need / 600)) -> starts from the smallest allowed disks
    n = max(1, need // 600)
    disk_size = max(600, -(-need // n))  # ceil division, clamped to the 600 GB floor

    if disk_size > 800:
        # need cannot be split within the 600-800 GB range -> over-provision with minimum-size disks
        n = -(-need // 600)  # ceil(need / 600)
        disk_size = 600

    return n, min(disk_size, 800)


def _calc_shuffle_disk_count(vcpu: int) -> int:
    """Calculate data disk count using the flexible 600-800 GB rule."""
    return _calc_shuffle_disk(vcpu)[0]


def _calc_shuffle_capacity_gb(vcpu: int) -> int:
    """Calculate per-node shuffle data disk total: disk size × disk count (>= vCPU × 40 GB)."""
    n, disk_size = _calc_shuffle_disk(vcpu)
    return n * disk_size


def _enrich_node_detail(node: dict) -> dict:
    """Auto-fill missing fields in node detail dict."""
    flavor = node.get('flavor', '')
    vcpu, memory = _parse_flavor_vcpu_mem(flavor)

    # Override with explicit values if provided
    vcpu = node.get('vcpu', vcpu)
    memory = node.get('memory_gb', memory)
    count = node.get('count', 0)

    # Auto-calculate disk info
    is_master = 'master' in node.get('group', '').lower()
    if is_master:
        disk_count = 1
        disk_size = 600
        data_disk_desc = '600GB 通用SSD × 1'
    else:
        disk_count, disk_size = _calc_shuffle_disk(vcpu)
        data_disk_desc = f'{disk_size}GB 通用SSD × {disk_count}'

    # Per-node shuffle capacity = disk size × disk count; total = per-node capacity × node count
    shuffle_capacity = (disk_count * disk_size) if not is_master else 0
    total_shuffle_tb = round(shuffle_capacity * count / 1024, 1) if shuffle_capacity else 0

    node['vcpu'] = vcpu
    node['memory_gb'] = memory
    node['system_disk'] = node.get('system_disk', '480GB 高IO')
    node['data_disk'] = node.get('data_disk', data_disk_desc)
    node['disk_count'] = node.get('disk_count', disk_count)
    node['disk_size_gb'] = node.get('disk_size_gb', disk_size)
    node['shuffle_capacity_gb'] = node.get('shuffle_capacity_gb', shuffle_capacity)
    node['total_vcpu'] = node.get('total_vcpu', vcpu * count)
    node['total_memory_gb'] = node.get('total_memory_gb', memory * count)
    node['total_shuffle_tb'] = node.get('total_shuffle_tb', total_shuffle_tb)
    return node


def _build_q14_note(report_data: Dict[str, Any], master_nodes: list) -> str:
    """
    迁移场景 Q14 核验 (master-sizing-algorithm.md Step 7):
    比较 MRS 管控节点规格 与 原集群 Master 实际使用量。
    Returns a conclusion string, or '-' when not applicable / inputs missing.
    """
    src = report_data.get('source_cluster', {}) or {}
    mem_util = src.get('master_mem_utilization_pct')
    cpu_util = src.get('master_cpu_utilization_pct')
    if not master_nodes or (mem_util is None and cpu_util is None):
        return '-'

    orig_count = src.get('master_node_count') or src.get('node_count') or len(master_nodes)
    orig_per_node_mem = src.get('master_node_memory_gb')
    if orig_per_node_mem is None:
        if not src.get('total_memory_gb'):
            return '-'
        orig_per_node_mem = src['total_memory_gb'] / orig_count
    orig_per_node_vcpu = src.get('master_node_vcpu')
    if orig_per_node_vcpu is None:
        if not src.get('total_cores'):
            return '-'
        orig_per_node_vcpu = src['total_cores'] / orig_count
    orig_total_mem = orig_per_node_mem * orig_count
    orig_total_cpu = orig_per_node_vcpu * orig_count
    mem_util = mem_util if mem_util is not None else 0
    cpu_util = cpu_util if cpu_util is not None else 0

    actual_mem_used = orig_total_mem * mem_util / 100
    actual_cpu_used = orig_total_cpu * cpu_util / 100
    mrs_total_mem = sum(n.get('total_memory_gb', 0) for n in master_nodes)
    mrs_total_cpu = sum(n.get('total_vcpu', 0) for n in master_nodes)
    mrs_per_node_mem = min(n.get('memory_gb', 0) for n in master_nodes)
    mrs_count = sum(n.get('count', 0) for n in master_nodes)

    risks = []
    if mrs_total_mem < actual_mem_used:
        risks.append('内存严重不足')
    elif mrs_total_mem < orig_total_mem:
        risks.append('总内存低于原集群')
    if mrs_per_node_mem < orig_per_node_mem * 0.75:
        risks.append('单节点内存低于原75%')
    if mrs_total_cpu < orig_total_cpu:
        risks.append('总CPU低于原集群')

    base = (f"原集群{orig_count}节点×{orig_per_node_mem:.0f}G(利用率{mem_util:g}%)/ "
            f"{orig_per_node_vcpu:.0f}核(利用率{cpu_util:g}%): 实用内存{actual_mem_used:.0f}G、"
            f"CPU{actual_cpu_used:.1f}核; MRS管控{mrs_count}节点 总内存{mrs_total_mem}G/"
            f"单节点{mrs_per_node_mem}G/总CPU{mrs_total_cpu}核")
    if risks:
        return f"⚠ 规格不足风险({', '.join(risks)}): {base}"
    return f"✓ 通过: {base}"


def generate_mrs_excel_report(report_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate MRS Cluster Sizing Report as multi-sheet Excel file.
    Single plan output (minimum surplus); no dual-plan comparison; no user selection needed.

    Args:
        report_data: dict with keys: source_cluster, plan_a (single plan),
                     recommendation_reason, obs_storage, decisions
        output_path: file path to save, default: MRS_Cluster_Sizing_Report_<date>.xlsx

    Returns:
        Path to the saved Excel file.
    """
    wb = openpyxl.Workbook()

    # Define styles
    header_font = Font(name='微软雅黑', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    cell_align = Alignment(vertical='top', wrap_text=True)
    plan_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')  # 浅绿(最终方案)
    total_font = Font(name='微软雅黑', bold=True)
    total_fill = PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    plan_a = report_data.get('plan_a', {})
    recommendation_reason = report_data.get('recommendation_reason', '')

    # =====================================================
    # Sheet 1: 集群规格推荐 (单方案)
    # =====================================================
    ws1 = wb.active
    ws1.title = '集群规格推荐'

    # Section A1:E2 = 单方案摘要
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

    # Section 2: 最终方案详细规格表 (A6开始)
    headers = ['节点组', '机型规格', 'vCPU', '内存(GB)', '系统盘',
               '数据盘规格(Shuffle)', 'Shuffle单盘', '盘块数', 'Shuffle总量(GB)',
               '节点数量', '总vCPU', '总内存GB', '总Shuffle TB', '推荐理由',
               'Q14校验(Master利用率)']
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=6, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # 写入最终方案的节点详情 (auto-enrich missing fields)
    raw_nodes = [_enrich_node_detail(n) for n in plan_a.get('nodes_detail', [])]
    master_nodes = [n for n in raw_nodes if 'master' in n.get('group', '').lower()]
    q14_note = _build_q14_note(report_data, master_nodes)
    row_idx = 7
    for node in raw_nodes:
        _is_master = 'master' in node.get('group', '').lower()
        ws1.cell(row=row_idx, column=1, value=node.get('group', ''))
        ws1.cell(row=row_idx, column=2, value=node.get('flavor', ''))
        ws1.cell(row=row_idx, column=3, value=node.get('vcpu', ''))
        ws1.cell(row=row_idx, column=4, value=node.get('memory_gb', ''))
        ws1.cell(row=row_idx, column=5, value=node.get('system_disk', '480GB 高IO'))
        ws1.cell(row=row_idx, column=6, value=node.get('data_disk', '600GB 通用SSD'))
        ws1.cell(row=row_idx, column=7, value=f"{node.get('disk_size_gb', 600)}GB 通用SSD")
        ws1.cell(row=row_idx, column=8, value=node.get('disk_count', ''))
        ws1.cell(row=row_idx, column=9, value=node.get('shuffle_capacity_gb', ''))
        ws1.cell(row=row_idx, column=10, value=node.get('count', ''))
        ws1.cell(row=row_idx, column=11, value=node.get('total_vcpu', ''))
        ws1.cell(row=row_idx, column=12, value=node.get('total_memory_gb', ''))
        ws1.cell(row=row_idx, column=13, value=node.get('total_shuffle_tb', ''))
        ws1.cell(row=row_idx, column=14, value=node.get('reason', ''))
        if _is_master and q14_note != '-':
            ws1.cell(row=row_idx, column=15, value=q14_note)
        row_idx += 1

    # =====================================================
    # Sheet 2: 资源对比 (单方案)
    # =====================================================
    ws2 = wb.create_sheet('资源对比')
    _elastic = report_data.get('elastic_task', {}).get('enabled', False)
    _elastic_load = report_data.get('elastic_task', {}).get('daily_load_pct', 40)
    res_headers = ['资源项', '原集群配置',
                   f'Core {_elastic_load}%日负载' if _elastic else 'Core节点(全量)',
                   f'Task {100 - _elastic_load}%+缓冲' if _elastic else 'Task节点(无弹性)',
                   '总量目标(含缓冲)', 'MRS推荐配置', '增长百分比', '是否满足', '说明']
    for col, header in enumerate(res_headers, 1):
        cell = ws2.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # 从report_data提取数据
    src = report_data.get('source_cluster', {})
    tgt = report_data.get('target', {})

    # 计算最终方案的总资源(仅Core+Task计算节点,不含Master管控和OBS存储)
    rec_total_vcpu = 0
    rec_total_mem = 0
    rec_total_shuffle_tb = 0.0
    rec_total_nodes = 0
    compute_groups = {'Core', 'Task'}  # 仅统计计算节点
    for node in plan_a.get('nodes_detail', []):
        group_name = node.get('group', '')
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

    src_cores = src.get('total_cores', 0)
    src_mem = src.get('total_memory_gb', 0)
    src_hdfs = src.get('hdfs_capacity_tb', 0)
    replicas = src.get('hdfs_replicas', 3)
    core_cores = tgt.get('core_cores', 0)
    core_mem = tgt.get('core_memory_gb', 0)
    task_cores = tgt.get('task_cores', 0)
    task_mem = tgt.get('task_memory_gb', 0)
    total_cores = tgt.get('total_with_buffer_cores', 0)
    total_mem = tgt.get('total_with_buffer_memory_gb', 0)
    _obs = report_data.get('obs_storage', {})
    obs_actual = _obs.get('actual_capacity_tb', _obs.get('single_replica_tb', 0))

    # 增长百分比计算
    vcpu_growth = f"+{(rec_total_vcpu - src_cores) / src_cores * 100:.1f}%" if src_cores else "-"
    mem_growth = f"+{(rec_total_mem - src_mem) / src_mem * 100:.1f}%" if src_mem else "-"
    obs_growth = f"-{(1 - obs_actual / src_hdfs) * 100:.1f}%" if src_hdfs else "-"

    _task_count = 0
    _master_count = 0
    for _n in plan_a.get('nodes_detail', []):
        if _n.get('group') == 'Task':
            _task_count = _n.get('count', 0)
        elif 'master' in _n.get('group', '').lower():
            _master_count = _n.get('count', 0)
    _vcpu_note = (f'Core=原集群×{_elastic_load}%无缓冲;Task=总量-Core含缓冲' if _elastic
                  else 'Core=原集群全量匹配,无弹性Task,无缓冲')
    if _elastic:
        _mem_note = '内存超出因1:4单规格约束'
    elif src_mem and rec_total_mem == src_mem:
        _mem_note = '与原集群内存规格完全一致,无额外内存冗余'
    elif src_mem and rec_total_mem > src_mem:
        _mem_note = f'内存超出{(rec_total_mem - src_mem) / src_mem * 100:.1f}%因单规格粒度约束'
    else:
        _mem_note = '内存按最小冗余方案匹配'
    _shuffle_note = 'Core+Task数据盘用于Shuffle' if _elastic else 'Core数据盘用于Shuffle'
    _node_desc = f"{_master_count or 5} Master+{plan_a.get('core_count', '')} Core"
    if _elastic and _task_count:
        _node_desc += f"+{_task_count} Task"
    res_rows = [
        ('总vCPU', src_cores, core_cores, task_cores, total_cores, rec_total_vcpu, vcpu_growth, '✓',
         _vcpu_note),
        ('总内存(GB)', src_mem, core_mem, task_mem, total_mem, rec_total_mem, mem_growth, '✓',
         _mem_note),
        ('总Shuffle存储(TB)', 'N/A', '-', '-', 'N/A', f"{rec_total_shuffle_tb:.1f}", '-', '-',
         _shuffle_note),
        ('OBS存储(TB)', f"{src_hdfs}({replicas}副本)", '-', '-', f"{obs_actual}(实际容量)", obs_actual, obs_growth, '✓',
         f"{src_hdfs}÷{replicas}，OBS容量按实际所需存储直接给出（不取套餐包）"),
        ('节点数', '-', '-', '-', '-', plan_a.get('total_nodes', rec_total_nodes), '-', '-',
         _node_desc),
    ]
    for row_idx, row_data in enumerate(res_rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = cell_align
            cell.border = thin_border
            # 增长百分比列绿色/红色
            if col_idx == 7 and isinstance(value, str) and value.startswith('+'):
                cell.font = Font(name='微软雅黑', color='008000')
            elif col_idx == 7 and isinstance(value, str) and value.startswith('-'):
                cell.font = Font(name='微软雅黑', color='FF0000')
            # 是否满足列绿色✓
            if col_idx == 8 and value == '✓':
                cell.font = Font(name='微软雅黑', color='008000', bold=True)

    # =====================================================
    # Sheet 3: 选型决策理由
    # =====================================================
    ws3 = wb.create_sheet('选型决策理由')
    dec_headers = ['决策项', '候选方案', '最终选择', '选择理由', '淘汰原因']
    for col, header in enumerate(dec_headers, 1):
        cell = ws3.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    for row_idx, decision in enumerate(report_data.get('decisions', []), 2):
        ws3.cell(row=row_idx, column=1, value=decision.get('point', ''))
        ws3.cell(row=row_idx, column=2, value=decision.get('candidates', ''))
        ws3.cell(row=row_idx, column=3, value=decision.get('selected', ''))
        ws3.cell(row=row_idx, column=4, value=decision.get('reasoning', ''))
        ws3.cell(row=row_idx, column=5, value=decision.get('rejected', ''))

    # =====================================================
    # Sheet 4: OBS存储规格
    # =====================================================
    ws4 = wb.create_sheet('OBS存储规格')
    obs_headers = ['计算项', '原始值', '计算逻辑', '结果', '说明']
    for col, header in enumerate(obs_headers, 1):
        cell = ws4.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill

    obs = report_data.get('obs_storage', {})
    _src = report_data.get('source_cluster', {})
    _hdfs_tb = _src.get('hdfs_capacity_tb', '')
    _daily_gb = _src.get('daily_increment_gb', '')
    _retention = _src.get('retention_days', '')
    _full_tb = _src.get('full_data_volume_tb', _hdfs_tb)
    _actual_cap = obs.get('actual_capacity_tb', obs.get('single_replica_tb', ''))
    obs_rows = [
        ('数据源类型', f'HDFS({replicas}副本)', '-', '-', '用户CDH集群HDFS数据'),
        ('HDFS存量数据量', f"{_hdfs_tb} TB", '-', f"{_hdfs_tb} TB", f'{replicas}副本总容量'),
        ('日增量数据', f"{_daily_gb} GB/天", '-', f"{_daily_gb} GB/天", '每日增量数据量'),
        ('数据保存周期', f"{_retention} 天", '-', f"{_retention} 天", '数据保存周期'),
        ('全量数据量', f"{_full_tb} TB", '存量 + 日增量×保存周期', f"{_full_tb} TB", '核数/内存/存储均按全量数据量计算'),
        ('副本数', f"{replicas}", '-', f"{replicas}", 'HDFS副本数'),
        ('实际所需容量(单副本)', '-', f"{_hdfs_tb} / {replicas}", f"{_actual_cap} TB", 'OBS仅存储单副本，即实际所需存储'),
        ('OBS容量', '-', '直接采用实际所需存储', f"{_actual_cap} TB", '不取套餐包，按实际所需存储直接给出'),
        ('OBS存储类型', '-', '标准存储', f"{_actual_cap} TB", '频繁访问数据'),
    ]
    for row_idx, (item, orig, logic, result, note) in enumerate(obs_rows, 2):
        ws4.cell(row=row_idx, column=1, value=item)
        ws4.cell(row=row_idx, column=2, value=orig)
        ws4.cell(row=row_idx, column=3, value=logic)
        ws4.cell(row=row_idx, column=4, value=result)
        ws4.cell(row=row_idx, column=5, value=note)

    # Auto-fit column widths
    for ws in [ws1, ws2, ws3, ws4]:
        for col in range(1, ws.max_column + 1):
            max_len = 0
            for row in range(1, ws.max_row + 1):
                val = ws.cell(row=row, column=col).value
                if val:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[get_column_letter(col)].width = min(max_len + 4, 50)
        ws.freeze_panes = 'A2'

    # Save
    if output_path is None:
        output_path = f"MRS_Cluster_Sizing_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb.save(output_path)
    return output_path


if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description='MRS Cluster Sizing Report Generator (single plan, minimal excess)')
    parser.add_argument('--input', '-i', type=str, default=None,
                        help='Path to report.json file with sizing data from Phase 1-4 investigation. '
                             'If not provided, runs built-in demo data.')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output Excel file path. '
                             'Default: MRS_Cluster_Sizing_Report_<YYYYMMDD>.xlsx')
    args = parser.parse_args()

    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        print(f"已加载调研数据: {args.input}")
    else:
        # Example usage with CDH migration data (single plan, minimal excess)
        report_data = {
        "source_cluster": {
            "total_cores": 1480, "total_memory_gb": 4380,
            "node_count": 30,
            "master_node_count": 3, "master_node_memory_gb": 128, "master_node_vcpu": 32,
            "master_mem_utilization_pct": 45, "master_cpu_utilization_pct": 30,
            "hdfs_capacity_tb": 560, "hdfs_replicas": 3,
            "daily_increment_gb": 500, "retention_days": 365,
            "full_data_volume_tb": 560
        },
        "elastic_task": {"enabled": False, "runtime_hours": 0, "runtime_hours_month": 0},
        "plan_a": {
            "name": "最小冗余方案 — ac9.32xlarge.4 × 12",
            "core_flavor": "ac9.32xlarge.4 (128C/512G)", "core_count": 12,
            "core_total_vcpu": 1536, "core_total_mem_gb": 6144,
            "core_data_disk_count": 8, "core_data_disk_size_gb": 640,
            "core_fault_impact": "-8.3% vCPU",
            "hdfs_datanodes": 12,
            "nodes_detail": [
                {"group": "Master", "flavor": "ac9.8xlarge.4 (32C/128G)", "count": 5, "reason": "14 Core≤20→16核基线; OBS需128GB→升级32核; 1480核≥100→5节点"},
                {"group": "Core", "flavor": "ac9.32xlarge.4 (128C/512G)", "count": 12, "reason": "1:4均衡; 12×128=1536C(+3.8%); 12×512=6144G(+40.2%); 总冗余44%最低; shuffle 128×40=5120GB→8×640GB"}
            ]
        },
        "recommendation_reason": "ac9.32xlarge.4×12: CPU+3.8%+内存+40.2%=总冗余44.0%; vs ac9.32xlarge.2×18: CPU+55.7%+内存+5.2%=总冗余60.9%; 选Total_excess最小的方案",
        "obs_storage": {
            "actual_capacity_tb": 187, "single_replica_tb": 187
        },
        "decisions": [
            {"point": "Core规格选择(最小冗余)", "candidates": "ac9.32xl.4×12(冗余44.0%) / ac9.32xl.2×18(冗余60.9%) / ac9.16xl.4×24(冗余44.0%但更多节点)",
             "selected": "ac9.32xlarge.4 × 12 (最小冗余方案)",
             "reasoning": "CPU+3.8%+内存+40.2%=总冗余44.0%最低; vs 1:2方案总冗余60.9%; vs 64C规格冗余相同但节点翻倍",
             "rejected": "ac9.32xl.2×18: CPU+55.7%内存浪费严重; ac9.16xl.4×24: 冗余相同但24节点系统盘/管理费更高"}
        ]
        }
        print("未指定 --input,使用内置演示数据(1480核 CDH迁移)")

    output = generate_mrs_excel_report(report_data, output_path=args.output)
    print(f"Excel报告已生成: {output}")
