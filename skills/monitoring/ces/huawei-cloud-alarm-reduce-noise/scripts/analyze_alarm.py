#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
告警降噪分析脚本
分析华为云AOM告警数据，从两个维度生成降噪优化建议
输出HTML格式的报告

字段语义说明（避免误用）：
- alarm_start_time    : 告警首次触发时间（毫秒时间戳，13位）
- last_occur_time     : 告警最近发生时间（毫秒时间戳，13位）
- original_time       : 告警原始发生时间（毫秒时间戳，13位）
- alarm_trigger_time  : 告警实例累计触发次数（int 小整数，**非时间戳**）
- convert_time        : 数据入库/转换时间
- record_time         : 数据记录时间
时间字段兜底优先级：alarm_start_time -> last_occur_time -> original_time
（绝不能将 alarm_trigger_time 作为时间兜底，会被误用为 Unix 纪元+9 秒）
"""

import json
import argparse
import os
from datetime import datetime, timedelta
from collections import defaultdict
import html
from pathlib import Path
from workspace import WORKSPACE_DIR, MARKING_TABLE_PATH


def get_alarm_timestamp_ms(alarm):
    """获取告警时间戳（毫秒），按 alarm_start_time -> last_occur_time -> original_time 兜底

    注意：alarm_trigger_time 是累计触发次数（int 小整数），不是时间戳，绝不能作为兜底。
    """
    return (
        alarm.get('alarm_start_time')
        or alarm.get('last_occur_time')
        or alarm.get('original_time')
        or 0
    )


ALARM_LEVEL_TO_CES_LEVEL = {
    'CRITICAL': 1,
    'MAJOR': 2,
    'MINOR': 3,
    'INFO': 4,
}

HV_KEY_TO_CES_LEVEL = {
    'critical': 1,
    'major': 2,
    'minor': 3,
    'info': 4,
}


def load_multi_region_data(json_file):
    """加载多区域告警数据

    返回: {region_name: (alarm_history, username, time_range)} 或 None（格式不匹配）
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'alarms' not in data:
        return None

    result = {}
    for region_name, region_data in data['alarms'].items():
        alarm_history = region_data.get('alarm_history', [])
        username = region_data.get('username', region_name)
        time_range = region_data.get('time_range', {})
        result[region_name] = (alarm_history, username, time_range)

    return result


def load_multi_region_rules(input_path):
    """加载多区域CES告警规则

    返回: {region_name: rules_list} 或 None（文件不存在）
    """
    input_dir = os.path.dirname(os.path.abspath(input_path))
    rules_path = os.path.join(input_dir, 'ces_alarm_rules.json')
    if not os.path.exists(rules_path):
        return None

    with open(rules_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _parse_dim_value(dim_value):
    """从 dimValue 字符串（如 'bucket_name=wl-toc-api-req-img-dump-prod'）中解析资源名称。

    支持单个 kv (k=v) 与多个 kv 组合 ('k1=v1,k2=v2')，返回最后一个 v。
    """
    if not dim_value:
        return ''
    parts = [p.strip() for p in dim_value.split(',') if p.strip()]
    if not parts:
        return ''
    last = parts[-1]
    if '=' in last:
        return last.split('=', 1)[1].strip()
    return last


def get_resource_name(alarm):
    """获取告警资源的可读名称。

    优先级：
    1. alarm_resource.resourceName（非空）
    2. 从 alarm_resource.dimValue 解析
    3. 从 alarm_resource.resourceId 解析
    4. 兜底返回 'Unknown'
    """
    ar = alarm.get('alarm_resource') or {}
    rn = ar.get('resourceName')
    if rn:
        return rn
    parsed = _parse_dim_value(ar.get('dimValue', ''))
    if parsed:
        return parsed
    parsed = _parse_dim_value(ar.get('resourceId', ''))
    if parsed:
        return parsed
    return 'Unknown'


def get_metric_name_cn(alarm):
    """从 metric_expression_ch 中解析中文指标名。

    表达式格式: '<中文名> 原始值 <op> <val><unit>'
    返回 '原始值' 之前的中文片段；若解析失败则回退到原 metric_name。
    """
    import re
    expr_ch = alarm.get('metric_expression_ch', '')
    m = re.match(r'^(.+?)\s+原始值\s+', expr_ch)
    return m.group(1) if m else alarm.get('metric_name', '')


def format_ces_expression(alarm):
    """将告警表达式统一格式化为英文CES样式：metric_name operator value [unit]

    优先从 metric_expression_ch 提取 (operator, value, unit) 三元组，
    用英文 metric_name 重建为 CES 风格表达式；
    兜底：清洗 metric_expression 中的 {metric=...:value.last(0)} 包裹；
    最后回退到空串。
    """
    metric_name = alarm.get('metric_name', '').lstrip('#')
    expr_ch = alarm.get('metric_expression_ch', '')
    expr_en = alarm.get('metric_expression', '')

    if expr_ch:
        import re
        m = re.match(r'^(.+?)\s+原始值\s+([><=!]+)\s+(\d+\.?\d*)(.*)$', expr_ch)
        if m:
            op, val, unit = m.group(2), m.group(3), m.group(4).strip()
            parts = [metric_name, op, val]
            if unit:
                parts.append(unit)
            return ' '.join(parts)

    if expr_en:
        import re
        cleaned = re.sub(r'\{metric=([^:]+):value\.last\(0\)\}', r'\1', expr_en)
        return cleaned.strip()

    return ''


def match_ces_expression(alarm, alarm_rules):
    """匹配CES告警表达式

    一、匹配资源ID:
      1. 非ALL_INSTANCE: 优先按 dim 字典逐维度比对 resource_list._id，无 resource_list 时按 namespace+region 匹配
      2. ALL_INSTANCE: service 与 namespace 最后一段比对, region 与 region 比对
    二、匹配告警规则:
      1. metric_name 与 policies[].metric_name
      2. alarm_level 映射为数字后与 policies[].level 比对
    """
    if not alarm_rules:
        return '未匹配'

    resource_id = alarm.get('alarm_resource', {}).get('resourceId', '')
    service = alarm.get('service', '')
    region = alarm.get('region', '')
    metric_name = alarm.get('metric_name', '').lstrip('#')
    alarm_level = alarm.get('alarm_level', '')
    ces_level = ALARM_LEVEL_TO_CES_LEVEL.get(alarm_level)

    raw_data = alarm.get('meta_data', {}).get('rawData', [])
    alarm_ns = raw_data[0].get('ns', '') if raw_data else ''
    alarm_dim = raw_data[0].get('dim', {}) if raw_data else {}

    for rule in alarm_rules:
        rule_type = rule.get('type', '')
        resource_matched = False

        if rule_type != 'ALL_INSTANCE':
            resource_list = rule.get('resource_list', [])
            if resource_list:
                for res in resource_list:
                    if isinstance(res, dict):
                        ids = res.get('_id', [])
                    elif isinstance(res, list):
                        ids = res
                    else:
                        ids = []
                    if alarm_dim:
                        all_dims_match = True
                        for id_item in ids:
                            dim_name = id_item.get('name', '')
                            if dim_name == 'mount_point':
                                continue
                            dim_value = id_item.get('value', '')
                            if alarm_dim.get(dim_name) != dim_value:
                                all_dims_match = False
                                break
                        if all_dims_match and ids:
                            resource_matched = True
                            break
                    else:
                        for id_item in ids:
                            if id_item.get('value', '') == resource_id:
                                resource_matched = True
                                break
                        if resource_matched:
                            break
            else:
                namespace = rule.get('namespace', '')
                ns_service = namespace.split('.')[-1] if '.' in namespace else namespace
                ns_match = (ns_service == service) or (alarm_ns and alarm_ns == namespace)
                if ns_match and rule.get('region', '') == region:
                    resource_matched = True
        elif rule_type == 'ALL_INSTANCE':
            namespace = rule.get('namespace', '')
            ns_service = namespace.split('.')[-1] if '.' in namespace else namespace
            ns_match = (ns_service == service) or (alarm_ns and alarm_ns == namespace)
            if ns_match and rule.get('region', '') == region:
                resource_matched = True

        if not resource_matched:
            continue

        for policy in rule.get('policies', []):
            if policy.get('metric_name', '') != metric_name:
                continue
            if ces_level is not None and policy.get('level') != ces_level:
                hv = policy.get('hierarchical_value', {})
                hv_levels = {HV_KEY_TO_CES_LEVEL.get(k) for k in hv}
                if ces_level not in hv_levels:
                    continue
            expr = '{} {} {} {}'.format(
                policy.get('metric_name', ''),
                policy.get('comparison_operator', ''),
                policy.get('value', ''),
                policy.get('unit', '')
            ).strip()
            return expr

    return '未匹配'


def extract_threshold(expression):
    """从告警表达式中提取阈值"""
    import re
    match = re.search(r'[><]=?\s*(\d+\.?\d*)', expression)
    if match:
        return float(match.group(1))
    return None


def analyze_alarm_rules(alarms):
    """分析告警规则 - 重复规则检测 + 级别抑制建议"""
    results = {
        'duplicate_rules': [],       # 重复告警规则（去重分析输入）
        'level_suppression': [],     # 级别抑制建议（AOM 抑制规则）
    }

    resource_metrics = defaultdict(list)
    for alarm in alarms:
        key = (alarm.get('alarm_resource', {}).get('resourceId'),
               alarm.get('metric_name'))
        resource_metrics[key].append(alarm)

    # 重复告警规则：同一阈值不同级别
    for (resource_id, metric), alarm_list in resource_metrics.items():
        if len(alarm_list) > 1:
            threshold_dict = {}
            for a in alarm_list:
                expr = format_ces_expression(a)
                threshold = extract_threshold(expr)
                level = a.get('alarm_level', '')
                if threshold:
                    key = (threshold, level)
                    if key not in threshold_dict:
                        threshold_dict[key] = {'threshold': threshold, 'level': level, 'alarm': a}

            unique_thresholds = list(threshold_dict.values())
            has_duplicate = False
            for i, t1 in enumerate(unique_thresholds):
                for t2 in unique_thresholds[i+1:]:
                    if t1['threshold'] == t2['threshold'] and t1['level'] != t2['level']:
                        has_duplicate = True
                        break
                if has_duplicate:
                    break

            if has_duplicate:
                resource_type = alarm_list[0].get('alarm_resource', {}).get('resourceType', 'Unknown')
                results['duplicate_rules'].append({
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                    'metric': metric,
                    'rules': unique_thresholds
                })

    # 级别抑制建议（AOM 抑制规则）
    level_counts = defaultdict(int)
    for alarm in alarms:
        level_counts[alarm.get('alarm_level', 'Unknown')] += 1
    total_alarms = len(alarms)
    if total_alarms:
        critical_pct = level_counts.get('CRITICAL', 0) / total_alarms * 100
        if critical_pct > 20:
            results['level_suppression'].append({
                'type': 'level',
                'issue': f'CRITICAL告警占比{critical_pct:.1f}%，超过20%，存在级别稀释风险',
                'suggestion': '建议创建AOM抑制规则：紧急告警触发时抑制次要/提示级别告警',
                'source_condition': '告警级别 = 紧急',
                'suppress_condition': '告警级别 = 次要 OR 告警级别 = 提示',
                'scope': '任意告警分组规则'
            })
        minor_pct = level_counts.get('MINOR', 0) / total_alarms * 100
        if minor_pct > 50:
            results['level_suppression'].append({
                'type': 'level',
                'issue': f'MINOR告警占比{minor_pct:.1f}%，超过50%，告警噪音过大',
                'suggestion': '建议创建AOM抑制规则：重要告警触发时抑制次要级别告警',
                'source_condition': '告警级别 = 重要',
                'suppress_condition': '告警级别 = 次要',
                'scope': '任意告警分组规则'
            })

    return results
def analyze_alarm_suppression(alarms):
    """分析静默规则建议 - 测试环境 + 低优先级（AOM 静默规则）"""
    results = {
        'silence_suggestions': []     # AOM 静默规则建议
    }

    test_keywords = ['test', 'dev', 'debug', 'Demo', 'DEMO']

    # 按资源分组统计
    resource_alarms = defaultdict(list)
    for alarm in alarms:
        resource_name = get_resource_name(alarm)
        resource_alarms[resource_name].append(alarm)

    # 检测测试环境资源 → 静默规则建议
    test_resources = []
    for resource_name, alarm_list in resource_alarms.items():
        for keyword in test_keywords:
            if keyword.lower() in resource_name.lower():
                test_resources.append({
                    'resource': resource_name,
                    'alarm_count': len(alarm_list),
                    'keyword': keyword,
                })
                break

    if test_resources:
        results['silence_suggestions'].append({
            'type': 'test_environment',
            'title': '测试环境静默建议',
            'description': '以下资源可能属于测试环境，建议创建AOM静默规则屏蔽其告警通知',
            'filter_condition': '资源名称正则匹配 test*|dev*|demo*',
            'silence_period': '全天',
            'items': test_resources[:10]
        })

    # 检测低优先级告警 → 静默规则建议
    minor_alarms = []
    for alarm in alarms:
        if alarm.get('alarm_level') == 'MINOR':
            resource_name = get_resource_name(alarm)
            minor_alarms.append({
                'resource': resource_name,
                'metric': alarm.get('metric_name', ''),
                'level': 'MINOR',
            })

    if len(minor_alarms) > 5:
        results['silence_suggestions'].append({
            'type': 'minor_level',
            'title': '低优先级静默建议',
            'description': f'MINOR级别告警共{len(minor_alarms)}条，建议创建AOM静默规则在非工作时间屏蔽',
            'filter_condition': '告警级别 = 次要',
            'silence_period': '非工作时间（如 18:00-08:00）',
            'items': minor_alarms[:10]
        })

    return results
def analyze_alarm_convergence(alarms):
    """分析告警收敛 - 告警风暴识别 + 路由分组建议"""
    results = {
        'alarm_storm': [],           # 告警风暴识别
        'grouping_suggestions': [],  # AOM 路由分组建议
    }

    alarm_counts = defaultdict(int)
    for alarm in alarms:
        key = (alarm.get('alarm_resource', {}).get('resourceId'),
               alarm.get('metric_name'))
        alarm_counts[key] += 1

    for (resource_id, metric), count in alarm_counts.items():
        if count > 30:
            for alarm in alarms:
                if alarm.get('alarm_resource', {}).get('resourceId') == resource_id:
                    resource_name = get_resource_name(alarm)
                    resource_type = alarm.get('alarm_resource', {}).get('resourceType', 'Unknown')
                    results['alarm_storm'].append({
                        'resource': resource_name,
                        'resource_type': resource_type,
                        'metric': metric,
                        'service': alarm.get('service', ''),
                        'trigger_count': count,
                        'severity': 'severe' if count > 100 else 'high',
                    })
                    break

    # 路由分组建议（AOM 分组规则）
    service_counts = defaultdict(int)
    for alarm in alarms:
        service = alarm.get('service', 'Unknown')
        service_counts[service] += 1

    for service, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True):
        if count > 10:
            results['grouping_suggestions'].append({
                'service': service,
                'alarm_count': count,
                'group_condition': f'告警源 = {service}',
                'merge_method': '按告警源 + 严重度',
                'first_wait': '15s',
                'change_wait': '60s',
                'repeat_wait': '5min',
            })

    # 告警风暴分组建议
    for storm in results['alarm_storm']:
        results['grouping_suggestions'].append({
            'service': storm['service'],
            'alarm_count': storm['trigger_count'],
            'group_condition': f"告警源 = {storm['service']} AND 资源类型 = {storm['resource_type']}",
            'merge_method': '按告警源 + 严重度',
            'first_wait': '15s',
            'change_wait': '60s',
            'repeat_wait': '5min',
            'is_storm': True,
            'resource': storm['resource'],
            'metric': storm['metric'],
        })

    return results
