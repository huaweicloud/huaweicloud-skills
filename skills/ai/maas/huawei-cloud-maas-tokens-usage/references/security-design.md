# Security Design - Credential Lifecycle & Tool Separation

Detailed security architecture for Huawei Cloud MaaS tokens usage query. Referenced by SKILL.md.

## Table of Contents

- [Tool Separation for Security](#tool-separation-for-security)
- [Credential Leakage Risk Elimination](#credential-leakage-risk-elimination)
- [Security Flow: Credential Lifecycle](#security-flow-credential-lifecycle)

---

## Tool Separation for Security

| Operation | Tool | Reason |
|-----------|------|--------|
| Credential loading | Python `os.environ` / file read | AK/SK read into Python process memory only, never exported |
| Request signing | Python `huaweicloudsdkcore.Signer` | SDK-HMAC-SHA256 signing inside Python process; AK/SK never on CLI |
| HTTP POST | Python `requests` | Signed request sent from Python process; no shell, no `ps -ef` leakage |
| Timezone resolution | Python `datetime` | Auto-detect OS local timezone; no hardcoded CST |
| Time range segmentation | Python `datetime` | Auto-segment ranges > 30 days; aggregate in Python memory |

## Credential Leakage Risk Elimination

| Risk Point | Old Method (Insecure) | New Method (Secure) |
|------------|----------------------|---------------------|
| Credential input | User types AK/SK in conversation → leaked in chat history | Read from env vars or `--credentials-file` → never in conversation |
| Credential storage | Hardcoded in script → leaked in source code | Env vars or credentials file → IAM-controlled access |
| Request signing | Manual SDK-HMAC-SHA256 implementation → error-prone, may leak | `huaweicloudsdkcore.Signer` → battle-tested, in-process only |
| HTTP request | `curl` with `--header "Authorization: ..."` → leaked via `ps -ef` | Python `requests.post(headers=signed_headers)` → process memory only |
| Temporary credentials | `X-Security-Token` passed via CLI → leaked via `ps -ef` | `X-Security-Token` added by SDK signer in Python → process memory only |
| Credential lifetime | Persists in shell history / command history | Read fresh per script invocation; never recorded in history |

## Security Flow: Credential Lifecycle

```
1. Python reads AK/SK from env vars (HW_ACCESS_KEY / HW_SECRET_KEY) or --credentials-file (in memory only)
2. Python reads HW_SECURITY_TOKEN if present (temporary credentials, in memory only)
3. Python resolves time range from --from / --to or user expression (last 7/14/30 days, this month)
4. Python auto-segments ranges > 30 days into multiple ≤ 30-day segments
5. Python builds request body (service_type, start_time, end_time, timezone, infer_type, api_keys)
6. Python SDK Signer signs the request (AK/SK in process memory, never exported)
7. Python requests.post sends signed request to modelarts.{region}.myhuaweicloud.com
8. Python receives response, aggregates segments, converts token units (thousand → M tokens)
9. Python prints statistics table (Total/Prompt/Completion Tokens, Requests, Errors, Error Rate)
10. Python process exits — AK/SK variable destroyed with process
```

> **⚠️ Critical: AK/SK is never persisted**
>
> AK/SK exists only in the Python process memory for the duration of the script execution.
> When the Python process exits, the AK/SK variable is destroyed automatically.
> There is no KMS encryption, no credential caching, no credential export — the simplest and safest design.

---

## References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview and core workflows |
| [troubleshooting.md](troubleshooting.md) | Common query issues and solutions |