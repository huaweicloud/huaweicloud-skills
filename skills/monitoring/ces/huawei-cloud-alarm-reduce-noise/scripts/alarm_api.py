#!/usr/bin/env python3
"""
华为云 CES + AOM 告警 API 封装。
通过 hcloud CLI 调用华为云 API，使用 AK/SK 认证（环境变量）。

替代原 CloudScope OA 平台的 HTTP 接口，所有函数通过 subprocess 调用 hcloud CLI。
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from config import get_region, get_project_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# CES level int → 字符串级别（与 analyze_alarm.py 的 ALARM_LEVEL_TO_CES_LEVEL 对应）
CES_LEVEL_TO_STR = {
    1: 'CRITICAL',
    2: 'MAJOR',
    3: 'MINOR',
    4: 'INFO',
}


def _run_hcloud(service: str, operation: str, region: str, params: dict = None) -> dict:
    """调用 hcloud CLI 并返回解析后的 JSON 结果。

    Args:
        service: 云服务名（如 CES、AOM、IAM）
        operation: 操作名（如 ListAlarmHistories/v2）
        region: 区域 ID
        params: 额外参数字典

    Returns:
        解析后的 JSON 字典，失败时返回空字典。
    """
    cmd = ["hcloud", service, operation, f"--cli-region={region}"]

    pid = get_project_id(region)
    if pid:
        cmd.append(f"--cli-project-id={pid}")

    if params:
        for key, value in params.items():
            if value is not None:
                cmd.append(f"--{key}={value}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("hcloud %s %s failed (rc=%d): %s",
                         service, operation, result.returncode, result.stderr.strip()[:500])
            return {}

        stdout = result.stdout.strip()
        if not stdout:
            return {}
        return json.loads(stdout)

    except subprocess.TimeoutExpired:
        logger.error("hcloud %s %s timed out", service, operation)
        return {}
    except json.JSONDecodeError as e:
        logger.error("hcloud %s %s JSON decode error: %s", service, operation, e)
        return {}
    except Exception as e:
        logger.error("hcloud %s %s error: %s", service, operation, e)
        return {}


def _format_time_for_ces(dt: datetime) -> str:
    """将 datetime 格式化为 CES API 要求的 ISO 8601 格式。

    例: 2022-02-10T10:05:46+08:00
    """
    return dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')


def _map_alarm_history(raw: dict, region: str) -> dict:
    """将 CES ListAlarmHistories/v2 返回的告警记录映射为 analyze_alarm.py 期望的格式。

    CES v2 API 实际返回字段:
      record_id, alarm_id, name, status, level(int 1-4), type,
      begin_time/last_alarm_time/first_alarm_time (ISO 8601),
      metric{namespace, dimensions[], metric_name},
      condition{comparison_operator, value, unit, ...},
      additional_info{resource_id, resource_name, event_id}

    关键字段映射:
      CES level (int 1-4) → alarm_level (str CRITICAL/MAJOR/MINOR/INFO)
      CES metric.namespace → namespace / service
      CES metric.metric_name → metric_name
      CES additional_info.resource_id → alarm_resource.resourceId
      CES begin_time → alarm_start_time (毫秒时间戳)
      CES last_alarm_time → last_occur_time (毫秒时间戳)
      region 从查询参数注入
    """
    from datetime import datetime, timedelta

    def _iso_to_ms(ts_str):
        """将 ISO 8601 字符串转为毫秒时间戳，失败返回 0。"""
        if not ts_str or not isinstance(ts_str, str):
            return 0
        try:
            dt = datetime.fromisoformat(ts_str)
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            return 0

    # 级别映射: int → str
    level_int = raw.get('level')
    if isinstance(level_int, int) and level_int in CES_LEVEL_TO_STR:
        alarm_level = CES_LEVEL_TO_STR[level_int]
    elif isinstance(level_int, str):
        alarm_level = level_int.upper()
    else:
        alarm_level = 'INFO'

    # 从嵌套 metric 对象提取 namespace 和 metric_name
    metric_obj = raw.get('metric') or {}
    namespace = metric_obj.get('namespace', '')
    metric_name = metric_obj.get('metric_name', '')
    dimensions = metric_obj.get('dimensions') or []

    # 从 additional_info 提取资源信息，回退到 dimensions
    add_info = raw.get('additional_info') or {}
    resource_id = add_info.get('resource_id', '')
    resource_name = add_info.get('resource_name', '')

    # dimValue: 取第一个维度的 value 作为资源标识兜底
    dim_value = dimensions[0].get('value', '') if dimensions else ''
    if not resource_id:
        resource_id = dim_value
    if not resource_name:
        resource_name = dim_value

    # 资源类型从 namespace 推导 (SYS.ECS → ECS, SYS.CDN → CDN)
    resource_type = namespace.split('.')[-1] if namespace else ''

    # 构造 alarm_resource
    alarm_resource = {
        'resourceId': resource_id,
        'resourceName': resource_name,
        'resourceType': resource_type,
        'dimValue': dim_value,
    }

    # 构造 meta_data
    meta_data = {
        'alarmID': raw.get('alarm_id', ''),
    }

    # 时间字段: CES v2 返回 ISO 8601 字符串，转为毫秒时间戳
    alarm_start_time = _iso_to_ms(raw.get('begin_time'))
    last_occur_time = _iso_to_ms(raw.get('last_alarm_time'))

    # alarm_trigger_time: 累计触发次数，CES v2 单条记录代表一次触发
    alarm_trigger_time = 1

    mapped = {
        'id': raw.get('record_id', ''),
        'alarm_id': raw.get('alarm_id', ''),
        'alarm_name': raw.get('name', ''),
        'alarm_level': alarm_level,
        'alarm_status': raw.get('status', ''),
        'alarm_type': raw.get('type', 'metric'),
        'metric_name': metric_name,
        'metric_expression': '',
        'metric_expression_ch': '',
        'service': namespace.split('.')[-1] if namespace else '',
        'region': region,
        'namespace': namespace,
        'alarm_start_time': alarm_start_time,
        'last_occur_time': last_occur_time,
        'alarm_trigger_time': alarm_trigger_time,
        'alarm_resource': alarm_resource,
        'meta_data': meta_data,
        'enterprise_project_id': raw.get('enterprise_project_id', ''),
        'update_time': 0,
    }

    return mapped



def fetch_all_alert_history(
    region: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    alarm_type: str = None,
) -> list:
    """获取告警历史记录（通过 hcloud CES ListAlarmHistories/v2，自动分页）

    Args:
        region: 区域 ID，None 时使用默认区域
        start_time: 查询起始时间，None 默认为当前时间前24小时
        end_time: 查询截止时间，None 默认为当前时间
        alarm_type: 告警类型过滤（'metric' 或 'event'），None 为不过滤

    Returns:
        告警历史列表，每条记录已映射为 analyze_alarm.py 期望的格式。
    """
    if region is None:
        region = get_region()

    now = end_time if end_time is not None else datetime.now()
    start = start_time if start_time is not None else now.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)

    params = {
        'create_time_from': _format_time_for_ces(start),
        'create_time_to': _format_time_for_ces(now),
        'limit': 100,
        'offset': 0,
    }
    if alarm_type:
        params['alarm_type'] = alarm_type

    all_alarms = []
    offset = 0

    while True:
        params['offset'] = offset
        data = _run_hcloud('CES', 'ListAlarmHistories/v2', region, params)

        if not data:
            break

        alarms = data.get('alarm_histories') or []
        count = data.get('count', 0)

        for raw in alarms:
            all_alarms.append(_map_alarm_history(raw, region))

        offset += len(alarms)
        if offset >= count or len(alarms) == 0:
            break

        logger.info(f"已获取 {offset}/{count} 条告警历史")

    logger.info(f"区域 {region}: 共获取 {len(all_alarms)} 条告警历史")
    return all_alarms


def fetch_ces_alarm_rules(region: str = None) -> list:
    """获取 CES 告警规则列表（通过 hcloud CLI）

    Args:
        region: 区域 ID

    Returns:
        告警规则列表
    """
    if region is None:
        region = get_region()

    all_rules = []
    offset = 0
    limit = 100

    while True:
        params = {'limit': limit, 'offset': offset}
        data = _run_hcloud('CES', 'ListAlarmRules', region, params)

        if not data:
            break

        alarms = data.get('alarms', [])
        count = data.get('count', 0)

        for rule in alarms:
            rule_dict = rule if isinstance(rule, dict) else _to_dict(rule)
            rule_dict['region'] = region
            rule_dict['source'] = 'CES'
            all_rules.append(rule_dict)

        offset += len(alarms)
        if offset >= count or len(alarms) == 0:
            break

    logger.info(f"区域 {region}: 共获取 {len(all_rules)} 条 CES 告警规则")
    return all_rules


def fetch_aom_alarm_rules(region: str = None) -> list:
    """获取 AOM 告警规则列表（通过 hcloud CLI ListMetricOrEventAlarmRule）

    分别获取 metric 和 event 类型的规则。

    Args:
        region: 区域 ID

    Returns:
        告警规则列表
    """
    if region is None:
        region = get_region()

    all_rules = []

    for rule_type in ('metric', 'event'):
        params = {'alarm_rule_type': rule_type}
        data = _run_hcloud('AOM', 'ListMetricOrEventAlarmRule', region, params)

        if not data:
            continue

        rules = data.get('alarm_rules', []) or data.get('data', {}).get('alarm_rules', [])
        for rule in rules:
            rule_dict = rule if isinstance(rule, dict) else _to_dict(rule)
            rule_dict['region'] = region
            rule_dict['source'] = 'AOM'
            rule_dict['rule_type'] = rule_type
            all_rules.append(rule_dict)

    logger.info(f"区域 {region}: 共获取 {len(all_rules)} 条 AOM 告警规则")
    return all_rules


def fetch_metric_alarms(region: str = None) -> list:
    """获取指标告警规则列表（CES + AOM 合并）

    替代原 OA 平台的 fetch_metric_alarms，合并 CES 和 AOM 两个来源的告警规则。

    Args:
        region: 区域 ID

    Returns:
        合并后的告警规则列表
    """
    ces_rules = fetch_ces_alarm_rules(region)
    aom_rules = fetch_aom_alarm_rules(region)

    # 过滤：仅保留启用的规则
    all_rules = ces_rules + aom_rules
    enabled_rules = [r for r in all_rules if r.get('enabled') is True or r.get('alarm_rule_enabled') is True]

    logger.info(f"区域 {region}: 合并后 {len(enabled_rules)} 条启用的告警规则")
    return enabled_rules


def fetch_metric_alarm_policies(alarm_id: str, region: str = None) -> list:
    """获取 CES 告警规则的策略列表

    通过 hcloud CES ListAlarmRulePolicies 获取指定告警规则下的策略。

    Args:
        alarm_id: 告警规则 ID
        region: 区域 ID

    Returns:
        策略列表
    """
    if region is None:
        region = get_region()

    all_policies = []
    offset = 0
    limit = 100

    while True:
        params = {'alarm_id': alarm_id, 'limit': limit, 'offset': offset}
        data = _run_hcloud('CES', 'ListAlarmRulePolicies', region, params)

        if not data:
            break

        policies = data.get('policies', [])
        count = data.get('count', 0)

        for policy in policies:
            p = policy if isinstance(policy, dict) else _to_dict(policy)
            all_policies.append(p)

        offset += len(policies)
        if offset >= count or len(policies) == 0:
            break

    return all_policies


def fetch_metric_alarm_resources(alarm_id: str, region: str = None) -> list:
    """获取 CES 告警规则关联的资源列表

    通过 hcloud CES ListAlarmRuleResources 获取指定告警规则关联的资源。

    Args:
        alarm_id: 告警规则 ID
        region: 区域 ID

    Returns:
        资源列表
    """
    if region is None:
        region = get_region()

    all_resources = []
    offset = 0
    limit = 100

    while True:
        params = {'alarm_id': alarm_id, 'limit': limit, 'offset': offset}
        data = _run_hcloud('CES', 'ListAlarmRuleResources', region, params)

        if not data:
            break

        resources = data.get('resources') or []
        count = data.get('count', 0)

        for res in resources:
            r = res if isinstance(res, dict) else _to_dict(res)
            all_resources.append(r)

        offset += len(resources)
        if offset >= count or len(resources) == 0:
            break

    return all_resources


def _to_dict(obj):
    """将对象转为字典（兼容 SDK model 对象和普通 dict）。"""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return obj
