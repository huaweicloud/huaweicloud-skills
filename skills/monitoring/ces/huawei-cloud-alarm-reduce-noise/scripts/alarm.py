#!/usr/bin/env python3
"""
告警数据采集脚本（华为云 CES + AOM 版本）

通过 hcloud CLI 从华为云 CES 和 AOM 采集告警历史和规则数据。
认证方式：AK/SK 环境变量（HW_ACCESS_KEY / HW_SECRET_KEY）。
采集维度：按区域（region）采集，替代原按租户（tenant）采集。

输出格式兼容：alarm_result.json 仍用 {alarms: {region_name: {...}}} 结构。
"""

import sys

from datetime import datetime, timedelta
from alarm_api import (
    fetch_all_alert_history,
    fetch_metric_alarms,
    fetch_metric_alarm_resources,
)
from tool import set_json_dict, write_data_to_json
from config import get_region
from workspace import WORKSPACE_DIR, MARKING_TABLE_PATH


def _collect_single_region(region: str, start_time: datetime, end_time: datetime):
    """采集单个区域的告警数据和告警规则（内部函数）

    :param region: 区域 ID（如 cn-south-1）
    :param start_time: 查询起始时间
    :param end_time: 查询截止时间
    :return: (alarm_data_dict, alarm_rules_list)
    """
    print(f"  正在采集告警历史（CES ListAlarmHistories/v2）...")
    alarm_history = fetch_all_alert_history(
        region=region, start_time=start_time, end_time=end_time
    )

    now = end_time if end_time is not None else (
        datetime.now() - timedelta(days=1)
    ).replace(hour=23, minute=59, second=59, microsecond=0)
    actual_start = start_time if start_time is not None else now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    time_range = {
        "start": actual_start.strftime('%Y-%m-%d %H:%M:%S'),
        "end": now.strftime('%Y-%m-%d %H:%M:%S'),
        "label": f"{actual_start.strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"
    }

    alarm_data = {
        "username": region,
        "region": region,
        "time_range": time_range,
        "alarm_history": alarm_history,
        "alarm_num": len(alarm_history)
    }

    print(f"  正在采集告警规则（CES ListAlarmRules + AOM ListMetricOrEventAlarmRule）...")
    alarm_rules = fetch_metric_alarms(region=region)

    # 对非 ALL_INSTANCE 的规则，获取关联资源列表
    multi_rules = [r for r in alarm_rules if r.get("type") != "ALL_INSTANCE"]
    if multi_rules:
        print(f"  正在获取 {len(multi_rules)} 条非全实例规则的关联资源...")
        for rule in multi_rules:
            alarm_id = rule.get("alarm_id") or rule.get("alarm_rule_id", "")
            if alarm_id:
                try:
                    resources = fetch_metric_alarm_resources(alarm_id=alarm_id, region=region)
                    rule["resource_list"] = resources or []
                except Exception as e:
                    print(f"  警告: 获取规则 {alarm_id} 关联资源失败: {e}")
                    rule["resource_list"] = []

    return alarm_data, alarm_rules


def alarm_batch(regions: list, start_time: datetime = None, end_time: datetime = None, output: str = None):
    """批量采集多个区域的告警数据

    :param regions: 区域 ID 列表（如 ['cn-south-1', 'cn-north-4']）
    :param start_time: 查询起始时间
    :param end_time: 查询截止时间
    :param output: 输出文件路径
    :return: 汇总结果
    """
    all_alarms = {}
    all_rules = {}

    for region in regions:
        print(f"\n=== 采集区域: {region} ===")
        try:
            alarm_data, alarm_rules = _collect_single_region(
                region, start_time, end_time
            )
            all_alarms[region] = alarm_data
            all_rules[region] = alarm_rules
            print(f"  告警数: {alarm_data['alarm_num']}, 规则数: {len(alarm_rules)}")
        except Exception as e:
            print(f"  采集失败: {e}")
            all_alarms[region] = {
                "username": region,
                "region": region,
                "time_range": {},
                "alarm_history": [],
                "alarm_num": 0,
                "error": str(e)
            }
            all_rules[region] = []

    output_path = output or (WORKSPACE_DIR + '/alarm_result.json')
    set_json_dict(output_path, data={"alarms": all_alarms})

    rules_path = WORKSPACE_DIR + '/ces_alarm_rules.json'
    write_data_to_json(all_rules, rules_path)

    total_alarms = sum(d.get("alarm_num", 0) for d in all_alarms.values())
    total_rules = sum(len(r) for r in all_rules.values())
    return {
        "status": "success",
        "region_count": len(regions),
        "total_alarm_num": total_alarms,
        "total_rule_num": total_rules
    }


