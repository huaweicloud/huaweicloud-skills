# Security Guide - Credential Handling & Secure Configuration

Operational security rules for the `huawei-cloud-maas-tokens-usage` skill. This document holds the detailed
guidance (including the refusal template for user-provided AK/SK) that [SKILL.md](../SKILL.md) summarizes in its
`## Authentication` section. For the underlying security architecture (tool separation, credential-lifecycle
diagram, leakage-risk elimination), see [security-design.md](security-design.md).

## Table of Contents

- [1. Security Rules](#1-security-rules)
- [2. Handling User-Provided Credentials](#2-handling-user-provided-credentials)
- [3. Secure Credential Configuration Methods](#3-secure-credential-configuration-methods)
- [4. Credentials File Formats](#4-credentials-file-formats)
- [5. `--notify-url` Webhook Security (SSRF Protection)](#5---notify-url-webhook-security-ssrf-protection)
- [6. Why These Rules Exist](#6-why-these-rules-exist)
- [7. References](#7-references)

---

## 1. Security Rules

> **Must be followed in every interaction with this skill:**

| # | Rule |
|---|------|
| 1 | **Prohibited** — reading, echoing, or printing AK/SK values (never log them, never show them in output, never echo them back) |
| 2 | **Prohibited** — asking the user to input AK/SK directly in the conversation |
| 3 | **Prohibited** — accepting AK/SK directly provided by the user in the conversation |
| 4 | **Prohibited** — using `hcloud configure set` (or any CLI argument / shell variable) to pass plaintext credential values |
| 5 | **Prohibited** — hardcoding AK/SK in scripts, or exporting them to shell variables or stdout |
| 6 | **Prohibited** — implementing SDK-HMAC-SHA256 signing manually (must use `huaweicloudsdkcore.Signer`) |
| 7 | **Prohibited** — passing `HW_SECURITY_TOKEN` as a CLI argument (it is read from the environment or the credentials file by the script only) |
| 8 | **Only allowed** — read credentials from environment variables or a credentials file (`--credentials-file`); they stay in Python process memory |
| 9 | **Mandatory** — keep the query scope read-only (read MaaS statistics only; never modify MaaS services, endpoints, API keys, or IAM policies) |
| 10 | **Prohibited** — pointing `--notify-url` at a plain-HTTP URL, an IP literal, or any host outside the Huawei Cloud allowlist; never disable TLS verification for the notification |

> The full list of prohibited operations (including non-security capability constraints) is also tabulated in
> [SKILL.md](../SKILL.md) under `## ⛔ Prohibited Operations (Security Constraints)`.

---

## 2. Handling User-Provided Credentials

If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):

1. **Stop immediately** — Do not execute any commands
2. **Politely refuse** and return the following message:

   ```
   For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.

   Please use one of the following secure methods to configure credentials:

   Method 1: Environment variables (permanent AK/SK)
       export HW_ACCESS_KEY=<your-access-key-id>
       export HW_SECRET_KEY=<your-access-key-secret>

   Method 2: Environment variables (temporary AK/SK + Security Token)
       export HW_ACCESS_KEY=<your-temp-access-key-id>
       export HW_SECRET_KEY=<your-temp-access-key-secret>
       export HW_SECURITY_TOKEN=<your-security-token>

   Method 3: Credentials file
       Create a file (e.g., ~/aksk.txt) with AK on line 1, SK on line 2, Security Token on line 3 (if using temporary credentials).
       Then use: --credentials-file ~/aksk.txt

   After configuration is complete, please retry your request.
   ```

3. **Do not continue** executing any Huawei Cloud operations until credentials are configured

> **Credential-free alternative:** if the user cannot or will not configure credentials, do not fall back to asking
> for them in chat — explain the secure configuration methods above and stop.

---

## 3. Secure Credential Configuration Methods

### Method 1 — Environment variables (permanent AK/SK)

```bash
export HW_ACCESS_KEY=<your-access-key-id>
export HW_SECRET_KEY=<your-access-key-secret>
```

### Method 2 — Environment variables (temporary AK/SK + Security Token)

```bash
export HW_ACCESS_KEY=<your-temp-access-key-id>
export HW_SECRET_KEY=<your-temp-access-key-secret>
export HW_SECURITY_TOKEN=<your-security-token>
```

`HW_SECURITY_TOKEN` is only needed for temporary (STS) credentials. The script reads it and the
`huaweicloudsdkcore.Signer` sends it as the `X-Security-Token` request header — it is never placed on the command
line, so it never appears in `ps -ef` or shell history.

Verify without printing values:

```bash
python3 -c 'import os,sys;ak=os.environ.get("HW_ACCESS_KEY","");sk=os.environ.get("HW_SECRET_KEY","");ok=bool(ak) and bool(sk);print("AK/SK configured OK" if ok else "ERROR: HW_ACCESS_KEY/HW_SECRET_KEY not set");sys.exit(0 if ok else 1)'
```

On Windows, set them as **system environment variables** through the GUI (System Properties → Advanced →
Environment Variables), not with `setx`, which records the value in command history. See
[cli-installation-guide.md](cli-installation-guide.md) for the step-by-step walkthrough.

### Method 3 — Credentials file (`--credentials-file`)

```bash
python3 scripts/maas_rest_usage_stats.py --credentials-file ./creds.txt --last-days 7
```

All three file formats below are accepted, and **all three support the Security Token** (temporary credentials).

---

## 4. Credentials File Formats

| Format | Layout | Example |
|--------|--------|---------|
| `KEY=VALUE` | one assignment per line | `HW_ACCESS_KEY=<ak>`<br>`HW_SECRET_KEY=<sk>`<br>`HW_SECURITY_TOKEN=<token>` |
| CSV | three comma-separated columns; the **third column** is the token | `<ak>,<sk>,<token>` |
| One value per line | **third line** is the token | line 1 `<ak>`<br>line 2 `<sk>`<br>line 3 `<token>` |

```
# Format 1: KEY=VALUE (comments starting with # and blank lines are ignored)
HW_ACCESS_KEY=<your-access-key-id>
HW_SECRET_KEY=<your-access-key-secret>
HW_SECURITY_TOKEN=<your-security-token>
```

```
# Format 2: CSV (third column = Security Token; omit it for permanent AK/SK)
<your-access-key-id>,<your-access-key-secret>,<your-security-token>
```

```
# Format 3: one value per line (line 3 = Security Token; omit the line for permanent AK/SK)
<your-access-key-id>
<your-access-key-secret>
<your-security-token>
```

> For permanent AK/SK, the third column/line (`HW_SECURITY_TOKEN`) may be omitted.
> The file must be a **readable UTF-8 text file** (the script opens it with `encoding="utf-8"`). If it does not exist the script stops with `Error: Credentials file not found: <path>`; if it exists but cannot be read (directory, permission denied, non-UTF-8/UTF-16 bytes, other `OSError`) it stops with `Error: Cannot read credentials file <path>: <msg>` — both on stderr with exit code 1.
> Never commit a credentials file to version control, and never print its contents.

---

## 5. `--notify-url` Webhook Security (SSRF Protection)

`--notify-url URL` posts the query summary JSON to a webhook after the table is printed. Because the skill
otherwise only talks to Huawei Cloud endpoints, the URL is treated as untrusted input and validated **during
parameter validation — before credentials are read and before any query is sent**.

**Allowed vs. rejected URLs:**

| Check | Allowed | Rejected |
|-------|---------|----------|
| Scheme | `https` | `http`, `ftp`, `file`, any other scheme |
| Host | non-empty DNS name | empty host |
| Host type | DNS name | IP literal (IPv4 dotted-quad or IPv6 containing `:`) |
| Domain | `myhuaweicloud.com`, `huaweicloud.com`, or any subdomain of either (e.g. `maas.myhuaweicloud.com`) | any other domain, look-alikes such as `myhuaweicloud.com.evil.example` |
| TLS | `verify=True` (always, not configurable) | `verify=False` is never used |

**Rejection (validation stage, nothing sent):**

```
Error: --notify-url rejected: only HTTPS URLs on trusted Huawei Cloud hosts (*.myhuaweicloud.com / *.huaweicloud.com) are allowed; the request was NOT sent.
```

Exit code `1`; neither the ShowStatistics query nor the notification is sent.

**Delivery failure (after a successful query):** the table is printed normally, stderr gets

```
Warning: failed to send --notify-url notification: <msg>
```

and the **exit code stays `0`** — a webhook problem must not mask a successful query.

**Payload** (`Content-Type: application/json`, timeout 10 s):

```json
{
  "region": "cn-southwest-2",
  "period": "2026-05-08 00:00:00 ~ 2026-05-21 00:00:00 (CST)",
  "total_tokens": 2482084.98,
  "prompt_tokens": 2456504.362,
  "completion_tokens": 24872.928,
  "total_requests": 67188,
  "total_errors": 8002
}
```

> Token values are sent in the API's original unit (thousand), exactly as returned/aggregated — not converted to M tokens.

On success the script prints `Results sent to webhook: <url>`. The payload never contains AK/SK, the security
token, or request headers.

---

## 6. Why These Rules Exist

| Risk point | Exposure if violated | Mitigation |
|------------|----------------------|------------|
| Credentials typed in the conversation | Leaked into chat history / transcripts | Refuse (section 2) and use env vars or `--credentials-file` |
| Credentials hardcoded in a script | Leaked in source code and version control | Read from env vars / file at runtime |
| Credentials passed as CLI arguments | Visible in `ps -ef` and shell history | No credential CLI arguments in this skill |
| `hcloud configure set` with plaintext values | Recorded in command history | Environment variables or `--credentials-file` instead |
| Credentials printed or logged | Leaked into logs, terminal scrollback | Never print or log credential values |
| Manual SDK-HMAC-SHA256 implementation | Signing bugs, accidental credential exposure | Always use `huaweicloudsdkcore.Signer` |
| Credentials persisted after the query | Credentials remain on disk / in memory | Read fresh per invocation; destroyed when the Python process exits |
| `--notify-url` pointed at an arbitrary host | SSRF: the query summary (and internal network access) could leak to an attacker-controlled endpoint | HTTPS-only + Huawei Cloud host allowlist + IP-literal rejection, enforced before the query is sent |

---

## 7. References

| Document | Description |
|----------|-------------|
| [SKILL.md](../SKILL.md) | Skill overview, `## Authentication` summary, `## ⛔ Prohibited Operations` table, `## Security Design` |
| [security-design.md](security-design.md) | Security architecture: tool separation, leakage-risk elimination, credential lifecycle |
| [cli-installation-guide.md](cli-installation-guide.md) | Credentials configuration, Windows GUI env var setup |
| [troubleshooting.md](troubleshooting.md) | Credentials/API error symptoms and solutions |
