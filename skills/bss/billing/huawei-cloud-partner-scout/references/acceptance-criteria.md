# Acceptance Criteria

## Functional
- [ ] All 9 query scenario groups from the requirement (客户管理 / 账户余额 / 收支明细 /
      云经销商 / 代金券额度 / 优惠券列表 / 客户消费账单 / 客户资源 / 订单查询) are
      reachable through the 10 catalog entry points.
- [ ] All 30 source operations map to real `huaweicloudsdkbss` methods whose REST paths
      were verified from SDK `_http_info` (no invented endpoints).
- [ ] Every copyable template in `related-commands.md` executes against the SDK without
      TypeError/import errors (validated with `limit=1` smoke runs).
- [ ] Read-only enforcement: no create/update/delete/pay API is present in any template;
      refused write operations are listed explicitly.

## Semantic Layer
- [ ] `catalog.yml` defines 10 entry_points, each with `required_context`, `triggers`,
      `primary_facts`, `ontology_files`.
- [ ] `shared-dimensions.yml` defines 9 conformed dimensions
      (Dim_Customer … Dim_Time).
- [ ] 6 model files cover business processes customer/partner/coupon/bill/resource/order.
- [ ] 22 facts total, including 2 child facts
      (`OrderDetail`, `RefundOrderDetail`, parent=`CustomerOrder`).
- [ ] Every measure declares `additivity` ∈ {additive, semi_additive, non_additive}.

## Robustness
- [ ] Error interception table covers: no-partner-access (`domain_id has no access to
      this api`), `CBC.0151`, `NETWORK_ERROR`/proxy, `CBC.80021021` (>1y span),
      limit>100 400 error.
- [ ] Credentials only from environment variables; none hardcoded.
- [ ] Identity/ID fields desensitized in output by default (No-Leak discipline).

## Quality Reporting
- [ ] `scripts/skill_quality_sdk.py` present (vendored from skillsopr).
- [ ] SKILL.md contains a `Quality Reporting` section with integration notes and
      error-code convention, and Prerequisites lists `SKILL_QUALITY_*` env vars.

## Compliance
- [ ] `bash validate-skill.sh skills/bss/billing/huawei-cloud-partner-scout` passes
      with no FAIL items.
- [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; all file extensions
      in the allowlist; references/ filenames kebab-case.