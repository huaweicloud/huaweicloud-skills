---
name: huawei-cloud-cost-estimation
description: >-
  Estimate Huawei Cloud pre-order costs, provision allowlisted resources through
  hcloud, and guide unsubscribe requests through the console. Use when the user
  asks for Huawei Cloud pricing, budgets, resource creation, unsubscribe
  guidance, or hcloud readiness checks.
compatibility:
  hcloud KooCLI 7.2+, matching IAM permissions, and outbound network; the agent does not install
  dependencies
metadata:
  language: en
  translation_of: huawei-cloud-cost-estimation-cn
  author: concept-git
  version: "3.3.0"
  openclaw:
    requires:
      bins: [hcloud]
    primaryEnv: HUAWEICLOUD_SDK_AK
    homepage: https://github.com/concept-git/cloud-concept-skills/tree/main/skills/productivity/en/huawei-cloud-cost-estimation
    envVars:
      - { name: HUAWEICLOUD_SDK_AK, required: false }
      - { name: HUAWEICLOUD_SDK_SK, required: false }
      - { name: HUAWEICLOUD_SDK_REGION, required: false }
---

# Huawei Cloud Quotes and Provisioning

## Overview

Estimate Huawei Cloud pre-order costs with the BSS pricing APIs, provision allowlisted resources through `hcloud` after quoting and confirmation, and guide unsubscribe requests through the console. A quote is an estimate assembled from verified price lines, not a final bill.

Progressive disclosure: this file routes each task to the matching reference; detailed fields, operation lists and pitfalls live in `references/`.

## Prerequisites

- `hcloud` (KooCLI) 7.2 or later, installed and configured locally by the user; the agent does not install dependencies. Readiness and setup: `references/cli-installation.md`.
- IAM permissions matching the quoted and provisioned services; permission failures: `references/iam-policies.md`.
- Outbound network access to the Huawei Cloud endpoints.
- Credentials stay local: never collect AK/SK or tokens in chat, and follow G12 before handling secret-bearing output.
- Read the matching categories in `references/gotchas.md` before deciding or calling `hcloud`.

## Workflow

### Read by task

Before deciding or calling hcloud, read the matching categories in `references/gotchas.md`. Paths below are relative to `references/`; read relevant sections and reuse prior reads.

| Task | Read | Gotchas |
| --- | --- | --- |
| Check hcloud | `cli-installation.md` | A |
| Quote/compare | `pricing/commands.md` | A, B |
| Check compatibility | `lifecycle/concepts.md`: relevant checks | A, C |
| Check existing orders/errors | Current help for the relevant read-only API | A, D |
| Prepare login | `lifecycle/concepts.md`: login selection | E |
| Prepare provisioning | `lifecycle/concepts.md`; selected operation, dependencies and payment fields in `lifecycle/commands.md` | A–D; add E for credentials |
| Unsubscribe/stop | `lifecycle/concepts.md`: unsubscribe section, console guidance only | — |

For provisioning, read pricing files only for unresolved or changed quotes. Route bills/balances to the read-only billing skill or Cost Center; other clouds and non-allowlisted writes to their consoles.

### Quote

1. Establish service, region, configuration, quantity, billing mode and period/usage. Ask missing decision-relevant inputs together. When delegated, choose for the user's budget and purpose. Disclose Linux/empty-AZ/NA assumptions for quotes; obtain billing mode and duration from the user.
2. Resolve the candidate and product billing mapping using the pricing contract. Submit only lines eligible under G03–G06; retain their configuration, source, exact request and matched response.
3. Itemize verified prices and missing items, reconcile totals/currency and state the query date. Reuse the same evidence and line states in exported quotes; this is not a final bill.

### Provision

1. Find the operation in the allowlist and read its current help. Verify dependencies through read-only calls; classify each as supported, incompatible, or unresolved with evidence.
2. Quote the complete configuration and associated costs. For an unverified cost, disclose that charges may apply and obtain separate consent; known incompatibility remains blocking.
3. Build the final request with explicit payment, renewal and login choices. Inspect conditional fields and run global `--dryrun`, following G09/G12. Keep the checked request revision with its evidence.
4. Show the configuration, cost and execution order; associate confirmation with that request. Execute it separately with only global `--dryrun` removed. Follow G09–G11 for edits or failures.
5. Query order/payment and resource outcomes. Report verified results and unresolved items, retaining their IDs with the checked request and confirmation.

### Communication and lookup

Match the user's language; give the conclusion, evidence and next step plainly. Complete clear read-only work without repeated permission requests. Ask only for missing decisions and purchase confirmation; report progress on long tasks.

- Permission failure: `references/iam-policies.md`.
- Field relationships unclear: `references/pricing/rfq-models/rfq-core.yml` and only the relevant billing-mode model.

## Core Commands

Read current operation help before each call: `hcloud <Service> <Operation> --cli-region=<region> --help` (runtime discovery; stop if help fails).

- Every call carries `--cli-region`: BSS pricing uses `cn-north-1`, while resource regions stay the deployment region (G02).
- Add `--cli-output=json` and read the complete response, including business status and pagination scope (G01).
- Provisioning runs global `--dryrun` first; the execution request is the checked request with only global `--dryrun` removed (G09).
- Request fields, pagination and amount fields: `references/pricing/commands.md` (pricing) and `references/lifecycle/commands.md` (provisioning allowlist).

## Parameter Confirmation

Confirm these with the user before quoting or provisioning; ask missing decision-relevant inputs together.

| Parameter | When | Meaning |
| --- | --- | --- |
| Service, resource type, region, billing mode, full spec code | Always | Quote identity; a change requires another lookup and repricing (G03) |
| Quantity, capacity and usage with units | Always | Subscription count, purchased capacity and usage are separate (G04) |
| Period type and count | Yearly/monthly only | `period_type` 2 month / 3 year; price-affecting changes need repricing |
| `--cli-region` | Every call | BSS pricing `cn-north-1`; regional calls use the deployment region (G02) |
| `--cli-output=json` | Every call | Machine-readable evidence; retain the exact request and matched response |
| `--dryrun` | Provisioning | Global dry run only; remove it when executing the checked request (G09) |
| Payment, renewal and login choice | Provisioning | Set explicitly; ECS/EVS default to manual payment (G10) |

## Read-only verification

Run these after setup to confirm the quoting path end to end. Every step is read-only: nothing is created, changed or deleted.

```bash
bash scripts/quote-smoke.sh services
bash scripts/quote-smoke.sh resources
bash scripts/quote-smoke.sh specs
bash scripts/quote-smoke.sh units
bash scripts/quote-smoke.sh price
```

The helper resolves the project from IAM and queries BSS in `cn-north-1`. It temporarily switches the KooCLI catalog language to `cn` (the English catalog omits BSS) and restores it on exit.

## References

| File | Content |
| --- | --- |
| `references/cli-installation.md` | KooCLI readiness, version and connectivity checks, user setup |
| `references/gotchas.md` | Central pitfall library G01–G12 |
| `references/iam-policies.md` | IAM permissions for quoting and allowlisted provisioning |
| `references/lifecycle/commands.md` | Provisioning operation allowlist, dependencies and payment fields |
| `references/lifecycle/concepts.md` | Sales/compatibility checks, login selection, unsubscribe guidance |
| `references/pricing/commands.md` | Pricing commands, fields, constraints and amount handling |
| `references/pricing/rfq-models/rfq-core.yml` | Pricing field relationship contract |
| `references/pricing/rfq-models/rfq-ondemand-model.yml` | Pay-per-use model |
| `references/pricing/rfq-models/rfq-period-model.yml` | Yearly/monthly model |