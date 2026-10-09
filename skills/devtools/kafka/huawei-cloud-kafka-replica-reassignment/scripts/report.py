#!/usr/bin/env python3
"""
Report generator: produce an HTML report summarizing the full pipeline.

Includes: parameters used, per-stage validation results, allocation stats,
degradation events, disk usage distribution, JSON file inventory.
"""

import json
import os
from datetime import datetime


def generate_report(stage1_result, stage2_result, stage3_result, validation_results, params, output_path):
    """Generate HTML report."""

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Build validation table rows
    val_rows = ''
    for stage_name, stage_val in validation_results.items():
        stage_label = {'stage1': '阶段一', 'stage2': '阶段二', 'stage3': '阶段三'}.get(stage_name, stage_name)
        status_class = 'pass' if stage_val.get('pass') else 'fail'
        val_rows += f'''
        <tr>
            <td>{stage_label}</td>
            <td class="{status_class}">{'PASS' if stage_val.get('pass') else 'FAIL'}</td>
            <td><pre>{stage_val.get('summary', '')}</pre></td>
        </tr>'''

    # Build degradation section
    deg_events = stage1_result.get('degradation_events', [])
    deg_html = ''
    if deg_events:
        deg_html = '<div class="section"><h3>⚠️ 降级事件</h3><table><tr><th>事件</th></tr>'
        for evt in deg_events:
            deg_html += f'<tr><td class="warn">{evt}</td></tr>'
        deg_html += '</table></div>'
    else:
        deg_html = '<div class="section"><h3>降级事件</h3><p class="pass">无降级，所有副本均满足 L0 级别（不同 broker）</p></div>'

    # Build JSON file inventory
    json_files = stage3_result.get('file_groups', [])
    json_html = '<table><tr><th>文件名</th><th>分区数</th></tr>'
    for jf in json_files:
        json_html += f'<tr><td>{jf["filename"]}</td><td>{jf["partition_count"]}</td></tr>'
    json_html += '</table>'

    # Stats
    s1_stats = stage1_result.get('stats', {})
    s2_stats = stage2_result.get('stats', {})
    s3_stats = stage3_result.get('stats', {})

    # Disk usage distribution
    broker_path = stage1_result.get('outputs', [''])[2] if len(stage1_result.get('outputs', [])) > 2 else ''
    disk_html = '<p>详见 broker_updated.xlsx</p>'
    try:
        import openpyxl
        if broker_path and os.path.exists(broker_path):
            wb = openpyxl.load_workbook(broker_path, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            disk_html = '<table><tr><th>Broker ID</th><th>挂载点</th><th>已使用(GB)</th><th>磁盘大小(GB)</th><th>使用率</th></tr>'
            for row in rows[1:]:
                if row and row[0]:
                    usage = row[7]
                    usage_class = 'pass'
                    try:
                        usage_val = float(str(usage).replace('%', ''))
                        if usage_val > params.get('disk_threshold', 70):
                            usage_class = 'fail'
                        elif usage_val > params.get('disk_threshold', 70) - 5:
                            usage_class = 'warn'
                    except (ValueError, TypeError):
                        pass
                    disk_html += f'<tr><td>{row[0]}</td><td>{row[4]}</td><td>{row[5]}</td><td>{row[6]}</td><td class="{usage_class}">{usage}</td></tr>'
            disk_html += '</table>'
    except Exception:
        pass

    # Overall status
    all_pass = all(v.get('pass') for v in validation_results.values())
    overall_status = '✅ 全部通过' if all_pass else '❌ 存在失败项'
    overall_class = 'pass' if all_pass else 'fail'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kafka 副本扩容复核报告</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background: #f5f5f5; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #2c3e50; margin-top: 30px; }}
        h3 {{ color: #34495e; }}
        .section {{ margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 5px; border-left: 4px solid #3498db; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th {{ background: #3498db; color: white; padding: 8px 12px; text-align: left; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #ddd; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .pass {{ color: #27ae60; font-weight: bold; }}
        .fail {{ color: #e74c3c; font-weight: bold; }}
        .warn {{ color: #f39c12; font-weight: bold; }}
        .status-banner {{ padding: 15px 20px; border-radius: 5px; margin: 20px 0; text-align: center; font-size: 18px; font-weight: bold; }}
        .status-banner.{overall_class} {{ background: {'#d4edda' if all_pass else '#f8d7da'}; color: {'#155724' if all_pass else '#721c24'}; border: 1px solid {'#c3e6cb' if all_pass else '#f5c6cb'}; }}
        pre {{ white-space: pre-wrap; font-size: 13px; background: #f4f4f4; padding: 10px; border-radius: 3px; overflow-x: auto; }}
        .params {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; }}
        .param-item {{ padding: 10px; background: #ecf0f1; border-radius: 4px; }}
        .param-label {{ color: #7f8c8d; font-size: 12px; }}
        .param-value {{ font-size: 16px; font-weight: bold; color: #2c3e50; }}
        .footer {{ margin-top: 40px; padding-top: 15px; border-top: 1px solid #ddd; color: #95a5a6; font-size: 12px; text-align: center; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Kafka 副本扩容复核报告</h1>
    <p>生成时间：{timestamp}</p>

    <div class="status-banner {overall_class}">
        {overall_status}
    </div>

    <h2>📋 参数摘要</h2>
    <div class="params">
        <div class="param-item">
            <div class="param-label">目标副本数</div>
            <div class="param-value">{params.get('replica_count', 2)}</div>
        </div>
        <div class="param-item">
            <div class="param-label">磁盘使用率阈值</div>
            <div class="param-value">{params.get('disk_threshold', 70)}%</div>
        </div>
        <div class="param-item">
            <div class="param-label">JSON 拆分策略</div>
            <div class="param-value">{params.get('json_strategy', 'size_10g')}</div>
        </div>
        <div class="param-item">
            <div class="param-label">策略参数</div>
            <div class="param-value">{params.get('json_strategy_param', 10)}</div>
        </div>
    </div>

    <h2>✅ 各阶段校验结果</h2>
    <table>
        <tr><th>阶段</th><th>状态</th><th>详情</th></tr>
        {val_rows}
    </table>

    <h2>📊 阶段一：分配统计</h2>
    <div class="section">
        <table>
            <tr><th>指标</th><th>值</th></tr>
            <tr><td>处理的 topic 数</td><td>{s1_stats.get('topics_processed', 0)}</td></tr>
            <tr><td>分区总数</td><td>{s1_stats.get('partitions_total', 0)}</td></tr>
            <tr><td>新增副本数</td><td>{s1_stats.get('new_replicas_assigned', 0)}</td></tr>
            <tr><td>最大磁盘使用率</td><td class="{'fail' if s1_stats.get('max_disk_usage', 0) > params.get('disk_threshold', 70) else 'pass'}">{s1_stats.get('max_disk_usage', 0)}%</td></tr>
            <tr><td>Broker 分区均衡</td><td>max={s1_stats.get('broker_partition_balance', {}).get('max', 0)}, min={s1_stats.get('broker_partition_balance', {}).get('min', 0)}, diff={s1_stats.get('broker_partition_balance', {}).get('diff', 0)}</td></tr>
            <tr><td>降级事件数</td><td class="{'warn' if stage1_result.get('degradation_count', 0) > 0 else 'pass'}">{stage1_result.get('degradation_count', 0)}</td></tr>
        </table>
    </div>

    {deg_html}

    <h2>📊 阶段二：合并统计</h2>
    <div class="section">
        <table>
            <tr><th>指标</th><th>值</th></tr>
            <tr><td>原始行数</td><td>{s2_stats.get('main_rows', 0)}</td></tr>
            <tr><td>新增行数</td><td>{s2_stats.get('new_rows', 0)}</td></tr>
            <tr><td>合并行数</td><td>{s2_stats.get('merged_rows', 0)}</td></tr>
            <tr><td>topic 数量</td><td>{s2_stats.get('topic_count', 0)}</td></tr>
        </table>
    </div>

    <h2>📊 阶段三：JSON 文件清单</h2>
    <div class="section">
        <table>
            <tr><th>指标</th><th>值</th></tr>
            <tr><td>JSON 条目总数</td><td>{s3_stats.get('total_entries', 0)}</td></tr>
            <tr><td>生成文件数</td><td>{s3_stats.get('files_generated', 0)}</td></tr>
            <tr><td>校验通过</td><td class="pass">{s3_stats.get('validation_pass', 0)}</td></tr>
            <tr><td>校验失败</td><td class="{'fail' if s3_stats.get('validation_fail', 0) > 0 else 'pass'}">{s3_stats.get('validation_fail', 0)}</td></tr>
        </table>
        {json_html}
    </div>

    <h2>💾 磁盘使用率分布</h2>
    <div class="section">
        {disk_html}
    </div>

    <h2>📁 输出文件</h2>
    <div class="section">
        <h3>阶段一</h3>
        <ul>
            {''.join(f'<li>{f}</li>' for f in stage1_result.get('outputs', []))}
        </ul>
        <h3>阶段二</h3>
        <ul>
            {''.join(f'<li>{f}</li>' for f in stage2_result.get('outputs', []))}
        </ul>
        <h3>阶段三</h3>
        <ul>
            {''.join(f'<li>{f}</li>' for f in stage3_result.get('outputs', []))}
        </ul>
    </div>

    <div class="footer">
        Generated by kafka-replica-reassignment skill | {timestamp}
    </div>
</div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path
