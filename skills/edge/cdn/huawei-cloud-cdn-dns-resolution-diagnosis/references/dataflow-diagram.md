# Data Flow Diagram — CDN DNS Resolution Diagnosis

```mermaid
flowchart TD
    subgraph Input[Input Parameters]
        DOMAIN["domain_name<br/>(required)"]
        REGION["--cli-region=<region>"]
    end

    subgraph PreCheck[Prerequisites Check]
        CHK_CLI["hcloud version ≥ 3.2.0"]
        CHK_PY["python ≥ 3.8"]
        CHK_DNSPY["dnspython ≥ 2.1 importable"]
        CHK_CRED["hcloud configure list<br/>credentials valid?"]
    end

    subgraph Step1[Step 1: Permission Check and CNAME Retrieval]
        S1["ShowDomainDetailByName<br/>--domain_name=<domain>"]
        RET1{"return code?"}
        S1 --> RET1
        RET1 -->|404| ERR1["Abort: domain not found"]
        RET1 -->|403| ERR2["Abort: permission denied"]
        RET1 -->|200| OK1["Domain validation passed<br/>obtain domain_id + cname"]
    end

    subgraph Step2[Step 2: DNS Resolution Probe]
        S2["python scripts/dns_resolve.py<br/>--domain <domain_name> --timeout 10"]
        RET2{"JSON data.error.reason?"}
        S2 -->|"JSON {data.resolved_ips, data.error}"| RET2
        RET2 -->|"null + non-empty data.resolved_ips"| OK2["Record IP list"]
        RET2 -->|"null + empty data.resolved_ips"| EMPTY2["Not resolved<br/>prompt to configure CNAME"]
        RET2 -->|"dns_timeout"| TIMEOUT2["DNS probe timeout ⚠️"]
        RET2 -->|"dns_nxdomain"| NXDOMAIN2["Domain does not exist"]
        RET2 -->|"dns_no_answer"| NOANSWER2["No A records"]
        RET2 -->|"missing_library (exit 2)"| LIBERR2["Abort: install dnspython"]
    end

    subgraph Step3[Step 3: IP Attribution Check]
        CHK_CNT{"IP count?"}
        S3["ShowIpInfo/v2<br/>--ips=<IP1,IP2,...>"]
        RET3{"attribution result?"}
        CHK_CNT -->|"≤ 20"| S3
        CHK_CNT -->|"> 20"| TRUNC["Take first 20<br/>note limit in report"]
        TRUNC --> S3
        S3 --> RET3
        RET3 -->|all belongs=true| OK3["Resolved to Huawei Cloud ✅"]
        RET3 -->|all belongs=false| FAIL3["Not resolved to Huawei Cloud ❌"]
        RET3 -->|mixed belongs| MIX3["Partial resolution ⚠️<br/>prompt multi-region probing"]
    end

    subgraph Step4[Step 4: Report Generation]
        REPORT["Structured text diagnosis report<br/>- Analysis time<br/>- Target domain<br/>- Expected CNAME<br/>- DNS Resolution IP list<br/>- Diagnosis items list<br/>- Conclusion and remediation suggestion"]
    end

    Input --> PreCheck
    PreCheck -->|credentials valid| Step1
    PreCheck -->|credentials invalid| ERR_CRED["Abort: prompt to configure credentials"]
    Step1 -->|200 JSON {id, cname}| Step2
    Step2 -->|"JSON data.resolved_ips"| Step3
    Step2 -->|"empty data.resolved_ips"| Step4
    Step2 -->|"dns_timeout"| Step4
    Step3 --> Step4
    Step4 --> OUTPUT["Return diagnosis report"]

    EMPTY2 --> Step4
    NXDOMAIN2 --> Step4
    NOANSWER2 --> Step4
    TIMEOUT2 --> Step4
    OK3 --> Step4
    FAIL3 --> Step4
    MIX3 --> Step4
```

## Data Flow Summary

| Phase | Command | Input | Output |
|-------|---------|-------|--------|
| Prerequisites check | `hcloud configure list`, `python -c "import dns.resolver"` | None | Credential status, library availability |
| Permission check | `ShowDomainDetailByName` | domain_name | JSON {id, cname, domain_status} |
| DNS resolution | `python scripts/dns_resolve.py --domain <domain> --timeout 10` | domain_name | JSON (`{result, data, error_msg}` envelope): {data.resolved_ips, data.duration_ms, data.error} |
| IP attribution | `ShowIpInfo/v2` | ips (comma-separated, ≤20, from data.resolved_ips) | belongs field for each IP |
| Report generation | — | All probe results (JSON fields) | Structured text report |

## Key Constraints

- **Timeout**: `dns_resolve.py` enforces a 10-second timeout via `--timeout 10` (default)
- **IP limit**: ShowIpInfo/v2 queries at most 20 IPs; excess takes the first 20
- **Read-only**: Only query and probe, no configuration changes
- **Credential security**: Prohibited from reading/echoing/printing AK/SK
- **Recommended region**: use `--cli-region=<region>`
- **JSON-only data flow**: Step 2 output is a JSON object consumed by Step 3 and Step 4 (no free-form text parsing)

## IP Attribution Decision Logic

| Scenario | Condition | Conclusion | Report Status |
|----------|-----------|------------|---------------|
| Resolved | All IPs belongs=true | Domain correctly resolved to Huawei Cloud CDN | ✅ Pass |
| Not resolved | All IPs belongs=false | Domain not resolved to Huawei Cloud CDN; CNAME needs to be configured | ❌ Fail |
| Partial resolution | Some belongs=true, some false | Partial regions switched, suspected false positive | ⚠️ Warning |
