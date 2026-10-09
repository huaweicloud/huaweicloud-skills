---
name: huawei-cloud-cost-estimation
description: "Estimate Huawei Cloud resource prices before purchase — read-only pre-order price estimation. Triggers include: 华为云/huaweicloud/hcloud + 报价/询价/价格/价格估算/预算/比价/费用预估/budget/cost estimation/quote/pricing. Use when the user asks how much a Huawei Cloud resource will cost (period 包年包月 or on-demand 按需) on 华为云/Huawei Cloud/hcloud. Runs a 4-step RFQ flow (Parse → Clarify → Query → Verify & Present) over hcloud BSS pricing APIs in fixed region cn-north-1: period quote (ListRateOnPeriodDetail) and on-demand quote (ListOnDemandResourceRatings), with dimension resolution chains (ListServiceTypes/ListServiceResources/ListResourceSpecs/ListUsageTypes/ListMeasureUnits). Refuses any history bill/balance/reconciliation, purchase/provision, unsubscribe/delete, credentials in chat, and non-Huawei pricing."
tags: [huawei-cloud, bss, pricing, cost-estimation, finops]
---

# Huawei Cloud · Pre-Purchase Price Estimation · Read-Only RFQ

## Overview

Huawei Cloud cost estimation via **hcloud** ≥7.2.2 — BSS read-only pricing. **Use when** the user
mentions Huawei Cloud / 华为云 / hcloud together with pricing intents: 报价, 询价, 价格,
价格估算, 预算, budget, 比价, cost estimation, quote, pricing, price estimate. Triggers include
these pricing/estimation keywords on Huawei Cloud contexts. Answer: how much will this resource
cost (period or on-demand), where the difference is between specs/billing modes, what a combined
quote sums to. Query only; no provisioning, no purchase, no unsubscribe, no history bills, no
credentials.

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud) >= 7.2.2** and BSS read-only IAM.
> `hcloud BSS` always uses the fixed region `--cli-region=cn-north-1`; the resource deploy region is
> carried inside each quote line's `region` field.

```bash
hcloud version
hcloud configure list
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json --limit=1
```

If not installed or authenticated, point the user to
[references/cli-installation-guide.md](references/cli-installation-guide.md). Do NOT configure
credentials on the user's behalf and do NOT accept AK/SK/token pasted in chat.

## Scope

### In scope (read-only)

| Step | What it answers |
| --- | --- |
| Dimension resolve | service type, resource type, resource spec, usage type, measure unit codes |
| Period quote | year/month package price for one or more lines |
| On-demand quote | pay-per-use price for one or more lines |
| Presentation | line-item sum = total; CNY; official price by default, discounted only if returned |

### Out of scope — route, don't execute

| Request | Routing |
| --- | --- |
| History bills / balance / reconciliation | 费用中心 or BSS read-only billing APIs (do not use this skill) |
| Purchase / provision / create / renew / delete / unsubscribe | console guidance only; never run CLI write commands |
| Non-Huawei cloud pricing | refuse politely |
| AK/SK/token in chat | point to cli-installation-guide.md |
| Remembering or guessing prices | prices only from the current hcloud response |

## Principles

1. **Price only from the current response** — no fabrication, no analogy, no memory.
2. **Params only from the current `--help`** — never guess parameter names.
3. **Read-only** — every operation is a `List*`/`Show*`/read-only pricing POST; nothing mutates your account.
4. **Route out-of-scope safely** — out-of-scope intent (bills/balance/reconciliation, purchase/provision,
   unsubscribe/delete, credentials, non-Huawei pricing) is declined and pointed to the correct service; the
   skill always keeps the right to refuse requests outside its read-only pricing scope.
5. **Never default Duration** — `usage_factor` must come from `ListUsageTypes` for that `resource_type_code`.
6. **Use slots ≠ size slots** — combine Measure Resolve rules in `references/commands.md`.

## Workflow — 4-Step RFQ

| Phase | What the agent does | Reference File |
| --- | --- | --- |
| **1. Parse** | Extract quadruple `cloud_service_type / resource_type / region / resource_spec` plus period or usage; read `references/semantic/catalog.yml` to route period vs on-demand | `references/semantic/catalog.yml` |
| **2. Clarify** | If region / quantity / period or usage / linear size is missing, ask in one round (2–4 candidates). Only safe-defaults (OS=linux, AZ=empty, `fee_installment_mode=NA`) may be disclosed and continued | `references/semantic/rfq-*.yml` |
| **3. Query** | Run the strict dimension chain, then the quote. Multi-candidate → ask user. Specs having rows ≠ quotable | `references/commands.md` |
| **4. Verify & Present** | Sum line items = total; align currency/period/quantity; format `[service] [spec] [region] [qty×period] = ¥<amount>`; append 加总 + 「非最终账单」; default official price, discount only if returned | this file (Response Requirements) |

