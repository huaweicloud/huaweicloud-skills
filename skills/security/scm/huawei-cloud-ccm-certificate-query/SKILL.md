---
name: huawei-cloud-ccm-certificate-query
description: >-
  Query Huawei Cloud CCM (Cloud Certificate Manager) SCM SSL certificate
  inventory and export it as a Markdown file. Lists certificates with
  server-side certificate-name/domain and status filters, shows one
  certificate's detail, derives remaining days to expiry plus an expiry grade,
  and exports the same result to Markdown (default
  ccm_certificates_<region>_<timestamp>.md). Strictly read-only (no apply,
  purchase, revoke, deploy, import, export-certificate or delete). Trigger
  scenarios: daily inspection, certificate expiry reminder, troubleshooting,
  manual Q&A and scheduled calls from other Agents. Triggers include:
  查询华为云CCM列表, 查询SSL证书列表, 证书到期查询, 证书清单, 证书到期提醒,
  SSL证书巡检, 查看证书详情, 证书剩余天数, 云证书管理服务, 导出证书清单,
  证书列表导出md, 证书清单导出, 导出CCM证书清单, 证书巡检报告,
  list CCM certificates, query SSL certificates, certificate expiry check,
  certificate inventory, SSL certificate inspection, show certificate detail,
  export certificate inventory, certificate report markdown, Huawei Cloud CCM.
tags: [huawei-cloud, ccm, scm, certificate, readonly]
---

# Huawei Cloud CCM Certificate Query

## Overview

This skill queries Huawei Cloud CCM (云证书管理服务) **SCM SSL certificates** through
the SCM v3 OpenAPI. It is designed for certificate inventory inspection and expiry
reminders, and its `--json` output is directly consumable by other Agents.

Capabilities:

- **List certificates** (`list`) — `GET /v3/scm/certificates` (`ListCertificates`).
  - Server-side filtering by certificate name/domain (`--name` → API `content`)
    and certificate status (`--status` → API `status`).
  - Automatic offset pagination over the whole result set; `--limit` caps the
    total number of records returned.
  - Derived fields: `days_to_expire` and `expiry_level`
    (`expired` / `expiring` / `normal`) based on `expire_time`.
  - **Markdown export** (`list --output <path>`) — writes the same result as a
    self-contained `.md` document (summary block + nine-column table). The file
    content is echoed to stdout, so the export and the console output are line-for-line identical.
- **Show certificate detail** (`show`) — `GET /v3/scm/certificates/{certificate_id}`
  (`ShowCertificate`), including issuer time, validity window, status,
  domains, algorithm, fingerprint and domain-validation information.
- **Human output** — aligned table (list) or field list (show).
- **Machine output** — `--json` returns a stable structured document suitable for
  scheduled Agents and downstream automation.
- **Archivable output** — Markdown export for inspection reports and distribution.

Scope boundaries:

- ✅ Read-only SCM SSL certificate list and detail queries, plus local Markdown export.
- ❌ CSV / HTML / PDF / Excel export, mail delivery, OBS upload.
- ❌ PCA private certificates and CAs — out of scope.
- ❌ Any mutating operation (apply, purchase, subscribe, revoke, deploy, push,
  import, `ExportCertificate`, delete, tag write) — no entry point is provided.
  The Markdown export is a local file write only; no cloud resource is created or changed.
- ❌ The certificate private key is never requested or printed.

### Relationship to the base skill (Issue #1096 / PR #973)

This skill is one deliverable with two increments:

- **Issue #1096 / PR #973** created the skill and its `list` / `show` query
  capability (filters, pagination, derived expiry fields, table and `--json` output).
- **Issue #1098** (this iteration) **extends that same skill** with the Markdown
  export — no new skill directory, no duplicate trigger set. The query layer
  (`build_list_query`, `collect_certificates`, `normalize_certificate`) is reused
  unchanged; only the rendering layer gained `render_markdown` and the `--output` flag.

