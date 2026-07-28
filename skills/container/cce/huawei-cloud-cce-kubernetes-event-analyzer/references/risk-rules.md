# Risk Rules & Guardrails

## Hard Constraints (NEVER violate)

### H1: Read-Only Operations

This skill only queries Kubernetes events and lists related resources. No modifications are made to any cluster resource.

**Rationale**: Event analysis should never alter cluster state. Remediation must be handled by dedicated diagnosis/remediation skills with appropriate confirmation mechanisms.

### H2: Data Redaction

Do not expose sensitive data such as node names, pod names, or workload names that could identify production systems in public outputs. Use redacted or fictional examples in summaries when possible.

**Rationale**: Production system identifiers in event summaries can leak infrastructure details to unauthorized parties.

### H3: Hand Off Remediation

If event analysis reveals a clear remediation path, provide evidence and hand off to the appropriate diagnosis or remediation skill instead of executing recovery actions here.

**Rationale**: This skill lacks confirmation mechanisms for write operations. Diagnosis skills have proper guardrails for remediation actions.

### H4: Time-Bounded Queries

Keep event queries time-bounded. Prefer recent windows (1-24 hours) to avoid overwhelming results.

**Rationale**: Unbounded queries can return thousands of events, making analysis impractical and consuming excessive API resources.

## Soft Constraints (SHOULD follow, exceptions documented)

### S1: Start with K8s API

Use `huawei_get_cce_events` as the primary query method. Fall back to `huawei_query_k8s_events_from_lts` only when precise time-range filtering or keyword search is needed.

**Rationale**: K8s API is simpler. LTS provides server-side filtering and requires the log-agent default Event-to-LTS collection to be enabled.

### S2: Filter Warning First

When analyzing events, filter `type == "Warning"` first. Warning events are the primary diagnostic signal.

**Rationale**: Normal events are informational noise. Warning events indicate actual problems requiring attention.

### S3: Group by Reason Before Detail

Always group events by `reason` before examining individual events. This reveals systemic patterns faster.

**Rationale**: Individual event inspection without grouping misses recurring patterns that indicate root causes.

## Guardrails

1. **Read-only**: This skill never modifies, deletes, or creates Kubernetes resources
2. **No auto-remediation**: If the user asks to take action based on event findings, redirect to `huawei-cloud-cce-auto-remediation-runner` with the evidence summarized
3. **Data redaction**: Never expose production pod/node/workload names in summaries
4. **Handoff required**: Event findings that indicate specific failures must be handed off to diagnosis skills with evidence
5. **Time-bounded**: Default to recent 1-24 hour windows; never query without time bounds unless user explicitly requests
