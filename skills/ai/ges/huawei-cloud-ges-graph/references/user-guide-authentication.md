# Authentication and Token Guide

## GES IAM Authentication (Three Methods, Priority High→Low)

1. **`GES_TOKEN`** — a pre-issued IAM token placed in the environment (highest priority, valid ~24h).
2. **AK/SK (recommended)** — `HUAWEI_CLOUD_AK`/`HUAWEI_CLOUD_SK` (or `access_key`/`secret_key` in the CSV).
   The code signs an `hw_access_key` token request against IAM.
3. **Username/password** — `GES_USERNAME`/`GES_PASSWORD`/`GES_DOMAIN_NAME` (fallback when AK/SK is unavailable).

**Auth failure behavior**: when IAM or the GES API returns `401/403/418`, the script raises an explicit
"认证失败，请检查 AK/SK、用户名密码或 GES_TOKEN" error so the cause (wrong credentials / expired token /
region mismatch) is immediately visible instead of a generic HTTP error.

## GitCode Platform Note (issue tracking / PR push context)

GitCode.com has **disabled Git Basic Auth**. For any Git/API interaction with GitCode (e.g. pushing the
skill repo, commenting on issues), authenticate with an **API Token**:

- **API (GitCode v5)**: `PRIVATE-TOKEN: <token>` header, or `Authorization: Bearer <token>`.
- **Git push over HTTPS**: use `https://oauth2:<token>@gitcode.com/...` (or an SSH key). Plain
  `https://user:password@gitcode.com/...` is rejected.
- Tokens are issued in GitCode account settings → Access Tokens; scope at least `api` for issue/PR automation.

> This does NOT affect GES graph access. GES always uses IAM auth described above.