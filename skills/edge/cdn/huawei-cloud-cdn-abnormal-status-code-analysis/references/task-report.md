# Step 6: Diagnosis Report

> Goal: aggregate Steps 1-5 into a structured text report with a decision-tree
> conclusion and a clear remediation boundary (no CLI write ops).

## Report template

```
==================== CDN Abnormal Status Code Diagnosis Report ====================
Analysis Time: <ISO8601>
Target Domain: <domain>      Region: cn-north-1

--- Summary ---
Abnormal code(s): <e.g. 403, or 502>
Anomaly window: <CST time>      Volume: <count> / <ratio %>
Edge/origin verdict: bs_status_code_<X> = <empty|non-empty> → <edge-generated|origin-generated>

--- Distribution ---
Top client IPs: <..>      Top URL/Path: <..>      Top UA/Referer: <..>
Client verdict: <few-IP burst | many real users> (ip_num=<..>, req_num=<..>)
Traffic spike: <yes/no> (bw_peak=<..>)

--- Root Cause ---
Candidate mechanism: <e.g. edge rate-limit/CC; referer block; IP-blacklist;
  回源HOST wrong; origin 502; refresh-induced burst>
Evidence: <config state; bs verdict; log rows; rule list; etc.>
Ruled out: <e.g. url_auth off; referer off; rules empty; origin 2xx-only>
Unconfirmed via CLI: <e.g. ListBanUrl/ListAccessControlTask blocked by CDN.0004 whitelist>

--- Conclusion ---
Status: <Edge-generated | Origin-generated | Partial / requires manual verification>
Suggestion: <e.g. account-level CC/IP限频 review; check 回源HOST; inspect origin 502;
  open 工单 to enable ListBanUrl whitelist for audit>
Remediation boundary: fixes are write ops (UpdateBlackWhiteList / UpdateDomainFullConfig /
  CreateRefreshTasks / VerifyDomainOwner / …) → use CDN console or run hcloud manually;
  this skill does NOT execute them.
===================================================================================
```

## Decision tree (root-cause attribution)

```mermaid
flowchart TD
    S[Abnormal code X appears] --> Q1{bs_status_code_X<br/>has X?}
    Q1 -->|yes (origin)| ORIGIN
    Q1 -->|no (edge)| EDGE
    ORIGIN --> O1{X?}
    O1 -- 403/404 --> O1a[回源HOST wrong / origin permission or missing resource<br/>ShowOriginHost + ShowDomainDetail]
    O1 -- 500/502/530 --> O1b[origin internal/unreachable/DNS<br/>ShowDomainDetail.sources + bs_status_code]
    O1 -- 503 --> O1c[origin overload/timeout<br/>origin_receive_timeout + ShowHistoryTasks]
    O1 -- 504 --> O1d[origin timeout<br/>origin_receive_timeout + origin perf]
    O1 -- 499 --> O1e[client closed, often slow/large<br/>log rt + ShowBandwidthCalc]
    EDGE --> E1{X?}
    E1 -- 401/403 --> E1a[auth/referer/IP-blacklist/UA/ban/rate-limit/CC<br/>Step 4B]
    E1 -- 495/496 --> E1b[TLS/cert<br/>ShowCertificatesHttpsInfo]
    E1 -- 503 edge --> E1c[edge rate-limit/CC<br/>ListDomainClientStats + ShowBandwidthCalc]
    E1 -- 416 --> E1d[range invalid<br/>cache_rules]
```

## Exit criteria

- Report contains summary, distribution, root cause, conclusion, remediation
  boundary.
- Every claimed cause has evidence; every unconfirmed item is marked honestly.
- No write operation is recommended to be executed by the skill itself.
