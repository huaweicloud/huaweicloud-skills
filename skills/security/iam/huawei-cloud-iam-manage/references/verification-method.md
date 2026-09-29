# Verification Method

## 1. Environment verification

```bash
hcloud configure list            # must show a valid AKSK profile
hcloud IAM ListUsersV5 --cli-region=cn-north-4 --limit=1   # smoke query
```

## 2. Feature verification

Each `huawei_*` action should be verified against a non-production account or a sandbox project:

| Action class | Verification steps |
| ------------ | ----------------- |
| Query (R3) | Run each `list_*` command; assert the JSON/table output matches the console (总用户数/组数/策略数>0 or expected empty). |
| Analyze (R3) | Run `huawei_analyze_iam_least_privilege` / `huawei_analyze_iam_password_compliance`; assert risk tables are produced and consistent with raw `list_*` + `ListAttached*` data. |
| Create (R2) | (1) Pre-check list shows no such resource → (2) create → (3) read-back query shows the new resource. |
| Attach/Detach (R2) | Attach a policy to a test user → `ListAttachedUserPoliciesV5` shows it → detach → not listed. |
| Create AK/SK (R2) | Create → response contains AK + SK (SK shown once, not stored) → `ListPermanentAccessKeys` shows the AK. |
| Config login (R2) | Create/update login profile with a throwaway password → `ShowLoginProfileV5` reflects it; enable login protect → `ShowUserLoginProtect` reflects it; disable again. |
| Delete (R1) | Create a throwaway user/group/agency/AK-SK/policy → confirm impact list → delete → read-back shows absence → cleanup done. |

## 3. Compliance checks (local, offline)

| Check | Command |
| ----- | ------- |
| SKILL.md exists and ≤ 500 lines | `wc -l SKILL.md` |
| Frontmatter name/description/tags | `grep -E '^(name\|description\|tags):' SKILL.md` |
| No hardcoded credentials | `grep -rEn '(AK[A-Z]* *[:=] *[A-Z0-9]{16,}\|secret ?key *[:=])' .` |
| No `version:` in frontmatter | `grep -n '^version:' SKILL.md` |
| File count ≤ 30, ext allowlist | `find . -type f \| wc -l` |
| Final PR scope = one skill dir | `git diff origin/master..HEAD --stat` |

## 4. Acceptance gate

Run 20 action smoke tests (query actions auto; write actions with confirm) against a sandbox account.
All Query R3 = automatic pass; all Manage R2/R1 = pass only after confirmation flow verified and
resources cleaned up. Record per-action pass/fail in the test report.