# Acceptance Criteria — huawei-cloud-iam-diagnose

This checklist mirrors the acceptance criteria from GitCode issue #784.

## 1. Registration & routing

- [x] SKILL.md conforms to the GitCode Skill registration specification (frontmatter name/description/tags, required sections).
- [x] All 8 `huawei_*` actions are declared and routable:

| # | Action | Script |
|---|--------|--------|
| 1 | `huawei_list_attached_user_policies` | `scripts/list_attached_user_policies.py` |
| 2 | `huawei_list_attached_group_policies` | `scripts/list_attached_group_policies.py` |
| 3 | `huawei_list_user_groups` | `scripts/list_user_groups.py` |
| 4 | `huawei_list_iam_agencies` | `scripts/list_iam_agencies.py` |
| 5 | `huawei_diagnose_user_permission` | `scripts/diagnose_user_permission.py` |
| 6 | `huawei_trace_permission_chain` | `scripts/trace_permission_chain.py` |
| 7 | `huawei_check_group_permission` | `scripts/check_group_permission.py` |
| 8 | `huawei_check_agency_permission` | `scripts/check_agency_permission.py` |

## 2. CLI dependency

- [x] `hcloud IAM` CLI dependency declared correctly: KooCLI 7.2.12+ supported, `hcloud configure`
      produces `~/.hcloud/config.json` which the SDK scripts read as the credentials fallback.
- [x] KooCLI command-format standard documented (service `IAM`, PascalCase operations,
      `--cli-region`).

## 3. Read-only & R3

- [x] All 8 actions are read-only and R3 auto-execute (no write operations; no MFA confirmation gate).
- [x] Only IAM namespace scripts are used; no other skill is referenced.

## 4. Precision grading

- [x] Predefined system policy + group inheritance → 高 (high)
- [x] Custom policy without Condition → 中 (medium)
- [x] Policy with Condition → 低 (low)
- [x] Agency stacking → 中 (medium)
- [x] EPS authorization → 中 (medium)

## 5. Output semantics

- [x] Verdicts worded as **大概率有/无权限** (likely has / likely has not), not an authoritative
      auth conclusion.
- [x] Custom policy + Condition + agency stacking always marked **仅供参考 (for reference only)**.
- [x] When 100% certainty is needed, skill guides to IAM console / actual API trial call / CTS audit
      (see verification-method.md).

## 6. Auth modes

- [x] AK/SK credentials via `HW_ACCESS_KEY` / `HW_SECRET_KEY` environment variables.
- [x] Local hcloud profile via `~/.hcloud/config.json` (with `HCLOUD_PROFILE` selection).