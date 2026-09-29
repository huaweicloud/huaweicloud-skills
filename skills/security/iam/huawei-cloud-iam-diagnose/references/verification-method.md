# Verification Method

This skill is a **reference** permission analysis. This document explains how to verify a verdict
and how to reach 100% certainty when required.

## 1. Self-check before trusting a verdict

1. **Credentials scope** — did any step report `HTTP 403`? If yes, the verdict is built on partial
   data and should be labelled accordingly.
2. **Group/agency chain coverage** — confirm both `group_domain_roles` and
   `group_all_project_roles` (and agency equivalents) returned data or an explicit error.
3. **Policy document availability** — policy docs are marked "拉取失败/无权限" when they could not
   be read; treat those as unknown.
4. **Confidence grade** — re-check the grade against the `Condition` presence, policy type
   (preset vs custom), and source (group vs agency vs EPS).

## 2. Cross-validation with the real check interfaces

For group and agency chains, run the true check:

```bash
python3 scripts/check_group_permission.py \
  --group_id=<g> --role_id=<r> --scope=domain --domain_id=<d>
python3 scripts/check_agency_permission.py \
  --agency_id=<a> --role_id=<r> --scope=domain --domain_id=<d>
```

- `HAS (HTTP 204)` → the group/agency indeed holds the role.
- `NO (HTTP 404)` → it does not.
- `ERROR 403` → the caller lacks IAM admin permission; cannot verify via the API.

## 3. Reaching 100% certainty (beyond this skill)

When the user needs a definitive answer, escalate to one of these authoritative sources:

1. **IAM console** — IAM > Users > user > Permission (授权记录), and IAM > Agencies.
2. **Actual API trial call** — call the target service API with the user's credentials; a real
   `403` is the authoritative answer.
3. **CTS (Cloud Trace Service) audit logs** — query for the user's `action` attempts; a recorded
   `denied` event is authoritative.

## 4. Precision-grade definitions

| Grade | Meaning | When |
|---|---|---|
| 高 (high) | static Allow/Deny mapping with high confidence | preset system policy + group inheritance |
| 中 (medium) | mapping may be correct | custom policy without Condition; agency stacking; EPS authorization |
| 低 (low) | cannot be trusted | statement contains a `Condition` (context-dependent) |

**仅供参考 (for reference only)** — any combination of custom policy + `Condition` + agency
stacking. Do not state definitively that access is or is not granted in these cases.

## 5. Acceptance test matrix (functional)

| # | Test | Expected |
|---|---|---|
| 1 | `list_user_groups.py --user_name=<known>` | returns the user's groups or "not in any group" |
| 2 | `list_attached_user_policies.py --user_name=<known>` | lists direct policies or empty |
| 3 | `list_attached_group_policies.py --group_id=<known>` | lists policies or empty |
| 4 | `list_iam_agencies.py` | lists agencies |
| 5 | `diagnose_user_permission.py --user_name=<u> --action=ecs:servers:list` | prints a verdict + chain + confidence |
| 6 | `trace_permission_chain.py --user_name=<u> --json` | prints JSON with chains |
| 7 | `check_group_permission.py` with a known role | `HAS`/`NO`/`ERROR` clearly reported |
| 8 | `check_agency_permission.py` with a known role | `HAS`/`NO`/`ERROR` clearly reported |