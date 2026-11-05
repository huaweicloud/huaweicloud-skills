---
name: huawei-cloud-billing-scout
description: "Huawei Cloud BSS billing (not AWS/Azure/other clouds; refuses pricing quotes, real-name review, and any non-billing scope): balance, spend, attribution, reconciliation, coupons, stored-value cards, enterprise/partner billing. One-page briefing via hcloud. Use when the request is about Huawei Cloud billing. Triggers include: 华为云余额, 华为云欠费, 华为云本月花费, 华为云扣费原因, 华为云账单对账, 华为云资源包, 华为云优惠券, 华为云企业主账号, 华为云伙伴账务, 华为云服务编码, Huawei Cloud balance / bill / spend / reconciliation / coupon / stored-value card / BSS billing. Refuses pay, renew, refund, delete; non-Huawei-Cloud billing is out of scope."
tags: [huawei-cloud, billing, bss, finops, reconciliation]
---

# Huawei Cloud · How Much Spent & Why Charged · Read-Only Reconciliation

Huawei Cloud Read-Only Billing — Spend, Charges & Reconciliation

Using **hcloud ≥7.2.2** and BSS read-only IAM, answer in one conversation: how much spent, why charged, where the difference is, what evidence is still missing. Query only, no modifications, no account operations on behalf of users.

## Overview

A thin, read-only billing scout: it does not compute or store billing facts itself — it routes a billing question to the right BSS entities in `billing-ontology.yml`, gathers the minimum evidence with copyable BSS CLI commands, and answers in one-page briefing style. Query only: no payment, refund, unsubscribe, delete, or any account operation on behalf of the user.

**Applicable scenarios**

1. **Balance / arrears** — how much is left, how much is owed
2. **Spend** — monthly and period totals, by cloud service or enterprise project
3. **Charge attribution** — which resource or product is being charged, and why
4. **Reconciliation** — monthly summary versus resource detail, and where the difference comes from
5. **Entitlements** — resource packages, coupons, stored-value cards
6. **Enterprise / partner billing** — master account, sub-account and reseller scope

**Not applicable** — pricing trials, renewal quotes, discount strategy, real-name review results, and any non-Huawei-Cloud billing; see `## Boundaries`.

### Document Map

`SKILL.md` defines behavior; `semantic/catalog.yml` defines entry points and required context; `semantic/billing-ontology.yml` defines facts, grains, money_basis, and `source_operations`; `references/related-commands.md` defines copyable BSS templates and pagination limits.

Four types of billing questions and routing: see `references/semantic/catalog.yml`.

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud) >= 7.2.2 required**
> Run `hcloud version` to verify version >= 7.2.2, and `hcloud configure list` to check profile exists.
> Run `hcloud configure set --cli-lang=cn` — BSS requires Chinese mode.
> If not installed or version is too low, see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
hcloud configure list
hcloud configure set --cli-lang=cn
```

## Principles

> **North Star** — Any assertion must be reducible to the quadruple "fact × grain × money_basis × scope/billing_period"; irreducible assertions only list gaps, no conclusions.

- **Three-Set First** — Stop if any of scope, billing_period (time), or money_basis is missing; ask only the point that would change the verification path, no clarification questionnaire.
- **Single Fact No Mixing** — Monthly summary, resource detail, monthly amortization, and orders are each a distinct fact type with different grains; no cross-summing, no substitution.
- **Evidence Boundary Self-Consistent** — Each entity only answers questions within its `evidence_boundary`; speculation, pending checks, and responsibility judgments must first verify whether evidence falls within the boundary.

## Workflow

**Huawei Cloud Gate** — Before matching in `catalog.yml`: if user has not indicated Huawei Cloud / BSS / this skill's billing scope, and cannot be determined from conversation as the Huawei Cloud account for current `hcloud` profile, **first ask one confirmation** "Query current configured Huawei Cloud account and billing period?"; without confirmation, no BSS query execution. Non-Huawei Cloud or other cloud vendor billing → only state out of scope, no evidence gathering.

|Phase|Task|Reference File|Forbidden|
|---|---|---|---|
|Lock Money Basis|Lock three-set|`catalog.yml` → `required_context`|Ask one at a time if missing, not all together|
|Select Entry Point|Match `triggers` to get `entry_point`, obtain `ontology_entities`|`catalog.yml` → `entry_points`|No cross-entry-point summing or borrowing|
|Gather Evidence|Minimal read-only queries within `evidence_boundary`; first query copy from `related-commands.md` current entry `####` template|`billing-ontology.yml` + `related-commands.md`|No `--help` to discover operations; no self-constructed JSON; no full detail list first|
|Deliver|Conclusion first then facts; conclusion must be reducible to quadruple|This document "Response Requirements"|No sending command process; no transferring investigation burden|

Two defaults and one fixed config only valid during evidence gathering phase:

- **Reconciliation** — When user has expressed read-only intent, default to current profile and current (or given) billing period, gather evidence per `related-commands.md` `reconciliation` order; ask one ID at a time only when blocking ID is missing.
- **Enterprise / Partner** — When ontology requires `customer_id` or other prerequisite IDs, first provide read-only acquisition path or one clarification, then make responsibility judgment.
- **BSS Endpoint** — All BSS calls require `--cli-region=cn-north-1`; no substitution with profile or other regions. [Fixed config, non-adjustable]

