# Step 4: Root Cause — origin side (4A) / edge side (4B)

> Branch on the Step 2 fork. Read-only. All ops here are query-class GET.

## 4A. Origin-side root cause (origin returned the abnormal code)

Applies when `bs_status_code_*` is non-empty. Typical codes: 403/404
(回源HOST / origin permission / missing resource), 500/502/503/504/530
(origin internal error / unreachable / overload / timeout / DNS).

```bash
# 回源HOST (wrong host → origin serves wrong site → 403/404)
hcloud CDN ShowOriginHost --cli-region=cn-north-1 --domain_id=$DOMAIN_ID --cli-output=json

# Domain detail: sources / origin / status / CNAME effectiveness
hcloud CDN ShowDomainDetail --cli-region=cn-north-1 --domain_id=$DOMAIN_ID --cli-output=json

# Refresh/preheat history (a refresh near the anomaly ⇒ cache miss burst ⇒ transient origin 4xx/5xx)
hcloud CDN ShowHistoryTasks/v2 --cli-region=cn-north-1 --file_type=file --page_number=1 --page_size=50 --cli-output=json \
  | jq '.tasks[]?|{task_type,create_time,total,processing,succeed,failed}'
# If create_time falls in the anomaly window ⇒ highly relevant.
# Per-task detail: hcloud CDN ShowHistoryTaskDetails/v2

# Top origin URL (which origin URL is most abnormal — cross with bs_status_code)
hcloud CDN ListCdnDomainTopOriginUrl --cli-region=cn-north-1 --domain_name=$DOMAIN --stat_type=req_num \
  --start_time=$HOUR_S --end_time=$HOUR_E --cli-output=json | jq '.result'

# Origin timeout config (504-related: origin_receive_timeout)
hcloud CDN ShowDomainFullConfig/v2 --cli-region=cn-north-1 --domain_name=$DOMAIN --cli-output=json \
  | jq '.configs.origin_receive_timeout,.configs.sources,.configs.origin_protocol'
```

## 4B. Edge-side root cause (origin healthy, CDN edge generated the code)

Applies when `bs_status_code_*` is empty. Typical codes: 401/403 (auth /
referer / IP-blacklist / UA / ban / rate-limit), 495/496 (TLS), 503 (edge
rate-limit).

```bash
# Full edge config (url_auth/referer/ip_filter/user_agent_*/... all visible at once)
hcloud CDN ShowDomainFullConfig/v2 --cli-region=cn-north-1 --domain_name=$DOMAIN --cli-output=json > /tmp/cfg.json
jq '.configs|keys' /tmp/cfg.json
jq '.configs|{url_auth,referer,ip_filter,user_agent_filter,user_agent_black_and_white_list}' /tmp/cfg.json
# Note: domain-level config has no ip_frequency/cc_protection section. If
# behavior matches rate-limit/CC (few IPs, 200→403 flip, traffic spike), it is
# account-level protection not exposed in domain config.

# Referer防盗链 (403 source)
hcloud CDN ShowRefer --cli-region=cn-north-1 --domain_id=$DOMAIN_ID --cli-output=json

# IP blacklist (per-IP block signature = same IP 200 then 403)
hcloud CDN ShowBlackWhiteList --cli-region=cn-north-1 --domain_id=$DOMAIN_ID --cli-output=json

# Rule engine block rules
hcloud CDN ListRuleDetails --cli-region=cn-north-1 --domain_name=$DOMAIN --cli-output=json | jq '.rules'

# Banned URL / access-control tasks (may need 工单 whitelist; CDN.0004 = record & proceed)
hcloud CDN ListBanUrl --cli-region=cn-north-1 --start_time=$DAY_S --end_time=$DAY_E --page_number=1 --page_size=50 --cli-output=json
hcloud CDN ListAccessControlTask --cli-region=cn-north-1 --start_time=$DAY_S --end_time=$DAY_E --limit=100 --cli-output=json

# Response header / error page (status code rewritten?)
hcloud CDN ShowResponseHeader --cli-region=cn-north-1 --domain_id=$DOMAIN_ID --cli-output=json

# Edge rate-limit / CC evidence (few IPs + high req + bandwidth spike + 200→403 flip)
hcloud CDN ListDomainClientStats --cli-region=cn-north-1 --domain_name=$DOMAIN --stat_type=ip_num --start_time=$DAY_S --end_time=$DAY_E --cli-output=json | jq '.result'
hcloud CDN ShowBandwidthCalc --cli-region=cn-north-1 --domain_name=$DOMAIN --calc_type=bw_peak --start_time=$DAY_S --end_time=$DAY_E --cli-output=json | jq '.result'

# Cert / TLS (49x / SSL errors)
hcloud CDN ShowCertificatesHttpsInfo/v2 --cli-region=cn-north-1 --domain_name=$DOMAIN --cli-output=json
```

## Exit criteria

- A candidate mechanism is named (e.g. edge rate-limit/CC, referer block,
  IP-blacklist, 回源HOST wrong, origin 502, refresh-induced burst).
- Conflicting hypotheses are ruled out with evidence (config off, rules empty,
  origin 2xx-only, etc.).
- Exact mechanism that needs工单/whitelist to confirm (e.g. ListBanUrl
  blocked) is recorded honestly as "unconfirmed via CLI".