def analyze_alarm_correlation(alarms):
    """分析告警关联 - 根因分析 + 抑制规则建议"""
    results = {
        'correlation_analysis': [],     # 根因分析结果
        'suppression_suggestions': [],  # AOM 抑制规则建议
    }

    resource_issues = defaultdict(lambda: defaultdict(int))
    for alarm in alarms:
        resource = get_resource_name(alarm)
        metric = alarm.get('metric_name', '')
        resource_issues[resource][metric] += 1

    for resource, metrics_dict in resource_issues.items():
        unique_count = len(metrics_dict)
        if unique_count > 2:
            sorted_metrics = sorted(metrics_dict.items(), key=lambda x: x[1], reverse=True)
            root_cause = sorted_metrics[0][0]
            derived = [m for m, _ in sorted_metrics[1:]]
            results['correlation_analysis'].append({
                'resource': resource,
                'unique_count': unique_count,
                'total_count': sum(metrics_dict.values()),
                'metrics': sorted_metrics,
                'root_cause': root_cause,
                'derived': derived,
                'suggestion': f'根因可能为{root_cause}，衍生告警: {", ".join(derived[:3])}'
            })

            # 生成 AOM 抑制规则建议
            results['suppression_suggestions'].append({
                'type': 'root_cause',
                'resource': resource,
                'root_cause': root_cause,
                'derived': derived[:3],
                'source_condition': f'告警规则 = {root_cause}',
                'suppress_condition': f'告警规则 = {", ".join(derived[:3])}',
                'scope': '任意告警分组规则',
                'suggestion': f'当{root_cause}触发时，抑制{", ".join(derived[:3])}的告警通知'
            })

    return results
def analyze_top10_alarms(alarms, core_ids=None, alarm_rules=None):
    """分析TOP10告警"""
    from core_resources import is_core_resource
    key_counts = defaultdict(int)
    key_details = {}

    for alarm in alarms:
        resource_id = alarm.get('alarm_resource', {}).get('resourceId', '')
        resource_name = get_resource_name(alarm)
        metric = alarm.get('metric_name', '')
        key = (resource_id, metric)
        key_counts[key] += 1
        if key not in key_details:
            key_details[key] = {
                'resource': resource_name,
                'resource_id': resource_id,
                'resource_type': alarm.get('alarm_resource', {}).get('resourceType', 'Unknown'),
                'metric': metric,
                'metric_cn': get_metric_name_cn(alarm),
                'level': alarm.get('alarm_level', ''),
                'service': alarm.get('service', ''),
                'expression': format_ces_expression(alarm),
                'is_core': is_core_resource(alarm, core_ids) if core_ids else False,
                '_alarm': alarm,
            }

    sorted_items = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    results = []
    for rank, (key, count) in enumerate(sorted_items, 1):
        detail = key_details[key]
        ces_expr = match_ces_expression(detail['_alarm'], alarm_rules) if alarm_rules else '未匹配'
        results.append({
            'rank': rank,
            'resource': detail['resource'],
            'resource_id': detail['resource_id'],
            'resource_type': detail['resource_type'],
            'metric': detail['metric'],
            'metric_cn': detail['metric_cn'],
            'level': detail['level'],
            'service': detail['service'],
            'expression': detail['expression'],
            'count': count,
            'is_core': detail['is_core'],
            'ces_expression': ces_expr,
        })

    return results


UNRESOLVED_LEVELS = [
    ('>90天', 90, 'danger'),
    ('>30天', 30, 'warning'),
    ('>14天', 14, 'info'),
    ('>7天', 7, 'info'),
]


def analyze_unresolved(alarms, end_date_str=None):
    """分析长久未恢复告警"""
    results = {
        'by_level': {},
        'list': [],
        'total_unresolved': 0,
    }

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                end_date = datetime.now()
    else:
        end_date = datetime.now()

    unresolved = []
    for alarm in alarms:
        if alarm.get('recover_time'):
            continue

        start_time_ms = get_alarm_timestamp_ms(alarm)
        if not start_time_ms:
            continue

        start_dt = datetime.fromtimestamp(start_time_ms / 1000)
        duration_days = (end_date - start_dt).days

        if duration_days < 7:
            continue

        resource_name = get_resource_name(alarm)
        resource_type = alarm.get('alarm_resource', {}).get('resourceType', 'Unknown')
        resource_id = alarm.get('alarm_resource', {}).get('resourceId', '')

        level_label = None
        level_class = None
        for label, threshold, cls in UNRESOLVED_LEVELS:
            if duration_days >= threshold:
                level_label = label
                level_class = cls
                break

        if not level_label:
            continue

        results['by_level'][level_label] = results['by_level'].get(level_label, 0) + 1

        unresolved.append({
            'resource': resource_name,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'metric': alarm.get('metric_name', ''),
            'level': alarm.get('alarm_level', ''),
            'service': alarm.get('service', ''),
            'start_time': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_days': duration_days,
            'duration_label': level_label,
            'duration_class': level_class,
            'expression': format_ces_expression(alarm),
        })

    unresolved.sort(key=lambda x: x['duration_days'], reverse=True)
    results['list'] = unresolved
    results['total_unresolved'] = len(unresolved)

    return results


def score_color(score):
    """根据分数返回CSS颜色变量"""
    if score >= 80:
        return 'var(--semi-color-success)'
    elif score >= 60:
        return 'var(--semi-color-primary)'
    elif score >= 40:
        return 'var(--semi-color-warning)'
    else:
        return 'var(--semi-color-danger)'


def calculate_health_score(alarms, convergence_results, unresolved_results, daily_trend):
    """计算健康度评分（0-100），5维加权"""
    total = len(alarms)

    if total <= 50:
        volume = 100
    elif total <= 200:
        volume = 80
    elif total <= 500:
        volume = 60
    elif total <= 1000:
        volume = 40
    else:
        volume = 20

    critical_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'CRITICAL')
    critical_pct = (critical_count / total * 100) if total else 0
    if critical_pct == 0:
        severity = 100
    elif critical_pct <= 5:
        severity = 85
    elif critical_pct <= 10:
        severity = 70
    elif critical_pct <= 20:
        severity = 50
    else:
        severity = 30

    storm_count = len(convergence_results.get('alarm_storm', []))
    convergence = max(0, 100 - storm_count * 10)

    unresolved_count = unresolved_results.get('total_unresolved', 0) if unresolved_results else 0
    if unresolved_count == 0:
        unresolved = 100
    elif unresolved_count <= 3:
        unresolved = 80
    elif unresolved_count <= 10:
        unresolved = 60
    elif unresolved_count <= 20:
        unresolved = 40
    else:
        unresolved = 20

    if daily_trend and len(daily_trend) >= 2:
        recent = daily_trend[-1].get('total', 0)
        previous = daily_trend[-2].get('total', 0)
        if recent < previous:
            trend = 100
        elif recent == previous:
            trend = 70
        else:
            trend = 40
    else:
        trend = 70

    total_score = int(volume * 0.20 + severity * 0.25 + convergence * 0.15 + unresolved * 0.20 + trend * 0.20)

    return {
        'total': total_score,
        'volume': volume,
        'severity': severity,
        'convergence': convergence,
        'unresolved': unresolved,
        'trend': trend,
    }


def analyze_daily_trend(alarms, time_range=None):
    """分析每日告警趋势"""
    daily_data = defaultdict(lambda: {'total': 0, 'active': 0, 'recovered': 0, 'critical': 0, 'major': 0, 'minor': 0, 'hours': defaultdict(int)})

    for alarm in alarms:
        ts = get_alarm_timestamp_ms(alarm)
        if not ts or ts < 1000000000:
            continue
        dt = datetime.fromtimestamp(ts / 1000)
        date_str = dt.strftime('%Y-%m-%d')
        hour = dt.strftime('%H')

        d = daily_data[date_str]
        d['total'] += 1
        d['hours'][hour] += 1

        level = alarm.get('alarm_level', '')
        if level == 'CRITICAL':
            d['critical'] += 1
        elif level == 'MAJOR':
            d['major'] += 1
        elif level == 'MINOR':
            d['minor'] += 1

        if not alarm.get('recover_time'):
            d['active'] += 1
        else:
            d['recovered'] += 1

    if time_range:
        start_str = time_range.get('start', '')[:10]
        end_str = time_range.get('end', '')[:10]
        if start_str and end_str:
            cur = datetime.strptime(start_str, '%Y-%m-%d')
            end = datetime.strptime(end_str, '%Y-%m-%d')
            while cur <= end:
                date_str = cur.strftime('%Y-%m-%d')
                if date_str not in daily_data:
                    daily_data[date_str]
                cur += timedelta(days=1)

    result = []
    for date in sorted(daily_data.keys()):
        d = daily_data[date]
        peak_hour = f"{max(d['hours'].items(), key=lambda x: x[1])[0]}:00" if d['hours'] else '-'
        result.append({
            'date': date,
            'total': d['total'],
            'active': d['active'],
            'recovered': d['recovered'],
            'critical': d['critical'],
            'major': d['major'],
            'minor': d['minor'],
            'peak_hour': peak_hour,
        })

    return result


def analyze_alarm_temporal_correlation(alarms, window_minutes=15, min_windows=2):
    """告警时序关联性分析：基于时间窗的共现分析"""
    sorted_alarms = sorted(alarms, key=lambda a: get_alarm_timestamp_ms(a))

    events = []
    current_event = []
    current_end = 0
    window_ms = window_minutes * 60 * 1000

    for alarm in sorted_alarms:
        ts = get_alarm_timestamp_ms(alarm)
        if not ts or ts < 1000000000:
            continue
        if ts > current_end and current_event:
            events.append(current_event)
            current_event = []
        current_event.append(alarm)
        current_end = ts + window_ms

    if current_event:
        events.append(current_event)

    co_occurrence = defaultdict(lambda: defaultdict(int))

    for event in events:
        signatures = set()
        for alarm in event:
            resource_key = alarm.get('alarm_resource', {}).get('resourceId', '')
            metric = alarm.get('metric_name', '')
            sig = (resource_key, metric)
            signatures.add(sig)

        if len(signatures) >= 2:
            sig_list = list(signatures)
            for i in range(len(sig_list)):
                for j in range(i + 1, len(sig_list)):
                    pair = tuple(sorted([sig_list[i], sig_list[j]]))
                    co_occurrence[pair[0]][pair[1]] += 1

    strong_pairs = []
    for sig_a, targets in co_occurrence.items():
        for sig_b, count in targets.items():
            if count >= min_windows:
                strong_pairs.append((sig_a, sig_b, count))

    parent = {}
    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for sig_a, sig_b, count in strong_pairs:
        union(sig_a, sig_b)

    groups = defaultdict(list)
    for sig_a, sig_b, count in strong_pairs:
        root = find(sig_a)
        groups[root].append((sig_a, sig_b, count))

    result = []
    group_id = 1
    for root, pairs in groups.items():
        members = set()
        total_co = 0
        for sig_a, sig_b, count in pairs:
            members.add(sig_a)
            members.add(sig_b)
            total_co = max(total_co, count)

        member_details = []
        for alarm in sorted_alarms:
            resource_key = alarm.get('alarm_resource', {}).get('resourceId', '')
            metric = alarm.get('metric_name', '')
            sig = (resource_key, metric)
            if sig in members:
                member_details.append({
                    'resource': get_resource_name(alarm),
                    'metric': metric,
                    'service': alarm.get('service', ''),
                })

        seen = set()
        unique_members = []
        for m in member_details:
            key = (m['resource'], m['metric'])
            if key not in seen:
                seen.add(key)
                unique_members.append(m)

        if total_co >= 5:
            strength = 'high'
        elif total_co >= 3:
            strength = 'medium'
        else:
            strength = 'low'

        result.append({
            'group_id': group_id,
            'strength': strength,
            'co_occurrence': total_co,
            'member_count': len(unique_members),
            'members': unique_members[:10],
            'total_alarms': sum(m['count'] for m in unique_members) if unique_members and 'count' in unique_members[0] else len(unique_members),
        })
        group_id += 1

    result.sort(key=lambda x: x['co_occurrence'], reverse=True)
    return {'co_occurrence_groups': result, 'window_minutes': window_minutes, 'min_windows': min_windows}


def build_action_lists(convergence_results, unresolved_results, rule_results,
                     correlation_results, temporal_results, suppression_results=None):
    """构建降噪建议汇总（按 AOM 4 环节分类）"""
    high_actions = []
    medium_actions = []
    low_actions = []

    # === 分组建议（高优先级）===
    for item in convergence_results.get('alarm_storm', [])[:3]:
        high_actions.append({
            'title': f"[路由分组] 处理告警风暴: {item['resource']} - {item['metric']}",
            'desc': f"触发{item['trigger_count']}次，建议创建AOM路由分组规则：分组条件=告警源+资源类型，合并方式=按严重度，首次等待15s/变化等待60s/重复等待5min",
        })

    for item in convergence_results.get('grouping_suggestions', [])[:3]:
        if not item.get('is_storm'):
            high_actions.append({
                'title': f"[路由分组] 高频告警源分组: {item['service']}",
                'desc': f"告警{item['alarm_count']}次，分组条件={item['group_condition']}，合并方式={item['merge_method']}，等待参数={item['first_wait']}/{item['change_wait']}/{item['repeat_wait']}",
            })

    # === 未恢复告警（高优先级）===
    for item in (unresolved_results or {}).get('list', [])[:3]:
        if item.get('duration_days', 0) > 30:
            high_actions.append({
                'title': f"闭环长期告警: {item['resource']} - {item['metric']}",
                'desc': f"已持续{item['duration_days']}天未恢复，需升级处理",
            })

    # === 抑制建议（中优先级）===
    for item in rule_results.get('level_suppression', [])[:2]:
        medium_actions.append({
            'title': f"[抑制规则] 级别抑制: {item.get('source_condition', '')}",
            'desc': f"{item['issue']}，抑制条件={item.get('suppress_condition', '')}，范围={item.get('scope', '')}",
        })

    for item in correlation_results.get('suppression_suggestions', [])[:2]:
        medium_actions.append({
            'title': f"[抑制规则] 根因抑制: {item['resource']}",
            'desc': f"源告警={item.get('source_condition', '')}，抑制={item.get('suppress_condition', '')}，范围={item.get('scope', '')}",
        })

    for item in correlation_results.get('correlation_analysis', [])[:2]:
        medium_actions.append({
            'title': f"配置告警关联: {item['resource']}",
            'desc': f"存在{item['unique_count']}种指标，建议进行根因分析并配置抑制规则",
        })

    for item in (temporal_results or {}).get('co_occurrence_groups', [])[:2]:
        member_names = ', '.join(m['resource'] for m in item['members'][:3])
        medium_actions.append({
            'title': f"排查告警共现: 关联组{item['group_id']}",
            'desc': f"成员: {member_names}，共现{item['co_occurrence']}次",
        })

    # === 去重建议（低优先级）===
    for item in rule_results.get('duplicate_rules', [])[:3]:
        low_actions.append({
            'title': f"[去重] 合并重复规则: {item['metric']}",
            'desc': "存在同一阈值不同级别的规则，AOM内置去重可自动处理；如为CES告警，建议迁移到AOM",
        })

    # === 静默建议（低优先级）===
    if suppression_results:
        for item in suppression_results.get('silence_suggestions', [])[:2]:
            low_actions.append({
                'title': f"[静默规则] {item['title']}",
                'desc': f"过滤条件={item.get('filter_condition', '')}，静默时间段={item.get('silence_period', '')}",
            })

    return {'high': high_actions, 'medium': medium_actions, 'low': low_actions}


