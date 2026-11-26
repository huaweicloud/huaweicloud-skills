# Gotchas

Read relevant sections; reuse prior reads. Fields and normal steps are in command references.

Assessment: met → continue; not met → correct. Missing, conflicting or inapplicable evidence → unresolved: pause dependent steps, continue independent work. Report tool failures separately; unknown ≠ zero.

## A. Responses and evidence

- **G01 | Response completeness.** `exit 0 ≠ business success`. Capture complete output, check business status and pagination scope, then filter. Errors are clues: inspect permission evidence for 403; for read-only 429 wait two seconds and retry once; repair parameter errors once with field evidence. Write failures follow G11.

- **G02 | Region and API identity.** `BSS endpoint = cn-north-1; resource region = deployment region`. BSS quotes accept any valid accessible project of the quoted customer; regional creation uses the target-region project. Use current explicit-version help; pause related calls when parameter definitions are missing. Configuration output includes only necessary status, hiding profile names and credential fragments. Readiness checks use CLI/IAM only; financial queries must belong to the user's financial task.

## B. Pricing, aggregating or exporting

- **G03 | Configuration and billing bindings.** `spec identity = service + resource type + region + billing mode + full spec code`. Check existing OS suffixes in fuzzy matches; obtain creation IDs from the service API. Identity changes require another lookup; price-affecting configuration changes require repricing, and removing a resource removes its charges. Capacity/usage mappings need product evidence linking billing item, field and unit ID; spec names, amounts, unit dictionaries or price changes, even combined, do not suffice. If a binding is unknown, pause that line's rating calls; do not probe by omitting capacity, changing unit IDs or trying unbound specs. Continue independent lines or obtain a same-configuration console quote.

- **G04 | Quantity and units.** `quantity ≠ capacity ≠ usage`; use `usage = capacity × duration` only when the product contract supports it. Resolve subscription_num, resource_size, usage_value and capacity/usage units separately; do not default the factor to Duration. Follow the [pricing contract](pricing/commands.md) for mode fields and CLI spelling; API error field names do not replace CLI field names.

- **G05 | ELB fee scope.** New shared instances incur an instance fee; historical free conditions apply only to legacy instances proven eligible. Dedicated fixed specifications incur converted LCU fees; pay-per-use elastic specifications incur LCU plus instance fees. Selected EIP/bandwidth is additional. Resolve network/application flavor and AZ count before applying G03; spec names alone do not establish capacity units. Amounts apply only to the matching configuration and query time. [Shared billing][elb-shared] / [dedicated billing][elb-dedicated].

- **G06 | Quote completeness.** `subtotal = Σ verified lines for the current configuration, currency and amount basis`. Check in-scope billing items against product evidence; match responses by request and line ID, sum full precision, then round. On-demand responses already include usage; do not multiply again. Display gaps beside the subtotal and do not call it a complete total while gaps remain. HTML and diagrams use the same data and states. Verify what zero means; `monthly price × 12 ≠ annual offer`. Comparisons require identical scope and basis; tax terms, validity periods, SLAs and price guarantees require separate evidence.

## C. Compatibility and ability to create

- **G07 | Network constraints.** In ordinary regional VPCs, recorded subnet AZ does not restrict ECS placement. Check chosen-VPC membership, subnet status and free IPs; check disk/instance and special-network constraints separately. Security-group vpc_id is advisory: missing or different values do not require a new group. Actual rules determine port access; the name default does not. [Subnet definition][subnet] / [security-group definition][security-group].

- **G08 | Conclusion boundaries.** `directory match ≠ sale availability ≠ this account's ability to create`; balance covering a quote also does not establish ability to create. For ECS use target-AZ status when present, otherwise regional status; regional abandon does not override AZ normal. Check billing support, account conditions and dependencies; other services use their own definitions. Empty AZ only removes the pricing filter.

## D. Creation preparation, orders and failures

- **G09 | Request consistency.** `execution request = checked request − global --dryrun`. Restore service dry_run/dryRun execution values before the global check. Dry run establishes constructibility only; check conditional fields for the exact operation and path, not a similar API. Recheck request edits; material configuration/cost/payment/renewal/login changes need reconfirmation, while authorized non-material repairs retain approval. Invoke dry run and real creation separately.

- **G10 | Acceptance, payment and delivery.** Each state needs its own evidence: `order ID ≠ paid; resource ID ≠ delivered; balance difference ≠ itemized payment`. ECS/EVS default to manual payment; set payment fields explicitly from the command table and renewal false unless requested. EVS server_id inherits billing mode, not auto-pay or a new full month; verify period and end date separately. EIP auto-pay uses cash; coupons require console payment.

- **G11 | Write retries.** Submit serially in confirmed order; an error or uncertain acceptance pauses remaining writes.
  - Explicit parameter rejection without acceptance: repair from evidence, recheck and retry the same purchase once.
  - Timeout or uncertain acceptance: reconcile first; do not resend until acceptance is ruled out.
  - Pending payment: prefer console payment of the original order.
  Replacement requires separate authorization identifying the old order and duplicate-purchase risk; verify cancellation/expiry. Respect service idempotency scope and lifetime; do not cycle purchases or roll back automatically. Report completed, failed, unresolved and unexecuted items separately.

## E. Credentials and potentially secret-bearing output

- **G12 | Secret-output boundary.** `private JSON ≠ private logs`: KooCLI 7.2.12 dry run prints adminPass. Generate/use secrets locally; files 0600, directories 0700. Organize cli-jsonInput by complete parameter locations such as path/body. Capture/redact stdout/stderr before tool output, inspect CLI logs and disable debug/shell tracing; redaction failure returns only an error. Deliver credential locations; remove temporary copies after safe handoff and outcome reconciliation. If unsupported, use a user-local step or an agreed key method. Never collect AK/SK/tokens in chat or load private keys into context. [Input contract][json-input].

[elb-shared]: https://support.huaweicloud.com/price-elb/elb_billing_0004.md
[elb-dedicated]: https://support.huaweicloud.com/price-elb/elb_billing_0003.md
[subnet]: https://support.huaweicloud.com/api-vpc/vpc_subnet01_0002.md
[security-group]: https://support.huaweicloud.com/api-vpc/vpc_sg01_0001.md
[json-input]: https://support.huaweicloud.com/hcli_faq/hcli_19_004.md
