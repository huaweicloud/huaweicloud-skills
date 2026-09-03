# LTS Alarm Rule Configuration Reference

## Alarm Types

| Type | Create Command | Description |
|------|---------------|-------------|
| Keyword Alarm | `CreateKeywordsAlarmRule` | Triggered when keyword match count exceeds threshold |
| SQL Alarm | `CreateSqlAlarmRule` | Triggered when SQL query result meets condition |

## Alarm Severity Levels

| Level | Description |
|-------|-------------|
| `Critical` | Critical alarm — immediate attention required |
| `Major` | Major alarm — investigate soon |
| `Minor` | Minor alarm — monitor |
| `Info` | Informational alarm — for awareness |

> Enumerated values (from `--help`): `[Info|Minor|Major|Critical]`. `Warning` is **not** a valid level.

## Frequency Configuration

| Frequency Type | Description | Example |
|---------------|-------------|---------|
| `CRON` | Cron-based schedule | `--frequency.type=CRON --frequency.cron_expr="0 */5 * * * *"` |
| `FIXED_RATE` | Fixed interval | `--frequency.type=FIXED_RATE --frequency.fixed_rate=5 --frequency.fixed_rate_unit=minute` |

## Keyword Alarm Rule Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--keywords_alarm_rule_name` | Yes | Alarm rule name |
| `--keywords_alarm_level` | Yes | Severity: Info/Minor/Major/Critical |
| `--keywords_requests.[N].log_group_id` | Yes | Target log group ID |
| `--keywords_requests.[N].log_stream_id` | Yes | Target log stream ID |
| `--keywords_requests.[N].keywords` | Yes | Keywords to match (e.g., "ERROR") |
| `--keywords_requests.[N].condition` | Yes | Comparison operator: >=, >, <, <= |
| `--keywords_requests.[N].number` | Yes | Threshold count |
| `--keywords_requests.[N].search_time_range` | Yes | Time window value (max 60 when unit=minute) |
| `--keywords_requests.[N].search_time_range_unit` | Yes | Time unit: minute (only `minute` accepted) |
| `--notification_frequency` | Yes | Notification interval: 0/5/10/15/30/60/180/360 |
| `--frequency.type` | Yes | Frequency type: CRON/HOURLY/DAILY/WEEKLY/FIXED_RATE |

## SQL Alarm Rule Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--sql_alarm_rule_name` | Yes | Alarm rule name |
| `--sql_alarm_level` | Yes | Severity: Info/Minor/Major/Critical |
| `--sql_requests.[N].log_group_id` | Yes | Target log group ID |
| `--sql_requests.[N].log_stream_id` | Yes | Target log stream ID |
| `--sql_requests.[N].sql` | Yes | SQL query statement |
| `--sql_requests.[N].search_time_range` | Yes | Time window value (max 60 when unit=minute) |
| `--sql_requests.[N].search_time_range_unit` | Yes | Time unit: minute/hour |
| `--condition_expression` | Yes | Condition expression (e.g., ">=1") |
| `--frequency.type` | Yes | Frequency type |
| `--notification_frequency` | Yes | Notification interval: 0/5/10/15/30/60/180/360 |

## Alarm Status Management

```bash
# Enable alarm rule (status: RUNNING/STOPPING; type: keywords/sql)
hcloud LTS UpdateAlarmRuleStatus --cli-region={region} --project_id={pid} \
  --alarm_rule_id={id} --status=RUNNING --type=keywords

# Disable alarm rule
hcloud LTS UpdateAlarmRuleStatus --cli-region={region} --project_id={pid} \
  --alarm_rule_id={id} --status=STOPPING --type=keywords
```

## Transfer Types

| Type | Description | Target |
|------|-------------|--------|
| `OBS` | Transfer to OBS bucket | Object storage |
| `DIS` | Transfer to DIS | Data Ingestion Service |
| `DMS` | Transfer to DMS Kafka | Distributed Message Service |

## Transfer Storage Formats

| Format | Description |
|--------|-------------|
| `RAW` | Raw log format |
| `JSON` | JSON structured format |
