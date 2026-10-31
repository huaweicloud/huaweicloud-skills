# Cost Estimation for Single-to-HA Conversion (RDS for MySQL)

> This reference supports the SKILL workflow cost assessment step (Step 6). It documents the behavior of `scripts/rds_cost_estimate.py` in compare mode and the verified pricing API facts (remote validation 2026-10-22, instance `c29f...in01`, cn-north-4).

## 1. Purpose

The cost assessment estimates how much converting a single RDS for MySQL instance to a primary/standby (HA) instance increases the cost. It quotes both the single instance spec and its corresponding HA spec, for the compute flavor and the instance storage volume, and reports the price delta and multiple. The assessment is read-only: it only queries prices and never creates any resource.

## 2. Compare Mode

Run the script in compare mode with the single instance flavor, storage, and charge mode from the pre-check report:

```bash
python3 scripts/rds_cost_estimate.py \
  --region <region> \
  --compare-single-ha \
  --spec-code <single_flavor_ref> \
  --storage-size-gb <volume_size> \
  --storage-type <volume_type> \
  --charge-mode <charge_mode> \
  --output rds_cost_estimate_result.json
```

The `--charge-mode` value comes from the Step 5 pre-check report (`pre_check.instance_status.charge_mode`, one of `postPaid`/`prePaid`): `postPaid` quotes only on-demand prices, `prePaid` only monthly/yearly prices, and omitting the flag quotes both modes (backward compatible).

The script derives the HA spec code from the single spec code:

| Flavor family | Rule | Example |
| --- | --- | --- |
| x86 | append `.ha` | `rds.mysql.x1.large.2` → `rds.mysql.x1.large.2.ha` |
| ARM | replace `.single` with `.ha` | `rds.mysql.large.arm2.single` → `rds.mysql.large.arm2.ha` |

Verified fact: all 54 single flavors of MySQL 8.0 have a paired HA flavor; `instance_mode` values are lowercase `single`/`ha`/`replica`.

## 3. Storage Spec Mapping

The storage `resource_spec` is derived from the instance `volume.type` and the deployment mode:

| volume.type | single | ha |
| --- | --- | --- |
| CLOUDSSD | `rds.mysql.volume.cloudssd` | `rds.mysql.volume.cloudssd.ha` |
| ESSD | `rds.mysql.volume.essd` | `rds.mysql.volume.essd.ha` |
| ESSD2 | `rds.mysql.volume.essd2` | `rds.mysql.volume.essd2.ha` |
| GPSSD2 | `rds.mysql.volume.gpssd2` | `rds.mysql.volume.gpssd2.ha` |

The mapping is verified via `ListResourceSpecs` (cloud_service_type `hws.service.type.rds`, resource_type `hws.resource.type.rds.volume`). An unmapped `volume.type` (e.g. `ULTRAHIGH`, which MySQL does not use) produces a warning and the storage quote is skipped.

## 4. Output Structure

The compare report contains:

- `single_price` / `ha_price` — per-spec results, each with `on_demand` (true on-demand quote, null when filtered out by `--charge-mode prePaid`) and `period_pricing` (monthly `period_type=2`, yearly `period_type=3`, empty when filtered out by `--charge-mode postPaid`); each price line carries `compute` / `storage` / `total` components
- `price_delta` — the formatted difference between the HA total and the single total (preferred from the true on-demand amount, then monthly, then yearly)
- `ha_multiple` — the formatted HA/single total multiple (about 2x for the compute flavor)
- `query_params.charge_mode` — the instance charge-mode filter (`postPaid`/`prePaid`/null for both)
- `query_params.storage_specs` — the resolved single/ha storage specs
- `scope_note` — states that storage is included in the comparison when quoted (detected across both the on-demand and period quote lines)
- `warnings` — per-quote failures isolated without aborting the run

## 5. Verified Pricing API Facts

- **On-demand quoting works** via `BSS ListOnDemandResourceRatings` with `usage_measure_id=4` (hour). `usage_measure_id=1` fails with `CBC.6050` (`Convert from value measure(1) to measure unit(4) error`). The true on-demand prices match the console page "pay-per-use" unit price.
- **Storage is quotable** as a second product (`resource_type=hws.resource.type.rds.volume`, `resource_size=<GB>`, `size_measure_id=17`) in both `ListOnDemandResourceRatings` and `ListRateOnPeriodDetail`.
- Verified prices for 40 GB CLOUDSSD (cn-north-4): single storage 0.08 CNY/h / 40 CNY/month / 400 CNY/year; HA storage 0.088 CNY/h / 64 CNY/month / 640 CNY/year. HA storage is higher: about +10% on-demand, about +60% monthly/yearly.
- Verified compute prices for `rds.mysql.x1.large.2`: on-demand 0.54 CNY/h, 275 CNY/month, 2,750 CNY/year; HA (`rds.mysql.x1.large.2.ha`): on-demand 1.08 CNY/h, 550 CNY/month, 5,500 CNY/year. The HA compute flavor is exactly 2x the single flavor.
- The previous `period_type=4` hourly prepaid price (0.38 single / 0.76 HA) is **not** the on-demand price; it is about 42% lower and is no longer used as the on-demand reference.
- All BSS calls use `--cli-region=cn-north-1` (BSS is a global service); the real region is passed in `product_infos.N.region`.

### Failure-mode interpretation — BSS channel-region error vs quote-business error

The hard-coded `--cli-region=cn-north-1` is the BSS channel region only; it does **not** affect quote correctness because the real instance region is carried per product in `product_infos.N.region`. The two error modes below are distinct and **must** be interpreted differently:

- **BSS channel-region error** — when a user runs the script from a non-`cn-north-1` region and BSS is restricted for that channel, the hcloud CLI raises a "region not supported" type error before the BSS call reaches the rating engine. The exception path (`HcloudError` raised by `run_hcloud`) is caught in `quote_on_demand` / `quote_period` and recorded as a warning whose text carries the BSS channel context — `BSS channel cn-north-1, instance region <region>` — so the channel-layer cause is visible at the warning layer. This is **not** a quote-business error: the rating engine never ran, and switching the BSS channel (or checking BSS permissions) resolves it. **Do not** treat this as a quote failure of the target region/flavor.
- **Quote-business error** — when the BSS rating engine runs and the response carries an `error_code` (e.g. `CBC.6050` from `usage_measure_id=1`), the warning text records the parsed `error_code`/`error_msg` directly. This is a quote-business error from the rating engine; the `--cli-region` channel is healthy and the error reflects a real rating-layer rejection.

The two paths are distinguishable in the `warnings[]` array: channel-layer warnings carry the `BSS channel ... instance region ...` annotation, business-layer warnings carry the parsed `error_code`. SKILL.md Step 6 surfaces this as a constraint; this paragraph is the mechanism.