def filter_alarm_fields(alarm_history: list) -> list:
    """过滤告警历史列表，保留指定属性"""
    filtered_list = []
    keep_keys = [
        "id", "region", "service", "namespace",
        "metric_expression", "metric_expression_ch", "metric_name",
        "alarm_id", "alarm_level", "alarm_name"
    ]

    for alarm in alarm_history:
        filtered_alarm = {}

        for key in keep_keys:
            if key in alarm:
                filtered_alarm[key] = alarm[key]

        if "meta_data" in alarm and isinstance(alarm["meta_data"], dict):
            filtered_alarm["meta_data"] = {
                "alarmID": alarm["meta_data"].get("alarmID")
            }

        if "alarm_resource" in alarm and isinstance(alarm["alarm_resource"], dict):
            ar = alarm["alarm_resource"]
            filtered_alarm["alarm_resource"] = {
                "resourceType": ar.get("resourceType"),
                "dimValue": ar.get("dimValue"),
                "resourceId": ar.get("resourceId"),
                "resourceName": ar.get("resourceName")
            }

        filtered_list.append(filtered_alarm)

    return filtered_list


if __name__ == "__main__":
    import argparse
    from core_resources import load_core_regions
    parser = argparse.ArgumentParser(description='告警数据采集（华为云 CES + AOM）')
    parser.add_argument('-o', '--output', default=None,
                        help='输出JSON文件路径（默认: <WORKSPACE_DIR>/alarm_result.json）')
    parser.add_argument('--days', type=int, default=None,
                        help='查询近N天的告警数据（如 --days 7 表示近7天）')
    parser.add_argument('--start-date', dest='start_date', default=None,
                        help='查询起始日期（格式：YYYY-MM-DD）')
    parser.add_argument('--end-date', dest='end_date', default=None,
                        help='查询截止日期（格式：YYYY-MM-DD）')
    args = parser.parse_args()

    # 从核心资源标记表自动读取区域列表
    regions = load_core_regions(MARKING_TABLE_PATH)
    if not regions:
        print("❌ 关键资源标记表为空，无法确定采集区域。")
        print(f"   文件路径: {MARKING_TABLE_PATH}")
        print("   请在表中填入数据，列说明：")
        print("     Region        - 资源所在区域（如 cn-south-1）")
        print("     resource_type - 资源类型（如 ECS、RDS）")
        print("     resource_id   - 资源ID（如 46ef6243-xxxx-xxxx-xxxx-xxxxxxxxxxxx）")
        print('     是否核心业务   - 填"是"标记为核心资源')
        print("   填好后重新执行本流程。")
        sys.exit(1)
    else:
        print(f"从标记表读取到 {len(regions)} 个区域: {regions}")

    # 确定时间范围
    start_time = None
    end_time = None

    if args.start_date and args.end_date:
        start_time = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_time = datetime.strptime(args.end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    elif args.days:
        end_time = (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
        start_time = (datetime.now() - timedelta(days=args.days)).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        end_time = (datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
        start_time = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    result = alarm_batch(regions, start_time=start_time, end_time=end_time, output=args.output)
    print(f"\n采集完成: {result['region_count']}个区域, 共{result['total_alarm_num']}条告警, {result['total_rule_num']}条规则")
