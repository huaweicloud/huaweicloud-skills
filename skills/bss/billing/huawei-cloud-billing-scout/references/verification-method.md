# Verification Method

How to verify that `huawei-cloud-billing-scout` behaves as specified — specification compliance first, then read-only functional checks.

## 1. Specification compliance (no credentials needed)

```bash
bash skills/devtools/common/huawei-cloud-skill-creator/scripts/validate-skill.sh \
  -s skills/bss/billing/huawei-cloud-billing-scout
```

Expected: `FAIL: 0`.

> Known checker limitation: the CLI-command checks treat the first token after `hcloud` as a Service name, so
> management subcommands such as `hcloud configure list` are reported as "invalid service / operation name" and
> "omits --cli-region". The same warnings appear on other CLI-based skills (e.g. `huawei-cloud-ecs-manage`).

## 2. Frontmatter and structure

```bash
python3 -c "import io,yaml; d=yaml.safe_load(io.open('skills/bss/billing/huawei-cloud-billing-scout/SKILL.md',encoding='utf-8').read().split('---')[1]); print(d['name'], len(d['tags']), 'version' in d); assert d['name']=='huawei-cloud-billing-scout' and len(d['tags'])<=5 and 'version' not in d"
```

Expected: prints `huawei-cloud-billing-scout 5 False` and exits 0.

Required SKILL.md sections (all present): Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents.

## 3. Environment readiness (no credential values printed)

```bash
hcloud version
hcloud configure list
```

Expected: version `>= 7.2.2` and an active profile. Never echo AK/SK.

## 4. Read-only functional verification (needs credentials)

Start from a narrow query; replace `<billing_period>` with a `YYYY-MM` value.

```bash
hcloud BSS ShowCustomerAccountBalances --cli-region=cn-north-1 --cli-output=json
hcloud BSS ShowCustomerMonthlySum --bill_cycle=<billing_period> --cli-region=cn-north-1 --cli-output=json
hcloud BSS ListCustomerBillsFeeRecords --bill_cycle=<billing_period> --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
hcloud BSS ListCustomerselfResourceRecordDetails --cycle=<billing_period> --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json
```

Expected: each call returns a JSON body for the requested scope.

- `403 Forbidden` / `CBC.0151` → the BSS read-only permission is missing; report it as a prerequisite, not as "no bill" (see `iam-policies.md`).
- Empty result → report "no matching evidence under this scope / billing period" together with the boundary searched.

## 5. Behavior checks

| Check | Expected behaviour |
| --- | --- |
| Three-Set First | A question missing scope / billing_period / money_basis triggers exactly one clarification, never a questionnaire |
| Read-only | No write command is ever issued; pay / renew / refund / delete / unsubscribe are refused |
| No Extrapolation | Paginated, partial-window or zero-amount results are never stated as whole-account or final billing |
| No Leak | No credentials, complete business IDs, `profile` or `region` in the answer |
| Briefing style | Conclusion first, `·` list or short paragraphs, no Markdown tables |
| Gap over guess | A failed or empty query becomes a gap plus one read-only next step, with no invented amount |
| SDK fallback credentials | Before an SDK-path query, `HW_ACCESS_KEY` / `HW_SECRET_KEY` presence is checked; absence is reported as a gap |