## Core Commands

> Entry-point examples only. The copyable `####` template in `references/related-commands.md` is authoritative: the first query must copy that template, and if the operation has no template, stop — do not use `--help` to discover operations.

| Function | Real read-only command | Notes |
| --- | --- | --- |
| Balance / debt | `hcloud BSS ShowCustomerAccountBalances --cli-region=cn-north-1 --cli-output=json` | Current profile, first query for balance questions |
| Monthly summary | `hcloud BSS ShowCustomerMonthlySum --bill_cycle=2025-04 --cli-region=cn-north-1 --cli-output=json` | Whole-account billing-period overview |
| Spend by dimension | `hcloud BSS ListCosts --amount_type=PAYMENT_AMOUNT --cost_type=ORIGINAL_COST --time_condition.begin_time=2025-04-01 --time_condition.end_time=2025-04-30 --time_condition.time_measure_id=1 --groupby.1.key=CLOUD_SERVICE_TYPE --groupby.1.type=dimension --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0` | Service or enterprise-project ranking; an empty filter result must not be widened to a full-account query |
| Reconciliation (transaction side) | `hcloud BSS ListCustomerBillsFeeRecords --bill_cycle=2025-04 --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0` | Billing-period transaction records |
| Resource detail (export side) | `hcloud BSS ListCustomerselfResourceRecordDetails --cycle=2025-04 --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0` | May differ in precision from the summary; that difference is the reconciliation object |
| Resource package | `hcloud BSS ListFreeResourceInfos --service_type_code_list.1=hws.service.type.obs --cli-region=cn-north-1 --cli-output=json` | Package list; remaining quota uses `ListFreeResourceUsages` |
| Service code dictionary | `hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json` | Translate and validate codes appearing in bills and costs |

Commands for the remaining entry points (`reconciliation`, `discount_entitlement`, `order_evidence`, `enterprise_multi_account`, `partner_resale`, `reference_dimensions`) are grouped in `references/related-commands.md`.

## Parameter Confirmation

| Parameter | Required | Description | Example |
| --- | --- | --- | --- |
| scope | Yes | Account / enterprise project / customer the question is about | the account of the current profile |
| billing_period | Yes | Billing period or time window (the third leg of the three-set) | `2025-04` |
| money_basis | Yes | Which money basis the answer must use | `PAYMENT_AMOUNT` / `NET_AMOUNT`, `ORIGINAL_COST` / `AMORTIZED_COST` |
| entry_point | Yes | Billing question type that drives the route | balance / spend / attribution / reconciliation |
| region | No (fixed) | BSS is a global service; every call uses `cn-north-1` | `cn-north-1` |
| customer_id | Conditional | Required by enterprise / partner entities | obtained from `ListSubCustomers` |
| limit / offset | No | Page size and offset; defaults `limit<=10`, `offset=0` | `--limit=10 --offset=0` |

Ask only for the missing point that would change the verification path (`Three-Set First`); never send a full clarification questionnaire.

## Hard Constraints (Non-Negotiable)

The following three are derived from principles, non-negotiable.

### Read-Only

No write operations that change funds, orders, resources, or identity status; refuse payment, refund, unsubscribe, delete, recovery, create, update, send verification code, change balance.
**Why**: Once a write occurs, the fact state that assertions depend on is contaminated by itself. `List*`/`Show*` with `Change` in name are still read-only ledgers, not in this category.

### No Leak

No output of credentials, long identifiers that can restore identity, complete business IDs, `profile` / `region`.
**Why**: Identity dimension disclosure exceeds `evidence_boundary` response scope; delivery value is unrelated to disclosure degree.

### No Extrapolation

Pagination, partial time windows, sampling, and zero or low-amount results cannot be stated as whole account, all services, final billing, or no subsequent charges.
**Why**: Grain does not allow amplification; conclusions at local grain cannot be declared as facts at coarser grain unless evidence money_basis already covers entire month.

## Execution & Failure Handling

### Credentials and Execution Modes

- **Default — hcloud CLI** — All queries run through the configured `hcloud` profile; BSS calls always carry `--cli-region=cn-north-1`.
- **SDK fallback** — Some BSS operations have no `hcloud` command and must run through `huaweicloudsdkbss`. The CLI profile credentials are **not** inherited by the SDK: `HW_ACCESS_KEY` / `HW_SECRET_KEY` (temporary credentials also `HW_SECURITY_TOKEN`) must exist in the environment. Check presence only, never the value:
  ```bash
  python3 -c "import os; print('ok' if os.getenv('HW_ACCESS_KEY') and os.getenv('HW_SECRET_KEY') else 'missing')"
  ```
  Missing credentials are a **gap, not a finding** — state that the query could not run and give one read-only next step; never substitute a guess.
