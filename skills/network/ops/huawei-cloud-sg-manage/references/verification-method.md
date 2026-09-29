# Verification Method — huawei-cloud-sg-manage

End-to-end verification after installation. All commands are read-only except the
explicitly-marked R2/R1 ones, which MUST run in a **dedicated sandbox project** and only
after confirmation.

## 1. Prerequisite checks

```bash
hcloud version                     # KooCLI 7.2.x+
hcloud configure list              # valid profile (mode AKSK) or AK/SK env vars set
export PATH="$HOME/.local/bin:$PATH" && bash scripts/ensure_cli.sh
python3 scripts/huawei-cloud.py list_actions   # must list all 11 actions
```

## 2. Query (R3 — safe on any project)

```bash
python3 scripts/huawei-cloud.py huawei_list_security_groups region=cn-north-4 --limit 5
python3 scripts/huawei-cloud.py huawei_list_security_group_rules region=cn-north-4
python3 scripts/huawei-cloud.py huawei_get_security_group security_group_id={sg_id} region=cn-north-4
```

**Pass:** exit 0, JSON with `"success": true`, non-empty-ish lists.

## 3. Analyze (R3 — read-only)

```bash
python3 scripts/huawei-cloud.py huawei_diagnose_sg_port_connectivity \
  security_group_id={sg_id} direction=ingress protocol=tcp port=22 remote=10.0.0.0/8 region=cn-north-4
python3 scripts/huawei-cloud.py huawei_analyze_sg_rule_conflict security_group_id={sg_id} region=cn-north-4
python3 scripts/huawei-cloud.py huawei_audit_sg_overexposed_rules security_group_id={sg_id} region=cn-north-4
```

**Pass:** JSON with `verdict` (ALLOW/DENY/INDETERMINATE), `findings` arrays and a
`summary` with counts; exit code 0.

## 4. Manage (R2/R1 — sandbox project, confirmation required)

1. **Preview gate:** run the action WITHOUT `confirmed=true` → must return
   `"preview": true`, the exact hcloud command, and an impact/warning block; no resource
   is changed.
2. **Create (R2):** create a sandbox SG, add a rule, update its name — verify each with
   the query actions.
3. **Delete (R1):** delete the rule and the SG — verify removal with
   `huawei_list_security_group_rules` / `huawei_list_security_groups`.
4. **Negative test:** `huawei_create_sg_rule` without `direction` → clear error.

**Pass:** every mutation is preceded by a preview, all resources created are cleaned up,
deletion warnings were shown.

## 5. Cleanup

Ensure no sandbox resources remain after the test (delete created SGs/rules).