def generate_html_report(alarms, username, time_range, rule_results, suppression_results, convergence_results, correlation_results, unresolved_results=None, core_ids=None, health_score=None, daily_trend=None, temporal_correlation=None, action_lists=None, alarm_rules=None):
    """生成HTML报告"""

    html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>告警降噪优化分析报告</title>
    <style>
        :root {{
            --semi-color-primary: #0064FA;
            --semi-color-success: #3BB346;
            --semi-color-warning: #FC8800;
            --semi-color-danger: #F93920;
            --semi-color-bg-0: #FFFFFF;
            --semi-color-bg-1: #FFFFFF;
            --semi-color-text-0: #1C1F23;
            --semi-color-text-1: rgba(28,31,35,0.8);
            --semi-color-text-2: rgba(28,31,35,0.62);
            --semi-color-fill-0: rgba(46,50,56,0.05);
            --semi-color-fill-1: rgba(46,50,56,0.09);
            --semi-color-border: rgba(28,31,35,0.08);
            --semi-border-radius-small: 3px;
            --semi-border-radius-large: 12px;
            --shadow-elevated: 0 4px 14px rgba(0, 0, 0, 0.1);
            --toc-width: 220px;
        }}
        html {{
            scroll-behavior: smooth;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background: var(--semi-color-fill-0);
            color: var(--semi-color-text-0);
            line-height: 1.6;
            font-size: 14px;
        }}
        .toc {{
            position: fixed;
            left: 0;
            top: 0;
            width: var(--toc-width);
            height: 100vh;
            background: var(--semi-color-bg-1);
            border-right: 1px solid var(--semi-color-border);
            padding: 24px 0;
            overflow-y: auto;
            z-index: 100;
        }}
        .toc-title {{
            font-size: 16px;
            font-weight: 600;
            color: var(--semi-color-text-0);
            padding: 0 20px 16px;
            border-bottom: 1px solid var(--semi-color-border);
            margin-bottom: 8px;
        }}
        .toc-list {{
            list-style: none;
        }}
        .toc-item {{
            display: block;
        }}
        .toc-item a {{
            display: block;
            padding: 8px 20px;
            font-size: 14px;
            color: var(--semi-color-text-1);
            text-decoration: none;
            border-left: 3px solid transparent;
            transition: all 0.2s;
        }}
        .toc-item a:hover {{
            background: var(--semi-color-fill-0);
            color: var(--semi-color-primary);
        }}
        .toc-item.active a {{
            color: var(--semi-color-primary);
            border-left-color: var(--semi-color-primary);
            background: var(--semi-color-fill-0);
            font-weight: 600;
        }}
        .toc-sub {{
            list-style: none;
        }}
        .toc-sub a {{
            display: block;
            padding: 6px 20px 6px 36px;
            font-size: 12px;
            color: var(--semi-color-text-2);
            text-decoration: none;
            border-left: 3px solid transparent;
            transition: all 0.2s;
        }}
        .toc-sub a:hover {{
            background: var(--semi-color-fill-0);
            color: var(--semi-color-primary);
        }}
        .toc-sub.active a {{
            color: var(--semi-color-primary);
            border-left-color: var(--semi-color-primary);
            background: var(--semi-color-fill-0);
            font-weight: 600;
        }}
        .content {{
            margin-left: var(--toc-width);
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }}
        .header {{
            background: var(--semi-color-primary);
            color: white;
            padding: 32px;
            border-radius: var(--semi-border-radius-large);
            margin-bottom: 24px;
        }}
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            line-height: 40px;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .card {{
            background: var(--semi-color-bg-1);
            border-radius: var(--semi-border-radius-large);
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid var(--semi-color-border);
            overflow: hidden;
        }}
        .card-header {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--semi-color-primary);
            display: flex;
            align-items: center;
        }}
        .card-header-icon {{
            display: inline-block;
            font-size: 14px;
            line-height: 1;
            margin-left: 8px;
            vertical-align: middle;
            cursor: pointer;
            opacity: 0.65;
            color: var(--semi-color-text-2);
            border-radius: 50%;
            padding: 0 2px;
            position: relative;
        }}
        .card-header-icon:hover {{
            opacity: 1;
            color: var(--semi-color-primary);
            background: var(--semi-color-fill-1);
        }}
        .card-header-icon:hover::after {{
            content: attr(data-tooltip);
            position: absolute;
            left: calc(100% + 10px);
            top: 50%;
            transform: translateY(-50%);
            padding: 8px 12px;
            background: rgba(28, 31, 35, 0.95);
            color: #fff;
            font-size: 12px;
            line-height: 1.5;
            border-radius: 6px;
            width: max-content;
            max-width: 360px;
            white-space: pre-line;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            pointer-events: none;
            z-index: 1000;
        }}
        .card-header-icon:hover::before {{
            content: '';
            position: absolute;
            left: calc(100%);
            top: 50%;
            transform: translateY(-50%);
            border: 5px solid transparent;
            border-right-color: rgba(28, 31, 35, 0.95);
            pointer-events: none;
            z-index: 1000;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
        }}
        .stat-item {{
            background: var(--semi-color-fill-0);
            padding: 20px;
            border-radius: var(--semi-border-radius-small);
            text-align: center;
            transition: background var(--semi-color-fill-1);
        }}
        .stat-item:hover {{
            background: var(--semi-color-fill-1);
        }}
        .stat-item .value {{
            font-size: 32px;
            font-weight: 600;
            color: var(--semi-color-primary);
            line-height: 40px;
        }}
        .stat-item .label {{
            font-size: 14px;
            color: var(--semi-color-text-1);
            margin-top: 8px;
        }}
        .section-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--semi-color-primary);
        }}
        .dimension-title::before {{
            content: '';
            width: 4px;
            height: 24px;
            background: var(--semi-color-primary);
            margin-right: 12px;
            border-radius: 2px;
        }}
        .dimension-subtitle {{
            font-size: 14px;
            color: var(--semi-color-text-1);
            margin-bottom: 12px;
            padding-left: 16px;
        }}
        .issue {{
            background: var(--semi-color-bg-1);
            border: 1px solid var(--semi-color-border);
            border-left: 2px solid var(--semi-color-danger);
            padding: 16px;
            margin-bottom: 12px;
            border-radius: var(--semi-border-radius-small);
            transition: box-shadow var(--shadow-elevated);
        }}
        .issue:hover {{
            box-shadow: var(--shadow-elevated);
        }}
        .issue.warning {{
            border-left-color: var(--semi-color-warning);
        }}
        .issue.info {{
            border-left-color: var(--semi-color-primary);
        }}
        .issue.success {{
            border-left-color: var(--semi-color-success);
        }}
        .issue.suggestion {{
            border-left-color: var(--semi-color-primary);
        }}
        .issue-title {{
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--semi-color-text-0);
            font-size: 14px;
        }}
        .issue-content {{
            font-size: 14px;
            color: var(--semi-color-text-1);
            line-height: 20px;
        }}
        .suggestion {{
            margin-top: 12px;
            padding: 12px;
            background: var(--semi-color-fill-0);
            border-radius: var(--semi-border-radius-small);
            font-size: 14px;
            color: var(--semi-color-text-1);
        }}
        .suggestion::before {{
            content: '\\1F4A1 ';
        }}
        .priority {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: var(--semi-border-radius-small);
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
        .priority.high {{
            background: var(--semi-color-danger);
            color: white;
        }}
        .priority.medium {{
            background: var(--semi-color-warning);
            color: white;
        }}
        .config-box {{
            background: var(--semi-color-fill-0);
            padding: 16px;
            border-radius: var(--semi-border-radius-small);
            margin-top: 12px;
            font-size: 14px;
        }}
        .config-item {{
            display: flex;
            margin-bottom: 8px;
        }}
        .config-item:last-child {{
            margin-bottom: 0;
        }}
        .config-label {{
            font-weight: 600;
            width: 150px;
            color: var(--semi-color-text-0);
        }}
        .sub-section {{
            margin-bottom: 24px;
        }}
        .sub-section-title {{
            font-size: 16px;
            font-weight: 600;
            color: var(--semi-color-text-0);
            margin-bottom: 12px;
        }}
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin: 12px 0 16px 0; }}
        .data-table th {{ padding: 10px 12px; background: var(--semi-color-fill-1); text-align: left; border: 1px solid var(--semi-color-border); font-weight: 600; }}
        .data-table td {{ padding: 10px 12px; border: 1px solid var(--semi-color-border); }}
        .rank-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            font-size: 12px;
            font-weight: 600;
            background: var(--semi-color-fill-0);
            color: var(--semi-color-text-1);
        }}
        .rank-badge.top-3 {{
            background: var(--semi-color-primary);
            color: white;
        }}
        .score-badge {{
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 16px;
            font-weight: 600;
            margin-top: 12px;
        }}
        .dist-bar {{
            display: flex;
            gap: 2px;
            height: 28px;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        .dist-segment {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: 600;
            color: white;
            white-space: nowrap;
            overflow: hidden;
            min-width: 70px;
            flex-shrink: 0;
        }}
        .score-dimensions {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 12px;
            margin-top: 16px;
        }}
        .score-dim {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .score-dim-label {{
            width: 140px;
            font-size: 13px;
        }}
        .score-dim-icon {{
            display: inline-block;
            font-size: 13px;
            line-height: 1;
            margin-left: 6px;
            vertical-align: middle;
            cursor: pointer;
            opacity: 0.65;
            color: var(--semi-color-text-2);
            border-radius: 50%;
            padding: 0 2px;
            position: relative;
        }}
        .score-dim-icon:hover {{
            opacity: 1;
            color: var(--semi-color-primary);
            background: var(--semi-color-fill-1);
            transform: scale(1.15);
        }}
        .score-dim-icon:hover::after {{
            content: attr(data-tooltip);
            position: absolute;
            left: calc(100% + 10px);
            top: 50%;
            transform: translateY(-50%);
            padding: 8px 12px;
            background: rgba(28, 31, 35, 0.95);
            color: #fff;
            font-size: 12px;
            line-height: 1.5;
            border-radius: 6px;
            width: max-content;
            max-width: 320px;
            white-space: pre-line;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            pointer-events: none;
            z-index: 1000;
        }}
        .score-dim-icon:hover::before {{
            content: '';
            position: absolute;
            left: calc(100%);
            top: 50%;
            transform: translateY(-50%);
            border: 5px solid transparent;
            border-right-color: rgba(28, 31, 35, 0.95);
            pointer-events: none;
            z-index: 1000;
        }}
        .score-dim-bar {{
            flex: 1;
            height: 10px;
            border-radius: 5px;
            background: var(--semi-color-fill-0);
            overflow: hidden;
        }}
        .score-dim-fill {{
            height: 100%;
            border-radius: 5px;
            transition: width 0.3s;
        }}
        .score-dim-value {{
            width: 50px;
            text-align: right;
            font-size: 14px;
            font-weight: 600;
        }}
        .action-list {{
            list-style: none;
        }}
        .action-item {{
            padding: 12px 16px;
            border: 1px solid var(--semi-color-border);
            border-radius: var(--semi-border-radius-small);
            margin-bottom: 8px;
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }}
        .action-item:hover {{
            box-shadow: var(--shadow-elevated);
        }}
        .action-num {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: var(--semi-color-primary);
            color: white;
            font-size: 13px;
            font-weight: 600;
            flex-shrink: 0;
        }}
        .action-content {{
            flex: 1;
        }}
        .action-title {{
            font-weight: 600;
            font-size: 14px;
            color: var(--semi-color-text-0);
            margin-bottom: 4px;
        }}
        .action-desc {{
            font-size: 13px;
            color: var(--semi-color-text-1);
        }}
        .priority.low {{
            background: var(--semi-color-success);
            color: white;
        }}
        .stat-item .value.danger {{
            color: var(--semi-color-danger);
        }}
        .stat-item .value.warning {{
            color: var(--semi-color-warning);
        }}
    </style>
