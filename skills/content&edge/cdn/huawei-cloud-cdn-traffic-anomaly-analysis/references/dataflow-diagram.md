# Data Flow Diagram — CDN Traffic Anomaly Analysis

```mermaid
flowchart TD
    subgraph Input[Input Parameters]
        DOMAIN["domain_name<br/>(required)"]
        DAYS["--days=7<br/>(default)"]
        REGION["--cli-region=cn-north-4"]
    end

    subgraph PreCheck[Prerequisites Check]
        CHK_CLI["hcloud version ≥ 3.2.0"]
        CHK_PY["python --version ≥ 3.8"]
        CHK_CRED["hcloud configure list"]
    end

    subgraph Phase1[Phase 1: Billing Mode Detection]
        S1["ShowChargeModes<br/>--product_type=base"]
        BILLING{"charge_mode?"}
        B1["bw_95"]
        B2["flux / combine_flux"]
        B3["bw / bw_peak"]
        S1 --> BILLING
    end

    subgraph Phase2[Phase 2: Domain Resolution]
        S2["ListDomains/v2<br/>--domain_status=online"]
        VALIDATE{"domain exists?"}
        S2 --> VALIDATE
        VALIDATE -->|no| ERR["Error: domain not found"]
        VALIDATE -->|yes| S4
    end

    subgraph Phase3[Phase 3: Timestamp Calculation]
        S4["cdn_timestamp.py --days=7<br/>→ current window (start_ms, end_ms)"]
        S4B["cdn_timestamp.py --baseline<br/>→ 3×30-day windows"]
    end

    subgraph Phase4[Phase 4: Metric Query]
        direction TB
        subgraph bw95Path["bw_95 Path"]
            Q_CUR["ShowBandwidthCalc<br/>--calc_type=bw_95<br/>range: 7 days"]
            Q_BSL["ShowBandwidthCalc<br/>--calc_type=bw_95<br/>range: 3×30-day windows<br/>(3 API calls, sleep 0.6s)"]
            Q_CUR --> BW95_RES["current_value (bit/s, 7d P95)"]
            Q_BSL --> BW95_BSL["baseline: 3 aggregate values<br/>(mean / max of 3 windows)"]
        end
        subgraph fluxBWPath["flux / bw Path"]
            Q_COMB["ShowDomainStats/v2<br/>range: past 97 days<br/>(90d baseline + 7d current)"]
            Q_COMB --> SPLIT{"split result"}
            SPLIT --> CURR["current: last 7 daily values"]
            SPLIT --> BASE["baseline: first 90 daily values"]
        end
    end

    subgraph Phase5[Phase 5: Threshold Judgment]
        direction TB
        ABS["Absolute Threshold Check"]
        ABS_R1{{"bw_95: ≥ 8 Gbps"}}
        ABS_R2{{"flux: any day > 5 TB"}}
        ABS_R3{{"bw: any day ≥ 3 Gbps"}}

        REL["Relative Baseline Check"]
        STATS["baseline statistics<br/>(mean / P95 / max)"]
        REL_R{{"current > baseline_max × 1.5?"}}

        DUAL{"result tier"}

        ABS --> ABS_R1
        ABS --> ABS_R2
        ABS --> ABS_R3
        REL --> STATS --> REL_R

        ABS_R1 & ABS_R2 & ABS_R3 & REL_R --> DUAL
        DUAL -->|"exceeds absolute"| ABN["⚠️ Anomalous"]
        DUAL -->|"exceeds relative only"| WATCH["👀 Watch"]
        DUAL -->|"neither"| NORM["✅ Normal"]
    end

    subgraph Phase6[Phase 6: Report Generation]
        REPORT["Structured Analysis Report<br/>- Billing mode & metric<br/>- Current window daily values<br/>- Baseline statistics<br/>- Deviation rate<br/>- Tier conclusion"]
    end

    Input --> PreCheck --> Phase1
    B1 --> Phase2 & Phase3
    B2 --> Phase2 & Phase3
    B3 --> Phase2 & Phase3

    Phase3 -->|bw_95| bw95Path
    B1 --> bw95Path
    Phase3 -->|flux / bw| fluxBWPath
    B2 & B3 --> fluxBWPath

    bw95Path & fluxBWPath --> Phase5 --> Phase6
```

## Data Flow Summary

| Phase | bw_95 Path | flux / bw Path |
|-------|-----------|----------------|
| **API Calls** | 6 total (1 billing + 1 domain + 1 current + 3 baseline) | 3 total (1 billing + 1 domain + 1 combined 97d query) |
| **Current Window** | 7-day P95 aggregate (single value, bit/s) | Last 7 daily values from 97-day result |
| **Baseline** | 3 × 30-day P95 aggregates → statistics (mean, max) | First 90 daily values from 97-day result → statistics (mean, P95, max) |
| **Rate Limit** | ShowBandwidthCalc: 2/s, 6 calls ≈ 3s | ShowDomainStats: 15/s, no concern |

## Key API Constraints

- **ShowBandwidthCalc**: max 31-day range, single aggregate value (no per-day breakdown). Baseline requires 3 separate 30-day queries.
- **ShowDomainStats/v2**: supports ≥365-day range, returns one data point per day at `interval=86400`. A single 97-day query covers both baseline (first 90 days) and current window (last 7 days).