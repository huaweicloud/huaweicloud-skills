# LTS API Command Quick Reference

## Traffic Statistics

| Command | Method | Description |
|---------|--------|-------------|
| `ListLogHistogram` | POST | Query keyword search count / histogram |
| `ListTopnTrafficStatistics` | POST | Statistics top N log group or log stream traffic |
| `ListTimeLineTrafficStatistics` | POST | Statistics query resources by time period |

### ListLogHistogram Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--group_id` | Yes | string | Log group ID |
| `--stream_id` | Yes | string | Log stream ID |
| `--start_time` | Yes | string | Start time |
| `--end_time` | Yes | string | End time |
| `--key_word` | Yes | string | Keyword |
| `--step_interval` | Yes | integer | Step interval |
| `--is_iterative` | No | boolean | Iterative query, default false |

### ListTopnTrafficStatistics Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--resource_type` | Yes | string | log_group / log_stream / tenant |
| `--topn` | Yes | integer | Top N, range 1-100 |
| `--start_time` | Yes | integer | Start timestamp (ms) |
| `--end_time` | Yes | integer | End timestamp (ms) |
| `--search_list.1` | Yes | array | Data type: index/write/storage/basicTransfer/seniorTransfer/coldStorage |
| `--sort_by` | Yes | string | Sort field (must be in search_list) |
| `--is_desc` | Yes | boolean | Descending order |
| `--filter.{key}` | Yes | map | Filter conditions |

### ListTimeLineTrafficStatistics Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--resource_type` | Yes | string | log_group / log_stream / tenant |
| `--search_type` | Yes | string | write/index/storage/basicTransfer/seniorTransfer |
| `--start_time` | Yes | integer | Start timestamp (ms) |
| `--end_time` | Yes | integer | End timestamp (ms) |
| `--period` | Yes | integer | Time interval in hours, range 1-24 |
| `--timezone` | Yes | string | Timezone |
| `--resource_id` | No | string | Resource ID |

## Log Query and Context

| Command | Method | Description |
|---------|--------|-------------|
| `ListLogs` | POST | Query log content in a log stream |
| `ListLogContext` | POST | Query context logs (before/after a specific log) |

### ListLogContext Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--log_group_id` | Yes | string | Log group ID |
| `--log_stream_id` | Yes | string | Log stream ID |
| `--line_num` | No | string | Log line sequence number (nanosecond timestamp) |
| `--backwards_size` | No | integer | Lines before, range [0,500], default 100 |
| `--forwards_size` | No | integer | Lines after, range [0,500], default 100 |
| `--scroll_id` | No | string | Pagination scroll ID |
| `--__time__` | No | string | Custom time field (ms timestamp) |

## Collection Inspection

| Command | Method | Description |
|---------|--------|-------------|
| `ListHostGroup` | POST | List host groups |
| `ListHost` | POST | List hosts (with collection status) |
| `ListAccessConfig` | POST | List access configs (collection configs) |

### Host Status Values

| Status | Meaning | Collection OK? |
|--------|---------|---------------|
| `running` | Agent running | Yes |
| `offline` | Host offline | No - broken |
| `error` | Agent error | No - may be broken |
| `plugin error` | Plugin error | No - may be broken |
| `uninstall` | Not installed | No |
| `installing` | Installing | Pending |
| `install-fail` | Install failed | No |
| `upgrading` | Upgrading | Pending |
| `upgrade-fail` | Upgrade failed | No |
| `uninstalling` | Uninstalling | Pending |
| `authentication error` | Auth failure | No - broken |

## OBS Transfer

| Command | Method | Description |
|---------|--------|-------------|
| `CreateTransfer` | POST | Create OBS/DIS/DMS transfer |
| `ListTransfers` | GET | List transfer configs |
| `DeleteTransfer` | DELETE | Delete transfer config |

## Log Group and Stream

| Command | Method | Description |
|---------|--------|-------------|
| `ListLogGroups` | GET | List all log groups |
| `ListLogStream` | GET | List log streams in a group |
| `ListLogStreams` | GET | List log stream info |

## Unavailable Features

| Feature | Reason |
|---------|--------|
| Consumer group management | Invitation-only beta, Java/Go SDK only, no REST API |
| Offline download task | Console whitelist feature, no public API; use OBS transfer as alternative |