</head>
<body>
    <nav class="toc">
        <div class="toc-title">目录</div>
        <ul class="toc-list">
            <li class="toc-item" data-target="overview"><a href="#overview">告警概览</a>
                <ul class="toc-sub">
                    <li data-target="health-details"><a href="#health-details">健康度评分明细</a></li>
                    <li data-target="level-dist"><a href="#level-dist">告警级别分布</a></li>
                    <li data-target="service-dist"><a href="#service-dist">告警服务类型分布</a></li>
                </ul>
            </li>
            <li class="toc-item" data-target="top10"><a href="#top10">TOP10 告警</a></li>
            <li class="toc-item" data-target="daily-trend"><a href="#daily-trend">每日告警趋势</a></li>
            <li class="toc-item" data-target="governance"><a href="#governance">告警治理</a>
                <ul class="toc-sub">
                    <li data-target="governance-grouping"><a href="#governance-grouping">路由分组建议</a></li>
                    <li data-target="governance-dedup"><a href="#governance-dedup">去重分析</a></li>
                    <li data-target="governance-suppression"><a href="#governance-suppression">抑制规则建议</a></li>
                    <li data-target="governance-silence"><a href="#governance-silence">静默规则建议</a></li>
                    <li data-target="governance-temporal"><a href="#governance-temporal">告警时序关联性分析</a></li>
                </ul>
            </li>
            </li>
            <li class="toc-item" data-target="unresolved"><a href="#unresolved">长久未恢复告警</a>
                <ul class="toc-sub">
                    <li data-target="unresolved-stats"><a href="#unresolved-stats">分级统计</a></li>
                    <li data-target="unresolved-list"><a href="#unresolved-list">未恢复明细</a></li>
                </ul>
            </li>
            <li class="toc-item" data-target="actions"><a href="#actions">降噪建议汇总</a></li>
        </ul>
    </nav>

    <div class="content">
        <div class="container">
            <div class="header">
                <h1>告警降噪优化分析报告</h1>
                <div class="subtitle">区域: {username} | 数据时间范围: {time_range_label} | 生成时间: {timestamp}</div>
                <div class="score-badge" style="background:{health_score_color};">健康度评分：{health_score} / 100</div>
            </div>

            <div class="card" id="overview">
                <h2 class="card-header">告警概览</h2>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="value">{total_alarms}</div>
                        <div class="label">告警事件数</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{notification_count}</div>
                        <div class="label">通知消息数</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{unique_resources}</div>
                        <div class="label">涉及资源数</div>
                    </div>
                    <div class="stat-item">
                        <div class="value danger">{critical_count}</div>
                        <div class="label">Critical告警</div>
                    </div>
                    <div class="stat-item">
                        <div class="value warning">{major_count}</div>
                        <div class="label">Major告警</div>
                    </div>
                    <div class="stat-item">
                        <div class="value" style="color:var(--semi-color-text-2);">{minor_count}</div>
                        <div class="label">Minor告警</div>
                    </div>
                    <div class="stat-item">
                        <div class="value warning">{unresolved_active_count}</div>
                        <div class="label">未恢复告警</div>
                    </div>
                    {core_stats_html}
                </div>
            </div>

            <div class="card" id="health-details">
                <h2 class="card-header">健康度评分明细<span class="card-header-icon" data-tooltip="健康度评分由 5 个维度加权计算得出：告警总量(20%) + 严重告警占比(25%) + 告警收敛率(15%) + 长久未恢复告警(20%) + 告警趋势(20%)">ⓘ</span></h2>
                {health_score_details}
            </div>

            <div style="display:flex;gap:16px;">
                <div class="card" id="level-dist" style="flex:1;">
                    <h2 class="card-header">告警级别分布</h2>
                    {level_distribution}
                </div>
                <div class="card" id="service-dist" style="flex:1;">
                    <h2 class="card-header">告警服务类型分布</h2>
                    {service_distribution}
                </div>
            </div>

            <div class="card" id="top10">
                <h2 class="card-header">TOP10 告警</h2>
                {top10_issues}
            </div>

            <div class="card" id="daily-trend">
                <h2 class="card-header">每日告警趋势<span class="card-header-icon" data-tooltip="用于观察告警在收敛还是恶化，以及每天告警高峰期">ⓘ</span></h2>
                {daily_trend_html}
            </div>

            <div class="card" id="governance">
                <h2 class="card-header">告警治理</h2>
                {grouping_issues}
                {dedup_issues}
                {suppression_issues}
                {silence_issues}
                <div class="sub-section-title" id="governance-temporal">告警时序关联性分析</div>
                {temporal_correlation_html}
            </div>

            <div class="card" id="unresolved">
                <h2 class="card-header">长久未恢复告警</h2>
                {unresolved_issues}
            </div>

            {actions_summary_html}
        </div>
    </div>

    <script>
        (function() {{
            var sections = document.querySelectorAll('.card[id]');
            var tocItems = document.querySelectorAll('.toc-item[data-target], .toc-sub[data-target]');

            function setActive(id) {{
                tocItems.forEach(function(el) {{
                    if (el.dataset.target === id) {{
                        el.classList.add('active');
                    }} else {{
                        el.classList.remove('active');
                    }}
                }});
            }}

            var observer = new IntersectionObserver(function(entries) {{
                entries.forEach(function(entry) {{
                    if (entry.isIntersecting) {{
                        setActive(entry.target.id);
                    }}
                }});
            }}, {{ rootMargin: '-80px 0px -70% 0px', threshold: 0 }});

            sections.forEach(function(s) {{ observer.observe(s); }});

            tocItems.forEach(function(el) {{
                el.querySelector('a').addEventListener('click', function(e) {{
                    e.preventDefault();
                    var target = document.getElementById(el.dataset.target);
                    if (target) {{
                        target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                        setActive(el.dataset.target);
                    }}
                }});
            }});
        }})();
    </script>
