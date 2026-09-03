# Acceptance Criteria

## Functional Requirements

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-01 | List host assets with filtering by host_id, os_type, agent_status | `ListHostStatus` returns valid JSON |
| AC-02 | List vulnerabilities with filtering by type, status, repair_priority | `ListVulnerabilities` returns valid JSON |
| AC-03 | Show vulnerability details for Linux/Windows/CMS types | `ShowLinuxVulDetail` etc. return valid JSON |
| AC-04 | Show baseline overview and statistics | `ShowBaselineOverview` returns valid JSON |
| AC-05 | List baseline check rules per host | `ListHostCheckRules` returns valid JSON |
| AC-06 | List intrusion alert events with severity/event_class filtering | `ListEventHandleHistory` returns valid JSON |
| AC-07 | List brute-force events (login_0001, login_0002) | `ListEventHandleHistory` with event_class_ids returns valid JSON |
| AC-08 | List weak password detection results | `ListWeakPasswordUsers` returns valid JSON |
| AC-09 | Query common login IPs and locations | `ListLoginCommonIp` / `ListLoginCommonLocation` return valid JSON |
| AC-10 | Query risk score | `ShowRiskScore` returns valid JSON |
| AC-11 | Update alert handling status (ChangeEvent) | `ChangeEvent` returns success (requires confirmation) |
| AC-12 | Update vulnerability status (ChangeVulStatus) | `ChangeVulStatus` returns success (requires confirmation) |

## Non-Functional Requirements

| ID | Criterion |
|----|-----------|
| NF-01 | All query operations are read-only and safe to execute without confirmation |
| NF-02 | All mutating operations (ChangeEvent, ChangeVulStatus) require explicit user confirmation |
| NF-03 | No AK/SK values are hardcoded in any file |
| NF-04 | Output is structured JSON suitable for programmatic consumption |
| NF-05 | Supports filtering by risk level, host ID, and time range (via event query) |
| NF-06 | Does not perform isolation, antivirus, or other high-risk actions |

## Scope Boundaries

| Boundary | Status |
|----------|--------|
| Create/Delete host resources | ❌ Not supported |
| Isolate host / kill process | ❌ Not supported |
| Real-time blocking | ❌ Not supported |
| Query only (List/Show) | ✅ Supported |
| Alert handling (Update) | ✅ Supported with confirmation |
