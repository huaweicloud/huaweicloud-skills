---
name: huawei-cloud-cost-estimation
description: |
  Generates Huawei Cloud pre-order estimates, provisions allowlisted resources through hcloud, and
  routes unsubscribe requests to console guidance. Use for Huawei Cloud pricing, budgets, creation,
  provisioning, or unsubscribe. Creates require runtime help, --dryrun, fee review, and confirmation.
  Never emits or runs unsubscribe operations, accepts credentials, or performs non-allowlisted writes.
  Triggers include: "华为云报价", "报价", "价格估算", "费用预估", "比价", "询价", "开通报价", "创建报价",
  "华为云价格", "价格查询", "预算评估", "费用计算", "price estimate", "cost estimation", "budget",
  "quote", "pricing", "provision", "create", "purchase", "价格", "费用", "华为云多少钱".
tags: [huawei-cloud, bss, billing, cost-estimation, provisioning]
---

# Huawei Cloud Cost Estimation and Provisioning

Prices come only from the current response: never guess, analogize, or recall them. Provisioning is
the only permitted write path; unsubscribe is console guidance only.

## Overview

Estimates Huawei Cloud pre-order costs and, when the user wants to buy or create, provisions
resources through an allowlisted `hcloud` command set, then routes unsubscribe requests to console
guidance. **Use when** the user asks about Huawei Cloud / 华为云 / hcloud pricing, budgets, creation or
provisioning in Chinese or English: 报价, 询价, 价格估算, 费用预估, 比价, 开通, 创建, price estimate,
budget, quote, pricing, provision, create, purchase. Answer: how much a resource will cost, which
spec/billing-mode combination fits, whether a resource can be provisioned, and how to unsubscribe —
never by guessing prices, inventing parameters, or running non-allowlisted writes.

- Pricing runs a 4-step RFQ flow (Parse → Clarify → Query → Verify & Present) over `hcloud BSS`
  read-only APIs in the fixed region `cn-north-1`.
- Lifecycle Create is limited to the 74 allowlisted operations in `references/lifecycle/commands.md`
  and only after `--help`, fee review, `--dryrun`, and explicit confirmation.
- Unsubscribe is console guidance only; no unsubscribe CLI/API is ever emitted or executed.

## Prerequisites

> **Prerequisite check: Huawei Cloud CLI (hcloud) >= 7.2.2** and an authenticated profile with
> BSS read-only + lifecycle dependency IAM permissions (see `references/iam-policies.md`).
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

> **Environment dependency (BSS pricing chain)**: the price-inquiry chain
> (`ListServiceTypes`, `ListServiceResources`, `ListResourceSpecs`, `ListUsageTypes`,
> `ListMeasureUnits`, `ListRateOnPeriodDetail`, `ListOnDemandResourceRatings`) runs against the
> authenticated account's BSS (Business Support System) APIs. In sandboxed or restricted
> environments where BSS access is not provisioned (no service metadata, no executor mapping), the
> pricing chain cannot be verified end-to-end. In that case state clearly that prices cannot be
> queried in the current environment, then stop — never guess, estimate from memory, or fabricate
> amounts.

## Scope

### In scope

| Request | Handling |
| --- | --- |
| Quote, budget, or comparison | Pricing (4-step RFQ) |
| Provision, purchase, or create | Lifecycle Create, limited to `references/lifecycle/commands.md` |
| Unsubscribe or stop using | console-only Unsubscribe Guidance |

### Out of scope — route, don't execute

| Request | Routing |
| --- | --- |
| Historical bills, balance, or reconciliation | 费用中心 or read-only BSS billing APIs (do not use this skill) |
| Non-Huawei cloud pricing | refuse politely |
| Non-allowlisted writes | console guidance; never run them |
| AK/SK/token in chat | point to `references/cli-installation-guide.md` |
| Remembering or guessing prices | prices only from the current hcloud response |

## Execution Pace

Complete chains of at most three hcloud commands directly to the next safety gate. For longer
chains, run only two or three commands per round, report progress and the next step, then ask
whether to continue. A user may request uninterrupted execution, but clarification, unknown-cost
approval, `--dryrun`, and write confirmation remain mandatory.

## Workflow

### Pricing — 4-Step RFQ

1. **Parse** `cloud_service_type / resource_type / region / resource_spec` plus period or usage;
   route through `references/pricing/semantic/catalog.yml`.
2. **Clarify** missing region, quantity, duration/usage, linear size, ambiguous categories, or
   unresolved variants in one question with two to four candidates. Disclose and apply only safe
   defaults: OS=linux, empty AZ, and `fee_installment_mode=NA`.
3. **Query** using `references/pricing/commands.md`: `ListServiceResources` → `ListResourceSpecs` →
   on-demand `ListUsageTypes(--resource_type_code)` → measure resolution → quotation. Ask on
   multiple matches; a spec match may still fail. Never invent duration or mix capacity and usage
   slots.
