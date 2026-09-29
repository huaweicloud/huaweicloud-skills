# Data Flow Diagram — CDN Query Reference

```mermaid
flowchart TD
    subgraph Input[User Query]
        QUERY["What do you want to query?"]
    end

    subgraph Category1[Domain Management]
        D1["ListDomains/v2<br/>List all domains"]
        D2["ShowDomainDetailByName<br/>Get domain_id"]
        D3["ShowDomainFullConfig/v2<br/>Full configuration"]
        D4["ShowOriginHost<br/>Origin host config"]
        D5["ShowCacheRules<br/>Cache TTL rules"]
        D6["ShowResponseHeader<br/>HTTP headers"]
        D7["ShowRefer<br/>Referer validation"]
        D8["ShowHttpInfo<br/>HTTPS certificate"]
        D9["ShowCertificatesHttpsInfo/v2<br/>Cert binding info"]
        D10["ShowBlackWhiteList<br/>IP blacklist/whitelist"]
        D11["ShowVerifyDomainOwnerInfo<br/>Domain ownership"]
        D12["ListDomainConfigs<br/>Specific config items"]
        D13["ShowTags/v2<br/>Domain tags"]
    end

    subgraph Category2[Statistics & Analytics]
        S1["ShowChargeModes<br/>Account billing mode"]
        S2["ShowDomainStats/v2<br/>Time-series stats<br/>(flux/bw/req_num/status codes)"]
        S3["ShowBandwidthCalc<br/>95th percentile bandwidth<br/>(max 31-day range)"]
        S4["ShowTopDomainNames<br/>Top domains by metric<br/>(max 1-day span)"]
        S5["ListCdnDomainTopIps<br/>Top IPs"]
        S6["ListCdnDomainTopPath<br/>Top URL paths"]
        S7["ListCdnDomainTopUas<br/>Top User-Agents"]
        S8["ListCdnDomainTopRefers<br/>Top Referers"]
        S9["ListCdnDomainTopOriginUrl<br/>Top origin URLs"]
        S10["ShowTopUrl/v2<br/>Top URLs v2"]
        S11["ShowDomainLocationStats/v2<br/>Geographic/ISP distribution"]
        S12["ShowDomainCountryStat<br/>Country-level stats"]
    end

    subgraph Category3[Refresh / Log / Export]
        R1["ShowHistoryTasks/v2<br/>Refresh/preheat task history"]
        R2["ShowHistoryTaskDetails/v2<br/>Task details"]
        R3["ShowUrlTaskInfo/v2<br/>URL task info<br/>(max 24h span)"]
        R4["ListBanUrl<br/>Banned URL list"]
        R5["ShowLogs/v2<br/>CDN access logs"]
        R6["ListExportTasks<br/>Export task list"]
        R7["DownloadStatisticsExcel<br/>Download stats as Excel"]
        R8["DownloadRegionCarrierExcel<br/>Download region/carrier Excel"]
    end

    subgraph Category4[Template / Rule / Tag / Account]
        T1["ShowDomainTemplate<br/>Domain templates"]
        T2["ShowAppliedTemplateRecord<br/>Applied template records"]
        T3["ListRuleDetails<br/>Rule details"]
        T4["ListShareCacheGroups<br/>Shared cache groups"]
        T5["ListSubscriptionTasks<br/>Subscription tasks"]
        T6["ShowIpInfo/v2<br/>Check CDN IP"]
        T7["ShowQuota/v2<br/>Account quota"]
        T8["ShowSpecialUser<br/>Special user config"]
        T9["ListSpecialConfiguration<br/>Special configurations"]
        T10["ShowStatsConfigs<br/>Statistics config"]
        T11["BatchCopyDomain<br/>Batch copy domain config"]
    end

    QUERY -->|"Domain info/config"| Category1
    QUERY -->|"Traffic/bandwidth stats"| Category2
    QUERY -->|"Logs/refresh tasks"| Category3
    QUERY -->|"Templates/rules/account"| Category4

    D2 -->|"Get domain_id"| D3 & D4 & D5 & D6 & D7 & D8 & D10 & D13

    S1 -->|"Determine billing mode"| S2 & S3
    S4 -->|"Identify top domains"| S5 & S6 & S7 & S8 & S9 & S10 & S11 & S12
```

## Data Flow Summary

| Category | APIs | Key Workflows |
|----------|------|---------------|
| Domain Management | 14 | List domains → Get domain_id → Query specific configs |
| Statistics & Analytics | 12 | Query billing mode → Query stats → Drill down by dimension |
| Refresh / Log / Export | 8 | Query task history → Get task details → Download logs/reports |
| Template / Rule / Tag / Account | 11 | Query templates/rules → Check account quota/IPs |

## Common Prerequisite Pattern

```
Step 1: ShowDomainDetailByName --domain_name=<domain>  →  obtain domain_id
Step 2: Use domain_id for APIs that require it:
        - ShowHttpInfo
        - ShowOriginHost
        - ShowBlackWhiteList
        - ShowCacheRules
        - ShowResponseHeader
        - ShowRefer
        - ShowTags/v2
```
