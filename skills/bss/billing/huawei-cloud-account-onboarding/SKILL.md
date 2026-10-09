---
name: huawei-cloud-account-onboarding
description: "Huawei Cloud real-name authentication guidance (BSS): query real-name auth status and get the face-recognition QR code URL via huaweicloudsdkbss. Read-only, no identity data collected, no auth performed on the user's behalf. Use when the user asks about 实名认证 / 认证状态 / 实名 / 账号认证 / 企业认证 / 个人认证 / real-name verification / 认证二维码 / 人脸认证 / 扫码认证 on Huawei Cloud (not AWS/Azure/alibaba/other clouds)."
tags: [huawei-cloud, bss, account, onboarding, real-name-auth]
---

# Huawei Cloud Account Onboarding — Real-Name Authentication Guidance

Read-only conversational guidance for Huawei Cloud real-name authentication: query the current
authentication status (`verified_status` / `verified_type`) and fetch the face-recognition QR code
URL when the customer needs to complete or re-initiate authentication.

> **Execution mode: huaweicloudsdkbss (Python SDK).** As of hcloud CLI 7.2.12, KooCLI reports
> `Unsupported service: BSS`, so this skill executes via the official `huaweicloudsdkbss` Python SDK
> against the BSS endpoint `https://bss.myhuaweicloud.com` (fixed region `cn-north-1`).

## Overview

Huawei Cloud customers must complete real-name authentication before using most services. The
status query and face-auth QR code are scattered across multiple console pages; this skill aggregates
them into a conversational flow so an agent can help the customer in one conversation.

### Feature scope

1. Query real-name authentication status — `verified_status`: `-1` not verified, `0` under review,
   `1` rejected, `2` verified; `verified_type`: `0` personal, `1` enterprise.
2. Get the face real-name authentication QR code URL — single-use, auto-invalidated after 10 minutes,
   main account only (sub-account returns `CBC.99007297`).
3. Confirm completion — after the customer finishes scanning on the phone, query the status again on
   explicit user confirmation (no automatic polling).

### Authentication state flow

```text
-1 (not verified) ──get QR + user scans──▶ 0 (reviewing) ──▶ 2 (verified)
        │                                          │
        └────────────◀── 1 (rejected) ◀────────────┘
                  (re-fetch QR only after asking the user)
```

### Out of scope (red lines, non-negotiable)

- Never collect real identity information (ID number, ID photos, AK/SK).
- Never perform authentication on the user's behalf — QR scanning and face recognition must be done
  by the user on their own phone.
- No automatic polling/waiting for verification; re-query only after user confirmation.
- When the QR code expires, ask the user before re-fetching — never auto re-fetch.
- Huawei Cloud scenarios only; other cloud providers' KYC flows are out of scope.

## Prerequisites

1. **Python 3.8+** with the official SDK installed:

   ```bash
   pip install huaweicloudsdkbss
   ```

2. **Customer main-account AK/SK** (non-partner account) available in environment variables.
   The SDK scripts read credentials automatically from `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
   (fallback: `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`). Never hardcode credentials.
3. **Network access** to `https://bss.myhuaweicloud.com`. Corporate intranets may require:

   ```bash
   export HTTPS_PROXY=http://your-proxy:port
   ```

4. **Fixed region**: BSS is a global service reached at `cn-north-1` → `bss.myhuaweicloud.com`.
   Do not substitute other regions.

## Workflow

```text
Step 1  Confirm intent + Huawei Cloud scope (not other clouds)
Step 2  Check prerequisites (SDK installed, AK/SK env vars present)
Step 3  Query real-name auth status  ->  python3 scripts/show_real_name_auth_status.py
Step 4  Interpret verified_status and answer
         -1  -> offer to fetch QR code (ask user first)
          0  -> tell user review is in progress
          1  -> suggest re-initiation (ask user before fetching a new QR)
          2  -> confirm already verified, no need to repeat
Step 5  If QR needed: run scripts/show_real_name_auth_qr_code.py, show URL,
        warn: single-use + 10-minute expiry + main-account-only
Step 6  On user confirmation, re-query status to confirm completion (no auto-polling)
```