### Dimension resolution chain (strict order)

`ListServiceResources` → `ListResourceSpecs` → (on-demand) `ListUsageTypes(--resource_type_code)` → `ListMeasureUnits` + Measure Resolve → quote.

Copy the first query from the matching `####` template in `references/commands.md`. No `--help`-based discovery during the flow; no self-constructed JSON; no full detail lists first.

## Core Commands

> All `hcloud BSS` commands use `--cli-region=cn-north-1`. Multi-line quotes are submitted in ONE
> request via dot notation `--product_infos.N.*` (max 100 lines). Pricing APIs have no pagination.

### Resolve project scope (IAM read-only)

```bash
hcloud IAM KeystoneListAuthProjects --cli-region={region} --cli-output=json
```

### List service / resource / spec dimensions (BSS read-only)

```bash
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json --limit={limit} --offset={offset}
hcloud BSS ListServiceResources --service_type_code={cloud_service_type} --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
hcloud BSS ListResourceSpecs --charge_mode=1 --cloud_service_type={cst} --resource_type={rt} --region_code={region} --filters.1.key=RESOURCE_SPEC --filters.1.value={spec_hint} --limit=100 --cli-region=cn-north-1 --cli-output=json
hcloud BSS ListUsageTypes --resource_type_code={rt} --cli-region=cn-north-1 --cli-output=json --limit=100 --offset=0
hcloud BSS ListMeasureUnits --cli-region=cn-north-1 --cli-output=json
```

### Period quote (BSS/ListRateOnPeriodDetail, read-only POST)

```bash
hcloud BSS ListRateOnPeriodDetail \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type={cst} \
  --product_infos.1.resource_type={rt} \
  --product_infos.1.resource_spec={spec} \
  --product_infos.1.region={deploy_region} \
  --product_infos.1.period_type={0|2|3|4} --product_infos.1.period_num={n} --product_infos.1.subscription_num={qty} \
  --cli-region=cn-north-1 --cli-output=json
```

Linear products (volume / bandwidth / share_bandwidth) additionally require
`--product_infos.1.resource_size={size} --product_infos.1.size_measure_id={17|15}`.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | fixed `cn-north-1` for all BSS commands |
| `--project_id` | Yes | resolved via `KeystoneListAuthProjects` |
| `--product_infos.N.id` | Yes | unique id within the request; maps response rows back |
| `--product_infos.N.cloud_service_type` | Yes | raw code from `ListServiceTypes` |
| `--product_infos.N.resource_type` | Yes | raw code from `ListServiceResources` |
| `--product_infos.N.resource_spec` | Yes | raw code from `ListResourceSpecs` (never fabricate; OS suffix already included) |
| `--product_infos.N.region` | Yes | actual deploy region of the resource |
| `--product_infos.N.period_type` | Yes | `0` day / `2` month / `3` year / `4` hour |
| `--product_infos.N.period_num` | Yes | number of periods |
| `--product_infos.N.subscription_num` | Yes | quantity, 1..10000 |
| `--product_infos.N.resource_size` | Conditional | linear products only (volume/bandwidth/share_bandwidth) |
| `--product_infos.N.size_measure_id` | Conditional | `17` GB (volume), `15` Mbps (bandwidth/share_bandwidth) |
| `--product_infos.N.fee_installment_mode` | No | default `NA` (CloudPond only) |

### On-demand quote (BSS/ListOnDemandResourceRatings, read-only POST)

```bash
hcloud BSS ListOnDemandResourceRatings \
  --project_id={project_id} \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type={cst} \
  --product_infos.1.resource_type={rt} \
  --product_infos.1.resource_spec={spec} \
  --product_infos.1.region={deploy_region} \
  --product_infos.1.usage_factor={factor} --product_infos.1.usage_value={value} --product_infos.1.usage_measure_id={mid} \
  --product_infos.1.subscription_num={qty} \
  --cli-region=cn-north-1 --cli-output=json
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--product_infos.N.usage_factor` | Yes | raw `code` from `ListUsageTypes` — never default `Duration` |
| `--product_infos.N.usage_value` | Yes | scalar per Measure Resolve rules (hours / GB×hour / GB / count) |
| `--product_infos.N.usage_measure_id` | Yes | usage slot id from `ListMeasureUnits` — ≠ `size_measure_id` |
| `--inquiry_precision` | No | `0` default 6 digits / `1` full 10 digits |

## Parameter Confirmation

