# CTS Audit Readiness

Use this playbook when the user asks whether operation audit, trace lookup, or key event notification is ready.

## Inputs

- Account/domain scope and target region.
- Trace type and time range for trace lookup.
- Whether OBS delivery bucket and notification topics are in scope.

## Read-Only Flow

1. Run CTS `ListTrackers` to confirm tracker status, tracker type, OBS bucket delivery, and KMS encryption posture.
2. Run CTS `ListOperations` to map the cloud service and operation names the user wants to audit.
3. Run CTS `ListTraces` with an explicit `trace_type` and bounded time range when investigating a specific event.
4. Run CTS `ListNotifications` only after confirming the notification type.
5. Run CTS `ListTraceResources` when the user needs resource-level trace coverage; it requires explicit domain scope.

## Guardrails

- Treat trace output as sensitive because it can include operator, source IP, resource ID, and request metadata.
- Do not change tracker, notification, or OBS delivery settings from this playbook.
- Do not treat missing traces as proof that an operation did not happen until tracker status, time range, region, and trace type are verified.

## Promotion Gaps

- Collect live read-only smoke evidence for at least `ListTrackers` and `ListTraces`.
- Document expected empty-result behavior for new accounts and low-activity regions.
