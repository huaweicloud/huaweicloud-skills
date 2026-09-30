# CCE AZ Power Outage Experiment — Log Analysis Workflow

## 6-Step Analysis Workflow

### Step 1: Environment Check
- Verify hcloud, kubectl, python3 are available
- Verify AK/SK credentials are configured
- Verify kubectl can connect to the CCE cluster

### Step 2: Load Experiment Context
- **Auto-detect mode**:
  - Prefer reading execution-log.json → post-hoc analysis mode
  - Fall back to experiment.json → real-time monitoring mode
- Extract experiment time window (start_time / end_time)
- Extract affected node and Pod lists

### Step 3: Identify Affected Services
- Scan Pods on affected nodes
- Get associated Services (via selector matching)
- Get associated Ingresses (via backend service references)
- Get associated ConfigMaps

### Step 4: Collect Logs
- **CCE Pod logs**: `kubectl logs --since-time` filtered by time window
- **LTS logs**: `hcloud LTS ListLogs` to query managed service logs
- **Kubernetes Events**: `kubectl get events --all-namespaces`
- Time window coverage: shutdown → rescheduling → recovery full process

### Step 5: Analyze Error Patterns
- **ERROR**: application error logs
- **Exception / StackTrace**: exception stack traces
- **Connection refused**: connection refused (service unavailable)
- **Timeout / Deadline exceeded**: timeout
- **5xx HTTP**: server-side errors (500/502/503/504)
- **Reconnect**: reconnected successfully
- **Degraded**: degraded mode marker
- **Recovered**: recovery marker

### Step 6: Generate Analysis Report
- Experiment overview
- Affected service list
- Pod rescheduling timeline
- Error pattern statistics
- Business impact assessment
- Improvement recommendations

## Real-time / Post-hoc Mode Auto-Detection

| Condition | Mode | Data Source |
|-----------|------|-------------|
| execution-log.json exists | Post-hoc analysis | execution-log.json |
| Only experiment.json exists | Real-time monitoring | experiment.json + live kubectl |
| Neither exists | Error | Prompt user |

## Error Pattern Classification Table

| Pattern | Keywords | Severity | Description |
|---------|----------|----------|-------------|
| ERROR | error | High | Application error |
| Exception | exception, stacktrace | High | Exception stack trace |
| Connection refused | connection refused | High | Service unavailable |
| Timeout | timeout, deadline exceeded | Medium | Timeout |
| 5xx HTTP | 500, 502, 503, 504 | High | Server-side error |
| Reconnect | reconnect, reconnected | Low | Reconnected successfully |
| Degraded | degrad | Medium | Degraded mode |
| Recovered | recover, restored | Low | Recovered |

## Error Timeline Analysis During Pod Rescheduling

1. **Shutdown phase** (Node Ready→NotReady): Connection refused, Timeout may occur
2. **Eviction phase** (Pod Running→Terminating): 5xx HTTP may occur (service briefly unavailable)
3. **Scheduling phase** (Pod Pending→Running): Timeout may occur (waiting for new Pod to start)
4. **Recovery phase** (Node NotReady→Ready): Recovered markers should appear

By comparing error occurrence times with the Pod rescheduling timeline, you can pinpoint error root causes and impact scope.
