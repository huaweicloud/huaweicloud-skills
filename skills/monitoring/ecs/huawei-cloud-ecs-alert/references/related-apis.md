# Related APIs

This document lists the core Huawei Cloud CES APIs used by this skill.

## Core CES APIs

### CreateAlarm

**Function**: Create a single alarm rule

**API**: `POST /v1.0/{project_id}/alarms`

**hcloud Command**:

```bash
hcloud CES CreateAlarm \
  --cli-region=cn-north-4 \
  --alarm_name=ecs-cpu-alarm \
  --metric_namespace=SYS.ECS \
  --metric_name=cpu_util \
  --dim.0=name=instance_id,value=ecs-001 \
  --condition.0.metric_name=cpu_util \
  --condition.0.period=300 \
  --condition.0.filter=average \
  --condition.0.comparison=gt \
  --condition.0.threshold=80 \
  --condition.0.unit=count \
  --condition.0.count=3 \
  --alarm_action_id=<action-id> \
  --alarm_enabled=true

```

**Key Parameters**:

- `alarm_name`: Alarm rule name (must be unique)
- `metric_namespace`: Service namespace (SYS.ECS for ECS)
- `metric_name`: Metric name (cpu_util, mem_util, etc.)
- `dim`: Monitoring dimension (instance_id, etc.)
- `condition`: Alarm condition (threshold, period, etc.)
- `alarm_action_id`: SMN topic URN for notifications

### ListAlarms

**Function**: Query alarm rule list

**API**: `GET /v1.0/{project_id}/alarms`

**hcloud Command**:

```bash
hcloud CES ListAlarms \
  --cli-region=cn-north-4 \
  --limit=100 \
  --offset=0

```

**Key Parameters**:

- `limit`: Number of results per page (default 100)
- `offset`: Offset for pagination
- `alarm_type`: Alarm type (MULTI_INSTANCE_ID, etc.)

### UpdateAlarm

**Function**: Update alarm rule configuration

**API**: `PUT /v1.0/{project_id}/alarms/{alarm_id}`

**hcloud Command**:

```bash
hcloud CES UpdateAlarm \
  --cli-region=cn-north-4 \
  --alarm_id=alarm-001 \
  --alarm_name=updated-alarm-name \
  --alarm_enabled=true \
  --condition.0.threshold=90

```

### ShowMetricData

**Function**: Query monitoring metric data

**API**: `POST /v1.0/{project_id}/metric-data`

**hcloud Command**:

```bash
hcloud CES ShowMetricData \
  --cli-region=cn-north-4 \
  --namespace=SYS.ECS \
  --metric_name=cpu_util \
  --dim.0=instance_id,ecs-001 \
  --from=2024-01-01T10:00:00Z \
  --to=2024-01-01T11:00:00Z \
  --period=300 \
  --filter=average

```

**Key Parameters**:

- `namespace`: Service namespace
- `metric_name`: Metric name
- `dim`: Monitoring dimension
- `from`: Start time (ISO 8601 format)
- `to`: End time (ISO 8601 format)
- `period`: Data aggregation interval (seconds)
- `filter`: Aggregation function (average, max, min)

### ListMetrics

**Function**: Query available metrics

**API**: `GET /v1.0/{project_id}/metrics`

**hcloud Command**:

```bash
hcloud CES ListMetrics \
  --cli-region=cn-north-4 \
  --namespace=SYS.ECS

```

## SMN APIs (Notifications)

### ListTopics

**Function**: Query SMN topic list

**API**: `GET /v2/{project_id}/notifications/topics`

**hcloud Command**:

```bash
hcloud SMN ListTopics --cli-region=cn-north-4

```

### Subscribe

**Function**: Subscribe endpoint to topic

**API**: `POST /v2/{project_id}/notifications/topics/{topic_urn}/subscriptions`

**hcloud Command**:

```bash
hcloud SMN Subscribe \
  --cli-region=cn-north-4 \
  --topic-urn=urn:smn:cn-north-4:xxx:topic-name \
  --protocol=email \
  --endpoint=user@example.com

```

### Unsubscribe

**Function**: Unsubscribe endpoint from topic

**API**: `DELETE /v2/{project_id}/notifications/topics/{topic_urn}/subscriptions/{subscription_urn}`

**hcloud Command**:

```bash
hcloud SMN Unsubscribe \
  --cli-region=cn-north-4 \
  --subscription-urn=urn:smn:cn-north-4:xxx:topic-name:subscription-001

```

## ECS APIs (Instance Query)

### ListServersDetails

**Function**: Query ECS instance details

**API**: `GET /v1/{project_id}/cloudservers/details`

**hcloud Command**:

```bash
hcloud ECS ListServersDetails --cli-region=cn-north-4

```

## API Documentation References

- [CES API Reference](https://support.huaweicloud.com/api-ces/ces_03_0001.html)
- [SMN API Reference](https://support.huaweicloud.com/api-smn/smn-api-170301001.html)
- [ECS API Reference](https://support.huaweicloud.com/api-ecs/ecs_01_0100.html)
