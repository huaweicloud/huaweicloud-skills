# SCM v3 API Reference (Read-Only)

Data source: Huawei Cloud **SCM v3 OpenAPI**, verified against the
`huaweicloudsdkscm` v3 client source (`scm_client.py` `_http_info`
`resource_path`) and the KooCLI SCM template metadata (v7.3.12).

## Endpoints

| Operation | Method | Path | IAM action |
|-----------|--------|------|------------|
| `ListCertificates` | GET | `/v3/scm/certificates` | `scm:cert:list` |
| `ShowCertificate` | GET | `/v3/scm/certificates/{certificate_id}` | `scm:cert:get` |

Endpoint host: `scm.{region}.myhuaweicloud.com` (for example
`scm.cn-north-4.myhuaweicloud.com`). Only these two read-only operations are
used by this skill.

## ListCertificates Request Parameters

| Query parameter | Type | Used as | Notes |
|-----------------|------|---------|-------|
| `content` | string | `--name` | Fuzzy search by certificate name or bound domain; max 255 chars |
| `status` | string | `--status` | See status values below; default `ALL` |
| `expired_days_since` | integer | `--expiring N` | Certificate is within validity or expires in at most N days; max 1095 |
| `limit` | integer | paging | 10 / 20 / 50 per page (the script uses 50) |
| `offset` | integer | paging | Query offset |
| `enterprise_project_id` | string | `--enterprise-project-id` | `all`, `0` or an enterprise project UUID |
| `owned_by_self` | boolean | `--include-shared` | `true` (default) = own resources only; `false` = own + shared |
| `sort_key` | string | `--sort-key` | `certExpiredTime` (default in this skill), `certStatus`, `certUpdateTime` |
| `sort_dir` | string | `--sort-dir` | `ASC` or `DESC` |
| `deploy_support` | boolean | not exposed | Filter deployable certificates only |

There is no dedicated `name` request parameter; the official API uses `content`
for certificate-name/domain fuzzy search. The skill maps `--name` to `content`
so the filter is evaluated server-side.

## ListCertificates Response

```json
{
  "certificates": [
    {
      "id": "1234567890abcdef",
      "name": "example.com",
      "domain": "example.com",
      "sans": "www.example.com",
      "signature_algorithm": "SHA256-RSA",
      "deploy_support": true,
      "type": "DV_SSL_CERT",
      "brand": "GLOBALSIGN",
      "expire_time": "2026-12-31 23:59:59",
      "domain_type": "MULTI_DOMAIN",
      "validity_period": 12,
      "status": "ISSUED",
      "domain_count": 5,
      "wildcard_count": 0,
      "description": "",
      "domain_id": "01a0...",
      "enterprise_project_id": "0"
    }
  ],
  "total_count": 1
}
```

- `certificates` — list of `CertificateDetail` objects.
- `total_count` — total number of certificates matching the filters (paging is
  evaluated against this value).
- The list model does **not** include `issue_time`; the skill keeps the field in
  the output as `null`/`-` unless a deployment returns it. `show` supplies the
  issuance time.

## ShowCertificate Response

```json
{
  "id": "1234567890abcdef",
  "status": "ISSUED",
  "order_id": "CS...",
  "name": "example.com",
  "type": "DV_SSL_CERT",
  "brand": "GLOBALSIGN",
  "push_support": "true",
  "revoke_reason": null,
  "signature_algorithm": "SHA256-RSA",
  "issue_time": "2026-01-01 00:00:00",
  "not_before": "2026-01-01 00:00:00",
  "not_after": "2026-12-31 23:59:59",
  "validity_period": 12,
  "validation_method": "DNS",
  "domain_type": "MULTI_DOMAIN",
  "multi_domain_type": "primary_single",
  "domain": "example.com",
  "sans": "www.example.com",
  "domain_count": 5,
  "wildcard_count": 0,
  "fingerprint": "SHA1-FINGERPRINT",
  "shared": false,
  "application_info": {},
  "description": "",
  "enterprise_project_id": "0",
  "authentification": []
}
```

