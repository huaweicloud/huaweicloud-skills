# Cost Estimation for Single-to-HA Conversion (RDS for MySQL)

> This reference supports the SKILL workflow cost assessment step (Step 5). It documents the behavior of `scripts/rds_cost_estimate.py` in compare mode and the verified pricing API facts (remote validation 2026-10-22 and 2026-11-06, cn-north-4 and cn-south-1).

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

The SKILL workflow **always** passes `--charge-mode` with the instance's actual charge mode from the Step 4 pre-check report. An instance has exactly one billing mode, so quoting both would show a price that can never apply to it: `postPaid` quotes on-demand prices only, `prePaid` quotes monthly/yearly prices only. The workflow must never omit the flag, because omitting it quotes both modes.

The script still supports omitting `--charge-mode` for ad-hoc CLI use (backward compatible), but that path is **not** used by the workflow.

The script derives the HA spec code from the single spec code with the shared rule in `rds_common.derive_ha_spec_code`, which the pre-condition check reuses:

| Instance type | `group_type` | Single spec shape | Rule | Example |
| --- | --- | --- | --- | --- |
| Dedicated | `dedicated` | no suffix | append `.ha` | `rds.mysql.x1.large.2` → `rds.mysql.x1.large.2.ha` |
| General-purpose | `general` | no suffix | append `.ha` | `rds.mysql.n1.large.2` → `rds.mysql.n1.large.2.ha` |
| Kunpeng general-enhanced | `armFlavors` | `.single` suffix | replace `.single` with `.ha` | `rds.mysql.large.arm2.single` → `rds.mysql.large.arm2.ha` |

Verified against the MySQL 8.0 catalog (2026-11-06, 248 flavors): the rule matched 48 of the 49 single flavors. The one miss, `rds.mysql.x1.32xlarge.2`, has **no** HA counterpart at all, so the derivation is correct but the result must still be looked up in `ListFlavors` before claiming support. The reverse also exists: `rds.mysql.x1.48xlarge.4.ha` is an HA flavor with no single counterpart.

`instance_mode` has four values: `single`, `ha`, `replica` (read replica) and `cluster`. Only `ha` is a primary/standby flavor — filtering with "not single" would wrongly pull in 150 replica and cluster entries.

### 2.1 Price multiple is not a fixed 2x

Verified quotes (cn-south-1, CNY, 2026-11-06):

| Instance type | Flavor | On-demand single → HA | Multiple | Monthly single → HA | Multiple |
| --- | --- | --- | --- | --- | --- |
| General | `rds.mysql.n1.large.2` | 0.32 → 1.02 | **3.19x** | 156 → 406 | **2.60x** |
| General | `rds.mysql.n1.large.4` | 0.38 → 1.15 | **3.03x** | 190 → 520 | **2.74x** |
| General | `rds.mysql.n1.xlarge.2` | 0.75 → 1.90 | **2.53x** | 360 → 805 | **2.24x** |
| General | `rds.mysql.n1.2xlarge.4` | 1.91 → 4.20 | **2.20x** | 1000 → 2000 | 2.00x |
| Dedicated | `rds.mysql.x1.large.2` | 0.54 → 1.08 | 2.00x | 275 → 550 | 2.00x |
| Kunpeng | `rds.mysql.2xlarge.arm2.single` | 1.48 → 2.97 | 2.01x | 712 → 1424 | 2.00x |

General-purpose flavors show a 2.2x–3.2x multiple that shrinks as the flavor grows; dedicated and Kunpeng flavors are consistently about 2x. The SKILL must present the multiple actually quoted and must not state a fixed "about 2x" figure.

## 3. Storage Spec Mapping

The storage `resource_spec` is derived from the instance `volume.type` and the deployment mode:

| volume.type | single | ha |
| --- | --- | --- |
| CLOUDSSD | `rds.mysql.volume.cloudssd` | `rds.mysql.volume.cloudssd.ha` |
| ESSD | `rds.mysql.volume.essd` | `rds.mysql.volume.essd.ha` |
| ESSD2 | `rds.mysql.volume.essd2` | `rds.mysql.volume.essd2.ha` |
| GPSSD2 | `rds.mysql.volume.gpssd2` | `rds.mysql.volume.gpssd2.ha` |

The mapping is verified via `ListResourceSpecs` (cloud_service_type `hws.service.type.rds`, resource_type `hws.resource.type.rds.volume`, paginated with `--marker`, and requiring `charge_mode` and `region_code`). `RDS ListStorageTypes` returns exactly these four values as the legal `volume.type` values for MySQL in a region, so the map is complete for the type vocabulary ListInstances actually reports.

**Storage type must come from ListInstances, never from RMS.** RMS `properties.volumeType` reports `ULTRAHIGH` for a MySQL instance whose ListInstances `volume.type` is `CLOUDSSD`; the BSS catalog has no `rds.mysql.*ultrahigh*` entry at all (ULTRAHIGH exists only for HWSQL, MSSQL, PostgreSQL and openGauss). Using the RMS value would silently drop the storage line from the quote.

