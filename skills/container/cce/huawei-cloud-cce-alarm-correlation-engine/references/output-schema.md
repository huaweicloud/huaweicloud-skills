# Output Schema

```json
{
  "summary": "alarm correlation summary",
  "time_window": "last 1h",
  "groups": [
    {
      "group_key": "resource or alarm type",
      "severity": "critical | major | minor | info",
      "count": 0,
      "active_count": 0,
      "history_count": 0,
      "representative_alarms": []
    }
  ],
  "timeline": [],
  "likely_related_resources": [],
  "recommended_next_skill": "huawei-cloud-cce-root-cause-analyzer"
}
```