</body>
</html>'''

    unique_resources = len(set(a.get('alarm_resource', {}).get('resourceId', '') for a in alarms))
    critical_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'CRITICAL')
    major_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'MAJOR')
    minor_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'MINOR')
    unresolved_active_count = sum(1 for a in alarms if not a.get('recover_time'))
    notification_count = sum(len(a.get('notification_ids') or []) for a in alarms)

    if core_ids:
        from core_resources import is_core_resource
        core_alarm_count = sum(1 for a in alarms if is_core_resource(a, core_ids))
        core_resource_count = len(set(
            a.get('alarm_resource', {}).get('resourceId', '')
            for a in alarms if is_core_resource(a, core_ids)
        ))
        core_pct = f"{core_alarm_count * 100 // len(alarms)}%" if alarms else "0%"
        core_stats_html = f'''
                    <div class="stat-item">
                        <div class="value">{core_alarm_count}</div>
                        <div class="label">核心资源告警 ({core_pct})</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{core_resource_count}</div>
                        <div class="label">核心资源数</div>
                    </div>'''
    else:
        core_stats_html = '''
                    <div class="stat-item">
                        <div class="value">0</div>
                        <div class="label">核心资源告警 (0%)</div>
                    </div>'''

    hs = health_score or {'total': 0, 'volume': 0, 'severity': 0, 'convergence': 0, 'unresolved': 0, 'trend': 0}
    hs_color = score_color(hs['total'])

    grouping_issues_html = generate_grouping_html(convergence_results)
    dedup_issues_html = generate_dedup_html(rule_results)
    suppression_issues_html = generate_suppression_html(rule_results, correlation_results)
    silence_issues_html = generate_silence_html(suppression_results)
    top10_html = generate_top10_html(analyze_top10_alarms(alarms, core_ids, alarm_rules), core_ids)
    unresolved_html = generate_unresolved_issues_html(unresolved_results) if unresolved_results else ''
    health_score_details_html = generate_health_score_details_html(hs)
    level_dist_html = generate_level_distribution_html(alarms)
    service_dist_html = generate_service_distribution_html(alarms)
    daily_trend_html_val = generate_daily_trend_html(daily_trend) if daily_trend else ''
    temporal_corr_html = generate_temporal_correlation_html(temporal_correlation) if temporal_correlation else ''
    actions_html = generate_actions_summary_html(action_lists) if action_lists else ''

    time_range_label = time_range.get('label', '近1天') if time_range else '近1天'

    return html_template.format(
        username=username,
        time_range_label=time_range_label,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_alarms=len(alarms),
        unique_resources=unique_resources,
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        unresolved_active_count=unresolved_active_count,
        notification_count=notification_count,
        core_stats_html=core_stats_html,
        health_score=hs['total'],
        health_score_color=hs_color,
        health_score_details=health_score_details_html,
        level_distribution=level_dist_html,
        service_distribution=service_dist_html,
        grouping_issues=grouping_issues_html,
        dedup_issues=dedup_issues_html,
        suppression_issues=suppression_issues_html,
        silence_issues=silence_issues_html,
        temporal_correlation_html=temporal_corr_html,
        unresolved_issues=unresolved_html,
        top10_issues=top10_html,
        daily_trend_html=daily_trend_html_val,
        actions_summary_html=actions_html
    )


def generate_region_sections(alarms, username, time_range, rule_results,
                             suppression_results, convergence_results,
                             correlation_results, unresolved_results=None,
                             core_ids=None, health_score=None, daily_trend=None,
                             temporal_correlation=None, action_lists=None,
                             alarm_rules=None):
    """为单个区域生成所有section的HTML内容
    返回: (sections_dict, header_info_dict)
      sections_dict: {section_id: html_str}
      header_info_dict: {username, time_range_label, health_score, health_score_color}
    """
    unique_resources = len(set(a.get('alarm_resource', {}).get('resourceId', '') for a in alarms))
    critical_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'CRITICAL')
    major_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'MAJOR')
    minor_count = sum(1 for a in alarms if a.get('alarm_level', '') == 'MINOR')
    unresolved_active_count = sum(1 for a in alarms if not a.get('recover_time'))
    notification_count = sum(len(a.get('notification_ids') or []) for a in alarms)

    if core_ids:
        from core_resources import is_core_resource
        core_alarm_count = sum(1 for a in alarms if is_core_resource(a, core_ids))
        core_resource_count = len(set(
            a.get('alarm_resource', {}).get('resourceId', '')
            for a in alarms if is_core_resource(a, core_ids)
        ))
        core_pct = f"{core_alarm_count * 100 // len(alarms)}%" if alarms else "0%"
        core_stats_html = f'''
                    <div class="stat-item">
                        <div class="value">{core_alarm_count}</div>
                        <div class="label">核心资源告警 ({core_pct})</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{core_resource_count}</div>
                        <div class="label">核心资源数</div>
                    </div>'''
    else:
        core_stats_html = '''
                    <div class="stat-item">
                        <div class="value">0</div>
                        <div class="label">核心资源告警 (0%)</div>
                    </div>'''

    hs = health_score or {'total': 0, 'volume': 0, 'severity': 0, 'convergence': 0, 'unresolved': 0, 'trend': 0}
    hs_color = score_color(hs['total'])

    overview_html = f'''<div class="stat-grid">
                    <div class="stat-item">
                        <div class="value">{len(alarms)}</div>
                        <div class="label">告警事件数</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{notification_count}</div>
                        <div class="label">通知消息数</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{unique_resources}</div>
                        <div class="label">涉及资源数</div>
                    </div>
                    <div class="stat-item">
                        <div class="value danger">{critical_count}</div>
                        <div class="label">Critical告警</div>
                    </div>
                    <div class="stat-item">
                        <div class="value warning">{major_count}</div>
                        <div class="label">Major告警</div>
                    </div>
                    <div class="stat-item">
                        <div class="value" style="color:var(--semi-color-text-2);">{minor_count}</div>
                        <div class="label">Minor告警</div>
                    </div>
                    <div class="stat-item">
                        <div class="value warning">{unresolved_active_count}</div>
                        <div class="label">未恢复告警</div>
                    </div>
                    {core_stats_html}
                </div>'''

    grouping_issues_html = generate_grouping_html(convergence_results)
    dedup_issues_html = generate_dedup_html(rule_results)
    suppression_issues_html = generate_suppression_html(rule_results, correlation_results)
    silence_issues_html = generate_silence_html(suppression_results)
    top10_html = generate_top10_html(analyze_top10_alarms(alarms, core_ids, alarm_rules), core_ids)
    unresolved_html = generate_unresolved_issues_html(unresolved_results) if unresolved_results else ''
    health_score_details_html = generate_health_score_details_html(hs)
    level_dist_html = generate_level_distribution_html(alarms)
    service_dist_html = generate_service_distribution_html(alarms)
    daily_trend_html_val = generate_daily_trend_html(daily_trend) if daily_trend else ''
    temporal_corr_html = generate_temporal_correlation_html(temporal_correlation) if temporal_correlation else ''
    actions_html = generate_actions_summary_html(action_lists) if action_lists else ''

    governance_html = (
        grouping_issues_html
        + dedup_issues_html
        + suppression_issues_html
        + silence_issues_html
        + f'<div class="sub-section-title" id="governance-temporal">告警时序关联性分析</div>'
        + temporal_corr_html
    )

    sections = {
        'overview': overview_html,
        'health_details': health_score_details_html,
        'level_dist': level_dist_html,
        'service_dist': service_dist_html,
        'top10': top10_html,
        'governance': governance_html,
        'daily_trend': daily_trend_html_val,
        'unresolved': unresolved_html,
        'actions': actions_html,
    }

    time_range_label = time_range.get('label', '近1天') if time_range else '近1天'

    header_info = {
        'username': username,
        'time_range_label': time_range_label,
        'health_score': hs['total'],
        'health_score_color': hs_color,
    }

    return sections, header_info


def generate_multi_region_html_report(region_sections, region_headers, global_cust_options,
                                      timestamp_str=None):
    """生成多区域HTML报告（带区域切换器）

    :param region_sections: {region_name: {section_id: html_str}}
    :param region_headers: {region_name: {username, time_range_label, health_score, health_score_color}}
    :param global_cust_options: [{"value": region_name, "label": region_name}, ...]
    :param timestamp_str: 生成时间字符串
    :return: HTML字符串
    """
    from datetime import datetime
    timestamp_str = timestamp_str or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    first_region = global_cust_options[0]['value'] if global_cust_options else ''
    first_sections = region_sections.get(first_region, {})
    first_header = region_headers.get(first_region, {})

    sections_json = json.dumps(region_sections, ensure_ascii=False)
    header_json = json.dumps(region_headers, ensure_ascii=False)
    cust_options_json = json.dumps(global_cust_options, ensure_ascii=False)

    SECTION_IDS = ['overview', 'health_details', 'level_dist', 'service_dist',
                   'top10', 'daily_trend', 'governance',
                   'unresolved', 'actions']

    html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>告警降噪优化分析报告</title>
    <style>
        :root {
            --semi-color-primary: #0064FA;
            --semi-color-success: #3BB346;
            --semi-color-warning: #FC8800;
            --semi-color-danger: #F93920;
            --semi-color-secondary: #8A92A6;
            --semi-color-bg-0: #FFFFFF;
            --semi-color-bg-1: #FFFFFF;
            --semi-color-text-0: #1C1F23;
            --semi-color-text-1: rgba(28,31,35,0.8);
            --semi-color-text-2: rgba(28,31,35,0.62);
            --semi-color-fill-0: rgba(46,50,56,0.05);
            --semi-color-fill-1: rgba(46,50,56,0.09);
            --semi-color-border: rgba(28,31,35,0.08);
            --semi-border-radius-small: 3px;
            --semi-border-radius-large: 12px;
            --shadow-elevated: 0 4px 14px rgba(0, 0, 0, 0.1);
            --toc-width: 220px;
        }
        html { scroll-behavior: smooth; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif;
            background: var(--semi-color-fill-0);
            color: var(--semi-color-text-0);
            line-height: 1.6;
            font-size: 14px;
        }
        .toc {
            position: fixed; left: 0; top: 0; width: var(--toc-width); height: 100vh;
            background: var(--semi-color-bg-1); border-right: 1px solid var(--semi-color-border);
            padding: 24px 0; overflow-y: auto; z-index: 100;
        }
        .toc-title { font-size: 16px; font-weight: 600; color: var(--semi-color-text-0); padding: 0 20px 16px; border-bottom: 1px solid var(--semi-color-border); margin-bottom: 8px; }
        .toc-list { list-style: none; }
        .toc-item { display: block; }
        .toc-item a { display: block; padding: 8px 20px; font-size: 14px; color: var(--semi-color-text-1); text-decoration: none; border-left: 3px solid transparent; transition: all 0.2s; }
        .toc-item a:hover { background: var(--semi-color-fill-0); color: var(--semi-color-primary); }
        .toc-item.active a { color: var(--semi-color-primary); border-left-color: var(--semi-color-primary); background: var(--semi-color-fill-0); font-weight: 600; }
        .toc-sub { list-style: none; }
        .toc-sub a { display: block; padding: 6px 20px 6px 36px; font-size: 12px; color: var(--semi-color-text-2); text-decoration: none; border-left: 3px solid transparent; transition: all 0.2s; }
        .toc-sub a:hover { background: var(--semi-color-fill-0); color: var(--semi-color-primary); }
        .toc-sub.active a { color: var(--semi-color-primary); border-left-color: var(--semi-color-primary); background: var(--semi-color-fill-0); font-weight: 600; }
        .content { margin-left: var(--toc-width); }
        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
        .header { background: var(--semi-color-primary); color: white; padding: 32px; border-radius: var(--semi-border-radius-large); margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }
        .header-left { flex: 1; }
        .header h1 { font-size: 28px; font-weight: 600; line-height: 40px; margin-bottom: 8px; }
        .header .subtitle { opacity: 0.9; font-size: 14px; }
        .score-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-size: 16px; font-weight: 600; margin-top: 12px; }
        .header-right { display: flex; align-items: center; gap: 8px; margin-left: 24px; flex-shrink: 0; }
        .header-right .cust-label { font-size: 14px; font-weight: 600; opacity: 0.9; white-space: nowrap; }
        .global-cust-select { position: relative; width: 160px; }
        .global-cust-trigger { width: 100%; max-width: 160px; border: 1px solid rgba(255,255,255,0.5); background: rgba(255,255,255,0.15); color: #fff; border-radius: var(--semi-border-radius-small); padding: 6px 8px; font-size: 13px; cursor: pointer; box-sizing: border-box; display: flex; align-items: center; justify-content: space-between; gap: 4px; min-height: 30px; }
        .global-cust-trigger:hover { border-color: rgba(255,255,255,0.7); background: rgba(255,255,255,0.2); }
        .global-cust-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .global-cust-text.placeholder { opacity: 0.6; }
        .global-cust-arrow { font-size: 10px; opacity: 0.7; flex-shrink: 0; transition: transform 0.2s; }
        .global-cust-trigger.open .global-cust-arrow { transform: rotate(180deg); }
        .global-cust-clear { position: absolute; right: 14px; top: 53%; transform: translateY(-50%); width: 16px; height: 16px; border-radius: 50%; background: var(--semi-color-fill-1); color: var(--semi-color-text-2); font-size: 10px; line-height: 16px; text-align: center; cursor: pointer; display: none; border: none; padding: 0; }
        .global-cust-clear:hover { background: var(--semi-color-fill-1); color: var(--semi-color-text-0); }
        .global-cust-clear.visible { display: block; }
        .global-cust-dropdown { display: none; position: absolute; top: 100%; left: 0; width: 100%; background: var(--semi-color-bg-1); border: 1px solid var(--semi-color-border); border-top: none; border-radius: 0 0 var(--semi-border-radius-small) var(--semi-border-radius-small); box-shadow: var(--shadow-elevated); z-index: 100; }
        .global-cust-dropdown.open { display: block; }
        .global-cust-search-wrap { padding: 8px 8px 4px; border-bottom: 1px solid var(--semi-color-border); position: sticky; top: 0; background: var(--semi-color-bg-1); z-index: 1; }
        .global-cust-search { width: 100%; border: 1px solid var(--semi-color-border); background: var(--semi-color-bg-0); color: var(--semi-color-text-0); border-radius: var(--semi-border-radius-small); padding: 6px 24px 6px 8px; font-size: 13px; box-sizing: border-box; outline: none; }
        .global-cust-search:focus { border-color: var(--semi-color-primary); }
        .global-cust-search::placeholder { color: var(--semi-color-text-2); }
        .global-cust-options { max-height: 200px; overflow-y: auto; }
        .global-cust-option { padding: 8px 10px; cursor: pointer; font-size: 13px; color: var(--semi-color-text-1); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .global-cust-option:hover { background: var(--semi-color-fill-1); }
        .global-cust-option.selected { background: rgba(0,100,250,0.08); color: var(--semi-color-primary); font-weight: 600; }
        .global-cust-no-result { padding: 12px; text-align: center; color: var(--semi-color-text-2); font-size: 13px; }
        .card { background: var(--semi-color-bg-1); border-radius: var(--semi-border-radius-large); padding: 24px; margin-bottom: 24px; border: 1px solid var(--semi-color-border); overflow: hidden; }
        .card-header { font-size: 20px; font-weight: 600; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid var(--semi-color-primary); display: flex; align-items: center; }
        .card-header-icon { display: inline-block; font-size: 14px; line-height: 1; margin-left: 8px; vertical-align: middle; cursor: pointer; opacity: 0.65; color: var(--semi-color-text-2); border-radius: 50%; padding: 0 2px; position: relative; }
        .card-header-icon:hover { opacity: 1; color: var(--semi-color-primary); background: var(--semi-color-fill-1); }
        .card-header-icon:hover::after { content: attr(data-tooltip); position: absolute; left: calc(100% + 10px); top: 50%; transform: translateY(-50%); padding: 8px 12px; background: rgba(28, 31, 35, 0.95); color: #fff; font-size: 12px; line-height: 1.5; border-radius: 6px; width: max-content; max-width: 360px; white-space: pre-line; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); pointer-events: none; z-index: 1000; }
        .card-header-icon:hover::before { content: ''; position: absolute; left: calc(100%); top: 50%; transform: translateY(-50%); border: 5px solid transparent; border-right-color: rgba(28, 31, 35, 0.95); pointer-events: none; z-index: 1000; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
        .stat-item { background: var(--semi-color-fill-0); padding: 20px; border-radius: var(--semi-border-radius-small); text-align: center; transition: background var(--semi-color-fill-1); }
        .stat-item:hover { background: var(--semi-color-fill-1); }
        .stat-item .value { font-size: 32px; font-weight: 600; color: var(--semi-color-primary); line-height: 40px; }
        .stat-item .label { font-size: 14px; color: var(--semi-color-text-1); margin-top: 8px; }
        .section-title { font-size: 20px; font-weight: 600; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid var(--semi-color-primary); }
        .dimension-subtitle { font-size: 14px; color: var(--semi-color-text-1); margin-bottom: 12px; padding-left: 16px; }
        .issue { background: var(--semi-color-bg-1); border: 1px solid var(--semi-color-border); border-left: 2px solid var(--semi-color-danger); padding: 16px; margin-bottom: 12px; border-radius: var(--semi-border-radius-small); transition: box-shadow var(--shadow-elevated); }
        .issue:hover { box-shadow: var(--shadow-elevated); }
        .issue.warning { border-left-color: var(--semi-color-warning); }
        .issue.info { border-left-color: var(--semi-color-primary); }
        .issue.success { border-left-color: var(--semi-color-success); }
        .issue.suggestion { border-left-color: var(--semi-color-primary); }
        .issue-title { font-weight: 600; margin-bottom: 8px; color: var(--semi-color-text-0); font-size: 14px; }
        .issue-content { font-size: 14px; color: var(--semi-color-text-1); line-height: 20px; }
        .suggestion { margin-top: 12px; padding: 12px; background: var(--semi-color-fill-0); border-radius: var(--semi-border-radius-small); font-size: 14px; color: var(--semi-color-text-1); }
        .suggestion::before { content: '\\1F4A1 '; }
        .priority { display: inline-block; padding: 2px 8px; border-radius: var(--semi-border-radius-small); font-size: 12px; font-weight: 600; margin-left: 10px; }
        .priority.high { background: var(--semi-color-danger); color: white; }
        .priority.medium { background: var(--semi-color-warning); color: white; }
        .priority.low { background: var(--semi-color-success); color: white; }
        .config-box { background: var(--semi-color-fill-0); padding: 16px; border-radius: var(--semi-border-radius-small); margin-top: 12px; font-size: 14px; }
        .sub-section { margin-bottom: 24px; }
        .sub-section-title { font-size: 16px; font-weight: 600; color: var(--semi-color-text-0); margin-bottom: 12px; }
        .data-table { width: 100%; border-collapse: collapse; font-size: 14px; margin: 12px 0 16px 0; }
        .data-table th { padding: 10px 12px; background: var(--semi-color-fill-1); text-align: left; border: 1px solid var(--semi-color-border); font-weight: 600; }
        .data-table td { padding: 10px 12px; border: 1px solid var(--semi-color-border); }
        .rank-badge { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; font-size: 12px; font-weight: 600; background: var(--semi-color-fill-0); color: var(--semi-color-text-1); }
        .rank-badge.top-3 { background: var(--semi-color-primary); color: white; }
        .score-dimensions { display: grid; grid-template-columns: 1fr; gap: 12px; margin-top: 16px; }
        .score-dim { display: flex; align-items: center; gap: 12px; }
        .score-dim-label { width: 140px; font-size: 13px; }
        .score-dim-icon { display: inline-block; font-size: 13px; line-height: 1; margin-left: 6px; vertical-align: middle; cursor: pointer; opacity: 0.65; color: var(--semi-color-text-2); border-radius: 50%; padding: 0 2px; position: relative; }
        .score-dim-icon:hover { opacity: 1; color: var(--semi-color-primary); background: var(--semi-color-fill-1); transform: scale(1.15); }
        .score-dim-icon:hover::after { content: attr(data-tooltip); position: absolute; left: calc(100% + 10px); top: 50%; transform: translateY(-50%); padding: 8px 12px; background: rgba(28, 31, 35, 0.95); color: #fff; font-size: 12px; line-height: 1.5; border-radius: 6px; width: max-content; max-width: 320px; white-space: pre-line; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); pointer-events: none; z-index: 1000; }
        .score-dim-icon:hover::before { content: ''; position: absolute; left: calc(100%); top: 50%; transform: translateY(-50%); border: 5px solid transparent; border-right-color: rgba(28, 31, 35, 0.95); pointer-events: none; z-index: 1000; }
        .score-dim-bar { flex: 1; height: 10px; border-radius: 5px; background: var(--semi-color-fill-0); overflow: hidden; }
        .score-dim-fill { height: 100%; border-radius: 5px; transition: width 0.3s; }
        .score-dim-value { width: 50px; text-align: right; font-size: 14px; font-weight: 600; }
        .action-list { list-style: none; }
        .action-item { padding: 12px 16px; border: 1px solid var(--semi-color-border); border-radius: var(--semi-border-radius-small); margin-bottom: 8px; display: flex; align-items: flex-start; gap: 12px; }
        .action-item:hover { box-shadow: var(--shadow-elevated); }
        .action-num { display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: var(--semi-color-primary); color: white; font-size: 13px; font-weight: 600; flex-shrink: 0; }
        .action-content { flex: 1; }
        .action-title { font-weight: 600; font-size: 14px; color: var(--semi-color-text-0); margin-bottom: 4px; }
        .action-desc { font-size: 13px; color: var(--semi-color-text-1); }
        .stat-item .value.danger { color: var(--semi-color-danger); }
        .stat-item .value.warning { color: var(--semi-color-warning); }
        .priority.low { background: var(--semi-color-success); color: white; }
        .dist-bar { display: flex; gap: 2px; height: 28px; border-radius: 4px; overflow: hidden; margin-top: 8px; }
        .dist-segment { display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; color: white; white-space: nowrap; overflow: hidden; min-width: 70px; flex-shrink: 0; }
    </style>
</head>
<body>
    <nav class="toc">
        <div class="toc-title">目录</div>
        <ul class="toc-list">
            <li class="toc-item" data-target="overview"><a href="#overview">告警概览</a>
                <ul class="toc-sub">
                    <li data-target="health-details"><a href="#health-details">健康度评分明细</a></li>
                    <li data-target="level-dist"><a href="#level-dist">告警级别分布</a></li>
                    <li data-target="service-dist"><a href="#service-dist">告警服务类型分布</a></li>
                </ul>
            </li>
            <li class="toc-item" data-target="top10"><a href="#top10">TOP10 告警</a></li>
            <li class="toc-item" data-target="daily-trend"><a href="#daily-trend">每日告警趋势</a></li>
            <li class="toc-item" data-target="governance"><a href="#governance">告警治理</a>
                <ul class="toc-sub">
                    <li data-target="governance-grouping"><a href="#governance-grouping">路由分组建议</a></li>
                    <li data-target="governance-dedup"><a href="#governance-dedup">去重分析</a></li>
                    <li data-target="governance-suppression"><a href="#governance-suppression">抑制规则建议</a></li>
                    <li data-target="governance-silence"><a href="#governance-silence">静默规则建议</a></li>
                    <li data-target="governance-temporal"><a href="#governance-temporal">告警时序关联性分析</a></li>
                </ul>
            </li>
            <li class="toc-item" data-target="unresolved"><a href="#unresolved">长久未恢复告警</a></li>
            <li class="toc-item" data-target="actions"><a href="#actions">降噪建议汇总</a></li>
        </ul>
    </nav>

    <div class="content">
        <div class="container">
            <div class="header">
                <div class="header-left">
                    <h1>告警降噪优化分析报告</h1>
                    <div class="subtitle" id="header-subtitle">区域: __FIRST_USERNAME__ | 数据时间范围: __FIRST_TIME_RANGE__ | 生成时间: __TIMESTAMP__</div>
                    <div class="score-badge" id="header-score-badge" style="background:__FIRST_HS_COLOR__;">健康度评分：__FIRST_HS__ / 100</div>
                </div>
                <div class="header-right" id="header-right">
                    <span class="cust-label">区域：</span>
                    <div class="global-cust-select" id="global-cust-select">
                        <div class="global-cust-trigger" id="global-cust-trigger">
                            <span class="global-cust-text placeholder" id="global-cust-text">选择区域</span>
                            <span class="global-cust-arrow">▼</span>
                        </div>
                        <div class="global-cust-dropdown" id="global-cust-dropdown">
                            <div class="global-cust-search-wrap">
                                <input type="text" class="global-cust-search" id="global-cust-search" placeholder="搜索区域" autocomplete="off" />
                                <button type="button" class="global-cust-clear" id="global-cust-clear">&times;</button>
                            </div>
                            <div class="global-cust-options" id="global-cust-options"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card" id="overview">
                <h2 class="card-header">告警概览</h2>
                <div id="sec-overview">__SEC_OVERVIEW__</div>
            </div>

            <div class="card" id="health-details">
                <h2 class="card-header">健康度评分明细<span class="card-header-icon" data-tooltip="健康度评分由 5 个维度加权计算得出：告警总量(20%) + 严重告警占比(25%) + 告警收敛率(15%) + 长久未恢复告警(20%) + 告警趋势(20%)">ⓘ</span></h2>
                <div id="sec-health_details">__SEC_HEALTH_DETAILS__</div>
            </div>

            <div style="display:flex;gap:16px;">
                <div class="card" id="level-dist" style="flex:1;">
                    <h2 class="card-header">告警级别分布</h2>
                    <div id="sec-level_dist">__SEC_LEVEL_DIST__</div>
                </div>
                <div class="card" id="service-dist" style="flex:1;">
                    <h2 class="card-header">告警服务类型分布</h2>
                    <div id="sec-service_dist">__SEC_SERVICE_DIST__</div>
                </div>
            </div>

            <div class="card" id="top10">
                <h2 class="card-header">TOP10 告警</h2>
                <div id="sec-top10">__SEC_TOP10__</div>
            </div>

            <div class="card" id="daily-trend">
                <h2 class="card-header">每日告警趋势<span class="card-header-icon" data-tooltip="用于观察告警在收敛还是恶化，以及每天告警高峰期">ⓘ</span></h2>
                <div id="sec-daily_trend">__SEC_DAILY_TREND__</div>
            </div>

            <div class="card" id="governance">
                <h2 class="card-header">告警治理</h2>
                <div id="sec-governance">__SEC_GOVERNANCE__</div>
            </div>

            <div class="card" id="unresolved">
                <h2 class="card-header">长久未恢复告警</h2>
                <div id="sec-unresolved">__SEC_UNRESOLVED__</div>
            </div>

            <div class="card" id="actions">
                <h2 class="card-header">降噪建议汇总（按优先级排序）</h2>
                <div id="sec-actions">__SEC_ACTIONS__</div>
            </div>
        </div>
    </div>

    <script>
        var GLOBAL_CUST_OPTIONS = __CUST_OPTIONS_JSON__;
        var SECTIONS_BY_CUST = __SECTIONS_JSON__;
        var HEADER_INFO_BY_CUST = __HEADER_JSON__;
        var SECTION_IDS = ['overview','health_details','level_dist','service_dist','top10','daily_trend','governance','unresolved','actions'];

        var globalCustValue = '';
        var globalCustTrigger = document.getElementById('global-cust-trigger');
        var globalCustText = document.getElementById('global-cust-text');
        var globalCustDropdown = document.getElementById('global-cust-dropdown');
        var globalCustSearch = document.getElementById('global-cust-search');
        var globalCustOptions = document.getElementById('global-cust-options');
        var globalCustClear = document.getElementById('global-cust-clear');

        function escapeHtml(s) {
            if (!s) return '';
            return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        }

        function openGlobalCustDropdown() {
            globalCustSearch.value = '';
            renderGlobalOptions('');
            globalCustDropdown.classList.add('open');
            globalCustTrigger.classList.add('open');
            setTimeout(function() { globalCustSearch.focus(); }, 0);
        }

        function closeGlobalCustDropdown() {
            globalCustDropdown.classList.remove('open');
            globalCustTrigger.classList.remove('open');
        }

        function renderGlobalOptions(keyword) {
            var kw = (keyword || '').toLowerCase();
            var html = '';
            var hasMatch = false;
            for (var i = 0; i < GLOBAL_CUST_OPTIONS.length; i++) {
                var opt = GLOBAL_CUST_OPTIONS[i];
                if (kw && opt.label.toLowerCase().indexOf(kw) === -1 && opt.value.toLowerCase().indexOf(kw) === -1) continue;
                hasMatch = true;
                var cls = 'global-cust-option';
                if (opt.value === globalCustValue) cls += ' selected';
                html += '<div class="' + cls + '" data-value="' + escapeHtml(opt.value) + '">' + escapeHtml(opt.label) + '</div>';
            }
            if (!hasMatch) html = '<div class="global-cust-no-result">无匹配结果</div>';
            globalCustOptions.innerHTML = html;
            var items = globalCustOptions.querySelectorAll('.global-cust-option');
            for (var j = 0; j < items.length; j++) {
                items[j].addEventListener('mousedown', function(e) {
                    e.preventDefault();
                    var val = this.getAttribute('data-value');
                    globalCustValue = val;
                    for (var k = 0; k < GLOBAL_CUST_OPTIONS.length; k++) {
                        if (GLOBAL_CUST_OPTIONS[k].value === val) {
                            globalCustText.textContent = GLOBAL_CUST_OPTIONS[k].label;
                            globalCustText.classList.remove('placeholder');
                            break;
                        }
                    }
                    closeGlobalCustDropdown();
                    updateGlobalClearBtn();
                    onGlobalCustChange();
                });
            }
        }

        function updateGlobalClearBtn() {
            if (globalCustValue) {
                globalCustClear.className = 'global-cust-clear visible';
            } else {
                globalCustClear.className = 'global-cust-clear';
            }
        }

        function onGlobalCustChange() {
            var cust = globalCustValue;
            var sections = SECTIONS_BY_CUST[cust] || {};
            for (var i = 0; i < SECTION_IDS.length; i++) {
                var id = SECTION_IDS[i];
                var el = document.getElementById('sec-' + id);
                if (el && sections[id] !== undefined) {
                    el.innerHTML = sections[id];
                }
            }
            var info = HEADER_INFO_BY_CUST[cust];
            if (info) {
                var subtitle = '区域: ' + escapeHtml(info.username) + ' | 数据时间范围: ' + escapeHtml(info.time_range_label) + ' | 生成时间: ' + escapeHtml(globalTimestamp);
                document.getElementById('header-subtitle').textContent = subtitle;
                var badge = document.getElementById('header-score-badge');
                badge.textContent = '健康度评分：' + info.health_score + ' / 100';
                badge.style.background = info.health_score_color;
            }
            // Re-init TOC scroll spy
            initTocScrollSpy();
        }

        function initTocScrollSpy() {
            var sections = document.querySelectorAll('.card[id]');
            var tocItems = document.querySelectorAll('.toc-item[data-target], .toc-sub[data-target]');
            function setActive(id) {
                tocItems.forEach(function(el) {
                    if (el.dataset.target === id) {
                        el.classList.add('active');
                    } else {
                        el.classList.remove('active');
                    }
                });
            }
            var observer = new IntersectionObserver(function(entries) {
                entries.forEach(function(entry) {
                    if (entry.isIntersecting) {
                        setActive(entry.target.id);
                    }
                });
            }, { rootMargin: '-80px 0px -70% 0px', threshold: 0 });
            sections.forEach(function(s) { observer.observe(s); });
            tocItems.forEach(function(el) {
                el.querySelector('a').addEventListener('click', function(e) {
                    e.preventDefault();
                    var target = document.getElementById(el.dataset.target);
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        setActive(el.dataset.target);
                    }
                });
            });
        }

        var globalTimestamp = '__TIMESTAMP__';

        function initGlobalCustSelect() {
            if (!GLOBAL_CUST_OPTIONS || GLOBAL_CUST_OPTIONS.length === 0) {
                document.getElementById('header-right').style.display = 'none';
                return;
            }
            globalCustValue = GLOBAL_CUST_OPTIONS[0].value;
            globalCustText.textContent = GLOBAL_CUST_OPTIONS[0].label;
            globalCustText.classList.remove('placeholder');
            updateGlobalClearBtn();
            globalCustTrigger.addEventListener('click', function(e) {
                if (globalCustDropdown.classList.contains('open')) {
                    closeGlobalCustDropdown();
                } else {
                    openGlobalCustDropdown();
                }
            });
            globalCustSearch.addEventListener('input', function() {
                renderGlobalOptions(globalCustSearch.value);
            });
            globalCustSearch.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') { closeGlobalCustDropdown(); }
            });
            document.addEventListener('mousedown', function(e) {
                if (!globalCustTrigger.contains(e.target) && !globalCustDropdown.contains(e.target)) {
                    closeGlobalCustDropdown();
                }
            });
            globalCustClear.addEventListener('click', function(e) {
                e.stopPropagation();
                globalCustSearch.value = '';
                renderGlobalOptions('');
                globalCustSearch.focus();
            });
        }

        initGlobalCustSelect();
        initTocScrollSpy();
    </script>
</body>
</html>'''

    # Fill in first region's content
    replacements = {
        '__FIRST_USERNAME__': html.escape(first_header.get('username', '')),
        '__FIRST_TIME_RANGE__': first_header.get('time_range_label', '近1天'),
        '__TIMESTAMP__': timestamp_str,
        '__FIRST_HS__': str(first_header.get('health_score', 0)),
        '__FIRST_HS_COLOR__': first_header.get('health_score_color', 'var(--semi-color-primary)'),
        '__CUST_OPTIONS_JSON__': cust_options_json,
        '__SECTIONS_JSON__': sections_json,
        '__HEADER_JSON__': header_json,
    }

    for sid in SECTION_IDS:
        replacements['__SEC_' + sid.upper() + '__'] = first_sections.get(sid, '')

    for placeholder, value in replacements.items():
        html_template = html_template.replace(placeholder, value)

    return html_template


