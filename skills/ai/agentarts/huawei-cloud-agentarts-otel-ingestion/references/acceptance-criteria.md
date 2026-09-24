# Acceptance Criteria

## Ingestion Verification Checklist

All items must pass before ingestion is considered complete.

### Path A: APM deliverConfig

- [ ] Tracing business created (`business_id` obtained)
- [ ] Business token obtained and configured in application
- [ ] Access point retrieved
- [ ] deliverConfig forwarding created (`deliver_otel_trace=true`)
- [ ] Kafka configuration correct (SASL_SSL, topic reachable)
- [ ] Application-side OTel SDK/Collector configured and started without errors

### Path B: OTLP Direct (Verification Only)

- [ ] OTel Collector deployed with OTLP receiver
- [ ] Test application generates spans successfully
- [ ] Data export confirmed (Collector logs show export success)
- [ ] Note: agent-ops may not have OTLP receiver — fall back to Path A

### AI Agent Observation

- [ ] GenAI semantic conventions applied (`gen_ai.system`, `gen_ai.request.model`)
- [ ] Token usage attributes set (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`)
- [ ] Agent invocation spans created (`invoke_agent`, `execute_tool`)
- [ ] Spans exported via OTLP to APM endpoint

### Management Plane Verification

- [ ] Traces queryable via `ShowOpsTrace` / `ListOpsTrace`
- [ ] Sessions queryable via `ListOpsSession`
- [ ] Metrics queryable via `ShowOpsAgentMetricTrend` / `ShowOpsAgentMetricGauge`
- [ ] Logs queryable via `ListOpsAgentLog` (if log ingestion enabled)

### Security Checklist

- [ ] No AK/SK hardcoded in configuration files
- [ ] Credentials stored in environment variables or CLI profile
- [ ] Business token refreshed if expired
- [ ] No sensitive data in trace attributes (passwords, keys, PII)
- [ ] IAM permissions follow least-privilege principle

### Performance Checklist

- [ ] OTel SDK batch processor configured (not synchronous export)
- [ ] Collector queue size adequate for throughput
- [ ] Kafka producer `acks` set to `all` for reliability
- [ ] Small traffic verification completed before full rollout