4. **Verify and present** that line items sum to the total and currency, period, and quantity align.
   Present `[service] [spec] [region] [quantity × period] = amount`, total, and “not a final bill.”
   Show discounts only when returned.

### Lifecycle Create — 7 Gates

Read `references/lifecycle/concepts.md`, then perform every gate in order:

1. **Allowlist** — Map intent to an operation in `references/lifecycle/commands.md`; refuse misses.
2. **Help** — Run `hcloud <Service> <Operation> --help` for required and conditional fields. Stop on
   `[APIE_ERROR]` or missing schema; never guess.
3. **Resolve** — Run required read-only dependencies such as VPC, subnet, AZ, image, and flavor. Let
   the user choose among multiple matches.
4. **Cost** — Use Pricing when possible. Otherwise disclose “price unknown and may incur charges”
   and obtain separate approval.
5. **Dry** — Add global `--dryrun` to the complete command. Fix and rerun failures; never promote a
   failed dry run.
6. **Confirm** — Show resource, region, spec, quantity, billing, known or unknown price, and batch
   order; wait for explicit confirmation.
7. **Execute** — Remove only `--dryrun`. Run multiple commands in order, stop on failure, never
   auto-rollback, and report succeeded, failed, and unexecuted items.

Any parameter, region, quantity, or operation change invalidates the dry run and confirmation and
returns to Help.

### Unsubscribe Guidance

Never run or generate unsubscribe CLI/API operations, and never use `--dryrun` as a substitute for
console preview.

- **Subscription resources:** direct the user to Huawei Cloud Console → Cost Center → Orders →
  Unsubscriptions. Ask them to back up or migrate data and verify the account, resource, related
  resources, refund, fees, and refund destination before submission.
- **Pay-per-use resources:** unsubscribe does not apply. Direct the user to the service console to
  delete the resource after backup; do not delete it for them.