Trigger words are shared, not duplicated: query triggers keep the original
wording, and the export-specific ones (`导出证书清单`, `证书列表导出md`,
`证书清单导出`, `certificate report markdown`) point at the same skill.

## Prerequisites

1. **Python 3.8+** — standard library only; no third-party packages required.
2. **Huawei Cloud AK/SK** — configured **out of band** as environment variables:
   - `HUAWEI_ACCESS_KEY` (or `HUAWEI_AK` / `HW_ACCESS_KEY` / `HWC_ACCESS_KEY`)
   - `HUAWEI_SECRET_KEY` (or `HUAWEI_SK` / `HW_SECRET_KEY` / `HWC_SECRET_KEY`)
   - Optional temporary credential token: `HUAWEI_SECURITY_TOKEN`
   - Never paste AK/SK into a chat or a command line; the script never echoes them.
3. **Region** — `--region <region>` or `HUAWEI_REGION` / `HW_REGION_NAME`
   (default `cn-north-4`, e.g. `cn-north-4`, `cn-east-3`, `ap-southeast-1`).
4. **IAM permissions** — `scm:cert:list` for list, `scm:cert:get` for show.
   See `references/iam-policies.md` for a least-privilege policy.
5. **Network** — outbound HTTPS to `scm.{region}.myhuaweicloud.com`
   (override with `--endpoint`, mainly for tests or private endpoints).

## Workflow

1. **Confirm target region** and make sure AK/SK are exported in the shell
   environment (out of band). Do not request secrets in conversation.
2. **Choose the operation** — `list` for inventory/expiry inspection, `show`
   when a certificate ID is already known.
3. **Run the script** with filters and output mode:
   `python3 scripts/list_certificates.py list ...` or `... show ...`.
4. **Read the result** — default table for humans; `--json` for Agents;
   `--output <path>` to export the same result as Markdown (also echoed to stdout).
5. **Handle empty/error results** — empty list is a success (`total: 0`, exit 0)
   and never produces an empty Markdown file; credential/permission/region/path
   errors are reported with readable hints and a non-zero exit code, never with
   AK/SK values.

## Core Commands

```bash
# List every certificate in the region (automatic pagination)
python3 scripts/list_certificates.py list --region cn-north-4

# Filter by certificate name or bound domain (server-side fuzzy search)
python3 scripts/list_certificates.py list --region cn-north-4 --name example.com

# Filter by certificate status (server-side)
python3 scripts/list_certificates.py list --region cn-north-4 --status ISSUED

# Combine filters and cap the total number of records
python3 scripts/list_certificates.py list --region cn-north-4 \
  --name example --status ISSUED --limit 20

# Certificates expiring within 30 days (server-side expiry window)
python3 scripts/list_certificates.py list --region cn-north-4 --expiring 30

# JSON output for Agents (stable schema, parseable)
python3 scripts/list_certificates.py list --region cn-north-4 --json

# Export the same result as Markdown into the current directory
# (default name: ccm_certificates_<region>_<timestamp>.md)
python3 scripts/list_certificates.py list --region cn-north-4 --output .

# Export with filters, an explicit file path, and a 45-day expiry threshold
python3 scripts/list_certificates.py list --region cn-north-4 \
  --status ISSUED --expiring 60 --expire-days 45 \
  --output ./reports/ccm-certificates-2026-11.md

# Show one certificate by ID
python3 scripts/list_certificates.py show --region cn-north-4 \
  --cert-id 1234567890abcdef

# Show one certificate as JSON
python3 scripts/list_certificates.py show --region cn-north-4 \
  --cert-id 1234567890abcdef --json
```

### Output Fields

