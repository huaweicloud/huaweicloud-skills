# Data Flow Diagram — CDN Domain Ownership Verification Diagnosis

```mermaid
flowchart TD
    subgraph Input[Input Parameters]
        DOMAIN["domain_name<br/>(required)"]
        REGION["--cli-region=<region>"]
    end

    subgraph PreCheck[Prerequisites Check]
        CHK_CLI["hcloud version ≥ 3.2.0"]
        CHK_PY["python ≥ 3.8 + requests ≥ 2.25 + dnspython ≥ 2.1"]
        CHK_CRED["hcloud configure list<br/>credentials valid?"]
        CHK_DOM{"Target domain<br/>user-provided?"}
        ASK_DOM["Ask the user for the domain;<br/>if unknown, list domains via<br/>ListDomains/v2 and let the user choose"]
        CHK_CRED --> CHK_DOM
        CHK_DOM -->|no| ASK_DOM
    end

    subgraph Step1[Step 1: Verification Info Query + Permission Check]
        S1["ShowVerifyDomainOwnerInfo<br/>--domain_name=<domain>"]
        RET1{"Response?"}
        S1 --> RET1
        RET1 -->|404 / CDN.0171| ERR1["Abort: domain not under current account"]
        RET1 -->|403| ERR2["Abort: insufficient permission"]
        RET1 -->|200| RET2{"Verification method?"}
        RET2 -->|dns_verify_type=TXT| DNS["DNS TXT verification"]
        RET2 -->|file_verify_url| FILE["File verification"]
        RET2 -->|already passed| PASS["Report: cache latency, recommend refresh"]
    end

    subgraph Step2[Step 2: File Verification Probe]
        S3["python scripts/file_probe.py --url file_verify_url [--timeout 10]"]
        RET3{"Probe JSON?"}
        S3 --> RET3
        RET3 -->|http_status=200 + content_preview matches| OK3["File verification passed ✅"]
        RET3 -->|http_status=404| FAIL3["File verification failed ❌"]
        RET3 -->|error.reason=connect_timeout| TIMEOUT3["Probe timed out ⚠️"]
    end

    subgraph Step3[Step 3: DNS TXT Verification]
        S4["python scripts/dns_txt_probe.py --name dns_query_name [--resolver ip] [--timeout 10]"]
        RET4{"Probe JSON?"}
        S4 --> RET4
        RET4 -->|txt_records contains verify_content| OK4["DNS verification passed ✅"]
        RET4 -->|empty/mismatch (dns_no_answer)| FAIL4["DNS verification failed ❌"]
        RET4 -->|error.reason=dns_timeout| TIMEOUT4["Probe timed out ⚠️"]
    end

    subgraph Step4[Step 4: Report Generation]
        REPORT["Structured text diagnosis report<br/>- Analysis time<br/>- Target domain<br/>- Diagnosis item list<br/>- Conclusion and fix recommendations"]
    end

    Input --> PreCheck
    CHK_CRED -->|credentials invalid| ERR_CRED["Abort: prompt to configure credentials"]
    CHK_DOM -->|provided| Step1
    Step1 -->|file verification| Step2
    Step1 -->|DNS TXT verification| Step3
    Step1 -->|already passed| PASS
    Step2 --> Step4
    Step3 --> Step4
    PASS --> Step4
    Step4 --> OUTPUT["Return diagnosis report"]
```

## Data Flow Summary

| Phase | Command | Input | Output |
|-------|---------|-------|--------|
| Prerequisites check | `hcloud configure list` + `python -c "import requests, dns.resolver"` | None | Credential status + library availability |
| Verification info query + permission check | `ShowVerifyDomainOwnerInfo` | domain_name | dns_verify_type, dns_verify_name, file_verify_url, verify_content (200 = domain belongs to current account) |
| File probe | `python scripts/file_probe.py --url` | file_verify_url | JSON `{result, data:{url, http_status, content_length, content_preview, duration_ms, error}, error_msg}` |
| DNS probe | `python scripts/dns_txt_probe.py --name [--resolver]` | dns_query_name | JSON `{result, data:{name, resolver, txt_records, duration_ms, error}, error_msg}` |
| Report generation | — | Probe JSON fields | Structured text report |

Edge labels between probe nodes and the report are JSON objects (not free-form
text): the report reads `data.http_status` / `data.content_preview` from the file probe
and `data.txt_records` / `data.resolver` from the DNS probe.

## Key Constraints

- **Timeout**: each Python probe script enforces a 10-second timeout via `--timeout` (default 10)
- **JSON output**: each probe emits a single JSON object on stdout; stderr is reserved for diagnostic logs
- **Read-only**: query and probe only, no configuration changes; HEAD/GET and DNS TXT only
- **Credential security**: do not read/echo/print AK/SK; probe scripts accept no credentials
- **Recommended region**: use `--cli-region=<region>`
