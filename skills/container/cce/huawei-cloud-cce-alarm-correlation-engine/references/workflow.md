# Workflow

1. Read the alarm name, resource, time window, and severity level provided by the user.
2. Default to the last 1 hour; if the user describes a past failure, expand the time window per the user's specification.
3. Call `huawei_list_aom_alarms`; do not only query active_alert.
4. Call `huawei_analyze_aom_alarms` to form deduplicated, burst, attention, and steady groupings.
5. If alarms are related to notifications or mute rules, read alarm rules, action rules, and mute rules.
6. Group by resource, namespace, node, workload, and alarm type.
7. Output Pod, Node, Network, or Workload objects that require further diagnosis.