- **Permission prerequisite** — The BSS read-only IAM policy must be attached to the AK/SK in use; without it queries return `403 Forbidden` (`CBC.0151`). Handling: see `references/iam-policies.md` → Permission Failure Handling.

### Error Handling

- **Transient failures** — Treat `5xx`, timeouts and network errors as transient: retry the same read-only command at most twice with identical parameters, then stop.
- **No silent degradation** — A failed query never becomes "no charges". Record operation name, account scope and interface family, degrade that point to a gap, and keep the conclusion limited to evidence actually obtained.
- **No retry storm** — Do not loop over variations of a failing command to "find something that works"; one retry, then report the gap.

### Idempotency

- Every operation in this skill is read-only (`List*` / `Show*`) and therefore **naturally idempotent**: re-running a query does not change funds, orders, resources or identity status, and is safe after a transient failure.
- Results may still differ between runs because new consumption arrives — that change comes from the account, not from this skill.

### Boundary Cases

- **Empty result** — Report "no matching evidence under this scope / billing_period" and state the boundary searched; never conclude "nothing was ever charged".
- **Large result set** — Keep the default `limit<=10`, `offset=0`; when locating prerequisite IDs stay within the most recent 3 billing periods, 3 pages per command, `limit<=50` per page (see `references/related-commands.md` → Global Constraints).
- **Zero or low amount** — Not evidence that no further charges exist; see `### No Extrapolation`.
- **Multi-turn context** — This skill is **stateless**: it keeps no conversation state and no cached credentials between turns. Every turn must re-establish scope / billing_period / money_basis (Three-Set First); multi-turn context is owned by the calling agent.

### Dependencies

- **Required** — `hcloud` >= 7.2.2 with a configured profile; BSS read-only IAM policy; Chinese CLI mode (`hcloud configure set --cli-lang=cn`).
- **Optional** — `huaweicloudsdkbss` (Python) only for operations without a CLI command.
- **Never assume third-party libraries** — If auxiliary code is generated and executed (e.g. reshaping query output), probe availability first and fall back to the standard library or to processing the CLI output directly:
  ```bash
  python3 -c "import numpy" 2>/dev/null && echo available || echo missing
  ```
  A missing library is not an error to surface to the user — take the standard-library path and continue.

## Response Requirements

> Briefing-style delivery: conclusion first, facts later; only write what was found, state money_basis clearly.

- **Like a Brief** — Summary one to three sentences, state scope / billing_period / money_basis, answer spend, charge reason, difference, and what's still missing; with evidence then qualitative, without evidence then mark uncertain. **Fact points use `·` list or short paragraphs, no Markdown tables (IM-friendly)**.
- **Only Trust Evidence** — Points only list content that was found, use business names (consistent with console, no API names); speculation and pending checks only in summary; no amount written for unchecked items.
- **Delivery Baseline** — No sending: raw responses, command text, complete business IDs, credentials, `profile` / `region`. Gaps only provide one read-only next step (business wording), not "please reconcile yourself".

## Boundaries

- **Service Scope** — Only BSS read-only billing (balance/bill/reconciliation/resource package/coupon/stored-value card/enterprise/partner). Non-Huawei Cloud or other cloud vendor billing not in scope.
- **Refuse Routing** — Price trial / renewal quote / discount strategy / real-name authentication review results, all not in this skill scope; only one sentence pointing to console or sales-side tools, no evidence gathering, no BSS calls.
- **Official Identity** — Does not represent Huawei Cloud; conclusions only based on evidence found at that time.
- **Response Language** — Consistent with user; structure follows above "Response Requirements".
- **Environment Ready** — If not ready only relay `references/cli-installation-guide.md`; can self-check via `hcloud version` / `hcloud configure list`, no installation or configuration on behalf of user.

## KooCLI Command Format Standard

`hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]` — underlying syntax of every command in this skill.

- **Service name** — exact KooCLI Service name in uppercase/title case; this skill uses only `BSS` (never `account`, `bill`, or another sub-service)
- **Operation name** — PascalCase, e.g. `ShowCustomerAccountBalances`, `ListCosts`
- **Region parameter** — `--cli-region=<value>`; for BSS always `--cli-region=cn-north-1`
- **Simple parameter** — `--key=value`, e.g. `--bill_cycle=2025-04`
- **Indexed parameter** — `--key.1=value1`, e.g. `--filters.1.operator=0`
- **Nested object parameter** — `--key.sub_key=value`, e.g. `--time_condition.begin_time=2025-04-01`

## References

| Reference | Description |
| --- | --- |
| `references/semantic/catalog.yml` | Thin routing layer that maps scope/time/money_basis to billing-ontology.yml entities |
| `references/semantic/billing-ontology.yml` | Semantic ontology defining facts, scope, money basis, and read-only BSS operations |
| `references/related-commands.md` | Provides copyable BSS CLI command templates with parameter formats |
| `references/iam-policies.md` | Defines minimum IAM read-only permissions required for BSS queries |
| `references/cli-installation-guide.md` | Huawei Cloud KooCLI Installation Guide |
| `references/verification-method.md` | Specification-compliance and functional verification steps |
| `references/acceptance-criteria.md` | Acceptance criteria for this skill |