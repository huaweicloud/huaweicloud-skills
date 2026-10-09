# Data Flow Diagram — CDN Origin Server Diagnosis

```mermaid
flowchart TD
    subgraph Input[Input Parameters]
        DOMAIN["domain_name<br/>(required)"]
        REGION["--cli-region=<region>"]
    end

    subgraph PreCheck[Pre-checks]
        CHK_CLI["hcloud version ≥ 3.2.0"]
        CHK_PY["python ≥ 3.8 + requests ≥ 2.25"]
        CHK_CRED["hcloud configure list<br/>credentials valid?"]
        CHK_DOM{"Target domain<br/>user-provided?"}
        ASK_DOM["Ask the user for the domain;<br/>if unknown, list domains via<br/>ListDomains/v2 and let the user choose"]
        CHK_CRED --> CHK_DOM
        CHK_DOM -->|no| ASK_DOM
    end

    subgraph Step1[Step 1: Permission Validation]
        S1["ShowDomainDetailByName<br/>--domain_name=<domain>"]
        RET1{"Return code?"}
        S1 --> RET1
        RET1 -->|404| ERR1["Abort: domain does not exist"]
        RET1 -->|403| ERR2["Abort: insufficient permissions"]
        RET1 -->|200| OK1["Domain validation passed<br/>get domain_id"]
    end

    subgraph Step2[Step 2: Origin Configuration Query]
        S2["ShowDomainFullConfig/v2<br/>--domain_name=<domain>"]
        RET2{"configs.sources?"}
        S2 --> RET2
        RET2 -->|empty| EMPTY["Report: origin not configured<br/>abort probe"]
        RET2 -->|non-empty| PARSE["Parse configuration<br/>origin_addr / origin_type<br/>http_port / https_port<br/>origin_protocol"]
    end

    subgraph Step3[Step 3: Origin Probe]
        PROTO{"origin_protocol?"}
        PARSE --> PROTO
        PROTO -->|http| HTTP["origin_probe.py<br/>--scheme http --host <origin_addr> --port <http_port>"]
        PROTO -->|https| HTTPS["origin_probe.py<br/>--scheme https --host <origin_addr> --port <https_port>"]
        PROTO -->|follow| BOTH["Probe both http and https"]
        RET3{"JSON result?"}
        HTTP --> RET3
        HTTPS --> RET3
        BOTH --> RET3
        RET3 -->|connected=true, http_status 200/3xx| OK3["Origin reachable ✅"]
        RET3 -->|http_status 5xx / connected=false| FAIL3["Origin unreachable ❌<br/>prompt IP whitelist"]
        RET3 -->|error.reason=connect_timeout| TIMEOUT3["Probe timeout ⚠️"]
    end

    subgraph Step4[Step 4: Report Generation]
        REPORT["Structured text diagnosis report<br/>- Analysis time<br/>- Target domain<br/>- Origin configuration info<br/>- Diagnosis item list<br/>- Conclusion and remediation suggestion"]
    end

    Input --> PreCheck
    CHK_CRED -->|credentials invalid| ERR_CRED["Abort: prompt to configure credentials"]
    CHK_DOM -->|provided| Step1
    Step1 -->|200| Step2
    Step2 -->|sources empty| EMPTY
    EMPTY --> Step4
    Step2 -->|sources non-empty| Step3
    Step3 -->|JSON {connected, http_status, is_private_address, error}| Step4
    Step4 --> OUTPUT["Return diagnosis report"]
```

## Data Flow Summary

| Stage | Command | Input | Output |
|-------|---------|-------|--------|
| Pre-check | `hcloud configure list` | None | Credential status |
| Permission validation | `ShowDomainDetailByName` | domain_name | domain_id, domain_status |
| Origin configuration query | `ShowDomainFullConfig/v2` | domain_name | configs.sources (origin_addr, origin_type, http_port, https_port), origin_protocol |
| Origin probe | `python scripts/origin_probe.py` | scheme + host + port | JSON (`{result, data, error_msg}` envelope): `{data.scheme, data.host, data.port, data.connected, data.http_status, data.is_private_address, data.duration_ms, data.error}` |
| Report generation | — | All probe JSON results | Structured text report |

## Key Constraints

- **Timeout**: All probe commands use a 10-second timeout
- **Read-only**: Query and probe only; no configuration changes are performed
- **Credential security**: Reading/echoing/printing AK/SK is prohibited
- **Recommended region**: use `--cli-region=<region>`
- **Protocol matching**: Select the probe protocol and port based on origin_protocol
