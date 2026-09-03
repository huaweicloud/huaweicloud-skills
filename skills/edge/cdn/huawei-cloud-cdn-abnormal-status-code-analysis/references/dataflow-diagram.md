# Data Flow Diagram — CDN Abnormal Status Code Analysis

```mermaid
flowchart TD
    subgraph Input[Input Parameters]
        DOMAIN["domain_name<br/>(required)"]
        REGION["--cli-region=cn-north-1"]
        WIN["time window<br/>start/end ms + interval"]
    end

    subgraph PreCheck[Prerequisites]
        CHK_CLI["hcloud >= 3.2.0"]
        CHK_PY["python >= 3.8 + requests >= 2.25"]
        CHK_CRED["hcloud configure list"]
    end

    subgraph S1[Step 1: Discovery & Quantify]
        L1["ListDomains/v2 → domain_id"]
        Q1["ShowDomainStats/v2 summary<br/>http_code_2xx..5xx + req_num"]
        BW1["ShowBandwidthCalc<br/>(traffic-spike correlation)"]
    end

    subgraph S2[Step 2: Localize & Fork]
        Q2a["detail status_code_4xx,5xx<br/>→ exact code + time array"]
        Q2b["detail bs_status_code_4xx,5xx<br/>★ edge vs origin fork ★"]
        FORK{"bs result?"}
        Q2a --> FORK
        FORK -->|result empty| EDGE["edge-generated → 4B"]
        FORK -->|result non-empty| ORIGIN["origin-generated → 4A"]
    end

    subgraph S3[Step 3: Distribution]
        TOP3["Top-N (req_num): TopIps/Path/OriginUrl/Refers/Uas"]
        CLI3["ListDomainClientStats<br/>ip_num (刷量 vs real users)"]
    end

    subgraph S4[Step 4: Root Cause]
        RA["4A origin: ShowOriginHost / ShowDomainDetail /<br/>ShowHistoryTasks / TopOriginUrl"]
        RB["4B edge: ShowDomainFullConfig / ShowRefer /<br/>ShowBlackWhiteList / ListRuleDetails /<br/>ListBanUrl / ListAccessControlTask /<br/>ShowResponseHeader / ShowCertificatesHttpsInfo"]
    end

    subgraph S5[Step 5: Forensics]
        LOG["ShowLogs/v2 → link"]
        FETCH["python scripts/fetch_cdn_log.py --url --status"]
        IP["ShowIpInfo/v2"]
    end

    subgraph S6[Step 6: Report]
        REP["Diagnosis report + decision tree<br/>remediation boundary (console/工单)"]
    end

    Input --> PreCheck
    PreCheck -->|valid| S1
    PreCheck -->|invalid| ERR["Abort: configure credentials"]
    S1 --> S2
    S2 --> EDGE --> S3
    S2 --> ORIGIN --> S3
    S3 --> S4
    EDGE --> RB
    ORIGIN --> RA
    S4 --> S5
    S5 --> S6
    S6 --> OUT["Return diagnosis report"]
```

## Data Flow Summary

| Phase | Command | Input | Output |
|-------|---------|-------|--------|
| Discovery | `ListDomains/v2` + `ShowDomainStats summary` + `ShowBandwidthCalc` | domain_name, window | domain_id, 4xx/5xx totals + ratio, bandwidth peak |
| Localize & fork | `ShowDomainStats detail status_code_*` + `bs_status_code_*` | domain_name, window | exact code, time array, edge/origin verdict |
| Distribution | Top-N + `ListDomainClientStats` | domain_name, window | top IPs/paths/UA, ip_num |
| Root cause | `ShowDomainFullConfig` / `ShowOriginHost` / `ShowDomainDetail` / `ShowHistoryTasks` … | domain_name / domain_id | config state, origin config, refresh history |
| Forensics | `ShowLogs/v2` + `fetch_cdn_log.py` + `ShowIpInfo/v2` | domain_name, link, IPs | per-request abnormal rows JSON, IP attribution |
| Report | — | all above | structured text report |

## Key Constraints

- **Read-only**: every action is a query (GET statistics / GET config / GET log
  link / read-only log download); no write/delete operations.
- **Edge/origin fork** is the backbone: `bs_status_code_*` empty ⇒ edge; non-empty
  ⇒ origin. All downstream root-cause steps branch on this.
- **Credential security**: do not read/echo/print AK/SK; the log helper accepts
  no credentials (it only consumes a presigned link).
- **Region**: use `--cli-region=cn-north-1` (CDN does not support `cn-north-4`).
