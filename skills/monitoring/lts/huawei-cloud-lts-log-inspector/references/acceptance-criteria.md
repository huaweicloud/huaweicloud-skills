# Acceptance Criteria

## Query Operations

| Criteria | Verification Method |
|----------|-------------------|
| ListLogHistogram returns histogram data for valid group/stream/time range | Execute with known valid IDs, verify response contains histogram buckets |
| ListTopnTrafficStatistics returns TOP-N sorted results | Execute with `--is_desc=true --sort_by=write`, verify results are sorted descending |
| ListTimeLineTrafficStatistics returns time-series data | Execute with valid time range, verify response contains time-series points |
| ListLogContext returns context logs within size limits | Execute with `--backwards_size=100 --forwards_size=100`, verify response has <= 200 log lines |
| ListHostGroup returns host group list | Execute without filters, verify response contains host group array |
| ListHost returns hosts with status field | Execute with `--filter.host_status=offline`, verify all returned hosts have status=offline |
| ListAccessConfig returns access configs | Execute without filters, verify response contains access config array |

## Mutating Operations

| Criteria | Verification Method |
|----------|-------------------|
| CreateTransfer outputs cost risk warning before execution | Verify warning is displayed and user confirmation is required |
| CreateTransfer creates OBS transfer successfully | Execute with valid params, verify response contains transfer ID |
| DeleteTransfer removes transfer config | Execute with valid transfer ID, verify transfer no longer in ListTransfers |

## Diagnostic Workflows

| Criteria | Verification Method |
|----------|-------------------|
| Traffic surge diagnosis identifies top log streams | Execute workflow, verify output contains ranked log streams by write traffic |
| Collection break diagnosis identifies offline/error hosts | Execute workflow, verify output contains hosts with broken collection status |
| Log flooding diagnosis identifies high-frequency log streams | Execute workflow, verify output contains log streams sorted by write volume |

## Output Quality

| Criteria | Verification Method |
|----------|-------------------|
| Traffic report is structured and readable | Verify output contains TOP-N table, timeline chart data, and summary |
| Collection anomaly checklist is actionable | Verify output lists each anomalous host with status and affected config |
| Context log fragments are concise | Verify output does not exceed 500 lines per direction |
| Cost risk warning is prominent | Verify warning appears before any CreateTransfer execution |

## Constraint Compliance

| Criteria | Verification Method |
|----------|-------------------|
| No bulk export of all logs | Verify CreateTransfer always requires specific log_group_id and log_stream_id |
| No TTL/index/alarm modification | Verify Skill does not call any modification commands for these resources |
| Cost warning on transfer creation | Verify warning is displayed before CreateTransfer execution |