`ShowCertificate` never returns the certificate private key. The mutating
`ExportCertificate` operation (which can return key material) is out of scope.

## Field Mapping

| Output field | List source | Show source |
|--------------|-------------|-------------|
| `id` | `id` | `id` |
| `name` | `name` | `name` |
| `type` | `type` | `type` |
| `domain` | `domain` | `domain` |
| `sans` | `sans` | `sans` |
| `status` / `status_label` | `status` | `status` |
| `issue_time` | `issue_time` (usually absent) | `issue_time` |
| `not_before` / `not_after` | absent | `not_before` / `not_after` |
| `expire_time` | `expire_time` | `expire_time` or `not_after` |
| `days_to_expire` | derived from `expire_time` | derived from `expire_time` / `not_after` |
| `expiry_level` / `expiry_label` | derived | derived |
| `brand` | `brand` | `brand` |
| `signature_algorithm` | `signature_algorithm` | `signature_algorithm` |
| `domain_type` | `domain_type` | `domain_type` |
| `validity_period` | `validity_period` | `validity_period` |
| `deploy_support` | `deploy_support` | `push_support` |
| `enterprise_project_id` | `enterprise_project_id` | `enterprise_project_id` |

Derived fields:

- `days_to_expire = (expire_date - today_utc).days` — negative when expired.
- `expiry_level` — `expired` (< 0 or status `EXPIRED` without a date),
  `expiring` (0 … threshold), `normal` (> threshold), `unknown` (no date).
  The threshold defaults to 30 days and is set by `--expire-days`.

## Markdown Export Field Mapping

`list --output` renders the normalized records described above; it performs **no
extra API call**. Exported columns map one-to-one to the terminal table:

| Markdown column | Normalized field | Note |
|-----------------|------------------|------|
| 证书 ID | `id` | — |
| 名称 | `name` | — |
| 类型 | `type` | SCM type code (e.g. `DV_SSL_CERT`, `OV_SSL_CERT`, `EV_SSL_CERT`, upload/managed type) |
| 绑定域名 | `domain` | `sans` (additional domains) is not a column; it stays visible in `show` |
| 状态 | `status_label` → `status` | Chinese label, falls back to the SCM code |
| 签发时间 | `issue_time` | normalized `YYYY-MM-DD`; `-` because the list model omits it |
| 到期时间 | `expire_time` | normalized `YYYY-MM-DD` |
| 剩余天数 | `days_to_expire` | negative when expired |
| 到期等级 | `expiry_label` | `已过期` / `即将到期` / `正常` / `未知`; the header summary carries the `expired`/`expiring`/`normal` legend and the active threshold |

Summary block sources: `Region` = effective region; `查询条件` = the applied
`--name` / `--status` / `--expiring` / `--expire-days` / `--enterprise-project-id`
/ `--include-shared` / sort / `--limit` / `--offset`; `记录数` =
`返回 <len(certs)> 张（服务端匹配 <total_count> 张）`. Full format specification:
`references/markdown-export.md`.

## Status Values

| Status | Meaning |
|--------|---------|
| `PAID` | Paid; waiting for certificate application |
| `ISSUED` | Issued |
| `CHECKING` | Application under review |
| `CANCELCHECKING` | Cancellation under review |
| `UNPASSED` | Application failed |
| `EXPIRED` | Expired |
| `REVOKING` | Revocation under review |
| `CANCLEREVOKING` | Revocation cancellation under review |
| `REVOKED` | Revoked |
| `UPLOAD` | Managed/uploaded certificate |
| `CHECKING_ORG` | Organization verification pending |
| `ISSUING` | To be issued |
| `SUPPLEMENTCHECKING` | Additional domain under review |
| `CANCELSUPPLEMENTING` | Additional-domain cancellation under review |
| `ALL` | All statuses |

## Error Envelopes

SCM returns errors as a JSON object:

```json
{"error_code": "SCM.4002", "error_msg": "Permission denied ..."}
```

The script maps 401/403 to an authentication/permission hint, 400 to a
parameter/region hint, and other statuses to a generic SCM error. Error text is
sanitized: the `Authorization` header, security token, AK and SK are never
included.