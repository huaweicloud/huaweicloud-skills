# Verification Method

## Static Verification

Run these checks after code or documentation changes:

```bash
python3 -m compileall -q scripts/huawei_cloud
git diff --check -- .
wc -l SKILL.md
```

`SKILL.md` should stay at or below 500 lines. Move detailed operational guidance into `references/`.

## Environment Verification

Verify required CLIs:

```bash
python3 --version
hcloud version
hcloud configure list
kubectl version --client
kubectl cce --version
```

If `kubectl cce` is unavailable, follow [kubectl-cce.md](kubectl-cce.md).

## Functional Smoke Tests

Use a non-production CCE cluster with AOM Prometheus integration enabled.

### CCE AOM Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_pod_metrics_topN \
  region=<region> cluster_id=<cluster-id> namespace=default top_n=3 hours=1

python3 scripts/huawei-cloud.py huawei_get_cce_node_metrics_topN \
  region=<region> cluster_id=<cluster-id> top_n=3 hours=1
```

Expected result: `success=true`, a resolved `aom_instance_id`, and populated `metrics` keys. Empty metric series can be acceptable only when the required AOM collection is not enabled; do not treat empty data as proof of health.

### Component Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_cce_coredns_metrics region=<region> cluster_id=<cluster-id> hours=1
python3 scripts/huawei-cloud.py huawei_get_cce_nginx_ingress_metrics region=<region> cluster_id=<cluster-id> hours=1 check_certificates=false
python3 scripts/huawei-cloud.py huawei_get_cce_autoscaler_metrics region=<region> cluster_id=<cluster-id> hours=1
```

Expected result: `success=true`. Missing component series should be reported as empty/unknown, not fabricated.

### Cloud Resource Metrics

```bash
python3 scripts/huawei-cloud.py huawei_get_ecs_metrics region=<region> instance_id=<ecs-id>
python3 scripts/huawei-cloud.py huawei_get_elb_metrics region=<region> elb_id=<elb-id> hours=1
python3 scripts/huawei-cloud.py huawei_get_eip_metrics region=<region> eip_id=<eip-id> hours=1
python3 scripts/huawei-cloud.py huawei_get_nat_gateway_metrics region=<region> nat_gateway_id=<nat-id> hours=1
```

Expected result: `success=true` and `source=hcloud` for CES-backed cloud resource metrics.

### Aggregation

```bash
python3 scripts/huawei-cloud.py huawei_cce_cluster_monitoring_aggregation \
  region=<region> cluster_id=<cluster-id> \
  start_time="YYYY-MM-DD HH:MM:SS" end_time="YYYY-MM-DD HH:MM:SS" top_n=5
```

Expected result: `success=true`, `summary`, `pod_metrics`, `node_metrics`, `component_metrics`, and cloud resource sections. If LoadBalancer Service discovery fails, report the kubectl/kubectl-cce error.

## Regression Rules

- Verify all registered dispatcher actions remain callable.
- Verify JSON output is standards-compliant and does not contain `NaN` or `Infinity`.
- Verify read-only behavior: no create/update/delete/restart/scale action is executed.
