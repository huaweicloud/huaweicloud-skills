#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HDFS Performance Analyzer.

Extracts omaplugin metrics, slow RPC, audit log request counts, TopUser
operations, and Block Report statistics from local HDFS log files, then
generates 11 HTML trend charts (dark-theme SVG with interactive hover
tooltips and threshold reference lines) plus an analysis summary.

Usage:
    python3 hdfs_perf_analyze.py <log_dir> <time_start> <time_end>
    python3 hdfs_perf_analyze.py "/xxx/log" "2026-06-11 09:00:00" "2026-06-11 12:00:00"

Standard library only (no external dependencies).
"""

import os
import re
import sys
import zipfile

COLORS = [
    '#58a6ff', '#f0883e', '#7ee787', '#d2a8ff', '#f85149', '#79c0ff',
    '#ffa657', '#ff7b72', '#a5d6ff', '#ffc680', '#56d364', '#d2a8ff',
    '#3fb950', '#db61a2', '#e3b341', '#8b949e', '#f778ba', '#a371f7',
    '#57ab5a', '#c69026',
]

INTERACTIVE_JS = """
<script>
(function(){
  var svg=document.querySelector('svg');
  if(!svg)return;
  var tooltip=document.createElementNS('http://www.w3.org/2000/svg','g');
  tooltip.setAttribute('id','tooltip');
  tooltip.style.display='none';
  tooltip.innerHTML='<rect x="0" y="0" width="220" height="60" rx="4" fill="#21262d" stroke="#30363d" stroke-width="1"/><text id="tt-line1" x="10" y="20" fill="#8b949e" font-size="11"></text><text id="tt-line2" x="10" y="38" fill="#c9d1d9" font-size="13" font-weight="bold"></text><text id="tt-line3" x="10" y="54" fill="#8b949e" font-size="11"></text>';
  svg.appendChild(tooltip);
  var circles=svg.querySelectorAll('circle[data-idx]');
  circles.forEach(function(c){
    c.addEventListener('mouseenter',function(e){
      var d=this.dataset;
      document.getElementById('tt-line1').textContent=d.name||'';
      document.getElementById('tt-line2').textContent=d.value||'';
      document.getElementById('tt-line3').textContent=d.time||'';
      var pt=svg.createSVGPoint();pt.x=parseFloat(this.getAttribute('cx'));pt.y=parseFloat(this.getAttribute('cy'));
      var tx=pt.x+10;var ty=pt.y-70;
      if(tx+220>svg.viewBox.baseVal.width)tx=pt.x-230;
      if(ty<0)ty=pt.y+10;
      tooltip.setAttribute('transform','translate('+tx+','+ty+')');
      tooltip.style.display='';
    });
    c.addEventListener('mouseleave',function(){tooltip.style.display='none';});
  });
})();
</script>"""


def fmt_int(v):
    """Format integer with thousands separators (e.g. 142855636 -> '142,855,636')."""
    return f"{int(round(v)):,}"


def fmt_val(v, unit):
    """Format a value with its unit, matching the JS fmtVal helpers."""
    if unit == 'ms':
        return f"{v:.1f} {unit}"
    return f"{fmt_int(v)} {unit}"


def extract_zips(log_dir):
    """Auto-extract *.zip files in log_dir into subdirectories.

    Handles omaplugin*.zip, hadoop-omm-namenode*.zip, hdfs-audit-namenode*.zip.
    If a zip already has a matching extracted directory, it is skipped.

    Entry names are validated against path traversal ("../") before extraction
    to prevent Zip Slip write-outside-target attacks on malicious archives.
    """
    if not os.path.isdir(log_dir):
        return
    for name in os.listdir(log_dir):
        if not name.lower().endswith('.zip'):
            continue
        base = name[:-4]
        target_dir = os.path.join(log_dir, base)
        if os.path.isdir(target_dir):
            continue
        zip_path = os.path.join(log_dir, name)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                root = os.path.realpath(target_dir)
                for info in zf.infolist():
                    dest = os.path.realpath(os.path.join(root, info.filename))
                    if os.path.commonpath([root, dest]) != root:
                        raise ValueError(
                            f'unsafe entry in archive: {info.filename!r}'
                        )
                zf.extractall(root)
            print(f'  Extracted: {name} -> {base}/')
        except (zipfile.BadZipFile, OSError, ValueError) as e:
            print(f'  Skip (extract failed): {name} ({e})')


def list_log_subdirs(log_dir, prefix):
    """List subdirectories of log_dir whose name starts with prefix."""
    result = []
    if not os.path.isdir(log_dir):
        return result
    for name in os.listdir(log_dir):
        full = os.path.join(log_dir, name)
        if name.startswith(prefix) and os.path.isdir(full):
            result.append(full)
    return result


def list_log_files(subdir_path):
    """List *.log files in subdir_path (non-recursive)."""
    result = []
    if not os.path.isdir(subdir_path):
        return result
    for name in os.listdir(subdir_path):
        if name.lower().endswith('.log'):
            result.append(os.path.join(subdir_path, name))
    return result


def extract_omaplugin_data(log_dir, time_start, time_end):
    """Extract omaplugin metrics. Returns dict: key -> list of [ts, value]."""
    print('[1/6] Extracting omaplugin metrics...')
    keys = [
        'nn_rpcprocessingtimeavgtime_client_rt',
        'nn_rpcqueuetimeavgtime_client_rt',
        'nn_pendingdeletionblocks_rt',
        'nn_underreplicatedblocks_rt',
        'nn_excessblocks_rt',
        'nn_blockstotal_rt',
        'nn_io_write_kb',
        'nn_io_read_kb',
    ]
    data = {k: [] for k in keys}

    ts_re = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
    for sub in list_log_subdirs(log_dir, 'omaplugin'):
        for fpath in list_log_files(sub):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        m = ts_re.match(line)
                        if not m:
                            continue
                        ts = m.group(1)
                        if ts < time_start or ts > time_end:
                            continue
                        for k in keys:
                            km = re.search(
                                r'key=' + re.escape(k) + r'\s*,value=([0-9.]+)',
                                line,
                            )
                            if km:
                                data[k].append([ts, float(km.group(1))])
            except OSError:
                pass
    for k in keys:
        data[k].sort(key=lambda p: p[0])
    counts = ', '.join(f'{k}={len(data[k])}' for k in keys)
    print(f'  Extracted: {counts}')
    return data


def extract_slow_rpc(log_dir, time_start, time_end):
    """Extract slow RPC entries from namenode logs."""
    print('[2/6] Extracting slow RPC from namenode logs...')
    slow_rpc = []
    ts_re = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
    cmd_re = re.compile(r'slow rpc call for (\w+) took (\d+)ms')
    for sub in list_log_subdirs(log_dir, 'hadoop-omm-namenode'):
        for fpath in list_log_files(sub):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if 'slow rpc' not in line:
                            continue
                        m = ts_re.match(line)
                        if not m:
                            continue
                        ts = m.group(1)
                        if ts < time_start or ts > time_end:
                            continue
                        cm = cmd_re.search(line)
                        if cm:
                            slow_rpc.append({
                                'ts': ts,
                                'cmd': cm.group(1),
                                'took': int(cm.group(2)),
                                'line': line.rstrip('\n'),
                            })
            except OSError:
                pass
    slow_rpc.sort(key=lambda r: r['took'])
    print(f'  Total slow RPC: {len(slow_rpc)}')
    cmd_count = {}
    for r in slow_rpc:
        cmd_count[r['cmd']] = cmd_count.get(r['cmd'], 0) + 1
    by_type = ', '.join(
        f'{c}:{n}' for c, n in sorted(cmd_count.items(), key=lambda x: -x[1])
    )
    print(f'  By type: {by_type}')
    return slow_rpc


def extract_audit_data(log_dir, time_start, time_end):
    """Extract audit log request counts. Returns {bins, cmd_bins, all_cmds}."""
    print('[3/6] Extracting audit log request counts...')
    bins = {}
    cmd_bins = {}
    all_cmds = set()
    ts_re = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
    cmd_re = re.compile(r'cmd=(\w+)')
    for sub in list_log_subdirs(log_dir, 'hdfs-audit-namenode'):
        for fpath in list_log_files(sub):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if not line.strip():
                            continue
                        m = ts_re.match(line)
                        if not m:
                            continue
                        ts = m.group(1)
                        if ts < time_start or ts > time_end:
                            continue
                        cm = cmd_re.search(line)
                        if not cm:
                            continue
                        cmd = cm.group(1)
                        bin_key = ts[:16]
                        bins[bin_key] = bins.get(bin_key, 0) + 1
                        if bin_key not in cmd_bins:
                            cmd_bins[bin_key] = {}
                        cmd_bins[bin_key][cmd] = cmd_bins[bin_key].get(cmd, 0) + 1
                        all_cmds.add(cmd)
            except OSError:
                pass
    total = sum(bins.values())
    print(f'  Total records: {total}, Bins: {len(bins)}, Cmd types: {len(all_cmds)}')
    return {'bins': bins, 'cmd_bins': cmd_bins, 'all_cmds': all_cmds}


def extract_top_user_ops(log_dir, time_start, time_end):
    """Extract TopUser operation counts from 5min-TopUserOpCounts.log."""
    print('[4/6] Extracting top user operations...')
    top_file = os.path.join(log_dir, '5min-TopUserOpCounts.log')
    if not os.path.isfile(top_file):
        print('  5min-TopUserOpCounts.log not found, skipping')
        return None

    time_slots = []
    all_ops = set()
    all_users = set()
    ts_re = re.compile(r'300s Operation Collecter\s*-\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})')
    op_re = re.compile(r'^(\S+.*?)\s*:\s*total=(\d+)')
    user_re = re.compile(r'^(.+?)=(\d+)\s*$')

    current_ts = None
    current_slot_data = None
    try:
        with open(top_file, 'r', encoding='utf-8', errors='ignore') as fh:
            for line in fh:
                m = ts_re.search(line)
                if m:
                    if current_slot_data and current_slot_data['ops']:
                        time_slots.append(current_slot_data)
                    ts = m.group(1).replace('T', ' ')
                    if time_start <= ts <= time_end:
                        current_ts = ts
                        current_slot_data = {'ts': ts, 'ops': {}}
                    else:
                        current_ts = None
                        current_slot_data = None
                    continue
                if not current_ts or not current_slot_data:
                    continue
                if re.match(r'^={10,}', line.strip()):
                    continue
                om = op_re.match(line)
                if not om:
                    continue
                op = om.group(1).strip()
                total = int(om.group(2))
                current_slot_data['ops'][op] = total
                all_ops.add(op)
                user_parts = line.split(';')
                users = {}
                for part in user_parts[1:]:
                    um = user_re.match(part.strip())
                    if um:
                        users[um.group(1)] = int(um.group(2))
                        all_users.add(um.group(1))
                current_slot_data[op + '_users'] = users
    except OSError:
        pass
    if current_slot_data and current_slot_data['ops']:
        time_slots.append(current_slot_data)
    print(f'  Time slots: {len(time_slots)}, Op types: {len(all_ops)}')
    return {'time_slots': time_slots, 'all_ops': all_ops, 'all_users': all_users}


def extract_block_report(log_dir, time_start, time_end):
    """Extract processReport entries from namenode logs (per-minute aggregation)."""
    print('[5/6] Extracting block report from namenode logs...')
    bins = {}
    ts_re = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
    blocks_re = re.compile(r'blocks:\s*(\d+)')
    proc_re = re.compile(r'processing time:\s*(\d+)\s*msecs')
    for sub in list_log_subdirs(log_dir, 'hadoop-omm-namenode'):
        for fpath in list_log_files(sub):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line in fh:
                        if 'processReport' not in line:
                            continue
                        m = ts_re.match(line)
                        if not m:
                            continue
                        ts = m.group(1)
                        if ts < time_start or ts > time_end:
                            continue
                        bm = blocks_re.search(line)
                        pm = proc_re.search(line)
                        if not bm or not pm:
                            continue
                        blocks = int(bm.group(1))
                        proc_time = int(pm.group(1))
                        bin_key = ts[:16]
                        if bin_key not in bins:
                            bins[bin_key] = {'blocks': 0, 'proc_time': 0, 'count': 0}
                        bins[bin_key]['blocks'] += blocks
                        bins[bin_key]['proc_time'] += proc_time
                        bins[bin_key]['count'] += 1
            except OSError:
                pass
    sorted_keys = sorted(bins.keys())
    result = {
        'timestamps': sorted_keys,
        'blocks': [bins[k]['blocks'] for k in sorted_keys],
        'proc_time': [bins[k]['proc_time'] for k in sorted_keys],
        'count': [bins[k]['count'] for k in sorted_keys],
    }
    total_reports = sum(bins[k]['count'] for k in sorted_keys)
    print(f'  Block report bins: {len(sorted_keys)}, total reports: {total_reports}')
    return result


def build_axis_and_grid(cl, cr, ct, cb, y_min, y_max, y_ticks, timestamps, n, unit):
    """Build SVG Y/X axis lines and labels."""
    cw = cr - cl
    ch = cb - ct
    y_range = y_max - y_min
    y_lines = ''
    for i in range(y_ticks):
        y_val = y_min + (y_range * i / (y_ticks - 1))
        y_pos = cb - (ch * i / (y_ticks - 1))
        if unit == 'ms':
            label = f'{y_val:.1f}'
        elif y_val >= 1000:
            label = fmt_int(y_val)
        else:
            label = str(int(round(y_val)))
        y_lines += (f'<line x1="{cl}" y1="{y_pos:.1f}" x2="{cr}" '
                    f'y2="{y_pos:.1f}" stroke="#30363d" stroke-width="1"/>')
        y_lines += (f'<text x="{cl - 8}" y="{y_pos + 4:.1f}" fill="#8b949e" '
                    f'font-size="11" text-anchor="end">{label}</text>')
    x_lines = ''
    x_tc = min(12, n)
    if x_tc > 1:
        for i in range(x_tc):
            idx = round(i * (n - 1) / (x_tc - 1))
            x_pos = cl + (cw * idx / (n - 1)) if n > 1 else cl
            label = timestamps[idx][11:16]
            x_lines += (f'<line x1="{x_pos:.1f}" y1="{ct}" x2="{x_pos:.1f}" '
                        f'y2="{cb}" stroke="#30363d" stroke-width="1"/>')
            x_lines += (f'<text x="{x_pos:.1f}" y="{cb + 18}" fill="#8b949e" '
                        f'font-size="11" text-anchor="middle">{label}</text>')
    return y_lines, x_lines


def build_path_with_dots(vals, timestamps, cl, cr, ct, cb, y_min, y_max, n, name, color, unit):
    """Build SVG path string and interactive dot circles for a data series."""
    cw = cr - cl
    ch = cb - ct
    y_range = y_max - y_min
    path_d = ''
    dots = ''
    for i in range(n):
        v = vals[i]
        if v is None:
            continue
        x = cl + (cw * i / (n - 1)) if n > 1 else cl
        y = cb - (ch * (v - y_min) / y_range)
        prefix = 'M' if not path_d else 'L'
        path_d += f'{prefix}{x:.1f},{y:.1f} '
        display_val = fmt_val(v, unit)
        dots += (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}" opacity="0" '
            f'data-idx="{i}" data-name="{name}" data-value="{display_val}" '
            f'data-time="{timestamps[i]}" style="cursor:pointer">'
            '<animate attributeName="opacity" from="0" to="1" dur="0.01s" '
            'fill="freeze" begin="mouseover" />'
            '<animate attributeName="r" from="3" to="5" dur="0.01s" '
            'fill="freeze" begin="mouseover" />'
            '<animate attributeName="opacity" from="1" to="0" dur="0.01s" '
            'fill="freeze" begin="mouseout" />'
            '<animate attributeName="r" from="5" to="3" dur="0.01s" '
            'fill="freeze" begin="mouseout" /></circle>'
        )
    return path_d, dots


def gen_metric_chart(key, points, config, out_dir):
    """Generate a single metric trend chart HTML file."""
    if not points:
        print(f'  No data for {key}')
        return
    values = [p[1] for p in points]
    timestamps = [p[0] for p in points]
    min_val = min(values)
    max_val = max(values)
    n = len(points)

    cl, cr, ct, cb = 80, 940, 50, 450
    y_min, y_max = min_val, max_val
    if y_max == y_min:
        y_max = y_min + 1
    y_ticks = 7
    y_lines, x_lines = build_axis_and_grid(
        cl, cr, ct, cb, y_min, y_max, y_ticks, timestamps, n, config['unit']
    )

    threshold_line = ''
    over_stat = ''
    if config.get('threshold'):
        th = config['threshold']
        cw = cr - cl
        ch = cb - ct
        y_range = y_max - y_min
        th_y = cb - (ch * (th - y_min) / y_range)
        if ct <= th_y <= cb:
            threshold_line = (
                f'<line x1="{cl}" y1="{th_y:.1f}" x2="{cr}" y2="{th_y:.1f}" '
                f'stroke="#f85149" stroke-width="1.5" stroke-dasharray="8,4"/>'
            )
            threshold_line += (
                f'<text x="{cr + 5}" y="{th_y + 4:.1f}" fill="#f85149" '
                f'font-size="11">{th}ms</text>'
            )
        over_count = sum(1 for v in values if v > th)
        over_stat = (
            '<div class="stat-box"><div class="label">'
            f'Over {th}ms</div><div class="value value-peak">'
            f'{over_count} / {n}</div></div>'
        )

    path_d, dots = build_path_with_dots(
        values, timestamps, cl, cr, ct, cb, y_min, y_max, n,
        config.get('metric_name', key), config['color'], config['unit'],
    )

    accent = config['accent']
    html = (
        f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{config["title"]}</title>'
        '<style>body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;'
        'margin:20px;padding:0}h2{text-align:center;color:' + accent + ';margin-bottom:5px}'
        'h3{text-align:center;color:#8b949e;font-size:14px;margin-top:0}.container{width:95%;'
        'max-width:1200px;margin:0 auto;background:#161b22;border-radius:8px;padding:20px;'
        'border:1px solid #30363d;overflow-x:auto}.stats{display:flex;justify-content:center;'
        'gap:40px;margin:15px 0;flex-wrap:wrap}.stat-box{background:#21262d;border:1px solid '
        '#30363d;border-radius:6px;padding:10px 20px;text-align:center}.stat-box .label{'
        'color:#8b949e;font-size:12px}.stat-box .value{font-size:20px;font-weight:bold}'
        '.value-peak{color:#d2a8ff}.value-blue{color:' + accent + '}</style></head><body>'
        f'<h2>{config["title"]}</h2><h3>{config["subtitle"]}</h3><div class="stats">'
        '<div class="stat-box"><div class="label">Peak</div><div class="value value-peak">'
        f'{fmt_val(max_val, config["unit"])}</div></div>'
        '<div class="stat-box"><div class="label">Min</div><div class="value value-blue">'
        f'{fmt_val(min_val, config["unit"])}</div></div>{over_stat}</div>'
        '<div class="container"><svg viewBox="0 0 970 520" width="100%" '
        'preserveAspectRatio="xMidYMid meet"><rect width="970" height="520" fill="#161b22"/>'
        f'{y_lines}{x_lines}{threshold_line}'
        f'<path d="{path_d}" fill="none" stroke="{config["color"]}" stroke-width="1.5"/>'
        f'{dots}</svg></div>{INTERACTIVE_JS}</body></html>'
    )
    out_path = os.path.join(out_dir, config['filename'])
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'  Generated: {config["filename"]} ({n} points, peak={fmt_val(max_val, config["unit"])})')


def gen_metric_charts(omaplugin_data, time_start, time_end, out_dir):
    """Generate the 6 standard metric trend charts + the IO chart."""
    print('[6/6] Generating trend charts...')
    ts_label = f'{time_start[:16]} - {time_end[:16]}'
    configs = {
        'nn_rpcprocessingtimeavgtime_client_rt': {
            'title': 'NameNode RPC Processing Time Trend',
            'subtitle': f'nn_rpcprocessingtimeavgtime_client_rt | {ts_label}',
            'unit': 'ms', 'threshold': 100, 'color': '#58a6ff',
            'accent': '#58a6ff', 'filename': 'nn_rpc_processing_trend.html',
            'metric_name': 'RPC Processing Time',
        },
        'nn_rpcqueuetimeavgtime_client_rt': {
            'title': 'NameNode RPC Queue Time Trend',
            'subtitle': f'nn_rpcqueuetimeavgtime_client_rt | {ts_label}',
            'unit': 'ms', 'threshold': 400, 'color': '#58a6ff',
            'accent': '#58a6ff', 'filename': 'nn_rpc_queue_trend.html',
            'metric_name': 'RPC Queue Time',
        },
        'nn_pendingdeletionblocks_rt': {
            'title': 'NameNode Pending Deletion Blocks Trend',
            'subtitle': f'nn_pendingdeletionblocks_rt | {ts_label}',
            'unit': 'blocks', 'threshold': None, 'color': '#f0883e',
            'accent': '#f0883e', 'filename': 'nn_pendingdeletionblocks_trend.html',
            'metric_name': 'Pending Deletion Blocks',
        },
        'nn_underreplicatedblocks_rt': {
            'title': 'NameNode Under Replicated Blocks Trend',
            'subtitle': f'nn_underreplicatedblocks_rt | {ts_label}',
            'unit': 'blocks', 'threshold': None, 'color': '#d2a8ff',
            'accent': '#d2a8ff', 'filename': 'nn_underreplicatedblocks_trend.html',
            'metric_name': 'Under Replicated Blocks',
        },
        'nn_excessblocks_rt': {
            'title': 'NameNode Excess Blocks Trend',
            'subtitle': f'nn_excessblocks_rt | {ts_label}',
            'unit': 'blocks', 'threshold': None, 'color': '#7ee787',
            'accent': '#7ee787', 'filename': 'nn_excessblocks_trend.html',
            'metric_name': 'Excess Blocks',
        },
        'nn_blockstotal_rt': {
            'title': 'NameNode Total Blocks Trend',
            'subtitle': f'nn_blockstotal_rt | {ts_label}',
            'unit': 'blocks', 'threshold': None, 'color': '#79c0ff',
            'accent': '#79c0ff', 'filename': 'nn_blockstotal_trend.html',
            'metric_name': 'Total Blocks',
        },
    }
    for key, config in configs.items():
        gen_metric_chart(key, omaplugin_data[key], config, out_dir)
    gen_io_chart(omaplugin_data, time_start, time_end, out_dir)


def gen_io_chart(omaplugin_data, time_start, time_end, out_dir):
    """Generate the NameNode disk IO read/write combined trend chart."""
    write_data = omaplugin_data.get('nn_io_write_kb', [])
    read_data = omaplugin_data.get('nn_io_read_kb', [])
    if not write_data and not read_data:
        print('  No IO data for chart')
        return

    ts_label = f'{time_start[:16]} - {time_end[:16]}'
    all_ts = set()
    for p in write_data:
        all_ts.add(p[0])
    for p in read_data:
        all_ts.add(p[0])
    sorted_ts = sorted(all_ts)
    n = len(sorted_ts)
    if n == 0:
        return

    write_map = {p[0]: p[1] for p in write_data}
    read_map = {p[0]: p[1] for p in read_data}
    write_vals = [write_map.get(t) for t in sorted_ts]
    read_vals = [read_map.get(t) for t in sorted_ts]

    all_valid = [v for v in write_vals if v is not None] + [v for v in read_vals if v is not None]
    if not all_valid:
        return
    y_min = 0
    y_max = max(all_valid)
    if y_max == 0:
        y_max = 1

    cl, cr, ct, cb = 100, 1300, 60, 560
    y_ticks = 9
    y_lines, x_lines = build_axis_and_grid(
        cl, cr, ct, cb, y_min, y_max, y_ticks, sorted_ts, n, 'KB/s'
    )

    write_path, write_dots = build_path_with_dots(
        write_vals, sorted_ts, cl, cr, ct, cb, y_min, y_max, n,
        'IO Write (KB/s)', '#f0883e', 'KB/s',
    )
    read_path, read_dots = build_path_with_dots(
        read_vals, sorted_ts, cl, cr, ct, cb, y_min, y_max, n,
        'IO Read (KB/s)', '#58a6ff', 'KB/s',
    )

    legend = (
        f'<rect x="{cr + 20}" y="{ct + 5}" width="12" height="12" fill="#f0883e"/>'
        f'<text x="{cr + 38}" y="{ct + 15}" fill="#c9d1d9" font-size="12">nn_io_write_kb</text>'
        f'<rect x="{cr + 20}" y="{ct + 25}" width="12" height="12" fill="#58a6ff"/>'
        f'<text x="{cr + 38}" y="{ct + 35}" fill="#c9d1d9" font-size="12">nn_io_read_kb</text>'
    )

    write_peak = max((v for v in write_vals if v is not None), default=0)
    read_peak = max((v for v in read_vals if v is not None), default=0)

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>NameNode IO Trend</title>'
        '<style>body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;'
        'margin:20px;padding:0}h2{text-align:center;color:#7ee787;margin-bottom:5px}h3{'
        'text-align:center;color:#8b949e;font-size:14px;margin-top:0}.container{width:95%;'
        'max-width:1400px;margin:0 auto;background:#161b22;border-radius:8px;padding:20px;'
        'border:1px solid #30363d;overflow-x:auto}.stats{display:flex;justify-content:center;'
        'gap:40px;margin:15px 0;flex-wrap:wrap}.stat-box{background:#21262d;border:1px solid '
        '#30363d;border-radius:6px;padding:10px 20px;text-align:center}.stat-box .label{'
        'color:#8b949e;font-size:12px}.stat-box .value{font-size:20px;font-weight:bold}'
        '.value-write{color:#f0883e}.value-read{color:#58a6ff}</style></head><body>'
        '<h2>NameNode Disk IO Read/Write Trend</h2>'
        f'<h3>nn_io_write_kb &amp; nn_io_read_kb | {ts_label}</h3><div class="stats">'
        '<div class="stat-box"><div class="label">Write Peak (KB/s)</div>'
        f'<div class="value value-write">{fmt_int(write_peak)}</div></div>'
        '<div class="stat-box"><div class="label">Read Peak (KB/s)</div>'
        f'<div class="value value-read">{fmt_int(read_peak)}</div></div></div>'
        f'<div class="container"><svg viewBox="0 0 {cr + 200} {cb + 80}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet"><rect width="{cr + 200}" height="{cb + 80}" '
        f'fill="#161b22"/>{y_lines}{x_lines}'
        f'<path d="{write_path}" fill="none" stroke="#f0883e" stroke-width="1.5"/>{write_dots}'
        f'<path d="{read_path}" fill="none" stroke="#58a6ff" stroke-width="1.5"/>{read_dots}'
        f'{legend}</svg></div>{INTERACTIVE_JS}</body></html>'
    )
    out_path = os.path.join(out_dir, 'nn_io_trend.html')
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'  Generated: nn_io_trend.html (write={len(write_data)} points, read={len(read_data)} points)')


def gen_topuser_chart(top_user_data, time_start, time_end, out_dir):
    """Generate the TopUser per-operation-type trend chart."""
    if not top_user_data:
        return
    time_slots = top_user_data['time_slots']
    all_ops = top_user_data['all_ops']
    if not time_slots:
        print('  No top user data for charts')
        return

    ts_label = f'{time_start[:16]} - {time_end[:16]}'

    def op_sum(op):
        return sum(t['ops'].get(op, 0) for t in time_slots)

    sorted_ops = sorted(all_ops, key=lambda o: -op_sum(o))

    timestamps = [t['ts'] for t in time_slots]
    n = len(time_slots)
    op_values = {op: [t['ops'].get(op, 0) for t in time_slots] for op in sorted_ops}
    all_vals = [v for vals in op_values.values() for v in vals]
    cl, cr, ct, cb = 100, 1300, 60, 560
    y_min = 0
    y_max = max(all_vals) if all_vals else 0
    if y_max == 0:
        y_max = 1
    y_ticks = 9
    y_lines, x_lines = build_axis_and_grid(
        cl, cr, ct, cb, y_min, y_max, y_ticks, timestamps, n, ''
    )
    paths = ''
    dots_all = ''
    legend = ''
    for ci, op in enumerate(sorted_ops):
        vals = op_values[op]
        color = COLORS[ci % len(COLORS)]
        path_d, dots = build_path_with_dots(
            vals, timestamps, cl, cr, ct, cb, y_min, y_max, n, op, color, '',
        )
        paths += f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        dots_all += dots
        ly = ct + 15 + ci * 18
        legend += (
            f'<rect x="{cr + 20}" y="{ly - 10}" width="12" height="12" fill="{color}"/>'
            f'<text x="{cr + 38}" y="{ly}" fill="#c9d1d9" font-size="12">{op}</text>'
        )
    svg_h = ct + (cb - ct) + 80 + len(sorted_ops) * 18
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<title>NN Top User Op Counts by Type</title>'
        '<style>body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;'
        'margin:20px;padding:0}h2{text-align:center;color:#c9d1d9;margin-bottom:5px}h3{'
        'text-align:center;color:#8b949e;font-size:14px;margin-top:0}.container{width:95%;'
        'max-width:1600px;margin:0 auto;background:#161b22;border-radius:8px;padding:20px;'
        'border:1px solid #30363d;overflow-x:auto}</style></head><body>'
        '<h2>NameNode Top User Op Counts by Type</h2>'
        f'<h3>{ts_label}</h3><div class="container">'
        f'<svg viewBox="0 0 {cr + 200} {svg_h}" width="100%" preserveAspectRatio="xMidYMid meet">'
        f'<rect width="{cr + 200}" height="{svg_h}" fill="#161b22"/>'
        f'{y_lines}{x_lines}{paths}{dots_all}{legend}</svg></div>{INTERACTIVE_JS}</body></html>'
    )
    out_path = os.path.join(out_dir, 'nn_topuser_ops_trend.html')
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'  Generated: nn_topuser_ops_trend.html ({len(sorted_ops)} op types, {n} slots)')


def gen_topuser_all_chart(top_user_data, time_start, time_end, out_dir):
    """Generate the total operations trend chart (sum of all RPC types, excluding 'all')."""
    if not top_user_data:
        return
    time_slots = top_user_data['time_slots']
    all_ops = top_user_data['all_ops']
    if not time_slots:
        print('  No top user all data for charts')
        return

    ts_label = f'{time_start[:16]} - {time_end[:16]}'
    timestamps = [t['ts'] for t in time_slots]
    n = len(time_slots)
    ops_no_all = [op for op in all_ops if op != 'all']

    def slot_sum(t):
        return sum(t['ops'].get(op, 0) for op in ops_no_all)

    total_vals = [slot_sum(t) for t in time_slots]
    if all(v == 0 for v in total_vals):
        print('  No total operation data')
        return

    peak = max(total_vals)
    min_val = min(total_vals)
    cl, cr, ct, cb = 80, 940, 50, 450
    y_min = 0
    y_max = peak if peak != 0 else 1
    y_ticks = 7
    y_lines, x_lines = build_axis_and_grid(
        cl, cr, ct, cb, y_min, y_max, y_ticks, timestamps, n, ''
    )
    path_d, dots = build_path_with_dots(
        total_vals, timestamps, cl, cr, ct, cb, y_min, y_max, n,
        'Total Operations', '#58a6ff', '',
    )
    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<title>NameNode Total Operations Trend</title>'
        '<style>body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;'
        'margin:20px;padding:0}h2{text-align:center;color:#58a6ff;margin-bottom:5px}h3{'
        'text-align:center;color:#8b949e;font-size:14px;margin-top:0}.container{width:95%;'
        'max-width:1200px;margin:0 auto;background:#161b22;border-radius:8px;padding:20px;'
        'border:1px solid #30363d;overflow-x:auto}.stats{display:flex;justify-content:center;'
        'gap:40px;margin:15px 0;flex-wrap:wrap}.stat-box{background:#21262d;border:1px solid '
        '#30363d;border-radius:6px;padding:10px 20px;text-align:center}.stat-box .label{'
        'color:#8b949e;font-size:12px}.stat-box .value{font-size:20px;font-weight:bold}'
        '.value-peak{color:#d2a8ff}.value-blue{color:#58a6ff}</style></head><body>'
        '<h2>NameNode Total Operations Trend</h2>'
        f'<h3>Sum of all RPC types ({len(ops_no_all)} types) | {ts_label}</h3>'
        '<div class="stats"><div class="stat-box"><div class="label">Peak</div>'
        f'<div class="value value-peak">{fmt_int(peak)}</div></div>'
        '<div class="stat-box"><div class="label">Min</div>'
        f'<div class="value value-blue">{fmt_int(min_val)}</div></div></div>'
        '<div class="container"><svg viewBox="0 0 970 520" width="100%" '
        'preserveAspectRatio="xMidYMid meet"><rect width="970" height="520" fill="#161b22"/>'
        f'{y_lines}{x_lines}<path d="{path_d}" fill="none" stroke="#58a6ff" '
        f'stroke-width="1.5"/>{dots}</svg></div>{INTERACTIVE_JS}</body></html>'
    )
    out_path = os.path.join(out_dir, 'nn_topuser_all_trend.html')
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'  Generated: nn_topuser_all_trend.html ({n} slots, {len(ops_no_all)} RPC types summed, peak={fmt_int(peak)})')


def gen_block_report_chart(block_report_data, time_start, time_end, out_dir):
    """Generate the Block Report trend chart (dual Y-axis: blocks + processing time)."""
    if not block_report_data or not block_report_data['timestamps']:
        print('  No block report data for chart')
        return

    ts_label = f'{time_start[:16]} - {time_end[:16]}'
    timestamps = block_report_data['timestamps']
    n = len(timestamps)
    blocks_vals = block_report_data['blocks']
    proc_time_vals = block_report_data['proc_time']

    blocks_max = max(blocks_vals) if blocks_vals else 0
    if blocks_max == 0:
        return
    proc_time_max = max(proc_time_vals) if proc_time_vals else 0
    if proc_time_max == 0:
        return

    cl, cr, ct, cb = 100, 1300, 60, 560
    left_y_min = 0
    left_y_max = blocks_max * 1.1
    right_y_max = proc_time_max * 1.1
    y_ticks = 9
    cw = cr - cl
    ch = cb - ct
    left_range = left_y_max - left_y_min
    right_range = right_y_max

    y_lines = ''
    for i in range(y_ticks):
        left_val = left_y_min + (left_range * i / (y_ticks - 1))
        right_val = right_range * i / (y_ticks - 1)
        y_pos = cb - (ch * i / (y_ticks - 1))
        y_lines += (
            f'<line x1="{cl}" y1="{y_pos:.1f}" x2="{cr}" y2="{y_pos:.1f}" '
            f'stroke="#30363d" stroke-width="1"/>'
        )
        y_lines += (
            f'<text x="{cl - 8}" y="{y_pos + 4:.1f}" fill="#58a6ff" font-size="11" '
            f'text-anchor="end">{fmt_int(left_val)}</text>'
        )
        y_lines += (
            f'<text x="{cr + 8}" y="{y_pos + 4:.1f}" fill="#f0883e" font-size="11">'
            f'{fmt_int(right_val)}</text>'
        )

    x_lines = ''
    x_tc = min(12, n)
    if x_tc > 1:
        for i in range(x_tc):
            idx = round(i * (n - 1) / (x_tc - 1))
            x_pos = cl + (cw * idx / (n - 1)) if n > 1 else cl
            label = timestamps[idx][11:16]
            x_lines += (
                f'<line x1="{x_pos:.1f}" y1="{ct}" x2="{x_pos:.1f}" y2="{cb}" '
                f'stroke="#30363d" stroke-width="1"/>'
            )
            x_lines += (
                f'<text x="{x_pos:.1f}" y="{cb + 18}" fill="#8b949e" font-size="11" '
                f'text-anchor="middle">{label}</text>'
            )

    blocks_path, blocks_dots = build_path_with_dots(
        blocks_vals, timestamps, cl, cr, ct, cb, left_y_min, left_y_max, n,
        'Blocks Sum', '#58a6ff', 'blocks',
    )
    proc_path, proc_dots = build_path_with_dots(
        proc_time_vals, timestamps, cl, cr, ct, cb, 0, right_y_max, n,
        'Processing Time Sum (ms)', '#f0883e', 'ms',
    )

    legend = (
        f'<rect x="{cr + 20}" y="{ct + 5}" width="12" height="12" fill="#58a6ff"/>'
        f'<text x="{cr + 38}" y="{ct + 15}" fill="#c9d1d9" font-size="12">Blocks Sum (left)</text>'
        f'<rect x="{cr + 20}" y="{ct + 25}" width="12" height="12" fill="#f0883e"/>'
        f'<text x="{cr + 38}" y="{ct + 35}" fill="#c9d1d9" font-size="12">Processing Time Sum (right)</text>'
    )

    blocks_peak = max(blocks_vals)
    proc_time_peak = max(proc_time_vals)
    total_reports = sum(block_report_data['count'])

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<title>NameNode Block Report Trend</title>'
        '<style>body{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;'
        'margin:20px;padding:0}h2{text-align:center;color:#7ee787;margin-bottom:5px}h3{'
        'text-align:center;color:#8b949e;font-size:14px;margin-top:0}.container{width:95%;'
        'max-width:1400px;margin:0 auto;background:#161b22;border-radius:8px;padding:20px;'
        'border:1px solid #30363d;overflow-x:auto}.stats{display:flex;justify-content:center;'
        'gap:40px;margin:15px 0;flex-wrap:wrap}.stat-box{background:#21262d;border:1px solid '
        '#30363d;border-radius:6px;padding:10px 20px;text-align:center}.stat-box .label{'
        'color:#8b949e;font-size:12px}.stat-box .value{font-size:20px;font-weight:bold}'
        '.value-blocks{color:#58a6ff}.value-proc{color:#f0883e}</style></head><body>'
        '<h2>NameNode Block Report Trend</h2>'
        f'<h3>processReport | {ts_label}</h3><div class="stats">'
        '<div class="stat-box"><div class="label">Peak Blocks Sum / min</div>'
        f'<div class="value value-blocks">{fmt_int(blocks_peak)}</div></div>'
        '<div class="stat-box"><div class="label">Peak Processing Time Sum / min</div>'
        f'<div class="value value-proc">{fmt_int(proc_time_peak)} ms</div></div>'
        '<div class="stat-box"><div class="label">Total Reports</div>'
        f'<div class="value" style="color:#c9d1d9">{fmt_int(total_reports)}</div></div></div>'
        f'<div class="container"><svg viewBox="0 0 {cr + 200} {cb + 80}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet"><rect width="{cr + 200}" height="{cb + 80}" '
        f'fill="#161b22"/>{y_lines}{x_lines}'
        f'<path d="{blocks_path}" fill="none" stroke="#58a6ff" stroke-width="1.5"/>{blocks_dots}'
        f'<path d="{proc_path}" fill="none" stroke="#f0883e" stroke-width="1.5"/>{proc_dots}'
        f'{legend}</svg></div>{INTERACTIVE_JS}</body></html>'
    )
    out_path = os.path.join(out_dir, 'nn_blockreport_trend.html')
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(html)
    print(f'  Generated: nn_blockreport_trend.html ({n} bins, total reports={fmt_int(total_reports)})')


def gen_summary(omaplugin_data, slow_rpc, audit_data, top_user_data, time_start, time_end, out_dir):
    """Generate the analysis summary (stdout + analysis_summary.txt)."""
    print('\n=== Analysis Summary ===')

    rpc_proc = omaplugin_data.get('nn_rpcprocessingtimeavgtime_client_rt', [])
    rpc_queue = omaplugin_data.get('nn_rpcqueuetimeavgtime_client_rt', [])
    pending_del = omaplugin_data.get('nn_pendingdeletionblocks_rt', [])
    under_rep = omaplugin_data.get('nn_underreplicatedblocks_rt', [])
    excess = omaplugin_data.get('nn_excessblocks_rt', [])
    blocks_total = omaplugin_data.get('nn_blockstotal_rt', [])
    io_write = omaplugin_data.get('nn_io_write_kb', [])
    io_read = omaplugin_data.get('nn_io_read_kb', [])

    if rpc_proc:
        peak = max(p[1] for p in rpc_proc)
        over100 = sum(1 for p in rpc_proc if p[1] > 100)
        print(f'RPC Processing Time: peak={peak:.1f}ms, over 100ms: {over100}/{len(rpc_proc)}')
    if rpc_queue:
        peak = max(p[1] for p in rpc_queue)
        over400 = sum(1 for p in rpc_queue if p[1] > 400)
        print(f'RPC Queue Time: peak={peak:.1f}ms, over 400ms: {over400}/{len(rpc_queue)}')
    if pending_del:
        print(f'Pending Deletion Blocks: peak={fmt_int(max(p[1] for p in pending_del))}')
    if excess:
        print(f'Excess Blocks: peak={fmt_int(max(p[1] for p in excess))}')
    if under_rep:
        print(f'Under Replicated Blocks: peak={fmt_int(max(p[1] for p in under_rep))}')
    if blocks_total:
        print(f'Blocks Total: peak={fmt_int(max(p[1] for p in blocks_total))}')
    if io_write:
        print(f'IO Write: peak={fmt_int(max(p[1] for p in io_write))} KB/s')
    if io_read:
        print(f'IO Read: peak={fmt_int(max(p[1] for p in io_read))} KB/s')

    print(f'\nSlow RPC Total: {len(slow_rpc)}')
    cmd_count = {}
    for r in slow_rpc:
        cmd_count[r['cmd']] = cmd_count.get(r['cmd'], 0) + 1
    for cmd, count in sorted(cmd_count.items(), key=lambda x: -x[1]):
        max_took = max(r['took'] for r in slow_rpc if r['cmd'] == cmd)
        print(f'  {cmd}: {count} times, max took={max_took}ms')

    if slow_rpc:
        top10 = sorted(slow_rpc, key=lambda r: -r['took'])[:10]
        print('\nTop 10 Slow RPC:')
        for r in top10:
            print(f"  [{r['ts']}] {r['cmd']} took {r['took']}ms")

    total_reqs = sum(audit_data['bins'].values())
    print(f'\nTotal Audit Requests: {fmt_int(total_reqs)}')

    print('\n=== Root Cause Analysis ===')
    rpc_queue_peak = max((p[1] for p in rpc_queue), default=0)
    rpc_proc_peak = max((p[1] for p in rpc_proc), default=0)
    pending_del_peak = max((p[1] for p in pending_del), default=0)
    excess_peak = max((p[1] for p in excess), default=0)

    findings = []
    if rpc_queue_peak > 400:
        findings.append(
            f'RPC Queue Time peak={rpc_queue_peak:.1f}ms, far exceeds 400ms threshold'
        )
    if rpc_proc_peak > 100:
        findings.append(
            f'RPC Processing Time peak={rpc_proc_peak:.1f}ms, exceeds 100ms threshold'
        )
    if pending_del_peak > 10000:
        findings.append(
            f'Pending Deletion Blocks peak={fmt_int(pending_del_peak)}, '
            'indicating heavy delete operations'
        )
    if excess_peak > 10000:
        findings.append(
            f'Excess Blocks peak={fmt_int(excess_peak)}, possible Balance operation'
        )
    if slow_rpc:
        if cmd_count:
            top_cmd = sorted(cmd_count.items(), key=lambda x: -x[1])[0]
            findings.append(
                f'Slow RPC dominated by {top_cmd[0]} ({top_cmd[1]} times), '
                'indicating large directory scan operations'
            )

    if not findings:
        print('No obvious performance issues found in the given time range.')
    else:
        for f in findings:
            print(f'- {f}')

    summary_path = os.path.join(out_dir, 'analysis_summary.txt')
    lines = [
        'HDFS Performance Analysis Summary',
        f'Time Range: {time_start} ~ {time_end}',
        '',
        '=== Findings ===',
    ]
    if findings:
        lines += [f'- {f}' for f in findings]
    else:
        lines.append('- No obvious performance issues found in the given time range.')
    lines.append('')
    lines.append('=== Slow RPC Top 10 ===')
    if slow_rpc:
        for r in sorted(slow_rpc, key=lambda r: -r['took'])[:10]:
            lines.append(f"[{r['ts']}] {r['cmd']} took {r['took']}ms")
    else:
        lines.append('None')
    with open(summary_path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(f'\nSummary saved to: {summary_path}')


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print('Usage: python3 hdfs_perf_analyze.py <log_dir> <time_start> <time_end>')
        print('Example: python3 hdfs_perf_analyze.py "D:/logs" "2026-06-11 09:00:00" "2026-06-11 12:00:00"')
        sys.exit(1)

    log_dir = args[0]
    time_start = args[1] if len(args) > 1 else '2026-06-11 00:00:00'
    time_end = args[2] if len(args) > 2 else '2099-12-31 23:59:59'
    out_dir = os.path.join(log_dir, 'trends')
    os.makedirs(out_dir, exist_ok=True)

    print('=== HDFS Performance Analyzer ===')
    print(f'Log dir: {log_dir}')
    print(f'Time range: {time_start} ~ {time_end}')
    print(f'Output dir: {out_dir}')
    print('')

    extract_zips(log_dir)
    omaplugin_data = extract_omaplugin_data(log_dir, time_start, time_end)
    slow_rpc = extract_slow_rpc(log_dir, time_start, time_end)
    audit_data = extract_audit_data(log_dir, time_start, time_end)
    top_user_data = extract_top_user_ops(log_dir, time_start, time_end)
    block_report_data = extract_block_report(log_dir, time_start, time_end)

    gen_metric_charts(omaplugin_data, time_start, time_end, out_dir)
    gen_topuser_chart(top_user_data, time_start, time_end, out_dir)
    gen_topuser_all_chart(top_user_data, time_start, time_end, out_dir)
    gen_block_report_chart(block_report_data, time_start, time_end, out_dir)
    gen_summary(omaplugin_data, slow_rpc, audit_data, top_user_data, time_start, time_end, out_dir)

    print(f'\n=== Done! All charts saved to: {out_dir} ===')


if __name__ == '__main__':
    main()
