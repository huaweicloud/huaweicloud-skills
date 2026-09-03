# Step 1: Discovery & Quantification

> Goal: confirm the target domain, then quantify 4xx/5xx volume and ratio over
> a window, and check whether the anomaly coincides with a traffic/bandwidth
> spike. Read-only.

## 1.1 List domains → obtain domain_id

```bash
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --cli-output=json | jq '.domains[]|{domain_name,domain_status,service_area,id}'
```

- Record `DOMAIN` and `DOMAIN_ID` (several Show* ops take `--domain_id`).
- If `domain_status != online`, surface it — a non-online domain explains
  global anomalies on its own.

## 1.2 Quantify status codes (summary)

Use a wide window first (e.g. last 31 days, daily), then narrow.

```bash
# 31-day totals, daily
read S E < <(python3 -c "import time;now=int(time.time());DAY=86400;m=(now+8*3600)//DAY*DAY-8*3600;print(m-31*DAY,m)")
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=summary \
  --domain_name=$DOMAIN \
  --stat_type=req_num,http_code_2xx,http_code_3xx,http_code_4xx,http_code_5xx \
  --start_time=${S}000 --end_time=${E}000 --interval=86400 --cli-output=json | jq '.result'
```

Read `result.http_code_4xx` / `http_code_5xx`; ratio vs `req_num` = abnormal rate.

## 1.3 Narrow to the anomaly window (detail, hourly)

```bash
# 7-day detail, hourly — peak index ⇒ anomaly hour
read S E < <(python3 -c "import time;now=int(time.time());DAY=86400;m=(now+8*3600)//DAY*DAY-8*3600;print(m-7*DAY,m)")
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=detail \
  --domain_name=$DOMAIN --stat_type=http_code_4xx,http_code_5xx \
  --start_time=${S}000 --end_time=${E}000 --interval=3600 --cli-output=json | jq '.result'
```

The peak array index maps to a time bucket. Set `DAY_S/DAY_E` (anomaly day,
CST 0:00) and `HOUR_S/HOUR_E` (anomaly hour) accordingly.

## 1.4 Traffic/bandwidth correlation

```bash
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 --domain_name=$DOMAIN \
  --calc_type=bw_peak --start_time=${S}000 --end_time=${E}000 \
  --cli-output=json | jq '.result'
```

A bandwidth/req spike aligned with the 4xx/5xx spike suggests刷量 → edge
rate-limit/CC (see Step 4B).

## Exit criteria

- Anomaly code segment (4xx and/or 5xx) identified with non-zero volume.
- Anomaly window (`DAY_S/DAY_E`, `HOUR_S/HOUR_E`) set for Step 2.
- Traffic-spike presence noted for Step 4.
