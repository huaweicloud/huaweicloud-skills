# Acceptance Criteria

## Diagnosis Completion Checklist

All items must be addressed before diagnosis is considered complete.

### Phase 1: Subscription Metadata Check

- [ ] Data type identified (metrics / logs / traces / all)
- [ ] Environment context confirmed (region, domain_id, project_id, time range)
- [ ] APM business checked (`ListBusiness` executed)
- [ ] APM token checked (`ShowToken` executed)
- [ ] AOM Prometheus instance checked (`ListPromInstance` executed)
- [ ] AOM access code checked (`ListAccessCode` executed)
- [ ] LTS log groups checked (`ListLogGroups` executed)
- [ ] LTS log streams checked (`ListLogStreams` executed)
- [ ] Missing metadata identified and root cause determined

### Phase 2: Data Pipeline Check

- [ ] Application-side reporting verified (OTEL SDK / exporter / ICAgent)
- [ ] Data source-side ingestion verified (APM / AOM / LTS receiving data)
- [ ] Forwarding pipeline verified (deliverConfig, Kafka for traces)
- [ ] Query-side parameters verified (metric_name, labels, keywords, filters)

### Phase 3: Common Checks

- [ ] Timestamp format verified (13-digit milliseconds, not 10-digit seconds)
- [ ] Region consistency verified (ingestion region = query region)
- [ ] Authentication verified (IAM token / AppCode valid)
- [ ] Permissions verified (403 → insufficient permissions, 401 → expired token)

### Phase 4: Diagnostic Report

- [ ] Root cause identified (with confidence level)
- [ ] Fix recommendations provided (actionable steps)
- [ ] Verification method provided (how to confirm fix works)
- [ ] Report generated using the diagnostic report template

### Error Code Handling

- [ ] `LTS.2446` → keyword syntax fixed
- [ ] `403` → permission issue diagnosed (agency / IAM / subscription)
- [ ] `RESOURCE_NOT_EXIST` → resource record missing
- [ ] `401` → token refreshed
