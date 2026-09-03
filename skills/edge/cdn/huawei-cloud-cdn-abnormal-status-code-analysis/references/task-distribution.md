# Step 3: Distribution — who / where / what path

> Goal: locate which client IPs / paths / UA / referer dominate the abnormal
> codes, and whether it is a few-IP burst (刷量 → edge rate-limit/CC) vs many
> real users (global issue). Read-only.

## 3.1 Client IP count (刷量 vs real users)

```bash
hcloud CDN ListDomainClientStats --cli-region=cn-north-1 --domain_name=$DOMAIN --stat_type=ip_num \
  --start_time=$DAY_S --end_time=$DAY_E --cli-output=json | jq '.result'
```

- Low `ip_num` + high `req_num` ⇒ few-IP burst (刷量 / rate-limit / CC).
- High `ip_num` ⇒ many real users (global config/origin issue).
- Note: `ip_num` span supports 1 day at CST 0:00; `uv` span supports 5 minutes
  at 5-min points.

## 3.2 Top-N drill (req_num only — cross-reference with status codes)

The Top-N family `stat_type` supports **only `flux`/`req_num`**, no status code.
Use it to shortlist suspect IPs/paths/UA/referer, then cross-check those against
`ShowLogs` / `ShowDomainStats` for their status codes.

```bash
for OP in ListCdnDomainTopIps ListCdnDomainTopPath ListCdnDomainTopOriginUrl ListCdnDomainTopRefers ListCdnDomainTopUas; do
  echo "=== $OP ==="
  hcloud CDN $OP --cli-region=cn-north-1 --domain_name=$DOMAIN --stat_type=req_num \
    --start_time=$HOUR_S --end_time=$HOUR_E --cli-output=json | jq '.result // .top_url // .'
done
```

## Exit criteria

- 刷量 vs real-users verdict recorded.
- Shortlist of suspect IPs / paths / UA / referer for Step 5 forensics.