If automation is requested, preserve this boundary and provide the
[official unsubscribe rules](https://support.huaweicloud.com/usermanual-billing/unsubscription_topic_2000010.html).

## Core Commands

> All `hcloud BSS` commands use `--cli-region=cn-north-1`. Arrays use dot notation
> (`--product_infos.N.*`); output with `--cli-output=json`. Full contracts and exact templates live
> in `references/pricing/commands.md` and `references/lifecycle/commands.md`.

### Resolve project scope (IAM read-only)

```bash
hcloud IAM KeystoneListAuthProjects --cli-region={region} --cli-output=json
hcloud IAM KeystoneListProjects --domain_id={domain_id} --cli-region={region} --cli-output=json
```

### Pricing dimensions (BSS read-only)

```bash
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json --limit=10 --offset=0
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
`--product_infos.N.resource_size={size} --product_infos.N.size_measure_id={17|15}`.

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

### Lifecycle create (allowlisted write path)

The 74 allowlisted operations (e.g. `ECS/CreateServers`, `DDS/CreateInstance`, `RDS/CreateInstance`)
are enumerated in `references/lifecycle/commands.md`. Parameters always come from the current
`--help`, never from memory. Minimal executable example (VPC is allowlisted, `VPC/CreateVpc` is a
readily dry-runnable create):

```bash
hcloud VPC CreateVpc --help
hcloud VPC CreateVpc --vpc.name={name} --vpc.cidr=172.16.0.0/16 --cli-region={region} --dryrun
```

Every other allowlisted operation follows the same shape: run `--help` first, then build the full
command from the help output, add `--dryrun`, and only remove `--dryrun` after the dry-run gate and
explicit confirmation. Pass the `--dryrun` gate and explicit confirmation before executing without
`--dryrun`; one failure stops the batch, no auto-rollback.

### Lifecycle dependency lookups (read-only)

Run only the dependencies the help output marks required (`references/lifecycle/commands.md`):

```bash
hcloud EPS ListEnterpriseProject --cli-region=cn-north-4 --cli-output=json
hcloud VPC ListVpcs --cli-region={region} --cli-output=json
hcloud VPC ListSubnets --cli-region={region} --cli-output=json
hcloud ECS NovaListAvailabilityZones --cli-region={region} --cli-output=json
hcloud IMS ListImages --cli-region={region} --cli-output=json
hcloud EVS CinderListVolumeTypes --cli-region={region} --cli-output=json
hcloud ECS NovaListKeypairs --cli-region={region} --cli-output=json
hcloud ECS NovaListFlavors --cli-region={region} --cli-output=json
```

> **EPS region note**: EPS does not support `cn-north-1`. Query enterprise projects with
> `--cli-region=cn-north-4` (or another EPS-enabled region such as `ru-moscow-1` /
> `my-kualalumpur-1`); the returned `enterprise_project_id` is region-independent for lifecycle
> create parameters. The BSS fixed region `cn-north-1` applies to price inquiry only, never to EPS.

## Parameter Confirmation

| Parameter | Required | Description | Example |
| --- | --- | --- | --- |
| `--cli-region` | Yes (auto) | fixed `cn-north-1` for all BSS commands | `--cli-region=cn-north-1` |
| `--project_id` | Yes | resolved via `KeystoneListAuthProjects` | `--project_id=xxx` |
| `--product_infos.N.cloud_service_type` | Yes | raw code from `ListServiceTypes` | `hws.service.type.ec2` |
| `--product_infos.N.resource_type` | Yes | raw code from `ListServiceResources` | `hws.resource.type.vm` |
| `--product_infos.N.resource_spec` | Yes | raw code from `ListResourceSpecs` (never fabricate) | `c6.2xlarge.2.linux` |
| `--product_infos.N.region` | Yes | actual deploy region of the resource | `cn-north-4` |
| `--product_infos.N.subscription_num` | Yes | quantity, 1..10000 | `1` |
| `--product_infos.N.period_type` | Conditional | period quote only: `0` day / `2` month / `3` year / `4` hour | `2` |
| `--product_infos.N.period_num` | Conditional | period quote only: number of periods | `1` |
| `--product_infos.N.usage_factor` | Conditional | on-demand only: raw `code` from `ListUsageTypes` | `Duration` |
| `--product_infos.N.usage_value` | Conditional | on-demand only: scalar per Measure Resolve rules | `2` |
| `--product_infos.N.usage_measure_id` | Conditional | on-demand only: usage slot from `ListMeasureUnits` (≠ `size_measure_id`) | `4` |
| `--product_infos.N.resource_size` | Conditional | linear products only (volume / bandwidth / share_bandwidth) | `40` |
| `--product_infos.N.size_measure_id` | Conditional | `17` GB (volume), `15` Mbps (bandwidth / share_bandwidth) | `17` |
| `--dryrun` | Yes (lifecycle) | global dry-run gate before any create; never `--dry-run` | `--dryrun` |

Missing region, quantity, duration/usage, or linear size is clarified in one question with two to
four candidates before any command runs.

## Unsubscribe Console Path

Never run or generate unsubscribe CLI/API operations; `--dryrun` previews request construction only
and never replaces the console. Subscription resources go through Console → Cost Center → Orders →
Unsubscriptions after data backup and account/resource/refund verification; pay-per-use resources
are deleted by the user in the service console after backup.

## Critical Rules

1. Prices come from the current response; parameters come from current help.
2. No real create call without a successful `--dryrun` and explicit confirmation.
3. Never automate or emit unsubscribe operations.
4. Refuse AK, SK, and tokens in chat; point to `references/cli-installation-guide.md` for
   self-configuration.
5. Every BSS call uses `--cli-region=cn-north-1`; `product_infos.N.region` remains the deployment
   region.
6. Route out-of-scope work to Cost Center, the appropriate console, or read-only billing.

Use bullets or numbered items, not GFM tables, in user-facing responses. For command-level traps,
read `references/pricing/commands.md`.

## KooCLI Command Format Standard

Every command follows the generic KooCLI shape:
`hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]`.

| Feature | Description | Example |
| --- | --- | --- |
| Service name | Exact KooCLI Service name beginning with uppercase/title case | `BSS`, `IAM`, `ECS`, `VPC`, `DDS` |
| Operation name | PascalCase | `ListRateOnPeriodDetail`, `CreateServers` |
| Region parameter | `--cli-region=<value>` | `--cli-region=cn-north-1` |
| Simple parameter | `--key=value` | `--project_id=xxx` |
| Indexed parameter | `--key.N=value` dot notation | `--product_infos.1.id=1` |
| Global dry-run | `--dryrun` (not `--dry-run`) | `--dryrun` |

Placeholder tokens above (e.g. `<Service>`) are illustrative only — never run them literally.

## Reference Documents

| Document | Content |
| --- | --- |
| [references/lifecycle/concepts.md](references/lifecycle/concepts.md) | Lifecycle execution concepts: allowlist, help, lookup, dry-run, fee status, batch invariants, unsubscribe console path |
| [references/lifecycle/commands.md](references/lifecycle/commands.md) | The 74 allowlisted create operations and dependency lookup commands |
| [references/pricing/commands.md](references/pricing/commands.md) | Pricing command contracts, response fields, universal traps, Measure Resolve table |
| [references/pricing/semantic/catalog.yml](references/pricing/semantic/catalog.yml) | Routing catalog: period / on-demand / dimension_lookup |
| [references/pricing/semantic/rfq-ondemand-model.yml](references/pricing/semantic/rfq-ondemand-model.yml) | On-demand quote fact/line model |
| [references/pricing/semantic/rfq-period-model.yml](references/pricing/semantic/rfq-period-model.yml) | Period quote fact/line model |
| [references/pricing/semantic/rfq-shared-dimensions.yml](references/pricing/semantic/rfq-shared-dimensions.yml) | Shared conformed dimensions |
| [references/iam-policies.md](references/iam-policies.md) | Least-privilege IAM policies |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | KooCLI install and auth guide (only to relay to user) |

For 403 or permission failures, read `references/iam-policies.md`. If hcloud is unavailable, relay
`references/cli-installation-guide.md`; never install it for the user.