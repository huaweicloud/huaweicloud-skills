# Huawei Cloud Managed Service Logs Reference

## CCE Pod Log Collection

### kubectl logs Command
```bash
# Collect logs for a specific Pod (filtered by time window)
kubectl logs <pod-name> -n <namespace> --since-time <RFC3339-time> --tail=1000

# Collect logs for all Pods matching a label selector
kubectl logs -l <label-selector> -n <namespace> --since-time <RFC3339-time>
```

### Time Window Filtering
- `--since-time`: Start time (RFC3339 format, e.g. 2026-01-01T10:00:00Z)
- `--tail`: Maximum number of lines
- Note: Logs of deleted Pods cannot be retrieved via `kubectl logs`

## LTS (Log Tank Service) Log Query

### hcloud LTS Commands
```bash
# List log groups
hcloud LTS ListLogGroups --cli-region=<region>

# List log streams
hcloud LTS ListLogStream --log_group_id=<group-id> --cli-region=<region>

# Query log content
hcloud LTS ListLogs --log_stream_id=<stream-id> --start_time=<start> --end_time=<end> --cli-region=<region>
```

### LTS Log Ingestion Requirements
- LTS collection plugin (ICAgent) must be installed in the CCE cluster
- Log ingestion rules must be configured (specifying log path and log stream)
- Query time range limit: maximum 31 days per query

## CES (Cloud Eye Service) Metrics Reference

### CCE-Related Metrics
- **Node status**: cce_node_status (Ready=1, NotReady=0)
- **Pod status**: cce_pod_status (Running=1, Pending=0)
- **CPU usage**: cce_node_cpu_usage
- **Memory usage**: cce_node_memory_usage

### Query Command
```bash
# Query node monitoring metrics
hcloud CES ShowMetricData --metric_name=cce_node_status --namespace=CCE --dim.0=node_id,<node-id> --cli-region=<region>
```

## Kubernetes Events Collection

### kubectl get events
```bash
# Get events across all namespaces
kubectl get events --all-namespaces -o json

# Sort by time
kubectl get events --all-namespaces --sort-by='.lastTimestamp'
```

### Event Types of Interest
- **NodeNotReady**: Node became NotReady
- **NodeReady**: Node recovered to Ready
- **Pod evicted**: Pod was evicted
- **FailedScheduling**: Pod scheduling failed
- **Started**: Pod container started
- **Unhealthy**: Health check failed

## Log Collection Best Practices

1. **Time window**: Cover from 1 minute before shutdown to 1 minute after recovery
2. **Multi-source collection**: Collect Pod logs, LTS logs, and Kubernetes Events simultaneously
3. **Error filtering**: Filter by keywords such as ERROR/Exception/Timeout
4. **Time alignment**: Sort all logs by timestamp for correlated analysis
5. **Preserve raw logs**: Save collected raw logs to files for post-hoc traceability