## Core Commands

All commands are read-only (`Show`). Each script exits non-zero with a clear message on error.

### Query real-name authentication status

```bash
python3 scripts/show_real_name_auth_status.py
```

Example response:

```json
{"verified_status": 2, "verified_type": 0}
```

### verified_status semantics

| value | meaning | agent action |
| ------- | --------- | -------------- |
| -1 | not verified | offer QR code (ask user first) |
| 0 | under review | inform user to wait for review |
| 1 | rejected | suggest re-initiation (re-fetch QR only after asking) |
| 2 | verified | inform user; nothing to do |

### verified_type semantics

| value | meaning                                  |
|-------|------------------------------------------|
| 0     | personal real-name auth (个人实名认证)   |
| 1     | enterprise real-name auth (企业实名认证) |

### Get face real-name authentication QR code

```bash
python3 scripts/show_real_name_auth_qr_code.py
```

Example response:

```json
{"qr_code_url": "https://auth.huaweicloud.com/authui/thirdLogin?idp=CHNIDP&service=https%3a%2f%2f..."}
```

Warnings to always pass to the user:

- QR code is **single-use** — it becomes invalid once scanned.
- It **expires in 10 minutes** if not scanned.
- Only the **main account** can fetch it. If the calling credential is a
  sub-account, the API returns `CBC.99007297`; the script then reports a
  structured result and exits `0` (see below), and the agent should tell the
  user to use main-account AK/SK.

### Missing credentials — graceful error

When no AK/SK is present in the environment, both scripts print a clear
`ERROR: AK/SK not found ...` message to stderr and exit with code `2`
(no traceback). To verify this behavior in an environment that already has
credentials set, run the bundled self-test:

```bash
python3 scripts/show_real_name_auth_status.py --missing-creds-check
```

It re-runs the script with every credential env var stripped, checks the
graceful-error contract (exit `2`, clear message, no traceback), and exits `0`
with a JSON summary when the behavior matches.

## Parameter Confirmation

| Parameter | Required | Description | Source |
| ----------- | ---------- | ------------- | -------- |
| `HUAWEICLOUD_SDK_AK` / `HUAWEI_ACCESS_KEY` | Yes | Customer main-account Access Key | environment |
| `HUAWEICLOUD_SDK_SK` / `HUAWEI_SECRET_KEY` | Yes | Customer main-account Secret Key | environment |
| `HTTPS_PROXY` | No | Corporate proxy for intranet access | environment |
| region | Fixed | `cn-north-1` → `bss.myhuaweicloud.com` | hardcoded in scripts |

The two APIs take no request parameters.

## Error Handling

| Error code | Meaning | Agent action |
| ------------ | --------- | -------------- |
| `CBC.0151` | Access denied | Ask user to check the AK/SK validity |
| `CBC.99007297` | Sub-account has no permission for the QR API | Script exits `0` with structured JSON `{"qr_code_url": null, "error_code": "CBC.99007297", ...}`; tell the user to use the main-account AK/SK |
| `CBC.0100` | Invalid parameter | Check the request parameters |
| `CBC.0999` | Other | Recommend contacting Huawei Cloud support |
| missing AK/SK | Credentials not set | Both scripts print `ERROR: AK/SK not found ...` to stderr and exit `2` (no traceback). Self-test: `python3 scripts/show_real_name_auth_status.py --missing-creds-check` |
| network error | Connection failed | Suggest setting `HTTPS_PROXY` |

## Reference Documents

- [IAM Policies](references/iam-policies.md) — least-privilege policy for BSS real-name auth read-only access
- [Verification Method](references/verification-method.md) — how to verify the skill end-to-end
- [Dataflow Diagram](references/dataflow-diagram.md) — Mermaid sequence diagram of the skill flow
- [Acceptance Criteria](references/acceptance-criteria.md) — pass/fail criteria per feature
- [Related Commands](references/related-commands.md) — API summary, status codes, and quick reference