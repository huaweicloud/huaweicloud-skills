# Verification Method — huawei-cloud-sg-manage

End-to-end verification after installation. All commands are read-only except the
explicitly-marked R2/R1 ones, which MUST run in a **dedicated sandbox project** and only
after confirmation.

Run everything from the skill directory
(`skills/network/ops/huawei-cloud-sg-manage`).

## 1. Prerequisite and failure-path checks (offline, no credentials needed)

```bash
hcloud version
python3 scripts/huawei-cloud.py list_actions
PATH=/nonexistent python3 scripts/huawei-cloud.py huawei_list_security_groups
env -u HUAWEI_ACCESS_KEY -u HUAWEI_SECRET_KEY -u HUAWEICLOUD_SDK_AK -u HUAWEICLOUD_SDK_SK \
  -u HW_ACCESS_KEY -u HW_SECRET_KEY HCLOUD_CONFIG_DIR=/nonexistent \
  python3 scripts/huawei-cloud.py huawei_list_security_groups
```

**Pass:** `list_actions` returns exactly the 11 `huawei_*` actions; the two failure calls
return within 2 seconds with `"success": false` and `error_code` `cli_missing` /
`credentials_missing` plus a `hint` — never an empty list, never a traceback.

Timeout path (no network): `HCLOUD_TIMEOUT=2` against an unreachable region endpoint must
return `error_code=timeout` within ~2 seconds.

## 2. Query (R3 — safe on any project)

```bash
python3 scripts/huawei-cloud.py huawei_list_security_groups region=cn-north-4
python3 scripts/huawei-cloud.py huawei_list_security_group_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_get_security_group security_group_id=<sg-id> region=cn-north-4
```

**Pass:** exit 0, JSON with `"success": true`, non-empty-ish lists.

## 3. Analyze (R3 — read-only, one query per resource)

```bash
python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
  security_group_id=<sg-id> direction=ingress protocol=tcp port=22 remote=10.0.0.0/8
python3 scripts/huawei-cloud.py huawei_analyze_sg_rule_conflict security_group_id=<sg-id>
python3 scripts/huawei-cloud.py huawei_audit_sg_overexposed_rules security_group_id=<sg-id>
```

**Pass:** JSON with `verdict` (ALLOW/DENY/INDETERMINATE), `findings` arrays and a
`summary` with counts; exit code 0. Diagnose issues exactly two hcloud calls (Show +
Rules) — a repeated call for the same SG inside one intent is a defect (per-process cache
in `scripts/sg/common.py`).

## 4. Manage (R2/R1 — sandbox project, confirmation required)

1. **Preview gate:** run the action WITHOUT `confirmed=true` → must return
   `"preview": true`, the exact hcloud command, `preconditions`, `impact`, `rollback`
   and a warning block; no resource is changed.
2. **L5 three-part check:** every write preview carries 前置确认 (`preconditions`),
   影响范围 (`impact`), 回滚 (`rollback`, plus `current_values` / `rules_snapshot` /
   `captured_rule` where a restore needs them).
3. **Create (R2):** create a sandbox SG, add a rule, update its name — verify each with
   the query actions; then delete the created rule/SG by the ids returned.
4. **Delete (R1):** preview first (rule snapshot exported), delete the rule and the SG —
   verify removal with `huawei_list_security_group_rules` / `huawei_list_security_groups`.
5. **Negative test:** `huawei_create_sg_rule` without `direction` → `error_code=missing_parameter`,
   exit 1, readable hint.

**Pass:** every mutation is preceded by a preview, all resources created are cleaned up,
deletion warnings were shown, and the rollback command in each preview is copy-pasteable.

## 5. Cleanup

Ensure no sandbox resources remain after the test (delete created SGs/rules).