# Diagnostic Report Template

## Observability No-Data Diagnosis Report

### Problem Description

| Field | Value |
|-------|-------|
| **Data Type** | {metrics / logs / traces / all} |
| **Symptom** | {complete absence / partial absence / error code} |
| **Onset** | {when did the issue start} |
| **Error Code** | {LTS.2446 / 403 / 401 / RESOURCE_NOT_EXIST / none} |
| **Region** | {cn-north-4} |
| **Time Range** | {start_time ~ end_time} |

### Subscription Metadata Check

| Metadata | Service | Status | Action Needed |
|----------|---------|--------|---------------|
| apmBusiness | APM | {exists / missing} | {none / create business} |
| apmToken | APM | {valid / invalid / missing} | {none / get token} |
| promInstance | AOM | {exists / missing} | {none / create instance} |
| aomAccessCode | AOM | {valid / invalid / missing} | {none / create code} |
| logGroup | LTS | {exists / missing} | {none / subscribe LTS} |
| logStream | LTS | {exists / missing} | {none / create stream} |

### Data Pipeline Check

| Check Point | Status | Details |
|-------------|--------|---------|
| Application-side reporting | {configured / not configured} | {OTEL SDK / exporter / ICAgent status} |
| Data source ingestion | {receiving / not receiving} | {APM / AOM / LTS data status} |
| Forwarding pipeline | {OK / broken} | {deliverConfig, Kafka status} |
| Query parameters | {correct / incorrect} | {metric_name, labels, keywords, filters} |

### Common Checks

| Check | Status | Details |
|-------|--------|---------|
| Timestamp format | {13-digit ms / 10-digit s} | {correct / needs fix} |
| Region consistency | {consistent / mismatch} | {ingestion region vs query region} |
| Authentication | {valid / invalid} | {IAM token / AppCode status} |
| Permissions | {sufficient / insufficient} | {IAM policies / agency status} |

### Root Cause Analysis

**Primary root cause:** {description with confidence level}

**Secondary causes (if applicable):**
1. {cause 2}
2. {cause 3}

### Fix Recommendations

1. {step 1 — specific and actionable}
2. {step 2}
3. {step 3}

### Verification Method

After applying fixes, verify data recovery by:
1. {verification step 1}
2. {verification step 2}

### Diagnostic Commands Executed

| # | Command | Result |
|---|---------|--------|
| 1 | `hcloud APM ListBusiness --cli-region=cn-north-4` | {result} |
| 2 | `hcloud APM ShowToken --cli-region=cn-north-4 --x-business-id={id}` | {result} |
| 3 | `hcloud AOM ListPromInstance --cli-region=cn-north-4` | {result} |
| 4 | `hcloud LTS ListLogGroups --cli-region=cn-north-4` | {result} |
| ... | ... | ... |
