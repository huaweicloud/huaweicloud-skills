# Operation Guide

This reference holds detailed operating notes for `huawei-cloud-cce-alarm-correlation-engine`. Keep `SKILL.md` focused on routing, safety, and core commands.

## Parameter Reference

### Alarm Query Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `region` | Yes | Huawei Cloud region, for example `cn-north-4` |
| `cluster_id` | No | CCE cluster ID; when provided, only alarms related to this cluster are returned |
| `ak` | No | Access Key ID; explicit tool parameter has highest priority |
| `sk` | No | Secret Access Key; explicit tool parameter has highest priority |
| `project_id` | No | Huawei Cloud project ID; tools resolve it internally when possible: explicit value first, then active hcloud profile/IAM project lookup for the target region, then environment fallback |

### Alarm Rule Mutation Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `region` | Yes | Huawei Cloud region |
| `rule_name` | Yes for create, update, delete | Alarm rule name |
| `rule_id` | Yes for enable, disable | Alarm rule ID |
| `metric_name` | Yes for metric rule creation | Metric name |
| `namespace` | Yes for creation | Metric namespace |
| `event_name` | Yes for event rule creation | Event name; use the localized description plus event key format from `references/cce-event-list.md` |
| `bind_notification_rule_id` | Yes for batch configure | Existing AOM notification rule ID/name. If missing, call `huawei_list_aom_action_rules`, show candidates, and wait for explicit user confirmation. |
| `notification_topic_urn` | Yes for notification rule creation | SMN topic URN |
| `notification_topic_name` | Yes for notification rule creation | SMN topic name |
| `notification_topic_display_name` | No | Optional SMN topic display name |
| `notification_user_name` | No | Optional user name stored on the notification action rule |
| `alarm_template_id` | No | AOM alarm template ID used for batch configure or cleanup; defaults to the cloud-side CCE alarm template |
| `rule_name_prefix` | No | Prefix for batch-created or matched rule names; defaults to `cluster_id` |
| `include_metric_alarms` | No | Whether to include metric alarm templates; default `true` |
| `include_event_alarms` | No | Whether to include event alarm templates; default `true` |
| `alarm_items` | No | Comma-separated allowlist of template names or event names to create or clean up |
| `skip_existing` | No | Skip existing rules during confirmed batch configure; default `true` |
| `prom_instance_id` | No | Optional override; batch configure auto-resolves the target cluster AOM Prometheus instance from the `cie-collector` addon |
| `delete_auto_notification_rule` | No | Also delete `auto-cluster-{cluster_id}` during cleanup; default `false` |
| `comparison_operator` | Yes for metric rule creation | Threshold comparison operator |
| `threshold` | Yes for metric rule creation | Alarm threshold value |
| `period` | Yes for metric rule creation | Statistics period in seconds |
| `evaluation_periods` | Yes for metric rule creation | Consecutive trigger period count |
| `statistic` | Yes for metric rule creation | Statistics method |
| `alarm_level` | Yes for creation | Alarm severity level |
| `fields` | No | Additional JSON fields for creation |
| `updates` | No | JSON batch update fields |
| `enterprise_project_id` | No | Enterprise project scope |
| `confirm` | No | Must be `true` for mutation operations to execute |

## Output Expectations

Alarm query outputs should include `region`, optional `cluster_id`, `total_count`, `firing_count`, `resolved_count`, `severity_stats`, and `type_stats`.

For CCE alarms, prioritize these resource clues when present: `cluster_name`, `namespace`, `pod_name`, `resource_kind`, `event_name`, and `message`.

## Diagnosis Hand-Off

| Alarm Characteristics | Recommended Skill |
|----------------------|-------------------|
| `CrashLoopBackOff`, `BackOffStart`, `FailedStart`, `ImagePullBackOff` | `huawei-cloud-cce-pod-failure-diagnoser` |
| `FailedScheduling`, insufficient CPU or memory | `huawei-cloud-cce-pod-failure-diagnoser` or `huawei-cloud-cce-node-failure-diagnoser` |
| `NodeNotReady`, node pressure, NPD events | `huawei-cloud-cce-node-failure-diagnoser` |
| Ingress 502/504, Service unreachable, ELB anomalies | `huawei-cloud-cce-network-failure-diagnoser` |
| Multiple alarm categories impact business simultaneously | `huawei-cloud-cce-root-cause-analyzer` |
| Scaling, reboot, drain, or other remediation needed | `huawei-cloud-cce-auto-remediation-runner` |

## Verification

1. Confirm connectivity with `huawei_list_aom_alarms region=<region> cluster_id=<cluster_id>`.
2. Run `huawei_analyze_aom_alarms` and verify burst, attention, and chronic groupings.
3. Run `huawei_aom_alarm_inspection` and verify the cluster risk summary.
4. Preview a mutation command without `confirm` and verify that no change is executed.
5. After any confirmed mutation, call `huawei_list_aom_alarm_rules` to verify rule state.

## Common Pitfalls

| Pitfall | Correct Approach |
|---------|-----------------|
| Only querying active alarms | Use `huawei_list_aom_alarms`, which merges active and history alarms |
| Calling mutation tools without preview | Preview first, then add `confirm=true` only after explicit user approval |
| Creating event rules with wrong event name format | Use the format documented in `references/cce-event-list.md` |
| Creating metric rules with arbitrary thresholds | Use `references/cce-prometheus-metric-alarms.md` |
| Choosing a notification rule automatically | List candidates and wait for explicit user confirmation |
| Deleting notification action rules without impact review | Preview first and verify dependent alarms |
| Executing remediation directly from this skill | Hand off to `huawei-cloud-cce-auto-remediation-runner` |
| Ignoring mute rules during notification gaps | Query both action rules and mute rules |