Parameter tables live with each command group above — `Period quote` section lists the
`ListRateOnPeriodDetail` parameters (Required/Conditional/Optional), and `On-demand quote`
section lists `ListOnDemandResourceRatings` parameters. Dimension/list commands use `--limit`
/ `--offset` (optional, default 10), and `ListResourceSpecs` uses `--filters.[N].key=RESOURCE_SPEC`
plus `--filters.[N].value` for spec filtering. Exact required/optional split for every command is
verified against the runtime `--help` output of the concrete command (never guessed).

## Reading the Response

| API | Official price | Discounted (report only if present) |
| --- | --- | --- |
| `ListRateOnPeriodDetail` | `official_website_rating_result.official_website_amount` | `optional_discount_rating_results[]` where `best_offer==1` |
| `ListOnDemandResourceRatings` | root / `product_rating_results[]` `official_website_amount` | `amount` when `discount_amount>0` |

`measure_id=1` = CNY (人民币元); `currency=CNY`, empty means CNY. On-demand response already
contains `usage_value` — do NOT multiply again.

## Error Handling

| Code | Handling |
| --- | --- |
| `403` / `CBC.0151` | record operation + account scope; suggest the read-only Action from `references/iam-policies.md` |
| `429` | wait 2s, retry once; still failing → stop |
| `CBC.0100` | verify runtime `--help` vs parameter combination |
| `CBC.99006006` | back to spec / region / billing-mode confirmation (verified: non-existent spec → this code) |
| `CBC.99006055` | shrink quote batch or period |
| `CBC.6006` / `CBC.6050` | change usage type/factor or same-abbreviation sibling once; no exhaustive enumeration |

## Response Requirements

> Plain IM-friendly text; no GFM tables for user-facing messages. Use `·` bullets or numbering.

- **Line format**: `[service] [spec] [region] [qty×period] = ¥<amount>`
- **Sum** line items and verify sum = total; then label `<总价> 非最终账单`
- **Default official price**; attach discounted price only when the response returns a discount
- 口诀复核: restate the quadruple in plain words to confirm before quoting when ambiguous
- **Never expose** internal parameter names to the user; never echo full command chains

## KooCLI Command Format Standard

Every command follows the generic KooCLI shape: `hcloud` + the service name (e.g. `BSS`, `IAM`,
`ECS`) + a PascalCase operation name (e.g. `ListRateOnPeriodDetail`) + `--key=value` flags. The
placeholder tokens above (e.g. `<service>`) are illustrative only — never run them literally.

- Service names: `BSS`, `IAM`, `ECS` (detected case from KooCLI metadata)
- Operation names: PascalCase (e.g. `ListRateOnPeriodDetail`)
- Indexed params: `--product_infos.1.id=1` dot notation (JSON arrays / `[...]` not accepted)
- Region: BSS always `cn-north-1`; IAM uses the profile/current region; ECS AZ uses the resource region

## Reference Documents

| Document | Content |
| --- | --- |
| [references/commands.md](references/commands.md) | Command contracts, response fields, universal traps, Measure Resolve table |
| [references/semantic/catalog.yml](references/semantic/catalog.yml) | Routing catalog: period / on-demand / dimension_lookup |
| [references/semantic/rfq-shared-dimensions.yml](references/semantic/rfq-shared-dimensions.yml) | Shared conformed dimensions |
| [references/semantic/rfq-period-model.yml](references/semantic/rfq-period-model.yml) | Period quote fact/line model (Kimball star) |
| [references/semantic/rfq-ondemand-model.yml](references/semantic/rfq-ondemand-model.yml) | On-demand quote fact/line model |
| [references/dataflow-diagram.md](references/dataflow-diagram.md) | Mermaid data flow |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policies |
| [references/verification-method.md](references/verification-method.md) | How to verify the skill |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | KooCLI install/auth guide (only to relay to user) |
| [scripts/cost_estimation.py](scripts/cost_estimation.py) | Helper runner (read-only) with quality reporting |

## Hard Constraints (Non-Negotiable)

1. **Never guess prices or params** — price only from current response; params only from current `--help`.
2. **Never run a write command** — purchase/provision/renew/delete/unsubscribe stay on the console.
3. **Never accept credentials in chat** — AK/SK/token are refused and routed to the install guide.
4. **BSS endpoint fixed** — `hcloud BSS` always `--cli-region=cn-north-1`; deploy region lives in
   `product_infos.N.region`.
5. **No history bills / balance / reconciliation here** — route to 费用中心 or BSS billing read-only
   APIs.
6. **No cross-service quote synthesis** — each quote line's quadruple must come from its own dimension
   query.