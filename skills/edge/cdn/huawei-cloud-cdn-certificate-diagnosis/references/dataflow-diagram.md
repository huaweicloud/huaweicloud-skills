# Data Flow Diagram — CDN Certificate Diagnosis

```mermaid
flowchart TD
    subgraph Input[Input Parameters]
        DOMAIN["domain_name<br/>(required)"]
        REGION["--cli-region=<region>"]
    end

    subgraph PreCheck[Pre Checks]
        CHK_CLI["hcloud version ≥ 3.2.0"]
        CHK_PY["Python ≥ 3.8 available<br/>(stdlib ssl + socket)"]
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
        RET1 -->|404| ERR1["Stop: Domain not found"]
        RET1 -->|403| ERR2["Stop: Insufficient permission"]
        RET1 -->|200| OK1["Domain validation passed<br/>Obtain domain_id"]
    end

    subgraph Step2[Step 2: Certificate Configuration Query]
        S2["ShowCertificatesHttpsInfo/v2<br/>--domain_name=<domain>"]
        M2{"Match https[] element<br/>by domain_name"}
        RET2{"https_status?"}
        S2 --> M2
        M2 -->|no match / empty https[]| NOMATCH["Treat as certificate not configured"]
        M2 -->|matched| RET2
        NOMATCH --> NOCERT
        RET2 -->|0| NOCERT["Report: Certificate not configured<br/>Stop"]
        RET2 -->|2| CONFIG["Report: Certificate configuring<br/>Prompt to wait"]
        RET2 -->|3| CERT["Certificate configured<br/>Obtain cert_name, expiration_time"]
    end

    subgraph Step3[Step 3: Certificate Probe]
        S3["python scripts/cert_probe.py<br/>--domain=<domain> --timeout 10"]
        RET3{"JSON probe result?"}
        S3 --> RET3
        RET3 -->|connected=true, tls!=null| OK3["Parse JSON tls fields<br/>subject_cn/issuer_cn/not_before/not_after/san_list ✅"]
        RET3 -->|error.reason=connect_timeout| TIMEOUT3["Probe timed out"]
        RET3 -->|error.reason=connect_failed| FAIL3["Connection failed"]
        RET3 -->|error.reason=tls_handshake_failed| FAIL3B["TLS handshake failed"]
    end

    subgraph Step4[Step 4: Days Remaining Calculation]
        CHK_EXP{"expiration_time<br/>empty?"}
        PY["python scripts/cert_expiry_check.py<br/>--expiration_time=<ms-timestamp>"]
        STATUS{"status?"}
        CHK_EXP -->|Empty| UNK["output: data.days_remaining=null<br/>data.status=unknown<br/>Report: Expiration time unknown"]
        CHK_EXP -->|Valid| PY
        PY --> STATUS
        STATUS -->|days > 30| NORMAL["status=normal ✅"]
        STATUS -->|0 < days ≤ 30| WARN["status=warning ⚠️"]
        STATUS -->|days ≤ 0| EXPIRED["status=expired ❌"]
    end

    subgraph Step5[Step 5: Report Generation]
        REPORT["Structured text diagnosis report<br/>- Analysis time<br/>- Target domain<br/>- Diagnosis item list<br/>- Conclusion and fix recommendation"]
    end

    Input --> PreCheck
    CHK_CRED -->|Credentials invalid| ERR_CRED["Stop: Prompt to configure credentials"]
    CHK_DOM -->|provided| Step1
    Step1 -->|200| Step2
    Step2 -->|https_status=3| Step3
    Step3 --> Step4
    Step4 --> Step5
    Step2 -->|https_status=0| NOCERT2["Skip probe and calculation<br/>Report directly"]
    Step2 -->|https_status=2| CONFIG2["Skip probe and calculation<br/>Report directly"]
    NOCERT2 --> Step5
    CONFIG2 --> Step5
    UNK --> Step5
    Step5 --> OUTPUT["Return diagnosis report"]
```

## Data Flow Summary

| Phase | Command | Input | Output |
|-------|---------|-------|--------|
| Pre check | `hcloud configure list` | None | Credential status |
| Permission validation | `ShowDomainDetailByName` | domain_name | domain_id, domain_status |
| Certificate configuration query | `ShowCertificatesHttpsInfo/v2` | domain_name | https[] element matched by domain_name: https_status, cert_name, expiration_time |
| Certificate probe | `python scripts/cert_probe.py --domain <domain> --timeout 10` | domain_name | JSON (`{result, data, error_msg}` envelope): `data.tls.{subject_cn, issuer_cn, not_before, not_after, san_list}`, `data.duration_ms`, `data.error` |
| Expiration calculation | `python scripts/cert_expiry_check.py` | expiration_time (ms) | `data.days_remaining`, `data.status` (inside `{result, data, error_msg}` envelope) |
| Edge between Step 3 and Step 4 | — | JSON object | Map `data.tls.not_after` (ISO 8601 UTC) into the expiry check input |
| Report generation | — | All query and probe results | Structured text report |

## Key Constraints

- **Timeout**: `cert_probe.py` enforces a 10-second timeout by default (`--timeout`, range 1-30); TCP connect and TLS handshake share this budget
- **Read-only**: query and probe only; no configuration changes; no probe writes to disk
- **JSON contract**: data exchanged between Steps 3-4-5 is JSON; no curl/dig text is parsed downstream
- **Credential security**: prohibited from reading/echoing/printing AK/SK; `cert_probe.py` does not accept credentials
- **Recommended region**: use `--cli-region=<region>`
- **Python script responsibility**: `cert_probe.py` handles TLS probing only; `cert_expiry_check.py` handles only days-remaining calculation; neither handles business flow
- **expiration_time empty**: no calculation performed; report "Expiration time unknown"; expose the raw API response to the user
