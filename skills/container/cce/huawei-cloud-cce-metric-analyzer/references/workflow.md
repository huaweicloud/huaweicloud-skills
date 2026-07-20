# Workflow

## Metric Query Sequence

1. Identify `region`, `cluster_id` from user query.
2. Determine query target:
   - **Pod TopN**: Use `huawei_get_cce_pod_metrics_topN` for cluster-wide ranking
   - **Single Pod**: Use `huawei_get_cce_pod_metrics` for specific pod time-series
   - **Node TopN**: Use `huawei_get_cce_node_metrics_topN` for cluster-wide ranking
   - **Single Node**: Use `huawei_get_cce_node_metrics` for specific node time-series
3. Optional filters: `namespace`, `label_selector`, `node_ip`
4. Set `top_n` (default 10) and `hours` (default 1) parameters.
5. Execute query and parse results.

## Pod Metrics Workflow

```
User: Show Pods with the highest CPU usage in a namespace
1. huawei_get_cce_pod_metrics_topN(region, cluster_id, namespace=xxx, top_n=10)
2. Sort results by cpu_usage_percent descending
3. Filter for critical/warning status
4. Report top consumers and anomaly thresholds
```

## Node Metrics Workflow

```
User: Show Node memory usage ranking in the cluster
1. huawei_get_cce_node_metrics_topN(region, cluster_id, top_n=10)
2. Sort results by memory_usage_percent descending
3. Filter for critical/warning status
4. Report top consumers and node health status
```

## Threshold Detection

| Resource | Critical | Warning | Status Field |
|----------|----------|---------|--------------|
| CPU | >80% | >50% | `status` in cpu data |
| Memory | >85% | >50% | `status` in memory data |
| Disk | >85% | >70% | `status` in disk data |

## Next Steps

If anomalies are detected:
- For Pod issues: suggest `huawei-cloud-cce-pod-failure-diagnoser` or `huawei-cloud-cce-workload-failure-diagnoser`
- For Node issues: suggest `huawei-cloud-cce-node-failure-diagnoser`
- For capacity planning: suggest `huawei-cloud-cce-capacity-trend-forecaster`
- For cost optimization: suggest `huawei-cloud-cce-cost-optimization-advisor`