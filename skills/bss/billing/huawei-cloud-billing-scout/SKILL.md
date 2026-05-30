---
name: huawei-cloud-billing-scout
description: "Huawei Cloud BSS billing (not AWS/Azure/other clouds; refuses pricing quotes, real-name review, and any non-billing scope): balance, spend, attribution, reconciliation, coupons, stored-value cards, enterprise/partner billing. One-page briefing via hcloud. Use only when the user explicitly mentions 华为云 / Huawei Cloud / BSS and 余额/账单/对账/资源包/代金券/储值卡/企业或伙伴账务; refuses pay, renew, refund, delete."
tags: [huawei-cloud, billing, bss, finops, reconciliation]
---

# Huawei Cloud · How Much Spent & Why Charged · Read-Only Reconciliation

Huawei Cloud Read-Only Billing — Spend, Charges & Reconciliation

Using **hcloud ≥7.2.2** and BSS read-only IAM, answer in one conversation: how much spent, why charged, where the difference is, what evidence is still missing. Query only, no modifications, no account operations on behalf of users.

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud) >= 7.2.2 required**
> Run `hcloud version` to verify version >= 7.2.2, and `hcloud configure list` to check profile exists.
> If not installed or version is too low, see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation guide.

```bash
hcloud version
hcloud configure list
```

## Principles

> **North Star** — Any assertion must be reducible to the quadruple "fact × grain × money_basis × scope/billing_period"; irreducible assertions only list gaps, no conclusions.

- **Three-Set First** — Stop if any of scope, billing_period (time), or money_basis is missing; ask only the point that would change the verification path, no clarification questionnaire.
- **Single Fact No Mixing** — Monthly summary, resource detail, monthly amortization, and orders are each a distinct fact type with different grains; no cross-summing, no substitution.
- **Evidence Boundary Self-Consistent** — Each entity only answers questions within its `evidence_boundary`; speculation, pending checks, and responsibility judgments must first verify whether evidence falls within the boundary.

## Division of Labor

`SKILL.md` defines behavior; `semantic/catalog.yml` defines entry points and required context; `semantic/billing-ontology.yml` defines facts, grains, money_basis, and `source_operations`; `references/related-commands.md` defines copyable BSS templates and pagination limits.

Four types of billing questions and routing: see `references/semantic/catalog.yml`.

## Verification Path

**Huawei Cloud Gate** — Before matching in `catalog.yml`: if user has not indicated Huawei Cloud / BSS / this skill's billing scope, and cannot be determined from conversation as the Huawei Cloud account for current `hcloud` profile, **first ask one confirmation** "Query current configured Huawei Cloud account and billing period?"; without confirmation, no BSS query execution. Non-Huawei Cloud or other cloud vendor billing → only state out of scope, no evidence gathering.

|Phase|Task|Reference File|Forbidden|
|---|---|---|---|
|Lock Money Basis|Lock three-set|`catalog.yml` → `required_context`|Ask one at a time if missing, not all together|
|Select Entry Point|Match `triggers` to get `entry_point`, obtain `ontology_entities`|`catalog.yml` → `entry_points`|No cross-entry-point summing or borrowing|
|Gather Evidence|Minimal read-only queries within `evidence_boundary`; first query copy from `related-commands.md` current entry `####` template|`billing-ontology.yml` + `related-commands.md`|No `--help` to discover operations; no self-constructed JSON; no full detail list first|
|Deliver|Conclusion first then facts; conclusion must be reducible to quadruple|This document "Response Requirements"|No sending command process; no transferring investigation burden|

Two defaults only valid during evidence gathering phase:

- **Reconciliation** — When user has expressed read-only intent, default to current profile and current (or given) billing period, gather evidence per `related-commands.md` `reconciliation` order; ask one ID at a time only when blocking ID is missing.
- **Enterprise / Partner** — When ontology requires `customer_id` or other prerequisite IDs, first provide read-only acquisition path or one clarification, then make responsibility judgment.

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

## References

| Reference | Description |
| --- | --- |
| `references/semantic/catalog.yml` | Thin routing layer that maps scope/time/money_basis to billing-ontology.yml entities |
| `references/semantic/billing-ontology.yml` | Semantic ontology defining facts, scope, money basis, and read-only BSS operations |
| `references/related-commands.md` | Provides copyable BSS CLI command templates with parameter formats |
| `references/iam-policies.md` | Defines minimum IAM read-only permissions required for BSS queries |
| `references/cli-installation-guide.md` | Huawei Cloud KooCLI Installation Guide |