# Verification Method

## 1. Environment Verification

```bash
hcloud version          # KooCLI installed
hcloud configure list   # credentials configured
hcloud EIP --help       # EIP service available
hcloud CES --help       # CES service available
```

## 2. Permission Verification

Run a read-only query and confirm no permission error:

```bash
hcloud EIP ListPublicips/v2 --cli-region=cn-north-4
hcloud CES ListMetrics --cli-region=cn-north-4 --namespace=SYS.VPC
```

If "Insufficient permissions" appears, apply the policy in `references/iam-policies.md`.

## 3. Functional Verification

| # | Case | Command | Expected |
| --- | ------ | --------- | ---------- |
| 1 | List EIPs | `python3 scripts/eip_query.py list --limit 5` | Table of EIPs |
| 2 | EIP detail | `python3 scripts/eip_query.py show --publicip_id {id}` | Full JSON detail |
| 3 | Bandwidth usage rate | `python3 scripts/eip_query.py metric --publicip_id {id} --metric upstream_bandwidth_usage --filter average --period 300` | % datapoints + peak/avg |
| 4 | Inbound/outbound traffic | `python3 scripts/eip_query.py metric --publicip_id {id} --metric down_stream --metric up_stream --filter sum --period 3600` | Byte totals |
| 5 | Peak bandwidth | `python3 scripts/eip_query.py metric --publicip_id {id} --filter max --period 300` | max values (bit/s) |
| 6 | Time-range query | pass `--from`/`--to` (Unix ms) | data in range only |
| 7 | Shared bandwidth | `python3 scripts/eip_query.py metric --bandwidth_id {bw_id} --metric downstream_bandwidth_usage` | % datapoints |

## 4. Error Handling Verification

- **Empty datapoints**: widen `--from`/`--to`, or increase `--period`.
- **Permission denied**: check IAM policy.
- **No data for dimension**: confirm `bandwidth_share_type`; switch `publicip_id`
  ↔ `bandwidth_id`.
- **Invalid metric name**: run `ListMetrics --namespace=SYS.VPC` to list valid names.

## 5. Environment Variables

| Variable | Purpose |
| ---------- | --------- |
| `HUAWEICLOUD_SDK_REGION` | Default region (default cn-north-4) |
| `HCLOUD_BIN` | Custom hcloud binary path |
| `SKILL_QUALITY_DISABLE=1` | Disable quality-report upload (local debugging) |