| Field | Meaning |
|-------|---------|
| `id` | Certificate ID |
| `name` | Certificate name |
| `type` | Certificate type (DV/OV/EV SSL variants) |
| `domain` | Primary bound domain |
| `sans` | Additional domains (multi-domain certificates) |
| `status` | SCM status code (`ISSUED`, `EXPIRED`, `UPLOAD`, …) |
| `status_label` | Human-readable status label (Chinese) |
| `issue_time` | Issuance time when supplied by the API, else `null`/`-` |
| `not_before` / `not_after` | Validity window (detail response) |
| `expire_time` | Expiry time used for grading |
| `days_to_expire` | Remaining whole days (negative when already expired) |
| `expiry_level` | `expired` / `expiring` / `normal` / `unknown` |
| `expiry_label` | Human-readable expiry grade (Chinese) |
| `brand` | Certificate brand |
| `signature_algorithm` | Signature algorithm |
| `domain_type` | `SINGLE_DOMAIN` / `WILDCARD` / `MULTI_DOMAIN` |
| `validity_period` | Validity in months |
| `deploy_support` | Whether the certificate supports deployment |
| `enterprise_project_id` | Enterprise project ID |
| `description` | Certificate description |

`list --json` envelope:

```json
{
  "region": "cn-north-4",
  "total": 1,
  "returned": 1,
  "filters": {"name": null, "status": "ISSUED", "expiring": null},
  "expiry_threshold_days": 30,
  "certs": [
    {
      "id": "1234567890abcdef",
      "name": "example.com",
      "type": "DV_SSL_CERT",
      "domain": "example.com",
      "status": "ISSUED",
      "status_label": "已签发",
      "issue_time": "2026-01-01 00:00:00",
      "expire_time": "2026-12-31 23:59:59",
      "days_to_expire": 49,
      "expiry_level": "normal",
      "expiry_label": "正常"
    }
  ]
}
```

The number of records actually returned is `returned`; the server-reported total
for the applied filters is `total` (it may exceed `returned` when `--limit` is
used or pagination is interrupted).

### Expiry Grading

- `expired` — `days_to_expire < 0`, or status is `EXPIRED` when the expiry date
  is missing.
- `expiring` — `0 <= days_to_expire <= --expire-days` (default 30).
- `normal` — `days_to_expire > --expire-days`.
- `unknown` — no usable expiry date.

### Markdown Export (`list --output`)

`--output PATH` renders the identical query result as a Markdown document and
writes it to disk. `PATH` may be:

| `--output` form | Result |
|-----------------|--------|
| `.` / `/abs/dir` (existing directory) | file created inside it as `ccm_certificates_<region>_<timestamp>.md` |
| `./dir/` (trailing separator) | same default name inside that directory |
| `./reports/inventory.md` | that exact file path (parent directory must exist) |
| omitted | no file is written (terminal table only) |

Document layout:

1. `# 华为云 CCM 证书清单`
2. Summary table — `Region`, `查询条件` (name/status/expiring/expire-days/enterprise
   project/include-shared/sort/limit/offset), `生成时间`, `记录数`
   (`返回 N 张（服务端匹配 M 张）`), `到期分级` legend.
3. Result table with nine columns — 证书 ID / 名称 / 类型 / 绑定域名 / 状态 /
   签发时间 / 到期时间 / 剩余天数 / 到期等级.
4. A read-only data-source footer.

Rules:

- Cell values are identical to the terminal table (`-` for missing values,
  dates normalized to `YYYY-MM-DD`, expiry grade shown as its Chinese label
  with the `expired` / `expiring` / `normal` legend in the summary block).
- `|`, backslash and CR/LF are escaped (`\|`, `<br>`) so the table never breaks.
- The Markdown text is printed to stdout as well, so `stdout` and the file are
  byte-identical; the export confirmation goes to stderr.
- **An empty result never creates a file**: it prints
  `未查询到任何证书（total: 0），未生成 Markdown 文件。` and exits `0`.
- `--output` and `--json` are mutually exclusive (exit `2`).
- The export is a local file write; the API traffic stays read-only.

