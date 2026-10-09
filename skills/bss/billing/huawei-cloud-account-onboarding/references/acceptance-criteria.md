# Acceptance Criteria

Acceptance criteria for the `huawei-cloud-account-onboarding` skill. Each item is independently
testable; all Critical items must pass.

## Critical

| ID | Criterion | How to verify |
| ---- | ----------- | --------------- |
| AC-01 | Skill directory named `huawei-cloud-account-onboarding` under `skills/`, frontmatter `name` matches directory name | `validate-skill.sh` |
| AC-02 | Frontmatter has `name`, `description` (with trigger words), `tags` (≤5); no `version` field | `validate-skill.sh` |
| AC-03 | Both BSS APIs use only real, verified paths: `GET /v2/customers/real-name-auth-status` and `GET /v2/customers/real-name-auth-qrcode` (from SDK `_http_info`) | code review of scripts |
| AC-04 | No credentials hardcoded anywhere in the skill package; AK/SK read from env vars only | `grep` + gitleaks |
| AC-05 | No cross-skill references; no execution of scripts from other skills | `validate-skill.sh` |
| AC-06 | Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents | `validate-skill.sh` |
| AC-07 | `references/iam-policies.md` exists | `validate-skill.sh` |
| AC-08 | Never collects identity data (ID number, ID photos) and never performs auth on the user's behalf | code review of SKILL.md + scripts |

## High

| ID | Criterion | How to verify |
| ---- | ----------- | --------------- |
| AC-09 | `ShowRealNameAuthStatus` returns verified_status/verified_type correctly on a live account | TC-01 |
| AC-10 | `ShowRealNameAuthQrCode` returns a valid `https://` QR URL on a live main account | TC-02 |
| AC-11 | Missing-credential path exits with a clear, non-stacktrace error | `python3 scripts/show_real_name_auth_status.py --missing-creds-check` (TC-03) |
| AC-12 | QR expiry and single-use warnings are always conveyed to the user | SKILL.md review |
| AC-13 | Sub-account permission error (`CBC.99007297`) is mapped to the "use main-account AK/SK" guidance; the script exits `0` with structured JSON `error_code=CBC.99007297` | error table review + TC-02 |

## Medium

| ID | Criterion | How to verify |
| ---- | ----------- | --------------- |
| AC-14 | References use lowercase kebab-case filenames | file listing |
| AC-15 | Total files ≤ 30, total size ≤ 40 MB, SKILL.md ≤ 500 lines | `validate-skill.sh` |
| AC-16 | Fixed region `cn-north-1` / `bss.myhuaweicloud.com` documented and enforced in scripts | code review |

## Non-Goals (explicitly out of scope)

- Creating or modifying accounts
- Collecting/submitting real identity materials
- Automatically polling until authentication completes
- Auto re-fetching expired QR codes
- Other cloud providers' KYC flows