def generate_top10_html(results, core_ids=None):
    """生成TOP10告警HTML"""
    if not results:
        return '<div class="issue success"><div class="issue-content">暂无告警数据</div></div>'

    level_class = {'CRITICAL': 'high', 'MAJOR': 'medium'}

    html_parts = ['''
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
            <tr style="background:var(--semi-color-fill-1);text-align:left;">
                <th style="padding:10px 12px;width:50px;">排名</th>
                <th style="padding:10px 12px;">资源名称</th>
                <th style="padding:10px 12px;">资源ID</th>
                <th style="padding:10px 12px;">指标</th>
                <th style="padding:10px 12px;">服务</th>
                <th style="padding:10px 12px;width:80px;">级别</th>
                <th style="padding:10px 12px;width:60px;">触发次数</th>
                <th style="padding:10px 12px;">OA告警表达式</th>
                <th style="padding:10px 12px;">CES告警表达式</th>
            </tr>
        </thead>
        <tbody>''']

    for item in results:
        cls = level_class.get(item['level'], '')
        top3 = ' top-3' if item['rank'] <= 3 else ''
        core_badge = '<span class="priority high" style="font-size:11px;margin-left:0;margin-right:4px;">核心</span>' if item.get('is_core') else ''
        ces_expr = item.get('ces_expression', '未匹配')
        html_parts.append(f'''
            <tr style="border-bottom:1px solid var(--semi-color-border);">
                <td style="padding:10px 12px;"><span class="rank-badge{top3}">{item['rank']}</span></td>
                <td style="padding:10px 12px;">{core_badge}{html.escape(item['resource'])}<br><span style="color:var(--semi-color-text-2);font-size:12px;">{html.escape(item['resource_type'])}</span></td>
                <td style="padding:10px 12px;"><span style="color:var(--semi-color-text-2);font-size:12px;">{html.escape(item.get('resource_id', ''))}</span></td>
                <td style="padding:10px 12px;">{html.escape(item.get('metric_cn') or item['metric'])}</td>
                <td style="padding:10px 12px;">{html.escape(item['service'])}</td>
                <td style="padding:10px 12px;"><span class="priority {cls}">{item['level']}</span></td>
                <td style="padding:10px 12px;font-weight:600;">{item['count']}</td>
                <td style="padding:10px 12px;"><span style="color:var(--semi-color-text-2);font-size:12px;">{html.escape(item['expression'])}</span></td>
                <td style="padding:10px 12px;"><span style="color:var(--semi-color-text-2);font-size:12px;">{html.escape(ces_expr)}</span></td>
            </tr>''')

    html_parts.append('</tbody></table>')
    return ''.join(html_parts)


def generate_grouping_html(results):
    """生成路由分组建议HTML - AOM 路由分组"""
    html_parts = []

    html_parts.append('<div class="sub-section-title" id="governance-grouping">1. 路由分组建议<span class="card-header-icon" data-tooltip="AOM 告警降噪支持路由分组规则：将满足分组条件的告警合并为一个告警组，减少通知数量。&#10;分组参数：分组条件（告警源/资源类型/严重度等）+ 合并方式 + 等待参数（首次等待/变化等待/重复等待）。&#10;注意：CES 告警不经过 AOM 降噪链，路由分组仅对 AOM 告警生效。">ⓘ</span></div>')

    grouping_suggestions = results.get('grouping_suggestions', [])
    if grouping_suggestions:
        html_parts.append('<table class="data-table"><thead><tr><th>告警源</th><th>告警数</th><th>分组条件</th><th>合并方式</th><th>首次等待</th><th>变化等待</th><th>重复等待</th></tr></thead><tbody>')
        for item in grouping_suggestions[:15]:
            storm_tag = ' <span class="priority high">告警风暴</span>' if item.get('is_storm') else ''
            html_parts.append(f"<tr><td>{item['service']}{storm_tag}</td><td>{item['alarm_count']}</td><td>{item['group_condition']}</td><td>{item['merge_method']}</td><td>{item['first_wait']}</td><td>{item['change_wait']}</td><td>{item['repeat_wait']}</td></tr>")
        html_parts.append('</tbody></table>')
    else:
        html_parts.append('<div class="issue success"><div class="issue-content">未检测到需要分组的告警源</div></div>')

    # 告警风暴 issue 卡片
    alarm_storm = results.get('alarm_storm', [])
    if alarm_storm:
        for item in alarm_storm[:5]:
            sev = item.get('severity', 'high')
            priority_cls = 'high' if sev == 'severe' else 'medium'
            html_parts.append(f'''
            <div class="issue">
                <div class="issue-title">{item['metric']} <span class="priority {priority_cls}">{sev.upper()}</span></div>
                <div class="issue-content">资源: {item['resource']}, 类型: {item['resource_type']}, 服务: {item.get('service', '')}</div>
                <div class="issue-content">触发次数: {item['trigger_count']}次</div>
                <div class="suggestion">建议创建AOM路由分组规则：按告警源+资源类型分组，合并重复通知</div>
            </div>
            ''')

    return ''.join(html_parts)


def generate_dedup_html(results):
    """生成去重分析HTML - AOM 内置去重 + 重复告警统计"""
    html_parts = []

    html_parts.append('<div class="sub-section-title" id="governance-dedup">2. 去重分析<span class="card-header-icon" data-tooltip="AOM 告警降噪链内置去重环节：同一告警规则在同一资源上的重复告警会自动去重，无需手动配置。&#10;注意：CES 告警不经过 AOM 降噪链，CES 重复告警需通过迁移到 AOM 或在告警规则层面合并来解决。">ⓘ</span></div>')

    duplicate_rules = results.get('duplicate_rules', [])
    if duplicate_rules:
        html_parts.append('<table class="data-table"><thead><tr><th>指标</th><th>资源ID</th><th>资源类型</th><th>阈值详情</th></tr></thead><tbody>')
        for item in duplicate_rules[:10]:
            threshold_details = []
            for rule in item['rules']:
                threshold_details.append(f"{rule['threshold']}% ({rule['level']})")
            threshold_str = ", ".join(threshold_details)
            html_parts.append(f"<tr><td>{item['metric']}</td><td>{item['resource_id']}</td><td>{item['resource_type']}</td><td>{threshold_str}</td></tr>")
        html_parts.append('</tbody></table>')
        html_parts.append('''
        <div class="issue warning">
            <div class="issue-title">重复告警规则建议</div>
            <div class="issue-content">存在同一阈值不同级别的规则，建议合并为单条规则以减少重复告警。</div>
            <div class="issue-content">如为 CES 告警规则，考虑迁移到 AOM 以利用内置去重能力。</div>
        </div>
        ''')
    else:
        html_parts.append('<div class="issue success"><div class="issue-content">未检测到重复告警规则</div></div>')

    return ''.join(html_parts)