## Parameter Confirmation

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `list` / `show` | Yes | — | Query mode (one subcommand per invocation) |
| `--region` | No | `cn-north-4` or `HUAWEI_REGION` | SCM region; also used in the endpoint |
| `--name` | No (list) | — | Fuzzy server-side search by certificate name or domain (`content`) |
| `--status` | No (list) | `ALL` | Server-side status filter; accepts SCM codes or lowercase aliases |
| `--expiring` | No (list) | — | Server-side window: only certificates expiring within N days (`expired_days_since`) |
| `--expire-days` | No (list) | `30` | Local expiry-grade threshold in days |
| `--limit` | No (list) | all | Maximum total records returned; automatic paging otherwise |
| `--offset` | No (list) | `0` | Starting offset for pagination |
| `--enterprise-project-id` | No (list) | — | Enterprise project filter (`all` / `0` / UUID) |
| `--include-shared` | No (list) | false | Also query certificates shared with the tenant (`owned_by_self=false`) |
| `--sort-key` | No (list) | `certExpiredTime` | `certExpiredTime` / `certStatus` / `certUpdateTime` |
| `--sort-dir` | No (list) | `ASC` | `ASC` / `DESC` |
| `--cert-id` | Yes (show) | — | Certificate ID to show |
| `--json` | No | false | Emit structured JSON instead of a table (mutually exclusive with `--output`) |
| `--output` | No (list) | — | Export the same result as a Markdown file; path may be a file, an existing directory, or a path ending with `/` (default name `ccm_certificates_<region>_<timestamp>.md`); markdown is also echoed to stdout |
| `--endpoint` | No | `scm.{region}.myhuaweicloud.com` | Endpoint override (tests/private endpoints) |
| `--timeout` | No | `30` | HTTP timeout in seconds |

Status aliases accepted by `--status` (case-insensitive): `ALL`, `PAID`,
`ISSUED`, `CHECKING`, `CANCELCHECKING`, `UNPASSED`, `EXPIRED`, `REVOKING`,
`REVOKED`, `UPLOAD`, `CHECKING_ORG`, `ISSUING`, `SUPPLEMENTCHECKING`,
`CANCELSUPPLEMENTING`, `CANCLEREVOKING`.

## Error Handling

| Situation | Behavior | Exit code |
|-----------|----------|-----------|
| No matching certificates | Prints an empty table / `{"certs": [], "total": 0}`; with `--output` prints `未查询到任何证书…未生成 Markdown 文件。` and writes nothing | `0` |
| Invalid arguments / unknown status | Readable Chinese hint, lists valid choices | `2` |
| `--output` + `--json` together | Readable hint: choose one output mode | `2` |
| `--output` parent directory missing / unwritable target | Readable hint naming the directory or file and how to fix it; nothing is written | `2` |
| Missing AK/SK | Prints an out-of-band env-var template; never asks in chat, never prints secrets | `3` |
| Invalid/expired credentials (HTTP 401) | Readable hint that credentials are invalid or expired | `4` |
| Insufficient permission (HTTP 403) | Readable hint naming the required IAM actions (`scm:cert:list` / `scm:cert:get`) | `4` |
| Invalid region / unreachable endpoint | Readable hint to check region and network; endpoint host is shown, secrets are not | `5` |
| Other SCM API error | Error code plus sanitized message from the API | `6` |

The script never logs or prints `Authorization`, `X-Security-Token`, AK or SK.
When `--json` is used, errors are still written to stderr; stdout stays parseable
JSON on success.

Read-only guarantee: the script issues only `GET` requests to the two read-only
paths above. It contains no POST/PUT/PATCH/DELETE request path and no code for
apply, purchase, revoke, deploy, push, import, export or delete.

## Reference Documents

| File | Contents |
|------|----------|
| [references/api.md](references/api.md) | SCM v3 endpoints, request parameters, response fields, field mapping and status codes |
| [references/markdown-export.md](references/markdown-export.md) | Markdown export: naming rules, path resolution, summary/table layout, escaping, error classes |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policy for list/show queries |
| [references/verification-method.md](references/verification-method.md) | Offline unit tests and live read-only verification procedure |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance checklist mapped to commands and expected evidence |
| [references/troubleshooting.md](references/troubleshooting.md) | Common failures (401/403/region/empty results) and diagnosis steps |