The BSS catalog also carries IOPS/throughput variants (`rds.mysql.volume.essd2.iops`, `rds.mysql.volume.gpssd2.iops`, `rds.mysql.volume.gpssd2.throughput`, and their `.ha` counterparts) and edge variants (`edgessd`, `edgesas`). Those are not returned by `ListStorageTypes` as `volume.type` values, so an unmapped type still produces a warning and the storage quote is skipped rather than guessing.

## 4. Output Structure

The compare report contains:

- `single_price` / `ha_price` — per-spec results, each with `on_demand` (true on-demand quote, null when filtered out by `--charge-mode prePaid`) and `period_pricing` (monthly `period_type=2`, yearly `period_type=3`, empty when filtered out by `--charge-mode postPaid`); each price line carries `compute` / `storage` / `total` components
- `price_delta` — the formatted difference between the HA total and the single total (preferred from the true on-demand amount, then monthly, then yearly)
- `ha_multiple` — the formatted HA/single total multiple (about 2x for dedicated and Kunpeng flavors, 2.2x–3.2x for general-purpose flavors; see section 2.1)
- `query_params.charge_mode` — the instance charge-mode filter (`postPaid`/`prePaid`/null for both)
- `query_params.storage_specs` — the resolved single/ha storage specs
- `scope_note` — states that storage is included in the comparison when quoted (detected across both the on-demand and period quote lines)
- `warnings` — per-quote failures isolated without aborting the run

## 5. Verified Pricing API Facts

- **On-demand quoting works** via `BSS ListOnDemandResourceRatings` with `usage_measure_id=4` (hour). `usage_measure_id=1` fails with `CBC.6050` (`Convert from value measure(1) to measure unit(4) error`). The true on-demand prices match the console page "pay-per-use" unit price.
- **Storage is quotable** as a second product (`resource_type=hws.resource.type.rds.volume`, `resource_size=<GB>`, `size_measure_id=17`) in both `ListOnDemandResourceRatings` and `ListRateOnPeriodDetail`.
- Verified prices for 40 GB CLOUDSSD (cn-north-4): single storage 0.08 CNY/h / 40 CNY/month / 400 CNY/year; HA storage 0.088 CNY/h / 64 CNY/month / 640 CNY/year. HA storage is higher: about +10% on-demand, about +60% monthly/yearly.
- Verified compute prices for `rds.mysql.x1.large.2`: on-demand 0.54 CNY/h, 275 CNY/month, 2,750 CNY/year; HA (`rds.mysql.x1.large.2.ha`): on-demand 1.08 CNY/h, 550 CNY/month, 5,500 CNY/year. The HA compute flavor is exactly 2x the single flavor.
- **BSS only accepts `cn-north-1` as the `--cli-region` channel**; any other value fails with `cli-region的值不支持,当前支持的区域值如下: cn-north-1`. The real region travels in `product_infos.N.region` and the project id is the target region's project id.
- **RMS only accepts `cn-north-4` as the `--cli-region` channel**, with the same style of rejection for any other value. It is independent of the region the instances live in.
- Prepaid responses carry `optional_discount_rating_results` (usually empty) and no `discount_rating_results`; `parse_period` therefore falls back to `official_website_rating_amount`, which is the correct total for these accounts.
- The previous `period_type=4` hourly prepaid price (0.38 single / 0.76 HA) is **not** the on-demand price; it is about 42% lower and is no longer used as the on-demand reference.
- All BSS calls use `--cli-region=cn-north-1` (BSS is a global service); the real region is passed in `product_infos.N.region`.

### Failure-mode interpretation — BSS channel-region error vs quote-business error

The hard-coded `--cli-region=cn-north-1` is the BSS channel region only; it does **not** affect quote correctness because the real instance region is carried per product in `product_infos.N.region`. The two error modes below are distinct and **must** be interpreted differently:

- **BSS channel-region error** — when a user runs the script from a non-`cn-north-1` region and BSS is restricted for that channel, the hcloud CLI raises a "region not supported" type error before the BSS call reaches the rating engine. The exception path (`HcloudError` raised by `run_hcloud`) is caught in `quote_on_demand` / `quote_period` and recorded as a warning whose text carries the BSS channel context — `BSS channel cn-north-1, instance region <region>` — so the channel-layer cause is visible at the warning layer. This is **not** a quote-business error: the rating engine never ran, and switching the BSS channel (or checking BSS permissions) resolves it. **Do not** treat this as a quote failure of the target region/flavor.
- **Quote-business error** — when the BSS rating engine runs and the response carries an `error_code` (e.g. `CBC.6050` from `usage_measure_id=1`), the warning text records the parsed `error_code`/`error_msg` directly. This is a quote-business error from the rating engine; the `--cli-region` channel is healthy and the error reflects a real rating-layer rejection.

The two paths are distinguishable in the `warnings[]` array: channel-layer warnings carry the `BSS channel ... instance region ...` annotation, business-layer warnings carry the parsed `error_code`. SKILL.md Step 6 surfaces this as a constraint; this paragraph is the mechanism.