def generate_suppression_html(rule_results, correlation_results):
    """生成抑制规则建议HTML - 级别抑制 + 根因抑制"""
    html_parts = []

    html_parts.append('<div class="sub-section-title" id="governance-suppression">3. 抑制规则建议<span class="card-header-icon" data-tooltip="AOM 抑制规则：当源告警满足条件时，抑制目标告警的通知。支持级别抑制、根因抑制、依赖抑制。&#10;注意：根源告警恢复后，抑制规则自动失效，被抑制的衍生告警将恢复通知。">ⓘ</span></div>')

    # 级别抑制
    level_suppression = rule_results.get('level_suppression', [])
    if level_suppression:
        for item in level_suppression:
            html_parts.append(f'''
            <div class="issue warning">
                <div class="issue-title">级别抑制建议</div>
                <div class="issue-content">{item['issue']}</div>
                <div class="issue-content">源告警条件: {item.get('source_condition', '')}</div>
                <div class="issue-content">抑制条件: {item.get('suppress_condition', '')}</div>
                <div class="issue-content">作用范围: {item.get('scope', '')}</div>
                <div class="suggestion">{item['suggestion']}</div>
            </div>
            ''')

    # 根因抑制
    suppression_suggestions = correlation_results.get('suppression_suggestions', [])
    if suppression_suggestions:
        for item in suppression_suggestions[:10]:
            derived_str = ", ".join(item.get('derived', []))
            html_parts.append(f'''
            <div class="issue warning">
                <div class="issue-title">根因抑制建议 - {item['resource']}</div>
                <div class="issue-content">根因指标: <strong>{item['root_cause']}</strong></div>
                <div class="issue-content">衍生指标: {derived_str}</div>
                <div class="issue-content">源告警条件: {item.get('source_condition', '')}</div>
                <div class="issue-content">抑制条件: {item.get('suppress_condition', '')}</div>
                <div class="suggestion">{item['suggestion']}</div>
            </div>
            ''')

    if not level_suppression and not suppression_suggestions:
        html_parts.append('<div class="issue success"><div class="issue-content">未检测到需要抑制的告警</div></div>')

    return ''.join(html_parts)


def generate_silence_html(results):
    """生成静默规则建议HTML - 测试环境 + 低优先级 + 维护窗口"""
    html_parts = []

    html_parts.append('<div class="sub-section-title" id="governance-silence">4. 静默规则建议<span class="card-header-icon" data-tooltip="AOM 静默规则：在指定时间段内屏蔽满足过滤条件的告警通知。适用于测试环境、低优先级告警、维护窗口等场景。&#10;参数：过滤条件（告警级别/资源名称/告警源等）+ 静默时间段。">ⓘ</span></div>')

    silence_suggestions = results.get('silence_suggestions', [])
    if silence_suggestions:
        for suggestion in silence_suggestions:
            cls = 'warning' if suggestion['type'] == 'test_environment' else 'info'
            html_parts.append(f'''
            <div class="issue {cls}">
                <div class="issue-title">{suggestion['title']}</div>
                <div class="issue-content">{suggestion['description']}</div>
                <div class="issue-content">过滤条件: {suggestion.get('filter_condition', '')}</div>
                <div class="issue-content">静默时间段: {suggestion.get('silence_period', '')}</div>
            ''')
            for item in suggestion.get('items', [])[:10]:
                if 'alarm_count' in item:
                    html_parts.append(f"<div class='issue-content'>- {item['resource']}: {item['alarm_count']}次告警</div>")
                else:
                    html_parts.append(f"<div class='issue-content'>- {item['resource']}: {item.get('metric', '')}</div>")
            html_parts.append('</div>')
    else:
        html_parts.append('<div class="issue success"><div class="issue-content">未检测到需要静默的告警</div></div>')

    return ''.join(html_parts)

def generate_unresolved_issues_html(results):
    """生成长久未恢复告警HTML"""
    if not results or not results.get("total_unresolved"):
        return '<div class="issue success"><div class="issue-content">无长久未恢复告警（>=7天）</div></div>'


    html_parts = []
    by_level = results.get('by_level', {})
    total = results.get('total_unresolved', 0)

    level_class_map = {'danger': 'high', 'warning': 'medium', 'info': 'info'}
    level_order = ['>90天', '>30天', '>14天', '>7天']

    html_parts.append('<div class="sub-section-title" id="unresolved-stats">分级统计</div>')
    html_parts.append(f'<div class="issue info"><div class="issue-title">共 {total} 条未恢复告警（>=7天）</div>')

    for label in level_order:
        count = by_level.get(label, 0)
        if count > 0:
            cls = ''
            for lbl, _, css_cls in UNRESOLVED_LEVELS:
                if lbl == label:
                    cls = level_class_map.get(css_cls, '')
                    break
            html_parts.append(f'<div class="issue-content" style="margin-left:16px;">{label}: {count} 条</div>')
    html_parts.append('</div>')

    unresolved_list = results.get('list', [])
    if unresolved_list:
        html_parts.append('<div class="sub-section-title" id="unresolved-list">未恢复明细</div>')
        html_parts.append('''
        <table style="width:100%;border-collapse:collapse;font-size:14px;">
            <thead>
                <tr style="background:var(--semi-color-fill-1);text-align:left;">
                    <th style="padding:10px 12px;">资源</th>
                    <th style="padding:10px 12px;">指标</th>
                    <th style="padding:10px 12px;width:80px;">级别</th>
                    <th style="padding:10px 12px;width:80px;">持续天数</th>
                    <th style="padding:10px 12px;width:120px;">首次触发</th>
                </tr>
            </thead>
            <tbody>''')

        level_class = {'CRITICAL': 'high', 'MAJOR': 'medium'}
        for item in unresolved_list[:20]:
            cls = level_class.get(item['level'], '')
            dur_cls = level_class_map.get(item.get('duration_class', ''), '')
            html_parts.append(f'''
                <tr style="border-bottom:1px solid var(--semi-color-border);">
                    <td style="padding:10px 12px;">{html.escape(item['resource'])}<br><span style="color:var(--semi-color-text-2);font-size:12px;">{html.escape(item['resource_type'])} | {html.escape(item['service'])}</span></td>
<td style="padding:10px 12px;">{html.escape(item.get('metric_cn') or item['metric'])}</td>
                    <td style="padding:10px 12px;"><span class="priority {cls}">{item['level']}</span></td>
                    <td style="padding:10px 12px;"><span class="priority {dur_cls}">{item['duration_days']}天</span></td>
                    <td style="padding:10px 12px;font-size:12px;">{item['start_time']}</td>
                </tr>''')

        html_parts.append('</tbody></table>')

        if len(unresolved_list) > 20:
            html_parts.append(f'<div class="issue-content" style="margin-top:8px;color:var(--semi-color-text-2);">...共 {len(unresolved_list)} 条，仅展示前20条</div>')

    return ''.join(html_parts)


def generate_health_score_details_html(health_score):
    """生成健康度评分明细HTML"""
    if not health_score:
        return '<div class="issue success"><div class="issue-content">暂无健康度评分数据</div></div>'

    dims = [
        (
            '告警总量',
            health_score['volume'],
            'ⓘ',
            '统计周期内告警事件总数，按规模分档评分\n≤50:100\n≤200:80\n≤500:60\n≤1000:40\n>1000:20'
        ),
        (
            '严重告警占比',
            health_score['severity'],
            'ⓘ',
            'CRITICAL 告警占总告警比例，比例越高分越低\n0%:100\n≤5%:85\n≤10%:70\n≤20%:50\n>20%:30'
        ),
        (
            '告警收敛率',
            health_score['convergence'],
            'ⓘ',
            '基于告警风暴数量评分，每个风暴扣10分\n告警风暴=同一资源同一指标短时间内高频触发\n0个:100\n1个:90\n2个:80\n3个:70\n5个:50\n≥10个:0'
        ),
        (
            '长久未恢复告警',
            health_score['unresolved'],
            'ⓘ',
            '持续7天以上未恢复的告警数\n0:100\n≤3:80\n≤10:60\n≤20:40\n>20:20'
        ),
        (
            '每日告警趋势',
            health_score['trend'],
            'ⓘ',
            '最近两天告警总量对比\n下降:100\n持平:70（数据不足默认）\n上升:40'
        ),
    ]

    html_parts = ['<div class="score-dimensions">']
    for label, value, icon, tooltip in dims:
        color = score_color(value)
        html_parts.append(f'''
        <div class="score-dim">
            <span class="score-dim-label">{label}<span class="score-dim-icon" data-tooltip="{tooltip}">{icon}</span></span>
            <div class="score-dim-bar"><div class="score-dim-fill" style="width:{value}%;background:{color};"></div></div>
            <span class="score-dim-value">{value}</span>
        </div>''')
    html_parts.append('</div>')
    return ''.join(html_parts)


def _generate_pie_chart_svg(data_items, colors, size=220):
    """生成饼图SVG。data_items: [(label, count), ...], colors: [color_str, ...]"""
    import math
    total = sum(c for _, c in data_items)
    if total == 0:
        return '<div class="issue success"><div class="issue-content">暂无告警数据</div></div>'

    cx, cy, r = size / 2, size / 2, size / 2 - 10
    svg_parts = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="display:block;margin:0 auto;">']

    angle = -90  # start from top
    for i, (label, count) in enumerate(data_items):
        if count == 0:
            continue
        pct = count / total
        sweep = pct * 360
        end_angle = angle + sweep
        # Convert to radians
        a1 = math.radians(angle)
        a2 = math.radians(end_angle)
        x1 = cx + r * math.cos(a1)
        y1 = cy + r * math.sin(a1)
        x2 = cx + r * math.cos(a2)
        y2 = cy + r * math.sin(a2)
        large_arc = 1 if sweep > 180 else 0
        color = colors[i % len(colors)]
        # Path: move to center, line to start, arc to end, close
        path = f'M {cx:.1f} {cy:.1f} L {x1:.1f} {y1:.1f} A {r} {r} 0 {large_arc} 1 {x2:.1f} {y2:.1f} Z'
        svg_parts.append(f'<path d="{path}" fill="{color}" stroke="white" stroke-width="2"/>')
        angle = end_angle

    svg_parts.append('</svg>')
    return ''.join(svg_parts)


def _generate_pie_legend_html(data_items, colors, total):
    """生成饼图图例HTML"""
    parts = ['<div style="display:flex;flex-wrap:wrap;gap:12px 24px;justify-content:center;margin-top:12px;font-size:13px;">']
    for i, (label, count) in enumerate(data_items):
        if count == 0:
            continue
        pct = round(count / total * 100, 1) if total > 0 else 0
        color = colors[i % len(colors)]
        parts.append(f'<div style="display:flex;align-items:center;gap:6px;"><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{color};"></span>{html.escape(str(label))} <strong>{count}</strong> ({pct}%)</div>')
    parts.append('</div>')
    return ''.join(parts)


def generate_level_distribution_html(alarms):
    """生成告警级别分布HTML（饼图）"""
    total = len(alarms)
    if total == 0:
        return '<div class="issue success"><div class="issue-content">暂无告警数据</div></div>'

    critical = sum(1 for a in alarms if a.get('alarm_level', '') == 'CRITICAL')
    major = sum(1 for a in alarms if a.get('alarm_level', '') == 'MAJOR')
    minor = sum(1 for a in alarms if a.get('alarm_level', '') == 'MINOR')

    data_items = [('CRITICAL', critical), ('MAJOR', major), ('MINOR', minor)]
    colors = ['#F93920', '#FC8800', '#3BB346']

    svg = _generate_pie_chart_svg(data_items, colors)
    legend = _generate_pie_legend_html(data_items, colors, total)
    return f'<div style="text-align:center;">{svg}{legend}</div>'


def generate_service_distribution_html(alarms):
    """生成告警服务类型分布HTML（饼图）"""
    total = len(alarms)
    if total == 0:
        return '<div class="issue success"><div class="issue-content">暂无告警数据</div></div>'

    service_counts = defaultdict(int)
    for alarm in alarms:
        svc = alarm.get('service', 'Unknown')
        service_counts[svc] += 1

    sorted_services = sorted(service_counts.items(), key=lambda x: x[1], reverse=True)
    data_items = [(svc, cnt) for svc, cnt in sorted_services]
    colors = ['#0064FA', '#0095EE', '#3BB346', '#FC8800', '#F93920', '#6B7075', '#A855F7', '#EC4899']

    svg = _generate_pie_chart_svg(data_items, colors)
    legend = _generate_pie_legend_html(data_items, colors, total)
    return f'<div style="text-align:center;">{svg}{legend}</div>'


