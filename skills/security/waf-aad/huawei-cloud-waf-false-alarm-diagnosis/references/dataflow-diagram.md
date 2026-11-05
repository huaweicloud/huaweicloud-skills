# Data Flow Diagram

```mermaid
graph TD
    A[Customer report: blocked / 418 / page won't open / interface blocked] --> B[Step1 Confirm domain access & protect status]
    B -->|ListHost / ListCompositeHosts / ShowHost| C[host_id, policy_id, protect_status, mode]
    C --> D[Step2 Retrieve blocking events]
    D -->|ListEvent domain+time+IP action=block; ShowEvent| E[events: rule, attack_type, action, url, payload, sip]
    E --> F[Step3 False-positive judgment]
    F -->|payload + rule + business context| G{False positive?}
    G --> H[Step4 Walk rule priority chain]
    H -->|ListIgnoreRule / Whiteblackip / Geoip / Custom / Punishment / Anticrawler / Cc / PolicyProtectRules / ShowPolicy| I[Blocking rule pinpointed]
    I --> J[Step5 Recommend safest release]
    J -->|read-only output commands| K[Global whitelist > IP whitelist > log-only observe]
    K --> L[User executes chosen command]
    L --> M[Step6 Re-query events to verify]
    M -->|same window ListEvent before/after| N[Conclusion + release-effective? + rollback guide]
    G -->|Not a false positive| O[Keep blocking; advise security team]
    O --> N
```

## Key Decision Branch: False-Positive Judgment

- Normal business params hit semantic character groups (select/limit → sqli), static/framework paths look like attack payloads, known security/scanner UA, cloud/vendor egress IP vs iprank/geo rules → suspect false positive.
- Follow the rule priority chain to pinpoint which rule produced `action=block`.

## Rule Priority Chain (for release-method recommendation)

误报屏蔽/全局白名单 (IgnoreRule) → IP 白名单 (WhiteblackipRule white=1) → IP 黑名单 (white=0) → 地理位置封禁 (GeoipRule) → 精准防护 (CustomRule) → 攻击惩罚 (PunishmentRule) → 动态反爬 (AnticrawlerRule) → CC 防护 (CcRule) → Web 基础防护 (ListWebBasicProtectionRules).

Always recommend the highest-priority entry that covers the blocking feature; never recommend disabling web basic protection first.