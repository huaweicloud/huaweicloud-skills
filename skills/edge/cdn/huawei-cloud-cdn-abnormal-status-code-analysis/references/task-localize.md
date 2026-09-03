# Step 2: Localize & Fork — exact code + edge/origin

> Goal: drill to the **specific status code** + time bucket, then run the
> **edge-vs-origin fork** that decides whether Step 4 walks 4A (origin) or 4B
> (edge). Read-only.

## 2.1 Exact code on the anomaly day (edge)

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=detail \
  --domain_name=$DOMAIN --stat_type=status_code_4xx,status_code_5xx \
  --start_time=$DAY_S --end_time=$DAY_E --interval=3600 --cli-output=json | jq '.result'
```

`result` keys are specific codes that occurred, e.g. `{"403":[..],"502":[..]}`.
Each value is a time array; the non-zero index ⇒ anomaly hour.

## 2.2 ★ Edge vs origin fork ★ (back-to-source status codes)

Run the **same window** against the back-to-source statistics. Edge
(`status_code_*`) and origin (`bs_status_code_*`) cannot be mixed in one
query — run them separately.

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=detail \
  --domain_name=$DOMAIN --stat_type=bs_status_code_4xx,bs_status_code_5xx \
  --start_time=$DAY_S --end_time=$DAY_E --interval=3600 --cli-output=json | jq '.result'
```

Decision:

| `bs_status_code_*` result | Verdict | Next step |
|---------------------------|---------|-----------|
| `result = {}` (empty) | **Edge-generated** — origin never returned the code | Step 4B (edge root cause) |
| `result` non-empty | **Origin-generated** — origin returned the code | Step 4A (origin root cause) |

## 2.3 Origin overall health (optional confirmation)

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=summary \
  --domain_name=$DOMAIN \
  --stat_type=bs_http_code_2xx,bs_http_code_3xx,bs_http_code_4xx,bs_http_code_5xx \
  --start_time=$DAY_S --end_time=$DAY_E --interval=86400 --cli-output=json | jq '.result'
```

If origin returned only `bs_http_code_2xx` (no 4xx/5xx), origin is fully
healthy ⇒ anomaly is edge-generated regardless of any single-code doubt.

## Exit criteria

- Exact abnormal code(s) known (e.g. `403`, or `502`).
- Edge/origin verdict recorded (drives Step 4 branch).
- If edge-generated, the anomaly hour is confirmed for Step 3/5.