def generate_daily_trend_html(daily_data):
    """生成每日告警趋势HTML（曲线图+表格）"""
    if not daily_data:
        return '<div class="issue success"><div class="issue-content">暂无每日告警趋势数据</div></div>'

    max_val = max(max(d['total'], d['active']) for d in daily_data) or 1
    n = len(daily_data)

    svg_w, svg_h = 860, 240
    pad_left, pad_right = 50, 20
    pad_top, pad_bottom = 20, 40
    plot_w = svg_w - pad_left - pad_right
    plot_h = svg_h - pad_top - pad_bottom

    if n == 1:
        xs = [(pad_left + plot_w) / 2]
    else:
        x_step = plot_w / (n - 1)
        xs = [pad_left + i * x_step for i in range(n)]

    def y_pos(val):
        return pad_top + plot_h - (val / max_val) * plot_h

    def smooth_path(pts, tension=0.2, y_min=None, y_max=None):
        if len(pts) < 2:
            return ''
        if len(pts) == 2:
            return f'M {pts[0][0]:.1f},{pts[0][1]:.1f} L {pts[1][0]:.1f},{pts[1][1]:.1f}'
        path = [f'M {pts[0][0]:.1f},{pts[0][1]:.1f}']
        for i in range(len(pts) - 1):
            p0 = pts[i - 1] if i > 0 else pts[i]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[i + 2] if i + 2 < len(pts) else pts[i + 1]
            c1x = p1[0] + (p2[0] - p0[0]) * tension
            c1y = p1[1] + (p2[1] - p0[1]) * tension
            c2x = p2[0] - (p3[0] - p1[0]) * tension
            c2y = p2[1] - (p3[1] - p1[1]) * tension
            if y_min is not None:
                c1y = max(c1y, y_min)
                c2y = max(c2y, y_min)
            if y_max is not None:
                c1y = min(c1y, y_max)
                c2y = min(c2y, y_max)
            path.append(f'C {c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}')
        return ' '.join(path)

    total_pts, active_pts = [], []
    circles, labels = [], []

    for i, d in enumerate(daily_data):
        x = xs[i]
        yt, ya = y_pos(d['total']), y_pos(d['active'])
        total_pts.append((x, yt))
        active_pts.append((x, ya))
        circles.append(f'<circle cx="{x:.1f}" cy="{yt:.1f}" r="4" fill="#3b82f6" stroke="#fff" stroke-width="1.5"/>')
        circles.append(f'<circle cx="{x:.1f}" cy="{ya:.1f}" r="4" fill="#ef4444" stroke="#fff" stroke-width="1.5"/>')
        labels.append(f'<text x="{x:.1f}" y="{yt - 12:.1f}" text-anchor="middle" font-size="11" font-weight="600" fill="#3b82f6">{d["total"]}</text>')
        labels.append(f'<text x="{x:.1f}" y="{svg_h - 12:.1f}" text-anchor="middle" font-size="11" fill="#999">{d["date"][5:]}</text>')

    grid = []
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        gy = pad_top + plot_h - frac * plot_h
        gv = round(max_val * frac)
        grid.append(f'<line x1="{pad_left}" y1="{gy:.1f}" x2="{svg_w - pad_right}" y2="{gy:.1f}" stroke="#e0e0e0" stroke-dasharray="3,3"/>')
        grid.append(f'<text x="{pad_left - 8}" y="{gy + 4:.1f}" text-anchor="end" font-size="10" fill="#999">{gv}</text>')

    svg = [f'<svg viewBox="0 0 {svg_w} {svg_h}" style="display:block;margin:0 auto;max-width:{svg_w}px;">']
    svg.extend(grid)
    svg.append(f'<line x1="{pad_left}" y1="{pad_top + plot_h}" x2="{svg_w - pad_right}" y2="{pad_top + plot_h}" stroke="#d0d0d0"/>')
    if n >= 2:
        y_bottom = pad_top + plot_h
        svg.append(f'<path d="{smooth_path(total_pts, y_max=y_bottom)}" fill="none" stroke="#3b82f6" stroke-width="2"/>')
        svg.append(f'<path d="{smooth_path(active_pts, y_max=y_bottom)}" fill="none" stroke="#ef4444" stroke-width="2"/>')
    svg.extend(circles)
    svg.extend(labels)
    svg.append('</svg>')

    html_parts = [f'<div style="padding:16px 0;text-align:center;">{"".join(svg)}</div>']

    html_parts.append('''
    <div style="display:flex;gap:24px;justify-content:center;margin-top:8px;font-size:12px;color:var(--semi-color-text-2);">
        <span><span style="display:inline-block;width:12px;height:12px;background:#3b82f6;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>总量</span>
        <span><span style="display:inline-block;width:12px;height:12px;background:#ef4444;border-radius:2px;vertical-align:middle;margin-right:4px;"></span>未恢复</span>
    </div>''')

    html_parts.append('''
    <table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:16px;">
        <thead>
            <tr style="background:var(--semi-color-fill-1);text-align:left;">
                <th style="padding:10px 12px;">日期</th>
                <th style="padding:10px 12px;">告警事件数</th>
                <th style="padding:10px 12px;">恢复数</th>
                <th style="padding:10px 12px;">未恢复数</th>
                <th style="padding:10px 12px;">Critical</th>
                <th style="padding:10px 12px;">Major</th>
                <th style="padding:10px 12px;">峰值小时</th>
            </tr>
        </thead>
        <tbody>''')

    for d in daily_data:
        html_parts.append(f'''
            <tr style="border-bottom:1px solid var(--semi-color-border);">
                <td style="padding:10px 12px;">{d['date']}</td>
                <td style="padding:10px 12px;font-weight:600;">{d['total']}</td>
                <td style="padding:10px 12px;color:var(--semi-color-success);">{d['recovered']}</td>
                <td style="padding:10px 12px;color:var(--semi-color-danger);">{d['active']}</td>
                <td style="padding:10px 12px;">{d['critical']}</td>
                <td style="padding:10px 12px;">{d['major']}</td>
                <td style="padding:10px 12px;">{d['peak_hour']}</td>
            </tr>''')

    html_parts.append('</tbody></table>')
    return ''.join(html_parts)


def generate_temporal_correlation_html(temporal_results):
    """生成告警时序关联性分析HTML"""
    groups = temporal_results.get('co_occurrence_groups', [])
    window_minutes = temporal_results.get('window_minutes', 15)
    min_windows = temporal_results.get('min_windows', 2)

    if not groups:
        return f'<div class="issue success"><div class="issue-content">基于{window_minutes}分钟时间窗，未发现共现告警组合</div></div>'

    html_parts = [f'<div class="dimension-subtitle">基于{window_minutes}分钟时间窗，识别在至少{min_windows}个时间窗内同时出现的告警组合</div>']

    strength_class = {'high': 'high', 'medium': 'medium', 'low': 'info'}
    strength_label = {'high': 'HIGH', 'medium': 'MEDIUM', 'low': 'LOW'}

    for group in groups[:10]:
        cls = strength_class.get(group['strength'], 'info')
        badge = strength_label.get(group['strength'], 'LOW')
        member_lines = []
        for m in group['members']:
            member_lines.append(f'<div class="issue-content" style="margin-left:16px;">- {html.escape(m["resource"])} | {html.escape(m["metric"])} | {html.escape(m["service"])}</div>')

        html_parts.append(f'''
        <div class="issue warning">
            <div class="issue-title">关联组 {group['group_id']} <span class="priority {cls}">{badge}</span></div>
            <div class="issue-content">共现次数: {group['co_occurrence']}，成员数: {group['member_count']}</div>
            {"".join(member_lines)}
            <div class="suggestion">建议排查这些告警的根因关联，配置抑制规则减少衍生告警通知</div>
        </div>''')

    return ''.join(html_parts)


def generate_dependency_convergence_html():
    """生成依赖关系收敛建议HTML（静态内容）"""
    return '''
    <div class="issue info">
        <div class="issue-title">建议配置的依赖关系</div>
        <div class="issue-content" style="margin-left:12px;">
            <div>- 主机宕机 → 静默该主机上所有虚拟机/容器的告警</div>
            <div>- 基础服务异常 → 静默使用该服务的应用告警</div>
            <div>- 数据库异常 → 静默使用该数据库的应用告警</div>
            <div>- 网络异常 → 静默因网络不可达导致的服务告警</div>
        </div>
    </div>'''


def generate_action_list_html(actions):
    """生成单个优先级建议列表HTML"""
    if not actions:
        return '<div class="issue-content" style="color:var(--semi-color-text-2);">暂无建议</div>'

    html_parts = ['<ul class="action-list">']
    for i, action in enumerate(actions, 1):
        html_parts.append(f'''
        <li class="action-item">
            <span class="action-num">{i}</span>
            <div class="action-content">
                <div class="action-title">{html.escape(action['title'])}</div>
                <div class="action-desc">{html.escape(action['desc'])}</div>
            </div>
        </li>''')
    html_parts.append('</ul>')
    return ''.join(html_parts)


def generate_actions_summary_html(action_lists):
    """生成降噪建议汇总卡片HTML"""
    if not action_lists:
        return ''

    html_parts = ['''
    <div class="card" id="actions">
        <h2 class="card-header">降噪建议汇总（按优先级排序）</h2>
        <div class="sub-section">
            <div class="sub-section-title">高优先级 <span class="priority high">本周处理</span></div>''']
    html_parts.append(generate_action_list_html(action_lists.get('high', [])))
    html_parts.append('''
        </div>
        <div class="sub-section">
            <div class="sub-section-title">中优先级 <span class="priority medium">本月处理</span></div>''')
    html_parts.append(generate_action_list_html(action_lists.get('medium', [])))
    html_parts.append('''
        </div>
        <div class="sub-section">
            <div class="sub-section-title">长期优化 <span class="priority low">季度规划</span></div>''')
    html_parts.append(generate_action_list_html(action_lists.get('low', [])))
    html_parts.append('''
        </div>
    </div>''')

    return ''.join(html_parts)


def _run_analysis_for_region(alarms, username, time_range, alarm_rules, core_ids):
    """对单个区域运行全部分析函数，返回所有分析结果"""
    print(f"  Analyzing alarm rules (a + b)...")
    rule_results = analyze_alarm_rules(alarms)

    print(f"  Analyzing alarm suppression (c)...")
    suppression_results = analyze_alarm_suppression(alarms)

    print(f"  Analyzing alarm convergence (d + e)...")
    convergence_results = analyze_alarm_convergence(alarms)

    print(f"  Analyzing alarm correlation (f)...")
    correlation_results = analyze_alarm_correlation(alarms)

    print(f"  Analyzing unresolved alarms...")
    unresolved_results = analyze_unresolved(alarms, None)

    print(f"  Analyzing daily trend...")
    daily_trend = analyze_daily_trend(alarms, time_range)

    print(f"  Analyzing alarm temporal correlation...")
    temporal_correlation = analyze_alarm_temporal_correlation(alarms)

    print(f"  Calculating health score...")
    health_score = calculate_health_score(alarms, convergence_results, unresolved_results, daily_trend)
    print(f"  Health score: {health_score['total']}/100")
    print(f"  Building action lists...")
    action_lists = build_action_lists(
        convergence_results, unresolved_results, rule_results,
        correlation_results, temporal_correlation, suppression_results
    )

    return {
        'rule_results': rule_results,
        'suppression_results': suppression_results,
        'convergence_results': convergence_results,
        'correlation_results': correlation_results,
        'unresolved_results': unresolved_results,
        'daily_trend': daily_trend,
        'temporal_correlation': temporal_correlation,
        'health_score': health_score,
        'action_lists': action_lists,
    }


def main_batch(args):
    """多区域分析入口"""
    from core_resources import load_core_resources, is_core_resource

    print(f"Loading multi-region alarm data from: {args.input}")
    region_data = load_multi_region_data(args.input)

    if region_data is None:
        print("Error: Input file is not in multi-region format. Expected {\"alarms\": {...}} structure.")
        return

    print(f"Loaded {len(region_data)} regions: {list(region_data.keys())}")

    multi_rules = load_multi_region_rules(args.input)
    if multi_rules:
        print(f"Loaded multi-region CES alarm rules for {len(multi_rules)} regions")
    else:
        print("ces_alarm_rules.json not found, CES expression column will show '未匹配'")

    # 始终加载核心资源标记表，按区域过滤
    core_resource_map = load_core_resources(args.core_resources)
    print(f"Loaded core resources for {len(core_resource_map)} regions")

    region_sections = {}
    region_headers = {}

    # 收集所有区域数据用于 ALL 汇总
    all_alarms = []
    all_rules = []
    all_core_ids = set()
    all_time_range = {}

    for region_name, (alarms, username, time_range) in region_data.items():
        print(f"\n=== Analyzing region: {region_name} ===")
        print(f"  Loaded {len(alarms)} alarms")

        region_alarm_rules = None
        if multi_rules and region_name in multi_rules:
            region_alarm_rules = multi_rules[region_name]
            print(f"  Loaded {len(region_alarm_rules)} alarm rules")

        # 按区域获取核心资源，过滤告警
        core_ids = core_resource_map.get(region_name, set())
        print(f"  Core resources for {region_name}: {len(core_ids)}")
        filtered_alarms = [a for a in alarms if is_core_resource(a, core_ids)]
        print(f"  Filtered to {len(filtered_alarms)} core resource alarms (from {len(alarms)} total)")
        alarms = filtered_alarms

        analysis = _run_analysis_for_region(
            alarms, username, time_range, region_alarm_rules, core_ids
        )

        sections, header_info = generate_region_sections(
            alarms, username, time_range,
            analysis['rule_results'],
            analysis['suppression_results'],
            analysis['convergence_results'],
            analysis['correlation_results'],
            analysis['unresolved_results'],
            core_ids,
            analysis['health_score'],
            analysis['daily_trend'],
            analysis['temporal_correlation'],
            analysis['action_lists'],
            region_alarm_rules
        )

        region_sections[region_name] = sections
        region_headers[region_name] = header_info

        # 累积用于 ALL 汇总
        all_alarms.extend(alarms)
        if region_alarm_rules:
            all_rules.extend(region_alarm_rules)
        all_core_ids |= core_ids
        if not all_time_range and time_range:
            all_time_range = time_range

    # 构建 ALL（所有区域）汇总
    ALL_KEY = 'ALL'
    all_username = 'ALL（所有区域）'
    print(f"\n=== Analyzing region: {ALL_KEY} (所有区域汇总) ===")
    print(f"  Combined alarms: {len(all_alarms)}")
    print(f"  Combined rules: {len(all_rules)}")
    print(f"  Combined core resources: {len(all_core_ids)}")
    all_analysis = _run_analysis_for_region(
        all_alarms, all_username, all_time_range,
        all_rules if all_rules else None, all_core_ids
    )
    all_sections, all_header_info = generate_region_sections(
        all_alarms, all_username, all_time_range,
        all_analysis['rule_results'],
        all_analysis['suppression_results'],
        all_analysis['convergence_results'],
        all_analysis['correlation_results'],
        all_analysis['unresolved_results'],
        all_core_ids,
        all_analysis['health_score'],
        all_analysis['daily_trend'],
        all_analysis['temporal_correlation'],
        all_analysis['action_lists'],
        all_rules if all_rules else None
    )
    region_sections[ALL_KEY] = all_sections
    region_headers[ALL_KEY] = all_header_info

    global_cust_options = [
        {"value": ALL_KEY, "label": "ALL（所有区域）"}
    ] + [
        {"value": name, "label": name}
        for name in sorted(region_data.keys())
    ]

    print(f"\nGenerating multi-region HTML report...")
    html_content = generate_multi_region_html_report(
        region_sections, region_headers, global_cust_options
    )

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Multi-region report generated: {args.output}")
    print(f"Regions: {len(region_data)}")


def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description='告警降噪分析工具')
        parser.add_argument('--input', '-i', default=str(Path(WORKSPACE_DIR) / 'alarm_result.json'), help='输入告警JSON文件路径（默认: <WORKSPACE_DIR>/alarm_result.json）')
        parser.add_argument('--output', '-o', default=str(Path(WORKSPACE_DIR) / 'alarm-noise-report.html'), help='输出HTML报告路径（默认: <WORKSPACE_DIR>/alarm-noise-report.html）')
        parser.add_argument('--core-resources', dest='core_resources', default=MARKING_TABLE_PATH, help='核心资源标记表xlsx路径（默认: assets/关键资源标记表.xlsx）')
        args = parser.parse_args()

    # 检测多区域格式
    multi_data = load_multi_region_data(args.input)
    if multi_data is None:
        print("Error: Input file is not in multi-region format. Expected {\"alarms\": {...}} structure.")
        return

    main_batch(args)


if __name__ == '__main__':
    main()
