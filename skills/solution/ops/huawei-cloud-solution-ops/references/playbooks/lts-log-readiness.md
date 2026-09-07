# LTS Log Readiness

Use this playbook when the user asks for log discovery, bounded log search, log transfer posture, or observability readiness through LTS.

## Inputs

- Target region and optional log group ID/log stream ID.
- Bounded start and end time for log query.
- Optional keyword, chart, transfer, or notification template scope.

## Read-Only Flow

1. Run LTS `ListLogGroups` and `ListLogStreams` to discover available log containers.
2. Run LTS `ListLogStream` with an explicit log group ID before querying a specific stream.
3. Run LTS `ListLogs` only with explicit log group ID, stream ID, start time, and end time.
4. Run LTS `ListAccessConfig` and `ListTransfers` when ingestion or log-dump posture is in scope.
5. Run LTS `ListCharts` or notification-template queries only after confirming the log group, log stream, and domain scope.

## Guardrails

- Logs can contain secrets, personal data, request payloads, and incident details.
- Keep query windows small and filter with keywords when possible.
- Do not create, update, delete, transfer, or subscribe logs from this playbook.
- Summarize matched log patterns instead of pasting raw lines unless the user explicitly approves raw output.

## Promotion Gaps

- Collect live read-only smoke evidence for discovery and one bounded `ListLogs` query.
- Document timestamp units and query limits observed in live validation.
