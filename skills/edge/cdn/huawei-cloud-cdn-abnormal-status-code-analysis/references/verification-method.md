# Verification Method

Verify the skill produces correct, complete diagnosis results.

## 0. Verify Python library availability

```bash
python -c "import requests; print('requests ok')"
```

If it fails: `pip install requests>=2.25`.

## 1. Verify credential configuration

```bash
hcloud configure list
```

Confirm a valid AK/SK profile (mode=AKSK) exists.

## 2. Verify domain discovery

```bash
hcloud CDN ListDomains/v2 --cli-region=cn-north-1 --cli-output=json | jq '.domains[]|{domain_name,domain_status,id}'
```

Expect 200 with at least one domain; capture `domain_id`.

## 3. Verify status-code quantification

```bash
read S E < <(python3 -c "import time;now=int(time.time());DAY=86400;m=(now+8*3600)//DAY*DAY-8*3600;print(m-31*DAY,m)")
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=summary \
  --domain_name=<domain> \
  --stat_type=req_num,http_code_2xx,http_code_3xx,http_code_4xx,http_code_5xx \
  --start_time=${S}000 --end_time=${E}000 --interval=86400 --cli-output=json | jq '.result'
```

Expect `result` containing `req_num` and the `http_code_Nxx` totals.

## 4. Verify the edge/origin fork

```bash
hcloud CDN ShowDomainStats/v2 --cli-region=cn-north-1 --action=detail \
  --domain_name=<domain> --stat_type=bs_status_code_4xx \
  --start_time=${S}000 --end_time=${E}000 --interval=86400 --cli-output=json | jq '.result'
```

- `result={}` ⇒ edge-generated verdict; non-empty ⇒ origin-generated.

## 5. Verify edge config

```bash
hcloud CDN ShowDomainFullConfig/v2 --cli-region=cn-north-1 --domain_name=<domain> --cli-output=json | jq '.configs|keys'
```

Expect the `configs` sections (url_auth/referer/ip_filter/…).

## 6. Verify log forensics

```bash
hcloud CDN ShowLogs/v2 --cli-region=cn-north-1 --domain_name=<domain> \
  --start_time=<hour_s> --end_time=<hour_e> --page_size=100 --cli-output=json | jq '.logs[]|{name,link,size}'
python scripts/fetch_cdn_log.py --url "<link>" --status 403 --timeout 30 --max-lines 50
```

Expect one JSON object on stdout with `rows[]` / `count` / `error`.

## 7. Verify IP attribution

```bash
hcloud CDN ShowIpInfo/v2 --cli-region=cn-north-1 --ips=<ip1>,<ip2> --cli-output=json | jq '.cdn_ips[]'
```

## Expected output

A structured text report (see [task-report.md](task-report.md)) with summary,
distribution, root cause, conclusion, and remediation boundary.
