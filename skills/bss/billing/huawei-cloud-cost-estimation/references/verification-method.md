# Verification Method

How to verify the `huawei-cloud-cost-estimation` skill is working and compliant.

## 1. Prerequisite check

```bash
hcloud version                              # >= 7.2.2
hcloud IAM KeystoneListAuthProjects --cli-region=cn-north-1 --cli-output=json   # returns projects -> ok
hcloud BSS ListServiceTypes --cli-region=cn-north-1 --cli-output=json --limit=1 # BSS reachable
```

## 2. Dimension chain smoke test (read-only)

```bash
hcloud BSS ListServiceResources --service_type_code=hws.service.type.ec2 \
  --cli-region=cn-north-1 --cli-output=json --limit=3
hcloud BSS ListResourceSpecs --charge_mode=1 \
  --cloud_service_type=hws.service.type.ec2 --resource_type=hws.resource.type.vm \
  --region_code=cn-north-1 --filters.1.key=RESOURCE_SPEC --filters.1.value=c6.2xlarge \
  --limit=5 --cli-region=cn-north-1 --cli-output=json
hcloud BSS ListUsageTypes --resource_type_code=hws.resource.type.vm \
  --cli-region=cn-north-1 --cli-output=json --limit=5
hcloud BSS ListMeasureUnits --cli-region=cn-north-1 --cli-output=json
```

Expected: non-empty `service_types` / `infos` / `cloud_service_basics` / `usage_types` / `measure_units`.

## 3. Period quote check (read-only)

```bash
hcloud BSS ListRateOnPeriodDetail --project_id=<project_id> \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.ec2 \
  --product_infos.1.resource_type=hws.resource.type.vm \
  --product_infos.1.resource_spec=c6.2xlarge.2.linux \
  --product_infos.1.region=cn-north-1 \
  --product_infos.1.period_type=2 --product_infos.1.period_num=1 --product_infos.1.subscription_num=1 \
  --cli-region=cn-north-1 --cli-output=json
```

Expected: `official_website_rating_result.official_website_amount` present, `currency=CNY`.
Reference on a live account: c6.2xlarge.2.linux 1 month = 834.2 CNY; ac3.large.2.linux 1 month = 179.2 CNY.

## 4. On-demand quote check (read-only)

```bash
hcloud BSS ListOnDemandResourceRatings --project_id=<project_id> \
  --product_infos.1.id=1 \
  --product_infos.1.cloud_service_type=hws.service.type.ec2 \
  --product_infos.1.resource_type=hws.resource.type.vm \
  --product_infos.1.resource_spec=ac3.large.2.linux \
  --product_infos.1.region=cn-north-1 \
  --product_infos.1.usage_factor=Duration --product_infos.1.usage_value=1 --product_infos.1.usage_measure_id=4 \
  --product_infos.1.subscription_num=1 \
  --cli-region=cn-north-1 --cli-output=json
```

Expected: `official_website_amount` present, `currency=CNY`. Reference: 0.37 CNY for 1 hour.

## 5. Helper script check (optional)

```bash
python3 scripts/cost_estimation.py auth-projects
python3 scripts/cost_estimation.py period-quote --project-id=<id> --spec c6.2xlarge.2.linux \
  --service-type hws.service.type.ec2 --resource-type hws.resource.type.vm \
  --region cn-north-1 --period-type 2 --period-num 1 --quantity 1
```

## 6. Specification compliance

```bash
bash /root/.agents/skills/huawei-cloud-skill-creator/scripts/validate-skill.sh \
  /tmp/multica-task-3158059231/opencode/hws-skills/skills/bss/billing/huawei-cloud-cost-estimation
```

## 7. Security checks

- No AK/SK, tokens, or `hcloud configure set` commands in the skill package (except the
  config guide in `cli-installation-guide.md` for the user to run themselves).
- No write operations (Create/Delete/Update) are part of the skill's commands.
- No cross-skill calls.

## 8. Known environment notes

- `ECS/NovaListAvailabilityZones` may return `APIGW.0802` (forbidden in the selected region)
  when the account has no ECS scope there. It is an optional helper; quote flow should not
  depend on it.
- BSS metadata must be present (see `cli-installation-guide.md` section 2); otherwise
  commands report `Unsupported service: BSS`.