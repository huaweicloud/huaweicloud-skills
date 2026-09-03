# Acceptance Criteria

## Functional Requirements

| ID | Requirement | Verification |
|----|-------------|-------------|
| F-01 | List all log groups | `ListLogGroups` returns JSON array |
| F-02 | List log streams under a group | `ListLogStreams` with group name returns streams |
| F-03 | Query log stream index | `ListLogStreamIndex` returns index config |
| F-04 | List transfer tasks | `ListTransfers` returns transfer list |
| F-05 | List keyword alarm rules | `ListKeywordsAlarmRules` returns rules |
| F-06 | List SQL alarm rules | `ListSqlAlarmRules` returns rules |
| F-07 | Query alarm history | `ListActiveOrHistoryAlarms` returns alarm events |
| F-08 | Search logs by keyword | `ListLogs` with keywords returns matching log entries |
| F-09 | Get log context | `ListLogContext` returns surrounding log lines |
| F-10 | Get log histogram | `ListLogHistogram` returns time distribution |
| F-11 | Query structured logs | `ListQueryStructuredLogs` with SQL returns structured results |
| F-12 | Create log group with TTL | `CreateLogGroup` returns new group ID |
| F-13 | Create log stream | `CreateLogStream` returns new stream ID |
| F-14 | Create full-text index | `CreateLogStreamIndex` returns index config |
| F-15 | Create OBS transfer | `CreateTransfer` returns transfer ID |
| F-16 | Create keyword alarm | `CreateKeywordsAlarmRule` returns rule ID |
| F-17 | Create SQL alarm | `CreateSqlAlarmRule` returns rule ID |
| F-18 | Update log group TTL | `UpdateLogGroup` confirms TTL change |
| F-19 | Update log stream | `UpdateLogStream` confirms config change |
| F-20 | Update transfer config | `UpdateTransfer` confirms change |
| F-21 | Toggle alarm status | `UpdateAlarmRuleStatus` confirms status change |
| F-22 | Delete log group (with confirm) | `DeleteLogGroup` removes group after confirmation |
| F-23 | Delete log stream (with confirm) | `DeleteLogStream` removes stream after confirmation |
| F-24 | Delete transfer (with confirm) | `DeleteTransfer` removes task after confirmation |
| F-25 | Delete alarm rule (with confirm) | `DeleteKeywordsAlarmRule` removes rule after confirmation |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NF-01 | All query operations are read-only and safe to execute without confirmation |
| NF-02 | All Create/Update operations return a resource configuration snapshot |
| NF-03 | All Delete operations require explicit user confirmation (confirm/ok/确认) |
| NF-04 | Batch deletion of all LTS resources is prohibited |
| NF-05 | Log search results are returned as summaries (not full raw logs) |
| NF-06 | Supports filtering by ID, time range, and keywords |
| NF-07 | No hardcoded region — uses {region} placeholder |
| NF-08 | No hardcoded credentials — reads from env vars or CLI profile |
