# Acceptance Criteria

Criteria are checked by the reviewer before merge; `references/verification-method.md` gives the executable checks.

## Functional

| ID | Criterion | How to check |
| --- | --- | --- |
| AC-01 | Routing — every billing question maps to exactly one `entry_point` in `references/semantic/catalog.yml`; the six applicable scenarios in `SKILL.md` → Overview cover the documented scope | Route each scenario by hand and confirm a single entry point |
| AC-02 | Three-Set First — a question missing scope / billing_period / money_basis triggers **one** clarification for the blocking point only | Inspect an answer to an underspecified question |
| AC-03 | Evidence-first — the conclusion is reducible to the quadruple "fact × grain × money_basis × scope/billing_period"; an irreducible assertion lists gaps instead of a conclusion | Manual review of a sample answer |
| AC-04 | Read-only — no write operation is issued at any point; pay / renew / refund / delete / unsubscribe are refused with one sentence pointing to the console | Command review + refusal walkthrough |
| AC-05 | No Extrapolation — paginated, partial-window, sampled or zero-amount results are never stated as whole-account, all-services, or final billing | Manual review |
| AC-06 | No Leak — the answer contains no credentials, restorable long identifiers, complete business IDs, `profile` or `region` | Manual review |
| AC-07 | Briefing style — conclusion first, facts as a `·` list or short paragraphs, no Markdown tables, one page maximum | Manual review |
| AC-08 | Gap over guess — a failed or empty query is reported as a gap plus one read-only next step; no amount is written for unchecked items | Simulate `403 CBC.0151` and an empty result |
| AC-09 | Partner prerequisite — coupon **quota** operations state the partner-account requirement and offer the console path instead of reporting "no coupons" | Trigger with a non-partner account |
| AC-10 | SDK fallback credentials — the SDK path checks `HW_ACCESS_KEY` / `HW_SECRET_KEY` presence (values never printed) and reports absence as a gap | Inspect `SKILL.md` → Execution & Failure Handling, `related-commands.md` → Global Constraints |
| AC-11 | Core Commands are real and executable — every command in `SKILL.md` → Core Commands carries `--cli-region=cn-north-1` and runs read-only with `--limit=10` | Run each command |
| AC-12 | Service-code acquisition — the reference-dimension route explains obtaining a `service_type_code` via `ListServiceTypes` instead of inferring it | Inspect `related-commands.md` → reference_dimensions |

## Compliance and packaging

| ID | Criterion |
| --- | --- |
| AC-13 | `validate-skill.sh` reports `FAIL: 0` for this skill |
| AC-14 | Package limits: ≤ 30 files, total content ≤ 40 MB, `SKILL.md` ≤ 500 lines |
| AC-15 | One PR changes only this Skill directory |
| AC-16 | No hardcoded AK/SK and no in-session credential-entry form anywhere in the package |
| AC-17 | No direct cross-Skill calls; adjacent capabilities are referenced by name only in documentation |

## Non-functional

| ID | Criterion |
| --- | --- |
| AC-18 | No installation or configuration is performed on the user's behalf; the skill only relays `references/cli-installation-guide.md` |
| AC-19 | The skill does not claim to represent Huawei Cloud; conclusions are limited to the evidence found |
| AC-20 | Undeclared dependencies are not assumed: auxiliary code probes third-party libraries before use and falls back to the standard library |
